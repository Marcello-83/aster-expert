# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 51 for PONTONS-ALU-01 (consigne § 6 and § 7), one folder per variant,
read from the tables Code_Aster printed during the run (never recomputed by a model of
the tool): unit 31 (EFGE_ELNO of every bar), 32 (DEPL of every node), 33 (REAC_NODA of
the supports), and the mesh read by `medcoupling` (trunk `dump_med`).

Formats of lot 50 ter (`;`, decimal point, UTF-8 without BOM, SI, one `#` line on top,
17 significant digits), plus `appuis_neoprene.csv` and `piles.csv`. The combinations are
given as rules (`combinaisons.csv`, `evenements.csv`), enumerated by `recombiner.py`:
listed one by one they would be 276 235 rows per variant (5 416 185 for E).

Bearing forces (P38): F = −K·(u_haut − u_bas), the force of the bearing on the deck, so
that Fz > 0 is a compression and Fz < 0 a retaining force (uplift, P38); variant M
(mechanical bearing, no stiffness): the same force read as the internal force at the
top of the support profile, which carries only the bearing (docs/essais_lot51.md,
criterion 4, checks both readings on R).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.controles.tables import TableIndex
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51 import (
    Branch,
    Event,
    branches,
    counts,
    envelope,
    event_rows,
    events,
    governing,
    magnitudes,
    resultant_max,
    rule_rows,
)
from pontons_alu_01.extensions_lot51 import tributary_areas
from pontons_alu_01.generation_lot51 import (
    all_cases,
    case_label,
    mechanical_cases,
    values,
)
from pontons_alu_01.geometrie_lot51 import Geometry51, geometry
from pontons_alu_01.lot50ter import (
    first_of,
    local_axes,
    names,
    occurrences,
    read_comm,
    section_properties,
)
from pontons_alu_01.variantes_lot51 import Variant, variants

FloatArray = NDArray[np.float64]
EFGE = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
DEPL = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")
REAC = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")
VERTICAL = ("SUPPORTS", "PILES")
"""Families oriented by VECT_Y (1, 0, 0); the others by VECT_Z (0, 0, 1)."""
FAMILY_AXIS = {
    "POUTRES_PRINC": 0,
    "MONTANTS": 1,
    "DIAGONALES": 0,
    "PANNES_SEC": 0,
    "SUPPORTS": 2,
    "CHEVETRES": 1,
    "LONGRINES": 0,
    "PILES": 2,
}
STATES_COMPARED = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
)
BEARINGS = tuple(f"{a}_{s}" for a in ("A1", "A2", "A3") for s in ("YM", "YP"))
PILES = ("C1_YM", "C1_YP", "C2_YM", "C2_YP")


# --------------------------------------------------------------------------- tables


def parse_tableau(text: str) -> list[tuple[list[str], list[dict[str, str]]]]:
    """Tables of an IMPR_TABLE file (FORMAT='TABLEAU'): one cell per header name, an
    absent value printed `-` (a node without rotation) read as empty."""
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("##ASTER"):
            i += 1
            continue
        cols = lines[i + 1].split()
        rows = []
        j = i + 2
        while j < len(lines) and lines[j].strip() and not lines[j].startswith("#"):
            cells = lines[j].split()
            if len(cells) != len(cols):
                message = (
                    f"ligne de table de {len(cells)} cellules pour {len(cols)} colonnes"
                )
                raise ValueError(message)
            rows.append(
                {c: ("" if x == "-" else x) for c, x in zip(cols, cells, strict=True)}
            )
            j += 1
        out.append((cols, rows))
        i = j
    return out


@dataclass
class RunTables:
    """Per case: EFGE_ELNO rows (cell, node) -> 6 values, DEPL per node, REAC per node."""

    efge: dict[str, dict[tuple[int, int], FloatArray]]
    depl: dict[str, dict[int, FloatArray]]
    reac: dict[str, dict[int, FloatArray]]
    order_to_case: dict[int, str]


def _float(cell: str) -> float:
    return float(cell) if cell else math.nan


def read_run(run_dir: Path, g: Geometry51) -> RunTables:
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


@dataclass
class Element:
    number: int
    """Code_Aster cell number (= MED number among the SEG2, 1-based)."""
    family: str
    group: str
    nodes: tuple[int, int]
    """1-based node numbers."""
    y_local: FloatArray
    z_local: FloatArray
    length: float
    section: str
    member: str = ""


@dataclass
class Member:
    name: str
    label: str
    family: str
    group: str
    section: str
    nodes: list[int]
    elements: list[int]
    abscissa: dict[int, float] = field(default_factory=dict)

    @property
    def length(self) -> float:
        return self.abscissa[self.nodes[-1]]


