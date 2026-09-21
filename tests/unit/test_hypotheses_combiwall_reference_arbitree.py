"""M5/P1-P4/R1-R2 confronted a second time: MM's v2 arbitration, recorded
for real (lot 18).

`data/examples/hypotheses_combiwall_reference_arbitree.json` is
`hypotheses_combiwall_reference.json` (unchanged, kept as the unarbitrated
version) with the nine decisions of
`/media/sf_partage/echanges/arbitrage_combiwall_MM_v2.md` folded in through
`aster_expert.agent.arbitration.record_practice_decision`/`apply_decision`/
`insert_practice_entry` -- never hand-built, so this test also exercises
those three functions against a real, full-size fiche rather than the
hand-built fixtures of `tests/unit/test_agent_arbitration.py`.
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

_ARBITREE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "examples"
    / "hypotheses_combiwall_reference_arbitree.json"
)


def _load() -> HypothesesSheet:
    return HypothesesSheet.model_validate_json(
        _ARBITREE_PATH.read_text(encoding="utf-8")
    )


def test_arbitree_fiche_json_is_valid_json_before_schema_validation() -> None:
    json.loads(_ARBITREE_PATH.read_text(encoding="utf-8"))


def test_arbitree_fiche_round_trips_through_the_schema() -> None:
    sheet = _load()

    assert (
        len(sheet.entries) == 25
    )  # 24 du spécimen + décision 0 (R2, insert_practice_entry)


def test_arbitree_fiche_has_nine_decided_practice_entries() -> None:
    sheet = _load()

    tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "tranche"
    ]
    assert len(tranche_practice) == 9
    assert {e.point_label for e in tranche_practice} == {
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
    }
    assert all(e.decided_by == "MM" for e in tranche_practice)
    assert all(e.validity_domain for e in tranche_practice)
    assert all(e.discarded_variants for e in tranche_practice)


def test_arbitree_fiche_has_no_remaining_non_tranche_practice_entry() -> None:
    """Every `pratique` entry the original spécimen carried is now decided --
    the nine decisions cover all eight pre-existing `non_tranche` points
    plus the new "Objet et périmètre du calcul" (décision 0)."""
    sheet = _load()

    non_tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    ]
    assert non_tranche_practice == []


def test_arbitree_fiche_is_still_not_ready_for_generation() -> None:
    """Two blockers remain, neither addressed by this lot's arbitration:
    the pre-existing `code_aster`/`non_tranche` entry (point 1, tableau
    comparatif DKT/DST/Q4G/DKTG/Q4GG, unchanged since lot 14) and the empty
    `group_naming` section (R3, lot 17) -- naming convention arbitration is
    explicitly out of scope for this lot."""
    sheet = _load()

    assert sheet.is_ready_for_generation is False
    blockers = sheet.generation_blockers()
    assert len(blockers) == 2
    assert any("group_naming" in b for b in blockers)
    assert any("tableau comparatif" in b for b in blockers)


def test_arbitree_fiche_never_attaches_a_documentary_source_to_a_practice_entry() -> (
    None
):
    """M2, confirmed again on the arbitrated fiche."""
    sheet = _load()

    for entry in sheet.entries:
        if isinstance(entry, PracticeHypothesisEntry):
            for source in entry.sources:
                assert not isinstance(source, (DocumentarySource, CatalogueSource))


def test_original_reference_fiche_is_unchanged() -> None:
    """S4: the unarbitrated version stays versioned, untouched by this lot."""
    original_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "examples"
        / "hypotheses_combiwall_reference.json"
    )
    sheet = HypothesesSheet.model_validate_json(
        original_path.read_text(encoding="utf-8")
    )

    assert len(sheet.entries) == 24
    non_tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    ]
    assert len(non_tranche_practice) == 8
