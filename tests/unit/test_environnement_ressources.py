"""Tests de `aster_expert.environnement.ressources` (lot 41 ter) : motifs pour
lesquels un test réel `lent_aster` ou `lent_salome` est ignoré. Ni Docker ni
Salomé : `runner` et `which` sont factices."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aster_expert.environnement.ressources import aster_unavailable, salome_unavailable

_DIGEST = "sha256:" + "b" * 64
_MESH = """
mesh:
  work_dir_root: data/processed/mesh_runs
  salome:
    runtime: singularity
    image_path: {image}
    expected_version: V
    install_root: /opt/salome
    version_file: README
    version_pattern: 'Version\\s*:\\s*(\\S+)'
    env_scripts: []
    container_options: []
    command: "salome -t {{script}} args:{{args}}"
    timeout_seconds: 10
  checker:
    work_dir_root: data/processed/mesh_checks
    timeout_seconds: 10
    memory_mb: 512
    cpus_limit: "1"
"""


def _project(tmp_path: Path, *, catalogue: bool = True) -> Path:
    root = tmp_path / "depot"
    (root / "config").mkdir(parents=True)
    (root / "config" / "versions.yaml").write_text(
        "detected:\n  container:\n    image_repository: simvia/code_aster\n"
        f"    image_digest: {_DIGEST}\n",
        encoding="utf-8",
    )
    image = tmp_path / "salome.sif"
    image.write_bytes(b"sif")
    (root / "config" / "validation.yaml").write_text(
        _MESH.format(image=image), encoding="utf-8"
    )
    if catalogue:
        (root / "data" / "processed" / "catalogue" / _DIGEST).mkdir(parents=True)
    return root


def _runner(failing: str | None = None, error: str = "refus"):  # type: ignore[no-untyped-def]
    def run(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        code = 1 if failing is not None and failing in argv else 0
        return subprocess.CompletedProcess(argv, code, "", error if code else "")

    return run


def _which(*present: str):  # type: ignore[no-untyped-def]
    return lambda name: f"/usr/bin/{name}" if name in present else None


def test_aster_available(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert aster_unavailable(root, runner=_runner(), which=_which("docker")) is None


@pytest.mark.parametrize(
    ("which", "failing", "catalogue", "fragment"),
    [
        (("cave",), None, True, "docker absent du PATH"),
        (("docker",), "info", True, "démon Docker injoignable"),
        (("docker",), "inspect", True, f"image simvia/code_aster@{_DIGEST} absente"),
        (("docker",), None, False, "catalogue non extrait"),
    ],
)
def test_aster_unavailable_reasons(
    tmp_path: Path,
    which: tuple[str, ...],
    failing: str | None,
    catalogue: bool,
    fragment: str,
) -> None:
    root = _project(tmp_path, catalogue=catalogue)
    reason = aster_unavailable(root, runner=_runner(failing), which=_which(*which))
    assert reason is not None
    assert fragment in reason


def test_aster_unavailable_without_a_detected_image(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "config" / "versions.yaml").write_text("detected: {}\n", encoding="utf-8")
    reason = aster_unavailable(root, runner=_runner(), which=_which("docker"))
    assert reason is not None
    assert "sans dépôt ni digest" in reason


def test_salome_available_and_its_reasons(tmp_path: Path) -> None:
    root = _project(tmp_path)
    both = _which("docker", "singularity")
    assert salome_unavailable(root, runner=_runner(), which=both) is None
    reason = salome_unavailable(root, runner=_runner(), which=_which("docker"))
    assert reason is not None
    assert reason.startswith("singularity absent du PATH")
    (tmp_path / "salome.sif").unlink()
    reason = salome_unavailable(root, runner=_runner(), which=both)
    assert reason is not None
    assert reason.startswith("image Salomé absente")


def test_salome_needs_docker_for_mesh_check(tmp_path: Path) -> None:
    root = _project(tmp_path)
    reason = salome_unavailable(
        root, runner=_runner("info"), which=_which("docker", "singularity")
    )
    assert reason is not None
    assert reason.startswith("mesh check impossible : démon Docker injoignable")


def test_salome_with_an_unreadable_configuration(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / "config" / "validation.yaml").write_text("mesh: {}\n", encoding="utf-8")
    assert salome_unavailable(root, runner=_runner(), which=_which()) is not None