@dataclass
class Model:
    coords: FloatArray
    """Row n − 1 for node n."""
    node_groups: dict[int, list[str]]
    group_nodes: dict[str, list[int]]
    elements: dict[int, Element]
    springs: dict[str, tuple[int, int]]
    """Bearing -> (bottom node, top node)."""
    members: list[Member]
    joints: dict[int, list[str]]


def section_label(family: str, v: Variant) -> str:
    return {
        "POUTRES_PRINC": f"tube {v.beam_side_mm:g}x{v.beam_side_mm:g}x{v.beam_thickness_mm:g}",
        "MONTANTS": "tube 150x150x7",
        "DIAGONALES": "tube 150x150x7",
        "SUPPORTS": "tube 150x150x7",
        "PANNES_SEC": "tube 50x50x5",
        "CHEVETRES": "BA 0.40x0.40",
        "LONGRINES": "BA 0.40x0.40",
        "PILES": "pile D0.50",
    }[family]


def build_model(
    dump: dict[str, Any], tables: RunTables, g: Geometry51, v: Variant
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
    # Code_Aster numbers the SEG2 first, in the MED order: checked on every EFGE row.
    first_case = next(iter(tables.efge.values()))
    ends: dict[int, list[int]] = {}
    for cell, node in first_case:
        ends.setdefault(cell, []).append(node)
    elements: dict[int, Element] = {}
    for number, (n1, n2) in enumerate(seg_conn, start=1):
        if number not in group_of:
            continue  # SEG2 des bords et des coupes de la semelle (sans élément de barre)
        family = member_names[group_of[number]]
        if family == "NEOPRENES":
            continue
        if sorted(ends.get(number, [])) != sorted((n1 + 1, n2 + 1)):
            message = f"maille {number} : nœuds de la table ≠ nœuds du MED"
            raise ValueError(message)
        cara, vec = (
            ("VECT_Y", (1.0, 0.0, 0.0))
            if family in VERTICAL
            else ("VECT_Z", (0.0, 0.0, 1.0))
        )
        _, y, z = local_axes(coords[n1], coords[n2], cara, vec)
        elements[number] = Element(
            number=number,
            family=family,
            group=group_of[number],
            nodes=(n1 + 1, n2 + 1),
            y_local=y,
            z_local=z,
            length=float(np.linalg.norm(coords[n2] - coords[n1])),
            section=section_label(family, v),
        )
    springs = {}
    for b in BEARINGS:
        (bottom,) = group_nodes[f"NB_{b}"]
        (top,) = group_nodes[f"BR_{b}_A"]
        springs[b] = (bottom, top)
    joints: dict[int, list[str]] = {}
    for lk in g.links:
        for side in ("A", "B"):
            (n,) = group_nodes[f"{lk.name}_{side}"]
            joints.setdefault(n, []).append(lk.name)
    for name in ("APP_QUAI_YM", "APP_QUAI_YP", "APP_FIXE"):
        for n in group_nodes[name]:
            joints.setdefault(n, []).append(name)
    for b, (bottom, top) in springs.items():
        joints.setdefault(bottom, []).append(f"NEO_{b}")
        joints.setdefault(top, []).append(f"NEO_{b}")
    members = _members(coords, elements, joints)
    return Model(coords, node_groups, group_nodes, elements, springs, members, joints)


def _members(
    coords: FloatArray, elements: dict[int, Element], joints: dict[int, list[str]]
) -> list[Member]:
    """Each bar (group PP_T1_YM, MONT_T1_1 … CHEV_C1, PILE_C1_YM) cut at its connection
    nodes: nodes shared with another bar, nodes of a link, supports, bearings."""
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
        family = elems[0].family
        axis = FAMILY_AXIS[family]
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
            axis_name = "XYZ"[axis]
            member = Member(
                name=f"{group}_{k:02d}",
                label=f"{group} de {axis_name} = {_short(a)} à {_short(b)}",
                family=family,
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


def _short(v: float) -> str:
    text = f"{round(v, 6):.6f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


# --------------------------------------------------------------------------- CSV


def number(v: float) -> str:
    f = float(v)
    if math.isnan(f):
        return ""
    if f == 0.0:
        return "0.0"
    return repr(f)


def geo(v: float) -> float:
    """A coordinate without its binary noise (1 mm grid within 1e-6, else 12 decimals)."""
    f = float(v)
    snapped = round(f, 3)
    if abs(f - snapped) < 1e-6:
        return snapped + 0.0
    return round(f, 12) + 0.0


def write(
    path: Path, header: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]
) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(f"# {header}\n")
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [
                    number(float(x)) if isinstance(x, float | np.floating) else x
                    for x in row
                ]
            )
            count += 1
    return count


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- bearings


