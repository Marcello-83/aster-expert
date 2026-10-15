"""Invariants of `mesh check` for the pier and three spans of PONTONS-ALU-01 (lot 51),
computed from the parameters of `maillage_palee.py` only (`geometrie_lot51`), before
any run: counts, bounding boxes and cardinalities of every group, one node in each
link group, nodes of the quay supports and of the pile feet on the footing, no
orphan node, no coincident nodes (two linked nodes are always 1 mm apart or more)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pontons_alu_01.geometrie_lot51 import (
    Geometry51,
    Member,
    Point,
    expected_counts,
)

TOL = 1.0e-9
FAMILIES = (
    "POUTRES_PRINC",
    "MONTANTS",
    "DIAGONALES",
    "PANNES_SEC",
    "SUPPORTS",
    "NEOPRENES",
    "CHEVETRES",
    "LONGRINES",
    "PILES",
)


def _bbox(points: Iterable[Point]) -> list[float]:
    pts = list(points)
    return [
        min(p[0] for p in pts),
        max(p[0] for p in pts),
        min(p[1] for p in pts),
        max(p[1] for p in pts),
        min(p[2] for p in pts),
        max(p[2] for p in pts),
    ]


def _cells(name: str, members: Iterable[Member]) -> dict[str, Any]:
    ms = list(members)
    return {
        "name": name,
        "kind": "cell",
        "count": sum(m.elements for m in ms),
        "cell_type": "SEG2",
        "bbox": _bbox(p for m in ms for p in m.points),
        "tolerance": TOL,
    }


def _nodes(name: str, points: Iterable[Point]) -> dict[str, Any]:
    pts = list(points)
    return {
        "name": name,
        "kind": "node",
        "count": len(pts),
        "bbox": _bbox(pts),
        "tolerance": TOL,
    }


def zone_pieces(g: Geometry51, zone_name: str) -> list[tuple[Point, Point, int]]:
    zone = next(z for z in g.zones if z.name == zone_name)
    m = g.member(zone.member)
    pieces = list(zip(m.points, m.points[1:], m.counts, strict=False))
    return [
        (a, b, n)
        for a, b, n in pieces
        if a[0] >= zone.x0 - 1e-9 and b[0] <= zone.x1 + 1e-9
    ]


def invariants(g: Geometry51) -> dict[str, Any]:
    counts = expected_counts(g)
    groups: list[dict[str, Any]] = []
    for family in FAMILIES:
        members = g.family(family)
        groups.append(_cells(family, members))
        groups.extend(_cells(m.name, [m]) for m in members)
    groups.append(
        {
            "name": "SEMELLE",
            "kind": "cell",
            "count": counts["QUAD4"],
            "cell_type": "QUAD4",
            "bbox": [
                g.footing_x[0],
                g.footing_x[-1],
                g.footing_y[0],
                g.footing_y[-1],
                g.footing_z,
                g.footing_z,
            ],
            "tolerance": TOL,
        }
    )
    for zone in g.zones:
        inside = zone_pieces(g, zone.name)
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
    every += [(g.footing_x[0], g.footing_y[0], g.footing_z)]
    every += [(g.footing_x[-1], g.footing_y[-1], g.footing_z)]
    feet = [lk.b for lk in g.links if lk.name.startswith("PS_")]
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
                "label": f"appui côté quai {name}",
                "point": list(points[0]),
                "tolerance": TOL,
            }
            for name, points in (
                ("YM", g.node_groups["APP_QUAI_YM"]),
                ("YP", g.node_groups["APP_QUAI_YP"]),
            )
        ]
        + [
            {"label": f"pied de pile {k} (semelle)", "point": list(b), "tolerance": TOL}
            for k, b in enumerate(feet, start=1)
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": 1.0e-6},
        "subsets": [{"group": m.name, "of": m.family} for m in g.members]
        + [{"group": z.name, "of": g.member(z.member).name} for z in g.zones],
    }


__all__ = ["FAMILIES", "invariants", "zone_pieces"]
