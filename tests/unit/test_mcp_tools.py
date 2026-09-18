"""Tests for `aster_expert.mcp.tools` (lot 8): the wrapper functions themselves,

without going through the MCP protocol layer (see
tests/integration/test_mcp_server.py for that). Every fixture here is a
reduced, local corpus/catalogue built in `tmp_path` — no network, no Docker
(CLAUDE.md, "aucun accès réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import aster_expert.validation.validate as validate_module
from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir
from aster_expert.mcp.errors import McpToolError
from aster_expert.mcp.logging import default_query_log_path
from aster_expert.mcp.tools import (
    analyze_comm,
    get_command_schema,
    search_codeaster_docs,
    validate_comm,
)

DIGEST = "sha256:testdigest"

_RETRIEVAL_YAML = """
defaults:
  source_priority:
    syntaxe: [catalogue, U4, U7, testcase, source]
    theorie: [R, U2, U4, U3, V]
    methode: [U2, U4, R, U3]
"""


def _write_fragment(handle: Any, **overrides: Any) -> None:
    fragment = {
        "fragment_id": "U4.51.03#COMPORTEMENT",
        "granularity": "by_file",
        "document_id": "U4.51.03",
        "document_title": "Opérateur STAT_NON_LINE",
        "family": "U4",
        "aster_version": "17.4.0",
        "section_path": ["COMPORTEMENT"],
        "source_path": "source/manuals/man_u/u4/u4.51.03.rst",
        "source_commit": "a" * 40,
        "line_start": 1,
        "line_end": 10,
        "related_commands": ["STAT_NON_LINE"],
        "content": "Mot-clé facteur COMPORTEMENT : loi de comportement non linéaire.",
    }
    fragment.update(overrides)
    handle.write(json.dumps(fragment) + "\n")


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config" / "retrieval.yaml").write_text(_RETRIEVAL_YAML, encoding="utf-8")

    fragments_path = root / "data" / "processed" / "fragments_by_file.jsonl"
    fragments_path.parent.mkdir(parents=True)
    with fragments_path.open("w", encoding="utf-8") as handle:
        _write_fragment(handle)
        _write_fragment(
            handle,
            fragment_id="D.01.01#autre",
            document_id="D.01.01",
            family="D",
            content="Un document hors priorité syntaxe, sans rapport.",
            related_commands=[],
        )

    index_dir = default_index_dir(root, "by_file")
    build_bm25_index(fragments_path, index_dir)
    return root


def test_search_codeaster_docs_unknown_profile_fails_loudly(project_root: Path) -> None:
    with pytest.raises(McpToolError, match="Profil inconnu"):
        search_codeaster_docs(
            project_root=project_root, query="comportement", profile="bogus"
        )


def test_search_codeaster_docs_unknown_granularity_fails_loudly(
    project_root: Path,
) -> None:
    with pytest.raises(McpToolError, match="Granularité inconnue"):
        search_codeaster_docs(
            project_root=project_root, query="comportement", granularity="bogus"
        )


def test_search_codeaster_docs_missing_index_fails_loudly(tmp_path: Path) -> None:
    root = tmp_path / "no_index"
    (root / "config").mkdir(parents=True)
    (root / "config" / "retrieval.yaml").write_text(_RETRIEVAL_YAML, encoding="utf-8")

    with pytest.raises(McpToolError, match="Index introuvable"):
        search_codeaster_docs(project_root=root, query="comportement")


def test_search_codeaster_docs_returns_level_a_and_journals_the_call(
    project_root: Path,
) -> None:
    result = search_codeaster_docs(
        project_root=project_root, query="comportement non linéaire", k=5
    )

    assert result.validation_level == "A"
    assert result.profile == "syntaxe"
    assert result.priority_families == ("catalogue", "U4", "U7", "testcase", "source")
    assert len(result.results) == 1
    assert result.results[0].document_id == "U4.51.03"

    log_lines = default_query_log_path(project_root).read_text(encoding="utf-8")
    entry = json.loads(log_lines.splitlines()[-1])
    assert entry["tool"] == "search_codeaster_docs"
    assert entry["query"] == "comportement non linéaire"
    assert entry["profile"] == "syntaxe"
    assert entry["returned"] == [
        {
            "identifier": "U4.51.03#COMPORTEMENT",
            "score": pytest.approx(entry["returned"][0]["score"]),
        }
    ]


def _write_catalogue(catalogue_dir: Path) -> None:
    catalogue_dir.mkdir(parents=True)
    schema = {
        "command": "STAT_NON_LINE",
        "aster_version": "17.4.0",
        "image_digest": DIGEST,
        "catalogue_source": "/opt/x/code_aster/Cata",
        "catalogue_hash": "sha256:cataloguehash",
        "kind": "operator",
        "result_type": "evol_noli",
        "result_type_dynamic": False,
        "docu": None,
        "keywords": [
            {
                "path": ["COMPORTEMENT"],
                "variant_id": "aaaa",
                "kind": "factor",
                "status": "optional",
                "min_occurrences": 1,
                "max_occurrences": None,
                "condition": [],
                "children": [
                    {
                        "path": ["COMPORTEMENT", "RELATION"],
                        "variant_id": "bbbb",
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
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    (catalogue_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(schema), encoding="utf-8"
    )


@pytest.fixture
def catalogue_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    catalogue_dir = root / "data" / "processed" / "catalogue" / DIGEST
    _write_catalogue(catalogue_dir)
    versions_yaml = root / "config" / "versions.yaml"
    versions_yaml.parent.mkdir(parents=True)
    versions_yaml.write_text(
        "detected:\n  container:\n    image_digest: " + DIGEST + "\n", encoding="utf-8"
    )
    return root


def test_get_command_schema_returns_level_a(catalogue_root: Path) -> None:
    result = get_command_schema(project_root=catalogue_root, command="STAT_NON_LINE")

    assert result.validation_level == "A"
    assert result.command_schema.command == "STAT_NON_LINE"
    assert result.keyword_variants is None


def test_get_command_schema_keyword_lists_every_variant(catalogue_root: Path) -> None:
    result = get_command_schema(
        project_root=catalogue_root,
        command="STAT_NON_LINE",
        keyword="COMPORTEMENT.RELATION",
    )

    assert result.keyword_variants is not None
    assert len(result.keyword_variants) == 1
    assert result.keyword_variants[0].variant_id == "bbbb"

    entry = json.loads(
        default_query_log_path(catalogue_root)
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert entry["tool"] == "get_command_schema"
    assert entry["returned"] == [
        {"identifier": "STAT_NON_LINE.COMPORTEMENT.RELATION#bbbb", "score": None}
    ]


def test_get_command_schema_unknown_command_fails_loudly(catalogue_root: Path) -> None:
    with pytest.raises(McpToolError, match="STAT_NON_LINEX"):
        get_command_schema(project_root=catalogue_root, command="STAT_NON_LINEX")


def test_analyze_comm_returns_level_a_and_never_journals_content(
    tmp_path: Path,
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")
    project_root = tmp_path / "project"
    project_root.mkdir()

    result = analyze_comm(project_root=project_root, comm_path=str(comm_path))

    assert result.validation_level == "A"
    assert len(result.analysis.statements) == 1
    assert result.analysis.statements[0].command == "LIRE_MAILLAGE"

    entry = json.loads(
        default_query_log_path(project_root)
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert entry["file_name"] == "case.comm"
    assert entry["file_fingerprint"] == result.analysis.file_hash
    assert "MAIL" not in json.dumps(entry)
    assert "LIRE_MAILLAGE" not in json.dumps(entry)


def test_analyze_comm_syntax_error_fails_loudly(tmp_path: Path) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text("def broken(:\n", encoding="utf-8")
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(McpToolError):
        analyze_comm(project_root=project_root, comm_path=str(comm_path))


def test_validate_comm_missing_workroot_fails_loudly(tmp_path: Path) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")

    with pytest.raises(McpToolError, match="ASTER_CONTAINER_WORKROOT"):
        validate_comm(
            project_root=tmp_path / "project", comm_path=str(comm_path), workroot=None
        )


def test_validate_comm_missing_file_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(McpToolError, match="Fichier introuvable"):
        validate_comm(
            project_root=tmp_path / "project",
            comm_path=str(tmp_path / "nope.comm"),
            workroot=tmp_path,
        )


def test_validate_comm_journals_only_name_and_fingerprint_never_content(
    catalogue_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")
    docker_bin = tmp_path / "docker"
    docker_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {0: {"id": 0, "ok": True}}

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    report = validate_comm(
        project_root=catalogue_root,
        comm_path=str(comm_path),
        workroot=tmp_path,
        docker_bin_env=str(docker_bin),
    )

    assert report.validation_level == "B"
    assert report.valid is True

    entry = json.loads(
        default_query_log_path(catalogue_root)
        .read_text(encoding="utf-8")
        .splitlines()[-1]
    )
    assert entry["tool"] == "validate_comm"
    assert entry["file_name"] == "case.comm"
    assert entry["file_fingerprint"].startswith("sha256:")
    assert "MAIL" not in json.dumps(entry)
    assert "LIRE_MAILLAGE" not in json.dumps(entry)
