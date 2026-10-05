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


def test_comm_parse_prints_analysis_json(
    tmp_path: Path, lecture_sous_tmp: Path
) -> None:
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


def test_section_returns_full_content_by_fragment_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    long_content = "Phrase de section. " * 50  # over the 280-char search excerpt cap
    fragment = {
        "fragment_id": "U2.02.01#Conclusion",
        "granularity": "by_file",
        "document_id": "U2.02.01",
        "document_title": "Comparaison DKT/DST/Q4G",
        "family": "U2",
        "aster_version": "17.4.0",
        "section_path": ["Conclusion"],
        "source_path": "source/manuals/man_u/u2/u2.02.01/conclusion.rst",
        "source_commit": "b" * 40,
        "line_start": 1,
        "line_end": 65,
        "related_commands": [],
        "content": long_content,
    }
    fragments_path = tmp_path / "data" / "processed" / "fragments_by_file.jsonl"
    fragments_path.parent.mkdir(parents=True)
    fragments_path.write_text(json.dumps(fragment) + "\n", encoding="utf-8")
    build_bm25_index(fragments_path, default_index_dir(tmp_path, "by_file"))

    result = runner.invoke(app, ["section", "--fragment-id", "U2.02.01#Conclusion"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["content"] == long_content
    assert payload["content_length"] == len(long_content)
    assert payload["is_full_section"] is True
    assert f"Taille totale : {len(long_content)} caractères" in result.stderr


def test_section_with_explicit_range_returns_only_that_slice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    fragment = {
        "fragment_id": "U2.02.01#Conclusion",
        "granularity": "by_file",
        "document_id": "U2.02.01",
        "document_title": "Comparaison DKT/DST/Q4G",
        "family": "U2",
        "aster_version": "17.4.0",
        "section_path": ["Conclusion"],
        "source_path": "source/manuals/man_u/u2/u2.02.01/conclusion.rst",
        "source_commit": "b" * 40,
        "line_start": 1,
        "line_end": 3,
        "related_commands": [],
        "content": "ligne A\nligne B\nligne C",
    }
    fragments_path = tmp_path / "data" / "processed" / "fragments_by_file.jsonl"
    fragments_path.parent.mkdir(parents=True)
    fragments_path.write_text(json.dumps(fragment) + "\n", encoding="utf-8")
    build_bm25_index(fragments_path, default_index_dir(tmp_path, "by_file"))

    result = runner.invoke(
        app,
        [
            "section",
            "--fragment-id",
            "U2.02.01#Conclusion",
            "--line-start",
            "2",
            "--line-end",
            "2",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["content"] == "ligne B\n"
    assert payload["is_full_section"] is False


def test_section_range_out_of_bounds_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aster_expert.indexing.bm25_index import build_bm25_index, default_index_dir

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    fragment = {
        "fragment_id": "U2.02.01#Conclusion",
        "granularity": "by_file",
        "document_id": "U2.02.01",
        "document_title": "Comparaison DKT/DST/Q4G",
        "family": "U2",
        "aster_version": "17.4.0",
        "section_path": ["Conclusion"],
        "source_path": "source/manuals/man_u/u2/u2.02.01/conclusion.rst",
        "source_commit": "b" * 40,
        "line_start": 1,
        "line_end": 3,
        "related_commands": [],
        "content": "ligne A\nligne B\nligne C",
    }
    fragments_path = tmp_path / "data" / "processed" / "fragments_by_file.jsonl"
    fragments_path.parent.mkdir(parents=True)
    fragments_path.write_text(json.dumps(fragment) + "\n", encoding="utf-8")
    build_bm25_index(fragments_path, default_index_dir(tmp_path, "by_file"))

    result = runner.invoke(
        app,
        [
            "section",
            "--fragment-id",
            "U2.02.01#Conclusion",
            "--line-start",
            "1",
            "--line-end",
            "50",
        ],
    )

    assert result.exit_code == 1
    assert "hors des bornes" in result.stderr


def test_section_fails_loudly_without_any_identifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))

    result = runner.invoke(app, ["section"])

    assert result.exit_code == 1
    assert "sont requis" in result.stderr


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


def test_run_fails_loudly_without_execution_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(_MINIMAL_COMM, encoding="utf-8")

    result = runner.invoke(app, ["run", str(comm_path)])

    assert result.exit_code == 1
    assert "Exécution échouée" in result.stderr


def test_run_fails_loudly_outside_allowed_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(tmp_path))
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "validation.yaml").write_text(
        "execution:\n"
        "  enabled: true\n"
        "  allowed_roots: [astest]\n"
        "  work_dir_root: data/processed/runs\n"
        "  keep_work_dir: true\n"
        "  timeout_seconds: 60\n"
        "  memory_mb: 512\n"
        '  cpus_limit: "1"\n'
        "  mpi_processes: 1\n"
        "  write_outside_work_dir: false\n",
        encoding="utf-8",
    )
    comm_path = tmp_path / "case.comm"
    comm_path.write_text(_MINIMAL_COMM, encoding="utf-8")

    result = runner.invoke(app, ["run", str(comm_path)])

    assert result.exit_code == 1
    assert "allowed_roots" in result.stderr


def test_mcp_check_reports_the_first_discrepancy_and_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aster_expert.mcp.check as check

    async def failing(*args: object, **kwargs: object) -> list[check.ToolCheck]:
        message = "outils du serveur [] ≠ outils déclarés dans le code"
        raise check.McpCheckError(message)

    monkeypatch.setattr(check, "run_check", failing)
    result = runner.invoke(app, ["mcp-check"])
    assert result.exit_code == 1
    assert "mcp-check ÉCHEC" in result.output
    assert "search_test_cases" in result.output  # the declared tools are listed first


def test_mcp_check_succeeds_when_every_tool_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aster_expert.mcp.check as check

    async def passing(*args: object, **kwargs: object) -> list[check.ToolCheck]:
        return [check.ToolCheck(tool="x", request={"a": 1}, summary="level A")]

    monkeypatch.setattr(check, "run_check", passing)
    result = runner.invoke(app, ["mcp-check"])
    assert result.exit_code == 0
    assert "mcp-check OK : 1 outils" in result.output
