"""Shear and torsion of a rectangular reinforced concrete section, EN 1992-1-1
(lot 39), outside Code_Aster.

Units of the package (`aster_expert.rebar.model`): m, MPa, MN, MN.m, m2, m2/m.

Articles implemented, vertical links (`alpha = 90 deg`), no prestress:

- 6.2.2(1): `V_Rd,c`, Expressions (6.2a) and (6.2b), with the recommended
  `C_Rd,c = 0,18/gamma_c`, `v_min = 0,035 k^(3/2) fck^(1/2)` (6.3N), `k1 = 0,15`;
- 6.2.3(3): `V_Rd,s = Asw/s z fywd cot(theta)` (6.8) and
  `V_Rd,max = alpha_cw bw z nu1 fcd / (cot(theta) + tan(theta))` (6.9), with
  `1 <= cot(theta) <= 2,5` (6.7N), `nu1 = nu = 0,6 (1 - fck/250)` (6.6N) and
  `alpha_cw` of Note 3 (σcp-dependent);
- 6.3.2: thin-walled closed section equivalent to the solid section, `t_ef = A/u`
  but not less than twice the distance from the edge to the axis of the
  longitudinal bars (6.3.2(1)); `A_k`, `u_k` on the centre-line of the walls;
  wall shear flow `tau t_ef = T_Ed / (2 A_k)` (6.26); longitudinal torsion steel
  `sum(A_sl) fyd / u_k = T_Ed / (2 A_k) cot(theta)` (6.28);
  `T_Rd,max = 2 nu alpha_cw fcd A_k t_ef sin(theta) cos(theta)` (6.30);
  crushing criterion `T_Ed/T_Rd,max + V_Ed/V_Rd,max <= 1` (6.29); no shear or
  torsion reinforcement beyond the minimum when
  `T_Ed/T_Rd,c + V_Ed/V_Rd,c <= 1` (6.31), `T_Rd,c` obtained with `tau = fctd`.
- Torsion links: from 6.3.2(3) (wall shear force `V_Ed,i = tau t_ef z_i`,
  (6.27)) designed as shear by 6.2.3(3): per wall and per leg,
  `A_t/s = T_Ed / (2 A_k fywd cot(theta))`.

The strut angle is common to shear and torsion; the design takes the largest
`cot(theta)` of `[1; 2,5]` that satisfies (6.29), which minimises the links.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from aster_expert.rebar.model import Concrete, Rectangle, Steel

COT_THETA_MIN = 1.0
COT_THETA_MAX = 2.5
"""Recommended limits of (6.7N)."""


class ThinWall(BaseModel):
    """Equivalent thin-walled section of 6.3.2(1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    t_ef: float
    a_k: float
    u_k: float


class ShearTorsionDesign(BaseModel):
    """Result for one direction of shear with the concomitant torsion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    v_rd_c: float
    """MN, (6.2a)/(6.2b)."""
    t_rd_c: float
    """MN.m, torsional cracking moment (`tau = fctd` in (6.26))."""
    concrete_ratio: float
    """`T_Ed/T_Rd,c + V_Ed/V_Rd,c` (6.31): no calculated links when <= 1."""
    cot_theta: float
    z: float
    asw_s: float
    """Shear links, m2/m, all legs of one link together (6.8)."""
    at_s: float
    """Torsion links, m2/m, per leg in one wall (6.27 with 6.8)."""
    asl_torsion: float
    """Longitudinal torsion steel, m2, whole perimeter (6.28)."""
    crushing_ratio: float
    """`T_Ed/T_Rd,max + V_Ed/V_Rd,max` at `cot_theta` (6.29); > 1: struts crush."""
    feasible: bool
    note: str = ""


def thin_wall(section: Rectangle) -> ThinWall:
    """`t_ef = max(A/u, 2 c)`, `A_k = (b - t_ef)(h - t_ef)`,
    `u_k = 2 (b - t_ef + h - t_ef)` (6.3.2(1)); `c` is the larger of the two cover
    distances to the bar axis."""
    b, h = section.width, section.depth
    t_ef = max(b * h / (2.0 * (b + h)), 2.0 * max(section.cover_pos, section.cover_neg))
    return ThinWall(
        t_ef=t_ef,
        a_k=(b - t_ef) * (h - t_ef),
        u_k=2.0 * ((b - t_ef) + (h - t_ef)),
    )


def nu(fck: float) -> float:
    """Strength reduction factor for concrete cracked in shear, (6.6N)."""
    return 0.6 * (1.0 - fck / 250.0)


def alpha_cw(sigma_cp: float, fcd: float) -> float:
    """6.2.3(3), Note 3 (recommended), `sigma_cp` MPa, compression positive."""
    if sigma_cp <= 0.0:
        return 1.0
    if sigma_cp <= 0.25 * fcd:
        return 1.0 + sigma_cp / fcd
    if sigma_cp <= 0.5 * fcd:
        return 1.25
    return 2.5 * (1.0 - sigma_cp / fcd)


def v_rd_c(
    section: Rectangle,
    concrete: Concrete,
    *,
    d: float,
    as_l: float,
    sigma_cp: float,
) -> float:
    """`V_Rd,c` (MN), 6.2.2(1), (6.2a) with its lower bound (6.2b); `d` in m (`k`
    uses it in mm), `as_l` the tension steel (m2), `sigma_cp` MPa (compression
    positive, limited to `0,2 fcd`)."""
    bw = section.width
    k = min(1.0 + math.sqrt(200.0 / (d * 1000.0)), 2.0)
    rho_l = min(as_l / (bw * d), 0.02)
    sigma = min(sigma_cp, 0.2 * concrete.fcd)
    c_rd_c = 0.18 / concrete.gamma_c
    v_min = 0.035 * k**1.5 * math.sqrt(concrete.fck)
    k1 = 0.15
    v_a = (c_rd_c * k * (100.0 * rho_l * concrete.fck) ** (1.0 / 3.0) + k1 * sigma) * (
        bw * d
    )
    v_b = (v_min + k1 * sigma) * bw * d
    return float(max(v_a, v_b))


def fctd(concrete: Concrete, alpha_ct: float = 1.0) -> float:
    """`fctd = alpha_ct fctk,0.05 / gamma_c` (3.1.6(2), (3.16)), with
    `fctk,0.05 = 0,7 fctm` (Table 3.1)."""
    return alpha_ct * 0.7 * concrete.fctm / concrete.gamma_c


def design_shear_torsion(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    *,
    v_ed: float,
    t_ed: float,
    n_comp: float = 0.0,
    as_l: float = 0.0,
    z: float | None = None,
) -> ShearTorsionDesign:
    """Links and longitudinal torsion steel for a shear force `v_ed` acting in the
    plane of `section.depth` (`bw = section.width`) with the torsion `t_ed`.

    `d = depth - cover_pos` (the tension layer of the positive face), `z = 0,9 d` by
    default (6.2.3(1)). Magnitudes are used (`abs`)."""
    v, t = abs(v_ed), abs(t_ed)
    b, h = section.width, section.depth
    d = h - section.cover_pos
    lever = 0.9 * d if z is None else z
    fcd, fywd = concrete.fcd, steel.fyd
    sigma_cp = n_comp / (b * h)
    wall = thin_wall(section)
    acw = alpha_cw(sigma_cp, fcd)
    nu1 = nu(concrete.fck)
    vrdc = v_rd_c(section, concrete, d=d, as_l=as_l, sigma_cp=sigma_cp)
    trdc = fctd(concrete) * 2.0 * wall.a_k * wall.t_ef
    concrete_ratio = v / vrdc + t / trdc

    def crushing(cot: float) -> float:
        s_c = cot / (1.0 + cot * cot)  # sin(theta) cos(theta)
        v_max = acw * b * lever * nu1 * fcd * s_c
        t_max = 2.0 * nu1 * acw * fcd * wall.a_k * wall.t_ef * s_c
        return v / v_max + t / t_max

    if crushing(COT_THETA_MAX) <= 1.0:
        cot = COT_THETA_MAX
    elif crushing(COT_THETA_MIN) > 1.0:
        return ShearTorsionDesign(
            v_rd_c=vrdc,
            t_rd_c=trdc,
            concrete_ratio=concrete_ratio,
            cot_theta=COT_THETA_MIN,
            z=lever,
            asw_s=0.0,
            at_s=0.0,
            asl_torsion=0.0,
            crushing_ratio=crushing(COT_THETA_MIN),
            feasible=False,
            note="écrasement des bielles pour tout cot(theta) de [1 ; 2,5] (6.29)",
        )
    else:
        lo, hi = COT_THETA_MIN, COT_THETA_MAX
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if crushing(mid) <= 1.0:
                lo = mid
            else:
                hi = mid
        cot = lo
    if concrete_ratio <= 1.0:
        return ShearTorsionDesign(
            v_rd_c=vrdc,
            t_rd_c=trdc,
            concrete_ratio=concrete_ratio,
            cot_theta=cot,
            z=lever,
            asw_s=0.0,
            at_s=0.0,
            asl_torsion=0.0,
            crushing_ratio=crushing(cot),
            feasible=True,
            note="béton seul suffisant (6.31) : armatures minimales seulement",
        )
    return ShearTorsionDesign(
        v_rd_c=vrdc,
        t_rd_c=trdc,
        concrete_ratio=concrete_ratio,
        cot_theta=cot,
        z=lever,
        asw_s=v / (lever * fywd * cot),
        at_s=t / (2.0 * wall.a_k * fywd * cot),
        asl_torsion=t * wall.u_k * cot / (2.0 * wall.a_k * steel.fyd),
        crushing_ratio=crushing(cot),
        feasible=True,
    )


__all__ = [
    "COT_THETA_MAX",
    "COT_THETA_MIN",
    "ShearTorsionDesign",
    "ThinWall",
    "alpha_cw",
    "design_shear_torsion",
    "fctd",
    "nu",
    "thin_wall",
    "v_rd_c",
]
