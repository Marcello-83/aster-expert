"""Tests for aster_expert.retrieval.bench (lot 7, D5/D6).

A tiny hand-built BM25 index (via `aster_expert.indexing.bm25_index`) and a
tiny question set only: no real corpus, no network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bm25s

from aster_expert.indexing.bm25_index import build_bm25_index, load_bm25_index
from aster_expert.retrieval.bench import (
    rank_documents_for_question,
    run_granularity_bench,
    run_naive_baseline_comparison,
)
from aster_expert.retrieval.models import EvaluationQuestion

_NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
_FAKE_VERSION = {
    "solver": "17.4.0",
    "documentation_revision": "0" * 40,
    "compatibility_status": "jeu de test factice, sans lien avec un corpus réel",
}


def _fragment(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "granularity": "by_file",
        "source_name": "codeaster-doc",
        "source_commit": "deadbeef" * 5,
        "aster_version": "17.4.0",
        "section_path": ["index"],
        "content_hash": "sha256:" + "0" * 64,
        "line_start": 1,
        "line_end": 1,
        "related_commands": [],
        "related_keywords": [],
        "related_documents": [],
        "language": "fr",
        "extracted_at": _NOW,
    }
    defaults.update(overrides)
    return defaults


def _build_index(
    tmp_path: Path, fragments: list[dict[str, object]]
) -> tuple[bm25s.BM25, list[dict[str, Any]]]:
    fragments_path = tmp_path / "fragments.jsonl"
    with fragments_path.open("w", encoding="utf-8") as handle:
        for fragment in fragments:
            handle.write(json.dumps(fragment))
            handle.write("\n")
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    return load_bm25_index(index_dir)


def _question(**overrides: object) -> EvaluationQuestion:
    defaults: dict[str, object] = {
        "id": "eval-001",
        "question": "question factice",
        "domain": "domaine_factice",
        "origin": "travail reel",
        "version": _FAKE_VERSION,
        "required_documents": ("U4.51.03",),
        "answerability": "explicit",
        "gold_confidence": "high",
    }
    defaults.update(overrides)
    return EvaluationQuestion.model_validate(defaults)


def _sample_fragments() -> list[dict[str, object]]:
    return [
        _fragment(
            fragment_id="U4.51.03#index",
            document_id="U4.51.03",
            document_title="Opérateur STAT_NON_LINE",
            family="U4",
            source_path="man_u/u4/u4.51.03/index.rst",
            content="STAT_NON_LINE calcule la réponse mécanique non linéaire.",
            related_commands=["STAT_NON_LINE"],
        ),
        _fragment(
            fragment_id="U4.51.03#Syntaxe",
            document_id="U4.51.03",
            document_title="Opérateur STAT_NON_LINE",
            family="U4",
            source_path="man_u/u4/u4.51.03/Syntaxe.rst",
            content="Syntaxe complète de STAT_NON_LINE avec tous ses mots-clés.",
            related_commands=["STAT_NON_LINE"],
        ),
        _fragment(
            fragment_id="U4.41.01#index",
            document_id="U4.41.01",
            document_title="Opérateur AFFE_MODELE",
            family="U4",
            source_path="man_u/u4/u4.41.01/index.rst",
            content="AFFE_MODELE affecte une modélisation au maillage.",
            related_commands=["AFFE_MODELE"],
        ),
    ]


def test_rank_documents_for_question_dedupes_multiple_fragments_of_one_document(
    tmp_path: Path,
) -> None:
    retriever, corpus = _build_index(tmp_path, _sample_fragments())
    question = _question(question="Comment utiliser STAT_NON_LINE ?")

    ranked = rank_documents_for_question(retriever, corpus, question, version=None)

    assert ranked[0] == "U4.51.03"
    assert (
        ranked.count("U4.51.03") == 1
    )  # deux fragments du même document, un seul rang


def test_run_granularity_bench_reports_hit_at_multiple_k(tmp_path: Path) -> None:
    retriever, corpus = _build_index(tmp_path, _sample_fragments())
    questions = [
        _question(
            id="eval-001",
            question="Comment utiliser STAT_NON_LINE ?",
            domain="convergence",
            required_documents=("U4.51.03",),
        ),
        _question(
            id="eval-002",
            question="Comment affecter une modélisation ?",
            domain="maillage",
            required_documents=("U4.41.01",),
        ),
    ]

    report = run_granularity_bench(
        retriever,
        corpus,
        questions,
        granularity="by_file",
        fragment_count=len(corpus),
        version=None,
        k_values=(5, 10),
    )

    assert report.n_questions_evaluated == 2
    assert 5 in report.reports_by_k
    assert 10 in report.reports_by_k
    assert report.reports_by_k[10].hit_rate_at_k == 1.0
    assert "convergence" in report.ventilation_by_domain[10]
    assert report.failures_at_k10 == ()


def test_run_granularity_bench_lists_failures_at_k10(tmp_path: Path) -> None:
    retriever, corpus = _build_index(tmp_path, _sample_fragments())
    questions = [
        _question(
            id="eval-001",
            question="Un sujet totalement absent du corpus indexé ici.",
            required_documents=("Z9.99.99",),
        ),
    ]

    report = run_granularity_bench(
        retriever,
        corpus,
        questions,
        granularity="by_file",
        fragment_count=len(corpus),
        version=None,
        k_values=(10,),
    )

    assert len(report.failures_at_k10) == 1
    assert report.failures_at_k10[0].id == "eval-001"
    assert report.failures_at_k10[0].required_documents == ("Z9.99.99",)


def test_run_naive_baseline_restricts_to_questions_with_expected_commands(
    tmp_path: Path,
) -> None:
    retriever, corpus = _build_index(tmp_path, _sample_fragments())
    questions = [
        _question(
            id="eval-001",
            question="Comment utiliser STAT_NON_LINE ?",
            required_documents=("U4.51.03",),
            expected_commands=("STAT_NON_LINE",),
        ),
        _question(
            id="eval-002",
            question="Question sans commande explicite.",
            required_documents=("U4.41.01",),
            expected_commands=(),
        ),
    ]
    documents_by_command: dict[str, tuple[str, ...]] = {"STAT_NON_LINE": ("U4.51.03",)}

    report = run_naive_baseline_comparison(
        retriever,
        corpus,
        questions,
        documents_by_command,
        version=None,
        k_values=(5,),
    )

    assert report.n_questions_with_expected_commands == 1
    assert report.naive_reports_by_k[5].n_questions_evaluated == 1
    assert report.naive_reports_by_k[5].hit_rate_at_k == 1.0
