"""Orientation des normales des mailles de chaque couche de poussée (lot 35).

La charge de poussée est appliquée couche par couche (`FORCE_COQUE/PRES`, une
occurrence par groupe de couche) avec `VERI_NORM="NON"` : le contrôle automatique
d'orientation de Code_Aster exige un groupe de bord connexe, ce que la couche de
marne (trois tubes que les palplanches ne relient pas) n'est pas. Ce module
remplace la vérification désactivée par une vérification explicite, faite sur le
maillage **relu après `MODI_MAILLAGE/ORIE_NORM_COQUE`** (écrit en MED par le `.comm`,
`quai_cw_test_01.generation.comm.oriented_mesh_block`) : la connectivité orientée est
celle que Code_Aster tient, jamais celle du MED d'entrée.

Le sens attendu vient de la fiche (point 5) : une pression positive doit pousser
vers le bassin, la normale de chaque maille de `ECRAN_POUSSEE` est donc tournée
**vers la terre** (Y > 0) -- radialement vers l'extérieur du tube pour une facette de
tube (demi-tube côté terre), selon +Y pour une palplanche (plan Y = 0). La normale
d'une maille est celle de la règle de la main droite sur l'ordre de ses nœuds
(formule de Newell) ; la vérification ne réimplémente pas `ORIE_NORM_COQUE`, elle
en constate le résultat.
"""

from __future__ import annotations

import math

from aster_expert.meshing.invariants import (
    InvariantResult,
    MedDump,
    _group_cells,
)

Vector = tuple[float, float, float]

#: Composante de la normale attendue au minimum pour une facette verticale de
#: tube (cosinus avec la direction radiale) ; les facettes d'un tube de 40 pans
#: sont à 4,5° au plus de la direction radiale de leur centre, d'où un cosinus
#: supérieur à 0,99 : le seuil sépare sans ambiguïté un sens de l'autre.
MIN_ALIGNMENT = 0.9


def cell_normal(dump: MedDump, level: int, cell_id: int) -> Vector:
    """Normale unitaire de la maille (règle de la main droite sur l'ordre des
    nœuds ; formule de Newell), `(0, 0, 0)` pour une maille dégénérée."""
    nodes = dump.levels[str(level)].connectivity[cell_id]
    pts = [dump.coords[n] for n in nodes]
    nx = ny = nz = 0.0
    for a, b in zip(pts, pts[1:] + pts[:1], strict=True):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    norm = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norm == 0.0:
        return (0.0, 0.0, 0.0)
    return (nx / norm, ny / norm, nz / norm)


def _centroid(dump: MedDump, level: int, cell_id: int) -> Vector:
    nodes = dump.levels[str(level)].connectivity[cell_id]
    pts = [dump.coords[n] for n in nodes]
    n = len(pts)
    return (
        sum(p[0] for p in pts) / n,
        sum(p[1] for p in pts) / n,
        sum(p[2] for p in pts) / n,
    )


def _expected_direction(
    dump: MedDump,
    level: int,
    cell_id: int,
    *,
    tube_of_cell: str | None,
    tube_axes: dict[str, float],
) -> Vector:
    """Direction attendue de la normale : radiale sortante pour une facette de
    tube (axe vertical passant par `(x_axe, 0)`), +Y pour une palplanche."""
    if tube_of_cell is None:
        return (0.0, 1.0, 0.0)
    cx, cy, _ = _centroid(dump, level, cell_id)
    rx, ry = cx - tube_axes[tube_of_cell], cy
    norm = math.hypot(rx, ry)
    return (rx / norm, ry / norm, 0.0) if norm > 0.0 else (0.0, 0.0, 0.0)


def check_layer_normals(
    dump: MedDump,
    *,
    layer_groups: list[str],
    tube_axes: dict[str, float],
    sheet_group: str,
) -> list[InvariantResult]:
    """Pour chaque groupe de couche, chaque maille a sa normale tournée vers la
    terre.

    `tube_axes` associe le nom du groupe de mailles de chaque tube (`TUBE_05`) à
    l'abscisse X de son axe ; une maille d'un groupe de couche appartient soit à
    l'un de ces tubes, soit à `sheet_group` (les palplanches), sinon le contrôle
    échoue (une maille sans famille connue n'a pas de sens attendu).

    Évalués, par couche : (1) toutes les mailles ont une famille (tube ou palplanche) ;
    (2) toutes les normales sont horizontales (composante Z nulle à 1e-9 près) ;
    (3) toutes sont tournées vers la terre, cosinus minimal avec la direction attendue
    au moins égal à `MIN_ALIGNMENT` ; la valeur relevée est ce cosinus minimal.
    """
    tube_cells = {
        tube: {(lv, i) for _, lv, i in _group_cells(dump, tube)} for tube in tube_axes
    }
    sheet_cells = {(lv, i) for _, lv, i in _group_cells(dump, sheet_group)}
    results: list[InvariantResult] = []

    def add(label: str, expected: object, obtained: object, ok: bool) -> None:
        results.append(
            InvariantResult(
                kind="normales",
                label=label,
                expected=str(expected),
                obtained=str(obtained),
                ok=ok,
            )
        )

    for group in layer_groups:
        cells = _group_cells(dump, group)
        label = f"normales de {group}"
        if not cells:
            add(f"{label} : groupe présent", "au moins une maille", 0, False)
            continue
        unknown = 0
        tilted = 0
        wrong = 0
        min_cos = math.inf
        for _, level, cell_id in cells:
            key = (level, cell_id)
            tube = next(
                (t for t, members in tube_cells.items() if key in members), None
            )
            if tube is None and key not in sheet_cells:
                unknown += 1
                continue
            normal = cell_normal(dump, level, cell_id)
            if abs(normal[2]) > 1e-9:
                tilted += 1
            wanted = _expected_direction(
                dump, level, cell_id, tube_of_cell=tube, tube_axes=tube_axes
            )
            cosine = sum(a * b for a, b in zip(normal, wanted, strict=True))
            min_cos = min(min_cos, cosine)
            if cosine < MIN_ALIGNMENT:
                wrong += 1
        add(f"{label} : {len(cells)} mailles, famille connue", 0, unknown, unknown == 0)
        add(f"{label} : normales non horizontales", 0, tilted, tilted == 0)
        add(
            f"{label} : normales tournées vers la terre "
            f"(cosinus minimal >= {MIN_ALIGNMENT:g})",
            0,
            f"{wrong} mailles à contresens ou hors seuil, cosinus minimal "
            f"{min_cos:.6g}",
            wrong == 0,
        )
    return results


__all__ = ["MIN_ALIGNMENT", "cell_normal", "check_layer_normals"]
