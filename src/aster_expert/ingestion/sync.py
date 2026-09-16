"""`aster-expert sources sync` : orchestrates config/sources.yaml.

For each declared source: clone if `local_path` is absent, else fetch and
reconcile. A working copy carrying uncommitted changes, or one whose checked
out commit diverges from what the declared `ref` resolves to on the remote,
is never touched further: it is reported in the manifest and left exactly as
found (CLAUDE.md, "Gestion des dépôts externes"; docs/development-plan.md,
lot 3).

Idempotence, precisely defined: cloning a source that is not yet present is
a one-time, state-creating action (`status: "cloned"`) — asking that to be
idempotent against "nothing existed" is not meaningful. What is required,
and tested, is that once a source is present and matches its declaration,
repeated runs (`status: "adopted"`) leave it, and the manifest, unchanged:
no `git` command that could modify the working copy is even issued in that
steady state, only a bounded `fetch` of the one declared ref.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aster_expert.ingestion import git_client
from aster_expert.ingestion.errors import SourcesConfigError
from aster_expert.ingestion.git_client import GitCommandError
from aster_expert.ingestion.models import (
    Manifest,
    ManifestSourceEntry,
    SourceConfig,
    SourcesDefaults,
    SourcesFile,
    SyncStatus,
)


def default_sources_yaml_path(project_root: Path) -> Path:
    return project_root / "config" / "sources.yaml"


def default_manifest_path(project_root: Path) -> Path:
    return project_root / "data" / "raw" / "manifest.json"


def load_sources_config(path: Path) -> SourcesFile:
    if not path.is_file():
        message = f"config/sources.yaml introuvable : {path}"
        raise SourcesConfigError(message)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        message = f"config/sources.yaml invalide : {exc}"
        raise SourcesConfigError(message) from exc
    try:
        return SourcesFile.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError, kept generic on purpose
        message = f"config/sources.yaml ne respecte pas le schéma attendu : {exc}"
        raise SourcesConfigError(message) from exc


class _EntryFactory:
    """Binds the fields constant for one source, so each branch below only

    ever states what actually varies: status, commit, dirty, detail.
    """

    def __init__(
        self,
        source: SourceConfig,
        *,
        families: tuple[str, ...],
        now: datetime,
    ) -> None:
        self._source = source
        self._families = families
        self._now = now

    def __call__(
        self,
        status: SyncStatus,
        *,
        commit: str | None,
        dirty: bool,
        detail: str | None,
    ) -> ManifestSourceEntry:
        source = self._source
        return ManifestSourceEntry(
            name=source.name,
            url=source.url,
            ref=source.ref,
            commit=commit,
            local_path=str(source.local_path),
            synchronized_at=self._now,
            dirty=dirty,
            families=self._families,
            status=status,
            detail=detail,
        )


def _sync_one_source(
    source: SourceConfig,
    defaults: SourcesDefaults,
    *,
    project_root: Path,
    now: datetime,
    timeout: int,
) -> ManifestSourceEntry:
    local_path = project_root / source.local_path
    policy = source.update_policy or defaults.update_policy
    make_entry = _EntryFactory(source, families=source.enabled_family_names(), now=now)

    if not local_path.is_dir():
        return _clone_fresh(
            source,
            defaults,
            local_path=local_path,
            policy=policy,
            make_entry=make_entry,
            timeout=timeout,
        )
    return _reconcile_existing(
        source,
        defaults,
        local_path=local_path,
        policy=policy,
        make_entry=make_entry,
        timeout=timeout,
    )


def _clone_fresh(
    source: SourceConfig,
    defaults: SourcesDefaults,
    *,
    local_path: Path,
    policy: str,
    make_entry: _EntryFactory,
    timeout: int,
) -> ManifestSourceEntry:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Every fresh clone lands directly on the declared `ref` — a single
        # bounded ref, never a full-history clone, whatever `policy` says
        # ("pinned" without the ref existing on the remote is not supported:
        # documented limitation, see docs/development-plan.md lot 3).
        git_client.clone(
            source.url,
            source.ref,
            local_path,
            partial=defaults.partial_clone,
            depth=defaults.depth,
            timeout=timeout,
        )
    except GitCommandError as exc:
        return make_entry(
            "blocked_error", commit=None, dirty=False, detail=f"clone failed: {exc}"
        )

    commit = git_client.current_commit(local_path)
    detail = f"cloned '{source.ref}' fresh, now at {commit}"

    declared_peeled = (
        git_client.peel_to_commit(local_path, source.commit)
        if source.commit is not None
        else None
    )
    if declared_peeled is not None and declared_peeled != commit:
        detail += (
            f"; note: config/sources.yaml declares commit {source.commit} "
            f"(peels to {declared_peeled}), which differs from the freshly "
            "cloned commit — the clone is authoritative, the declaration may "
            "need updating"
        )

    if policy == "pinned" and declared_peeled is not None and declared_peeled != commit:
        return make_entry(
            "blocked_error",
            commit=commit,
            dirty=False,
            detail=(
                f"'pinned' policy: declared commit {source.commit} (peels to "
                f"{declared_peeled}) is not what ref '{source.ref}' resolves "
                f"to ({commit}); refusing an unbounded clone to search for "
                "the pinned commit"
            ),
        )

    return make_entry("cloned", commit=commit, dirty=False, detail=detail)


def _reconcile_existing(
    source: SourceConfig,
    defaults: SourcesDefaults,
    *,
    local_path: Path,
    policy: str,
    make_entry: _EntryFactory,
    timeout: int,
) -> ManifestSourceEntry:
    if not git_client.is_git_repository(local_path):
        return make_entry(
            "blocked_error",
            commit=None,
            dirty=False,
            detail=f"{local_path} exists but is not a Git repository",
        )

    origin = git_client.remote_url(local_path)
    if origin is not None and _normalize_url(origin) != _normalize_url(source.url):
        return make_entry(
            "blocked_error",
            commit=git_client.current_commit(local_path),
            dirty=git_client.working_copy_dirty(local_path),
            detail=(
                f"origin remote is '{origin}', declared url is '{source.url}'; "
                "refusing to treat this working copy as the declared source"
            ),
        )

    dirty = git_client.working_copy_dirty(local_path)
    if dirty and not defaults.allow_dirty:
        return make_entry(
            "blocked_dirty",
            commit=git_client.current_commit(local_path),
            dirty=True,
            detail=(
                "working copy has uncommitted changes; synchronization "
                "refused, nothing was fetched or checked out"
            ),
        )

    if policy == "fetch_only":
        return _fetch_only(
            source,
            defaults,
            local_path=local_path,
            dirty=dirty,
            make_entry=make_entry,
            timeout=timeout,
        )

    return _fetch_and_reconcile(
        source,
        defaults,
        local_path=local_path,
        policy=policy,
        dirty=dirty,
        make_entry=make_entry,
        timeout=timeout,
    )


def _fetch_only(
    source: SourceConfig,
    defaults: SourcesDefaults,
    *,
    local_path: Path,
    dirty: bool,
    make_entry: _EntryFactory,
    timeout: int,
) -> ManifestSourceEntry:
    try:
        git_client.fetch(
            local_path,
            source.ref,
            partial=defaults.partial_clone,
            depth=defaults.depth,
            timeout=timeout,
        )
    except GitCommandError as exc:
        return make_entry(
            "blocked_error",
            commit=git_client.current_commit(local_path),
            dirty=dirty,
            detail=f"fetch failed: {exc}",
        )
    return make_entry(
        "adopted",
        commit=git_client.current_commit(local_path),
        dirty=dirty,
        detail="fetch_only: remote-tracking refs updated, working copy left untouched",
    )


def _fetch_and_reconcile(
    source: SourceConfig,
    defaults: SourcesDefaults,
    *,
    local_path: Path,
    policy: str,
    dirty: bool,
    make_entry: _EntryFactory,
    timeout: int,
) -> ManifestSourceEntry:
    """`fetch_and_checkout` / `pinned` : adopt if it matches, else stop.

    Never checks out or resets an existing working copy — only a fresh
    clone (`_clone_fresh`) ever lands on a commit it didn't already have.
    """
    try:
        git_client.fetch(
            local_path,
            source.ref,
            partial=defaults.partial_clone,
            depth=defaults.depth,
            timeout=timeout,
        )
        target_commit = git_client.resolve_local_ref_commit(local_path)
    except GitCommandError as exc:
        return make_entry(
            "blocked_error",
            commit=git_client.current_commit(local_path),
            dirty=dirty,
            detail=f"fetch/resolve failed: {exc}",
        )

    current = git_client.current_commit(local_path)

    if policy == "pinned":
        return _reconcile_pinned(
            source,
            local_path=local_path,
            current=current,
            dirty=dirty,
            make_entry=make_entry,
        )

    if current == target_commit:
        detail = (
            f"working copy matches declared ref '{source.ref}' at {current}, "
            "adopted as-is"
        )
        if source.commit is not None:
            declared_peeled = git_client.peel_to_commit(local_path, source.commit)
            if declared_peeled != target_commit:
                detail += (
                    f"; note: config/sources.yaml declares commit "
                    f"{source.commit} (peels to {declared_peeled}), which "
                    f"differs from what ref '{source.ref}' resolves to on "
                    f"the remote now ({target_commit})"
                )
        return make_entry("adopted", commit=current, dirty=dirty, detail=detail)

    return make_entry(
        "blocked_diverged",
        commit=current,
        dirty=dirty,
        detail=(
            f"working copy is at {current}, but ref '{source.ref}' resolves "
            f"to {target_commit} on the remote; refusing to check out or "
            "reset — signalled, not corrected"
        ),
    )


def _reconcile_pinned(
    source: SourceConfig,
    *,
    local_path: Path,
    current: str,
    dirty: bool,
    make_entry: _EntryFactory,
) -> ManifestSourceEntry:
    if source.commit is None:
        return make_entry(
            "blocked_error",
            commit=current,
            dirty=dirty,
            detail="'pinned' policy requires a declared commit",
        )
    declared_peeled = git_client.peel_to_commit(local_path, source.commit)
    if current == declared_peeled:
        return make_entry(
            "adopted",
            commit=current,
            dirty=dirty,
            detail=f"working copy pinned at declared commit {declared_peeled}",
        )
    return make_entry(
        "blocked_diverged",
        commit=current,
        dirty=dirty,
        detail=(
            f"working copy is at {current}, declared pinned commit is "
            f"{declared_peeled}; refusing to check out or reset"
        ),
    )


def _normalize_url(url: str) -> str:
    stripped = url.strip().rstrip("/")
    if stripped.endswith(".git"):
        stripped = stripped[: -len(".git")]
    return stripped


def sync_sources(
    *,
    project_root: Path,
    sources_yaml_path: Path | None = None,
    manifest_path: Path | None = None,
    now: datetime | None = None,
    timeout: int = 600,
) -> Manifest:
    """Synchronize every source declared in config/sources.yaml.

    Never raises for a single source's dirty or diverged working copy: that
    is a reported outcome (`status`), not a pipeline failure. Only a
    malformed config, or a filesystem it cannot write to, raises.
    """
    config_path = sources_yaml_path or default_sources_yaml_path(project_root)
    config = load_sources_config(config_path)
    resolved_now = now if now is not None else datetime.now(UTC)

    entries = tuple(
        _sync_one_source(
            source,
            config.defaults,
            project_root=project_root,
            now=resolved_now,
            timeout=timeout,
        )
        for source in config.sources
    )
    manifest = Manifest(generated_at=resolved_now, sources=entries)

    output_path = manifest_path or default_manifest_path(project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(json.loads(manifest.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return manifest
