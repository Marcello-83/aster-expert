"""`aster-expert mesh check`: verify a MED file against an invariants file.

The MED file is read **without Salome**: `scripts/dump_med.py` runs with
`medcoupling` inside the Code_Aster Docker image (restricted container: network
disabled, non-root user, resource limits, only a dedicated directory mounted).
Nothing is installed in the project environment. The comparison itself is done
here, on the JSON dump (`aster_expert.meshing.invariants`).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import kill_container, run_in_container
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.meshing.config import MeshConfig
from aster_expert.meshing.errors import MeshCheckError
from aster_expert.meshing.invariants import (
    InvariantResult,
    MedDump,
    evaluate,
    format_report,
    load_invariants,
)
from aster_expert.meshing.run import sha256_file

logger = logging.getLogger(__name__)

_DUMP_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "dump_med.py"
_MED_NAME = "input.med"
_DUMP_NAME = "dump.json"
REPORT_NAME = "rapport_mesh_check.txt"

ContainerRunner = Callable[..., "subprocess.CompletedProcess[str]"]


class MeshCheckReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    med_path: str
    med_sha256: str
    invariants_path: str
    invariants_sha256: str
    image_ref: str
    work_dir: str
    report_path: str
    results: tuple[InvariantResult, ...]
    ok: bool
    checked_at: datetime


def check_med(
    med: Path,
    invariants_path: Path,
    *,
    project_root: Path,
    config: MeshConfig,
    docker_bin: Path,
    image_ref: str,
    runner: ContainerRunner = run_in_container,
    script_path: Path = _DUMP_SCRIPT,
) -> MeshCheckReport:
    if not med.is_file():
        message = f"MED file not found: {med}"
        raise MeshCheckError(message)
    if not script_path.is_file():
        message = f"dump script not found: {script_path}"
        raise MeshCheckError(message)
    invariants = load_invariants(invariants_path)

    checker = config.checker
    root = project_root / checker.work_dir_root
    root.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    work_dir = root / run_id
    work_dir.mkdir()
    shutil.copy2(med, work_dir / _MED_NAME)
    shutil.copy2(script_path, work_dir / script_path.name)

    command = (
        build_environment_setup_script()
        + f"\npython3 {MOUNT_TARGET}/{script_path.name} "
        f"{MOUNT_TARGET}/{_MED_NAME} {MOUNT_TARGET}/{_DUMP_NAME}\n"
    )
    container_name = f"aster-expert-mesh-check-{uuid.uuid4().hex}"
    logger.info("reading %s with medcoupling in %s", med, image_ref)
    try:
        result = runner(
            docker_bin=docker_bin,
            image_ref=image_ref,
            workdir=work_dir,
            command=command,
            network="none",
            memory=f"{checker.memory_mb}m",
            cpus=checker.cpus_limit,
            timeout=checker.timeout_seconds,
            container_name=container_name,
        )
    except subprocess.TimeoutExpired as exc:
        kill_container(docker_bin, container_name)
        message = f"MED reading exceeded {checker.timeout_seconds} s"
        raise MeshCheckError(message) from exc
    except EnvironmentDetectionError as exc:
        raise MeshCheckError(str(exc)) from exc
    if result.returncode != 0:
        message = (
            f"medcoupling could not read {med} (code {result.returncode}): "
            f"{(result.stderr or result.stdout).strip()[-800:]}"
        )
        raise MeshCheckError(message)
    dump_path = work_dir / _DUMP_NAME
    if not dump_path.is_file():
        message = f"the reader produced no dump ({_DUMP_NAME} absent in {work_dir})"
        raise MeshCheckError(message)

    dump = MedDump.model_validate_json(dump_path.read_text(encoding="utf-8"))
    results = evaluate(dump, invariants)
    report_text = format_report(med.name, results)
    report_path = work_dir / REPORT_NAME
    report_path.write_text(report_text, encoding="utf-8")
    return MeshCheckReport(
        med_path=str(med),
        med_sha256=sha256_file(med),
        invariants_path=str(invariants_path),
        invariants_sha256=sha256_file(invariants_path),
        image_ref=image_ref,
        work_dir=str(work_dir),
        report_path=str(report_path),
        results=tuple(results),
        ok=all(r.ok for r in results),
        checked_at=datetime.now(UTC),
    )
