# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 51 bis for PONTONS-ALU-01 (consigne § 2 and § 3), one folder per
variant, read from the tables Code_Aster printed during the run (never recomputed by a
model of the tool): unit 31 (EFGE_ELNO of every bar), 32 (DEPL of every node), 33
(REAC_NODA of the quay hinges, of the ears of the pin bearings and of the cap beam nodes
under them), and the mesh read by `medcoupling` (trunk `dump_med`).

Formats of lot 51 (`exports_lot51`: `;`, decimal point, UTF-8 without BOM, SI, one `#`
line on top, 17 significant digits), without `appuis_neoprene.csv`; in its place
`appuis_axes.csv` (forces of each pin on its cap beam or support, P44), and
`palee_equilibre.csv` (sum of the soil reactions under the footing, springs in tension,
tension of the piles, missing ballast, P49).

Force of a pin on the cap beam (choice A9): REAC_NODA of the cap beam node under it,
which only the relations of the pin act on; at X = 14,02, the opposite of REAC_NODA of
the ear (force of the support on the deck). Fz is counted positive downwards, so that
Fz > 0 is a compression and Fz < 0 a tension of the anchors (uplift).
"""

from __future__ import annotations

import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51 import (
    Branch,
    Event,
    counts,
    enumerate_branch,
    envelope,
    event_rows,
    governing,
    magnitudes,
    resultant_max,
    rule_rows,
)
from pontons_alu_01.combinaisons_lot51bis import branches, events
from pontons_alu_01.exports_lot51 import (
    DEPL,
    EFGE,
    FAMILY_AXIS,
    REAC,
    STATES_COMPARED,
    Element,
    Member,
    Model,
    _float,
    _members,
    geo,
    mesh_dump,
    number,
    parse_tableau,
    section_rows,
    sha256,
    write,
)
from pontons_alu_01.extensions_lot51 import tributary_areas
from pontons_alu_01.generation_lot51bis import (
    Values51bis,
    all_cases,
    case_label,
    concrete_volumes,
    mechanical_cases,
    values,
)
from pontons_alu_01.geometrie_lot51bis import Geometry51bis, geometry
from pontons_alu_01.lot50ter import first_of, local_axes, names, occurrences, read_comm
from pontons_alu_01.variantes_lot51bis import Variant51bis, variants

FloatArray = NDArray[np.float64]
PILES = ("C1_YM", "C1_YP", "C2_YM", "C2_YP")
STATES = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
)
TANGENTIAL = ("ACX_", "ACZ_")
"""Unit cases of the tangential berthing component, left out of the characteristic
SLS deflection (P51)."""
LOT = "lot51bis"


# --------------------------------------------------------------------------- tables


@dataclass
class RunTables:
    efge: dict[str, dict[tuple[int, int], FloatArray]]
    depl: dict[str, dict[int, FloatArray]]
    reac: dict[str, dict[int, FloatArray]]
    order_to_case: dict[int, str]


def read_run(run_dir: Path, g: Geometry51bis) -> RunTables:
    from aster_expert.controles.tables import TableIndex  # noqa: PLC0415

    proc = run_dir / "proc.0"
    mess = TableIndex((proc / "fort.6").read_text(encoding="utf-8", errors="replace"))
    mechanical = mechanical_cases(g)
    order_to_case: dict[int, str] = {}
    for case in mechanical:
        (row,) = mess.find(f"RP_{case}")
        head = str(row["_head"]).split()
        order_to_case[int(head[-2])] = head[-1]
    if [order_to_case[k] for k in sorted(order_to_case)] != mechanical:
        message = "NUME_ORDRE de MACRO_ELAS_MULT : ordre des cas inattendu"
        raise ValueError(message)

    def case_of(cells: dict[str, str]) -> str:
        result = cells[next(iter(cells))]
        if result == "ELEM":
            return order_to_case[int(cells["NUME_ORDRE"])]
        return result

    efge: dict[str, dict[tuple[int, int], FloatArray]] = {}
    for _, rows in parse_tableau((proc / "fort.31").read_text(encoding="utf-8")):
        for cells in rows:
            key = (int(cells["MAILLE"]), int(cells["NOEUD"]))
            efge.setdefault(case_of(cells), {})[key] = np.array(
                [_float(cells[c]) for c in EFGE]
            )
    depl: dict[str, dict[int, FloatArray]] = {}
    for _, rows in parse_tableau((proc / "fort.32").read_text(encoding="utf-8")):
        for cells in rows:
            depl.setdefault(case_of(cells), {})[int(cells["NOEUD"])] = np.array(
                [_float(cells.get(c, "")) for c in DEPL]
            )
    reac: dict[str, dict[int, FloatArray]] = {}
    for _, rows in parse_tableau((proc / "fort.33").read_text(encoding="utf-8")):
        for cells in rows:
            reac.setdefault(case_of(cells), {})[int(cells["NOEUD"])] = np.array(
                [_float(cells.get(c, "")) for c in REAC]
            )
    return RunTables(efge, depl, reac, order_to_case)


# --------------------------------------------------------------------------- model


def section_label(family: str, v: Variant51bis) -> str:
    return {
        "POUTRES_PRINC": f"tube {v.beam_side_mm:g}x{v.beam_side_mm:g}x{v.beam_thickness_mm:g}",
        "MONTANTS": "tube 150x150x7",
        "DIAGONALES": "tube 150x150x7",
        "PANNES_SEC": "tube 50x50x5",
        "CHEVETRES": f"BA 0.40x{v.ring_height:.2f}",
        "LONGRINES": f"BA 0.40x{v.ring_height:.2f}",
        "PILES": "pile D0.50",
    }[family]


def build_model(
    dump: dict[str, Any], tables: RunTables, g: Geometry51bis, v: Variant51bis
) -> Model:
    coords = np.array(dump["coords"], dtype=np.float64)
    seg = dump["levels"]["-1"]
    seg_conn = [tuple(int(n) for n in c) for c in seg["connectivity"]]
    node_groups: dict[int, list[str]] = {n + 1: [] for n in range(len(coords))}
    cell_groups: dict[str, set[int]] = {}
    group_nodes: dict[str, list[int]] = {}
    for grp in dump["groups"]:
        if grp["level"] == 1:
            ids = [int(i) + 1 for i in grp["ids"]]
        elif grp["level"] == -1:
            cell_groups[grp["name"]] = {int(i) + 1 for i in grp["ids"]}
            ids = sorted({n + 1 for i in grp["ids"] for n in seg_conn[int(i)]})
        else:
            level = dump["levels"][str(grp["level"])]["connectivity"]
            ids = sorted({n + 1 for i in grp["ids"] for n in level[int(i)]})
        group_nodes[grp["name"]] = ids
        for n in ids:
            node_groups[n].append(grp["name"])
    for n in node_groups:
        node_groups[n] = sorted(set(node_groups[n]))
    member_names = {m.name: m.family for m in g.members}
    group_of: dict[int, str] = {}
    for name in member_names:
        for c in cell_groups[name]:
            group_of[c] = name
    first_case = next(iter(tables.efge.values()))
    ends: dict[int, list[int]] = {}
    for cell, node in first_case:
        ends.setdefault(cell, []).append(node)
    elements: dict[int, Element] = {}
    for number_, (n1, n2) in enumerate(seg_conn, start=1):
        if number_ not in group_of:
            continue  # SEG2 des bords et des coupes de la semelle (sans élément de barre)
        family = member_names[group_of[number_]]
        if sorted(ends.get(number_, [])) != sorted((n1 + 1, n2 + 1)):
            message = f"maille {number_} : nœuds de la table ≠ nœuds du MED"
            raise ValueError(message)
        cara, vec = (
            ("VECT_Y", (1.0, 0.0, 0.0))
            if family == "PILES"
            else ("VECT_Z", (0.0, 0.0, 1.0))
        )
        _, y, z = local_axes(coords[n1], coords[n2], cara, vec)
        elements[number_] = Element(
            number=number_,
            family=family,
            group=group_of[number_],
            nodes=(n1 + 1, n2 + 1),
            y_local=y,
            z_local=z,
            length=float(np.linalg.norm(coords[n2] - coords[n1])),
            section=section_label(family, v),
        )
    joints: dict[int, list[str]] = {}
    for lk in g.links:
        for side in ("A", "B"):
            (n,) = group_nodes[f"{lk.name}_{side}"]
            joints.setdefault(n, []).append(lk.name)
    for a in g.axes:
        for k in range(1, len(a.ears) + 1):
            (n,) = group_nodes[a.ear_group(k)]
            joints.setdefault(n, []).append(f"AXE_{a.name}")
        if a.cap is not None:
            (n,) = group_nodes[a.cap_group]
            joints.setdefault(n, []).append(f"AXE_{a.name}")
    for name in ("APP_QUAI_YM", "APP_QUAI_YP"):
        for n in group_nodes[name]:
            joints.setdefault(n, []).append(name)
    members = _members(coords, elements, joints)
    return Model(coords, node_groups, group_nodes, elements, {}, members, joints)


# --------------------------------------------------------------------------- variant


@dataclass
class VariantData51bis:
    variant: Variant51bis
    model: Model
    tables: RunTables
    g: Geometry51bis
    cases: list[str]
    ev: dict[str, Event]
    bs: list[Branch]
    comm: Path
    vals: Values51bis


def load_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any]
) -> VariantData51bis:
    v = variants()[code]
    g = geometry(v.mesh_overrides)
    run_dir = Path(state[code]["execution"]["execution_dir"])
    tables = read_run(run_dir, g)
    dump = mesh_dump(ctx, Path(state[code]["maillage"]["med"]))
    model = build_model(dump, tables, g, v)
    data = {key: item.value for key, item in ctx.data().items().items()}
    ev = events(magnitudes(data))
    comm = Path(state[code]["comm"])
    return VariantData51bis(
        v, model, tables, g, all_cases(g), ev, branches(ev), comm, values(ctx, v)
    )


# --------------------------------------------------------------------------- pins


@dataclass
class PinResult:
    force: FloatArray
    """Force of the pin on the cap beam (or the fixed support), global axes."""
    slide_x: float
    """X of the pin point carried by the first ear minus X carried by the cap node."""
    rotations: tuple[float, float, float]
    """DRY ear 1 − DRY cap, DRY ear 2 − DRY cap, DRY ear 2 − DRY ear 1 (nan if absent)."""


def _pin_translation(depl: FloatArray, node: FloatArray, pin: FloatArray) -> FloatArray:
    return np.asarray(depl[:3] + np.cross(depl[3:6], pin - node), dtype=np.float64)


def pin_results(vd: VariantData51bis, case: str) -> dict[str, PinResult]:
    m = vd.model
    reac = vd.tables.reac[case]
    depl = vd.tables.depl[case]
    out: dict[str, PinResult] = {}
    for a in vd.g.axes:
        ears = [m.group_nodes[a.ear_group(k)][0] for k in range(1, len(a.ears) + 1)]
        pin = np.array(a.pin)
        p1 = _pin_translation(depl[ears[0]], m.coords[ears[0] - 1], pin)
        if a.cap is not None:
            (cap,) = m.group_nodes[a.cap_group]
            force = np.array(reac[cap][:3])
            pk = _pin_translation(depl[cap], m.coords[cap - 1], pin)
            slide = float(p1[0] - pk[0])
            ry_ref = float(depl[cap][4])
        else:
            force = -np.array(reac[ears[0]][:3])
            slide = float(p1[0])
            ry_ref = 0.0
        r1 = float(depl[ears[0]][4]) - ry_ref
        r2 = float(depl[ears[1]][4]) - ry_ref if len(ears) == 2 else math.nan
        r12 = float(depl[ears[1]][4] - depl[ears[0]][4]) if len(ears) == 2 else math.nan
        out[a.name] = PinResult(force, slide, (r1, r2, r12))
    return out


def pin_rows(vd: VariantData51bis) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for case in vd.cases:
        for name, r in pin_results(vd, case).items():
            a = vd.g.axis(name)
            rows.append(
                [
                    case,
                    a.bearing,
                    a.side,
                    "chevêtre" if a.cap is not None else "support fixe",
                    *(geo(c) for c in a.pin),
                    float(r.force[0]),
                    float(r.force[1]),
                    float(-r.force[2]),
                    float(r.slide_x),
                    *(float(x) for x in r.rotations),
                ]
            )
    return rows


# --------------------------------------------------------------------------- soil


def soil_areas(vd: VariantData51bis) -> tuple[list[int], FloatArray]:
    """Footing nodes and their tributary areas (RIGI_PARASOL, U4.42.01)."""
    m = vd.model
    nodes = m.group_nodes["SEMELLE"]
    areas = tributary_areas(vd.g)
    a = np.array(
        [
            areas[
                (
                    round(float(m.coords[n - 1][0]), 6),
                    round(float(m.coords[n - 1][1]), 6),
                )
            ]
            for n in nodes
        ]
    )
    return nodes, a


def soil_forces(vd: VariantData51bis) -> tuple[list[int], dict[str, FloatArray]]:
    """Footing nodes and, per case, the vertical force of the soil on the footing at
    each node (−k_n × tributary area × u_z, > 0 upwards, P19)."""
    nodes, a = soil_areas(vd)
    k = vd.vals.kn * a
    forces = {
        c: -k * np.array([vd.tables.depl[c][n][2] for n in nodes]) for c in vd.cases
    }
    return nodes, forces


def overlap_volume(vd: VariantData51bis) -> float:
    """Concrete counted twice at the corners of the ring: each tie runs from cap beam
    axis to cap beam axis (less 1 mm) and enters the b wide cap beams."""
    half = vd.vals.ring_b / 2.0
    caps = vd.g.parameters["X_PALEE"]
    inside = sum(
        max(0.0, half - min(abs(x - xc) for xc in caps))
        for m in vd.g.family("LONGRINES")
        for x in (m.points[0][0], m.points[-1][0])
    )
    return float(inside * vd.vals.ring_b * vd.vals.ring_h)


@dataclass
class Governed:
    value: float
    state: str
    combination: str
    coefficients: dict[str, float]
    where: str


def extreme_in_state(
    vd: VariantData51bis,
    f: dict[str, FloatArray],
    state: str,
    sign: float,
    where: list[str],
    *,
    without: tuple[str, ...] = (),
) -> Governed:
    ext = envelope(vd.bs, vd.ev, f, state, sign=sign, without=without)
    q = int(np.argmax(sign * ext.value))
    name, coefs = governing(vd.bs, vd.ev, ext, q)
    return Governed(float(ext.value[q]), state, name, coefs, where[q])


def equilibrium_rows(vd: VariantData51bis) -> tuple[list[list[Any]], dict[str, Any]]:
    nodes, forces = soil_forces(vd)
    total = {c: np.array([forces[c].sum()]) for c in vd.cases}
    rows: list[list[Any]] = []
    summary: dict[str, Any] = {}
    elu_min = math.inf
    for state in STATES:
        gov = extreme_in_state(vd, total, state, -1.0, ["semelle"])
        combo = sum(c * forces[k] for k, c in gov.coefficients.items() if k in forces)
        assert isinstance(combo, np.ndarray)
        tension = [n for n, fz in zip(nodes, combo, strict=True) if fz < 0.0]
        where = (
            f"tous les {len(nodes)} nœuds de la semelle"
            if len(tension) == len(nodes)
            else " | ".join(
                f"nœud {n} ({geo(vd.model.coords[n - 1][0])} ; {geo(vd.model.coords[n - 1][1])})"
                for n in tension
            )
        )
        rows.append(
            [
                state,
                "SRz_min",
                "semelle (Σ des forces du sol, > 0 vers le haut)",
                gov.value,
                "N",
                gov.combination,
                f"{len(tension)} ressorts en traction sur {len(nodes)}",
            ]
        )
        rows.append(
            [
                state,
                "ressorts_traction",
                "semelle, combinaison de SRz_min",
                float(len(tension)),
                "nombre",
                gov.combination,
                where or "aucun",
            ]
        )
        summary[state] = {
            "SRz_min_N": gov.value,
            "combinaison": gov.combination,
            "ressorts_traction": len(tension),
            "positions": where,
        }
        if state.startswith("ELU"):
            elu_min = min(elu_min, gov.value)
    for pile in PILES:
        (head,) = vd.model.group_nodes[f"TP_{pile}_A"]
        (foot,) = vd.model.group_nodes[f"PS_{pile}_A"]
        for position, node in (("tete", head), ("pied", foot)):
            (e,) = [
                el
                for el in vd.model.elements.values()
                if el.group == f"PILE_{pile}" and node in el.nodes
            ]
            f = {
                c: np.array([vd.tables.efge[c][(e.number, node)][0]]) for c in vd.cases
            }
            for state in STATES:
                gov = extreme_in_state(vd, f, state, 1.0, [f"{pile} {position}"])
                rows.append(
                    [
                        state,
                        "N_traction_max",
                        f"pile {pile}, {position} (élément {e.number}, nœud {node})",
                        gov.value,
                        "N",
                        gov.combination,
                        "traction"
                        if gov.value > 0.0
                        else "pas de traction (N max ≤ 0)",
                    ]
                )
    ballast = max(0.0, -elu_min) / 0.9
    overlap = overlap_volume(vd)
    net = (vd.vals.gamma_concrete - vd.vals.gamma_water) * overlap
    rows.append(
        [
            "ELU",
            "lest_manquant",
            "palée",
            ballast,
            "N",
            "",
            f"max(0 ; −ΣRz min ELU) / 0,9, ΣRz min ELU = {number(elu_min)} N (plus petit de "
            "l'ELU fondamental et de l'ELU accidentel)",
        ]
    )
    rows.append(
        [
            "",
            "recouvrement_angles",
            "anneau, angles comptés deux fois (longrines d'axe à axe des chevêtres)",
            net,
            "N",
            "",
            f"volume {number(overlap)} m3 ; poids déjaugé (25 − 10 kN/m3) compté en trop dans "
            "G1 et DEJ ; non retranché du lest manquant",
        ]
    )
    summary["lest_manquant_N"] = ballast
    summary["SRz_min_ELU_N"] = elu_min
    summary["recouvrement_m3"] = overlap
    summary["recouvrement_poids_deja_N"] = net
    return rows, summary


# --------------------------------------------------------------------------- exports


def source_line(vd: VariantData51bis, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, lot 51 bis, variante {vd.variant.code} ({vd.variant.description}) : "
        f"exécution {run}, .comm sha256 {sha256(vd.comm)}, maillage sha256 "
        f"{s['maillage']['med_sha256']}."
    )


AXES = (
    "Repère global : X le long du ponton depuis le quai (X = 0 rotules du quai, X = 6,25 et "
    "7,77 axes des chevêtres C1 et C2, X = 14,02 bout de la travée 2), Y transversal, Z "
    "vertical vers le haut (m NGF)."
)


def export_variant(
    vd: VariantData51bis, state: dict[str, Any], out: Path
) -> tuple[dict[str, int], dict[str, Any]]:
    out.mkdir(parents=True, exist_ok=True)
    src = source_line(vd, state)
    m = vd.model
    lv = vd.g.levels
    files: dict[str, int] = {}
    cases_text = "Cas : " + " ; ".join(f"{c} = {case_label(c)}" for c in vd.cases) + "."
    files["noeuds.csv"] = write(
        out / "noeuds.csv",
        f"{src} Unités : m. {AXES} noeud = numéro MED (à partir de 1) ; groupes du maillage qui le contiennent.",
        ["noeud", "x", "y", "z", "groupes"],
        [
            [n, *(geo(c) for c in m.coords[n - 1]), "|".join(m.node_groups[n])]
            for n in range(1, len(m.coords) + 1)
        ],
    )
    files["elements.csv"] = write(
        out / "elements.csv",
        f"{src} Unités : m. {AXES} element = numéro de la maille SEG2 (MED, à partir de 1). "
        "Repère local (U4.42.01) : x_l du nœud 1 au nœud 2 ; VECT_Z (0, 0, 1) pour les barres "
        "horizontales (z_l = projection de +Z, y_l = z_l ∧ x_l) ; VECT_Y (1, 0, 0) pour les "
        "piles (y_l = projection de +X). Liaisons : nœuds distincts liés dans le .comm ; appuis "
        f"à axe (P44) : axe non maillé, point P à Z = {lv['axe_appui']}, relations LIAISON_DDL.",
        [
            "element",
            "type",
            "noeud1",
            "noeud2",
            "famille",
            "groupe",
            "membre",
            "section",
            "yl_x",
            "yl_y",
            "yl_z",
            "zl_x",
            "zl_y",
            "zl_z",
            "excentricite_ou_liaison",
        ],
        element_rows(vd),
    )
    files["membres.csv"] = write(
        out / "membres.csv",
        f"{src} Unités : m. {AXES} Membre : barre entre deux nœuds de raccord (nœud commun à "
        "une autre barre, nœud d'une liaison ou d'un appui à axe, rotule du quai) ; début = "
        "extrémité de plus petite coordonnée selon l'axe de la famille.",
        [
            "membre",
            "libelle",
            "famille",
            "groupe",
            "section",
            "x_debut",
            "y_debut",
            "z_debut",
            "x_fin",
            "y_fin",
            "z_fin",
            "longueur",
            "noeud_debut",
            "noeud_fin",
            "elements",
            "raccords_debut",
            "raccords_fin",
        ],
        member_rows(vd),
    )
    files["efforts_elementaires.csv"] = write(
        out / "efforts_elementaires.csv",
        f"{src} Unités : N, N·m, m. EFGE_ELNO (POU_D_T) aux deux extrémités de chaque élément de "
        "barre, repère local de elements.csv ; convention Code_Aster brute : N > 0 en traction. "
        + cases_text,
        [
            "cas",
            "element",
            "membre",
            "groupe",
            "famille",
            "extremite",
            "noeud",
            "abscisse_m",
            *EFGE,
        ],
        force_rows(vd),
    )
    files["deplacements_elementaires.csv"] = write(
        out / "deplacements_elementaires.csv",
        f"{src} Unités : m, rad. DEPL par nœud et par cas élémentaire, repère global. "
        + cases_text,
        ["cas", "noeud", *DEPL],
        [
            [c, n, *(float(x) for x in vd.tables.depl[c][n])]
            for c in vd.cases
            for n in sorted(vd.tables.depl[c])
        ],
    )
    files["reactions_elementaires.csv"] = write(
        out / "reactions_elementaires.csv",
        f"{src} Unités : N, N·m, m. Effort de l'appui sur la structure, repère global. Rotules du "
        "quai = culée, non modélisée (P35, P45 : seul point fixe en X) : REAC_NODA, moments sans "
        "objet ; appuis à axe en X = 14,02 sur support fixe (P44) : REAC_NODA de l'oreille "
        "(moments : effet du bras de l'oreille, sans objet pour le support) ; ressorts de la "
        "semelle (SOL) : Σ des forces du sol −k·u, moment par rapport au point donné. Les "
        "appuis à axe sur les chevêtres sont dans appuis_axes.csv.",
        [
            "cas",
            "appui",
            "noeud",
            "x",
            "y",
            "z",
            "RX",
            "RY",
            "RZ",
            "MX",
            "MY",
            "MZ",
            "remarque",
        ],
        reaction_rows(vd),
    )
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        f"{src} Jeu B′ révisé (P27, P31 à P35) et ELU accidentel, avec le déjaugeage DEJ lié à G "
        "(P49 : G×1,2 sans DEJ, G×0,9 avec DEJ×1,0 ; ELS et ELU accidentel : G×1,0 avec ou sans "
        "DEJ), en règles : une combinaison = une option par emplacement d'une branche (produit "
        "des emplacements) ; option = « événement×facteur » (evenements.csv) ou ∅ (absence). "
        "Effectifs : "
        + ", ".join(f"{s} {n}" for s, n in counts(vd.bs).items())
        + f", total {sum(counts(vd.bs).values())}. recombiner.py les énumère.",
        [
            "etat_limite",
            "branche",
            "emplacement",
            "action",
            "nombre_options",
            "effectif_branche",
            "options",
        ],
        rule_rows(vd.bs),
    )
    files["evenements.csv"] = write(
        out / "evenements.csv",
        f"{src} Événements des actions (valeurs caractéristiques) : coefficient appliqué au cas "
        "élémentaire unitaire (kN sur 1 kN, kN/m sur 1 kN/m, kPa sur 1 kPa ; houle de 5 kPa sur "
        "les cas de 1 kPa). Valeurs de l'annexe A de la consigne du lot 51 (P29 à P34). "
        "G_DEJ_090 = 0,9 × G1 + 0,9 × G2 + 1,0 × DEJ et G_DEJ_100 = G1 + G2 + DEJ (P49).",
        ["action", "evenement", "cas", "coefficient"],
        event_rows(vd.ev),
    )
    files["charges.csv"] = write(
        out / "charges.csv",
        f"{src} Unités : N/m (répartie), N/m2 (surfacique), N (ponctuelle), m/s2 (pesanteur), K "
        "(température), m. Charges lues dans le .comm, repère global.",
        [
            "cas",
            "type",
            "groupe",
            "dir_x",
            "dir_y",
            "dir_z",
            "valeur",
            "unite",
            "x_debut",
            "y_debut",
            "z_debut",
            "x_fin",
            "y_fin",
            "z_fin",
            "source",
        ],
        load_rows(vd),
    )
    files["sections.csv"] = write(
        out / "sections.csv",
        f"{src} Unités : m, m2, m4, N/m ; AY, AZ : coefficients de cisaillement (A/Av). "
        "AFFE_CARA_ELEM : mots-clés affectés, puis caractéristiques que Code_Aster en déduit "
        "(U4.42.01), recalculées.",
        ["section", "groupes", "type", "cara", "valeur", "unite", "origine"],
        section_rows(vd.comm),
    )
    files["appuis_axes.csv"] = write(
        out / "appuis_axes.csv",
        f"{src} Unités : N, m, rad. Appuis articulés à axe (P44) : A1 (X = 6,25, chevêtre C1), A2 "
        "(X = 7,77, chevêtre C2), A3 (X = 14,02, support fixe de la palée suivante) ; YM (Y = "
        "−0,93, Y libre), YP (Y = +0,93, Y bloqué) ; x, y, z : point de l'axe. Par appui et par "
        "cas élémentaire : Fx, Fy = effort transmis par l'axe au chevêtre (ou au support), repère "
        "global ; Fz = effort vertical transmis, compté positif vers le bas (Fz > 0 compression, "
        "Fz < 0 traction des tiges, soulèvement) ; Fx = 0 (trou oblong) et, en YM, Fy = 0. "
        "glissement_x : déplacement en X de l'axe porté par l'oreille 1 moins celui porté par le "
        "chevêtre (en A3 : déplacement en X de l'axe). Rotations relatives autour de Y : "
        "oreille 1 (grande travée) − chevêtre, oreille 2 (petite travée) − chevêtre, oreille 2 − "
        "oreille 1 (A3 : oreille 1 seule, support fixe sans rotation).",
        [
            "cas",
            "appui",
            "rive",
            "support",
            "x",
            "y",
            "z",
            "Fx",
            "Fy",
            "Fz",
            "glissement_x",
            "rotation_y_oreille1",
            "rotation_y_oreille2",
            "rotation_y_oreille2_moins_1",
        ],
        pin_rows(vd),
    )
    files["piles.csv"] = write(
        out / "piles.csv",
        f"{src} Unités : N, N·m. Torseurs EFGE_ELNO en tête (sous-face de l'anneau, +{lv['tete_piles']}) "
        f"et en pied (dessus de la semelle, {lv['dessus_semelle']}) de chaque pile, repère local x_l = "
        "+Z, y_l = +X, z_l = +Y ; N > 0 en traction. Têtes encastrées dans l'anneau (P46), pieds "
        "encastrés dans la semelle.",
        ["cas", "pile", "position", "noeud", "element", "z", *EFGE],
        pile_rows(vd),
    )
    eq_rows, eq_summary = equilibrium_rows(vd)
    vol = concrete_volumes(vd.vals, vd.g)
    files["palee_equilibre.csv"] = write(
        out / "palee_equilibre.csv",
        f"{src} Unités : N. Équilibre de la palée (P49), enveloppes du jeu B′ révisé et de l'ELU "
        "accidentel avec DEJ (G×1,2 sans DEJ ; G×0,9 avec DEJ ; ELS, ELU accidentel avec et sans "
        "DEJ). SRz_min : minimum de la somme des forces du sol sur la semelle (> 0 vers le haut, "
        "−k_n × aire × u_z), avec sa combinaison ; ressorts_traction : nombre et position des "
        "ressorts tirés dans cette combinaison (sol linéaire, traction admise, P19 : constatée, "
        "jamais supprimée) ; N_traction_max : effort normal maximal de chaque pile en tête et en "
        "pied (N > 0 traction) ; lest_manquant = max(0 ; −ΣRz min ELU) / 0,9. Volume de béton "
        "modélisé : "
        + ", ".join(f"{k} {number(x)} m3" for k, x in vol.items())
        + f", total {number(sum(vol.values()))} m3.",
        ["etat_limite", "grandeur", "lieu", "valeur", "unite", "combinaison", "detail"],
        eq_rows,
    )
    shutil.copyfile(
        Path(__file__).resolve().parent / "scripts" / "recombiner_lot51bis.py",
        out / "recombiner.py",
    )
    return files, eq_summary


def element_rows(vd: VariantData51bis) -> list[list[Any]]:
    m = vd.model
    rows: list[list[Any]] = []
    for e in sorted(m.elements.values(), key=lambda e: e.number):
        rows.append(
            [
                e.number,
                "SEG2 POU_D_T",
                e.nodes[0],
                e.nodes[1],
                e.family,
                e.group,
                e.member,
                e.section,
                *(geo(x) for x in e.y_local),
                *(geo(x) for x in e.z_local),
                "aucune (axe neutre sur la ligne des nœuds)",
            ]
        )
    for lk in vd.g.links:
        (a,) = m.group_nodes[f"{lk.name}_A"]
        (b,) = m.group_nodes[f"{lk.name}_B"]
        offset = m.coords[b - 1] - m.coords[a - 1]
        rows.append(
            [
                lk.name,
                "LIAISON_SOLIDE",
                a,
                b,
                "LIAISON",
                lk.kind,
                *([""] * 8),
                f"LIAISON_SOLIDE (6 ddl liés) ; vecteur nœud 1 → nœud 2 = ({number(geo(offset[0]))}, "
                f"{number(geo(offset[1]))}, {number(geo(offset[2]))}) m",
            ]
        )
    for ax in vd.g.axes:
        ears = [m.group_nodes[ax.ear_group(k)][0] for k in range(1, len(ax.ears) + 1)]
        cap = m.group_nodes[ax.cap_group][0] if ax.cap is not None else ""
        text = (
            f"appui à axe (P44), axe parallèle à Y en ({number(ax.pin[0])}, {number(ax.pin[1])}, "
            f"{number(ax.pin[2])}) : LIAISON_DDL sur u_N + θ_N ∧ (P − N) ; "
            + (
                "oreilles des deux travées : translations de P et DRX égales ; "
                if len(ears) == 2
                else ""
            )
            + ("chevêtre : Z" if ax.cap is not None else "support fixe : Z")
            + (" et Y liés" if ax.blocks_y else " lié, Y libre")
            + ", X libre (trou oblong)"
        )
        rows.append(
            [
                f"AXE_{ax.name}",
                "LIAISON_DDL",
                ears[0],
                ears[1] if len(ears) == 2 else cap,
                "APPUI_AXE",
                f"AX_{ax.name}",
                *([""] * 8),
                text + (f" ; nœud du chevêtre {cap}" if len(ears) == 2 else ""),
            ]
        )
    return rows


def member_rows(vd: VariantData51bis) -> list[list[Any]]:
    m = vd.model
    rows = []
    for mem in m.members:
        p, q = m.coords[mem.nodes[0] - 1], m.coords[mem.nodes[-1] - 1]

        def joins(node: int, mem: Member = mem) -> str:
            items = [
                f"{o.name} : {'continuité' if o.group == mem.group else 'nœud commun'}"
                for o in m.members
                if node in (o.nodes[0], o.nodes[-1]) and o is not mem
            ]
            items += [f"{j} : liaison ou appui" for j in m.joints.get(node, [])]
            return " | ".join(items)

        rows.append(
            [
                mem.name,
                mem.label,
                mem.family,
                mem.group,
                mem.section,
                *(geo(x) for x in p),
                *(geo(x) for x in q),
                geo(mem.length),
                mem.nodes[0],
                mem.nodes[-1],
                " ".join(str(e) for e in mem.elements),
                joins(mem.nodes[0]),
                joins(mem.nodes[-1]),
            ]
        )
    return rows


def force_rows(vd: VariantData51bis) -> list[list[Any]]:
    m = vd.model
    rows: list[list[Any]] = []
    members = {mem.name: mem for mem in m.members}
    for case in vd.cases:
        table = vd.tables.efge[case]
        for e in sorted(m.elements.values(), key=lambda e: e.number):
            for end, node in enumerate(e.nodes, start=1):
                rows.append(
                    [
                        case,
                        e.number,
                        e.member,
                        e.group,
                        e.family,
                        end,
                        node,
                        geo(members[e.member].abscissa[node]),
                        *(float(x) for x in table[(e.number, node)]),
                    ]
                )
    return rows


def reaction_rows(vd: VariantData51bis) -> list[list[Any]]:
    m = vd.model
    nodes, areas = soil_areas(vd)
    k = np.array([vd.vals.kt, vd.vals.kt, vd.vals.kn])
    fx, fy = vd.g.footing_x, vd.g.footing_y
    centre = np.array([(fx[0] + fx[-1]) / 2.0, (fy[0] + fy[-1]) / 2.0, vd.g.footing_z])
    rows: list[list[Any]] = []
    for case in vd.cases:
        reac = vd.tables.reac[case]
        for name, note in (
            ("APP_QUAI_YM", "culée, rotule guidée : DX DZ bloqués, DY libre"),
            ("APP_QUAI_YP", "culée, rotule fixe : DX DY DZ bloqués"),
            ("AX_A3_YM_1", "appui à axe sur support fixe, X = 14,02 : DZ bloqué"),
            ("AX_A3_YP_1", "appui à axe sur support fixe, X = 14,02 : DY DZ bloqués"),
        ):
            for n in m.group_nodes[name]:
                r = reac[n]
                moments = r[3:] if name.startswith("AX_") else [math.nan] * 3
                rows.append(
                    [
                        case,
                        name,
                        n,
                        *(geo(c) for c in m.coords[n - 1]),
                        *(float(x) for x in r[:3]),
                        *(float(x) for x in moments),
                        note,
                    ]
                )
        depl = vd.tables.depl[case]
        total = np.zeros(3)
        moment = np.zeros(3)
        for n, area in zip(nodes, areas, strict=True):
            p = m.coords[n - 1]
            f = -k * area * depl[n][:3]
            total += f
            moment += np.cross(p - centre, f)
        rows.append(
            [
                case,
                "SOL (ressorts de la semelle, cumul)",
                f"{len(nodes)} nœuds",
                *(geo(c) for c in centre),
                *(float(x) for x in total),
                *(float(x) for x in moment),
                "Σ des forces du sol sur la semelle (−k·u) ; moment par rapport au point donné",
            ]
        )
    return rows


def pile_ends(vd: VariantData51bis) -> list[tuple[str, str, int, int]]:
    out = []
    for pile in PILES:
        (head,) = vd.model.group_nodes[f"TP_{pile}_A"]
        (foot,) = vd.model.group_nodes[f"PS_{pile}_A"]
        for position, node in (("tete", head), ("pied", foot)):
            (e,) = [
                el
                for el in vd.model.elements.values()
                if el.group == f"PILE_{pile}" and node in el.nodes
            ]
            out.append((pile, position, node, e.number))
    return out


def pile_rows(vd: VariantData51bis) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for case in vd.cases:
        for pile, position, node, e in pile_ends(vd):
            rows.append(
                [
                    case,
                    pile,
                    position,
                    node,
                    e,
                    geo(vd.model.coords[node - 1][2]),
                    *(float(x) for x in vd.tables.efge[case][(e, node)]),
                ]
            )
    return rows


def load_rows(vd: VariantData51bis) -> list[list[Any]]:
    comm = read_comm(vd.comm)
    concepts = {c: k for c, n, k in comm if n == "AFFE_CHAR_MECA"}
    _, mult = first_of(comm, "MACRO_ELAS_MULT")
    m = vd.model
    rows: list[list[Any]] = []
    vectors = {"FX": (1.0, 0.0, 0.0), "FY": (0.0, 1.0, 0.0), "FZ": (0.0, 0.0, 1.0)}
    for occ in occurrences(mult["CAS_CHARGE"]):
        case = str(occ["NOM_CAS"])
        charges = occ["CHAR_MECA"]
        charges = charges if isinstance(charges, tuple) else (charges,)
        for concept in charges:
            kw = concepts[concept.name]
            for g in occurrences(kw.get("PESANTEUR")):
                rows.append(
                    [
                        case,
                        "pesanteur",
                        "tout le modèle",
                        *(float(x) for x in g["DIRECTION"]),
                        float(g["GRAVITE"]),
                        "m/s2",
                        *([""] * 6),
                        f"PESANTEUR ({concept.name})",
                    ]
                )
            for key, kind, unit in (
                ("FORCE_POUTRE", "répartie", "N/m"),
                ("FORCE_NODALE", "ponctuelle", "N"),
                ("FORCE_COQUE", "surfacique", "N/m2"),
            ):
                for f in occurrences(kw.get(key)):
                    for group in names(f.get("GROUP_MA", f.get("GROUP_NO"))):
                        pts = m.coords[np.array(m.group_nodes[group]) - 1]
                        lo = pts.min(axis=0)
                        hi = pts.max(axis=0)
                        for comp, vec in vectors.items():
                            if comp in f:
                                rows.append(
                                    [
                                        case,
                                        kind,
                                        group,
                                        *vec,
                                        float(f[comp]),
                                        unit,
                                        *(geo(x) for x in lo),
                                        *(geo(x) for x in hi),
                                        f"{key}/{comp} ({concept.name})",
                                    ]
                                )
    for concept, name, kw in comm:
        if name != "CREA_CHAMP" or not concept.startswith("T_"):
            continue
        case = concept.removeprefix("T_")
        for a in occurrences(kw["AFFE"]):
            rows.append(
                [
                    case,
                    "température",
                    " ".join(names(a["GROUP_MA"])),
                    "",
                    "",
                    "",
                    float(a["VALE"]),
                    "K (écart uniforme, VALE_REF = 0)",
                    *([""] * 6),
                    f"CREA_CHAMP {concept}, AFFE_VARC M_{case}",
                ]
            )
    return rows


# --------------------------------------------------------------------------- comparison


def _arrays(
    vd: VariantData51bis, rows: list[tuple[int, int]], comp: int
) -> dict[str, FloatArray]:
    return {c: np.array([vd.tables.efge[c][r][comp] for r in rows]) for c in vd.cases}


def _rows_of(vd: VariantData51bis, families: tuple[str, ...]) -> list[tuple[int, int]]:
    return [
        (e.number, n)
        for e in vd.model.elements.values()
        if e.family in families
        for n in e.nodes
    ]


@dataclass
class Quantity:
    label: str
    unit: str
    value: float
    state: str
    combination: str
    where: str


def _max_over_states(
    vd: VariantData51bis,
    f: dict[str, FloatArray],
    *,
    sign: float,
    where: list[str],
    scale: float,
    states: tuple[str, ...] = STATES_COMPARED,
    without: tuple[str, ...] = (),
    absolute: bool = False,
) -> Quantity:
    best: tuple[float, float, str, str, str] | None = None
    for state in states:
        for sg in (1.0, -1.0) if absolute else (sign,):
            ext = envelope(vd.bs, vd.ev, f, state, sign=sg, without=without)
            scores = sg * ext.value
            q = int(np.argmax(scores))
            if best is None or float(scores[q]) > best[0]:
                name, _ = governing(vd.bs, vd.ev, ext, q)
                best = (float(scores[q]), float(ext.value[q]), state, name, where[q])
    assert best is not None
    return Quantity("", "", best[1] * scale, best[2], best[3], best[4])


def _resultant_over_states(
    vd: VariantData51bis,
    a: dict[str, FloatArray],
    b: dict[str, FloatArray],
    where: list[str],
    scale: float,
) -> Quantity:
    best: tuple[float, str, str] | None = None
    for state in STATES_COMPARED:
        vals = resultant_max(vd.bs, vd.ev, a, b, state)
        q = int(np.argmax(vals))
        if best is None or float(vals[q]) > best[0]:
            best = (float(vals[q]), state, where[q])
    assert best is not None
    return Quantity(
        "",
        "",
        best[0] * scale,
        best[1],
        "(résultante : maximum sur 2 048 directions)",
        best[2],
    )


def deflection_arrays(vd: VariantData51bis) -> tuple[dict[str, FloatArray], list[str]]:
    """uz relative to the chord of the supports of each main beam of span 1 (X = 0 and
    X = 6,25), per node."""
    rows = []
    where = []
    for side in ("YM", "YP"):
        mem = vd.g.member(f"PP_T1_{side}")
        nodes = sorted(
            {
                n
                for e in vd.model.elements.values()
                if e.group == mem.name
                for n in e.nodes
            },
            key=lambda n: float(vd.model.coords[n - 1][0]),
        )
        first, last = nodes[0], nodes[-1]
        x0 = float(vd.model.coords[first - 1][0])
        x1 = float(vd.model.coords[last - 1][0])
        for n in nodes:
            t = (float(vd.model.coords[n - 1][0]) - x0) / (x1 - x0)
            rows.append((n, first, last, t))
            where.append(f"PP_T1_{side} X = {geo(vd.model.coords[n - 1][0])}")
    f = {
        c: np.array(
            [d[n][2] - ((1 - t) * d[a][2] + t * d[b][2]) for n, a, b, t in rows]
        )
        for c in vd.cases
        for d in (vd.tables.depl[c],)
    }
    return f, where


def without_tangential(f: dict[str, FloatArray]) -> dict[str, FloatArray]:
    """P51: the tangential berthing component left out (its unit cases set to zero)."""
    return {
        c: (np.zeros_like(a) if c.startswith(TANGENTIAL) else a) for c, a in f.items()
    }


def corners(vd: VariantData51bis) -> list[tuple[int, int]]:
    out = []
    for pile in PILES:
        cap = vd.model.group_nodes[f"TP_{pile}_B"][0]
        tie = vd.model.group_nodes[f"LG_{pile}_A"][0]
        for e in vd.model.elements.values():
            if e.family in ("CHEVETRES", "LONGRINES"):
                out += [(e.number, n) for n in e.nodes if n in (cap, tie)]
    return out


def comparison(vd: VariantData51bis) -> dict[str, Quantity]:  # noqa: PLR0915
    out: dict[str, Quantity] = {}
    kn, knm, mm = 1e-3, 1e-3, 1e3

    def put(key: str, label: str, unit: str, q: Quantity) -> None:
        q.label, q.unit = label, unit
        out[key] = q

    for fam, prefix in (
        ("POUTRES_PRINC", "PP"),
        ("CHEVETRES", "CHEV"),
        ("LONGRINES", "LONG"),
    ):
        rows = _rows_of(vd, (fam,))
        where = [
            f"élément {e} nœud {n} ({vd.model.elements[e].member})" for e, n in rows
        ]
        put(
            f"{prefix}_My",
            f"{prefix} My extrême en valeur absolue, signé (MFY)",
            "kN·m",
            _max_over_states(
                vd, _arrays(vd, rows, 4), sign=1, where=where, scale=knm, absolute=True
            ),
        )
        put(
            f"{prefix}_Mz",
            f"{prefix} Mz extrême en valeur absolue, signé (MFZ)",
            "kN·m",
            _max_over_states(
                vd, _arrays(vd, rows, 5), sign=1, where=where, scale=knm, absolute=True
            ),
        )
        if fam == "POUTRES_PRINC":
            put(
                "PP_N_min",
                "PP N min",
                "kN",
                _max_over_states(
                    vd, _arrays(vd, rows, 0), sign=-1, where=where, scale=kn
                ),
            )
            put(
                "PP_N_max",
                "PP N max",
                "kN",
                _max_over_states(
                    vd, _arrays(vd, rows, 0), sign=1, where=where, scale=kn
                ),
            )
        else:
            put(
                f"{prefix}_T",
                f"{prefix} T extrême en valeur absolue, signé (MT)",
                "kN·m",
                _max_over_states(
                    vd,
                    _arrays(vd, rows, 3),
                    sign=1,
                    where=where,
                    scale=knm,
                    absolute=True,
                ),
            )
        put(
            f"{prefix}_V",
            f"{prefix} V max (√(VY² + VZ²))",
            "kN",
            _resultant_over_states(
                vd, _arrays(vd, rows, 1), _arrays(vd, rows, 2), where, kn
            ),
        )
    # Flèches de la travée 1 (P51) : ELS caractéristique sans la composante tangentielle
    # d'accostage, ELS fréquent avec ; actions variables seules (G et DEJ exclus).
    f, where = deflection_arrays(vd)
    for state, tag, ff in (
        ("ELS_frequent", "F", f),
        ("ELS_caracteristique", "C", without_tangential(f)),
    ):
        for sign, direction in ((-1.0, "bas"), (1.0, "haut")):
            q = _max_over_states(
                vd,
                ff,
                sign=sign,
                where=where,
                scale=mm,
                states=(state,),
                without=("G",),
            )
            put(
                f"FL_T1_{tag}_{direction}",
                f"flèche relative T1 vers le {direction}, {state}, variables seules (< 0 vers le bas)"
                + (
                    ", sans composante tangentielle d'accostage (P51)"
                    if tag == "C"
                    else ""
                ),
                "mm",
                q,
            )
    # Appuis à axe.
    axes = [a.name for a in vd.g.axes]
    pins = {c: pin_results(vd, c) for c in vd.cases}
    fz = {c: np.array([-pins[c][a].force[2] for a in axes]) for c in vd.cases}
    put(
        "AXE_Fz_min",
        "appuis à axe Fz min (< 0 : traction des tiges, soulèvement)",
        "kN",
        _max_over_states(vd, fz, sign=-1, where=axes, scale=kn),
    )
    put(
        "AXE_Fz_max",
        "appuis à axe Fz max (compression)",
        "kN",
        _max_over_states(vd, fz, sign=1, where=axes, scale=kn),
    )
    fy = {c: np.array([pins[c][a].force[1] for a in axes]) for c in vd.cases}
    put(
        "AXE_Fy_max",
        "appuis à axe Fy extrême en valeur absolue, signé (appuis YP)",
        "kN",
        _max_over_states(vd, fy, sign=1, where=axes, scale=kn, absolute=True),
    )
    sx = {c: np.array([pins[c][a].slide_x for a in axes]) for c in vd.cases}
    put(
        "AXE_dx",
        "appuis à axe glissement en X extrême signé (trou oblong)",
        "mm",
        _max_over_states(vd, sx, sign=1, where=axes, scale=mm, absolute=True),
    )
    put(
        "AXE_dx_ELS_C",
        "appuis à axe glissement en X extrême signé, ELS caractéristique (trou oblong)",
        "mm",
        _max_over_states(
            vd,
            sx,
            sign=1,
            where=axes,
            scale=mm,
            states=("ELS_caracteristique",),
            absolute=True,
        ),
    )
    # Piles.
    ends = pile_ends(vd)
    rows = [(e, n) for _, _, n, e in ends]
    where = [f"{p} {pos}" for p, pos, _, _ in ends]
    put(
        "PILE_N_min",
        "piles N min (compression)",
        "kN",
        _max_over_states(vd, _arrays(vd, rows, 0), sign=-1, where=where, scale=kn),
    )
    put(
        "PILE_N_max",
        "piles N max (traction maximale si > 0)",
        "kN",
        _max_over_states(vd, _arrays(vd, rows, 0), sign=1, where=where, scale=kn),
    )
    for pos, key in (("tete", "PILE_M_tete"), ("pied", "PILE_M_pied")):
        sub = [(e, n) for p, ps, n, e in ends if ps == pos]
        wsub = [f"{p} {ps}" for p, ps, _, _ in ends if ps == pos]
        put(
            key,
            f"piles M en {pos} (√(MFY² + MFZ²))",
            "kN·m",
            _resultant_over_states(
                vd, _arrays(vd, sub, 4), _arrays(vd, sub, 5), wsub, knm
            ),
        )
    put(
        "PILE_V",
        "piles V max (√(VY² + VZ²))",
        "kN",
        _resultant_over_states(
            vd, _arrays(vd, rows, 1), _arrays(vd, rows, 2), where, kn
        ),
    )
    # Nœuds d'angle de l'anneau.
    corner_rows = corners(vd)
    where = [
        f"élément {e} nœud {n} ({vd.model.elements[e].member})" for e, n in corner_rows
    ]
    for comp, key, lab in (
        (4, "ANGLE_My", "|My|"),
        (5, "ANGLE_Mz", "|Mz|"),
        (3, "ANGLE_T", "|T|"),
    ):
        put(
            key,
            f"anneau, nœuds d'angle, {lab} extrême signé",
            "kN·m",
            _max_over_states(
                vd,
                _arrays(vd, corner_rows, comp),
                sign=1,
                where=where,
                scale=knm,
                absolute=True,
            ),
        )
    # Équilibre de la palée.
    _, soil = soil_forces(vd)
    total = {c: np.array([soil[c].sum()]) for c in vd.cases}
    for key, states, lab in (
        ("SEM_SRz_min_ELU", ("ELU_fondamental", "ELU_accidentel"), "ELU"),
        ("SEM_SRz_min_ELS_C", ("ELS_caracteristique",), "ELS caractéristique"),
    ):
        put(
            key,
            f"semelle ΣRz min du sol, {lab} (> 0 vers le haut)",
            "kN",
            _max_over_states(
                vd, total, sign=-1, where=["semelle"], scale=kn, states=states
            ),
        )
    q = out["SEM_SRz_min_ELU"]
    put(
        "LEST_manquant",
        "lest manquant = max(0 ; −ΣRz min ELU) / 0,9",
        "kN",
        Quantity("", "", max(0.0, -q.value) / 0.9, q.state, q.combination, q.where),
    )
    # Culée (rotules du quai, non modélisée).
    quai = [
        vd.model.group_nodes["APP_QUAI_YM"][0],
        vd.model.group_nodes["APP_QUAI_YP"][0],
    ]
    where = ["rotule YM (guidée)", "rotule YP (fixe)"]
    for comp, key in ((0, "CULEE_RX"), (1, "CULEE_RY"), (2, "CULEE_RZ")):
        f = {c: np.array([vd.tables.reac[c][n][comp] for n in quai]) for c in vd.cases}
        put(
            key,
            f"culée (rotules du quai) R{'XYZ'[comp]} extrême signé",
            "kN",
            _max_over_states(vd, f, sign=1, where=where, scale=kn, absolute=True),
        )
    return out


COMPARISON_COLUMNS = (
    "PP_My",
    "PP_Mz",
    "PP_N_min",
    "PP_N_max",
    "PP_V",
    "FL_T1_F_bas",
    "FL_T1_F_haut",
    "FL_T1_C_bas",
    "FL_T1_C_haut",
    "AXE_Fz_min",
    "AXE_Fz_max",
    "AXE_Fy_max",
    "AXE_dx",
    "AXE_dx_ELS_C",
    "PILE_N_min",
    "PILE_N_max",
    "PILE_M_tete",
    "PILE_M_pied",
    "PILE_V",
    "CHEV_My",
    "CHEV_Mz",
    "CHEV_T",
    "CHEV_V",
    "LONG_My",
    "LONG_Mz",
    "LONG_T",
    "LONG_V",
    "ANGLE_My",
    "ANGLE_Mz",
    "ANGLE_T",
    "SEM_SRz_min_ELU",
    "SEM_SRz_min_ELS_C",
    "LEST_manquant",
    "CULEE_RX",
    "CULEE_RY",
    "CULEE_RZ",
)


# --------------------------------------------------------------------------- criteria


def criterion_linearity(vd: VariantData51bis) -> dict[str, float]:
    """Criterion 3: the total case against the sum of its span cases (DEPL)."""
    out = {}
    for base in ("G2", "Q", "HU", "HD"):
        nodes = sorted(vd.tables.depl[base])
        total = np.array([vd.tables.depl[base][n][:6] for n in nodes])
        parts = sum(
            np.array([vd.tables.depl[f"{base}_{t}"][n][:6] for n in nodes])
            for t in ("T1", "PT", "T2")
        )
        diff = np.nan_to_num(np.abs(total - parts))
        out[base] = float(diff.max() / np.nanmax(np.abs(total)))
    return out


def criterion_pins(vd: VariantData51bis) -> dict[str, float]:
    """Criterion 4: Σ REAC_NODA of the ears and the cap node of each pin; X of the
    force on the cap beam; Y on side YM; relative to max |F| of the case."""
    m = vd.model
    worst = {"somme": 0.0, "Fx": 0.0, "Fy_YM": 0.0}
    for case in vd.cases:
        reac = vd.tables.reac[case]
        pins = pin_results(vd, case)
        scale = max(float(np.abs(r.force).max()) for r in pins.values())
        scale = max(scale, 1e-300)
        for a in vd.g.axes:
            if a.cap is None:
                continue
            nodes = [m.group_nodes[a.ear_group(k)][0] for k in (1, 2)]
            nodes.append(m.group_nodes[a.cap_group][0])
            total = sum(np.array(reac[n][:3]) for n in nodes)
            worst["somme"] = max(worst["somme"], float(np.abs(total).max()) / scale)
            worst["Fx"] = max(worst["Fx"], abs(float(pins[a.name].force[0])) / scale)
            if not a.blocks_y:
                worst["Fy_YM"] = max(
                    worst["Fy_YM"], abs(float(pins[a.name].force[1])) / scale
                )
    return worst


def criterion_recombination(out: Path, vd: VariantData51bis) -> list[dict[str, Any]]:
    """Criterion 5: decomposition against the enumeration of the delivered
    recombiner.py at the governing place."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51bis", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    places: list[tuple[str, dict[str, FloatArray], list[str]]] = []
    rows = _rows_of(vd, ("POUTRES_PRINC",))
    places.append(
        ("MFY poutres principales", _arrays(vd, rows, 4), [f"{e}/{n}" for e, n in rows])
    )
    prow = [(e, n) for _, _, n, e in pile_ends(vd)]
    places.append(("N piles", _arrays(vd, prow, 0), [f"{e}/{n}" for e, n in prow]))
    axes = [a.name for a in vd.g.axes]
    pins = {c: pin_results(vd, c) for c in vd.cases}
    places.append(
        (
            "Fz appuis à axe",
            {c: np.array([-pins[c][a].force[2] for a in axes]) for c in vd.cases},
            axes,
        )
    )
    _, soil = soil_forces(vd)
    places.append(
        (
            "ΣRz semelle",
            {c: np.array([soil[c].sum()]) for c in vd.cases},
            ["semelle"],
        )
    )
    checks = []
    for label, f, where in places:
        for state in ("ELU_fondamental", "ELU_accidentel"):
            for sign in (1.0, -1.0):
                ext = envelope(vd.bs, vd.ev, f, state, sign=sign)
                q = int(np.argmax(sign * ext.value))
                values_q = {c: float(f[c][q]) for c in vd.cases}
                brute = rec.extremes(
                    [r for r in rules if r[0] == state], events_csv, values_q
                )[state]
                reference = brute[0] if sign > 0 else brute[2]
                value = float(ext.value[q])
                rel = abs(value - reference) / max(abs(reference), 1e-300)
                checks.append(
                    {
                        "grandeur": label,
                        "etat_limite": state,
                        "extreme": "max" if sign > 0 else "min",
                        "lieu": where[q],
                        "decomposition": value,
                        "enumeration": reference,
                        "ecart_relatif": rel,
                        "combinaison_enumeration": brute[1] if sign > 0 else brute[3],
                        "reussi": rel <= 1e-9,
                    }
                )
    return checks


