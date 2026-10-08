"""Combinations and envelopes of result arrays (lot 49), in plain numpy.

This module imports nothing but numpy and the standard library: it is copied next to
`scripts/livrables_med.py` and runs inside the Code_Aster container (whose Python has
numpy and `medcoupling`), and it is tested in the project's environment.

Arrays are the raw arrays of one field (rows: entities or entity-nodes, columns:
components), all of the same shape for every case of a field.

- `combine(arrays, fixed)`: Σ coefficient × array, in the order of `fixed` (the order
  of the floating-point sum is the order of the combination's coefficients);
- `with_moving(base, arrays, coefficient, positions)`: max and min of
  `base + coefficient × array[p]` over the positions `p`, with the index of the
  position that gives each (first one on a tie, as `numpy.argmax`);
- `envelope(maxima, minima, max_positions, min_positions)`: max and min over the
  combinations, with the index of the governing combination and of its position (−1
  when the governing combination has no moving load).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def combine(arrays: Mapping[str, FloatArray], fixed: Mapping[str, float]) -> FloatArray:
    """Σ coefficient × array of the fixed cases."""
    if not fixed:
        message = "combinaison sans cas"
        raise ValueError(message)
    out: FloatArray | None = None
    for case, coefficient in fixed.items():
        term = coefficient * arrays[case]
        out = term if out is None else out + term
    assert out is not None
    return out


@dataclass(frozen=True)
class Enveloped:
    maximum: FloatArray
    minimum: FloatArray
    arg_max: IntArray
    """Index (in `positions`) of the position of the max; −1 without positions."""
    arg_min: IntArray


def with_moving(
    base: FloatArray,
    arrays: Mapping[str, FloatArray],
    coefficient: float,
    positions: Sequence[str],
) -> Enveloped:
    """Max and min of `base + coefficient × arrays[p]` over `positions`."""
    if not positions:
        none = np.full(base.shape, -1, dtype=np.int64)
        return Enveloped(base, base, none, none.copy())
    maximum = np.full(base.shape, -np.inf)
    minimum = np.full(base.shape, np.inf)
    arg_max = np.full(base.shape, -1, dtype=np.int64)
    arg_min = np.full(base.shape, -1, dtype=np.int64)
    for index, name in enumerate(positions):
        value = base + coefficient * arrays[name]
        higher = value > maximum
        lower = value < minimum
        maximum = np.where(higher, value, maximum)
        minimum = np.where(lower, value, minimum)
        arg_max = np.where(higher, index, arg_max)
        arg_min = np.where(lower, index, arg_min)
    return Enveloped(maximum, minimum, arg_max, arg_min)


@dataclass(frozen=True)
class Envelope:
    maximum: FloatArray
    minimum: FloatArray
    max_combination: IntArray
    min_combination: IntArray
    max_position: IntArray
    """Index of the position in the governing combination's own list, −1 if none."""
    min_position: IntArray


def envelope(items: Sequence[Enveloped]) -> Envelope:
    """Max and min over combinations (first one on a tie)."""
    if not items:
        message = "enveloppe sans combinaison"
        raise ValueError(message)
    shape = items[0].maximum.shape
    maximum = np.full(shape, -np.inf)
    minimum = np.full(shape, np.inf)
    max_c = np.full(shape, -1, dtype=np.int64)
    min_c = np.full(shape, -1, dtype=np.int64)
    max_p = np.full(shape, -1, dtype=np.int64)
    min_p = np.full(shape, -1, dtype=np.int64)
    for index, item in enumerate(items):
        higher = item.maximum > maximum
        lower = item.minimum < minimum
        maximum = np.where(higher, item.maximum, maximum)
        minimum = np.where(lower, item.minimum, minimum)
        max_c = np.where(higher, index, max_c)
        min_c = np.where(lower, index, min_c)
        max_p = np.where(higher, item.arg_max, max_p)
        min_p = np.where(lower, item.arg_min, min_p)
    return Envelope(maximum, minimum, max_c, min_c, max_p, min_p)


def resultant(coords: FloatArray, forces: FloatArray) -> dict[str, float]:
    """Σ F and Σ (x × F) about the origin of nodal forces (n × 3, or n × 6 with
    moments in the last three columns), and the point where the vertical resultant
    applies (x̄, ȳ = moment / force, when the vertical force is not zero)."""
    f = forces[:, :3]
    moment = np.cross(coords, f).sum(axis=0)
    if forces.shape[1] >= 6:
        moment = moment + forces[:, 3:6].sum(axis=0)
    total = f.sum(axis=0)
    out = {
        "FX": float(total[0]),
        "FY": float(total[1]),
        "FZ": float(total[2]),
        "MX": float(moment[0]),
        "MY": float(moment[1]),
        "MZ": float(moment[2]),
    }
    if total[2] != 0.0:
        out["X_APPLICATION_FZ"] = float(-moment[1] / total[2])
        out["Y_APPLICATION_FZ"] = float(moment[0] / total[2])
    return out


__all__ = [
    "Envelope",
    "Enveloped",
    "combine",
    "envelope",
    "resultant",
    "with_moving",
]
