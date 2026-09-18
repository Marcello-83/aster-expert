"""In-memory cache of the BM25 index and command schemas (lot 8b, J1).

`data/processed/query_log.jsonl` (lot 8's own journal) measured
`search_codeaster_docs`'s first real call at 5.2 s: `aster_expert.mcp.tools`
reloaded the BM25 index (`aster_expert.indexing.bm25_index.load_bm25_index`)
from disk on every single call, exactly as
`docs/development-plan.md` (clôture lot 8) already flagged as a known
limitation. `get_command_schema` (0.03 s) and `analyze_comm` (0.006 s) were
already under one second on the same measurement and are left untouched —
CLAUDE.md, "pas d'optimisation sans mesure" — but `get_command_schema` reads
from the same on-disk catalogue this cache also holds, so its schema lookup
is cached too rather than left as a second, inconsistent code path.

The cache is a pair of plain module-level dicts, alive for the lifetime of
the process that imports this module — the MCP server (`aster_expert.mcp.
server`) runs as one long-lived `stdio` process per `claude mcp add`
registration, never re-exec'd between tool calls, so process lifetime is
server lifetime. Nothing here is persisted to disk or shared across
processes; a server restart clears it for free. `validate_comm`'s own
duration (54 s, real `docker run`) is execution time, not a reload cost, and
is out of scope for this cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bm25s

from aster_expert.catalogue.models import CommandSchema

# Re-exported (not just imported) so tests can patch `cache_module.load_*`
# to count calls without patching the underlying modules directly.
from aster_expert.catalogue.query import load_command_schema as load_command_schema
from aster_expert.indexing.bm25_index import load_bm25_index as load_bm25_index

_index_cache: dict[Path, tuple[bm25s.BM25, list[dict[str, Any]]]] = {}
_schema_cache: dict[tuple[Path, str, str], CommandSchema] = {}


def cached_bm25_index(index_dir: Path) -> tuple[bm25s.BM25, list[dict[str, Any]]]:
    """`load_bm25_index(index_dir)`, loaded from disk at most once per process."""
    key = index_dir.resolve()
    cached = _index_cache.get(key)
    if cached is None:
        cached = load_bm25_index(index_dir)
        _index_cache[key] = cached
    return cached


def cached_command_schema(
    catalogue_root: Path, digest: str, command: str
) -> CommandSchema:
    """`load_command_schema(catalogue_root, digest, command)`, cached per process."""
    key = (catalogue_root.resolve(), digest, command)
    cached = _schema_cache.get(key)
    if cached is None:
        cached = load_command_schema(catalogue_root, digest, command)
        _schema_cache[key] = cached
    return cached


def clear_caches() -> None:
    """Reset both caches. Test-only: the real server process never calls this."""
    _index_cache.clear()
    _schema_cache.clear()


__all__: list[str] = [
    "cached_bm25_index",
    "cached_command_schema",
    "clear_caches",
]
