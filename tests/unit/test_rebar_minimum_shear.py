"""Lot 39, étape 4 : formules EN 1992-1-1 hors de Code_Aster
(`aster_expert.rebar.minimum`, `aster_expert.rebar.shear`).

Every expected value is computed by hand **in the test**, step by step, from the
article it checks; the article is named in each test. Section of the crown beam
(C35/45, B500B, gamma_c = 1,5, gamma_s = 1,15, bar axis at 0,10 m, D18/D19) unless
stated otherwise.
"""

from __future__ import annotations

import math

import pytest

from aster_expert.rebar.minimum import (
    as_min_crack_control,
    as_min_flexure,
    kc_rectangular,
    reference_bar_diameter,
    rho_w_min,
    size_factor_k,
    steel_stress_table_7_2n,
)
from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.shear import (
    alpha_cw,
    design_shear_torsion,
    fctd,
    nu,
    thin_wall,
    v_rd_c,
)

_C35 = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
_B500 = Steel(fyk=500.0, gamma_s=1.15)
_BEAM_Z = Rectangle(width=1.40, depth=2.50, cover_pos=0.10, cover_neg=0.10)
"""Bending about z_l (MFZ): h = 2,50 m in the bending plane, b = 1,40 m."""


# --- 9.2.1.1(1), Expression (9.1N) --------------------------------------------


def test_as_min_flexure_crown_beam_mfz() -> None:
    fctm = 0.30 * 35.0 ** (2.0 / 3.0)  # Table 3.1
    assert fctm == pytest.approx(3.2100, abs=1e-4)
    d = 2.50 - 0.10
    expected = 0.26 * fctm / 500.0 * 1.40 * d  # 5,6089e-3 > 0,0013 b d = 4,368e-3
    assert expected > 0.0013 * 1.40 * d
    assert as_min_flexure(1.40, d, fctm, 500.0) == pytest.approx(expected, rel=1e-12)
    assert expected == pytest.approx(5.6089e-3, rel=1e-4)


def test_as_min_flexure_lower_bound_governs_for_low_fctm() -> None:
    # fctm = 2,0 MPa: 0,26 x 2/500 = 1,04e-3 < 1,3e-3 -> 0,0013 bt d.
    assert as_min_flexure(0.3, 0.45, 2.0, 500.0) == pytest.approx(0.0013 * 0.3 * 0.45)


# --- 7.3.2(2), Expressions (7.1) and (7.2) --------------------------------------


def test_size_factor_k_recommended_values() -> None:
    assert size_factor_k(0.25) == 1.0
    assert size_factor_k(2.50) == 0.65
    assert size_factor_k(0.55) == pytest.approx(1.0 - 0.35 * 0.25 / 0.50)


def test_kc_pure_bending_is_0_4_and_pure_tension_is_1() -> None:
    assert kc_rectangular(0.0, 2.50, 3.21) == pytest.approx(0.4)
    # Tension sigma_c = -fct,eff, h = 2,5 m: h* = 1, k1 = 2/(3 x 2,5),
    # kc = 0,4 (1 + 1 / (k1 x 2,5)) = 0,4 x 2,5 = 1,0.
    assert kc_rectangular(-3.21, 2.50, 3.21) == pytest.approx(1.0)


def test_as_min_crack_control_crown_beam_pure_bending() -> None:
    # Act = b h / 2 (tension half of the uncracked section in pure bending),
    # kc = 0,4, k = 0,65 (h >= 0,80 m), fct,eff = fctm, sigma_s = fyk.
    fctm = 0.30 * 35.0 ** (2.0 / 3.0)
    act = 1.40 * 2.50 / 2.0
    expected = 0.4 * 0.65 * fctm * act / 500.0
    assert expected == pytest.approx(2.9211e-3, rel=1e-4)
    got = as_min_crack_control(kc=0.4, k=0.65, fct_eff=fctm, act=act, sigma_s=500.0)
    assert got == pytest.approx(expected, rel=1e-12)


def test_reference_bar_diameter_inverts_7_6n() -> None:
    # 7.3.3(2), (7.6N): phi_s = phi*_s (fct,eff/2,9) kc h_cr / (2 (h - d)).
    # Crown beam, MFZ faces: phi_s = 40 mm, fct,eff = 3,21, kc = 0,4,
    # h_cr = h/2 = 1,25 m, h - d = 0,10 m: factor (3,21/2,9) x 0,4 x 1,25 / 0,2
    # = 2,7672 -> phi*_s = 14,455 mm.
    fctm = 0.30 * 35.0 ** (2.0 / 3.0)
    phi_star = reference_bar_diameter(
        40.0, fct_eff=fctm, kc=0.4, h_cr=1.25, h_minus_d=0.10
    )
    assert phi_star == pytest.approx(
        40.0 / ((fctm / 2.9) * 0.4 * 1.25 / 0.2), rel=1e-12
    )
    assert phi_star == pytest.approx(14.455, rel=1e-3)


