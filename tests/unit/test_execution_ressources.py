"""Resources of a run (lot 47 quater, DIAG-025): `.export` → `docker run` limits.

No Docker: `subprocess.run` of `aster_expert.execution.docker_client` is replaced by a
recorder, so the test reads the very argument vector `docker run` would receive.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import aster_expert.execution.execute as execute_module
from aster_expert.execution.config import ExecutionConfig
from aster_expert.execution.container_env import build_environment_setup_script
from aster_expert.execution.errors import ExecutionRunError
from aster_expert.execution.execute import execute_comm_file
from aster_expert.execution.ressources import (
    RUN_ASTER_DEFAULT_TIME_LIMIT,
    ExportParameters,
    MachineResources,
    ResourceSettings,
    check_free_disk,
    load_machine_overrides,
    machine_resources,
    read_export_parameters,
    resolve_resources,
    settings_from,
)

MACHINE = MachineResources(cpus=14, memory_total_mb=21_000, memory_available_mb=18_000)


def _settings(**overrides: object) -> ResourceSettings:
    raw: dict[str, object] = {
        "timeout_seconds": None,
        "memory_mb": None,
        "ncpus": 1,
        "mpi_processes": 1,
        "memory_margin_mb": 2800,
        "memory_share": 0.8,
        "min_free_disk_gb": 10.0,
    }
    raw.update(overrides)
    return settings_from(raw, {})


def _config(**overrides: object) -> ExecutionConfig:
    base: dict[str, object] = {
        "enabled": True,
        "allowed_roots": ("astest",),
        "work_dir_root": "data/processed/runs",
        "keep_work_dir": True,
        "timeout_seconds": None,
        "memory_mb": None,
        "mpi_processes": 1,
        "write_outside_work_dir": False,
        "memory_margin_mb": 2800,
    }
    base.update(overrides)
    return ExecutionConfig(**base)  # type: ignore[arg-type]


# --- .export ---------------------------------------------------------------------


def test_the_four_resource_parameters_are_read_and_files_ignored(
    tmp_path: Path,
) -> None:
    export = tmp_path / "cas.export"
    export.write_text(
        "P time_limit 7200\nP memory_limit 10240\nP ncpus 4\nP mpi_nbcpu 2\n"
        "P mpi_nbnoeud 1\nF comm cas.comm D 1\nF mmed cas.mmed D 20\n",
        encoding="utf-8",
    )
    assert read_export_parameters(export) == ExportParameters(
        time_limit=7200.0, memory_limit=10240.0, ncpus=4, mpi_nbcpu=2
    )


def test_an_unreadable_or_non_positive_parameter_is_refused(tmp_path: Path) -> None:
    export = tmp_path / "cas.export"
    export.write_text("P ncpus quatre\n", encoding="utf-8")
    with pytest.raises(
        ExecutionRunError, match="ligne 1 : valeur illisible pour ncpus"
    ):
        read_export_parameters(export)
    export.write_text("P time_limit 0\n", encoding="utf-8")
    with pytest.raises(ExecutionRunError, match="time_limit doit être positif"):
        read_export_parameters(export)


# --- precedence --------------------------------------------------------------------


def test_the_export_wins_over_the_configuration() -> None:
    resolved = resolve_resources(
        export=ExportParameters(
            time_limit=7200, memory_limit=10240, ncpus=4, mpi_nbcpu=1
        ),
        settings=_settings(timeout_seconds=1800, memory_mb=8192),
        machine=MACHINE,
    )
    assert (resolved.time_limit, resolved.memory_limit_mb) == (7200, 10240)
    assert resolved.origins["time_limit"] == ".export"
    assert resolved.docker_cpus == 4
    assert resolved.docker_memory_mb == 10240 + 2800
    assert resolved.outer_timeout == int(7200 * 1.25 * 4) + 20


def test_the_command_line_wins_over_the_export() -> None:
    resolved = resolve_resources(
        export=ExportParameters(time_limit=7200, memory_limit=10240),
        settings=_settings(),
        machine=MACHINE,
        cli_timeout=60,
        cli_memory_mb=1024,
    )
    assert (resolved.time_limit, resolved.memory_limit_mb) == (60, 1024)
    assert resolved.origins["memory_limit"] == "ligne de commande"


def test_without_export_nor_configuration_the_defaults_are_run_aster_and_machine() -> (
    None
):
    resolved = resolve_resources(
        export=ExportParameters(), settings=_settings(ncpus=8), machine=MACHINE
    )
    assert resolved.time_limit == RUN_ASTER_DEFAULT_TIME_LIMIT
    # ncpus is what run_aster will use inside the container, never the configuration.
    assert (resolved.ncpus, resolved.origins["ncpus"]) == (1, "défaut de run_aster")
    assert resolved.memory_limit_mb == int(18_000 * 0.8) - 2800


def test_a_bare_comm_runs_one_process_with_one_thread() -> None:
    resolved = resolve_resources(export=None, settings=_settings(), machine=MACHINE)
    assert (resolved.ncpus, resolved.mpi_nbcpu, resolved.docker_cpus) == (1, 1, 1)


def test_more_tasks_than_processors_is_refused() -> None:
    with pytest.raises(ExecutionRunError, match=r"4 × 4 = 16 dépasse les 14"):
        resolve_resources(
            export=ExportParameters(ncpus=4, mpi_nbcpu=4),
            settings=_settings(),
            machine=MACHINE,
        )


def test_more_memory_than_the_machine_is_refused() -> None:
    with pytest.raises(ExecutionRunError, match="au-delà des 21000 Mio"):
        resolve_resources(
            export=ExportParameters(memory_limit=8000, mpi_nbcpu=2),
            settings=_settings(),
            machine=MACHINE,
        )


# --- machine ---------------------------------------------------------------------


def test_machine_resources_read_meminfo(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       21504000 kB\nMemFree:  1000 kB\nMemAvailable:   19456000 kB\n",
        encoding="utf-8",
    )
    found = machine_resources(meminfo, cpu_count=lambda: 14)
    assert found == MachineResources(
        cpus=14, memory_total_mb=21000, memory_available_mb=19000
    )


def test_machine_configuration_overrides_and_rejects_unknown_keys(
    tmp_path: Path,
) -> None:
    (tmp_path / "config").mkdir()
    local = tmp_path / "config" / "machine.local.yaml"
    local.write_text("execution:\n  ncpus: 6\n  memory_mb: 12000\n", encoding="utf-8")
    settings = _config().resource_settings(tmp_path)
    assert (settings.ncpus, settings.memory_mb) == (6, 12000)
    local.write_text("execution:\n  cpus_limit: 4\n", encoding="utf-8")
    with pytest.raises(
        ExecutionRunError, match="clé\\(s\\) inconnue\\(s\\) cpus_limit"
    ):
        load_machine_overrides(tmp_path)


def test_the_disk_threshold_refuses_before_any_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def full(_where: Path) -> tuple[int, int, int]:
        return (120 * 10**9, 115 * 10**9, 5 * 10**9)

    with pytest.raises(
        ExecutionRunError, match=r"5\.0 Go libres .*seuil 10 Go.*ENV-003"
    ):
        check_free_disk(tmp_path, 10.0, full)

    root = tmp_path / "project"
    (root / "astest").mkdir(parents=True)
    comm = root / "astest" / "case.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")

    def never(**_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("aucun conteneur ne doit démarrer")

    monkeypatch.setattr(execute_module, "run_in_container", never)
    with pytest.raises(ExecutionRunError, match="espace disque insuffisant"):
        execute_comm_file(
            comm,
            project_root=root,
            config=_config(),
            docker_bin=Path("/usr/bin/docker"),
            image_repository="simvia/code_aster",
            image_digest="sha256:test",
            aster_version="17.4.0",
            machine=MACHINE,
            disk_usage=full,
        )


# --- end to end: the .export reaches `docker run` ---------------------------------


def test_the_export_is_passed_on_to_docker_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    (root / "astest").mkdir(parents=True)
    comm = root / "astest" / "cas.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    (root / "astest" / "cas.export").write_text(
        "P time_limit 7200\nP memory_limit 3000\nP ncpus 4\nP mpi_nbcpu 2\n"
        "F comm cas.comm D 1\n",
        encoding="utf-8",
    )
    recorded: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["argv"] = argv
        recorded["timeout"] = kwargs["timeout"]
        payload = {"ok": True, "return_code": 0, "diag": "OK", "times": [0, 0, 0, 0]}
        return subprocess.CompletedProcess(
            argv, 0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr("aster_expert.execution.docker_client.subprocess.run", fake_run)
    report = execute_comm_file(
        comm,
        project_root=root,
        config=_config(),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest="sha256:test",
        aster_version="17.4.0",
        machine=MACHINE,
        disk_usage=lambda _p: (10**12, 0, 10**12),
    )
    argv = recorded["argv"]
    assert isinstance(argv, list)
    assert "--cpus=8" in argv  # ncpus 4 × mpi_nbcpu 2
    assert f"--memory={2 * (3000 + 2800)}m" in argv
    assert recorded["timeout"] == int(7200 * 1.25 * 4) + 20
    command = argv[-1]
    assert "--time-limit 7200 --memory-limit 3000" in command
    assert "--file /work/cas.export" in command
    record = json.loads(
        (Path(report.work_dir) / "compte_rendu.json").read_text(encoding="utf-8")
    )
    assert "ncpus 4 (.export), mpi_nbcpu 2 (.export)" in record["resources"]
    assert "docker --cpus=8" in record["resources"]


def test_mpiexec_of_the_spack_view_is_put_on_the_path() -> None:
    script = build_environment_setup_script()
    assert 'export PATH="$PATH:$VIEW/bin"' in script
    # Appended after profile.sh: the Python it selects stays first.
    assert script.index('export PATH="$PATH:$VIEW/bin"') > script.index("profile.sh")
