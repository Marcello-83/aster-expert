"""Level-C containerized execution of a `.comm` file (docs/development-plan.md, lot 11).

Orchestrates `docker_client` and `scripts/run_comm.py` (itself a thin wrapper
around `run_aster.run_aster_main.main`/`run_aster.status.Status`, see that
script's docstring) the same way `aster_expert.validation.checker_client`
already orchestrates `scripts/check_command_syntax.py` -- one dedicated,
ephemeral work directory per invocation, mounted restricted
(docs/architecture.md, ADR-006), never the project's generic
`ASTER_CONTAINER_WORKROOT` scratch root: unlike catalogue extraction or
validation, this work directory is the report's own evidence
(`config/validation.yaml`, `execution.keep_work_dir: true`) and lives at a
known, project-relative location (`execution.work_dir_root`), not a
throwaway temp directory outside the repository.

**Sibling-file staging, not `.export` parsing (a deliberate, narrow
exception to O1's "no output analyzer" -- this is an *input* staging
convenience, never analysis of what `run_aster` produced).** An official cas
test's `.export` only ever references files by their bare name
(`external/codeaster-src/run_aster/export.py`, "F type path DRC unit" --
verified directly on `astest/zzzz169a.export`: `zzzz169a.comm`,
`zzzz169a.12`, `zzzz169a.mmed`, all siblings of the `.export` itself, no
sub-directory). Rather than parse the DRC file format ourselves (a real
reimplementation of `run_aster.export.Export`, forbidden by ADR-002 for this
project's own Python -- that class is only ever importable inside the
container), this module copies every file that shares the `.comm`'s stem
(`<stem>.*`) into the work directory whenever a sibling `<stem>.export`
exists, and hands `run_aster` the `.export` file: the real `Export`/`File`
machinery, running inside the container, is what actually decides which of
those files matter and for which logical unit -- this project never opens
the `.export` file itself. Without a sibling `.export`, the bare `.comm` is
handed to `run_aster` directly (its own documented "direct file" mode,
`external/codeaster-src/run_aster/run_aster_main.py`: "no data or result
files are managed by run_aster" -- a real, documented limitation of that
mode, not one this project invented).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aster_expert.chemins import PathRefusedError, execution_policy, resolve_input_path
from aster_expert.connaissances.declaration import AppliedKnowledge
from aster_expert.execution.compte_rendu import (
    build_record,
    parse_messages,
    sha256_file,
    write_record,
)
from aster_expert.execution.config import ExecutionConfig
from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import (
    kill_container,
    run_in_container,
)
from aster_expert.execution.errors import EnvironmentDetectionError, ExecutionRunError
from aster_expert.execution.models import DIAG_TO_STATUS, ExecutionReport
from aster_expert.execution.ressources import (
    DiskUsage,
    MachineResources,
    ResolvedResources,
    check_free_disk,
    machine_resources,
    read_export_parameters,
    resolve_resources,
)

_SCRIPT_NAME = "_aster_expert_run_comm.py"
_DEFAULT_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "run_comm.py"
_STATUS_FILE_NAME = "__status__"
# run_aster.run.TMPMESS (external/codeaster-src/run_aster/run.py).
_MESS_FILE_NAME = "fort.6"

# Added to the outer subprocess timeout (docs/architecture.md, ADR-006: « le délai
# maximal enveloppe l'appel docker run lui-même... pour couvrir aussi un conteneur qui
# ne se terminerait pas »). Since lot 47 quater the outer timeout is
# `time_limit × 1.25 × ncpus` (run_aster's own rule, see
# `aster_expert.execution.ressources`) plus this margin, which only covers container
# startup/shutdown (~25 s measured at lot 10c).
_TIMEOUT_MARGIN_SECONDS = 20


def check_allowed(
    comm_path: Path, *, config: ExecutionConfig, project_root: Path
) -> Path:
    """Refuse a `.comm` outside the configured roots. Never falls back to permissive.

    Goes through the common path resolution (lot 46): links and `..` are resolved
    before the comparison to `execution.allowed_roots`.
    """
    policy = execution_policy(config.allowed_roots, project_root)
    try:
        return resolve_input_path(
            comm_path, policy=policy, base=Path.cwd(), suffixes=(".comm",)
        )
    except PathRefusedError as exc:
        raise ExecutionRunError(str(exc)) from exc


def _declared_knowledge(comm: Path, project_root: Path) -> AppliedKnowledge | None:
    """Declaration of the knowledge applied (lot 46), refused before any container
    starts when a project's run has none or names an entry the base does not hold."""
    from aster_expert.connaissances.base import (  # noqa: PLC0415
        KnowledgeBaseError,
        load_knowledge,
    )
    from aster_expert.connaissances.declaration import (  # noqa: PLC0415
        DeclarationError,
        companion_path,
        load_for_run,
        project_of,
    )

    if not companion_path(comm).is_file() and project_of(comm, project_root) is None:
        return None
    try:
        base = load_knowledge(project_root)
        return load_for_run(comm, project_root, {*base.entries, *base.constats})
    except (DeclarationError, KnowledgeBaseError) as exc:
        raise ExecutionRunError(str(exc)) from exc


