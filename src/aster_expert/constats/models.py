"""One Code_Aster finding of the shared base (lot 41, étape 4).

A finding (`constat`) is a fact about Code_Aster -- what a command does, which
keyword to use, a trap established by a trial run -- not a fact about one
structure. It is kept once, in `connaissances/constats_code_aster/<id>.json`,
and every fiche that relies on it cites it by reference
(`aster_expert.agent.hypotheses.FindingReference`).

Every derived field is checked against the entry it summarises, never trusted:
the version is the one every source names, the validation level is the highest
the sources reach (A documentary, B catalogue introspection, C/D execution), the
trial cases are exactly the cases of the execution sources.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    CodeAsterSource,
    DocumentarySource,
    ExecutionSource,
)

ConstatLevel = Literal["A", "B", "C", "D"]

CONSTAT_ID = re.compile(r"^CA-\d{3}$")


class TrialCase(BaseModel):
    """A versioned trial case that established the finding by execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_path: str
    case_sha256: str
    mess_path: str | None


class FindingOrigin(BaseModel):
    """Where the finding was first recorded (the fiche it was extracted from)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project: str
    fiche: str
    point_label: str | None


def source_level(source: CodeAsterSource) -> ConstatLevel:
    if isinstance(source, ExecutionSource):
        return source.validation_level
    if isinstance(source, CatalogueSource):
        return "B"
    assert isinstance(source, DocumentarySource)
    return "A"


def derived_level(entry: CodeAsterHypothesisEntry) -> ConstatLevel:
    """Highest level reached by the sources: an execution source is C or D, a
    catalogue source B (the fact was read from the introspected catalogue), a
    documentary source A."""
    levels = [source_level(s) for s in entry.sources]
    return max(levels) if levels else "A"


def derived_trial_cases(entry: CodeAsterHypothesisEntry) -> tuple[TrialCase, ...]:
    seen: dict[tuple[str, str, str | None], TrialCase] = {}
    for s in entry.sources:
        if isinstance(s, ExecutionSource):
            key = (s.case_path, s.case_sha256, s.mess_path)
            seen.setdefault(
                key,
                TrialCase(
                    case_path=s.case_path,
                    case_sha256=s.case_sha256,
                    mess_path=s.mess_path,
                ),
            )
    return tuple(seen.values())


def entry_text(entry: CodeAsterHypothesisEntry) -> str:
    """The prose of the entry, where identifiers are looked for."""
    parts = [
        entry.topic,
        entry.option_retained or "",
        entry.justification or "",
        entry.notes or "",
        entry.validity_domain or "",
        *entry.options_considered,
    ]
    return "\n".join(parts)


class Constat(BaseModel):
    """One finding of the shared base."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    constat_id: str
    summary: str
    """The trap, or the fact, in one sentence."""
    aster_version: str
    validation_level: ConstatLevel
    commands: tuple[str, ...]
    """Catalogue commands the finding concerns (sources and text)."""
    keywords: tuple[str, ...]
    """Catalogue keywords and keyword values it names (e.g. `LIAISON_SOLIDE`,
    `DKT`)."""
    trial_cases: tuple[TrialCase, ...]
    origin: FindingOrigin
    entry: CodeAsterHypothesisEntry

    @model_validator(mode="after")
    def _coherent(self) -> Constat:
        if not CONSTAT_ID.match(self.constat_id):
            message = f"identifiant de constat {self.constat_id!r} : forme CA-nnn"
            raise ValueError(message)
        summary = self.summary.strip()
        if not summary.endswith(".") or len(summary) > 400:
            message = (
                f"{self.constat_id} : le résumé est une phrase terminée par un "
                "point, de 400 caractères au plus"
            )
            raise ValueError(message)
        if "..." in summary or "…" in summary:
            message = f"{self.constat_id} : pas de points de suspension dans le résumé"
            raise ValueError(message)
        if self.entry.point_label is not None:
            message = (
                f"{self.constat_id} : l'entrée de la base ne porte pas de "
                "point_label (il appartient à la fiche qui la cite)"
            )
            raise ValueError(message)
        if self.entry.status != "tranche":
            message = f"{self.constat_id} : seul un constat tranché entre dans la base"
            raise ValueError(message)
        versions = {s.aster_version for s in self.entry.sources}
        if versions != {self.aster_version}:
            message = (
                f"{self.constat_id} : version {self.aster_version} déclarée, "
                f"versions des sources {sorted(versions)}"
            )
            raise ValueError(message)
        if self.validation_level != derived_level(self.entry):
            message = (
                f"{self.constat_id} : niveau {self.validation_level} déclaré, "
                f"{derived_level(self.entry)} atteint par les sources"
            )
            raise ValueError(message)
        if self.trial_cases != derived_trial_cases(self.entry):
            message = (
                f"{self.constat_id} : les cas d'essai ne sont pas ceux des sources "
                "d'exécution"
            )
            raise ValueError(message)
        return self

    def searchable_text(self) -> str:
        return "\n".join(
            [
                self.summary,
                entry_text(self.entry),
                " ".join(self.commands),
                " ".join(self.keywords),
            ]
        )


__all__ = [
    "CONSTAT_ID",
    "Constat",
    "ConstatLevel",
    "FindingOrigin",
    "TrialCase",
    "derived_level",
    "derived_trial_cases",
    "entry_text",
    "source_level",
]
