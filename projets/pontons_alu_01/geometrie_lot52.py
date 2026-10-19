"""Geometry of PONTONS-ALU-01, lot 52: the PRO geometry of the whole pontoon, from the
parameters of `maillage/maillage_ponton_52.py`.

Same frame as lot 51 ter (`geometrie_lot51ter.build`: spans, piers, footings, pins,
groups), with the deck of decisions P63 to P65:

- P64, 1: posts and diagonals (tube COTE_MONTANTS) under the purlins, axis at
  Z_DESSUS − COTE_PANNES − COTE_MONTANTS / 2 (+1,29); each post welded on the flank of
  the main beams, linked to the beam node by a rigid vertical link of 0,01 m (`LM_`);
  the purlins rest on the posts and diagonals, linked by rigid links of 0,085 m (`LR_`);
- P64, 2: each diagonal welded on the posts at |Y| = B/2 − E_DIAG (0,68), the N
  pattern kept (from +Y of a post to −Y of the next one); the piece of post between the
  main beam and that node is the group MONTANTS_TRONCONS;
- P64, 3: X of the posts unchanged; the purlins are cut at the new crossings;
- P65: pin axis at +1,175 (Z_AXE of the script);
- unchanged: the edge purlin of the cantilever in the plane of the main beams (section
  of the purlins, hypothesis of lot 51 ter), the purlins of the cantilever tied at its
  end to that edge purlin.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pontons_alu_01.geometrie_lot51 import (
    SIDES,
    LoadZone,
    ParameterError,
    Point,
    _Builder,
)
from pontons_alu_01.geometrie_lot51bis import grid, point
from pontons_alu_01.geometrie_lot51ter import (
    OVERRIDABLE as OVERRIDABLE_51TER,
)
from pontons_alu_01.geometrie_lot51ter import (
    Geometry51ter,
    Span,
    build,
    read_parameters,
)
from pontons_alu_01.geometrie_lot51ter import (
    levels as levels_51ter,
)

SCRIPT = Path(__file__).resolve().parent / "maillage" / "maillage_ponton_52.py"
OVERRIDABLE = (*OVERRIDABLE_51TER, "COTE_MONTANTS", "E_DIAG")
TRONCONS = "MONTANTS_TRONCONS"
"""Group of the pieces of post between a main beam and the diagonal node (P64, 2)."""


def levels(p: dict[str, Any]) -> dict[str, float]:
    """Levels of lot 51 ter plus the axis of the posts and diagonals (P64)."""
    out = levels_51ter(p)
    out["montants"] = grid(p["Z_DESSUS"] - p["COTE_PANNES"] - p["COTE_MONTANTS"] / 2.0)
    return out


def diagonal_node(p: dict[str, Any]) -> float:
    """|Y| of the diagonal–post node (P64: B/2 − e_diag)."""
    return float(p["B"] / 2.0 - p["E_DIAG"])


def _deck(
    p: dict[str, Any], b: _Builder, all_spans: tuple[Span, ...], lv: dict[str, float]
) -> tuple[list[LoadZone], list[tuple[int, float, str]]]:
    """The deck of lot 52 (P64), zones and cleats as in lot 51 ter."""
    half = p["B"] / 2.0
    yd = diagonal_node(p)
    zp, zs, zm = lv["poutres"], lv["pannes"], lv["montants"]
    e = p["ENTRAXE_CHEVETRES"]
    inner = [y for y in p["Y_PANNES"] if -half < y < half]
    if not all(-yd < y < yd for y in inner):
        message = "panne hors de l'étendue des diagonales (|Y| < B/2 − E_DIAG)"
        raise ParameterError(message)
    ys_deck = sorted({-half, half, *inner})
    ys_post = sorted({-half, -yd, yd, half, *inner})
    ys_diag = sorted({-yd, yd, *inner})
    load_zones: list[LoadZone] = []
    cleats: list[tuple[int, float, str]] = []
    for sp in all_spans:
        x0, x1 = sp.x0, sp.x1
        if sp.nature == "grande":
            if x1 - x0 <= p["X_MONTANTS"][-1] + 1e-9:
                message = f"travée {sp.name} trop courte pour ses montants"
                raise ParameterError(message)
            posts = [x0, *(grid(x0 + x) for x in p["X_MONTANTS"]), x1]
            diagonals = list(zip(posts, posts[1:], strict=False))
            span_cleats = [grid(x0 + x) for x in p["X_TAQUETS"]]
            mid = (x0 + x1) / 2.0
            zones = [
                (f"{sp.name}D", x0, grid(x0 + p["L_ZONE"])),
                (
                    f"{sp.name}M",
                    grid(mid - p["L_ZONE"] / 2.0),
                    grid(mid + p["L_ZONE"] / 2.0),
                ),
                (f"{sp.name}F", grid(x1 - p["L_ZONE"]), x1),
            ]
        elif sp.nature == "petite":
            posts = [x0, x1]
            diagonals = [(x0, x1)]
            span_cleats = []
            k = int(sp.name[2:])
            mid = p["STATIONS"][k - 1] + e / 2.0
            zones = [
                (sp.name, grid(mid - p["L_ZONE"] / 2.0), grid(mid + p["L_ZONE"] / 2.0))
            ]
        else:
            posts = []
            diagonals = []
            span_cleats = []
            zones = [(sp.name, grid(x1 - p["L_ZONE"]), x1)]
        for x in span_cleats:
            cleats.append((len(cleats) + 1, x, sp.name))

        def x_diag(d: tuple[float, float], y: float) -> float:
            """X at y of the diagonal d = (post at +yd, next post at −yd)."""
            return float(d[0] + (yd - y) / (2.0 * yd) * (d[1] - d[0]))

        x_pp = sorted(
            set(posts)
            | {x for d in diagonals for x in d}
            | set(span_cleats)
            | {x for _, a, c in zones for x in (a, c)}
            | {x0, x1}
        )
        for side, sign in SIDES:
            name = f"PP_{sp.name}_{side}"
            b.bar(
                name,
                "POUTRES_PRINC",
                sp.name,
                [point(x, sign * half, zp) for x in x_pp],
            )
            load_zones += [LoadZone(f"ACC_{n}_{side}", name, a, c) for n, a, c in zones]
        for i, xm in enumerate(posts, start=1):
            b.bar(
                f"MONT_{sp.name}_{i}",
                "MONTANTS",
                sp.name,
                [point(xm, y, zm) for y in ys_post],
            )
            for side, sign in SIDES:
                b.link(
                    f"LM_{sp.name}_{i}_{side}",
                    "solide",
                    point(xm, sign * half, zm),
                    point(xm, sign * half, zp),
                )
        for i, d in enumerate(diagonals, start=1):
            b.bar(
                f"DIAG_{sp.name}_{i}",
                "DIAGONALES",
                sp.name,
                [point(x_diag(d, y), y, zm) for y in reversed(ys_diag)],
            )
        if sp.nature == "porte_a_faux":
            b.bar("RIVE_PF", "PANNE_RIVE", sp.name, [point(x1, y, zp) for y in ys_deck])
        for i, yp in enumerate(p["Y_PANNES"], start=1):
            if sp.nature == "porte_a_faux":
                xs = [x0, x1]
                tied = [x1]
            else:
                xs = sorted(set(posts) | {grid(x_diag(d, yp)) for d in diagonals})
                tied = xs
            b.bar(
                f"PANNE_{sp.name}_{i}",
                "PANNES_SEC",
                sp.name,
                [point(x, yp, zs) for x in xs],
            )
            for x in tied:
                b.link(
                    f"LR_{sp.name}_{i}_{xs.index(x) + 1:02d}",
                    "solide",
                    point(x, yp, zs),
                    point(x, yp, zp if sp.nature == "porte_a_faux" else zm),
                )
    return load_zones, cleats


def geometry_from(p: dict[str, Any]) -> Geometry51ter:
    return build(p, deck=_deck, lv=levels(p))


def geometry(overrides: Mapping[str, Any] | None = None) -> Geometry51ter:
    return geometry_from(read_parameters(SCRIPT, overrides, OVERRIDABLE))


def params_json(overrides: Mapping[str, Any]) -> bytes:
    """The parameter file handed to the Salome script (sorted, stable bytes)."""
    return (json.dumps(dict(sorted(overrides.items())), sort_keys=True) + "\n").encode()


def post_pieces(g: Geometry51ter) -> list[tuple[str, Point, Point, int]]:
    """(post, a, b, segments) of every piece of post between a main beam and the
    diagonal node (|Y| ≥ B/2 − e_diag): the group MONTANTS_TRONCONS."""
    yd = diagonal_node(g.parameters)
    out = []
    for m in g.family("MONTANTS"):
        for a, c, n in zip(m.points, m.points[1:], m.counts, strict=False):
            if min(abs(a[1]), abs(c[1])) >= yd - 1e-9:
                out.append((m.name, a, c, n))
    return out


__all__ = [
    "OVERRIDABLE",
    "SCRIPT",
    "TRONCONS",
    "diagonal_node",
    "geometry",
    "geometry_from",
    "levels",
    "params_json",
    "post_pieces",
]
