"""Grandeurs de la synthèse pour l'ingénieur, calculées à partir des tables lues
dans le `.mess` (lot 35). Pur : aucune lecture de fichier, aucune exécution.

Aucune grandeur n'est un verdict : chaque extrême est rapporté avec sa valeur, sa cote
et son élément ou nœud, jamais comparé à une limite de dimensionnement (aucune n'est
décidée dans la fiche). Les contrôles de validité de la décision 5 (signe, butée)
sont des constats sur le domaine du modèle linéaire (`SpringChecks`).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from aster_expert.report.tables import Record

#: Tolérance de correspondance de deux coordonnées (m) : les tables sont imprimées à
#: 12 chiffres significatifs.
COORD_TOL = 1.0e-6


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Extremum(_Model):
    """Une valeur extrême et son lieu (repère global des coordonnées)."""

    value: float
    x: float
    y: float
    z: float
    element: str | None = None
    node: str | None = None
    holder: str | None = None
    """Tube (`TUBE_05`), palplanche (`PALP_01_02`) ou tirant (`TIRANT_03`) porteur."""


class ExtremaPair(_Model):
    component: str
    maximum: Extremum
    minimum: Extremum


def _cell(row: Record, name: str) -> float:
    value = row[name]
    if not isinstance(value, float):
        message = f"colonne {name} non numérique : {value!r}"
        raise ValueError(message)
    return value


def _text(row: Record, name: str) -> str | None:
    value = row.get(name)
    if value is None:
        return None
    return f"{value:g}" if isinstance(value, float) else str(value)


def holder_of(x: float, y: float, axes: Sequence[float], radius: float) -> str:
    """Porteur d'un point : le tube dont le cercle de rayon `radius` passe par lui
    (à `COORD_TOL` près), sinon la palplanche comprise entre deux axes consécutifs
    (plan Y = 0). Un point de serrure (sur un tube et sur la palplanche) est au
    tube. Sans porteur reconnu : chaîne vide."""
    for k, xc in enumerate(axes, start=1):
        if abs(math.hypot(x - xc, y) - radius) <= COORD_TOL:
            return f"TUBE_{k:02d}"
    if abs(y) <= COORD_TOL:
        for k, (a, b) in enumerate(zip(axes[:-1], axes[1:], strict=True), start=1):
            if a - COORD_TOL <= x <= b + COORD_TOL:
                return f"PALP_{k:02d}_{k + 1:02d}"
    return ""


def _extremum(row: Record, component: str, holder: str) -> Extremum:
    return Extremum(
        value=_cell(row, component),
        x=_cell(row, "COOR_X"),
        y=_cell(row, "COOR_Y"),
        z=_cell(row, "COOR_Z"),
        element=_text(row, "MAILLE"),
        node=_text(row, "NOEUD"),
        holder=holder or None,
    )


def extrema(
    rows: Sequence[Record],
    components: Sequence[str],
    axes: Sequence[float],
    radius: float,
) -> list[ExtremaPair]:
    """Maximum et minimum de chaque composante, avec leur lieu. `rows` non vide."""
    if not rows:
        message = "table vide : aucun extremum à relever"
        raise ValueError(message)
    pairs: list[ExtremaPair] = []
    for component in components:
        high = max(rows, key=lambda r: _cell(r, component))
        low = min(rows, key=lambda r: _cell(r, component))
        pairs.append(
            ExtremaPair(
                component=component,
                maximum=_extremum(
                    high,
                    component,
                    holder_of(
                        _cell(high, "COOR_X"), _cell(high, "COOR_Y"), axes, radius
                    ),
                ),
                minimum=_extremum(
                    low,
                    component,
                    holder_of(_cell(low, "COOR_X"), _cell(low, "COOR_Y"), axes, radius),
                ),
            )
        )
    return pairs


# --- déplacements -----------------------------------------------------------


class HeadDisplacement(_Model):
    """Déplacement horizontal (DY) des nœuds des anneaux de tête des tubes."""

    max_abs: Extremum
    """Le nœud de plus grand |DY| ; `value` est signée."""
    minimum: Extremum
    maximum: Extremum
    n_nodes: int


def head_displacement(
    rows: Sequence[Record], axes: Sequence[float], radius: float
) -> HeadDisplacement:
    if not rows:
        message = "table de tête vide"
        raise ValueError(message)
    worst = max(rows, key=lambda r: abs(_cell(r, "DY")))
    pair = extrema(rows, ["DY"], axes, radius)[0]

    def at(row: Record) -> Extremum:
        return _extremum(
            row,
            "DY",
            holder_of(_cell(row, "COOR_X"), _cell(row, "COOR_Y"), axes, radius),
        )

    return HeadDisplacement(
        max_abs=at(worst), minimum=pair.minimum, maximum=pair.maximum, n_nodes=len(rows)
    )


class ProfilePoint(_Model):
    z: float
    mean: float
    minimum: float
    maximum: float
    n_nodes: int


def dy_profile(rows: Sequence[Record], *, z_places: int = 6) -> list[ProfilePoint]:
    """Profil de DY d'un tube : à chaque cote présente parmi ses nœuds, moyenne, minimum
    et maximum de DY sur l'anneau de nœuds de cette cote. La moyenne annulaire est le
    déplacement de la section ; l'étendue (min à max) dit l'ovalisation. De la cote
    haute à la cote basse."""
    by_z: dict[float, list[float]] = {}
    for row in rows:
        by_z.setdefault(round(_cell(row, "COOR_Z"), z_places), []).append(
            _cell(row, "DY")
        )
    return [
        ProfilePoint(
            z=z,
            mean=sum(values) / len(values),
            minimum=min(values),
            maximum=max(values),
            n_nodes=len(values),
        )
        for z, values in sorted(by_z.items(), reverse=True)
    ]


# --- efforts ----------------------------------------------------------------


class TieForce(_Model):
    """Effort axial d'un tirant (`EFGE_ELNO`, composante N, repère local de la barre :
    N > 0 en traction)."""

    tie: int
    x: float
    n: float
    minimum: float
    maximum: float
    n_rows: int


def tie_forces(rows: Sequence[Record], axes: Sequence[float]) -> list[TieForce]:
    """Un effort par tirant : les tirants sont dans les plans X = axe du tube qui les
    porte ; N est constant le long d'une barre (`minimum` = `maximum` en pratique, les
    deux sont rapportés)."""
    out: list[TieForce] = []
    for k, xc in enumerate(axes, start=1):
        mine = [
            _cell(r, "N") for r in rows if abs(_cell(r, "COOR_X") - xc) <= COORD_TOL
        ]
        if not mine:
            message = f"aucune ligne d'effort pour le tirant du tube {k} (X = {xc:g})"
            raise ValueError(message)
        out.append(
            TieForce(
                tie=k,
                x=xc,
                n=sum(mine) / len(mine),
                minimum=min(mine),
                maximum=max(mine),
                n_rows=len(mine),
            )
        )
    return out


# --- ressorts : signe et butée ------------------------------------------------


class SpringNode(_Model):
    """Un nœud à ressort : position, raideur totale, aires tributaires par bande."""

    x: float
    y: float
    z: float
    stiffness: float
    """N/m (somme des bandes)."""
    area: float
    """m² : aire tributaire projetée, toutes bandes."""
    capacity_n: float
    """N : Σ_bandes aire_b × σ'p_b(z) (force de butée limite du nœud)."""
    band_stiffness: dict[str, float]
    """N/m par bande (`RESS_AV_ARGI`, `RESS_AV_MARNE`)."""


