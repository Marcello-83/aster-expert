"""Serviceability limit states (ELS caractéristique, ELS quasi permanent) design of a
rectangular section, EN 1992-1-1, following `R7.04.05` (`Dimensionnement à l'ELS
Caractéristique` and `... Quasi Permanent`), written independently of Code_Aster.

Elastic, cracked (no concrete in tension), homogenised section (`alpha_e = Es/Ec`).
Two-layer equilibrium (moments, forces) is solved, for a linear strain plane
parameterised by the neutral-axis depth `x` (m, from the top face), over two
pivot families: the tension-steel pivot (`sigma_s = -sigma_s_lim`, swept from a
fully tensioned section up to the balanced depth `x_bal`) and the concrete pivot
(`sigma_c = sigma_c_lim`, swept from `x_bal` up to a fully compressed section, `x
-> h`). A fully compressed section beyond that sweep is outside this scope and
reported as infeasible with a note -- `docs/essais_lot38.md` records a case where
Code_Aster finds a feasible (zero) reinforcement that this module does not, in a
strongly compressed regime; check `feasible`, never assume it.

`design_els` covers the ELS caractéristique criterion (limitation of stresses,
`sigma_c_lim`/`sigma_s_lim` given by the caller). `design_els_qp` wraps it for the
ELS quasi permanente criterion (limitation of the crack opening `wk`), following the
documented iteration on `k_var` (the fraction of `fyk` retained as the steel stress
limit): `k_var = 1` first, then halved until the crack-width condition holds, then
bisected against the previous value.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from aster_expert.rebar.model import Concrete, Design, Rectangle, Steel

_TOLERANCE = 1e-12
_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(8)


def _concrete_force_moment(
    eps_top: float, eps_bot: float, section: Rectangle, ec: float
) -> tuple[float, float]:
    """Linear elastic, no tension: force (compression positive) and moment about
    mid-depth of the concrete alone."""
    h, b = section.depth, section.width
    gradient = eps_bot - eps_top
    y0 = -eps_top / gradient if gradient != 0.0 else (h if eps_top > 0.0 else 0.0)
    top = max(0.0, min(h, y0)) if eps_top <= 0.0 else 0.0
    # compressed span: from `start` to `end` (y measured from the top fibre)
    if eps_top > 0.0 and eps_bot > 0.0:
        start, end = 0.0, h
    elif eps_top > 0.0:
        start, end = 0.0, top if gradient < 0 else max(0.0, min(h, y0))
        start, end = 0.0, max(0.0, min(h, y0))
    elif eps_bot > 0.0:
        start, end = max(0.0, min(h, y0)), h
    else:
        return 0.0, 0.0
    if end <= start:
        return 0.0, 0.0
    y = 0.5 * (end - start) * _NODES + 0.5 * (end + start)
    strain = eps_top + gradient / h * y
    sigma = ec * np.clip(strain, 0.0, None)
    weights = 0.5 * (end - start) * _WEIGHTS
    force = b * float(np.sum(weights * sigma))
    moment = b * float(np.sum(weights * sigma * (0.5 * h - y)))
    return force, moment


def _solve_layers(
    eps_top: float,
    eps_bot: float,
    section: Rectangle,
    ec: float,
    es: float,
    n_comp: float,
    m: float,
    y_top: float,
    y_bot: float,
) -> tuple[float, float] | None:
    """Areas `(as_top, as_bot)` balancing `(n_comp, m)` on the strain plane
    `eps_top -> eps_bot` (linear across `[0, h]`), `None` if degenerate."""
    h = section.depth
    fc, mc = _concrete_force_moment(eps_top, eps_bot, section, ec)
    gradient = (eps_bot - eps_top) / h
    sig_t = es * (eps_top + gradient * y_top)
    sig_b = es * (eps_top + gradient * y_bot)
    a_t, a_b = 0.5 * h - y_top, 0.5 * h - y_bot
    det = sig_t * sig_b * (a_b - a_t)
    if abs(sig_t) < 1e-9 or abs(sig_b) < 1e-9 or abs(det) < 1e-18:
        return None
    rhs_n, rhs_m = n_comp - fc, m - mc
    as_top = (rhs_n * sig_b * a_b - rhs_m * sig_b) / det
    as_bot = (rhs_m * sig_t - rhs_n * sig_t * a_t) / det
    return as_top, as_bot


def _search(
    xis: np.ndarray,
    build: Callable[[float], tuple[float, float]],
    section: Rectangle,
    ec: float,
    es: float,
    n_comp: float,
    m: float,
    y_top: float,
    y_bot: float,
) -> tuple[float, float, float] | None:
    """Best `(total, as_top, as_bot)` over `xis`, refining the sign changes of each
    area at the grid resolution (bisection on the zero crossing)."""
    best: tuple[float, float, float] | None = None
    previous: tuple[float, tuple[float, float]] | None = None
    for xi in xis:
        eps_top, eps_bot = build(float(xi))
        solved = _solve_layers(
            eps_top, eps_bot, section, ec, es, n_comp, m, y_top, y_bot
        )
        if solved is None:
            previous = None
            continue
        candidates = [solved]
        if previous is not None:
            for index in (0, 1):
                if previous[1][index] * solved[index] < 0.0:

                    def residual(t: float, index: int = index) -> float:
                        et, eb = build(t)
                        s = _solve_layers(
                            et, eb, section, ec, es, n_comp, m, y_top, y_bot
                        )
                        return float("nan") if s is None else s[index]

                    lo, hi = previous[0], float(xi)
                    f_lo = residual(lo)
                    for _ in range(60):
                        mid = 0.5 * (lo + hi)
                        f_mid = residual(mid)
                        if (f_mid > 0.0) == (f_lo > 0.0):
                            lo, f_lo = mid, f_mid
                        else:
                            hi = mid
                    root = 0.5 * (lo + hi)
                    et, eb = build(root)
                    s = _solve_layers(et, eb, section, ec, es, n_comp, m, y_top, y_bot)
                    if s is not None:
                        candidates.append(s)
        for as_top, as_bot in candidates:
            if as_top < -_TOLERANCE or as_bot < -_TOLERANCE:
                continue
            total = max(as_top, 0.0) + max(as_bot, 0.0)
            if best is None or total < best[0]:
                best = (total, max(as_top, 0.0), max(as_bot, 0.0))
        previous = (float(xi), solved)
    return best


def design_els(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    n_tension: float,
    m: float,
    *,
    sigma_c_lim: float,
    sigma_s_lim: float,
    alpha_e: float = 15.0,
    grid: int = 2000,
) -> Design:
    """Reinforcement `(as_pos, as_neg)` under a linear elastic, cracked-section
    stress limitation (`sigma_c_lim`, `sigma_s_lim`, MPa). Restricted to a partially
    tensioned section reached from the tension-steel or the concrete pivot (see
    module docstring); a fully tensioned or fully compressed section is reported
    `feasible=False`."""
    if m < 0.0:
        mirrored = Rectangle(
            width=section.width,
            depth=section.depth,
            cover_pos=section.cover_neg,
            cover_neg=section.cover_pos,
        )
        flipped = design_els(
            mirrored,
            concrete,
            steel,
            n_tension,
            -m,
            sigma_c_lim=sigma_c_lim,
            sigma_s_lim=sigma_s_lim,
            alpha_e=alpha_e,
            grid=grid,
        )
        return flipped.model_copy(
            update={"as_pos": flipped.as_neg, "as_neg": flipped.as_pos}
        )
    h = section.depth
    y_top, y_bot = section.cover_neg, h - section.cover_pos
    d = y_bot
    """Effective depth: distance from the compressed (top) face to the **tension**
    steel layer -- the reference length of the pivot family below, not `h` (R7.04.05
    parameterises `xi = x/d`, `x` the neutral-axis depth from the top face)."""
    n_comp = -n_tension
    es, ec = steel.es, steel.es / alpha_e
    eps_s_lim = sigma_s_lim / es
    eps_c_lim = sigma_c_lim / ec
    x_bal = d * (alpha_e * sigma_c_lim) / (alpha_e * sigma_c_lim + sigma_s_lim)
    """Neutral-axis depth (m) where both limits are reached together."""

    def strain(eps_top: float, x: float) -> tuple[float, float]:
        """`(eps_top, eps_bot)` for the plane through `(y=0, eps_top)` and neutral
        axis at depth `x` (strain zero there), evaluated at `y = h`."""
        return eps_top, eps_top * (1.0 - h / x)

    def steel_pivot(x: float) -> tuple[float, float]:
        return strain(eps_s_lim * x / (d - x), x)

    def concrete_pivot(x: float) -> tuple[float, float]:
        return strain(eps_c_lim, x)

    # The tension-steel pivot (`sigma_s = -sigma_s_lim`) holds not only for the
    # partially compressed section (0 < x < x_bal, R7.04.05's `0 < xi < xi_12`) but,
    # with the same formula, all the way to a fully tensioned section (x <= 0, `xi <=
    # 0`, both faces at the limit) -- `_concrete_force_moment` already clips the
    # concrete's contribution to zero there, so a single geometric sweep of `x` down
    # to a very negative value covers both regimes without a separate formula.
    x_tension_grid = x_bal - d * np.concatenate(
        ([1e13 * d], 10.0 ** np.linspace(-6.0, 6.0, grid))
    )
    best: tuple[float, float, float] | None = None
    for xs, build in (
        (x_tension_grid, steel_pivot),
        (np.linspace(x_bal * (1.0 + 1e-9), h * (1.0 - 1e-9), grid), concrete_pivot),
    ):
        found = _search(np.sort(xs), build, section, ec, es, n_comp, m, y_top, y_bot)
        if found is not None and (best is None or found[0] < best[0]):
            best = found
    if best is None:
        return Design(
            as_pos=0.0,
            as_neg=0.0,
            feasible=False,
            note=(
                "hors du domaine couvert (section entièrement tendue ou entièrement "
                "comprimée à l'ELS -- non traité par ce module)"
            ),
        )
    return Design(as_pos=best[2], as_neg=best[1])


def design_els_qp(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    n_tension: float,
    m: float,
    *,
    wk_max: float,
    phi: float,
    kt: float,
    alpha_e: float = 15.0,
    sigma_c_lim_fl: float | None = None,
    grid: int = 2000,
) -> Design:
    """ELS quasi permanente: crack-width criterion `wk <= wk_max` (m), by iteration
    on `k_var` (fraction of `fyk` used as the steel stress limit, R7.04.05,
    `Dimensionnement à l'ELS Quasi Permanent`) -- `sigma_c,lim,FL` defaults to
    `0.45 * fck` (the usual value the documentation cites)."""
    sigma_c_lim = (0.45 * concrete.fck) if sigma_c_lim_fl is None else sigma_c_lim_fl

    def crack_width(k_var: float) -> tuple[Design, float]:
        design = design_els(
            section,
            concrete,
            steel,
            n_tension,
            m,
            sigma_c_lim=sigma_c_lim,
            sigma_s_lim=k_var * steel.fyk,
            alpha_e=alpha_e,
            grid=grid,
        )
        if not design.feasible or design.total <= 0.0:
            return design, float("inf")
        as_tension = design.as_pos if m >= 0.0 else design.as_neg
        if as_tension <= 0.0:
            return design, 0.0
        # Effective tension area and steel stress (elastic, cracked, singly governed
        # by the tension layer -- consistent with `design_els`'s two covered pivots).
        h, b = section.depth, section.width
        cover = section.cover_pos if m >= 0.0 else section.cover_neg
        a_ceff = b * min(2.5 * cover, 0.5 * h)
        rho_peff = as_tension / a_ceff
        # The tension steel stress: at the design point `design_els` returned,
        # sigma_s is exactly the pivot's limit `k_var * fyk` on the tension-steel
        # pivot family, and lower (not returned by `design_els`) on the concrete
        # pivot family -- using the limit here over-estimates wk on that second
        # family, a documented conservatism, never a silent underestimate.
        sigma_s = k_var * steel.fyk
        fctm = concrete.fctm
        delta_eps = (
            sigma_s - kt * fctm / rho_peff * (1.0 + alpha_e * rho_peff)
        ) / steel.es
        s_rmax = min(
            3.4 * (25.0 / (cover * 1000.0)) ** (2.0 / 3.0) * cover
            + 0.8 * 0.425 * (phi / rho_peff),
            1.3 * h,
        )
        wk = s_rmax * max(delta_eps, 0.0)
        return design, wk

    design_a, wk_a = crack_width(1.0)
    if wk_a <= wk_max:
        return design_a
    k_b = 0.5
    design_b, wk_b = crack_width(k_b)
    for _ in range(40):
        if wk_b <= wk_max:
            break
        k_b /= 2.0
        design_b, wk_b = crack_width(k_b)
    else:
        return Design(
            as_pos=0.0,
            as_neg=0.0,
            feasible=False,
            note="aucun k_var testé (jusqu'à 2^-40) ne sature l'ouverture de fissure",
        )
    lo, hi = k_b, 1.0
    design_f = design_b
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        design_mid, wk_mid = crack_width(mid)
        if wk_mid <= wk_max:
            lo, design_f = mid, design_mid
        else:
            hi = mid
    return design_f


__all__ = ["design_els", "design_els_qp"]
