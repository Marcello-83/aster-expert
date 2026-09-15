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


def test_unimplemented_command_fails_loudly() -> None:
    result = runner.invoke(app, ["sources", "sync"])
    assert result.exit_code == 1


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
