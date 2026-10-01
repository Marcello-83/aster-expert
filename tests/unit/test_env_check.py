"""Tests for `aster_expert.environnement.verification` (lot 41 bis).

No Docker, no Singularity, no shared folder: every external call goes through a
fake runner and a fake `which`; files live in a temporary directory.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aster_expert import cli
from aster_expert.environnement import verification as v
from aster_expert.environnement.verification import (
    CHECK_NAMES,
    CheckResult,
    EnvCheckError,
    EnvContext,
    InterpreterInfo,
)
from aster_expert.execution.models import ResolvedImage

_REPO = Path(__file__).resolve().parents[2]
_DIGEST = "sha256:" + "a" * 64
_LOCK = """
version = 1
requires-python = ">=3.12"

[[package]]
name = "aster-expert"
version = "0.1.0"

[[package]]
name = "PyYAML"
version = "6.0.3"

[[package]]
name = "typer"
version = "0.27.2"
"""
_MESH = """
mesh:
  work_dir_root: data/processed/mesh_runs
  salome:
    runtime: singularity
    image_path: {image}
    expected_version: V2024.1.0_scibian_univ
    install_root: /opt/salome
    version_file: README
    version_pattern: 'Version\\s*:\\s*(\\S+)'
    env_scripts: []
    container_options: [--containall]
    command: "salome -t {{script}} args:{{args}}"
    timeout_seconds: 10
  checker:
    work_dir_root: data/processed/mesh_checks
    timeout_seconds: 10
    memory_mb: 512
    cpus_limit: "1"
environnement:
  partage: {share}
