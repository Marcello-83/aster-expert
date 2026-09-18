"""Integration tests for the MCP server (lot 8, H5).

Exercises the actual MCP protocol layer (`MCPServer.call_tool`, the same
entry point a real client session uses) end to end, against a reduced
corpus/catalogue built in `tmp_path` — no network, no Docker
(`validate_comm`'s one Docker-dependent call is monkeypatched exactly like
`tests/unit/test_validate.py` does). Every tool is reached through
`aster_expert.mcp.server.app`, never by calling `aster_expert.mcp.tools`
directly (that is what `tests/unit/test_mcp_tools.py` covers): this file is
the "serveur interrogeable" exit criterion (docs/development-plan.md,
lot 8).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

import aster_expert.validation.validate as validate_module
from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir
from aster_expert.mcp.models import SearchDocsResult
from aster_expert.mcp.server import app

DIGEST = "sha256:testdigest"

_RETRIEVAL_YAML = """
defaults:
  source_priority:
    syntaxe: [catalogue, U4, U7, testcase, source]
    theorie: [R, U2, U4, U3, V]
    methode: [U2, U4, R, U3]
"""


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A reduced project tree: one indexed fragment, one catalogue command."""
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "config" / "retrieval.yaml").write_text(_RETRIEVAL_YAML, encoding="utf-8")
    (root / "config" / "versions.yaml").write_text(
        "detected:\n  container:\n    image_digest: " + DIGEST + "\n", encoding="utf-8"
    )

    fragments_path = root / "data" / "processed" / "fragments_by_file.jsonl"
    fragments_path.parent.mkdir(parents=True)
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
    fragments_path.write_text(json.dumps(fragment) + "\n", encoding="utf-8")
    build_bm25_index(fragments_path, default_index_dir(root, "by_file"))

    catalogue_dir = root / "data" / "processed" / "catalogue" / DIGEST
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
        "keywords": [],
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    (catalogue_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(schema), encoding="utf-8"
    )
    return root


@pytest.fixture(autouse=True)
def _project_env(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(project_root))


def test_search_codeaster_docs_via_mcp_call_tool(project_root: Path) -> None:
    res = _run(
        app.call_tool(
            "search_codeaster_docs",
            {"query": "comportement non linéaire", "profile": "syntaxe", "k": 5},
        )
    )

    assert res.is_error is False
    payload = res.structured_content
    assert payload["validation_level"] == "A"
    assert payload["profile"] == "syntaxe"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["document_id"] == "U4.51.03"


def test_get_document_section_via_mcp_call_tool(project_root: Path) -> None:
    res = _run(
        app.call_tool("get_document_section", {"fragment_id": "U4.51.03#COMPORTEMENT"})
    )

    assert res.is_error is False
    payload = res.structured_content
    assert payload["validation_level"] == "A"
    assert payload["section"]["fragment_id"] == "U4.51.03#COMPORTEMENT"
    assert payload["section"]["content"] == (
        "Mot-clé facteur COMPORTEMENT : loi de comportement non linéaire."
    )


def test_get_document_section_chains_off_a_search_hit(project_root: Path) -> None:
    """K2: a `SearchHit`'s own fields, unmodified, resolve through this tool."""
    search_res = _run(
        app.call_tool(
            "search_codeaster_docs",
            {"query": "comportement non linéaire", "profile": "syntaxe"},
        )
    )
    hit = search_res.structured_content["results"][0]

    section_res = _run(
        app.call_tool(
            "get_document_section",
            {
                "document_id": hit["document_id"],
                "section_path": list(hit["section_path"]),
                "granularity": hit["granularity"],
            },
        )
    )

    assert section_res.is_error is False
    assert (
        section_res.structured_content["section"]["fragment_id"]
        == "U4.51.03#COMPORTEMENT"
    )


def test_get_document_section_unknown_fragment_is_an_anticipated_tool_error(
    project_root: Path,
) -> None:
    with pytest.raises(ToolError) as excinfo:
        _run(app.call_tool("get_document_section", {"fragment_id": "nope"}))

    assert not isinstance(excinfo.value, UnexpectedToolError)
    assert "Aucun fragment" in str(excinfo.value)


