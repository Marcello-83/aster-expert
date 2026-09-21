"""Tests for `aster_expert.mcp.check` (lot 24): no network, no Docker.

The mismatch case starts a real stub server in a subprocess (a fresh process
is the point of the check) that exposes fewer tools than the code declares.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from aster_expert.mcp.check import (
    McpCheckError,
    ServerSpec,
    declared_tools,
    load_server_spec,
    run_check,
)
from aster_expert.mcp.server import app

_STUB = """
from mcp.server.mcpserver import MCPServer

app = MCPServer(name="stub")


@app.tool()
def search_codeaster_docs(query: str) -> dict:
    return {}


app.run(transport="stdio")
"""


def test_declared_tools_match_the_registered_ones() -> None:
    registered = sorted(tool.name for tool in asyncio.run(app.list_tools()))
    assert declared_tools() == registered
    assert "read_test_case" in registered


def test_declared_tools_reads_decorated_functions(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        "@app.tool(description='x')\ndef a(): ...\n\n"
        "@app.tool\ndef b(): ...\n\n"
        "def c(): ...\n\n"
        "@other.tool()\ndef d(): ...\n",
        encoding="utf-8",
    )
    assert declared_tools(source) == ["a", "b"]


def test_load_server_spec_expands_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASTER_TEST_UNSET", raising=False)
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "aster-expert": {
                        "command": "${CLAUDE_PROJECT_DIR}/.venv/bin/srv",
                        "args": ["--x", "${ASTER_TEST_UNSET:-fallback}"],
                        "env": {"ROOT": "${CLAUDE_PROJECT_DIR}"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    spec = load_server_spec(tmp_path)
    assert spec.command == f"{tmp_path}/.venv/bin/srv"
    assert spec.args == ["--x", "fallback"]
    assert spec.env == {"ROOT": str(tmp_path)}


def test_load_server_spec_rejects_missing_or_unset(tmp_path: Path) -> None:
    with pytest.raises(McpCheckError, match="introuvable"):
        load_server_spec(tmp_path)
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {"aster-expert": {"command": "${ASTER_TEST_UNSET_2}"}}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(McpCheckError, match="non définie"):
        load_server_spec(tmp_path)


def test_repository_mcp_json_declares_the_server() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = load_server_spec(root)
    assert Path(spec.command) == root / ".venv" / "bin" / "aster-expert-mcp"
    assert spec.env["ASTER_EXPERT_ROOT"] == str(root)


def test_run_check_fails_on_missing_tools(tmp_path: Path) -> None:
    stub = tmp_path / "stub.py"
    stub.write_text(_STUB, encoding="utf-8")
    spec = ServerSpec(command=sys.executable, args=[str(stub)], env={})
    with pytest.raises(McpCheckError, match="manquants") as info:
        asyncio.run(run_check(tmp_path, spec=spec))
    assert "read_test_case" in str(info.value)


def test_run_check_fails_on_tool_without_minimal_request(tmp_path: Path) -> None:
    spec = ServerSpec(command=sys.executable, args=["-c", "pass"], env={})
    with pytest.raises(McpCheckError, match="aucune requête minimale"):
        asyncio.run(run_check(tmp_path, spec=spec, expected=["new_tool"]))


def test_run_check_fails_when_server_cannot_start(tmp_path: Path) -> None:
    spec = ServerSpec(command=str(tmp_path / "absent"), args=[], env={})
    with pytest.raises(McpCheckError, match="démarrage"):
        asyncio.run(run_check(tmp_path, spec=spec))
