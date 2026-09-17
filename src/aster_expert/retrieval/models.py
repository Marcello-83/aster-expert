"""Data models for the retrieval evaluation set (lot 5, docs/corpus.md §8).

`EvaluationQuestion` matches the schema actually produced for
`data/evaluations/questions.jsonl`, a superset of the sketch in
docs/corpus.md §8: `source_question` (the broad user question a bounded
question was decomposed from, `data/evaluations/cas_usage.md`),
`verified_by` (what grounds `required_documents`/`supporting_documents` :
document title, section, source path — never a keyword match alone) and
`answer_outside_corpus` (the expected answer lives outside the documentary
corpus, e.g. in the official test cases or the catalogue itself) are
amendments made explicit here rather than left implicit in a raw dict.

Lot 5b (normalisation, external-review triage, docs/development-plan.md)
amended the schema further: `version` (never `null` any more — the corpus
covers exactly one documentary revision, so every gold answer records
which one it was checked against), the `expected_documents`/`supporting_documents`
split, `answerability` and `gold_confidence`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VersionInfo(BaseModel):
    """Version state a gold answer was verified against.

    `compatibility_status` is free text, not a boolean, because the
    solver/documentation correspondence itself is only partially checked
    (config/versions.yaml: tag correspondence confirmed by
    `git ls-remote --tags`, no cross-changelog confirmation) — CLAUDE.md
    forbids declaring "vérifié" anything that was not.
    """

    model_config = ConfigDict(frozen=True)

    solver: str
    documentation_revision: str
    compatibility_status: str


class EvaluationQuestion(BaseModel):
    """One reference question of the lot 5/5b evaluation set.

    `required_documents` empty means the question is unresolved (`note`
    must then explain what was searched and why no document was
    established) — never a guess forced into the field to avoid an empty
    result (CLAUDE.md, "Ne jamais confondre pertinence documentaire...").
    `supporting_documents` holds documents useful to a complete answer but
    whose absence would not make the answer wrong (docs/corpus.md §8) —
    never scored by `evaluate_retrieval`, which reads `required_documents`
    only.

    `answerability` distinguishes an answer present as-is in the corpus
    (`explicit`), one deduced from documented facts without being stated as
    such (`inferable`), one only partly covered by what the corpus
    establishes (`partial`), and a question with no official answer
    established at all (`absent` — `required_documents` is then empty, the
    normal outcome for eval-005/eval-007, not a masked failure).

    `gold_confidence` reflects the solidity of `verified_by` alone, not a
    new investigation: `high` for a direct, specific citation (file,
    section, quoted text) of every retained document; `medium` when the
    answer rests on a generic documented mechanism applied to a case the
    corpus never names, or when a required document is covered only by
    document-level citation rather than by content-level citation
    (docs/development-plan.md, lot 5b, X1); `provisional` for an unresolved
    question, since a negative "no document establishes this" finding is a
    search-time observation, not a durable fact — new corpus content or
    further reading could revise it.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    domain: str
    origin: str
    source_question: str | None = None
    version: VersionInfo
    required_documents: tuple[str, ...] = ()
    supporting_documents: tuple[str, ...] = ()
    expected_commands: tuple[str, ...] = ()
    verified_by: str | None = None
    note: str | None = None
    answerability: Literal["explicit", "inferable", "partial", "absent"]
    gold_confidence: Literal["high", "medium", "provisional"]
    answer_outside_corpus: bool = False
