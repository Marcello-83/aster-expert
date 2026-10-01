"""Exact Kirchhoff solution of a rectangular plate simply supported on its four
edges under a uniform load (Navier double series), with an independent
cross-check of the deflection by the Lévy single series.

Plate `0 <= x <= a`, `0 <= y <= b`, flexural rigidity
`D = E h^3 / (12 (1 - nu^2))`, uniform load `q` (Pa). Navier:

    w(x, y)  = 16 q / (pi^6 D) * S_w,   S_w = sum_{m,n odd} s_m(x) s_n(y) / (m n K^2)
    Mx(x, y) = 16 q / pi^4 * sum (m^2/a^2 + nu n^2/b^2) s_m s_n / (m n K^2)
    My(x, y) = 16 q / pi^4 * sum (nu m^2/a^2 + n^2/b^2) s_m s_n / (m n K^2)

with `K = m^2/a^2 + n^2/b^2`, `s_m(x) = sin(m pi x / a)`. Moments per unit
width, positive when they stretch the face `z < 0` (sagging under a downward
load), i.e. the Kirchhoff sign convention of the classical plate theory.

The number of terms is not chosen by hand: `navier_centre` doubles the
truncation order `N` (all odd `m, n <= N`) until the relative change of every
quantity falls below `tol`, and reports the history -- that history is the
justification of the number of terms required by the lot 43 instruction. At the
centre, the alternating signs of `s_m(a/2)` make the truncation error of the
moments shrink by about 8 at each doubling of `N` (observed, lot 43) and that of
the deflection much faster.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def flexural_rigidity(young: float, poisson: float, thickness: float) -> float:
    """`D = E h^3 / (12 (1 - nu^2))` (N.m)."""
    return young * thickness**3 / (12.0 * (1.0 - poisson**2))


@dataclass(frozen=True)
class NavierSums:
    """Dimensionless double sums at one point, truncated at odd `m, n <= order`."""

    order: int
    s_w: float
    s_mx: float
    s_my: float


def navier_sums(
    a: float, b: float, poisson: float, x: float, y: float, order: int
) -> NavierSums:
    """Sums of the Navier series at `(x, y)`, all odd `m, n <= order`."""
    s_w = s_mx = s_my = 0.0
    for m in range(1, order + 1, 2):
        sm = math.sin(m * math.pi * x / a)
        am = (m / a) ** 2
        for n in range(1, order + 1, 2):
            sn = math.sin(n * math.pi * y / b)
            bn = (n / b) ** 2
            k = am + bn
            common = sm * sn / (m * n * k * k)
            s_w += common
            s_mx += (am + poisson * bn) * common
            s_my += (poisson * am + bn) * common
    return NavierSums(order=order, s_w=s_w, s_mx=s_mx, s_my=s_my)


@dataclass(frozen=True)
class NavierResult:
    """Deflection and moments at one point, with the convergence history."""

    w: float
    """Deflection (m), positive in the direction of the load."""
    mx: float
    """Bending moment Mx (N.m/m), Kirchhoff convention."""
    my: float
    """Bending moment My (N.m/m)."""
    order: int
    """Truncation order retained (odd m, n <= order)."""
    history: tuple[tuple[int, float, float, float], ...] = field(default=())
    """(order, w, mx, my) for every order tried."""
    tol: float = 0.0


def navier(
    *,
    a: float,
    b: float,
    rigidity: float,
    poisson: float,
    q: float,
    x: float,
    y: float,
    tol: float = 1.0e-10,
    start: int = 1,
    max_order: int = 8193,
) -> NavierResult:
    """Navier solution at `(x, y)`, the order doubled until every relative change
    is below `tol`. Raises `ValueError` if `max_order` is reached first."""
    history: list[tuple[int, float, float, float]] = []
    order = start
    previous: tuple[float, float, float] | None = None
    while order <= max_order:
        s = navier_sums(a, b, poisson, x, y, order)
        w = 16.0 * q / (math.pi**6 * rigidity) * s.s_w
        mx = 16.0 * q / math.pi**4 * s.s_mx
        my = 16.0 * q / math.pi**4 * s.s_my
        history.append((order, w, mx, my))
        if previous is not None and all(
            abs(new - old) <= tol * abs(new)
            for new, old in zip((w, mx, my), previous, strict=True)
        ):
            return NavierResult(
                w=w, mx=mx, my=my, order=order, history=tuple(history), tol=tol
            )
        previous = (w, mx, my)
        order = 2 * order + 1
    message = f"série de Navier non convergée à {tol:g} près avant l'ordre {max_order}"
    raise ValueError(message)


def navier_centre(
    *,
    a: float,
    b: float,
    rigidity: float,
    poisson: float,
    q: float,
    tol: float = 1.0e-10,
) -> NavierResult:
    """Navier solution at the centre `(a/2, b/2)`."""
    return navier(
        a=a, b=b, rigidity=rigidity, poisson=poisson, q=q, x=a / 2, y=b / 2, tol=tol
    )


def levy_centre_deflection(
    *, a: float, b: float, rigidity: float, q: float, tol: float = 1.0e-15
) -> float:
    """Centre deflection by the Lévy single series (independent of Navier):

    w = 4 q a^4 / (pi^5 D) sum_{m odd} (-1)^((m-1)/2) / m^5
          * [1 - (alpha_m tanh alpha_m + 2) / (2 cosh alpha_m)],
    alpha_m = m pi b / (2 a).
    """
    total = 0.0
    m = 1
    while True:
        alpha = m * math.pi * b / (2.0 * a)
        # Beyond alpha ~ 700 cosh overflows; the correction is then below 1e-300.
        correction = (
            (alpha * math.tanh(alpha) + 2.0) / (2.0 * math.cosh(alpha))
            if alpha < 700.0
            else 0.0
        )
        bracket = 1.0 - correction
        term = (-1.0) ** ((m - 1) // 2) / m**5 * bracket
        total += term
        if abs(term) <= tol * abs(total):
            break
        m += 2
    return 4.0 * q * a**4 / (math.pi**5 * rigidity) * total


__all__ = [
    "NavierResult",
    "NavierSums",
    "flexural_rigidity",
    "levy_centre_deflection",
    "navier",
    "navier_centre",
    "navier_sums",
]
