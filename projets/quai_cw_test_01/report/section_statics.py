"""Contrôle d'équilibre des efforts d'ensemble à la cote de dragage (lot 37).

Les efforts d'ensemble (`quai_cw_test_01.report.sections`) sont intégrés sur une coupure
horizontale à la cote `z_d`. Ils doivent être cohérents avec la statique du **corps
inférieur** (tout ce qui est sous la coupure) : la force exercée par la partie haute
sur la partie basse est l'opposée de la somme des forces extérieures appliquées au
corps inférieur,

    T_coupure = - somme(F_y ext)      N_coupure = - somme(F_z ext)
    M_coupure = somme[(z - z_d) F_y - y F_z]          (moment d'axe X, en (y=0, z_d))

Forces extérieures du corps inférieur (les seules, sous `z_d`) : la poussée sur les
mailles de `ECRAN_POUSSEE` situées sous la coupure, intégrée sur la géométrie (comme
le `.comm` l'applique : fonction par couche évaluée aux nœuds pour `G` et `Q1`,
fonction de la cote pour l'eau), la force des ressorts de sol, les réactions d'appui
en pied (`PIED_TUBES`) et le poids (cas `G`). Le corps supérieur n'intervient pas :
tirants, poutre et charges de tête sont hors du corps inférieur.

**Cote de la coupure.** Les efforts par élément aux nœuds sont discontinus d'une
rangée de mailles à l'autre ; l'effort de la cote est la moyenne des estimations par
le bas et par le haut (`LevelForces.mean`), exacte à ~1 % de la statique là où aucune
force nodale n'est appliquée (vérifié sur le MED du lot 36 : `G`, ensemble, 0,9 à
1,5 % de la cote -11,75 à +2,00 m). Sur une rangée qui porte les ressorts de sol
(forces nodales concentrées), les deux estimations diffèrent de ~20 % et la moyenne
ne l'est plus qu'à quelques pour cent près (à -12,00 m : ~2 % pour `G`, mais sans
que les deux estimations soient de la même précision) : `section_statics` refuse
une cote qui porte des nœuds à ressort. La cote du contrôle est la **première rangée
au-dessus du dragage** (`z_d + 0,25 m` : le maillage), sans nœud à ressort.

Deux portées : l'**ensemble** de l'ouvrage (tubes, palplanches) et la **cellule** d'un
tube intérieur, sous une charge uniforme le long du quai (`G`, `Q1`, `EAU_P`,
`EAU_A`). La cellule va d'un plan de symétrie à mi-palplanche au suivant : par symétrie
et périodicité de la solution, aucun effort tangent ne traverse ces plans, le corps
est en équilibre avec les seules forces de sa cellule.

Ces égalités sont exactes pour la solution éléments finis prise aux nœuds ; les
efforts par élément aux nœuds (`EFGE_ELNO`) sont extrapolés des points de Gauss et
les intégrer sur une arête ne les reproduit qu'aux erreurs de discrétisation près :
l'écart est une grandeur **sensible à la discrétisation** (CLAUDE.md, critère de
réussite des essais).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict

from aster_expert.report.med_read import med_field_name
from quai_cw_test_01.generation.profiles import layer_profiles
from quai_cw_test_01.generation.values import ModelValues
from quai_cw_test_01.meshing.equilibrium import (
    Point,
    quad_pressure_force_and_z_moment,
)
from quai_cw_test_01.report import sections as sec
from quai_cw_test_01.report.med_source import MedData
from quai_cw_test_01.report.quantities import SpringNode

Z_TOL = 1.0e-6
BAND_TOL = 1.0e-6


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Balance(_Model):
    """Une grandeur mesurée (intégrale des efforts de coque) et attendue (statique)."""

    measured: float
    expected: float
    absolute_gap: float
    relative_gap: float | None
    """`|mesuré - attendu| / max(|attendu|, |mesuré|)`, `None` si les deux sont nuls."""


def balance(measured: float, expected: float) -> Balance:
    scale = max(abs(measured), abs(expected))
    gap = abs(measured - expected)
    return Balance(
        measured=measured,
        expected=expected,
        absolute_gap=gap,
        relative_gap=None if scale == 0.0 else gap / scale,
    )


class SectionStatics(_Model):
    case: str
    scope: str
    """`ensemble` ou `cellule TUBE_<nn>`."""
    z: float
    x_range: tuple[float, float] | None
    tubes: list[int]
    t_y: Balance
    m_x: Balance
    n_z: Balance
    measured_parts: dict[str, float]
    """Part des tubes et des palplanches dans `T_y`, `M_x`, `N` mesurés."""
    external_n: dict[str, float]
    """Forces extérieures du corps inférieur : pression, ressorts, pied, poids."""
    palp_normals_toward_terre: float | None
    """Part des mailles de palplanche de la portée dont la normale (ordre de la
    connectivité) a une composante Y positive."""


def _corner_points(data: MedData, cell: int) -> np.ndarray:
    points: np.ndarray = data.coords[data.conn[0][cell]]
    return points


def _quad_area(points: np.ndarray) -> float:
    """Aire d'un QUAD4 plan (demi-produit vectoriel des diagonales)."""
    return 0.5 * float(
        np.linalg.norm(np.cross(points[2] - points[0], points[3] - points[1]))
    )


