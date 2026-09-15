"""Unit tests for the docker CLI wrapper. No Docker, no network."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aster_expert.execution import docker_client
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import ResolvedImage


def _completed(
    argv: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


# --- find_docker_binary -----------------------------------------------------


def test_find_docker_binary_explicit_path_exists(tmp_path: Path) -> None:
    fake_docker = tmp_path / "docker"
    fake_docker.write_text("#!/bin/sh\n", encoding="utf-8")
    assert docker_client.find_docker_binary(str(fake_docker)) == fake_docker


def test_find_docker_binary_explicit_path_missing(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentDetectionError, match="does not exist"):
        docker_client.find_docker_binary(str(tmp_path / "missing"))


def test_find_docker_binary_found_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/docker")
    assert docker_client.find_docker_binary(None) == Path("/usr/bin/docker")


def test_find_docker_binary_not_in_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(EnvironmentDetectionError, match="not found in PATH"):
        docker_client.find_docker_binary(None)


# --- docker_version_raw ------------------------------------------------------


def test_docker_version_raw_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, stdout="Docker version 29.1.3\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert (
        docker_client.docker_version_raw(Path("/usr/bin/docker"))
        == "Docker version 29.1.3"
    )


def test_docker_version_raw_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, returncode=1, stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(EnvironmentDetectionError, match="boom"):
        docker_client.docker_version_raw(Path("/usr/bin/docker"))


# --- read_cave_pin ------------------------------------------------------------


def test_read_cave_pin_directory_wins(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (directory / ".cave").write_text("17.4.0\n", encoding="utf-8")
    (home / ".cave").write_text("16.8.0\n", encoding="utf-8")

    assert docker_client.read_cave_pin(directory, home) == ("17.4.0", "directory")


def test_read_cave_pin_falls_back_to_global(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cave").write_text("17.4.0\n", encoding="utf-8")

    assert docker_client.read_cave_pin(directory, home) == ("17.4.0", "global")


def test_read_cave_pin_none_found(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    assert docker_client.read_cave_pin(directory, home) == (None, "none")


# --- resolve_image ------------------------------------------------------------


def test_resolve_image_rejects_stable_from_env(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentDetectionError, match="symbolic tag"):
        docker_client.resolve_image(
            docker_bin=Path("/usr/bin/docker"),
            repository="simvia/code_aster",
            image_ref_env="stable",
            cwd=tmp_path,
            home=tmp_path,
        )


def test_resolve_image_rejects_testing_from_cave_pin(tmp_path: Path) -> None:
    (tmp_path / ".cave").write_text("testing\n", encoding="utf-8")
    with pytest.raises(EnvironmentDetectionError, match="symbolic tag"):
        docker_client.resolve_image(
            docker_bin=Path("/usr/bin/docker"),
            repository="simvia/code_aster",
            image_ref_env=None,
            cwd=tmp_path,
            home=tmp_path,
        )


def test_resolve_image_no_source_found(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentDetectionError, match="no image reference found"):
        docker_client.resolve_image(
            docker_bin=Path("/usr/bin/docker"),
            repository="simvia/code_aster",
            image_ref_env=None,
            cwd=tmp_path,
            home=tmp_path,
        )


def test_resolve_image_success_by_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "Id": "sha256:6a66bdaf0942",
        "RepoDigests": ["simvia/code_aster@sha256:d8d19ea91989"],
        "RepoTags": ["simvia/code_aster:17.4.0", "simvia/code_aster:stable"],
    }

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    image = docker_client.resolve_image(
        docker_bin=Path("/usr/bin/docker"),
        repository="simvia/code_aster",
        image_ref_env="17.4.0",
        cwd=tmp_path,
        home=tmp_path,
    )

    assert image == ResolvedImage(
        repository="simvia/code_aster",
        tag="17.4.0",
        digest="sha256:d8d19ea91989",
        image_id="sha256:6a66bdaf0942",
        cave_pin_source="none",
    )


def test_resolve_image_missing_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"Id": "sha256:abc", "RepoDigests": [], "RepoTags": []}

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(EnvironmentDetectionError, match="no RepoDigests"):
        docker_client.resolve_image(
            docker_bin=Path("/usr/bin/docker"),
            repository="simvia/code_aster",
            image_ref_env="17.4.0",
            cwd=tmp_path,
            home=tmp_path,
        )


def test_resolve_image_by_digest_picks_concrete_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "Id": "sha256:6a66bdaf0942",
        "RepoDigests": ["simvia/code_aster@sha256:d8d19ea91989"],
        "RepoTags": ["simvia/code_aster:stable", "simvia/code_aster:17.4.0"],
    }

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, stdout=json.dumps(payload))

    monkeypatch.setattr(subprocess, "run", fake_run)

    image = docker_client.resolve_image(
        docker_bin=Path("/usr/bin/docker"),
        repository="simvia/code_aster",
        image_ref_env="sha256:d8d19ea91989",
        cwd=tmp_path,
        home=tmp_path,
    )

    assert image.tag == "17.4.0"
    assert image.digest == "sha256:d8d19ea91989"


def test_resolve_image_inspect_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(argv, returncode=1, stderr="No such object")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(EnvironmentDetectionError, match="No such object"):
        docker_client.resolve_image(
            docker_bin=Path("/usr/bin/docker"),
            repository="simvia/code_aster",
            image_ref_env="17.4.0",
            cwd=tmp_path,
            home=tmp_path,
        )


# --- run_in_container ---------------------------------------------------------


def test_run_in_container_refuses_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    with pytest.raises(EnvironmentDetectionError, match="HOME"):
        docker_client.run_in_container(
            docker_bin=Path("/usr/bin/docker"),
            image_ref="simvia/code_aster@sha256:abc",
            workdir=fake_home,
            command="echo hi",
        )


def test_run_in_container_refuses_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentDetectionError, match="does not exist"):
        docker_client.run_in_container(
            docker_bin=Path("/usr/bin/docker"),
            image_ref="simvia/code_aster@sha256:abc",
            workdir=tmp_path / "missing",
            command="echo hi",
        )


def test_run_in_container_builds_restricted_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        return _completed(argv, stdout="{}")

    monkeypatch.setattr(subprocess, "run", fake_run)

    docker_client.run_in_container(
        docker_bin=Path("/usr/bin/docker"),
        image_ref="simvia/code_aster@sha256:abc",
        workdir=workdir,
        command="echo hi",
        network="none",
        memory="512m",
        cpus="1",
    )

    argv = captured["argv"]
    assert argv[:3] == ["/usr/bin/docker", "run", "--rm"]
    assert "--network=none" in argv
    assert "--memory=512m" in argv
    assert "--cpus=1" in argv
    assert f"{workdir.resolve()}:/work" in argv
    assert "-w" in argv and "/work" in argv
    assert argv[-4:] == ["simvia/code_aster@sha256:abc", "/bin/bash", "-c", "echo hi"]
    # non-root by default
    user_index = argv.index("--user")
    assert ":" in argv[user_index + 1]
