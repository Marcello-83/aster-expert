"""M3: invoke scripts/check_command_syntax.py inside the Aster container.

One container invocation checks every request in the batch (not one per
statement): container startup dominates the cost of a single `docker run`,
so batching is what makes validating a file with dozens of commands
practical. See docs/architecture.md, ADR-002, ADR-006.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import run_in_container
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.validation.errors import ValidationRunError

_SCRIPT_NAME = "check_command_syntax.py"
_DEFAULT_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / _SCRIPT_NAME
_REQUESTS_NAME = "requests.json"


def run_checks(
    requests: list[dict[str, Any]],
    *,
    image_ref: str,
    workroot: Path,
    docker_bin: Path,
    network: str = "none",
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 300,
    script_path: Path = _DEFAULT_SCRIPT_PATH,
) -> dict[int, dict[str, Any]]:
    """Run every request in one container invocation. Returns id -> result."""
    if not requests:
        return {}
    if not workroot.is_dir():
        message = f"work root does not exist or is not a directory: {workroot}"
        raise ValidationRunError(message)
    if not script_path.is_file():
        message = f"checker script not found: {script_path}"
        raise ValidationRunError(message)

    work_dir = Path(tempfile.mkdtemp(prefix="aster-expert-validate-", dir=workroot))
    try:
        shutil.copy2(script_path, work_dir / _SCRIPT_NAME)
        (work_dir / _REQUESTS_NAME).write_text(
            json.dumps({"requests": requests}), encoding="utf-8"
        )

        invocation = (
            f"python3 {MOUNT_TARGET}/{_SCRIPT_NAME} "
            f"--requests {MOUNT_TARGET}/{_REQUESTS_NAME}\n"
        )
        command = build_environment_setup_script() + "\n" + invocation

        try:
            result = run_in_container(
                docker_bin=docker_bin,
                image_ref=image_ref,
                workdir=work_dir,
                command=command,
                network=network,
                memory=memory,
                cpus=cpus,
                timeout=timeout,
            )
        except EnvironmentDetectionError as exc:
            raise ValidationRunError(str(exc)) from exc

        stdout = result.stdout.strip()
        last_line = stdout.splitlines()[-1] if stdout else ""
        try:
            payload = json.loads(last_line)
        except json.JSONDecodeError as exc:
            message = (
                f"checker script produced non-JSON output on stdout: {stdout!r}, "
                f"stderr: {result.stderr.strip()!r}"
            )
            raise ValidationRunError(message) from exc

        if result.returncode != 0:
            message = (
                f"checker script exited {result.returncode}: {result.stderr.strip()}"
            )
            raise ValidationRunError(message)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return {item["id"]: item for item in payload["results"]}
