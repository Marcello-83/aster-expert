"""Smoke tests for the CLI skeleton."""

from __future__ import annotations

from typer.testing import CliRunner

from aster_expert import __version__
from aster_expert.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_unimplemented_command_fails_loudly() -> None:
    result = runner.invoke(app, ["sources", "sync"])
    assert result.exit_code == 1