def _x_fraction(points: np.ndarray, x_range: tuple[float, float] | None) -> float:
    """Part de l'étendue en x d'une maille comprise dans `x_range` (charge uniforme
    en x sur la maille)."""
    if x_range is None:
        return 1.0
    lo, hi = float(points[:, 0].min()), float(points[:, 0].max())
    if hi - lo <= 0.0:
        return 1.0 if x_range[0] <= lo <= x_range[1] else 0.0
    overlap = min(hi, x_range[1]) - max(lo, x_range[0])
    return max(0.0, min(1.0, overlap / (hi - lo)))


def _pressure_profiles(mv: ModelValues, case: str) -> tuple[str, Any] | None:
    """Comment le `.comm` applique la poussée du cas : `("layers", couches)` pour
    `G`/`Q1` (fonction de la couche dont la bande contient tous les nœuds de la maille),
    `("function", profil)` pour l'eau ; `None` sans pression sur l'écran."""
    if case in ("G", "Q1"):
        earth = mv.profile_si("eau_terres.profil_poussee_terres_permanent")
        return "layers", layer_profiles(earth, case)
    if case in ("EAU_P", "EAU_A"):
        key = (
            "eau_terres.profil_pression_eau_permanent"
            if case == "EAU_P"
            else "eau_terres.profil_pression_eau_accidentel"
        )
        return "function", [(z, p) for z, p, _, _ in sorted(mv.profile_si(key))]
    return None


def _cell_pressure(
    corners: tuple[Point, Point, Point, Point], applied: tuple[str, Any]
) -> tuple[Point, float]:
    """Force de pression d'une maille et son `int F_y z` : la fonction de la couche qui
    contient la maille (`layers`, aucune pression si aucune) ou la fonction de la cote
    (`function`), évaluée aux nœuds."""
    kind, spec = applied
    if kind == "function":
        return quad_pressure_force_and_z_moment(corners, spec, "nodes")
    zs = [c[2] for c in corners]
    for layer in spec:
        if all(layer.z_low - BAND_TOL <= z <= layer.z_high + BAND_TOL for z in zs):
            return quad_pressure_force_and_z_moment(
                corners, list(layer.points), "nodes"
            )
    return (0.0, 0.0, 0.0), 0.0


