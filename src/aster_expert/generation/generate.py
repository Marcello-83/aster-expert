"""`aster-expert generate <fiche> <données> <maillage vérifié>` (lot 28, Étape 3).

Orchestrates the whole `.comm` build: refuses to run unless the fiche is
ready, the mesh was verified for the exact parameters the data file gives
today, and the five Étape 2 facts are present, then assembles the
deterministic text via `aster_expert.generation.comm` and writes it out.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.hypotheses import CodeAsterHypothesisEntry, HypothesesSheet
from aster_expert.agent.model_data import load_model_data
from aster_expert.generation import comm
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.springs import build_spring_classes, check_spring_sum
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.combiwall import build_params, expected_masses
from aster_expert.meshing.run import REPORT_NAME as RUN_REPORT_NAME
from aster_expert.meshing.run import MeshRunReport, find_verified_mesh, sha256_file

_REQUIRED_FACT_TOPICS = (
    "Liaison de corps solide entre un anneau de nœuds de coque et un nœud de poutre",
    "Pression répartie fonction de Z sur des coques DKT",
    "Orientation cohérente des normales de coque pour qu'une pression positive "
    "agisse côté terre",
    "Représentation d'un profil de pression discontinu par points doublés à "
    "Z ± 0,001 m",
    "Conditions de symétrie par rapport à un plan X = constante pour des coques "
    "DKT et des poutres POU_D_E",
    "Élément de barre : section, matériau, et absence de degré de rotation au "
    "nœud commun avec la coque",
    "Application d'une force et d'un moment nodaux sur un nœud d'élément de poutre",
)


def _params_json_bytes(params: dict[str, Any]) -> bytes:
    """Byte-identical to `scripts/build_lot27_maillage.py`'s own `_json`
    serialisation of the parameters file `mesh run` hashed at run time."""
    return (json.dumps(params, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _check_facts_present(sheet: HypothesesSheet) -> list[str]:
    topics = {
        e.topic
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.status == "tranche"
    }
    return [t for t in _REQUIRED_FACT_TOPICS if t not in topics]


class GenerationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    comm_sha256: str
    fiche_sha256: str
    data_sha256: str
    med_sha256: str
    aster_version: str
    n_spring_classes: int
    spring_sums_mn_per_m: dict[str, float]
    load_case_resultants_n: dict[str, tuple[float, float, float]]


def _tube_beam_points(params: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    axes = params["tube"]["axes_x"]
    y, z = params["poutre"]["y"], params["poutre"]["z"]
    return {f"{i:02d}": (x, y, z) for i, x in enumerate(axes, start=1)}


def _normal_reference_point(params: dict[str, Any]) -> tuple[float, float, float]:
    """A point on the land-side generatrix (angle 90 degrees, Y = +radius) of
    the central tube, at its head level -- any node of `ECRAN_POUSSEE`, whose
    geometric normal there is exactly (0, 1, 0)."""
    tube = params["tube"]
    central_axis = tube["axes_x"][tube["central"] - 1]
    return (central_axis, tube["rayon"], tube["cotes"][-1])


def _ascending_component(
    mv: ModelValues, name: str, component: str
) -> list[tuple[float, float]]:
    from aster_expert.generation.profiles import (  # noqa: PLC0415
        component_profile,
        doubled_profile,
    )

    points = mv.profile_si(name)
    comp = component_profile(points, component)
    return doubled_profile(list(reversed(comp)))


def generate_comm(
    *,
    fiche_path: Path,
    data_path: Path,
    med_path: Path,
    project_root: Path,
    work_dir_root: str,
    aster_version: str,
) -> tuple[str, GenerationReport]:
    if not fiche_path.is_file():
        message = f"fiche introuvable : {fiche_path}"
        raise GenerationError(message)
    if not data_path.is_file():
        message = f"fichier de données introuvable : {data_path}"
        raise GenerationError(message)
    if not med_path.is_file():
        message = f"maillage introuvable : {med_path}"
        raise GenerationError(message)

    sheet = HypothesesSheet.model_validate_json(fiche_path.read_text(encoding="utf-8"))
    data = load_model_data(data_path)
    blockers = sheet.generation_blockers(data)
    if blockers:
        message = (
            "génération refusée, la fiche ou les données ne sont pas prêtes :\n"
            + "\n".join(f"- {b}" for b in blockers)
        )
        raise GenerationError(message)

    missing_facts = _check_facts_present(sheet)
    if missing_facts:
        message = (
            "génération refusée, fait(s) de l'étape 2 manquant(s) :\n"
            + "\n".join(f"- {t}" for t in missing_facts)
        )
        raise GenerationError(message)

    params = build_params(data)
    current_params_sha = hashlib.sha256(_params_json_bytes(params)).hexdigest()

    run_report_path = med_path.parent / RUN_REPORT_NAME
    if not run_report_path.is_file():
        message = f"aucun rapport de mesh run à côté du maillage : {run_report_path}"
        raise GenerationError(message)
    run_report = MeshRunReport.model_validate_json(
        run_report_path.read_text(encoding="utf-8")
    )
    if run_report.params_sha256 != current_params_sha:
        message = (
            "génération refusée : le rapport de maillage ne porte pas sur les mêmes "
            f"empreintes de paramètres (maillage : {run_report.params_sha256}, "
            f"données actuelles : {current_params_sha})"
        )
        raise GenerationError(message)

    verified = find_verified_mesh(
        project_root / work_dir_root,
        script_sha256=run_report.script_sha256,
        params_sha256=run_report.params_sha256,
    )
    if verified is None or Path(verified.med_path).resolve() != med_path.resolve():
        message = (
            "génération refusée : ce maillage n'est pas confirmé vérifié par mesh "
            "check pour son empreinte script/paramètres (cache de maillage)"
        )
        raise GenerationError(message)

    mv = ModelValues(data)

    beam_points = _tube_beam_points(params)
    beam_group_names = list(beam_points)
    beam_group_full_names = {
        f"{comm.BEAM_NODE_PREFIX}{n}": p for n, p in beam_points.items()
    }
    normal_ref = _normal_reference_point(params)

    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    spring_classes = build_spring_classes(params, k_h)
    check_spring_sum(
        spring_classes,
        band="RESS_AV_ARGI",
        k_h=k_h["RESS_AV_ARGI"],
        projected_width_m=20.80,
        projected_height_m=6.00,
    )
    check_spring_sum(
        spring_classes,
        band="RESS_AV_MARNE",
        k_h=k_h["RESS_AV_MARNE"],
        projected_width_m=11.36,
        projected_height_m=8.00,
    )
    spring_group_names = [c.group_name for c in spring_classes]

    g_profile = _ascending_component(
        mv, "eau_terres.profil_poussee_terres_permanent", "G"
    )
    q1_profile = _ascending_component(
        mv, "eau_terres.profil_poussee_terres_permanent", "Q1"
    )
    eau_p_points = mv.profile_si("eau_terres.profil_pression_eau_permanent")
    eau_a_points = mv.profile_si("eau_terres.profil_pression_eau_accidentel")
    eau_p_profile = [(z, p) for z, p, _, _ in sorted(eau_p_points)]
    eau_a_profile = [(z, p) for z, p, _, _ in sorted(eau_a_points)]

    g_accel = mv.si("charges.acceleration_pesanteur")

    amarrage_fy = -mv.si("charges.amarrage_composante_horizontale")
    amarrage_effort = mv.si("charges.amarrage_effort")
    amarrage_incl = mv.si("charges.amarrage_inclinaison")
    amarrage_fz = amarrage_effort * math.sin(amarrage_incl)
    amarrage_mx = mv.si("charges.amarrage_moment_transport")

    accostage_effort = mv.si("charges.accostage_effort")
    defense_area = expected_masses(params)["DEFENSE"]["mass"]
    accostage_fy = accostage_effort / defense_area

    text_parts = [
        comm.header(
            aster_version=aster_version,
            fiche_sha256=sha256_file(fiche_path),
            data_sha256=sha256_file(data_path),
            med_sha256=sha256_file(med_path),
        ),
        comm.mesh_prep_block(
            beam_points=beam_group_full_names,
            normal_ref_point=normal_ref,
            spring_classes=spring_classes,
            spring_bands={
                band: (b["cote_bas"], b["cote_haut"])
                for band, b in params["bandes"].items()
            },
            edge_tube_low=min(beam_group_names),
            edge_tube_high=max(beam_group_names),
        ),
        comm.model_and_cara_block(mv, spring_classes),
        comm.materials_block(mv),
        comm.liaison_solide_block(beam_group_names),
        comm.symmetry_and_support_block(),
        comm.formule_block("F_G", g_profile),
        comm.formule_block("F_Q1", q1_profile),
        comm.formule_block("F_EAU_P", eau_p_profile),
        comm.formule_block("F_EAU_A", eau_a_profile),
        comm.pressure_load_block("CH_G_POUSSEE", "F_G"),
        comm.pesanteur_block("CH_G_POIDS", g_accel),
        comm.pressure_load_block("CH_Q1", "F_Q1"),
        comm.pressure_load_block("CH_EAU_P", "F_EAU_P"),
        comm.pressure_load_block("CH_EAU_A", "F_EAU_A"),
        comm.bollard_force_block(
            "CH_Q3", fy=amarrage_fy, fz=amarrage_fz, mx=amarrage_mx
        ),
        comm.defense_force_block("CH_A", fy=accostage_fy),
        comm.case_block("G", extra_charges=["CH_G_POUSSEE", "CH_G_POIDS"]),
        comm.controls_block("G", spring_group_names),
        comm.order_of_magnitude_block("G", beam_group_names),
        comm.case_block("EAU_P", extra_charges=["CH_EAU_P"]),
        comm.controls_block("EAU_P", spring_group_names),
        comm.case_block("EAU_A", extra_charges=["CH_EAU_A"]),
        comm.controls_block("EAU_A", spring_group_names),
        comm.case_block("Q1", extra_charges=["CH_Q1"]),
        comm.controls_block("Q1", spring_group_names),
        comm.case_block("Q3", extra_charges=["CH_Q3"]),
        comm.controls_block("Q3", spring_group_names, reaction_components=("DY", "DZ")),
        comm.order_of_magnitude_block("Q3", beam_group_names),
        comm.case_block("A", extra_charges=["CH_A"]),
        comm.controls_block("A", spring_group_names),
        comm.footer(["G", "EAU_P", "EAU_A", "Q1", "Q3", "A"]),
    ]
    text = "".join(text_parts)

    report = GenerationReport(
        comm_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        fiche_sha256=sha256_file(fiche_path),
        data_sha256=sha256_file(data_path),
        med_sha256=sha256_file(med_path),
        aster_version=aster_version,
        n_spring_classes=len(spring_classes),
        spring_sums_mn_per_m={
            band: sum(
                c.stiffness_mn_per_m * len(c.nodes)
                for c in spring_classes
                if c.band == band
            )
            for band in k_h
        },
        load_case_resultants_n={
            "Q3": (0.0, amarrage_fy, amarrage_fz),
            "A": (0.0, accostage_fy * defense_area, 0.0),
        },
    )
    return text, report


__all__ = ["GenerationReport", "generate_comm"]
