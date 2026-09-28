"""Biaxial bending of a rectangular section at the ULS, following the procedure
`R7.04.05` documents for `CALC_FERRAILLAGE` in 1D (lot 39), written independently of
Code_Aster.

`R7.04.05` (§ Calcul du ferraillage longitudinal en flexion déviée): the section is
designed separately for `(N, M_y)` and `(N, M_z)`; while Bresler's inequality
(EN 1992-1-1, 5.8.9(4), Expression (5.39)) `(M_z/M_Rz)^a + (M_y/M_Ry)^a <= 1` fails,
the four areas are increased in proportion by 10 % of the total area. `M_Rz`,
`M_Ry` are the resisting moments of each direction with its own pair of areas
under the acting `N`; `a` is interpolated from `N/N_R`
(`N_R = A_c fcd + A_s fyd`): 1 below 0,1, 1,5 at 0,7, 2 at 1,0.

Faces (`U4.81.42`, composition of the field; signs established by the lot 39
`limites` essai): `MFZ > 0` puts `AYS` (face `+y`) in tension, `MFY > 0` puts
`AZS` (face `+z`) in tension. Conventions of the package otherwise
(`aster_expert.rebar.model`): MN, MN.m, m, MPa; `n_tension` positive in tension.

Checked against the executed essai `devie_1`/`devie_3` (lot 39): the areas are
the direction-by-direction ones times 1,1^8, to 1e-6 relative
(`tests/unit/test_rebar_biaxial.py`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.ultimate import (
    ConcreteModel,
    _families,
    _Plane,
    concrete_parabola_rectangle,
    concrete_rectangle,
    design_ultimate,
)

MAX_ITERATIONS = 200


class BiaxialDesign(BaseModel):
    """Areas of the four faces (m2) and how they were obtained."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ays: float
    ayi: float
    azs: float
    azi: float
    iterations: int
    """Number of 10 % increases applied (0: no biaxial correction)."""
    bresler: float | None
    """Left-hand side of Bresler's inequality at the returned areas (`None` when
    one of the two moments is zero)."""
    feasible: bool = True
    note: str = ""


def _internal(
    plane: _Plane,
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    as_top: float,
    as_bot: float,
    model: ConcreteModel,
) -> tuple[float, float]:
    """Internal force (compression positive) and moment about mid-depth of the
    section with steel `as_top` at `cover_neg` and `as_bot` at `h - cover_pos`."""
    h = section.depth
    if model == "rectangle" and plane.pivot != "C":
        fc, mc = concrete_rectangle(
            plane.x if plane.x is not None else 0.0, section, concrete
        )
    else:
        fc, mc = concrete_parabola_rectangle(plane.eps0, plane.eps1, section, concrete)
    y_top, y_bot = section.cover_neg, h - section.cover_pos
    gradient = (plane.eps1 - plane.eps0) / h
    sig_t = steel.stress(plane.eps0 + gradient * y_top)
    sig_b = steel.stress(plane.eps0 + gradient * y_bot)
    force = fc + as_top * sig_t + as_bot * sig_b
    moment = (
        mc + as_top * sig_t * (0.5 * h - y_top) + as_bot * sig_b * (0.5 * h - y_bot)
    )
    return force, moment


def resisting_moment(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    as_pos: float,
    as_neg: float,
    n_tension: float,
    *,
    model: ConcreteModel = "rectangle",
) -> float | None:
    """Ultimate moment (MN.m, >= 0) with the **positive** face in tension, under
    the axial force `n_tension`, on the ultimate strain-plane family of
    `design_ultimate`. `None` when no ultimate plane balances the axial force."""
    n_comp = -n_tension
    y_bot = section.depth - section.cover_pos
    for _name, grid, build in _families(section, concrete, steel, y_bot):
        lo, hi = float(grid[0]), float(grid[-1])

        def residual(t: float, build=build) -> float:  # type: ignore[no-untyped-def]
            plane = build(t)
            return (
                _internal(plane, section, concrete, steel, as_neg, as_pos, model)[0]
                - n_comp
            )

        f_lo, f_hi = residual(lo), residual(hi)
        if f_lo * f_hi > 0.0:
            continue
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            f_mid = residual(mid)
            if (f_mid > 0.0) == (f_lo > 0.0):
                lo, f_lo = mid, f_mid
            else:
                hi = mid
        plane = build(0.5 * (lo + hi))
        return _internal(plane, section, concrete, steel, as_neg, as_pos, model)[1]
    return None


