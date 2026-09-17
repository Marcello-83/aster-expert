"""Tests for aster_expert.indexing.enrichment (lot 7b, E1).

Tiny hand-written catalogue fixtures only: no real corpus, no network
(CLAUDE.md, "Aucun accès réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.indexing.enrichment import (
    collect_related_commands,
    enrich_indexed_text,
    load_command_keyword_names,
)

_DDL_IMPO_COMMAND = {
    "command": "AFFE_CHAR_MECA",
    "aster_version": "17.4.0",
    "image_digest": "sha256:abc",
    "catalogue_source": "/opt/x/code_aster",
    "catalogue_hash": "sha256:def",
    "kind": "operator",
    "result_type": "char_meca",
    "result_type_dynamic": False,
    "docu": None,
    "keywords": [
        {
            "path": ["DDL_IMPO"],
            "variant_id": "aaaa",
            "kind": "factor",
            "status": "optional",
            "min_occurrences": 0,
            "max_occurrences": None,
            "condition": [],
            "children": [
                {
                    "path": ["DDL_IMPO", "DX"],
                    "variant_id": "bbbb",
                    "kind": "simple",
                    "status": "optional",
                    "value_type": "R",
                    "allowed_values": None,
                    "default": None,
                    "min_values": None,
                    "max_values": 1,
                    "condition": [],
                },
            ],
        },
        {
            "path": ["VERI_NORM"],
            "variant_id": "cccc",
            "kind": "simple",
            "status": "optional",
            "value_type": "TXM",
            "allowed_values": ["OUI", "NON"],
            "default": "OUI",
            "min_values": None,
            "max_values": 1,
            "condition": [],
        },
    ],
    "extracted_at": "2026-01-01T00:00:00+00:00",
}


def test_load_command_keyword_names_top_level_only(tmp_path: Path) -> None:
    digest_dir = tmp_path / "sha256:abc"
    digest_dir.mkdir()
    (digest_dir / "AFFE_CHAR_MECA.json").write_text(
        json.dumps(_DDL_IMPO_COMMAND), encoding="utf-8"
    )

    names = load_command_keyword_names(digest_dir, {"AFFE_CHAR_MECA"})

    assert names["AFFE_CHAR_MECA"] == ("DDL_IMPO", "VERI_NORM")
    assert "DX" not in names["AFFE_CHAR_MECA"]  # never a child of a factor


def test_load_command_keyword_names_skips_uncatalogued_command(
    tmp_path: Path,
) -> None:
    digest_dir = tmp_path / "sha256:abc"
    digest_dir.mkdir()

    names = load_command_keyword_names(digest_dir, {"DEFI_CONT"})

    assert names == {}


def test_enrich_indexed_text_adds_title_section_and_keywords() -> None:
    text = enrich_indexed_text(
        content="Bloquer un déplacement sur un groupe de noeuds.",
        document_title="Opérateurs AFFE_CHAR_MECA...",
        section_path=("index", "Chargements de type Dirichlet"),
        related_commands=("AFFE_CHAR_MECA",),
        keyword_names_by_command={"AFFE_CHAR_MECA": ("DDL_IMPO", "VERI_NORM")},
    )

    assert "Bloquer un déplacement" in text
    assert "Opérateurs AFFE_CHAR_MECA..." in text
    assert "Chargements de type Dirichlet" in text
    assert "AFFE_CHAR_MECA" in text
    assert "DDL_IMPO" in text
    assert "VERI_NORM" in text


def test_enrich_indexed_text_never_used_for_unrelated_command() -> None:
    text = enrich_indexed_text(
        content="contenu",
        document_title=None,
        section_path=(),
        related_commands=("AFFE_MODELE",),
        keyword_names_by_command={"AFFE_CHAR_MECA": ("DDL_IMPO",)},
    )
    assert "DDL_IMPO" not in text
    assert "AFFE_MODELE" in text


def test_collect_related_commands(tmp_path: Path) -> None:
    fragments_path = tmp_path / "fragments.jsonl"
    fragments_path.write_text(
        "\n".join(
            [
                json.dumps({"related_commands": ["AFFE_CHAR_MECA", "AFFE_MODELE"]}),
                json.dumps({"related_commands": ["AFFE_MODELE"]}),
                json.dumps({"related_commands": []}),
            ]
        ),
        encoding="utf-8",
    )

    commands = collect_related_commands(fragments_path)

    assert commands == {"AFFE_CHAR_MECA", "AFFE_MODELE"}
