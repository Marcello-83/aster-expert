"""Déclaration d'un projet et refus lisibles (lot 41, étapes 2.3 et 3).

Chaque refus est une `ProjectError` dont le message nomme le problème en français
(donnée manquante, groupe absent du maillage, cas sans résultante attendue,
données d'un autre ouvrage) ; en ligne de commande, `generate`, `report`,
`mesh check` et `projet` l'affichent (`<commande> ÉCHEC : ...`) et sortent en code 1,
jamais par une trace Python.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.projet.check import check_project, require_valid_project
from aster_expert.projet.context import (
    available_projects,
    load_project,
    resolve_project_dir,
)
from aster_expert.projet.declaration import DataRef, load_declaration
from aster_expert.projet.errors import ProjectError

_ROOT = Path(__file__).resolve().parents[2]
_DALLE = (
    _ROOT / "docs" / "audit" / "annexes_lot40" / "essai_dalle" / "dalle_donnees.yaml"
)

Factory = Callable[..., Any]
"""`tests/conftest.py`, `fake_project` : rend un `FakeProject`."""


def test_a_complete_fake_project_is_accepted(fake_project: Factory) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)

    assert check_project(ctx) == []
    assert ctx.number(DataRef(data="geometrie.longueur"), unit="m") == 2.0
    assert ctx.number(1.5) == 1.5
    assert available_projects(project.repo_root) == [project.name]


def test_the_quay_declaration_is_accepted() -> None:
    ctx = load_project("quai_cw_test_01", _ROOT)

    assert check_project(ctx) == []
    assert ctx.declaration.structure == "QUAI-CW-TEST-01"


def test_a_missing_field_is_named(tmp_path: Path) -> None:
    path = tmp_path / "projet.yaml"
    path.write_text(yaml.safe_dump({"schema_version": 1, "name": "x"}), "utf-8")

    with pytest.raises(ProjectError) as exc:
        load_declaration(path)

    text = str(exc.value)
    assert "déclaration incomplète ou incohérente" in text
    assert "champ manquant : structure" in text
    assert "champ manquant : comm" in text


def test_an_unknown_field_and_a_bad_extension_are_named(
    fake_project: Factory,
) -> None:
    project = fake_project(inconnu=1)
    with pytest.raises(ProjectError, match="champ inconnu : inconnu"):
        load_project(project.name, project.repo_root)

    project = fake_project(
        comm={"generator": "pas une extension", "output": "resultats/x.comm"}
    )
    with pytest.raises(ProjectError, match="module:fonction"):
        load_project(project.name, project.repo_root)


def test_generator_and_file_are_exclusive(fake_project: Factory) -> None:
    project = fake_project(comm={"output": "resultats/x.comm"})
    with pytest.raises(ProjectError, match="exactement un de `generator` ou `file`"):
        load_project(project.name, project.repo_root)


def test_unreadable_or_empty_declarations_are_refused(tmp_path: Path) -> None:
    missing = tmp_path / "projet.yaml"
    with pytest.raises(ProjectError, match="introuvable"):
        load_declaration(missing)
    missing.write_text("a: [", encoding="utf-8")
    with pytest.raises(ProjectError, match="illisible"):
        load_declaration(missing)
    missing.write_text("", encoding="utf-8")
    with pytest.raises(ProjectError, match="vide"):
        load_declaration(missing)


def test_an_unknown_project_lists_the_declared_ones(fake_project: Factory) -> None:
    project = fake_project()
    with pytest.raises(ProjectError) as exc:
        resolve_project_dir("inexistant", project.repo_root)
    assert "projet introuvable : inexistant" in str(exc.value)
    assert project.name in str(exc.value)
    assert resolve_project_dir(str(project.declaration_path), project.repo_root) == (
        project.directory.resolve()
    )


def test_the_name_must_be_the_directory(fake_project: Factory) -> None:
    project = fake_project(name="autre_nom")
    with pytest.raises(ProjectError, match="diffère du répertoire"):
        load_project(project.name, project.repo_root)


def test_an_extension_outside_the_project_package_is_refused(
    fake_project: Factory,
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    with pytest.raises(ProjectError, match="appartenir au paquet du projet"):
        ctx.extension("os:system")
    with pytest.raises(ProjectError, match="module introuvable"):
        ctx.extension(f"{project.name}.absent:f")
    with pytest.raises(ProjectError, match="pas de fonction"):
        ctx.extension(f"{project.name}.extensions:absente")


def test_a_data_value_with_an_unexpected_unit_is_refused(fake_project: Factory) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    with pytest.raises(ProjectError, match="unité 'm', 'mm' attendue"):
        ctx.number(DataRef(data="geometrie.longueur"), unit="mm")
    with pytest.raises(ProjectError, match="donnée manquante : geometrie.absente"):
        ctx.number(DataRef(data="geometrie.absente"))


# --- refus de l'étape 3 ------------------------------------------------------------


def test_a_group_absent_from_the_mesh_is_refused(fake_project: Factory) -> None:
    project = fake_project()
    data = project.declaration()
    data["controls"]["supports"].append(
        {"group": "ENCASTREMENT", "blocked": ["DX"], "table": "REAC_ENC_{case}"}
    )
    project.write_declaration(data)
    ctx = load_project(project.name, project.repo_root)

    problems = check_project(ctx)

    assert problems == [
        "groupe absent du maillage : ENCASTREMENT (groupe d'appui, absent des "
        "invariants invariants.yaml)"
    ]


def test_a_load_case_without_expected_resultant_is_refused(
    fake_project: Factory,
) -> None:
    project = fake_project()
    data = project.declaration()
    data["controls"]["cases"].append({"name": "V"})
    project.write_declaration(data)
    ctx = load_project(project.name, project.repo_root)

    with pytest.raises(ProjectError) as exc:
        require_valid_project(ctx)

    assert "cas de charge sans résultante attendue : V" in str(exc.value)


def test_a_missing_data_value_is_named(fake_project: Factory) -> None:
    project = fake_project()
    data = project.declaration()
    data["comm"]["required_data"] = ["geometrie.longueur", "tube.rayon"]
    project.write_declaration(data)
    ctx = load_project(project.name, project.repo_root)

    assert check_project(ctx) == [
        "donnée manquante : tube.rayon (exigée par le générateur, absente de "
        "donnees.yaml)"
    ]


def test_the_audit_slab_data_is_refused_by_the_quay_project() -> None:
    """Lot 40, § 5.3 : des données de dalle passées au générateur du quai
    s'arrêtaient sur une trace Python réclamant le rayon d'un tube. Désormais : un
    refus lisible, avant d'appeler le générateur, qui dit que les données sont
    celles d'un autre ouvrage et quelles données manquent."""
    ctx = load_project("quai_cw_test_01", _ROOT, data=_DALLE)

    problems = check_project(ctx)

    assert problems[0] == (
        "les données dalle_donnees.yaml sont celles de l'ouvrage 'DALLE-AUDIT-40', "
        "la déclaration admet 'QUAI-CW-TEST-01', 'QUAI-CW-TEST-01-LOT30-REDUIT', "
        "'QUAI-CW-TEST-01-LOT37-REDUIT-FIN'"
    )
    assert (
        "donnée manquante : tube.rayon (exigée par le générateur, absente de "
        "dalle_donnees.yaml)"
    ) in problems


