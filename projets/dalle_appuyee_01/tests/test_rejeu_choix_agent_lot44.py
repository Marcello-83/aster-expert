"""Rejeu de la catégorie `choix_agent` sur la fiche de la phase 1 du lot 43 (lot 44)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.connaissances.base import load_knowledge

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _ROOT / "projets" / "dalle_appuyee_01" / "scripts"


def _load(name: str) -> ModuleType:
    sys.path.insert(0, str(_SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rejeu() -> ModuleType:
    return _load("rejeu_choix_agent_lot44")


def test_blocker_counts_before_and_after(rejeu: ModuleType) -> None:
    summary = rejeu.counts()
    assert summary["bloqueurs_avant"] == 31
    assert summary["bloqueurs_apres"] == 19
    assert len(summary["bloqueurs_leves"]) == 13
    assert summary["bloqueurs_nouveaux"] == [
        "entrée pratique non tranchée (point 6) : Condition d'appui physique des "
        "bords : bilatérale ou unilatérale"
    ]
    assert summary["ecarts_donnees"] == []


def test_versioned_outputs_are_reproduced(rejeu: ModuleType) -> None:
    sheet = rejeu.replay_sheet(rejeu.build_sheet())
    text = json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2)
    assert rejeu.FICHE.read_text(encoding="utf-8") == text + "\n"
    summary = json.dumps(rejeu.counts(), ensure_ascii=False, indent=2) + "\n"
    assert rejeu.SUMMARY.read_text(encoding="utf-8") == summary


def test_what_commits_the_structure_stays_with_mm(rejeu: ModuleType) -> None:
    sheet: HypothesesSheet = rejeu.replay_sheet(rejeu.build_sheet())
    open_points = {
        e.point_label
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    }
    # Périmètre, plaque, charges, béton, appui physique, combinaisons, ferraillage.
    assert open_points == {"0", "1", "4", "5", "6", "13", "14"}
    assert {e.point_label for e in sheet.agent_choices()} == {"6", "9", "10"}


def test_every_named_verifier_exists_in_the_base(rejeu: ModuleType) -> None:
    sheet: HypothesesSheet = rejeu.replay_sheet(rejeu.build_sheet())
    known = set(load_knowledge(_ROOT).entries)
    named = {v for e in sheet.agent_choices() for s in e.sources for v in s.verified_by}
    named |= {v for g in sheet.agent_group_names() for v in g.verified_by}
    assert named
    assert named <= known
