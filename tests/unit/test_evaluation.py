"""Tests for aster_expert.retrieval.evaluation (lot 5).

Uses a fabricated question set and a fabricated ranked-results index only:
no corpus, no catalogue, no network (CLAUDE.md, "Aucun accès réseau dans les
tests unitaires").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.retrieval.evaluation import (
    evaluate_retrieval,
    load_questions,
    load_ranked_results,
    summarize_question_set,
)
from aster_expert.retrieval.models import EvaluationQuestion


def _question(**overrides: object) -> EvaluationQuestion:
    defaults: dict[str, object] = {
        "id": "eval-001",
        "question": "question factice",
        "domain": "domaine_factice",
        "origin": "travail reel",
        "expected_documents": ("U4.10.01",),
    }
    defaults.update(overrides)
    return EvaluationQuestion.model_validate(defaults)


def test_hit_when_expected_document_anywhere_in_top_k() -> None:
    questions = [_question(expected_documents=("U4.10.01", "U4.10.02"))]
    results = {"eval-001": ("U4.99.99", "U4.10.02", "U4.00.00")}

    report = evaluate_retrieval(questions, results, k=3)

    assert report.n_questions_evaluated == 1
    assert report.scores[0].hit is True
    assert report.hit_rate_at_k == 1.0
    # 1 relevant doc found among 3 retrieved, out of 2 expected documents.
    assert report.scores[0].precision_at_k == pytest.approx(1 / 3)
    assert report.scores[0].recall_at_k == pytest.approx(1 / 2)
    assert report.scores[0].reciprocal_rank == pytest.approx(1 / 2)


def test_miss_when_no_expected_document_within_k() -> None:
    questions = [_question(expected_documents=("U4.10.01",))]
    results = {"eval-001": ("U4.10.01", "U4.00.00")}

    report = evaluate_retrieval(questions, results, k=1)

    assert report.scores[0].hit is True  # rank 1, within k=1
    report_k_zero_equivalent = evaluate_retrieval(
        questions, {"eval-001": ("U4.00.00", "U4.10.01")}, k=1
    )
    assert report_k_zero_equivalent.scores[0].hit is False
    assert report_k_zero_equivalent.hit_rate_at_k == 0.0
    assert report_k_zero_equivalent.scores[0].reciprocal_rank == pytest.approx(1 / 2)


def test_unresolved_question_excluded_not_scored_as_failure() -> None:
    questions = [
        _question(id="eval-001", expected_documents=()),
        _question(id="eval-002", expected_documents=("U4.10.01",)),
    ]
    results = {"eval-002": ("U4.10.01",)}

    report = evaluate_retrieval(questions, results, k=5)

    assert report.n_questions_total == 2
    assert report.n_questions_excluded_unresolved == 1
    assert report.n_questions_evaluated == 1
    assert report.hit_rate_at_k == 1.0


def test_resolved_question_missing_from_results_is_a_scored_miss() -> None:
    questions = [_question(id="eval-001", expected_documents=("U4.10.01",))]

    report = evaluate_retrieval(questions, {}, k=5)

    assert report.n_questions_missing_result == 1
    assert report.n_questions_evaluated == 1
    assert report.scores[0].hit is False
    assert report.hit_rate_at_k == 0.0


def test_k_must_be_positive() -> None:
    with pytest.raises(ValueError):
        evaluate_retrieval([_question()], {}, k=0)


def test_load_questions_and_ranked_results_round_trip(tmp_path: Path) -> None:
    questions_path = tmp_path / "questions.jsonl"
    questions_path.write_text(
        '{"id": "eval-001", "question": "q", "domain": "d", "origin": "o", '
        '"expected_documents": ["U4.10.01"], "expected_commands": ["DEBUT"]}\n',
        encoding="utf-8",
    )
    results_path = tmp_path / "results.jsonl"
    results_path.write_text(
        '{"id": "eval-001", "ranked_documents": ["U4.10.01", "U4.10.02"]}\n',
        encoding="utf-8",
    )

    questions = load_questions(questions_path)
    results = load_ranked_results(results_path)

    assert questions[0].expected_commands == ("DEBUT",)
    report = evaluate_retrieval(questions, results, k=2)
    assert report.hit_rate_at_k == 1.0


def test_summarize_question_set_counts_domains_families_and_outside_corpus() -> None:
    questions = [
        _question(
            id="eval-001",
            domain="maillage",
            expected_documents=("U4.23.04",),
        ),
        _question(
            id="eval-002",
            domain="maillage",
            expected_documents=(),
            note="recherche infructueuse : aucun document ne traite ce point précis",
        ),
        _question(
            id="eval-003",
            domain="lois_comportement",
            expected_documents=("R7.01.03", "V6.04.100"),
        ),
        _question(
            id="eval-004",
            domain="convergence",
            expected_documents=(),
            answer_outside_corpus=True,
            note="réponse dans les messages du catalogue, hors corpus documentaire",
        ),
    ]

    summary = summarize_question_set(questions)

    assert summary.total == 4
    assert summary.resolved == 2
    assert summary.unresolved == 2
    assert summary.unresolved_ids == ("eval-002", "eval-004")
    assert summary.by_domain["maillage"] == {"resolved": 1, "unresolved": 1}
    assert summary.by_domain["lois_comportement"] == {"resolved": 1, "unresolved": 0}
    assert summary.document_family_counts == {"U4": 1, "R": 1, "V": 1}
    assert summary.outside_corpus_ids == ("eval-004",)
