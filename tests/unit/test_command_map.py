"""Unit tests for `aster_expert.ingestion.command_map` (lot 6, I5).

Synthetic fixtures reproducing the real shapes found on the 17.4.0 corpus:
a document naming several sibling commands together (`AFFE_CHAR_MECA` /
`_C` / `_F`), a command documented by several documents (`IMPR_RESU`, one
per output format), and a command name that must never match as a
substring of a longer one.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.command_map import (
    build_command_mapping,
    find_commands_in_title,
    load_catalogue_commands,
    load_u4_u7_documents,
    write_command_mapping_json,
)

FIXED_NOW = datetime(2026, 9, 16, 12, 0, 0, tzinfo=UTC)


def test_find_commands_in_title_exact_match() -> None:
    commands = ["COMB_SISM_MODAL", "STAT_NON_LINE"]
    assert find_commands_in_title("Opérateur COMB_SISM_MODAL", commands) == (
        "COMB_SISM_MODAL",
    )


def test_find_commands_in_title_never_matches_as_substring_of_longer_command() -> None:
    # AFFE_CHAR_MECA must never match inside the title of the
    # AFFE_CHAR_MECA_C document (real corpus case, lot 6).
    commands = ["AFFE_CHAR_MECA", "AFFE_CHAR_MECA_C"]
    assert find_commands_in_title("Opérateur AFFE_CHAR_MECA_C", commands) == (
        "AFFE_CHAR_MECA_C",
    )


def test_find_commands_in_title_finds_several_sibling_commands() -> None:
    commands = ["AFFE_CHAR_MECA", "AFFE_CHAR_MECA_C", "AFFE_CHAR_MECA_F"]
    title = "Opérateurs AFFE_CHAR_MECA, AFFE_CHAR_MECA_C et AFFE_CHAR_MECA_F"
    found = find_commands_in_title(title, commands)
    assert set(found) == set(commands)


def test_find_commands_in_title_no_match_returns_empty() -> None:
    assert find_commands_in_title("Nouveautés et modifications", ["FIN"]) == ()


def _docs(*pairs: tuple[str, str | None]) -> list[tuple[str, str | None]]:
    return list(pairs)


def test_build_command_mapping_one_document_one_command() -> None:
    documents = _docs(("U4.84.01", "Opérateur COMB_SISM_MODAL"))
    catalogue = ["COMB_SISM_MODAL", "STAT_NON_LINE"]

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.total_catalogue_commands == 2
    assert result.matched_catalogue_commands == 1
    assert result.edges == (
        result.edges[0].__class__(command="COMB_SISM_MODAL", document_id="U4.84.01"),
    )
    assert result.commands_without_document == ("STAT_NON_LINE",)
    assert result.documents_without_command == ()


def test_build_command_mapping_multiple_documents_for_one_command() -> None:
    # IMPR_RESU real shape: one command, four documents (one per format).
    documents = _docs(
        ("U4.91.01", "Procédure IMPR_RESU aux formats 'RESULTAT' et 'ASTER'"),
        ("U7.05.01", "Procédure IMPR_RESU au format 'IDEAS'"),
    )
    catalogue = ["IMPR_RESU"]

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    document_ids = {e.document_id for e in result.edges if e.command == "IMPR_RESU"}
    assert document_ids == {"U4.91.01", "U7.05.01"}


def test_build_command_mapping_multiple_commands_for_one_document() -> None:
    documents = _docs(
        (
            "U4.44.01",
            "Opérateurs AFFE_CHAR_MECA, AFFE_CHAR_MECA_C et AFFE_CHAR_MECA_F",
        )
    )
    catalogue = ["AFFE_CHAR_MECA", "AFFE_CHAR_MECA_C", "AFFE_CHAR_MECA_F"]

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.matched_catalogue_commands == 3
    commands_for_doc = {e.command for e in result.edges if e.document_id == "U4.44.01"}
    assert commands_for_doc == set(catalogue)


def test_build_command_mapping_document_without_command() -> None:
    documents = _docs(("U4.01.00", "Comment lire la documentation des commandes"))
    catalogue = ["FIN"]

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.documents_without_command == ("U4.01.00",)
    assert result.documents_naming_known_macro_command == ()


def test_build_command_mapping_flags_known_macro_command_separately() -> None:
    # DEFI_CONT is a known MacroCommands name outside the introspected
    # catalogue (docs/development-plan.md, lot 4/10b) — named in the title
    # but never turned into a false edge against a catalogue command.
    documents = _docs(("U4.44.13", "Opérateur DEFI_CONT"))
    catalogue = ["FIN"]  # DEFI_CONT deliberately absent from the catalogue

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.documents_without_command == ()
    assert result.documents_naming_known_macro_command == (("U4.44.13", "DEFI_CONT"),)
    assert result.edges == ()


def test_build_command_mapping_handles_missing_title() -> None:
    documents = _docs(("U4.01.02", None))
    catalogue = ["FIN"]

    result = build_command_mapping(
        documents,
        catalogue,
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )

    assert result.documents_without_command == ("U4.01.02",)


def test_load_u4_u7_documents_filters_by_family(tmp_path: Path) -> None:
    inventory_path = tmp_path / "inventory.jsonl"
    rows = [
        {"document_id": "U4.01.00", "family": "U4", "title": "T1"},
        {"document_id": "R7.01.03", "family": "R", "title": "T2"},
        {"document_id": "U7.05.01", "family": "U7", "title": "T3"},
    ]
    with inventory_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    documents = load_u4_u7_documents(inventory_path)
    assert documents == [("U4.01.00", "T1"), ("U7.05.01", "T3")]


def test_load_catalogue_commands(tmp_path: Path) -> None:
    catalogue_dir = tmp_path / "catalogue"
    catalogue_dir.mkdir()
    (catalogue_dir / "FIN.json").write_text("{}", encoding="utf-8")
    (catalogue_dir / "DEBUT.json").write_text("{}", encoding="utf-8")

    commands = load_catalogue_commands(catalogue_dir)
    assert set(commands) == {"FIN", "DEBUT"}


def test_write_command_mapping_json(tmp_path: Path) -> None:
    result = build_command_mapping(
        _docs(("U4.84.01", "Opérateur COMB_SISM_MODAL")),
        ["COMB_SISM_MODAL"],
        source_name="codeaster-doc",
        source_commit="deadbeef",
        now=FIXED_NOW,
    )
    output_path = tmp_path / "map.json"
    write_command_mapping_json(result, output_path)
    reloaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert reloaded["matched_catalogue_commands"] == 1
