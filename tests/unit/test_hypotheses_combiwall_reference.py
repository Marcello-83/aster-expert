"""M5: confront `HypothesesSheet` against a real, versioned specimen.

`data/examples/hypotheses_combiwall_reference.json` is the real combi-wall
fiche produced during a genuine usage trial, transcribed into this schema
(see `data/examples/README.md` for provenance and transcription discipline).
This is the one test in the suite that is not hand-built fixture data: it
is the actual confrontation the lot instructions require ("un schéma qui
n'a pas été confronté à un cas réel n'est pas validé").
"""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    DocumentarySource,
    HypothesesSheet,
    PracticeHypothesisEntry,
)

_REFERENCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "examples"
    / "hypotheses_combiwall_reference.json"
)


def _load() -> HypothesesSheet:
    return HypothesesSheet.model_validate_json(
        _REFERENCE_PATH.read_text(encoding="utf-8")
    )


def test_reference_fiche_round_trips_through_the_schema() -> None:
    sheet = _load()

    assert sheet.entries
    assert len(sheet.entries) == 24


def test_reference_fiche_matches_its_own_bilan_2_unresolved_count() -> None:
    """The specimen's own "Bilan 2" names 5 non-founded points; point 1
    split into 2 distinct practice questions at transcription (family
    choice, homogenization) -- 6 practice points, 8 entries once split."""
    sheet = _load()

    practice_unresolved = [
        e for e in sheet.unresolved_entries() if isinstance(e, PracticeHypothesisEntry)
    ]
    assert len(practice_unresolved) == 8
    assert {e.point_label for e in practice_unresolved} == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
    }


def test_reference_fiche_has_one_partially_read_code_aster_entry() -> None:
    """The U2.02.01 comparison-table case: section identified, content
    never read -- a code_aster-nature entry that stayed non_tranche despite
    carrying a source (lot 8c/14's own worked example)."""
    sheet = _load()

    non_tranche_code_aster = [
        e
        for e in sheet.entries
        if e.nature == "code_aster" and e.status == "non_tranche"
    ]
    assert len(non_tranche_code_aster) == 1
    entry = non_tranche_code_aster[0]
    assert entry.sources
    assert isinstance(entry.sources[0], DocumentarySource)
    assert entry.sources[0].excerpt is None


def test_reference_fiche_is_not_ready_for_generation() -> None:
    """Faithful to the specimen's own conclusion: several points remain open."""
    sheet = _load()

    assert sheet.is_ready_for_generation is False


def test_reference_fiche_never_attaches_a_documentary_source_to_a_practice_entry() -> (
    None
):
    """M2, confirmed on the real transcription, not just on hand-built
    fixtures: every practice entry's sources are practice sources only."""
    sheet = _load()

    for entry in sheet.entries:
        if isinstance(entry, PracticeHypothesisEntry):
            for source in entry.sources:
                assert not isinstance(source, (DocumentarySource, CatalogueSource))


def test_reference_fiche_json_is_valid_json_before_schema_validation() -> None:
    """Sanity check on the file itself, independent of the schema."""
    json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
