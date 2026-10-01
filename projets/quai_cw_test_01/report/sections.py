"""Efforts d'ensemble d'un tube vu comme une poutre (lot 37).

La synthèse donne les efforts de coque par mètre de largeur (`NXX`, `NXY`, `QX`,
`MXX` de `EFGE_ELNO`). L'effort utile de l'ingénieur est celui de la **section
horizontale** du tube à la cote z, intégré sur la circonférence.

Convention (U2.01.05, « Cas des coques », lue le jour du lot 37) : les efforts de
coque sont les intégrales dans l'épaisseur de `sigma`, dans un repère dont la 3e
direction `z_l` est la normale `n` : `N_ab = int sigma_ab dh`, `Q_a = int sigma_a3 dh`,
et la force transmise à travers une coupure de normale `nu` tangente à la coque est
`F = N nu + (Q . nu) n`. Le repère « utilisateur » des tubes est `x_l` = verticale
(`VECTEUR = (0, 0, 1)`, `comm.TUBE_LOCAL_X`), `z_l = n`, `y_l = z_l ^ x_l`. La coupure
horizontale de normale `+Z` (face dont la normale sortante est `+Z`, force exercée
**par la partie haute sur la partie basse**) transmet donc, par unité de longueur de
circonférence :

    F = NXX * Z + NXY * y_l + QX * n            (y_l = n ^ Z, n = normale de la maille)

Grandeurs de section, pour une cote z (somme sur les arêtes horizontales, valeurs
nodales interpolées linéairement le long de l'arête) :

- `N  = int NXX ds`                     effort normal (traction positive) ;
- `MX = int NXX (y - yc) ds`            moment d'axe X (vecteur moment, X) dû à `NXX` ;
- `MY = -int NXX (x - xc) ds`           moment d'axe Y, dû à `NXX` ;
- `TX, TY` = composantes horizontales de `int (NXY y_l + QX n) ds`, données
  **séparément** pour la part `NXY` (cisaillement de membrane) et la part `QX`
  (cisaillement transversal, normal à la coque) ;
- `MX_paroi = int MXX y_l,X ds`       moment des efforts de flexion de paroi (vecteur
  moment de coque `n ^ (M nu) = MXX y_l - MXY x_l`), généralement petit devant `MX`.

La normale `n` de chaque maille est déduite de l'ordre des nœuds de sa connectivité
(produit vectoriel des diagonales) : c'est le sens que la convention ci-dessus suppose ;
il n'est pas lu de la documentation et est confronté à la statique par
`aster_expert.report.equilibrium_section`.

Une maille est un QUAD4 à deux arêtes horizontales (facette verticale de tube ou
panneau plan vertical de palplanche). Chaque arête contribue à la cote de son bord :
l'arête haute d'une maille est vue « d'en dessous » (`below`), l'arête basse « d'en
dessus » (`above`) ; les efforts d'un niveau intérieur sont la moyenne des deux (les
valeurs par élément aux nœuds ne sont pas continues d'une rangée à l'autre).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from pydantic import BaseModel, ConfigDict

Z_PLACES = 6
"""Décimales de la cote qui identifie un niveau (micromètre)."""

_HORIZONTAL_TOL = 1.0e-9


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SectionVector(_Model):
    """Efforts d'une section (unités : N, N.m)."""

    n: float
    mx: float
    my: float
    tx_nxy: float
    ty_nxy: float
    tx_qx: float
    ty_qx: float
    mx_wall: float

    @property
    def tx(self) -> float:
        return self.tx_nxy + self.tx_qx

    @property
    def ty(self) -> float:
        return self.ty_nxy + self.ty_qx


class LevelForces(_Model):
    """Efforts d'un tube à une cote : estimations par le bas, par le haut, moyenne."""

    z: float
    below: SectionVector | None
    above: SectionVector | None
    mean: SectionVector


_FIELDS = ("n", "mx", "my", "tx_nxy", "ty_nxy", "tx_qx", "ty_qx", "mx_wall")


@dataclass
class _Acc:
    v: np.ndarray = field(default_factory=lambda: np.zeros(len(_FIELDS)))

    def vector(self) -> SectionVector:
        return SectionVector(**dict(zip(_FIELDS, map(float, self.v), strict=True)))


def _normal(points: np.ndarray) -> np.ndarray:
    """Normale unitaire d'un QUAD4 (produit vectoriel des diagonales, sens de la
    connectivité)."""
    n = np.cross(points[2] - points[0], points[3] - points[1])
    length = float(np.linalg.norm(n))
    if length == 0.0:
        message = "maille dégénérée (diagonales colinéaires)"
        raise ValueError(message)
    return n / length


def _clip_edge(
    pa: np.ndarray,
    pb: np.ndarray,
    fa: dict[str, float],
    fb: dict[str, float],
    x_range: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, dict[str, float], dict[str, float]] | None:
    """Tronque l'arête `[pa, pb]` à `x_lo <= x <= x_hi` (valeurs nodales interpolées
    linéairement) ; `None` si rien ne subsiste."""
    lo, hi = x_range
    dx = float(pb[0] - pa[0])
    if dx == 0.0:
        return (pa, pb, fa, fb) if lo <= pa[0] <= hi else None
    t0, t1 = sorted(((lo - pa[0]) / dx, (hi - pa[0]) / dx))
    t0, t1 = max(t0, 0.0), min(t1, 1.0)
    if t1 <= t0:
        return None

    def at(t: float) -> tuple[np.ndarray, dict[str, float]]:
        return pa + t * (pb - pa), {k: fa[k] + t * (fb[k] - fa[k]) for k in fa}

    qa, ga = at(t0)
    qb, gb = at(t1)
    return qa, qb, ga, gb


