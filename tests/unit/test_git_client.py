"""Unit tests for aster_expert.ingestion.git_client.

Local, temporary Git repositories only: no network access, no history-wide
operation (`git log --all`, `git log -S`) — see docs/development-plan.md,
lot 3, memory constraint.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aster_expert.ingestion import git_client
from aster_expert.ingestion.git_client import GitCommandError


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603, S607
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=path)
    _git("config", "user.name", "Test", cwd=path)
    _git("config", "user.email", "test@example.invalid", cwd=path)


def _commit(path: Path, filename: str, content: str, message: str) -> str:
    (path / filename).write_text(content, encoding="utf-8")
    _git("add", filename, cwd=path)
    _git("commit", "-q", "-m", message, cwd=path)
    return _git("rev-parse", "HEAD", cwd=path).stdout.strip()


@pytest.fixture
def remote_repo(tmp_path: Path) -> dict[str, object]:
    """A local 'remote': one commit on `main`, an annotated tag `v1` on it,

    a second commit on `main` afterwards (so `main` and `v1` diverge, which
    is what the divergence tests need), and a lightweight tag `v1-light`.
    """
    work = tmp_path / "work"
    _init_repo(work)
    first_commit = _commit(work, "README.md", "hello\n", "init")
    _git("tag", "-a", "v1", "-m", "release v1", cwd=work)
    v1_commit = first_commit
    _git("tag", "v1-light", cwd=work)
    second_commit = _commit(work, "README.md", "hello again\n", "second")

    bare = tmp_path / "remote.git"
    _git("clone", "-q", "--bare", str(work), str(bare), cwd=tmp_path)

    return {
        "url": str(bare),
        "v1_commit": v1_commit,
        "main_commit": second_commit,
        "work": work,
    }


def test_clone_lands_on_tag(tmp_path: Path, remote_repo: dict[str, object]) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    assert git_client.current_commit(dest) == remote_repo["v1_commit"]


def test_clone_lands_on_branch(tmp_path: Path, remote_repo: dict[str, object]) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "main", dest)

    assert git_client.current_commit(dest) == remote_repo["main_commit"]


def test_clone_unknown_ref_raises(
    tmp_path: Path, remote_repo: dict[str, object]
) -> None:
    dest = tmp_path / "clone"
    with pytest.raises(GitCommandError):
        git_client.clone(str(remote_repo["url"]), "no-such-ref", dest)


def test_is_git_repository(tmp_path: Path, remote_repo: dict[str, object]) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    assert git_client.is_git_repository(dest)
    assert not git_client.is_git_repository(tmp_path / "not-a-repo")


def test_working_copy_dirty(tmp_path: Path, remote_repo: dict[str, object]) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    assert not git_client.working_copy_dirty(dest)

    (dest / "untracked.txt").write_text("x\n", encoding="utf-8")
    assert git_client.working_copy_dirty(dest)

    (dest / "untracked.txt").unlink()
    assert not git_client.working_copy_dirty(dest)

    (dest / "README.md").write_text("modified\n", encoding="utf-8")
    assert git_client.working_copy_dirty(dest)


def test_peel_to_commit_handles_annotated_and_lightweight_tags(
    tmp_path: Path, remote_repo: dict[str, object]
) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest, partial=False)
    git_client.fetch(dest, "v1-light", partial=False)

    annotated_tag_sha = _git("rev-parse", "refs/tags/v1", cwd=dest).stdout.strip()
    assert (
        git_client.peel_to_commit(dest, annotated_tag_sha) == remote_repo["v1_commit"]
    )

    lightweight_tag_sha = git_client.resolve_local_ref_commit(dest)
    assert lightweight_tag_sha == remote_repo["v1_commit"]
    assert (
        git_client.peel_to_commit(dest, lightweight_tag_sha) == remote_repo["v1_commit"]
    )


def test_fetch_resolves_branch_not_covered_by_the_initial_clone(
    tmp_path: Path, remote_repo: dict[str, object]
) -> None:
    # Regression: after `clone(..., ref="v1")` (--single-branch), the
    # configured fetch refspec only covers "v1" — verified empirically that
    # a plain `git fetch origin main` then updates no ref at all. `fetch()`
    # must resolve "main" correctly regardless.
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    git_client.fetch(dest, "main")
    assert git_client.resolve_local_ref_commit(dest) == remote_repo["main_commit"]


def test_fetch_resolves_annotated_tag_to_its_commit(
    tmp_path: Path, remote_repo: dict[str, object]
) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "main", dest)

    git_client.fetch(dest, "v1")
    assert git_client.resolve_local_ref_commit(dest) == remote_repo["v1_commit"]


def test_fetch_unknown_ref_raises(
    tmp_path: Path, remote_repo: dict[str, object]
) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    with pytest.raises(GitCommandError):
        git_client.fetch(dest, "does-not-exist")


def test_remote_url(tmp_path: Path, remote_repo: dict[str, object]) -> None:
    dest = tmp_path / "clone"
    git_client.clone(str(remote_repo["url"]), "v1", dest)

    assert git_client.remote_url(dest) == str(remote_repo["url"])

    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    assert git_client.remote_url(not_a_repo) is None
