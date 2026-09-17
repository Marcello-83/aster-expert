"""Banc de mesure du lot 7 (D5/D6) : hit@k/recall@k/MRR, ventilations,
échecs nominatifs à k=10, et comparaison honnête à la recherche naïve.

`aster_expert.retrieval.evaluation` reste générique (une liste de résultats
classés, jamais le corpus lui-même) : ce module est la seule couche qui sait
comment produire cette liste à partir d'un index BM25 réel, et comment la
réduire à un classement de **documents** (le niveau que `required_documents`
score, docs/corpus.md §8) à partir d'un classement de **fragments** — un
fragment n'est jamais l'unité notée, seulement l'unité indexée.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import bm25s
from pydantic import BaseModel, ConfigDict

from aster_expert.indexing.bm25_index import search
from aster_expert.indexing.models import SearchHit
from aster_expert.indexing.naive_search import naive_command_search
from aster_expert.retrieval.evaluation import (
    BucketScore,
    EvaluationReport,
    evaluate_retrieval,
    list_failures,
    ventilate_by_answerability,
    ventilate_by_domain,
    ventilate_by_family,
)
from aster_expert.retrieval.models import EvaluationQuestion
from aster_expert.retrieval.source_priority import (
    SourcePriorityMode,
    hard_filter_search,
    soft_reweight_search,
)

# Fragments récupérés par requête avant réduction au niveau document : un
# classement de fragments dédupliqué en documents peut être plus court que
# le nombre de fragments demandé (plusieurs fragments d'un même document
# occupant les premiers rangs, surtout en granularité `by_subsection`) — une
# marge large garantit qu'un classement à k=20 documents distincts reste
# atteignable quand le corpus le permet, jamais tronqué artificiellement par
# une profondeur de recherche insuffisante.
_FRAGMENT_SEARCH_K = 150

RankFn = Callable[[EvaluationQuestion], tuple[str, ...]]


def _dedupe_to_documents(hits: list[SearchHit]) -> tuple[str, ...]:
    """Fragment hits, order-preserved, to a document ranking (first fragment
    of a document fixes its rank; later fragments of the same document are
    dropped, never re-scored or merged)."""
    ranked: list[str] = []
    for hit in hits:
        if hit.document_id not in ranked:
            ranked.append(hit.document_id)
    return tuple(ranked)


def rank_documents_for_question(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    question: EvaluationQuestion,
    *,
    version: str | None,
) -> tuple[str, ...]:
    """One question's fragment hits, deduplicated to a document ranking.

    Ranking unchanged from lot 7 (lot 7b instruction E1: "mesure le gain de
    E1 seul, à classement inchangé") — the only thing E1 can change is which
    index this is called against (`corpus`/`retriever` from the E1-enriched
    index, or the lot 7 reference index), never this function's own logic.
    """
    hits = search(
        retriever, corpus, question.question, k=_FRAGMENT_SEARCH_K, version=version
    )
    return _dedupe_to_documents(hits)


def rank_documents_with_source_priority(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    question: EvaluationQuestion,
    *,
    version: str | None,
    priority_families: tuple[str, ...],
    mode: SourcePriorityMode,
) -> tuple[str, ...]:
    """E2 : one question's fragment hits under the hard or soft priority variant."""
    if mode == "hard":
        hits = hard_filter_search(
            retriever,
            corpus,
            question.question,
            k=_FRAGMENT_SEARCH_K,
            priority_families=priority_families,
            version=version,
        )
    else:
        hits = soft_reweight_search(
            retriever,
            corpus,
            question.question,
            k=_FRAGMENT_SEARCH_K,
            priority_families=priority_families,
            version=version,
        )
    return _dedupe_to_documents(hits)


class FailureCase(BaseModel):
    """One resolved question that missed every required document at k=10."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    domain: str
    required_documents: tuple[str, ...]
    retrieved_at_k: tuple[str, ...]


class GranularityBenchReport(BaseModel):
    """Full lot 7 D5 measurement for one fragment granularity."""

    model_config = ConfigDict(frozen=True)

    granularity: str
    fragment_count: int
    n_questions_evaluated: int
    n_questions_excluded_unresolved: int
    reports_by_k: dict[int, EvaluationReport]
    ventilation_by_domain: dict[int, dict[str, BucketScore]]
    ventilation_by_family: dict[int, dict[str, BucketScore]]
    ventilation_by_answerability: dict[int, dict[str, BucketScore]]
    failures_at_k10: tuple[FailureCase, ...]


def run_granularity_bench(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    questions: list[EvaluationQuestion],
    *,
    granularity: str,
    fragment_count: int,
    version: str | None,
    k_values: tuple[int, ...] = (5, 10, 20),
    rank_fn: RankFn | None = None,
) -> GranularityBenchReport:
    """`rank_fn` (lot 7b) : one question -> its document ranking.

    Defaults to `rank_documents_for_question` against `retriever`/`corpus`
    (lot 7 behaviour, unchanged) when omitted. A caller measuring an E2
    variant instead passes a closure over `rank_documents_with_source_
    priority` — this function's own aggregation/ventilation/failure-listing
    logic never has to know which variant produced the ranking.
    """
    questions_by_id = {q.id: q for q in questions}
    resolved_rank_fn: RankFn = rank_fn or (
        lambda q: rank_documents_for_question(retriever, corpus, q, version=version)
    )
    results = {q.id: resolved_rank_fn(q) for q in questions if q.required_documents}

    reports_by_k = {k: evaluate_retrieval(questions, results, k=k) for k in k_values}
    reference_report = (
        reports_by_k[10] if 10 in reports_by_k else next(iter(reports_by_k.values()))
    )

    failures = tuple(
        FailureCase(
            id=score.id,
            question=questions_by_id[score.id].question,
            domain=questions_by_id[score.id].domain,
            required_documents=score.required_documents,
            retrieved_at_k=score.retrieved_at_k,
        )
        for score in list_failures(reports_by_k.get(10, reference_report))
    )

    return GranularityBenchReport(
        granularity=granularity,
        fragment_count=fragment_count,
        n_questions_evaluated=reference_report.n_questions_evaluated,
        n_questions_excluded_unresolved=reference_report.n_questions_excluded_unresolved,
        reports_by_k=reports_by_k,
        ventilation_by_domain={
            k: ventilate_by_domain(r.scores, questions_by_id)
            for k, r in reports_by_k.items()
        },
        ventilation_by_family={
            k: ventilate_by_family(r.scores, questions_by_id)
            for k, r in reports_by_k.items()
        },
        ventilation_by_answerability={
            k: ventilate_by_answerability(r.scores, questions_by_id)
            for k, r in reports_by_k.items()
        },
        failures_at_k10=failures,
    )


class NaiveBaselineReport(BaseModel):
    """Result of the D6 naive command-name baseline, and BM25 on the same subset."""

    model_config = ConfigDict(frozen=True)

    n_questions_with_expected_commands: int
    naive_reports_by_k: dict[int, EvaluationReport]
    bm25_reports_by_k: dict[int, EvaluationReport]


def run_naive_baseline_comparison(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    questions: list[EvaluationQuestion],
    documents_by_command: dict[str, tuple[str, ...]],
    *,
    version: str | None,
    k_values: tuple[int, ...] = (5, 10, 20),
) -> NaiveBaselineReport:
    """D6 : BM25 doit nettement battre une simple correspondance de nom de commande.

    Restreint aux questions résolues qui nomment au moins une commande
    attendue (`expected_commands`) : c'est le seul sous-ensemble où la
    référence naïve peut légitimement répondre — la comparer sur le jeu
    entier la pénaliserait sur des questions qu'elle n'a jamais prétendu
    couvrir.
    """
    subset = [q for q in questions if q.required_documents and q.expected_commands]

    naive_results = {
        q.id: naive_command_search(q.question, documents_by_command) for q in subset
    }
    bm25_results = {
        q.id: rank_documents_for_question(retriever, corpus, q, version=version)
        for q in subset
    }

    return NaiveBaselineReport(
        n_questions_with_expected_commands=len(subset),
        naive_reports_by_k={
            k: evaluate_retrieval(subset, naive_results, k=k) for k in k_values
        },
        bm25_reports_by_k={
            k: evaluate_retrieval(subset, bm25_results, k=k) for k in k_values
        },
    )


class VariantSummary(BaseModel):
    """One row of the E4 gain-decomposition table (lot 7b), for one k."""

    model_config = ConfigDict(frozen=True)

    variant: str
    k: int
    hit_rate_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float


class NonExplicitImpact(BaseModel):
    """E3 : what one variant does to one `answerability != "explicit"`,
    resolved question at k=10 -- nominative, not only aggregated, since
    there are only ever a handful of them (docs/corpus.md §8: "absent"
    questions carry empty `required_documents` and are never scored, so
    they never appear here)."""

    model_config = ConfigDict(frozen=True)

    id: str
    answerability: str
    required_documents: tuple[str, ...]
    hit_at_k10_lot7_reference: bool
    hit_at_k10_variant: bool


class Lot7bDecompositionReport(BaseModel):
    """E4 : the full lot 7b gain-decomposition measurement, four variants."""

    model_config = ConfigDict(frozen=True)

    k_values: tuple[int, ...]
    reports: dict[str, GranularityBenchReport]
    gain_table: tuple[VariantSummary, ...]
    non_explicit_impact: dict[str, tuple[NonExplicitImpact, ...]]


def _scores_at_k10(report: GranularityBenchReport) -> dict[str, Any]:
    reference = report.reports_by_k.get(10) or next(iter(report.reports_by_k.values()))
    return {score.id: score for score in reference.scores}


def run_lot7b_decomposition(
    *,
    reference_retriever: bm25s.BM25,
    reference_corpus: list[dict[str, Any]],
    e1_retriever: bm25s.BM25,
    e1_corpus: list[dict[str, Any]],
    questions: list[EvaluationQuestion],
    version: str | None,
    priority_families: tuple[str, ...],
    granularity: str = "by_file",
    k_values: tuple[int, ...] = (5, 10, 20),
) -> Lot7bDecompositionReport:
    """E4 : run the four lot 7b variants against the same question set.

    - ``lot7_reference`` : lot 7 index, lot 7 ranking (`rank_documents_for_question`)
      -- unchanged, the control measurement every gain is read against.
    - ``e1`` : E1-enriched index, same unchanged ranking (E1 instruction:
      "mesure le gain de E1 seul, à classement inchangé").
    - ``e1_e2a`` : E1-enriched index, `rank_documents_with_source_priority`
      in ``"hard"`` mode.
    - ``e1_e2b`` : E1-enriched index, same in ``"soft"`` mode.

    `priority_families` is always the caller's explicit choice (E2
    instruction: no automatic query-profile detection in this lot) --
    `"syntax"` by default at the CLI layer, since it matches the current
    bench's own nature (docs/corpus.md §8: every lot 5/5b question is a
    syntax/method question, none about theory or a worked example).
    """
    variants: dict[str, GranularityBenchReport] = {
        "lot7_reference": run_granularity_bench(
            reference_retriever,
            reference_corpus,
            questions,
            granularity=granularity,
            fragment_count=len(reference_corpus),
            version=version,
            k_values=k_values,
        ),
        "e1": run_granularity_bench(
            e1_retriever,
            e1_corpus,
            questions,
            granularity=granularity,
            fragment_count=len(e1_corpus),
            version=version,
            k_values=k_values,
        ),
        "e1_e2a": run_granularity_bench(
            e1_retriever,
            e1_corpus,
            questions,
            granularity=granularity,
            fragment_count=len(e1_corpus),
            version=version,
            k_values=k_values,
            rank_fn=lambda q: rank_documents_with_source_priority(
                e1_retriever,
                e1_corpus,
                q,
                version=version,
                priority_families=priority_families,
                mode="hard",
            ),
        ),
        "e1_e2b": run_granularity_bench(
            e1_retriever,
            e1_corpus,
            questions,
            granularity=granularity,
            fragment_count=len(e1_corpus),
            version=version,
            k_values=k_values,
            rank_fn=lambda q: rank_documents_with_source_priority(
                e1_retriever,
                e1_corpus,
                q,
                version=version,
                priority_families=priority_families,
                mode="soft",
            ),
        ),
    }

    gain_table = tuple(
        VariantSummary(
            variant=name,
            k=k,
            hit_rate_at_k=report.reports_by_k[k].hit_rate_at_k,
            mean_recall_at_k=report.reports_by_k[k].mean_recall_at_k,
            mean_reciprocal_rank=report.reports_by_k[k].mean_reciprocal_rank,
        )
        for name, report in variants.items()
        for k in k_values
        if k in report.reports_by_k
    )

    reference_scores = _scores_at_k10(variants["lot7_reference"])
    non_explicit_questions = [
        q for q in questions if q.required_documents and q.answerability != "explicit"
    ]
    non_explicit_impact = {
        name: tuple(
            NonExplicitImpact(
                id=question.id,
                answerability=question.answerability,
                required_documents=question.required_documents,
                hit_at_k10_lot7_reference=reference_scores[question.id].hit,
                hit_at_k10_variant=_scores_at_k10(report)[question.id].hit,
            )
            for question in non_explicit_questions
        )
        for name, report in variants.items()
    }

    return Lot7bDecompositionReport(
        k_values=k_values,
        reports=variants,
        gain_table=gain_table,
        non_explicit_impact=non_explicit_impact,
    )
