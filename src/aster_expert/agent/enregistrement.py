"""Recording of MM's decisions from a structured arbitration file (lot 48 bis).

Audit R6: every lot recorded MM's decisions with its own script (`fiche_lot47.py`,
`decisions_lot44.py`, ...), each holding the topics, the discarded variants and the
notes in Python. `aster-expert fiche enregistrer <projet> <arbitrage.md>` replaces them
with one generic reading of a structured file. Format (UTF-8 Markdown)::

    Source du texte : donnees/sources/arbitrage_xxx.md
    Enregistré le : 2026-10-05T14:00:00-04:00
    Domaine de validité par défaut : <texte>

    ### E13 — Formulations d'éléments et variantes de sensibilité
    > texte de MM, recopié
    > (les lignes citées se joignent par une espace)
    - Écartée : <variante> — <motif>
    - Domaine de validité : <texte>      (facultatif)
    - Note : <texte>                     (facultatif)

The quoted text of every decision must appear, word for word (spaces normalised), in the
file named by `Source du texte` -- the one MM's words were copied into: a decision is
never retyped. `Enregistré le` is the recording time (MM writes neither date nor hour).
Each decision goes through `record_practice_decision` (a re-arbitration keeps the
previous decision in `decision_history`), then `apply_decision` or, for a point the
fiche does not carry yet, `insert_practice_entry`.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.agent.arbitration import (
    apply_decision,
    insert_practice_entry,
    record_practice_decision,
)
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
)

_HEADING = re.compile(r"^### (?P<label>\S+) — (?P<topic>.+?)\s*$")
_HEADER = re.compile(
    r"^(?P<key>Source du texte|Enregistré le|Domaine de validité par défaut)"
    r" : (?P<value>.+?)\s*$"
)
_DISCARDED = re.compile(r"^- Écartée : (?P<description>.+?) — (?P<reason>.+?)\s*$")
_VALIDITY = re.compile(r"^- Domaine de validité : (?P<value>.+?)\s*$")
_NOTE = re.compile(r"^- Note : (?P<value>.+?)\s*$")


class RecordingError(ValueError):
    """The arbitration file is malformed, or a decision cannot be recorded."""


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    topic: str
    text: str
    discarded: tuple[DiscardedVariant, ...]
    validity: str | None = None
    note: str | None = None


class Arbitration(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    """Path (relative to the project directory) of the file MM's text is copied from."""
    recorded_at: datetime
    default_validity: str
    decisions: tuple[Decision, ...]


def _normal(text: str) -> str:
    return " ".join(text.split())


def parse_arbitration(text: str) -> Arbitration:
    header: dict[str, str] = {}
    blocks: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if (m := _HEADING.match(line)) is not None:
            current = {
                "label": m["label"],
                "topic": m["topic"],
                "quote": [],
                "discarded": [],
                "validity": None,
                "note": None,
            }
            blocks.append(current)
        elif current is None:
            if (m := _HEADER.match(line)) is not None:
                header[m["key"]] = m["value"]
        elif line.startswith(">"):
            quote = current["quote"]
            assert isinstance(quote, list)
            quote.append(line[1:].strip())
        elif (m := _DISCARDED.match(line)) is not None:
            discarded = current["discarded"]
            assert isinstance(discarded, list)
            discarded.append(
                DiscardedVariant(description=m["description"], reason=m["reason"])
            )
        elif (m := _VALIDITY.match(line)) is not None:
            current["validity"] = m["value"]
        elif (m := _NOTE.match(line)) is not None:
            current["note"] = m["value"]
        elif line.startswith("- "):
            message = f"ligne {number} : puce inconnue : {line[:60]!r}"
            raise RecordingError(message)
    for key in ("Source du texte", "Enregistré le", "Domaine de validité par défaut"):
        if key not in header:
            message = f"en-tête « {key} : … » absent"
            raise RecordingError(message)
    if not blocks:
        message = "aucune décision (« ### <point> — <sujet> »)"
        raise RecordingError(message)
    decisions = []
    for block in blocks:
        quote = block["quote"]
        discarded = block["discarded"]
        assert isinstance(quote, list)
        assert isinstance(discarded, list)
        if not quote or not discarded:
            message = (
                f"décision {block['label']} : un texte cité (« > ») et au moins une "
                "variante écartée (« - Écartée : … — … ») sont exigés"
            )
            raise RecordingError(message)
        decisions.append(
            Decision(
                label=str(block["label"]),
                topic=str(block["topic"]),
                text=" ".join(quote),
                discarded=tuple(discarded),
                validity=block["validity"]
                if isinstance(block["validity"], str)
                else None,
                note=block["note"] if isinstance(block["note"], str) else None,
            )
        )
    labels = [d.label for d in decisions]
    if len(labels) != len(set(labels)):
        message = "un point est décidé deux fois dans le même fichier"
        raise RecordingError(message)
    try:
        recorded_at = datetime.fromisoformat(header["Enregistré le"])
    except ValueError as exc:
        message = (
            f"« Enregistré le » : date ISO attendue, reçu {header['Enregistré le']!r}"
        )
        raise RecordingError(message) from exc
    if recorded_at.tzinfo is None:
        message = "« Enregistré le » : le fuseau horaire est exigé"
        raise RecordingError(message)
    return Arbitration(
        source=header["Source du texte"],
        recorded_at=recorded_at,
        default_validity=header["Domaine de validité par défaut"],
        decisions=tuple(decisions),
    )


