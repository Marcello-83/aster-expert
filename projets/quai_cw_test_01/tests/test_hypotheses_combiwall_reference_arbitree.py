"""M5/P1-P4/R1-R2 confronted a second time: MM's v2 arbitration, recorded
for real (lot 18).

`projets/quai_cw_test_01/fiche/hypotheses_combiwall_reference_arbitree.json` is
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
from datetime import datetime
from pathlib import Path

import pytest

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
    ExecutionSource,
    FindingReference,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.catalogue.query import catalogue_vocabulary
from aster_expert.constats.base import load_resolved_sheet

_ARBITREE_PATH = (
    Path(__file__).resolve().parents[3]
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)


def _load() -> HypothesesSheet:
    return load_resolved_sheet(_ARBITREE_PATH)


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
    # + la décision 11 (point 10, lot 27)
    # + la décision 12 (point 11, lot 28) et 6 constats code_aster (points 2, 3, 5 x3,
    #   7) dont 2 remplacent sur place des constats minces de la fiche de base (lot 14)
    # + 1 constat code_aster (mécanisme du pivot nul, point 3, lot 31)
    # + la décision 13 (point 12, lot 33) et 1 constat code_aster
    #   (FORCE_POUTRE, point 12)
    # + 3 constats d'exécution du lot 35 (CREA_POI1, point 4 ; poutre continue,
    #   point 12 ; REAC_NODA et LIAISON_SOLIDE, point 3) ; le quatrième (évaluation
    #   aux nœuds de FORCE_COQUE/PRES, point 5) remplace sur place celui du doublement
    # + 1 constat code_aster du lot 37 (identifiant POU_D_T, point 3) ; les décisions
    #   14, 15, 16 révisent des entrées existantes (aucune entrée ajoutée)
    # + lot 38 : D17 (point 13) et D18 (point 14) ajoutent deux entrées, D14 bis en
    #   révise une (historique conservé) ; 2 constats code_aster (symétrie de POU_D_T,
    #   point 7 ; état des lieux du ferraillage, point 14)
    # + lot 39 : D19 (point 14) ajoute une entrée ; 6 constats d'exécution sur
    #   CALC_FERRAILLAGE (point 14)
    # + lot 44 : D20 et D21 (point 14) ajoutent deux entrées
    assert len(sheet.entries) == 65


def test_arbitree_fiche_has_eleven_decided_practice_entries() -> None:
    sheet = _load()

    tranche_practice = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "tranche"
    ]
    # 10 up to lot 20, plus MM's decision on the tube shell choice (lot 21) and
    # the global frame (point 9, lot 25), decision 11 (point 10, lot 27),
    # decision 12 (point 11, lot 28), decision 13 (point 12, lot 33) and, lot 38,
    # D17 (point 13) and D18 (point 14), lot 39: D19 (point 14), lot 44: D20 and
    # D21 (point 14)
    assert len(tranche_practice) == 20
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
        "10",
        "11",
        "12",
        "13",
        "14",
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

    topics = [e.topic for e in sheet.entries if not isinstance(e, FindingReference)]
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
    assert set(revised) == {"1", "2", "3", "4", "5", "6", "7", "8"}
    for label in ("1", "2", "5"):
        entry = revised[label]
        assert len(entry.decision_history) == 1
        assert entry.decision_history[0].decided_at.date().isoformat() == "2026-09-18"
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-21"
    # Lot 37 : les décisions 16 (point 4) et 15 (point 6) ont ajouté un texte au
    # domaine de validité de la décision v3 (2026-09-21), qui passe en historique.
    for label in ("4", "6"):
        entry = revised[label]
        assert [h.decided_at.date().isoformat() for h in entry.decision_history] == [
            "2026-09-18",
            "2026-09-21",
        ]
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-25"
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

    assert len(sheet.group_naming) == 58
    assert all(g.status == "tranche" for g in sheet.group_naming)
    names = {g.group_name for g in sheet.group_naming}
    assert {"BOLLARD", "DEFENSE", "TUBE_05", "SYM_G", "ANC_09", "PIED_TUBES"} <= names
    assert not names & {"RESS_AR_REMB", "RESS_AV_REMB", "RESS_AV_SABLE"}


def test_arbitree_fiche_every_group_carries_a_point_label() -> None:
    sheet = _load()

    assert all(g.point_label for g in sheet.group_naming)
    assert {g.point_label for g in sheet.group_naming} == {
        "1",
        "2",
        "3",
        "4",
        "7",
        "8",
        "10",
        "11",
    }


def _catalogue_vocabulary() -> frozenset[str]:
    root = Path(__file__).resolve().parents[3] / "data" / "processed" / "catalogue"
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
        # Lot 39: D19 (point 14) names the command `CALC_FERRAILLAGE`, read as a
        # group without the vocabulary -- same by-design report as the two above.
        "groupe cité par la décision du point 14 absent de la convention : "
        "CALC_FERRAILLAGE",
    )
    assert sheet.group_naming_gaps(_catalogue_vocabulary()) == ()


def test_arbitree_fiche_has_no_blocker_left_after_decision_2_v5() -> None:
    """Lot 24: MM's v5 decision 2 (point 1, homogenisation) is recorded and closes
    the revision declared at lot 22; no entry of point 1 is under revision any
    more. No blocker does not mean the decision's validity domain is met (it
    requires a sensitivity study of the horizontal membrane rigidity).

    Lot 31: point 3 (junction decision 4) is declared under revision in turn,
    for an unrelated reason (the null-pivot mechanism established there) --
    the fiche was no longer blocker-free overall for that lot, though point
    1's own revision stayed closed.

    Lot 32: the point-3 revision is closed in turn (étape 1's boundary-
    condition rule removed the null pivot on the reduced quay, decision 4
    itself unchanged) -- no entry is under revision any more."""
    sheet = _load()

    assert sheet.entries_under_revision() == ()
    assert sheet.is_ready_for_generation is True
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
        Path(__file__).resolve().parents[3]
        / "projets"
        / "quai_cw_test_01"
        / "fiche"
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


def test_arbitree_fiche_records_decision_11_and_grounds_the_screen_on_it() -> None:
    """Lot 27: part B of `donnees_complementaires_combiwall_v1.md` is inserted at
    point 10 (its option table verbatim), `decided_at` is the recording time, and
    `ECRAN_POUSSEE` is defined by point 10 (it was on point 5)."""
    sheet = _load()
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == "10"
    ]
    assert entry.status == "tranche"
    assert entry.decided_by == "MM"
    assert entry.decided_at == datetime.fromisoformat("2026-09-21T11:51:43-04:00")
    assert entry.option_retained is not None
    assert "| Facettisation des tubes | 40 facettes sur la circonférence (9°)." in (
        entry.option_retained
    )
    assert len(entry.discarded_variants) == 3
    assert entry.sources[0].origin == "decision_ingenieur"
    (screen,) = [g for g in sheet.group_naming if g.group_name == "ECRAN_POUSSEE"]
    assert screen.point_label == "10"
    assert not entry.under_revision


def test_arbitree_fiche_records_decision_12_and_adds_pied_tubes() -> None:
    """Lot 28: `decision12_appui_vertical.md` is inserted at point 11 (its option
    verbatim), `decided_at` is the recording time, and `PIED_TUBES` is added to the
    group naming convention, grounded on point 11."""
    sheet = _load()
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == "11"
    ]
    assert entry.status == "tranche"
    assert entry.topic == "Appui vertical de l'écran"
    assert entry.decided_by == "MM"
    assert entry.decided_at == datetime.fromisoformat("2026-09-22T03:04:42-04:00")
    assert entry.option_retained is not None
    assert "PIED_TUBES" in entry.option_retained
    assert len(entry.discarded_variants) == 2
    assert entry.sources[0].origin == "decision_ingenieur"
    (pied,) = [g for g in sheet.group_naming if g.group_name == "PIED_TUBES"]
    assert pied.kind == "noeud"
    assert pied.point_label == "11"
    assert not entry.under_revision


def test_arbitree_fiche_records_the_lot31_finding_and_revision() -> None:
    """Lot 31: the null-pivot mechanism (point 3) is recorded as a new
    code_aster finding (never replacing the two existing point-3 findings,
    which answer a different question), then the point-3 practice entry
    (decision 4, junction method) is declared under revision citing it --
    the decision itself is untouched.

    Lot 32: the revision is closed in turn (`lift_revision`, étape 1's
    boundary-condition rule) -- decision 4 stays untouched, the fiche is no
    longer blocked on this point."""
    sheet = _load()
    code_aster_point_3 = [
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.point_label == "3"
    ]
    assert len(code_aster_point_3) == 5  # 3 + REAC_NODA (lot 35) + POU_D_T (lot 37)
    (finding,) = [
        e
        for e in code_aster_point_3
        if e.topic.startswith("Mécanisme documentaire du pivot nul")
    ]
    assert finding.status == "tranche"
    assert any(isinstance(s, DocumentarySource) for s in finding.sources)
    assert any(isinstance(s, CatalogueSource) for s in finding.sources)
    (decision,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == "3"
        and e.topic.startswith("Choix entre maillage coïncident")
    ]
    assert not decision.under_revision
    assert decision.option_retained is not None
    # Lot 37 : la décision 14 remplace l'option ; celle du lot 32 est en historique
    # (lot 38 : D14 bis remplace D14, qui passe en dernier de l'historique).
    assert "Maillage coïncident" in decision.decision_history[0].option_retained
    assert "élément de poutre de Timoshenko sur son axe" in decision.option_retained
    assert [(ev.kind, ev.by) for ev in decision.revision_history] == [
        ("declared", "Claude (lot 31)"),
        ("lifted", "Claude (lot 32)"),
    ]
    assert sheet.entries_under_revision() == ()


def test_arbitree_fiche_lot28_facts_are_recorded_and_sourced() -> None:
    """Lot 28, Étape 2: the five code_aster findings, catalogue- and
    doc-confirmed, with a verbatim excerpt each."""
    sheet = _load()

    findings = {
        e.topic: e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.status == "tranche"
    }
    liaison = findings[
        "Liaison de corps solide entre un anneau de nœuds de coque et un nœud de poutre"
    ]
    assert liaison.point_label == "3"
    assert "LIAISON_SOLIDE" in (liaison.option_retained or "")
    assert {
        (s.command, s.keyword_path)
        for s in liaison.sources
        if isinstance(s, CatalogueSource)
    } >= {("AFFE_CHAR_MECA", ("LIAISON_SOLIDE",))}

    pression = findings["Pression répartie fonction de Z sur des coques DKT"]
    assert pression.point_label == "5"
    assert "FORCE_COQUE" in (pression.option_retained or "")
    assert "PRES_REP n'est PAS utilisé" in (pression.option_retained or "")

    orientation = findings[
        "Orientation cohérente des normales de coque pour qu'une pression positive "
        "agisse côté terre"
    ]
    assert orientation.point_label == "5"
    assert "ORIE_NORM_COQUE" in (orientation.option_retained or "")

    # lot 35 : le constat du doublement à Z ± 1 mm est remplacé (historique dans les
    # notes) par celui de l'évaluation aux nœuds, établi par exécution
    assert (
        "Représentation d'un profil de pression discontinu par points doublés à "
        "Z ± 0,001 m"
    ) not in findings
    profil = findings[
        "Évaluation aux nœuds de FORCE_COQUE/PRES (fonction) : une marche de pression "
        "à une interface de couches déborde d'une demi-maille"
    ]
    assert profil.point_label == "5"
    assert any(isinstance(s, DocumentarySource) for s in profil.sources)
    assert any(isinstance(s, ExecutionSource) for s in profil.sources)
    assert "aux nœuds" in (profil.option_retained or "")
    assert "Historique du constat remplacé" in (profil.notes or "")
    assert "à Z ± 1 mm" in (profil.notes or "")

    symetrie = findings[
        "Conditions de symétrie par rapport à un plan X = constante pour des coques "
        "DKT et des poutres POU_D_E"
    ]
    assert symetrie.point_label == "7"
    for token in ("DX=0.0", "DRY=0.0", "DRZ=0.0"):
        assert token in (symetrie.option_retained or "")

    barre = findings[
        "Élément de barre : section, matériau, et absence de degré de rotation au "
        "nœud commun avec la coque"
    ]
    assert barre.point_label == "2"
    assert "GENERALE" in (barre.option_retained or "")

    # every excerpt is a real, non-empty passage (N1) -- exercised again here for
    # good measure, on top of `_require_a_verbatim_excerpt_when_documentary`
    for finding in (liaison, pression, orientation, symetrie, barre):
        documentary = [s for s in finding.sources if isinstance(s, DocumentarySource)]
        assert any((s.excerpt or "").strip() for s in documentary)


def test_arbitree_fiche_lot28_facts_supersede_the_thin_base_fiche_notes() -> None:
    """The two lot-14 catalogue-schema-only notes on points 3 and 5 (no verbatim
    excerpt, no source_commit) are gone -- superseded, not merely accumulated."""
    sheet = _load()

    topics = [e.topic for e in sheet.entries if not isinstance(e, FindingReference)]
    assert (
        "Mécanisme catalogue pour raccorder un maillage poutre à un maillage "
        "coque non coïncidents"
    ) not in topics
    assert (
        "Mécanisme catalogue d'application d'une pression fonction de la profondeur"
    ) not in topics


# --- lot 35 : constats établis par exécution au lot 34 ----------------------


def _code_aster(topic_start: str) -> CodeAsterHypothesisEntry:
    matches = [
        e
        for e in _load().entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.topic.startswith(topic_start)
    ]
    assert len(matches) == 1, topic_start
    return matches[0]


@pytest.mark.parametrize(
    ("topic_start", "point", "n_execution", "tokens"),
    [
        (
            "Évaluation aux nœuds de FORCE_COQUE/PRES",
            "5",
            3,
            ("aux nœuds", "par couche", "1,185e-3"),
        ),
        (
            "CREA_POI1 : une seule maille ponctuelle par nœud",
            "4",
            2,
            ("une** maille ponctuelle par nœud", "somme", "173 749"),
        ),
        (
            "Charge répartie sur une poutre continue liée par plusieurs LIAISON_SOLIDE",
            "12",
            1,
            ("CALCULEL2_92", "forces nodales", "29 811,6"),
        ),
        (
            "REAC_NODA aux nœuds liés par LIAISON_SOLIDE",
            "3",
            1,
            ("non bloquées", "bloquées", "9,790917005e5"),
        ),
    ],
)
def test_lot35_the_four_lot34_findings_are_recorded_with_execution_sources(
    topic_start: str, point: str, n_execution: int, tokens: tuple[str, ...]
) -> None:
    entry = _code_aster(topic_start)

    assert entry.status == "tranche"
    assert entry.point_label == point
    executions = [s for s in entry.sources if isinstance(s, ExecutionSource)]
    assert len(executions) == n_execution
    assert all(s.validation_level == "D" for s in executions)
    for token in tokens:
        assert token in (entry.option_retained or ""), token
    assert any(isinstance(s, CatalogueSource) for s in entry.sources)


def test_lot35_the_replaced_finding_keeps_its_own_history() -> None:
    entry = _code_aster("Évaluation aux nœuds de FORCE_COQUE/PRES")

    assert "Historique du constat remplacé" in (entry.notes or "")
    assert "REMPLACE" in (entry.notes or "")
    old_topic = (
        "Représentation d'un profil de pression discontinu par points doublés à "
        "Z ± 0,001 m"
    )
    assert old_topic in (entry.notes or "")


def test_lot35_the_before_and_after_deviations_of_the_nodal_evaluation() -> None:
    entry = _code_aster("Évaluation aux nœuds de FORCE_COQUE/PRES")
    executions = [s for s in entry.sources if isinstance(s, ExecutionSource)]
    before_spec, before_nodal, after = executions

    # avant : 1,185e-3 de moins que le profil spécifié, mais la règle d'évaluation aux
    # nœuds reproduit la valeur de Code_Aster à 1e-13 près ; après : profil spécifié
    assert before_spec.case_path.endswith("f1_avant.sonde.comm")
    assert before_spec.relative_deviation == pytest.approx(-1.185e-3, rel=1e-3)
    assert before_nodal.case_path == before_spec.case_path
    assert abs(before_nodal.relative_deviation) < 1e-13
    assert after.case_path.endswith("f1_apres.sonde.comm")
    assert abs(after.relative_deviation) < 1e-11


def test_lot35_the_lost_spring_stiffness_is_the_argile_share() -> None:
    entry = _code_aster("CREA_POI1 : une seule maille ponctuelle par nœud")
    sources = sorted(
        (s for s in entry.sources if isinstance(s, ExecutionSource)),
        key=lambda s: s.case_path,
    )

    after, before = sources  # f2_apres, f2_avant (ordre alphabétique)
    # avant : la raideur de la marne seule, soit 1 - k_argile/(k_argile + k_marne)
    assert before.relative_deviation == pytest.approx(-0.30434783, rel=1e-6)
    assert abs(after.relative_deviation) < 1e-11
