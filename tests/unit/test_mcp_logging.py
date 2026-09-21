"""Tests for the MCP query journal (lot 8, H3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aster_expert.mcp.logging import (
    QueryLogEntry,
    ReturnedItem,
    append_query_log,
    default_query_log_path,
)


def test_default_query_log_path(tmp_path: Path) -> None:
    assert default_query_log_path(tmp_path) == (
        tmp_path / "data" / "processed" / "query_log.jsonl"
    )


def test_append_query_log_creates_parent_and_writes_one_line(tmp_path: Path) -> None:
    log_path = tmp_path / "data" / "processed" / "query_log.jsonl"

    entry = append_query_log(
        log_path,
        tool="search_codeaster_docs",
        query="ressort non linéaire",
        profile="syntaxe",
        filters={"granularity": "by_file", "version": None},
        returned=[ReturnedItem(identifier="U4.51.03#x", score=4.2)],
        duration_s=0.031,
    )

    assert log_path.is_file()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    reloaded = QueryLogEntry.model_validate_json(lines[0])
    assert reloaded == entry
    assert reloaded.tool == "search_codeaster_docs"
    assert reloaded.query == "ressort non linéaire"
    assert reloaded.profile == "syntaxe"
    assert reloaded.filters == {"granularity": "by_file", "version": None}
    assert reloaded.returned == [ReturnedItem(identifier="U4.51.03#x", score=4.2)]


def test_append_query_log_appends_without_truncating(tmp_path: Path) -> None:
    log_path = tmp_path / "query_log.jsonl"

    append_query_log(log_path, tool="a", duration_s=0.0)
    append_query_log(log_path, tool="b", duration_s=0.0)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["tool"] for line in lines] == ["a", "b"]


def test_append_query_log_never_receives_file_content_for_comm_tools(
    tmp_path: Path,
) -> None:
    """`analyze_comm`/`validate_comm` only ever pass a name and a fingerprint.

    This test only checks the journal's own contract: nothing here rejects a
    caller that passes file content, so the "never log content" guarantee is
    the caller's discipline (`aster_expert.mcp.tools`), verified there and
    exercised end to end in `tests/integration/test_mcp_server.py`. This test
    fixes the shape a well-behaved caller uses.
    """
    log_path = tmp_path / "query_log.jsonl"

    entry = append_query_log(
        log_path,
        tool="analyze_comm",
        duration_s=0.004,
        file_name="sslv104a.comm",
        file_fingerprint="sha256:" + "a" * 64,
    )

    assert entry.query is None
    assert entry.profile is None
    assert entry.returned == []
    assert entry.file_name == "sslv104a.comm"
    assert entry.file_fingerprint == "sha256:" + "a" * 64


def test_check_origin_is_recorded_and_excluded_from_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aster_expert.mcp.logging import (
        CALL_ORIGIN_ENV,
        CHECK_ORIGIN,
        SESSION_ORIGIN,
        read_usage_entries,
    )

    log = tmp_path / "log.jsonl"
    monkeypatch.delenv(CALL_ORIGIN_ENV, raising=False)
    assert append_query_log(log, tool="a", duration_s=0.1).origin == SESSION_ORIGIN
    monkeypatch.setenv(CALL_ORIGIN_ENV, CHECK_ORIGIN)
    assert append_query_log(log, tool="b", duration_s=0.1).origin == CHECK_ORIGIN
    # A line written before the origin existed reads as usage.
    with log.open("a", encoding="utf-8") as handle:
        handle.write(
            '{"timestamp":"2026-01-01T00:00:00Z","tool":"old","duration_s":1}\n'
        )
    assert [e.tool for e in read_usage_entries(log)] == ["a", "old"]
    assert read_usage_entries(tmp_path / "absent.jsonl") == []
