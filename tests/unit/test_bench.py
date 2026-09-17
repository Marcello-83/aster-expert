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
    rank_documents_with_query_profile,
    rank_documents_with_source_priority,
    run_granularity_bench,
    run_lot7b_decomposition,
    run_naive_baseline_comparison,
    run_profile_routed_bench,
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


def test_rank_documents_with_source_priority_hard_mode_prefers_priority_family(
    tmp_path: Path,
) -> None:
    fragments = [
        _fragment(
            fragment_id="V1#index",
            document_id="V1",
            document_title="Cas test",
            family="V",
            source_path="v/v1/index.rst",
            content="modélisation modélisation modélisation générique",
        ),
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            document_title="Opérateur",
            family="U4",
            source_path="man_u/u4/x/index.rst",
            content="modélisation",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)
    question = _question(question="modélisation")

    ranked = rank_documents_with_source_priority(
        retriever,
        corpus,
        question,
        version=None,
        priority_families=("U4",),
        mode="hard",
    )

    assert ranked[0] == "U4_1"


def test_run_lot7b_decomposition_runs_all_four_variants(tmp_path: Path) -> None:
    reference_retriever, reference_corpus = _build_index(tmp_path, _sample_fragments())
    e1_retriever, e1_corpus = _build_index(tmp_path, _sample_fragments())
    questions = [
        _question(
            id="eval-001",
            question="Comment utiliser STAT_NON_LINE ?",
            domain="convergence",
            required_documents=("U4.51.03",),
            answerability="explicit",
        ),
        _question(
            id="eval-002",
            question="Comment affecter une modélisation ?",
            domain="maillage",
            required_documents=("U4.41.01",),
            answerability="inferable",
        ),
    ]

    report = run_lot7b_decomposition(
        reference_retriever=reference_retriever,
        reference_corpus=reference_corpus,
        e1_retriever=e1_retriever,
        e1_corpus=e1_corpus,
        questions=questions,
        version=None,
        priority_families=("U4",),
        k_values=(5, 10),
    )

    assert set(report.reports) == {"lot7_reference", "e1", "e1_e2a", "e1_e2b"}
    assert {row.variant for row in report.gain_table} == {
        "lot7_reference",
        "e1",
        "e1_e2a",
        "e1_e2b",
    }
    # Only the non-"explicit" question (eval-002) appears in the E3 impact
    # list, never eval-001.
    for impacts in report.non_explicit_impact.values():
        assert {impact.id for impact in impacts} == {"eval-002"}


def test_rank_documents_with_query_profile_uses_annotated_profile(
    tmp_path: Path,
) -> None:
    fragments = [
        _fragment(
            fragment_id="R1#index",
            document_id="R1",
            document_title="Référence théorique",
            family="R",
            source_path="r/r1/index.rst",
            content="loi de comportement loi de comportement loi de comportement",
        ),
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            document_title="Opérateur",
            family="U4",
            source_path="man_u/u4/x/index.rst",
            content="loi de comportement",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)
    question = _question(id="eval-777", question="loi de comportement")
    source_priority: dict[str, tuple[str, ...]] = {
        "syntaxe": ("U4",),
        "theorie": ("R",),
    }

    ranked_default = rank_documents_with_query_profile(
        retriever,
        corpus,
        question,
        version=None,
        profile_by_question_id={},
        source_priority_by_profile=source_priority,
        default_profile="syntaxe",
    )
    assert ranked_default[0] == "U4_1"

    ranked_annotated = rank_documents_with_query_profile(
        retriever,
        corpus,
        question,
        version=None,
        profile_by_question_id={"eval-777": "theorie"},
        source_priority_by_profile=source_priority,
        default_profile="syntaxe",
    )
    assert ranked_annotated[0] == "R1"


def test_run_profile_routed_bench_realistic_uses_per_question_profile(
    tmp_path: Path,
) -> None:
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
    source_priority: dict[str, tuple[str, ...]] = {
        "syntaxe": ("U4",),
        "theorie": ("R",),
        "methode": ("U2",),
    }

    report = run_profile_routed_bench(
        retriever,
        corpus,
        questions,
        granularity="by_file",
        fragment_count=len(corpus),
        version=None,
        profile_by_question_id={"eval-001": "theorie"},
        source_priority_by_profile=source_priority,
        default_profile="syntaxe",
        k_values=(10,),
    )

    # eval-002 is absent from the annotation: it falls back to the default
    # profile, never an invented one.
    assert report.unannotated_question_ids == ("eval-002",)
    assert set(report.ventilation_by_profile[10]) == {"theorie", "syntaxe"}
    assert report.floor.n_questions_evaluated == 2
    assert report.realistic.n_questions_evaluated == 2


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
