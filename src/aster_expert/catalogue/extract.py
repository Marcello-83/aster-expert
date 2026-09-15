"""`aster-expert catalogue extract` : run the catalogue introspection.

Resolves the Aster environment (lot 2), runs `scripts/introspect_catalogue.py`
inside a restricted container (mount limited to a dedicated directory, no
network, non-root user — docs/architecture.md, ADR-006), and writes the
resulting command schemas to `data/processed/catalogue/<digest>/`, replacing
any prior extraction for that digest. See docs/development-plan.md, lot 4.
"""

from __future__ import annotations

import json
import shlex
import shutil
import tempfile
from pathlib import Path

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import CommandSchema, ExtractionSummary
from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import find_docker_binary, run_in_container
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import DetectedEnvironment

_SCRIPT_NAME = "introspect_catalogue.py"
_DEFAULT_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / _SCRIPT_NAME
_OUTPUT_SUBDIR = "out"


def build_extraction_command(
    *, image_digest: str, catalogue_hash: str, aster_version: str
) -> str:
    args = [
        f"{MOUNT_TARGET}/{_SCRIPT_NAME}",
        "--image-digest",
        image_digest,
        "--catalogue-hash",
        catalogue_hash,
        "--aster-version",
        aster_version,
        "--output-dir",
        f"{MOUNT_TARGET}/{_OUTPUT_SUBDIR}",
    ]
    invocation = "python3 " + " ".join(shlex.quote(a) for a in args) + "\n"
    return build_environment_setup_script() + "\n" + invocation


def _run_introspection(
    *,
    detected: DetectedEnvironment,
    work_dir: Path,
    docker_bin: Path,
    network: str,
    memory: str | None,
    cpus: str | None,
    timeout: int,
) -> ExtractionSummary:
    full_ref = (
        f"{detected.container.image_repository}@{detected.container.image_digest}"
    )
    try:
        result = run_in_container(
            docker_bin=docker_bin,
            image_ref=full_ref,
            workdir=work_dir,
            command=build_extraction_command(
                image_digest=detected.container.image_digest,
                catalogue_hash=detected.catalogue.fingerprint_sha256,
                aster_version=detected.container.image_tag,
            ),
            mount_target=MOUNT_TARGET,
            network=network,
            memory=memory,
            cpus=cpus,
            timeout=timeout,
        )
    except EnvironmentDetectionError as exc:
        raise CatalogueExtractionError(str(exc)) from exc

    stdout = result.stdout.strip()
    summary_line = stdout.splitlines()[-1] if stdout else ""
    try:
        summary_data = json.loads(summary_line)
    except json.JSONDecodeError as exc:
        message = (
            f"introspection produced non-JSON summary on stdout: {stdout!r}, "
            f"stderr: {result.stderr.strip()!r}"
        )
        raise CatalogueExtractionError(message) from exc
    summary = ExtractionSummary.model_validate(summary_data)

    hard_errors = [a for a in summary.anomalies if a.kind == "extraction_error"]
    if result.returncode != 0 and not hard_errors:
        message = (
            f"introspection exited {result.returncode} without reporting an "
            f"extraction_error anomaly: {result.stderr.strip()}"
        )
        raise CatalogueExtractionError(message)
    return summary


def extract_catalogue(
    *,
    detected: DetectedEnvironment,
    workroot: Path,
    output_root: Path,
    docker_bin_env: str | None = None,
    network: str = "none",
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 900,
    script_path: Path = _DEFAULT_SCRIPT_PATH,
) -> tuple[Path, ExtractionSummary]:
    """Extract every command schema, write it under `output_root/<digest>/`.

    Returns the digest-named output directory and the extraction summary.
    Raises `CatalogueExtractionError` on any hard failure: missing
    prerequisites, a failed container run, or a per-command extraction error
    reported by the introspection script (see docs/metadata.md, section 2).
    Commands that failed to extract are simply absent from the output
    directory: the extraction summary names them (`extraction_error`
    anomalies), not silently.
    """
    if not workroot.is_dir():
        message = f"work root does not exist or is not a directory: {workroot}"
        raise CatalogueExtractionError(message)
    if not script_path.is_file():
        message = f"introspection script not found: {script_path}"
        raise CatalogueExtractionError(message)

    docker_bin = find_docker_binary(docker_bin_env)

    work_dir = Path(tempfile.mkdtemp(prefix="aster-expert-catalogue-", dir=workroot))
    try:
        shutil.copy2(script_path, work_dir / _SCRIPT_NAME)
        (work_dir / _OUTPUT_SUBDIR).mkdir()

        summary = _run_introspection(
            detected=detected,
            work_dir=work_dir,
            docker_bin=docker_bin,
            network=network,
            memory=memory,
            cpus=cpus,
            timeout=timeout,
        )

        produced_dir = work_dir / _OUTPUT_SUBDIR
        schemas = [
            CommandSchema.model_validate(
                json.loads(json_path.read_text(encoding="utf-8"))
            )
            for json_path in sorted(produced_dir.glob("*.json"))
        ]

        digest_dir = output_root / detected.container.image_digest
        if digest_dir.exists():
            shutil.rmtree(digest_dir)
        digest_dir.mkdir(parents=True)
        for schema in schemas:
            (digest_dir / f"{schema.command}.json").write_text(
                json.dumps(json.loads(schema.model_dump_json()), indent=2) + "\n",
                encoding="utf-8",
            )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return digest_dir, summary
