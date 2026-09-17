"""Tests for aster_expert.indexing.naive_search (lot 7, D6)."""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.indexing.naive_search import (
    build_documents_by_command,
    naive_command_search,
)


def test_build_documents_by_command_inverts_the_command_map(tmp_path: Path) -> None:
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
                        "command": "STAT_NON_LINE",
                        "document_id": "U4.51.03",
                        "document_title": "t",
                        "source_path": "p",
                    },
                ],
                "documents_naming_uncatalogued_command": [],
            }
        ),
        encoding="utf-8",
    )

    by_command = build_documents_by_command(path)

    assert by_command["AFFE_MODELE"] == ("U4.41.01",)
    assert by_command["STAT_NON_LINE"] == ("U4.51.03",)


def test_naive_command_search_matches_uppercase_command_token() -> None:
    by_command: dict[str, tuple[str, ...]] = {"STAT_NON_LINE": ("U4.51.03", "R5.03.01")}

    found = naive_command_search(
        "Comment utiliser STAT_NON_LINE pour un calcul quasi-statique ?", by_command
    )

    assert found == ("U4.51.03", "R5.03.01")


def test_naive_command_search_ignores_lowercase_mentions() -> None:
    by_command: dict[str, tuple[str, ...]] = {"STAT_NON_LINE": ("U4.51.03",)}

    found = naive_command_search(
        "stat_non_line en minuscules ne compte pas", by_command
    )

    assert found == ()


def test_naive_command_search_deduplicates_documents_across_commands() -> None:
    by_command: dict[str, tuple[str, ...]] = {
        "AFFE_CHAR_MECA": ("U4.44.01",),
        "AFFE_MODELE": ("U4.41.01", "U4.44.01"),
    }

    found = naive_command_search("AFFE_MODELE puis AFFE_CHAR_MECA", by_command)

    assert found == ("U4.41.01", "U4.44.01")


def test_naive_command_search_returns_empty_when_no_command_named() -> None:
    by_command: dict[str, tuple[str, ...]] = {"STAT_NON_LINE": ("U4.51.03",)}

    assert naive_command_search("Comment mailler une poutre ?", by_command) == ()
