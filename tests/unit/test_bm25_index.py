"""Tests for aster_expert.indexing.bm25_index (lot 7, D4).

A tiny hand-written fragments JSONL fixture only: no real corpus, no
network (CLAUDE.md, "Aucun accès réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.indexing.bm25_index import build_bm25_index, load_bm25_index, search

_NOW = datetime(2026, 1, 1, tzinfo=UTC).isoformat()


def _fragment(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "fragment_id": "U4.51.03#index",
        "granularity": "by_file",
        "source_name": "codeaster-doc",
        "source_commit": "deadbeef" * 5,
        "document_id": "U4.51.03",
        "document_title": "Opérateur STAT_NON_LINE",
        "family": "U4",
        "aster_version": "17.4.0",
        "section_path": ["index"],
        "content": "STAT_NON_LINE calcule la réponse mécanique non linéaire.",
        "content_hash": "sha256:" + "0" * 64,
        "source_path": "man_u/u4/u4.51.03/index.rst",
        "line_start": 1,
        "line_end": 1,
        "related_commands": ["STAT_NON_LINE"],
        "related_keywords": [],
        "related_documents": [],
        "language": "fr",
        "extracted_at": _NOW,
    }
    defaults.update(overrides)
    return defaults


def _write_fragments(path: Path, fragments: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for fragment in fragments:
            handle.write(json.dumps(fragment))
            handle.write("\n")


def _sample_fragments() -> list[dict[str, object]]:
    return [
        _fragment(
            fragment_id="U4.51.03#index",
            document_id="U4.51.03",
            family="U4",
            aster_version="17.4.0",
            content="STAT_NON_LINE calcule la réponse mécanique non linéaire.",
            related_commands=["STAT_NON_LINE"],
        ),
        _fragment(
            fragment_id="U4.41.01#index",
            document_id="U4.41.01",
            family="U4",
            aster_version="17.4.0",
            content="AFFE_MODELE affecte une modélisation au maillage.",
            related_commands=["AFFE_MODELE"],
        ),
        _fragment(
            fragment_id="R5.03.02#index",
            document_id="R5.03.02",
            family="R",
            aster_version="17.3.0",
            content="Théorie de l'algorithme de Newton pour STAT_NON_LINE.",
            related_commands=["STAT_NON_LINE"],
        ),
    ]


def test_build_and_search_finds_relevant_fragment(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"

    summary = build_bm25_index(fragments_path, index_dir)
    assert summary.fragment_count == 3
    assert summary.vocabulary_size > 0

    retriever, corpus = load_bm25_index(index_dir)
    hits = search(retriever, corpus, "STAT_NON_LINE convergence", k=5)

    assert hits  # at least one match
    assert hits[0].document_id in {"U4.51.03", "R5.03.02"}


def test_search_version_filter_excludes_other_versions(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, version="17.4.0")

    assert all(h.aster_version == "17.4.0" for h in hits)
    assert "R5.03.02" not in {h.document_id for h in hits}


def test_search_family_filter(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, family="R")

    assert all(h.family == "R" for h in hits)


def test_search_command_filter(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(
        retriever, corpus, "modélisation maillage", k=5, command="AFFE_MODELE"
    )

    assert len(hits) == 1
    assert hits[0].document_id == "U4.41.01"


def test_search_document_filter_returns_only_that_document(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, document_id="R5.03.02")

    assert all(h.document_id == "R5.03.02" for h in hits)


def test_search_filter_with_no_matches_returns_empty(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, family="V")

    assert hits == []


def test_search_never_returns_a_document_outside_the_filter_even_ranked_first(
    tmp_path: Path,
) -> None:
    """The masked-out top candidate must never leak through (weight_mask +
    an explicit `_matches` re-check, docs/architecture.md ADR-004)."""
    fragments = [
        _fragment(
            fragment_id="A#index",
            document_id="A",
            family="U4",
            content="convergence convergence convergence critère de convergence",
        ),
        _fragment(
            fragment_id="B#index",
            document_id="B",
            family="R",
            content="convergence",
        ),
    ]
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, fragments)
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "convergence", k=5, family="R")

    assert all(h.document_id == "B" for h in hits)