def test_steel_stress_table_7_2n_interpolates() -> None:
    # Table 7.2N, wk = 0,2 mm: 16 mm at 200 MPa, 12 mm at 240 MPa ->
    # 14,455 mm: 200 + (16 - 14,455)/4 x 40 = 215,45 MPa.
    sigma, beyond = steel_stress_table_7_2n(14.455, 0.2)
    assert sigma == pytest.approx(200.0 + (16.0 - 14.455) / 4.0 * 40.0, rel=1e-12)
    assert not beyond
    assert steel_stress_table_7_2n(16.0, 0.2) == (200.0, False)
    # Larger than the first row (25 mm at 160 MPa): bounded to 160, flagged.
    assert steel_stress_table_7_2n(25.8, 0.2) == (160.0, True)
    assert steel_stress_table_7_2n(25.0, 0.2) == (160.0, False)


def test_rho_w_min() -> None:
    # 9.2.2(5), (9.5N): 0,08 sqrt(35) / 500 = 9,466e-4.
    assert rho_w_min(35.0, 500.0) == pytest.approx(0.08 * math.sqrt(35.0) / 500.0)
    assert rho_w_min(35.0, 500.0) == pytest.approx(9.466e-4, rel=1e-3)


# --- 6.2.2, 6.2.3 ------------------------------------------------------------------


def test_nu_and_alpha_cw() -> None:
    assert nu(35.0) == pytest.approx(0.6 * (1.0 - 35.0 / 250.0))  # (6.6N) = 0,516
    fcd = 35.0 / 1.5
    assert alpha_cw(0.0, fcd) == 1.0
    assert alpha_cw(0.1 * fcd, fcd) == pytest.approx(1.1)
    assert alpha_cw(0.4 * fcd, fcd) == 1.25
    assert alpha_cw(0.8 * fcd, fcd) == pytest.approx(2.5 * 0.2)


def test_v_rd_c_textbook_beam() -> None:
    # bw = 0,30, d = 0,45, As = 1,5e-3, fck = 30, sigma_cp = 0.
    # k = 1 + sqrt(200/450) = 1,6667 ; rho = 1,5e-3/(0,3 x 0,45) = 0,011111 ;
    # C = 0,18/1,5 = 0,12 ; v = 0,12 x 1,6667 x (100 x 0,011111 x 30)^(1/3)
    #   = 0,2 x 3,2183 = 0,64366 MPa ; v_min = 0,035 x 1,6667^1,5 x sqrt(30) = 0,4104.
    c30 = Concrete(fck=30.0, gamma_c=1.5)
    section = Rectangle(width=0.30, depth=0.50, cover_pos=0.05, cover_neg=0.05)
    k = 1.0 + math.sqrt(200.0 / 450.0)
    v = 0.18 / 1.5 * k * (100.0 * 1.5e-3 / (0.30 * 0.45) * 30.0) ** (1.0 / 3.0)
    assert v == pytest.approx(0.64366, rel=1e-4)
    got = v_rd_c(section, c30, d=0.45, as_l=1.5e-3, sigma_cp=0.0)
    assert got == pytest.approx(v * 0.30 * 0.45, rel=1e-12)


def test_shear_links_textbook_beam() -> None:
    # 6.2.3(3): V_Ed = 0,30 MN, bw = 0,30, d = 0,45, z = 0,9 d = 0,405, fck = 30,
    # fcd = 20, nu1 = 0,528 ; V_Rd,max(cot 2,5) = 0,30 x 0,405 x 0,528 x 20
    # / (2,5 + 0,4) = 0,44242 >= 0,30 -> cot(theta) = 2,5 ;
    # Asw/s = 0,30 / (0,405 x 434,78 x 2,5) = 6,8149e-4 m2/m.
    c30 = Concrete(fck=30.0, gamma_c=1.5)
    section = Rectangle(width=0.30, depth=0.50, cover_pos=0.05, cover_neg=0.05)
    result = design_shear_torsion(section, c30, _B500, v_ed=0.30, t_ed=0.0)
    assert result.feasible
    assert result.cot_theta == 2.5
    assert result.z == pytest.approx(0.405)
    fywd = 500.0 / 1.15
    assert result.asw_s == pytest.approx(0.30 / (0.405 * fywd * 2.5), rel=1e-12)
    assert result.asw_s == pytest.approx(6.8149e-4, rel=1e-4)
    v_max = 0.30 * 0.405 * 0.528 * 20.0 / (2.5 + 0.4)
    assert result.crushing_ratio == pytest.approx(0.30 / v_max, rel=1e-12)


