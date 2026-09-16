"""Thin wrapper around the `git` CLI, used exclusively by `ingestion.sync`.

Memory constraint (this VM has 11 GiB and has already saturated once): every
function here does at most one bounded, single-ref Git operation. None of
them ever walks the whole history — no `git log --all`, no `git log -S`, no
plain `git fetch` without an explicit refspec that could pull every branch.
A partial clone (`--filter=blob:none`) is used unless the caller disables it.

`fetch()` always writes the resolved ref to one fixed, private local ref
(`_SYNC_TARGET_REF`) via an explicit `+<ref>:<dest>` refspec, rather than
relying on `remote.origin.fetch` to already cover it. This matters: after a
`--single-branch --branch <tag>` clone, that config only covers the cloned
tag (verified empirically — plain `git fetch origin <other-ref>` fetches
into `FETCH_HEAD` only and updates no ref at all in that case). An explicit
destination works uniformly for a branch, an annotated tag (dereferenced to
its commit automatically — verified empirically), or a lightweight tag,
without needing to guess which kind `ref` is.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitCommandError(Exception):
    """Raised when a `git` invocation fails or a ref cannot be resolved.

    Never raised on a guess: every case is a literal non-zero exit status or
    an absent ref, reported with the exact command and output.
    """


def _run(
    args: list[str], *, cwd: Path | None = None, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    argv = ["git", *args]
    try:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        message = f"'{' '.join(argv)}' timed out after {timeout}s"
        raise GitCommandError(message) from exc


def _require_ok(
    result: subprocess.CompletedProcess[str], *, action: str
) -> subprocess.CompletedProcess[str]:
    if result.returncode != 0:
        message = f"{action} failed: {result.stderr.strip() or result.stdout.strip()}"
        raise GitCommandError(message)
    return result


def is_git_repository(path: Path) -> bool:
    if not path.is_dir():
        return False
    result = _run(["rev-parse", "--git-dir"], cwd=path)
    return result.returncode == 0


def remote_url(path: Path, *, remote: str = "origin", timeout: int = 30) -> str | None:
    result = _run(["remote", "get-url", remote], cwd=path, timeout=timeout)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def working_copy_dirty(path: Path, *, timeout: int = 60) -> bool:
    """True if there are uncommitted changes: staged, unstaged, or untracked.

    A read-only status check, never a history walk.
    """
    result = _require_ok(
        _run(
            ["status", "--porcelain=v1", "--untracked-files=normal"],
            cwd=path,
            timeout=timeout,
        ),
        action=f"'git status' in {path}",
    )
    return bool(result.stdout.strip())


def current_commit(path: Path, *, timeout: int = 30) -> str:
    """The peeled commit HEAD currently points to (never a tag object sha)."""
    result = _require_ok(
        _run(["rev-parse", "HEAD^{commit}"], cwd=path, timeout=timeout),
        action=f"'git rev-parse HEAD' in {path}",
    )
    return result.stdout.strip()


def peel_to_commit(path: Path, sha: str, *, timeout: int = 30) -> str:
    """Resolve `sha` (a commit or an annotated tag object) to its commit.

    Requires the object to already be present locally (post-clone/fetch).
    """
    result = _require_ok(
        _run(["rev-parse", f"{sha}^{{commit}}"], cwd=path, timeout=timeout),
        action=f"resolving {sha} to a commit in {path}",
    )
    return result.stdout.strip()


def clone(
    url: str,
    ref: str,
    dest: Path,
    *,
    partial: bool = True,
    depth: int | None = None,
    timeout: int = 600,
) -> None:
    """Clone `url` straight onto `ref` (tag or branch).

    Never a full history scan: `--branch --single-branch` fetches and checks
    out exactly one ref.
    """
    args = ["clone"]
    if partial:
        args += ["--filter=blob:none"]
    if depth:
        args += ["--depth", str(depth)]
    args += ["--branch", ref, "--single-branch", url, str(dest)]
    _require_ok(_run(args, timeout=timeout), action=f"'git clone --branch {ref} {url}'")


# Private to this module: never a branch or tag name a human would choose,
# so it can never collide with one already present in a source repository.
_SYNC_TARGET_REF = "refs/aster-expert-sync/target"


def fetch(
    path: Path,
    ref: str,
    *,
    partial: bool = True,
    depth: int | None = None,
    timeout: int = 600,
) -> None:
    """Fetch exactly `ref` from `origin`, whether it is a tag or a branch.

    Written to `_SYNC_TARGET_REF`, always the same commit-only ref
    afterwards (`resolve_local_ref_commit`) — never `--all`, never a bare
    `git fetch` that would rely on whatever `remote.origin.fetch` happens to
    already cover.
    """
    args = ["fetch"]
    if partial:
        args += ["--filter=blob:none"]
    if depth:
        args += ["--depth", str(depth)]
    args += ["origin", f"+{ref}:{_SYNC_TARGET_REF}"]
    _require_ok(
        _run(args, cwd=path, timeout=timeout),
        action=f"'git fetch origin {ref}' in {path}",
    )


def resolve_local_ref_commit(path: Path, *, timeout: int = 30) -> str:
    """The commit `fetch()` last resolved `ref` to. Requires a prior fetch()."""
    result = _require_ok(
        _run(
            ["rev-parse", f"{_SYNC_TARGET_REF}^{{commit}}"], cwd=path, timeout=timeout
        ),
        action=f"resolving the last fetched ref in {path}",
    )
    return result.stdout.strip()
