"""`aster_expert.rebar.ultimate` against the official cas test `ssll13d.comm`
(`CALC_FERRAILLAGE`, `POU_D_T`, `CODIFICATION='EC2'`, `TYPE_DIAGRAMME='B2'`,
`FCK=35 MPa`, `FYK=500 MPa`, `GAMMA_S=1.15`, `GAMMA_C=1.5`, section 0,5 m x 0,3 m,
enrobage 0,04 m -- read via `read_test_case`, `external/codeaster-src/astest`,
commit `50ebc13c70ee9df62faf93ddcb746a3757b3042a`). `VALE_CALC`/`VALE_REFE` of
that cas test are themselves compared to `REFERENCE="ANALYTIQUE"`, so this is an
independent-module-vs-independent-module check, not merely a self-consistency
one; the absolute tolerance (1e-6 m^2) matches the cas test's own
`ORDRE_GRANDEUR`/`PRECISION`."""

from __future__ import annotations

import pytest

from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.ultimate import design_ultimate

_CONCRETE = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
_STEEL = Steel(fyk=500.0, gamma_s=1.15, es=210000.0)
_COVER = 0.04


def _section(depth: float, width: float) -> Rectangle:
    return Rectangle(width=width, depth=depth, cover_pos=_COVER, cover_neg=_COVER)


@pytest.mark.parametrize(
    ("depth", "width", "n", "m", "as_pos", "as_neg"),
    [
        # CHEFF4: N=0, MFZ=+1e5 N -> pivot A, positive face only.
        (0.5, 0.3, 0.0, 0.1, 5.18123984855709e-04, 0.0),
        # CHEFF5: N=0, MFY=-1e5 -> mirrored axis, negative face only.
        (0.3, 0.5, 0.0, -0.1, 0.0, 9.49184236626372e-04),
        # CHEFF8: N=2e6 (tension), MFZ=-1e5 -> both faces reinforced.
        (0.5, 0.3, 2.0, -0.1, 1.75238095238095e-03, 2.84761904761905e-03),
        # CHEFF12: pivot B, pure moment.
        (0.5, 0.3, 0.0, -0.26, 0.0, 1.43999329534403e-03),
        # CHEFF13: pivot B, larger moment.
        (0.5, 0.3, 0.0, -0.38, 0.0, 2.23821169164216e-03),
    ],
)
def test_design_ultimate_matches_ssll13d(
    depth: float, width: float, n: float, m: float, as_pos: float, as_neg: float
) -> None:
    result = design_ultimate(_section(depth, width), _CONCRETE, _STEEL, n, m)
    assert result.feasible
    assert result.as_pos == pytest.approx(as_pos, abs=1e-6)
    assert result.as_neg == pytest.approx(as_neg, abs=1e-6)


def test_design_ultimate_mirrors_negative_moment() -> None:
    positive = design_ultimate(_section(0.5, 0.3), _CONCRETE, _STEEL, 0.0, 0.1)
    negative = design_ultimate(_section(0.5, 0.3), _CONCRETE, _STEEL, 0.0, -0.1)
    assert negative.as_pos == pytest.approx(positive.as_neg, abs=1e-9)
    assert negative.as_neg == pytest.approx(positive.as_pos, abs=1e-9)
