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

    # 24 du spécimen + décision 0 (lot 18) + décision 9 (lot 19, R2) + 3 points
    # Code_Aster non fondés (lot 19, record_unfounded_point)
    assert len(sheet.entries) == 29


def test_arbitree_fiche_has_ten_decided_practice_entries() -> None:
    sheet = _load()

    tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "tranche"
    ]
    assert len(tranche_practice) == 10
    assert {e.point_label for e in tranche_practice} == {
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
    }
    assert all(e.decided_by == "MM" for e in tranche_practice)
    assert all(e.validity_domain for e in tranche_practice)
    assert all(e.discarded_variants for e in tranche_practice)


def test_arbitree_fiche_has_exactly_the_three_new_unfounded_practice_points() -> None:
    """Lot 19, step 5: three Code_Aster points revealed by v3, recorded by
    `record_unfounded_point`, never decided."""
    sheet = _load()

    non_tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    ]
    assert len(non_tranche_practice) == 3
    assert all(
        e.notes and e.notes.startswith("Cherché sous") for e in non_tranche_practice
    )


def test_arbitree_fiche_v3_revisions_keep_the_v2_decision_in_history() -> None:
    """Lot 19: points 1, 2, 4, 5, 6, 7 were revised; v2 (2026-09-18) stays in
    `decision_history`, v3 (2026-09-21) is the live decision."""
    sheet = _load()

    revised = {
        e.point_label: e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.status == "tranche"
        and e.decision_history
    }
    assert set(revised) == {"1", "2", "4", "5", "6", "7"}
    for entry in revised.values():
        assert len(entry.decision_history) == 1
        assert entry.decision_history[0].decided_at.date().isoformat() == "2026-09-18"
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-21"


def test_arbitree_fiche_unrevised_decisions_have_no_history() -> None:
    sheet = _load()

    for e in sheet.entries:
        if (
            isinstance(e, PracticeHypothesisEntry)
            and e.status == "tranche"
            and (e.point_label, e.decided_at.date().isoformat() if e.decided_at else "")
            in {("0", "2026-09-18"), ("3", "2026-09-18"), ("8", "2026-09-21")}
        ):
            assert e.decision_history == ()


def test_arbitree_fiche_norme_sources_carry_no_invented_day() -> None:
    """The schema's `date` is a full date; "2009-03" is not representable, so
    the norm sources carry `date=None` and the month stays in `reference`."""
    sheet = _load()

    norme = [
        (e.point_label, s)
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        for s in e.sources
        if s.origin == "norme"
    ]
    assert {pl for pl, _ in norme} == {"2", "4"}
    assert all(s.date is None and "mars 2009" in s.reference for _, s in norme)


def test_arbitree_fiche_group_naming_is_registered() -> None:
    sheet = _load()

    assert len(sheet.group_naming) == 57
    assert all(g.status == "tranche" for g in sheet.group_naming)
    names = {g.group_name for g in sheet.group_naming}
    assert {"BOLLARD", "DEFENSE", "TUBE_05", "SYM_G", "ANC_09"} <= names
    assert not names & {"RESS_AR_REMB", "RESS_AV_REMB", "RESS_AV_SABLE"}


def test_arbitree_fiche_group_naming_gaps_are_only_uncited_groups() -> None:
    """Lot 19, step 3: no group cited by a decision is missing from the
    convention; the gaps are groups no decision names (reported, not fixed)."""
    sheet = _load()

    gaps = sheet.group_naming_gaps()
    assert not [g for g in gaps if "absent de la convention" in g]
    assert gaps
    assert not any("BOLLARD" in g or "DEFENSE" in g for g in gaps)


def test_arbitree_fiche_is_still_not_ready_for_generation() -> None:
    """Four blockers remain: the `code_aster` point 1 comparison table
    (U2.02.01 leaves DKT-DKQ and COQUE_3D admissible without ranking them for
    a curved tube) and the three unfounded Code_Aster points of lot 19."""
    sheet = _load()

    assert sheet.is_ready_for_generation is False
    blockers = sheet.generation_blockers()
    assert len(blockers) == 4
    assert not any("group_naming" in b for b in blockers)
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
