"""`mesh:` section of `config/validation.yaml` (lot 26).

Nothing about Salome (image path, launch command, expected version) is coded
in Python: it all comes from this section.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from aster_expert.meshing.errors import MeshConfigError


class SalomeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    runtime: str
    image_path: str
    expected_version: str
    install_root: str
    version_file: str
    version_pattern: str
    env_scripts: tuple[str, ...]
    container_options: tuple[str, ...]
    command: str
    timeout_seconds: int


class CheckerConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    work_dir_root: str
    timeout_seconds: int
    memory_mb: int
    cpus_limit: str


class MeshConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    work_dir_root: str
    salome: SalomeConfig
    checker: CheckerConfig


def load_mesh_config(config_path: Path) -> MeshConfig:
    if not config_path.is_file():
        message = f"mesh config not found: {config_path}"
        raise MeshConfigError(message)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = data.get("mesh")
    if not isinstance(raw, dict):
        message = f"'mesh:' section missing or malformed in {config_path}"
        raise MeshConfigError(message)
    try:
        return MeshConfig.model_validate(raw)
    except ValidationError as exc:
        message = f"invalid 'mesh:' section in {config_path}: {exc}"
        raise MeshConfigError(message) from exc