class SignCheck(_Model):
    """Signe des ressorts : compression si DY < 0 (l'écran va vers le bassin)."""

    n_nodes: int
    n_tension: int
    n_compression: int
    n_null: int
    z_min_tension: float | None = None
    z_max_tension: float | None = None
    max_tension_reaction_n: float | None = None
    """Réaction en traction maximale k·DY (N), au nœud `at_max_tension`."""
    at_max_tension: Extremum | None = None


class BearingCheck(_Model):
    """Pression de réaction k·|DY| / A comparée à σ'p(z) (compression seule)."""

    n_compressed: int
    max_ratio: float
    """Taux maximal (1 = 100 %) : force de réaction / force de butée du nœud."""
    at_max: Extremum | None = None
    """Nœud du taux maximal : `value` = DY (m) ; `holder` = tube ou palplanche."""
    max_pressure_kpa: float | None = None
    limit_kpa: float | None = None
    n_over_100: int
    n_over_100_holders: list[str]


def _capacity(
    z: float, profile: dict[str, list[tuple[float, float]]], band: str
) -> float:
    """σ'p (Pa) de la couche de la bande `band` à la cote `z` : interpolation
    linéaire entre les points du profil de la couche (les cotes hors profil sont
    refusées, jamais extrapolées)."""
    points = profile[band]
    low, high = points[0][0], points[-1][0]
    if not (min(low, high) - COORD_TOL <= z <= max(low, high) + COORD_TOL):
        message = f"cote {z:g} hors du profil de butée de {band} [{low:g}, {high:g}]"
        raise ValueError(message)
    for (z0, p0), (z1, p1) in zip(points[:-1], points[1:], strict=True):
        lo, hi = sorted((z0, z1))
        if lo - COORD_TOL <= z <= hi + COORD_TOL:
            return p0 + (p1 - p0) * (z - z0) / (z1 - z0)
    message = f"cote {z:g} sans intervalle de butée pour {band}"
    raise ValueError(message)


