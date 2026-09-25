"""Grandeurs de la synthèse (lot 35), sur des tables de synthèse : porteurs, extrêmes,
profils, tirants, et contrôles de signe et de butée des ressorts."""

from __future__ import annotations

import pytest

from aster_expert.report import quantities as q
from aster_expert.report.tables import Record

AXES = [-2.6, 0.0, 2.6]
R = 0.71


def _row(**kw: float | str) -> Record:
    return dict(kw)


# --- porteur ----------------------------------------------------------------


def test_holder_is_the_tube_whose_circle_passes_through_the_point() -> None:
    assert q.holder_of(0.0, R, AXES, R) == "TUBE_02"
    assert q.holder_of(-2.6 - R, 0.0, AXES, R) == "TUBE_01"


def test_a_lock_point_belongs_to_the_tube_and_a_sheet_point_to_its_panel() -> None:
    assert q.holder_of(R, 0.0, AXES, R) == "TUBE_02"  # serrure : sur le tube 2
    assert q.holder_of(1.3, 0.0, AXES, R) == "PALP_02_03"
    assert q.holder_of(-1.3, 0.0, AXES, R) == "PALP_01_02"
    assert q.holder_of(0.3, 1.5, AXES, R) == ""


# --- extrêmes ---------------------------------------------------------------


def _effort_rows() -> list[Record]:
    return [
        _row(
            MAILLE="1", NOEUD="10", COOR_X=0.0, COOR_Y=R, COOR_Z=-5.0, NXX=3.0, MXX=-1.0
        ),
        _row(
            MAILLE="2", NOEUD="11", COOR_X=2.6, COOR_Y=R, COOR_Z=1.0, NXX=-7.0, MXX=4.0
        ),
        _row(
            MAILLE="3", NOEUD="12", COOR_X=-2.6, COOR_Y=R, COOR_Z=2.5, NXX=1.0, MXX=0.5
        ),
    ]


def test_extrema_give_the_value_the_level_and_the_holder() -> None:
    nxx, mxx = q.extrema(_effort_rows(), ["NXX", "MXX"], AXES, R)

    assert (nxx.maximum.value, nxx.maximum.z, nxx.maximum.holder) == (
        3.0,
        -5.0,
        "TUBE_02",
    )
    assert (nxx.minimum.value, nxx.minimum.holder, nxx.minimum.element) == (
        -7.0,
        "TUBE_03",
        "2",
    )
    assert (mxx.maximum.value, mxx.maximum.z) == (4.0, 1.0)
    assert mxx.minimum.node == "10"


def test_extrema_of_an_empty_table_is_refused() -> None:
    with pytest.raises(ValueError, match="table vide"):
        q.extrema([], ["N"], AXES, R)


def test_head_displacement_keeps_the_sign_of_the_largest_absolute_value() -> None:
    rows = [
        _row(COOR_X=0.0, COOR_Y=R, COOR_Z=2.6, DY=-0.013),
        _row(COOR_X=0.71, COOR_Y=0.0, COOR_Z=2.6, DY=-0.0129),
        _row(COOR_X=-0.71, COOR_Y=0.0, COOR_Z=2.6, DY=0.002),
    ]

    head = q.head_displacement(rows, AXES, R)

    assert head.max_abs.value == pytest.approx(-0.013)
    assert head.minimum.value == pytest.approx(-0.013)
    assert head.maximum.value == pytest.approx(0.002)
    assert head.n_nodes == 3


# --- profils, tirants -----------------------------------------------------------


def test_the_profile_averages_the_ring_at_each_level_from_top_to_bottom() -> None:
    rows = [
        _row(COOR_Z=-1.0, DY=-2.0),
        _row(COOR_Z=-1.0, DY=-4.0),
        _row(COOR_Z=0.0, DY=-1.0),
        _row(COOR_Z=0.0, DY=-1.0),
    ]

    profile = q.dy_profile(rows)

    assert [p.z for p in profile] == [0.0, -1.0]
    assert profile[1].mean == pytest.approx(-3.0)
    assert (profile[1].minimum, profile[1].maximum, profile[1].n_nodes) == (
        -4.0,
        -2.0,
        2,
    )


