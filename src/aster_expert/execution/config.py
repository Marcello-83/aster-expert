"""`execution:` section of `config/validation.yaml` (docs/development-plan.md, lot 11).

Read-only, validated (`pydantic`): this project never guesses a timeout, a
memory limit, or an allowed root -- every one of these comes from this file,
or an explicit CLI override of it.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from aster_expert.execution.errors import ExecutionRunError


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    # Project-relative or absolute directories a `.comm` may be executed
    # from. Empty means no root is authorized yet -- `aster-expert run`
    # refuses every file explicitly rather than fall back to "unrestricted"
    # (docs/development-plan.md, lot 11, O2).
    allowed_roots: tuple[str, ...]
    work_dir_root: str
    keep_work_dir: bool
    timeout_seconds: int
    memory_mb: int
    cpus_limit: str
    mpi_processes: int
    write_outside_work_dir: bool


def load_execution_config(config_path: Path) -> ExecutionConfig:
    if not config_path.is_file():
        message = f"execution config not found: {config_path}"
        raise ExecutionRunError(message)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = data.get("execution")
    if not isinstance(raw, dict):
        message = f"'execution:' section missing or malformed in {config_path}"
        raise ExecutionRunError(message)
    try:
        return ExecutionConfig(
            enabled=raw["enabled"],
            allowed_roots=tuple(raw.get("allowed_roots") or ()),
            work_dir_root=raw["work_dir_root"],
            keep_work_dir=raw["keep_work_dir"],
            timeout_seconds=raw["timeout_seconds"],
            memory_mb=raw["memory_mb"],
            cpus_limit=str(raw.get("cpus_limit", "1")),
            mpi_processes=raw.get("mpi_processes", 1),
            write_outside_work_dir=raw["write_outside_work_dir"],
        )
    except KeyError as exc:
        message = f"execution config missing key {exc} in {config_path}"
        raise ExecutionRunError(message) from exc
