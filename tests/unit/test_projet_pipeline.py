"""`aster-expert projet <nom> <étape>` (lot 41, étape 2.5) sur le projet factice :
chaque étape, l'état qu'elle laisse (`etat.json`), et ses refus. Le conteneur et
Salomé sont simulés (les fonctions qu'appellent les étapes sont remplacées) ; la
chaîne réelle du quai est rejouée au lot 41 (docs/essais_lot41.md, étape 7)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import aster_expert.execution.execute as execute_module
import aster_expert.meshing.check as check_module
import aster_expert.validation.validate as validate_module
from aster_expert.cli import app
from aster_expert.execution.models import ExecutionMessage, ExecutionReport
from aster_expert.meshing.check import MeshCheckReport
from aster_expert.meshing.invariants import InvariantResult
from aster_expert.projet.context import load_project
from aster_expert.projet.errors import ProjectError
from aster_expert.projet.pipeline import (
    Runtime,
    display_path,
    generate,
    load_state,
    run_step,
)
from aster_expert.validation.models import ValidationReport

Factory = Callable[..., Any]
_DIGEST = "sha256:" + "d" * 64


def _mess() -> str:
    def table(title: str, dz: float) -> str:
        return (
            "##ASTER 17.04.00\nINTITULE RESULTAT DX DY DZ\n"
            f"{title} RESU 0.000000000000E+00 0.000000000000E+00 {dz:.12E}\n\n"
        )

    sym = (
        (
            "##ASTER 17.04.00\nINTITULE NOEUD COOR_X COOR_Y COOR_Z DX DY DZ\n"
            "SYMETRIE_{c} N1 0.0E+00 0.0E+00 0.0E+00 1.0E-03 0.0E+00 0.0E+00\n"
            "SYMETRIE_{c} N2 2.000000000000E+00 0.0E+00 0.0E+00 -1.0E-03 0.0E+00 "
            "0.0E+00\n\n"
        )
        .replace("0.0E+00", "0.000000000000E+00")
        .replace("1.0E-03", "1.000000000000E-03")
    )
    return (
        table("REAC_APPUI_G", 100.0)
        + table("REAC_TOUS_G", 100.0)
        + table("REAC_APPUI_Q", 50.0)
        + table("REAC_TOUS_Q", 50.0)
        + sym.replace("{c}", "G")
        + sym.replace("{c}", "Q")
        + " --- DIAGNOSTIC JOB : OK\n"
    )


@pytest.fixture
def faked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Container, Salomé and version resolution replaced; returns what was called."""
    calls: dict[str, Any] = {"executed": []}
    monkeypatch.setattr(Runtime, "aster", lambda self: (_DIGEST, "17.4.0"))
    monkeypatch.setattr(Runtime, "docker_bin", lambda self: Path("/usr/bin/docker"))

    def fake_check(med: Path, invariants: Path, **_kwargs: Any) -> MeshCheckReport:
        report = tmp_path / "rapport_mesh_check.txt"
        report.write_text("Tous les invariants sont tenus.\n", encoding="utf-8")
        return MeshCheckReport(
            med_path=str(med),
            med_sha256="0" * 64,
            invariants_path=str(invariants),
            invariants_sha256="0" * 64,
            image_ref="image",
            work_dir=str(tmp_path),
            report_path=str(report),
            results=(
                InvariantResult(
                    kind="k", label="l", expected="1", obtained="1", ok=True
                ),
            ),
            ok=calls.get("mesh_ok", True),
            checked_at=datetime.now(UTC),
        )

    def fake_validate(comm: Path, **_kwargs: Any) -> ValidationReport:
        return ValidationReport(
            file_path=str(comm),
            aster_version="17.4.0",
            image_digest=_DIGEST,
            validation_level="B",
            catalogue_hash="h",
            valid=True,
            errors=[],
            warnings=[],
            commands_checked=[],
            commands_not_checked=[],
            checked_at=datetime.now(UTC),
        )

    def fake_execute(comm: Path, **_kwargs: Any) -> ExecutionReport:
        calls["executed"].append(comm)
        work = tmp_path / "runs" / f"run{len(calls['executed'])}"
        (work / "proc.0").mkdir(parents=True)
        (work / "proc.0" / "fort.6").write_text(_mess(), encoding="utf-8")
        (work / comm.name).write_bytes(comm.read_bytes())
        status = calls.get("status", "completed_ok")
        return ExecutionReport(
            comm_path=str(comm),
            aster_version="17.4.0",
            image_digest=_DIGEST,
            status=status,
            diag="OK" if status == "completed_ok" else "<F>_ERROR",
            return_code=0,
            work_dir=str(work),
            mess_path=str(work / "proc.0" / "fort.6"),
            result_files=(),
            duration_s=2.0,
            extracted_by="run_aster.status",
            executed_at=datetime.now(UTC),
            messages=(
                ExecutionMessage(
                    kind="<F>", identifier="X_1", line=3, text="<F> <X_1>"
                ),
            )
            if status != "completed_ok"
            else (),
        )

    monkeypatch.setattr(check_module, "check_med", fake_check)
    monkeypatch.setattr(validate_module, "validate_comm_file", fake_validate)
    monkeypatch.setattr(execute_module, "execute_comm_file", fake_execute)
    return calls


