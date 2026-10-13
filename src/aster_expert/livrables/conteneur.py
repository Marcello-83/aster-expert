"""Run `scripts/livrables_med.py` in the Code_Aster image (lot 49).

The project's Python has no MED module (ADR-002): the combinations and envelopes are
written into the MED by `medcoupling` inside the container, as `mesh check` and
`aster_expert.report.med_read` already do (network disabled, non-root user, one
dedicated directory mounted). The arithmetic is `aster_expert.livrables.calcul`, copied
next to the script.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import (
    find_docker_binary,
    kill_container,
    run_in_container,
)
from aster_expert.validation.validate import resolve_digest_for_version

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "livrables_med.py"
CALCUL = Path(__file__).resolve().parent / "calcul.py"
SCRIPT_CHARGES = ROOT / "scripts" / "livrables_charges.py"

ContainerRunner = Callable[..., "subprocess.CompletedProcess[str]"]


class ContainerError(RuntimeError):
    pass


def run_deliverables_container(
    files: dict[str, Path],
    spec: dict[str, Any],
    *,
    project_root: Path = ROOT,
    work_root: Path,
    memory_mb: int = 12288,
    timeout_seconds: int = 7200,
    runner: ContainerRunner = run_in_container,
    script: Path = SCRIPT,
) -> Path:
    """Copy `files` (name in the working directory -> source), the spec, the script
    and `calcul.py` into a new directory under `work_root`, run the script there and
    return the directory. The copies of the input MED files are deleted afterwards
    (ENV-003: a copy per reading filled the disk at lot 47 ter)."""
    digest, _ = resolve_digest_for_version(
        project_root / "data" / "processed" / "catalogue",
        None,
        project_root / "config" / "versions.yaml",
    )
    repository = os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")
    docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
    work_root.mkdir(parents=True, exist_ok=True)
    work = work_root / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    work.mkdir()
    for name, source in files.items():
        shutil.copy2(source, work / name)
    shutil.copy2(script, work / script.name)
    shutil.copy2(CALCUL, work / CALCUL.name)
    (work / "spec.json").write_text(
        json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    command = (
        build_environment_setup_script()
        + f"\npython3 {MOUNT_TARGET}/{script.name} {MOUNT_TARGET}/spec.json "
        f"{MOUNT_TARGET}/out.json\n"
    )
    name = f"aster-expert-livrables-{uuid.uuid4().hex}"
    try:
        result = runner(
            docker_bin=docker_bin,
            image_ref=f"{repository}@{digest}",
            workdir=work,
            command=command,
            network="none",
            memory=f"{memory_mb}m",
            cpus="1",
            timeout=timeout_seconds,
            container_name=name,
        )
    except subprocess.TimeoutExpired as exc:
        kill_container(docker_bin, name)
        message = f"livrables : conteneur au-delà de {timeout_seconds} s"
        raise ContainerError(message) from exc
    finally:
        for input_name in files:
            if input_name != "charges.med":
                (work / input_name).unlink(missing_ok=True)
    (work / "conteneur.log").write_text(
        (result.stdout or "") + (result.stderr or ""), encoding="utf-8"
    )
    if result.returncode != 0:
        message = (
            f"livrables : script en échec (code {result.returncode}) : "
            f"{(result.stderr or result.stdout).strip()[-1500:]}"
        )
        raise ContainerError(message)
    return work


__all__ = ["SCRIPT_CHARGES", "ContainerError", "run_deliverables_container"]
