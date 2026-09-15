"""Unit tests for `aster-expert env detect` orchestration. No Docker, no network."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from aster_expert.execution import detect
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import (
    AsterPythonInfo,
    CatalogueInfo,
    CodeAsterPackageInfo,
    ContainerInfo,
    DetectedEnvironment,
    InvocationInfo,
    ResolvedImage,
    RunAsterInfo,
)

FAKE_PROBE_JSON = {
    "run_aster": {
        "path_in_container": "/opt/.../bin/run_aster",
        "version_raw": "code_aster 17.4.0 (spack-local)",
    },
    "aster_python": {
        "interpreter_path_in_container": "/opt/.../bin/python3",
        "pythonpath_extra": ["/opt/.../site-packages"],
    },
    "code_aster_package": {"path_in_container": "/opt/.../code_aster"},
    "catalogue": {
        "path_in_container": "/opt/.../code_aster/Cata",
        "fingerprint_sha256": "abc123",
    },
}


def _fake_resolve_image(**_kwargs: object) -> ResolvedImage:
    return ResolvedImage(
        repository="simvia/code_aster",
        tag="17.4.0",
        digest="sha256:d8d19ea9",
        image_id="sha256:6a66bdaf",
        cave_pin_source="global",
    )


def _patch_common(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        detect, "find_docker_binary", lambda explicit: Path("/usr/bin/docker")
    )
    monkeypatch.setattr(
        detect,
        "docker_version_raw",
        lambda docker_bin, timeout=30: "Docker version 29.1.3",
    )
    monkeypatch.setattr(detect, "resolve_image", _fake_resolve_image)


def test_detect_environment_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    probe_script = tmp_path / "detect_environment.py"
    probe_script.write_text("# fake probe\n", encoding="utf-8")

    _patch_common(monkeypatch)
    captured: dict[str, Path] = {}

    def fake_run_in_container(
        *,
        docker_bin: Path,
        image_ref: str,
        workdir: Path,
        command: str,
        mount_target: str,
        network: str,
        memory: str | None,
        cpus: str | None,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        captured["workdir"] = workdir
        assert image_ref == "simvia/code_aster@sha256:d8d19ea9"
        assert (workdir / "detect_environment.py").is_file()
        return subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(FAKE_PROBE_JSON), stderr=""
        )

    monkeypatch.setattr(detect, "run_in_container", fake_run_in_container)

    result = detect.detect_environment(
        workroot=workroot,
        image_repository="simvia/code_aster",
        image_ref_env="17.4.0",
        probe_script=probe_script,
    )

    assert result.install_kind == "container_docker"
    assert result.container.image_digest == "sha256:d8d19ea9"
    assert result.container.image_tag == "17.4.0"
    assert result.run_aster.version_raw == "code_aster 17.4.0 (spack-local)"
    assert result.catalogue.fingerprint_sha256 == "abc123"
    assert result.aster_python.pythonpath_extra == ("/opt/.../site-packages",)
    # the dedicated work directory is cleaned up afterwards
    assert not captured["workdir"].exists()


def test_detect_environment_missing_workroot(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentDetectionError, match="ASTER_CONTAINER_WORKROOT"):
        detect.detect_environment(
            workroot=tmp_path / "missing",
            image_repository="simvia/code_aster",
            image_ref_env="17.4.0",
        )


def test_detect_environment_missing_probe_script(tmp_path: Path) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    with pytest.raises(EnvironmentDetectionError, match="probe script not found"):
        detect.detect_environment(
            workroot=workroot,
            image_repository="simvia/code_aster",
            image_ref_env="17.4.0",
            probe_script=tmp_path / "missing.py",
        )


def test_detect_environment_probe_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    probe_script = tmp_path / "detect_environment.py"
    probe_script.write_text("# fake probe\n", encoding="utf-8")

    _patch_common(monkeypatch)
    monkeypatch.setattr(
        detect,
        "run_in_container",
        lambda **_kwargs: subprocess.CompletedProcess(
            [], 3, stdout="", stderr="run_aster not found"
        ),
    )

    with pytest.raises(EnvironmentDetectionError, match="run_aster not found"):
        detect.detect_environment(
            workroot=workroot,
            image_repository="simvia/code_aster",
            image_ref_env="17.4.0",
            probe_script=probe_script,
        )


def test_detect_environment_non_json_probe_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    probe_script = tmp_path / "detect_environment.py"
    probe_script.write_text("# fake probe\n", encoding="utf-8")

    _patch_common(monkeypatch)
    monkeypatch.setattr(
        detect,
        "run_in_container",
        lambda **_kwargs: subprocess.CompletedProcess(
            [], 0, stdout="not json", stderr=""
        ),
    )

    with pytest.raises(EnvironmentDetectionError, match="non-JSON"):
        detect.detect_environment(
            workroot=workroot,
            image_repository="simvia/code_aster",
            image_ref_env="17.4.0",
            probe_script=probe_script,
        )


SAMPLE_VERSIONS_YAML = """# Versions Code_Aster.
#
# Header comment block, must survive untouched.

