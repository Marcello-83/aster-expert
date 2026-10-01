"""Practice precedents (lot 42, étape 1, « Règle sur les précédents »).

A precedent is a decision MM took in a project, with its justification and its
domain of validity. It is never applied automatically to another project:
`propose_precedent` builds a *non-arbitrated* `pratique` entry (status
`non_tranche`, hence a generation blocker) that names the precedent among the
options and in its notes, plus the `PracticeSource` of origin
`precedent_projet` that MM may cite when arbitrating it
(`aster_expert.agent.arbitration.record_practice_decision`). Only that
arbitration can turn the proposal into a decision.
"""

from __future__ import annotations

import datetime as dt

from aster_expert.agent.hypotheses import PracticeHypothesisEntry, PracticeSource
from aster_expert.connaissances.modeles import DecisionEvidence, Precedent


def precedent_from_entry(
    entry: PracticeHypothesisEntry,
    *,
    precedent_id: str,
    title: str,
    summary: str,
    origin_project: str,
    fiche: str,
    recorded_on: dt.date,
) -> Precedent:
    """A precedent from an arbitrated `pratique` entry of a fiche; every field
    is copied, none is rewritten."""
    if entry.status != "tranche" or entry.point_label is None:
        message = (
            f"{precedent_id} : seule une entrée pratique tranchée fonde un précédent"
        )
        raise ValueError(message)
    assert entry.decided_by is not None and entry.decided_at is not None
    return Precedent(
        id=precedent_id,
        title=title,
        summary=summary,
        origin_project=origin_project,
        date=recorded_on,
        validation_level="A",
        status="observé",
        sources=(
            DecisionEvidence(
                fiche=fiche,
                point_label=entry.point_label,
                decided_by=entry.decided_by,
                decided_at=entry.decided_at,
            ),
        ),
        fiche=fiche,
        point_label=entry.point_label,
        topic=entry.topic,
        option_retained=entry.option_retained or "",
        justification=entry.justification or "",
        validity_domain=entry.validity_domain or "",
        discarded_variants=tuple(
            f"{v.description} — écartée : {v.reason}" for v in entry.discarded_variants
        ),
        decided_by=entry.decided_by,
        decided_at=entry.decided_at,
        superseded_decisions=len(entry.decision_history),
    )


def precedent_source(precedent: Precedent) -> PracticeSource:
    """The source MM may cite if the arbitration retains the precedent."""
    return PracticeSource(
        origin="precedent_projet",
        reference=(
            f"{precedent.id} — {precedent.origin_project}, point "
            f"{precedent.point_label} ({precedent.fiche}), décidé par "
            f"{precedent.decided_by} le {precedent.decided_at.date().isoformat()}"
        ),
    )


def propose_precedent(
    precedent: Precedent, *, point_label: str, topic: str | None = None
) -> tuple[PracticeHypothesisEntry, PracticeSource]:
    """A proposal for a new fiche: a `non_tranche` entry, never a decision."""
    entry = PracticeHypothesisEntry(
        point_label=point_label,
        topic=topic or precedent.topic,
        options_considered=(
            f"Précédent {precedent.id} ({precedent.origin_project}) : "
            f"{precedent.option_retained}",
        ),
        notes=(
            f"Précédent proposé, non appliqué : {precedent.id}, origine "
            "precedent_projet. Domaine de validité du précédent : "
            f"{precedent.validity_domain} — à confronter au présent ouvrage et à "
            "arbitrer par MM (record_practice_decision)."
        ),
        status="non_tranche",
    )
    return entry, precedent_source(precedent)


__all__ = ["precedent_from_entry", "precedent_source", "propose_precedent"]
