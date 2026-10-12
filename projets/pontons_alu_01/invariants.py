"""Invariants of `mesh check` for PONTONS-ALU-01 (lot 50), computed from the
parameters of the Salome script only (`pontons_alu_01.geometrie`), before any run:
counts, bounding boxes and cardinalities of every group, nodes at the support points,
rigid links of exactly two nodes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pontons_alu_01.geometrie import Geometry, Member, Point, expected_counts

TOL = 1.0e-9


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


def _nodes(name: str, points: list[Point]) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "node",
        "count": len(points),
        "bbox": _bbox(points),
        "tolerance": TOL,
    }


def invariants(g: Geometry) -> dict[str, Any]:
    p = g.parameters
    span, half = p["L"], p["B"] / 2.0
    counts = expected_counts(g)
    groups: list[dict[str, Any]] = []
    for family in (
        "POUTRES_PRINC",
        "MONTANTS",
        "DIAGONALES",
        "PANNES_SEC",
        "SUPPORTS",
        "POTEAUX",
    ):
        members = g.family(family)
        groups.append(_cells(family, members))
        groups.extend(_cells(m.name, [m]) for m in members)
    groups.append(_cells("CHEVETRE", g.family("CHEVETRE")))
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
    x0, x1 = (round(x, 3) for x in p["X_ACCOSTAGE"])
    for name, member in (("ACC_YM", "PP_YM"), ("ACC_YP", "PP_YP")):
        m = g.member(member)
        pieces = list(zip(m.points, m.points[1:], m.counts, strict=False))
        inside = [
            (a, b, n) for a, b, n in pieces if a[0] >= x0 - 1e-9 and b[0] <= x1 + 1e-9
        ]
        groups.append(
            {
                "name": name,
                "kind": "cell",
                "count": sum(n for _, _, n in inside),
                "cell_type": "SEG2",
                "bbox": _bbox([q for a, b, _ in inside for q in (a, b)]),
                "tolerance": TOL,
            }
        )
    zp = g.deck_z
    apps = [(0.0, -half, zp), (0.0, half, zp)]
    feet = [h[0] for h in g.hinges]
    heads = [(span, y, p["Z_POTEAU_TETE"]) for y in p["Y_POTEAUX"]]
    bottoms = [(span, y, g.footing_z) for y in p["Y_POTEAUX"]]
    groups.append(_nodes("APP_QUAI", apps))
    groups.append(_nodes("APP_QUAI_YM", apps[:1]))
    groups.append(_nodes("APP_QUAI_YP", apps[1:]))
    groups.append(_nodes("PIEDS_SUPPORTS", feet))
    groups.append(_nodes("TETES_POTEAUX", heads))
    groups.append(_nodes("PIEDS_POTEAUX", bottoms))
    for name, y in (("AMAR_YM", -half), ("AMAR_YP", half)):
        groups.append(_nodes(name, [(x, y, zp) for x in p["X_AMARRAGE"]]))
    for i, link in enumerate(g.links, start=1):
        groups.append(_nodes(f"LR_{i:02d}", list(link)))
    for i, (foot, cap) in enumerate(g.hinges, start=1):
        groups.append(_nodes(f"ROT_S{i}", [foot]))
        groups.append(_nodes(f"ROT_C{i}", [cap]))
    every = [q for m in g.members for q in m.points]
    every += [(g.footing_x[0], g.footing_y[0], g.footing_z)]
    every += [(g.footing_x[-1], g.footing_y[-1], g.footing_z)]
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
            {"label": f"appui côté quai {k}", "point": list(a), "tolerance": TOL}
            for k, a in enumerate(apps, start=1)
        ]
        + [
            {
                "label": f"pied de poteau {k} (semelle)",
                "point": list(b),
                "tolerance": TOL,
            }
            for k, b in enumerate(bottoms, start=1)
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": 1.0e-6},
        "subsets": [
            {"group": m.name, "of": m.family}
            for m in g.members
            if m.family != "CHEVETRE"
        ]
        + [{"group": "ACC_YM", "of": "PP_YM"}, {"group": "ACC_YP", "of": "PP_YP"}],
    }


__all__ = ["invariants"]
