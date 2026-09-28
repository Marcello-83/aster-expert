"""Minimum reinforcement, EN 1992-1-1 (lot 39), outside Code_Aster.

Units of the package (`aster_expert.rebar.model`): m, MPa, MN, m2.

- `as_min_flexure`: minimum longitudinal tension reinforcement of beams,
  9.2.1.1(1), Expression (9.1N).
- `as_min_crack_control`: minimum reinforcement for crack control, 7.3.2(2),
  Expression (7.1), with `k` (7.3.2(2), recommended values) and `kc` for
  rectangular sections (Expression (7.2)).
- `reference_bar_diameter`, `steel_stress_table_7_2n`: the steel stress
  `sigma_s` of (7.1) limited for the crack width, from Table 7.2N and the
  bar-diameter modification of 7.3.3(2), Expression (7.6N);
- `rho_w_min`: minimum shear reinforcement ratio of beams, 9.2.2(5),
  Expression (9.5N).

Recommended values of the EN are used; a National Annex may change them, which
the caller then passes explicitly. None of these values is a project decision.
"""

from __future__ import annotations

import math


def as_min_flexure(width_t: float, d: float, fctm: float, fyk: float) -> float:
    """`As,min = 0,26 fctm/fyk bt d >= 0,0013 bt d` (m2), EN 1992-1-1 9.2.1.1(1),
    Expression (9.1N); `width_t` is the mean width of the tension zone."""
    return max(0.26 * fctm / fyk * width_t * d, 0.0013 * width_t * d)


def size_factor_k(h: float) -> float:
    """Coefficient `k` of 7.3.2(2) (non-uniform self-equilibrating stresses),
    recommended values: 1,0 for `h <= 0,30 m`, 0,65 for `h >= 0,80 m`, linear
    interpolation between (h: the smaller of the depth and the width of the web or
    flange, m)."""
    if h <= 0.30:
        return 1.0
    if h >= 0.80:
        return 0.65
    return 1.0 + (0.65 - 1.0) * (h - 0.30) / (0.80 - 0.30)


def kc_rectangular(sigma_c: float, h: float, fct_eff: float) -> float:
    """`kc = 0,4 [1 - sigma_c / (k1 (h/h*) fct,eff)] <= 1`, EN 1992-1-1 7.3.2(2),
    Expression (7.2), for rectangular sections and webs.

    `sigma_c = N_Ed / (b h)`, MPa, **positive in compression**; `h* = h` for
    `h < 1,0 m`, `1,0 m` otherwise; `k1 = 1,5` in compression, `2 h* / (3 h)` in
    tension. The result is bounded to `[0, 1]`.
    """
    h_star = h if h < 1.0 else 1.0
    k1 = 1.5 if sigma_c >= 0.0 else 2.0 * h_star / (3.0 * h)
    kc = 0.4 * (1.0 - sigma_c / (k1 * (h / h_star) * fct_eff))
    return min(1.0, max(0.0, kc))


def as_min_crack_control(
    *, kc: float, k: float, fct_eff: float, act: float, sigma_s: float
) -> float:
    """`As,min sigma_s = kc k fct,eff Act` (m2), EN 1992-1-1 7.3.2(2), Expression
    (7.1). `act` is the area of concrete in the tension zone just before the first
    crack (m2); `sigma_s` the absolute steel stress allowed just after cracking
    (MPa, `fyk` at most; a lower value may be needed to satisfy the crack width,
    Table 7.2N -- the caller's choice, stated in its report)."""
    return kc * k * fct_eff * act / sigma_s


TABLE_7_2N: dict[float, tuple[float, ...]] = {
    0.4: (40.0, 32.0, 20.0, 16.0, 12.0, 10.0, 8.0, 6.0),
    0.3: (32.0, 25.0, 16.0, 12.0, 10.0, 8.0, 6.0, 5.0),
    0.2: (25.0, 16.0, 12.0, 8.0, 6.0, 5.0, 4.0),
}
"""EN 1992-1-1, Table 7.2N: maximum bar diameter `phi*_s` (mm) for crack control,
per `wk` (mm), for the steel stresses of `TABLE_7_2N_STRESSES` (the 450 MPa row has
no value for 0,2 mm). Transcribed by the session from the standard: to be checked
against the engineer's copy before any use beyond this first draft."""
TABLE_7_2N_STRESSES: tuple[float, ...] = (
    160.0,
    200.0,
    240.0,
    280.0,
    320.0,
    360.0,
    400.0,
    450.0,
)


def reference_bar_diameter(
    phi_s: float, *, fct_eff: float, kc: float, h_cr: float, h_minus_d: float
) -> float:
    """`phi*_s` (mm) from the actual bar diameter `phi_s` (mm), inverting
    EN 1992-1-1 7.3.3(2), Expression (7.6N) (bending, part of the section in
    compression): `phi_s = phi*_s (fct,eff/2,9) kc h_cr / (2 (h - d))`
    (`h_cr`: depth of the tensile zone just before cracking, m)."""
    return phi_s * 2.9 / fct_eff * 2.0 * h_minus_d / (kc * h_cr)


def steel_stress_table_7_2n(phi_star: float, wk: float) -> tuple[float, bool]:
    """Steel stress (MPa) for which Table 7.2N allows `phi_star` (mm) at `wk` (mm),
    linear interpolation between rows. Second item: True when `phi_star` is beyond
    the table (larger than its first row), the stress being then the table's
    lowest one, 160 MPa -- not an extrapolation, a bound the caller reports."""
    column = TABLE_7_2N[wk]
    stresses = TABLE_7_2N_STRESSES[: len(column)]
    if phi_star >= column[0]:
        return stresses[0], phi_star > column[0]
    if phi_star <= column[-1]:
        return stresses[len(column) - 1], False
    for i in range(len(column) - 1):
        hi_phi, lo_phi = column[i], column[i + 1]
        if lo_phi <= phi_star <= hi_phi:
            t = (hi_phi - phi_star) / (hi_phi - lo_phi)
            return stresses[i] + t * (stresses[i + 1] - stresses[i]), False
    raise AssertionError(phi_star)


def rho_w_min(fck: float, fyk: float) -> float:
    """`rho_w,min = 0,08 sqrt(fck) / fyk`, EN 1992-1-1 9.2.2(5), Expression
    (9.5N)."""
    return 0.08 * math.sqrt(fck) / fyk


__all__ = [
    "TABLE_7_2N",
    "TABLE_7_2N_STRESSES",
    "as_min_crack_control",
    "as_min_flexure",
    "kc_rectangular",
    "reference_bar_diameter",
    "rho_w_min",
    "size_factor_k",
    "steel_stress_table_7_2n",
]
