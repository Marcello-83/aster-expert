"""Resources of a run: `.export` parameters, machine, Docker limits (lot 47 quater).

Before lot 47 quater, `aster-expert run` imposed `config/validation.yaml` values on
every run (1 800 s, 8 192 Mio, `--cpus=1`) whatever the `.export` said (DIAG-025).
The limits now come, in this order of precedence, from:

1. the command line (`--timeout`, `--memory-mb`);
2. the `.export` handed to `run_aster` (`P time_limit`, `P memory_limit`, `P ncpus`,
   `P mpi_nbcpu`);
3. for the time and memory, the machine configuration (`config/machine.local.yaml`, not
   versioned, written by MM for the VM it runs on), then the `execution:` section of
   `config/validation.yaml`;
4. defaults computed from the machine (`os.sched_getaffinity`, `/proc/meminfo`), or the
   defaults of `run_aster` itself (`time_limit` 86 400 s, `ncpus` 1, `mpi_nbcpu` 1,
   `run_aster/run_aster_main.py`, 17.4.0).

`ncpus` and `mpi_nbcpu` are never taken from the configuration at run time: `run_aster`
reads them from the `.export` inside the container, and the container must get exactly
what it will use. The configuration's `ncpus` and `mpi_processes` are the values the
project chain writes into the `.export` it generates.

**Narrow reading of the `.export` (documented gap).** `run_aster.export.Export` is only
importable inside the container (ADR-002). The Docker limits must be known *before* the
container starts, so this module reads the four `P` parameters above and nothing else:
one parameter per line, `P <name> <value>` (U1.04.00 § « Fichier EXPORT », D1.02.05).
Files (`F`/`R` lines) are never interpreted here: `run_aster` keeps deciding what they
mean, inside the container.

The Docker limits follow `run_aster`'s own rules, never a rule of this project:

- CPUs: `ncpus × mpi_nbcpu` (U2.08.06 « En pratique via Astk » : `ncpus` threads per MPI
  process, `mpi_nbcpu` processes in all); refused beyond the processors of the machine
  (same notice: « pas plus de processus MPI, multipliés éventuellement par le nombre de
  threads précédent, que de cœurs physiques disponibles »);
- memory: `memory_limit` is per MPI process (U2.08.06, figure 1.6); the container gets
  `mpi_nbcpu × (memory_limit + margin)`, the margin being the `addmem` of the image's
  `run_aster` configuration (2 800 Mio in 17.4.0, read in the image at lot 47 quater),
  which `run_aster.run_sbatch_main` adds to the reservation of a batch job;
- outer time limit: `time_limit × 1.25 × ncpus` (`run_aster/run.py`,
  `RunAster.execute_study`), plus the container start margin of `execute.py`.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aster_expert.execution.errors import ExecutionRunError

RUN_ASTER_DEFAULT_TIME_LIMIT = 86400
"""`run_aster_main.main`: `export.get("time_limit", 86400.0)` (17.4.0)."""

RUN_ASTER_TIMEOUT_FACTOR = 1.25
"""`RunAster.execute_study`: `time_limit * 1.25 * ncpus` (17.4.0)."""

MACHINE_CONFIG = Path("config") / "machine.local.yaml"
"""Machine configuration written by MM, never versioned (`.gitignore`)."""

_EXPORT_KEYS = {
    "time_limit": float,
    "memory_limit": float,
    "ncpus": int,
    "mpi_nbcpu": int,
}


@dataclass(frozen=True)
class ExportParameters:
    """The four resource parameters of a `.export`, `None` when absent."""

    time_limit: float | None = None
    memory_limit: float | None = None
    ncpus: int | None = None
    mpi_nbcpu: int | None = None


def read_export_parameters(path: Path) -> ExportParameters:
    """Read `P time_limit|memory_limit|ncpus|mpi_nbcpu` of a `.export` (see module)."""
    found: dict[str, Any] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        words = raw.split()
        if len(words) < 3 or words[0] != "P" or words[1] not in _EXPORT_KEYS:
            continue
        convert = _EXPORT_KEYS[words[1]]
        try:
            value = convert(float(words[2])) if convert is int else convert(words[2])
        except ValueError as exc:
            message = (
                f"{path.name}, ligne {number} : valeur illisible pour {words[1]} "
                f"({words[2]!r})"
            )
            raise ExecutionRunError(message) from exc
        if value <= 0:
            message = f"{path.name}, ligne {number} : {words[1]} doit être positif"
            raise ExecutionRunError(message)
        found[words[1]] = value
    return ExportParameters(**found)


@dataclass(frozen=True)
class MachineResources:
    """What the machine offers this process (VM, Cloud or CI runner)."""

    cpus: int
    memory_total_mb: int
    memory_available_mb: int


def _meminfo(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        words = rest.split()
        if words and words[0].isdigit():
            values[name.strip()] = int(words[0])  # kB
    return values


def machine_resources(
    meminfo: Path = Path("/proc/meminfo"),
    cpu_count: Callable[[], int] | None = None,
) -> MachineResources:
    """Processors usable by this process and memory of the machine (Mio)."""
    cpus = len(os.sched_getaffinity(0)) if cpu_count is None else cpu_count()
    info = _meminfo(meminfo.read_text(encoding="utf-8"))
    total = info.get("MemTotal")
    available = info.get("MemAvailable", info.get("MemFree"))
    if total is None or available is None:
        message = f"{meminfo} : MemTotal ou MemAvailable absent"
        raise ExecutionRunError(message)
    return MachineResources(
        cpus=cpus, memory_total_mb=total // 1024, memory_available_mb=available // 1024
    )


@dataclass(frozen=True)
class ResourceSettings:
    """Values of the configuration (`validation.yaml`, then `machine.local.yaml`).

    `None` means « automatique » : the `.export`, then the computed default.
    """

    timeout_seconds: int | None
    memory_mb: int | None
    ncpus: int
    mpi_processes: int
    memory_margin_mb: int
    memory_share: float
    min_free_disk_gb: float
    useful_threads_max: int = 1
    """Lot 49: threads that still pay (`aster_expert.execution.regle_fils`)."""


def load_machine_overrides(project_root: Path) -> dict[str, Any]:
    """`config/machine.local.yaml` (`execution:` section), empty when absent."""
    path = project_root / MACHINE_CONFIG
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = data.get("execution", {})
    if not isinstance(section, dict):
        message = f"{path} : section `execution:` mal formée"
        raise ExecutionRunError(message)
    unknown = sorted(set(section) - set(ResourceSettings.__dataclass_fields__))
    if unknown:
        message = f"{path} : clé(s) inconnue(s) {', '.join(unknown)}"
        raise ExecutionRunError(message)
    return section


def _auto_int(value: Any, name: str) -> int | None:
    if value is None or value == "auto":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        message = f"execution.{name} : entier positif ou « auto » attendu, lu {value!r}"
        raise ExecutionRunError(message)
    return value


def settings_from(raw: dict[str, Any], overrides: dict[str, Any]) -> ResourceSettings:
    """Merge `validation.yaml` (`raw`) with the machine configuration (`overrides`)."""
    merged = {**raw, **overrides}
    share = float(merged.get("memory_share", 0.8))
    if not 0 < share <= 1:
        message = f"execution.memory_share : entre 0 et 1, lu {share}"
        raise ExecutionRunError(message)
    return ResourceSettings(
        timeout_seconds=_auto_int(merged.get("timeout_seconds"), "timeout_seconds"),
        memory_mb=_auto_int(merged.get("memory_mb"), "memory_mb"),
        ncpus=_auto_int(merged.get("ncpus", 1), "ncpus") or 1,
        mpi_processes=_auto_int(merged.get("mpi_processes", 1), "mpi_processes") or 1,
        memory_margin_mb=int(merged.get("memory_margin_mb", 0)),
        memory_share=share,
        min_free_disk_gb=float(merged.get("min_free_disk_gb", 10.0)),
        useful_threads_max=_auto_int(
            merged.get("useful_threads_max", 1), "useful_threads_max"
        )
        or 1,
    )


@dataclass(frozen=True)
class ResolvedResources:
    """Limits of one execution, each with where it came from."""

    time_limit: int
    memory_limit_mb: int
    ncpus: int
    mpi_nbcpu: int
    docker_cpus: int
    docker_memory_mb: int
    outer_timeout: int
    origins: dict[str, str]

    def summary(self) -> str:
        """One line, in French, for the terminal and the report."""
        return (
            f"ncpus {self.ncpus} ({self.origins['ncpus']}), mpi_nbcpu {self.mpi_nbcpu} "
            f"({self.origins['mpi_nbcpu']}), time_limit {self.time_limit} s "
            f"({self.origins['time_limit']}), memory_limit {self.memory_limit_mb} Mio "
            f"({self.origins['memory_limit']}) ; docker --cpus={self.docker_cpus} "
            f"--memory={self.docker_memory_mb}m ; "
            f"délai extérieur {self.outer_timeout} s"
        )


def resolve_resources(
    *,
    export: ExportParameters | None,
    settings: ResourceSettings,
    machine: MachineResources,
    cli_timeout: int | None = None,
    cli_memory_mb: int | None = None,
    start_margin_s: int = 20,
) -> ResolvedResources:
    """Apply the precedence of the module docstring; refuse what the machine lacks.

    `export` is `None` for a bare `.comm` (no `.export` sibling): `run_aster` then runs
    one process with one thread (« no data or result files are managed by
    run_aster »), so `ncpus` and `mpi_nbcpu` are 1 whatever the configuration says.
    """
    origins: dict[str, str] = {}
    exp = export or ExportParameters()
    bare = export is None

    if bare:
        ncpus, origins["ncpus"] = 1, "fichier .comm seul"
        mpi, origins["mpi_nbcpu"] = 1, "fichier .comm seul"
    else:
        # What run_aster will use inside the container: the .export, else its own
        # default (`export.get("ncpus", 1)`, `export.get("mpi_nbcpu", 1)`). The
        # configuration's `ncpus` and `mpi_processes` are the defaults written into a
        # project's .export (`aster_expert.projet.pipeline`), never imposed here.
        if exp.ncpus is not None:
            ncpus, origins["ncpus"] = exp.ncpus, ".export"
        else:
            ncpus, origins["ncpus"] = 1, "défaut de run_aster"
        if exp.mpi_nbcpu is not None:
            mpi, origins["mpi_nbcpu"] = exp.mpi_nbcpu, ".export"
        else:
            mpi, origins["mpi_nbcpu"] = 1, "défaut de run_aster"

    if cli_timeout is not None:
        time_limit, origins["time_limit"] = cli_timeout, "ligne de commande"
    elif exp.time_limit is not None:
        time_limit, origins["time_limit"] = int(exp.time_limit), ".export"
    elif settings.timeout_seconds is not None:
        time_limit, origins["time_limit"] = settings.timeout_seconds, "configuration"
    else:
        time_limit = RUN_ASTER_DEFAULT_TIME_LIMIT
        origins["time_limit"] = "défaut de run_aster"

    if cli_memory_mb is not None:
        memory, origins["memory_limit"] = cli_memory_mb, "ligne de commande"
    elif exp.memory_limit is not None:
        memory, origins["memory_limit"] = int(exp.memory_limit), ".export"
    elif settings.memory_mb is not None:
        memory, origins["memory_limit"] = settings.memory_mb, "configuration"
    else:
        per_process = machine.memory_available_mb * settings.memory_share / mpi
        memory = int(per_process) - settings.memory_margin_mb
        origins["memory_limit"] = (
            f"calculée ({settings.memory_share:g} × mémoire disponible / mpi_nbcpu)"
        )
        if memory <= 0:
            message = (
                f"mémoire disponible insuffisante ({machine.memory_available_mb} Mio) "
                f"pour {mpi} processus MPI"
            )
            raise ExecutionRunError(message)

    docker_cpus = ncpus * mpi
    if docker_cpus > machine.cpus:
        message = (
            f"ncpus × mpi_nbcpu = {ncpus} × {mpi} = {docker_cpus} dépasse les "
            f"{machine.cpus} processeurs de la machine (U2.08.06 : pas plus de tâches "
            "que de cœurs disponibles)"
        )
        raise ExecutionRunError(message)
    docker_memory = mpi * (memory + settings.memory_margin_mb)
    if docker_memory > machine.memory_total_mb:
        message = (
            f"mémoire demandée {docker_memory} Mio "
            "(mpi_nbcpu × (memory_limit + marge)) "
            f"au-delà des {machine.memory_total_mb} Mio de la machine"
        )
        raise ExecutionRunError(message)
    outer = int(time_limit * RUN_ASTER_TIMEOUT_FACTOR * ncpus) + start_margin_s
    return ResolvedResources(
        time_limit=time_limit,
        memory_limit_mb=memory,
        ncpus=ncpus,
        mpi_nbcpu=mpi,
        docker_cpus=docker_cpus,
        docker_memory_mb=docker_memory,
        outer_timeout=outer,
        origins=origins,
    )


DiskUsage = Callable[[Path], tuple[int, int, int]]


def check_free_disk(
    where: Path, min_free_gb: float, usage: DiskUsage = shutil.disk_usage
) -> float:
    """Refuse an execution below `min_free_gb` free under `where` (ENV-003 prevention).

    Returns the free space (Go) when it is enough.
    """
    _total, _used, free = usage(where)
    free_gb = free / 1e9
    if free_gb < min_free_gb:
        message = (
            f"espace disque insuffisant avant exécution : {free_gb:.1f} Go libres sous "
            f"{where} (seuil {min_free_gb:g} Go, execution.min_free_disk_gb) ; "
            "libérer de l'espace selon la politique de rétention "
            "(docs/retention_donnees.md, ENV-003)"
        )
        raise ExecutionRunError(message)
    return free_gb


__all__ = [
    "MACHINE_CONFIG",
    "RUN_ASTER_DEFAULT_TIME_LIMIT",
    "ExportParameters",
    "MachineResources",
    "ResolvedResources",
    "ResourceSettings",
    "check_free_disk",
    "load_machine_overrides",
    "machine_resources",
    "read_export_parameters",
    "resolve_resources",
    "settings_from",
]
