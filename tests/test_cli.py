"""Smoke tests for the CLI skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aster_expert import __version__
from aster_expert.cli import app

runner = CliRunner()

# external/codeaster-src/astest/ssns112c.comm, lines 25 and 49, verbatim.
_MINIMAL_COMM = """\
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"), DEBUG=_F(SDVERI="OUI"))

FIN()
"""


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_sources_sync_fails_loudly_without_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    result = runner.invoke(app, ["sources", "sync"])
    assert result.exit_code == 1
    assert "sources.yaml" in result.stderr


def test_comm_parse_prints_analysis_json(tmp_path: Path) -> None:
    comm_path = tmp_path / "minimal.comm"
    comm_path.write_text(_MINIMAL_COMM, encoding="utf-8")

    result = runner.invoke(app, ["comm", "parse", str(comm_path)])

    assert result.exit_code == 0
    analysis = json.loads(result.stdout)
    assert [s["command"] for s in analysis["statements"]] == ["DEBUT", "FIN"]


def test_comm_parse_fails_loudly_on_syntax_error(tmp_path: Path) -> None:
    comm_path = tmp_path / "broken.comm"
    comm_path.write_text("DEBUT(CODE=\n", encoding="utf-8")

    result = runner.invoke(app, ["comm", "parse", str(comm_path)])

    assert result.exit_code == 1


def test_validate_fails_loudly_without_workroot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ASTER_CONTAINER_WORKROOT", raising=False)
    comm_path = tmp_path / "minimal.comm"
    comm_path.write_text(_MINIMAL_COMM, encoding="utf-8")

    result = runner.invoke(app, ["validate", str(comm_path)])

    assert result.exit_code == 1
    assert "ASTER_CONTAINER_WORKROOT" in result.stderr


_MINIMAL_RETRIEVAL_YAML = """\
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
    syntaxe: [catalogue, U4, U7, testcase, source]
    theorie: [R, U2, U4, U3, V]
    methode: [U2, U4, R, U3]
filters:
  allowed: [version, family, document_id]
output:
  show_scores: true
  show_source_path: true
  show_commit: true
  max_excerpt_chars: 1200
"""


def test_search_fails_loudly_on_unknown_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "retrieval.yaml").write_text(
        _MINIMAL_RETRIEVAL_YAML, encoding="utf-8"
    )

    result = runner.invoke(app, ["search", "une question", "--profile", "bogus"])

    assert result.exit_code == 1
    assert "Profil inconnu" in result.stderr
    assert "'bogus'" in result.stderr


def test_eval_profile_bench_fails_loudly_without_annotations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    (tmp_path / "data" / "evaluations").mkdir(parents=True)
    (tmp_path / "data" / "evaluations" / "questions.jsonl").write_text(
        "", encoding="utf-8"
    )

    result = runner.invoke(app, ["eval", "profile-bench"])

    assert result.exit_code == 1
    assert "Annotations de profil introuvables" in result.stderr
