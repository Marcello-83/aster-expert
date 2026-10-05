"""Discretization of the jetty ESTACADE-PIEUX-01 (lot 47): parameters of the Salome
script and expected counts, computed analytically from the data, before any run.

Agent's choice (point U2, domain `maillage`): regular QUAD4 of size h in both
directions on the slab, h dividing every coordinate that a load or a group needs
(files, pile lines, lane edges, wheel prints of TS and LM2 at the steps of E8/E16),
so that every print is a union of whole cells (no pressure evaluated at nodes
across a print edge, CA-029). The slab face is cut by the lines X = X_i (the cap
beams), Y = +-2.00 (pile lines) and Y = +-1.50 (lane edges); every edge receives
the integer number of segments `length / h`, never a rounding (CLAUDE.md, lot 27).
Each pile is a polyline of one-segment edges between the levels of
`ModelValues.pile_levels` (spring nodes every 0.50 m, section breaks of B2, the
mid-plane node shared with the slab and the cap beam).

The exported MED carries the SEG2 of every edge of the partition (lot 26): the 6
lines along X (Y = -3, -2, -1.5, 1.5, 2, 3) and the 9 lines along Y (X = 0, the 7
files, X = L), plus the pile segments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from estacade_pieux_01.donnees import ModelValues

PRECISION = 1.0e-9
CONVERGENCE_SIZES = (0.1, 0.05, 0.025)
"""Mesh convergence series of the slab under a wheel (point U3): ratio 2."""
PRODUCTION_SIZE = 0.05


class DiscretisationError(ValueError):
    """A size that does not divide a required coordinate."""


def _count(length: float, size: float, label: str) -> int:
    n = round(length / size)
    if n < 1 or abs(n * size - length) > PRECISION:
        message = f"{label} : {length} m n'est pas un multiple de la taille {size} m"
        raise DiscretisationError(message)
    return int(n)


@dataclass(frozen=True)
class JettyMesh:
    values: ModelValues
    size: float

    @property
    def x_cuts(self) -> tuple[float, ...]:
        return (0.0, *self.values.x_files, self.values.length)

    @property
    def y_cuts(self) -> tuple[float, ...]:
        v = self.values
        return (
            v.y_min,
            -v.y_piles,
            v.lane[0],
            v.lane[1],
            v.y_piles,
            v.y_max,
        )

    def x_segments(self) -> tuple[int, ...]:
        cuts = self.x_cuts
        return tuple(
            _count(b - a, self.size, f"X {a}-{b}")
            for a, b in zip(cuts, cuts[1:], strict=False)
        )

    def y_segments(self) -> tuple[int, ...]:
        cuts = self.y_cuts
        return tuple(
            _count(b - a, self.size, f"Y {a}-{b}")
            for a, b in zip(cuts, cuts[1:], strict=False)
        )

    @property
    def nx(self) -> int:
        return sum(self.x_segments())

    @property
    def ny(self) -> int:
        return sum(self.y_segments())

    @property
    def pile_segments(self) -> int:
        return len(self.values.pile_levels()) - 1

    @property
    def n_piles(self) -> int:
        return len(self.values.piles())

    @property
    def nodes(self) -> int:
        return (self.nx + 1) * (self.ny + 1) + self.n_piles * self.pile_segments

    @property
    def quads(self) -> int:
        return self.nx * self.ny

    @property
    def seg2(self) -> int:
        return (
            len(self.y_cuts) * self.nx
            + len(self.x_cuts) * self.ny
            + self.n_piles * self.pile_segments
        )

    def label(self) -> str:
        return f"h{self.size:.3f}".replace(".", "p")

    def parameters(self) -> dict[str, Any]:
        """Content of the parameters file of `maillage/estacade_mesh.py`."""
        v = self.values
        sections = []
        levels = v.pile_levels()
        for s in v.sections:
            sections.append(
                {"groupe": f"PIEU_{s.name}", "haut": s.z_top, "bas": s.z_bottom}
            )
        return {
            "taille_visee": self.size,
            "z_dalle": v.z_mid,
            "x_coupes": list(self.x_cuts),
            "segments_x": list(self.x_segments()),
            "y_coupes": list(self.y_cuts),
            "segments_y": list(self.y_segments()),
            "x_files": list(v.x_files),
            "voie": list(v.lane),
            "pieux": [
                {"nom": p.name, "file": p.file, "x": p.x, "y": p.y, "famille": p.family}
                for p in v.piles()
            ],
            "cotes_pieu": list(levels),
            "troncons": sections,
            "ressorts": [
                {"groupe": s.group, "famille": s.family, "cote": s.z} for s in v.springs
            ],
        }

    def parameters_bytes(self) -> bytes:
        return (json.dumps(self.parameters(), indent=1, sort_keys=True) + "\n").encode()

    def invariants(self) -> dict[str, Any]:
        """Invariants of `aster-expert mesh check`, from the parameters only."""
        v = self.values
        tol = PRECISION
        lx, y0, y1, z = v.length, v.y_min, v.y_max, v.z_mid
        ny_lane = self.y_segments()[2]
        ny_side = self.ny - ny_lane
        levels = v.pile_levels()
        zt = v.z_tip

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

        piles = v.piles()
        xs = [p.x for p in piles]
        ys = [p.y for p in piles]
        pile_box = [min(xs), max(xs), min(ys), max(ys), zt, z]
        groups = [
            group("DALLE", "cell", self.quads, "QUAD4", [0.0, lx, y0, y1, z, z]),
            group(
                "VOIE",
                "cell",
                self.nx * ny_lane,
                "QUAD4",
                [0.0, lx, v.lane[0], v.lane[1], z, z],
            ),
            group("TROTT", "cell", self.nx * ny_side, "QUAD4", [0.0, lx, y0, y1, z, z]),
            group("RIVE_YM", "cell", self.nx, "SEG2", [0.0, lx, y0, y0, z, z]),
            group("RIVE_YP", "cell", self.nx, "SEG2", [0.0, lx, y1, y1, z, z]),
            group(
                "CHEVETRES",
                "cell",
                len(v.x_files) * self.ny,
                "SEG2",
                [v.x_files[0], v.x_files[-1], y0, y1, z, z],
            ),
            group(
                "PIEUX",
                "cell",
                len(piles) * self.pile_segments,
                "SEG2",
                pile_box,
            ),
            group("TETES", "node", len(piles), None, [*pile_box[:4], z, z]),
            group("PIEDS", "node", len(piles), None, [*pile_box[:4], zt, zt]),
            group("COIN_ABOUT", "node", 1, None, [0.0, 0.0, y0, y0, z, z]),
        ]
        for i, x in enumerate(v.x_files, start=1):
            groups.append(
                group(f"CHEV_{i}", "cell", self.ny, "SEG2", [x, x, y0, y1, z, z])
            )
        for p in piles:
            groups.append(
                group(
                    f"PIEU_{p.name}",
                    "cell",
                    self.pile_segments,
                    "SEG2",
                    [p.x, p.x, p.y, p.y, zt, z],
                )
            )
        for s in v.sections:
            n_el = sum(
                1
                for a, b in zip(levels, levels[1:], strict=False)
                if v.section_at(a, b) is s
            )
            groups.append(
                group(
                    f"PIEU_{s.name}",
                    "cell",
                    len(piles) * n_el,
                    "SEG2",
                    [*pile_box[:4], s.z_bottom, s.z_top],
                )
            )
        for spring in v.springs:
            members = [p for p in piles if p.family == spring.family]
            groups.append(
                group(
                    spring.group,
                    "node",
                    len(members),
                    None,
                    [
                        min(p.x for p in members),
                        max(p.x for p in members),
                        min(p.y for p in members),
                        max(p.y for p in members),
                        spring.z,
                        spring.z,
                    ],
                )
            )
        nodes_at = [
            {"label": f"tête {p.name}", "point": [p.x, p.y, z], "tolerance": tol}
            for p in piles
        ]
        nodes_at.append(
            {"label": "coin about", "point": [0.0, y0, z], "tolerance": tol}
        )
        all_heads = [[p.x, p.y, z] for p in piles]
        shared = [
            {
                "label": f"têtes de pieux dans {other}",
                "groups": ["TETES", other],
                "kinds": ["node", "cell"],
                "count": len(piles),
                "at": all_heads,
                "tolerance": tol,
            }
            for other in ("DALLE", "CHEVETRES", "PIEUX")
        ]
        return {
            "schema_version": 1,
            "counts": {
                "nodes": self.nodes,
                "cells": {"QUAD4": self.quads, "SEG2": self.seg2},
            },
            "bbox": [0.0, lx, y0, y1, zt, z],
            "bbox_tolerance": tol,
            "groups": groups,
            "group_areas": [
                {"group": "DALLE", "area": lx * v.width, "tolerance": 1e-9},
                {
                    "group": "VOIE",
                    "area": lx * (v.lane[1] - v.lane[0]),
                    "tolerance": 1e-9,
                },
            ],
            "nodes_at": nodes_at,
            "shared_nodes": shared,
            "no_orphan_nodes": True,
            "no_coincident_nodes": {"tolerance": tol},
            "subsets": [
                {"group": "VOIE", "of": "DALLE"},
                {"group": "TROTT", "of": "DALLE"},
            ],
            "plane_nodes": [
                {"group": "PIEDS", "axis": "z", "value": zt, "tolerance": tol},
            ],
        }


__all__ = [
    "CONVERGENCE_SIZES",
    "DiscretisationError",
    "JettyMesh",
    "PRECISION",
    "PRODUCTION_SIZE",
]