def bearing_forces(
    model: Model,
    tables: RunTables,
    v: Variant,
    k: tuple[float, float, float],
    case: str,
) -> dict[str, tuple[FloatArray, FloatArray]]:
    """Per bearing: (F on the deck, global; u_top − u_bottom)."""
    depl = tables.depl[case]
    out = {}
    for b, (bottom, top) in model.springs.items():
        du = depl[top][:3] - depl[bottom][:3]
        if v.bearings == "mecanique":
            force = profile_top_force(model, tables, b, case)
        else:
            force = -np.array(k) * du
        out[b] = (force, du)
    return out


def profile_top_force(
    model: Model, tables: RunTables, bearing: str, case: str
) -> FloatArray:
    """Force of the bearing on the deck from the internal force at the top of the
    support profile: at the end node of an element, EFGE = the force of the rest of
    the structure on the element, in local axes; the bearing pushes the profile with
    it, and the deck with its opposite."""
    bottom, _ = model.springs[bearing]
    (e,) = [
        el
        for el in model.elements.values()
        if el.family == "SUPPORTS" and bottom in el.nodes
    ]
    values = tables.efge[case][(e.number, bottom)]
    p1 = model.coords[e.nodes[0] - 1]
    p2 = model.coords[e.nodes[1] - 1]
    x = (p2 - p1) / np.linalg.norm(p2 - p1)
    on_profile = values[0] * x + values[1] * e.y_local + values[2] * e.z_local
    if bottom == e.nodes[0]:
        on_profile = -on_profile
    return np.asarray(-on_profile, dtype=np.float64)


# --------------------------------------------------------------------------- variant


@dataclass
class VariantData:
    variant: Variant
    model: Model
    tables: RunTables
    g: Geometry51
    cases: list[str]
    k: tuple[float, float, float]
    ev: dict[str, Event]
    bs: list[Branch]
    comm: Path


def load_variant(ctx: ProjectContext, code: str, state: dict[str, Any]) -> VariantData:
    v = variants()[code]
    g = geometry(v.mesh_overrides)
    run_dir = Path(state[code]["execution"]["execution_dir"])
    tables = read_run(run_dir, g)
    dump = mesh_dump(ctx, Path(state[code]["maillage"]["med"]))
    model = build_model(dump, tables, g, v)
    vals = values(ctx, v)
    k = (vals.kx, vals.kx, vals.kz)
    data = {key: item.value for key, item in ctx.data().items().items()}
    ev = events(magnitudes(data), split=v.splice == "continu")
    comm = Path(state[code]["comm"])
    return VariantData(v, model, tables, g, all_cases(g), k, ev, branches(ev), comm)


def mesh_dump(ctx: ProjectContext, med: Path) -> dict[str, Any]:
    """The MED read by `medcoupling` in the container (trunk `dump_med`), kept next to
    the meshes of the lot."""
    from aster_expert.meshing.check import dump_med  # noqa: PLC0415
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415
    from aster_expert.projet.pipeline import Runtime  # noqa: PLC0415

    cache = ctx.results_dir / "lot51" / "maillage" / f"dump_{sha256(med)[:16]}.json"
    if not cache.is_file():
        rt = Runtime(ctx.repo_root)
        digest, _ = rt.aster()
        dump, _work = dump_med(
            med,
            project_root=ctx.repo_root,
            config=load_mesh_config(ctx.repo_root / "config" / "validation.yaml"),
            docker_bin=rt.docker_bin(),
            image_ref=f"{rt.image_repository}@{digest}",
        )
        cache.parent.mkdir(parents=True, exist_ok=True)  # clone neuf (lot 54)
        cache.write_text(dump.model_dump_json(), encoding="utf-8")
    loaded: dict[str, Any] = json.loads(cache.read_text(encoding="utf-8"))
    return loaded


# --------------------------------------------------------------------------- exports


