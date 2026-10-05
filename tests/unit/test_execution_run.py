"""Unit tests for level-C execution (docs/development-plan.md, lot 11).

`aster_expert.execution.execute.run_in_container` is monkeypatched -- it is
the one function in the whole pipeline that needs the Aster container
(docs/architecture.md, ADR-002): staging, allowed-roots enforcement, status
mapping, timeout handling and result-file collection are all plain project
Python, exercised here for real. No Docker, no network.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import aster_expert.execution.execute as execute_module
from aster_expert.execution.config import ExecutionConfig, load_execution_config
from aster_expert.execution.errors import ExecutionRunError
from aster_expert.execution.execute import check_allowed, execute_comm_file

DIGEST = "sha256:testdigest"


def _completed(
    argv: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def _config(**overrides: object) -> ExecutionConfig:
    base: dict[str, object] = {
        "enabled": True,
        "allowed_roots": ("astest",),
        "work_dir_root": "data/processed/runs",
        "keep_work_dir": True,
        "timeout_seconds": 1800,
        "memory_mb": 4096,
        "cpus_limit": "1",
        "mpi_processes": 1,
        "write_outside_work_dir": False,
    }
    base.update(overrides)
    return ExecutionConfig(**base)  # type: ignore[arg-type]


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "astest").mkdir(parents=True)
    (root / "outside").mkdir(parents=True)
    return root


# --- check_allowed ------------------------------------------------------------


def test_check_allowed_refuses_when_no_roots_declared(project_root: Path) -> None:
    comm = project_root / "astest" / "case.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    with pytest.raises(ExecutionRunError, match="aucune racine"):
        check_allowed(comm, config=_config(allowed_roots=()), project_root=project_root)


def test_check_allowed_refuses_missing_file(project_root: Path) -> None:
    comm = project_root / "astest" / "missing.comm"
    with pytest.raises(ExecutionRunError, match="introuvable"):
        check_allowed(comm, config=_config(), project_root=project_root)


def test_check_allowed_refuses_non_comm_suffix(project_root: Path) -> None:
    export = project_root / "astest" / "case.export"
    export.write_text("F comm case.comm D 1\n", encoding="utf-8")
    with pytest.raises(ExecutionRunError, match="extension"):
        check_allowed(export, config=_config(), project_root=project_root)


def test_check_allowed_refuses_file_outside_roots(project_root: Path) -> None:
    comm = project_root / "outside" / "case.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    with pytest.raises(ExecutionRunError, match="hors des racines autorisées"):
        check_allowed(comm, config=_config(), project_root=project_root)


def test_check_allowed_accepts_file_inside_root(project_root: Path) -> None:
    comm = project_root / "astest" / "case.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    resolved = check_allowed(comm, config=_config(), project_root=project_root)
    assert resolved == comm.resolve()


# --- load_execution_config -----------------------------------------------------


def test_load_execution_config_parses_real_file() -> None:
    config_path = Path(__file__).resolve().parents[2] / "config" / "validation.yaml"
    config = load_execution_config(config_path)
    assert config.enabled is True
    assert "external/codeaster-src/astest" in config.allowed_roots


def test_load_execution_config_missing_section(tmp_path: Path) -> None:
    config_path = tmp_path / "validation.yaml"
    config_path.write_text("schema_version: 1\n", encoding="utf-8")
    with pytest.raises(ExecutionRunError, match="execution"):
        load_execution_config(config_path)


# --- execute_comm_file ----------------------------------------------------------


def _stub_result(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return _completed(["docker"], stdout=json.dumps(payload) + "\n")


def _write_case(project_root: Path, *, with_export: bool = False) -> Path:
    comm = project_root / "astest" / "case.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    if with_export:
        (project_root / "astest" / "case.export").write_text(
            "F comm case.comm D 1\nF mmed case.mmed D 20\n", encoding="utf-8"
        )
        (project_root / "astest" / "case.mmed").write_text("mesh\n", encoding="utf-8")
    return comm


def test_execute_comm_file_direct_mode_ok(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)
    captured: dict[str, object] = {}

    def fake_run_in_container(
        *, workdir: Path, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured["workdir"] = workdir
        captured["kwargs"] = kwargs
        # Simulate the .mess file run_aster would have produced.
        (workdir / "fort.6").write_text("-- CODE_ASTER -- VERSION\n", encoding="utf-8")
        (workdir / "glob.1").write_text("result database\n", encoding="utf-8")
        return _stub_result(
            {
                "ok": True,
                "return_code": 0,
                "status_exitcode": 0,
                "diag": "OK",
                "is_completed": True,
                "results_saved": True,
                "times": [0.1, 0.0, 0.1, 0.2],
            }
        )

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert report.status == "completed_ok"
    assert report.diag == "OK"
    assert report.return_code == 0
    assert report.image_digest == DIGEST
    assert report.mess_path is not None
    assert Path(report.mess_path).name == "fort.6"
    assert "glob.1" in report.result_files
    # The staged input itself is never reported as "produced".
    assert "case.comm" not in report.result_files

    kwargs = captured["kwargs"]
    assert kwargs["cpus"] == "1"  # type: ignore[index]
    assert kwargs["memory"] == "4096m"  # type: ignore[index]


def test_execute_comm_file_finds_mess_under_proc_n(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`simvia/code_aster:17.4.0` nests output under `proc.0/` even for a
    single process (docs/development-plan.md, lot 11) -- confirmed against
    the real container, `astest/zzzz169a.comm`."""
    comm = _write_case(project_root)

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        proc_dir = workdir / "proc.0"
        proc_dir.mkdir()
        (proc_dir / "fort.6").write_text("mess content\n", encoding="utf-8")
        return _stub_result(
            {
                "ok": True,
                "return_code": 0,
                "diag": "OK",
                "is_completed": True,
                "results_saved": True,
                "times": [0.0, 0.0, 0.0, 0.0],
            }
        )

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert report.mess_path is not None
    assert Path(report.mess_path) == Path(report.work_dir) / "proc.0" / "fort.6"