def criterion_counts(vd: VariantData51bis) -> dict[str, Any]:
    """Criterion 6: the count by formula against the enumeration without duplicates."""
    seen = set()
    total = 0
    for b in vd.bs:
        for _, coefs in enumerate_branch(b, vd.ev):
            key = (b.state, *sorted((k, round(v, 12)) for k, v in coefs.items() if v))
            seen.add(key)
            total += 1
    formula = sum(counts(vd.bs).values())
    return {
        "formule": formula,
        "enumerees": total,
        "distinctes": len(seen),
        "reussi": formula == total == len(seen),
    }


# --------------------------------------------------------------------------- steps


def step_exports(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    root = ctx.results_dir / LOT / "exports"
    root.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    detail_rows: list[list[Any]] = []
    main_rows: list[list[Any]] = []
    for code in codes:
        s = state.get(code, {})
        execution = s.get("execution", {})
        v = variants()[code]
        if "execution_dir" not in execution:
            message = str(execution.get("message", "non exécutée"))
            main_rows.append(
                [
                    code,
                    v.description,
                    "non calculée : " + message.splitlines()[0],
                    *([""] * len(COMPARISON_COLUMNS)),
                ]
            )
            found = re.search(r"compte rendu dans (\S+)", message)
            if found is not None:
                mess = Path(found.group(1)) / "proc.0" / "fort.6"
                if mess.is_file():
                    message += "".join(
                        "\n" + line.strip()
                        for line in mess.read_text(
                            "utf-8", errors="replace"
                        ).splitlines()
                        if line.startswith("Degré de liberté physique associé")
                    )
            note = root / code
            note.mkdir(parents=True, exist_ok=True)
            (note / "instabilite.txt").write_text(
                f"PONTONS-ALU-01, lot 51 bis, variante {code} ({v.description}) : non calculée.\n"
                "Message de Code_Aster :\n" + message + "\n",
                encoding="utf-8",
            )
            summary[code] = {"statut": "non calculée", "message": message}
            print(f"{code} : non calculée")
            continue
        vd = load_variant(ctx, code, state)
        out = root / code
        files, equilibrium = export_variant(vd, state, out)
        quantities = comparison(vd)
        info: dict[str, Any] = {
            "statut": "calculée",
            "fichiers": files,
            "effectifs": counts(vd.bs),
            "volumes_beton_m3": concrete_volumes(vd.vals, vd.g),
            "cotes_m_ngf": vd.g.levels,
            "equilibre": equilibrium,
            "comparaison": {k: q.__dict__ for k, q in quantities.items()},
        }
        if code == "H80C":
            info["critere_3_linearite"] = criterion_linearity(vd)
            info["critere_4_appuis_axe"] = criterion_pins(vd)
            info["critere_5_recombinaison"] = criterion_recombination(out, vd)
            info["critere_6_effectifs"] = criterion_counts(vd)
        summary[code] = info
        main_rows.append(
            [
                code,
                v.description,
                "calculée",
                *(quantities[c].value for c in COMPARISON_COLUMNS),
            ]
        )
        for key in COMPARISON_COLUMNS:
            q = quantities[key]
            detail_rows.append(
                [code, key, q.label, q.unit, q.value, q.state, q.combination, q.where]
            )
        print(f"{code} : exports écrits ({sum(files.values())} lignes)")
    labels = {}
    for info in summary.values():
        for key, q in info.get("comparaison", {}).items():
            labels[key] = f"{q['label']} [{q['unit']}]"
    header = (
        "PONTONS-ALU-01, lot 51 bis : comparaison des variantes. Valeurs : enveloppes du jeu B′ "
        "révisé (ELU fondamental, ELS caractéristique, ELS fréquent) et de l'ELU accidentel, avec "
        "le déjaugeage DEJ (P49), sauf les flèches (ELS fréquent, ELS caractéristique sans la "
        "composante tangentielle d'accostage, P51 ; actions variables seules, relatives à la corde "
        "des appuis de la travée 1) et l'équilibre de la palée (états limites nommés). Unités : "
        "kN, kN·m, mm. Colonnes : "
        + " ; ".join(f"{k} = {labels.get(k, k)}" for k in COMPARISON_COLUMNS)
        + ". Détail (état limite, combinaison et lieu qui gouvernent) : comparaison_variantes_detail.csv."
    )
    write(
        root / "comparaison_variantes.csv",
        header,
        ["variante", "description", "statut", *COMPARISON_COLUMNS],
        main_rows,
    )
    write(
        root / "comparaison_variantes_detail.csv",
        "PONTONS-ALU-01, lot 51 bis : grandeurs de comparaison, état limite, combinaison et lieu qui gouvernent.",
        [
            "variante",
            "grandeur",
            "libelle",
            "unite",
            "valeur",
            "etat_limite",
            "combinaison",
            "lieu",
        ],
        detail_rows,
    )
    (root / "synthese.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )


def step_depot(ctx: ProjectContext, codes: list[str], target: Path | None) -> None:
    root = ctx.results_dir / LOT / "exports"
    dest = target or Path("/media/sf_partage/echanges/lot51bis/pontons_alu_01")
    dest.mkdir(parents=True, exist_ok=True)
    listed: list[str] = []
    for code in codes:
        folder = root / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue  # __pycache__ du recombiner importé par le critère 5
            (dest / code).mkdir(exist_ok=True)
            shutil.copyfile(f, dest / code / f.name)
            listed.append(f"{code}/{f.name}")
    for extra in ("comparaison_variantes.csv", "comparaison_variantes_detail.csv"):
        shutil.copyfile(root / extra, dest / extra)
        listed.append(extra)
    from aster_expert.livrables.charges_salome import set_med_path  # noqa: PLC0415

    charges = ctx.results_dir / "livrables" / "charges_salome"
    if "H80C" in codes and (charges / "charges.med").is_file():
        for name in ("charges.med", "charges_salome.py"):
            shutil.copyfile(charges / name, dest / "H80C" / name)
            listed.append(f"H80C/{name}")
        set_med_path(dest / "H80C" / "charges_salome.py", dest / "H80C" / "charges.med")
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(set(listed))]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    print(f"dépôt : {len(lines)} fichiers dans {dest}")


__all__ = [
    "COMPARISON_COLUMNS",
    "FAMILY_AXIS",
    "PinResult",
    "VariantData51bis",
    "comparison",
    "export_variant",
    "load_variant",
    "pin_results",
    "read_run",
    "step_depot",
    "step_exports",
    "without_tangential",
]
