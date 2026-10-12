"""Geometry of PONTONS-ALU-01 derived from the parameters of the Salome script (lot 50).

The parameters are written once, at the top of `maillage_pontons.py` (MM's request:
a stand-alone script he can read and edit), between `# PARAMETRES begin` and
`# PARAMETRES end`. This module reads that block without running the script (only
assignments of numbers, tuples and arithmetic on names already assigned are
accepted) and derives, independently of the script, what the trunk needs: the
expected counts and groups of `mesh check` (CLAUDE.md, « Comptages attendus »), the
rigid links and hinges of the `.comm`, the influence widths of the surface loads
(P22) and the stations of the design sections.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parent / "maillage" / "maillage_pontons.py"
BEGIN = "# PARAMETRES begin"
END = "# PARAMETRES end"

_OPERATORS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

Point = tuple[float, float, float]


class ParameterError(ValueError):
    """The parameter block of the script cannot be read."""


def _evaluate(node: ast.expr, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
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


def read_parameters(script: Path = SCRIPT) -> dict[str, Any]:
    """The assignments of the parameter block of `script`, evaluated."""
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
    return names


def grid(value: float) -> float:
    """1 mm grid, half up (the script's rule)."""
    return float(Decimal(repr(value)).quantize(Decimal("0.001"), ROUND_HALF_UP))


def point(x: float, y: float, z: float) -> Point:
    return (grid(x), grid(y), grid(z))


@dataclass(frozen=True)
class Member:
    """A continuous bar: its construction points and the number of elements of each
    piece (at most `TAILLE` long, at least `N_MIN` elements on the bar)."""

    name: str
    family: str
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
class Geometry:
    parameters: dict[str, Any]
    members: tuple[Member, ...]
    links: tuple[tuple[Point, Point], ...]
    """Rigid links (LIAISON_SOLIDE), upper (or beam) node first: groups LR_01…"""
    hinges: tuple[tuple[Point, Point], ...]
    """Support foot, cap beam node below (P18): groups ROT_Sk, ROT_Ck."""
    footing_x: tuple[float, ...]
    footing_y: tuple[float, ...]
    footing_z: float
    deck_z: float
    purlin_z: float

    def family(self, name: str) -> tuple[Member, ...]:
        return tuple(m for m in self.members if m.family == name)

    def member(self, name: str) -> Member:
        return next(m for m in self.members if m.name == name)


def _segments(length: float, size: float) -> int:
    return max(1, math.ceil(length / size - 1e-9))


def _member(name: str, family: str, pts: list[Point], p: dict[str, Any]) -> Member:
    pieces = [(a, b) for a, b in zip(pts, pts[1:], strict=False) if a != b]
    counts = [_segments(math.dist(a, b), p["TAILLE"]) for a, b in pieces]
    while sum(counts) < p["N_MIN"]:
        k = max(range(len(pieces)), key=lambda i: math.dist(*pieces[i]) / counts[i])
        counts[k] += 1
    kept = [pieces[0][0]] + [b for _, b in pieces]
    return Member(name, family, tuple(kept), tuple(counts))


@cache
def geometry(script: Path = SCRIPT) -> Geometry:
    p = read_parameters(script)
    span, half = p["L"], p["B"] / 2.0
    zp = grid(p["Z_PLAN_MOYEN"])
    zs = grid(p["Z_PLAN_MOYEN"] + p["EXC_PANNES"])

    def x_diag(d: tuple[float, float], y: float) -> float:
        return float(d[0] + (half - y) / p["B"] * (d[1] - d[0]))

    inner = [y for y in p["Y_PANNES"] if -half < y < half]
    members: list[Member] = []
    x_pp = sorted(
        {grid(x) for x in p["X_MONTANTS"]}
        | {grid(x) for d in p["DIAGONALES"] for x in d}
        | {grid(x) for x in p["X_AMARRAGE"] + p["X_ACCOSTAGE"]}
        | {0.0, grid(span)}
    )
    for name, y in (("PP_YM", -half), ("PP_YP", half)):
        members.append(
            _member(name, "POUTRES_PRINC", [point(x, y, zp) for x in x_pp], p)
        )
    for i, xm in enumerate(p["X_MONTANTS"], start=1):
        ys = {-half, half, *inner}
        if abs(xm - span) < 1e-9:
            ys |= set(p["Y_SUPPORTS"])
        members.append(
            _member(f"MONT_{i}", "MONTANTS", [point(xm, y, zp) for y in sorted(ys)], p)
        )
    for i, d in enumerate(p["DIAGONALES"], start=1):
        down = sorted({-half, half, *inner}, reverse=True)
        members.append(
            _member(
                f"DIAG_{i}",
                "DIAGONALES",
                [point(x_diag(d, y), y, zp) for y in down],
                p,
            )
        )
    crossings: dict[float, list[float]] = {}
    for yp in p["Y_PANNES"]:
        xs = {grid(x) for x in p["X_MONTANTS"]}
        xs |= {grid(x_diag(d, yp)) for d in p["DIAGONALES"]}
        crossings[yp] = sorted(xs)
    for i, yp in enumerate(p["Y_PANNES"], start=1):
        members.append(
            _member(
                f"PANNE_{i}",
                "PANNES_SEC",
                [point(x, yp, zs) for x in crossings[yp]],
                p,
            )
        )
    links = [
        (point(x, yp, zs), point(x, yp, zp))
        for yp in p["Y_PANNES"]
        for x in crossings[yp]
    ]
    for i, ys in enumerate(p["Y_SUPPORTS"], start=1):
        members.append(
            _member(
                f"SUP_{i}",
                "SUPPORTS",
                [
                    point(span, ys, p["Z_SUPPORT_BAS"]),
                    point(span, ys, p["Z_SUPPORT_HAUT"]),
                ],
                p,
            )
        )
    links += [
        (point(span, ys, p["Z_SUPPORT_HAUT"]), point(span, ys, zp))
        for ys in p["Y_SUPPORTS"]
    ]
    y_cap = sorted(
        {grid(y) for y in p["Y_CHEVETRE"] + p["Y_SUPPORTS"] + p["Y_POTEAUX"]}
        | {grid(y + s * p["D_POTEAUX"] / 2.0) for y in p["Y_POTEAUX"] for s in (-1, 1)}
    )
    lo, hi = p["Y_CHEVETRE"]
    y_cap = [y for y in y_cap if lo - 1e-9 <= y <= hi + 1e-9]
    members.append(
        _member(
            "CHEVETRE",
            "CHEVETRE",
            [point(span, y, p["Z_CHEVETRE"]) for y in y_cap],
            p,
        )
    )
    hinges = tuple(
        (point(span, ys, p["Z_SUPPORT_BAS"]), point(span, ys, p["Z_CHEVETRE"]))
        for ys in p["Y_SUPPORTS"]
    )
    for i, yc in enumerate(p["Y_POTEAUX"], start=1):
        members.append(
            _member(
                f"POT_{i}",
                "POTEAUX",
                [
                    point(span, yc, p["Z_POTEAU_PIED"]),
                    point(span, yc, p["Z_POTEAU_TETE"]),
                ],
                p,
            )
        )
    links += [
        (point(span, yc, p["Z_POTEAU_TETE"]), point(span, yc, p["Z_CHEVETRE"]))
        for yc in p["Y_POTEAUX"]
    ]
    links += [
        (point(span, yc, p["Z_POTEAU_PIED"]), point(span, yc, p["Z_SEMELLE"]))
        for yc in p["Y_POTEAUX"]
    ]
    return Geometry(
        parameters=p,
        members=tuple(members),
        links=tuple(links),
        hinges=hinges,
        footing_x=tuple(sorted({grid(x) for x in p["X_SEMELLE"]} | {grid(span)})),
        footing_y=tuple(sorted({grid(y) for y in p["Y_SEMELLE"] + p["Y_POTEAUX"]})),
        footing_z=grid(p["Z_SEMELLE"]),
        deck_z=zp,
        purlin_z=zs,
    )


def footing_divisions(g: Geometry) -> tuple[list[int], list[int]]:
    """Number of elements of each interval of the footing grid, along X then Y."""
    size = g.parameters["TAILLE"]
    nx = [
        _segments(b - a, size)
        for a, b in zip(g.footing_x, g.footing_x[1:], strict=False)
    ]
    ny = [
        _segments(b - a, size)
        for a, b in zip(g.footing_y, g.footing_y[1:], strict=False)
    ]
    return nx, ny


def expected_counts(g: Geometry) -> dict[str, int]:
    """Nodes, SEG2 and QUAD4 of the MED, computed from the parameters only."""
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
    return {
        "nodes": len(vertices) + interior + footing_nodes - len(shared),
        "SEG2": seg2 + footing_seg2,
        "QUAD4": sum(nx) * sum(ny),
    }


def influence_widths(g: Geometry) -> dict[str, float]:
    """P22: width of deck carried by each longitudinal line (main beams and purlins),
    half the distance to each neighbour, the deck stopping at the main beams' axes
    (hypothesis to be confirmed by MM: the loaded width is not given)."""
    half = g.parameters["B"] / 2.0
    lines = {"PP_YM": -half, "PP_YP": half}
    for i, y in enumerate(g.parameters["Y_PANNES"], start=1):
        lines[f"PANNE_{i}"] = y
    order = sorted(lines, key=lambda n: lines[n])
    ys = [lines[n] for n in order]
    edges = (
        [ys[0]] + [(a + b) / 2.0 for a, b in zip(ys, ys[1:], strict=False)] + [ys[-1]]
    )
    return {n: edges[k + 1] - edges[k] for k, n in enumerate(order)}


def half_deck_widths(g: Geometry) -> dict[str, float]:
    """Variant Q½ (D4): the part of each influence width with Y > 0."""
    half = g.parameters["B"] / 2.0
    lines = {"PP_YM": -half, "PP_YP": half}
    for i, y in enumerate(g.parameters["Y_PANNES"], start=1):
        lines[f"PANNE_{i}"] = y
    order = sorted(lines, key=lambda n: lines[n])
    ys = [lines[n] for n in order]
    edges = (
        [ys[0]] + [(a + b) / 2.0 for a, b in zip(ys, ys[1:], strict=False)] + [ys[-1]]
    )
    out = {}
    for k, n in enumerate(order):
        lo, hi = max(edges[k], 0.0), edges[k + 1]
        if hi > lo:
            out[n] = hi - lo
    return out


__all__ = [
    "Geometry",
    "Member",
    "ParameterError",
    "expected_counts",
    "footing_divisions",
    "geometry",
    "half_deck_widths",
    "influence_widths",
    "read_parameters",
]