def lower_body_loads(
    data: MedData,
    mv: ModelValues,
    case: str,
    z_cut: float,
    spring_nodes: dict[tuple[float, float, float], SpringNode],
    x_range: tuple[float, float] | None,
) -> dict[str, tuple[float, float, float]]:
    """Forces extérieures du corps inférieur, par origine : pour chacune
    `(F_y, F_z, S_yz)` avec `S_yz = somme[(z - z_cut) F_y - y F_z]` (le terme du moment
    d'axe X). Pression sur `ECRAN_POUSSEE`, ressorts, réactions en pied, poids."""
    out: dict[str, tuple[float, float, float]] = {}

    fy = sz = 0.0
    applied = _pressure_profiles(mv, case)
    if applied is not None:
        for cell in data.cell_groups[0]["ECRAN_POUSSEE"]:
            points = _corner_points(data, int(cell))
            if points[:, 2].max() > z_cut + Z_TOL:
                continue
            share = _x_fraction(points, x_range)
            if share == 0.0:
                continue
            corners = tuple(tuple(float(v) for v in p) for p in points)
            force, z_moment = _cell_pressure(corners, applied)  # type: ignore[arg-type]
            fy += share * force[1]
            sz += share * (z_moment - z_cut * force[1])
    out["pression"] = (fy, 0.0, sz)

    fy = sz = 0.0
    dy = data.node_field(case, "DEPL")[:, 1]
    for node in np.unique(data.conn[-2].ravel()):
        x, y, z = (float(v) for v in data.coords[int(node)])
        if z > z_cut + Z_TOL or (
            x_range is not None and not x_range[0] <= x <= x_range[1]
        ):
            continue
        spring = spring_nodes.get((round(x, 6), round(y, 6), round(z, 6)))
        if spring is None:
            message = f"nœud à ressort sans raideur analytique : {(x, y, z)}"
            raise ValueError(message)
        force_y = -spring.stiffness * float(dy[int(node)])
        fy += force_y
        sz += (z - z_cut) * force_y
    out["ressorts"] = (fy, 0.0, sz)

    reac = data.node_field(case, "REAC_NODA")
    fz = sz = 0.0
    for node in data.node_groups["PIED_TUBES"]:
        x, y, _ = (float(v) for v in data.coords[int(node)])
        if x_range is not None and not x_range[0] <= x <= x_range[1]:
            continue
        r_z = float(reac[int(node), 2])
        fz += r_z
        sz += -y * r_z
    out["pied"] = (0.0, fz, sz)

    fz = sz = 0.0
    if case == "G":
        g = mv.si("charges.acceleration_pesanteur")
        for group, thickness, rho in (
            (
                "TUBES",
                mv.si("tube.epaisseur_coque_retenue"),
                mv.si("tube.masse_volumique"),
            ),
            (
                "PALPS",
                mv.si("palplanche.epaisseur_coque_EPAIS"),
                mv.si("palplanche.masse_volumique"),
            ),
        ):
            for cell in data.cell_groups[0][group]:
                points = _corner_points(data, int(cell))
                if points[:, 2].max() > z_cut + Z_TOL:
                    continue
                share = _x_fraction(points, x_range)
                weight = share * _quad_area(points) * thickness * rho * g
                fz += -weight
                sz += float(points[:, 1].mean()) * weight
    out["poids"] = (0.0, fz, sz)
    return out


def _palp_cells(
    data: MedData, case: str
) -> tuple[list[tuple[np.ndarray, dict[str, np.ndarray]]], float]:
    """Mailles de palplanche avec leurs valeurs nodales `EFGE_NOEU` (par nœud de la
    maille), et la part de ces mailles dont la normale a `n_y > 0`."""
    name = med_field_name(f"{case}_EP", "EFGE_NOEU")
    values = data.arrays[name]
    nodes = data.arrays.get(f"{name}#nodes", np.arange(len(values)))
    row_of = {int(n): i for i, n in enumerate(nodes)}
    comps = {c: data.comp(name, c) for c in ("NXX", "NXY", "QX", "MXX")}
    cells: list[tuple[np.ndarray, dict[str, np.ndarray]]] = []
    toward = 0
    for cell in data.cell_groups[0]["PALPS"]:
        conn = data.conn[0][int(cell)]
        points = data.coords[conn]
        rows = [row_of[int(n)] for n in conn]
        cells.append((points, {c: values[rows, j] for c, j in comps.items()}))
        diagonals = np.cross(points[2] - points[0], points[3] - points[1])
        toward += 1 if diagonals[1] > 0.0 else 0
    return cells, toward / max(len(cells), 1)


def _tube_cells(
    data: MedData, case: str, tube: int
) -> list[tuple[np.ndarray, dict[str, np.ndarray]]]:
    field = med_field_name(f"{case}_ET", "EFGE_ELNO")
    values = data.arrays[f"{field}@0"]
    position = {int(c): i for i, c in enumerate(data.arrays[f"{field}@0#cells"])}
    comps = {c: data.comp(field, c) for c in ("NXX", "NXY", "QX", "MXX")}
    out: list[tuple[np.ndarray, dict[str, np.ndarray]]] = []
    for cell in data.cell_groups[0][f"TUBE_{tube:02d}"]:
        conn = data.conn[0][int(cell)]
        start = 4 * position[int(cell)]
        if len(conn) != 4:
            message = f"maille de tube à {len(conn)} nœuds (QUAD4 attendu)"
            raise ValueError(message)
        out.append(
            (
                data.coords[conn],
                {c: values[start : start + 4, j] for c, j in comps.items()},
            )
        )
    return out