def test_shear_strut_angle_is_reduced_when_cot_2_5_crushes() -> None:
    # V_Ed = 0,55 > V_Rd,max(2,5) = 0,44242: solve 0,55 = 0,30 x 0,405 x 0,528 x 20
    # x c/(1+c^2), i.e. c/(1+c^2) = 0,55/1,28304 = 0,42867 -> c = 1,6852.
    c30 = Concrete(fck=30.0, gamma_c=1.5)
    section = Rectangle(width=0.30, depth=0.50, cover_pos=0.05, cover_neg=0.05)
    result = design_shear_torsion(section, c30, _B500, v_ed=0.55, t_ed=0.0)
    s = 0.55 / (0.30 * 0.405 * 0.528 * 20.0)
    cot = (1.0 + math.sqrt(1.0 - 4.0 * s * s)) / (2.0 * s)
    assert result.cot_theta == pytest.approx(cot, rel=1e-9)
    assert result.crushing_ratio == pytest.approx(1.0, rel=1e-9)


# --- 6.3.2 --------------------------------------------------------------------------


def test_thin_wall_crown_beam() -> None:
    # A/u = 3,5/7,8 = 0,44872 > 2 c = 0,20 ; A_k = (1,4 - t)(2,5 - t) ;
    # u_k = 2 (1,4 - t + 2,5 - t).
    wall = thin_wall(_BEAM_Z)
    t = 3.5 / 7.8
    assert wall.t_ef == pytest.approx(t, rel=1e-12)
    assert wall.a_k == pytest.approx((1.4 - t) * (2.5 - t), rel=1e-12)
    assert wall.u_k == pytest.approx(2.0 * (3.9 - 2.0 * t), rel=1e-12)
    assert wall.a_k == pytest.approx(1.9514, rel=1e-4)


def test_torsion_crown_beam() -> None:
    # T_Ed = 1,0 MN.m, V_Ed = 0 ; T_Rd,c = fctd 2 A_k t_ef with
    # fctd = 0,7 x 3,2100 / 1,5 = 1,4980 MPa -> T_Rd,c = 2,6225 MN.m > 1: no
    # calculated steel. T_Ed = 4,0 MN.m: T/T_Rd,c > 1 ;
    # T_Rd,max(2,5) = 2 x 0,516 x 1 x 23,333 x A_k x t_ef x 2,5/7,25 = 7,262 > 4
    # -> cot = 2,5 ; A_t/s = 4 / (2 A_k fywd 2,5) ; A_sl = 4 u_k 2,5 / (2 A_k fyd).
    wall = thin_wall(_BEAM_Z)
    f_ctd = 0.7 * (0.30 * 35.0 ** (2.0 / 3.0)) / 1.5
    assert fctd(_C35) == pytest.approx(f_ctd, rel=1e-12)
    small = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=0.0, t_ed=1.0)
    assert small.t_rd_c == pytest.approx(f_ctd * 2.0 * wall.a_k * wall.t_ef, rel=1e-12)
    assert small.t_rd_c == pytest.approx(2.6225, rel=1e-3)
    assert small.at_s == 0.0 and small.asl_torsion == 0.0
    big = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=0.0, t_ed=4.0)
    fyd = 500.0 / 1.15
    t_max = 2.0 * 0.516 * 1.0 * (35.0 / 1.5) * wall.a_k * wall.t_ef * 2.5 / 7.25
    assert big.cot_theta == 2.5
    assert big.crushing_ratio == pytest.approx(4.0 / t_max, rel=1e-12)
    assert big.at_s == pytest.approx(4.0 / (2.0 * wall.a_k * fyd * 2.5), rel=1e-12)
    assert big.asl_torsion == pytest.approx(
        4.0 * wall.u_k * 2.5 / (2.0 * wall.a_k * fyd), rel=1e-12
    )


def test_combined_shear_torsion_crushing_interaction() -> None:
    # (6.29): the two ratios add at the same cot(theta).
    shear = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=3.0, t_ed=0.0)
    torsion = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=0.0, t_ed=4.0)
    both = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=3.0, t_ed=4.0)
    assert shear.cot_theta == torsion.cot_theta == 2.5
    if both.cot_theta == 2.5:
        assert both.crushing_ratio == pytest.approx(
            shear.crushing_ratio + torsion.crushing_ratio, rel=1e-12
        )
    else:
        assert both.crushing_ratio == pytest.approx(1.0, rel=1e-9)


def test_struts_crushing_is_reported_infeasible() -> None:
    result = design_shear_torsion(_BEAM_Z, _C35, _B500, v_ed=50.0, t_ed=0.0)
    assert not result.feasible
    assert result.crushing_ratio > 1.0
    assert "écrasement" in result.note
