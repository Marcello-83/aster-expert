"""Unit tests for `aster_expert.rebar.model` (lot 38)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aster_expert.rebar.model import Concrete, Rectangle, Steel


def test_concrete_c35_45_matches_documented_values() -> None:
    c = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
    assert c.fcd == pytest.approx(35.0 / 1.5)
    assert c.eps_c2 == pytest.approx(2.0e-3)
    assert c.eps_cu2 == pytest.approx(3.5e-3)
    assert c.lam == pytest.approx(0.8)
    assert c.eta == pytest.approx(1.0)


def test_concrete_above_50_mpa_uses_the_other_branch() -> None:
    c = Concrete(fck=60.0, gamma_c=1.5)
    assert c.eps_c2 > 2.0e-3
    assert c.lam < 0.8
    assert c.eta < 1.0


def test_steel_b500b_matches_documented_values() -> None:
    s = Steel(fyk=500.0, gamma_s=1.15, ductility_class="B")
    assert s.fyd == pytest.approx(500.0 / 1.15)
    assert s.eps_ud == pytest.approx(0.9 * 0.05)
    assert s.stress(1.0) == pytest.approx(s.fyd)  # plateau, B2 diagram
    assert s.stress(-1.0) == pytest.approx(-s.fyd)


def test_rectangle_rejects_crossing_reinforcement_layers() -> None:
    with pytest.raises(ValidationError):
        Rectangle(width=0.3, depth=0.5, cover_pos=0.3, cover_neg=0.3)


def test_rectangle_area() -> None:
    r = Rectangle(width=1.4, depth=2.5, cover_pos=0.065, cover_neg=0.065)
    assert r.area == pytest.approx(3.5)
