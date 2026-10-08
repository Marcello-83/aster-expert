"""`execution:` section of `config/validation.yaml` (docs/development-plan.md, lot 11).

Read-only, validated (`pydantic`): this project never guesses an allowed root. Since
lot 47 quater, the resources of a run (time, memory, threads, MPI processes) are no
longer imposed by this file: `timeout_seconds` and `memory_mb` may be `auto` (`None`),
and `aster_expert.execution.ressources` resolves them from the command line, the
`.export`, `config/machine.local.yaml`, this file, then the machine (DIAG-025).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from aster_expert.execution.errors import ExecutionRunError
from aster_expert.execution.interdits import ForbiddenKeyword
from aster_expert.execution.ressources import (
    ResourceSettings,
    load_machine_overrides,
    settings_from,
)


def _auto(value: Any) -> Any:
    return None if value == "auto" else value


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
    timeout_seconds: int | None
    memory_mb: int | None
    mpi_processes: int
    write_outside_work_dir: bool
    ncpus: int = 1
    memory_margin_mb: int = 0
    memory_share: float = 0.8
    min_free_disk_gb: float = 10.0
    forbidden_keywords: tuple[ForbiddenKeyword, ...] = ()
    """Lot 49: keyword values refused before any run, each with its diagnosis
    (`aster_expert.execution.interdits`)."""

    def resource_settings(self, project_root: Path) -> ResourceSettings:
        """This section, overridden by `config/machine.local.yaml` when it exists."""
        raw = {
            "timeout_seconds": self.timeout_seconds,
            "memory_mb": self.memory_mb,
            "ncpus": self.ncpus,
            "mpi_processes": self.mpi_processes,
            "memory_margin_mb": self.memory_margin_mb,
            "memory_share": self.memory_share,
            "min_free_disk_gb": self.min_free_disk_gb,
        }
        return settings_from(raw, load_machine_overrides(project_root))


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
            timeout_seconds=_auto(raw["timeout_seconds"]),
            memory_mb=_auto(raw["memory_mb"]),
            mpi_processes=raw.get("mpi_processes", 1),
            write_outside_work_dir=raw["write_outside_work_dir"],
            ncpus=raw.get("ncpus", 1),
            memory_margin_mb=raw.get("memory_margin_mb", 0),
            memory_share=raw.get("memory_share", 0.8),
            min_free_disk_gb=raw.get("min_free_disk_gb", 10.0),
            forbidden_keywords=tuple(
                ForbiddenKeyword.model_validate(r)
                for r in raw.get("forbidden_keywords") or ()
            ),
        )
    except KeyError as exc:
        message = f"execution config missing key {exc} in {config_path}"
        raise ExecutionRunError(message) from exc
