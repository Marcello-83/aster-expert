# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 51 ter for PONTONS-ALU-01 (consigne § Exports), one folder per variant,
read from the tables Code_Aster printed during the run (never recomputed by a model of
the tool): unit 31 (EFGE_ELNO of every bar), 32 (DEPL of every node), 33 (REAC_NODA of
the abutment supports, of the ears of the pins and of the cap beam nodes under them),
and the mesh read by `medcoupling` (trunk `dump_med`).

Formats of lot 51 bis (`;`, decimal point, UTF-8 without BOM, SI, one `#` line on top,
17 significant digits), extended to the whole pontoon (bars located by span and by
pier), and the files of this lot: `ancrage.csv` (anchoring force each pier would need),
`culee.csv` (reactions of the abutment), `chaine_x.csv` (normal force of the main beams
at each line of supports), `deplacements_axes.csv` (X displacement of the pins, for the
slotted holes).

Force of a pin on the cap beam (choice A9): REAC_NODA of the cap beam node under it, Fz
counted positive downwards (Fz > 0 compression, Fz < 0 tension of the anchors). DX of a
pin (choice A11): X translation of the pin point carried by ear 1.
"""

from __future__ import annotations

import itertools
import json
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51ter import (
    STATES,
    Branch,
    Event,
    brute_force,
    check_exclusions,
    counts,
    envelope,
    event_rows,
    events,
    expanded_counts,
    governing,
    magnitudes,
    resultant_max,
    rule_rows,
)
from pontons_alu_01.exports_lot51 import (
    DEPL,
    EFGE,
    REAC,
    Element,
    Member,
    Model,
    _float,
    _short,
    geo,
    mesh_dump,
    number,
    parse_tableau,
    section_rows,
    sha256,
    write,
)
from pontons_alu_01.exports_lot51bis import load_rows
from pontons_alu_01.generation_lot51ter import (
    SPLIT,
    THERMAL_CASES,
    Values51ter,
    all_cases,
    applied_loads,
    case_label,
    concrete_volumes,
    concrete_volumes_by_pier,
    mechanical_cases,
    values,
    zone_names,
)
from pontons_alu_01.geometrie_lot51ter import (
    Geometry51ter,
    geometry,
    span_length,
    tributary_areas,
)
from pontons_alu_01.lot50ter import local_axes
from pontons_alu_01.variantes_lot51ter import Variant51ter, variants

FloatArray = NDArray[np.float64]
LOT = "lot51ter"
TANGENTIAL = ("ACX_", "ACZ_")
"""Unit cases of the tangential berthing component, left out of the characteristic
SLS deflection (P51)."""
STATES_COMPARED = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
)
FAMILY_AXIS = {
    "POUTRES_PRINC": 0,
    "MONTANTS": 1,
    "DIAGONALES": 0,
    "PANNES_SEC": 0,
    "PANNE_RIVE": 1,
    "CHEVETRES": 1,
    "LONGRINES": 0,
    "PILES": 2,
}
KN = 1e-3
MM = 1e3


# --------------------------------------------------------------------------- tables


@dataclass
class RunTables:
    efge: dict[str, dict[tuple[int, int], FloatArray]]
    depl: dict[str, dict[int, FloatArray]]
    reac: dict[str, dict[int, FloatArray]]
    order_to_case: dict[int, str]


def read_run(run_dir: Path, g: Geometry51ter) -> RunTables:
    from aster_expert.controles.tables import TableIndex  # noqa: PLC0415

    proc = run_dir / "proc.0"
    mess = TableIndex((proc / "fort.6").read_text(encoding="utf-8", errors="replace"))
    mechanical = mechanical_cases(g)
    order_to_case: dict[int, str] = {}
    for case in mechanical:
        (row,) = mess.find(f"R{case}")
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


def section_label(family: str, v: Variant51ter) -> str:
    purlin = f"tube {v.purlin_side_mm:g}x{v.purlin_side_mm:g}x{v.purlin_thickness_mm:g}"
    return {
        "POUTRES_PRINC": f"tube {v.beam_side_mm:g}x{v.beam_side_mm:g}x{v.beam_thickness_mm:g}",
        "MONTANTS": "tube 150x150x7",
        "DIAGONALES": "tube 150x150x7",
        "PANNES_SEC": purlin,
        "PANNE_RIVE": purlin,
        "CHEVETRES": "BA 0.40x0.40",
        "LONGRINES": "BA 0.40x0.40",
        "PILES": "pile D0.50",
    }[family]


def _members(
    coords: FloatArray, elements: dict[int, Element], joints: dict[int, list[str]]
) -> list[Member]:
    """Each bar cut at its connection nodes (as `exports_lot51._members`, with the
    edge purlin of the cantilever)."""
    by_group: dict[str, list[Element]] = {}
    for e in elements.values():
        by_group.setdefault(e.group, []).append(e)
    groups_at: dict[int, set[str]] = {}
    for e in elements.values():
        for n in e.nodes:
            groups_at.setdefault(n, set()).add(e.group)
    cut = {n for n, gs in groups_at.items() if len(gs) >= 2} | set(joints)
    out: list[Member] = []
    for group in sorted(
        by_group, key=lambda gr: (list(FAMILY_AXIS).index(by_group[gr][0].family), gr)
    ):
        elems = by_group[group]
        axis = FAMILY_AXIS[elems[0].family]
        adjacency: dict[int, list[Element]] = {}
        for e in elems:
            for n in e.nodes:
                adjacency.setdefault(n, []).append(e)
        ends = [n for n, es in adjacency.items() if len(es) == 1]
        if len(ends) != 2 or any(len(es) > 2 for es in adjacency.values()):
            message = f"{group} n'est pas une barre continue"
            raise ValueError(message)
        start = min(ends, key=lambda n: float(coords[n - 1][axis]))
        chain_nodes, chain_elems = [start], []
        seen: set[int] = set()
        current = start
        while True:
            nxt = [e for e in adjacency[current] if e.number not in seen]
            if not nxt:
                break
            e = nxt[0]
            seen.add(e.number)
            chain_elems.append(e)
            current = e.nodes[1] if e.nodes[0] == current else e.nodes[0]
            chain_nodes.append(current)
        cuts = [0] + [i for i, n in enumerate(chain_nodes[1:-1], start=1) if n in cut]
        cuts.append(len(chain_nodes) - 1)
        for k, (i, j) in enumerate(zip(cuts, cuts[1:], strict=False), start=1):
            nodes = chain_nodes[i : j + 1]
            sub = chain_elems[i:j]
            a = float(coords[nodes[0] - 1][axis])
            b = float(coords[nodes[-1] - 1][axis])
            member = Member(
                name=f"{group}_{k:02d}",
                label=f"{group} de {'XYZ'[axis]} = {_short(a)} à {_short(b)}",
                family=elems[0].family,
                group=group,
                section=sub[0].section,
                nodes=nodes,
                elements=[e.number for e in sub],
            )
            s = 0.0
            member.abscissa[nodes[0]] = 0.0
            for e, n in zip(sub, nodes[1:], strict=True):
                s += e.length
                member.abscissa[n] = s
            for e in sub:
                e.member = member.name
            out.append(member)
    return out


def build_model(
    dump: dict[str, Any], tables: RunTables, g: Geometry51ter, v: Variant51ter
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
            continue  # SEG2 des bords et des coupes des semelles
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
        (n,) = group_nodes[a.cap_group]
        joints.setdefault(n, []).append(f"AXE_{a.name}")
    for name in ("APP_CULEE_YM", "APP_CULEE_YP"):
        for n in group_nodes[name]:
            joints.setdefault(n, []).append(name)
    members = _members(coords, elements, joints)
    return Model(coords, node_groups, group_nodes, elements, {}, members, joints)


# --------------------------------------------------------------------------- variant


@dataclass
class VariantData51ter:
    variant: Variant51ter
    model: Model
    tables: RunTables
    g: Geometry51ter
    cases: list[str]
    ev: dict[str, Event]
    bs: list[Branch]
    comm: Path
    vals: Values51ter
    span_of: dict[str, str] = field(default_factory=dict)
    """Bar group -> span or pier."""


def build_events(ctx: ProjectContext, g: Geometry51ter) -> dict[str, Event]:
    data = {key: item.value for key, item in ctx.data().items().items()}
    return events(
        magnitudes(data),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )


def load_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any]
) -> VariantData51ter:
    from pontons_alu_01.combinaisons_lot51ter import branches  # noqa: PLC0415

    v = variants()[code]
    g = geometry(v.mesh_overrides)
    run_dir = Path(state[code]["execution"]["execution_dir"])
    tables = read_run(run_dir, g)
    dump = mesh_dump(ctx, Path(state[code]["maillage"]["med"]))
    model = build_model(dump, tables, g, v)
    ev = build_events(ctx, g)
    return VariantData51ter(
        v,
        model,
        tables,
        g,
        all_cases(g),
        ev,
        branches(ev),
        Path(state[code]["comm"]),
        values(ctx, v),
        {m.name: m.span for m in g.members},
    )


# --------------------------------------------------------------------------- pins


@dataclass
class PinResult:
    force: FloatArray
    """Force of the pin on the cap beam, global axes."""
    dx: float
    """X of the pin point carried by ear 1 (displacement of the deck at the pin)."""
    slide_x: float
    """The same minus X of the pin point carried by the cap beam node."""
    rotations: tuple[float, float, float]
    """DRY ear 1 − DRY cap, DRY ear 2 − DRY cap, DRY ear 2 − DRY ear 1 (nan if absent)."""


def _pin_translation(depl: FloatArray, node: FloatArray, pin: FloatArray) -> FloatArray:
    return np.asarray(depl[:3] + np.cross(depl[3:6], pin - node), dtype=np.float64)


def pin_results(vd: VariantData51ter, case: str) -> dict[str, PinResult]:
    m = vd.model
    reac = vd.tables.reac[case]
    depl = vd.tables.depl[case]
    out: dict[str, PinResult] = {}
    for a in vd.g.axes:
        ears = [m.group_nodes[a.ear_group(k)][0] for k in range(1, len(a.ears) + 1)]
        pin = np.array(a.pin)
        p1 = _pin_translation(depl[ears[0]], m.coords[ears[0] - 1], pin)
        (cap,) = m.group_nodes[a.cap_group]
        pk = _pin_translation(depl[cap], m.coords[cap - 1], pin)
        ry = float(depl[cap][4])
        r1 = float(depl[ears[0]][4]) - ry
        r2 = float(depl[ears[1]][4]) - ry if len(ears) == 2 else math.nan
        r12 = float(depl[ears[1]][4] - depl[ears[0]][4]) if len(ears) == 2 else math.nan
        out[a.name] = PinResult(
            np.array(reac[cap][:3]), float(p1[0]), float(p1[0] - pk[0]), (r1, r2, r12)
        )
    return out


def pier_of(name: str) -> tuple[str, str]:
    """('P3', 'C1') of an axis name `P3C1_YM`."""
    head = name.split("_")[0]
    return head[:-2], head[-2:]


def pin_rows(vd: VariantData51ter) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for case in vd.cases:
        for name, r in pin_results(vd, case).items():
            a = vd.g.axis(name)
            pier, cap = pier_of(name)
            rows.append(
                [
                    case,
                    pier,
                    cap,
                    a.side,
                    len(a.ears),
                    *(geo(c) for c in a.pin),
                    float(r.force[0]),
                    float(r.force[1]),
                    float(-r.force[2]),
                    float(r.dx),
                    float(r.slide_x),
                    *(float(x) for x in r.rotations),
                ]
            )
    return rows


# --------------------------------------------------------------------------- soil


def soil_nodes(vd: VariantData51ter) -> dict[str, tuple[list[int], FloatArray]]:
    """Per pier: the footing nodes and their tributary areas (RIGI_PARASOL)."""
    m = vd.model
    areas = tributary_areas(vd.g)
    out: dict[str, tuple[list[int], list[float]]] = {}
    for n in m.group_nodes["SEMELLE"]:
        key = (round(float(m.coords[n - 1][0]), 6), round(float(m.coords[n - 1][1]), 6))
        pier, area = areas[key]
        nodes, a = out.setdefault(pier, ([], []))
        nodes.append(n)
        a.append(area)
    return {p: (nodes, np.array(a)) for p, (nodes, a) in out.items()}


def soil_forces(
    vd: VariantData51ter, component: int = 2
) -> dict[str, tuple[list[int], dict[str, FloatArray]]]:
    """Per pier: footing nodes and, per case, the force of the soil on the footing at
    each node along `component` (−k × tributary area × u, > 0 upwards for Z)."""
    k = vd.vals.kn if component == 2 else vd.vals.kt
    out = {}
    for pier, (nodes, a) in soil_nodes(vd).items():
        out[pier] = (
            nodes,
            {
                c: -k * a * np.array([vd.tables.depl[c][n][component] for n in nodes])
                for c in vd.cases
            },
        )
    return out


def pier_totals(vd: VariantData51ter, component: int = 2) -> dict[str, FloatArray]:
    """Per case: ΣR of the soil of each pier (array over the piers, in order P1…)."""
    forces = soil_forces(vd, component)
    piers = list(vd.g.piers)
    return {c: np.array([forces[p][1][c].sum() for p in piers]) for c in vd.cases}


# --------------------------------------------------------------------------- governed


@dataclass
class Governed:
    value: float
    state: str
    combination: str
    coefficients: dict[str, float]
    where: str


def extreme_in_state(
    vd: VariantData51ter,
    f: dict[str, FloatArray],
    state: str,
    sign: float,
    where: list[str],
    *,
    without: tuple[str, ...] = (),
) -> list[Governed]:
    """Per quantity, the extreme of `state` and its combination."""
    ext = envelope(vd.bs, vd.ev, f, state, sign=sign, without=without)
    out = []
    for q in range(len(where)):
        name, coefs = governing(vd.bs, vd.ev, ext, q)
        out.append(Governed(float(ext.value[q]), state, name, coefs, where[q]))
    return out


def value_of(coefs: dict[str, float], f: dict[str, FloatArray], q: int) -> float:
    return float(sum(c * f[k][q] for k, c in coefs.items()))


def wave_share(gov: Governed, f: dict[str, FloatArray], q: int) -> tuple[float, float]:
    """(contribution of the houle event, its share of the variable actions) to the
    quantity q in the governing combination."""
    houle = {"HU_TUBES", "HU_PANNES", "HU_PLATELAGE", "HD_TABLIER"}
    permanent = {"G1", "G2", "DEJ"}
    h = sum(c * f[k][q] for k, c in gov.coefficients.items() if k in houle)
    var = sum(c * f[k][q] for k, c in gov.coefficients.items() if k not in permanent)
    return float(h), (float(h / var) if var != 0.0 else math.nan)


# --------------------------------------------------------------------------- files


def source_line(vd: VariantData51ter, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, lot 51 ter, variante {vd.variant.code} ({vd.variant.description}) : "
        f"exécution {run}, .comm sha256 {sha256(vd.comm)}, maillage sha256 "
        f"{s['maillage']['med_sha256']}."
    )


def axes_text(vd: VariantData51ter) -> str:
    st = ", ".join(f"{x:g}" for x in vd.variant.stations)
    return (
        "Repère global : X le long du ponton depuis la ligne d'appui de la culée (X = 0), "
        f"axes des chevêtres C1 des palées P1 à P5 en X = {st}, C2 à + {vd.variant.cap_spacing:g} m, "
        f"bout du porte-à-faux en X = {vd.g.length:g} ; Y transversal ; Z vertical vers le haut (m NGF)."
    )


def element_rows(vd: VariantData51ter) -> list[list[Any]]:
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
                vd.span_of[e.group],
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
                "",
                *([""] * 8),
                f"LIAISON_SOLIDE (6 ddl liés) ; vecteur nœud 1 → nœud 2 = ({number(geo(offset[0]))}, "
                f"{number(geo(offset[1]))}, {number(geo(offset[2]))}) m",
            ]
        )
    for ax in vd.g.axes:
        ears = [m.group_nodes[ax.ear_group(k)][0] for k in range(1, len(ax.ears) + 1)]
        cap = m.group_nodes[ax.cap_group][0]
        pier, _ = pier_of(ax.name)
        text = (
            f"appui à axe (P44, P54), axe parallèle à Y en ({number(ax.pin[0])}, {number(ax.pin[1])}, "
            f"{number(ax.pin[2])}) : LIAISON_DDL sur u_N + θ_N ∧ (P − N) ; "
            + (
                "oreilles des deux travées : translations de P et DRX égales ; "
                if len(ears) == 2
                else "une oreille (petite travée continue avec le porte-à-faux) ; "
            )
            + "chevêtre : Z"
            + (" et Y liés" if ax.blocks_y else " lié, Y libre")
            + f", X libre (trou oblong) ; nœud du chevêtre {cap}"
        )
        rows.append(
            [
                f"AXE_{ax.name}",
                "LIAISON_DDL",
                ears[0],
                ears[1] if len(ears) == 2 else cap,
                "APPUI_AXE",
                f"AX_{ax.name}",
                pier,
                *([""] * 8),
                text,
            ]
        )
    return rows


def member_rows(vd: VariantData51ter) -> list[list[Any]]:
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
                vd.span_of[mem.group],
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


def force_rows(vd: VariantData51ter) -> Any:
    m = vd.model
    members = {mem.name: mem for mem in m.members}
    elements = sorted(m.elements.values(), key=lambda e: e.number)
    for case in vd.cases:
        table = vd.tables.efge[case]
        for e in elements:
            for end, node in enumerate(e.nodes, start=1):
                yield [
                    case,
                    e.number,
                    e.member,
                    e.group,
                    vd.span_of[e.group],
                    e.family,
                    end,
                    node,
                    geo(members[e.member].abscissa[node]),
                    *(float(x) for x in table[(e.number, node)]),
                ]


def reaction_rows(vd: VariantData51ter) -> list[list[Any]]:
    m = vd.model
    k = np.array([vd.vals.kt, vd.vals.kt, vd.vals.kn])
    soil = soil_nodes(vd)
    rows: list[list[Any]] = []
    for case in vd.cases:
        reac = vd.tables.reac[case]
        for name, note in (
            ("APP_CULEE_YM", "culée, axe YM : DX DZ bloqués, DY libre (P58)"),
            ("APP_CULEE_YP", "culée, axe YP : DX DY DZ bloqués (P58)"),
        ):
            for n in m.group_nodes[name]:
                r = reac[n]
                rows.append(
                    [
                        case,
                        name,
                        n,
                        *(geo(c) for c in m.coords[n - 1]),
                        *(float(x) for x in r[:3]),
                        math.nan,
                        math.nan,
                        math.nan,
                        note,
                    ]
                )
        depl = vd.tables.depl[case]
        for f in vd.g.footings:
            nodes, areas = soil[f.pier]
            centre = np.array(f.centre)
            total = np.zeros(3)
            moment = np.zeros(3)
            for n, area in zip(nodes, areas, strict=True):
                force = -k * area * depl[n][:3]
                total += force
                moment += np.cross(m.coords[n - 1] - centre, force)
            rows.append(
                [
                    case,
                    f"SOL_{f.pier} (ressorts de la semelle de {f.pier}, cumul)",
                    f"{len(nodes)} nœuds",
                    *(geo(c) for c in centre),
                    *(float(x) for x in total),
                    *(float(x) for x in moment),
                    "Σ des forces du sol sur la semelle (−k·u) ; moment par rapport au centre",
                ]
            )
    return rows


def pile_ends(vd: VariantData51ter) -> list[tuple[str, str, str, int, int]]:
    """(pier, pile, position, node, element) of each pile end."""
    out = []
    for f in vd.g.footings:
        for cap in ("C1", "C2"):
            for side in ("YM", "YP"):
                suffix = f"{f.pier}_{cap}_{side}"
                (head,) = vd.model.group_nodes[f"TP_{suffix}_A"]
                (foot,) = vd.model.group_nodes[f"PS_{suffix}_A"]
                for position, node in (("tete", head), ("pied", foot)):
                    (e,) = [
                        el
                        for el in vd.model.elements.values()
                        if el.group == f"PILE_{suffix}" and node in el.nodes
                    ]
                    out.append((f.pier, f"{cap}_{side}", position, node, e.number))
    return out


def pile_rows(vd: VariantData51ter) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for case in vd.cases:
        for pier, pile, position, node, e in pile_ends(vd):
            rows.append(
                [
                    case,
                    pier,
                    pile,
                    position,
                    node,
                    e,
                    geo(vd.model.coords[node - 1][2]),
                    *(float(x) for x in vd.tables.efge[case][(e, node)]),
                ]
            )
    return rows


def _arrays(
    vd: VariantData51ter, rows: list[tuple[int, int]], comp: int
) -> dict[str, FloatArray]:
    return {c: np.array([vd.tables.efge[c][r][comp] for r in rows]) for c in vd.cases}


def _rows_of(vd: VariantData51ter, families: tuple[str, ...]) -> list[tuple[int, int]]:
    return [
        (e.number, n)
        for e in sorted(vd.model.elements.values(), key=lambda e: e.number)
        if e.family in families
        for n in e.nodes
    ]


# --------------------------------------------------------------------------- lot files


def pier_rows(vd: VariantData51ter) -> tuple[list[list[Any]], dict[str, Any]]:
    """palee_equilibre.csv: one line per pier."""
    totals = pier_totals(vd)
    forces = soil_forces(vd)
    piers = list(vd.g.piers)
    volumes = concrete_volumes_by_pier(vd.vals, vd.g)
    gov = {s: extreme_in_state(vd, totals, s, -1.0, piers) for s in STATES}
    rows: list[list[Any]] = []
    summary: dict[str, Any] = {}
    for q, pier in enumerate(piers):
        vol = sum(volumes[pier].values())
        nodes, per_case = forces[pier]
        best = gov["ELU_fondamental"][q]
        combo = sum(
            c * per_case[k] for k, c in best.coefficients.items() if k in per_case
        )
        assert isinstance(combo, np.ndarray)
        tension = int((combo < 0.0).sum())
        elu_min = min(gov["ELU_fondamental"][q].value, gov["ELU_accidentel"][q].value)
        row = [
            pier,
            geo(vd.variant.stations[q]),
            vd.variant.pile_heights[q],
            vd.g.footings[q].z,
            vol,
            vd.vals.gamma_concrete * vol,
            (vd.vals.gamma_concrete - vd.vals.gamma_water) * vol,
        ]
        for s in STATES:
            row += [gov[s][q].value, gov[s][q].combination]
        row += [f"{tension} sur {len(nodes)}", max(0.0, -elu_min) / 0.9]
        rows.append(row)
        summary[pier] = {
            "volume_m3": vol,
            "SRz_min": {s: gov[s][q].value for s in STATES},
            "ressorts_traction_ELU": tension,
            "lest_manquant_N": max(0.0, -elu_min) / 0.9,
        }
    return rows, summary


def anchoring_rows(vd: VariantData51ter) -> tuple[list[list[Any]], dict[str, Any]]:
    """ancrage.csv: per pier, at the fundamental ULS and the characteristic SLS."""
    totals = pier_totals(vd)
    piers = list(vd.g.piers)
    ends = pile_ends(vd)
    pile_f = _arrays(vd, [(e, n) for _, _, _, n, e in ends], 0)
    rows: list[list[Any]] = []
    summary: dict[str, Any] = {}
    for state in ("ELU_fondamental", "ELS_caracteristique"):
        govs = extreme_in_state(vd, totals, state, -1.0, piers)
        piles = extreme_in_state(
            vd, pile_f, state, 1.0, [f"{p} {pl} {pos}" for p, pl, pos, _, _ in ends]
        )
        for q, pier in enumerate(piers):
            g = govs[q]
            anchor = max(0.0, -g.value)
            h, share = wave_share(g, totals, q)
            rows.append(
                [
                    pier,
                    state,
                    "SRz_min",
                    "semelle (Σ des forces du sol, > 0 vers le haut)",
                    g.value,
                    "N",
                    g.combination,
                    "",
                ]
            )
            rows.append(
                [
                    pier,
                    state,
                    "ancrage_requis",
                    "palée",
                    anchor,
                    "N",
                    g.combination,
                    "max(0 ; −ΣRz min)",
                ]
            )
            rows.append(
                [
                    pier,
                    state,
                    "part_HU",
                    "palée, combinaison de SRz_min",
                    share,
                    "-",
                    g.combination,
                    f"contribution de la houle à ΣRz : {number(h)} N, rapportée à celle de toutes les actions variables",
                ]
            )
            summary.setdefault(pier, {})[state] = {
                "SRz_min_N": g.value,
                "ancrage_requis_N": anchor,
                "combinaison": g.combination,
                "houle_N": h,
                "part_houle": share,
            }
            for (p, pile, pos, node, e), pg in zip(ends, piles, strict=True):
                if p != pier:
                    continue
                rows.append(
                    [
                        pier,
                        state,
                        "N_traction_max",
                        f"pile {pile}, {pos} (élément {e}, nœud {node})",
                        pg.value,
                        "N",
                        pg.combination,
                        "traction" if pg.value > 0.0 else "pas de traction (N max ≤ 0)",
                    ]
                )
    return rows, summary


CULEE_STATES = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_quasi_permanent",
)


def abutment_rows(vd: VariantData51ter) -> tuple[list[list[Any]], dict[str, Any]]:
    m = vd.model
    supports = [
        ("YM", m.group_nodes["APP_CULEE_YM"][0]),
        ("YP", m.group_nodes["APP_CULEE_YP"][0]),
    ]
    where = [f"axe {s}" for s, _ in supports]
    rows: list[list[Any]] = []
    summary: dict[str, Any] = {}
    comp = {
        k: {
            c: np.array([vd.tables.reac[c][n][i] for _, n in supports])
            for c in vd.cases
        }
        for i, k in enumerate(("RX", "RY", "RZ"))
    }
    for state in CULEE_STATES:
        for k in ("RX", "RY", "RZ"):
            for sign, tag in ((1.0, "max"), (-1.0, "min")):
                for gv, (side, _) in zip(
                    extreme_in_state(vd, comp[k], state, sign, where),
                    supports,
                    strict=True,
                ):
                    rows.append(
                        [side, state, f"{k}_{tag}", gv.value, "N", gv.combination]
                    )
                    summary.setdefault(state, {})[f"{side}_{k}_{tag}"] = gv.value
        h = resultant_max(vd.bs, vd.ev, comp["RX"], comp["RY"], state)
        for (side, _), val in zip(supports, h, strict=True):
            rows.append(
                [
                    side,
                    state,
                    "RH_max",
                    float(val),
                    "N",
                    "(résultante √(RX² + RY²) : maximum sur 2 048 directions)",
                ]
            )
            summary[state][f"{side}_RH_max"] = float(val)
    return rows, summary


def chain_rows(vd: VariantData51ter) -> list[list[Any]]:
    """chaine_x.csv: N of each main beam at each line of supports, fundamental ULS."""
    m = vd.model
    places: list[tuple[str, str, int, int]] = []
    for side in ("YM", "YP"):
        (n0,) = m.group_nodes[f"APP_CULEE_{side}"]
        places.append(("culée", side, n0, _element_at(vd, f"PP_T1_{side}", n0)))
        for a in vd.g.axes:
            if a.side != side:
                continue
            pier, cap = pier_of(a.name)
            (ear,) = m.group_nodes[a.ear_group(1)]
            group = next(
                gr
                for gr in (
                    f"PP_T{int(pier[1:])}_{side}",
                    f"PP_T{int(pier[1:]) + 1}_{side}",
                    f"PP_PT{pier[1:]}_{side}",
                )
                if _has_node(vd, gr, ear)
            )
            places.append((f"{pier} {cap}", side, ear, _element_at(vd, group, ear)))
    rows_q = [(e, n) for _, _, n, e in places]
    f = _arrays(vd, rows_q, 0)
    where = [f"{line} {side}" for line, side, _, _ in places]
    rows = []
    hi = extreme_in_state(vd, f, "ELU_fondamental", 1.0, where)
    lo = extreme_in_state(vd, f, "ELU_fondamental", -1.0, where)
    for (line, side, n, e), top, low in zip(places, hi, lo, strict=True):
        rows.append(
            [
                line,
                side,
                m.elements[e].group,
                e,
                n,
                geo(m.coords[n - 1][0]),
                top.value,
                top.combination,
                low.value,
                low.combination,
            ]
        )
    return rows


def _has_node(vd: VariantData51ter, group: str, node: int) -> bool:
    return any(e.group == group and node in e.nodes for e in vd.model.elements.values())


def _element_at(vd: VariantData51ter, group: str, node: int) -> int:
    (e,) = [
        el.number
        for el in vd.model.elements.values()
        if el.group == group and node in el.nodes
    ]
    return e


def axis_displacement_rows(
    vd: VariantData51ter,
) -> tuple[list[list[Any]], dict[str, Any]]:
    names = [a.name for a in vd.g.axes]
    pins = {c: pin_results(vd, c) for c in vd.cases}
    dx = {c: np.array([pins[c][a].dx for a in names]) for c in vd.cases}
    slide = {c: np.array([pins[c][a].slide_x for a in names]) for c in vd.cases}
    hi = extreme_in_state(vd, dx, "ELS_caracteristique", 1.0, names)
    lo = extreme_in_state(vd, dx, "ELS_caracteristique", -1.0, names)
    shi = extreme_in_state(vd, slide, "ELS_caracteristique", 1.0, names)
    slo = extreme_in_state(vd, slide, "ELS_caracteristique", -1.0, names)
    rows = []
    summary: dict[str, Any] = {}
    for q, name in enumerate(names):
        a = vd.g.axis(name)
        pier, cap = pier_of(name)
        rows.append(
            [
                pier,
                cap,
                a.side,
                geo(a.pin[0]),
                pins["TP"][name].dx,
                pins["TM"][name].dx,
                hi[q].value,
                hi[q].combination,
                lo[q].value,
                lo[q].combination,
                pins["TP"][name].slide_x,
                pins["TM"][name].slide_x,
                shi[q].value,
                slo[q].value,
            ]
        )
        summary[name] = {
            "TP": pins["TP"][name].dx,
            "ELS_c_max": hi[q].value,
            "ELS_c_min": lo[q].value,
        }
    return rows, summary


# --------------------------------------------------------------------------- comparison


@dataclass
class Quantity:
    label: str
    unit: str
    value: float
    state: str
    combination: str
    where: str


def _max_over_states(
    vd: VariantData51ter,
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
    vd: VariantData51ter,
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


def without_tangential(f: dict[str, FloatArray]) -> dict[str, FloatArray]:
    """P51: the tangential berthing component left out (its unit cases set to zero)."""
    return {
        c: (np.zeros_like(a) if c.startswith(TANGENTIAL) else a) for c, a in f.items()
    }


def _beam_nodes(vd: VariantData51ter, group: str) -> list[int]:
    return sorted(
        {n for e in vd.model.elements.values() if e.group == group for n in e.nodes},
        key=lambda n: float(vd.model.coords[n - 1][0]),
    )


def deflection_arrays(
    vd: VariantData51ter, span: str
) -> tuple[dict[str, FloatArray], list[str], float]:
    """uz relative to the chord of the supports of each main beam of a long span, or,
    for the cantilever, uz of the tip minus that of the pin of C2 of P5 and the
    rotation of the chord of PT5 (P51); per node; and the length L of the ratio
    (L = 2 Lpf for the cantilever)."""
    rows: list[tuple[int, int, int, float]] = []
    where: list[str] = []
    m = vd.model
    for side in ("YM", "YP"):
        if span == "PF":
            nodes = _beam_nodes(vd, f"PP_PF_{side}")
            pt = _beam_nodes(vd, f"PP_PT{len(vd.g.footings)}_{side}")
            support, tip, back = nodes[0], nodes[-1], pt[0]
            xs, xt, xb = (float(m.coords[n - 1][0]) for n in (support, tip, back))
            # w = u_tip − u_s − (u_s − u_b) (xt − xs) / (xs − xb)
            t = (xt - xs) / (xs - xb)
            rows.append((tip, support, back, t))
            where.append(f"PP_PF_{side} X = {geo(xt)}")
        else:
            nodes = _beam_nodes(vd, f"PP_{span}_{side}")
            first, last = nodes[0], nodes[-1]
            x0 = float(m.coords[first - 1][0])
            x1 = float(m.coords[last - 1][0])
            for n in nodes:
                t = (float(m.coords[n - 1][0]) - x0) / (x1 - x0)
                rows.append((n, first, last, -1.0 - t))
                where.append(f"PP_{span}_{side} X = {geo(m.coords[n - 1][0])}")

    def value(d: dict[int, FloatArray], n: int, a: int, b: int, t: float) -> float:
        if t >= 0.0:  # porte-à-faux : a = appui, b = début de PT5
            return float(d[n][2] - d[a][2] - (d[a][2] - d[b][2]) * t)
        s = -1.0 - t
        return float(d[n][2] - ((1 - s) * d[a][2] + s * d[b][2]))

    f = {c: np.array([value(vd.tables.depl[c], *r) for r in rows]) for c in vd.cases}
    length = 2.0 * vd.variant.cantilever if span == "PF" else span_length(vd.g, span)
    return f, where, length


def comparison(vd: VariantData51ter) -> dict[str, Quantity]:  # noqa: PLR0915
    out: dict[str, Quantity] = {}

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
                vd, _arrays(vd, rows, 4), sign=1, where=where, scale=KN, absolute=True
            ),
        )
        put(
            f"{prefix}_Mz",
            f"{prefix} Mz extrême en valeur absolue, signé (MFZ)",
            "kN·m",
            _max_over_states(
                vd, _arrays(vd, rows, 5), sign=1, where=where, scale=KN, absolute=True
            ),
        )
        if fam == "POUTRES_PRINC":
            n_arr = _arrays(vd, rows, 0)
            put(
                "PP_N_min",
                "PP N min",
                "kN",
                _max_over_states(vd, n_arr, sign=-1, where=where, scale=KN),
            )
            put(
                "PP_N_max",
                "PP N max",
                "kN",
                _max_over_states(vd, n_arr, sign=1, where=where, scale=KN),
            )
            put(
                "PP_N_abs",
                "PP |N| max, signé",
                "kN",
                _max_over_states(
                    vd, n_arr, sign=1, where=where, scale=KN, absolute=True
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
                    scale=KN,
                    absolute=True,
                ),
            )
        put(
            f"{prefix}_V",
            f"{prefix} V max (√(VY² + VZ²))",
            "kN",
            _resultant_over_states(
                vd, _arrays(vd, rows, 1), _arrays(vd, rows, 2), where, KN
            ),
        )
    # Flèches (P51) : ELS fréquent avec la composante tangentielle d'accostage, ELS
    # caractéristique sans ; actions variables seules ; L/flèche.
    spans = [s.name for s in vd.g.spans if s.nature == "grande"] + ["PF"]
    for span in spans:
        f, where, length = deflection_arrays(vd, span)
        for state, tag, ff in (
            ("ELS_frequent", "F", f),
            ("ELS_caracteristique", "C", without_tangential(f)),
        ):
            q = _max_over_states(
                vd,
                ff,
                sign=1,
                where=where,
                scale=MM,
                states=(state,),
                without=("G",),
                absolute=True,
            )
            put(
                f"FL_{span}_{tag}",
                f"flèche {span} extrême signée, {state}, variables seules (< 0 vers le bas)"
                + (
                    ", sans composante tangentielle d'accostage (P51)"
                    if tag == "C"
                    else ""
                ),
                "mm",
                q,
            )
            ratio = Quantity(
                "",
                "",
                length / abs(q.value / MM) if q.value else math.inf,
                q.state,
                q.combination,
                q.where,
            )
            put(
                f"LF_{span}_{tag}",
                f"L/flèche {span}, {state}"
                + (" (L = 2 Lpf)" if span == "PF" else f" (L = {length:.3f} m)"),
                "-",
                ratio,
            )
    # Appuis à axe.
    axes = [a.name for a in vd.g.axes]
    pins = {c: pin_results(vd, c) for c in vd.cases}
    fz = {c: np.array([-pins[c][a].force[2] for a in axes]) for c in vd.cases}
    put(
        "AXE_Fz_min",
        "appuis à axe Fz min (< 0 : traction des tiges, soulèvement)",
        "kN",
        _max_over_states(vd, fz, sign=-1, where=axes, scale=KN),
    )
    put(
        "AXE_Fz_max",
        "appuis à axe Fz max (compression)",
        "kN",
        _max_over_states(vd, fz, sign=1, where=axes, scale=KN),
    )
    fy = {c: np.array([pins[c][a].force[1] for a in axes]) for c in vd.cases}
    put(
        "AXE_Fy_max",
        "appuis à axe Fy extrême en valeur absolue, signé (appuis YP)",
        "kN",
        _max_over_states(vd, fy, sign=1, where=axes, scale=KN, absolute=True),
    )
    sx = {c: np.array([pins[c][a].slide_x for a in axes]) for c in vd.cases}
    put(
        "AXE_dx",
        "appuis à axe glissement en X extrême signé (trou oblong)",
        "mm",
        _max_over_states(vd, sx, sign=1, where=axes, scale=MM, absolute=True),
    )
    put(
        "AXE_dx_ELS_C",
        "appuis à axe glissement en X extrême signé, ELS caractéristique",
        "mm",
        _max_over_states(
            vd,
            sx,
            sign=1,
            where=axes,
            scale=MM,
            states=("ELS_caracteristique",),
            absolute=True,
        ),
    )
    p5 = [a for a in axes if a.startswith(f"P{len(vd.g.footings)}C2")]
    dx5 = {c: np.array([pins[c][a].dx for a in p5]) for c in vd.cases}
    put(
        "DX_P5",
        f"DX de l'axe C2 de P{len(vd.g.footings)} extrême signé, ELS caractéristique",
        "mm",
        _max_over_states(
            vd,
            dx5,
            sign=1,
            where=p5,
            scale=MM,
            states=("ELS_caracteristique",),
            absolute=True,
        ),
    )
    # Piles.
    ends = pile_ends(vd)
    rows = [(e, n) for _, _, _, n, e in ends]
    where = [f"{p} {pl} {pos}" for p, pl, pos, _, _ in ends]
    put(
        "PILE_N_min",
        "piles N min (compression)",
        "kN",
        _max_over_states(vd, _arrays(vd, rows, 0), sign=-1, where=where, scale=KN),
    )
    put(
        "PILE_N_max",
        "piles N max (traction maximale si > 0)",
        "kN",
        _max_over_states(vd, _arrays(vd, rows, 0), sign=1, where=where, scale=KN),
    )
    for pos, key in (("tete", "PILE_M_tete"), ("pied", "PILE_M_pied")):
        sub = [(e, n) for _, _, ps, n, e in ends if ps == pos]
        wsub = [f"{p} {pl} {ps}" for p, pl, ps, _, _ in ends if ps == pos]
        put(
            key,
            f"piles M en {pos} (√(MFY² + MFZ²))",
            "kN·m",
            _resultant_over_states(
                vd, _arrays(vd, sub, 4), _arrays(vd, sub, 5), wsub, KN
            ),
        )
    put(
        "PILE_V",
        "piles V max (√(VY² + VZ²))",
        "kN",
        _resultant_over_states(
            vd, _arrays(vd, rows, 1), _arrays(vd, rows, 2), where, KN
        ),
    )
    # Angles de l'anneau.
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
                scale=KN,
                absolute=True,
            ),
        )
    # Équilibre et ancrage des palées.
    totals = pier_totals(vd)
    piers = list(vd.g.piers)
    for key, states, lab in (
        ("SEM_SRz_min_ELU", ("ELU_fondamental", "ELU_accidentel"), "ELU"),
        ("SEM_SRz_min_ELS_C", ("ELS_caracteristique",), "ELS caractéristique"),
    ):
        put(
            key,
            f"palées ΣRz min du sol, {lab} (> 0 vers le haut), palée la plus défavorable",
            "kN",
            _max_over_states(vd, totals, sign=-1, where=piers, scale=KN, states=states),
        )
    q = out["SEM_SRz_min_ELU"]
    put(
        "LEST_manquant",
        "lest manquant = max(0 ; −ΣRz min ELU) / 0,9, palée la plus défavorable",
        "kN",
        Quantity("", "", max(0.0, -q.value) / 0.9, q.state, q.combination, q.where),
    )
    for key, state, lab in (
        ("ANCRAGE_ELU", "ELU_fondamental", "ELU fondamental"),
        ("ANCRAGE_ELS_C", "ELS_caracteristique", "ELS caractéristique"),
    ):
        g = _max_over_states(
            vd, totals, sign=-1, where=piers, scale=KN, states=(state,)
        )
        put(
            key,
            f"effort d'ancrage requis maximal sur les palées, {lab} (palée dans le lieu)",
            "kN",
            Quantity("", "", max(0.0, -g.value), g.state, g.combination, g.where),
        )
    # Culée.
    supports = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    where = ["axe YM", "axe YP"]
    for comp, key in ((0, "CULEE_RX"), (1, "CULEE_RY"), (2, "CULEE_RZ")):
        f = {
            c: np.array([vd.tables.reac[c][n][comp] for n in supports])
            for c in vd.cases
        }
        put(
            key,
            f"culée R{'XYZ'[comp]} extrême signé (un axe)",
            "kN",
            _max_over_states(vd, f, sign=1, where=where, scale=KN, absolute=True),
        )
    rx_total = {
        c: np.array([sum(vd.tables.reac[c][n][0] for n in supports)]) for c in vd.cases
    }
    put(
        "CULEE_RX_ELU",
        "culée ΣRX (deux axes) extrême signé, ELU fondamental",
        "kN",
        _max_over_states(
            vd,
            rx_total,
            sign=1,
            where=["culée"],
            scale=KN,
            states=("ELU_fondamental",),
            absolute=True,
        ),
    )
    return out


def corners(vd: VariantData51ter) -> list[tuple[int, int]]:
    out = []
    caps = {
        vd.model.group_nodes[f"TP_{p}_{c}_{s}_B"][0]
        for p in vd.g.piers
        for c in ("C1", "C2")
        for s in ("YM", "YP")
    }
    ties = {
        vd.model.group_nodes[f"LG_{p}_{c}_{s}_A"][0]
        for p in vd.g.piers
        for c in ("C1", "C2")
        for s in ("YM", "YP")
    }
    for e in sorted(vd.model.elements.values(), key=lambda e: e.number):
        if e.family in ("CHEVETRES", "LONGRINES"):
            out += [(e.number, n) for n in e.nodes if n in caps | ties]
    return out


def comparison_columns(g: Geometry51ter) -> tuple[str, ...]:
    spans = [s.name for s in g.spans if s.nature == "grande"] + ["PF"]
    return (
        "PP_My",
        "PP_Mz",
        "PP_N_min",
        "PP_N_max",
        "PP_N_abs",
        "PP_V",
        *(f"{k}_{s}_{t}" for s in spans for t in ("F", "C") for k in ("FL", "LF")),
        "AXE_Fz_min",
        "AXE_Fz_max",
        "AXE_Fy_max",
        "AXE_dx",
        "AXE_dx_ELS_C",
        "DX_P5",
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
        "ANCRAGE_ELU",
        "ANCRAGE_ELS_C",
        "CULEE_RX",
        "CULEE_RY",
        "CULEE_RZ",
        "CULEE_RX_ELU",
    )


# --------------------------------------------------------------------------- criteria


def criterion_resultants(vd: VariantData51ter) -> dict[str, Any]:
    """Criterion 3: declared resultant of the deck cases = width × loaded length ×
    1 kPa, per module and total; gap to the nominal length reported."""
    loads = applied_loads(vd.vals, vd.g)
    out: dict[str, Any] = {}
    for base, width in (
        ("HU_PLATELAGE", vd.vals.width_planks),
        ("HD_TABLIER", vd.vals.width_deck_top),
    ):
        worst = 0.0
        for module, spans in vd.g.modules().items():
            length = sum(span_length(vd.g, s) for s in spans)
            expected = width * length * 1000.0
            got = abs(loads[f"{base}_{module}"]["DZ"])
            worst = max(worst, abs(got - expected) / expected)
        length = sum(span_length(vd.g, s.name) for s in vd.g.spans)
        got = abs(loads[base]["DZ"])
        out[base] = {
            "ecart_relatif_max_modules": worst,
            "ecart_relatif_total": abs(got - width * length * 1000.0)
            / (width * length * 1000.0),
            "longueur_chargee_m": length,
            "longueur_nominale_m": vd.g.length,
            "ecart_relatif_longueur_nominale": abs(got - width * vd.g.length * 1000.0)
            / (width * vd.g.length * 1000.0),
        }
    return out


def criterion_linearity(vd: VariantData51ter) -> dict[str, float]:
    """Criterion 4: the total case against the sum of its modules (DEPL)."""
    out = {}
    for base in SPLIT:
        nodes = sorted(vd.tables.depl[base])
        total = np.array([vd.tables.depl[base][n][:6] for n in nodes])
        parts = sum(
            np.array([vd.tables.depl[f"{base}_{m}"][n][:6] for n in nodes])
            for m in vd.g.modules()
        )
        diff = np.nan_to_num(np.abs(total - parts))
        out[base] = float(diff.max() / np.nanmax(np.abs(total)))
    return out


def criterion_am1(vd: VariantData51ter) -> dict[str, Any]:
    """Criterion 5: AM1 alone, ΣRX abutment + ΣRX piers = applied force."""
    supports = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    rx_piers = pier_totals(vd, component=0)
    loads = applied_loads(vd.vals, vd.g)
    out: dict[str, Any] = {}
    for name in ("AM1_+X", "AM1_-X"):
        coefs = vd.ev[name].coefficients
        applied = sum(c * loads[k]["DX"] for k, c in coefs.items())
        abut = sum(
            c * sum(vd.tables.reac[k][n][0] for n in supports) for k, c in coefs.items()
        )
        piers = sum(c * float(rx_piers[k].sum()) for k, c in coefs.items())
        out[name] = {
            "force_appliquee_N": applied,
            "SRX_culee_N": abut,
            "SRX_palees_N": piers,
            "ecart_palees_relatif": abs(piers) / abs(applied),
            "ecart_culee_relatif": abs(abut + applied) / abs(applied),
            "reussi": abs(piers) / abs(applied) <= 1e-6
            and abs(abut + applied) / abs(applied) <= 1e-6,
        }
    return out


def criterion_tp(vd: VariantData51ter) -> dict[str, Any]:
    """Criterion 6: DX of the pin of C2 of P5 under TP against α·ΔT·X."""
    pins = pin_results(vd, "TP")
    n = len(vd.g.footings)
    x = vd.variant.stations[-1] + vd.variant.cap_spacing
    expected = vd.vals.alpha_alu * vd.vals.t_plus * x
    out: dict[str, Any] = {}
    for side in ("YM", "YP"):
        got = pins[f"P{n}C2_{side}"].dx
        out[side] = {
            "DX_m": got,
            "attendu_m": expected,
            "ecart_relatif": abs(got - expected) / expected,
        }
    out["reussi"] = all(
        v["ecart_relatif"] <= 0.01 for k, v in out.items() if k in ("YM", "YP")
    )
    return out


def criterion_pins(vd: VariantData51ter) -> dict[str, float]:
    """Criterion 7: Σ REAC_NODA of the ears and the cap node of each pin; X of the
    force on the cap beam; Y on side YM; relative to max |F| (absolute ≤ 1 N when
    max |F| ≤ 1 N)."""
    m = vd.model
    worst = {
        "somme": 0.0,
        "Fx": 0.0,
        "Fy_YM": 0.0,
        "cas_absolus": 0.0,
        "absolu_max_N": 0.0,
    }
    for case in vd.cases:
        reac = vd.tables.reac[case]
        pins = pin_results(vd, case)
        big = max(float(np.abs(r.force).max()) for r in pins.values())
        absolute = big <= 1.0
        scale = 1.0 if absolute else big
        if absolute:
            worst["cas_absolus"] += 1
        for a in vd.g.axes:
            nodes = [
                m.group_nodes[a.ear_group(k)][0] for k in range(1, len(a.ears) + 1)
            ]
            nodes.append(m.group_nodes[a.cap_group][0])
            total = sum(np.array(reac[n][:3]) for n in nodes)
            vals = {
                "somme": float(np.abs(total).max()),
                "Fx": abs(float(pins[a.name].force[0])),
                "Fy_YM": 0.0 if a.blocks_y else abs(float(pins[a.name].force[1])),
            }
            for k, v in vals.items():
                if absolute:
                    worst["absolu_max_N"] = max(worst["absolu_max_N"], v)
                else:
                    worst[k] = max(worst[k], v / scale)
    return worst


def recombination_places(
    vd: VariantData51ter,
) -> list[tuple[str, dict[str, FloatArray], list[str]]]:
    places: list[tuple[str, dict[str, FloatArray], list[str]]] = []
    rows = _rows_of(vd, ("POUTRES_PRINC",))
    places.append(
        ("MFY poutres principales", _arrays(vd, rows, 4), [f"{e}/{n}" for e, n in rows])
    )
    prow = [(e, n) for _, _, _, n, e in pile_ends(vd)]
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
    totals = pier_totals(vd)
    for q, pier in enumerate(vd.g.piers):
        places.append(
            (f"ΣRz {pier}", {c: totals[c][q : q + 1] for c in vd.cases}, [pier])
        )
    supports = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    places.append(
        (
            "RX culée",
            {
                c: np.array([vd.tables.reac[c][n][0] for n in supports])
                for c in vd.cases
            },
            ["YM", "YP"],
        )
    )
    return places


def criterion_recombination(out: Path, vd: VariantData51ter) -> list[dict[str, Any]]:
    """Criterion 8: decomposition against (a) the delivered recombiner.py and (b) the
    explicit enumeration of every pattern, at the governing place."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51ter", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    checks = []
    for label, f, where in recombination_places(vd):
        for state in ("ELU_fondamental", "ELU_accidentel"):
            for sign in (1.0, -1.0):
                ext = envelope(vd.bs, vd.ev, f, state, sign=sign)
                q = int(np.argmax(sign * ext.value))
                values_q = {c: float(f[c][q]) for c in vd.cases}
                brute = rec.extremes(
                    [r for r in rules if r[0] == state], events_csv, values_q
                )[state]
                reference = brute[0] if sign > 0 else brute[2]
                explicit = [
                    brute_force(b, vd.ev, values_q, sign)
                    for b in vd.bs
                    if b.state == state
                ]
                exhaustive = max(explicit) if sign > 0 else min(explicit)
                value = float(ext.value[q])
                rel = abs(value - reference) / max(abs(reference), 1e-300)
                rel2 = abs(value - exhaustive) / max(abs(exhaustive), 1e-300)
                checks.append(
                    {
                        "grandeur": label,
                        "etat_limite": state,
                        "extreme": "max" if sign > 0 else "min",
                        "lieu": where[q],
                        "decomposition": value,
                        "recombiner": reference,
                        "enumeration_explicite": exhaustive,
                        "ecart_relatif_recombiner": rel,
                        "ecart_relatif_explicite": rel2,
                        "combinaison_decomposition": governing(vd.bs, vd.ev, ext, q)[0],
                        "combinaison_recombiner": brute[1] if sign > 0 else brute[3],
                        "reussi": rel <= 1e-9 and rel2 <= 1e-9,
                    }
                )
    return checks