def test_get_document_section_with_range_via_mcp_call_tool(project_root: Path) -> None:
    """L1: line_start/line_end are reachable through the real MCP transport."""
    res = _run(
        app.call_tool(
            "get_document_section",
            {
                "fragment_id": "U4.51.03#COMPORTEMENT",
                "line_start": 1,
                "line_end": 10,
            },
        )
    )

    assert res.is_error is False
    payload = res.structured_content
    assert payload["section"]["is_full_section"] is True
    assert payload["section"]["requested_line_start"] == 1
    assert payload["section"]["requested_line_end"] == 10


def test_get_document_section_range_mismatch_is_an_anticipated_tool_error(
    project_root: Path,
) -> None:
    with pytest.raises(ToolError) as excinfo:
        _run(
            app.call_tool(
                "get_document_section",
                {"fragment_id": "U4.51.03#COMPORTEMENT", "line_start": 5},
            )
        )

    assert not isinstance(excinfo.value, UnexpectedToolError)
    assert "line_start et line_end" in str(excinfo.value)


def test_get_command_schema_via_mcp_call_tool(project_root: Path) -> None:
    res = _run(app.call_tool("get_command_schema", {"command": "STAT_NON_LINE"}))

    assert res.is_error is False
    payload = res.structured_content
    assert payload["validation_level"] == "A"
    assert payload["command_schema"]["command"] == "STAT_NON_LINE"
    assert payload["keyword_variants"] is None


def test_analyze_comm_via_mcp_call_tool(project_root: Path, tmp_path: Path) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")

    res = _run(app.call_tool("analyze_comm", {"comm_path": str(comm_path)}))

    assert res.is_error is False
    payload = res.structured_content
    assert payload["validation_level"] == "A"
    assert payload["analysis"]["statements"][0]["command"] == "LIRE_MAILLAGE"


def test_validate_comm_via_mcp_call_tool(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")
    docker_bin = tmp_path / "docker"
    docker_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setenv("ASTER_CONTAINER_WORKROOT", str(tmp_path))
    monkeypatch.setenv("ASTER_DOCKER_BIN", str(docker_bin))

    def fake_run_checks(
        requests: list[dict[str, Any]], **kwargs: Any
    ) -> dict[int, dict[str, Any]]:
        return {0: {"id": 0, "ok": True}}

    monkeypatch.setattr(validate_module, "run_checks", fake_run_checks)

    res = _run(app.call_tool("validate_comm", {"comm_path": str(comm_path)}))

    assert res.is_error is False
    payload = res.structured_content
    assert payload["validation_level"] == "B"
    assert payload["valid"] is True


def test_validate_comm_without_workroot_is_an_anticipated_tool_error(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASTER_CONTAINER_WORKROOT", raising=False)
    comm_path = tmp_path / "case.comm"
    comm_path.write_text('MAIL = LIRE_MAILLAGE(FORMAT="MED")\n', encoding="utf-8")

    with pytest.raises(ToolError, match="ASTER_CONTAINER_WORKROOT"):
        _run(app.call_tool("validate_comm", {"comm_path": str(comm_path)}))


def test_unknown_profile_is_an_anticipated_tool_error_not_a_crash(
    project_root: Path,
) -> None:
    with pytest.raises(ToolError) as excinfo:
        _run(app.call_tool("search_codeaster_docs", {"query": "x", "profile": "bogus"}))

    assert not isinstance(excinfo.value, UnexpectedToolError)
    assert "Profil inconnu" in str(excinfo.value)


def test_invalid_output_contract_fails_loudly_never_partial(project_root: Path) -> None:
    """A tool whose return value violates its own declared pydantic contract
    must make the call fail outright (`UnexpectedToolError`), never come back
    as a partial or silently-coerced result (docs/development-plan.md, lot 8,
    H5). Exercised on a throwaway server/tool, not the four real ones, so the
    fault is unambiguously the output-contract check itself, not one real
    tool's own logic.
    """
    scratch_server: MCPServer = MCPServer(name="aster-expert-contract-test")

    @scratch_server.tool()
    def broken_search() -> SearchDocsResult:
        # Missing every field `SearchDocsResult` requires but `query`.
        return {"validation_level": "A", "query": "x"}  # type: ignore[return-value]

    with pytest.raises(UnexpectedToolError):
        _run(scratch_server.call_tool("broken_search", {}))
