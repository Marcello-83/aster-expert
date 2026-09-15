"""Unit tests for `aster-expert catalogue extract` orchestration.

No Docker, no network: `run_in_container` and `find_docker_binary` are
monkeypatched, matching the pattern used for lot 2 (tests/unit/test_detect.py).
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.catalogue import extract
from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.execution.models import (
    AsterPythonInfo,
    CatalogueInfo,
    CodeAsterPackageInfo,
    ContainerInfo,
    DetectedEnvironment,
    InvocationInfo,
    RunAsterInfo,
)

SAMPLE_SCHEMA = {
    "command": "AFFE_CHAR_MECA",
    "aster_version": "17.4.0",
    "image_digest": "sha256:d8d19ea9",
    "catalogue_source": "/opt/x/code_aster",
    "catalogue_hash": "sha256:fingerprint",
    "kind": "operator",
    "result_type": "char_meca",
    "result_type_dynamic": False,
    "docu": None,
    "keywords": [],
    "extracted_at": "2026-01-01T00:00:00+00:00",
}

SAMPLE_SUMMARY = {
    "total_exposed": 1,
    "total_extracted": 1,
    "kind_counts": {"operator": 1},
    "encountered_classes": ["Operator"],
    "commands_without_usable_docu": 1,
    "anomalies": [],
}


def _sample_detected() -> DetectedEnvironment:
    return DetectedEnvironment(
        detected_at=datetime(2026, 9, 15, 8, 0, 0, tzinfo=UTC),
        install_kind="container_docker",
        container=ContainerInfo(
            engine="docker",
            engine_version_raw="Docker version 29.1.3",
            image_repository="simvia/code_aster",
            image_tag="17.4.0",
            image_digest="sha256:d8d19ea9",
            image_id="sha256:6a66bdaf",
            cave_pin_source="global",
        ),
        run_aster=RunAsterInfo(
            path_in_container="/opt/x/bin/run_aster", version_raw="v"
        ),
        aster_python=AsterPythonInfo(
            interpreter_path_in_container="/opt/x/bin/python3", pythonpath_extra=()
        ),
        code_aster_package=CodeAsterPackageInfo(path_in_container="/opt/x/code_aster"),
        catalogue=CatalogueInfo(
            path_in_container="/opt/x/code_aster/Cata",
            fingerprint_sha256="sha256:fingerprint",
        ),
        invocation=InvocationInfo(
            mechanism="profile_sh_plus_view", mount_pattern="x:/work"
        ),
    )


def test_extract_catalogue_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    output_root = tmp_path / "catalogue"
    script_path = tmp_path / "introspect_catalogue.py"
    script_path.write_text("# fake\n", encoding="utf-8")

    monkeypatch.setattr(
        extract, "find_docker_binary", lambda explicit: Path("/usr/bin/docker")
    )

    def fake_run_in_container(
        *,
        docker_bin: Path,
        image_ref: str,
        workdir: Path,
        command: str,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert image_ref == "simvia/code_aster@sha256:d8d19ea9"
        (workdir / "out" / "AFFE_CHAR_MECA.json").write_text(
            json.dumps(SAMPLE_SCHEMA), encoding="utf-8"
        )
        return subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(SAMPLE_SUMMARY), stderr=""
        )

    monkeypatch.setattr(extract, "run_in_container", fake_run_in_container)

    digest_dir, summary = extract.extract_catalogue(
        detected=_sample_detected(),
        workroot=workroot,
        output_root=output_root,
        script_path=script_path,
    )

    assert digest_dir == output_root / "sha256:d8d19ea9"
    assert (digest_dir / "AFFE_CHAR_MECA.json").is_file()
    assert summary.total_extracted == 1
    assert summary.anomalies == []


def test_extract_catalogue_replaces_prior_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    output_root = tmp_path / "catalogue"
    script_path = tmp_path / "introspect_catalogue.py"
    script_path.write_text("# fake\n", encoding="utf-8")

    stale_dir = output_root / "sha256:d8d19ea9"
    stale_dir.mkdir(parents=True)
    (stale_dir / "STALE_COMMAND.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        extract, "find_docker_binary", lambda explicit: Path("/usr/bin/docker")
    )

    def fake_run_in_container(
        *, workdir: Path, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        (workdir / "out" / "AFFE_CHAR_MECA.json").write_text(
            json.dumps(SAMPLE_SCHEMA), encoding="utf-8"
        )
        return subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(SAMPLE_SUMMARY), stderr=""
        )

    monkeypatch.setattr(extract, "run_in_container", fake_run_in_container)

    digest_dir, _summary = extract.extract_catalogue(
        detected=_sample_detected(),
        workroot=workroot,
        output_root=output_root,
        script_path=script_path,
    )

    assert not (digest_dir / "STALE_COMMAND.json").exists()
    assert (digest_dir / "AFFE_CHAR_MECA.json").is_file()


def test_extract_catalogue_hard_error_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    script_path = tmp_path / "introspect_catalogue.py"
    script_path.write_text("# fake\n", encoding="utf-8")

    monkeypatch.setattr(
        extract, "find_docker_binary", lambda explicit: Path("/usr/bin/docker")
    )

    failing_summary = {
        "total_exposed": 2,
        "total_extracted": 1,
        "kind_counts": {"operator": 1},
        "encountered_classes": ["Operator"],
        "commands_without_usable_docu": 1,
        "anomalies": [
            {"command": "BROKEN", "kind": "extraction_error", "detail": "boom"}
        ],
    }

    def fake_run_in_container(
        *, workdir: Path, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        (workdir / "out" / "AFFE_CHAR_MECA.json").write_text(
            json.dumps(SAMPLE_SCHEMA), encoding="utf-8"
        )
        return subprocess.CompletedProcess(
            [], 1, stdout=json.dumps(failing_summary), stderr="1 command failed"
        )

    monkeypatch.setattr(extract, "run_in_container", fake_run_in_container)

    digest_dir, summary = extract.extract_catalogue(
        detected=_sample_detected(),
        workroot=workroot,
        output_root=tmp_path / "catalogue",
        script_path=script_path,
    )
    # Extraction is not aborted: the good command is still written, the
    # failure is reported in the summary (never silent).
    assert (digest_dir / "AFFE_CHAR_MECA.json").is_file()
    assert summary.anomalies[0].kind == "extraction_error"


def test_extract_catalogue_missing_workroot(tmp_path: Path) -> None:
    with pytest.raises(CatalogueExtractionError, match="work root"):
        extract.extract_catalogue(
            detected=_sample_detected(),
            workroot=tmp_path / "missing",
            output_root=tmp_path / "catalogue",
        )


def test_extract_catalogue_missing_script(tmp_path: Path) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    with pytest.raises(
        CatalogueExtractionError, match="introspection script not found"
    ):
        extract.extract_catalogue(
            detected=_sample_detected(),
            workroot=workroot,
            output_root=tmp_path / "catalogue",
            script_path=tmp_path / "missing.py",
        )


def test_extract_catalogue_non_json_summary_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    script_path = tmp_path / "introspect_catalogue.py"
    script_path.write_text("# fake\n", encoding="utf-8")

    monkeypatch.setattr(
        extract, "find_docker_binary", lambda explicit: Path("/usr/bin/docker")
    )
    monkeypatch.setattr(
        extract,
        "run_in_container",
        lambda **_kwargs: subprocess.CompletedProcess(
            [], 0, stdout="not json", stderr=""
        ),
    )

    with pytest.raises(CatalogueExtractionError, match="non-JSON"):
        extract.extract_catalogue(
            detected=_sample_detected(),
            workroot=workroot,
            output_root=tmp_path / "catalogue",
            script_path=script_path,
        )


def test_build_extraction_command_contains_arguments() -> None:
    command = extract.build_extraction_command(
        image_digest="sha256:abc", catalogue_hash="sha256:def", aster_version="17.4.0"
    )
    assert "--image-digest sha256:abc" in command
    assert "--catalogue-hash sha256:def" in command
    assert "--aster-version 17.4.0" in command
    assert "--output-dir /work/out" in command
    assert "introspect_catalogue.py" in command