def check_quotes(arbitration: Arbitration, source_text: str) -> None:
    """Every quoted decision appears word for word in the source of MM's text."""
    haystack = _normal(source_text)
    for decision in arbitration.decisions:
        if _normal(decision.text) not in haystack:
            message = (
                f"décision {decision.label} : le texte cité ne figure pas à "
                f"l'identique dans {arbitration.source} (jamais retapé : le recopier)"
            )
            raise RecordingError(message)


def record_decisions(
    sheet: HypothesesSheet, arbitration: Arbitration
) -> tuple[HypothesesSheet, list[str]]:
    """The fiche with every decision of `arbitration` recorded, and what was done."""
    stem = Path(arbitration.source).stem
    reference = f"{stem} ({arbitration.source})"
    source_file = arbitration.source.removeprefix("donnees/")
    done: list[str] = []
    for decision in arbitration.decisions:
        existing = [
            e
            for e in sheet.entries
            if isinstance(e, PracticeHypothesisEntry)
            and e.point_label == decision.label
        ]
        if len(existing) > 1:
            message = f"point {decision.label} : plusieurs entrées pratique, ambigu"
            raise RecordingError(message)
        if existing:
            entry = existing[0]
            if entry.topic != decision.topic:
                message = (
                    f"point {decision.label} : sujet « {decision.topic} » ≠ celui de "
                    f"la fiche « {entry.topic} »"
                )
                raise RecordingError(message)
        else:
            entry = PracticeHypothesisEntry(
                point_label=decision.label,
                topic=decision.topic,
                status="non_tranche",
                notes=decision.note,
            )
        decided = record_practice_decision(
            entry=entry,
            option_retained=decision.text,
            justification=(
                f"Décision {decision.label} de MM, recopiée à l'identique "
                f"({source_file})."
            ),
            validity_domain=decision.validity or arbitration.default_validity,
            sources=(
                PracticeSource(
                    origin="arbitrage_mm",
                    reference=f"{reference}, {decision.label}",
                    date=arbitration.recorded_at.date(),
                ),
            ),
            discarded_variants=decision.discarded,
            decided_by="MM",
            decided_at=arbitration.recorded_at,
        )
        if existing:
            sheet = apply_decision(sheet, decided)
            done.append(
                f"{decision.label} : "
                + ("ré-arbitré" if entry.status == "tranche" else "tranché")
            )
        else:
            sheet = insert_practice_entry(sheet, decided)
            done.append(f"{decision.label} : inséré")
    return sheet, done


__all__ = [
    "Arbitration",
    "Decision",
    "RecordingError",
    "check_quotes",
    "parse_arbitration",
    "record_decisions",
]
