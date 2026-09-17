"""Tests for aster_expert.retrieval.config (lot 7b)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.retrieval.config import load_retrieval_config

_SAMPLE_YAML = """\
schema_version: 1
engines:
  lexical:
    enabled: true
    backend: bm25
    k1: 1.2
    b: 0.75
  vector:
    enabled: false
    backend: null
    model: null
    dimension: null
fusion:
  enabled: false
  method: null
reranking:
  enabled: false
  backend: null
defaults:
  top_k: 15
  source_priority:
    syntax: [catalogue, U4, U7, testcase, source]
    theory: [R, U2, U4, V]
    example: [testcase, V, U4]
filters:
  allowed: [version, family, document_id]
output:
  show_scores: true
  show_source_path: true
  show_commit: true
  max_excerpt_chars: 1200
"""


def test_load_retrieval_config_parses_source_priority(tmp_path: Path) -> None:
    path = tmp_path / "retrieval.yaml"
    path.write_text(_SAMPLE_YAML, encoding="utf-8")

    config = load_retrieval_config(path)

    assert config.defaults.top_k == 15
    assert config.defaults.source_priority["syntax"] == (
        "catalogue",
        "U4",
        "U7",
        "testcase",
        "source",
    )
    assert config.engines.vector.enabled is False


def test_load_retrieval_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_retrieval_config(tmp_path / "missing.yaml")


def test_load_retrieval_config_matches_the_real_project_file() -> None:
    """The actual `config/retrieval.yaml` must validate against this schema."""
    real_config_path = Path(__file__).resolve().parents[2] / "config" / "retrieval.yaml"
    config = load_retrieval_config(real_config_path)
    # Lot 7c, G1/G2 : profils renommés en français, alignés sur
    # `data/evaluations/query_profiles.jsonl`.
    assert set(config.defaults.source_priority) == {"syntaxe", "theorie", "methode"}
