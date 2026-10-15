"""Geometry of PONTONS-ALU-01, lot 51: the complete pier (« palée ») and three spans,
from the parameters of `maillage/maillage_palee.py`.

The parameters are written once, at the top of the Salome script (MM's request: a
stand-alone script he can read and edit), between `# PARAMETRES begin` and
`# PARAMETRES end`; a variant changes some of them through the parameter file passed
to the script (`args:<params.json>,<sortie.med>`, only `H_PILES` in this lot). This
module reads that block without running the script and builds, independently of the
script, what the trunk and the generator need: members and their discretisation,
links between distinct nodes, node and load groups, the footing grid, the influence
widths of the surface loads (P22) and the expected counts of `mesh check`.

Model (consigne of lot 51, § 1): span 1 (X = 0 to L), the small span between the two
cap beams, span 2 (X = X_PALEE[1] to X_PALEE[1] + L); the pier: four piles, two cap
beams (C1, C2) and two ties (« longrines », L−, L+) of reinforced concrete, footing on
springs; six bearings (support profile, then elastomeric bearing) under the main beams
at the two cap beams and at the far end of span 2. Two nodes that a link joins are
always distinct: the small span and the ties stop `JEU` (1 mm) short of the node they
are linked to, and the bearing spring is a 1 mm SEG2 (U2.02.03: the length of a
discrete element plays no part in its response).
"""

from __future__ import annotations

import ast
import json
import math
import operator
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parent / "maillage" / "maillage_palee.py"
BEGIN = "# PARAMETRES begin"
END = "# PARAMETRES end"
OVERRIDABLE = ("H_PILES",)
"""Parameters a variant may change through the parameter file."""

_OPERATORS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

Point = tuple[float, float, float]
SIDES = (("YM", -1.0), ("YP", 1.0))
SPANS = ("T1", "PT", "T2")


class ParameterError(ValueError):
    """The parameter block cannot be read, or an override is not admitted."""


def _evaluate(node: ast.expr, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float | str):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(_evaluate(e, names) for e in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand, names)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](
            _evaluate(node.left, names), _evaluate(node.right, names)
        )
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    message = f"expression non admise dans les paramètres : {ast.unparse(node)}"
    raise ParameterError(message)


def read_parameters(
    script: Path = SCRIPT, overrides: Mapping[str, float] | None = None
) -> dict[str, Any]:
    """The assignments of the parameter block, evaluated, then the overrides."""
    lines = script.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(BEGIN))
        end = next(i for i, line in enumerate(lines) if line.startswith(END))
    except StopIteration as exc:
        message = f"{script.name} : bloc {BEGIN!r} … {END!r} absent"
        raise ParameterError(message) from exc
    names: dict[str, Any] = {}
    for statement in ast.parse("\n".join(lines[start + 1 : end])).body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            message = f"instruction non admise : {ast.unparse(statement)}"
            raise ParameterError(message)
        names[statement.targets[0].id] = _evaluate(statement.value, names)
    for key, value in (overrides or {}).items():
        if key not in OVERRIDABLE:
            message = f"paramètre {key} non modifiable par une variante"
            raise ParameterError(message)
        names[key] = float(value)
    return names


def grid(value: float) -> float:
    """1 mm grid, half up (the script's rule)."""
    return float(Decimal(repr(value)).quantize(Decimal("0.001"), ROUND_HALF_UP)) + 0.0


def point(x: float, y: float, z: float) -> Point:
    return (grid(x), grid(y), grid(z))


@dataclass(frozen=True)
class Member:
    """A continuous bar: its construction points and the number of elements of each
    piece (at most `TAILLE`, at least `N_MIN` elements on the bar, one for a bearing
    spring)."""

    name: str
    family: str
    span: str
    points: tuple[Point, ...]
    counts: tuple[int, ...]

    @property
    def elements(self) -> int:
        return sum(self.counts)

    @property
    def length(self) -> float:
        return sum(
            math.dist(p, q) for p, q in zip(self.points, self.points[1:], strict=False)
        )