def tube_levels(
    data: MedData, case: str, tube: int, axis_x: float
) -> list[sec.LevelForces]:
    """Efforts d'ensemble d'un tube, à chaque cote."""
    cells = _tube_cells(data, case, tube)
    ys = np.concatenate([points[:, 1] for points, _ in cells])
    centre_y = float(ys.max() + ys.min()) / 2.0
    return sec.level_forces(cells, (axis_x, centre_y))


def _at(levels: Sequence[sec.LevelForces], z: float) -> sec.LevelForces:
    key = round(z, sec.Z_PLACES)
    for level in levels:
        if level.z == key:
            return level
    message = f"aucun niveau à la cote {z:g} m"
    raise ValueError(message)


def section_statics(
    data: MedData,
    mv: ModelValues,
    case: str,
    z_cut: float,
    axes: Sequence[float],
    spring_nodes: dict[tuple[float, float, float], SpringNode],
    *,
    cell_of_tube: int | None = None,
) -> SectionStatics:
    """Contrôle à la cote `z_cut` : ensemble de l'ouvrage, ou (`cell_of_tube`) cellule
    d'un tube intérieur (`x_range` de mi-palplanche à mi-palplanche)."""
    n_tubes = len(axes)
    if cell_of_tube is None:
        tubes = list(range(1, n_tubes + 1))
        x_range: tuple[float, float] | None = None
        scope = "ensemble"
    else:
        k = cell_of_tube
        if not 1 < k < n_tubes:
            message = (
                f"la cellule d'un tube de bord (demi-tube) n'est pas périodique : {k}"
            )
            raise ValueError(message)
        tubes = [k]
        x_range = ((axes[k - 2] + axes[k - 1]) / 2.0, (axes[k - 1] + axes[k]) / 2.0)
        scope = f"cellule TUBE_{k:02d}"

    at_cut = [
        int(node)
        for node in np.unique(data.conn[-2].ravel())
        if abs(float(data.coords[int(node), 2]) - z_cut) <= Z_TOL
    ]
    if at_cut:
        message = (
            f"la cote {z_cut:g} m porte {len(at_cut)} nœuds à ressort : coupure "
            "ambiguë (forces nodales), choisir une rangée sans ressort"
        )
        raise ValueError(message)
    tube_t = tube_m = tube_n = 0.0
    for tube in tubes:
        level = _at(tube_levels(data, case, tube, axes[tube - 1]), z_cut).mean
        tube_t += level.ty
        tube_m += level.mx + level.mx_wall
        tube_n += level.n

    cells, toward = _palp_cells(data, case)
    palp_levels = sec.level_forces(cells, (0.0, 0.0), x_range)
    palp = _at(palp_levels, z_cut).mean
    palp_t = palp.ty if palp else 0.0
    palp_m = (palp.mx + palp.mx_wall) if palp else 0.0
    palp_n = palp.n if palp else 0.0

    loads = lower_body_loads(data, mv, case, z_cut, spring_nodes, x_range)
    ext_fy = sum(v[0] for v in loads.values())
    ext_fz = sum(v[1] for v in loads.values())
    ext_m = sum(v[2] for v in loads.values())
    return SectionStatics(
        case=case,
        scope=scope,
        z=z_cut,
        x_range=x_range,
        tubes=tubes,
        t_y=balance(tube_t + palp_t, -ext_fy),
        m_x=balance(tube_m + palp_m, ext_m),
        n_z=balance(tube_n + palp_n, -ext_fz),
        measured_parts={
            "T_y tubes": tube_t,
            "T_y palplanches": palp_t,
            "M_x tubes": tube_m,
            "M_x palplanches": palp_m,
            "N tubes": tube_n,
            "N palplanches": palp_n,
        },
        external_n={
            "pression F_y": loads["pression"][0],
            "ressorts F_y": loads["ressorts"][0],
            "pied F_z": loads["pied"][1],
            "poids F_z": loads["poids"][1],
        },
        palp_normals_toward_terre=toward,
    )


__all__ = [
    "Balance",
    "SectionStatics",
    "balance",
    "lower_body_loads",
    "section_statics",
    "tube_levels",
]
