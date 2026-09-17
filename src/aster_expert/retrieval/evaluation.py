"""Recall/precision measurement on the lot 5 evaluation set.

Usable before any index or search engine exists (docs/development-plan.md,
lot 5): the only input this module needs is a ranked list of document ids
per question, supplied by whatever means (hand-written for a test, or later
`aster-expert search`). It never reads the corpus or the catalogue itself.

A question with an empty `required_documents` is unresolved (lot 5
instruction: "une question non résolue est un résultat, pas un échec à
masquer") and is excluded from every aggregate metric, never scored as a
failure. `supporting_documents` (lot 5b) is never read here: only
`required_documents` — the noyau without which the answer is wrong — is
scored.

Several documents can legitimately answer one question (docs/corpus.md §8);
`hit` below is intentionally "at least one expected document retrieved",
matching the lot 5 instruction ("la métrique sera 'au moins un document
attendu retrouvé', pas 'le bon document unique'"). Classic recall@k and
precision@k are also reported per query, since a question can carry more
than one expected document and both figures are informative together.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.retrieval.models import EvaluationQuestion


class RankedResult(BaseModel):
    """One ranked list of document ids returned for one question."""

    model_config = ConfigDict(frozen=True)

    id: str
    ranked_documents: tuple[str, ...] = ()


class QueryScore(BaseModel):
    """Recall/precision for one evaluated question at a fixed `k`."""

    model_config = ConfigDict(frozen=True)

    id: str
    k: int
    required_documents: tuple[str, ...]
    retrieved_at_k: tuple[str, ...]
    hit: bool
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float


class EvaluationReport(BaseModel):
    """Aggregate result of `evaluate_retrieval` over the whole question set."""

    model_config = ConfigDict(frozen=True)

    k: int
    n_questions_total: int
    n_questions_evaluated: int
    n_questions_excluded_unresolved: int
    n_questions_missing_result: int
    hit_rate_at_k: float
    mean_precision_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    scores: tuple[QueryScore, ...]


def _score_one(
    question: EvaluationQuestion, ranked: tuple[str, ...], k: int
) -> QueryScore:
    expected = set(question.required_documents)
    retrieved_at_k = ranked[:k]
    hits_at_k = [doc for doc in retrieved_at_k if doc in expected]

    reciprocal_rank = 0.0
    for rank, doc in enumerate(ranked, start=1):
        if doc in expected:
            reciprocal_rank = 1.0 / rank
            break

    precision = len(hits_at_k) / k if k else 0.0
    recall = len(set(hits_at_k)) / len(expected) if expected else 0.0

    return QueryScore(
        id=question.id,
        k=k,
        required_documents=question.required_documents,
        retrieved_at_k=retrieved_at_k,
        hit=bool(hits_at_k),
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
    )


def evaluate_retrieval(
    questions: list[EvaluationQuestion],
    results: dict[str, tuple[str, ...]],
    *,
    k: int,
) -> EvaluationReport:
    """Score `results` (question id -> ranked document ids) against `questions`.

    A question with `required_documents == ()` is excluded (unresolved, not
    a failure). A resolved question absent from `results` is scored as a
    complete miss (empty ranked list) and counted separately in
    `n_questions_missing_result`, never silently dropped.
    """
    if k <= 0:
        raise ValueError(f"k doit être strictement positif, reçu {k}")

    scores: list[QueryScore] = []
    n_excluded = 0
    n_missing_result = 0

    for question in questions:
        if not question.required_documents:
            n_excluded += 1
            continue
        if question.id not in results:
            n_missing_result += 1
        ranked = results.get(question.id, ())
        scores.append(_score_one(question, ranked, k))

    n_evaluated = len(scores)
    if n_evaluated:
        hit_rate = sum(1 for s in scores if s.hit) / n_evaluated
        mean_precision = sum(s.precision_at_k for s in scores) / n_evaluated
        mean_recall = sum(s.recall_at_k for s in scores) / n_evaluated
        mean_reciprocal_rank = sum(s.reciprocal_rank for s in scores) / n_evaluated
    else:
        hit_rate = mean_precision = mean_recall = mean_reciprocal_rank = 0.0

    return EvaluationReport(
        k=k,
        n_questions_total=len(questions),
        n_questions_evaluated=n_evaluated,
        n_questions_excluded_unresolved=n_excluded,
        n_questions_missing_result=n_missing_result,
        hit_rate_at_k=hit_rate,
        mean_precision_at_k=mean_precision,
        mean_recall_at_k=mean_recall,
        mean_reciprocal_rank=mean_reciprocal_rank,
        scores=tuple(scores),
    )


def load_questions(path: Path) -> list[EvaluationQuestion]:
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        questions.append(EvaluationQuestion.model_validate_json(line))
    return questions


def load_ranked_results(path: Path) -> dict[str, tuple[str, ...]]:
    """Read a JSONL file of `RankedResult` entries into an id -> ranking map."""
    results: dict[str, tuple[str, ...]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = RankedResult.model_validate_json(line)
        results[entry.id] = entry.ranked_documents
    return results


class QuestionSetSummary(BaseModel):
    """Descriptive counts over `data/evaluations/questions.jsonl` itself,
    independent of any retrieval run (compte rendu de fin de lot)."""

    model_config = ConfigDict(frozen=True)

    total: int
    resolved: int
    unresolved: int
    unresolved_ids: tuple[str, ...]
    by_domain: dict[str, dict[str, int]]
    document_family_counts: dict[str, int]
    outside_corpus_ids: tuple[str, ...]


class BucketScore(BaseModel):
    """Aggregate hit/recall/MRR over one bucket of questions (lot 7, D5)."""

    model_config = ConfigDict(frozen=True)

    n_questions: int
    hit_rate: float
    mean_recall: float
    mean_reciprocal_rank: float


def ventilate(
    scores: tuple[QueryScore, ...],
    questions_by_id: dict[str, EvaluationQuestion],
    key_fn: Callable[[EvaluationQuestion], list[str]],
) -> dict[str, BucketScore]:
    """Group `scores` by `key_fn(question)` and aggregate hit/recall/MRR per key.

    A question can contribute to several buckets at once (`key_fn` returns a
    list, not a single key) — the same multi-membership the lot 5 compte
    rendu already used for "répartition des documents attendus par
    famille" when a question names documents from more than one family,
    never forced into a single arbitrary bucket.
    """
    buckets: dict[str, list[QueryScore]] = defaultdict(list)
    for score in scores:
        question = questions_by_id[score.id]
        for key in key_fn(question):
            buckets[key].append(score)

    result: dict[str, BucketScore] = {}
    for key, bucket_scores in buckets.items():
        n = len(bucket_scores)
        result[key] = BucketScore(
            n_questions=n,
            hit_rate=sum(1 for s in bucket_scores if s.hit) / n,
            mean_recall=sum(s.recall_at_k for s in bucket_scores) / n,
            mean_reciprocal_rank=sum(s.reciprocal_rank for s in bucket_scores) / n,
        )
    return result


def ventilate_by_domain(
    scores: tuple[QueryScore, ...], questions_by_id: dict[str, EvaluationQuestion]
) -> dict[str, BucketScore]:
    return ventilate(scores, questions_by_id, lambda q: [q.domain])


def ventilate_by_answerability(
    scores: tuple[QueryScore, ...], questions_by_id: dict[str, EvaluationQuestion]
) -> dict[str, BucketScore]:
    return ventilate(scores, questions_by_id, lambda q: [q.answerability])


def ventilate_by_family(
    scores: tuple[QueryScore, ...], questions_by_id: dict[str, EvaluationQuestion]
) -> dict[str, BucketScore]:
    return ventilate(
        scores,
        questions_by_id,
        lambda q: sorted({_document_family(d) for d in q.required_documents}),
    )


def list_failures(report: EvaluationReport) -> tuple[QueryScore, ...]:
    """Every evaluated question that missed all required documents at `report.k`."""
    return tuple(score for score in report.scores if not score.hit)


def _document_family(document_id: str) -> str:
    """Group a document id to the family level the lot 5 report asks for
    (docs/development-plan.md, lot 5 : "répartition des documents attendus
    par famille (U2, U4, U7, R, V, D)"). The `U` family alone is kept split
    by sub-family (`U2`/`U4`/`U7` name distinct manual series with distinct
    content, docs/corpus.md §3); `R`/`V`/`D` are collapsed to their single
    letter, since the report groups them at that coarser level."""
    prefix = document_id.split(".", 1)[0]
    if prefix.startswith("U"):
        return prefix
    return prefix[0] if prefix else prefix


def summarize_question_set(questions: list[EvaluationQuestion]) -> QuestionSetSummary:
    by_domain: dict[str, dict[str, int]] = {}
    family_counts: Counter[str] = Counter()
    unresolved_ids: list[str] = []
    outside_corpus_ids: list[str] = []

    for question in questions:
        bucket = by_domain.setdefault(question.domain, {"resolved": 0, "unresolved": 0})
        if question.required_documents:
            bucket["resolved"] += 1
            for document_id in question.required_documents:
                family_counts[_document_family(document_id)] += 1
        else:
            bucket["unresolved"] += 1
            unresolved_ids.append(question.id)
        if question.answer_outside_corpus:
            outside_corpus_ids.append(question.id)

    resolved = sum(1 for q in questions if q.required_documents)
    return QuestionSetSummary(
        total=len(questions),
        resolved=resolved,
        unresolved=len(questions) - resolved,
        unresolved_ids=tuple(unresolved_ids),
        by_domain=by_domain,
        document_family_counts=dict(family_counts),
        outside_corpus_ids=tuple(outside_corpus_ids),
    )
