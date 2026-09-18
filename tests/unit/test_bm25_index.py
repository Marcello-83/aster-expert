"""Tests for aster_expert.indexing.bm25_index (lot 7, D4).

A tiny hand-written fragments JSONL fixture only: no real corpus, no
network (CLAUDE.md, "Aucun accès réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.indexing.bm25_index import (
    build_bm25_index,
    default_index_dir,
    find_fragments,
    load_bm25_index,
    search,
    to_document_section,
)

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


def test_search_family_in_filter(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    retriever, corpus = load_bm25_index(index_dir)

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, family_in=("U4", "R"))
    assert {h.family for h in hits} <= {"U4", "R"}

    hits = search(retriever, corpus, "STAT_NON_LINE", k=5, family_in=("V",))
    assert hits == []


def test_default_index_dir_variant_none_is_unchanged(tmp_path: Path) -> None:
    base = default_index_dir(tmp_path, "by_file")
    assert base == tmp_path / "data" / "indexes" / "bm25_by_file"


def test_default_index_dir_variant_suffixes_path(tmp_path: Path) -> None:
    variant = default_index_dir(tmp_path, "by_file", variant="e1")
    assert variant == tmp_path / "data" / "indexes" / "bm25_by_file_e1"


def test_build_bm25_index_without_enrichment_matches_lot7_behaviour(
    tmp_path: Path,
) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"

    summary = build_bm25_index(fragments_path, index_dir)

    assert summary.text_enrichment == "none"
    _, corpus = load_bm25_index(index_dir)
    # The persisted corpus content is exactly the fragment's raw content,
    # never anything enrichment could have appended.
    assert corpus[0]["content"] == _sample_fragments()[0]["content"]


def test_build_bm25_index_with_enrichment_helps_find_keyword_named_query(
    tmp_path: Path,
) -> None:
    fragments = [
        _fragment(
            fragment_id="U4.44.01#Chargements",
            document_id="U4.44.01",
            document_title="Opérateurs AFFE_CHAR_MECA",
            family="U4",
            section_path=["Chargements de type Dirichlet", "Mot-clé DDL_IMPO"],
            content=(
                "Cette section décrit comment imposer une valeur de "
                "déplacement, de rotation ou d'autres grandeurs nodales."
            ),
            related_commands=["AFFE_CHAR_MECA"],
        ),
        _fragment(
            fragment_id="V1.01.001#index",
            document_id="V1.01.001",
            document_title="Cas test générique",
            family="V",
            content=(
                "Ce cas test impose un déplacement bloqué et une rotation "
                "bloquée sur un groupe de noeuds du maillage étudié, "
                "reproduisant un chargement usuel."
            ),
            related_commands=[],
        ),
    ]
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, fragments)
    index_dir = tmp_path / "index"

    summary = build_bm25_index(
        fragments_path,
        index_dir,
        keyword_names_by_command={"AFFE_CHAR_MECA": ("DDL_IMPO", "VERI_NORM")},
    )
    assert summary.text_enrichment == "e1_title_section_keywords_scoped"

    retriever, corpus = load_bm25_index(index_dir)
    hits = search(retriever, corpus, "DDL_IMPO", k=5)

    assert hits
    assert hits[0].document_id == "U4.44.01"
    # The stored content is still the raw fragment content, never the
    # enriched text used only for tokenizing.
    assert "DDL_IMPO" not in corpus[0]["content"]


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


def test_find_fragments_by_fragment_id_returns_full_content_never_excerpted(
    tmp_path: Path,
) -> None:
    long_content = "Phrase de section. " * 50  # well over _EXCERPT_CHARS (280)
    fragments = [_fragment(fragment_id="U2.02.01#Conclusion", content=long_content)]
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, fragments)
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    _, corpus = load_bm25_index(index_dir)

    matches = find_fragments(corpus, fragment_id="U2.02.01#Conclusion")

    assert len(matches) == 1
    section = to_document_section(matches[0])
    assert section.content == long_content
    assert section.content_length == len(long_content)


def test_find_fragments_by_document_and_section_path(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    _, corpus = load_bm25_index(index_dir)

    matches = find_fragments(corpus, document_id="U4.51.03", section_path=("index",))

    assert len(matches) == 1
    assert matches[0]["fragment_id"] == "U4.51.03#index"


def test_find_fragments_unknown_identifier_returns_no_match(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments_by_file.jsonl"
    _write_fragments(fragments_path, _sample_fragments())
    index_dir = tmp_path / "index"
    build_bm25_index(fragments_path, index_dir)
    _, corpus = load_bm25_index(index_dir)

    assert find_fragments(corpus, fragment_id="does-not-exist") == []
    assert find_fragments(corpus, document_id="U4.51.03", section_path=("nope",)) == []


def test_to_document_section_defaults_to_whole_fragment() -> None:
    entry = _fragment(content="ligne 1\nligne 2\nligne 3", line_start=10, line_end=12)

    section = to_document_section(entry)

    assert section.content == "ligne 1\nligne 2\nligne 3"
    assert section.content_length == len(section.content)
    assert section.requested_line_start == 10
    assert section.requested_line_end == 12
    assert section.requested_length == section.content_length
    assert section.is_full_section is True
    assert section.outline == ()
    assert section.guidance is None


def test_to_document_section_full_request_never_alters_a_trailing_blank_line() -> None:
    """Regression: a naive splitlines()+"\\n".join() round-trip silently drops
    a final blank line's newline on content already built that way by
    `doc_fragments.build_fragments_for_document` (lot 7) -- exactly what a
    full-section request must never do (CLAUDE.md, "ne jamais modifier ni
    tronquer une partie d'un fichier ... sans nécessité")."""
    content_with_trailing_blank_line = "Titre\n=====\n\ntexte.\n\n"
    entry = _fragment(
        content=content_with_trailing_blank_line, line_start=1, line_end=5
    )

    section = to_document_section(entry)

    assert section.content == content_with_trailing_blank_line
    assert section.content_length == len(content_with_trailing_blank_line)
    assert section.requested_length == section.content_length


def test_to_document_section_explicit_range_returns_only_that_slice() -> None:
    entry = _fragment(
        content="ligne 1\nligne 2\nligne 3\nligne 4", line_start=5, line_end=8
    )

    section = to_document_section(entry, line_start=6, line_end=7)

    # The exact substring of the source spanning lines 6-7 inclusive,
    # trailing newline of the last selected line kept (it is itself part of
    # that physical line, and the line after it is not included) -- never a
    # re-joined approximation (lot 14, L1).
    assert section.content == "ligne 2\nligne 3\n"
    assert section.requested_line_start == 6
    assert section.requested_line_end == 7
    assert section.is_full_section is False
    # The *whole* fragment's size, never the slice's, so a caller always
    # knows the total (lot 14, L1).
    assert section.content_length == len("ligne 1\nligne 2\nligne 3\nligne 4")
    assert section.requested_length == len("ligne 2\nligne 3\n")


def test_to_document_section_only_one_bound_given_raises() -> None:
    entry = _fragment(content="a\nb\nc", line_start=1, line_end=3)

    with pytest.raises(ValueError, match="line_start et line_end"):
        to_document_section(entry, line_start=2)


def test_to_document_section_start_after_end_raises() -> None:
    entry = _fragment(content="a\nb\nc", line_start=1, line_end=3)

    with pytest.raises(ValueError, match="line_start"):
        to_document_section(entry, line_start=3, line_end=2)


def test_to_document_section_range_outside_fragment_bounds_raises() -> None:
    entry = _fragment(content="a\nb\nc", line_start=10, line_end=12)

    with pytest.raises(ValueError, match="hors des bornes"):
        to_document_section(entry, line_start=1, line_end=5)


def test_to_document_section_over_threshold_withholds_content_with_outline() -> None:
    content = (
        "Titre\n=====\n\ntexte introductif\n\n"
        "Sous-titre A\n------------\n\ncontenu A un peu long pour le test\n\n"
        "Sous-titre B\n------------\n\ncontenu B un peu long pour le test"
    )
    entry = _fragment(
        content=content, line_start=100, line_end=100 + len(content.splitlines()) - 1
    )

    section = to_document_section(entry, max_chars=10)

    assert section.content is None
    assert (
        section.is_full_section is True
    )  # the withheld request was the whole fragment
    assert section.content_length == len(content)
    assert section.requested_length == len(content)
    assert section.guidance is not None
    assert "line_start" in section.guidance
    assert [entry.title_path for entry in section.outline] == [
        ("Titre", "Sous-titre A"),
        ("Titre", "Sous-titre B"),
    ]
    # Outline line numbers are absolute (offset by the fragment's own
    # line_start=100), directly usable as the next call's line_start/line_end.
    assert (
        section.outline[0].line_start == 100 + 5
    )  # "Sous-titre A" is line 6 (0-indexed 5)


def test_to_document_section_over_threshold_without_headers_has_empty_outline() -> None:
    content = "prose sans aucun en-tête reStructuredText, juste du texte. " * 5
    entry = _fragment(content=content, line_start=1, line_end=1)

    section = to_document_section(entry, max_chars=10)

    assert section.content is None
    assert section.outline == ()
    assert "aucune sous-section détectée" in section.guidance
