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
    CodeAsterHypothesisEntry,
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

    # 24 du spécimen + décision 0 (lot 18) + décision 9 (lot 19, R2) + 5 entrées
    # du lot 20 (3 constats code_aster, 1 point non fondé, 1 renvoi pratique)
    # + point non fondé du lot 19 ; le tableau comparatif est remplacé sur place
    assert len(sheet.entries) == 31


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


def test_arbitree_fiche_has_exactly_two_open_practice_entries() -> None:
    """Lot 20: the surface-spring point (still unfounded after a full search)
    and the referral of the tube shell choice (DKT or COQUE_3D) to practice."""
    sheet = _load()

    open_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    ]
    assert {e.point_label for e in open_practice} == {"1", "4"}
    assert all(e.notes and e.notes.startswith("Cherché sous") for e in open_practice)


def test_arbitree_fiche_lot20_code_aster_findings_are_decided_and_sourced() -> None:
    sheet = _load()

    findings = {
        e.topic: e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.status == "tranche"
    }
    force_coque = next(
        t for t in findings if t.startswith("Application d'une force surfacique")
    )
    force_nodale = next(t for t in findings if "force et d'un moment nodaux" in t)
    recevables = next(
        t for t in findings if t.startswith("Modélisations de coque recevables")
    )
    for topic, keyword in (
        (force_coque, "FORCE_COQUE"),
        (force_nodale, "FORCE_NODALE"),
    ):
        entry = findings[topic]
        assert keyword in (entry.option_retained or "")
        catalogue = [s for s in entry.sources if isinstance(s, CatalogueSource)]
        assert [s.keyword_path for s in catalogue] == [(keyword,)]
        assert any(
            isinstance(s, DocumentarySource) and keyword in (s.excerpt or "")
            for s in entry.sources
        )
    assert "ne les départage pas" in (findings[recevables].option_retained or "")


def test_arbitree_fiche_comparison_table_entry_is_now_a_documented_finding() -> None:
    sheet = _load()

    table = [
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.topic.startswith("Contenu détaillé du tableau comparatif")
    ]
    assert len(table) == 1 and table[0].status == "tranche"


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


def test_arbitree_fiche_every_group_carries_a_point_label() -> None:
    sheet = _load()

    assert all(g.point_label for g in sheet.group_naming)
    assert {g.point_label for g in sheet.group_naming} == {
        "1",
        "2",
        "3",
        "4",
        "5",
        "7",
        "8",
    }


def test_arbitree_fiche_group_naming_gaps_report_the_open_points() -> None:
    """Lot 20, step 5: gaps are the groups hung on a point that still carries
    an open practice entry (point 1: tube shell choice; point 4: surface
    spring) -- reported, not masked."""
    sheet = _load()

    gaps = sheet.group_naming_gaps()
    assert len(gaps) == 22
    assert not [g for g in gaps if "absent de la convention" in g]
    assert any("PALP_01" in g and "point 1" in g for g in gaps)
    assert any("RESS_AV_ARGI" in g and "point 4" in g for g in gaps)
    assert not any("BOLLARD" in g or "DEFENSE" in g or "ANC_01" in g for g in gaps)


def test_arbitree_fiche_is_still_not_ready_for_generation() -> None:
    """Two blockers remain (lot 20): the surface-spring point and the tube
    shell choice referred to practice."""
    sheet = _load()

    assert sheet.is_ready_for_generation is False
    blockers = sheet.generation_blockers()
    assert len(blockers) == 2
    assert any("point 4" in b and "raideur de réaction" in b for b in blockers)
    assert any("point 1" in b and "DKT ou COQUE_3D" in b for b in blockers)


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