def test_the_whole_chain_on_the_fake_project(
    fake_project: Factory, faked: dict[str, Any]
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)

    lines = run_step(ctx, Runtime(project.repo_root), "tout", views=False)

    assert lines[0] == "== verifier"
    assert any("mesh check : 1/1 invariants tenus" in line for line in lines)
    assert any("Niveau B : valid=True" in line for line in lines)
    assert any("Contrôles D : RÉUSSI" in line for line in lines)
    assert any(line.startswith("Synthèse : ") for line in lines)
    state = load_state(ctx)
    assert state.validation is not None
    assert state.execution_dir is not None
    comm = Path(state.comm or "")
    assert comm.read_text(encoding="utf-8").startswith("# généré pour 17.4.0")
    assert "# L = 2.0" in comm.read_text(encoding="utf-8")
    assert (
        comm.with_suffix(".export")
        .read_text("utf-8")
        .endswith("F mmed barre.mmed D 20\n")
    )
    assert comm.with_suffix(".mmed").read_bytes() == b"MED factice"
    assert (ctx.results_dir / "controles" / "controles_d.json").is_file()
    assert "étape sans objet : le projet ne la déclare pas" in lines  # combinaisons
    assert faked["executed"] == [comm]


def test_ferraillage_without_members_is_refused(
    fake_project: Factory, faked: dict[str, Any]
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    run_step(ctx, Runtime(project.repo_root), "maillage")
    run_step(ctx, Runtime(project.repo_root), "generer")
    run_step(ctx, Runtime(project.repo_root), "executer")

    with pytest.raises(ProjectError, match="aucun élément à ferrailler"):
        run_step(ctx, Runtime(project.repo_root), "ferraillage")


def test_steps_say_which_step_must_come_first(
    fake_project: Factory, faked: dict[str, Any]
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)

    with pytest.raises(ProjectError, match="lancer d'abord l'étape « maillage »"):
        generate(ctx, Runtime(project.repo_root))
    with pytest.raises(ProjectError, match="lancer d'abord l'étape « generer »"):
        run_step(ctx, Runtime(project.repo_root), "valider")
    with pytest.raises(ProjectError, match="étape inconnue"):
        run_step(ctx, Runtime(project.repo_root), "cuisson")


def test_a_failed_mesh_check_and_a_failed_run_are_refused(
    fake_project: Factory, faked: dict[str, Any]
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    faked["mesh_ok"] = False
    with pytest.raises(ProjectError, match="invariant en écart"):
        run_step(ctx, Runtime(project.repo_root), "maillage")

    faked["mesh_ok"] = True
    run_step(ctx, Runtime(project.repo_root), "maillage")
    run_step(ctx, Runtime(project.repo_root), "generer")
    faked["status"] = "failed"
    with pytest.raises(ProjectError) as exc:
        run_step(ctx, Runtime(project.repo_root), "executer")
    assert "statut failed" in str(exc.value)
    assert "<F> X_1 (ligne 3)" in str(exc.value)


def test_a_blocking_fiche_stops_the_generation(
    fake_project: Factory, faked: dict[str, Any]
) -> None:
    project = fake_project()
    fiche = json.loads((project.directory / "fiche.json").read_text("utf-8"))
    fiche["group_naming"] = []
    (project.directory / "fiche.json").write_text(json.dumps(fiche), "utf-8")
    ctx = load_project(project.name, project.repo_root)

    with pytest.raises(ProjectError, match="aucune convention de nommage"):
        run_step(ctx, Runtime(project.repo_root), "verifier")
    with pytest.raises(ProjectError, match="génération refusée"):
        generate(
            ctx, Runtime(project.repo_root), med=project.directory / "maillage.med"
        )


def test_the_cli_runs_a_step(
    fake_project: Factory, faked: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    project = fake_project()
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(project.repo_root))

    result = CliRunner().invoke(app, ["projet", project.name, "verifier"])
    assert result.exit_code == 0, result.output
    assert "cohérente avec ses fichiers" in result.output

    result = CliRunner().invoke(app, ["projet", project.name, "controles"])
    assert result.exit_code == 1
    assert "lancer d'abord l'étape" in result.output

    result = CliRunner().invoke(
        app,
        [
            "generate",
            project.name,
            "--maillage",
            str(project.directory / "maillage.med"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["longueur"] == 2.0


def test_display_path_is_relative_from_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    inside = tmp_path / "a" / "b.txt"
    assert display_path(inside, tmp_path) == Path("a/b.txt")
    assert display_path(inside, tmp_path / "autre").is_absolute()