def source_line(vd: VariantData, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    comm = Path(s["comm"])
    return (
        f"PONTONS-ALU-01, lot 51, variante {vd.variant.code} ({vd.variant.description}) : "
        f"exécution {run}, .comm sha256 {sha256(comm)}, maillage sha256 "
        f"{s['maillage']['med_sha256']}."
    )


AXES = (
    "Repère global : X le long du ponton depuis le quai (X = 0 rotules du quai, X = 6,25 et "
    "7,77 axes des chevêtres C1 et C2, X = 14,02 bout de la travée 2), Y transversal, Z "
    "vertical vers le haut (m NGF)."
)


def export_variant(
    ctx: ProjectContext, vd: VariantData, state: dict[str, Any], out: Path
) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    src = source_line(vd, state)
    m = vd.model
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
        f"{src} Unités : m, N/m. {AXES} element = numéro de la maille SEG2 (MED, à partir de 1). "
        "Repère local (U4.42.01) : x_l du nœud 1 au nœud 2 ; VECT_Z (0, 0, 1) pour les barres "
        "horizontales (z_l = projection de +Z, y_l = z_l ∧ x_l) ; VECT_Y (1, 0, 0) pour les "
        "profilés supports et les piles (y_l = projection de +X). Néoprènes : SEG2 DIS_T de 1 mm, "
        "raideurs dans le repère global. Liaisons : nœuds distincts liés dans le .comm.",
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
        "une autre barre, nœud d'une liaison, appui, néoprène) ; début = extrémité de plus "
        "petite coordonnée selon l'axe de la famille.",
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
        f"{src} Unités : m, rad. DEPL par nœud et par cas élémentaire, repère global ; rotations "
        "vides aux nœuds sans rotation (haut des néoprènes). " + cases_text,
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
        "quai (P35) : REAC_NODA, moments sans objet ; pieds des profilés supports en X = 14,02 "
        "(APP_FIXE, encastrés) : REAC_NODA avec moments ; ressorts de la semelle (SOL) : Σ des "
        "forces du sol −k·u, moment par rapport au point donné. Les néoprènes sont dans "
        "appuis_neoprene.csv.",
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
        reaction_rows(ctx, vd),
    )
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        f"{src} Jeu B′ révisé (P27, P31 à P35) et ELU accidentel, en règles : une combinaison = "
        "une option par emplacement d'une branche (produit des emplacements) ; option = "
        "« événement×facteur » (evenements.csv) ou ∅ (absence). Effectifs : "
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
        "les cas de 1 kPa). Valeurs de l'annexe A de la consigne du lot 51 (P29 à P34).",
        ["action", "evenement", "cas", "coefficient"],
        event_rows(vd.ev),
    )
    files["charges.csv"] = write(
        out / "charges.csv",
        f"{src} Unités : N/m (répartie), N (ponctuelle), m/s2 (pesanteur), K (température), m. "
        "Charges lues dans le .comm, repère global.",
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
        load_rows(vd, Path(state[vd.variant.code]["comm"])),
    )
    files["sections.csv"] = write(
        out / "sections.csv",
        f"{src} Unités : m, m2, m4, N/m ; AY, AZ : coefficients de cisaillement (A/Av). "
        "AFFE_CARA_ELEM : mots-clés affectés, puis caractéristiques que Code_Aster en déduit "
        "(U4.42.01), recalculées.",
        ["section", "groupes", "type", "cara", "valeur", "unite", "origine"],
        section_rows(Path(state[vd.variant.code]["comm"])),
    )
    files["appuis_neoprene.csv"] = write(
        out / "appuis_neoprene.csv",
        f"{src} Unités : N, m. Par appui (A1 : X = 6,25 ; A2 : X = 7,77 ; A3 : X = 14,02 ; YM/YP : "
        "Y = ∓0,93) et par cas : effort de l'appui sur le tablier, repère global, Fz > 0 en "
        "compression, Fz < 0 = effort de retenue (soulèvement, dispositif anti-soulèvement, P38) ; "
        "déplacement relatif u_haut − u_bas entre les deux nœuds du ressort. "
        + (
            "Variante M : appui mécanique sans raideur, effort lu en tête du profilé support."
            if vd.variant.bearings == "mecanique"
            else f"F = −K·(u_haut − u_bas), Kx = Ky = {number(vd.k[0])} N/m, Kz = {number(vd.k[2])} N/m."
        ),
        [
            "cas",
            "appui",
            "noeud_bas",
            "noeud_haut",
            "x",
            "y",
            "Fx",
            "Fy",
            "Fz",
            "ux",
            "uy",
            "uz",
        ],
        bearing_rows(vd),
    )
    files["piles.csv"] = write(
        out / "piles.csv",
        f"{src} Unités : N, N·m. Torseurs EFGE_ELNO en tête (sous l'anneau) et en pied (dessus de "
        "la semelle) de chaque pile, repère local x_l = +Z, y_l = +X, z_l = +Y ; N > 0 en traction. "
        "Liaison en tête : "
        + ", ".join(f"{p} {h}" for p, h in vd.variant.heads.items())
        + ".",
        ["cas", "pile", "position", "noeud", "element", "z", *EFGE],
        pile_rows(vd),
    )
    shutil.copyfile(
        Path(__file__).resolve().parent / "scripts" / "recombiner_lot51.py",
        out / "recombiner.py",
    )
    return files


