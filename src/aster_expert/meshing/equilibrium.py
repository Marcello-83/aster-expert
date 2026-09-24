"""Lot 33, étape 3 : résultante appliquée sur un groupe de coques, intégrée
sur la géométrie réelle du maillage (quadrature de Gauss), indépendamment de
Code_Aster -- jamais relue d'un résultat de calcul. Module voisin de
`aster_expert.meshing.check`/`invariants` (même structure `MedDump`).

Chaque maille QUAD4 est traitée comme un quadrilatère bilinéaire standard
(fonctions de forme à 4 nœuds) : au point de Gauss `(xi, eta)`,
`dx/dxi x dx/deta` donne le vecteur normal x élément de surface (même
formule que la matrice jacobienne d'un élément fini isoparamétrique, R3.01.01).
La force sur la maille est `-intégrale p(z) n dA` -- signe de `FORCE_COQUE/
PRES` (U4.44.01 : une pression positive pousse dans le sens contraire de la
normale).

**Orientation de la normale : déduction, non un fait catalogue.** Le MED lu
ici est celui produit par Salomé, *avant* `ORIE_NORM_COQUE` (une opération
que Code_Aster applique à son propre objet MAILLAGE en mémoire, jamais
répercutée sur le fichier MED d'origine) : l'ordre des nœuds de connectivité
de ce fichier ne donne donc aucune garantie sur le sens que Code_Aster
retiendra. La normale de chaque maille est réorientée ici par une règle
géométrique propre à ce module, jamais lue du fichier ni du calcul : sa
composante Y (repère du point 9) est rendue positive -- cohérent avec le
point 5 (`ORIE_NORM_COQUE`, référence `VECT_NORM=(0, 1, 0)`) et avec
`ECRAN_POUSSEE` qui ne porte que la moitié du tube côté terre (Y >= 0 par
rapport à l'axe du tube) : sur cette moitié, une règle radiale-sortante et
cette règle en Y coïncident."""

from __future__ import annotations

import math
from typing import Literal

from aster_expert.generation.profiles import profile_value_at
from aster_expert.meshing.invariants import MedDump

Point = tuple[float, float, float]

_GAUSS2: tuple[tuple[float, float], ...] = (
    (-1.0 / math.sqrt(3.0), 1.0),
    (1.0 / math.sqrt(3.0), 1.0),
)
"""2-point Gauss-Legendre rule on [-1, 1] per axis (4 points total on a
QUAD4): exact for the bilinear-geometry x piecewise-linear-pressure
integrand here (`quadrature fine`, explicitly allowed by this lot's own
instructions in place of Code_Aster's own, undocumented-for-FORCE_COQUE,
quadrature family)."""


def _shape(xi: float, eta: float) -> tuple[float, float, float, float]:
    return (
        (1 - xi) * (1 - eta) / 4,
        (1 + xi) * (1 - eta) / 4,
        (1 + xi) * (1 + eta) / 4,
        (1 - xi) * (1 + eta) / 4,
    )


def _dshape(
    xi: float, eta: float
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    dxi = (-(1 - eta) / 4, (1 - eta) / 4, (1 + eta) / 4, -(1 + eta) / 4)
    deta = (-(1 - xi) / 4, -(1 + xi) / 4, (1 + xi) / 4, (1 - xi) / 4)
    return dxi, deta


def _cross(a: Point, b: Point) -> Point:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Point, s: float) -> Point:
    return (a[0] * s, a[1] * s, a[2] * s)


def _weighted_sum(
    weights: tuple[float, float, float, float],
    corners: tuple[Point, Point, Point, Point],
) -> Point:
    total = (0.0, 0.0, 0.0)
    for w, c in zip(weights, corners, strict=True):
        total = _add(total, _scale(c, w))
    return total


Evaluation = Literal["gauss", "nodes"]
"""Où la fonction de pression est évaluée sur une maille : `gauss` (aux points
d'intégration, l'intégrale du profil spécifié) ou `nodes` (aux quatre nœuds,
puis interpolée par les fonctions de forme -- ce que Code_Aster fait de
`FORCE_COQUE/PRES` donnée par une fonction, fait établi par exécution au lot 34
nœud par nœud, jamais documenté : U4.44.01 dit seulement « réel ou fonction »)."""


def quad_pressure_force(
    corners: tuple[Point, Point, Point, Point],
    profile: list[tuple[float, float]],
    evaluation: Evaluation = "gauss",
) -> Point:
    """`-integral p(z) n dA` over one planar QUAD4, by 2x2 Gauss quadrature.

    The raw cross product's sign (whichever way the 4 corners happen to be
    wound in the source MED) is flipped, per facet, to make its Y component
    non-negative -- see this module's own docstring for why."""
    centroid_dxi, centroid_deta = _dshape(0.0, 0.0)
    d_dxi = _weighted_sum(centroid_dxi, corners)
    d_deta = _weighted_sum(centroid_deta, corners)
    orientation = 1.0 if _cross(d_dxi, d_deta)[1] >= 0.0 else -1.0

    force = (0.0, 0.0, 0.0)
    for xi, wx in _GAUSS2:
        for eta, weta in _GAUSS2:
            n = _shape(xi, eta)
            dxi, deta = _dshape(xi, eta)
            dx_dxi = _weighted_sum(dxi, corners)
            dx_deta = _weighted_sum(deta, corners)
            normal_da = _scale(_cross(dx_dxi, dx_deta), orientation)
            if evaluation == "nodes":
                p = sum(
                    n[i] * profile_value_at(profile, corners[i][2]) for i in range(4)
                )
            else:
                p = profile_value_at(
                    profile, sum(n[i] * corners[i][2] for i in range(4))
                )
            w = wx * weta * p
            force = _add(force, _scale(normal_da, -w))
    return force


def group_pressure_resultant(
    dump: MedDump,
    group: str,
    profile: list[tuple[float, float]],
    evaluation: Evaluation = "gauss",
) -> Point:
    """Sum of `quad_pressure_force` over every 2D cell of `group` -- every
    cell must be a QUAD4 (the only cell type `ECRAN_POUSSEE` carries, lot
    26/27)."""
    total = (0.0, 0.0, 0.0)
    found = False
    for g in dump.groups:
        if g.name != group or g.level == 1:
            continue
        found = True
        level = dump.levels[str(g.level)]
        for cell_id in g.ids:
            nodes = level.connectivity[cell_id]
            if len(nodes) != 4:
                message = (
                    f"maille non QUAD4 dans le groupe {group} : "
                    f"{len(nodes)} nœuds (cell {cell_id})"
                )
                raise ValueError(message)
            corners = (
                dump.coords[nodes[0]],
                dump.coords[nodes[1]],
                dump.coords[nodes[2]],
                dump.coords[nodes[3]],
            )
            total = _add(total, quad_pressure_force(corners, profile, evaluation))
    if not found:
        message = f"groupe absent ou sans maille de niveau 2 : {group}"
        raise ValueError(message)
    return total


__all__ = ["Evaluation", "group_pressure_resultant", "quad_pressure_force"]