@dataclass(frozen=True)
class Link:
    """Two distinct nodes joined in the `.comm` (single-node groups `<name>_A`,
    `<name>_B`); `kind` says how (`solide`, `bras`, `eclissage`, `tete_pile`,
    `longrine`), the variant decides the rest."""

    name: str
    kind: str
    a: Point
    b: Point


@dataclass(frozen=True)
class LoadZone:
    """Elements of one main beam between two abscissae (berthing zones)."""

    name: str
    member: str
    x0: float
    x1: float


@dataclass(frozen=True)
class Geometry51:
    parameters: dict[str, Any]
    members: tuple[Member, ...]
    links: tuple[Link, ...]
    node_groups: dict[str, tuple[Point, ...]]
    zones: tuple[LoadZone, ...]
    footing_x: tuple[float, ...]
    footing_y: tuple[float, ...]
    footing_z: float
    deck_z: float
    purlin_z: float
    spans: dict[str, tuple[float, float]] = field(default_factory=dict)

    def family(self, name: str) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.family == name)

    def member(self, name: str) -> Member:
        return next(m for m in self.members if m.name == name)

    def link(self, name: str) -> Link:
        return next(lk for lk in self.links if lk.name == name)


def segments(length: float, size: float) -> int:
    return max(1, math.ceil(length / size - 1e-9))


def _member(
    name: str, family: str, span: str, pts: list[Point], p: dict[str, Any]
) -> Member:
    pieces = [(a, b) for a, b in zip(pts, pts[1:], strict=False) if a != b]
    counts = [segments(math.dist(a, b), p["TAILLE"]) for a, b in pieces]
    minimum = 1 if family == "NEOPRENES" else p["N_MIN"]
    while sum(counts) < minimum:
        k = max(range(len(pieces)), key=lambda i: math.dist(*pieces[i]) / counts[i])
        counts[k] += 1
    kept = [pieces[0][0]] + [b for _, b in pieces]
    return Member(name, family, span, tuple(kept), tuple(counts))


def zone_names(p: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(n) for n in p["NOMS_ZONES"])


