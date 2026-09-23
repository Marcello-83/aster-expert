"""Spring stiffness classes of the two subgrade-reaction bands (decision 5,
point 4; lot 28).

`aster_expert.meshing.combiwall.spring_node_areas` gives the exact, analytic
tributary area (projected on Y = 0) of every bassin-side node of each band.
This module turns that into the smallest possible set of named node groups --
nodes of *identical* stiffness are grouped together, one `CREA_POI1`/`DISCRET`
occurrence per class, never per node (lot 22, essai C; the fiche's own point 4
finding) -- and checks the sum invariant the generator must hold before writing
anything: for each band, Sigma k_i equals k_h times the band's own projected
area, to 1e-9 (in the band's native unit, MN/m).

Every group name carries the reserved prefix `GEN_` (CLAUDE.md, "Groupes
créés à l'exécution") -- never part of the mesh's own naming convention.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.generation.errors import GenerationError
from aster_expert.meshing.combiwall import Point3D, spring_node_areas

GROUP_PREFIX = "GEN_"
"""Reserved prefix for every group this module creates (CLAUDE.md)."""

_INVARIANT_TOL = 1e-9


class SpringClass(BaseModel):
    """One class of nodes sharing the identical spring stiffness."""

    model_config = ConfigDict(frozen=True)

    band: str
    group_name: str
    stiffness_mn_per_m: float
    """Nodal stiffness, in the band's own native unit (MN/m: MN/m3 x m^2)."""
    nodes: tuple[Point3D, ...]

    @property
    def stiffness_n_per_m(self) -> float:
        """SI conversion (N/m), done and commented by the generator, never
        embedded silently: 1 MN = 1e6 N."""
        return self.stiffness_mn_per_m * 1.0e6


def build_spring_classes(
    params: dict[str, Any], k_h_by_band: dict[str, float]
) -> list[SpringClass]:
    """One `SpringClass` per distinct tributary area of each band.

    `k_h_by_band` gives each band's subgrade-reaction modulus in its native
    unit (MN/m3, as the data file states it -- never converted here). Classes
    are returned sorted by (band, stiffness) for a deterministic group naming
    (`GEN_RESS_<band suffix>_<01, 02, ...>`, increasing stiffness).
    """
    areas = spring_node_areas(params)
    classes: list[SpringClass] = []
    for band, k_h in k_h_by_band.items():
        # Grouped by a rounded key (nodes related by the mesh's own mirror/rotation
        # symmetry compute to the same physical area but not always the identical
        # float, to floating-point noise from the trig involved) -- the *exact*,
        # unrounded area of one representative node is what is actually multiplied
        # by k_h, so the classification's own rounding never contaminates the
        # invariant check below with a systematic per-node bias.
        by_key: dict[float, list[tuple[Point3D, float]]] = {}
        for point, area in areas[band].items():
            by_key.setdefault(round(area, 9), []).append((point, area))
        suffix = band.removeprefix("RESS_AV_")
        for index, key in enumerate(sorted(by_key), start=1):
            members = by_key[key]
            points = tuple(sorted(p for p, _ in members))
            exact_area = members[0][1]
            classes.append(
                SpringClass(
                    band=band,
                    group_name=f"{GROUP_PREFIX}RESS_{suffix}_{index:02d}",
                    stiffness_mn_per_m=k_h * exact_area,
                    nodes=points,
                )
            )
    return classes


def check_spring_sum(
    classes: list[SpringClass],
    *,
    band: str,
    k_h: float,
    projected_width_m: float,
    projected_height_m: float,
) -> None:
    """Decision 5's own invariant, checked before any `.comm` line is written:
    Sigma k_i (this band) == k_h x width x height, to `_INVARIANT_TOL` (MN/m).
    """
    total = sum(c.stiffness_mn_per_m * len(c.nodes) for c in classes if c.band == band)
    expected = k_h * projected_width_m * projected_height_m
    gap = abs(total - expected)
    if gap > _INVARIANT_TOL:
        message = (
            f"invariant des ressorts rompu pour {band} : Sigma k_i = {total} MN/m, "
            f"attendu k_h x largeur x hauteur = {k_h} x {projected_width_m} x "
            f"{projected_height_m} = {expected} MN/m (écart {gap:g} > "
            f"{_INVARIANT_TOL:g})"
        )
        raise GenerationError(message)


__all__ = [
    "GROUP_PREFIX",
    "SpringClass",
    "build_spring_classes",
    "check_spring_sum",
]
