"""Troisième catégorie de la fiche : les choix de l'agent (lot 44, étape 1)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from aster_expert.agent.arbitration import (
    AGENT,
    record_agent_choice,
    record_practice_decision,
    render_decision_sheet,
)
from aster_expert.agent.drafting import SearchAttempt, record_unfounded_point
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)

_T0 = datetime.fromisoformat("2026-10-02T10:00:00-04:00")


def _question(
    point: str = "9", topic: str = "Repère global"
) -> PracticeHypothesisEntry:
    return record_unfounded_point(
        point_label=point,
        topic=topic,
        searches=(SearchAttempt(profile="methode", query="repère", outcome="rien"),),
        options_considered=("Origine au coin", "Origine au centre"),
    )


def _choice(**overrides: object) -> PracticeHypothesisEntry:
    arguments: dict[str, object] = {
        "entry": _question(),
        "domain": "repere",
        "verified_by": ("CTL-006", "REF-014"),
        "option_retained": "Origine au coin, X selon la grande portée.",
        "justification": "Repère de la série de Navier.",
        "validity_domain": "Dalle rectangulaire.",
        "discarded_variants": (
            DiscardedVariant(description="Origine au centre", reason="Navier au coin"),
        ),
        "reference": "rejeu lot 44",
        "decided_at": _T0,
    }
    arguments.update(overrides)
    return record_agent_choice(**arguments)  # type: ignore[arg-type]


def test_agent_choice_is_decided_and_does_not_block() -> None:
    entry = _choice()
    assert entry.status == "tranche"
    assert entry.is_agent_choice
    assert entry.decided_by == AGENT
    sheet = HypothesesSheet(
        project_name="P",
        structure_description="d",
        created_at=_T0,
        entries=(entry,),
        group_naming=(
            MeshGroupNaming(
                group_name="DALLE",
                kind="maille",
                description="Surface.",
                status="choix_agent",
                point_label="9",
                verified_by=("CTL-008", "CTL-009"),
            ),
        ),
    )
    assert sheet.generation_blockers() == ()
    assert sheet.agent_choices() == (entry,)
    assert len(sheet.agent_group_names()) == 1


def test_agent_choice_without_verifier_is_refused() -> None:
    with pytest.raises(ValidationError, match="désignés nommément"):
        _choice(verified_by=())
    with pytest.raises(ValidationError, match="désignés nommément"):
        PracticeSource(
            origin="choix_agent", reference="x", date=_T0.date(), domain="repere"
        )


def test_agent_choice_with_malformed_verifier_is_refused() -> None:
    with pytest.raises(ValidationError, match="mal nommés"):
        _choice(verified_by=("contrôle d'équilibre",))


def test_agent_choice_outside_the_partition_rule_is_refused() -> None:
    # Matériaux, actions, combinaisons... n'ont pas de domaine : refusés.
    with pytest.raises(ValidationError):
        _choice(domain="materiaux")
    with pytest.raises(ValidationError, match="domaine"):
        PracticeSource(
            origin="choix_agent",
            reference="x",
            date=_T0.date(),
            verified_by=("CTL-005",),
        )


def test_agent_fields_are_reserved_to_choix_agent() -> None:
    with pytest.raises(ValidationError, match="choix_agent"):
        PracticeSource(
            origin="arbitrage_mm",
            reference="x",
            date=_T0.date(),
            verified_by=("CTL-005",),
        )
    with pytest.raises(ValidationError, match="choix_agent"):
        MeshGroupNaming(
            group_name="X", kind="noeud", description="d", verified_by=("CTL-008",)
        )


def test_group_name_choice_without_verifier_is_refused() -> None:
    with pytest.raises(ValidationError, match="désignés nommément"):
        MeshGroupNaming(
            group_name="X", kind="noeud", description="d", status="choix_agent"
        )


def test_agent_choice_cannot_mix_origins() -> None:
    agent = PracticeSource(
        origin="choix_agent",
        reference="x",
        date=_T0.date(),
        domain="repere",
        verified_by=("CTL-006",),
    )
    mm = PracticeSource(origin="arbitrage_mm", reference="y", date=_T0.date())
    with pytest.raises(ValidationError, match="ne mêle pas"):
        record_practice_decision(
            entry=_question(),
            option_retained="o",
            justification="j",
            validity_domain="v",
            sources=(agent, mm),
            discarded_variants=(DiscardedVariant(description="a", reason="b"),),
            decided_by=AGENT,
            decided_at=_T0,
        )


def test_mm_replaces_an_agent_choice_and_keeps_it_in_history() -> None:
    choice = _choice()
    replaced = record_practice_decision(
        entry=choice,
        option_retained="Origine au centre.",
        justification="Choix de MM.",
        validity_domain="Dalle.",
        sources=(
            PracticeSource(origin="arbitrage_mm", reference="arb", date=_T0.date()),
        ),
        discarded_variants=(DiscardedVariant(description="Coin", reason="MM"),),
        decided_by="MM",
        decided_at=_T0,
    )
    assert not replaced.is_agent_choice
    assert replaced.decision_history[-1].decided_by == AGENT
    assert replaced.decision_history[-1].sources[0].verified_by == (
        "CTL-006",
        "REF-014",
    )


def test_decision_sheet_lists_agent_choices_in_a_separate_section() -> None:
    sheet = HypothesesSheet(
        project_name="P",
        structure_description="d",
        created_at=_T0,
        entries=(_question("4", "Charges"), _choice()),
        group_naming=(
            MeshGroupNaming(
                group_name="CENTRE",
                kind="noeud",
                description="Nœud central.",
                status="choix_agent",
                point_label="9",
                verified_by=("CTL-008",),
            ),
        ),
    )
    text = render_decision_sheet(sheet)
    head, _, agent = text.partition("## Choix de modélisation de l'agent")
    assert "Charges" in head and "Repère global" not in head
    assert "Repère global" in agent
    assert "Vérifié par : CTL-006, REF-014." in agent
    assert "`CENTRE`" in agent


def test_serialization_of_ordinary_entries_is_unchanged() -> None:
    source = PracticeSource(origin="arbitrage_mm", reference="y", date=_T0.date())
    assert set(source.model_dump(mode="json")) == {"origin", "reference", "date"}
    group = MeshGroupNaming(group_name="X", kind="noeud", description="d")
    assert "verified_by" not in group.model_dump(mode="json")
    choice = _choice()
    dumped = choice.model_dump(mode="json")
    assert PracticeHypothesisEntry.model_validate(dumped) == choice
