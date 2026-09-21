"""Assisted drafting of a `HypothesesSheet` (lot 14b).

Lot 14 built the schema by transcribing, by hand, a fiche produced during a
real usage trial (`data/examples/hypotheses_combiwall_reference.json`) and
left the transcription script itself out of the repository -- "un script
de transcription, non versionné". This module makes the *procedure* that
trial actually followed reproducible: search under the right profile, read
the section in full, confront the catalogue when a Code_Aster identifier is
at stake, then record what was found (`.claude/skills/hypotheses-drafting/
SKILL.md` walks this loop step by step, driven by the trame in
`load_default_trame`).

**This module never decides anything.** Choosing what to search, reading
the result, and writing `option_retained`/`justification` in French prose
is judgment -- an LLM agent's job, using the `aster-expert` MCP tools
directly, never this module's. What this module owns is the *write path*:
the only two functions ("N3, la barrière couvre aussi le chemin
d'écriture") a drafting session is meant to call once it has decided what
an entry should say. Each is deliberately narrower than
`CodeAsterHypothesisEntry`/`PracticeHypothesisEntry` themselves:

- `record_code_aster_finding` has no `status` parameter at all -- it always
  builds a `tranche` entry, delegating the N1 excerpt discipline to
  `CodeAsterHypothesisEntry` itself, so calling it with an unread
  `DocumentarySource` still raises. A point identified but not yet read
  is not recorded through this function (the drafting procedure is
  expected to read before writing, per N2 -- there is no "partial" shape
  reachable from here).
- `record_unfounded_point` has no `option_retained`/`justification`/
  `sources` parameter at all -- it cannot build anything but a `pratique`/
  `non_tranche` entry, however it is called. A corpus gap can never
  silently become a decision through this module; only an engineer,
  reviewing the sheet afterwards, makes that call (CLAUDE.md: la fiche
  produite est un projet, jamais une fiche validée).

A lot 14 draft of the transcription script fabricated a `source_path` and
even an invented section for one citation to fill a gap -- caught by
reviewing the JSON against the specimen's own text, not by a test. That is
exactly the failure `record_unfounded_point` makes structurally
unreachable: there is no field on it a fabricated value could land in.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    CodeAsterSource,
    DiscardedVariant,
    PracticeHypothesisEntry,
)
from aster_expert.retrieval.query_profiles import QueryProfile


class TrameTopic(BaseModel):
    """One rubric of a drafting trame (N4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    heading: str
    prompt: str
    profile_hint: QueryProfile | None = None


class Trame(BaseModel):
    """An ordered list of rubrics to instruct when drafting a fiche (N4).

    Configuration data, never hard-coded Python: `load_default_trame` only
    reads `data/config/hypotheses_trame_defaut.json` -- a project adapting
    the rubric order, or adding/removing one, edits that file, not this
    module.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str = ""
    topics: tuple[TrameTopic, ...] = ()


def default_trame_path(project_root: Path) -> Path:
    return project_root / "data" / "config" / "hypotheses_trame_defaut.json"


def load_trame(path: Path) -> Trame:
    return Trame.model_validate_json(path.read_text(encoding="utf-8"))


class SearchAttempt(BaseModel):
    """One `search_codeaster_docs` call tried while instructing a topic,
    kept whether or not it found anything -- the trace N2 requires: "avec
    la trace de ce qui a été cherché et sous quel profil".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: QueryProfile
    query: str
    outcome: str = Field(
        description=(
            "What the search/reading turned up, in the drafter's own words "
            "-- 'aucun résultat pertinent', or a one-line summary of a "
            "result that was found but did not settle the point."
        )
    )


def _format_search_trace(searches: tuple[SearchAttempt, ...]) -> str:
    lines = [f'Cherché sous {s.profile} ("{s.query}") : {s.outcome}.' for s in searches]
    return " ".join(lines)


def record_code_aster_finding(
    *,
    topic: str,
    sources: tuple[CodeAsterSource, ...],
    option_retained: str,
    justification: str,
    point_label: str | None = None,
    options_considered: tuple[str, ...] = (),
    discarded_variants: tuple[DiscardedVariant, ...] = (),
    notes: str | None = None,
) -> CodeAsterHypothesisEntry:
    """Record a point the corpus/catalogue actually founds.

    Always `nature="code_aster"`, `status="tranche"` -- there is no
    `status` parameter to override that. `CodeAsterHypothesisEntry` itself
    still enforces N1 (a real excerpt among `sources`) and the shared
    decision-fields check: a call missing either raises
    `pydantic.ValidationError`, exactly as if it had been built by hand.
    """
    return CodeAsterHypothesisEntry(
        point_label=point_label,
        topic=topic,
        options_considered=options_considered,
        option_retained=option_retained,
        justification=justification,
        discarded_variants=discarded_variants,
        notes=notes,
        sources=sources,
        status="tranche",
    )


def record_unfounded_point(
    *,
    topic: str,
    searches: tuple[SearchAttempt, ...],
    point_label: str | None = None,
    deduction: str | None = None,
    options_considered: tuple[str, ...] = (),
) -> PracticeHypothesisEntry:
    """Record a point the corpus does not found, with the trace of what was
    searched (N2/N3). Always `nature="pratique"`, `status="non_tranche"` --
    there is no `option_retained`/`justification`/`sources` parameter here
    at all, so this function cannot produce a decided entry regardless of
    what it is called with; turning this into a decision is the engineer's
    job, reviewing the sheet afterwards, never this drafting session's.

    `searches` must be non-empty: "jamais une entrée vide sans explication"
    (N2) is enforced here, not left to the caller's discipline.
    `deduction` is free text for a project-specific inference that
    connects catalogue facts to this situation without a document stating
    the conclusion itself (M5 correction 4) -- still not a decision, and
    still landing in `notes`, never in a field that would look like one.
    `options_considered` (lot 21) lists the options the question opposes,
    so that a later decision keeps them; it is a list of candidates, not a
    choice, and does not make the entry any less `non_tranche`.
    """
    if not searches:
        message = (
            "jamais une entrée vide sans explication : au moins une "
            "recherche (profil, requête, résultat) doit être tracée"
        )
        raise ValueError(message)
    notes = _format_search_trace(searches)
    if deduction:
        notes = f"{notes} Déduction : {deduction}"
    return PracticeHypothesisEntry(
        point_label=point_label,
        topic=topic,
        options_considered=options_considered,
        notes=notes,
        status="non_tranche",
    )


__all__: list[str] = [
    "SearchAttempt",
    "Trame",
    "TrameTopic",
    "default_trame_path",
    "load_trame",
    "record_code_aster_finding",
    "record_unfounded_point",
]