def element_rows(vd: VariantData) -> list[list[Any]]:
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
    kx, _, kz = vd.k
    for b, (bottom, top) in m.springs.items():
        text = (
            "appui mécanique : Y et Z liés, X libre (raideurs nulles)"
            if vd.variant.bearings == "mecanique"
            else f"néoprène K_T_D_L global : Kx = Ky = {number(kx)}, Kz = {number(kz)} N/m, Kθ = 0"
        )
        rows.append(
            [
                f"NEO_{b}",
                "SEG2 DIS_T",
                bottom,
                top,
                "NEOPRENES",
                f"NEO_{b}",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                text,
            ]
        )
    plan = json.loads((vd.comm.parent / "generation.json").read_text("utf-8"))["links"]
    how = {name: kind for kind, items in plan.items() for name in items}
    for lk in vd.g.links:
        (a,) = m.group_nodes[f"{lk.name}_A"]
        b_node = (
            m.group_nodes[f"TP_{lk.name.removeprefix('LG_')}_A"][0]
            if how[lk.name] == "bras" and lk.kind == "longrine"
            else m.group_nodes[f"{lk.name}_B"][0]
        )
        kind = how[lk.name]
        detail = {
            "solide": "LIAISON_SOLIDE (6 ddl liés)",
            "bras": "LIAISON_DDL : translations du nœud 1 liées au nœud 2 par un bras rigide, rotations libres",
            "bras_torsion": "LIAISON_DDL : translations par bras rigide et DRX liés, rotations autour de y_l et z_l libres (éclissage articulé)",
        }[kind]
        offset = m.coords[b_node - 1] - m.coords[a - 1]
        rows.append(
            [
                lk.name,
                "LIAISON_SOLIDE" if kind == "solide" else "LIAISON_DDL",
                a,
                b_node,
                "LIAISON",
                lk.kind,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                f"{detail} ; vecteur nœud 1 → nœud 2 = ({number(geo(offset[0]))}, "
                f"{number(geo(offset[1]))}, {number(geo(offset[2]))}) m",
            ]
        )
    return rows


def member_rows(vd: VariantData) -> list[list[Any]]:
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


def force_rows(vd: VariantData) -> list[list[Any]]:
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


def reaction_rows(ctx: ProjectContext, vd: VariantData) -> list[list[Any]]:
    m = vd.model
    vals = values(ctx, vd.variant)
    areas = tributary_areas(vd.g)
    footing = (
        m.group_nodes["N_SEMELLE"]
        if "N_SEMELLE" in m.group_nodes
        else m.group_nodes["SEMELLE"]
    )
    fx, fy = vd.g.footing_x, vd.g.footing_y
    centre = np.array([(fx[0] + fx[-1]) / 2.0, (fy[0] + fy[-1]) / 2.0, vd.g.footing_z])
    rows: list[list[Any]] = []
    for case in vd.cases:
        reac = vd.tables.reac[case]
        for name, note in (
            ("APP_QUAI_YM", "rotule guidée : DX DZ bloqués, DY libre"),
            ("APP_QUAI_YP", "rotule fixe : DX DY DZ bloqués"),
            ("APP_FIXE", "pied de profilé support encastré sur support fixe"),
        ):
            for n in m.group_nodes[name]:
                r = reac[n]
                moments = r[3:] if name == "APP_FIXE" else [math.nan] * 3
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
        total = np.zeros(3)
        moment = np.zeros(3)
        depl = vd.tables.depl[case]
        for n in footing:
            p = m.coords[n - 1]
            area = areas[(round(float(p[0]), 6), round(float(p[1]), 6))]
            f = -np.array([vals.kt, vals.kt, vals.kn]) * area * depl[n][:3]
            total += f
            moment += np.cross(p - centre, f)
        rows.append(
            [
                case,
                "SOL (ressorts de la semelle, cumul)",
                f"{len(footing)} nœuds",
                *(geo(c) for c in centre),
                *(float(x) for x in total),
                *(float(x) for x in moment),
                "Σ des forces du sol sur la semelle (−k·u) ; moment par rapport au point donné",
            ]
        )
    return rows