def test_generate_refuses_the_slab_data_readably() -> None:
    result = CliRunner().invoke(
        app, ["generate", "quai_cw_test_01", "--donnees", str(_DALLE)]
    )

    assert result.exit_code == 1
    assert "generate ÉCHEC : projet quai_cw_test_01 : déclaration refusée" in (
        result.output
    )
    assert "tube.rayon" in result.output
    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_report_refuses_the_slab_data_readably(
    tmp_path: Path, lecture_sous_tmp: Path
) -> None:
    result = CliRunner().invoke(
        app,
        [
            "report",
            str(tmp_path),
            "--projet",
            "quai_cw_test_01",
            "--donnees",
            str(_DALLE),
        ],
    )

    assert result.exit_code == 1
    assert "report ÉCHEC" in result.output
    assert "DALLE-AUDIT-40" in result.output
    assert "Traceback" not in result.output


def test_projet_refuses_an_unknown_project_and_an_unknown_step(
    fake_project: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = fake_project()
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(project.repo_root))

    result = CliRunner().invoke(app, ["projet", "inexistant"])
    assert result.exit_code == 1
    assert "projet ÉCHEC : projet introuvable : inexistant" in result.output

    result = CliRunner().invoke(app, ["projet", project.name, "cuisiner"])
    assert result.exit_code == 1
    assert "étape inconnue : cuisiner" in result.output


def test_mesh_check_refuses_an_incoherent_invariants_file(
    tmp_path: Path, lecture_sous_tmp: Path
) -> None:
    invariants = tmp_path / "invariants.yaml"
    invariants.write_text(
        yaml.safe_dump({"schema_version": 1, "groups": [{"nom": "X"}]}), "utf-8"
    )
    med = tmp_path / "m.med"
    med.write_bytes(b"x")

    result = CliRunner().invoke(app, ["mesh", "check", str(med), str(invariants)])

    assert result.exit_code == 1
    assert "mesh check ÉCHEC : fichier d'invariants incohérent" in result.output
    assert "champ manquant : groups.0.name" in result.output
    assert "champ inconnu : groups.0.nom" in result.output
    assert "Traceback" not in result.output


def test_mesh_check_without_arguments_says_what_to_give() -> None:
    result = CliRunner().invoke(app, ["mesh", "check"])

    assert result.exit_code == 1
    assert "donner le MED et le fichier d'invariants" in result.output
