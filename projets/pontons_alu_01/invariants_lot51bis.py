"""Invariants of `mesh check` for a pier type and three spans of PONTONS-ALU-01 (lot 51
bis), computed from the parameters of `maillage_palee_51bis.py` only
(`geometrie_lot51bis`), before any run. Same checks as lot 51 (`invariants_lot51`):
counts, bounding boxes and cardinalities of every group, one node in each link and
bearing group, quay supports and pile feet at their points, no orphan node, no
coincident nodes. No support profile and no bearing spring any more (P44)."""

from __future__ import annotations

from typing import Any

from pontons_alu_01.geometrie_lot51 import expected_counts
from pontons_alu_01.geometrie_lot51bis import Geometry51bis
from pontons_alu_01.invariants_lot51 import TOL, _bbox, _cells, _nodes, zone_pieces

FAMILIES = (
    "POUTRES_PRINC",
    "MONTANTS",
    "DIAGONALES",
    "PANNES_SEC",
    "CHEVETRES",
    "LONGRINES",
    "PILES",
)


def invariants(g: Geometry51bis) -> dict[str, Any]:
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
        + [{"group": z.name, "of": g.member(z.member).name} for z in g.zones],
    }


__all__ = ["FAMILIES", "invariants"]
