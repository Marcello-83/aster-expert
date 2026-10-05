"""Manifeste de l'archive d'exécution et refus de `rex` (lot 46, étape 4)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.connaissances.archive import (
    archive_problem,
    build_manifest,
    conformity_problem,
    digest,
)
from aster_expert.connaissances.rex import (
    RexRegistry,
    load_registry,
    record_manifest,
    render_report,
    review_project,
    write_metrics,
    write_registry,
)

_IDS = [f"2026100{i}T090000-aaaa000{i}" for i in range(1, 6)]


def _depot(tmp_path: Path, ids: list[str] = _IDS) -> Path:
    root = tmp_path / "depot"
    for layer in (
        "constats_code_aster",
        "diagnostics",
        "patrons",
        "controles",
        "references_validation",
        "precedents",
    ):
        (root / "connaissances" / layer).mkdir(parents=True)
    for run_id in ids:
        work = root / "data" / "processed" / "runs" / run_id
        work.mkdir(parents=True)
        record = {
            "report": {
                "comm_path": str(root / "projets" / "p" / "cas.comm"),
                "status": "completed_ok",
                "diag": "OK",
                "duration_s": 1.0,
                "mess_path": None,
            },
            "errors": [],
        }
        (work / "compte_rendu.json").write_text(json.dumps(record), "utf-8")
    write_registry(root, RexRegistry(project="p", case_roots=("projets/p",)))
    return root


def test_digest_ignore_l_ordre_et_depend_du_contenu() -> None:
    assert digest(_IDS) == digest(list(reversed(_IDS)))
    assert digest(_IDS) != digest(_IDS[:-1])


def test_conformite_du_manifeste() -> None:
    manifest = build_manifest(_IDS)
    assert conformity_problem(_IDS, manifest) is None
    # des exécutions plus récentes s'ajoutent : toujours conforme
    assert conformity_problem([*_IDS, "20261009T000000-bbbb0000"], manifest) is None
    assert "partielle" in (conformity_problem(_IDS[2:], manifest) or "")
    autre = [*_IDS[:-1], "20261005T090000-ffff0000"]
    assert "non conforme" in (conformity_problem(autre, manifest) or "")
    assert "aucun manifeste" in (conformity_problem(_IDS, None) or "")


def test_sans_manifeste_l_archive_n_est_pas_acceptee(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    report = review_project(root, "p")
    assert not report.archives_present
    assert "aucun manifeste" in (report.archive_problem or "")
    assert archive_problem(root) is not None


def test_archive_complete_acceptee_et_miroir_ecrit(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    manifest = record_manifest(root, "p")
    assert manifest.runs == 5
    assert load_registry(root, "p").archive == manifest
    miroir = json.loads(
        (root / "data" / "processed" / "runs" / "manifeste.json").read_text("utf-8")
    )
    assert miroir["p"]["sha256"] == digest(_IDS)
    report = review_project(root, "p")
    assert report.archives_present and report.runs == 5
    assert archive_problem(root) is None


def test_archive_partielle_refusee_et_manifeste_non_ecrase(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    record_manifest(root, "p")
    # profil Cloud : une exécution fraîche seulement
    partiel = tmp_path / "cloud"
    cloud = _depot(partiel, ids=["20261010T100000-cccc0000"])
    shutil.copy(
        root / "connaissances" / "rex" / "p.yaml",
        cloud / "connaissances" / "rex" / "p.yaml",
    )
    report = review_project(cloud, "p")
    assert not report.archives_present
    assert "partielle" in (report.archive_problem or "")
    assert "Archive d'exécution refusée" in render_report(report)[1]
    with pytest.raises(ValueError, match="contredit"):
        record_manifest(cloud, "p")
    assert load_registry(cloud, "p").archive == load_registry(root, "p").archive


def test_rex_cli_ne_reecrit_que_les_champs_declares(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _depot(tmp_path)
    record_manifest(root, "p")
    complet = review_project(root, "p")
    write_metrics(root, complet.metrics)
    metriques = root / "connaissances" / "metriques" / "p.yaml"
    avant = yaml.safe_load(metriques.read_text("utf-8"))
    assert avant["measured"]["runs"] == 5

    # l'archive devient partielle (Cloud) et une intervention est déclarée
    shutil.rmtree(root / "data" / "processed" / "runs" / _IDS[0])
    registre = root / "connaissances" / "rex" / "p.yaml"
    data = yaml.safe_load(registre.read_text("utf-8"))
    data["lots"] = [
        {
            "lot": "46",
            "supervisor_interventions": {
                "value": 1.0,
                "nature": "mesure",
                "note": "déclaré",
            },
            "avoided_errors": {"value": None, "nature": "non renseigné"},
        }
    ]
    registre.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(root))
    sortie = CliRunner().invoke(app, ["rex", "p"])
    assert sortie.exit_code == 0, sortie.output
    assert "Archive d'exécution refusée" in sortie.output
    assert "Champs déclarés seuls" in sortie.output
    apres = yaml.safe_load(metriques.read_text("utf-8"))
    assert apres["measured"] == avant["measured"]
    assert apres["knowledge"] == avant["knowledge"]
    assert apres["declared_interventions_since_baseline"] == 1.0
    assert apres["lots"][0]["lot"] == "46"
    # le registre ne reçoit aucune revue
    assert load_registry(root, "p").reviews == ()
    refus = CliRunner().invoke(app, ["rex", "p", "--manifeste"])
    assert refus.exit_code == 1
    assert "contredit" in refus.output


def test_rex_sans_archive_cree_un_fichier_sans_mesure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _depot(tmp_path)
    shutil.rmtree(root / "data")
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(root))
    sortie = CliRunner().invoke(app, ["rex", "p"])
    assert sortie.exit_code == 0, sortie.output
    metriques = yaml.safe_load(
        (root / "connaissances" / "metriques" / "p.yaml").read_text("utf-8")
    )
    assert metriques["measured"] is None
