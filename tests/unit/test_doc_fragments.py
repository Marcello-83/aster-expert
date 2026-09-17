"""Tests for aster_expert.parsing.doc_fragments (lot 7, D1/D2/D3).

Every fixture is a small directory tree built in `tmp_path`, mirroring the
real corpus shape established at lot 6 (a document is a directory, a
section is a `.rst` file) — never a real clone, no network
(CLAUDE.md, "Aucun accès réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.ingestion.models import DocumentEntry
from aster_expert.parsing.doc_fragments import (
    FragmentBuildError,
    SubsectionSpan,
    build_fragments_for_document,
    build_fragments_streaming,
    find_section_headers,
    load_related_commands,
    load_related_documents,
    slugify,
    split_into_subsections,
    verify_full_coverage,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)

_LONG_TEXT = """Mot clé COMPORTEMENT
====================

Intro text here.
More intro.

Sub one
-------

Content of sub one.

Sub two
-------

Content of sub two.

Sub two detail
^^^^^^^^^^^^^^

Deep content.
"""

_SHORT_TEXT = "But\n===\n\nQuelques lignes seulement.\n"


def _document(**overrides: object) -> DocumentEntry:
    defaults: dict[str, object] = {
        "document_id": "U4.51.11",
        "raw_label": "u4.51.11",
        "directory_name": "u4.51.11",
        "family": "U4",
        "subfamily": "U4",
        "title": "Titre du document",
        "relative_path": "man_u/u4/u4.51.11",
        "files": ("index.rst", "Mot_cl__COMPORTEMENT.rst"),
        "size_bytes": 100,
        "fingerprint": "sha256:" + "0" * 64,
        "source_name": "codeaster-doc",
        "source_commit": "deadbeef" * 5,
    }
    defaults.update(overrides)
    return DocumentEntry.model_validate(defaults)


def _write_document(
    root: Path, document: DocumentEntry, contents: dict[str, str]
) -> None:
    doc_dir = root / document.relative_path
    doc_dir.mkdir(parents=True, exist_ok=True)
    for file_rel, text in contents.items():
        (doc_dir / file_rel).write_text(text, encoding="utf-8")


# --- find_section_headers / split_into_subsections -------------------------


def test_find_section_headers_detects_nested_levels() -> None:
    lines = _LONG_TEXT.splitlines()
    headers = find_section_headers(lines)

    assert [h.title for h in headers] == [
        "Mot clé COMPORTEMENT",
        "Sub one",
        "Sub two",
        "Sub two detail",
    ]
    assert [h.level for h in headers] == [1, 2, 2, 3]


def test_find_section_headers_ignores_files_with_no_headers() -> None:
    text = "Just a paragraph.\nAnother line.\nNo headers at all.\n"
    assert find_section_headers(text.splitlines()) == []


def test_split_into_subsections_covers_every_line_exactly_once() -> None:
    spans = split_into_subsections(_LONG_TEXT)
    verify_full_coverage(_LONG_TEXT, spans)  # never raises

    assert spans[0].title_path == ("Mot clé COMPORTEMENT",)
    assert spans[1].title_path == ("Mot clé COMPORTEMENT", "Sub one")
    assert spans[-1].title_path == ("Mot clé COMPORTEMENT", "Sub two", "Sub two detail")


def test_split_into_subsections_headerless_file_is_one_span() -> None:
    text = "Syntaxe brute\nsans en-tête reST du tout.\n"
    spans = split_into_subsections(text)

    assert len(spans) == 1
    assert spans[0].title_path == ()
    assert spans[0].content == text


def test_split_into_subsections_keeps_preamble_before_first_header() -> None:
    text = "Préambule.\nEncore du préambule.\n\nSection\n-------\n\nCorps.\n"
    spans = split_into_subsections(text)

    assert spans[0].title_path == ()
    assert "Préambule" in spans[0].content
    assert spans[1].title_path == ("Section",)
    verify_full_coverage(text, spans)


def test_verify_full_coverage_raises_on_incorrect_bounds() -> None:
    spans = [
        SubsectionSpan(
            title_path=(), line_start=1, line_end=1, content="only first line"
        )
    ]
    with pytest.raises(FragmentBuildError):
        verify_full_coverage(_SHORT_TEXT, spans)


def test_slugify_is_deterministic_and_ascii_safe() -> None:
    assert slugify("Modélisation Générale") == "modelisation_generale"
    assert slugify(slugify("Modélisation Générale")) == slugify("Modélisation Générale")


# --- build_fragments_for_document -------------------------------------------


def test_build_fragments_for_document_by_file_one_fragment_per_section(
    tmp_path: Path,
) -> None:
    document = _document()
    _write_document(
        tmp_path,
        document,
        {"index.rst": _SHORT_TEXT, "Mot_cl__COMPORTEMENT.rst": _LONG_TEXT},
    )

    fragments = list(
        build_fragments_for_document(
            document,
            repo_root=tmp_path,
            granularity="by_file",
            aster_version="17.4.0",
            now=_NOW,
        )
    )

    assert len(fragments) == 2
    by_section = {f.section_path: f for f in fragments}
    assert by_section[("index",)].content == _SHORT_TEXT
    assert by_section[("Mot_cl__COMPORTEMENT",)].content == _LONG_TEXT
    for fragment in fragments:
        assert fragment.granularity == "by_file"
        assert fragment.document_id == "U4.51.11"
        assert fragment.family == "U4"
        assert fragment.aster_version == "17.4.0"
        assert fragment.content_hash.startswith("sha256:")


def test_build_fragments_for_document_by_subsection_splits_only_long_files(
    tmp_path: Path,
) -> None:
    document = _document()
    _write_document(
        tmp_path,
        document,
        {"index.rst": _SHORT_TEXT, "Mot_cl__COMPORTEMENT.rst": _LONG_TEXT},
    )

    fragments = list(
        build_fragments_for_document(
            document,
            repo_root=tmp_path,
            granularity="by_subsection",
            aster_version="17.4.0",
            subsection_line_threshold=5,  # forces the long file to split
            now=_NOW,
        )
    )

    # index.rst (short) stays whole; Mot_cl__COMPORTEMENT.rst (long) splits
    # into its 4 detected headers.
    index_fragments = [f for f in fragments if f.section_path[0] == "index"]
    comportement_fragments = [
        f for f in fragments if f.section_path[0] == "Mot_cl__COMPORTEMENT"
    ]
    assert len(index_fragments) == 1
    assert index_fragments[0].content == _SHORT_TEXT
    assert len(comportement_fragments) == 4


def test_build_fragments_for_document_by_subsection_keeps_short_files_whole(
    tmp_path: Path,
) -> None:
    document = _document(files=("index.rst", "Mot_cl__COMPORTEMENT.rst"))
    _write_document(
        tmp_path,
        document,
        {"index.rst": _SHORT_TEXT, "Mot_cl__COMPORTEMENT.rst": _LONG_TEXT},
    )

    fragments = list(
        build_fragments_for_document(
            document,
            repo_root=tmp_path,
            granularity="by_subsection",
            aster_version="17.4.0",
            subsection_line_threshold=1000,  # nothing exceeds this
            now=_NOW,
        )
    )

    assert len(fragments) == 2  # identical to by_file at this threshold


def test_build_fragments_attaches_related_commands_and_documents(
    tmp_path: Path,
) -> None:
    document = _document(files=("index.rst",))
    _write_document(tmp_path, document, {"index.rst": _SHORT_TEXT})

    fragments = list(
        build_fragments_for_document(
            document,
            repo_root=tmp_path,
            granularity="by_file",
            aster_version="17.4.0",
            related_commands=("STAT_NON_LINE",),
            related_documents=("R5.03.02",),
            now=_NOW,
        )
    )

    assert fragments[0].related_commands == ("STAT_NON_LINE",)
    assert fragments[0].related_documents == ("R5.03.02",)


def test_fragment_ids_are_deterministic_across_two_builds(tmp_path: Path) -> None:
    document = _document()
    _write_document(
        tmp_path,
        document,
        {"index.rst": _SHORT_TEXT, "Mot_cl__COMPORTEMENT.rst": _LONG_TEXT},
    )

    def build() -> list[tuple[str, str, str]]:
        return [
            (f.fragment_id, f.content_hash, f.content)
            for f in build_fragments_for_document(
                document,
                repo_root=tmp_path,
                granularity="by_subsection",
                aster_version="17.4.0",
                subsection_line_threshold=5,
                now=_NOW,
            )
        ]

    first = build()
    second = build()
    assert first == second  # idempotence, hashes included (docs/corpus.md §7)


# --- related-links loaders ---------------------------------------------------


def test_load_related_commands_merges_edges_and_uncatalogued_mentions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "command_document_map.json"
    path.write_text(
        json.dumps(
            {
                "edges": [
                    {
                        "command": "AFFE_MODELE",
                        "document_id": "U4.41.01",
                        "document_title": "t",
                        "source_path": "p",
                    },
                    {
                        "command": "AFFE_CHAR_MECA",
                        "document_id": "U4.41.01",
                        "document_title": "t",
                        "source_path": "p",
                    },
                ],
                "documents_naming_uncatalogued_command": [
                    {
                        "document_id": "U4.41.01",
                        "command": "DEFI_CONT",
                        "document_title": "t",
                        "source_path": "p",
                        "known_location": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = load_related_commands(path)

    assert result["U4.41.01"] == ("AFFE_CHAR_MECA", "AFFE_MODELE", "DEFI_CONT")


def test_load_related_documents_dedupes_and_sorts_targets(tmp_path: Path) -> None:
    path = tmp_path / "xref_graph.json"
    path.write_text(
        json.dumps(
            {
                "edges": [
                    {
                        "source_document_id": "U2.03.07",
                        "target_document_id": "R5.03.02",
                        "via": "explicit_label",
                        "count": 2,
                    },
                    {
                        "source_document_id": "U2.03.07",
                        "target_document_id": "R5.03.01",
                        "via": "explicit_label",
                        "count": 1,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = load_related_documents(path)

    assert result["U2.03.07"] == ("R5.03.01", "R5.03.02")


# --- streaming builder --------------------------------------------------------


def test_build_fragments_streaming_processes_inventory_end_to_end(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    document = _document(files=("index.rst",))
    _write_document(repo_root, document, {"index.rst": _SHORT_TEXT})

    inventory_path = tmp_path / "inventory.jsonl"
    inventory_path.write_text(document.model_dump_json() + "\n", encoding="utf-8")

    command_map_path = tmp_path / "command_document_map.json"
    command_map_path.write_text(
        json.dumps({"edges": [], "documents_naming_uncatalogued_command": []}),
        encoding="utf-8",
    )
    xref_path = tmp_path / "xref_graph.json"
    xref_path.write_text(json.dumps({"edges": []}), encoding="utf-8")

    output_path = tmp_path / "fragments_by_file.jsonl"
    summary = build_fragments_streaming(
        inventory_path=inventory_path,
        repo_root=repo_root,
        granularity="by_file",
        aster_version="17.4.0",
        command_map_path=command_map_path,
        xref_path=xref_path,
        output_path=output_path,
        now=_NOW,
    )

    assert summary.documents_processed == 1
    assert summary.fragment_count == 1
    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    fragment = json.loads(lines[0])
    assert fragment["document_id"] == "U4.51.11"
    assert fragment["granularity"] == "by_file"
