"""Environment check, first command of every lot (lot 41 bis).

The upgrade of the VM from Ubuntu 24.04 to 26.04 removed the system Python 3.12
the project's `.venv` was built on: the venv silently switched to 3.14, could no
longer import its packages, and the MCP server stopped starting. Nothing in the
code had changed. This module checks, in order, everything the tool relies on
outside its own code, and stops at the first discrepancy:

1. the interpreter running the tool is the project's `.venv`, at the version of
   `.python-version`, built on a Python that is not the system's;
2. every distribution installed in the venv is the one `uv.lock` pins, and the
   project's direct requirements are installed and importable;
3. Docker answers without `sudo`; 4. `cave` is present and pinned;
5. the Code_Aster image resolved like `aster-expert run` does has the digest of
   `config/versions.yaml`; 6. the Salome runtime and image answer with the
   expected version; 7. the shared folder accepts a write;
8. the MCP server command of `.mcp.json` exists and its interpreter imports the
   server module.

Lot 41 ter: the checks run under a profile, `vm` or `cloud` (`detect_profile`).
In the cloud (a Claude Code cloud session, `CLAUDE_CODE_REMOTE=true`), `cave`,
Salome and the shared folder do not exist by design: their absence is reported
as expected, never as a failure. Every other check is the same in both profiles.

Lot 46 bis: a third profile, `ci` (GitHub Actions, `GITHUB_ACTIONS=true`). There
too `cave`, Salome, the shared folder and the MCP server are absent by design
(the image is pulled by digest and handed over as `ASTER_IMAGE_REF`; no `.mcp.json`
session). Without `cave` to fall back on, a missing `ASTER_IMAGE_REF` is a failure
of the `image` check, never a silent default.

Every external call goes through an injectable runner, so that the checks are
tested without Docker, Singularity or the shared folder.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from aster_expert.execution.config import load_execution_config
from aster_expert.execution.ressources import (
    MACHINE_CONFIG,
    MachineResources,
    machine_resources,
)

Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]
Which = Callable[[str], str | None]

PYTHON_VERSION_FILE = ".python-version"
LOCK_FILE = "uv.lock"
PROJECT_DISTRIBUTION = "aster-expert"
# Prefixes where a distribution's Python lives: an interpreter based there is the
# system's, the very dependency lot 41 bis removes.
SYSTEM_PREFIXES: tuple[Path, ...] = (Path("/usr"),)
_NORMALIZE = re.compile(r"[-_.]+")
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


Profile = Literal["vm", "cloud", "ci"]
PROFILES: tuple[Profile, ...] = ("vm", "cloud", "ci")
PROFILE_ENV = "ASTER_EXPERT_PROFIL"
CLOUD_MARKER_ENV = "CLAUDE_CODE_REMOTE"
CI_MARKER_ENV = "GITHUB_ACTIONS"
IMAGE_REF_ENV = "ASTER_IMAGE_REF"
# Checks whose resource is absent from a cloud session by design (lot 41 ter):
# no `cave` (the image is pulled by digest), no Salome image (a local file of
# several GB, on no registry), no VirtualBox shared folder.
EXPECTED_ABSENT_IN_CLOUD: frozenset[str] = frozenset({"cave", "salome", "partage"})
# Lot 46 bis: same absences in a GitHub Actions runner, plus the MCP server.
EXPECTED_ABSENT_IN_CI: frozenset[str] = frozenset({"cave", "salome", "partage", "mcp"})
EXPECTED_ABSENT: dict[Profile, frozenset[str]] = {
    "vm": frozenset(),
    "cloud": EXPECTED_ABSENT_IN_CLOUD,
    "ci": EXPECTED_ABSENT_IN_CI,
}


class EnvCheckError(Exception):
    """One environment check failed; the message is meant for the user."""


class CheckResult(BaseModel):
    """Outcome of one passed check.

    `expected_absent` marks a resource the profile does not provide (lot 41 ter):
    the check is passed, and `detail` says why the resource is missing.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    detail: str
    expected_absent: bool = False