def bearing_rows(vd: VariantData) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for case in vd.cases:
        for b, (force, du) in bearing_forces(
            vd.model, vd.tables, vd.variant, vd.k, case
        ).items():
            bottom, top = vd.model.springs[b]
            p = vd.model.coords[bottom - 1]
            rows.append(
                [
                    case,
                    b,
                    bottom,
                    top,
                    geo(p[0]),
                    geo(p[1]),
                    *(float(x) for x in force),
                    *(float(x) for x in du),
                ]
            )
    return rows


def pile_ends(vd: VariantData) -> list[tuple[str, str, int, int]]:
    """(pile, position, node, element) at the head and the foot of each pile."""
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


def pile_rows(vd: VariantData) -> list[list[Any]]:
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


def load_rows(vd: VariantData, comm_path: Path) -> list[list[Any]]:
    comm = read_comm(comm_path)
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
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        f"PESANTEUR ({concept.name})",
                    ]
                )
            for key, kind, unit in (
                ("FORCE_POUTRE", "répartie", "N/m"),
                ("FORCE_NODALE", "ponctuelle", "N"),
            ):
                for f in occurrences(kw.get(key)):
                    group = str(f.get("GROUP_MA", f.get("GROUP_NO")))
                    pts = m.coords[np.array(m.group_nodes[group]) - 1]
                    lo = pts[np.argmin(pts[:, 0])]
                    hi = pts[np.argmax(pts[:, 0])]
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
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    f"CREA_CHAMP {concept}, AFFE_VARC M_{case}",
                ]
            )
    return rows


def section_rows(comm_path: Path) -> list[list[Any]]:
    comm = read_comm(comm_path)
    _, cara = first_of(comm, "AFFE_CARA_ELEM")
    rows: list[list[Any]] = []
    for occ in occurrences(cara["POUTRE"]):
        groups = names(occ["GROUP_MA"])
        for r in section_properties(occ):
            rows.append(
                [
                    groups[0],
                    " ".join(groups),
                    str(occ["SECTION"]),
                    r.cara,
                    r.value,
                    r.unit,
                    r.origin,
                ]
            )
    for occ in occurrences(cara["DISCRET"]):
        vals = occ["VALE"]
        vals = vals if isinstance(vals, tuple) else (vals,)
        for k, x in enumerate(vals):
            rows.append(
                [
                    str(occ["GROUP_MA"]),
                    str(occ["GROUP_MA"]),
                    "DISCRET",
                    f"{occ['CARA']}[{k + 1}]",
                    float(x),
                    "N/m ou kg",
                    "affecté (mot-clé du .comm)",
                ]
            )
    return rows


# --------------------------------------------------------------------------- comparison


def _arrays(
    vd: VariantData, rows: list[tuple[int, int]], comp: int
) -> dict[str, FloatArray]:
    return {c: np.array([vd.tables.efge[c][r][comp] for r in rows]) for c in vd.cases}


def _rows_of(vd: VariantData, families: tuple[str, ...]) -> list[tuple[int, int]]:
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
    vd: VariantData,
    f: dict[str, FloatArray],
    *,
    sign: float,
    where: list[str],
    scale: float,
    states: tuple[str, ...] = STATES_COMPARED,
    without: tuple[str, ...] = (),
    absolute: bool = False,
) -> Quantity:
    """Extreme over the states: max (sign 1), min (sign −1) or, `absolute`, the
    largest in magnitude, reported with its sign."""
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
    vd: VariantData,
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


