"""Unit tests for `aster-expert catalogue show` support functions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import CommandSchema
from aster_expert.catalogue.query import (
    find_keyword_variants,
    load_command_schema,
    resolve_active_digest,
    resolve_digest_for_aster_version,
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
            "variant_id": "aaaaaaaaaaaaaaaa",
            "kind": "factor",
            "status": "optional",
            "min_occurrences": 1,
            "max_occurrences": None,
            "condition": [],
            "children": [
                {
                    "path": ["COMPORTEMENT", "RELATION"],
                    "variant_id": "bbbbbbbbbbbbbbbb",
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

# Mirrors the real anomaly found on STAT_NON_LINE (lot 4b, C1): the same
# path (["COMPORTEMENT", "RESI_INTE"]) declared under two different Bloc,
# each with its own condition and variant_id.
SAMPLE_COMMAND_WITH_DUPLICATE_PATH = {
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
            "variant_id": "aaaaaaaaaaaaaaaa",
            "kind": "factor",
            "status": "optional",
            "min_occurrences": 1,
            "max_occurrences": None,
            "condition": [],
            "children": [
                {
                    "path": ["COMPORTEMENT", "RESI_INTE"],
                    "variant_id": "variant-one-0001",
                    "kind": "simple",
                    "status": "optional",
                    "value_type": "R",
                    "allowed_values": None,
                    "default": None,
                    "min_values": None,
                    "max_values": 1,
                    "condition": ["equal_to(\"RELATION\", 'ELAS')"],
                },
                {
                    "path": ["COMPORTEMENT", "RESI_INTE"],
                    "variant_id": "variant-two-0002",
                    "kind": "simple",
                    "status": "optional",
                    "value_type": "R",
                    "allowed_values": None,
                    "default": 1.0e-6,
                    "min_values": None,
                    "max_values": 1,
                    "condition": ["equal_to(\"RELATION\", 'VMIS_ISOT_LINE')"],
                },
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


def test_resolve_digest_for_aster_version_single_match(tmp_path: Path) -> None:
    digest_dir = tmp_path / "sha256:aaa"
    digest_dir.mkdir()
    (digest_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(SAMPLE_COMMAND), encoding="utf-8"
    )
    assert resolve_digest_for_aster_version(tmp_path, "17.4.0") == "sha256:aaa"


def test_resolve_digest_for_aster_version_no_match_raises(tmp_path: Path) -> None:
    digest_dir = tmp_path / "sha256:aaa"
    digest_dir.mkdir()
    (digest_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(SAMPLE_COMMAND), encoding="utf-8"
    )
    with pytest.raises(CatalogueExtractionError, match="18.0.0"):
        resolve_digest_for_aster_version(tmp_path, "18.0.0")


def test_resolve_digest_for_aster_version_ambiguous_raises(tmp_path: Path) -> None:
    for name in ("sha256:aaa", "sha256:bbb"):
        digest_dir = tmp_path / name
        digest_dir.mkdir()
        (digest_dir / "STAT_NON_LINE.json").write_text(
            json.dumps(SAMPLE_COMMAND), encoding="utf-8"
        )
    with pytest.raises(CatalogueExtractionError, match="more than one"):
        resolve_digest_for_aster_version(tmp_path, "17.4.0")


def test_resolve_digest_for_aster_version_missing_root_raises(tmp_path: Path) -> None:
    with pytest.raises(CatalogueExtractionError, match="no extracted catalogue"):
        resolve_digest_for_aster_version(tmp_path / "missing", "17.4.0")


def test_find_keyword_variants_top_level_factor() -> None:
    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    variants = find_keyword_variants(schema, ["COMPORTEMENT"])
    assert len(variants) == 1
    assert variants[0].path == ["COMPORTEMENT"]
    assert variants[0].kind == "factor"


def test_find_keyword_variants_nested_simple() -> None:
    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    variants = find_keyword_variants(schema, ["COMPORTEMENT", "RELATION"])
    assert len(variants) == 1
    assert variants[0].path == ["COMPORTEMENT", "RELATION"]
    assert variants[0].kind == "simple"


def test_find_keyword_variants_not_found_raises() -> None:
    schema = CommandSchema.model_validate(SAMPLE_COMMAND)
    with pytest.raises(CatalogueExtractionError, match="keyword path not found"):
        find_keyword_variants(schema, ["COMPORTEMENT", "NOPE"])


def test_find_keyword_variants_returns_every_duplicate_never_just_one() -> None:
    """Regression test (lot 4b, C1).

    Must fail if a future change reintroduces the old `next()`-based lookup,
    which silently returned only the first of several same-path entries.
    """
    schema = CommandSchema.model_validate(SAMPLE_COMMAND_WITH_DUPLICATE_PATH)

    variants = find_keyword_variants(schema, ["COMPORTEMENT", "RESI_INTE"])

    assert len(variants) == 2, (
        "expected both RESI_INTE variants, got only "
        f"{len(variants)} — a path lookup must never silently drop variants"
    )
    variant_ids = {v.variant_id for v in variants}
    assert variant_ids == {"variant-one-0001", "variant-two-0002"}
    conditions = {tuple(v.condition) for v in variants}
    assert conditions == {
        ("equal_to(\"RELATION\", 'ELAS')",),
        ("equal_to(\"RELATION\", 'VMIS_ISOT_LINE')",),
    }


def test_catalogue_vocabulary_collects_commands_keywords_and_values(
    tmp_path: Path,
) -> None:
    import pytest

    from aster_expert.catalogue.errors import CatalogueExtractionError
    from aster_expert.catalogue.models import (
        CommandSchema,
        FactorKeywordSchema,
        SimpleKeywordSchema,
    )
    from aster_expert.catalogue.query import catalogue_vocabulary

    child = SimpleKeywordSchema(
        path=["GRP", "CHAMP"],
        variant_id="v",
        kind="simple",
        status="optional",
        value_type="TXM",
        allowed_values=["EFGE_NOEU", 3],
        default=None,
        min_values=None,
        max_values=None,
        condition=[],
    )
    factor = FactorKeywordSchema(
        path=["GRP"],
        variant_id="v",
        kind="factor",
        status="optional",
        min_occurrences=None,
        max_occurrences=None,
        condition=[],
        children=[child],
    )
    schema = CommandSchema(
        command="CMD",
        aster_version="x",
        image_digest="d",
        catalogue_source="s",
        catalogue_hash="h",
        kind="operator",
        result_type=None,
        result_type_dynamic=False,
        docu=None,
        keywords=[factor],
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    (tmp_path / "sha256:d").mkdir()
    (tmp_path / "sha256:d" / "CMD.json").write_text(
        schema.model_dump_json(), encoding="utf-8"
    )

    assert catalogue_vocabulary(tmp_path, "sha256:d") == {
        "CMD",
        "GRP",
        "CHAMP",
        "EFGE_NOEU",
    }
    with pytest.raises(CatalogueExtractionError):
        catalogue_vocabulary(tmp_path, "sha256:absent")
