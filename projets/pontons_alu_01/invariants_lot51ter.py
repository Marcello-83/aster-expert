"""Invariants of `mesh check` for the whole pontoon of PONTONS-ALU-01 (lot 51 ter),
computed from the parameters of `maillage_ponton_51ter.py` only (`geometrie_lot51ter`),
before any run: counts, bounding boxes and cardinalities of every group (families,
bars, the five footings, the 42 berthing zones, the ring corners), one node in each
link, pin and cleat group, abutment supports, pile feet and cap nodes under the pins
at their points, no orphan node, no coincident nodes."""

from __future__ import annotations

from typing import Any

from pontons_alu_01.geometrie_lot51 import Point
from pontons_alu_01.geometrie_lot51ter import (
    Geometry51ter,
    expected_counts,
    footing_divisions,
)
from pontons_alu_01.invariants_lot51 import TOL, _bbox, _cells, _nodes

FAMILIES = (
    "POUTRES_PRINC",
    "MONTANTS",
    "DIAGONALES",
    "PANNES_SEC",
    "PANNE_RIVE",
    "CHEVETRES",
    "LONGRINES",
    "PILES",
)


def pieces_between(
    g: Geometry51ter, member: str, x0: float, x1: float
) -> list[tuple[Point, Point, int]]:
    """Pieces of a member (points, segments) lying between two abscissae."""
    m = g.member(member)
    return [
        (a, b, n)
        for a, b, n in zip(m.points, m.points[1:], m.counts, strict=False)
        if min(a[0], b[0]) >= x0 - 1e-9 and max(a[0], b[0]) <= x1 + 1e-9
    ]


def corner_pieces(g: Geometry51ter) -> list[tuple[Point, Point, int]]:
    out = []
    for a, c in g.corners:
        pier = next(f.pier for f in g.footings if f.xs[0] <= a[0] <= f.xs[-1])
        side = "YM" if a[1] < 0 else "YP"
        out += pieces_between(g, f"LONG_{pier}_{side}", a[0], c[0])
    return out


def invariants(g: Geometry51ter) -> dict[str, Any]:
    counts = expected_counts(g)
    groups: list[dict[str, Any]] = []
    for family in FAMILIES:
        members = g.family(family)
        groups.append(_cells(family, members))
        groups.extend(_cells(m.name, [m]) for m in members)
    corners = corner_pieces(g)
    groups.append(
        {
            "name": "ANGLES_ANNEAU",
            "kind": "cell",
            "count": sum(n for _, _, n in corners),
            "cell_type": "SEG2",
            "bbox": _bbox([q for a, b, _ in corners for q in (a, b)]),
            "tolerance": TOL,
        }
    )
    ties = g.family("LONGRINES")
    corner_set = {(a, b) for a, b, _ in corners}
    current = [
        (a, b)
        for m in ties
        for a, b in zip(m.points, m.points[1:], strict=False)
        if (a, b) not in corner_set
    ]
    groups.append(
        {
            "name": "LONGRINES_COURANT",
            "kind": "cell",
            "count": sum(m.elements for m in ties) - sum(n for _, _, n in corners),
            "cell_type": "SEG2",
            "bbox": _bbox([q for pair in current for q in pair]),
            "tolerance": TOL,
        }
    )
    quads = 0
    for f in g.footings:
        nx, ny = footing_divisions(g, f)
        quads += sum(nx) * sum(ny)
        groups.append(
            {
                "name": f.group,
                "kind": "cell",
                "count": sum(nx) * sum(ny),
                "cell_type": "QUAD4",
                "bbox": [f.xs[0], f.xs[-1], f.ys[0], f.ys[-1], f.z, f.z],
                "tolerance": TOL,
            }
        )
    groups.append(
        {
            "name": "SEMELLE",
            "kind": "cell",
            "count": quads,
            "cell_type": "QUAD4",
            "bbox": _bbox(
                [(f.xs[0], f.ys[0], f.z) for f in g.footings]
                + [(f.xs[-1], f.ys[-1], f.z) for f in g.footings]
            ),
            "tolerance": TOL,
        }
    )
    for zone in g.zones:
        inside = pieces_between(g, zone.member, zone.x0, zone.x1)
        groups.append(
            {
                "name": zone.name,
                "kind": "cell",
                "count": sum(n for _, _, n in inside),
                "cell_type": "SEG2",
                "bbox": _bbox([q for a, b, _ in inside for q in (a, b)]),
                "tolerance": TOL,
            }
        )
    for name, points in sorted(g.node_groups.items()):
        groups.append(_nodes(name, points))
    every = [q for m in g.members for q in m.points]
    for f in g.footings:
        every += [(f.xs[0], f.ys[0], f.z), (f.xs[-1], f.ys[-1], f.z)]
    feet = [lk for lk in g.links if lk.name.startswith("PS_")]
    return {
        "schema_version": 1,
        "counts": {
            "nodes": counts["nodes"],
            "cells": {"QUAD4": counts["QUAD4"], "SEG2": counts["SEG2"]},
        },
        "bbox": _bbox(every),
        "bbox_tolerance": TOL,
        "groups": groups,
        "nodes_at": [
            {
                "label": f"appui de culée {side}",
                "point": list(g.node_groups[f"APP_CULEE_{side}"][0]),
                "tolerance": TOL,
            }
            for side in ("YM", "YP")
        ]
        + [
            {
                "label": f"semelle sous le pied de pile {lk.name[3:]}",
                "point": list(lk.b),
                "tolerance": TOL,
            }
            for lk in feet
        ]
        + [
            {
                "label": f"nœud du chevêtre sous l'appui {a.name}",
                "point": list(a.cap),
                "tolerance": TOL,
            }
            for a in g.axes
            if a.cap is not None
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": 1.0e-6},
        "subsets": [{"group": m.name, "of": m.family} for m in g.members]
        + [{"group": z.name, "of": z.member} for z in g.zones]
        + [{"group": f.group, "of": "SEMELLE"} for f in g.footings]
        + [
            {"group": "ANGLES_ANNEAU", "of": "LONGRINES"},
            {"group": "LONGRINES_COURANT", "of": "LONGRINES"},
        ],
    }


__all__ = ["FAMILIES", "corner_pieces", "invariants", "pieces_between"]
