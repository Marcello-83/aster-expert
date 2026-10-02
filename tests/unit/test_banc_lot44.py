"""Banc d'évaluation : les 22 questions du tri de MM versées au lot 44."""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.retrieval.evaluation import load_questions
from aster_expert.retrieval.query_profiles import load_query_profiles

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data" / "evaluations"
ORIGIN = "journal des requêtes (lot 42), tri validé par MM, document établi au lot 44"


def test_the_22_retained_questions_are_in_the_bench_with_a_profile() -> None:
    questions = [
        q for q in load_questions(EVAL / "questions.jsonl") if q.origin == ORIGIN
    ]
    assert len(questions) == 22
    assert [q.id for q in questions] == [f"eval-{n:03d}" for n in range(66, 88)]
    profiles = load_query_profiles(EVAL / "query_profiles.jsonl")
    assert all(q.id in profiles for q in questions)
    sources = {q.source_question for q in questions}
    retained = {
        "cand-001",
        "cand-002",
        "cand-003",
        "cand-004",
        "cand-005",
        "cand-006",
        "cand-008",
        "cand-010",
        "cand-011",
        "cand-013",
        "cand-014",
        "cand-016",
        "cand-017",
        "cand-024",
        "cand-028",
        "cand-030",
        "cand-033",
        "cand-034",
        "cand-035",
        "cand-036",
        "cand-037",
        "cand-029",
    }
    assert sources == retained


def test_undocumented_questions_carry_no_forced_document() -> None:
    questions = [
        q for q in load_questions(EVAL / "questions.jsonl") if q.origin == ORIGIN
    ]
    absent = [q for q in questions if q.answerability == "absent"]
    assert {q.source_question for q in absent} == {"cand-002", "cand-016", "cand-030"}
    for q in absent:
        assert q.required_documents == ()
        assert q.gold_confidence == "provisional"
        assert "Non documentée" in (q.note or "")
    for q in questions:
        if q.answerability != "absent":
            assert q.required_documents and q.verified_by


def test_bench_reports_before_and_after_are_versioned() -> None:
    before = json.loads((EVAL / "lot44" / "banc_avant.json").read_text("utf-8"))
    after = json.loads((EVAL / "lot44" / "banc_apres.json").read_text("utf-8"))
    assert before["realistic"]["n_questions_evaluated"] == 63
    assert after["realistic"]["n_questions_evaluated"] == 82
