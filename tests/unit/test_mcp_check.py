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
    ensure_command_executable,
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
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
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


def test_load_server_spec_rejects_missing_or_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASTER_TEST_UNSET_2", raising=False)
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


def test_project_dir_is_not_injected_by_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Lot 24 injected CLAUDE_PROJECT_DIR: the check passed where Claude Code
    # failed on an empty variable.
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "aster-expert": {"command": "${CLAUDE_PROJECT_DIR}/.venv/bin/srv"}
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(McpCheckError, match="non définie"):
        load_server_spec(tmp_path)


def test_default_value_applies_when_variable_is_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "aster-expert": {
                        "command": "${CLAUDE_PROJECT_DIR:-/opt/x}/bin/srv",
                        "env": {"A": "${CLAUDE_PROJECT_DIR:-}"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    spec = load_server_spec(tmp_path)
    assert spec.command == "/opt/x/bin/srv"
    assert spec.env == {"A": ""}


def test_repository_mcp_json_resolves_to_an_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    spec = load_server_spec(root)
    assert Path(spec.command) == root / ".venv" / "bin" / "aster-expert-mcp"
    assert spec.env["ASTER_EXPERT_ROOT"] == str(root)
    ensure_command_executable(spec)


def test_ensure_command_executable_rejects_absent_and_non_executable(
    tmp_path: Path,
) -> None:
    absent = ServerSpec(command=str(tmp_path / "absent"), args=[], env={})
    with pytest.raises(McpCheckError, match="introuvable"):
        ensure_command_executable(absent)
    plain = tmp_path / "plain"
    plain.write_text("x", encoding="utf-8")
    plain.chmod(0o644)
    with pytest.raises(McpCheckError, match="non exécutable"):
        ensure_command_executable(ServerSpec(command=str(plain), args=[], env={}))


def test_run_check_stops_when_configured_command_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    (tmp_path / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "aster-expert": {
                        "command": "${CLAUDE_PROJECT_DIR:-" + str(tmp_path) + "}/nope"
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(McpCheckError, match="introuvable après expansion"):
        asyncio.run(run_check(tmp_path))


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
