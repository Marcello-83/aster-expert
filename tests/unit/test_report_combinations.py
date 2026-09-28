"""`aster_expert.report.combinations` (lot 38, décision D17, point 13)."""

from __future__ import annotations

import pytest

from aster_expert.report.combinations import (
    CASES,
    combine,
    enumerate_combinations,
)


def test_enumerate_combinations_has_eighteen_entries() -> None:
    combinations = enumerate_combinations()
    assert len(combinations) == 18
    assert len({c.name for c in combinations}) == 18  # no duplicate name
    by_family: dict[str, int] = {}
    for c in combinations:
        by_family[c.family] = by_family.get(c.family, 0) + 1
    assert by_family == {
        "ELU fondamentale": 8,
        "ELU accidentelle": 1,
        "ELS caractéristique": 4,
        "ELS fréquente": 4,
        "ELS quasi permanente": 1,
    }


def test_every_coefficient_names_a_known_case() -> None:
    for combination in enumerate_combinations():
        assert set(combination.coefficients) <= set(CASES)
        assert combination.coefficients  # never empty


def test_elu_fondamentale_q3_dominant_defavorable_matches_d17_text() -> None:
    combination = next(
        c for c in enumerate_combinations() if c.name == "ELU_FOND_Q3_DOM_G_defav"
    )
    assert combination.coefficients == {"G": 1.35, "EAU_P": 1.35, "Q3": 1.5}


def test_elu_accidentelle_matches_d17_text() -> None:
    combination = next(
        c for c in enumerate_combinations() if c.name == "ELU_ACCIDENTELLE"
    )
    assert combination.coefficients == {"G": 1.0, "EAU_A": 1.0, "A": 1.0, "Q1": 0.5}


def test_els_quasi_permanente_matches_d17_text() -> None:
    combination = next(
        c for c in enumerate_combinations() if c.name == "ELS_QUASI_PERMANENTE"
    )
    assert combination.coefficients == {
        "G": 1.0,
        "EAU_P": 1.0,
        "Q1": pytest.approx(0.3),
        "Q3": pytest.approx(0.0),
    }


def test_combine_is_a_plain_linear_combination() -> None:
    values = {"G": 10.0, "Q1": 2.0, "Q3": 3.0}
    assert combine({"G": 1.35, "Q1": 1.5}, values) == pytest.approx(
        1.35 * 10.0 + 1.5 * 2.0
    )
