"""Resources the real tests need, and why they are missing (lot 41 ter).

The real tests are split in two markers: `lent_aster` (Docker and the Code_Aster
image, plus the extracted catalogue the execution resolves its version from)
and `lent_salome` (the Salome runtime and image, plus Docker for `mesh check`).
Each function returns `None` when the resource is usable, otherwise a reason
written for the user, which `tests/conftest.py` turns into a skip message. In a
cloud session `lent_salome` is skipped by design: the Salome image is a local
file of several GB, on no registry.

External calls go through an injectable runner and `which`, as in
`aster_expert.environnement.verification`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aster_expert.environnement.verification import (
    EnvCheckError,
    Runner,
    Which,
    default_runner,
    read_expected_image,
)


def _call(runner: Runner, argv: list[str], timeout: int) -> str | None:
    """None when `argv` succeeds, else the reason it did not."""
    try:
        result = runner(argv, timeout)
    except subprocess.TimeoutExpired:
        return f"`{' '.join(argv)}` sans réponse après {timeout} s"
    except OSError as exc:
        return f"`{' '.join(argv)}` ne se lance pas : {exc}"
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        return f"`{' '.join(argv)}` échoue : {lines[0] if lines else result.returncode}"
    return None


def aster_unavailable(
    project_root: Path,
    *,
    runner: Runner = default_runner,
    which: Which = shutil.which,
) -> str | None:
    """Why Code_Aster cannot be run here, or None.

    Docker answering, the image of `config/versions.yaml` present by digest, and
    its catalogue extracted (`data/processed/catalogue/<digest>`).
    """
    docker = which("docker")
    if docker is None:
        return "docker absent du PATH"
    reason = _call(runner, [docker, "info", "--format", "{{.ServerVersion}}"], 30)
    if reason is not None:
        return f"démon Docker injoignable : {reason}"
    try:
        repository, digest = read_expected_image(project_root)
    except EnvCheckError as exc:
        return str(exc)
    reference = f"{repository}@{digest}"
    if _call(runner, [docker, "image", "inspect", reference], 30) is not None:
        return (
            f"image {reference} absente (profil cloud : `scripts/cloud_setup.sh` "
            "la tire par son digest)"
        )
    catalogue = project_root / "data" / "processed" / "catalogue" / digest
    if not catalogue.is_dir():
        return f"catalogue non extrait : {catalogue} (`aster-expert catalogue extract`)"
    return None


def salome_unavailable(
    project_root: Path,
    *,
    runner: Runner = default_runner,
    which: Which = shutil.which,
) -> str | None:
    """Why Salome cannot be run here, or None.

    The runtime of `mesh.salome.runtime` in `PATH` and the image file of
    `mesh.salome.image_path`; `mesh check` then needs Code_Aster's image
    (`medcoupling`), checked by `aster_unavailable`.
    """
    from aster_expert.meshing.config import load_mesh_config
    from aster_expert.meshing.errors import MeshConfigError

    try:
        config = load_mesh_config(project_root / "config" / "validation.yaml")
    except MeshConfigError as exc:
        return str(exc)
    salome = config.salome
    if which(salome.runtime) is None:
        return (
            f"{salome.runtime} absent du PATH (Salomé n'existe que dans la VM : "
            "image locale, sur aucun registre)"
        )
    image = Path(salome.image_path).expanduser()
    if not image.is_file():
        return f"image Salomé absente : {image}"
    reason = aster_unavailable(project_root, runner=runner, which=which)
    if reason is not None:
        return f"mesh check impossible : {reason}"
    return None


__all__: list[str] = ["aster_unavailable", "salome_unavailable"]
