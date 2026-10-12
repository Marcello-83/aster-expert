"""État du projet lisible par la machine (lot 46, étape 3)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

from aster_expert import etat

_REPO = Path(__file__).resolve().parents[2]


def test_etat_valide_au_schema() -> None:
    state = etat.load_state(_REPO)
    assert state.lots[-1].id == state.mis_a_jour_au_lot
    assert {p.nom for p in state.projets} == {
        "quai_cw_test_01",
        "dalle_appuyee_01",
        "estacade_pieux_01",  # lot 47
        "pontons_alu_01",  # lot 50
    }
    for nom in (
        "recherche",
        "catalogue",
        "analyse",
        "validation_b",
        "execution_c",
        "controles_d",
        "reference_e",
        "ferraillage",
        "notes",
    ):
        assert nom in {c.nom for c in state.capacites}


def test_readme_genere_depuis_etat_yaml() -> None:
    assert etat.check_readme(_REPO) == []


def test_readme_diverge_si_le_fichier_d_etat_change(tmp_path: Path) -> None:
    for name in ("README.md",):
        (tmp_path / name).write_text((_REPO / name).read_text("utf-8"), "utf-8")
    (tmp_path / "docs").mkdir()
    raw = yaml.safe_load((_REPO / "docs" / "etat.yaml").read_text("utf-8"))
    raw["capacites"][0]["limites"] = "autre limite"
    (tmp_path / "docs" / "etat.yaml").write_text(
        yaml.safe_dump(raw, allow_unicode=True), "utf-8"
    )
    assert "diverge" in etat.check_readme(tmp_path)[0]
    assert etat.update_readme(tmp_path) is True
    assert etat.check_readme(tmp_path) == []


def test_readme_sans_marqueurs_refuse(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "etat.yaml").write_text(
        (_REPO / "docs" / "etat.yaml").read_text("utf-8"), "utf-8"
    )
    (tmp_path / "README.md").write_text("# Sans marqueurs\n", "utf-8")
    with pytest.raises(etat.StateError, match="marqueurs"):
        etat.check_readme(tmp_path)


def test_fichiers_et_commits_cites_existent() -> None:
    assert etat.check_references(_REPO) == []


def test_commit_inconnu_signale(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    raw = yaml.safe_load((_REPO / "docs" / "etat.yaml").read_text("utf-8"))
    raw["lots"][-1]["commit"] = "deadbee"
    raw["capacites"] = []
    raw["projets"] = []
    raw["metriques"] = []
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "etat.yaml").write_text(
        yaml.safe_dump(raw, allow_unicode=True), "utf-8"
    )
    problems = etat.check_references(tmp_path)
    if not any("deadbee" in p for p in problems):
        pytest.skip("dépôt sans historique exploitable")
    assert any("commit deadbee inconnu" in p for p in problems)


def test_requires_python_aligne_sur_la_decision_du_lot_41bis() -> None:
    meta = tomllib.loads((_REPO / "pyproject.toml").read_text("utf-8"))
    assert meta["project"]["requires-python"] == ">=3.12,<3.13"
    pin = (_REPO / ".python-version").read_text("utf-8").strip()
    assert re.fullmatch(r"3\.12(\.\d+)?", pin)


def test_journal_du_plan_renvoie_a_l_etat() -> None:
    plan = (_REPO / "docs" / "development-plan.md").read_text("utf-8")
    assert "docs/etat.yaml" in plan
    assert "| Lot | Branche | État |" not in plan
