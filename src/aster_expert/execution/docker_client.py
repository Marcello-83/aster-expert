"""Thin wrapper around the `docker` CLI.

`aster_expert` never calls `cave run`: `cave` has no subcommand equivalent to
`docker exec` (its only execution subcommand is `cave run -- <file.export>`).
Instead, `docker run` is invoked directly, reproducing the mount pattern
observed from `cave` but restricted to a dedicated directory. See
docs/architecture.md, ADR-002, ADR-003, ADR-006.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import FORBIDDEN_IMAGE_TAGS, ResolvedImage


def find_docker_binary(explicit: str | None = None) -> Path:
    """Locate the `docker` binary. Never assumes a default path silently."""
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_file():
            message = f"ASTER_DOCKER_BIN={explicit!r} does not exist"
            raise EnvironmentDetectionError(message)
        return candidate
    found = shutil.which("docker")
    if found is None:
        message = "docker binary not found in PATH; set ASTER_DOCKER_BIN"
        raise EnvironmentDetectionError(message)
    return Path(found)


def docker_version_raw(docker_bin: Path, *, timeout: int = 30) -> str:
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [str(docker_bin), "--version"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        message = f"'{docker_bin} --version' failed: {result.stderr.strip()}"
        raise EnvironmentDetectionError(message)
    return result.stdout.strip()


def read_cave_pin(directory: Path, home: Path) -> tuple[str | None, str]:
    """Read a `cave` version pin: directory-local `.cave` first, else global.

    Returns (pin_value, source) with source in {"directory", "global", "none"}.
    """
    local = directory / ".cave"
    if local.is_file():
        value = local.read_text(encoding="utf-8").strip()
        if value:
            return value, "directory"
    global_pin = home / ".cave"
    if global_pin.is_file():
        value = global_pin.read_text(encoding="utf-8").strip()
        if value:
            return value, "global"
    return None, "none"


def _pick_concrete_tag(repo_tags: list[str], repository: str) -> str:
    """Return a non-symbolic tag for `repository` among `RepoTags`, if any."""
    prefix = f"{repository}:"
    for repo_tag in repo_tags:
        if not repo_tag.startswith(prefix):
            continue
        candidate_tag = repo_tag[len(prefix) :]
        if candidate_tag.lower() not in FORBIDDEN_IMAGE_TAGS:
            return candidate_tag
    return ""


def resolve_image(
    *,
    docker_bin: Path,
    repository: str,
    image_ref_env: str | None,
    cwd: Path,
    home: Path,
    timeout: int = 30,
) -> ResolvedImage:
    """Resolve the image to use, by digest, never by the "stable" tag.

    Order: an explicit `ASTER_IMAGE_REF` wins; otherwise a `cave` pin
    (directory-local, then global) is used. A symbolic tag ("stable",
    "testing") is refused outright, from either source.
    """
    if image_ref_env:
        candidate = image_ref_env.strip()
        source = "none"
    else:
        pin_value, source = read_cave_pin(cwd, home)
        if pin_value is None:
            message = (
                "no image reference found: set ASTER_IMAGE_REF, or pin a "
                "version with `cave pin <version>` / `cave use <version>`"
            )
            raise EnvironmentDetectionError(message)
        candidate = pin_value

    if candidate.lower() in FORBIDDEN_IMAGE_TAGS:
        message = (
            f"'{candidate}' is a symbolic tag, forbidden as a resolved version "
            "(docs/architecture.md, ADR-002): it is mobile on the registry and "
            "has been observed to diverge from the local image of the same "
            "name. Pin a concrete version, e.g. `cave pin 17.4.0`, or set "
            "ASTER_IMAGE_REF explicitly."
        )
        raise EnvironmentDetectionError(message)

    if candidate.startswith("sha256:"):
        full_ref = f"{repository}@{candidate}"
    else:
        full_ref = f"{repository}:{candidate}"

    inspect = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [str(docker_bin), "inspect", full_ref, "--format", "{{json .}}"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if inspect.returncode != 0:
        message = f"'docker inspect {full_ref}' failed: {inspect.stderr.strip()}"
        raise EnvironmentDetectionError(message)
    data = json.loads(inspect.stdout)

    repo_digests: list[str] = data.get("RepoDigests") or []
    digest_prefix = f"{repository}@"
    digest = next(
        (d[len(digest_prefix) :] for d in repo_digests if d.startswith(digest_prefix)),
        None,
    )
    if digest is None:
        message = (
            f"image '{full_ref}' has no RepoDigests for repository "
            f"'{repository}': it was built locally or never pulled from a "
            "registry. Refusing to guess a version identity."
        )
        raise EnvironmentDetectionError(message)

    image_id = data.get("Id")
    if not image_id:
        message = f"'docker inspect {full_ref}' returned no Id"
        raise EnvironmentDetectionError(message)

    if candidate.startswith("sha256:"):
        tag = _pick_concrete_tag(data.get("RepoTags") or [], repository)
    else:
        tag = candidate

    return ResolvedImage(
        repository=repository,
        tag=tag,
        digest=digest,
        image_id=image_id,
        cave_pin_source=source,
    )


def run_in_container(
    *,
    docker_bin: Path,
    image_ref: str,
    workdir: Path,
    command: str,
    mount_target: str = "/work",
    network: str = "none",
    drop_to_host_user: bool = True,
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 300,
    container_name: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `command` (a shell string) inside the image, mount restricted.

    `workdir` must be a dedicated, already-existing directory. Never $HOME,
    never a repository root: that guarantee is the caller's responsibility
    (a freshly created temporary directory satisfies it by construction). See
    docs/architecture.md, ADR-006.

    `container_name` (docs/development-plan.md, lot 11) gives the container a
    known name so a caller whose own `timeout` fires can `kill_container` it
    explicitly afterward: killing the local `docker run` client process on a
    `subprocess.TimeoutExpired` does not, by itself, stop the container it
    started (ADR-006: "le délai maximal... pour couvrir aussi un conteneur
    qui ne se terminerait pas" -- a client-side kill alone does not satisfy
    that).
    """
    resolved = workdir.resolve()
    if resolved == Path.home().resolve():
        message = "refusing to mount $HOME into the container"
        raise EnvironmentDetectionError(message)
    if not resolved.is_dir():
        message = f"mount directory does not exist: {resolved}"
        raise EnvironmentDetectionError(message)

    argv = [str(docker_bin), "run", "--rm", f"--network={network}"]
    if drop_to_host_user:
        argv += ["--user", f"{os.getuid()}:{os.getgid()}"]
    if memory:
        argv += [f"--memory={memory}"]
    if cpus:
        argv += [f"--cpus={cpus}"]
    if container_name:
        argv += ["--name", container_name]
    argv += ["-v", f"{resolved}:{mount_target}", "-w", mount_target]
    argv += [image_ref, "/bin/bash", "-c", command]

    return subprocess.run(  # noqa: S603 - argv built from typed fields, no shell
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def kill_container(docker_bin: Path, container_name: str, *, timeout: int = 30) -> None:
    """Best-effort `docker kill` + `docker rm -f`, never raises.

    Used only after this project's own outer timeout fires on a `docker run`
    invocation (docs/development-plan.md, lot 11, O2): the local client
    process is already gone by then, but the container it started may still
    be running server-side. A failure here (container already gone, docker
    daemon unreachable) is swallowed -- there is nothing more this project
    can do about it, and the caller has already decided to report a timeout
    regardless of whether this cleanup succeeds.
    """
    for args in (["kill", container_name], ["rm", "-f", container_name]):
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(  # noqa: S603 - fixed argv, no shell
                [str(docker_bin), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