def comparison(vd: VariantData) -> dict[str, Quantity]:
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
    # Flèche de la travée 1, relative à la corde des appuis, actions variables seules :
    # vers le bas (min) et vers le haut (max), chacune à son état limite.
    f, where = deflection_arrays(vd)
    for state, tag in (("ELS_frequent", "F"), ("ELS_caracteristique", "C")):
        for sign, direction in ((-1.0, "bas"), (1.0, "haut")):
            q = _max_over_states(
                vd,
                f,
                sign=sign,
                where=where,
                scale=mm,
                states=(state,),
                without=("G",),
            )
            put(
                f"FL_T1_{tag}_{direction}",
                f"flèche relative T1 vers le {direction}, {state}, variables seules (< 0 vers le bas)",
                "mm",
                q,
            )
    # Néoprènes.
    bf = {c: bearing_forces(vd.model, vd.tables, vd.variant, vd.k, c) for c in vd.cases}
    where = list(BEARINGS)
    fz = {c: np.array([bf[c][b][0][2] for b in BEARINGS]) for c in vd.cases}
    put(
        "NEO_Fz_min",
        "néoprènes Fz min (< 0 : retenue)",
        "kN",
        _max_over_states(vd, fz, sign=-1, where=where, scale=kn),
    )
    put(
        "NEO_Fz_max",
        "néoprènes Fz max (compression)",
        "kN",
        _max_over_states(vd, fz, sign=1, where=where, scale=kn),
    )
    fxa = {c: np.array([bf[c][b][0][0] for b in BEARINGS]) for c in vd.cases}
    fya = {c: np.array([bf[c][b][0][1] for b in BEARINGS]) for c in vd.cases}
    put(
        "NEO_Fxy",
        "néoprènes Fxy max",
        "kN",
        _resultant_over_states(vd, fxa, fya, where, kn),
    )
    uxa = {c: np.array([bf[c][b][1][0] for b in BEARINGS]) for c in vd.cases}
    uya = {c: np.array([bf[c][b][1][1] for b in BEARINGS]) for c in vd.cases}
    put(
        "NEO_dh",
        "néoprènes déplacement horizontal relatif max",
        "mm",
        _resultant_over_states(vd, uxa, uya, where, mm),
    )
    # Piles.
    ends = pile_ends(vd)
    rows = [(e, n) for _, _, n, e in ends]
    where = [f"{p} {pos}" for p, pos, _, _ in ends]
    put(
        "PILE_N_min",
        "piles N min",
        "kN",
        _max_over_states(vd, _arrays(vd, rows, 0), sign=-1, where=where, scale=kn),
    )
    put(
        "PILE_N_max",
        "piles N max",
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
    # Rotules du quai.
    quai = [
        vd.model.group_nodes["APP_QUAI_YM"][0],
        vd.model.group_nodes["APP_QUAI_YP"][0],
    ]
    where = ["rotule YM (guidée)", "rotule YP (fixe)"]
    for comp, key in ((0, "QUAI_RX"), (1, "QUAI_RY"), (2, "QUAI_RZ")):
        f = {c: np.array([vd.tables.reac[c][n][comp] for n in quai]) for c in vd.cases}
        put(
            key,
            f"rotules du quai R{'XYZ'[comp]} extrême signé",
            "kN",
            _max_over_states(vd, f, sign=1, where=where, scale=kn, absolute=True),
        )
    return out


def deflection_arrays(vd: VariantData) -> tuple[dict[str, FloatArray], list[str]]:
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


def corners(vd: VariantData) -> list[tuple[int, int]]:
    """Element ends of the ring at its corners: cap beam node above each pile, tie end."""
    out = []
    for pile in PILES:
        cap = vd.model.group_nodes[f"TP_{pile}_B"][0]
        tie = vd.model.group_nodes[f"LG_{pile}_A"][0]
        for e in vd.model.elements.values():
            if e.family in ("CHEVETRES", "LONGRINES"):
                out += [(e.number, n) for n in e.nodes if n in (cap, tie)]
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
    "NEO_Fz_min",
    "NEO_Fz_max",
    "NEO_Fxy",
    "NEO_dh",
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
    "QUAI_RX",
    "QUAI_RY",
    "QUAI_RZ",
)


# --------------------------------------------------------------------------- criteria


def criterion_linearity(vd: VariantData) -> dict[str, float]:
    """Criterion 3: the total case against the sum of its span cases (DEPL)."""
    out = {}
    for base in ("G2", "Q", "HU", "HD"):
        total = np.array(
            [vd.tables.depl[base][n][:6] for n in sorted(vd.tables.depl[base])]
        )
        parts = sum(
            np.array(
                [
                    vd.tables.depl[f"{base}_{t}"][n][:6]
                    for n in sorted(vd.tables.depl[base])
                ]
            )
            for t in ("T1", "PT", "T2")
        )
        diff = np.nan_to_num(np.abs(total - parts))
        out[base] = float(diff.max() / np.nanmax(np.abs(total)))
    return out


def criterion_bearings(vd: VariantData) -> float:
    """Criterion 4: −K·Δu against the force read at the top of the support profile."""
    worst = 0.0
    for case in vd.cases:
        forces = []
        diffs = []
        for b in BEARINGS:
            bottom, top = vd.model.springs[b]
            du = vd.tables.depl[case][top][:3] - vd.tables.depl[case][bottom][:3]
            spring = -np.array(vd.k) * du
            profile = profile_top_force(vd.model, vd.tables, b, case)
            forces.append(np.abs(spring).max())
            diffs.append(np.abs(spring - profile).max())
        worst = max(worst, max(diffs) / max(max(forces), 1e-300))
    return worst


