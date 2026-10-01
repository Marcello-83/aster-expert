"""Référence de Navier de la dalle (lot 43) : convergence de la série et
contrôles indépendants (série de Lévy, symétrie, coefficients tabulés)."""

from __future__ import annotations

import math

import pytest

from dalle_appuyee_01.navier import (
    flexural_rigidity,
    levy_centre_deflection,
    navier,
    navier_centre,
)


def test_flexural_rigidity() -> None:
    assert flexural_rigidity(12.0, 0.0, 1.0) == pytest.approx(1.0, rel=1e-15)
    assert flexural_rigidity(1.0, 0.5, 1.0) == pytest.approx(1.0 / 9.0, rel=1e-15)


@pytest.mark.parametrize("ratio", [1.0, 1.5, 2.0])
def test_navier_deflection_matches_levy(ratio: float) -> None:
    """Deux séries indépendantes de la même solution de Kirchhoff."""
    nav = navier_centre(a=1.0, b=ratio, rigidity=1.0, poisson=0.3, q=1.0, tol=1e-9)
    levy = levy_centre_deflection(a=1.0, b=ratio, rigidity=1.0, q=1.0)
    assert nav.w == pytest.approx(levy, rel=1e-9)


def test_square_plate_moments_are_equal() -> None:
    res = navier_centre(a=2.0, b=2.0, rigidity=3.0, poisson=0.2, q=5.0, tol=1e-8)
    assert res.mx == pytest.approx(res.my, rel=1e-14)


def test_tabulated_coefficients() -> None:
    """Coefficients classiques (Timoshenko et Woinowsky-Krieger, plaque appuyée
    sous charge uniforme, nu = 0,3), donnés à trois chiffres significatifs :
    w = alpha q a^4 / D, Mx = beta q a^2, My = beta1 q a^2."""
    sq = navier_centre(a=1.0, b=1.0, rigidity=1.0, poisson=0.3, q=1.0, tol=1e-8)
    assert sq.w == pytest.approx(0.00406, abs=5e-6)
    assert sq.mx == pytest.approx(0.0479, abs=5e-5)
    r15 = navier_centre(a=1.0, b=1.5, rigidity=1.0, poisson=0.3, q=1.0, tol=1e-8)
    assert r15.w == pytest.approx(0.00772, abs=5e-6)
    assert r15.mx == pytest.approx(0.0812, abs=5e-5)
    assert r15.my == pytest.approx(0.0498, abs=5e-5)


def test_orientation_swaps_moments() -> None:
    """Tourner la dalle de 90° échange Mx et My, la flèche ne change pas."""
    one = navier_centre(a=6.0, b=4.0, rigidity=1.0, poisson=0.2, q=1.0, tol=1e-8)
    two = navier_centre(a=4.0, b=6.0, rigidity=1.0, poisson=0.2, q=1.0, tol=1e-8)
    assert one.w == pytest.approx(two.w, rel=1e-12)
    assert one.mx == pytest.approx(two.my, rel=1e-8)
    assert one.my == pytest.approx(two.mx, rel=1e-8)


def test_history_documents_the_number_of_terms() -> None:
    res = navier_centre(a=6.0, b=4.0, rigidity=1.0, poisson=0.2, q=1.0, tol=1e-6)
    orders = [h[0] for h in res.history]
    assert orders[-1] == res.order
    assert all(o2 == 2 * o1 + 1 for o1, o2 in zip(orders, orders[1:], strict=False))
    last, before = res.history[-1], res.history[-2]
    for i in (1, 2, 3):
        assert abs(last[i] - before[i]) <= 1e-6 * abs(last[i])


def test_deflection_vanishes_on_edges() -> None:
    res = navier(a=6.0, b=4.0, rigidity=1.0, poisson=0.2, q=1.0, x=0.0, y=2.0, tol=1e-6)
    assert abs(res.w) < 1e-15
    assert abs(res.mx) < 1e-15


def test_non_convergence_is_refused() -> None:
    with pytest.raises(ValueError, match="non convergée"):
        navier(
            a=1.0,
            b=1.0,
            rigidity=1.0,
            poisson=0.3,
            q=1.0,
            x=0.5,
            y=0.5,
            tol=0.0,
            max_order=15,
        )


def test_linearity_in_load() -> None:
    one = navier_centre(a=6.0, b=4.0, rigidity=2.0, poisson=0.2, q=1.0, tol=1e-8)
    ten = navier_centre(a=6.0, b=4.0, rigidity=2.0, poisson=0.2, q=10.0, tol=1e-8)
    assert ten.w == pytest.approx(10 * one.w, rel=1e-13)
    assert math.isclose(ten.mx, 10 * one.mx, rel_tol=1e-13)