def cell_edge_contributions(
    points: np.ndarray,
    values: Mapping[str, np.ndarray],
    center: tuple[float, float],
    x_range: tuple[float, float] | None = None,
) -> list[tuple[float, str, np.ndarray]]:
    """Contribution des arêtes horizontales d'un QUAD4.

    `points` : (4, 3) ; `values` : composantes (`NXX`, `NXY`, `QX`, `MXX`), chacune
    de 4 valeurs nodales ; `center` : `(xc, yc)` de l'axe du tube. Renvoie, pour chaque
    arête horizontale, `(z, côté, vecteur)` où le côté est `below` pour l'arête haute
    de la maille (la maille est sous la coupure) et `above` pour son arête basse.
    Le vecteur suit `_FIELDS`. `x_range` : ne garder de chaque arête que la part
    comprise entre les deux abscisses (contrôle par cellule périodique, valeurs
    nodales interpolées)."""
    n_hat = _normal(points)
    # y_l = n ^ Z : x_l est la verticale (repère « utilisateur », voir le module)
    y_l = np.array([n_hat[1], -n_hat[0], 0.0])
    zs = points[:, 2]
    edges = [(i, (i + 1) % 4) for i in range(4)]
    horizontal = [(a, b) for a, b in edges if abs(zs[a] - zs[b]) <= _HORIZONTAL_TOL]
    if len(horizontal) != 2:
        message = (
            f"maille à {len(horizontal)} arête(s) horizontale(s) au lieu de 2 : "
            "facette non verticale ou non alignée sur les niveaux"
        )
        raise ValueError(message)
    z_top = max(float(zs[a]) for a, _ in horizontal)
    out: list[tuple[float, str, np.ndarray]] = []
    xc, yc = center
    for a, b in horizontal:
        pa, pb = points[a], points[b]
        fa = {k: float(v[a]) for k, v in values.items()}
        fb = {k: float(v[b]) for k, v in values.items()}
        if x_range is not None:
            clipped = _clip_edge(pa, pb, fa, fb, x_range)
            if clipped is None:
                continue
            pa, pb, fa, fb = clipped
        length = float(np.linalg.norm(pb - pa))
        xa, ya = pa[0] - xc, pa[1] - yc
        xb, yb = pb[0] - xc, pb[1] - yc

        nxx, nxy, qx, mxx = (
            length * (fa[name] + fb[name]) / 2.0 for name in ("NXX", "NXY", "QX", "MXX")
        )
        prod_y = (
            2.0 * fa["NXX"] * ya
            + fa["NXX"] * yb
            + fb["NXX"] * ya
            + 2.0 * fb["NXX"] * yb
        ) / 6.0
        prod_x = (
            2.0 * fa["NXX"] * xa
            + fa["NXX"] * xb
            + fb["NXX"] * xa
            + 2.0 * fb["NXX"] * xb
        ) / 6.0
        vec = np.array(
            [
                nxx,
                length * prod_y,
                -length * prod_x,
                nxy * y_l[0],
                nxy * y_l[1],
                qx * n_hat[0],
                qx * n_hat[1],
                mxx * y_l[0],
            ]
        )
        z = float(zs[a])
        out.append((z, "below" if z == z_top else "above", vec))
    return out


def level_forces(
    cells: Sequence[tuple[np.ndarray, Mapping[str, np.ndarray]]],
    center: tuple[float, float],
    x_range: tuple[float, float] | None = None,
) -> list[LevelForces]:
    """Efforts par niveau (croissant en z) pour les mailles d'un même tube (ou d'un
    ensemble de mailles : palplanches, avec `x_range`)."""
    acc: dict[tuple[float, str], _Acc] = {}
    for points, values in cells:
        for z, side, vec in cell_edge_contributions(points, values, center, x_range):
            key = (round(z, Z_PLACES), side)
            acc.setdefault(key, _Acc()).v += vec
    out: list[LevelForces] = []
    for z in sorted({k[0] for k in acc}):
        below = acc.get((z, "below"))
        above = acc.get((z, "above"))
        parts = [a.v for a in (below, above) if a is not None]
        mean = _Acc(v=np.mean(parts, axis=0))
        out.append(
            LevelForces(
                z=z,
                below=below.vector() if below else None,
                above=above.vector() if above else None,
                mean=mean.vector(),
            )
        )
    return out


def polygon_perimeter(radius: float, sides: int) -> float:
    """Périmètre du polygone régulier inscrit (référence des tests)."""
    return 2.0 * sides * radius * math.sin(math.pi / sides)


__all__ = [
    "LevelForces",
    "SectionVector",
    "cell_edge_contributions",
    "level_forces",
    "polygon_perimeter",
]
