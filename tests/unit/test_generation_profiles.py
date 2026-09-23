"""Discontinuous pressure profile -> DEFI_FONCTION points (decision 5, point 5)."""

from __future__ import annotations

import pytest

from aster_expert.generation.profiles import component_profile, doubled_profile

Point = tuple[float, float, str | None, str | None]


def test_an_interface_is_split_at_plus_minus_one_mm() -> None:
    points: list[Point] = [
        (-26.0, 66500.0, "marne", "G"),
        (-18.0, 35800.0, "marne", "G"),
        (-18.0, 80800.0, "argile", "G"),
        (-12.0, 90000.0, "argile", "G"),
    ]
    out = doubled_profile(points)
    zs = [z for z, _ in out]
    assert zs == sorted(zs)
    assert all(a < b for a, b in zip(zs, zs[1:], strict=False))
    assert (-18.001, 35800.0) in out
    assert (-17.999, 80800.0) in out
    assert (-26.0, 66500.0) in out
    assert (-12.0, 90000.0) in out


def test_a_lone_point_is_untouched() -> None:
    out = doubled_profile([(2.0, 0.0, "remblai", None)])
    assert out == [(2.0, 0.0)]


def test_more_than_two_points_at_the_same_z_is_refused() -> None:
    with pytest.raises(ValueError, match="interface ambiguë"):
        doubled_profile(
            [
                (-2.0, 1.0, "a", None),
                (-2.0, 2.0, "b", None),
                (-2.0, 3.0, "c", None),
            ]
        )


def test_component_profile_filters_by_series() -> None:
    points: list[Point] = [
        (4.0, 0.0, "remblai", "G"),
        (4.0, 12.3, "remblai", "Q1"),
        (2.0, 11.7, "remblai", "G"),
    ]
    g_only = component_profile(points, "G")
    assert g_only == [(4.0, 0.0, "remblai", "G"), (2.0, 11.7, "remblai", "G")]


def test_real_ascending_permanent_earth_pressure_profile_is_strictly_increasing() -> (
    None
):
    """The model's own G-component profile (source data order is descending
    from the crest): reversed to ascending Z, the interface order (lower
    layer ending, then upper layer starting) falls out correctly."""
    descending: list[Point] = [
        (4.0, 0.0, "remblai", "G"),
        (2.0, 11.7, "remblai", "G"),
        (-2.0, 24.0, "remblai", "G"),
        (-2.0, 21.2, "sable", "G"),
        (-9.0, 41.1, "sable", "G"),
        (-9.0, 42.4, "argile", "G"),
        (-18.0, 80.8, "argile", "G"),
        (-18.0, 35.8, "marne", "G"),
        (-26.0, 66.5, "marne", "G"),
    ]
    ascending = list(reversed(descending))
    out = doubled_profile(ascending)
    zs = [z for z, _ in out]
    assert all(a < b for a, b in zip(zs, zs[1:], strict=False))
    # doubling perturbs an interface's shared Z, it never adds or drops a point
    assert len(out) == len(descending)
