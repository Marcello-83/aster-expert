"""Start-up check of the MCP server (lot 24).

A Claude Code session keeps the server process it started at launch: code
added afterwards is invisible to it (lot 23: `search_test_cases` and
`read_test_case` missing). This module starts a *fresh* server exactly as
`.mcp.json` declares it, lists its tools, compares them to those the source
of `aster_expert.mcp.server` declares, then calls each one on a minimal
request. It stops at the first discrepancy.

The declared tools are read from the source (`ast`), not from the imported
`app`: the comparison must not depend on the code it checks importing cleanly
in this same process.
"""

from __future__ import annotations

import ast
import json
import os
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, ConfigDict

SERVER_NAME = "aster-expert"
_SERVER_SOURCE = Path(__file__).with_name("server.py")
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
_MINIMAL_COMM = "DEBUT()\nFIN()\n"


class McpCheckError(Exception):
    """The fresh server does not match the code, or a tool call failed."""


class ServerSpec(BaseModel):
    """Launch command of the server, as `.mcp.json` declares it."""

    model_config = ConfigDict(frozen=True)

    command: str
    args: list[str]
    env: dict[str, str]


class ToolCheck(BaseModel):
    """Outcome of one tool's minimal call."""

    model_config = ConfigDict(frozen=True)

    tool: str
    request: dict[str, Any]
    summary: str


def _expand(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        value = variables.get(name)
        if value is None:
            if default is None:
                message = f".mcp.json : variable ${{{name}}} non définie"
                raise McpCheckError(message)
            return default
        return value

    return _VAR.sub(replace, text)


def load_server_spec(project_root: Path) -> ServerSpec:
    """Read `.mcp.json` and expand `${VAR}` / `${VAR:-default}` as Claude Code does."""
    config_path = project_root / ".mcp.json"
    if not config_path.is_file():
        message = f"Configuration MCP de projet introuvable : {config_path}"
        raise McpCheckError(message)
    try:
        servers = json.loads(config_path.read_text(encoding="utf-8"))["mcpServers"]
        entry = servers[SERVER_NAME]
    except (ValueError, KeyError, TypeError) as exc:
        message = f"{config_path} ne déclare pas le serveur {SERVER_NAME!r} ({exc!r})"
        raise McpCheckError(message) from exc
    variables = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_root)}
    return ServerSpec(
        command=_expand(str(entry["command"]), variables),
        args=[_expand(str(arg), variables) for arg in entry.get("args", [])],
        env={
            str(key): _expand(str(value), variables)
            for key, value in entry.get("env", {}).items()
        },
    )


def declared_tools(server_source: Path = _SERVER_SOURCE) -> list[str]:
    """Names of the functions `server.py` registers with `@app.tool(...)`."""
    tree = ast.parse(server_source.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "tool"
                and isinstance(target.value, ast.Name)
                and target.value.id == "app"
            ):
                names.append(node.name)
    return sorted(names)


def _payload(result: Any) -> dict[str, Any]:
    if result.is_error:
        text = " ".join(getattr(block, "text", "") for block in result.content)
        message = f"outil en erreur : {text.strip()}"
        raise McpCheckError(message)
    structured = result.structured_content
    if not isinstance(structured, dict):
        message = "réponse sans contenu structuré"
        raise McpCheckError(message)
    return structured


