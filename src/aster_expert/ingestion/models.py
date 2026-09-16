"""Data models for config/sources.yaml and data/raw/manifest.json.

See docs/corpus.md sections 1 and 5.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

UpdatePolicy = Literal["fetch_only", "fetch_and_checkout", "pinned"]


class SourceFamily(BaseModel):
    """One documentary/code family carried by a source (docs/corpus.md §3)."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    paths: tuple[str, ...] = ()


class SourceConfig(BaseModel):
    """One declared external repository (config/sources.yaml `sources[]`)."""

    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    ref: str
    commit: str | None = None
    local_path: str
    license: str
    families: dict[str, SourceFamily]
    update_policy: UpdatePolicy | None = None

    def enabled_family_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(name for name, family in self.families.items() if family.enabled)
        )


class SourcesDefaults(BaseModel):
    model_config = ConfigDict(frozen=True)

    clone_root: str
    update_policy: UpdatePolicy
    allow_dirty: bool
    partial_clone: bool
    depth: int | None = None


class SecondarySource(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    indexed: bool
    note: str


class SourcesFile(BaseModel):
    """The parsed content of config/sources.yaml."""

    model_config = ConfigDict(frozen=True)

    schema_version: int
    defaults: SourcesDefaults
    sources: tuple[SourceConfig, ...]
    secondary_sources: tuple[SecondarySource, ...] = ()


# Status of a single source's synchronization attempt. A `blocked_*` status
# is a normal, reported outcome, never an exception: this project never
# corrects a diverging or dirty working copy with authority (CLAUDE.md,
# "Gestion des dépôts externes").
SyncStatus = Literal[
    "cloned",
    "adopted",
    "blocked_dirty",
    "blocked_diverged",
    "blocked_error",
]


class ManifestSourceEntry(BaseModel):
    """One entry of data/raw/manifest.json `sources[]` (docs/corpus.md §5).

    `status`/`detail` are an amendment (lot 3) to the schema sketched in
    docs/corpus.md: the documented fields alone cannot distinguish a source
    that was actually synchronized from one whose sync was refused (dirty
    working copy, or a working copy diverged from the declaration) without
    losing information silently, which CLAUDE.md forbids.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    ref: str
    commit: str | None
    local_path: str
    synchronized_at: datetime
    dirty: bool
    families: tuple[str, ...]
    status: SyncStatus
    detail: str | None = None


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    sources: tuple[ManifestSourceEntry, ...]
