"""Discretization of the slab (lot 43, section B of the arbitration): parameters
of the Salomé script and expected counts, computed analytically, before any run.

The slab `0 <= x <= L`, `0 <= y <= B` is partitioned by the two lines
`x = L/2` and `y = B/2` into four faces, so that the centre is a vertex of the
geometry (the `CENTRE` node exists in every mesh) and each edge receives an
integer number of segments (CLAUDE.md, lot 27: never the rounding of a local
length). Regular QUAD4: `nx = 2 * round(L / 2 / h)`, `ny = 2 * round(B / 2 / h)`.

The exported MED also carries the SEG2 of the 1D mesh of every edge of the
partition (lot 26): the 4 sides (`2 (nx + ny)`) and the 2 inner lines
(`nx + ny`).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

PRECISION = 1.0e-9


def segment_count(length: float, size: float) -> int:
    """Nearest integer to `length / size`, at least 1 (same rule as the quay)."""
    return max(1, int(math.floor(length / size + 0.5 + 1e-9)))


@dataclass(frozen=True)
class SlabMesh:
    length: float
    width: float
    size: float

    @property
    def half_x(self) -> int:
        return segment_count(self.length / 2.0, self.size)

    @property
    def half_y(self) -> int:
        return segment_count(self.width / 2.0, self.size)

    @property
    def nx(self) -> int:
        return 2 * self.half_x

    @property
    def ny(self) -> int:
        return 2 * self.half_y

    @property
    def nodes(self) -> int:
        return (self.nx + 1) * (self.ny + 1)

    @property
    def quads(self) -> int:
        return self.nx * self.ny

    @property
    def segments(self) -> int:
        return 3 * (self.nx + self.ny)

    def parameters(self) -> dict[str, Any]:
        """Content of the parameters file of `maillage/dalle_mesh.py`."""
        return {
            "longueur": self.length,
            "largeur": self.width,
            "segments_x_demi": self.half_x,
            "segments_y_demi": self.half_y,
            "taille_visee": self.size,
        }

    def parameters_bytes(self) -> bytes:
        return (json.dumps(self.parameters(), indent=1, sort_keys=True) + "\n").encode()

    def invariants(self) -> dict[str, Any]:
        """Invariants of `aster-expert mesh check`, from the parameters only."""
        lx, ly = self.length, self.width
        tol = PRECISION

        def group(
            name: str, kind: str, count: int, cell_type: str | None, bbox: list[float]
        ) -> dict[str, Any]:
            out: dict[str, Any] = {
                "name": name,
                "kind": kind,
                "count": count,
                "bbox": bbox,
                "tolerance": tol,
            }
            if cell_type is not None:
                out["cell_type"] = cell_type
            return out

        return {
            "schema_version": 1,
            "counts": {
                "nodes": self.nodes,
                "cells": {"QUAD4": self.quads, "SEG2": self.segments},
            },
            "bbox": [0.0, lx, 0.0, ly, 0.0, 0.0],
            "bbox_tolerance": tol,
            "groups": [
                group(
                    "DALLE", "cell", self.quads, "QUAD4", [0.0, lx, 0.0, ly, 0.0, 0.0]
                ),
                group(
                    "APPUI_X0", "cell", self.ny, "SEG2", [0.0, 0.0, 0.0, ly, 0.0, 0.0]
                ),
                group("APPUI_X6", "cell", self.ny, "SEG2", [lx, lx, 0.0, ly, 0.0, 0.0]),
                group(
                    "APPUI_Y0", "cell", self.nx, "SEG2", [0.0, lx, 0.0, 0.0, 0.0, 0.0]
                ),
                group("APPUI_Y4", "cell", self.nx, "SEG2", [0.0, lx, ly, ly, 0.0, 0.0]),
                group(
                    "APPUIS",
                    "node",
                    2 * (self.nx + self.ny),
                    None,
                    [0.0, lx, 0.0, ly, 0.0, 0.0],
                ),
                group("P_A", "node", 1, None, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                group("P_B", "node", 1, None, [lx, lx, 0.0, 0.0, 0.0, 0.0]),
                group(
                    "CENTRE",
                    "node",
                    1,
                    None,
                    [lx / 2, lx / 2, ly / 2, ly / 2, 0.0, 0.0],
                ),
            ],
            "group_areas": [{"group": "DALLE", "area": lx * ly, "tolerance": 1e-9}],
            "nodes_at": [
                {"label": "coin A", "point": [0.0, 0.0, 0.0], "tolerance": tol},
                {"label": "coin B", "point": [lx, 0.0, 0.0], "tolerance": tol},
                {"label": "centre", "point": [lx / 2, ly / 2, 0.0], "tolerance": tol},
                {"label": "coin opposé", "point": [lx, ly, 0.0], "tolerance": tol},
            ],
            "shared_nodes": [
                {
                    "label": "coin A dans les appuis",
                    "groups": ["P_A", "APPUIS"],
                    "kinds": ["node", "node"],
                    "count": 1,
                    "at": [[0.0, 0.0, 0.0]],
                    "tolerance": tol,
                },
                {
                    "label": "coin B dans les appuis",
                    "groups": ["P_B", "APPUIS"],
                    "kinds": ["node", "node"],
                    "count": 1,
                    "at": [[lx, 0.0, 0.0]],
                    "tolerance": tol,
                },
                {
                    "label": "centre dans la dalle",
                    "groups": ["CENTRE", "DALLE"],
                    "kinds": ["node", "cell"],
                    "count": 1,
                    "at": [[lx / 2, ly / 2, 0.0]],
                    "tolerance": tol,
                },
            ],
            "no_orphan_nodes": True,
            "no_coincident_nodes": {"tolerance": tol},
        }


__all__ = ["PRECISION", "SlabMesh", "segment_count"]
