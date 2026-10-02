"""Lot 45 : D21 s'applique à la dalle (mention corrigée dans la fiche et PRE-030)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from aster_expert.agent.hypotheses import PracticeHypothesisEntry
from aster_expert.connaissances.base import dump_entry, entry_path, read_entry

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _ROOT / "projets" / "dalle_appuyee_01" / "scripts"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    sys.path.insert(0, str(_SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "decisions_lot45", _SCRIPTS / "decisions_lot45.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["decisions_lot45"] = module
    spec.loader.exec_module(module)
    return module


def test_current_fiche_and_precedent_are_reproduced(script: ModuleType) -> None:
    sheet = script.current_sheet()
    text = json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2)
    assert script.FICHE.read_text(encoding="utf-8") == text + "\n"
    assert script.DOCUMENT.read_text(encoding="utf-8") == script.lot43.render(sheet)
    precedent = script.precedent(sheet)
    versioned = read_entry(entry_path(_ROOT, precedent), precedent.layer)
    assert dump_entry(versioned) == dump_entry(precedent)


def test_p6_applies_d21_and_keeps_the_lot_43_decision(script: ModuleType) -> None:
    sheet = script.current_sheet()
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.topic == script.P6_TOPIC
    )
    assert "application de D21 (PRE-020," in (entry.justification or "")
    assert "kc = 0,4" in (entry.option_retained or "")
    assert not any(
        "Act = zone tendue" in v.description for v in entry.discarded_variants
    )
    (prior,) = entry.decision_history
    assert "MM écarte « PRE-021" in (prior.justification or "")
    # La mention fausse ne subsiste que dans l'historique de la décision.
    assert "écarte « PRE-021" not in (entry.justification or "")
