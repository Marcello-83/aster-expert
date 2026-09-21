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

import pytest

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
    ExecutionSource,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.catalogue.query import catalogue_vocabulary

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
    # + point non fondé du lot 19 ; le tableau comparatif est remplacé sur place ;
    # + 4 constats d'exécution du lot 22 (le constat des ressorts est remplacé)
    # + 2 constats d'exécution du lot 23 (efforts généralisés, équilibre) ; les
    # constats REAC_NODA et RHO sont remplacés sur place
    # + 1 constat d'exécution (axes d'ELAS_COQUE, lot 25) et la décision du repère
    # global (point 9, lot 25)
    assert len(sheet.entries) == 39


def test_arbitree_fiche_has_eleven_decided_practice_entries() -> None:
    sheet = _load()

    tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "tranche"
    ]
    # 10 up to lot 20, plus MM's decision on the tube shell choice (lot 21) and
    # the global frame (point 9, lot 25)
    assert len(tranche_practice) == 12
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
        "9",
    }
    assert all(e.decided_by == "MM" for e in tranche_practice)
    assert all(e.validity_domain for e in tranche_practice)
    assert all(e.discarded_variants for e in tranche_practice)


def test_arbitree_fiche_has_no_open_practice_entry_left() -> None:
    """Lot 21: the tube shell choice is decided by MM and the surface-spring
    point is replaced by a documented Code_Aster finding."""
    sheet = _load()

    assert not [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "non_tranche"
    ]


def test_arbitree_fiche_tube_shell_decision_is_recorded_as_worded() -> None:
    sheet = _load()

    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.topic.startswith("Choix de la modélisation de coque du tube")
    ]
    assert entry.point_label == "1"
    assert entry.status == "tranche"
    assert entry.decided_by == "MM"
    assert entry.decided_at is not None
    assert entry.decided_at.isoformat() == "2026-09-21T18:00:00"
    # the entry was open, never decided before: no prior decision to keep
    assert entry.decision_history == ()
    # `options_considered` (lot 21) survives the decision
    assert entry.options_considered == ("DKT", "COQUE_3D")
    assert (entry.option_retained or "").startswith("Le tube est modélisé en DKT")
    assert [v.description for v in entry.discarded_variants] == ["Tube en COQUE_3D."]
    (source,) = entry.sources
    assert source.origin == "decision_ingenieur"
    assert source.date is not None and source.date.isoformat() == "2026-09-21"


def test_arbitree_fiche_nodal_spring_finding_replaces_the_unfounded_point() -> None:
    sheet = _load()

    topics = [e.topic for e in sheet.entries]
    assert not [t for t in topics if t.startswith("Répartition d'une raideur")]
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.topic.startswith("Affectation, à des nœuds existants")
    ]
    assert entry.status == "tranche" and entry.point_label == "4"
    for identifier in ("CREA_POI1", "DIS_T", "K_T_D_N", "REPERE = GLOBAL"):
        assert identifier in (entry.option_retained or "")
    catalogue = {
        (s.command, s.keyword_path)
        for s in entry.sources
        if isinstance(s, CatalogueSource)
    }
    assert catalogue == {
        ("CREA_MAILLAGE", ("CREA_POI1",)),
        ("AFFE_MODELE", ("AFFE", "MODELISATION")),
        ("AFFE_CARA_ELEM", ("DISCRET",)),
    }
    assert {
        s.document_id for s in entry.sources if isinstance(s, DocumentarySource)
    } == {
        "U4.23.02",
        "U4.42.01",
        "U2.02.03",
        "V1.01.372",
    }
    # the former unfounded point's search trace is kept in the notes
    assert "Historique du point non fondé remplacé (lot 20) : Cherché sous" in (
        entry.notes or ""
    )
    assert "RIGI_PARASOL" in (entry.notes or "")


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
    # Lot 23 : v4 revised points 7 and 8 again (2026-09-22, after v3).
    assert set(revised) == {"1", "2", "4", "5", "6", "7", "8"}
    for label in ("1", "2", "4", "5", "6"):
        entry = revised[label]
        assert len(entry.decision_history) == 1
        assert entry.decision_history[0].decided_at.date().isoformat() == "2026-09-18"
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-21"
    v7, v8 = revised["7"], revised["8"]
    assert [h.decided_at.date().isoformat() for h in v7.decision_history] == [
        "2026-09-18",
        "2026-09-21",
    ]
    assert [h.decided_at.date().isoformat() for h in v8.decision_history] == [
        "2026-09-21"
    ]
    for entry in (v7, v8):
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-22"


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


def _catalogue_vocabulary() -> frozenset[str]:
    root = Path(__file__).resolve().parents[2] / "data" / "processed" / "catalogue"
    digests = sorted(p for p in root.glob("sha256:*") if p.is_dir())
    if not digests:
        pytest.skip("catalogue extrait absent (data/processed/catalogue)")
    return catalogue_vocabulary(root, digests[-1].name)


def test_arbitree_fiche_group_naming_gaps_are_closed() -> None:
    """Lot 21: no point hung on by a group carries an open practice entry any
    more (lot 20 reported 22 gaps, on points 1 and 4).

    Lot 24 reported two false positives, `EPAIS` and `EFGE_NOEU` (backticked
    Code_Aster identifiers read as mesh groups). Lot 25: the check now takes the
    catalogue vocabulary (no hard-coded list) and reports nothing. Without the
    vocabulary the two reports are still there: the check needs it, by design.
    """
    sheet = _load()

    assert sheet.group_naming_gaps() == (
        "groupe cité par la décision du point 1 absent de la convention : EPAIS",
        "groupe cité par la décision du point 1 absent de la convention : EFGE_NOEU",
    )
    assert sheet.group_naming_gaps(_catalogue_vocabulary()) == ()


def test_arbitree_fiche_has_no_blocker_left_after_decision_2_v5() -> None:
    """Lot 24: MM's v5 decision 2 (point 1, homogenisation) is recorded and closes
    the revision declared at lot 22; no entry is under revision any more. No
    blocker does not mean the decision's validity domain is met (it requires a
    sensitivity study of the horizontal membrane rigidity)."""
    sheet = _load()

    assert sheet.generation_blockers() == ()
    assert sheet.is_ready_for_generation is True
    assert sheet.entries_under_revision() == ()
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.topic.startswith("Homogénéisation ou représentation distincte")
    ]
    assert entry.status == "tranche" and entry.decided_by == "MM"
    assert entry.decided_at is not None
    assert entry.decided_at.date().isoformat() == "2026-09-21"
    assert [(ev.kind, ev.by) for ev in entry.revision_history] == [
        ("declared", "Claude (lot 22 ; motif mis à jour au lot 23)"),
        ("lifted", "MM"),
    ]
    assert entry.validity_domain is not None
    assert "sensibilité" in entry.validity_domain


def test_arbitree_fiche_point_8_revision_is_declared_then_lifted_by_decision_9() -> (
    None
):
    sheet = _load()

    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.topic.startswith("Application des charges localisées")
    ]
    assert not entry.under_revision
    assert [(ev.kind, ev.by) for ev in entry.revision_history] == [
        ("declared", "Claude (lot 22)"),
        ("lifted", "MM"),
    ]


def test_arbitree_fiche_never_attaches_a_documentary_source_to_a_practice_entry() -> (
    None
):
    """M2, confirmed again on the arbitrated fiche."""
    sheet = _load()

    for entry in sheet.entries:
        if isinstance(entry, PracticeHypothesisEntry):
            for source in entry.sources:
                assert not isinstance(
                    source, (DocumentarySource, CatalogueSource, ExecutionSource)
                )


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
