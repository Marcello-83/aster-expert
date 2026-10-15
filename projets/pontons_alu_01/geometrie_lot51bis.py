"""Geometry of PONTONS-ALU-01, lot 51 bis: one pier type and three spans, from the
parameters of `maillage/maillage_palee_51bis.py`.

As in lot 51 (`geometrie_lot51`), the parameters are written once, at the top of the
Salome script, and read here without running it; a variant changes `H_ANNEAU` and
`H_PILES` through the parameter file. What changes from lot 51 (decisions P44 to P48):

- deck raised by 0,50 m (P47); the derived levels (bearing axis, top of the cap beam,
  ring axis, pile heads, footing) are computed here as in the script, on the 1 mm grid;
- no support profile and no elastomeric bearing: each bearing is a pin (P44) whose axis
  is not a mesh node. It joins the ends of the main beams that meet there (`ears`: the
  long span first, then the small span) and, at the cap beams, the cap beam node under
  the bearing (`cap`); at X = 14,02 the pin sits on a fixed support;
- footing 2,60 × 2,60 × 0,20 m centred on the piles (P48).

Everything else (spans, bracing, purlins, zones, cleats, ring and pile layout, links of
the purlins, pile heads, ties and pile feet) is built as in lot 51.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from pontons_alu_01.geometrie_lot51 import (
    SIDES,
    SPANS,
    Geometry51,
    LoadZone,
    ParameterError,
    Point,
    _Builder,
    _evaluate,
    zone_names,
)

SCRIPT = Path(__file__).resolve().parent / "maillage" / "maillage_palee_51bis.py"
BEGIN = "# PARAMETRES begin"
END = "# PARAMETRES end"
OVERRIDABLE = ("H_ANNEAU", "H_PILES")
"""Parameters a variant may change through the parameter file."""
BEARINGS = ("A1", "A2", "A3")


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
    """1 mm grid, half up, after removing the binary noise (the script's rule)."""
    exact = Decimal(repr(round(value, 9)))
    return float(exact.quantize(Decimal("0.001"), ROUND_HALF_UP)) + 0.0


def point(x: float, y: float, z: float) -> Point:
    return (grid(x), grid(y), grid(z))


@dataclass(frozen=True)
class Axis:
    """A pin bearing (P44): the beam ends it joins, the cap beam node under it (none
    at X = 14,02, fixed support), the point of its axis, and whether it blocks Y."""

    name: str
    bearing: str
    side: str
    ears: tuple[Point, ...]
    cap: Point | None
    pin: Point
    blocks_y: bool

    def ear_group(self, k: int) -> str:
        return f"AX_{self.name}_{k}"

    @property
    def cap_group(self) -> str:
        return f"AX_{self.name}_K"


@dataclass(frozen=True)
class Geometry51bis(Geometry51):
    axes: tuple[Axis, ...] = ()
    levels: dict[str, float] = field(default_factory=dict)

    def axis(self, name: str) -> Axis:
        return next(a for a in self.axes if a.name == name)


def levels(p: dict[str, Any]) -> dict[str, float]:
    """Levels of lot 51 bis (m NGF), as the script computes them (P47, P48)."""
    zp = grid(p["Z_PLAN_MOYEN"])
    axis = grid(zp - p["H_POUTRES"] / 2.0 - p["DESCENTE_AXE"])
    top = grid(axis - p["H_CHAPE"])
    head = grid(top - p["H_ANNEAU"])
    foot = grid(head - p["H_PILES"])
    return {
        "plan_moyen": zp,
        "pannes": grid(p["Z_PLAN_MOYEN"] + p["EXC_PANNES"]),
        "sous_face_poutres": grid(zp - p["H_POUTRES"] / 2.0),
        "axe_appui": axis,
        "dessus_chevetre": top,
        "axe_anneau": grid(top - p["H_ANNEAU"] / 2.0),
        "sous_face_anneau": head,
        "tete_piles": head,
        "dessus_semelle": foot,
        "plan_moyen_semelle": grid(foot - p["EP_SEMELLE"] / 2.0),
        "dessous_semelle": grid(foot - p["EP_SEMELLE"]),
    }


def span_bounds(p: dict[str, Any]) -> dict[str, tuple[float, float]]:
    x1, x2 = p["X_PALEE"]
    return {
        "T1": (0.0, grid(p["L"])),
        "PT": (grid(x1 + p["JEU"]), grid(x2 - p["JEU"])),
        "T2": (grid(x2), grid(x2 + p["L"])),
    }


def build(p: dict[str, Any]) -> Geometry51bis:  # noqa: PLR0915 -- même trame que le script
    half = p["B"] / 2.0
    lv = levels(p)
    zp, zs = lv["plan_moyen"], lv["pannes"]
    bounds = span_bounds(p)
    x_c1, x_c2 = (grid(x) for x in p["X_PALEE"])
    inner = [y for y in p["Y_PANNES"] if -half < y < half]
    b = _Builder(p)

    def x_diag(d: tuple[float, float], y: float) -> float:
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
            b.bar(f"MONT_{span}_{i}", "MONTANTS", span, [point(xm, y, zp) for y in ys])
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
                f"PANNE_{span}_{i}", "PANNES_SEC", span, [point(x, yp, zs) for x in xs]
            )
            for x in xs:
                b.link(
                    f"LR_{span}_{i}_{xs.index(x) + 1:02d}",
                    "solide",
                    point(x, yp, zs),
                    point(x, yp, zp),
                )
    # Pin bearings (P44): ears = beam ends meeting at the axis, cap = cap beam node.
    za = lv["axe_anneau"]
    layout = {
        "A1": (x_c1, (bounds["T1"][1], bounds["PT"][0]), True),
        "A2": (x_c2, (bounds["T2"][0], bounds["PT"][1]), True),
        "A3": (bounds["T2"][1], (bounds["T2"][1],), False),
    }
    axes: list[Axis] = []
    for name, (x, ears, on_cap) in layout.items():
        for side, sign in SIDES:
            y = sign * half
            axis = Axis(
                name=f"{name}_{side}",
                bearing=name,
                side=side,
                ears=tuple(point(xe, y, zp) for xe in ears),
                cap=point(x, y, za) if on_cap else None,
                pin=point(x, y, lv["axe_appui"]),
                blocks_y=side == "YP",
            )
            axes.append(axis)
            for k, ear in enumerate(axis.ears, start=1):
                b.node_groups[axis.ear_group(k)] = (ear,)
            if axis.cap is not None:
                b.node_groups[axis.cap_group] = (axis.cap,)
    # Ring (P48): cap beams C1, C2 along Y, ties along X stopping JEU short.
    y_cap = sorted(
        {grid(y) for y in (*p["Y_CHEVETRE"], *p["Y_APPUIS"], *p["Y_PILES"], 0.0)}
        | {grid(y + s * p["D_PILES"] / 2.0) for y in p["Y_PILES"] for s in (-1, 1)}
    )
    lo, hi = p["Y_CHEVETRE"]
    y_cap = [y for y in y_cap if lo - 1e-9 <= y <= hi + 1e-9]
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
    z_head, z_foot = lv["tete_piles"], lv["dessus_semelle"]
    z_footing = lv["plan_moyen_semelle"]
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
    groups["APP_A3"] = tuple(point(bounds["T2"][1], s * half, zp) for _, s in SIDES)
    for k, x in enumerate(taquets, start=1):
        for side, sign in SIDES:
            groups[f"TQ{k}_{side}"] = (point(x, sign * half, zp),)
    footing_x = tuple(sorted({grid(x) for x in (*p["X_SEMELLE"], x_c1, x_c2)}))
    footing_y = tuple(sorted({grid(y) for y in (*p["Y_SEMELLE"], *p["Y_PILES"])}))
    return Geometry51bis(
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
        axes=tuple(axes),
        levels=lv,
    )


def geometry(overrides: Mapping[str, float] | None = None) -> Geometry51bis:
    return build(read_parameters(SCRIPT, overrides))


def params_json(overrides: Mapping[str, float]) -> bytes:
    """The parameter file handed to the Salome script (sorted, stable bytes)."""
    return (json.dumps(dict(sorted(overrides.items())), sort_keys=True) + "\n").encode()


__all__ = [
    "BEARINGS",
    "OVERRIDABLE",
    "SCRIPT",
    "Axis",
    "Geometry51bis",
    "build",
    "geometry",
    "grid",
    "levels",
    "params_json",
    "read_parameters",
    "span_bounds",
]
