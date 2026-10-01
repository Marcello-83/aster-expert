"""Compte rendu lisible de chaque exécution (lot 41, étape 5.1) : JSON et Markdown
écrits à côté de l'exécution, messages `<A>`/`<F>` de `run_aster.error_messages`
avec leur identifiant. Le conteneur est simulé (`run_in_container`), comme dans
`test_execution_run.py` ; l'extraction réelle est éprouvée par `pytest -m lent`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import aster_expert.execution.execute as execute_module
from aster_expert.execution.compte_rendu import (
    REPORT_JSON,
    REPORT_MD,
    load_record,
    parse_message,
)
from aster_expert.execution.config import ExecutionConfig
from aster_expert.execution.execute import execute_comm_file


def _config(root: Path) -> ExecutionConfig:
    return ExecutionConfig(
        enabled=True,
        allowed_roots=("cas",),
        work_dir_root="runs",
        keep_work_dir=True,
        timeout_seconds=60,
        memory_mb=1024,
        cpus_limit="1",
        mpi_processes=1,
        write_outside_work_dir=False,
    )


def _case(root: Path) -> Path:
    (root / "cas").mkdir(parents=True)
    comm = root / "cas" / "essai.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    (root / "cas" / "essai.export").write_text("F comm essai.comm D 1\n", "utf-8")
    return comm


def _stub(payload: dict[str, object]):  # type: ignore[no-untyped-def]
    def fake(*, workdir: Path, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (workdir / "proc.0").mkdir()
        (workdir / "proc.0" / "fort.6").write_text("listing\n", encoding="utf-8")
        (workdir / "resu.med").write_bytes(b"12345")
        return subprocess.CompletedProcess(
            ["docker"], 0, stdout=json.dumps(payload) + "\n", stderr=""
        )

    return fake


def test_parse_message_reads_kind_and_identifier() -> None:
    fatal = parse_message(
        378, "<F> <CALCULEL7_40>\n\n Le calcul   n'est pas possible pour POUTRE"
    )
    assert fatal.kind == "<F>"
    assert fatal.identifier == "CALCULEL7_40"
    assert fatal.text == "<F> <CALCULEL7_40> Le calcul n'est pas possible pour POUTRE"
    alarm = parse_message(12, "<A> sans identifiant")
    assert (alarm.kind, alarm.identifier) == ("<A>", None)
    python = parse_message(3, "Traceback (most recent call last)")
    assert python.kind == "erreur Python"


def test_a_failed_run_writes_its_report_with_the_fatal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _case(tmp_path)
    monkeypatch.setattr(
        execute_module,
        "run_in_container",
        _stub(
            {
                "ok": True,
                "return_code": 1,
                "diag": "<F>_ERROR",
                "messages": [
                    {"line": 20, "text": "<A> <MODELISA4_8> alarme"},
                    {"line": 21, "text": "<A> <MODELISA4_8> alarme"},
                    {"line": 99, "text": "<F> <CALCULEL7_40> arrêt"},
                ],
                "messages_source": "run_aster.error_messages",
                "messages_truncated": 0,
            }
        ),
    )

    report = execute_comm_file(
        comm,
        project_root=tmp_path,
        config=_config(tmp_path),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest="sha256:" + "a" * 64,
        aster_version="17.4.0",
    )

    assert report.status == "failed"
    record = load_record(Path(report.work_dir))
    assert record.alarms_by_identifier == {"MODELISA4_8": 2}
    assert [(m.kind, m.identifier) for m in record.errors] == [("<F>", "CALCULEL7_40")]
    assert set(record.inputs_sha256) == {"essai.comm", "essai.export"}
    assert record.outputs["resu.med"] == 5
    assert "--file /work/essai.export" in record.command
    markdown = (Path(report.work_dir) / REPORT_MD).read_text(encoding="utf-8")
    assert "| <F> | CALCULEL7_40 | 99 | <F> <CALCULEL7_40> arrêt |" in markdown
    assert "| `MODELISA4_8` | 2 |" in markdown
    assert (
        json.loads((Path(report.work_dir) / REPORT_JSON).read_text("utf-8"))["report"][
            "status"
        ]
        == "failed"
    )


def test_a_crashed_run_still_writes_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _case(tmp_path)
    monkeypatch.setattr(
        execute_module,
        "run_in_container",
        _stub({"ok": False, "crash": "ImportError: run_aster"}),
    )

    report = execute_comm_file(
        comm,
        project_root=tmp_path,
        config=_config(tmp_path),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest="sha256:" + "a" * 64,
        aster_version="17.4.0",
    )

    assert report.status == "crashed"
    markdown = (Path(report.work_dir) / REPORT_MD).read_text(encoding="utf-8")
    assert "Messages non extraits : ImportError: run_aster" in markdown


def test_a_timeout_writes_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    comm = _case(tmp_path)

    def too_long(**_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["docker"], 1)

    monkeypatch.setattr(execute_module, "run_in_container", too_long)
    monkeypatch.setattr(execute_module, "kill_container", lambda *a: None)

    report = execute_comm_file(
        comm,
        project_root=tmp_path,
        config=_config(tmp_path),
        docker_bin=Path("/usr/bin/docker"),
        image_repository="simvia/code_aster",
        image_digest="sha256:" + "a" * 64,
        aster_version="17.4.0",
    )

    assert report.status == "interrupted_timeout"
    assert load_record(Path(report.work_dir)).report.status == "interrupted_timeout"
