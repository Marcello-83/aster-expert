"""Extensions du projet QUAI-CW-TEST-01, nommées par `projet.yaml` (lot 41).

Le tronc commun (`aster_expert.projet`, `aster_expert.controles`,
`aster_expert.combinaisons`, `aster_expert.ferraillage`) appelle ces fonctions
pour ce que seul ce projet sait faire : écrire les paramètres de son script
Salomé, générer son `.comm`, intégrer ses charges, calculer les forces de ses
ressorts, rédiger la prose de ses rapports. Chacune délègue au code déplacé de
`src/` dans ce paquet, sans en changer le comportement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext
from quai_cw_test_01.controles import (
    integrated_loads,
    spring_by_band,
    spring_stiffness_check,
)
from quai_cw_test_01.generation.generate import _params_json_bytes, generate_comm
from quai_cw_test_01.generation.springs import (
    COMBINED_BAND,
    SpringClass,
    build_spring_classes,
)
from quai_cw_test_01.meshing.combiwall import build_params, expected_masses

MESH_RUNS = "data/processed/mesh_runs"
"""Racine des maillages de `mesh run` (cache de maillage vérifié), relative au
dépôt."""


def _params(ctx: ProjectContext) -> dict[str, Any]:
    if "params" not in ctx.cache:
        ctx.cache["params"] = build_params(ctx.data())
    params: dict[str, Any] = ctx.cache["params"]
    return params


def mesh_parameters(ctx: ProjectContext) -> bytes:
    """Fichier de paramètres du script Salomé, octet pour octet celui dont
    `mesh run` a enregistré l'empreinte (`build_lot27_maillage.py`)."""
    return _params_json_bytes(_params(ctx))


def generate(
    ctx: ProjectContext,
    *,
    fiche_path: Path,
    data_path: Path,
    med_path: Path,
    aster_version: str,
) -> tuple[str, dict[str, Any]]:
    """Le `.comm` de production (générateur des lots 28 à 37, sans option de
    diagnostic)."""
    text, report = generate_comm(
        fiche_path=fiche_path,
        data_path=data_path,
        med_path=med_path,
        project_root=ctx.repo_root,
        work_dir_root=MESH_RUNS,
        aster_version=aster_version,
        waived_revisions=ctx.waived_revisions("generer"),
    )
    return text, json.loads(report.model_dump_json())


