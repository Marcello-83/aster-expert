"""Tests for aster_expert.retrieval.query_profiles (lot 7c, G1/G3).

Tiny hand-written JSONL fixtures only: no network, no dependency on
`data/evaluations/query_profiles.jsonl` itself (CLAUDE.md, "Aucun accès
réseau dans les tests unitaires").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aster_expert.retrieval.query_profiles import (
    default_query_profiles_path,
    load_query_profiles,
)


def test_load_query_profiles_reads_id_to_profile_mapping(tmp_path: Path) -> None:
    path = tmp_path / "query_profiles.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {"id": "eval-001", "question": "q1", "query_profile": "theorie"}
                ),
                json.dumps(
                    {"id": "eval-002", "question": "q2", "query_profile": "syntaxe"}
                ),
            ]
        ),
        encoding="utf-8",
    )

    profiles = load_query_profiles(path)

    assert profiles == {"eval-001": "theorie", "eval-002": "syntaxe"}


def test_load_query_profiles_never_invents_a_missing_id(tmp_path: Path) -> None:
    path = tmp_path / "query_profiles.jsonl"
    path.write_text(
        json.dumps({"id": "eval-001", "question": "q1", "query_profile": "methode"}),
        encoding="utf-8",
    )

    profiles = load_query_profiles(path)

    assert "eval-065" not in profiles


def test_load_query_profiles_rejects_unknown_profile_value(tmp_path: Path) -> None:
    path = tmp_path / "query_profiles.jsonl"
    path.write_text(
        json.dumps({"id": "eval-001", "question": "q1", "query_profile": "exemple"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_query_profiles(path)


def test_default_query_profiles_path(tmp_path: Path) -> None:
    assert default_query_profiles_path(tmp_path) == (
        tmp_path / "data" / "evaluations" / "query_profiles.jsonl"
    )
