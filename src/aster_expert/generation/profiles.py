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

from pydantic import BaseModel, ConfigDict

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


INTERFACE_EPSILON_M = 1.0e-9
"""Écart, de part et d'autre d'une interface de couches, entre les deux valeurs
de `layered_profile` : assez petit pour qu'aucun point d'intégration d'un
maillage réel ne s'y trouve, distinct du doublement à 1 mm de
`doubled_profile` (celui de la fonction écrite dans le `.comm`)."""


class LayerProfile(BaseModel):
    """Une couche de sol et sa pression, linéaire par morceaux sur `[z_low, z_high]`."""

    model_config = ConfigDict(frozen=True)

    name: str
    z_low: float
    z_high: float
    points: tuple[tuple[float, float], ...]
    """`(z, p)` strictement croissants en `z`, du bas de la couche à son haut."""


def layer_profiles(
    points: list[tuple[float, float, str | None, str | None]], component: str
) -> list[LayerProfile]:
    """Les couches d'un composant, de la plus basse à la plus haute. Une couche
    porte au moins deux points (un sommet intérieur est admis) ; deux couches
    voisines partagent la cote de leur interface, sans se recouvrir."""
    layers: dict[str, list[tuple[float, float]]] = {}
    for z, p, layer, comp in points:
        if comp != component:
            continue
        if layer is None:
            message = (
                f"point sans couche à la cote {z:g} : profil par couche impossible"
            )
            raise ValueError(message)
        layers.setdefault(layer, []).append((z, p))
    out: list[LayerProfile] = []
    for layer, pts in layers.items():
        if len(pts) < 2:
            message = f"la couche {layer} porte {len(pts)} point(s), 2 au moins requis"
            raise ValueError(message)
        polyline = tuple(sorted(pts))
        if not polyline[0][0] < polyline[-1][0]:
            message = f"couche {layer} d'épaisseur nulle à la cote {polyline[0][0]:g}"
            raise ValueError(message)
        if any(a[0] >= b[0] for a, b in zip(polyline[:-1], polyline[1:], strict=True)):
            message = f"couche {layer} : deux points à la même cote"
            raise ValueError(message)
        out.append(
            LayerProfile(
                name=layer,
                z_low=polyline[0][0],
                z_high=polyline[-1][0],
                points=polyline,
            )
        )
    out.sort(key=lambda layer: layer.z_low)
    for below, above in zip(out[:-1], out[1:], strict=True):
        if above.z_low < below.z_high:
            message = f"les couches {below.name} et {above.name} se recouvrent"
            raise ValueError(message)
    return out


def layered_profile(
    points: list[tuple[float, float, str | None, str | None]], component: str
) -> list[tuple[float, float]]:
    """Profil `(z, p)` strictement croissant d'un composant, construit **par
    couche** : chaque couche porte ses points et sa pression varie linéairement
    entre eux ; à l'interface entre deux couches, la valeur de la couche
    inférieure s'arrête à `z - epsilon` et celle de la couche supérieure commence
    à `z + epsilon`.

    Ne dépend ni de l'ordre des lignes du fichier de données ni du tri des
    valeurs : trier des paires `(z, p)` permute les deux points d'une interface
    quand la pression de la couche du dessus est inférieure à celle du dessous,
    et relie alors deux couches par une rampe fictive (lot 34). Sans voisin au-
    dessus ou au-dessous, une couche garde son point extrême tel quel."""
    layers = layer_profiles(points, component)
    out: list[tuple[float, float]] = []
    for i, layer in enumerate(layers):
        has_below = i > 0 and layers[i - 1].z_high == layer.z_low
        has_above = i + 1 < len(layers) and layers[i + 1].z_low == layer.z_high
        for j, (z, p) in enumerate(layer.points):
            if j == 0 and has_below:
                z += INTERFACE_EPSILON_M
            elif j == len(layer.points) - 1 and has_above:
                z -= INTERFACE_EPSILON_M
            out.append((z, p))
    for a, b in zip(out[:-1], out[1:], strict=True):
        if not a[0] < b[0]:
            message = f"profil par couche non strictement croissant : {a}, {b}"
            raise ValueError(message)
    return out


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
    "LayerProfile",
    "integrate_profile",
    "layer_profiles",
    "layered_profile",
    "profile_value_at",
]
