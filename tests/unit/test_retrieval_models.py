"""Unit tests for aster_expert.retrieval.models (lot 5b schema amendment)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aster_expert.retrieval.models import EvaluationQuestion, VersionInfo

_VERSION = VersionInfo(
    solver="17.4.0",
    documentation_revision="9c8c179f57ef7ca1d2891cac275ee4823a57967c",
    compatibility_status="correspondance de tag vérifiée (git ls-remote)",
)


def _question(**overrides: object) -> EvaluationQuestion:
    defaults: dict[str, object] = {
        "id": "eval-001",
        "question": "question factice",
        "domain": "domaine_factice",
        "origin": "travail reel",
        "version": _VERSION,
        "required_documents": ("U4.10.01",),
        "answerability": "explicit",
        "gold_confidence": "high",
    }
    defaults.update(overrides)
    return EvaluationQuestion.model_validate(defaults)


def test_version_is_mandatory_and_never_null() -> None:
    """Lot 5b, N1 : `version: null` is no longer a valid state — a question
    without a version object fails validation rather than defaulting."""
    with pytest.raises(ValidationError):
        EvaluationQuestion.model_validate(
            {
                "id": "eval-001",
                "question": "q",
                "domain": "d",
                "origin": "o",
                "required_documents": ("U4.10.01",),
                "answerability": "explicit",
                "gold_confidence": "high",
            }
        )


def test_answerability_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        _question(answerability="oui_mais_non")


def test_gold_confidence_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        _question(gold_confidence="tres_sur")


def test_required_and_supporting_documents_are_independent_fields() -> None:
    question = _question(
        required_documents=("U4.10.01",),
        supporting_documents=("R5.03.01", "U2.01.05"),
    )
    assert question.required_documents == ("U4.10.01",)
    assert question.supporting_documents == ("R5.03.01", "U2.01.05")


def test_unresolved_question_has_empty_required_documents() -> None:
    question = _question(
        required_documents=(),
        answerability="absent",
        gold_confidence="provisional",
        verified_by=None,
    )
    assert question.required_documents == ()
    assert question.answerability == "absent"
