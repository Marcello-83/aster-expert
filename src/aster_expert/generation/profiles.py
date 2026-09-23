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


__all__ = ["component_profile", "doubled_profile"]
