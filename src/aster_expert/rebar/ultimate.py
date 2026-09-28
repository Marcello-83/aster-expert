"""Ultimate limit state (ULS) design of a rectangular section in uniaxial bending
with axial force, EN 1992-1-1 (lot 38).

The method follows the three-pivot rule described by `R7.04.05` (`Dimensionnement à
l'ELU`), written independently of Code_Aster: for every ultimate strain plane of the
family pivot A -> pivot B -> pivot C, the two equilibrium equations (axial force and
moment) are linear in the two unknown steel areas; the design retains the plane with
the smallest total area, both areas non-negative. Concrete follows the simplified
rectangular block by default (`model="rectangle"`, only for the planes whose neutral
axis lies in the section -- pivot C, fully compressed, always uses the exact diagram
below regardless of `model`) or the parabola-rectangle diagram (integrated exactly,
piecewise Gauss-Legendre, `model="parabola_rectangle"`). `R7.04.05` documents the
rectangular block as an option ("il est aussi possible de réaliser le calcul avec
l'hypothèse d'un diagramme rectangulaire simplifié"), but the official cas test
`ssll13d.comm` (`CALC_FERRAILLAGE`, EC2) matches this module's `"rectangle"` model
to 1e-6 m^2 on every pivot-A/pivot-B case checked (`test_rebar_ultimate.py`) and the
`"parabola_rectangle"` model does not (off by 0.1-0.6 %) : `CALC_FERRAILLAGE`'s
actual ULS behaviour is the simplified block, not merely an offered alternative --
an execution finding of this lot, kept as the default here. Steel follows the
horizontal-plateau diagram.

Lot 39: a couple `(N, M)` inside the domain of the plain concrete section is not the
equilibrium of any ultimate plane with non-negative areas; `design_ultimate` now
returns zero reinforcement for it (`concrete_alone_moment_capacity`), as
`CALC_FERRAILLAGE` does, instead of reporting it infeasible.

Conventions: see `aster_expert.rebar.model`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from aster_expert.rebar.model import Concrete, Design, Rectangle, Steel

ConcreteModel = Literal["parabola_rectangle", "rectangle"]

_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(8)
_TOLERANCE = 1e-12
"""Area below which a negative value is a rounding residue, m2."""


def _pieces(eps0: float, gradient: float, h: float, eps_c2: float) -> list[float]:
    """Sorted abscissae in [0, h] where the strain crosses 0 or `eps_c2`."""
    cuts = [0.0, h]
    if gradient != 0.0:
        for level in (0.0, eps_c2):
            y = (level - eps0) / gradient
            if 0.0 < y < h:
                cuts.append(y)
    return sorted(cuts)


def concrete_parabola_rectangle(
    eps0: float,
    eps1: float,
    section: Rectangle,
    concrete: Concrete,
) -> tuple[float, float]:
    """Force (MN, compression positive) and moment about mid-depth (MN.m, positive
    when the resultant is above mid-depth, `y` measured from the top face) of the
    parabola-rectangle diagram for the linear strain plane `eps0` (top) -> `eps1`
    (bottom)."""
    h, b = section.depth, section.width
    gradient = (eps1 - eps0) / h
    fcd, eps_c2, n = concrete.fcd, concrete.eps_c2, concrete.exponent
    force = moment = 0.0
    cuts = _pieces(eps0, gradient, h, eps_c2)
    for a, c in zip(cuts[:-1], cuts[1:], strict=True):
        if c - a <= 0.0:
            continue
        y = 0.5 * (c - a) * _NODES + 0.5 * (c + a)
        eps = eps0 + gradient * y
        sigma = np.where(
            eps <= 0.0,
            0.0,
            np.where(
                eps >= eps_c2,
                fcd,
                fcd * (1.0 - np.clip(1.0 - eps / eps_c2, 0.0, 1.0) ** n),
            ),
        )
        weights = 0.5 * (c - a) * _WEIGHTS
        force += b * float(np.sum(weights * sigma))
        moment += b * float(np.sum(weights * sigma * (0.5 * h - y)))
    return force, moment


def concrete_rectangle(
    x: float, section: Rectangle, concrete: Concrete
) -> tuple[float, float]:
    """Same for the simplified rectangular block of depth `lambda * x` (neutral axis
    depth `x`, from the top face)."""
    if x <= 0.0:
        return 0.0, 0.0
    h = section.depth
    a = min(concrete.lam * x, h)
    force = concrete.eta * concrete.fcd * section.width * a
    return force, force * (0.5 * h - 0.5 * a)


class _Plane:
    """One ultimate strain plane and the equilibrium solved on it."""

    __slots__ = ("as_bot", "as_top", "eps0", "eps1", "pivot", "x")

    def __init__(
        self, eps0: float, eps1: float, pivot: Literal["A", "B", "C"], x: float | None
    ) -> None:
        self.eps0, self.eps1, self.pivot, self.x = eps0, eps1, pivot, x
        self.as_top = self.as_bot = float("nan")


def _solve(
    plane: _Plane,
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    n_comp: float,
    m: float,
    model: ConcreteModel,
    y_top: float,
    y_bot: float,
) -> bool:
    """Fill `plane.as_top`/`as_bot`; False when the plane gives no solution."""
    h = section.depth
    if model == "rectangle" and plane.pivot != "C":
        fc, mc = concrete_rectangle(
            plane.x if plane.x is not None else 0.0, section, concrete
        )
    else:
        fc, mc = concrete_parabola_rectangle(plane.eps0, plane.eps1, section, concrete)
    gradient = (plane.eps1 - plane.eps0) / h
    sig_t = steel.stress(plane.eps0 + gradient * y_top)
    sig_b = steel.stress(plane.eps0 + gradient * y_bot)
    a_t, a_b = 0.5 * h - y_top, 0.5 * h - y_bot
    det = sig_t * sig_b * (a_b - a_t)
    if abs(sig_t) < 1e-9 or abs(sig_b) < 1e-9 or abs(det) < 1e-18:
        return False
    rhs_n, rhs_m = n_comp - fc, m - mc
    plane.as_top = (rhs_n * sig_b * a_b - rhs_m * sig_b) / det
    plane.as_bot = (rhs_m * sig_t - rhs_n * sig_t * a_t) / det
    return True


def _families(
    section: Rectangle, concrete: Concrete, steel: Steel, y_bot: float
) -> list[tuple[str, np.ndarray, Callable[[float], _Plane]]]:
    """The three segments of the strain-plane family, each with a parameter grid and
    the constructor of its planes."""
    h = section.depth
    eps_ud, eps_cu2, eps_c2 = steel.eps_ud, concrete.eps_cu2, concrete.eps_c2
    x_ab = y_bot * eps_cu2 / (eps_cu2 + eps_ud)

    def pivot_a(v: float) -> _Plane:
        x = x_ab - h * 10.0**v if v > -12.0 else x_ab
        return _Plane(eps_ud * x / (y_bot - x), eps_ud * (x - h) / (y_bot - x), "A", x)

    def pivot_b(x: float) -> _Plane:
        return _Plane(eps_cu2, eps_cu2 * (x - h) / x, "B", x)

    y_c = h * (1.0 - eps_c2 / eps_cu2)

    def pivot_c(eps_b: float) -> _Plane:
        slope = (eps_b - eps_c2) / (h - y_c)
        return _Plane(eps_c2 - slope * y_c, eps_b, "C", None)

    return [
        ("A", np.concatenate(([-13.0], np.linspace(-6.0, 4.0, 1600))), pivot_a),
        ("B", np.linspace(x_ab, h, 2400)[1:], pivot_b),
        ("C", np.linspace(0.0, eps_c2, 800), pivot_c),
    ]


def _bisect(
    fun: Callable[[float], float], lo: float, hi: float, iterations: int = 80
) -> float:
    f_lo = fun(lo)
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        f_mid = fun(mid)
        if (f_mid > 0.0) == (f_lo > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def concrete_alone_moment_capacity(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    n_comp: float,
    *,
    model: ConcreteModel = "rectangle",
) -> float | None:
    """Moment (MN.m, about mid-depth) the plain concrete section carries at its
    ultimate boundary under the compression `n_comp` (MN, > 0), with the same
    concrete diagram and the same strain-plane family as `design_ultimate` (lot 39).

    `None` when `n_comp` is not a compression the plain concrete can balance
    (`n_comp <= 0` or beyond the pure-compression resistance). The concrete force
    is monotonic along the family pivot A -> B -> C, so the plane whose force equals
    `n_comp` is found by bisection on each segment's parameter.
    """
    if n_comp <= 0.0:
        return None
    y_bot = section.depth - section.cover_pos

    def concrete_of(plane: _Plane) -> tuple[float, float]:
        if model == "rectangle" and plane.pivot != "C":
            return concrete_rectangle(
                plane.x if plane.x is not None else 0.0, section, concrete
            )
        return concrete_parabola_rectangle(plane.eps0, plane.eps1, section, concrete)

    for _name, grid, build in _families(section, concrete, steel, y_bot):
        lo, hi = float(grid[0]), float(grid[-1])
        f_lo = concrete_of(build(lo))[0] - n_comp
        f_hi = concrete_of(build(hi))[0] - n_comp
        if f_lo == 0.0:
            return concrete_of(build(lo))[1]
        if f_lo * f_hi > 0.0:
            continue

        def residual(t: float, build: Callable[[float], _Plane] = build) -> float:
            return concrete_of(build(t))[0] - n_comp

        root = _bisect(residual, lo, hi, 200)
        return concrete_of(build(root))[1]
    return None


def design_ultimate(
    section: Rectangle,
    concrete: Concrete,
    steel: Steel,
    n_tension: float,
    m: float,
    *,
    model: ConcreteModel = "rectangle",
) -> Design:
    """Smallest reinforcement `(as_pos, as_neg)` balancing `(n_tension, m)`.

    A couple inside the domain of the plain concrete section (compression, and
    `|m|` at most the concrete-alone capacity under that compression) needs no
    reinforcement: zero on both faces, `feasible=True` (lot 39 -- the lot 38
    version reported such interior points as infeasible, while `CALC_FERRAILLAGE`
    returns zero; `R7.04.05` keeps the minimum total area "tout en veillant à ce
    que les deux sections soient positives").
    """
    capacity = concrete_alone_moment_capacity(
        section, concrete, steel, -n_tension, model=model
    )
    if capacity is not None and abs(m) <= capacity:
        return Design(
            as_pos=0.0,
            as_neg=0.0,
            note=(
                "point intérieur du domaine du béton seul : "
                f"|M| = {abs(m):.6g} <= M_c(N) = {capacity:.6g} MN.m"
            ),
        )
    if m < 0.0:
        mirrored = Rectangle(
            width=section.width,
            depth=section.depth,
            cover_pos=section.cover_neg,
            cover_neg=section.cover_pos,
        )
        flipped = design_ultimate(mirrored, concrete, steel, n_tension, -m, model=model)
        return flipped.model_copy(
            update={
                "as_pos": flipped.as_neg,
                "as_neg": flipped.as_pos,
            }
        )
    h = section.depth
    y_top, y_bot = section.cover_neg, h - section.cover_pos
    n_comp = -n_tension
    best: tuple[float, _Plane] | None = None

    def consider(plane: _Plane) -> None:
        nonlocal best
        if not (
            _solve(plane, section, concrete, steel, n_comp, m, model, y_top, y_bot)
        ):
            return
        if plane.as_top < -_TOLERANCE or plane.as_bot < -_TOLERANCE:
            return
        total = max(plane.as_top, 0.0) + max(plane.as_bot, 0.0)
        if best is None or total < best[0]:
            best = (total, plane)

    for _name, grid, build in _families(section, concrete, steel, y_bot):
        previous: tuple[float, _Plane] | None = None
        for value in grid:
            plane = build(float(value))
            ok = _solve(plane, section, concrete, steel, n_comp, m, model, y_top, y_bot)
            if ok:
                consider(plane)
                if previous is not None:
                    for attribute in ("as_top", "as_bot"):
                        before = getattr(previous[1], attribute)
                        after = getattr(plane, attribute)
                        if before * after < 0.0:

                            def residual(
                                t: float,
                                attribute: str = attribute,
                                build: Callable[[float], _Plane] = build,
                            ) -> float:
                                probe = build(t)
                                if not _solve(
                                    probe,
                                    section,
                                    concrete,
                                    steel,
                                    n_comp,
                                    m,
                                    model,
                                    y_top,
                                    y_bot,
                                ):
                                    return float("nan")
                                return float(getattr(probe, attribute))

                            root = _bisect(residual, previous[0], float(value))
                            consider(build(root))
                previous = (float(value), plane)
            else:
                previous = None
    if best is None:
        return Design(
            as_pos=0.0,
            as_neg=0.0,
            feasible=False,
            note="aucun plan de déformation ultime ne réalise l'équilibre",
        )
    plane = best[1]
    as_top, as_bot = max(plane.as_top, 0.0), max(plane.as_bot, 0.0)
    gradient = (plane.eps1 - plane.eps0) / h
    sigma_top = steel.stress(plane.eps0 + gradient * y_top)
    return Design(
        as_pos=as_bot,
        as_neg=as_top,
        as_neg_needed_in_compression=bool(as_top > _TOLERANCE and sigma_top > 0.0),
        pivot=plane.pivot,
        neutral_axis_depth=plane.x,
    )