def detect_profile(
    environ: Mapping[str, str] | None = None,
) -> tuple[Profile, str]:
    """(profile, reason): `ASTER_EXPERT_PROFIL` wins, else the platform markers.

    Claude Code sets `CLAUDE_CODE_REMOTE=true` in a cloud session and never
    locally (documentation « Configure cloud environments »); GitHub Actions
    sets `GITHUB_ACTIONS=true` in every workflow run (lot 46 bis).
    """
    env = os.environ if environ is None else environ
    forced = (env.get(PROFILE_ENV) or "").strip()
    if forced:
        for profile in PROFILES:
            if forced == profile:
                return profile, f"{PROFILE_ENV}={forced}"
        message = f"{PROFILE_ENV}={forced!r} : valeurs admises 'vm', 'cloud' ou 'ci'"
        raise EnvCheckError(message)
    if (env.get(CLOUD_MARKER_ENV) or "").strip().lower() == "true":
        return "cloud", f"{CLOUD_MARKER_ENV}=true"
    if (env.get(CI_MARKER_ENV) or "").strip().lower() == "true":
        return "ci", f"{CI_MARKER_ENV}=true"
    return "vm", f"{CLOUD_MARKER_ENV} non défini"


class InterpreterInfo(BaseModel):
    """What the running interpreter says about itself."""

    model_config = ConfigDict(frozen=True)

    version: tuple[int, int, int]
    prefix: Path
    base_prefix: Path

    @classmethod
    def current(cls) -> InterpreterInfo:
        info = sys.version_info
        return cls(
            version=(info.major, info.minor, info.micro),
            prefix=Path(sys.prefix),
            base_prefix=Path(sys.base_prefix),
        )


