"""Tests for `aster_expert.mcp.cache` (lot 8b, J1): loaded from disk at most
once per process, never on every call.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import aster_expert.mcp.cache as cache_module
from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir
from aster_expert.mcp.cache import cached_bm25_index, cached_command_schema

DIGEST = "sha256:testdigest"


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    cache_module.clear_caches()
    yield
    cache_module.clear_caches()


def _write_fragment(handle: Any) -> None:
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
    handle.write(json.dumps(fragment) + "\n")


def _build_index(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    with fragments_path.open("w", encoding="utf-8") as handle:
        _write_fragment(handle)
    index_dir = default_index_dir(tmp_path, "by_file")
    build_bm25_index(fragments_path, index_dir)
    return index_dir


def test_cached_bm25_index_loads_from_disk_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_dir = _build_index(tmp_path)
    calls: list[Path] = []
    real_load = cache_module.load_bm25_index

    def counting_load(path: Path) -> Any:
        calls.append(path)
        return real_load(path)

    monkeypatch.setattr(cache_module, "load_bm25_index", counting_load)

    first_retriever, first_corpus = cached_bm25_index(index_dir)
    second_retriever, second_corpus = cached_bm25_index(index_dir)

    assert len(calls) == 1
    assert first_retriever is second_retriever
    assert first_corpus is second_corpus


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
        "keywords": [],
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    (catalogue_dir / "STAT_NON_LINE.json").write_text(
        json.dumps(schema), encoding="utf-8"
    )


def test_cached_command_schema_loads_from_disk_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogue_root = tmp_path / "catalogue"
    _write_catalogue(catalogue_root / DIGEST)
    calls: list[tuple[Path, str, str]] = []
    real_load = cache_module.load_command_schema

    def counting_load(root: Path, digest: str, command: str) -> Any:
        calls.append((root, digest, command))
        return real_load(root, digest, command)

    monkeypatch.setattr(cache_module, "load_command_schema", counting_load)

    first = cached_command_schema(catalogue_root, DIGEST, "STAT_NON_LINE")
    second = cached_command_schema(catalogue_root, DIGEST, "STAT_NON_LINE")

    assert len(calls) == 1
    assert first is second


def test_cached_bm25_index_distinguishes_different_index_dirs(
    tmp_path: Path,
) -> None:
    index_dir_a = _build_index(tmp_path / "a")
    index_dir_b = _build_index(tmp_path / "b")

    retriever_a, _ = cached_bm25_index(index_dir_a)
    retriever_b, _ = cached_bm25_index(index_dir_b)

    assert retriever_a is not retriever_b
