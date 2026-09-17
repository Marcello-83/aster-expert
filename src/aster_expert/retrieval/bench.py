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

from typing import Any

import bm25s
from pydantic import BaseModel, ConfigDict

from aster_expert.indexing.bm25_index import search
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

# Fragments récupérés par requête avant réduction au niveau document : un
# classement de fragments dédupliqué en documents peut être plus court que
# le nombre de fragments demandé (plusieurs fragments d'un même document
# occupant les premiers rangs, surtout en granularité `by_subsection`) — une
# marge large garantit qu'un classement à k=20 documents distincts reste
# atteignable quand le corpus le permet, jamais tronqué artificiellement par
# une profondeur de recherche insuffisante.
_FRAGMENT_SEARCH_K = 150


def rank_documents_for_question(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    question: EvaluationQuestion,
    *,
    version: str | None,
) -> tuple[str, ...]:
    """One question's fragment hits, deduplicated to a document ranking.

    Order preserved from the fragment ranking (already sorted by score):
    the first fragment of a document fixes that document's rank, later
    fragments of the same document are dropped, never re-scored or merged.
    """
    hits = search(
        retriever, corpus, question.question, k=_FRAGMENT_SEARCH_K, version=version
    )
    ranked: list[str] = []
    for hit in hits:
        if hit.document_id not in ranked:
            ranked.append(hit.document_id)
    return tuple(ranked)


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
) -> GranularityBenchReport:
    questions_by_id = {q.id: q for q in questions}
    results = {
        q.id: rank_documents_for_question(retriever, corpus, q, version=version)
        for q in questions
        if q.required_documents
    }

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
