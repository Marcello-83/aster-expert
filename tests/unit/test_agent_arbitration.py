"""Tests for aster_expert.agent.arbitration (lot 15, P1-P4).

P1 is the central deliverable: these tests must fail if any path other
than `record_practice_decision` can move a `pratique` entry to
`status="tranche"`, or if that entry can end up without a source, a
discarded variant, or a `decided_by`/`decided_at` pair. No network, no
corpus, no catalogue (CLAUDE.md): every source here is hand-built.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from aster_expert.agent.arbitration import (
    apply_decision,
    record_practice_decision,
    render_decision_sheet,
)
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DiscardedVariant,
    DocumentarySource,
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
)

_DOC_SOURCE = DocumentarySource(
    document_id="R7.01.25",
    aster_version="17.4.0",
    section_path=("index",),
    source_path="source/manuals/man_r/r7/r7.01.25/index.rst",
    profile="methode",
    excerpt="Ce document décrit des lois surfaciques pour barrages.",
)

_CATALOGUE_SOURCE = CatalogueSource(
    command="DEFI_MATERIAU",
    aster_version="17.4.0",
    keyword_path=("MOHR_COULOMB",),
)


def _practice_source(day: int = 18) -> PracticeSource:
    return PracticeSource(
        origin="decision_ingenieur",
        reference="Choix du bureau d'études : contact frottant",
        date=date(2026, 9, day),
    )


_DISCARDED = (
    DiscardedVariant(
        description="Éléments de joint", reason="non documenté pour ce cas"
    ),
)

_UNRESOLVED_ENTRY = PracticeHypothesisEntry(
    point_label="4",
    topic="Choix entre contact surfacique, ressorts discrets et éléments de joint",
    notes='Cherché sous methode ("interface sol-écran") : aucun résultat pertinent.',
    status="non_tranche",
)

_ESTABLISHED_SIBLING = CodeAsterHypothesisEntry(
    point_label="4",
    topic="Mécanisme catalogue de contact-frottement pour une interface sol-écran",
    option_retained="DEFI_CONTACT / FORMULATION='DISCRETE'",
    justification="get_command_schema liste ce mécanisme pour ce cas.",
    sources=(_CATALOGUE_SOURCE, _DOC_SOURCE),
    status="tranche",
)


def _sheet(entries: tuple[object, ...]) -> HypothesesSheet:
    return HypothesesSheet(
        project_name="Quai combi-wall -- essai",
        structure_description="Écran de soutènement ancré",
        aster_version="17.4.0",
        created_at=datetime(2026, 9, 18),
        entries=entries,  # type: ignore[arg-type]
    )


def test_record_practice_decision_builds_a_tranche_entry() -> None:
    entry = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant (DEFI_CONTACT)",
        justification="Cohérent avec les projets antérieurs similaires.",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    assert isinstance(entry, PracticeHypothesisEntry)
    assert entry.nature == "pratique"
    assert entry.status == "tranche"
    assert entry.topic == _UNRESOLVED_ENTRY.topic
    assert entry.point_label == "4"
    assert entry.decision_history == ()


def test_record_practice_decision_rejects_no_discarded_variant() -> None:
    with pytest.raises(ValidationError, match="variantes écartées"):
        record_practice_decision(
            entry=_UNRESOLVED_ENTRY,
            option_retained="Contact frottant",
            justification="x",
            sources=(_practice_source(),),
            discarded_variants=(),
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_record_practice_decision_rejects_no_source() -> None:
    with pytest.raises(ValidationError, match="exige au moins une source"):
        record_practice_decision(
            entry=_UNRESOLVED_ENTRY,
            option_retained="Contact frottant",
            justification="x",
            sources=(),
            discarded_variants=_DISCARDED,
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_record_practice_decision_rejects_a_documentary_source() -> None:
    """P1: a Code_Aster documentary source remains structurally impossible
    for a practice arbitration, exactly as at lot 14 (M2)."""
    with pytest.raises(ValidationError):
        record_practice_decision(
            entry=_UNRESOLVED_ENTRY,
            option_retained="Contact frottant",
            justification="x",
            sources=(_DOC_SOURCE,),  # type: ignore[arg-type]
            discarded_variants=_DISCARDED,
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_record_practice_decision_has_no_status_parameter() -> None:
    """Mirrors drafting.py's N3 discipline: no caller can make this build
    anything but a `tranche` entry."""
    assert "status" not in inspect.signature(record_practice_decision).parameters


def test_record_practice_decision_required_parameters_have_no_default() -> None:
    params = inspect.signature(record_practice_decision).parameters
    for name in ("sources", "discarded_variants", "decided_by", "decided_at"):
        assert params[name].default is inspect.Parameter.empty


def test_record_practice_decision_first_arbitration_has_empty_history() -> None:
    entry = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="x",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    assert entry.decision_history == ()


def test_record_practice_decision_preserves_history_on_re_arbitration() -> None:
    first = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="Décision initiale",
        sources=(_practice_source(18),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    second = record_practice_decision(
        entry=first,
        option_retained="Ressorts discrets",
        justification="Révision après retour d'expérience",
        sources=(_practice_source(20),),
        discarded_variants=_DISCARDED,
        decided_by="M. Martin",
        decided_at=datetime(2026, 10, 1, 9, 0),
    )

    assert second.option_retained == "Ressorts discrets"
    assert len(second.decision_history) == 1
    assert second.decision_history[0].option_retained == "Contact frottant"
    assert second.decision_history[0].decided_by == "J. Dupont"


def test_no_hand_built_shortcut_reaches_a_tranche_practice_entry() -> None:
    """The guarantee P1 asks to be tested for: any construction path --
    not just this module's function -- that tries to produce a decided
    `pratique` entry missing decided_by/decided_at/discarded_variants is
    rejected by the schema itself."""
    with pytest.raises(ValidationError):
        PracticeHypothesisEntry(
            topic=_UNRESOLVED_ENTRY.topic,
            option_retained="Contact frottant",
            justification="x",
            sources=(_practice_source(),),
            status="tranche",
        )


def test_apply_decision_replaces_matching_entry() -> None:
    sheet = _sheet((_ESTABLISHED_SIBLING, _UNRESOLVED_ENTRY))
    decided = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="x",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    updated = apply_decision(sheet, decided)

    assert len(updated.entries) == 2
    assert updated.entries[1].status == "tranche"
    assert updated.entries[0] == _ESTABLISHED_SIBLING
    assert sheet.entries[1].status == "non_tranche"


def test_apply_decision_rejects_when_entry_not_found() -> None:
    sheet = _sheet((_ESTABLISHED_SIBLING,))
    decided = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="x",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    with pytest.raises(ValueError, match="aucune entrée pratique correspondante"):
        apply_decision(sheet, decided)


def test_apply_decision_rejects_ambiguous_match() -> None:
    duplicate = PracticeHypothesisEntry(
        point_label=_UNRESOLVED_ENTRY.point_label,
        topic=_UNRESOLVED_ENTRY.topic,
        status="non_tranche",
    )
    sheet = _sheet((_UNRESOLVED_ENTRY, duplicate))
    decided = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="x",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    with pytest.raises(ValueError, match="ambiguë"):
        apply_decision(sheet, decided)


def test_render_decision_sheet_lists_each_unresolved_entry_with_corpus_context() -> (
    None
):
    other_unresolved = PracticeHypothesisEntry(
        topic="Phasage construction/excavation",
        point_label="6",
        notes="Aucun document dédié à ce phasage.",
        status="non_tranche",
    )
    sheet = _sheet((_ESTABLISHED_SIBLING, _UNRESOLVED_ENTRY, other_unresolved))

    document = render_decision_sheet(sheet)

    assert "Choix entre contact surfacique" in document
    assert "Phasage construction/excavation" in document
    assert "DEFI_CONTACT / FORMULATION='DISCRETE'" in document
    assert "R7.01.25" in document
    assert "aucun résultat pertinent" in document
    assert "Aucune option catalogue directement rattachée" in document


def test_render_decision_sheet_carries_no_recommendation() -> None:
    """The preamble names the absence of a recommendation explicitly (that
    sentence itself is exempted below); no per-option text should ever mark
    one choice as preferred."""
    sheet = _sheet((_ESTABLISHED_SIBLING, _UNRESOLVED_ENTRY))

    document = render_decision_sheet(sheet)

    body = document.split("### Options disponibles au catalogue", 1)[1]
    lowered = body.lower()
    assert "recommand" not in lowered
    assert "conseil" not in lowered
    assert "il faut" not in lowered


def test_render_decision_sheet_ignores_resolved_practice_entries() -> None:
    decided = record_practice_decision(
        entry=_UNRESOLVED_ENTRY,
        option_retained="Contact frottant",
        justification="x",
        sources=(_practice_source(),),
        discarded_variants=_DISCARDED,
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )
    sheet = _sheet((_ESTABLISHED_SIBLING, decided))

    document = render_decision_sheet(sheet)

    assert "## 1." not in document