def test_execute_comm_file_export_mode_stages_siblings(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root, with_export=True)
    staged: dict[str, object] = {}

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        staged["files"] = sorted(p.name for p in workdir.iterdir())
        return _stub_result(
            {
                "ok": True,
                "return_code": 0,
                "status_exitcode": 0,
                "diag": "OK",
                "is_completed": True,
                "results_saved": True,
                "times": [0.0, 0.0, 0.0, 0.0],
            }
        )

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    files = staged["files"]
    assert "case.comm" in files  # type: ignore[operator]
    assert "case.export" in files  # type: ignore[operator]
    assert "case.mmed" in files  # type: ignore[operator]


def test_execute_comm_file_alarms_never_reported_as_plain_ok(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _stub_result(
            {
                "ok": True,
                "return_code": 0,
                "status_exitcode": 0,
                "diag": "<A>_ALARM",
                "is_completed": True,
                "results_saved": True,
                "times": [0.0, 0.0, 0.0, 0.0],
            }
        )

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert report.status == "completed_with_alarms"


def test_execute_comm_file_crash_before_status(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _stub_result({"ok": False, "crash": "ImportError: no code_aster"})

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert report.status == "crashed"
    assert report.diag is None


def test_execute_comm_file_unrecognized_diag_fails_loudly(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _stub_result({"ok": True, "diag": "<X>_NEVER_SEEN"})

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    with pytest.raises(ExecutionRunError, match="unrecognized diagnostic"):
        execute_comm_file(
            comm,
            project_root=project_root,
            config=_config(),
            docker_bin=Path("/usr/bin/docker"),
            image_repository="simvia/code_aster",
            image_digest=DIGEST,
            aster_version="17.4.0",
        )


def test_execute_comm_file_timeout_kills_container_and_reports_interrupted(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)
    killed: list[str] = []

    def fake_run_in_container(
        *, container_name: str, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="docker run", timeout=1)

    def fake_kill_container(_docker_bin: Path, name: str, **_kwargs: object) -> None:
        killed.append(name)

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)
    monkeypatch.setattr(execute_module, "kill_container", fake_kill_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(timeout_seconds=1),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert report.status == "interrupted_timeout"
    assert report.return_code is None
    assert len(killed) == 1


def test_execute_comm_file_removes_work_dir_when_not_kept(
    project_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _write_case(project_root)

    def fake_run_in_container(
        *, workdir: Path, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _stub_result(
            {
                "ok": True,
                "return_code": 0,
                "diag": "OK",
                "is_completed": True,
                "results_saved": True,
                "times": [0.0, 0.0, 0.0, 0.0],
            }
        )

    monkeypatch.setattr(execute_module, "run_in_container", fake_run_in_container)

    report = execute_comm_file(
        comm,
        project_root=project_root,
        config=_config(keep_work_dir=False),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest=DIGEST,
        aster_version="17.4.0",
    )

    assert not Path(report.work_dir).exists()
