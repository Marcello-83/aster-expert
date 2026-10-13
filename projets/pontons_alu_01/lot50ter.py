"""Export of lot 50 ter for PONTONS-ALU-01: the data the supervisor needs for the EC9
checks, the 3D views and the DXF drawings, read from the results of lot 50 bis
(reference run, P24 and P25, MP1200, k = 1), never a new run.

Sources: the arrays of the deliverables (`resultats/livrables/donnees/*.npz`: mesh,
DEPL, EFGE_ELNO, REAC_NODA, SIEF_ELGA of the soil springs) and the production `.comm`
itself, read as Python syntax (never executed) for the sections (AFFE_CARA_ELEM/POUTRE),
the orientation (AFFE_CARA_ELEM/ORIENTATION), the links (AFFE_CHAR_MECA/LIAISON_SOLIDE,
LIAISON_DDL, DDL_IMPO) and the loads (AFFE_CHAR_MECA, CREA_CHAMP and AFFE_MATERIAU/
AFFE_VARC of the thermal cases).

Common format (consigne): `;` separator, decimal point, UTF-8 without BOM, SI units,
one comment line `# ...` on top (source, units, sign conventions). Numbers are written
with 17 significant digits (`repr`): recombining from the files adds no rounding.

Numbering: node = MED node number (1-based); element = MED number of the SEG2 cell
within the SEG2 type (1-based; the CSV of lot 50 bis print the 0-based index, so
« maille 78 » there is element 79 here).

Local axes (U4.42.01, ORIENTATION, VECT_Y | VECT_Z): x_l from node 1 to node 2 of the
cell; VECT_Z: z_l = projection of the vector on the plane orthogonal to x_l, y_l =
z_l × x_l; VECT_Y: y_l = projection, z_l = x_l × y_l; the last occurrence prevails.

Derived properties of the RECTANGLE and CERCLE sections: formulas and shear tables of
U4.42.01 (R3.08.03), recomputed here -- Code_Aster does not print them without INFO=2.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.arrondis import GridRule, off_grid_noise
from aster_expert.livrables.donnees import Deliverables, FieldArrays
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons import STATE_OF_FAMILY, set_b, set_b_prime

FloatArray = NDArray[np.float64]
Vector = tuple[float, float, float]

CASES = (
    "G1",
    "G2",
    "Q",
    "QD",
    "HU",
    "HD",
    "AMM",
    "AMP",
    "ACM",
    "ACP",
    "AAM",
    "AAP",
    "TP",
    "TM",
    "TAP",
    "TAM",
)
CASE_LABELS = {
    "G1": "G1",
    "G2": "G2",
    "Q": "Q",
    "QD": "Q½",
    "HU": "Hu (1 kPa)",
    "HD": "Hd (1 kPa)",
    "AMM": "AM−",
    "AMP": "AM+",
    "ACM": "AC−",
    "ACP": "AC+",
    "AAM": "ACA−",
    "AAP": "ACA+",
    "TP": "T+",
    "TM": "T−",
    "TAP": "TA+",
    "TAM": "TA−",
}
BAR_GROUPS = (
    "POUTRES_PRINC",
    "MONTANTS",
    "DIAGONALES",
    "PANNES_SEC",
    "SUPPORTS",
    "CHEVETRE",
    "POTEAUX",
)
FORCE_FAMILIES = BAR_GROUPS[:-1]
"""Families of efforts_elementaires.csv (consigne: the columns, not the piles)."""
ALUMINIUM = BAR_GROUPS[:5]
MEMBER_PREFIX = {
    "POUTRES_PRINC": "PP_",
    "MONTANTS": "MONT_",
    "DIAGONALES": "DIAG_",
    "PANNES_SEC": "PANNE_",
    "SUPPORTS": "SUP_",
    "CHEVETRE": "CHEVETRE",
    "POTEAUX": "POT_",
}
MEMBER_AXIS = {
    "POUTRES_PRINC": 0,
    "MONTANTS": 1,
    "DIAGONALES": 0,
    "PANNES_SEC": 0,
    "SUPPORTS": 2,
    "CHEVETRE": 1,
    "POTEAUX": 2,
}
AXIS_NAME = ("X", "Y", "Z")
COMPONENT_VECTOR: dict[str, Vector] = {
    "FX": (1.0, 0.0, 0.0),
    "FY": (0.0, 1.0, 0.0),
    "FZ": (0.0, 0.0, 1.0),
}
ULS = ("ELU_fondamental", "ELU_accidentel")


# --------------------------------------------------------------------------- .comm


@dataclass(frozen=True)
class Concept:
    """A name of the `.comm` used as a value (a concept)."""

    name: str


def _value(node: ast.expr) -> Any:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "_F":
            return {k.arg: _value(k.value) for k in node.keywords if k.arg}
        return {
            "__command__": node.func.id,
            **{k.arg: _value(k.value) for k in node.keywords if k.arg},
        }
    if isinstance(node, ast.Tuple | ast.List):
        return tuple(_value(e) for e in node.elts)
    if isinstance(node, ast.Name):
        return Concept(node.id)
    return ast.literal_eval(node)


def read_comm(path: Path) -> list[tuple[str, str, dict[str, Any]]]:
    """(concept, command, keywords) of every assignment `X = COMMAND(...)` of the
    `.comm`, in order; the file is parsed, never executed."""
    out = []
    for statement in ast.parse(path.read_text(encoding="utf-8")).body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Name)
        ):
            keywords = _value(statement.value)
            keywords.pop("__command__", None)
            out.append(
                (statement.targets[0].id, statement.value.func.id, dict(keywords))
            )
    return out


def occurrences(value: Any) -> list[dict[str, Any]]:
    """A factor keyword as a list of occurrences (one `_F` or a tuple of them)."""
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return [v for v in value if isinstance(v, dict)]


def names(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def command(comm: list[tuple[str, str, dict[str, Any]]], name: str) -> dict[str, Any]:
    """Keywords of the last assignment of concept `name`."""
    found = [k for c, _, k in comm if c == name]
    if not found:
        message = f"concept {name} absent du .comm"
        raise KeyError(message)
    return found[-1]


def first_of(
    comm: list[tuple[str, str, dict[str, Any]]], cmd: str
) -> tuple[str, dict[str, Any]]:
    return next((c, k) for c, n, k in comm if n == cmd)


# --------------------------------------------------------------------------- sections

AY_TABLE_RECT = (
    (0.00, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95),
    (
        (1.200,) * 12,
        (
            1.200,
            1.209,
            1.212,
            1.217,
            1.220,
            1.221,
            1.220,
            1.217,
            1.212,
            1.207,
            1.202,
            1.201,
        ),
        (
            1.200,
            1.229,
            1.236,
            1.247,
            1.252,
            1.253,
            1.249,
            1.241,
            1.230,
            1.217,
            1.206,
            1.202,
        ),
        (
            1.200,
            1.300,
            1.317,
            1.339,
            1.348,
            1.345,
            1.332,
            1.309,
            1.280,
            1.247,
            1.217,
            1.206,
        ),
        (
            1.200,
            1.413,
            1.442,
            1.477,
            1.489,
            1.479,
            1.451,
            1.408,
            1.354,
            1.295,
            1.238,
            1.214,
        ),
        (
            1.200,
            1.577,
            1.621,
            1.671,
            1.683,
            1.662,
            1.614,
            1.545,
            1.460,
            1.366,
            1.272,
            1.230,
        ),
        (
            1.200,
            1.803,
            1.866,
            1.936,
            1.949,
            1.913,
            1.838,
            1.733,
            1.608,
            1.469,
            1.325,
            1.256,
        ),
        (
            1.200,
            2.115,
            2.207,
            2.309,
            2.324,
            2.267,
            2.154,
            2.000,
            1.818,
            1.619,
            1.409,
            1.301,
        ),
        (
            1.200,
            2.561,
            2.704,
            2.866,
            2.894,
            2.810,
            2.640,
            2.409,
            2.140,
            1.848,
            1.541,
            1.378,
        ),
        (
            1.200,
            3.265,
            3.520,
            3.830,
            3.907,
            3.790,
            3.524,
            3.154,
            2.720,
            2.252,
            1.771,
            1.517,
        ),
        (
            1.200,
            4.715,
            5.358,
            6.216,
            6.536,
            6.401,
            5.916,
            5.186,
            4.300,
            3.331,
            2.338,
            1.841,
        ),
        (
            1.200,
            6.689,
            8.194,
            10.294,
            11.236,
            11.189,
            10.375,
            9.014,
            7.296,
            5.372,
            3.367,
            2.371,
        ),
    ),
)
"""U4.42.01, SECTION='RECTANGLE': Tab(column, row); AY = Tab(αy, αz), AZ = Tab(αz, αy);
rows are α of the row, columns α of the column, both 0 … 0,95, linear interpolation."""
AY_TABLE_CIRCLE = (
    (0.00, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00),
    (
        1.167,
        1.174,
        1.199,
        1.289,
        1.419,
        1.563,
        1.700,
        1.815,
        1.902,
        1.960,
        1.991,
        2.000,
    ),
)
"""U4.42.01, SECTION='CERCLE': AY = AZ as a function of α = (R − EP)/R."""


def _bracket(grid: Sequence[float], value: float) -> tuple[int, float]:
    if not grid[0] <= value <= grid[-1]:
        message = f"α = {value} hors du tableau de U4.42.01 ({grid[0]} … {grid[-1]})"
        raise ValueError(message)
    for i in range(len(grid) - 1):
        if value <= grid[i + 1]:
            return i, (value - grid[i]) / (grid[i + 1] - grid[i])
    return len(grid) - 2, 1.0


def shear_rectangle(column: float, row: float) -> float:
    """Tab(column, row) of U4.42.01, bilinear."""
    grid, table = AY_TABLE_RECT
    i, u = _bracket(grid, row)
    j, v = _bracket(grid, column)
    return (
        (1 - u) * (1 - v) * table[i][j]
        + (1 - u) * v * table[i][j + 1]
        + u * (1 - v) * table[i + 1][j]
        + u * v * table[i + 1][j + 1]
    )


def shear_circle(alpha: float) -> float:
    grid, table = AY_TABLE_CIRCLE
    i, u = _bracket(grid, alpha)
    return (1 - u) * table[i] + u * table[i + 1]


@dataclass(frozen=True)
class SectionRow:
    cara: str
    value: float
    unit: str
    origin: str


def section_properties(occurrence: dict[str, Any]) -> list[SectionRow]:
    """Assigned keywords of an AFFE_CARA_ELEM/POUTRE occurrence and the properties
    Code_Aster derives from them (U4.42.01), recomputed."""
    kind = str(occurrence["SECTION"])
    caras = names(occurrence["CARA"])
    vals = occurrence["VALE"]
    vals = (vals,) if isinstance(vals, int | float) else tuple(vals)
    given = {c: float(v) for c, v in zip(caras, vals, strict=True)}
    units = {
        "A": "m2",
        "IY": "m4",
        "IZ": "m4",
        "JX": "m4",
        "AY": "-",
        "AZ": "-",
        "H": "m",
        "HY": "m",
        "HZ": "m",
        "EP": "m",
        "EPY": "m",
        "EPZ": "m",
        "R": "m",
        "RY": "m",
        "RZ": "m",
        "RT": "m",
    }
    rows = [
        SectionRow(c, v, units.get(c, ""), "affecté (mot-clé du .comm)")
        for c, v in given.items()
    ]
    derived: dict[str, float] = {}
    if kind == "RECTANGLE":
        hy = given.get("HY", given.get("H"))
        hz = given.get("HZ", given.get("H"))
        assert hy is not None and hz is not None
        hollow = "EP" in given or "EPY" in given or "EPZ" in given
        epy = given.get("EPY", given.get("EP", hy / 2.0))
        epz = given.get("EPZ", given.get("EP", hz / 2.0))
        derived["A"] = hy * hz - (hy - 2 * epy) * (hz - 2 * epz)
        derived["IY"] = hy * hz**3 / 12.0 - (hy - 2 * epy) * (hz - 2 * epz) ** 3 / 12.0
        derived["IZ"] = hz * hy**3 / 12.0 - (hz - 2 * epz) * (hy - 2 * epy) ** 3 / 12.0
        if hollow:
            jx = (
                2.0
                * epy
                * epz
                * (hy - epy) ** 2
                * (hz - epz) ** 2
                / (hy * epy + hz * epz - epy**2 - epz**2)
            )
            derived["JX"] = jx
            derived["RT"] = jx / (2.0 * epz * (hy - epy) * (hz - epz))
        else:
            a, b = (hy / 2.0, hz / 2.0) if hy > hz else (hz / 2.0, hy / 2.0)
            j = a * b**3 * (16.0 / 3.0 - 3.36 * b / a + 0.28 * b**5 / a**5)
            derived["JX"] = j
            derived["RT"] = j * (3 * a + 1.8 * b) / (8 * a**2 * b**2)
        alpha_y, alpha_z = (hy - 2 * epy) / hy, (hz - 2 * epz) / hz
        derived["AY"] = shear_rectangle(alpha_y, alpha_z)
        derived["AZ"] = shear_rectangle(alpha_z, alpha_y)
        derived["RY"] = hy / 2.0
        derived["RZ"] = hz / 2.0
    elif kind == "CERCLE":
        r = given["R"]
        ep = given.get("EP", r)
        inertia = math.pi * r**4 / 4.0 - math.pi * (r - ep) ** 4 / 4.0
        derived["A"] = math.pi * r**2 - math.pi * (r - ep) ** 2
        derived["IY"] = inertia
        derived["IZ"] = inertia
        derived["JX"] = 2.0 * inertia
        derived["AY"] = shear_circle((r - ep) / r)
        derived["AZ"] = derived["AY"]
        derived["RY"] = derived["RZ"] = derived["RT"] = r
    elif kind != "GENERALE":
        message = f"SECTION = {kind} non traitée par l'export"
        raise ValueError(message)
    origin = "calculé par Code_Aster (U4.42.01, R3.08.03), recalculé ici"
    rows += [
        SectionRow(c, v, units.get(c, ""), origin)
        for c, v in derived.items()
        if c not in given
    ]
    return rows


# --------------------------------------------------------------------------- model


def _unit(v: FloatArray) -> FloatArray:
    norm = float(np.linalg.norm(v))
    if norm < 1e-12:
        message = "vecteur nul : orientation indéfinie"
        raise ValueError(message)
    return v / norm


def local_axes(
    p1: FloatArray, p2: FloatArray, cara: str, vector: Vector
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """x_l, y_l, z_l of a SEG2 oriented by VECT_Y or VECT_Z (U4.42.01)."""
    x = _unit(p2 - p1)
    v = np.asarray(vector, dtype=np.float64)
    projected = _unit(v - float(v @ x) * x)
    if cara == "VECT_Z":
        z = projected
        y = np.cross(z, x)
    elif cara == "VECT_Y":
        y = projected
        z = np.cross(x, y)
    else:
        message = f"ORIENTATION/CARA = {cara} non traité par l'export"
        raise ValueError(message)
    return x, y, z


@dataclass
class Element:
    number: int
    """MED number within SEG2 (1-based)."""
    index: int
    family: str
    group: str
    nodes: tuple[int, int]
    """0-based node indices."""
    section: str
    y_local: FloatArray
    z_local: FloatArray
    length: float
    member: str = ""


@dataclass
class Link:
    name: str
    kind: str
    nodes: tuple[int, ...]
    detail: str


@dataclass
class Member:
    name: str
    label: str
    family: str
    group: str
    section: str
    nodes: list[int]
    """0-based node indices, from start to end."""
    elements: list[int]
    """SEG2 numbers, from start to end."""
    abscissa: dict[int, float] = field(default_factory=dict)

    @property
    def length(self) -> float:
        return self.abscissa[self.nodes[-1]]


@dataclass
class Model:
    coords: FloatArray
    node_groups: dict[int, list[str]]
    elements: dict[int, Element]
    links: list[Link]
    members: list[Member]
    supports: dict[int, str]
    sections: dict[str, tuple[dict[str, Any], tuple[str, ...]]]
    comm: list[tuple[str, str, dict[str, Any]]]
    cell_groups: dict[str, set[int]]
    """SEG2 numbers of every SEG2 cell group."""

    def member(self, name: str) -> Member:
        return next(m for m in self.members if m.name == name)


SECTION_NAMES = {
    "POUTRES_PRINC": "MP1200",
    "MONTANTS": "tube 150x150x7",
    "DIAGONALES": "tube 150x150x7",
    "SUPPORTS": "tube 150x150x7",
    "PANNES_SEC": "tube 50x50x5",
    "CHEVETRE": "chevetre 0.25x0.40",
    "POTEAUX": "poteau D0.50",
}


def _section_name(groups: tuple[str, ...]) -> str:
    labels = {SECTION_NAMES[g] for g in groups}
    assert len(labels) == 1, groups
    return labels.pop()


def build_model(d: Deliverables, comm_path: Path) -> Model:
    """Elements, links, supports and members of the model, from the mesh of the
    deliverables and the `.comm`."""
    mesh = d.mesh
    coords = mesh.coords
    comm = read_comm(comm_path)
    _, cara = first_of(comm, "AFFE_CARA_ELEM")
    sections: dict[str, tuple[dict[str, Any], tuple[str, ...]]] = {}
    section_of: dict[str, str] = {}
    for occ in occurrences(cara["POUTRE"]):
        groups = names(occ["GROUP_MA"])
        label = _section_name(groups)
        sections[label] = (occ, groups)
        for g in groups:
            section_of[g] = label
    orientation_of: dict[str, tuple[str, Vector]] = {}
    for occ in occurrences(cara.get("ORIENTATION")):
        vec = tuple(float(v) for v in occ["VALE"])
        assert len(vec) == 3
        for g in names(occ["GROUP_MA"]):
            orientation_of[g] = (str(occ["CARA"]), (vec[0], vec[1], vec[2]))

    conn = mesh.arrays["conn_-1"]
    elements: dict[int, Element] = {}
    for family in BAR_GROUPS:
        cells = mesh.cell_group(family)
        assert cells is not None and cells[0] == -1
        prefix = MEMBER_PREFIX[family]
        member_groups = [
            k.split("_", 2)[2]
            for k in mesh.arrays
            if k.startswith("gma_-1_")
            and k.split("_", 2)[2].startswith(prefix)
            and k.split("_", 2)[2] != family
        ] or [family]
        group_of: dict[int, str] = {}
        for g in member_groups:
            sub = mesh.cell_group(g)
            assert sub is not None
            for c in sub[1].tolist():
                group_of[int(c)] = g
        o_cara, o_vec = orientation_of[family]
        for c in cells[1].tolist():
            n1, n2 = (int(n) for n in conn[c][:2])
            _, y, z = local_axes(coords[n1], coords[n2], o_cara, o_vec)
            elements[int(c) + 1] = Element(
                number=int(c) + 1,
                index=int(c),
                family=family,
                group=group_of[int(c)],
                nodes=(n1, n2),
                section=section_of[family],
                y_local=y,
                z_local=z,
                length=float(np.linalg.norm(coords[n2] - coords[n1])),
            )

    node_groups: dict[int, list[str]] = {i: [] for i in range(len(coords))}
    for key, ids in mesh.arrays.items():
        if key.startswith("gno_"):
            for n in ids.tolist():
                node_groups[int(n)].append(key[4:])
        elif key.startswith("gma_"):
            level = key.split("_")[1]
            sub_conn = mesh.arrays[f"conn_{level}"][ids]
            for n in np.unique(sub_conn[sub_conn >= 0]).tolist():
                node_groups[int(n)].append(key.split("_", 2)[2])
    for n in node_groups:
        node_groups[n] = sorted(set(node_groups[n]))

    _, cl = next((c, k) for c, n, k in comm if n == "AFFE_CHAR_MECA" and c == "CL")
    links: list[Link] = []
    for occ in occurrences(cl.get("LIAISON_SOLIDE")):
        for g in names(occ["GROUP_NO"]):
            nodes = tuple(int(n) for n in mesh.node_group(g).tolist())
            links.append(
                Link(g, "LIAISON_SOLIDE", nodes, "liaison rigide (6 ddl liés)")
            )
    hinge_pairs: dict[str, set[str]] = {}
    for occ in occurrences(cl.get("LIAISON_DDL")):
        groups = names(occ["GROUP_NO"])
        hinge_pairs.setdefault(groups[0], set()).update(groups[1:])
    for upper, lowers in sorted(hinge_pairs.items()):
        (lower,) = lowers
        n_up = int(mesh.node_group(upper)[0])
        n_lo = int(mesh.node_group(lower)[0])
        arm = float(coords[n_up][2] - coords[n_lo][2])
        links.append(
            Link(
                f"{upper}-{lower}",
                "LIAISON_DDL",
                (n_up, n_lo),
                "articulation : translations du pied liées à l'axe du chevêtre par un "
                f"bras rigide de {number(geo(arm))} m (u_S = u_C + θ_C ∧ h·Z), "
                "rotations libres",
            )
        )
    supports: dict[int, str] = {}
    for occ in occurrences(cl.get("DDL_IMPO")):
        blocked = [k for k in ("DX", "DY", "DZ", "DRX", "DRY", "DRZ") if k in occ]
        free = [k for k in ("DX", "DY", "DZ") if k not in occ]
        for g in names(occ["GROUP_NO"]):
            text = f"appui {g} : {' '.join(blocked)} bloqués"
            if free:
                text += f", {' '.join(free)} libre"
            for n in mesh.node_group(g).tolist():
                supports[int(n)] = text

    members = _members(coords, elements, links, supports)
    cell_groups = {
        key.split("_", 2)[2]: {int(c) + 1 for c in ids.tolist()}
        for key, ids in mesh.arrays.items()
        if key.startswith("gma_-1_")
    }
    return Model(
        coords,
        node_groups,
        elements,
        links,
        members,
        supports,
        sections,
        comm,
        cell_groups,
    )


def _members(
    coords: FloatArray,
    elements: dict[int, Element],
    links: list[Link],
    supports: dict[int, str],
) -> list[Member]:
    """Split every bar (member group PP_YM, MONT_1 … CHEVETRE) at its connection
    nodes: nodes shared with another bar, nodes of a link, supports."""
    by_group: dict[str, list[Element]] = {}
    for e in elements.values():
        by_group.setdefault(e.group, []).append(e)
    groups_at: dict[int, set[str]] = {}
    for e in elements.values():
        for n in e.nodes:
            groups_at.setdefault(n, set()).add(e.group)
    joints = {n for n, gs in groups_at.items() if len(gs) >= 2}
    for link in links:
        joints |= set(link.nodes)
    joints |= set(supports)

    out: list[Member] = []
    for group in sorted(by_group, key=_group_order):
        elems = by_group[group]
        family = elems[0].family
        axis = MEMBER_AXIS[family]
        adjacency: dict[int, list[Element]] = {}
        for e in elems:
            for n in e.nodes:
                adjacency.setdefault(n, []).append(e)
        ends = [n for n, es in adjacency.items() if len(es) == 1]
        if len(ends) != 2 or any(len(es) > 2 for es in adjacency.values()):
            message = f"{group} n'est pas une barre continue"
            raise ValueError(message)
        start = min(ends, key=lambda n: float(coords[n][axis]))
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
        assert len(chain_elems) == len(elems), group
        cuts = [0] + [
            i for i, n in enumerate(chain_nodes[1:-1], start=1) if n in joints
        ]
        cuts.append(len(chain_nodes) - 1)
        for k, (i, j) in enumerate(zip(cuts, cuts[1:], strict=False), start=1):
            nodes = chain_nodes[i : j + 1]
            sub = chain_elems[i:j]
            a, b = float(coords[nodes[0]][axis]), float(coords[nodes[-1]][axis])
            name = f"{group}_{k:02d}"
            member = Member(
                name=name,
                label=f"{group} de {AXIS_NAME[axis]} = {_short(a)} à {_short(b)}",
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
                e.member = name
            out.append(member)
    return out


def _group_order(group: str) -> tuple[int, str]:
    for i, family in enumerate(BAR_GROUPS):
        if group.startswith(MEMBER_PREFIX[family]):
            return i, group
    return len(BAR_GROUPS), group


def _short(v: float) -> str:
    text = f"{round(v, 6):.6f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def connections(model: Model, member: Member, node: int) -> list[tuple[str, str]]:
    """(member, nature) of everything attached to `member` at `node`."""
    out: list[tuple[str, str]] = []
    alu = member.family in ALUMINIUM

    def members_at(n: int) -> list[Member]:
        return [m for m in model.members if n in m.nodes and m is not member]

    for other in members_at(node):
        if other.group == member.group:
            nature = "continuité (même barre)"
        elif alu and other.family in ALUMINIUM:
            nature = "soudé"
        else:
            nature = "nœud commun"
        out.append((other.name, nature))
    for link in model.links:
        if node not in link.nodes:
            continue
        for partner in link.nodes:
            if partner == node:
                continue
            attached = [m for m in model.members if partner in m.nodes]
            if link.kind == "LIAISON_DDL":
                nature = f"articulation ({link.name})"
            elif alu and all(m.family in ALUMINIUM for m in attached) and attached:
                nature = f"soudé, excentricité par liaison rigide ({link.name})"
            else:
                nature = f"liaison rigide ({link.name})"
            if attached:
                out += [(m.name, nature) for m in attached]
            else:
                groups = [
                    g for g in model.node_groups[partner] if g in ("SEMELLE", "SOL")
                ]
                out.append((f"nœud {partner + 1} ({'/'.join(groups)})", nature))
    if node in model.supports:
        out.append(("—", model.supports[node]))
    return out


# --------------------------------------------------------------------------- fields


def result_field(d: Deliverables, ctx: ProjectContext, name: str) -> FieldArrays:
    section = ctx.declaration.deliverables
    assert section is not None
    info = next(i for i in d.field_infos(section.fields) if i.field == name)
    return d.field(info)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- CSV


GRID = GridRule(grille_decimales=3, epsilon=1.0e-6, bloquant=False)
"""Grid of config/arrondis.yaml (`maillage`): 1 mm, noise below 1e-6 m."""


def geo(v: float) -> float:
    """A coordinate, length or direction cosine without its binary noise: snapped to
    the 1 mm grid when within 1e-6 of it (`1.3579999999999999` -> 1.358), else 12
    decimals. Forces and displacements are never rounded."""
    f = float(v)
    snapped = round(f, GRID.grille_decimales)
    if f == snapped or off_grid_noise(f, GRID) is not None:
        return snapped + 0.0
    return round(f, 12) + 0.0


def number(v: float) -> str:
    """17 significant digits, decimal point; -0.0 written 0.0."""
    f = float(v)
    if f == 0.0:
        return "0.0"
    return repr(f)


def write(
    path: Path, header: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]
) -> int:
    """Write a CSV of the common format; returns the number of data rows."""
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(f"# {header}\n")
        writer = csv.writer(stream, delimiter=";", lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [
                    number(float(v)) if isinstance(v, float | np.floating) else v
                    for v in row
                ]
            )
            count += 1
    return count


# --------------------------------------------------------------------------- tables


def nodes_rows(model: Model) -> list[list[Any]]:
    return [
        [n + 1, *(geo(c) for c in model.coords[n]), "|".join(model.node_groups[n])]
        for n in range(len(model.coords))
    ]


def element_rows(model: Model) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for e in sorted(model.elements.values(), key=lambda e: e.number):
        rows.append(
            [
                e.number,
                "SEG2 POU_D_T",
                e.nodes[0] + 1,
                e.nodes[1] + 1,
                e.family,
                e.group,
                e.member,
                e.section,
                *(geo(v) for v in e.y_local),
                *(geo(v) for v in e.z_local),
                "aucune (axe neutre sur la ligne des nœuds)",
            ]
        )
    for link in model.links:
        a, b = link.nodes[0], link.nodes[-1]
        offset = model.coords[b] - model.coords[a]
        rows.append(
            [
                link.name,
                link.kind,
                a + 1,
                b + 1,
                "LIAISON",
                link.name,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                f"{link.detail} ; vecteur nœud 1 → nœud 2 = "
                f"({number(geo(offset[0]))}, {number(geo(offset[1]))}, "
                f"{number(geo(offset[2]))}) m",
            ]
        )
    return rows


def _connection_text(items: list[tuple[str, str]]) -> str:
    return " | ".join(f"{m} : {n}" for m, n in items)


def member_rows(model: Model) -> list[list[Any]]:
    rows = []
    for m in model.members:
        p, q = model.coords[m.nodes[0]], model.coords[m.nodes[-1]]
        inner = []
        for n in m.nodes[1:-1]:
            items = connections(model, m, n)
            if items:
                inner.append(
                    f"nœud {n + 1} à s = {number(geo(m.abscissa[n]))} m : "
                    + _connection_text(items)
                )
        rows.append(
            [
                m.name,
                m.label,
                m.family,
                m.group,
                m.section,
                *(geo(v) for v in p),
                *(geo(v) for v in q),
                geo(m.length),
                m.nodes[0] + 1,
                m.nodes[-1] + 1,
                " ".join(str(e) for e in m.elements),
                _connection_text(connections(model, m, m.nodes[0])),
                _connection_text(connections(model, m, m.nodes[-1])),
                " || ".join(inner),
            ]
        )
    return rows


def force_rows(model: Model, fa: FieldArrays) -> list[list[Any]]:
    comps = list(fa.info.components)
    assert comps == ["N", "VY", "VZ", "MT", "MFY", "MFZ"], comps
    rows: list[list[Any]] = []
    elno = np.flatnonzero(fa.kind == 1)
    order = sorted(
        (int(i) for i in elno),
        key=lambda i: (int(fa.entity[i]), int(fa.local[i])),
    )
    for case in CASES:
        values = fa.arrays[f"cas/{case}"]
        for i in order:
            e = model.elements.get(int(fa.entity[i]) + 1)
            if e is None or e.family not in FORCE_FAMILIES:
                continue
            end = int(fa.local[i])
            node = e.nodes[end]
            m = model.member(e.member)
            rows.append(
                [
                    case,
                    e.number,
                    e.member,
                    e.group,
                    e.family,
                    end + 1,
                    node + 1,
                    geo(m.abscissa[node]),
                    *(float(v) for v in values[i]),
                ]
            )
    return rows


def displacement_rows(fa: FieldArrays) -> list[list[Any]]:
    comps = list(fa.info.components)
    assert comps == ["DX", "DY", "DZ", "DRX", "DRY", "DRZ"], comps
    nodes = np.flatnonzero(fa.kind == 0)
    order = sorted((int(i) for i in nodes), key=lambda i: int(fa.entity[i]))
    return [
        [case, int(fa.entity[i]) + 1, *(float(v) for v in fa.arrays[f"cas/{case}"][i])]
        for case in CASES
        for i in order
    ]


def reaction_rows(
    model: Model,
    reac: FieldArrays,
    springs: FieldArrays,
    spring_nodes: NDArray[np.int64],
    centre: FloatArray,
) -> list[list[Any]]:
    """Quay hinges (REAC_NODA, force of the support on the structure) and the soil
    springs cumulated: −Σ k·u (SIEF_ELGA of the DIS_T, N, VY, VZ along X, Y, Z: the
    force of the soil on the footing), with its moment about `centre`."""
    assert list(reac.info.components) == ["DX", "DY", "DZ"]
    assert list(springs.info.components) == ["N", "VY", "VZ"]
    hinge_rows = sorted(
        (int(i) for i in np.flatnonzero(reac.kind == 0)),
        key=lambda i: int(reac.entity[i]),
    )
    rows: list[list[Any]] = []
    for case in CASES:
        for i in hinge_rows:
            n = int(reac.entity[i])
            name = next(
                g for g in model.node_groups[n] if g in ("APP_QUAI_YM", "APP_QUAI_YP")
            )
            rows.append(
                [
                    case,
                    name,
                    n + 1,
                    *(geo(c) for c in model.coords[n]),
                    *(float(v) for v in reac.arrays[f"cas/{case}"][i]),
                    "",
                    "",
                    "",
                    model.supports[n],
                ]
            )
        forces = -springs.arrays[f"cas/{case}"]
        arms = model.coords[spring_nodes] - centre
        total = forces.sum(axis=0)
        moment = np.cross(arms, forces).sum(axis=0)
        rows.append(
            [
                case,
                "SOL (ressorts de la semelle, cumul)",
                f"{len(spring_nodes)} nœuds",
                *(geo(c) for c in centre),
                *(float(v) for v in total),
                *(float(v) for v in moment),
                "Σ des forces du sol sur la semelle (−k·u) ; moment par rapport "
                "au point donné en x, y, z",
            ]
        )
    return rows


def combination_rows() -> list[list[Any]]:
    rows: list[list[Any]] = []
    for set_name, combos in (("B", set_b()), ("B′", set_b_prime())):
        for c in combos:
            rows.append(
                [
                    c.name,
                    STATE_OF_FAMILY[c.family],
                    set_name,
                    *(float(c.coefficients.get(case, 0.0)) for case in CASES),
                ]
            )
    return rows


def load_rows(model: Model) -> list[list[Any]]:
    """The loads of the `.comm`, per elementary case."""
    comm = model.comm
    _, mult = first_of(comm, "MACRO_ELAS_MULT")
    rows: list[list[Any]] = []
    blank = ["", "", "", "", "", "", ""]
    for occ in occurrences(mult["CAS_CHARGE"]):
        case = str(occ["NOM_CAS"])
        charge = occ["CHAR_MECA"]
        assert isinstance(charge, Concept)
        keywords = command(comm, charge.name)
        for occ_g in occurrences(keywords.get("PESANTEUR")):
            direction = tuple(float(v) for v in occ_g["DIRECTION"])
            rows.append(
                [
                    case,
                    "pesanteur",
                    "tout le modèle (masse volumique RHO des matériaux)",
                    *direction,
                    float(occ_g["GRAVITE"]),
                    "m/s2",
                    *blank,
                    f"AFFE_CHAR_MECA/PESANTEUR ({charge.name})",
                ]
            )
        for occ_f in occurrences(keywords.get("FORCE_POUTRE")):
            group = str(occ_f["GROUP_MA"])
            for comp, vec in COMPONENT_VECTOR.items():
                if comp in occ_f:
                    start, end = _extent(model, group)
                    rows.append(
                        [
                            case,
                            "répartie",
                            group,
                            *vec,
                            float(occ_f[comp]),
                            "N/m",
                            *start[0],
                            *end[0],
                            f"s = {number(geo(start[1]))} à {number(geo(end[1]))} m "
                            "le long de "
                            f"{start[2]} ; AFFE_CHAR_MECA/FORCE_POUTRE/{comp} "
                            f"({charge.name})",
                        ]
                    )
        for occ_n in occurrences(keywords.get("FORCE_NODALE")):
            group = str(occ_n["GROUP_NO"])
            node_ids = [n for n, gs in model.node_groups.items() if group in gs]
            for comp, vec in COMPONENT_VECTOR.items():
                if comp not in occ_n:
                    continue
                for n in node_ids:
                    p = [geo(c) for c in model.coords[n]]
                    rows.append(
                        [
                            case,
                            "ponctuelle",
                            f"{group} (nœud {n + 1})",
                            *vec,
                            float(occ_n[comp]),
                            "N",
                            *p,
                            *p,
                            f"AFFE_CHAR_MECA/FORCE_NODALE/{comp} ({charge.name})",
                        ]
                    )
        for key in keywords:
            if key not in {"MODELE", "PESANTEUR", "FORCE_POUTRE", "FORCE_NODALE"}:
                message = f"{charge.name} : chargement {key} non traité par l'export"
                raise ValueError(message)
    for concept, name, keywords in comm:
        if name != "MECA_STATIQUE":
            continue
        mater = keywords["CHAM_MATER"]
        assert isinstance(mater, Concept)
        for occ_v in occurrences(command(comm, mater.name).get("AFFE_VARC")):
            field_concept = occ_v["CHAM_GD"]
            assert isinstance(field_concept, Concept)
            reference = float(occ_v["VALE_REF"])
            for occ_t in occurrences(command(comm, field_concept.name)["AFFE"]):
                value = float(occ_t["VALE"])
                rows.append(
                    [
                        concept,
                        "température",
                        " ".join(names(occ_t["GROUP_MA"])),
                        "",
                        "",
                        "",
                        value - reference,
                        "K (écart uniforme)",
                        *blank[:6],
                        f"TEMP = {number(value)} °C, "
                        f"VALE_REF = {number(reference)} °C ; "
                        f"CREA_CHAMP {field_concept.name}, AFFE_MATERIAU/AFFE_VARC "
                        f"{mater.name}",
                    ]
                )
    return rows


def _extent(
    model: Model, group: str
) -> tuple[tuple[list[float], float, str], tuple[list[float], float, str]]:
    """Start and end of a loaded cell group: coordinates and abscissae along the bar
    (member group) that carries it."""
    cells = [e for e in model.elements.values() if _cell_in_group(model, e, group)]
    if not cells:
        message = f"groupe chargé {group} sans élément de barre"
        raise ValueError(message)
    bar = cells[0].group
    members = [m for m in model.members if m.group == bar]
    offset = 0.0
    abscissa: dict[int, float] = {}
    for m in members:
        for n, s in m.abscissa.items():
            abscissa.setdefault(n, offset + s)
        offset += m.length
    nodes = {n for e in cells for n in e.nodes}
    first = min(nodes, key=lambda n: abscissa[n])
    last = max(nodes, key=lambda n: abscissa[n])
    return (
        ([geo(c) for c in model.coords[first]], abscissa[first], bar),
        ([geo(c) for c in model.coords[last]], abscissa[last], bar),
    )


def _cell_in_group(model: Model, e: Element, group: str) -> bool:
    return e.number in model.cell_groups.get(group, set())


def section_rows(model: Model) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for label, (occ, groups) in model.sections.items():
        for r in section_properties(occ):
            rows.append(
                [
                    label,
                    " ".join(groups),
                    str(occ["SECTION"]),
                    r.cara,
                    r.value,
                    r.unit,
                    r.origin,
                ]
            )
    return rows


__all__ = [
    "CASES",
    "CASE_LABELS",
    "Model",
    "build_model",
    "combination_rows",
    "connections",
    "displacement_rows",
    "element_rows",
    "result_field",
    "force_rows",
    "load_rows",
    "local_axes",
    "member_rows",
    "nodes_rows",
    "reaction_rows",
    "read_comm",
    "section_properties",
    "section_rows",
    "sha256",
    "shear_circle",
    "shear_rectangle",
    "write",
]