def spring_nodes(
    areas: dict[str, dict[tuple[float, float, float], float]],
    k_h_mn_per_m3: dict[str, float],
    butee_pa: dict[str, list[tuple[float, float]]],
) -> dict[tuple[float, float, float], SpringNode]:
    """Les nœuds à ressort, à partir des aires tributaires analytiques par bande
    (`quai_cw_test_01.meshing.combiwall.spring_node_areas`), des modules de réaction
    (MN/m³ -> N/m³ ici, par 1e6) et du profil de butée (Pa) de la couche de chaque
    bande. La clé est la position arrondie au micromètre.

    Raideur d'un nœud : Σ_bandes k_h × aire ; force de butée : Σ_bandes aire × σ'p de
    la couche de la bande. Un nœud commun à deux bandes (limite argile/marne) porte les
    deux -- la butée est alors la somme des deux parts, chacune avec sa couche."""
    nodes: dict[tuple[float, float, float], SpringNode] = {}
    for band, by_point in areas.items():
        for point, area in by_point.items():
            key = (round(point[0], 6), round(point[1], 6), round(point[2], 6))
            k_band = k_h_mn_per_m3[band] * 1.0e6 * area
            cap = area * _capacity(point[2], butee_pa, band)
            old = nodes.get(key)
            if old is None:
                nodes[key] = SpringNode(
                    x=key[0],
                    y=key[1],
                    z=key[2],
                    stiffness=k_band,
                    area=area,
                    capacity_n=cap,
                    band_stiffness={band: k_band},
                )
            else:
                nodes[key] = old.model_copy(
                    update={
                        "stiffness": old.stiffness + k_band,
                        "area": old.area + area,
                        "capacity_n": old.capacity_n + cap,
                        "band_stiffness": {**old.band_stiffness, band: k_band},
                    }
                )
    return nodes


def _key(row: Record) -> tuple[float, float, float]:
    return (
        round(_cell(row, "COOR_X"), 6),
        round(_cell(row, "COOR_Y"), 6),
        round(_cell(row, "COOR_Z"), 6),
    )


def _match(
    nodes: dict[tuple[float, float, float], SpringNode], row: Record
) -> SpringNode:
    node = nodes.get(_key(row))
    if node is None:
        # les tables portent 12 chiffres : repli sur le voisin le plus proche à 1 µm
        x, y, z = _cell(row, "COOR_X"), _cell(row, "COOR_Y"), _cell(row, "COOR_Z")
        best = min(
            nodes.values(),
            key=lambda n: (n.x - x) ** 2 + (n.y - y) ** 2 + (n.z - z) ** 2,
        )
        if math.dist((best.x, best.y, best.z), (x, y, z)) > 1.0e-5:
            message = f"nœud de ressort inconnu à ({x:g}, {y:g}, {z:g})"
            raise ValueError(message)
        return best
    return node


class SpringChecks(_Model):
    sign: SignCheck
    bearing: BearingCheck
    layer_forces_n: dict[str, float]
    """Force exercée par les ressorts sur l'écran (N, repère global, direction Y) par
    bande : -Σ k·DY. Positive vers la terre (+Y)."""
    total_force_n: float