def bresler_exponent(n_ratio: float) -> float:
    """`a` of EN 1992-1-1 5.8.9(4) as `R7.04.05` tabulates it: 1 for
    `N/N_R <= 0,1`, linear to 1,5 at 0,7 and 2 at 1,0."""
    if n_ratio <= 0.1:
        return 1.0
    if n_ratio <= 0.7:
        return 1.0 + 0.5 * (n_ratio - 0.1) / 0.6
    return min(2.0, 1.5 + 0.5 * (n_ratio - 0.7) / 0.3)


def design_biaxial(
    width_y: float,
    width_z: float,
    cover: float,
    concrete: Concrete,
    steel: Steel,
    n_tension: float,
    mfy: float,
    mfz: float,
    *,
    model: ConcreteModel = "rectangle",
) -> BiaxialDesign:
    """Four-face areas of a rectangle `HY = width_y` (along `y`), `HZ = width_z`
    (along `z`), same bar-axis distance `cover` on every face, under
    `(n_tension, mfy, mfz)` (MN, MN.m)."""
    section_z = Rectangle(
        width=width_z, depth=width_y, cover_pos=cover, cover_neg=cover
    )
    section_y = Rectangle(
        width=width_y, depth=width_z, cover_pos=cover, cover_neg=cover
    )
    dz = design_ultimate(section_z, concrete, steel, n_tension, mfz, model=model)
    dy = design_ultimate(section_y, concrete, steel, n_tension, mfy, model=model)
    if not (dz.feasible and dy.feasible):
        return BiaxialDesign(
            ays=0.0,
            ayi=0.0,
            azs=0.0,
            azi=0.0,
            iterations=0,
            bresler=None,
            feasible=False,
            note=f"flexion composée non résolue : {dz.note} {dy.note}".strip(),
        )
    areas = [dz.as_pos, dz.as_neg, dy.as_pos, dy.as_neg]
    if mfy == 0.0 or mfz == 0.0:
        return BiaxialDesign(
            ays=areas[0],
            ayi=areas[1],
            azs=areas[2],
            azi=areas[3],
            iterations=0,
            bresler=None,
        )
    n_comp = -n_tension
    for iteration in range(MAX_ITERATIONS + 1):
        m_rz = resisting_moment(
            section_z if mfz > 0 else _mirror(section_z),
            concrete,
            steel,
            areas[0] if mfz > 0 else areas[1],
            areas[1] if mfz > 0 else areas[0],
            n_tension,
            model=model,
        )
        m_ry = resisting_moment(
            section_y if mfy > 0 else _mirror(section_y),
            concrete,
            steel,
            areas[2] if mfy > 0 else areas[3],
            areas[3] if mfy > 0 else areas[2],
            n_tension,
            model=model,
        )
        n_r = width_y * width_z * concrete.fcd + sum(areas) * steel.fyd
        a = bresler_exponent(n_comp / n_r)
        if m_rz is None or m_ry is None or m_rz <= 0.0 or m_ry <= 0.0:
            value = float("inf")
        else:
            value = (abs(mfz) / m_rz) ** a + (abs(mfy) / m_ry) ** a
        if value <= 1.0:
            return BiaxialDesign(
                ays=areas[0],
                ayi=areas[1],
                azs=areas[2],
                azi=areas[3],
                iterations=iteration,
                bresler=value,
            )
        total = sum(areas)
        areas = [area + area / total * 0.1 * total for area in areas]
    return BiaxialDesign(
        ays=areas[0],
        ayi=areas[1],
        azs=areas[2],
        azi=areas[3],
        iterations=MAX_ITERATIONS,
        bresler=None,
        feasible=False,
        note="inéquation de Bresler non vérifiée après le nombre maximal d'itérations",
    )


def _mirror(section: Rectangle) -> Rectangle:
    return Rectangle(
        width=section.width,
        depth=section.depth,
        cover_pos=section.cover_neg,
        cover_neg=section.cover_pos,
    )


__all__ = [
    "BiaxialDesign",
    "bresler_exponent",
    "design_biaxial",
    "resisting_moment",
]
