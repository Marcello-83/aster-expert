"""Crochet `pre-push` (lot 48 bis, audit R4) : l'envoi est refusé au premier échec
du formatage, de l'analyse statique ou des tests, dans cet ordre."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_HOOK = _REPO / "scripts" / "git-hooks" / "pre-push"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )


def _stub(path: Path, name: str, failing: tuple[str, ...]) -> None:
    """Outil factice : journalise ses arguments, échoue pour `failing`."""
    patterns = "|".join(f'"{f}"' for f in failing) or '"__jamais__"'
    path.write_text(
        "#!/bin/sh\n"
        f'echo "{name} $*" >> "$(dirname "$0")/journal.txt"\n'
        f'case "{name} $1" in {patterns}) exit 1;; esac\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _depot(tmp_path: Path, failing: tuple[str, ...]) -> Path:
    root = tmp_path / "depot"
    distant = tmp_path / "distant.git"
    subprocess.run(["git", "init", "-q", "--bare", str(distant)], check=True)
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "essai@example.invalid")
    _git(root, "config", "user.name", "Essai")
    hooks = root / "scripts" / "git-hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-push").write_bytes(_HOOK.read_bytes())
    (hooks / "pre-push").chmod(0o755)
    _git(root, "config", "core.hooksPath", "scripts/git-hooks")
    venv = root / ".venv" / "bin"
    venv.mkdir(parents=True)
    _stub(venv / "ruff", "ruff", failing)
    _stub(venv / "pytest", "pytest", failing)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--no-verify", "-m", "essai")
    _git(root, "remote", "add", "origin", str(distant))
    return root


def test_the_hook_is_executable_and_runs_the_three_checks_in_order() -> None:
    assert _HOOK.stat().st_mode & stat.S_IXUSR
    text = _HOOK.read_text(encoding="utf-8")
    assert (
        text.index('ruff" format --check')
        < text.index('ruff" check')
        < text.index('pytest" -q')
    )


def test_a_clean_push_runs_every_check(tmp_path: Path) -> None:
    root = _depot(tmp_path, ())
    result = _git(root, "push", "-q", "origin", "HEAD:refs/heads/essai")
    assert result.returncode == 0, result.stderr
    journal = (root / ".venv" / "bin" / "journal.txt").read_text(encoding="utf-8")
    assert journal.splitlines() == [
        "ruff format --check",
        "ruff check",
        "pytest -q",
    ]


@pytest.mark.parametrize(
    ("failing", "executed"),
    [
        (("ruff format",), ["ruff format --check"]),
        (("ruff check",), ["ruff format --check", "ruff check"]),
        (("pytest -q",), ["ruff format --check", "ruff check", "pytest -q"]),
    ],
)
def test_the_first_failure_refuses_the_push(
    tmp_path: Path, failing: tuple[str, ...], executed: list[str]
) -> None:
    root = _depot(tmp_path, failing)
    result = _git(root, "push", "-q", "origin", "HEAD:refs/heads/essai")
    assert result.returncode != 0
    journal = (root / ".venv" / "bin" / "journal.txt").read_text(encoding="utf-8")
    assert journal.splitlines() == executed
    distant = _git(tmp_path / "distant.git", "branch", "--list")
    assert distant.stdout.strip() == ""