def test_each_tie_takes_the_effort_of_its_own_plane() -> None:
    rows = [
        _row(COOR_X=-2.6, N=100.0),
        _row(COOR_X=-2.6, N=100.0),
        _row(COOR_X=0.0, N=300.0),
        _row(COOR_X=2.6, N=100.0),
    ]

    ties = q.tie_forces(rows, AXES)

    assert [t.n for t in ties] == [100.0, 300.0, 100.0]
    assert ties[0].n_rows == 2


def test_a_tie_without_any_row_is_an_error() -> None:
    with pytest.raises(ValueError, match="tirant du tube 2"):
        q.tie_forces([_row(COOR_X=-2.6, N=1.0), _row(COOR_X=2.6, N=1.0)], AXES)


# --- ressorts : signe et butée ---------------------------------------------------

# une bande de sol : argile de -18 à -12 (butée 200 kPa constante, 2 points), aire 1 m²
_BUTEE = {
    "RESS_AV_ARGI": [(-12.0, 100e3), (-18.0, 200e3)],
    "RESS_AV_MARNE": [(-18.0, 300e3), (-26.0, 600e3)],
}
_AREAS = {
    "RESS_AV_ARGI": {(0.0, -R, -12.0): 1.0, (1.0, 0.0, -18.0): 1.0},
    "RESS_AV_MARNE": {(1.0, 0.0, -18.0): 2.0, (0.5, 0.0, -26.0): 1.0},
}
_KH = {"RESS_AV_ARGI": 35.0, "RESS_AV_MARNE": 80.0}  # MN/m3


def _nodes() -> dict[tuple[float, float, float], q.SpringNode]:
    return q.spring_nodes(_AREAS, _KH, _BUTEE)


def test_a_node_shared_by_two_bands_carries_both_stiffness_and_capacity() -> None:
    node = _nodes()[(1.0, 0.0, -18.0)]

    assert node.stiffness == pytest.approx((35.0 * 1.0 + 80.0 * 2.0) * 1e6)
    assert node.area == pytest.approx(3.0)
    # butée à -18 : 200 kPa (argile, 1 m2) + 300 kPa (marne, 2 m2)
    assert node.capacity_n == pytest.approx(200e3 * 1.0 + 300e3 * 2.0)
    assert set(node.band_stiffness) == {"RESS_AV_ARGI", "RESS_AV_MARNE"}


def test_a_level_outside_the_bearing_profile_is_refused_not_extrapolated() -> None:
    areas = {"RESS_AV_ARGI": {(0.0, -R, -30.0): 1.0}}

    with pytest.raises(ValueError, match="hors du profil de butée"):
        q.spring_nodes(areas, _KH, _BUTEE)


def _springs(dy_shared: float, dy_top: float, dy_foot: float) -> list[Record]:
    return [
        _row(COOR_X=0.0, COOR_Y=-R, COOR_Z=-12.0, DY=dy_top),
        _row(COOR_X=1.0, COOR_Y=0.0, COOR_Z=-18.0, DY=dy_shared),
        _row(COOR_X=0.5, COOR_Y=0.0, COOR_Z=-26.0, DY=dy_foot),
    ]


def test_compression_is_a_displacement_toward_the_basin() -> None:
    checks = q.spring_checks(_springs(-0.001, -0.001, -0.001), _nodes(), AXES, R)

    assert checks.sign.n_compression == 3
    assert checks.sign.n_tension == 0
    assert checks.sign.z_min_tension is None
    assert checks.bearing.n_compressed == 3
    assert checks.bearing.n_over_100 == 0


def test_tension_is_counted_with_its_levels_and_its_largest_reaction() -> None:
    checks = q.spring_checks(_springs(0.002, -0.001, 0.001), _nodes(), AXES, R)

    sign = checks.sign
    assert (sign.n_tension, sign.n_compression, sign.n_null) == (2, 1, 0)
    assert (sign.z_min_tension, sign.z_max_tension) == (-26.0, -18.0)
    # le plus grand k*DY est celui du nœud partagé : (35 + 160) MN/m x 0,002 m
    assert sign.max_tension_reaction_n == pytest.approx(195e6 * 0.002)
    assert sign.at_max_tension is not None
    assert sign.at_max_tension.z == -18.0
    assert checks.bearing.n_compressed == 1


