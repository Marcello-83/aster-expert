"""Generic grid invariant of `mesh check` (lot 48 bis).

« No coordinate within `epsilon` of a multiple of the grid without being on it »: a
node at `2.4999999999` or `0.30000000004` is the trace of a construction that did not
start from exact values (an angle, a division, an accumulated sum). It adds nothing,
breaks the search of nodes by coordinate and makes a group selected by a box depend on
rounding. The grid and `epsilon` come from `config/arrondis.yaml` (one table for every
rounding).

A MED stores coordinates as binary doubles of fixed size: rounding them reduces neither
the file nor the number of lines (measured, `docs/essais_lot48bis.md`); the gain is in
readability and robustness. The invariant **reports**; it fails the check only when the
table says `bloquant: true`, which is not the case while the versioned meshes carry
deviations (they are reported, not modified).
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from aster_expert.arrondis import GridRule, off_grid_noise

AXES = ("x", "y", "z")
EXAMPLES = 5


class GridExample(BaseModel):
    model_config = ConfigDict(frozen=True)

    node: int
    axis: str
    value: float
    distance: float


class GridReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    grid: float
    epsilon: float
    blocking: bool
    nodes: int
    coordinates: int
    noisy: int
    """Coordinates within `epsilon` of a grid multiple without being on it."""
    nodes_concerned: int
    max_distance: float
    examples: tuple[GridExample, ...]
    ok: bool
    """False only when the deviation blocks (`blocking`) and there is one."""

    def line(self) -> str:
        state = "écart rapporté" if self.noisy and not self.blocking else "tenu"
        if self.noisy and self.blocking:
            state = "ÉCART"
        return (
            f"[grille] grille {self.grid:g} m, epsilon {self.epsilon:g} : "
            f"{self.noisy} coordonnée(s) presque sur la grille sans y être sur "
            f"{self.coordinates} ({self.nodes_concerned} nœud(s) sur {self.nodes}), "
            f"écart maximal {self.max_distance:.3e} : {state}"
        )


def check_grid(coords: Sequence[Sequence[float]], rule: GridRule) -> GridReport:
    noisy = 0
    nodes: set[int] = set()
    worst = 0.0
    examples: list[GridExample] = []
    for node, point in enumerate(coords):
        for axis, value in zip(AXES, point, strict=False):
            distance = off_grid_noise(value, rule)
            if distance is None:
                continue
            noisy += 1
            nodes.add(node)
            worst = max(worst, distance)
            if len(examples) < EXAMPLES:
                examples.append(
                    GridExample(node=node, axis=axis, value=value, distance=distance)
                )
    return GridReport(
        grid=rule.grid,
        epsilon=rule.epsilon,
        blocking=rule.bloquant,
        nodes=len(coords),
        coordinates=sum(min(len(p), 3) for p in coords),
        noisy=noisy,
        nodes_concerned=len(nodes),
        max_distance=worst,
        examples=tuple(examples),
        ok=not (rule.bloquant and noisy),
    )


__all__ = ["GridExample", "GridReport", "check_grid"]
