"""Keyword values refused before any run (lot 49): `PARALLELISME_TEMPS='OUI'`, DIAG-027.

No Docker: the container function is replaced by one that fails the test if called.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

import aster_expert.execution.execute as execute_module
from aster_expert.execution.config import ExecutionConfig, load_execution_config
from aster_expert.execution.errors import ExecutionRunError
from aster_expert.execution.execute import execute_comm_file
from aster_expert.execution.interdits import ForbiddenKeyword, find_forbidden
from aster_expert.execution.ressources import MachineResources

ROOT = Path(__file__).resolve().parents[2]
RULE = ForbiddenKeyword(
    command="CALC_CHAMP",
    keyword="PARALLELISME_TEMPS",
    values=("OUI",),
    diagnostic="DIAG-027",
    reason="réactions fausses de 1 à 2 % sous MPI",
)
COMM = """DEBUT()
R = CALC_CHAMP(reuse=R, RESULTAT=R, FORCE=("REAC_NODA",), PARALLELISME_TEMPS={value})
FIN()
"""


def test_the_refused_value_is_found_with_its_line_and_diagnosis() -> None:
    found = find_forbidden(COMM.format(value='"OUI"'), [RULE])
    assert len(found) == 1
    assert found[0].line == 2
    assert "DIAG-027" in found[0].message()
    assert "PARALLELISME_TEMPS=OUI" in found[0].message()


def test_the_other_value_and_other_commands_pass() -> None:
    assert find_forbidden(COMM.format(value='"NON"'), [RULE]) == []
    text = "DEBUT()\nX = DEFI_CONSTANTE(VALE=1.0)\nFIN()\n"
    assert find_forbidden(text, [RULE]) == []


def test_an_unresolved_value_is_refused_too() -> None:
    text = COMM.format(value="choix").replace("DEBUT()\n", 'DEBUT()\nchoix = "OUI"\n')
    text = text.replace('choix = "OUI"', "choix = input()")
    found = find_forbidden(text, [RULE])
    assert [use.value for use in found] == ["<valeur non résolue>"]


def test_the_configuration_refuses_time_parallelism_with_diag_027() -> None:
    config = load_execution_config(ROOT / "config" / "validation.yaml")
    rules = {(r.command, r.keyword): r for r in config.forbidden_keywords}
    rule = rules[("CALC_CHAMP", "PARALLELISME_TEMPS")]
    assert rule.values == ("OUI",)
    assert rule.diagnostic == "DIAG-027"
    diagnosis = yaml.safe_load(
        (ROOT / "connaissances" / "diagnostics" / "DIAG-027.yaml").read_text("utf-8")
    )
    assert "PARALLELISME_TEMPS" in diagnosis["keywords"]


def test_the_run_is_refused_before_any_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    (root / "astest").mkdir(parents=True)
    comm = root / "astest" / "cas.comm"
    comm.write_text(COMM.format(value='"OUI"'), encoding="utf-8")

    def never(**_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("aucun conteneur ne doit démarrer")

    monkeypatch.setattr(execute_module, "run_in_container", never)
    config = ExecutionConfig(
        enabled=True,
        allowed_roots=("astest",),
        work_dir_root="data/processed/runs",
        keep_work_dir=True,
        timeout_seconds=None,
        memory_mb=None,
        mpi_processes=1,
        write_outside_work_dir=False,
        forbidden_keywords=(RULE,),
    )
    with pytest.raises(ExecutionRunError, match="DIAG-027"):
        execute_comm_file(
            comm,
            project_root=root,
            config=config,
            docker_bin=Path("/usr/bin/docker"),
            image_repository="simvia/code_aster",
            image_digest="sha256:test",
            aster_version="17.4.0",
            machine=MachineResources(
                cpus=14, memory_total_mb=21_000, memory_available_mb=18_000
            ),
        )
    assert not (root / "data" / "processed" / "runs").exists()