class EnvContext(BaseModel):
    """Everything the checks read; built from the real machine by `from_machine`."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    project_root: Path
    home: Path
    interpreter: InterpreterInfo
    installed: dict[str, str]
    direct_requirements: tuple[str, ...]
    image_ref_env: str | None = None
    profile: Profile = "vm"


def normalize_name(name: str) -> str:
    """PEP 503 normalized distribution name."""
    return _NORMALIZE.sub("-", name).lower()


def installed_distributions() -> dict[str, str]:
    """Normalized name -> version of every distribution of the running venv."""
    found: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            found[normalize_name(str(name))] = dist.version
    return found


def direct_requirement_names(requirements: Iterable[str]) -> tuple[str, ...]:
    """Normalized names of requirement strings, every extra included."""
    names: list[str] = []
    for requirement in requirements:
        match = _REQUIREMENT_NAME.match(requirement)
        if match is not None:
            names.append(normalize_name(match.group(1)))
    return tuple(sorted(set(names)))


def from_machine(project_root: Path) -> EnvContext:
    """Context of the running interpreter, its venv and the detected profile."""
    try:
        requires = importlib.metadata.requires(PROJECT_DISTRIBUTION) or []
    except importlib.metadata.PackageNotFoundError:
        requires = []
    return EnvContext(
        project_root=project_root,
        home=Path.home(),
        interpreter=InterpreterInfo.current(),
        installed=installed_distributions(),
        direct_requirements=direct_requirement_names(requires),
        image_ref_env=os.environ.get(IMAGE_REF_ENV),
        profile=detect_profile()[0],
    )


def default_runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv built from typed configuration, no shell
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def _run(
    runner: Runner, argv: list[str], timeout: int
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(argv, timeout)
    except subprocess.TimeoutExpired as exc:
        message = f"`{' '.join(argv)}` sans réponse après {timeout} s"
        raise EnvCheckError(message) from exc
    except OSError as exc:
        message = f"`{' '.join(argv)}` ne se lance pas : {exc}"
        raise EnvCheckError(message) from exc


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0] if lines else ""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


# --- 1. Python ---------------------------------------------------------------


def read_python_version_file(project_root: Path) -> tuple[int, ...]:
    path = project_root / PYTHON_VERSION_FILE
    if not path.is_file():
        message = f"{PYTHON_VERSION_FILE} absent de {project_root}"
        raise EnvCheckError(message)
    text = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+(\.\d+)?", text):
        message = f"{PYTHON_VERSION_FILE} illisible : {text!r} (attendu 3.12 ou 3.12.x)"
        raise EnvCheckError(message)
    return tuple(int(part) for part in text.split("."))


def check_python(ctx: EnvContext) -> CheckResult:
    expected = read_python_version_file(ctx.project_root)
    actual = ctx.interpreter.version
    shown = ".".join(str(part) for part in actual)
    if actual[: len(expected)] != expected:
        wanted = ".".join(str(part) for part in expected)
        message = (
            f"Python {shown} au lieu de {wanted} ({PYTHON_VERSION_FILE}) ; "
            "recréer le .venv : `uv sync --locked --all-extras`"
        )
        raise EnvCheckError(message)
    venv = (ctx.project_root / ".venv").resolve()
    prefix = ctx.interpreter.prefix.resolve()
    if prefix != venv:
        message = (
            f"l'interpréteur ({prefix}) n'est pas celui du .venv du projet ({venv}) ; "
            "lancer `.venv/bin/aster-expert`"
        )
        raise EnvCheckError(message)
    base = ctx.interpreter.base_prefix.resolve()
    for system in SYSTEM_PREFIXES:
        if _is_within(base, system):
            message = (
                f"le .venv repose sur le Python du système ({base}) ; il doit reposer "
                "sur un Python géré par uv : `uv sync --locked --all-extras`"
            )
            raise EnvCheckError(message)
    return CheckResult(name="python", detail=f"{shown}, .venv sur {base}")


# --- 2. Dependencies ---------------------------------------------------------


def read_lock_versions(project_root: Path) -> dict[str, str]:
    """Normalized name -> version of every package `uv.lock` pins (project excluded)."""
    path = project_root / LOCK_FILE
    if not path.is_file():
        message = f"{LOCK_FILE} absent de {project_root}"
        raise EnvCheckError(message)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        message = f"{LOCK_FILE} illisible : {exc}"
        raise EnvCheckError(message) from exc
    pins: dict[str, str] = {}
    for package in data.get("package", []):
        name = normalize_name(str(package.get("name", "")))
        version = package.get("version")
        if name and version is not None and name != PROJECT_DISTRIBUTION:
            pins[name] = str(version)
    return pins


def import_names(distribution: str) -> list[str]:
    """Importable top-level names a distribution provides."""
    names: list[str] = []
    for module, dists in importlib.metadata.packages_distributions().items():
        if any(normalize_name(d) == distribution for d in dists) and (
            module.isidentifier() and not module.startswith("_")
        ):
            names.append(module)
    return sorted(names)


def check_dependencies(
    ctx: EnvContext,
    *,
    importer: Callable[[str], object] = importlib.import_module,
    names_of: Callable[[str], list[str]] = import_names,
) -> CheckResult:
    pins = read_lock_versions(ctx.project_root)
    if PROJECT_DISTRIBUTION not in ctx.installed:
        message = (
            f"le paquet {PROJECT_DISTRIBUTION} n'est pas installé dans le .venv : "
            "`uv sync --locked --all-extras`"
        )
        raise EnvCheckError(message)
    for name in ctx.direct_requirements:
        if name not in ctx.installed:
            message = (
                f"dépendance {name} absente du .venv : `uv sync --locked --all-extras`"
            )
            raise EnvCheckError(message)
    for name, version in sorted(ctx.installed.items()):
        if name == PROJECT_DISTRIBUTION:
            continue
        pinned = pins.get(name)
        if pinned is None:
            message = f"{name} {version} installé mais absent de {LOCK_FILE}"
            raise EnvCheckError(message)
        if pinned != version:
            message = f"{name} {version} installé, {pinned} verrouillé dans {LOCK_FILE}"
            raise EnvCheckError(message)
    imported = 0
    for name in ctx.direct_requirements:
        for module in names_of(name):
            try:
                importer(module)
            except Exception as exc:  # any import failure is the finding
                message = (
                    f"`import {module}` ({name}) échoue : {type(exc).__name__}: {exc}"
                )
                raise EnvCheckError(message) from exc
            imported += 1
    return CheckResult(
        name="dependances",
        detail=(
            f"{len(ctx.installed) - 1} distributions conformes à {LOCK_FILE}, "
            f"{len(ctx.direct_requirements)} dépendances directes, "
            f"{imported} modules importés"
        ),
    )


# --- 3. Docker, 4. cave, 5. image -----------------------------------------------


def _docker_bin(which: Which) -> str:
    found = which("docker")
    if found is None:
        message = "docker introuvable dans le PATH"
        raise EnvCheckError(message)
    return found


def check_docker(ctx: EnvContext, runner: Runner, which: Which) -> CheckResult:
    del ctx
    docker = _docker_bin(which)
    result = _run(runner, [docker, "version", "--format", "{{.Server.Version}}"], 30)
    if result.returncode != 0:
        message = (
            "le démon Docker ne répond pas à l'utilisateur "
            f"({_first_line(result.stderr)}) ; "
            "service `docker` actif et utilisateur dans le groupe `docker` ? "
            "(correction système : à faire par MM, jamais par la session)"
        )
        raise EnvCheckError(message)
    return CheckResult(
        name="docker", detail=f"démon {result.stdout.strip()}, sans sudo"
    )


def check_cave(ctx: EnvContext, runner: Runner, which: Which) -> CheckResult:
    from aster_expert.execution.docker_client import read_cave_pin

    found = which("cave")
    if found is None:
        message = "cave introuvable dans le PATH"
        raise EnvCheckError(message)
    result = _run(runner, [found, "--version"], 30)
    if result.returncode != 0:
        message = f"`cave --version` échoue : {_first_line(result.stderr)}"
        raise EnvCheckError(message)
    pin, source = read_cave_pin(ctx.project_root, ctx.home)
    if pin is None:
        message = "aucune version épinglée par cave (`cave use <version>`)"
        raise EnvCheckError(message)
    return CheckResult(
        name="cave", detail=f"{result.stdout.strip()}, version {pin} ({source})"
    )


def read_expected_image(project_root: Path) -> tuple[str, str]:
    """(repository, digest) of the last detected environment, `config/versions.yaml`."""
    path = project_root / "config" / "versions.yaml"
    if not path.is_file():
        message = f"{path} absent"
        raise EnvCheckError(message)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    container = ((data.get("detected") or {}).get("container")) or {}
    repository = container.get("image_repository")
    digest = container.get("image_digest")
    if not repository or not digest:
        message = f"{path} : `detected.container` sans dépôt ni digest d'image"
        raise EnvCheckError(message)
    return str(repository), str(digest)


def check_image(ctx: EnvContext, runner: Runner, which: Which) -> CheckResult:
    del runner
    from aster_expert.execution.docker_client import resolve_image
    from aster_expert.execution.errors import EnvironmentDetectionError

    repository, expected = read_expected_image(ctx.project_root)
    if ctx.profile == "ci" and not (ctx.image_ref_env or "").strip():
        message = (
            f"{IMAGE_REF_ENV} non défini : sans `cave`, le profil ci n'a aucune autre "
            "source de la référence de l'image ; le workflow la construit depuis "
            "config/versions.yaml (digest), jamais recopiée en dur"
        )
        raise EnvCheckError(message)
    try:
        resolved = resolve_image(
            docker_bin=Path(_docker_bin(which)),
            repository=repository,
            image_ref_env=ctx.image_ref_env,
            cwd=ctx.project_root,
            home=ctx.home,
        )
    except EnvironmentDetectionError as exc:
        raise EnvCheckError(str(exc)) from exc
    if resolved.digest != expected:
        message = (
            f"image {repository}:{resolved.tag} de digest {resolved.digest}, "
            f"config/versions.yaml attend {expected}"
        )
        raise EnvCheckError(message)
    return CheckResult(
        name="image", detail=f"{repository}:{resolved.tag} {resolved.digest}"
    )


# --- 6. Salome -----------------------------------------------------------------


def check_salome(ctx: EnvContext, runner: Runner, which: Which) -> CheckResult:
    from aster_expert.meshing.config import load_mesh_config
    from aster_expert.meshing.errors import MeshConfigError, MeshRunError
    from aster_expert.meshing.run import read_salome_version

    try:
        config = load_mesh_config(ctx.project_root / "config" / "validation.yaml")
    except MeshConfigError as exc:
        raise EnvCheckError(str(exc)) from exc
    salome = config.salome
    runtime = which(salome.runtime)
    if runtime is None:
        message = f"{salome.runtime} introuvable dans le PATH (mesh.salome.runtime)"
        raise EnvCheckError(message)
    result = _run(runner, [runtime, "--version"], 30)
    if result.returncode != 0:
        message = f"`{salome.runtime} --version` échoue : {_first_line(result.stderr)}"
        raise EnvCheckError(message)
    image = Path(salome.image_path).expanduser()
    if not image.is_file():
        message = f"image Salomé absente : {image} (mesh.salome.image_path)"
        raise EnvCheckError(message)
    try:
        version = read_salome_version(config, image, runner)
    except MeshRunError as exc:
        raise EnvCheckError(str(exc)) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"l'image Salomé ne se lance pas : {exc}"
        raise EnvCheckError(message) from exc
    if version != salome.expected_version:
        message = (
            f"Salomé {version} dans l'image, {salome.expected_version} attendu "
            "(mesh.salome.expected_version)"
        )
        raise EnvCheckError(message)
    return CheckResult(
        name="salome", detail=f"{result.stdout.strip()}, image {image.name} {version}"
    )


# --- 7. Shared folder ----------------------------------------------------------


def read_shared_folder(project_root: Path) -> Path:
    path = project_root / "config" / "validation.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    raw = ((data or {}).get("environnement") or {}).get("partage")
    if not raw:
        message = f"{path} : `environnement.partage` non renseigné"
        raise EnvCheckError(message)
    return Path(str(raw)).expanduser()


def check_shared_folder(ctx: EnvContext) -> CheckResult:
    folder = read_shared_folder(ctx.project_root)
    if not folder.is_dir():
        message = (
            f"dossier partagé absent ou non monté : {folder} "
            "(montage VirtualBox : à rétablir par MM, jamais par la session)"
        )
        raise EnvCheckError(message)
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".env-check-") as probe:
            probe.write(b"env-check\n")
            probe.flush()
    except OSError as exc:
        message = f"écriture impossible dans {folder} : {exc}"
        raise EnvCheckError(message) from exc
    return CheckResult(name="partage", detail=f"{folder}, écriture possible")


# --- 9. Free disk space (lot 47 ter, ENV-003) ------------------------------------

MIN_FREE_GB: dict[Profile, float] = {"vm": 10.0, "cloud": 2.0, "ci": 2.0}
"""Free space required under the repository (Go). Lot 47 ter: a full disk of the VM
stopped two runs and left their reports empty (ENV-003); a run of the jetty writes
about 2 Go and each reading of its MED of results needed 4 Go more."""

DiskUsage = Callable[[Path], tuple[int, int, int]]


def check_disk(ctx: EnvContext, usage: DiskUsage = shutil.disk_usage) -> CheckResult:
    total, _used, free = usage(ctx.project_root)
    free_gb = free / 1e9
    floor = MIN_FREE_GB[ctx.profile]
    detail = f"{free_gb:.1f} Go libres sur {total / 1e9:.0f} Go (minimum {floor:g} Go)"
    if free_gb < floor:
        message = (
            f"espace disque insuffisant : {detail} sous {ctx.project_root} ; "
            "libérer de l'espace avant toute exécution (ENV-003)"
        )
        raise EnvCheckError(message)
    return CheckResult(name="disque", detail=detail)


# --- 10. Resources of the machine (lot 47 quater, DIAG-025) ------------------------


def check_resources(
    ctx: EnvContext,
    machine: Callable[[], MachineResources] | None = None,
) -> CheckResult:
    """Processors and memory given to Code_Aster, and the execution defaults.

    Informative: it fails only when the machine or the configuration cannot be read.
    `aster-expert run` refuses later a run whose `.export` asks for more.
    """
    found = (machine or machine_resources)()
    config = load_execution_config(ctx.project_root / "config" / "validation.yaml")
    settings = config.resource_settings(ctx.project_root)
    local = (ctx.project_root / MACHINE_CONFIG).is_file()
    detail = (
        f"{found.cpus} processeurs, {found.memory_total_mb / 1024:.1f} Go de mémoire "
        f"({found.memory_available_mb / 1024:.1f} Go disponibles) ; "
        f"défauts d'un .export de projet : ncpus {settings.ncpus}, "
        f"mpi_nbcpu {settings.mpi_processes} ; seuil disque avant exécution "
        f"{settings.min_free_disk_gb:g} Go ; "
        + (f"{MACHINE_CONFIG} lu" if local else f"{MACHINE_CONFIG} absent")
    )
    if settings.ncpus * settings.mpi_processes > found.cpus:
        message = (
            f"{detail} : ncpus × mpi_nbcpu par défaut dépasse les processeurs de la "
            "machine"
        )
        raise EnvCheckError(message)
    return CheckResult(name="ressources", detail=detail)


# --- 8. MCP server -------------------------------------------------------------


_SERVER_IMPORT = "import sys, aster_expert.mcp.server; print(sys.prefix)"


def _check_venv_prefix(ctx: EnvContext, prefix: str, how: str) -> None:
    venv = (ctx.project_root / ".venv").resolve()
    if Path(prefix).resolve() != venv:
        message = (
            f"le serveur MCP s'exécute ({how}) avec le Python de {prefix}, pas avec "
            f"le Python du .venv ({venv})"
        )
        raise EnvCheckError(message)


def _import_failure(result: subprocess.CompletedProcess[str]) -> EnvCheckError:
    lines = result.stderr.strip().splitlines()
    message = (
        f"l'interpréteur du serveur MCP n'importe pas aster_expert.mcp.server : "
        f"{lines[-1] if lines else result.returncode}"
    )
    return EnvCheckError(message)


def check_mcp_server(ctx: EnvContext, runner: Runner) -> CheckResult:
    """The command of `.mcp.json` runs the server with the project's `.venv`.

    Two launch forms (lot 41 ter): `uv run --project <dir> ... aster-expert-mcp`,
    portable between the VM and the cloud, checked by running the same `uv run`
    on `python -c "import aster_expert.mcp.server"`; or an executable script whose
    `#!` line names the interpreter (form used up to lot 41 bis).
    """
    from aster_expert.mcp.check import (
        McpCheckError,
        ensure_command_executable,
        load_server_spec,
        uv_project_args,
    )

    try:
        spec = load_server_spec(ctx.project_root)
        command = ensure_command_executable(spec, ctx.project_root)
    except McpCheckError as exc:
        raise EnvCheckError(str(exc)) from exc
    if command.name == "uv":
        try:
            prefix_args = uv_project_args(spec, ctx.project_root)
        except McpCheckError as exc:
            raise EnvCheckError(str(exc)) from exc
        argv = [str(command), *prefix_args, "python", "-c", _SERVER_IMPORT]
        result = _run(runner, argv, 300)
        if result.returncode != 0:
            raise _import_failure(result)
        prefix = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        _check_venv_prefix(ctx, prefix, "uv run")
        return CheckResult(
            name="mcp",
            detail=f"{command} {' '.join(spec.args)}, module serveur importable",
        )
    with command.open("rb") as handle:
        first = handle.readline().decode("utf-8", errors="replace").strip()
    if not first.startswith("#!"):
        message = f"{command} n'a pas de ligne d'interpréteur (#!)"
        raise EnvCheckError(message)
    interpreter = Path(first[2:].strip().split()[0])
    venv_python = ctx.project_root / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        message = f"interpréteur du serveur MCP introuvable : {interpreter}"
        raise EnvCheckError(message)
    if interpreter.resolve() != venv_python.resolve():
        message = (
            f"le serveur MCP s'exécute avec {interpreter}, pas avec le Python du "
            f".venv ({venv_python})"
        )
        raise EnvCheckError(message)
    result = _run(
        runner, [str(interpreter), "-c", "import aster_expert.mcp.server"], 120
    )
    if result.returncode != 0:
        raise _import_failure(result)
    return CheckResult(name="mcp", detail=f"{command}, module serveur importable")


# --- Sequence --------------------------------------------------------------------

CHECK_NAMES: tuple[str, ...] = (
    "python",
    "dependances",
    "docker",
    "cave",
    "image",
    "salome",
    "partage",
    "disque",
    "ressources",
    "mcp",
)


def run_checks(
    ctx: EnvContext,
    *,
    runner: Runner = default_runner,
    which: Which = shutil.which,
    importer: Callable[[str], object] = importlib.import_module,
    names_of: Callable[[str], list[str]] = import_names,
    on_result: Callable[[CheckResult], None] | None = None,
    disk_usage: DiskUsage = shutil.disk_usage,
    machine: Callable[[], MachineResources] | None = None,
) -> list[CheckResult]:
    """Run every check in order; raise `EnvCheckError` naming the first failure.

    The raised error's message starts with the failing check's name. In the
    `cloud` and `ci` profiles, a failure of a check of `EXPECTED_ABSENT[profile]` is an
    expected absence (`CheckResult.expected_absent`), not a failure.
    """
    steps: dict[str, Callable[[], CheckResult]] = {
        "python": lambda: check_python(ctx),
        "dependances": lambda: check_dependencies(
            ctx, importer=importer, names_of=names_of
        ),
        "docker": lambda: check_docker(ctx, runner, which),
        "cave": lambda: check_cave(ctx, runner, which),
        "image": lambda: check_image(ctx, runner, which),
        "salome": lambda: check_salome(ctx, runner, which),
        "partage": lambda: check_shared_folder(ctx),
        "disque": lambda: check_disk(ctx, disk_usage),
        "ressources": lambda: check_resources(ctx, machine),
        "mcp": lambda: check_mcp_server(ctx, runner),
    }
    results: list[CheckResult] = []
    for name in CHECK_NAMES:
        try:
            result = steps[name]()
        except EnvCheckError as exc:
            if name in EXPECTED_ABSENT[ctx.profile]:
                result = CheckResult(
                    name=name,
                    detail=f"absent, attendu en profil {ctx.profile} ({exc})",
                    expected_absent=True,
                )
                results.append(result)
                if on_result is not None:
                    on_result(result)
                continue
            raise EnvCheckError(f"{name} : {exc}") from exc
        except Exception as exc:  # no Python traceback for the user
            message = f"{name} : erreur inattendue {type(exc).__name__}: {exc}"
            raise EnvCheckError(message) from exc
        results.append(result)
        if on_result is not None:
            on_result(result)
    return results
