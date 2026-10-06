"""Lecture d'un MED de résultats par `medcoupling`, dans le conteneur (lot 36).

Le Python du projet n'a aucun module MED : `scripts/med_results_dump.py` s'exécute
avec `medcoupling` dans l'image Docker de `cave` (comme `mesh check`, mêmes limites :
réseau désactivé, utilisateur non root, un seul répertoire monté). Le projet ne lit
que le JSON produit.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aster_expert.execution.container_env import (
    MOUNT_TARGET,
    build_environment_setup_script,
)
from aster_expert.execution.docker_client import (
    find_docker_binary,
    kill_container,
    run_in_container,
)
from aster_expert.meshing.check import run_then_drop_copy
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.errors import MeshCheckError
from aster_expert.validation.validate import resolve_digest_for_version

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = ROOT / "scripts" / "med_results_dump.py"
_MED_NAME = "input.med"
_OUT_NAME = "out.json"
_ARRAYS_NAME = "out.npz"

ContainerRunner = Callable[..., "subprocess.CompletedProcess[str]"]


def run_med_script(
    med: Path,
    args: list[str],
    *,
    project_root: Path = ROOT,
    memory_mb: int = 6144,
    timeout_seconds: int = 1800,
    runner: ContainerRunner = run_in_container,
) -> dict[str, Any]:
    """Exécute `med_results_dump.py <med> <sortie> <args…>` dans le conteneur et
    renvoie le JSON qu'il a écrit. Le MED est copié dans le répertoire de travail
    dédié (`data/processed/mesh_checks/…`), jamais monté depuis son emplacement."""
    if not med.is_file():
        message = f"MED introuvable : {med}"
        raise MeshCheckError(message)
    config = load_mesh_config(project_root / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        project_root / "data" / "processed" / "catalogue",
        None,
        project_root / "config" / "versions.yaml",
    )
    repository = os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")
    image_ref = f"{repository}@{digest}"
    docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
    root = project_root / config.checker.work_dir_root
    root.mkdir(parents=True, exist_ok=True)
    work_dir = root / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
    work_dir.mkdir()
    shutil.copy2(med, work_dir / _MED_NAME)
    shutil.copy2(_SCRIPT, work_dir / _SCRIPT.name)
    joined = " ".join(args)
    command = (
        build_environment_setup_script()
        + f"\npython3 {MOUNT_TARGET}/{_SCRIPT.name} {MOUNT_TARGET}/{_MED_NAME} "
        f"{MOUNT_TARGET}/{_OUT_NAME} {joined}\n"
    )
    name = f"aster-expert-med-read-{uuid.uuid4().hex}"
    logger.info("lecture de %s par medcoupling dans %s", med, image_ref)
    try:
        result = run_then_drop_copy(
            runner,
            work_dir / _MED_NAME,
            docker_bin=docker_bin,
            image_ref=image_ref,
            workdir=work_dir,
            command=command,
            network="none",
            memory=f"{memory_mb}m",
            cpus=config.checker.cpus_limit,
            timeout=timeout_seconds,
            container_name=name,
        )
    except subprocess.TimeoutExpired as exc:
        kill_container(docker_bin, name)
        (work_dir / _MED_NAME).unlink(missing_ok=True)
        message = f"lecture du MED au-delà de {timeout_seconds} s"
        raise MeshCheckError(message) from exc
    if result.returncode != 0:
        message = (
            f"medcoupling n'a pas pu lire {med} (code {result.returncode}) : "
            f"{(result.stderr or result.stdout).strip()[-800:]}"
        )
        raise MeshCheckError(message)
    out = work_dir / _OUT_NAME
    if not out.is_file():
        message = f"aucune sortie du lecteur ({_OUT_NAME} absent de {work_dir})"
        raise MeshCheckError(message)
    payload: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
    payload["_work_dir"] = str(work_dir)
    return payload


def take_arrays(payload: dict[str, Any]) -> dict[str, Any]:
    """The arrays written by the reader (`out.npz`), loaded in memory, then the file
    deleted (lot 47 ter, ENV-003): an extraction is used once, by its caller."""
    import numpy as np  # noqa: PLC0415

    path = Path(payload["_work_dir"]) / _ARRAYS_NAME
    with np.load(path) as npz:
        arrays = {k: np.array(npz[k]) for k in npz.files}
    path.unlink()
    return arrays


def med_field_name(case: str, quantity: str) -> str:
    """Nom MED complet d'un champ : nom du résultat (`NOM_RESU_MED`) complété à 8
    caractères par des `_`, puis le nom du champ (`G` + `DEPL` -> `G_______DEPL`)."""
    return case.ljust(8, "_") + quantity