def span_bounds(p: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Abscissae of the ends of each span's bars (the small span stops JEU short of
    the cap beam axes)."""
    x1, x2 = p["X_PALEE"]
    return {
        "T1": (0.0, grid(p["L"])),
        "PT": (grid(x1 + p["JEU"]), grid(x2 - p["JEU"])),
        "T2": (grid(x2), grid(x2 + p["L"])),
    }


@dataclass
class _Builder:
    p: dict[str, Any]
    members: list[Member] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    node_groups: dict[str, tuple[Point, ...]] = field(default_factory=dict)

    def bar(self, name: str, family: str, span: str, pts: list[Point]) -> None:
        self.members.append(_member(name, family, span, pts, self.p))

    def link(self, name: str, kind: str, a: Point, b: Point) -> None:
        if a == b:
            message = f"liaison {name} : nœuds confondus"
            raise ParameterError(message)
        self.links.append(Link(name, kind, a, b))
        self.node_groups[f"{name}_A"] = (a,)
        self.node_groups[f"{name}_B"] = (b,)


def build(p: dict[str, Any]) -> Geometry51:
    half = p["B"] / 2.0
    zp = grid(p["Z_PLAN_MOYEN"])
    zs = grid(p["Z_PLAN_MOYEN"] + p["EXC_PANNES"])
    bounds = span_bounds(p)
    x_c1, x_c2 = (grid(x) for x in p["X_PALEE"])
    inner = [y for y in p["Y_PANNES"] if -half < y < half]
    b = _Builder(p)

    def x_diag(d: tuple[float, float], y: float) -> float:
        """Abscissa at y of the diagonal d = (x at +B/2, x at −B/2)."""
        return float(d[0] + (half - y) / p["B"] * (d[1] - d[0]))

    zones = tuple(
        (str(n), float(z[0]), float(z[1]))
        for n, z in zip(zone_names(p), p["ZONES_ACCOSTAGE"], strict=True)
    )
    taquets: list[float] = []
    load_zones: list[LoadZone] = []
    for span in SPANS:
        x0, x1 = bounds[span]
        if span == "PT":
            montants = [x0, x1]
            diagonals = [(x0, x1)]
        else:
            montants = [grid(x0 + x) for x in p["X_MONTANTS"]]
            diagonals = [(grid(x0 + a), grid(x0 + c)) for a, c in p["DIAGONALES"]]
            taquets += [grid(x0 + x) for x in p["X_TAQUETS"]]
        in_span = [
            (n, grid(a), grid(c)) for n, a, c in zones if x0 <= a and c <= x1 + 1e-9
        ]
        x_pp = sorted(
            set(montants)
            | {x for d in diagonals for x in d}
            | {grid(x0 + x) for x in p["X_TAQUETS"] if span != "PT"}
            | {x for _, a, c in in_span for x in (a, c)}
            | {x0, x1}
        )
        for side, sign in SIDES:
            name = f"PP_{span}_{side}"
            b.bar(
                name, "POUTRES_PRINC", span, [point(x, sign * half, zp) for x in x_pp]
            )
            load_zones += [
                LoadZone(f"ACC_{n}_{side}", name, a, c) for n, a, c in in_span
            ]
        for i, xm in enumerate(montants, start=1):
            ys = sorted({-half, half, *inner})
            b.bar(
                f"MONT_{span}_{i}",
                "MONTANTS",
                span,
                [point(xm, y, zp) for y in ys],
            )
        for i, d in enumerate(diagonals, start=1):
            down = sorted({-half, half, *inner}, reverse=True)
            b.bar(
                f"DIAG_{span}_{i}",
                "DIAGONALES",
                span,
                [point(x_diag(d, y), y, zp) for y in down],
            )
        for i, yp in enumerate(p["Y_PANNES"], start=1):
            xs = sorted(set(montants) | {grid(x_diag(d, yp)) for d in diagonals})
            b.bar(
                f"PANNE_{span}_{i}",
                "PANNES_SEC",
                span,
                [point(x, yp, zs) for x in xs],
            )
            for x in xs:
                b.link(
                    f"LR_{span}_{i}_{xs.index(x) + 1:02d}",
                    "solide",
                    point(x, yp, zs),
                    point(x, yp, zp),
                )
    # Bearings (P38, P39): support profile, 1 mm spring, arm to the main beam node.
    bearings = {
        "A1": (x_c1, "T1", bounds["T1"][1]),
        "A2": (x_c2, "T2", bounds["T2"][0]),
        "A3": (bounds["T2"][1], "T2", bounds["T2"][1]),
    }
    z_neo = grid(p["Z_SUPPORT_HAUT"] + p["EP_NEOPRENE"])
    for name, (x, _, x_beam) in bearings.items():
        for side, sign in SIDES:
            y = sign * half
            b.bar(
                f"SUP_{name}_{side}",
                "SUPPORTS",
                "PALEE" if name != "A3" else "T2",
                [point(x, y, p["Z_SUPPORT_BAS"]), point(x, y, p["Z_SUPPORT_HAUT"])],
            )
            b.bar(
                f"NEO_{name}_{side}",
                "NEOPRENES",
                "PALEE" if name != "A3" else "T2",
                [point(x, y, p["Z_SUPPORT_HAUT"]), point(x, y, z_neo)],
            )
            b.link(
                f"BR_{name}_{side}", "bras", point(x, y, z_neo), point(x_beam, y, zp)
            )
            b.node_groups[f"NB_{name}_{side}"] = (point(x, y, p["Z_SUPPORT_HAUT"]),)
            if name != "A3":
                cap = "C1" if name == "A1" else "C2"
                b.link(
                    f"SC_{cap}_{side}",
                    "solide",
                    point(x, y, p["Z_SUPPORT_BAS"]),
                    point(x, y, p["Z_ANNEAU"]),
                )
    # Splices (P42): end of span 1 and start of the small span, end of the small span
    # and start of span 2.
    for side, sign in SIDES:
        y = sign * half
        b.link(
            f"EC_A1_{side}",
            "eclissage",
            point(bounds["T1"][1], y, zp),
            point(bounds["PT"][0], y, zp),
        )
        b.link(
            f"EC_A2_{side}",
            "eclissage",
            point(bounds["T2"][0], y, zp),
            point(bounds["PT"][1], y, zp),
        )
    # Ring (P40, P43): cap beams C1, C2 along Y, ties along X stopping JEU short.
    y_cap = sorted(
        {grid(y) for y in (*p["Y_CHEVETRE"], *p["Y_APPUIS"], *p["Y_PILES"], 0.0)}
        | {grid(y + s * p["D_PILES"] / 2.0) for y in p["Y_PILES"] for s in (-1, 1)}
    )
    lo, hi = p["Y_CHEVETRE"]
    y_cap = [y for y in y_cap if lo - 1e-9 <= y <= hi + 1e-9]
    za = grid(p["Z_ANNEAU"])
    for cap, x in (("C1", x_c1), ("C2", x_c2)):
        b.bar(f"CHEV_{cap}", "CHEVETRES", "PALEE", [point(x, y, za) for y in y_cap])
    xl = sorted(
        {
            bounds["PT"][0],
            bounds["PT"][1],
            grid(x_c1 + p["D_PILES"] / 2.0),
            grid(x_c2 - p["D_PILES"] / 2.0),
            grid((x_c1 + x_c2) / 2.0),
        }
    )
    z_head = grid(p["Z_PILE_TETE"])
    z_foot = grid(p["Z_PILE_TETE"] - p["H_PILES"])
    z_footing = grid(p["Z_PILE_TETE"] - p["H_PILES"] - p["EP_SEMELLE"] / 2.0)
    for (side, _), y in zip(SIDES, p["Y_PILES"], strict=True):
        b.bar(f"LONG_{side}", "LONGRINES", "PALEE", [point(x, y, za) for x in xl])
    for cap, x, x_tie in (("C1", x_c1, xl[0]), ("C2", x_c2, xl[-1])):
        for (side, _), y in zip(SIDES, p["Y_PILES"], strict=True):
            b.bar(
                f"PILE_{cap}_{side}",
                "PILES",
                "PALEE",
                [point(x, y, z_foot), point(x, y, z_head)],
            )
            b.link(
                f"TP_{cap}_{side}", "tete_pile", point(x, y, z_head), point(x, y, za)
            )
            b.link(f"LG_{cap}_{side}", "longrine", point(x_tie, y, za), point(x, y, za))
            b.link(
                f"PS_{cap}_{side}",
                "solide",
                point(x, y, z_foot),
                point(x, y, z_footing),
            )
    groups = b.node_groups
    groups["TETES_PILES"] = tuple(lk.a for lk in b.links if lk.name.startswith("TP_"))
    groups["PIEDS_PILES"] = tuple(lk.a for lk in b.links if lk.name.startswith("PS_"))
    groups["APP_QUAI_YM"] = (point(0.0, -half, zp),)
    groups["APP_QUAI_YP"] = (point(0.0, half, zp),)
    groups["APP_QUAI"] = groups["APP_QUAI_YM"] + groups["APP_QUAI_YP"]
    groups["APP_FIXE"] = tuple(
        point(bounds["T2"][1], s * half, p["Z_SUPPORT_BAS"]) for _, s in SIDES
    )
    for k, x in enumerate(taquets, start=1):
        for side, sign in SIDES:
            groups[f"TQ{k}_{side}"] = (point(x, sign * half, zp),)
    footing_x = tuple(sorted({grid(x) for x in (*p["X_SEMELLE"], x_c1, x_c2)}))
    footing_y = tuple(sorted({grid(y) for y in (*p["Y_SEMELLE"], *p["Y_PILES"])}))
    return Geometry51(
        parameters=p,
        members=tuple(b.members),
        links=tuple(b.links),
        node_groups=groups,
        zones=tuple(load_zones),
        footing_x=footing_x,
        footing_y=footing_y,
        footing_z=z_footing,
        deck_z=zp,
        purlin_z=zs,
        spans=bounds,
    )


def geometry(overrides: Mapping[str, float] | None = None) -> Geometry51:
    return build(read_parameters(SCRIPT, overrides))


def params_json(overrides: Mapping[str, float]) -> bytes:
    """The parameter file handed to the Salome script (sorted, stable bytes)."""
    return (json.dumps(dict(sorted(overrides.items())), sort_keys=True) + "\n").encode()


def footing_divisions(g: Geometry51) -> tuple[list[int], list[int]]:
    size = g.parameters["TAILLE"]
    nx = [
        segments(b - a, size)
        for a, b in zip(g.footing_x, g.footing_x[1:], strict=False)
    ]
    ny = [
        segments(b - a, size)
        for a, b in zip(g.footing_y, g.footing_y[1:], strict=False)
    ]
    return nx, ny


def footing_stations(g: Geometry51) -> tuple[list[float], list[float]]:
    nx, ny = footing_divisions(g)

    def stations(bounds: tuple[float, ...], counts: list[int]) -> list[float]:
        out = [bounds[0]]
        for (a, b), n in zip(
            zip(bounds, bounds[1:], strict=False), counts, strict=False
        ):
            out += [a + (b - a) * k / n for k in range(1, n + 1)]
        return out

    return stations(g.footing_x, nx), stations(g.footing_y, ny)


def expected_counts(g: Geometry51) -> dict[str, int]:
    """Nodes, SEG2 and QUAD4 of the MED, from the parameters only."""
    vertices: set[Point] = set()
    seg2 = 0
    interior = 0
    for m in g.members:
        vertices.update(m.points)
        seg2 += m.elements
        interior += m.elements - (len(m.points) - 1)
    nx, ny = footing_divisions(g)
    footing_nodes = (sum(nx) + 1) * (sum(ny) + 1)
    footing_seg2 = len(g.footing_y) * sum(nx) + len(g.footing_x) * sum(ny)
    shared = {
        v
        for v in vertices
        if abs(v[2] - g.footing_z) < 1e-9
        and g.footing_x[0] <= v[0] <= g.footing_x[-1]
        and g.footing_y[0] <= v[1] <= g.footing_y[-1]
    }
    linked = {p for lk in g.links for p in (lk.a, lk.b)}
    orphans = {
        p for p in linked if p not in vertices and abs(p[2] - g.footing_z) > 1e-9
    }
    if orphans:
        message = f"nœuds de liaison hors de toute barre : {sorted(orphans)[:3]}"
        raise ParameterError(message)
    return {
        "nodes": len(vertices) + interior + footing_nodes - len(shared),
        "SEG2": seg2 + footing_seg2,
        "QUAD4": sum(nx) * sum(ny),
    }


def _strips(g: Geometry51) -> tuple[list[str], list[float]]:
    """Longitudinal lines of a span sorted by Y and the edges of their strips (P22,
    P24: deck of 2,00 m, main beams at the edges)."""
    half = g.parameters["B"] / 2.0
    deck = g.parameters["LARGEUR_TABLIER"] / 2.0
    lines = {"PP_YM": -half, "PP_YP": half}
    for i, y in enumerate(g.parameters["Y_PANNES"], start=1):
        lines[f"PANNE_{i}"] = y
    order = sorted(lines, key=lambda n: lines[n])
    ys = [lines[n] for n in order]
    edges = [-deck] + [(a + b) / 2.0 for a, b in zip(ys, ys[1:], strict=False)] + [deck]
    return order, edges


def _line_member(line: str, span: str) -> str:
    kind, rest = line.split("_", 1)
    return f"{kind}_{span}_{rest}"


def influence_widths(g: Geometry51, span: str) -> dict[str, float]:
    """Width of deck carried by each longitudinal member of `span`."""
    order, edges = _strips(g)
    return {_line_member(n, span): edges[k + 1] - edges[k] for k, n in enumerate(order)}


def half_deck_widths(g: Geometry51, span: str) -> dict[str, float]:
    """Variant Q½ (D4): the part of each influence width with Y > 0."""
    order, edges = _strips(g)
    out = {}
    for k, n in enumerate(order):
        lo, hi = max(edges[k], 0.0), edges[k + 1]
        if hi > lo:
            out[_line_member(n, span)] = hi - lo
    return out


__all__ = [
    "SIDES",
    "SPANS",
    "Geometry51",
    "Link",
    "LoadZone",
    "Member",
    "ParameterError",
    "build",
    "expected_counts",
    "footing_divisions",
    "footing_stations",
    "geometry",
    "grid",
    "half_deck_widths",
    "influence_widths",
    "params_json",
    "read_parameters",
    "span_bounds",
    "zone_names",
]
