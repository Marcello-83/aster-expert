"""Append-only journal of MCP tool calls (lot 8, H3).

Every call to a tool exposed by `aster_expert.mcp.server` appends exactly one
line to `data/processed/query_log.jsonl`: timestamp, tool name, query,
profile, filters, the identifiers of whatever was returned with their
scores, and duration. This is the evidence base the lot C1 decision (whether
a vector index is justified) will be made from, so every field it needs must
already be here from the first real call — never patched in retroactively.

The content of a user file is never journaled: for `analyze_comm` and
`validate_comm`, only the file's name and its `sha256:...` fingerprint are
recorded (`file_name`/`file_fingerprint`), never its text (CLAUDE.md, lot 8
H3). This module has exactly one responsibility, appending; it never reads
the log back, summarizes it, or aggregates it — that belongs to whichever
lot actually consumes it (docs/development-plan.md, lot C1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ReturnedItem(BaseModel):
    """One identifier a tool call returned, with its score if it has one.

    `score` is `None` for a tool that does not rank anything (e.g.
    `get_command_schema`), never a fabricated `0.0` or `1.0` standing in for
    "not applicable".
    """

    model_config = ConfigDict(frozen=True)

    identifier: str
    score: float | None = None


class QueryLogEntry(BaseModel):
    """One line of `data/processed/query_log.jsonl` (lot 8, H3)."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    tool: str
    query: str | None = None
    profile: str | None = None
    filters: dict[str, str | None] = Field(default_factory=dict)
    returned: list[ReturnedItem] = Field(default_factory=list)
    duration_s: float
    file_name: str | None = None
    file_fingerprint: str | None = None


def default_query_log_path(project_root: Path) -> Path:
    return project_root / "data" / "processed" / "query_log.jsonl"


def append_query_log(
    log_path: Path,
    *,
    tool: str,
    duration_s: float,
    query: str | None = None,
    profile: str | None = None,
    filters: dict[str, str | None] | None = None,
    returned: list[ReturnedItem] | None = None,
    file_name: str | None = None,
    file_fingerprint: str | None = None,
) -> QueryLogEntry:
    """Build one `QueryLogEntry` and append it as a single JSON line.

    A pydantic model is built (never a hand-assembled `dict`) so a caller
    that passes something the schema rejects fails loudly here rather than
    writing a malformed line to a journal nothing re-validates on read
    (CLAUDE.md, "modèles de données validés pour tout objet sérialisé").
    """
    entry = QueryLogEntry(
        timestamp=datetime.now(UTC),
        tool=tool,
        query=query,
        profile=profile,
        filters=filters or {},
        returned=returned or [],
        duration_s=duration_s,
        file_name=file_name,
        file_fingerprint=file_fingerprint,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry.model_dump_json() + "\n")
    return entry
