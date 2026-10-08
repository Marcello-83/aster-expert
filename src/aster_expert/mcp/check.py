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
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, ConfigDict

from aster_expert.mcp.logging import CALL_ORIGIN_ENV, CHECK_ORIGIN

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
    # Claude Code defines CLAUDE_PROJECT_DIR in the environment of the launched
    # server, not when it reads the configuration (lot 25): the expansion uses
    # the shell environment only. Injecting the variable here (lot 24) made the
    # check pass while Claude Code failed on an empty `${CLAUDE_PROJECT_DIR}`.
    variables = dict(os.environ)
    return ServerSpec(
        command=_expand(str(entry["command"]), variables),
        args=[_expand(str(arg), variables) for arg in entry.get("args", [])],
        env={
            str(key): _expand(str(value), variables)
            for key, value in entry.get("env", {}).items()
        },
    )


def ensure_command_executable(
    spec: ServerSpec, project_root: Path | None = None
) -> Path:
    """Resolve the expanded command to an existing executable file, else fail.

    A bare name (`uv`) is looked up in `PATH`, as Claude Code does; a relative
    path is taken from `project_root`, the directory Claude Code starts a
    project-scoped stdio server in (documentation « MCP », lot 41 ter).
    """
    if "/" not in spec.command:
        found = shutil.which(spec.command)
        if found is None:
            message = (
                f"commande du serveur introuvable après expansion : {spec.command} "
                "(absente du PATH)"
            )
            raise McpCheckError(message)
        command = Path(found)
    else:
        command = Path(spec.command)
        if not command.is_absolute() and project_root is not None:
            command = project_root / command
    if not command.is_file():
        message = f"commande du serveur introuvable après expansion : {spec.command}"
        raise McpCheckError(message)
    if not os.access(command, os.X_OK):
        message = f"commande du serveur non exécutable : {spec.command}"
        raise McpCheckError(message)
    return command


SERVER_ENTRY_POINT = "aster-expert-mcp"


def uv_project_args(spec: ServerSpec, project_root: Path) -> list[str]:
    """Arguments of a `uv run ... aster-expert-mcp` launch, server name removed.

    The value of `--project` is made absolute from `project_root`, so that the
    arguments mean the same whatever the caller's working directory.
    """
    args = list(spec.args)
    if not args or args[0] != "run" or args[-1] != SERVER_ENTRY_POINT:
        message = (
            f"lancement par uv attendu sous la forme `uv run ... {SERVER_ENTRY_POINT}`"
            f", trouvé : uv {' '.join(args)}"
        )
        raise McpCheckError(message)
    args = args[:-1]
    if "--project" not in args:
        message = "lancement par uv sans `--project` : le .venv utilisé serait ambigu"
        raise McpCheckError(message)
    index = args.index("--project") + 1
    if index >= len(args):
        message = "`--project` sans valeur dans .mcp.json"
        raise McpCheckError(message)
    directory = Path(args[index])
    if not directory.is_absolute():
        directory = project_root / directory
    args[index] = str(directory.resolve())
    return args


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


async def _probe_constats(session: ClientSession, work_dir: Path) -> list[ToolCheck]:
    del work_dir
    request = {"command": "AFFE_CHAR_MECA", "limit": 1}
    found = await _call(session, "search_constats", request)
    hit = _first(found, "results", "search_constats")
    return [
        ToolCheck(
            tool="search_constats",
            request=request,
            summary=f"{hit['constat_id']}, level {found.get('validation_level')}",
        )
    ]


async def _probe_connaissances(
    session: ClientSession, work_dir: Path
) -> list[ToolCheck]:
    del work_dir
    request: dict[str, Any] = {"keyword": "FORCE_COQUE", "limit": 1}
    found = await _call(session, "search_connaissances", request)
    hit = _first(found, "results", "search_connaissances")
    return [
        ToolCheck(
            tool="search_connaissances",
            request=request,
            summary=(
                f"{hit['id']} ({hit['layer']}, {hit['status']}), level "
                f"{found.get('validation_level')}"
            ),
        )
    ]


def _project_with_deliverables(project_root: Path) -> str | None:
    """First project (alphabetical order) whose deliverables exist: the trunk names
    no project (`tests/unit/test_tronc_commun_sans_ouvrage.py`)."""
    root = project_root / "projets"
    if not root.is_dir():
        return None
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        if (directory / "resultats" / "livrables" / "manifeste.json").is_file():
            return directory.name
    return None


async def _probe_query_results(session: Any, work_dir: Path) -> list[ToolCheck]:
    """Lot 49: one extremum of the displacements read in the deliverables of the
    first project that has them."""
    project_root = work_dir.parents[3] if len(work_dir.parents) > 3 else work_dir
    name = _project_with_deliverables(project_root)
    if name is None:
        message = (
            "query_results : aucun projet n'a de livrables (aster-expert projet <nom> "
            "livrables) ; l'outil ne peut pas être appelé sur une requête minimale"
        )
        raise McpCheckError(message)
    request: dict[str, Any] = {
        "projet": name,
        "champ": "DEPL",
        "mode": "extremum",
        "limite": 50,
    }
    found = await _call(session, "query_results", request)
    row = _first(found, "rows", "query_results")
    return [
        ToolCheck(
            tool="query_results",
            request=request,
            summary=(
                f"{row['composante']} {row['extremum']} = {row['valeur_si']} "
                f"{row['unite_si']}, level {found.get('validation_level')}"
            ),
        )
    ]


# One probe per group of tools. A declared tool covered by no probe fails the
# check: whoever adds a tool must also give it a minimal request here.
_PROBES: dict[str, Probe] = {
    "search_codeaster_docs": _probe_docs,
    "get_command_schema": _probe_schema,
    "analyze_comm": _probe_comm,
    "search_test_cases": _probe_test_cases,
    "search_constats": _probe_constats,
    "search_connaissances": _probe_connaissances,
    "query_results": _probe_query_results,
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
    spec_from_config = spec is None
    spec = spec if spec is not None else load_server_spec(project_root)
    expected = expected if expected is not None else declared_tools()
    command = spec.command
    if spec_from_config:
        command = str(ensure_command_executable(spec, project_root))
    unprobed = sorted(
        tool for tool in expected if tool not in _PROBES and tool not in _COVERED_BY
    )
    if unprobed:
        message = f"aucune requête minimale définie pour : {unprobed} (mcp/check.py)"
        raise McpCheckError(message)

    parameters = StdioServerParameters(
        command=command,
        args=spec.args,
        env={**spec.env, CALL_ORIGIN_ENV: CHECK_ORIGIN},
        cwd=project_root,
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
            # Under data/processed (read policy, lot 46): a system temp directory
            # is outside every read root, the probe would be refused.
            scratch = project_root / "data" / "processed" / "mcp_check"
            scratch.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="aster-expert-mcp-check-", dir=scratch
            ) as tmp:
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
    "ensure_command_executable",
    "load_server_spec",
    "run_check",
    "uv_project_args",
]
