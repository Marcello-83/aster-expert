"""Geometry of PONTONS-ALU-01, lot 54: the final PRO geometry of the whole pontoon, from
the parameters of `maillage/maillage_ponton_52.py` (the script of lot 52, whose
parameters X_MONTANTS, B_CHEVETRE and Y_CHEVETRE a variant may change from lot 54 on).

The deck and the frame are those of lot 52 (`geometrie_lot52.geometry_from`):

- P67: inner posts of a long span at Xd + k × 1,25 (k = 1 to 4), five equal panels; the
  diagonals keep the N pattern of lot 52, all identical and parallel in the long spans;
  the purlins are cut at the new crossings; cleats unchanged (Xd + 1,6 and Xd + 4,6);
- P68: cap beams 0,60 (along X) × 0,40, from Y = −1,20 to +1,20; the ties (0,40 × 0,40)
  are cut at the face of the cap beams (ring corners, ANGLES_ANNEAU), the links of the
  ring (LG_, TP_) and the pins unchanged.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from pontons_alu_01.geometrie_lot51ter import Geometry51ter, read_parameters
from pontons_alu_01.geometrie_lot52 import OVERRIDABLE as OVERRIDABLE_52
from pontons_alu_01.geometrie_lot52 import SCRIPT, geometry_from, params_json

OVERRIDABLE = (*OVERRIDABLE_52, "X_MONTANTS", "B_CHEVETRE", "Y_CHEVETRE")


def geometry(overrides: Mapping[str, Any] | None = None) -> Geometry51ter:
    return geometry_from(read_parameters(SCRIPT, overrides, OVERRIDABLE))


def diagonal_lengths(g: Geometry51ter) -> dict[str, float]:
    """Length (m) of every diagonal of the long spans, end to end (P67: all equal)."""
    long_spans = {s.name for s in g.spans if s.nature == "grande"}
    return {
        m.name: math.dist(m.points[0], m.points[-1])
        for m in g.family("DIAGONALES")
        if m.span in long_spans
    }


__all__ = ["OVERRIDABLE", "SCRIPT", "diagonal_lengths", "geometry", "params_json"]
