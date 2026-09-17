"""Tests for aster_expert.retrieval.evaluation (lot 5).

Uses a fabricated question set and a fabricated ranked-results index only:
no corpus, no catalogue, no network (CLAUDE.md, "Aucun accès réseau dans les
tests unitaires").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aster_expert.retrieval.evaluation import (
    evaluate_retrieval,
    list_failures,
    load_questions,
    load_ranked_results,
    summarize_question_set,
    ventilate_by_answerability,
    ventilate_by_domain,
    ventilate_by_family,
)
from aster_expert.retrieval.models import EvaluationQuestion

_FAKE_VERSION = {
    "solver": "17.4.0",
    "documentation_revision": "0" * 40,
    "compatibility_status": "jeu de test factice, sans lien avec un corpus réel",
}


def _question(**overrides: object) -> EvaluationQuestion:
    defaults: dict[str, object] = {
        "id": "eval-001",
        "question": "question factice",
        "domain": "domaine_factice",
        "origin": "travail reel",
        "version": _FAKE_VERSION,
        "required_documents": ("U4.10.01",),
        "answerability": "explicit",
        "gold_confidence": "high",
    }
    defaults.update(overrides)
    return EvaluationQuestion.model_validate(defaults)


def test_hit_when_expected_document_anywhere_in_top_k() -> None:
    questions = [_question(required_documents=("U4.10.01", "U4.10.02"))]
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
    questions = [_question(required_documents=("U4.10.01",))]
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
        _question(
            id="eval-001",
            required_documents=(),
            answerability="absent",
            gold_confidence="provisional",
        ),
        _question(id="eval-002", required_documents=("U4.10.01",)),
    ]
    results = {"eval-002": ("U4.10.01",)}

    report = evaluate_retrieval(questions, results, k=5)

    assert report.n_questions_total == 2
    assert report.n_questions_excluded_unresolved == 1
    assert report.n_questions_evaluated == 1
    assert report.hit_rate_at_k == 1.0


def test_resolved_question_missing_from_results_is_a_scored_miss() -> None:
    questions = [_question(id="eval-001", required_documents=("U4.10.01",))]

    report = evaluate_retrieval(questions, {}, k=5)

    assert report.n_questions_missing_result == 1
    assert report.n_questions_evaluated == 1
    assert report.scores[0].hit is False
    assert report.hit_rate_at_k == 0.0


def test_k_must_be_positive() -> None:
    with pytest.raises(ValueError):
        evaluate_retrieval([_question()], {}, k=0)


def test_supporting_documents_never_scored() -> None:
    """A retrieved supporting-only document is not a hit (lot 5b, docs/corpus.md §8:
    'la métrique ne lit que required_documents')."""
    questions = [
        _question(
            required_documents=("U4.10.01",),
            supporting_documents=("R5.03.01",),
        )
    ]
    results: dict[str, tuple[str, ...]] = {"eval-001": ("R5.03.01",)}

    report = evaluate_retrieval(questions, results, k=1)

    assert report.scores[0].hit is False
    assert report.scores[0].required_documents == ("U4.10.01",)


def test_load_questions_and_ranked_results_round_trip(tmp_path: Path) -> None:
    questions_path = tmp_path / "questions.jsonl"
    fake_version = json.dumps(
        {
            "solver": "17.4.0",
            "documentation_revision": "0" * 40,
            "compatibility_status": "jeu de test",
        }
    )
    questions_path.write_text(
        '{"id": "eval-001", "question": "q", "domain": "d", "origin": "o", '
        f'"version": {fake_version}, '
        '"required_documents": ["U4.10.01"], "expected_commands": ["DEBUT"], '
        '"answerability": "explicit", "gold_confidence": "high"}\n',
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
            required_documents=("U4.23.04",),
        ),
        _question(
            id="eval-002",
            domain="maillage",
            required_documents=(),
            answerability="absent",
            gold_confidence="provisional",
            note="recherche infructueuse : aucun document ne traite ce point précis",
        ),
        _question(
            id="eval-003",
            domain="lois_comportement",
            required_documents=("R7.01.03", "V6.04.100"),
        ),
        _question(
            id="eval-004",
            domain="convergence",
            required_documents=(),
            answerability="absent",
            gold_confidence="provisional",
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


def test_ventilate_by_domain_groups_and_averages_correctly() -> None:
    questions = [
        _question(id="eval-001", domain="maillage", required_documents=("U4.10.01",)),
        _question(id="eval-002", domain="maillage", required_documents=("U4.10.02",)),
        _question(
            id="eval-003", domain="convergence", required_documents=("U4.20.01",)
        ),
    ]
    results: dict[str, tuple[str, ...]] = {
        "eval-001": ("U4.10.01",),  # hit
        "eval-002": ("U4.99.99",),  # miss
        "eval-003": ("U4.20.01",),  # hit
    }
    report = evaluate_retrieval(questions, results, k=5)
    questions_by_id = {q.id: q for q in questions}

    buckets = ventilate_by_domain(report.scores, questions_by_id)

    assert buckets["maillage"].n_questions == 2
    assert buckets["maillage"].hit_rate == pytest.approx(0.5)
    assert buckets["convergence"].n_questions == 1
    assert buckets["convergence"].hit_rate == pytest.approx(1.0)


def test_ventilate_by_family_counts_a_multi_family_question_in_every_bucket() -> None:
    questions = [
        _question(
            id="eval-001",
            required_documents=("R7.01.03", "V6.04.100"),
        ),
    ]
    results: dict[str, tuple[str, ...]] = {"eval-001": ("R7.01.03",)}
    report = evaluate_retrieval(questions, results, k=5)
    questions_by_id = {q.id: q for q in questions}

    buckets = ventilate_by_family(report.scores, questions_by_id)

    assert set(buckets) == {"R", "V"}
    assert buckets["R"].n_questions == 1
    assert buckets["V"].n_questions == 1
    assert buckets["R"].hit_rate == pytest.approx(1.0)
    assert buckets["V"].hit_rate == pytest.approx(1.0)  # même question, même hit


def test_ventilate_by_answerability() -> None:
    questions = [
        _question(id="eval-001", answerability="explicit", required_documents=("A",)),
        _question(id="eval-002", answerability="partial", required_documents=("B",)),
    ]
    results: dict[str, tuple[str, ...]] = {"eval-001": ("A",), "eval-002": ("Z",)}
    report = evaluate_retrieval(questions, results, k=5)
    questions_by_id = {q.id: q for q in questions}

    buckets = ventilate_by_answerability(report.scores, questions_by_id)

    assert buckets["explicit"].hit_rate == pytest.approx(1.0)
    assert buckets["partial"].hit_rate == pytest.approx(0.0)


def test_list_failures_returns_only_missed_questions() -> None:
    questions = [
        _question(id="eval-001", required_documents=("A",)),
        _question(id="eval-002", required_documents=("B",)),
    ]
    results: dict[str, tuple[str, ...]] = {"eval-001": ("A",), "eval-002": ("Z",)}
    report = evaluate_retrieval(questions, results, k=5)

    failures = list_failures(report)

    assert len(failures) == 1
    assert failures[0].id == "eval-002"
