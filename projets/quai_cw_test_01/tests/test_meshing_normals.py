"""Orientation des normales des couches de poussée (lot 35), sur des dumps de
synthèse : une facette de tube (plan X = 1, axe à X = 0) et un panneau de palplanche
(plan Y = 0). Ni Docker ni Salomé."""

from __future__ import annotations

import pytest

from aster_expert.meshing.invariants import MedDump
from quai_cw_test_01.meshing.normals import cell_normal, check_layer_normals

_COORDS = [
    # facette de tube, plan X = 1 (nœuds 0 à 3)
    (1.0, 0.0, 0.0),
    (1.0, 0.2, 0.0),
    (1.0, 0.2, 1.0),
    (1.0, 0.0, 1.0),
    # panneau de palplanche, plan Y = 0 (nœuds 4 à 7)
    (2.0, 0.0, 0.0),
    (3.0, 0.0, 0.0),
    (3.0, 0.0, 1.0),
    (2.0, 0.0, 1.0),
]
_TUBE_OK = [0, 1, 2, 3]  # normale +X : radiale sortante (axe à X = 0)
_SHEET_FLIPPED = [4, 5, 6, 7]  # normale -Y : vers le bassin, à contresens
_SHEET_OK = [4, 7, 6, 5]  # normale +Y : vers la terre


def _dump(
    tube: list[int], sheet: list[int], *, groups: dict[str, list[int]]
) -> MedDump:
    return MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": _COORDS,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4", "NORM_QUAD4"],
                    "connectivity": [tube, sheet],
                }
            },
            "groups": [
                {"name": name, "level": 0, "ids": ids} for name, ids in groups.items()
            ],
        }
    )


_GROUPS = {"TUBE_01": [0], "PALPS": [1], "GEN_COUCHE_SABLE": [0, 1]}


def _check(dump: MedDump) -> list[tuple[str, bool]]:
    results = check_layer_normals(
        dump,
        layer_groups=["GEN_COUCHE_SABLE"],
        tube_axes={"TUBE_01": 0.0},
        sheet_group="PALPS",
    )
    return [(r.label, r.ok) for r in results]


def test_right_hand_normal_follows_the_node_order() -> None:
    dump = _dump(_TUBE_OK, _SHEET_OK, groups=_GROUPS)

    assert cell_normal(dump, 0, 0) == pytest.approx((1.0, 0.0, 0.0))
    assert cell_normal(dump, 0, 1) == pytest.approx((0.0, 1.0, 0.0))
    assert cell_normal(_dump(_TUBE_OK, _SHEET_FLIPPED, groups=_GROUPS), 0, 1) == (
        pytest.approx((0.0, -1.0, 0.0))
    )


def test_every_cell_facing_the_land_side_is_accepted() -> None:
    results = _check(_dump(_TUBE_OK, _SHEET_OK, groups=_GROUPS))

    assert len(results) == 3
    assert all(ok for _, ok in results)


def test_altered_mesh_with_a_flipped_cell_is_rejected() -> None:
    """Altération : le panneau de palplanche regarde le bassin (-Y)."""
    results = _check(_dump(_TUBE_OK, _SHEET_FLIPPED, groups=_GROUPS))

    failed = [label for label, ok in results if not ok]
    assert failed == [
        "normales de GEN_COUCHE_SABLE : normales tournées vers la terre "
        "(cosinus minimal >= 0.9)"
    ]


def test_a_flipped_tube_facet_is_rejected_too() -> None:
    results = _check(_dump(_TUBE_OK[::-1], _SHEET_OK, groups=_GROUPS))

    assert [ok for _, ok in results] == [True, True, False]


def test_a_cell_of_no_known_family_is_rejected() -> None:
    groups = {
        "TUBE_01": [0],
        "GEN_COUCHE_SABLE": [0, 1],
    }  # la palplanche n'a pas de famille

    results = _check(_dump(_TUBE_OK, _SHEET_OK, groups=groups))

    assert results[0] == (
        "normales de GEN_COUCHE_SABLE : 2 mailles, famille connue",
        False,
    )


def test_an_absent_layer_group_is_reported() -> None:
    groups = {"TUBE_01": [0], "PALPS": [1]}

    results = _check(_dump(_TUBE_OK, _SHEET_OK, groups=groups))

    assert results == [("normales de GEN_COUCHE_SABLE : groupe présent", False)]