schema_version: 2

target: null

detected:
  detected_at: null
  install_kind: null
  container:
    engine: null

# Correspondance déclarée entre version de code et révisions des dépôts.
versions: []
# trailing comment block, must survive untouched.

policy:
  cross_version_results: warn
  missing_target: fail
"""


def _sample_detected_environment() -> DetectedEnvironment:
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
            path_in_container="/opt/.../bin/run_aster",
            version_raw="code_aster 17.4.0 (spack-local)",
        ),
        aster_python=AsterPythonInfo(
            interpreter_path_in_container="/opt/.../bin/python3",
            pythonpath_extra=("/opt/.../site-packages",),
        ),
        code_aster_package=CodeAsterPackageInfo(
            path_in_container="/opt/.../code_aster"
        ),
        catalogue=CatalogueInfo(
            path_in_container="/opt/.../code_aster/Cata",
            fingerprint_sha256="abc123",
        ),
        invocation=InvocationInfo(
            mechanism="profile_sh_plus_view",
            mount_pattern="<workdir>:/work",
        ),
    )


def test_write_detected_section_preserves_surroundings(tmp_path: Path) -> None:
    path = tmp_path / "versions.yaml"
    path.write_text(SAMPLE_VERSIONS_YAML, encoding="utf-8")

    detect.write_detected_section(path, _sample_detected_environment())

    new_text = path.read_text(encoding="utf-8")
    assert "Header comment block, must survive untouched." in new_text
    assert "trailing comment block, must survive untouched." in new_text
    assert "versions: []" in new_text
    assert "missing_target: fail" in new_text

    data = yaml.safe_load(new_text)
    assert data["schema_version"] == 2
    assert data["target"] is None
    assert data["detected"]["install_kind"] == "container_docker"
    assert data["detected"]["container"]["image_digest"] == "sha256:d8d19ea9"
    assert data["detected"]["catalogue"]["fingerprint_sha256"] == "abc123"
    assert data["policy"]["cross_version_results"] == "warn"


def test_write_detected_section_missing_block(tmp_path: Path) -> None:
    path = tmp_path / "versions.yaml"
    path.write_text("schema_version: 2\ntarget: null\n", encoding="utf-8")

    with pytest.raises(
        EnvironmentDetectionError, match="'detected:' section not found"
    ):
        detect.write_detected_section(path, _sample_detected_environment())


def test_build_probe_command_contains_expected_steps() -> None:
    command = detect.build_probe_command()
    assert "RUNASTER_ROOT" in command
    assert "share/aster/profile.sh" in command
    assert "python3 /work/detect_environment.py" in command
    assert "readlink -f" in command
    # P2 (lot 4): `set -u` is on for the whole probe, only lifted around
    # sourcing the upstream, non-nounset-safe `profile.sh`.
    source_line = 'source "$PREFIX/share/aster/profile.sh"'
    assert source_line in command
    assert command.strip().startswith("set -u")
    assert "set +u\n" in command
    lifted_index = command.index("set +u")
    source_index = command.index(source_line)
    restored_index = command.index("set -u", source_index)
    assert lifted_index < source_index < restored_index
    # P3 (lot 4): the Spack view root is derived from the resolved prefix by
    # walking up its ancestry, never a hardcoded path.
    assert "SPACK_ROOT" in command
    assert 'CANDIDATE=$(dirname "$CANDIDATE")' in command
    assert "/opt/spack" not in command