"""


def _completed(
    argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


def _project(tmp_path: Path, *, share: Path | None = None) -> Path:
    root = tmp_path / "depot"
    (root / ".venv").mkdir(parents=True)
    (root / "config").mkdir()
    (root / ".python-version").write_text("3.12\n", encoding="utf-8")
    (root / "uv.lock").write_text(_LOCK, encoding="utf-8")
    image = tmp_path / "salome.sif"
    image.write_bytes(b"sif")
    shared = share if share is not None else tmp_path / "partage"
    shared.mkdir(exist_ok=True)
    (root / "config" / "validation.yaml").write_text(
        _MESH.format(image=image, share=shared), encoding="utf-8"
    )
    (root / "config" / "versions.yaml").write_text(
        "detected:\n  container:\n    image_repository: simvia/code_aster\n"
        f"    image_digest: {_DIGEST}\n",
        encoding="utf-8",
    )
    return root


def _ctx(root: Path, **changes: object) -> EnvContext:
    values: dict[str, object] = {
        "project_root": root,
        "home": root.parent,
        "interpreter": InterpreterInfo(
            version=(3, 12, 14),
            prefix=root / ".venv",
            base_prefix=Path("/home/u/.local/share/uv/python/cpython-3.12"),
        ),
        "installed": {"aster-expert": "0.1.0", "pyyaml": "6.0.3", "typer": "0.27.2"},
        "direct_requirements": ("pyyaml", "typer"),
    }
    values.update(changes)
    return EnvContext.model_validate(values)


# --- Python ---------------------------------------------------------------------


def test_python_accepts_the_pinned_version_in_the_project_venv(tmp_path: Path) -> None:
    result = v.check_python(_ctx(_project(tmp_path)))
    assert result.name == "python"
    assert result.detail.startswith("3.12.14")


def test_python_refuses_another_version(tmp_path: Path) -> None:
    root = _project(tmp_path)
    interpreter = InterpreterInfo(
        version=(3, 14, 4), prefix=root / ".venv", base_prefix=Path("/opt/x")
    )
    with pytest.raises(EnvCheckError, match=r"Python 3\.14\.4 au lieu de 3\.12"):
        v.check_python(_ctx(root, interpreter=interpreter))


def test_python_refuses_an_interpreter_outside_the_venv(tmp_path: Path) -> None:
    root = _project(tmp_path)
    interpreter = InterpreterInfo(
        version=(3, 12, 14), prefix=tmp_path / "ailleurs", base_prefix=Path("/opt/x")
    )
    with pytest.raises(EnvCheckError, match="n'est pas celui du .venv"):
        v.check_python(_ctx(root, interpreter=interpreter))


def test_python_refuses_a_venv_built_on_the_system_python(tmp_path: Path) -> None:
    root = _project(tmp_path)
    interpreter = InterpreterInfo(
        version=(3, 12, 3), prefix=root / ".venv", base_prefix=Path("/usr")
    )
    with pytest.raises(EnvCheckError, match="Python du système"):
        v.check_python(_ctx(root, interpreter=interpreter))


def test_python_requires_a_readable_version_file(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / ".python-version").unlink()
    with pytest.raises(EnvCheckError, match="absent"):
        v.check_python(_ctx(root))
    (root / ".python-version").write_text("cpython@3.12\n", encoding="utf-8")
    with pytest.raises(EnvCheckError, match="illisible"):
        v.check_python(_ctx(root))


def test_python_with_a_patch_level_pin_compares_the_patch(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / ".python-version").write_text("3.12.13\n", encoding="utf-8")
    with pytest.raises(EnvCheckError, match="au lieu de 3.12.13"):
        v.check_python(_ctx(root))


# --- Dependencies ------------------------------------------------------------------


def _names(dist: str) -> list[str]:
    return {"pyyaml": ["yaml"], "typer": ["typer"]}[dist]


def test_dependencies_match_the_lock_and_import(tmp_path: Path) -> None:
    imported: list[str] = []

    def importer(name: str) -> object:
        imported.append(name)
        return object()

    result = v.check_dependencies(
        _ctx(_project(tmp_path)), importer=importer, names_of=_names
    )
    assert imported == ["yaml", "typer"]
    assert "2 distributions conformes" in result.detail


def test_dependencies_refuse_a_version_other_than_the_lock(tmp_path: Path) -> None:
    ctx = _ctx(
        _project(tmp_path),
        installed={"aster-expert": "0.1.0", "pyyaml": "6.0.2", "typer": "0.27.2"},
    )
    with pytest.raises(EnvCheckError, match="pyyaml 6.0.2 installé, 6.0.3 verrouillé"):
        v.check_dependencies(ctx, importer=lambda _: None, names_of=_names)


def test_dependencies_refuse_a_package_absent_from_the_lock(tmp_path: Path) -> None:
    ctx = _ctx(
        _project(tmp_path),
        installed={
            "aster-expert": "0.1.0",
            "pyyaml": "6.0.3",
            "typer": "0.27.2",
            "pip": "24.0",
        },
    )
    with pytest.raises(EnvCheckError, match="pip 24.0 installé mais absent"):
        v.check_dependencies(ctx, importer=lambda _: None, names_of=_names)


def test_dependencies_refuse_a_missing_direct_requirement(tmp_path: Path) -> None:
    ctx = _ctx(
        _project(tmp_path), installed={"aster-expert": "0.1.0", "typer": "0.27.2"}
    )
    with pytest.raises(EnvCheckError, match="dépendance pyyaml absente"):
        v.check_dependencies(ctx, importer=lambda _: None, names_of=_names)


def test_dependencies_refuse_an_uninstalled_project(tmp_path: Path) -> None:
    ctx = _ctx(_project(tmp_path), installed={"pyyaml": "6.0.3", "typer": "0.27.2"})
    with pytest.raises(EnvCheckError, match="aster-expert n'est pas installé"):
        v.check_dependencies(ctx, importer=lambda _: None, names_of=_names)


def test_dependencies_report_an_import_failure(tmp_path: Path) -> None:
    def importer(name: str) -> object:
        if name == "typer":
            raise ModuleNotFoundError("No module named 'typer'")
        return object()

    with pytest.raises(EnvCheckError, match="`import typer` .* ModuleNotFoundError"):
        v.check_dependencies(
            _ctx(_project(tmp_path)), importer=importer, names_of=_names
        )


def test_dependencies_require_the_lock_file(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "uv.lock").unlink()
    with pytest.raises(EnvCheckError, match="uv.lock absent"):
        v.check_dependencies(_ctx(root), importer=lambda _: None, names_of=_names)


def test_direct_requirement_names_keep_every_extra() -> None:
    names = v.direct_requirement_names(
        ["typer>=0.12", "mcp<3,>=2.0; extra == 'mcp'", "PyYAML>=6.0", "types-PyYAML"]
    )
    assert names == ("mcp", "pyyaml", "typer", "types-pyyaml")


# --- Docker, cave, image -------------------------------------------------------------


def _which(found: dict[str, str]) -> v.Which:
    return lambda name: found.get(name)


def test_docker_reports_an_unreachable_daemon(tmp_path: Path) -> None:
    def runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return _completed(argv, 1, stderr="permission denied while trying to connect")

    with pytest.raises(EnvCheckError, match="groupe `docker`"):
        v.check_docker(_ctx(_project(tmp_path)), runner, _which({"docker": "/bin/d"}))


def test_docker_missing_and_present(tmp_path: Path) -> None:
    ctx = _ctx(_project(tmp_path))
    with pytest.raises(EnvCheckError, match="docker introuvable"):
        v.check_docker(ctx, lambda a, t: _completed(a), _which({}))
    result = v.check_docker(
        ctx, lambda a, t: _completed(a, stdout="29.1.3\n"), _which({"docker": "/bin/d"})
    )
    assert result.detail == "démon 29.1.3, sans sudo"


def test_cave_requires_a_pin(tmp_path: Path) -> None:
    root = _project(tmp_path)
    ctx = _ctx(root)
    runner = lambda a, t: _completed(a, stdout="cave 0.1.4\n")  # noqa: E731
    with pytest.raises(EnvCheckError, match="aucune version épinglée"):
        v.check_cave(ctx, runner, _which({"cave": "/bin/cave"}))
    (root.parent / ".cave").write_text("17.4.0\n", encoding="utf-8")
    result = v.check_cave(ctx, runner, _which({"cave": "/bin/cave"}))
    assert result.detail == "cave 0.1.4, version 17.4.0 (global)"


def test_image_compares_the_resolved_digest_to_the_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aster_expert.execution import docker_client

    resolved = {"digest": _DIGEST}

    def fake_resolve(**kwargs: object) -> ResolvedImage:
        return ResolvedImage(
            repository=str(kwargs["repository"]),
            tag="17.4.0",
            digest=resolved["digest"],
            image_id="sha256:id",
            cave_pin_source="global",
        )

    monkeypatch.setattr(docker_client, "resolve_image", fake_resolve)
    ctx = _ctx(_project(tmp_path))
    which = _which({"docker": "/bin/d"})
    assert v.check_image(ctx, lambda a, t: _completed(a), which).detail.endswith(
        _DIGEST
    )
    resolved["digest"] = "sha256:" + "b" * 64
    with pytest.raises(EnvCheckError, match="config/versions.yaml attend"):
        v.check_image(ctx, lambda a, t: _completed(a), which)


# --- Salome --------------------------------------------------------------------------


def _salome_runner(version: str) -> v.Runner:
    def runner(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        if argv[-1] == "--version":
            return _completed(argv, stdout="singularity-ce version 4.3.7\n")
        return _completed(argv, stdout=f"Version        : {version}\n")

    return runner


def test_salome_reads_the_version_inside_the_image(tmp_path: Path) -> None:
    ctx = _ctx(_project(tmp_path))
    which = _which({"singularity": "/bin/singularity"})
    result = v.check_salome(ctx, _salome_runner("V2024.1.0_scibian_univ"), which)
    assert "V2024.1.0_scibian_univ" in result.detail
    with pytest.raises(EnvCheckError, match="V2025 dans l'image"):
        v.check_salome(ctx, _salome_runner("V2025"), which)


def test_salome_missing_runtime_or_image(tmp_path: Path) -> None:
    root = _project(tmp_path)
    ctx = _ctx(root)
    runner = _salome_runner("V2024.1.0_scibian_univ")
    with pytest.raises(EnvCheckError, match="singularity introuvable"):
        v.check_salome(ctx, runner, _which({}))
    (tmp_path / "salome.sif").unlink()
    with pytest.raises(EnvCheckError, match="image Salomé absente"):
        v.check_salome(ctx, runner, _which({"singularity": "/bin/s"}))


# --- Shared folder -------------------------------------------------------------------


def test_shared_folder_is_written_then_left_clean(tmp_path: Path) -> None:
    ctx = _ctx(_project(tmp_path))
    assert v.check_shared_folder(ctx).detail.endswith("écriture possible")
    assert list((tmp_path / "partage").iterdir()) == []


def test_shared_folder_absent(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (tmp_path / "partage").rmdir()
    with pytest.raises(EnvCheckError, match="absent ou non monté"):
        v.check_shared_folder(_ctx(root))


def test_shared_folder_must_be_configured(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "config" / "validation.yaml").write_text("mesh: {}\n", encoding="utf-8")
    with pytest.raises(EnvCheckError, match="environnement.partage"):
        v.check_shared_folder(_ctx(root))


# --- MCP server --------------------------------------------------------------------


def _mcp_project(tmp_path: Path, interpreter: Path | None = None) -> Path:
    root = _project(tmp_path)
    (root / ".venv" / "bin").mkdir()
    venv_python = root / ".venv" / "bin" / "python"
    venv_python.symlink_to(sys.executable)
    command = root / ".venv" / "bin" / "aster-expert-mcp"
    command.write_text(
        f"#!{interpreter or venv_python}\nimport sys\n", encoding="utf-8"
    )
    command.chmod(0o755)
    (root / ".mcp.json").write_text(
        json.dumps(
            {"mcpServers": {"aster-expert": {"command": str(command), "args": []}}}
        ),
        encoding="utf-8",
    )
    return root


def test_mcp_server_interpreter_must_import_the_server(tmp_path: Path) -> None:
    ctx = _ctx(_mcp_project(tmp_path))
    ok = v.check_mcp_server(ctx, lambda a, t: _completed(a))
    assert ok.detail.endswith("module serveur importable")

    def broken(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return _completed(
            argv,
            1,
            stderr="Traceback\nModuleNotFoundError: No module named 'aster_expert'",
        )

    with pytest.raises(EnvCheckError, match="No module named 'aster_expert'"):
        v.check_mcp_server(ctx, broken)


def test_mcp_server_must_run_with_the_venv_python(tmp_path: Path) -> None:
    other = tmp_path / "autre_python"
    other.write_text("", encoding="utf-8")
    ctx = _ctx(_mcp_project(tmp_path, interpreter=other))
    with pytest.raises(EnvCheckError, match="pas avec le Python du .venv"):
        v.check_mcp_server(ctx, lambda a, t: _completed(a))


def test_mcp_server_command_must_exist(tmp_path: Path) -> None:
    root = _mcp_project(tmp_path)
    (root / ".venv" / "bin" / "aster-expert-mcp").unlink()
    with pytest.raises(EnvCheckError, match="introuvable après expansion"):
        v.check_mcp_server(_ctx(root), lambda a, t: _completed(a))


# --- Sequence and command ------------------------------------------------------------


def test_run_checks_stops_at_the_first_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[str] = []

    def passing(name: str) -> object:
        def check(*args: object, **kwargs: object) -> CheckResult:
            called.append(name)
            return CheckResult(name=name, detail="ok")

        return check

    def failing(*args: object, **kwargs: object) -> CheckResult:
        called.append("cave")
        raise EnvCheckError("absent")

    for name, function in (
        ("python", "check_python"),
        ("dependances", "check_dependencies"),
        ("docker", "check_docker"),
        ("image", "check_image"),
    ):
        monkeypatch.setattr(v, function, passing(name))
    monkeypatch.setattr(v, "check_cave", failing)
    seen: list[str] = []
    with pytest.raises(EnvCheckError, match=r"^cave : absent$"):
        v.run_checks(_ctx(_project(tmp_path)), on_result=lambda r: seen.append(r.name))
    assert called == ["python", "dependances", "docker", "cave"]
    assert seen == ["python", "dependances", "docker"]


def test_run_checks_turns_an_unexpected_error_into_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> CheckResult:
        raise KeyError("x")

    monkeypatch.setattr(v, "check_python", boom)
    with pytest.raises(EnvCheckError, match="python : erreur inattendue KeyError"):
        v.run_checks(_ctx(_project(tmp_path)))


def test_cli_env_check_exits_1_and_lists_unevaluated_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(ctx: EnvContext, *, on_result: Callable[[CheckResult], None]) -> None:
        on_result(CheckResult(name="python", detail="3.12.14"))
        raise EnvCheckError("dependances : pyyaml absent")

    monkeypatch.setattr(v, "from_machine", lambda root: _ctx(_project(tmp_path)))
    monkeypatch.setattr(v, "run_checks", fake_run)
    result = CliRunner().invoke(cli.app, ["env-check"])
    assert result.exit_code == 1
    assert "OK python : 3.12.14" in result.output
    assert "env-check ÉCHEC : dependances : pyyaml absent" in result.output
    assert f"Non évalués : {', '.join(CHECK_NAMES[2:])}" in result.output
    assert "Traceback" not in result.output


def test_cli_env_check_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(ctx: EnvContext, *, on_result: Callable[[CheckResult], None]) -> None:
        for name in CHECK_NAMES:
            on_result(CheckResult(name=name, detail="ok"))

    monkeypatch.setattr(v, "from_machine", lambda root: _ctx(_project(tmp_path)))
    monkeypatch.setattr(v, "run_checks", fake_run)
    result = CliRunner().invoke(cli.app, ["env-check"])
    assert result.exit_code == 0
    assert "env-check OK : 8 vérifications." in result.output


# --- The repository's own pins --------------------------------------------------------


def test_repository_pins_python_312_managed_by_uv() -> None:
    pin = (_REPO / ".python-version").read_text(encoding="utf-8").strip()
    assert pin == "3.12"
    project = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["tool"]["mypy"]["python_version"] == pin
    assert project["tool"]["ruff"]["target-version"] == "py312"
    assert project["tool"]["uv"]["python-preference"] == "only-managed"
    lock = tomllib.loads((_REPO / "uv.lock").read_text(encoding="utf-8"))
    assert lock["requires-python"] == project["project"]["requires-python"]