async def _call(
    session: ClientSession, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    try:
        result = await session.call_tool(tool, arguments)
    except Exception as exc:
        message = f"{tool} {arguments} : {exc!r}"
        raise McpCheckError(message) from exc
    try:
        return _payload(result)
    except McpCheckError as exc:
        message = f"{tool} {arguments} : {exc}"
        raise McpCheckError(message) from exc


def _first(payload: dict[str, Any], key: str, tool: str) -> dict[str, Any]:
    items = payload.get(key)
    if not isinstance(items, list) or not items:
        message = f"{tool} : `{key}` vide sur la requête minimale"
        raise McpCheckError(message)
    first = items[0]
    if not isinstance(first, dict):
        message = f"{tool} : `{key}` mal formé"
        raise McpCheckError(message)
    return first


def _first_check_error(
    group: BaseExceptionGroup[BaseException],
) -> McpCheckError | None:
    for error in group.exceptions:
        if isinstance(error, McpCheckError):
            return error
        if isinstance(error, BaseExceptionGroup):
            nested = _first_check_error(error)
            if nested is not None:
                return nested
    return None


Probe = Callable[[ClientSession, Path], Awaitable[list[ToolCheck]]]


async def _probe_docs(session: ClientSession, work_dir: Path) -> list[ToolCheck]:
    del work_dir
    request = {"query": "STAT_NON_LINE", "k": 1}
    search = await _call(session, "search_codeaster_docs", request)
    hit = _first(search, "results", "search_codeaster_docs")
    fragment_id = str(hit["fragment_id"])
    section = await _call(
        session,
        "get_document_section",
        {"fragment_id": fragment_id, "granularity": hit.get("granularity", "by_file")},
    )
    return [
        ToolCheck(tool="search_codeaster_docs", request=request, summary=fragment_id),
        ToolCheck(
            tool="get_document_section",
            request={"fragment_id": fragment_id},
            summary=f"level {section.get('validation_level')}",
        ),
    ]


async def _probe_schema(session: ClientSession, work_dir: Path) -> list[ToolCheck]:
    del work_dir
    request = {"command": "STAT_NON_LINE"}
    schema = await _call(session, "get_command_schema", request)
    return [
        ToolCheck(
            tool="get_command_schema",
            request=request,
            summary=f"level {schema.get('validation_level')}",
        )
    ]


async def _probe_comm(session: ClientSession, work_dir: Path) -> list[ToolCheck]:
    comm = work_dir / "minimal.comm"
    comm.write_text(_MINIMAL_COMM, encoding="utf-8")
    request = {"comm_path": str(comm)}
    analysis = await _call(session, "analyze_comm", request)
    report = await _call(session, "validate_comm", request)
    return [
        ToolCheck(
            tool="analyze_comm",
            request=request,
            summary=f"level {analysis.get('validation_level')}",
        ),
        ToolCheck(
            tool="validate_comm",
            request=request,
            summary=(
                f"level {report.get('validation_level')}, valid={report.get('valid')}"
            ),
        ),
    ]


async def _probe_test_cases(session: ClientSession, work_dir: Path) -> list[ToolCheck]:
    del work_dir
    request = {"command": "AFFE_MODELE", "limit": 1}
    search = await _call(session, "search_test_cases", request)
    hit = _first(search, "results", "search_test_cases")
    path = str(hit["path"])
    read = await _call(
        session, "read_test_case", {"path": path, "line_start": 1, "line_end": 5}
    )
    return [
        ToolCheck(tool="search_test_cases", request=request, summary=path),
        ToolCheck(
            tool="read_test_case",
            request={"path": path},
            summary=f"level {read.get('validation_level')}",
        ),
    ]


# One probe per group of tools. A declared tool covered by no probe fails the
# check: whoever adds a tool must also give it a minimal request here.
_PROBES: dict[str, Probe] = {
    "search_codeaster_docs": _probe_docs,
    "get_command_schema": _probe_schema,
    "analyze_comm": _probe_comm,
    "search_test_cases": _probe_test_cases,
}
_COVERED_BY: dict[str, str] = {
    "get_document_section": "search_codeaster_docs",
    "validate_comm": "analyze_comm",
    "read_test_case": "search_test_cases",
}


async def run_check(
    project_root: Path,
    *,
    spec: ServerSpec | None = None,
    expected: list[str] | None = None,
) -> list[ToolCheck]:
    """Start a fresh server, compare its tools to the code, call each one.

    Raises `McpCheckError` at the first discrepancy.
    """
    spec = spec if spec is not None else load_server_spec(project_root)
    expected = expected if expected is not None else declared_tools()
    unprobed = sorted(
        tool for tool in expected if tool not in _PROBES and tool not in _COVERED_BY
    )
    if unprobed:
        message = f"aucune requête minimale définie pour : {unprobed} (mcp/check.py)"
        raise McpCheckError(message)

    parameters = StdioServerParameters(
        command=spec.command, args=spec.args, env=spec.env, cwd=project_root
    )
    checks: list[ToolCheck] = []
    try:
        async with (
            stdio_client(parameters) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            listed = sorted(tool.name for tool in (await session.list_tools()).tools)
            if listed != expected:
                message = (
                    f"outils du serveur {listed} ≠ outils déclarés dans le code "
                    f"{expected} : manquants {sorted(set(expected) - set(listed))}, "
                    f"en trop {sorted(set(listed) - set(expected))}"
                )
                raise McpCheckError(message)
            with tempfile.TemporaryDirectory(prefix="aster-expert-mcp-check-") as tmp:
                for tool, probe in _PROBES.items():
                    if tool in expected:
                        checks.extend(await probe(session, Path(tmp)))
    except BaseExceptionGroup as group:
        # anyio wraps what is raised inside the client's task group.
        found = _first_check_error(group)
        if found is None:
            raise
        raise found from None
    except OSError as exc:
        message = f"démarrage du serveur impossible ({spec.command}) : {exc}"
        raise McpCheckError(message) from exc
    return checks


__all__: list[str] = [
    "McpCheckError",
    "ServerSpec",
    "ToolCheck",
    "declared_tools",
    "load_server_spec",
    "run_check",
]
