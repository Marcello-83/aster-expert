"""Tests for aster_expert.retrieval.source_priority (lot 7b, E2).

Tiny hand-built BM25 index only: no real corpus, no network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bm25s
import pytest

from aster_expert.indexing.bm25_index import build_bm25_index, load_bm25_index
from aster_expert.retrieval.source_priority import (
    hard_filter_search,
    load_source_priority,
    soft_reweight_search,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()

_RETRIEVAL_YAML = """\
defaults:
  top_k: 15
  source_priority:
    syntax: [U4, U7]
    theory: [R, U2]
"""


def _fragment(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "fragment_id": "X#index",
        "granularity": "by_file",
        "source_name": "codeaster-doc",
        "source_commit": "deadbeef" * 5,
        "document_id": "X",
        "document_title": "Titre factice",
        "family": "U4",
        "aster_version": "17.4.0",
        "section_path": ["index"],
        "content": "contenu factice",
        "content_hash": "sha256:" + "0" * 64,
        "source_path": "man_u/u4/x/index.rst",
        "line_start": 1,
        "line_end": 1,
        "related_commands": [],
        "related_keywords": [],
        "related_documents": [],
        "language": "fr",
        "extracted_at": _NOW,
    }
    defaults.update(overrides)
    return defaults


def _build_index(
    tmp_path: Path, fragments: list[dict[str, object]]
) -> tuple[bm25s.BM25, list[dict[str, Any]]]:
    fragments_path = tmp_path / "fragments.jsonl"
    with fragments_path.open("w", encoding="utf-8") as handle:
        for fragment in fragments:
            handle.write(json.dumps(fragment))
            handle.write("\n")
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    return load_bm25_index(index_dir)


def test_load_source_priority(tmp_path: Path) -> None:
    path = tmp_path / "retrieval.yaml"
    path.write_text(_RETRIEVAL_YAML, encoding="utf-8")

    priority = load_source_priority(path)

    assert priority == {"syntax": ("U4", "U7"), "theory": ("R", "U2")}


def test_hard_filter_search_prefers_priority_family_then_falls_back(
    tmp_path: Path,
) -> None:
    fragments = [
        _fragment(
            fragment_id="V1#index",
            document_id="V1",
            family="V",
            content="convergence convergence convergence critère",
        ),
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            family="U4",
            content="convergence",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)

    # V scores much higher on raw BM25 for this query, yet the hard filter
    # ranks U4 first (only family in the priority list).
    hits = hard_filter_search(
        retriever, corpus, "convergence", k=5, priority_families=("U4", "U7")
    )
    assert hits[0].document_id == "U4_1"
    # The fallback still surfaces V, since the priority pool alone is
    # smaller than k.
    assert {h.document_id for h in hits} == {"U4_1", "V1"}


def test_hard_filter_search_no_fallback_when_priority_pool_already_fills_k(
    tmp_path: Path,
) -> None:
    fragments = [
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            family="U4",
            content="convergence critère",
        ),
        _fragment(
            fragment_id="V1#index",
            document_id="V1",
            family="V",
            content="convergence critère",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)

    hits = hard_filter_search(
        retriever, corpus, "convergence", k=1, priority_families=("U4", "U7")
    )
    assert len(hits) == 1
    assert hits[0].document_id == "U4_1"


def test_soft_reweight_search_can_reorder_by_family(tmp_path: Path) -> None:
    fragments = [
        _fragment(
            fragment_id="V1#index",
            document_id="V1",
            family="V",
            content="convergence convergence convergence critère de convergence",
        ),
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            family="U4",
            content="convergence critère",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)

    unweighted_top_is_v = True  # raw BM25 favors the denser V fragment
    hits = soft_reweight_search(
        retriever,
        corpus,
        "convergence",
        k=5,
        priority_families=("U4", "U7"),
        out_of_priority_factor=0.1,
    )
    assert unweighted_top_is_v
    assert hits[0].document_id == "U4_1"
    # Nobody excluded: V still present, just ranked lower.
    assert {h.document_id for h in hits} == {"U4_1", "V1"}


def test_hard_filter_search_combines_with_document_filter(tmp_path: Path) -> None:
    fragments = [
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            family="U4",
            content="convergence",
        ),
        _fragment(
            fragment_id="U4_2#index",
            document_id="U4_2",
            family="U4",
            content="convergence",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)

    hits = hard_filter_search(
        retriever,
        corpus,
        "convergence",
        k=5,
        priority_families=("U4", "U7"),
        document_id="U4_1",
    )
    assert {h.document_id for h in hits} == {"U4_1"}


def test_soft_reweight_search_combines_with_section_filter(tmp_path: Path) -> None:
    fragments = [
        _fragment(
            fragment_id="U4_1#Syntaxe",
            document_id="U4_1",
            family="U4",
            section_path=["Syntaxe"],
            content="convergence",
        ),
        _fragment(
            fragment_id="U4_1#index",
            document_id="U4_1",
            family="U4",
            section_path=["index"],
            content="convergence",
        ),
    ]
    retriever, corpus = _build_index(tmp_path, fragments)

    hits = soft_reweight_search(
        retriever,
        corpus,
        "convergence",
        k=5,
        priority_families=("U4",),
        section_contains="syntaxe",
    )
    assert {h.fragment_id for h in hits} == {"U4_1#Syntaxe"}


def test_soft_reweight_search_rejects_pool_smaller_than_k(tmp_path: Path) -> None:
    fragments = [_fragment(fragment_id="U4_1#index", document_id="U4_1", family="U4")]
    retriever, corpus = _build_index(tmp_path, fragments)

    with pytest.raises(ValueError, match="pool_size"):
        soft_reweight_search(
            retriever,
            corpus,
            "x",
            k=10,
            priority_families=("U4",),
            pool_size=5,
        )
