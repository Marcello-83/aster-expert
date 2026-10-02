"""Lot 44 : décision de MM sur Es (200 GPa) dans la fiche courante de la dalle."""

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
        "decisions_lot44", _SCRIPTS / "decisions_lot44.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["decisions_lot44"] = module
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


def test_es_is_200_gpa_and_the_lot_43_decision_is_kept(script: ModuleType) -> None:
    sheet = script.current_sheet()
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.topic == script.ELS_TOPIC
    )
    assert "EYS = 200 000 MPa" in (entry.option_retained or "")
    assert "αe = 15 est maintenu" in (entry.validity_domain or "")
    (prior,) = entry.decision_history
    assert "EYS = 210 000 MPa" in prior.option_retained
    assert script.precedent(sheet).superseded_decisions == 1


def test_recalculation_with_es_is_reported() -> None:
    report = json.loads(
        (
            _ROOT
            / "projets"
            / "dalle_appuyee_01"
            / "references"
            / "recalcul_es_lot44.json"
        ).read_text(encoding="utf-8")
    )
    qp = report["densites_max_m2_par_m"]["ELS_QUASI_PERMANENTE"]
    assert qp["DNSXI"]["ecart"] == "+6,61 %"
    assert "inchangé" in report["ferraillage_retenu"]
