"""`scripts/run_comm.py` under MPI (lot 47 quater, ENV-004).

With `mpi_nbcpu` > 1, `run_aster_main` restarts itself under `mpiexec` with its own
`--status-file` and leaves none where we asked: the status must then come from
`run_aster.status.get_status` on the listing of every rank. `run_aster` is only
importable in the container, so a stand-in package is injected; it reproduces the
behaviour observed on `simvia/code_aster:17.4.0` (runs `m02`, `m04` of the lot).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_comm.py"


class _Status:
    def __init__(self, diag: str = "?", exitcode: int = -1) -> None:
        self.diag = diag
        self.exitcode = exitcode
        self.times = [1.0, 0.0, 1.0, 2.0]

    @staticmethod
    def load(_path: str) -> _Status:
        raise AssertionError("aucun fichier de statut en MPI")

    def is_completed(self) -> bool:
        return self.diag == "OK"

    def results_saved(self) -> bool:
        return self.diag == "OK"


def _get_status(exitcode: int, output: str) -> _Status:
    text = Path(output).read_text(encoding="utf-8")
    return _Status("OK" if "DIAGNOSTIC JOB : OK" in text else "<F>_ERROR", exitcode)


def _load(monkeypatch: pytest.MonkeyPatch, ranks: dict[int, str]) -> Any:
    def fake_main(argv: list[str]) -> int:
        wrkdir = Path(argv[argv.index("--wrkdir") + 1])
        for rank, text in ranks.items():
            (wrkdir / f"proc.{rank}").mkdir()
            (wrkdir / f"proc.{rank}" / "fort.6").write_text(text, encoding="utf-8")
        return 0

    package = types.ModuleType("run_aster")
    main_module = types.ModuleType("run_aster.run_aster_main")
    main_module.main = fake_main  # type: ignore[attr-defined]
    status_module = types.ModuleType("run_aster.status")
    status_module.Status = _Status  # type: ignore[attr-defined]
    status_module.get_status = _get_status  # type: ignore[attr-defined]
    errors_module = types.ModuleType("run_aster.error_messages")
    errors_module.search_msg = lambda _text, maxlines: {}  # type: ignore[attr-defined]
    for name, module in (
        ("run_aster", package),
        ("run_aster.run_aster_main", main_module),
        ("run_aster.status", status_module),
        ("run_aster.error_messages", errors_module),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("run_comm_for_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(module: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Any:
    module.main(
        [
            "--file",
            str(tmp_path / "cas.export"),
            "--wrkdir",
            str(tmp_path),
            "--status-file",
            str(tmp_path / "__status__"),
            "--time-limit",
            "60",
            "--memory-limit",
            "512",
        ]
    )
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_mpi_status_comes_from_every_rank_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ok = "--- DIAGNOSTIC JOB : OK\n"
    module = _load(monkeypatch, {0: ok, 1: ok})
    payload = _run(module, tmp_path, capsys)
    assert payload["diag"] == "OK"
    assert payload["status_source"].startswith("run_aster.status.get_status sur 2 rang")


def test_a_failure_on_another_rank_is_not_hidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load(monkeypatch, {0: "--- DIAGNOSTIC JOB : OK\n", 1: " <F> arrêt\n"})
    payload = _run(module, tmp_path, capsys)
    assert payload["diag"] == "<F>_ERROR"
    assert "proc.1/fort.6" in payload["status_source"]