# Resolved at call time, so that the unit tests can replace it (tests/conftest.py):
# a unit test never depends on the free space of the machine that runs it.
_disk_usage: DiskUsage = shutil.disk_usage


def disk_floor_gb(configured: float) -> float:
    """Free space required before a run (Go): the configured threshold, lowered to the
    one of `env-check` in the `cloud` and `ci` profiles (2 Go: a GitHub runner has about
    4 Go free), never raised. Lot 47 quater, ENV-003."""
    from aster_expert.environnement.verification import (  # noqa: PLC0415
        MIN_FREE_GB,
        EnvCheckError,
        detect_profile,
    )

    try:
        profile, _reason = detect_profile()
    except EnvCheckError:
        return configured
    return configured if profile == "vm" else min(configured, MIN_FREE_GB[profile])


def plan_resources(
    comm: Path,
    *,
    config: ExecutionConfig,
    project_root: Path,
    timeout_seconds: int | None = None,
    memory_mb: int | None = None,
    machine: MachineResources | None = None,
) -> ResolvedResources:
    """Limits of the run of `comm` (lot 47 quater): its `.export` sibling, when there is
    one, is what `run_aster` will execute, so its resource parameters are read here and
    passed on to `docker run` (`aster_expert.execution.ressources`)."""
    export_sibling = comm.with_name(f"{comm.stem}.export")
    export = (
        read_export_parameters(export_sibling) if export_sibling.is_file() else None
    )
    return resolve_resources(
        export=export,
        settings=config.resource_settings(project_root),
        machine=machine or machine_resources(),
        cli_timeout=timeout_seconds,
        cli_memory_mb=memory_mb,
        start_margin_s=_TIMEOUT_MARGIN_SECONDS,
    )


def _stage_inputs(comm_path: Path, work_dir: Path) -> str:
    """Copy the `.comm` (and any `<stem>.*` siblings, see module docstring).

    Returns the basename to hand to `run_aster`: the `.export` sibling's
    name when one exists, the `.comm`'s own name otherwise.
    """
    stem = comm_path.stem
    export_sibling = comm_path.with_name(f"{stem}.export")
    if export_sibling.is_file():
        for sibling in sorted(comm_path.parent.glob(f"{stem}.*")):
            if sibling.is_file():
                shutil.copy2(sibling, work_dir / sibling.name)
        return export_sibling.name

    shutil.copy2(comm_path, work_dir / comm_path.name)
    return comm_path.name


def _staged_relative_files(work_dir: Path) -> set[str]:
    return {str(p.relative_to(work_dir)) for p in work_dir.rglob("*") if p.is_file()}


