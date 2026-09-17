"""Data models for the retrieval evaluation set (lot 5, docs/corpus.md §8).

`EvaluationQuestion` matches the schema actually produced for
`data/evaluations/questions.jsonl`, a superset of the sketch in
docs/corpus.md §8: `source_question` (the broad user question a bounded
question was decomposed from, `data/evaluations/cas_usage.md`),
`verified_by` (what grounds `expected_documents` : document title, section,
source path — never a keyword match alone) and `answer_outside_corpus`
(the expected answer lives outside the documentary corpus, e.g. in the
official test cases or the catalogue itself) are amendments made explicit
here rather than left implicit in a raw dict.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EvaluationQuestion(BaseModel):
    """One reference question of the lot 5 evaluation set.

    `expected_documents` empty means the question is unresolved (`note`
    must then explain what was searched and why no document was
    established) — never a guess forced into the field to avoid an empty
    result (CLAUDE.md, "Ne jamais confondre pertinence documentaire...").
    """

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    domain: str
    origin: str
    source_question: str | None = None
    version: str | None = None
    expected_documents: tuple[str, ...] = ()
    expected_commands: tuple[str, ...] = ()
    verified_by: str | None = None
    note: str | None = None
    answer_outside_corpus: bool = False
