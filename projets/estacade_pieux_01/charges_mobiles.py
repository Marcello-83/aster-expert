"""Positions of the moving loads TS and LM2 (E8, E15, E16) and their print groups.

TS: tandem of two axles 1.20 m apart along X, two wheels 2.00 m apart along Y, square
print 0.40 m; centre of the tandem at X = mid + step k, k = -29 ... 29 (every print
on the slab, positions symmetric about the middle of the deck). LM2: one axle of two
wheels 2.00 m apart, print 0.35 m (X) x 0.60 m (Y); centre at X = mid - h/2 - step k
and mid + h/2 + step k with h the production cell (0.05 m), k = 0 ... so that every
print edge lies on a mesh line. Transverse positions: "axé" (wheels at Y = +-1.00)
and "bord de voie" on the side Y > 0 (outer wheel tangent to the lane edge).

The print of an axle is the intersection of an X band (the axle) and a Y band (the two
wheels): element groups built by `CREA_GROUP_MA/BANDE` with `CRIT_NOEUD="TOUS"`
(PAT-003),
so that each print is a union of whole cells and the pressure is uniform on it.
"""

from __future__ import annotations

from dataclasses import dataclass

from estacade_pieux_01.donnees import ModelValues

ALIGN = 1.0e-9


@dataclass(frozen=True)
class Axle:
    x: float
    """Centre of the axle along X."""
    half_x: float
    wheels_y: tuple[float, ...]
    half_y: float

    def bounds_x(self) -> tuple[float, float]:
        return (self.x - self.half_x, self.x + self.half_x)


@dataclass(frozen=True)
class MovingCase:
    name: str
    """`TSA_P00` (TS axé, k = +0), `TSB_M12`, `L2A_P03`, `L2B_M00` (8 characters
    at most)."""
    model: str
    """`TS` or `LM2`."""
    transverse: str
    """`axe` or `bord`."""
    x: float
    axles: tuple[Axle, ...]
    wheel_load: float
    """N per wheel."""

    @property
    def pressure(self) -> float:
        a = self.axles[0]
        return self.wheel_load / (4.0 * a.half_x * a.half_y)

    @property
    def total(self) -> float:
        return self.wheel_load * sum(len(a.wheels_y) for a in self.axles)


def ts_wheels(v: ModelValues, transverse: str) -> tuple[float, float]:
    if transverse == "axe":
        return (-v.ts_y_centred, v.ts_y_centred)
    outer = v.lane[1] - v.ts_print / 2.0
    return (outer - v.ts_wheel_spacing, outer)


def lm2_wheels(v: ModelValues, transverse: str) -> tuple[float, float]:
    if transverse == "axe":
        return (-v.ts_y_centred, v.ts_y_centred)
    outer = v.lane[1] - v.lm2_print_y / 2.0
    return (outer - v.lm2_wheel_spacing, outer)


def _label(prefix: str, k: int) -> str:
    return f"{prefix}_{'P' if k >= 0 else 'M'}{abs(k):02d}"


def ts_cases(v: ModelValues, transverse: str) -> tuple[MovingCase, ...]:
    mid = v.length / 2.0
    half = v.ts_print / 2.0
    reach = v.ts_axle_spacing / 2.0 + half
    k_max = int((mid - reach) / v.moving_step + ALIGN)
    wheels = ts_wheels(v, transverse)
    out = []
    for k in range(-k_max, k_max + 1):
        x = round(mid + v.moving_step * k, 9)
        axles = tuple(
            Axle(
                x=round(x + s * v.ts_axle_spacing / 2.0, 9),
                half_x=half,
                wheels_y=wheels,
                half_y=half,
            )
            for s in (-1.0, 1.0)
        )
        out.append(
            MovingCase(
                name=_label("TS" + ("A" if transverse == "axe" else "B"), k),
                model="TS",
                transverse=transverse,
                x=x,
                axles=axles,
                wheel_load=v.ts_wheel,
            )
        )
    return tuple(out)


def lm2_cases(v: ModelValues, transverse: str, cell: float) -> tuple[MovingCase, ...]:
    mid = v.length / 2.0
    half_x = v.lm2_print_x / 2.0
    half_y = v.lm2_print_y / 2.0
    wheels = lm2_wheels(v, transverse)
    prefix = "L2" + ("A" if transverse == "axe" else "B")
    out = []
    for sign, tag in ((-1.0, "M"), (1.0, "P")):
        k = 0
        while True:
            x = round(mid + sign * (cell / 2.0 + v.moving_step * k), 9)
            if x - half_x < -ALIGN or x + half_x > v.length + ALIGN:
                break
            out.append(
                MovingCase(
                    name=f"{prefix}_{tag}{k:02d}",
                    model="LM2",
                    transverse=transverse,
                    x=x,
                    axles=(Axle(x=x, half_x=half_x, wheels_y=wheels, half_y=half_y),),
                    wheel_load=v.lm2_wheel,
                )
            )
            k += 1
    return tuple(sorted(out, key=lambda c: c.x))


def all_cases(v: ModelValues, cell: float) -> tuple[MovingCase, ...]:
    return (
        *ts_cases(v, "axe"),
        *ts_cases(v, "bord"),
        *lm2_cases(v, "axe", cell),
        *lm2_cases(v, "bord", cell),
    )


def check_alignment(cases: tuple[MovingCase, ...], size: float) -> list[str]:
    """Print edges that are not mesh lines of size `size` (none is admitted)."""
    bad = []
    for case in cases:
        for axle in case.axles:
            edges = [*axle.bounds_x()]
            for y in axle.wheels_y:
                edges += [y - axle.half_y, y + axle.half_y]
            for e in edges:
                n = round(e / size)
                if abs(n * size - e) > 1e-7:
                    bad.append(f"{case.name} : bord {e} non aligné sur {size}")
    return bad


__all__ = [
    "Axle",
    "MovingCase",
    "all_cases",
    "check_alignment",
    "lm2_cases",
    "lm2_wheels",
    "ts_cases",
    "ts_wheels",
]
