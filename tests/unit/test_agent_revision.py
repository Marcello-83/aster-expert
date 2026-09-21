"""« En révision » (lot 22, V1): an explicit, reasoned, logged blocker.

`generation_blockers()` was empty at lot 21 while decision 2 was in revision.
These tests fail if a revision can be declared without a reason, if it can
disappear without a logged event, or if an entry under revision stops being
a generation blocker.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from aster_expert.agent.arbitration import (
    apply_decision,
    declare_under_revision,
    lift_revision,
    record_practice_decision,
)
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
    RevisionEvent,
)

_T0 = datetime(2026, 9, 21, 10, 0, 0)
_T1 = datetime(2026, 9, 22, 10, 0, 0)
_T2 = datetime(2026, 9, 23, 10, 0, 0)
_SOURCE = PracticeSource(
    origin="decision_ingenieur", reference="MM, séance", date=_T0.date()
)


def _decided(topic: str = "Choix du tube") -> PracticeHypothesisEntry:
    open_entry = PracticeHypothesisEntry(
        point_label="1", topic=topic, status="non_tranche"
    )
    return record_practice_decision(
        entry=open_entry,
        option_retained="DKT",
        justification="mince",
        validity_domain="h/R < 1/20",
        sources=(_SOURCE,),
        discarded_variants=(DiscardedVariant(description="COQUE_3D", reason="coût"),),
        decided_by="MM",
        decided_at=_T0,
    )


def _sheet(*entries: PracticeHypothesisEntry) -> HypothesesSheet:
    return HypothesesSheet(
        project_name="p",
        structure_description="s",
        created_at=_T0,
        entries=entries,
        group_naming=(
            MeshGroupNaming(
                group_name="TUBE",
                kind="maille",
                description="d",
                status="tranche",
                point_label="1",
            ),
        ),
    )


def test_a_decided_entry_is_not_under_revision_by_default() -> None:
    entry = _decided()

    assert entry.under_revision is False
    assert entry.revision_history == ()
    assert _sheet(entry).generation_blockers() == ()


def test_declaring_a_revision_makes_the_entry_a_generation_blocker() -> None:
    entry = declare_under_revision(
        _decided(), reason="v4 non confirmée", declared_by="Claude", declared_at=_T1
    )
    sheet = _sheet(entry)

    assert entry.under_revision is True
    assert entry.revision_reason == "v4 non confirmée"
    assert sheet.is_ready_for_generation is False
    assert sheet.generation_blockers() == (
        "entrée pratique en révision (point 1) : Choix du tube -- motif : "
        "v4 non confirmée",
    )
    assert sheet.entries_under_revision() == (entry,)


def test_the_declaration_is_logged_and_the_decision_untouched() -> None:
    decided = _decided()

    entry = declare_under_revision(
        decided, reason="motif", declared_by="Claude", declared_at=_T1
    )

    (event,) = entry.revision_history
    assert (event.kind, event.reason, event.by, event.at) == (
        "declared",
        "motif",
        "Claude",
        _T1,
    )
    assert entry.model_copy(update={"revision_history": ()}) == decided


@pytest.mark.parametrize("reason", ["", "   "])
def test_a_reason_is_mandatory(reason: str) -> None:
    with pytest.raises(ValidationError):
        declare_under_revision(
            _decided(), reason=reason, declared_by="Claude", declared_at=_T1
        )


def test_an_author_is_mandatory() -> None:
    with pytest.raises(ValidationError):
        declare_under_revision(
            _decided(), reason="motif", declared_by=" ", declared_at=_T1
        )


def test_an_open_entry_cannot_be_declared_under_revision() -> None:
    open_entry = PracticeHypothesisEntry(topic="t", status="non_tranche")

    with pytest.raises(ValueError, match="non tranchée"):
        declare_under_revision(
            open_entry, reason="motif", declared_by="Claude", declared_at=_T1
        )


def test_declaring_twice_is_refused() -> None:
    entry = declare_under_revision(
        _decided(), reason="motif", declared_by="Claude", declared_at=_T1
    )

    with pytest.raises(ValueError, match="déjà en révision"):
        declare_under_revision(
            entry, reason="autre", declared_by="Claude", declared_at=_T2
        )


def test_lifting_keeps_the_decision_and_logs_a_second_event() -> None:
    declared = declare_under_revision(
        _decided(), reason="motif", declared_by="Claude", declared_at=_T1
    )

    lifted = lift_revision(
        declared, reason="la décision tient", lifted_by="MM", lifted_at=_T2
    )

    assert lifted.under_revision is False
    assert [e.kind for e in lifted.revision_history] == ["declared", "lifted"]
    assert lifted.revision_history[1].reason == "la décision tient"
    assert lifted.option_retained == "DKT"
    assert _sheet(lifted).generation_blockers() == ()


def test_lifting_an_entry_not_under_revision_is_refused() -> None:
    with pytest.raises(ValueError, match="pas en révision"):
        lift_revision(_decided(), reason="r", lifted_by="MM", lifted_at=_T2)


def test_a_new_decision_closes_the_revision_and_keeps_both_histories() -> None:
    declared = declare_under_revision(
        _decided(), reason="motif", declared_by="Claude", declared_at=_T1
    )

    redecided = record_practice_decision(
        entry=declared,
        option_retained="COQUE_3D",
        justification="épais",
        validity_domain="h/R > 1/20",
        sources=(_SOURCE,),
        discarded_variants=(DiscardedVariant(description="DKT", reason="précision"),),
        decided_by="MM",
        decided_at=_T2,
    )

    assert redecided.under_revision is False
    assert [e.kind for e in redecided.revision_history] == ["declared", "lifted"]
    assert redecided.revision_history[1].at == _T2
    assert redecided.revision_history[1].by == "MM"
    assert [d.option_retained for d in redecided.decision_history] == ["DKT"]
    sheet = apply_decision(_sheet(declared), redecided)
    assert sheet.generation_blockers() == ()


def test_the_log_must_alternate_starting_with_declared() -> None:
    lifted_first = RevisionEvent(kind="lifted", reason="r", by="MM", at=_T1)
    declared = RevisionEvent(kind="declared", reason="r", by="MM", at=_T1)

    with pytest.raises(ValidationError, match="alterner"):
        PracticeHypothesisEntry.model_validate(
            {
                **_decided().model_dump(),
                "revision_history": [lifted_first.model_dump()],
            }
        )
    with pytest.raises(ValidationError, match="alterner"):
        PracticeHypothesisEntry.model_validate(
            {
                **_decided().model_dump(),
                "revision_history": [declared.model_dump(), declared.model_dump()],
            }
        )


def test_an_open_entry_cannot_carry_an_open_revision_when_built_by_hand() -> None:
    declared = RevisionEvent(kind="declared", reason="r", by="MM", at=_T1)

    with pytest.raises(ValidationError, match="non tranchée"):
        PracticeHypothesisEntry(
            topic="t", status="non_tranche", revision_history=(declared,)
        )


def test_the_revision_state_survives_a_json_round_trip() -> None:
    entry = declare_under_revision(
        _decided(), reason="motif", declared_by="Claude", declared_at=_T1
    )
    sheet = _sheet(entry)

    reloaded = HypothesesSheet.model_validate_json(sheet.model_dump_json())

    assert reloaded == sheet
    assert reloaded.generation_blockers() == sheet.generation_blockers()
