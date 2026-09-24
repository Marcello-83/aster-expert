"""A piecewise-linear pressure profile as a Code_Aster `FORMULE`/`DEFI_FONCTION`
(decision 5, point 5; lot 28).

`DEFI_FONCTION(VERIF='CROISSANT')` (the default) refuses two points at the
same abscissa -- exactly what a layer interface in the data (two points at
the same Z, one per layer) is. The fiche's own point 5 finding doubles each
interface at Z +/- 1 mm, established safe there (no integration point of a
0.25 m-tall QUAD4, under any documented quadrature family of the reference
element, lies within 1 mm of an edge).
"""

from __future__ import annotations

_DOUBLE_OFFSET_M = 0.001


def doubled_profile(
    points: list[tuple[float, float, str | None, str | None]],
) -> list[tuple[float, float]]:
    """`(z, p)` pairs, strictly increasing in `z`: an interface (two points at
    the same `z`, one per layer) is split into `z - 1 mm` (the layer below)
    and `z + 1 mm` (the layer above), in that order. A single point at a `z`
    (no interface) is left untouched. Input points must already be sorted by
    `z`, then by their position in the source table (interface order: layer
    ending first, then layer starting) -- the data file's own row order.
    """
    by_z: dict[float, list[tuple[float, float, str | None, str | None]]] = {}
    order: list[float] = []
    for z, p, layer, component in points:
        if z not in by_z:
            by_z[z] = []
            order.append(z)
        by_z[z].append((z, p, layer, component))

    out: list[tuple[float, float]] = []
    for z in order:
        group = by_z[z]
        if len(group) == 1:
            out.append((z, group[0][1]))
        elif len(group) == 2:
            out.append((z - _DOUBLE_OFFSET_M, group[0][1]))
            out.append((z + _DOUBLE_OFFSET_M, group[1][1]))
        else:
            message = f"plus de deux points à la même cote {z:g} : interface ambiguë"
            raise ValueError(message)
    for a, b in zip(out[:-1], out[1:], strict=True):
        if not a[0] < b[0]:
            message = f"profil non strictement croissant après doublement : {a}, {b}"
            raise ValueError(message)
    return out


def component_profile(
    points: list[tuple[float, float, str | None, str | None]], component: str
) -> list[tuple[float, float, str | None, str | None]]:
    """The sub-profile of one component (`G` or `Q1`) of a table that gives both,
    in the source's own row order."""
    return [p for p in points if p[3] == component]


def profile_value_at(points: list[tuple[float, float]], z: float) -> float:
    """The profile's own value at `z`, flat beyond its own range -- the same
    extension `formule_block`'s own `DEFI_FONCTION(PROL_DROITE/PROL_GAUCHE=
    "CONSTANT")` applies inside Code_Aster."""
    if z <= points[0][0]:
        return points[0][1]
    if z >= points[-1][0]:
        return points[-1][1]
    for (z0, p0), (z1, p1) in zip(points, points[1:], strict=False):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return p0 + t * (p1 - p0)
    message = f"cote {z:g} non couverte par le profil {points}"  # pragma: no cover
    raise AssertionError(message)  # pragma: no cover


def integrate_profile(
    points: list[tuple[float, float]], z_low: float, z_high: float
) -> tuple[float, float]:
    """`(resultant, first_moment) = (integral p dz, integral p*z dz)` of the
    piecewise-linear profile through `points` (strictly increasing `z`), over
    `[z_low, z_high]`, extended flat beyond the profile's own range exactly
    as `profile_value_at` -- never extrapolated linearly, never zero by omission.

    Exact on each linear segment (a closed form, not a numerical
    approximation): for a segment `[a, b]` with values `pa, pb`, the segment
    of `integral p dz` is the trapezoid area `(pa + pb) / 2 * (b - a)`, and
    the segment of `integral p*z dz` is `a * (pa + pb) / 2 * (b - a) +
    (b - a)**2 * (pa / 6 + pb / 3)` (verified against the constant case,
    `p * (a + b) / 2 * (b - a)`, and the unit ramp, `1/3`).

    Used by `aster_expert.generation.generate` for décision 13 (lot 33,
    étape 2): the poussée/pression d'eau linéique on the crown beam, between
    the screen's own head (point 10) and the terrace level, never read by
    hand from the profile."""
    if z_low >= z_high:
        message = f"bornes non ordonnées : {z_low} >= {z_high}"
        raise ValueError(message)
    breakpoints = sorted({z_low, z_high, *(z for z, _ in points if z_low < z < z_high)})
    resultant = 0.0
    first_moment = 0.0
    for a, b in zip(breakpoints, breakpoints[1:], strict=False):
        pa, pb = profile_value_at(points, a), profile_value_at(points, b)
        length = b - a
        resultant += (pa + pb) / 2 * length
        first_moment += a * (pa + pb) / 2 * length + length**2 * (pa / 6 + pb / 3)
    return resultant, first_moment


__all__ = [
    "component_profile",
    "doubled_profile",
    "integrate_profile",
    "profile_value_at",
]