def _find_mess_path(work_dir: Path) -> str | None:
    """Locate `run_aster.run.TMPMESS` ("fort.6"), possibly under `proc.N/`.

    `RunAster.execute` nests the working directory under `proc.<rank>`
    whenever the image reports itself as an MPI-parallel build
    (`external/codeaster-src/run_aster/run.py`), regardless of whether more
    than one process was actually requested -- confirmed in session on
    `simvia/code_aster:17.4.0`, docs/development-plan.md, lot 11: a plain
    `mpi_nbcpu=1` run still lands its `fort.6` at `<work_dir>/proc.0/fort.6`,
    never at the work directory's own root. There is only ever one `fort.6`
    per invocation of this function (unit 6 is reserved -- `run_aster.run.
    copy_datafiles` itself raises if a staged data file claims it), so the
    first match is unambiguous.
    """
    direct = work_dir / _MESS_FILE_NAME
    if direct.is_file():
        return str(direct)
    nested = sorted(work_dir.rglob(_MESS_FILE_NAME))
    return str(nested[0]) if nested else None


def execute_comm_file(
    comm_path: Path,
    *,
    project_root: Path,
    config: ExecutionConfig,
    docker_bin: Path,
    image_repository: str,
    image_digest: str,
    aster_version: str,
    network: str = "none",
    timeout_seconds: int | None = None,
    memory_mb: int | None = None,
    script_path: Path = _DEFAULT_SCRIPT_PATH,
    machine: MachineResources | None = None,
    disk_usage: DiskUsage | None = None,
) -> ExecutionReport:
    if not config.enabled:
        message = (
            "execution is disabled (config/validation.yaml, execution.enabled: false)"
        )
        raise ExecutionRunError(message)

    resolved_comm = check_allowed(comm_path, config=config, project_root=project_root)
    knowledge = _declared_knowledge(resolved_comm, project_root)

    if not script_path.is_file():
        message = f"run_comm.py script not found: {script_path}"
        raise ExecutionRunError(message)

    resources = plan_resources(
        resolved_comm,
        config=config,
        project_root=project_root,
        timeout_seconds=timeout_seconds,
        memory_mb=memory_mb,
        machine=machine,
    )
    effective_timeout = resources.time_limit
    effective_memory_mb = resources.memory_limit_mb

    work_dir_root = project_root / config.work_dir_root
    work_dir_root.mkdir(parents=True, exist_ok=True)
    settings = config.resource_settings(project_root)
    check_free_disk(
        work_dir_root,
        disk_floor_gb(settings.min_free_disk_gb),
        disk_usage or _disk_usage,
    )
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    work_dir = work_dir_root / run_id
    work_dir.mkdir(parents=True)

    entry_name = _stage_inputs(resolved_comm, work_dir)
    inputs_sha256 = {
        name: sha256_file(work_dir / name)
        for name in sorted(_staged_relative_files(work_dir))
    }
    shutil.copy2(script_path, work_dir / _SCRIPT_NAME)
    staged_before = _staged_relative_files(work_dir)

    status_file = f"{MOUNT_TARGET}/{_STATUS_FILE_NAME}"
    invocation = (
        f"python3 {MOUNT_TARGET}/{_SCRIPT_NAME} "
        f"--file {MOUNT_TARGET}/{entry_name} "
        f"--wrkdir {MOUNT_TARGET} "
        f"--status-file {status_file} "
        f"--time-limit {effective_timeout} "
        f"--memory-limit {effective_memory_mb}\n"
    )
    command = build_environment_setup_script() + "\n" + invocation

    image_ref = f"{image_repository}@{image_digest}"
    container_name = f"aster-expert-run-{uuid.uuid4().hex}"
    outer_timeout = resources.outer_timeout

    started = time.monotonic()
    try:
        result = run_in_container(
            docker_bin=docker_bin,
            image_ref=image_ref,
            workdir=work_dir,
            command=command,
            network=network,
            memory=f"{resources.docker_memory_mb}m",
            cpus=str(resources.docker_cpus),
            timeout=outer_timeout,
            container_name=container_name,
        )
    except subprocess.TimeoutExpired:
        kill_container(docker_bin, container_name)
        duration_s = time.monotonic() - started
        timed_out = ExecutionReport(
            comm_path=str(resolved_comm),
            aster_version=aster_version,
            image_digest=image_digest,
            status="interrupted_timeout",
            diag=None,
            return_code=None,
            work_dir=str(work_dir),
            mess_path=None,
            result_files=(),
            duration_s=duration_s,
            extracted_by="run_aster.status",
            executed_at=datetime.now(UTC),
        )
        if config.keep_work_dir:
            write_record(
                build_record(
                    timed_out,
                    command=invocation.strip(),
                    image=image_ref,
                    inputs_sha256=inputs_sha256,
                    knowledge_root=project_root,
                    knowledge=knowledge,
                    resources=resources.summary(),
                )
            )
        else:
            shutil.rmtree(work_dir, ignore_errors=True)
        return timed_out
    except EnvironmentDetectionError as exc:
        if not config.keep_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
        raise ExecutionRunError(str(exc)) from exc
    duration_s = time.monotonic() - started

    stdout = result.stdout.strip()
    last_line = stdout.splitlines()[-1] if stdout else ""
    try:
        payload: dict[str, Any] = json.loads(last_line)
    except Exception as exc:  # noqa: BLE001 - reported as ExecutionRunError, not swallowed
        message = (
            f"run_comm.py produced non-JSON output on stdout: {stdout!r}, "
            f"stderr: {result.stderr.strip()!r}"
        )
        raise ExecutionRunError(message) from exc

    mess_path = _find_mess_path(work_dir)

    staged_after = _staged_relative_files(work_dir)
    produced = staged_after - staged_before - {_STATUS_FILE_NAME, _SCRIPT_NAME}
    result_files = tuple(sorted(produced))

    if not payload.get("ok", False):
        report = ExecutionReport(
            comm_path=str(resolved_comm),
            aster_version=aster_version,
            image_digest=image_digest,
            status="crashed",
            diag=None,
            return_code=payload.get("return_code"),
            work_dir=str(work_dir),
            mess_path=mess_path,
            result_files=result_files,
            duration_s=duration_s,
            extracted_by="run_aster.status",
            executed_at=datetime.now(UTC),
            messages=parse_messages(payload.get("messages") or []),
            messages_error=payload.get("crash"),
        )
    else:
        diag = payload.get("diag")
        status = DIAG_TO_STATUS.get(diag) if diag is not None else None
        if status is None:
            message = (
                f"run_aster.status produced an unrecognized diagnostic string: "
                f"{diag!r} (an unrecognized value fails loudly rather than "
                "being guessed into an existing bucket)"
            )
            raise ExecutionRunError(message)
        report = ExecutionReport(
            comm_path=str(resolved_comm),
            aster_version=aster_version,
            image_digest=image_digest,
            status=status,
            diag=diag,
            return_code=payload.get("return_code"),
            work_dir=str(work_dir),
            mess_path=mess_path,
            result_files=result_files,
            duration_s=duration_s,
            extracted_by="run_aster.status",
            executed_at=datetime.now(UTC),
            messages=parse_messages(payload.get("messages") or []),
            messages_source=payload.get("messages_source"),
            status_source=payload.get("status_source"),
            messages_truncated=int(payload.get("messages_truncated") or 0),
            messages_error=payload.get("messages_error"),
        )

    if config.keep_work_dir:
        # Lot 41 : compte rendu lisible à côté de l'exécution (JSON et Markdown).
        write_record(
            build_record(
                report,
                command=invocation.strip(),
                image=image_ref,
                inputs_sha256=inputs_sha256,
                knowledge_root=project_root,
                knowledge=knowledge,
                resources=resources.summary(),
            )
        )
    else:
        shutil.rmtree(work_dir, ignore_errors=True)

    return report


__all__ = ["check_allowed", "disk_floor_gb", "execute_comm_file", "plan_resources"]
