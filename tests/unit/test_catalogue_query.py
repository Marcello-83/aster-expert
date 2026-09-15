"""Unit tests for `aster-expert catalogue show` support functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import CommandSchema
from aster_expert.catalogue.query import (
    find_keyword,
    load_command_schema,
    resolve_active_digest,
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
                    "condition": [],
                }
            ],
        }
    ],
    "extracted_at": "2026-01-01T00:00:00+00:00",
}

VERSIONS_YAML_WITH_DIGEST = """\
schema_version: 2
target: null
detected:
  detected_at: '2026-09-15T08:00:00Z'
  container:
    image_digest: sha256:d8d19ea9
versions: []
"""

VERSIONS_YAML_WITHOUT_DIGEST = """\
schema_version: 2
target: null
detected:
  detected_at: null
versions: []
"""


def test_resolve_active_digest_success(tmp_path: Path) -> None:
    path = tmp_path / "versions.yaml"
    path.write_text(VERSIONS_YAML_WITH_DIGEST, encoding="utf-8")
    assert resolve_active_digest(path) == "sha256:d8d19ea9"


def test_resolve_active_digest_missing_digest(tmp_path: Path) -> None:
    path = tmp_path / "versions.yaml"
    path.write_text(VERSIONS_YAML_WITHOUT_DIGEST, encoding="utf-8")
    with pytest.raises(CatalogueExtractionError, match="no detected image digest"):
        resolve_active_digest(path)


def test_resolve_active_digest_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CatalogueExtractionError, match="not found"):
        resolve_active_digest(tmp_path / "missing.yaml")


def test_load_command_schema_success(tmp_path: Path) -> None:
    digest_dir = tmp_path / "sha256:d8d19ea9"
    digest_dir.mkdir()
    (digest_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(SAMPLE_COMMAND), encoding="utf-8"
    )
    schema = load_command_schema(tmp_path, "sha256:d8d19ea9", "STAT_NON_LINE")
    assert schema.command == "STAT_NON_LINE"


def test_load_command_schema_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(CatalogueExtractionError, match="no extracted schema"):
        load_command_schema(tmp_path, "sha256:d8d19ea9", "STAT_NON_LINE")


def test_find_keyword_top_level_factor() -> None:

    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    entry = find_keyword(schema, ["COMPORTEMENT"])
    assert entry.path == ["COMPORTEMENT"]
    assert entry.kind == "factor"


def test_find_keyword_nested_simple() -> None:

    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    entry = find_keyword(schema, ["COMPORTEMENT", "RELATION"])
    assert entry.path == ["COMPORTEMENT", "RELATION"]
    assert entry.kind == "simple"


def test_find_keyword_not_found_raises() -> None:

    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    with pytest.raises(CatalogueExtractionError, match="keyword path not found"):
        find_keyword(schema, ["COMPORTEMENT", "NOPE"])
