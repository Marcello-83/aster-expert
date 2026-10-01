"""Fiche proposée de la dalle (lot 43) : rejouable à l'octet, aucune décision
pratique prise par la session, citations retrouvées dans le corpus."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    FindingReference,
    HypothesesSheet,
    PracticeHypothesisEntry,
)

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "projets" / "dalle_appuyee_01" / "scripts" / "build_fiche_lot43.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_fiche_lot43", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_fiche_lot43"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build() -> ModuleType:
    return _load()


def test_versioned_fiche_is_reproduced_byte_for_byte(build: ModuleType) -> None:
    sheet = build.build_sheet()
    text = (
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    )
    assert build.FICHE.read_text(encoding="utf-8") == text


def test_versioned_document_is_reproduced(build: ModuleType) -> None:
    assert build.DOCUMENT.read_text(encoding="utf-8") == build.render(
        build.build_sheet()
    )


def test_no_practice_decision_is_taken(build: ModuleType) -> None:
    sheet: HypothesesSheet = build.build_sheet()
    practice = [e for e in sheet.entries if isinstance(e, PracticeHypothesisEntry)]
    assert practice
    assert all(e.status == "non_tranche" for e in practice)
    assert all(e.option_retained is None and not e.sources for e in practice)
    assert all(g.status == "non_tranche" for g in sheet.group_naming)
    assert not sheet.is_ready_for_generation


def test_both_halves_are_present(build: ModuleType) -> None:
    sheet: HypothesesSheet = build.build_sheet()
    founded = [e for e in sheet.entries if isinstance(e, CodeAsterHypothesisEntry)]
    refs = [e for e in sheet.entries if isinstance(e, FindingReference)]
    assert all(e.status == "tranche" for e in founded)
    assert len(founded) + len(refs) >= len(sheet.unresolved_entries())


def test_precedents_are_proposed_with_their_text(build: ModuleType) -> None:
    sheet: HypothesesSheet = build.build_sheet()
    by_point = {
        e.point_label: e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
    }
    for point, precedent in (
        ("9", "PRE-012"),
        ("10", "PRE-013"),
        ("13", "PRE-016"),
        ("14", "PRE-018"),
    ):
        entry = by_point[point]
        assert any(
            o.startswith(f"Précédent {precedent}") for o in entry.options_considered
        )
        assert f"Précédent proposé, non appliqué : {precedent}" in (entry.notes or "")


def test_referenced_findings_exist_in_the_base(build: ModuleType) -> None:
    from aster_expert.constats.base import base_dir, load_base, resolve_sheet

    resolved = resolve_sheet(build.build_sheet(), load_base(base_dir(_ROOT)))
    assert not resolved.finding_references()


def test_excerpts_are_verbatim_in_the_corpus(build: ModuleType) -> None:
    if not build.CORPUS.is_dir():
        pytest.skip(f"corpus documentaire absent : {build.CORPUS}")
    assert build.check_excerpts() == []