def criterion_recombination(out: Path, vd: VariantData) -> list[dict[str, Any]]:
    """Criterion 5: the extremes of the decomposition at a governing place against the
    combination-by-combination enumeration of the delivered recombiner.py (standard
    library, rules read back from the exported CSV)."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    checks = []
    places: list[tuple[str, dict[str, FloatArray], list[str]]] = []
    rows = _rows_of(vd, ("POUTRES_PRINC",))
    places.append(
        ("MFY poutres principales", _arrays(vd, rows, 4), [f"{e}/{n}" for e, n in rows])
    )
    ends = pile_ends(vd)
    prow = [(e, n) for _, _, n, e in ends]
    places.append(("N piles", _arrays(vd, prow, 0), [f"{e}/{n}" for e, n in prow]))
    bf = {c: bearing_forces(vd.model, vd.tables, vd.variant, vd.k, c) for c in vd.cases}
    places.append(
        (
            "Fz néoprènes",
            {c: np.array([bf[c][b][0][2] for b in BEARINGS]) for c in vd.cases},
            list(BEARINGS),
        )
    )
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


# --------------------------------------------------------------------------- steps


def step_exports(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    root = ctx.results_dir / "lot51" / "exports"
    root.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    detail_rows: list[list[Any]] = []
    main_rows: list[list[Any]] = []
    for code in codes:
        s = state.get(code, {})
        execution = s.get("execution", {})
        v = variants()[code]
        if "execution_dir" not in execution:
            message = execution.get("message", "non exécutée")
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
                f"PONTONS-ALU-01, lot 51, variante {code} ({v.description}) : non calculée.\n"
                "Consigne § 2 : variante mécaniquement instable, signalée sans stabilisation "
                "artificielle.\nMessage de Code_Aster :\n" + message + "\n",
                encoding="utf-8",
            )
            summary[code] = {
                "statut": "non calculée",
                "message": message,
                "erreurs": execution.get("erreurs", []),
            }
            print(f"{code} : non calculée")
            continue
        vd = load_variant(ctx, code, state)
        out = root / code
        files = export_variant(ctx, vd, state, out)
        quantities = comparison(vd)
        info: dict[str, Any] = {
            "statut": "calculée",
            "fichiers": files,
            "effectifs": counts(vd.bs),
            "comparaison": {k: q.__dict__ for k, q in quantities.items()},
        }
        if code == "R":
            info["critere_3_linearite"] = criterion_linearity(vd)
            info["critere_4_neoprenes"] = criterion_bearings(vd)
            info["critere_5_recombinaison"] = criterion_recombination(out, vd)
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
        "PONTONS-ALU-01, lot 51 : comparaison des variantes. Valeurs : enveloppes du jeu B′ "
        "révisé (ELU fondamental, ELS caractéristique, ELS fréquent) et de l'ELU accidentel, "
        "sauf les flèches (ELS fréquent, ELS caractéristique, actions variables seules, "
        "relatives à la corde des appuis de la travée 1). Unités : kN, kN·m, mm. Colonnes : "
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
        "PONTONS-ALU-01, lot 51 : grandeurs de comparaison, état limite, combinaison et lieu qui gouvernent.",
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
    root = ctx.results_dir / "lot51" / "exports"
    dest = target or Path("/media/sf_partage/echanges/lot51/pontons_alu_01")
    dest.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    for code in codes:
        folder = root / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue  # __pycache__ du recombiner importé par le critère 5
            (dest / code).mkdir(exist_ok=True)
            shutil.copyfile(f, dest / code / f.name)
            names.append(f"{code}/{f.name}")
    for extra in ("comparaison_variantes.csv", "comparaison_variantes_detail.csv"):
        shutil.copyfile(root / extra, dest / extra)
        names.append(extra)
    from aster_expert.livrables.charges_salome import set_med_path  # noqa: PLC0415

    charges = ctx.results_dir / "livrables" / "charges_salome"
    if "R" in codes and (charges / "charges.med").is_file():
        for name in ("charges.med", "charges_salome.py"):
            shutil.copyfile(charges / name, dest / "R" / name)
            names.append(f"R/{name}")
        set_med_path(dest / "R" / "charges_salome.py", dest / "R" / "charges.med")
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(set(names))]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    print(f"dépôt : {len(lines)} fichiers dans {dest}")


__all__ = [
    "COMPARISON_COLUMNS",
    "VariantData",
    "bearing_forces",
    "comparison",
    "export_variant",
    "load_variant",
    "parse_tableau",
    "profile_top_force",
    "read_run",
]
