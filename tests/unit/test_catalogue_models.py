"""Unit tests for the pydantic catalogue schema models."""

from __future__ import annotations

from aster_expert.catalogue.models import (
    CommandSchema,
    ExtractionAnomaly,
    ExtractionSummary,
    FactorKeywordSchema,
    SimpleKeywordSchema,
)

SAMPLE_COMMAND = {
    "command": "STAT_NON_LINE",
    "aster_version": "17.4.0",
    "image_digest": "sha256:abc",
    "catalogue_source": "/opt/x/code_aster",
    "catalogue_hash": "sha256:def",
    "kind": "operator",
    "result_type": "evol_noli",
    "result_type_dynamic": False,
    "docu": None,
    "keywords": [
        {
            "path": ["COMPORTEMENT"],
            "kind": "factor",
            "status": "optional",
            "min_occurrences": 1,
            "max_occurrences": None,
            "condition": [],
            "children": [
                {
                    "path": ["COMPORTEMENT", "RELATION"],
                    "kind": "simple",
                    "status": "required",
                    "value_type": "TXM",
                    "allowed_values": ["ELAS", "VMIS_ISOT_LINE"],
                    "default": None,
                    "min_values": 1,
                    "max_values": 1,
                    "condition": ['TYPE == "A"'],
                }
            ],
        }
    ],
    "extracted_at": "2026-01-01T00:00:00+00:00",
}


def test_command_schema_round_trips() -> None:
    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    assert schema.command == "STAT_NON_LINE"
    factor = schema.keywords[0]
    assert isinstance(factor, FactorKeywordSchema)
    simple = factor.children[0]
    assert isinstance(simple, SimpleKeywordSchema)
    assert simple.condition == ['TYPE == "A"']

    dumped = schema.model_dump(mode="json")
    assert dumped["keywords"][0]["children"][0]["value_type"] == "TXM"


def test_command_schema_accepts_list_value_type() -> None:
    data = dict(SAMPLE_COMMAND)
    data["keywords"] = [
        {
            "path": ["MODELE"],
            "kind": "simple",
            "status": "required",
            "value_type": ["cham_no_sdaster", "carte_sdaster"],
            "allowed_values": None,
            "default": None,
            "min_values": 1,
            "max_values": 1,
            "condition": [],
        }
    ]
    schema = CommandSchema.model_validate(data)
    keyword = schema.keywords[0]
    assert isinstance(keyword, SimpleKeywordSchema)
    assert keyword.value_type == ["cham_no_sdaster", "carte_sdaster"]


def test_command_schema_accepts_complex_default() -> None:
    data = dict(SAMPLE_COMMAND)
    data["keywords"] = [
        {
            "path": ["CENTRE_CONTOUR"],
            "kind": "simple",
            "status": "optional",
            "value_type": "C",
            "allowed_values": None,
            "default": {"real": 0.0, "imag": 0.0},
            "min_values": 1,
            "max_values": 1,
            "condition": [],
        }
    ]
    schema = CommandSchema.model_validate(data)
    keyword = schema.keywords[0]
    assert isinstance(keyword, SimpleKeywordSchema)
    assert keyword.default == {"real": 0.0, "imag": 0.0}


def test_extraction_summary_round_trips() -> None:
    summary = ExtractionSummary.model_validate(
        {
            "total_exposed": 268,
            "total_extracted": 267,
            "kind_counts": {
                "operator": 135,
                "macro": 116,
                "procedure": 15,
                "formule": 1,
            },
            "encountered_classes": [
                "Bloc",
                "FactorKeyword",
                "SimpleKeyword",
                "Operator",
            ],
            "anomalies": [
                {"command": "BROKEN", "kind": "extraction_error", "detail": "boom"},
            ],
        }
    )
    assert summary.total_extracted == 267
    assert summary.anomalies == [
        ExtractionAnomaly(command="BROKEN", kind="extraction_error", detail="boom")
    ]
