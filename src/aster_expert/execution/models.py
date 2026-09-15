"""Data models for the `detected` section of config/versions.yaml.

See docs/architecture.md, ADR-002, ADR-003, ADR-006.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# The "stable" and "testing" tags are mobile aliases on the registry side and
# have been observed to diverge from the locally cached image of the same
# name (docs/architecture.md, ADR-002). They are never a valid resolved tag.
FORBIDDEN_IMAGE_TAGS = frozenset({"stable", "testing"})


class ResolvedImage(BaseModel):
    """Identity of the container image actually used, resolved by digest."""

    model_config = ConfigDict(frozen=True)

    repository: str
    tag: str
    digest: str
    image_id: str
    cave_pin_source: str  # "directory" | "global" | "none"


class ContainerInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str
    engine_version_raw: str
    image_repository: str
    image_tag: str
    image_digest: str
    image_id: str
    cave_pin_source: str


class RunAsterInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str
    version_raw: str


class AsterPythonInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    interpreter_path_in_container: str
    pythonpath_extra: tuple[str, ...]


class CodeAsterPackageInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str


class CatalogueInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path_in_container: str
    fingerprint_sha256: str


class InvocationInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    mechanism: str
    mount_pattern: str


class DetectedEnvironment(BaseModel):
    """The full `detected` section written to config/versions.yaml."""

    model_config = ConfigDict(frozen=True)

    detected_at: datetime
    install_kind: str
    container: ContainerInfo
    run_aster: RunAsterInfo
    aster_python: AsterPythonInfo
    code_aster_package: CodeAsterPackageInfo
    catalogue: CatalogueInfo
    invocation: InvocationInfo