def integrated_resultant(
    ctx: ProjectContext,
    case: str,
    *,
    comm_path: Path,
    mesh_path: Path,
    out_dir: Path,
) -> dict[str, dict[str, float]]:
    """Charge d'un cas de pression (G, Q1, EAU_P, EAU_A), intégrée indépendamment
    sur les mailles du maillage (`integrated_loads`) ; le détail est écrit dans
    `integrale.json`, une fois pour tous les cas."""
    if "integrale" not in ctx.cache:
        declaration = ctx.declaration
        result = integrated_loads(
            mess_text=None,
            comm_text=comm_path.read_text(encoding="utf-8"),
            data_path=ctx.data_path,
            mesh_path=mesh_path,
            invariants_path=ctx.path(declaration.mesh.invariants),
            repo_root=ctx.repo_root,
        )
        (out_dir / "integrale.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        ctx.cache["integrale"] = result
    cases = ctx.cache["integrale"]["cases"]
    return {
        "as_evaluated": cases[case]["as_evaluated"]["integrated_n"],
        "specified": cases[case]["integrated_n"],
    }


def comm_resultant(
    ctx: ProjectContext,
    case: str,
    *,
    comm_path: Path,
    mesh_path: Path,  # noqa: ARG001 - signature commune des extensions de résultante
    out_dir: Path,  # noqa: ARG001
) -> dict[str, dict[str, float]]:
    """Q3 (amarrage) et A (accostage) : charges ponctuelles lues du `.comm`
    (bollard ; défense, intensité × aire de l'empreinte), comme au lot 34."""
    comm_text = comm_path.read_text(encoding="utf-8")
    if case == "Q3":
        bollard = re.search(
            r"GROUP_NO=\(\"BOLLARD\",\), FY=([-\d.eE+]+), FZ=([-\d.eE+]+)", comm_text
        )
        if bollard is None:
            message = "charge du bollard absente du .comm"
            raise ValueError(message)
        values = {"DX": 0.0, "DY": float(bollard[1]), "DZ": float(bollard[2])}
    elif case == "A":
        defense = re.search(r"GROUP_MA=\(\"DEFENSE\",\), FY=([-\d.eE+]+)\)", comm_text)
        if defense is None:
            message = "charge de défense absente du .comm"
            raise ValueError(message)
        area = expected_masses(_params(ctx))["DEFENSE"]["mass"]
        values = {"DX": 0.0, "DY": float(defense[1]) * area, "DZ": 0.0}
    else:
        message = f"cas {case} : pas de charge ponctuelle écrite dans le .comm"
        raise ValueError(message)
    return {"as_evaluated": values, "specified": values}


def _spring_classes(ctx: ProjectContext) -> list[SpringClass]:
    if "springs" not in ctx.cache:
        items = ctx.data().items()
        k_h = {
            "RESS_AV_ARGI": float(items["sol.k_h_argile_marneuse_raide"].value),  # type: ignore[arg-type]
            "RESS_AV_MARNE": float(items["sol.k_h_marne_compacte"].value),  # type: ignore[arg-type]
        }
        ctx.cache["springs"] = build_spring_classes(_params(ctx), k_h)
    classes: list[SpringClass] = ctx.cache["springs"]
    return classes


def spring_forces(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions de ressorts
) -> dict[str, float]:
    """Σ k·DY par bande (argile, marne), les classes communes aux deux bandes
    exclues (leurs nœuds sont comptés dans chacune de leurs bandes)."""
    classes = [c for c in _spring_classes(ctx) if c.band != COMBINED_BAND]
    return spring_by_band(mess_text, case, classes)


def spring_stiffness(ctx: ProjectContext, comm_text: str) -> dict[str, Any]:
    """Chaque nœud à ressort porte une seule raideur, et la somme écrite dans le
    `.comm` égale la somme lue des bandes."""
    return spring_stiffness_check(comm_text, _spring_classes(ctx))


def synthesis(
    ctx: ProjectContext,  # noqa: ARG001 - signature commune des extensions de synthèse
    *,
    result: Path,
    out_dir: Path,
    data_path: Path,
    comm_path: Path | None = None,
    level_d_path: Path | None = None,
    med_path: Path | None = None,
    label: str = "",
    views: bool = True,
) -> list[str]:
    """Synthèse d'un calcul du quai (lots 35 à 37) : `synthese.md`, `controles.md`,
    `synthese.json` et les vues PNG. Reprise telle quelle de l'ancienne commande
    `aster-expert report` du tronc commun ; rend les lignes à afficher."""
    from quai_cw_test_01.report.build import CASES, build_synthesis  # noqa: PLC0415
    from quai_cw_test_01.report.med_source import load_med_data  # noqa: PLC0415
    from quai_cw_test_01.report.render import (  # noqa: PLC0415
        matplotlib_available,
        plot_profiles,
        render_controls,
        render_synthesis,
    )

    run_dir = result if result.is_dir() else result.parent
    mess = result / "proc.0" / "fort.6" if result.is_dir() else result
    med = med_path if med_path is not None else run_dir / "proc.0" / "fort.80"
    has_med = med.is_file()
    if not mess.is_file() and not has_med:
        message = f"ni listing ({mess}) ni MED de résultats ({med})"
        raise ValueError(message)
    out_dir.mkdir(parents=True, exist_ok=True)
    med_data = load_med_data(med, CASES) if has_med else None
    synth = build_synthesis(
        mess if mess.is_file() else None,
        data_path,
        comm_path=comm_path,
        level_d_path=level_d_path,
        med_data=med_data,
    )
    view_files = []
    if med_data is not None and views and matplotlib_available():
        from quai_cw_test_01.report.figures import (  # noqa: PLC0415
            build_context,
            make_figures,
        )

        view_files = make_figures(
            med_data, build_context(data_path, label=label), out_dir / "vues"
        )
    figures = plot_profiles(synth, out_dir) if not view_files else []
    (out_dir / "synthese.md").write_text(
        render_synthesis(synth, figures, view_files, out_dir), encoding="utf-8"
    )
    (out_dir / "controles.md").write_text(render_controls(synth), encoding="utf-8")
    (out_dir / "synthese.json").write_text(
        synth.model_dump_json(indent=2), encoding="utf-8"
    )
    lines = [
        f"Synthèse : {out_dir / 'synthese.md'}",
        f"Contrôles : {out_dir / 'controles.md'}",
        f"Source : {synth.provenance.source}"
        + (
            f" (écart MED/.mess {synth.provenance.cross_check_max:.2e})"
            if synth.provenance.cross_check_max is not None
            else ""
        ),
    ]
    if view_files:
        lines.append(f"Vues : {len(view_files)} PNG dans {out_dir / 'vues'}")
    elif not figures:
        lines.append(
            "Figures : aucune (matplotlib absent de l'environnement du projet, ou "
            "vues désactivées) ; profils en tableaux seuls."
        )
    return lines


__all__ = [
    "comm_resultant",
    "generate",
    "integrated_resultant",
    "mesh_parameters",
    "spring_forces",
    "spring_stiffness",
    "synthesis",
]