def spring_checks(
    rows: Sequence[Record],
    nodes: dict[tuple[float, float, float], SpringNode],
    axes: Sequence[float],
    radius: float,
) -> SpringChecks:
    """Signe et butée des ressorts d'un cas élémentaire, et somme par couche.

    `rows` : `DEPL/DY` de chaque nœud à ressort (table `RESSORTS_<cas>`). Un nœud de
    DY nul n'est ni en traction ni en compression. Ces contrôles portent sur un cas
    **élémentaire** : ils ne vérifient pas l'ouvrage (aucune combinaison décidée) ; un
    dépassement est un constat sur le domaine du modèle linéaire."""
    if not rows:
        message = "table des ressorts vide"
        raise ValueError(message)
    tension: list[tuple[SpringNode, Record]] = []
    compression = 0
    null = 0
    worst: tuple[float, SpringNode, Record] | None = None
    over: list[str] = []
    n_over = 0
    layer: dict[str, float] = {}
    for row in rows:
        node = _match(nodes, row)
        dy = _cell(row, "DY")
        for band, k_band in node.band_stiffness.items():
            layer[band] = layer.get(band, 0.0) - k_band * dy
        if dy > 0.0:
            tension.append((node, row))
            continue
        if dy == 0.0:
            null += 1
            continue
        compression += 1
        ratio = node.stiffness * abs(dy) / node.capacity_n
        if worst is None or ratio > worst[0]:
            worst = (ratio, node, row)
        if ratio > 1.0:
            n_over += 1
            over.append(holder_of(node.x, node.y, axes, radius) or "hors tube")
    if tension:
        biggest = max(tension, key=lambda t: t[0].stiffness * _cell(t[1], "DY"))
        zs = [n.z for n, _ in tension]
        sign = SignCheck(
            n_nodes=len(rows),
            n_tension=len(tension),
            n_compression=compression,
            n_null=null,
            z_min_tension=min(zs),
            z_max_tension=max(zs),
            max_tension_reaction_n=biggest[0].stiffness * _cell(biggest[1], "DY"),
            at_max_tension=_extremum(
                biggest[1],
                "DY",
                holder_of(biggest[0].x, biggest[0].y, axes, radius),
            ),
        )
    else:
        sign = SignCheck(
            n_nodes=len(rows), n_tension=0, n_compression=compression, n_null=null
        )
    if worst is None:
        bearing = BearingCheck(
            n_compressed=0, max_ratio=0.0, n_over_100=0, n_over_100_holders=[]
        )
    else:
        ratio, node, row = worst
        bearing = BearingCheck(
            n_compressed=compression,
            max_ratio=ratio,
            at_max=_extremum(row, "DY", holder_of(node.x, node.y, axes, radius)),
            max_pressure_kpa=node.stiffness * abs(_cell(row, "DY")) / node.area / 1e3,
            limit_kpa=node.capacity_n / node.area / 1e3,
            n_over_100=n_over,
            n_over_100_holders=sorted(set(over)),
        )
    return SpringChecks(
        sign=sign,
        bearing=bearing,
        layer_forces_n=layer,
        total_force_n=sum(layer.values()),
    )


# --- réactions --------------------------------------------------------------


class GroupReaction(_Model):
    """Résultante de `REAC_NODA` d'un groupe d'appui (N, repère global)."""

    group: str
    dx: float
    dy: float
    dz: float
    blocked: list[str]
    """Composantes réellement bloquées : seules elles sont des réactions d'appui."""


#: Composantes réellement bloquées de chaque groupe d'appui (lots 23 et 34) : les
#: réactions des autres composantes de `SYM_G`/`SYM_D` sont des forces de liaison de
#: `LIAISON_SOLIDE` qui s'annulent sur l'ensemble des nœuds.
BLOCKED_COMPONENTS = {
    "ANCR": ["DX", "DY", "DZ"],
    "PIED": ["DZ"],
    "SYMG": ["DX"],
    "SYMD": ["DX"],
}


def group_reaction(group: str, code: str, row: Record) -> GroupReaction:
    return GroupReaction(
        group=group,
        dx=_cell(row, "DX"),
        dy=_cell(row, "DY"),
        dz=_cell(row, "DZ"),
        blocked=BLOCKED_COMPONENTS[code],
    )


class TieAnchorCheck(_Model):
    """Lecture croisée : les efforts axiaux des tirants (`EFGE_ELNO`, N) projetés selon
    la direction des tirants égalent la réaction des ancrages (`REAC_NODA`, composantes
    bloquées) -- un tirant n'est relié qu'à l'ancrage (statique du nœud d'ancrage).
    Horizontale : exacte dans tous les cas. Verticale : exacte hors pesanteur ; sous
    pesanteur (`gravity`) l'ancrage porte en plus une part du poids propre du tirant,
    l'écart n'est alors pas un défaut de lecture."""

    cos_theta: float
    sin_theta: float
    ties_dy_n: float
    anchor_dy_n: float
    gap_dy: float
    """Écart relatif (ties - ancrage) / |ancrage|."""
    ties_dz_n: float
    anchor_dz_n: float
    gap_dz: float
    gravity: bool


def tie_anchor_check(
    ties: Sequence[TieForce],
    anchor: GroupReaction,
    direction: tuple[float, float],
    *,
    gravity: bool,
) -> TieAnchorCheck:
    """`direction` : `(cos, sin)` du tirant, du haut (tête sur le tube) vers l'ancrage,
    dans le plan (Y, Z)."""
    cos_t, sin_t = direction
    total = sum(t.n for t in ties)
    ties_dy, ties_dz = total * cos_t, total * sin_t

    def gap(a: float, b: float) -> float:
        return (a - b) / abs(b) if b != 0.0 else math.inf

    return TieAnchorCheck(
        cos_theta=cos_t,
        sin_theta=sin_t,
        ties_dy_n=ties_dy,
        anchor_dy_n=anchor.dy,
        gap_dy=gap(ties_dy, anchor.dy),
        ties_dz_n=ties_dz,
        anchor_dz_n=anchor.dz,
        gap_dz=gap(ties_dz, anchor.dz),
        gravity=gravity,
    )
