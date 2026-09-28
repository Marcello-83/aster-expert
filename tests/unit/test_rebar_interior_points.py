"""Lot 39, étape 1 : points intérieurs du domaine du béton seul
(`docs/essais_lot39.md`, critère écrit avant l'exécution).

Section of the crown beam (2,50 m in the bending plane, 1,40 m wide), C35/45,
B500B, gamma_c = 1,5, gamma_s = 1,15, alpha_cc = 1,0, cover to the bar axis 0,065 m
(the lot 38 trials). References: `CALC_FERRAILLAGE` results of lot 38
(`data/examples/lot38_essais/rapports/mess_essais.txt`, table `FERR_LOT38`) and the
hand calculation given in the lot 39 statement.
"""

from __future__ import annotations

import pytest

from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.serviceability import (
    concrete_alone_max_stress,
    design_els,
    design_els_qp,
    gross_section_stresses,
)
from aster_expert.rebar.ultimate import (
    concrete_alone_moment_capacity,
    design_ultimate,
)

_CONCRETE = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
_STEEL = Steel(fyk=500.0, gamma_s=1.15, es=210000.0)
_SECTION = Rectangle(width=1.40, depth=2.50, cover_pos=0.065, cover_neg=0.065)
_M = 2.183517


def test_case_1_pure_bending_matches_code_aster() -> None:
    result = design_ultimate(_SECTION, _CONCRETE, _STEEL, 0.0, _M)
    assert result.feasible
    assert result.as_pos == pytest.approx(2.074217960424e-03, rel=1e-6)
    assert result.as_neg == pytest.approx(0.0, abs=1e-12)


def test_case_3_tension_matches_code_aster() -> None:
    result = design_ultimate(_SECTION, _CONCRETE, _STEEL, 5.0, _M)
    assert result.feasible
    assert result.as_pos == pytest.approx(7.869024936709e-03, rel=1e-6)
    assert result.as_neg == pytest.approx(3.630975063291e-03, rel=1e-6)
    # Fully tensioned section: the sum is N / fyd (hand calculation).
    assert result.total == pytest.approx(5.0 / (500.0 / 1.15), rel=1e-6)


def test_concrete_alone_capacity_matches_hand_calculation() -> None:
    # a = N / (eta fcd b) ; M_c = N (h - a) / 2 (rectangular block, pivot A/B).
    a = 5.0 / (35.0 / 1.5 * 1.40)
    assert a == pytest.approx(0.153061, abs=1e-6)
    capacity = concrete_alone_moment_capacity(_SECTION, _CONCRETE, _STEEL, 5.0)
    assert capacity is not None
    assert capacity == pytest.approx(5.0 * (2.50 - a) / 2.0, rel=1e-6)
    assert capacity == pytest.approx(5.867347, rel=1e-6)


def test_case_2_compression_is_an_interior_point() -> None:
    result = design_ultimate(_SECTION, _CONCRETE, _STEEL, -5.0, _M)
    assert result.feasible
    assert result.as_pos == 0.0
    assert result.as_neg == 0.0
    assert "béton seul" in result.note


def test_case_2_mirrored_moment_is_also_interior() -> None:
    result = design_ultimate(_SECTION, _CONCRETE, _STEEL, -5.0, -_M)
    assert result.feasible
    assert result.total == 0.0


def test_just_beyond_the_concrete_capacity_needs_a_small_area() -> None:
    capacity = concrete_alone_moment_capacity(_SECTION, _CONCRETE, _STEEL, 5.0)
    assert capacity is not None
    result = design_ultimate(_SECTION, _CONCRETE, _STEEL, -5.0, 1.001 * capacity)
    assert result.feasible
    assert 0.0 < result.total < 1e-4


def test_no_capacity_in_tension_or_beyond_squash_load() -> None:
    assert concrete_alone_moment_capacity(_SECTION, _CONCRETE, _STEEL, -1.0) is None
    squash = _CONCRETE.fcd * _SECTION.area
    assert (
        concrete_alone_moment_capacity(_SECTION, _CONCRETE, _STEEL, 1.01 * squash)
        is None
    )


def test_case_4_els_qp_plain_concrete_needs_no_steel() -> None:
    result = design_els_qp(
        _SECTION, _CONCRETE, _STEEL, -1.0, 0.5, wk_max=0.2e-3, phi=0.025, kt=0.4
    )
    assert result.feasible
    assert result.total == 0.0


def test_case_4_plain_concrete_stress_without_tension() -> None:
    # e = 0,5 m > h/6 = 0,4167 m: compressed depth 3 (h/2 - e) = 2,25 m.
    sigma = concrete_alone_max_stress(_SECTION, 1.0, 0.5)
    assert sigma == pytest.approx(2.0 * 1.0 / (1.40 * 2.25), rel=1e-12)
    result = design_els(
        _SECTION,
        _CONCRETE,
        _STEEL,
        -1.0,
        0.5,
        sigma_c_lim=21.0,
        sigma_s_lim=400.0,
    )
    assert result.feasible
    assert result.total == 0.0


def test_case_4_gross_section_is_uncracked() -> None:
    # Hand calculation of the statement: sigma = -0,286 +/- 0,343 MPa.
    top, bottom = gross_section_stresses(_SECTION, -1.0, 0.5)
    assert top == pytest.approx(-1.0 / 3.5 + 0.5 / (1.40 * 2.50**2 / 6.0), rel=1e-6)
    assert bottom == pytest.approx(-1.0 / 3.5 - 0.5 / (1.40 * 2.50**2 / 6.0), rel=1e-6)
    assert top == pytest.approx(0.0571429, rel=1e-5)
    assert top < _CONCRETE.fctm


def test_plain_concrete_cannot_carry_pure_bending_at_els() -> None:
    assert concrete_alone_max_stress(_SECTION, 0.0, 0.5) is None
    assert concrete_alone_max_stress(_SECTION, 1.0, 1.25) is None
