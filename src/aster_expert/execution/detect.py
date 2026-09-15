"""`aster-expert env detect` : resolve the containerized Aster environment.

Orchestrates docker_client to resolve the image (by digest, never by the
"stable" tag), run the in-container probe (scripts/detect_environment.py) in
a restricted, network-isolated, non-root container, and write the result into
config/versions.yaml's `detected` section without disturbing the rest of the
file. See docs/architecture.md, ADR-002, ADR-003, ADR-006.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import (
    docker_version_raw,
    find_docker_binary,
    resolve_image,
    run_in_container,
)
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import (
    AsterPythonInfo,
    CatalogueInfo,
    CodeAsterPackageInfo,
    ContainerInfo,
    DetectedEnvironment,
    InvocationInfo,
    RunAsterInfo,
)

_MOUNT_TARGET = MOUNT_TARGET
_PROBE_SCRIPT_NAME = "detect_environment.py"
_DEFAULT_PROBE_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / _PROBE_SCRIPT_NAME
)


def build_probe_command() -> str:
    invocation = (
        f"python3 {_MOUNT_TARGET}/{_PROBE_SCRIPT_NAME} \\\n"
        '    --run-aster-path "$RA" \\\n'
        '    --pythonpath-extra "$PYTHONPATH_EXTRA"\n'
    )
    return build_environment_setup_script() + "\n" + invocation


def detect_environment(
    *,
    workroot: Path,
    image_repository: str,
    image_ref_env: str | None,
    docker_bin_env: str | None = None,
    network: str = "none",
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 300,
    probe_script: Path = _DEFAULT_PROBE_SCRIPT,
    home: Path | None = None,
) -> DetectedEnvironment:
    """Resolve the Aster container environment. Fails loudly, never guesses."""
    if not workroot.is_dir():
        message = (
            f"ASTER_CONTAINER_WORKROOT does not exist or is not a directory: {workroot}"
        )
        raise EnvironmentDetectionError(message)
    if not probe_script.is_file():
        message = f"probe script not found: {probe_script}"
        raise EnvironmentDetectionError(message)

    home = home if home is not None else Path.home()
    docker_bin = find_docker_binary(docker_bin_env)
    engine_version_raw = docker_version_raw(docker_bin)
    image = resolve_image(
        docker_bin=docker_bin,
        repository=image_repository,
        image_ref_env=image_ref_env,
        cwd=Path.cwd(),
        home=home,
    )
    full_ref = f"{image.repository}@{image.digest}"

    work_dir = Path(tempfile.mkdtemp(prefix="aster-expert-detect-", dir=workroot))
    try:
        shutil.copy2(probe_script, work_dir / _PROBE_SCRIPT_NAME)
        result = run_in_container(
            docker_bin=docker_bin,
            image_ref=full_ref,
            workdir=work_dir,
            command=build_probe_command(),
            mount_target=_MOUNT_TARGET,
            network=network,
            memory=memory,
            cpus=cpus,
            timeout=timeout,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    if result.returncode != 0:
        message = (
            f"probe failed inside container '{full_ref}' "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
        raise EnvironmentDetectionError(message)

    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        message = f"probe produced non-JSON output: {result.stdout!r}"
        raise EnvironmentDetectionError(message) from exc

    return DetectedEnvironment(
        detected_at=datetime.now(UTC),
        install_kind="container_docker",
        container=ContainerInfo(
            engine="docker",
            engine_version_raw=engine_version_raw,
            image_repository=image.repository,
            image_tag=image.tag,
            image_digest=image.digest,
            image_id=image.image_id,
            cave_pin_source=image.cave_pin_source,
        ),
        run_aster=RunAsterInfo(**probe["run_aster"]),
        aster_python=AsterPythonInfo(
            interpreter_path_in_container=probe["aster_python"][
                "interpreter_path_in_container"
            ],
            pythonpath_extra=tuple(probe["aster_python"]["pythonpath_extra"]),
        ),
        code_aster_package=CodeAsterPackageInfo(**probe["code_aster_package"]),
        catalogue=CatalogueInfo(**probe["catalogue"]),
        invocation=InvocationInfo(
            mechanism="profile_sh_plus_view",
            mount_pattern=f"<répertoire de travail dédié>:{_MOUNT_TARGET}",
        ),
    )


# Matches only the indented lines belonging to the block: a following blank
# line (the usual separator before the next section) is left untouched.
_DETECTED_BLOCK_PATTERN = re.compile(r"^detected:\n(?:[ \t]+[^\n]*\n)*", re.MULTILINE)


def write_detected_section(
    versions_yaml_path: Path, detected: DetectedEnvironment
) -> None:
    """Replace the `detected:` block in config/versions.yaml, in place.

    Every other section of the file (header comments, `target`, `versions`,
    `policy`, and their comments) is left byte-for-byte untouched: only the
    machine-written `detected:` block is regenerated.
    """
    text = versions_yaml_path.read_text(encoding="utf-8")
    if not _DETECTED_BLOCK_PATTERN.search(text):
        message = f"'detected:' section not found in {versions_yaml_path}"
        raise EnvironmentDetectionError(message)

    payload = {"detected": json.loads(detected.model_dump_json())}
    rendered = yaml.safe_dump(
        payload, sort_keys=False, allow_unicode=True, default_flow_style=False
    )

    new_text = _DETECTED_BLOCK_PATTERN.sub(rendered, text, count=1)
    versions_yaml_path.write_text(new_text, encoding="utf-8")
