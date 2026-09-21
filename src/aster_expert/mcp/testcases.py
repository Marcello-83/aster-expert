"""Read-only access to the command files of the official test cases (lot 22).

Lot 21 had to read `.comm` files of `external/codeaster-src/astest` directly,
because no MCP tool reached them (the documentary index holds the manuals,
not the test-case sources). This module closes that gap with two functions,
both read-only:

- `search_testcases` finds the command files that use a given command, and
  optionally a given keyword, by confronting the request with the structure
  the project's own parser (`aster_expert.parsing.comm_parser`) reconstructs
  -- never a text search alone, which would match comments and strings;
- `read_testcase` returns one command file, whole under a size threshold and
  by line range above it, exactly like `get_document_section`.

The corpus is `external/codeaster-src/astest` at the commit the last
synchronisation recorded (`data/raw/manifest.json`). If the working copy no
longer sits on that commit, or carries local modifications, both functions
refuse to answer rather than describe a corpus nobody recorded (CLAUDE.md,
principe 1 and "Gestion des dépôts externes").

Only command files are served (`.comm`, `.com1`, `.com2`, ...): a path is
resolved and must stay inside the corpus root, so `..` or an absolute path
outside it is refused.

Level A: a test case is an executable reference, not a template
(CLAUDE.md, principe 5), and reading one proves nothing about any other file.
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.ingestion.git_client import (
    GitCommandError,
    current_commit,
    working_copy_dirty,
)
from aster_expert.mcp.errors import McpToolError
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.parsing.errors import CommParseError
from aster_expert.parsing.models import KeywordNode, Statement

SOURCE_NAME = "codeaster-src"
CORPUS_SUBDIR = Path("astest")
MAX_FILE_CHARS = 20_000
_COMMAND_FILE = re.compile(r"\.com(m|\d+)$")

KeywordPath = tuple[str, ...]


class TestcaseSource(BaseModel):
    """Provenance of the corpus that answered (CLAUDE.md, principe 4)."""

    __test__ = False
    model_config = ConfigDict(frozen=True)

    source_name: str
    source_commit: str
    aster_version: str | None
    corpus_root: str


class TestcaseHit(BaseModel):
    """One command file using the requested command (and keyword)."""

    __test__ = False
    model_config = ConfigDict(frozen=True)

    path: str
    line_starts: list[int]
    """First line of each matching statement (the command itself)."""
    keyword_paths: list[str]
    """Dotted paths of the requested keyword found in those statements; empty
    when no keyword was requested."""


class SearchTestcasesResult(BaseModel):
    __test__ = False
    model_config = ConfigDict(frozen=True)

    validation_level: str = "A"
    command: str
    keyword: str | None
    source: TestcaseSource
    files_scanned: int
    files_unparsable: int
    """Files that contain the command name but that the parser could not read;
    reported, never silently skipped."""
    total_matches: int
    results: list[TestcaseHit]
    truncated: bool


class TestcaseFileResult(BaseModel):
    __test__ = False
    model_config = ConfigDict(frozen=True)

    validation_level: str = "A"
    path: str
    source: TestcaseSource
    total_lines: int
    content_length: int
    line_start: int | None
    line_end: int | None
    content: str | None
    guidance: str | None


def _manifest_entry(project_root: Path) -> dict[str, str]:
    manifest = project_root / "data" / "raw" / "manifest.json"
    if not manifest.is_file():
        message = (
            f"Manifeste de synchronisation introuvable ({manifest}) ; lancez "
            "'aster-expert sources sync' d'abord"
        )
        raise McpToolError(message)
    for entry in json.loads(manifest.read_text(encoding="utf-8"))["sources"]:
        if entry["name"] == SOURCE_NAME:
            return {k: str(v) for k, v in entry.items() if v is not None}
    message = f"Source {SOURCE_NAME!r} absente du manifeste {manifest}"
    raise McpToolError(message)


def resolve_corpus(project_root: Path) -> tuple[Path, TestcaseSource]:
    """Return the corpus root and its provenance, or refuse.

    The working copy must sit on the commit the manifest recorded, unmodified.
    """
    entry = _manifest_entry(project_root)
    repo = project_root / entry["local_path"]
    root = repo / CORPUS_SUBDIR
    if not root.is_dir():
        message = f"Corpus des cas tests introuvable : {root}"
        raise McpToolError(message)
    try:
        head = current_commit(repo)
        dirty = working_copy_dirty(repo)
    except GitCommandError as exc:
        raise McpToolError(str(exc)) from exc
    if head != entry["commit"]:
        message = (
            f"La copie de travail {repo} est au commit {head}, le manifeste "
            f"enregistre {entry['commit']} : corpus refusé (jamais mélanger "
            "deux révisions en silence)"
        )
        raise McpToolError(message)
    if dirty:
        message = f"La copie de travail {repo} porte des modifications locales : refusé"
        raise McpToolError(message)
    source = TestcaseSource(
        source_name=SOURCE_NAME,
        source_commit=head,
        aster_version=entry.get("ref"),
        corpus_root=str(root),
    )
    return root, source


def _keyword_paths(
    keywords: dict[str, KeywordNode], prefix: KeywordPath = ()
) -> list[KeywordPath]:
    paths: list[KeywordPath] = []
    for name, node in keywords.items():
        here = (*prefix, name)
        paths.append(here)
        if node.node == "factor":
            for occurrence in node.occurrences:
                paths.extend(_keyword_paths(occurrence.keywords, here))
    return paths


# (path -> statements): parsing is the cost, the corpus never changes under a
# fixed commit, so a process-lifetime memo is enough.
_parse_cache: dict[Path, list[Statement] | None] = {}


def _statements(path: Path) -> list[Statement] | None:
    if path not in _parse_cache:
        try:
            source = path.read_text(encoding="utf-8")
            # Corpus files carry legacy escape sequences in strings; the
            # interpreter's warning about them is noise here, not a finding.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                statements: list[Statement] | None = parse_comm_source(
                    source, file_path=str(path)
                ).statements
        except (CommParseError, UnicodeDecodeError):
            statements = None
        _parse_cache[path] = statements
    return _parse_cache[path]


def clear_parse_cache() -> None:
    """Test-only."""
    _parse_cache.clear()


def command_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.iterdir() if p.is_file() and _COMMAND_FILE.search(p.name)
    )


def search_testcases(
    root: Path,
    source: TestcaseSource,
    *,
    command: str,
    keyword: str | None = None,
    limit: int = 50,
) -> SearchTestcasesResult:
    if limit < 1:
        message = "limit doit être au moins 1"
        raise McpToolError(message)
    wanted = tuple(keyword.split(".")) if keyword else None
    name = re.compile(rf"\b{re.escape(command)}\b")
    # Cheap textual pre-filter only: the structural match below decides.
    last = re.compile(rf"\b{re.escape(wanted[-1])}\b") if wanted else None
    files = command_files(root)
    unparsable = 0
    hits: list[TestcaseHit] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not name.search(text) or (last is not None and not last.search(text)):
            continue
        statements = _statements(path)
        if statements is None:
            unparsable += 1
            continue
        lines: list[int] = []
        found: list[str] = []
        for statement in statements:
            if statement.command != command:
                continue
            if wanted is not None:
                matching = [
                    ".".join(p)
                    for p in _keyword_paths(statement.keywords)
                    if p[-len(wanted) :] == wanted
                ]
                if not matching:
                    continue
                found.extend(matching)
            lines.append(statement.line_start)
        if lines:
            hits.append(
                TestcaseHit(
                    path=path.name,
                    line_starts=lines,
                    keyword_paths=sorted(set(found)),
                )
            )
    return SearchTestcasesResult(
        command=command,
        keyword=keyword,
        source=source,
        files_scanned=len(files),
        files_unparsable=unparsable,
        total_matches=len(hits),
        results=hits[:limit],
        truncated=len(hits) > limit,
    )


def _resolve_inside(root: Path, requested: str) -> Path:
    candidate = (root / requested).resolve()
    if candidate.parent != root.resolve() or not _COMMAND_FILE.search(candidate.name):
        message = (
            f"Chemin refusé : {requested!r} n'est pas un fichier de commandes "
            f"(.comm, .comN) situé directement dans le corpus {root}"
        )
        raise McpToolError(message)
    if not candidate.is_file():
        message = f"Cas test introuvable dans le corpus : {requested!r}"
        raise McpToolError(message)
    return candidate


def read_testcase(
    root: Path,
    source: TestcaseSource,
    *,
    path: str,
    line_start: int | None = None,
    line_end: int | None = None,
    max_chars: int = MAX_FILE_CHARS,
) -> TestcaseFileResult:
    if (line_start is None) != (line_end is None):
        message = "line_start et line_end doivent être donnés ensemble."
        raise McpToolError(message)
    target = _resolve_inside(root, path)
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    text = "\n".join(lines)
    if line_start is None or line_end is None:
        if len(text) > max_chars:
            return TestcaseFileResult(
                path=target.name,
                source=source,
                total_lines=total,
                content_length=len(text),
                line_start=1,
                line_end=total,
                content=None,
                guidance=(
                    f"Fichier de {len(text)} caractères, au-delà du seuil "
                    f"({max_chars}) : demander une plage via line_start/"
                    f"line_end, dans les bornes 1..{total}."
                ),
            )
        return TestcaseFileResult(
            path=target.name,
            source=source,
            total_lines=total,
            content_length=len(text),
            line_start=1,
            line_end=total,
            content=text,
            guidance=None,
        )
    if not 1 <= line_start <= line_end <= total:
        message = (
            f"Plage {line_start}-{line_end} hors des bornes du fichier (1..{total})."
        )
        raise McpToolError(message)
    chunk = "\n".join(lines[line_start - 1 : line_end])
    if len(chunk) > max_chars:
        message = (
            f"Plage de {len(chunk)} caractères, au-delà du seuil ({max_chars}) : "
            "demander une plage plus étroite."
        )
        raise McpToolError(message)
    return TestcaseFileResult(
        path=target.name,
        source=source,
        total_lines=total,
        content_length=len(text),
        line_start=line_start,
        line_end=line_end,
        content=chunk,
        guidance=None,
    )


__all__: list[str] = [
    "SearchTestcasesResult",
    "TestcaseFileResult",
    "TestcaseHit",
    "TestcaseSource",
    "clear_parse_cache",
    "read_testcase",
    "resolve_corpus",
    "search_testcases",
]
