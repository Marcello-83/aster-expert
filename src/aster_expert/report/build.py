"""Construction de la synthèse d'un calcul de quai à partir de son `.mess` (lot 35).

Lit les tables imprimées par le `.comm` généré (`aster_expert.generation.comm`,
`synthesis_block`, `controls_block`), calcule les grandeurs (`quantities`) et les
range dans un modèle sérialisable (`Synthesis`), que `render` met en forme.

Depuis le lot 36, la source est le MED de résultats (`med_path`), relu par
`medcoupling` dans le conteneur (`aster_expert.report.med_source`) ; les tables du
`.mess` ne sont plus qu'une contre-vérification (`Provenance.cross_check_max`). Sans
`med_path`, chaque grandeur vient d'une table imprimée du `.mess` (lot 35), traçable
à une commande du `.comm`. La synthèse dit laquelle des deux sources l'a produite
(`Provenance.source`).
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.model_data import ModelData, load_model_data
from aster_expert.generation import comm
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.combiwall import build_params, spring_node_areas
from aster_expert.report import quantities as q
from aster_expert.report.med_source import (
    MedData,
    cross_check,
    load_med_data,
    med_tables,
)
from aster_expert.report.tables import Record, read_tables

CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")
"""Cas élémentaires, dans l'ordre du `.comm` (aucune combinaison décidée)."""

BAND_LAYER = {"RESS_AV_ARGI": "argile marneuse", "RESS_AV_MARNE": "marne compacte"}
"""Couche de sol de chaque bande de ressorts (données, `sol.*`)."""

GROUP_LABELS = {
    "ANCRAGES": "ANCR",
    "PIED_TUBES": "PIED",
    "SYM_G": "SYMG",
    "SYM_D": "SYMD",
}
"""Groupe d'appui -> code court de `quantities.BLOCKED_COMPONENTS`."""


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Provenance(_Model):
    mess_path: str | None
    mess_sha256: str | None
    comm_sha256: str | None
    data_path: str
    aster_version: str | None
    med_read: bool
    """`True` : les grandeurs viennent du MED de résultats ; `False` : du `.mess`."""
    source: str = "mess"
    """`med` ou `mess` : la source des grandeurs de la synthèse."""
    med_path: str | None = None
    med_sha256: str | None = None
    cross_check_max: float | None = None
    """Écart relatif maximal, toutes tables, entre le MED et les tables du `.mess`
    (`med_source.cross_check`), quand les deux sont fournis."""
    cross_check: dict[str, float] | None = None


class TubeProfile(_Model):
    tube: int
    label: str
    by_case: dict[str, list[q.ProfilePoint]]


class CaseSummary(_Model):
    case: str
    head: q.HeadDisplacement
    ties: list[q.TieForce]
    tubes: list[q.ExtremaPair]
    palps: list[q.ExtremaPair]
    beam: list[q.ExtremaPair] | None
    reactions: list[q.GroupReaction]
    springs: q.SpringChecks
    tie_anchor: q.TieAnchorCheck


class Synthesis(_Model):
    project: str
    provenance: Provenance
    axes_x: list[float]
    radius: float
    palp_local_x: list[float]
    beam_orientation_checked: bool | None
    profiles: list[TubeProfile]
    cases: list[CaseSummary]
    level_d: dict[str, Any] | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _butee_pa(data: ModelData) -> dict[str, list[tuple[float, float]]]:
    """Profil de butée limite de chaque bande de ressorts, en pascals, du haut vers le
    bas de la couche (la cote décroît)."""
    item = data.items().get("sol.profil_butee_limite")
    if item is None or item.status != "fourni" or item.profile is None:
        message = "donnée `sol.profil_butee_limite` absente ou à fournir"
        raise ValueError(message)
    if item.unit != "kPa":
        message = f"sol.profil_butee_limite : unité {item.unit!r} au lieu de kPa"
        raise ValueError(message)
    out: dict[str, list[tuple[float, float]]] = {}
    for band, layer in BAND_LAYER.items():
        points = [(p.z, p.p * 1.0e3) for p in item.profile if p.layer == layer]
        if len(points) < 2:
            message = (
                f"butée : la couche {layer!r} de {band} porte {len(points)} point(s)"
            )
            raise ValueError(message)
        out[band] = sorted(points, key=lambda pt: -pt[0])
    return out


def _table_names(cases: tuple[str, ...], profile_tubes: tuple[int, ...]) -> list[str]:
    names: list[str] = []
    for case in cases:
        names += [
            f"RESSORTS_{case}",
            comm.synthesis_title("tete", case),
            comm.synthesis_title("tubes", case),
            comm.synthesis_title("palplanches", case),
            comm.synthesis_title("tirants", case),
        ]
        names += [comm.profile_title(t, case) for t in profile_tubes]
        names += [comm.reaction_table_title(g, case) for g in GROUP_LABELS]
        names.append(comm.synthesis_title("poutre", case))
    return names


