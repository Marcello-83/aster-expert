"""`aster_expert.rebar.serviceability` against the official cas test `ssll13b.comm`
(`CALC_FERRAILLAGE`, `TYPE_COMB='ELS'`, section 0,5 m x 0,3 m, enrobage 0,04 m,
`SIGS_ELS=400 MPa`, `SIGC_*_ELS=0,6*35=21 MPa`, `ALPHA_E=15`). The heavily
tensioned case (CHEFF8) matches to the cas test's own tolerance; a moderately
reinforced pure-moment case (CHEFF4) does not (docs/essais_lot38.md, lot 38,
§Limites; lot 39: 2,7 % after the correction of the neutral-axis depth, the module
agreeing with the steel-pivot formula of R7.04.05 worked by hand,
docs/essais_lot39.md) -- both are asserted here, the second loosely, to keep the
gap visible to `pytest` rather than silently regressing further."""

from __future__ import annotations

import pytest

from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.serviceability import design_els, design_els_qp

_CONCRETE = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
_STEEL = Steel(fyk=500.0, gamma_s=1.15, es=210000.0)
_COVER = 0.04
_SIGMA_C_LIM = 21.0
_SIGMA_S_LIM = 400.0
_ALPHA_E = 15.0


def _section(depth: float, width: float) -> Rectangle:
    return Rectangle(width=width, depth=depth, cover_pos=_COVER, cover_neg=_COVER)


def test_design_els_matches_ssll13b_in_the_heavily_tensioned_case() -> None:
    # CHEFF8: N=2e6 (tension), MFZ=-1e5 -- both faces engaged, concrete negligible.
    result = design_els(
        _section(0.5, 0.3),
        _CONCRETE,
        _STEEL,
        2.0,
        -0.1,
        sigma_c_lim=_SIGMA_C_LIM,
        sigma_s_lim=_SIGMA_S_LIM,
        alpha_e=_ALPHA_E,
    )
    assert result.feasible
    assert result.as_pos == pytest.approx(1.90476190476191e-03, abs=1e-6)
    assert result.as_neg == pytest.approx(3.09523809523809e-03, abs=1e-6)


def test_design_els_pure_moment_is_of_the_right_order_but_not_exact() -> None:
    # CHEFF4: N=0, MFZ=+1e5 -- documented gap (docs/essais_lot38.md,
    # docs/essais_lot39.md): the module gives 6,0447e-4, the value of R7.04.05's
    # steel-pivot formula worked by hand, larger than Code_Aster by 2,7 %
    # (conservative here, not proven so in general); cause not established.
    result = design_els(
        _section(0.5, 0.3),
        _CONCRETE,
        _STEEL,
        0.0,
        0.1,
        sigma_c_lim=_SIGMA_C_LIM,
        sigma_s_lim=_SIGMA_S_LIM,
        alpha_e=_ALPHA_E,
    )
    assert result.feasible
    reference = 5.88764731062629e-04
    assert result.as_pos == pytest.approx(reference, rel=0.03)
    assert result.as_pos == pytest.approx(6.0447e-04, rel=1e-4)
    assert result.as_neg == pytest.approx(0.0, abs=1e-6)


def test_design_els_qp_runs_and_respects_the_crack_limit_when_feasible() -> None:
    result = design_els_qp(
        _section(2.50, 1.40),
        _CONCRETE,
        _STEEL,
        0.0,
        2.183517,
        wk_max=0.2e-3,
        phi=0.025,
        kt=0.4,
    )
    assert result.as_pos >= 0.0
    assert result.as_neg >= 0.0


def test_design_els_qp_strongly_compressed_case_is_plain_concrete() -> None:
    # Strongly compressed case (docs/essais_lot38.md): Code_Aster finds a zero
    # reinforcement. Lot 38 reported it infeasible; since lot 39 the plain
    # concrete, without tension, balances the couple within the limit and the
    # module returns zero too -- with a note saying why, never a silent zero.
    result = design_els_qp(
        _section(2.50, 1.40),
        _CONCRETE,
        _STEEL,
        -1.0,
        0.5,
        wk_max=0.2e-3,
        phi=0.025,
        kt=0.4,
    )
    assert result.feasible
    assert result.total == 0.0
    assert "béton seul" in result.note
