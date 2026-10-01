"""Combinaisons de la décision D17 (point 13) par le tronc commun (lot 41).

Jusqu'au lot 40, les coefficients γ/ψ de D17 étaient écrits dans le code du quai
(`report/combinations.py`) en plus du fichier de données. Ils sont désormais lus du
seul fichier de données, par la déclaration `combinations` de `projet.yaml` et le
moteur générique `aster_expert.combinaisons` : ces tests vérifient que le résultat
est exactement celui du lot 38 (noms, familles, coefficients, ordre)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.combinaisons.enumeration import (
    Combination,
    combine,
    enumerate_combinations,
)
from aster_expert.projet.context import load_project

_ROOT = Path(__file__).resolve().parents[3]
_CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")

# Les 18 combinaisons du lot 38 (data/examples/lot38_combinaisons/combinaisons.csv),
# dans leur ordre.
_LOT38_NAMES = [
    "ELU_FOND_Q1_DOM_Q3_ACC_G_defav",
    "ELU_FOND_Q1_DOM_G_defav",
    "ELU_FOND_Q1_DOM_Q3_ACC_G_favo",
    "ELU_FOND_Q1_DOM_G_favo",
    "ELU_FOND_Q3_DOM_Q1_ACC_G_defav",
    "ELU_FOND_Q3_DOM_G_defav",
    "ELU_FOND_Q3_DOM_Q1_ACC_G_favo",
    "ELU_FOND_Q3_DOM_G_favo",
    "ELU_ACCIDENTELLE",
    "ELS_CARA_Q1_DOM_Q3_ACC",
    "ELS_CARA_Q1_DOM",
    "ELS_CARA_Q3_DOM_Q1_ACC",
    "ELS_CARA_Q3_DOM",
    "ELS_FREQ_Q1_DOM_Q3_ACC",
    "ELS_FREQ_Q1_DOM",
    "ELS_FREQ_Q3_DOM_Q1_ACC",
    "ELS_FREQ_Q3_DOM",
    "ELS_QUASI_PERMANENTE",
]


def _combinations() -> list[Combination]:
    ctx = load_project("quai_cw_test_01", _ROOT)
    assert ctx.declaration.combinations is not None
    return enumerate_combinations(ctx.declaration.combinations, ctx.number)


def test_the_eighteen_combinations_of_lot_38_in_their_order() -> None:
    combinations = _combinations()
    assert [c.name for c in combinations] == _LOT38_NAMES
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
    for combination in _combinations():
        assert set(combination.coefficients) <= set(_CASES)
        assert combination.coefficients


def test_elu_fondamentale_q3_dominant_defavorable_matches_d17_text() -> None:
    combination = next(
        c for c in _combinations() if c.name == "ELU_FOND_Q3_DOM_G_defav"
    )
    assert combination.coefficients == {"G": 1.35, "EAU_P": 1.35, "Q3": 1.5}


def test_accompanying_action_is_gamma_q_psi0_in_the_same_order() -> None:
    combination = next(
        c for c in _combinations() if c.name == "ELU_FOND_Q1_DOM_Q3_ACC_G_defav"
    )
    assert list(combination.coefficients) == ["G", "EAU_P", "Q1", "Q3"]
    assert combination.coefficients["Q3"] == 1.5 * 0.7


def test_elu_accidentelle_matches_d17_text() -> None:
    combination = next(c for c in _combinations() if c.name == "ELU_ACCIDENTELLE")
    assert combination.coefficients == {"G": 1.0, "EAU_A": 1.0, "A": 1.0, "Q1": 0.5}


def test_els_frequente_accompanying_carries_psi0_as_d17_says() -> None:
    combination = next(c for c in _combinations() if c.name == "ELS_FREQ_Q1_DOM_Q3_ACC")
    assert combination.coefficients == {"G": 1.0, "EAU_P": 1.0, "Q1": 0.5, "Q3": 0.7}


def test_els_quasi_permanente_matches_d17_text() -> None:
    combination = next(c for c in _combinations() if c.name == "ELS_QUASI_PERMANENTE")
    assert combination.coefficients == {
        "G": 1.0,
        "EAU_P": 1.0,
        "Q1": pytest.approx(0.3),
        "Q3": pytest.approx(0.0),
    }


def test_the_coefficients_come_from_the_data_file(tmp_path: Path) -> None:
    """Changer γQ dans les données change les combinaisons : aucune valeur n'est
    tenue par le code."""
    source = (
        _ROOT / "projets" / "quai_cw_test_01" / "donnees" / "combiwall_model_data.yaml"
    )
    original = source.read_text(encoding="utf-8")
    text = original.replace(
        "gamma_q:\n      {status: fourni, value: 1.50,",
        "gamma_q:\n      {status: fourni, value: 1.40,",
    )
    assert text != original
    data = tmp_path / "donnees.yaml"
    data.write_text(text, encoding="utf-8")
    ctx = load_project("quai_cw_test_01", _ROOT, data=data)
    assert ctx.declaration.combinations is not None
    combos = enumerate_combinations(ctx.declaration.combinations, ctx.number)
    target = next(c for c in combos if c.name == "ELU_FOND_Q3_DOM_G_defav")
    assert target.coefficients["Q3"] == 1.40


def test_combine_is_a_plain_linear_combination() -> None:
    values = {"G": 10.0, "Q1": 2.0, "Q3": 3.0}
    assert combine({"G": 1.35, "Q1": 1.5}, values) == pytest.approx(
        1.35 * 10.0 + 1.5 * 2.0
    )
