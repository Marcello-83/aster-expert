"""`aster-expert projet creer <nom>` (lot 44, étape 3)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.connaissances.rex import load_registry, render_report, review_project
from aster_expert.projet.check import check_project
from aster_expert.projet.context import load_project
from aster_expert.projet.creation import add_execution_roots, create_project
from aster_expert.projet.errors import ProjectError

_ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime.fromisoformat("2026-10-02T10:00:00-04:00")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal copy of the repository: configuration and knowledge base."""
    shutil.copytree(_ROOT / "connaissances", tmp_path / "connaissances")
    (tmp_path / "config").mkdir()
    shutil.copy(_ROOT / "config" / "validation.yaml", tmp_path / "config")
    (tmp_path / "projets").mkdir()
    return tmp_path


def test_create_project_writes_tree_declaration_roots_and_registry(repo: Path) -> None:
    before = (repo / "config" / "validation.yaml").read_text(encoding="utf-8")
    created = create_project(repo, "essai_lot44", now=_NOW)
    project = repo / "projets" / "essai_lot44"
    for sub in (
        "fiche",
        "donnees/sources",
        "maillage",
        "scripts",
        "tests",
        "references/cas",
    ):
        assert (project / sub).is_dir()
    ctx = load_project("essai_lot44", repo)
    assert ctx.declaration.structure == "ESSAI-LOT44"
    assert ctx.sheet().project_name == "ESSAI-LOT44"
    # Ce qui manque est dit, rien d'autre : invariants du maillage à écrire.
    problems = check_project(ctx)
    assert problems
    assert all("invariants" in p for p in problems), problems
    after = (repo / "config" / "validation.yaml").read_text(encoding="utf-8")
    assert after.startswith(before.split("  work_dir_root:")[0].rstrip("\n"))
    roots = yaml.safe_load(after)["execution"]["allowed_roots"]
    assert "projets/essai_lot44/resultats" in roots
    assert "projets/essai_lot44/references/cas" in roots
    assert created.roots_added == (
        "projets/essai_lot44/resultats",
        "projets/essai_lot44/references/cas",
    )
    assert "# Lot 41 : résultats des projets" in after  # commentaires conservés
    assert load_registry(repo, "essai_lot44").case_roots == ("projets/essai_lot44",)


def test_new_project_passes_rex_without_error(repo: Path) -> None:
    create_project(repo, "essai_lot44", now=_NOW)
    (repo / "data" / "processed" / "runs").mkdir(parents=True)
    report = review_project(repo, "essai_lot44")
    assert not report.blocking
    assert report.archives_present
    assert render_report(report)


def test_creation_never_overwrites(repo: Path) -> None:
    create_project(repo, "essai_lot44", now=_NOW)
    with pytest.raises(ProjectError, match="existe déjà"):
        create_project(repo, "essai_lot44", now=_NOW)
    with pytest.raises(ProjectError, match="refusé"):
        create_project(repo, "Essai-44", now=_NOW)


def test_execution_roots_are_added_once(repo: Path) -> None:
    roots = ("projets/x/resultats",)
    assert add_execution_roots(repo, roots, "x") == roots
    assert add_execution_roots(repo, roots, "x") == ()


def test_cli_projet_creer(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(repo))
    result = CliRunner().invoke(app, ["projet", "creer", "essai_cli"])
    assert result.exit_code == 0, result.output
    assert "Registre rex : connaissances/rex/essai_cli.yaml" in result.output
    again = CliRunner().invoke(app, ["projet", "creer", "essai_cli"])
    assert again.exit_code == 1
