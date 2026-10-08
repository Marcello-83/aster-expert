"""Threads of a run, by the rule of lot 49.

Rule (consigne of lot 49, step 0, set on the measurements of
`docs/essais_lot49.md` § 1): number of threads = processors available ÷ number of runs
started at the same time, capped by the number of threads that still pay
(`execution.useful_threads_max`, from the measurements; beyond it a run is slower).
One run alone gets every useful thread; three variants run together share the
machine. MPI stays off by default (`execution.mpi_processes: 1`, lot 47 quater: no gain
measured).

The values come from `config/validation.yaml`, overridden by `config/machine.local.yaml`
(`aster_expert.execution.ressources.load_machine_overrides`).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aster_expert.execution.ressources import (
    MachineResources,
    load_machine_overrides,
    machine_resources,
)

DEFAULT_USEFUL_THREADS = 1


def useful_threads(project_root: Path) -> int:
    """`execution.useful_threads_max` (machine file first), else 1."""
    raw: dict[str, object] = {}
    config = project_root / "config" / "validation.yaml"
    if config.is_file():
        data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        raw = dict(data.get("execution", {}) or {})
    value = load_machine_overrides(project_root).get(
        "useful_threads_max", raw.get("useful_threads_max", DEFAULT_USEFUL_THREADS)
    )
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        message = f"execution.useful_threads_max : entier positif attendu, lu {value!r}"
        raise ValueError(message)
    return value


def threads_for(
    project_root: Path,
    concurrent: int = 1,
    machine: MachineResources | None = None,
) -> int:
    """Threads of each of `concurrent` runs started together (at least 1)."""
    if concurrent < 1:
        message = f"nombre d'exécutions simultanées : {concurrent}"
        raise ValueError(message)
    cpus = (machine or machine_resources()).cpus
    return max(1, min(useful_threads(project_root), cpus // concurrent))


__all__ = ["DEFAULT_USEFUL_THREADS", "threads_for", "useful_threads"]
