"""Lot 45 : `FERR_MIN` n'est demandé qu'avec `UNITE_CONTRAINTE='MPa'` (CA-041)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.ferraillage.unites import (
    FERR_MIN_UNIT,
    check_ferr_min_unit,
    ferr_min_unit_violations,
)
from aster_expert.projet.errors import ProjectError

_ROOT = Path(__file__).resolve().parents[2]
_CASES = _ROOT / "data" / "examples" / "lot39_essais"


def _call(unit: str | None, extra: str = "") -> str:
    unit_line = f'    UNITE_CONTRAINTE="{unit}",\n' if unit else ""
    return (
        'RESU = CALC_FERRAILLAGE(\n    RESULTAT=RESU,\n    CODIFICATION="EC2",\n'
        f'{unit_line}    AFFE=(_F(TOUT="OUI", FYK=500.0{extra}),),\n)\n'
    )


def test_the_unit_is_mpa() -> None:
    assert FERR_MIN_UNIT == "MPa"


def test_the_versioned_case_in_pa_is_refused_and_the_one_in_mpa_accepted() -> None:
    pa = (_CASES / "fermin" / "fermin.comm").read_text(encoding="utf-8")
    mpa = (_CASES / "fermin_mpa" / "fermin_mpa.comm").read_text(encoding="utf-8")

    problems = ferr_min_unit_violations(pa)

    assert len(problems) == 1
    assert "FERR_MIN avec UNITE_CONTRAINTE='Pa'" in problems[0]
    assert "CA-041" in problems[0]
    with pytest.raises(ProjectError, match="FERR_MIN n'est juste qu'en 'MPa'"):
        check_ferr_min_unit(pa)
    assert ferr_min_unit_violations(mpa) == []
    check_ferr_min_unit(mpa)


def test_a_call_without_ferr_min_is_free_in_either_unit() -> None:
    assert ferr_min_unit_violations(_call("Pa")) == []
    assert ferr_min_unit_violations(_call("MPa")) == []
    assert ferr_min_unit_violations(_call("Pa", ', FERR_MIN_FISS="EC2"')) == []


def test_ferr_min_without_a_unit_or_in_pa_is_refused() -> None:
    assert len(ferr_min_unit_violations(_call("Pa", ', FERR_MIN="EC2"'))) == 1
    assert "None" in ferr_min_unit_violations(_call(None, ', FERR_MIN="EC2"'))[0]
    assert ferr_min_unit_violations(_call("MPa", ', FERR_MIN="EC2"')) == []


def test_each_call_is_judged_on_its_own_unit() -> None:
    text = _call("MPa", ', FERR_MIN="EC2"') + _call("Pa", ', FERR_MIN="EC2"')

    problems = ferr_min_unit_violations(text)

    assert len(problems) == 1
    assert problems[0].startswith("ligne 7")


def test_an_unreadable_text_is_refused_rather_than_passed() -> None:
    with pytest.raises(ProjectError, match="non contrôlé"):
        ferr_min_unit_violations("CALC_FERRAILLAGE(")
