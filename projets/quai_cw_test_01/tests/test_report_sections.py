"""Lot 37 : efforts d'ensemble d'un tube, sur un tube synthétique (polygone régulier
à 40 facettes, deux rangées de mailles) dont les efforts de coque sont imposés."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest

from quai_cw_test_01.report import sections as sec

_N = 40
_R = 0.71
_Z = (0.0, 0.25, 0.5)


def _ring(z: float) -> np.ndarray:
    theta = 2.0 * math.pi * np.arange(_N) / _N
    return np.stack([_R * np.cos(theta), _R * np.sin(theta), np.full(_N, z)], axis=1)


def _cells(
    field: Callable[[str, np.ndarray], float],
) -> list[tuple[np.ndarray, dict[str, np.ndarray]]]:
    """Mailles de deux rangées ; `field(comp, points)` donne la valeur nodale."""
    out = []
    for z0, z1 in zip(_Z[:-1], _Z[1:], strict=True):
        lo, hi = _ring(z0), _ring(z1)
        for i in range(_N):
            j = (i + 1) % _N
            # sens de la connectivité : normale sortante (radiale)
            points = np.array([lo[i], lo[j], hi[j], hi[i]])
            values = {
                c: np.array([field(c, p) for p in points])
                for c in ("NXX", "NXY", "QX", "MXX")
            }
            out.append((points, values))
    return out


def _flat(value: float) -> Callable[[str, np.ndarray], float]:
    return lambda comp, p: value if comp == "NXX" else 0.0


def test_uniform_nxx_gives_n_times_the_polygon_perimeter() -> None:
    levels = sec.level_forces(_cells(_flat(2.0e5)), (0.0, 0.0))
    assert [lv.z for lv in levels] == list(_Z)
    for lv in levels:
        assert lv.mean.n == pytest.approx(
            2.0e5 * sec.polygon_perimeter(_R, _N), rel=1e-12
        )
        assert lv.mean.mx == pytest.approx(0.0, abs=1e-6)
        assert lv.mean.ty == pytest.approx(0.0, abs=1e-6)


def test_linear_nxx_in_y_gives_the_bending_moment_of_the_polygon() -> None:
    a = 3.0e5
    levels = sec.level_forces(
        _cells(lambda c, p: a * p[1] if c == "NXX" else 0.0), (0.0, 0.0)
    )
    theta = 2.0 * math.pi * np.arange(_N + 1) / _N
    y = _R * np.sin(theta)
    chord = 2.0 * _R * math.sin(math.pi / _N)
    integral = float(np.sum(chord * (y[:-1] ** 2 + y[:-1] * y[1:] + y[1:] ** 2) / 3.0))
    for lv in levels:
        assert lv.mean.mx == pytest.approx(a * integral, rel=1e-12)
        assert lv.mean.n == pytest.approx(0.0, abs=1e-6)
        assert lv.mean.my == pytest.approx(0.0, abs=1e-6)


def test_moment_about_y_uses_the_opposite_sign_of_x() -> None:
    a = 1.0e5
    levels = sec.level_forces(
        _cells(lambda c, p: a * p[0] if c == "NXX" else 0.0), (0.0, 0.0)
    )
    chord = 2.0 * _R * math.sin(math.pi / _N)
    theta = 2.0 * math.pi * np.arange(_N + 1) / _N
    x = _R * np.cos(theta)
    integral = float(np.sum(chord * (x[:-1] ** 2 + x[:-1] * x[1:] + x[1:] ** 2) / 3.0))
    assert levels[1].mean.my == pytest.approx(-a * integral, rel=1e-12)
    assert levels[1].mean.mx == pytest.approx(0.0, abs=1e-6)


def test_shear_flow_of_a_thin_tube_recovers_the_shear_force() -> None:
    """Écoulement de cisaillement d'un tube mince sous un effort tranchant `V` selon
    Y : `NXY = -V cos(phi) / (pi R)`, avec `y_l = n ^ Z = (sin phi, -cos phi)`, donne
    `TY = V` aux erreurs de facettisation près (O(1/n^2), 0,4 % à 40 facettes)."""
    shear = 5.0e5

    def field(comp: str, p: np.ndarray) -> float:
        phi = math.atan2(p[1], p[0])
        return -shear * math.cos(phi) / (math.pi * _R) if comp == "NXY" else 0.0

    lv = sec.level_forces(_cells(field), (0.0, 0.0))[1]
    assert lv.mean.ty_nxy == pytest.approx(shear, rel=1e-2)
    assert lv.mean.tx_nxy == pytest.approx(0.0, abs=1e-3 * shear)
    assert lv.mean.ty_qx == 0.0


def test_transverse_shear_qx_acts_along_the_normal() -> None:
    """`QX = q` constant sur un tube : la force est `q n`, de somme nulle sur un anneau
    fermé, mais `QX = q cos(phi)` donne `TX = q pi R` (projection sur la normale)."""
    q = 1.0e4

    def field(comp: str, p: np.ndarray) -> float:
        phi = math.atan2(p[1], p[0])
        return q * math.cos(phi) if comp == "QX" else 0.0

    lv = sec.level_forces(_cells(field), (0.0, 0.0))[1]
    assert lv.mean.tx_qx == pytest.approx(q * math.pi * _R, rel=1e-2)
    assert lv.mean.ty_qx == pytest.approx(0.0, abs=1e-3 * q)


def test_edge_levels_have_one_side_and_inner_levels_the_mean_of_both() -> None:
    def field(comp: str, p: np.ndarray) -> float:
        return p[2] * 1.0e5 if comp == "NXX" else 0.0  # varie d'une rangée à l'autre

    levels = sec.level_forces(_cells(field), (0.0, 0.0))
    bottom, middle, top = levels
    assert bottom.below is None and bottom.above is not None
    assert top.above is None and top.below is not None
    assert middle.below is not None and middle.above is not None
    assert middle.mean.n == pytest.approx(middle.below.n, rel=1e-12)  # continu ici


def test_a_non_vertical_facet_is_refused() -> None:
    points = np.array([[0, 0, 0], [1, 0, 0.2], [1, 1, 0.5], [0, 1, 0.3]], dtype=float)
    values = {c: np.zeros(4) for c in ("NXX", "NXY", "QX", "MXX")}
    with pytest.raises(ValueError, match="arête"):
        sec.cell_edge_contributions(points, values, (0.0, 0.0))