def criterion_counts(
    out: Path, vd: VariantData51ter, *, enumerate_rules: bool
) -> dict[str, Any]:
    """Criterion 9 and 10: counts by formula, by recombiner.py and by enumeration of
    the rules without duplicates; exclusions in the rules."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51ter", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    formula = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    result: dict[str, Any] = {
        "formule": formula,
        "formule_total": sum(formula.values()),
        "recombiner": rec.count(rules),
        "dispositions_formule": expanded,
        "dispositions_total": sum(expanded.values()),
        "dispositions_recombiner": rec.count(rules, events_csv),
        "exclusions": check_exclusions(vd.bs, vd.ev),
    }
    ok = (
        result["recombiner"] == formula
        and result["dispositions_recombiner"] == expanded
    )
    if enumerate_rules:
        seen = set()
        total = 0
        for b in vd.bs:
            for choice in itertools.product(*(s.options for s in b.slots)):
                key = (b.state, *sorted((n, f) for n, f in choice if n is not None))
                seen.add(key)
                total += 1
        result["enumerees"] = total
        result["distinctes"] = len(seen)
        ok = ok and total == len(seen) == sum(formula.values())
    result["reussi"] = ok and not result["exclusions"]
    return result


# --------------------------------------------------------------------------- exports


def export_variant(
    vd: VariantData51ter,
    state: dict[str, Any],
    out: Path,
    *,
    source: str | None = None,
    forces_csv: bool = True,
) -> tuple[dict[str, int], dict[str, Any]]:
    """The files of lot 51 ter for one variant. Lot 51 quater: `source` replaces the
    source line of the headers, `forces_csv=False` leaves out efforts_elementaires.csv
    (written for one variant only)."""
    out.mkdir(parents=True, exist_ok=True)
    src = source if source is not None else source_line(vd, state)
    axes = axes_text(vd)
    m = vd.model
    lv = vd.g.levels
    files: dict[str, int] = {}
    cases_text = "Cas : " + " ; ".join(f"{c} = {case_label(c)}" for c in vd.cases) + "."
    files["noeuds.csv"] = write(
        out / "noeuds.csv",
        f"{src} Unités : m. {axes} noeud = numéro MED (à partir de 1) ; groupes du maillage qui le contiennent.",
        ["noeud", "x", "y", "z", "groupes"],
        [
            [n, *(geo(c) for c in m.coords[n - 1]), "|".join(m.node_groups[n])]
            for n in range(1, len(m.coords) + 1)
        ],
    )
    files["elements.csv"] = write(
        out / "elements.csv",
        f"{src} Unités : m. {axes} element = numéro de la maille SEG2 (MED, à partir de 1) ; "
        "travee_ou_palee : T1 à T5 (grandes travées), PT1 à PT5 (petites travées), PF (porte-à-faux), "
        "P1 à P5 (palées). Repère local (U4.42.01) : x_l du nœud 1 au nœud 2 ; VECT_Z (0, 0, 1) pour les "
        "barres horizontales ; VECT_Y (1, 0, 0) pour les piles. Liaisons : nœuds distincts liés dans le "
        f".comm ; appuis à axe (P44, P54) : axe non maillé, point P à Z = {lv['axe_appui']}, relations LIAISON_DDL.",
        [
            "element",
            "type",
            "noeud1",
            "noeud2",
            "famille",
            "groupe",
            "travee_ou_palee",
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
        f"{src} Unités : m. {axes} Membre : barre entre deux nœuds de raccord ; début = extrémité de "
        "plus petite coordonnée selon l'axe de la famille.",
        [
            "membre",
            "libelle",
            "famille",
            "groupe",
            "travee_ou_palee",
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
    if forces_csv:
        files["efforts_elementaires.csv"] = write(
            out / "efforts_elementaires.csv",
            f"{src} Unités : N, N·m, m. EFGE_ELNO (POU_D_T) aux deux extrémités de chaque élément de barre, "
            "repère local de elements.csv ; convention Code_Aster brute : N > 0 en traction. "
            + cases_text,
            [
                "cas",
                "element",
                "membre",
                "groupe",
                "travee_ou_palee",
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
        (
            [c, n, *(float(x) for x in vd.tables.depl[c][n])]
            for c in vd.cases
            for n in sorted(vd.tables.depl[c])
        ),
    )
    files["reactions_elementaires.csv"] = write(
        out / "reactions_elementaires.csv",
        f"{src} Unités : N, N·m, m. Effort de l'appui sur la structure, repère global : axes de la culée "
        "(P58, REAC_NODA, moments sans objet) ; ressorts de chaque semelle (SOL_Pk) : Σ des forces du sol "
        "−k·u, moment par rapport au centre de la semelle. Les appuis à axe sont dans appuis_axes.csv.",
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
    tally = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        f"{src} Jeu B′ révisé et ELU accidentel (P49, P56, P57, P59) en règles : une combinaison = une option "
        "par emplacement d'une branche ; option = « événement×facteur » (evenements.csv) ou ∅. Q et QD : "
        "dispositions défavorables par modules (lignes d'influence, colonne portee de evenements.csv). "
        "Effectifs en règles : "
        + ", ".join(f"{s} {n}" for s, n in tally.items())
        + f", total {sum(tally.values())} ; avec les 63 dispositions de Q et de QD comptées : "
        + ", ".join(f"{s} {n}" for s, n in expanded.items())
        + f", total {sum(expanded.values())}. "
        "recombiner.py les énumère.",
        [
            "etat_limite",
            "branche",
            "emplacement",
            "action",
            "nombre_options",
            "effectif_branche",
            "effectif_dispositions",
            "options",
        ],
        rule_rows(vd.bs, vd.ev),
    )
    files["evenements.csv"] = write(
        out / "evenements.csv",
        f"{src} Événements des actions (valeurs caractéristiques) : coefficient appliqué au cas élémentaire "
        "unitaire (kN sur 1 kN, kN/m sur 1 kN/m, kPa sur 1 kPa). portee : « fixe » ou « module Mk » (Q et QD, "
        "chaque module chargé ou non, choix défavorable). Houle (P56) : HU, HD caractéristiques, HU_F "
        "fréquent ; G_DEJ_090 = 0,9 × (G1 + G2) + DEJ, G_DEJ_100 = G1 + G2 + DEJ (P49).",
        ["action", "evenement", "portee", "cas", "coefficient"],
        event_rows(vd.ev),
    )
    files["charges.csv"] = write(
        out / "charges.csv",
        f"{src} Unités : N/m (répartie), N/m2 (surfacique), N (ponctuelle), m/s2 (pesanteur), K (température), "
        "m. Charges lues dans le .comm, repère global.",
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
        load_rows(vd),  # type: ignore[arg-type]
    )
    files["sections.csv"] = write(
        out / "sections.csv",
        f"{src} Unités : m, m2, m4, N/m ; AY, AZ : coefficients de cisaillement (A/Av). AFFE_CARA_ELEM : "
        "mots-clés affectés, puis caractéristiques que Code_Aster en déduit (U4.42.01), recalculées.",
        ["section", "groupes", "type", "cara", "valeur", "unite", "origine"],
        section_rows(vd.comm),
    )
    files["appuis_axes.csv"] = write(
        out / "appuis_axes.csv",
        f"{src} Unités : N, m, rad. Appuis articulés à axe (P44, P54), deux lignes par palée (chevêtres C1 et "
        "C2), rives YM (Y libre) et YP (Y bloqué) ; x, y, z : point de l'axe. Par appui et par cas : Fx, Fy = "
        "effort de l'axe sur le chevêtre, repère global ; Fz compté positif vers le bas (Fz < 0 : traction des "
        "tiges, soulèvement) ; dx_axe : déplacement en X de l'axe porté par l'oreille 1 ; glissement_x : le "
        "même moins celui porté par le nœud du chevêtre ; rotations relatives autour de Y.",
        [
            "cas",
            "palee",
            "chevetre",
            "rive",
            "oreilles",
            "x",
            "y",
            "z",
            "Fx",
            "Fy",
            "Fz",
            "dx_axe",
            "glissement_x",
            "rotation_y_oreille1",
            "rotation_y_oreille2",
            "rotation_y_oreille2_moins_1",
        ],
        pin_rows(vd),
    )
    files["piles.csv"] = write(
        out / "piles.csv",
        f"{src} Unités : N, N·m. Torseurs EFGE_ELNO en tête (+{lv['tete_piles']}) et en pied (dessus de la "
        "semelle de la palée) de chaque pile, repère local x_l = +Z, y_l = +X, z_l = +Y ; N > 0 en traction.",
        ["cas", "palee", "pile", "position", "noeud", "element", "z", *EFGE],
        pile_rows(vd),
    )
    pr, pier_summary = pier_rows(vd)
    files["palee_equilibre.csv"] = write(
        out / "palee_equilibre.csv",
        f"{src} Unités : m, m3, N. Une ligne par palée : volume de béton modélisé (angles de l'anneau comptés "
        "une fois), poids, poids déjaugé, ΣRz min du sol (> 0 vers le haut) par état limite avec sa "
        "combinaison, ressorts tendus dans la combinaison de l'ELU fondamental (sol linéaire, traction "
        "admise, P19), lest manquant = max(0 ; −ΣRz min ELU) / 0,9.",
        [
            "palee",
            "x_c1",
            "hauteur_piles",
            "z_plan_moyen_semelle",
            "volume_beton",
            "poids_beton",
            "poids_deja",
            *(x for s in STATES for x in (f"SRz_min_{s}", f"combinaison_{s}")),
            "ressorts_traction_ELU_fondamental",
            "lest_manquant",
        ],
        pr,
    )
    ar, anchor_summary = anchoring_rows(vd)
    files["ancrage.csv"] = write(
        out / "ancrage.csv",
        f"{src} Unités : N. Ancrage que demanderait chaque palée (aucun ancrage modélisé : le soulèvement se "
        "constate) : ΣRz min du sol, effort d'ancrage requis = max(0 ; −ΣRz min), part de la houle dans la "
        "combinaison gouvernante, traction maximale de chaque pile en tête et en pied ; ELU fondamental et "
        "ELS caractéristique.",
        [
            "palee",
            "etat_limite",
            "grandeur",
            "lieu",
            "valeur",
            "unite",
            "combinaison",
            "detail",
        ],
        ar,
    )
    cr, abut_summary = abutment_rows(vd)
    files["culee.csv"] = write(
        out / "culee.csv",
        f"{src} Unités : N. Réactions des axes de la culée (effort de l'appui sur le tablier, repère global, "
        "P58 : YP bloqué en X, Y, Z ; YM en X, Z) : max et min de RX, RY, RZ avec leur combinaison, résultante "
        "horizontale maximale ; RZ_min < 0 : soulèvement.",
        ["appui", "etat_limite", "grandeur", "valeur", "unite", "combinaison"],
        cr,
    )
    files["chaine_x.csv"] = write(
        out / "chaine_x.csv",
        f"{src} Unités : N, m. Effort normal (N > 0 traction) de chaque poutre principale au droit de chaque "
        "ligne d'appui (culée, chevêtres C1 et C2 des palées), élément de la grande travée (ou de PT5) à "
        "l'oreille, ELU fondamental, max et min avec leur combinaison.",
        [
            "ligne",
            "rive",
            "groupe",
            "element",
            "noeud",
            "x",
            "N_max",
            "combinaison_max",
            "N_min",
            "combinaison_min",
        ],
        chain_rows(vd),
    )
    dr, dx_summary = axis_displacement_rows(vd)
    files["deplacements_axes.csv"] = write(
        out / "deplacements_axes.csv",
        f"{src} Unités : m. Pour chaque axe d'appui de palée : DX de l'axe (porté par l'oreille 1) sous TP et "
        "TM seuls, DX max et min à l'ELS caractéristique avec leur combinaison ; glissement relatif au "
        "chevêtre sous TP, TM et ses extrêmes ELS caractéristique (dimensionnement des trous oblongs).",
        [
            "palee",
            "chevetre",
            "rive",
            "x",
            "DX_TP",
            "DX_TM",
            "DX_max_ELS_c",
            "combinaison_max",
            "DX_min_ELS_c",
            "combinaison_min",
            "glissement_TP",
            "glissement_TM",
            "glissement_max_ELS_c",
            "glissement_min_ELS_c",
        ],
        dr,
    )
    shutil.copyfile(
        Path(__file__).resolve().parent / "scripts" / "recombiner_lot51ter.py",
        out / "recombiner.py",
    )
    return files, {
        "palees": pier_summary,
        "ancrage": anchor_summary,
        "culee": abut_summary,
        "deplacements_axes": dx_summary,
    }


def step_exports(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    root = ctx.results_dir / LOT / "exports"
    root.mkdir(parents=True, exist_ok=True)
    summary_path = root / "synthese.json"
    summary: dict[str, Any] = (
        json.loads(summary_path.read_text("utf-8")) if summary_path.is_file() else {}
    )
    for code in codes:
        execution = state.get(code, {}).get("execution", {})
        if "execution_dir" not in execution:
            summary[code] = {
                "statut": "non calculée",
                "message": str(execution.get("message", "")),
            }
            print(f"{code} : non calculée")
            continue
        vd = load_variant(ctx, code, state)
        out = root / code
        files, details = export_variant(vd, state, out)
        quantities = comparison(vd)
        info: dict[str, Any] = {
            "statut": "calculée",
            "fichiers": files,
            "effectifs": counts(vd.bs),
            "effectifs_dispositions": expanded_counts(vd.bs, vd.ev),
            "volumes_beton_m3": concrete_volumes(vd.vals, vd.g),
            "cotes_m_ngf": vd.g.levels,
            "details": details,
            "comparaison": {k: q.__dict__ for k, q in quantities.items()},
            "critere_3_resultantes": criterion_resultants(vd),
            "critere_5_AM1": criterion_am1(vd),
            "critere_6_TP": criterion_tp(vd),
        }
        if code == "B10":
            info["critere_4_linearite"] = criterion_linearity(vd)
            info["critere_7_appuis_axe"] = criterion_pins(vd)
            info["critere_8_recombinaison"] = criterion_recombination(out, vd)
            info["critere_9_10_effectifs"] = criterion_counts(
                out, vd, enumerate_rules=True
            )
        summary[code] = info
        summary_path.write_text(
            json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
            "utf-8",
        )
        print(f"{code} : exports écrits ({sum(files.values())} lignes)")
    write_comparison(root, summary)


def write_comparison(root: Path, summary: dict[str, Any]) -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    columns = comparison_columns(g)
    labels: dict[str, str] = {}
    main_rows: list[list[Any]] = []
    detail_rows: list[list[Any]] = []
    for code, v in variants().items():
        info = summary.get(code)
        if info is None or info.get("statut") != "calculée":
            main_rows.append(
                [code, v.description, "non calculée", *([""] * len(columns))]
            )
            continue
        comp = info["comparaison"]
        main_rows.append(
            [
                code,
                v.description,
                "calculée",
                *(float(comp[c]["value"]) for c in columns),
            ]
        )
        for key in columns:
            q = comp[key]
            labels[key] = f"{q['label']} [{q['unit']}]"
            detail_rows.append(
                [
                    code,
                    key,
                    q["label"],
                    q["unit"],
                    float(q["value"]),
                    q["state"],
                    q["combination"],
                    q["where"],
                ]
            )
    header = (
        "PONTONS-ALU-01, lot 51 ter : comparaison des variantes (ponton intégral). Valeurs : enveloppes du jeu B′ "
        "révisé (ELU fondamental, ELS caractéristique, ELS fréquent) et de l'ELU accidentel, avec DEJ (P49), la "
        "houle P56 et P57, sauf les flèches (P51 : ELS fréquent, ELS caractéristique sans la composante "
        "tangentielle d'accostage ; actions variables seules ; grandes travées relatives à la corde, "
        "porte-à-faux relatif à l'appui et à la corde de PT5, L = 2 Lpf) et les états limites nommés. Unités : "
        "kN, kN·m, mm. Colonnes : "
        + " ; ".join(f"{k} = {labels.get(k, k)}" for k in columns)
        + ". Détail : comparaison_variantes_detail.csv."
    )
    write(
        root / "comparaison_variantes.csv",
        header,
        ["variante", "description", "statut", *columns],
        main_rows,
    )
    write(
        root / "comparaison_variantes_detail.csv",
        "PONTONS-ALU-01, lot 51 ter : grandeurs de comparaison, état limite, combinaison et lieu qui gouvernent.",
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


def step_depot(ctx: ProjectContext, codes: list[str], target: Path | None) -> None:
    root = ctx.results_dir / LOT / "exports"
    dest = target or Path("/media/sf_partage/echanges/lot51ter/pontons_alu_01")
    dest.mkdir(parents=True, exist_ok=True)
    listed: list[str] = []
    for code in codes:
        folder = root / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue
            (dest / code).mkdir(exist_ok=True)
            shutil.copyfile(f, dest / code / f.name)
            listed.append(f"{code}/{f.name}")
    for extra in ("comparaison_variantes.csv", "comparaison_variantes_detail.csv"):
        shutil.copyfile(root / extra, dest / extra)
        listed.append(extra)
    from aster_expert.livrables.charges_salome import set_med_path  # noqa: PLC0415

    charges = ctx.results_dir / "livrables" / "charges_salome"
    if "B10" in codes and (charges / "charges.med").is_file():
        for name in ("charges.med", "charges_salome.py"):
            shutil.copyfile(charges / name, dest / "B10" / name)
            listed.append(f"B10/{name}")
        set_med_path(dest / "B10" / "charges_salome.py", dest / "B10" / "charges.med")
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(set(listed))]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    print(f"dépôt : {len(lines)} fichiers dans {dest}")


__all__ = [
    "PinResult",
    "VariantData51ter",
    "comparison",
    "comparison_columns",
    "criterion_counts",
    "criterion_recombination",
    "deflection_arrays",
    "export_variant",
    "load_variant",
    "pin_results",
    "read_run",
    "step_depot",
    "step_exports",
    "without_tangential",
    "THERMAL_CASES",
]
