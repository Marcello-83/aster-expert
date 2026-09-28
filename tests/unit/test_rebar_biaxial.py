"""`aster_expert.rebar.biaxial` against the lot 39 executed essai `limites`
(`data/examples/lot39_essais/limites/`, `CALC_FERRAILLAGE`, ELU, section
2,50 x 1,40 m, bar axis at 0,10 m, C35/45, B500B; listing
`data/examples/lot39_essais/rapports/mess_limites_extrait.txt`)."""

from __future__ import annotations

import pytest

from aster_expert.rebar.biaxial import (
    bresler_exponent,
    design_biaxial,
    resisting_moment,
)
from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.ultimate import design_ultimate

_C = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
_S = Steel(fyk=500.0, gamma_s=1.15)


@pytest.mark.parametrize(
    ("moment", "ays", "azs"),
    [
        # devie_1: MFY = MFZ = 1 MN.m (instant 5 of `limites`).
        (1.0, 2.059760660639e-03, 3.811935915531e-03),
        # devie_3: MFY = MFZ = 3 MN.m (instant 8).
        (3.0, 6.212746719987e-03, 1.155610237267e-02),
    ],
)
def test_biaxial_matches_code_aster(moment: float, ays: float, azs: float) -> None:
    result = design_biaxial(2.50, 1.40, 0.10, _C, _S, 0.0, moment, moment)
    assert result.feasible
    assert result.iterations == 8
    assert result.ays == pytest.approx(ays, rel=1e-6)
    assert result.azs == pytest.approx(azs, rel=1e-6)
    assert result.ayi == pytest.approx(0.0, abs=1e-12)
    assert result.azi == pytest.approx(0.0, abs=1e-12)
    assert result.bresler is not None and result.bresler <= 1.0


def test_single_direction_is_the_uniaxial_design() -> None:
    # mfz_1 (instant 1): AYS = 9,608935496537e-04, no Bresler iteration.
    result = design_biaxial(2.50, 1.40, 0.10, _C, _S, 0.0, 0.0, 1.0)
    assert result.iterations == 0
    assert result.ays == pytest.approx(9.608935496537e-04, rel=1e-6)
    # mfy_m1 (instant 4): AZI = 1,778296237482e-03.
    result = design_biaxial(2.50, 1.40, 0.10, _C, _S, 0.0, -1.0, 0.0)
    assert result.azi == pytest.approx(1.778296237482e-03, rel=1e-6)
    assert result.azs == pytest.approx(0.0, abs=1e-12)


def test_resisting_moment_of_a_designed_section_is_the_design_moment() -> None:
    section = Rectangle(width=1.40, depth=2.50, cover_pos=0.10, cover_neg=0.10)
    design = design_ultimate(section, _C, _S, 0.0, 1.0)
    capacity = resisting_moment(section, _C, _S, design.as_pos, design.as_neg, 0.0)
    assert capacity == pytest.approx(1.0, rel=1e-9)


def test_bresler_exponent_table() -> None:
    # R7.04.05 / EN 1992-1-1 5.8.9(4): a = 1 (N/NR <= 0,1), 1,5 (0,7), 2 (1,0).
    assert bresler_exponent(0.0) == 1.0
    assert bresler_exponent(0.1) == 1.0
    assert bresler_exponent(0.7) == pytest.approx(1.5)
    assert bresler_exponent(1.0) == pytest.approx(2.0)
    assert bresler_exponent(0.4) == pytest.approx(1.25)
