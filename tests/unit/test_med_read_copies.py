"""Lot 47 ter, ENV-003: the reader of a MED of results copies it into its work
directory; the copy (1.9 GB for the jetty) and the extraction were never deleted and
filled the disk of the VM. Now the copy goes as soon as the container returns, even
on failure, and `take_arrays` deletes the extraction once loaded. No Docker."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aster_expert.meshing.check import run_then_drop_copy
from aster_expert.meshing.errors import MeshCheckError
from aster_expert.report import med_read

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "config").mkdir()
    shutil.copy2(ROOT / "config" / "validation.yaml", tmp_path / "config")
    monkeypatch.setattr(
        med_read, "resolve_digest_for_version", lambda *a, **k: ("sha256:0", None)
    )
    monkeypatch.setattr(med_read, "find_docker_binary", lambda *a: "docker")
    return tmp_path


def _fake_container(returncode: int) -> Any:
    def runner(**kwargs: Any) -> subprocess.CompletedProcess[str]:
        work = Path(kwargs["workdir"])
        assert (work / "input.med").read_bytes() == b"MED"  # the copy exists
        (work / "out.json").write_text(json.dumps({"fields": {}}), "utf-8")
        np.savez(work / "out.npz", a=np.arange(3.0))
        return subprocess.CompletedProcess([], returncode, "", "erreur simulée")

    return runner


def test_the_copy_is_deleted_after_reading_and_the_arrays_once_loaded(
    project: Path, tmp_path: Path
) -> None:
    med = tmp_path / "resultats.rmed"
    med.write_bytes(b"MED")
    payload = med_read.run_med_script(
        med, ["extract"], project_root=project, runner=_fake_container(0)
    )
    work = Path(payload["_work_dir"])
    assert not (work / "input.med").exists()
    assert med.read_bytes() == b"MED"  # the original is never touched
    arrays = med_read.take_arrays(payload)
    assert list(arrays["a"]) == [0.0, 1.0, 2.0]
    assert not (work / "out.npz").exists()
    assert (work / "out.json").is_file()  # the small JSON report stays


def test_the_copy_is_deleted_when_the_reader_fails(
    project: Path, tmp_path: Path
) -> None:
    med = tmp_path / "resultats.rmed"
    med.write_bytes(b"MED")
    with pytest.raises(MeshCheckError):
        med_read.run_med_script(
            med, ["extract"], project_root=project, runner=_fake_container(1)
        )
    copies = list((project / "data").rglob("input.med"))
    assert copies == []


def test_run_then_drop_copy_on_an_exception(tmp_path: Path) -> None:
    copy = tmp_path / "input.med"
    copy.write_bytes(b"MED")

    def boom(**_: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("docker", 1)

    with pytest.raises(subprocess.TimeoutExpired):
        run_then_drop_copy(boom, copy)
    assert not copy.exists()