def test_a_zero_displacement_is_neither_tension_nor_compression() -> None:
    checks = q.spring_checks(_springs(0.0, -0.001, -0.001), _nodes(), AXES, R)

    assert (checks.sign.n_tension, checks.sign.n_compression, checks.sign.n_null) == (
        0,
        2,
        1,
    )


def test_bearing_ratio_is_reaction_over_capacity_and_flags_over_100_percent() -> None:
    # nœud de tête : k = 35e6 N/m, capacité 100 kPa x 1 m2 = 100 kN ; u = 4 mm
    # -> réaction 140 kN, taux 140 %
    rows = [_row(COOR_X=0.0, COOR_Y=-R, COOR_Z=-12.0, DY=-0.004)]

    checks = q.spring_checks(rows, _nodes(), AXES, R)

    bearing = checks.bearing
    assert bearing.max_ratio == pytest.approx(1.4)
    assert bearing.n_over_100 == 1
    assert bearing.at_max is not None
    assert bearing.at_max.z == -12.0
    assert bearing.max_pressure_kpa == pytest.approx(140.0)
    assert bearing.limit_kpa == pytest.approx(100.0)
    assert bearing.n_over_100_holders == ["TUBE_02"]


def test_layer_forces_sum_the_force_exerted_on_the_wall_by_band() -> None:
    rows = [_row(COOR_X=1.0, COOR_Y=0.0, COOR_Z=-18.0, DY=-0.001)]

    checks = q.spring_checks(rows, _nodes(), AXES, R)

    # force sur l'écran = -k*DY : vers la terre pour un déplacement vers le bassin
    assert checks.layer_forces_n["RESS_AV_ARGI"] == pytest.approx(35e6 * 0.001)
    assert checks.layer_forces_n["RESS_AV_MARNE"] == pytest.approx(160e6 * 0.001)
    assert checks.total_force_n == pytest.approx(195e6 * 0.001)


def test_an_unknown_spring_node_is_refused() -> None:
    rows = [_row(COOR_X=9.0, COOR_Y=9.0, COOR_Z=-15.0, DY=-0.001)]

    with pytest.raises(ValueError, match="nœud de ressort inconnu"):
        q.spring_checks(rows, _nodes(), AXES, R)


# --- réactions --------------------------------------------------------------


def test_only_the_really_blocked_components_of_a_support_group_are_marked() -> None:
    row = _row(DX=1.0, DY=2.0, DZ=3.0)

    assert q.group_reaction("SYM_G", "SYMG", row).blocked == ["DX"]
    assert q.group_reaction("PIED_TUBES", "PIED", row).blocked == ["DZ"]
    assert q.group_reaction("ANCRAGES", "ANCR", row).blocked == ["DX", "DY", "DZ"]


# --- lecture croisée tirants / ancrages ---------------------------------------


def test_the_ties_projected_on_their_direction_balance_the_anchor_reaction() -> None:
    import math

    ties = [
        q.TieForce(tie=k, x=x, n=n, minimum=n, maximum=n, n_rows=2)
        for k, (x, n) in enumerate(((-2.6, 100e3), (0.0, 300e3), (2.6, 100e3)), 1)
    ]
    theta = math.radians(-20.0)
    direction = (math.cos(theta), math.sin(theta))
    anchor = q.GroupReaction(
        group="ANCRAGES",
        dx=0.0,
        dy=500e3 * direction[0],
        dz=500e3 * direction[1],
        blocked=["DX", "DY", "DZ"],
    )

    check = q.tie_anchor_check(ties, anchor, direction, gravity=False)

    assert check.ties_dy_n == pytest.approx(500e3 * direction[0])
    assert abs(check.gap_dy) < 1e-12
    assert abs(check.gap_dz) < 1e-12
    assert check.gravity is False


def test_under_gravity_the_vertical_gap_is_flagged_not_hidden() -> None:
    ties = [
        q.TieForce(tie=1, x=0.0, n=1000.0, minimum=1000.0, maximum=1000.0, n_rows=2)
    ]
    anchor = q.GroupReaction(
        group="ANCRAGES", dx=0.0, dy=940.0, dz=-300.0, blocked=["DX", "DY", "DZ"]
    )

    check = q.tie_anchor_check(ties, anchor, (0.94, -0.34), gravity=True)

    assert check.gravity is True
    assert check.gap_dz == pytest.approx((-340.0 - -300.0) / 300.0)
