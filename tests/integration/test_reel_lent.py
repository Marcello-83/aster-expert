"""Tests d'intégration réels (lot 41, étape 5.2) : Code_Aster et Salomé lancés pour
de bon, hors de la série par défaut.

Lancer : `pytest -m lent` (environ deux minutes : conteneur Code_Aster, image
Singularity de Salomé-Méca). La série par défaut les écarte (`-m "not lent"` dans
`pyproject.toml`) : aucun test unitaire n'exige Docker ni Salomé.

Cas utilisés : des cas d'essai déjà versionnés et qualifiés, jamais écrits pour ce
test -- `data/examples/lot22_essais/essai_c/c.comm` (plaque sur ressorts nodaux,
DZ = 1e-3 m imprimé, lot 22), `data/examples/lot39_essais/fiss/fiss.comm` (arrêt
attendu `<F> <CALCULEL7_40>`, lot 39) et la géométrie 1 du lot 26 (plaque avec
raidisseur, `scripts/salome/lot26_plaque_raidisseur.py`, 25 nœuds). Les
répertoires de travail sont dans `tmp_path` : rien n'est écrit dans le dépôt.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from aster_expert.constats.rejeu import value_printed
from aster_expert.execution.compte_rendu import REPORT_JSON, REPORT_MD, load_record
from aster_expert.execution.config import load_execution_config
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.execution.execute import execute_comm_file
from aster_expert.meshing.check import check_med
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.run import run_salome_script
from aster_expert.validation.validate import resolve_digest_for_version

pytestmark = pytest.mark.lent

_ROOT = Path(__file__).resolve().parents[2]
_LOT22 = _ROOT / "data" / "examples" / "lot22_essais"
_LOT39 = _ROOT / "data" / "examples" / "lot39_essais"
_LOT26 = _ROOT / "data" / "examples" / "lot26_essais" / "plaque_raidisseur"


def _aster() -> tuple[str, str]:
    return resolve_digest_for_version(
        _ROOT / "data" / "processed" / "catalogue",
        None,
        _ROOT / "config" / "versions.yaml",
    )


def _run(comm: Path, allowed: Path, tmp_path: Path):  # type: ignore[no-untyped-def]
    base = load_execution_config(_ROOT / "config" / "validation.yaml")
    config = base.model_copy(
        update={
            "allowed_roots": [str(allowed)],
            "work_dir_root": str(tmp_path / "runs"),
            "keep_work_dir": True,
        }
    )
    digest, version = _aster()
    return execute_comm_file(
        comm,
        project_root=_ROOT,
        config=config,
        docker_bin=find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None),
        image_repository=os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster"),
        image_digest=digest,
        aster_version=version,
        timeout_seconds=300,
        memory_mb=2048,
    )


def test_code_aster_runs_a_versioned_case_and_writes_its_report(
    tmp_path: Path,
) -> None:
    report = _run(_LOT22 / "essai_c" / "c.comm", _LOT22, tmp_path)

    assert report.status == "completed_ok", report
    assert report.messages_source == "run_aster.error_messages"
    assert not [m for m in report.messages if m.kind == "<F>"]
    work_dir = Path(report.work_dir)
    assert (work_dir / REPORT_JSON).is_file()
    assert (
        (work_dir / REPORT_MD)
        .read_text(encoding="utf-8")
        .startswith("# Compte rendu d'exécution")
    )
    record = load_record(work_dir)
    assert set(record.inputs_sha256) == {"c.comm", "c.export", "c.mail"}
    assert record.report.duration_s is not None
    assert report.mess_path is not None
    mess = Path(report.mess_path).read_text(encoding="utf-8", errors="replace")
    # la valeur de la source d'exécution du lot 22 (DZ = 1e-3 m), critère du rejeu
    assert value_printed(mess, 0.001)


def test_a_fatal_error_is_reported_with_its_identifier(tmp_path: Path) -> None:
    report = _run(_LOT39 / "fiss" / "fiss.comm", _LOT39, tmp_path)

    assert report.status == "failed"
    record = load_record(Path(report.work_dir))
    fatal = [m for m in record.errors if m.kind == "<F>"]
    assert [m.identifier for m in fatal] == ["CALCULEL7_40"]
    assert "POUTRE" in fatal[0].text
    markdown = (Path(report.work_dir) / REPORT_MD).read_text(encoding="utf-8")
    assert "CALCULEL7_40" in markdown


def test_salome_meshes_a_minimal_geometry_and_mesh_check_holds(
    tmp_path: Path,
) -> None:
    config = load_mesh_config(_ROOT / "config" / "validation.yaml")
    if shutil.which(config.salome.runtime) is None:
        pytest.skip(f"{config.salome.runtime} absent")
    params = tmp_path / "params.json"
    shutil.copyfile(_LOT26 / "params.json", params)
    # Racine de travail propre au test : jamais le cache de maillage du dépôt.
    run = run_salome_script(
        _ROOT / "scripts" / "salome" / "lot26_plaque_raidisseur.py",
        project_root=tmp_path,
        config=config,
        params=params,
    )
    assert not run.from_cache
    assert Path(run.med_path).is_file()

    digest, _ = _aster()
    report = check_med(
        Path(run.med_path),
        _LOT26 / "invariants.yaml",
        project_root=tmp_path,
        config=config,
        docker_bin=find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None),
        image_ref=f"simvia/code_aster@{digest}",
    )
    assert report.ok, [r for r in report.results if not r.ok]
    assert len(report.results) > 10