def _beam_orientation_ok(rows: list[Record]) -> bool:
    """Chaque élément de poutre est listé de son premier nœud (X le plus bas) vers le
    second : `x_l = +X`, donc `y_l = +Y` et `z_l = +Z` (repère par défaut de
    `AFFE_CARA_ELEM/ORIENTATION`, U4.42.01). Déduit de l'ordre des lignes de la table
    `EFGE_ELNO` (premier puis second nœud de l'élément) : un fait de lecture, pas un
    fait de la documentation."""
    by_element: dict[str, list[float]] = {}
    for row in rows:
        by_element.setdefault(str(row["MAILLE"]), []).append(float(row["COOR_X"]))
    return all(len(xs) == 2 and xs[0] < xs[1] for xs in by_element.values())


def build_synthesis(
    mess_path: Path | None,
    data_path: Path,
    *,
    comm_path: Path | None = None,
    level_d_path: Path | None = None,
    cases: tuple[str, ...] = CASES,
    med_path: Path | None = None,
    med_data: MedData | None = None,
) -> Synthesis:
    """Lit `mess_path` (le `.mess` d'une exécution du `.comm` généré) et range les
    grandeurs de chaque cas élémentaire. Une table attendue et absente est une
    erreur : `Synthesis` n'est jamais partiel en silence."""
    data = load_model_data(data_path)
    mv = ModelValues(data)
    params = build_params(data)
    axes = [float(x) for x in params["tube"]["axes_x"]]
    radius = float(params["tube"]["rayon"])
    central = int(params["tube"]["central"])
    profile_tubes = tuple(dict.fromkeys((central, 1)))

    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    nodes = q.spring_nodes(spring_node_areas(params), k_h, _butee_pa(data))

    names = _table_names(cases, profile_tubes)
    mess_tables = (
        read_tables(mess_path, names)
        if mess_path is not None and mess_path.is_file()
        else None
    )
    cross: dict[str, float] | None = None
    if med_path is not None or med_data is not None:
        loaded = med_data or load_med_data(med_path, cases)  # type: ignore[arg-type]
        tables = med_tables(loaded, names, profile_tubes=profile_tubes)
        if mess_tables is not None:
            cross = cross_check(tables, mess_tables)
    elif mess_tables is not None:
        tables = mess_tables
    else:
        message = "ni MED de résultats ni listing .mess lisible : aucune source"
        raise ValueError(message)
    used_med = med_path is not None or med_data is not None
    med_file = med_path or (med_data.path if med_data else None)

    profiles = [
        TubeProfile(
            tube=t,
            label=f"TUBE_{t:02d}",
            by_case={
                case: q.dy_profile(tables[comm.profile_title(t, case)])
                for case in cases
            },
        )
        for t in profile_tubes
    ]
    summaries: list[CaseSummary] = []
    beam_ok: bool | None = None
    tie = params["tirants"]
    run_y, drop_z = tie["fin_y"] - tie["debut_y"], tie["fin_z"] - tie["debut_z"]
    length = math.hypot(run_y, drop_z)
    direction = (run_y / length, drop_z / length)
    for case in cases:
        beam_rows = tables[comm.synthesis_title("poutre", case)]
        if beam_ok is None and beam_rows:
            beam_ok = _beam_orientation_ok(beam_rows)
        ties = q.tie_forces(tables[comm.synthesis_title("tirants", case)], axes)
        reactions = [
            q.group_reaction(
                group, code, tables[comm.reaction_table_title(group, case)][0]
            )
            for group, code in GROUP_LABELS.items()
        ]
        summaries.append(
            CaseSummary(
                case=case,
                head=q.head_displacement(
                    tables[comm.synthesis_title("tete", case)], axes, radius
                ),
                ties=ties,
                tubes=q.extrema(
                    tables[comm.synthesis_title("tubes", case)],
                    comm.TUBE_EFFORT_COMPONENTS,
                    axes,
                    radius,
                ),
                palps=q.extrema(
                    tables[comm.synthesis_title("palplanches", case)],
                    comm.PALP_EFFORT_COMPONENTS,
                    axes,
                    radius,
                ),
                beam=q.extrema(beam_rows, comm.BEAM_EFFORT_COMPONENTS, axes, radius)
                if beam_rows
                else None,
                reactions=reactions,
                springs=q.spring_checks(
                    tables[f"RESSORTS_{case}"], nodes, axes, radius
                ),
                tie_anchor=q.tie_anchor_check(
                    ties, reactions[0], direction, gravity=case == "G"
                ),
            )
        )
    vector = mv.si_vector("palplanche.vecteur_axe_L")
    return Synthesis(
        project=data.project,
        provenance=Provenance(
            mess_path=str(mess_path) if mess_path else None,
            mess_sha256=_sha256(mess_path)
            if mess_path is not None and mess_path.is_file()
            else None,
            comm_sha256=_sha256(comm_path) if comm_path else None,
            data_path=str(data_path),
            aster_version=None,
            med_read=used_med,
            source="med" if used_med else "mess",
            med_path=str(med_file) if med_file else None,
            med_sha256=_sha256(med_file) if med_file else None,
            cross_check_max=max(cross.values()) if cross else None,
            cross_check=cross,
        ),
        axes_x=axes,
        radius=radius,
        palp_local_x=[float(v) for v in vector],
        beam_orientation_checked=beam_ok,
        profiles=profiles,
        cases=summaries,
        level_d=json.loads(level_d_path.read_text(encoding="utf-8"))
        if level_d_path
        else None,
    )
