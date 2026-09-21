"""`aster-expert mesh run`: run a Salome script headless, in a dedicated directory.

The script is executed by the Salome-Meca Singularity image declared in
`config/validation.yaml` (`mesh.salome`). Nothing about the image, the launch
command or the expected version is coded here. The run fails when Salome exits
in error, when its log holds a Python traceback, when no MED file is produced,
when the installed version differs from the expected one, or when a parameter
file was given and the script did not record its fingerprint (rule of
`CLAUDE.md`, "Scripts Salome").

The script receives `sys.argv[1:] = [<params file name>, <output MED name>]`
(or only the output name without parameters) and must write, next to the MED,
`<output stem>.meta.json` holding `{"params_sha256": ...}`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shlex
import shutil
import subprocess
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from aster_expert.meshing.config import MeshConfig
from aster_expert.meshing.errors import MeshRunError

logger = logging.getLogger(__name__)

WORK_MOUNT = "/work"
REPORT_NAME = "mesh_run_report.json"
LOG_NAME = "salome.log"
DIGEST_CACHE_NAME = "image_digests.json"

Runner = Callable[[list[str], int], "subprocess.CompletedProcess[str]"]


class MeshRunReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    work_dir: str
    script_name: str
    script_sha256: str
    params_name: str | None
    params_sha256: str | None
    params_sha256_recorded_by_script: str | None
    med_path: str
    med_sha256: str
    log_path: str
    salome_version: str
    expected_version: str
    image_path: str
    image_sha256: str
    image_sha256_source: str
    command: tuple[str, ...]
    duration_s: float
    executed_at: datetime


def _default_runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv built from typed configuration, no shell
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def image_sha256(image: Path, cache_path: Path) -> tuple[str, str]:
    """Fingerprint of the image, and where it came from ("computed" or "cache").

    Hashing a 5 Gio image takes over a minute, so a digest is reused as long as
    path, size and modification time are unchanged (the cache key).
    """
    stat = image.stat()
    key = f"{image}|{stat.st_size}|{stat.st_mtime_ns}"
    cache: dict[str, str] = {}
    if cache_path.is_file():
        try:
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cache = {str(k): str(v) for k, v in loaded.items()}
        except (OSError, ValueError):
            cache = {}
    if key in cache:
        return cache[key], "cache"
    logger.info("hashing Salome image %s (size %d)", image, stat.st_size)
    digest = sha256_file(image)
    cache[key] = digest
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    return digest, "computed"


def _exec_prefix(config: MeshConfig) -> list[str]:
    salome = config.salome
    return [salome.runtime, "exec", *salome.container_options]


def read_salome_version(
    config: MeshConfig, image: Path, runner: Runner = _default_runner
) -> str:
    """Version string read inside the image, from the file named in the config."""
    salome = config.salome
    version_file = f"{salome.install_root}/{salome.version_file}"
    argv = [*_exec_prefix(config), str(image), "cat", version_file]
    result = runner(argv, 120)
    if result.returncode != 0:
        message = f"cannot read {version_file} in {image}: {result.stderr.strip()}"
        raise MeshRunError(message)
    match = re.search(salome.version_pattern, result.stdout)
    if match is None:
        message = (
            f"pattern {salome.version_pattern!r} not found in {version_file} of {image}"
        )
        raise MeshRunError(message)
    return match.group(1)


def build_shell_command(config: MeshConfig, script_name: str, args: list[str]) -> str:
    salome = config.salome
    sources = [
        f"source {shlex.quote(f'{salome.install_root}/{name}')}"
        for name in salome.env_scripts
    ]
    launch = salome.command.format(
        script=shlex.quote(f"{WORK_MOUNT}/{script_name}"), args=",".join(args)
    )
    return " && ".join([*sources, launch])


def run_salome_script(
    script: Path,
    *,
    project_root: Path,
    config: MeshConfig,
    params: Path | None = None,
    runner: Runner = _default_runner,
) -> MeshRunReport:
    if not script.is_file():
        message = f"script not found: {script}"
        raise MeshRunError(message)
    if params is not None and not params.is_file():
        message = f"parameters file not found: {params}"
        raise MeshRunError(message)
    salome = config.salome
    image = Path(salome.image_path).expanduser()
    if not image.is_file():
        message = f"Salome image not found: {image} (mesh.salome.image_path)"
        raise MeshRunError(message)
    if shutil.which(salome.runtime) is None:
        message = f"runtime {salome.runtime!r} not found in PATH (mesh.salome.runtime)"
        raise MeshRunError(message)

    version = read_salome_version(config, image, runner)
    if version != salome.expected_version:
        message = (
            f"Salome version {version!r} differs from the expected "
            f"{salome.expected_version!r} (mesh.salome.expected_version)"
        )
        raise MeshRunError(message)

    work_dir_root = project_root / config.work_dir_root
    work_dir_root.mkdir(parents=True, exist_ok=True)
    image_digest, digest_source = image_sha256(image, work_dir_root / DIGEST_CACHE_NAME)

    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    work_dir = work_dir_root / run_id
    work_dir.mkdir()
    shutil.copy2(script, work_dir / script.name)
    args: list[str] = []
    if params is not None:
        shutil.copy2(params, work_dir / params.name)
        args.append(params.name)
    med_name = f"{script.stem}.med"
    args.append(med_name)
    for name in (script.name, *args):
        if "," in name or " " in name:
            message = f"file name {name!r} must not contain a comma or a space"
            raise MeshRunError(message)

    shell = build_shell_command(config, script.name, args)
    argv = [
        *_exec_prefix(config),
        "--bind",
        f"{work_dir}:{WORK_MOUNT}",
        "--pwd",
        WORK_MOUNT,
        str(image),
        "bash",
        "-c",
        shell,
    ]
    logger.info("running Salome script %s in %s", script, work_dir)
    started = time.monotonic()
    try:
        result = runner(argv, salome.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        message = (
            f"Salome exceeded {salome.timeout_seconds} s "
            f"(mesh.salome.timeout_seconds); work directory kept: {work_dir}"
        )
        raise MeshRunError(message) from exc
    duration = time.monotonic() - started

    log_path = work_dir / LOG_NAME
    log_path.write_text(
        f"$ {shell}\n--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n",
        encoding="utf-8",
    )
    if result.returncode != 0:
        message = f"Salome exited with code {result.returncode}; log: {log_path}"
        raise MeshRunError(message)
    if "Traceback (most recent call last)" in result.stdout + result.stderr:
        message = f"the script raised a Python exception; log: {log_path}"
        raise MeshRunError(message)
    med_path = work_dir / med_name
    if not med_path.is_file():
        message = f"no MED file produced ({med_name} absent); log: {log_path}"
        raise MeshRunError(message)

    params_sha = sha256_file(params) if params is not None else None
    recorded: str | None = None
    meta_path = work_dir / f"{script.stem}.meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            recorded = meta.get("params_sha256")
        except ValueError:
            recorded = None
    if params_sha is not None and recorded != params_sha:
        message = (
            f"the script did not record the fingerprint of its parameters "
            f"(expected {params_sha} in {meta_path.name}, found {recorded!r})"
        )
        raise MeshRunError(message)

    report = MeshRunReport(
        work_dir=str(work_dir),
        script_name=script.name,
        script_sha256=sha256_file(script),
        params_name=params.name if params is not None else None,
        params_sha256=params_sha,
        params_sha256_recorded_by_script=recorded,
        med_path=str(med_path),
        med_sha256=sha256_file(med_path),
        log_path=str(log_path),
        salome_version=version,
        expected_version=salome.expected_version,
        image_path=str(image),
        image_sha256=image_digest,
        image_sha256_source=digest_source,
        command=tuple(argv),
        duration_s=duration,
        executed_at=datetime.now(UTC),
    )
    (work_dir / REPORT_NAME).write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    return report
