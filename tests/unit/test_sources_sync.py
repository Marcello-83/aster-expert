"""Unit tests for `aster-expert sources sync` (aster_expert.ingestion.sync).

Local, temporary Git repositories only: no network access. Covers the exit
criteria of docs/development-plan.md lot 3: idempotence, refusal to
overwrite a dirty working copy, and reconciliation of a pre-existing,
diverged working copy without correcting it.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from aster_expert.ingestion import git_client, sync
from aster_expert.ingestion.errors import SourcesConfigError

FIXED_NOW = datetime(2026, 9, 16, 8, 0, 0, tzinfo=UTC)


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
    work = tmp_path / "upstream_work"
    _init_repo(work)
    v1_commit = _commit(work, "catalogue.py", "# catalogue v1\n", "init")
    _git("tag", "-a", "v1", "-m", "release v1", cwd=work)
    main_commit = _commit(work, "catalogue.py", "# catalogue v2\n", "second")

    bare = tmp_path / "upstream.git"
    _git("clone", "-q", "--bare", str(work), str(bare), cwd=tmp_path)

    return {"url": str(bare), "v1_commit": v1_commit, "main_commit": main_commit}


def _write_sources_yaml(
    project_root: Path, *, url: str, ref: str, commit: str | None
) -> Path:
    config = {
        "schema_version": 1,
        "defaults": {
            "clone_root": "external",
            "update_policy": "fetch_and_checkout",
            "allow_dirty": False,
            "partial_clone": True,
            "depth": None,
        },
        "sources": [
            {
                "name": "codeaster-src",
                "url": url,
                "ref": ref,
                "commit": commit,
                "local_path": "external/codeaster-src",
                "license": "GPL-3.0",
                "families": {
                    "catalogue": {"enabled": True, "paths": []},
                    "testcases": {"enabled": False, "paths": []},
                },
            }
        ],
    }
    path = project_root / "config" / "sources.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def project_root(tmp_path: Path, remote_repo: dict[str, object]) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    _write_sources_yaml(
        root,
        url=str(remote_repo["url"]),
        ref="v1",
        commit=str(remote_repo["v1_commit"]),
    )
    return root


def test_sync_clones_absent_source(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    assert len(manifest.sources) == 1
    entry = manifest.sources[0]
    assert entry.status == "cloned"
    assert entry.commit == remote_repo["v1_commit"]
    assert entry.dirty is False
    assert entry.families == ("catalogue",)
    assert (project_root / "external" / "codeaster-src" / "catalogue.py").is_file()

    manifest_path = sync.default_manifest_path(project_root)
    assert manifest_path.is_file()
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["sources"][0]["status"] == "cloned"


def test_sync_adopts_existing_matching_repo(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    local_path = project_root / "external" / "codeaster-src"
    git_client.clone(str(remote_repo["url"]), "v1", local_path)

    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    entry = manifest.sources[0]
    assert entry.status == "adopted"
    assert entry.commit == remote_repo["v1_commit"]
    assert entry.dirty is False


def test_sync_idempotent_across_two_consecutive_runs(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    # First run creates the source (a one-time, state-creating action).
    sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    # The next two runs both operate on an already-synced, matching source:
    # this is the steady state idempotence actually claims.
    manifest_2 = sync.sync_sources(project_root=project_root, now=FIXED_NOW)
    manifest_3 = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    assert manifest_2 == manifest_3
    assert manifest_2.sources[0].status == "adopted"


def test_sync_refuses_dirty_working_copy_without_touching_it(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    sync.sync_sources(project_root=project_root, now=FIXED_NOW)
    local_path = project_root / "external" / "codeaster-src"
    (local_path / "catalogue.py").write_text("# local edit\n", encoding="utf-8")

    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    entry = manifest.sources[0]
    assert entry.status == "blocked_dirty"
    assert entry.dirty is True
    assert entry.detail is not None
    # the local edit survives untouched
    assert (local_path / "catalogue.py").read_text(encoding="utf-8") == "# local edit\n"
    assert git_client.working_copy_dirty(local_path)


def test_sync_reports_divergence_without_correcting_it(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    local_path = project_root / "external" / "codeaster-src"
    # Clone onto "main" (a different commit than the declared ref "v1").
    git_client.clone(str(remote_repo["url"]), "main", local_path)
    commit_before = git_client.current_commit(local_path)
    assert commit_before == remote_repo["main_commit"]

    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    entry = manifest.sources[0]
    assert entry.status == "blocked_diverged"
    assert entry.commit == remote_repo["main_commit"]
    assert str(remote_repo["v1_commit"]) in (entry.detail or "")
    # never checked out or reset: the working copy is exactly as it was
    assert git_client.current_commit(local_path) == commit_before


def test_sync_blocks_on_remote_url_mismatch(
    project_root: Path, remote_repo: dict[str, object], tmp_path: Path
) -> None:
    local_path = project_root / "external" / "codeaster-src"
    other_work = tmp_path / "other_upstream"
    _init_repo(other_work)
    _commit(other_work, "readme.txt", "unrelated\n", "init")
    git_client.clone(str(other_work), "main", local_path)

    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    entry = manifest.sources[0]
    assert entry.status == "blocked_error"
    assert "origin remote" in (entry.detail or "")


def test_sync_missing_config_raises(tmp_path: Path) -> None:
    with pytest.raises(SourcesConfigError):
        sync.sync_sources(project_root=tmp_path, now=FIXED_NOW)


def test_sync_unknown_ref_is_blocked_error(
    project_root: Path, remote_repo: dict[str, object]
) -> None:
    _write_sources_yaml(
        project_root, url=str(remote_repo["url"]), ref="no-such-ref", commit=None
    )

    manifest = sync.sync_sources(project_root=project_root, now=FIXED_NOW)

    entry = manifest.sources[0]
    assert entry.status == "blocked_error"
    assert entry.commit is None
