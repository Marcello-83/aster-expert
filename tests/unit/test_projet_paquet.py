"""`aster-expert projet exporter-resultats <nom>` (lot 45) sur le projet factice :
contenu du paquet, empreintes et cohérences, niveau atteint niveau par niveau,
régénération du `.comm`, refus (MED, plafond de 20 Mo, fichier exigé absent).
L'état laissé par les étapes est écrit directement (aucun conteneur) ; le paquet
réel des deux projets est produit au lot 45 (partie A)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from typing import Any

import pytest
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.declaration import PACKAGE_MAX_BYTES
from aster_expert.projet.errors import ProjectError
from aster_expert.projet.paquet import (
    MANIFEST_NAME,
    compare_comm,
    export_results,
    lines_only_comments,
    normalize_comm,
    reevaluate_package,
)
from aster_expert.projet.pipeline import ProjectState, Runtime, save_state

Factory = Callable[..., Any]
_DIGEST = "sha256:" + "d" * 64
_COMM = "# généré pour 17.4.0\nDEBUT()\n# L = 2.0\nFIN()\n"
_MESS = "  --- DIAGNOSTIC JOB : OK\n"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _package(**changes: Any) -> dict[str, Any]:
    package: dict[str, Any] = {
        "items": [
            {"section": "controles", "source": "resultats/controles/controles_d.json"},
            {"section": "cas", "source": "resultats/vues/*.png", "label": "vue"},
            {"section": "cas", "source": "resultats/tableau.csv"},
        ],
    }
    package.update(changes)
    return package


@pytest.fixture
def ready(
    fake_project: Factory, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., ProjectContext]:
    """A fake project whose steps have run: verified mesh, `.comm`, level B,
    execution with its report, level D controls carrying their provenance."""
    monkeypatch.setattr(Runtime, "aster", lambda self: (_DIGEST, "17.4.0"))

    def make(
        *,
        package: dict[str, Any] | None = None,
        provenance: bool = True,
        executed_comm: str = _COMM,
    ) -> ProjectContext:
        project = fake_project(results_package=package or _package())
        ctx = load_project(project.name, project.repo_root)
        results = ctx.results_dir
        (results / "controles").mkdir(parents=True)
        (results / "vues").mkdir()
        comm = results / "barre.comm"
        comm.write_text(_COMM, encoding="utf-8")
        mesh = project.directory / "maillage.med"
        run = project.repo_root / "runs" / project.name
        (run / "proc.0").mkdir(parents=True)
        (run / "proc.0" / "fort.6").write_text(_MESS, encoding="utf-8")
        (run / "barre.comm").write_text(executed_comm, encoding="utf-8")
        (run / "compte_rendu.json").write_text(
            json.dumps(
                {
                    "report": {
                        "aster_version": "17.4.0",
                        "image_digest": _DIGEST,
                        "status": "completed_ok",
                        "diag": "OK",
                        "duration_s": 2.0,
                        "executed_at": "2026-10-02T00:00:00Z",
                    },
                    "inputs_sha256": {
                        "barre.comm": _sha(executed_comm.encode()),
                        "barre.mmed": _sha(mesh.read_bytes()),
                    },
                }
            ),
            encoding="utf-8",
        )
        summary: dict[str, Any] = {"threshold": 1e-6, "verdict": "RÉUSSI"}
        if provenance:
            summary["provenance"] = {
                "mess_sha256": _sha(_MESS.encode()),
                "comm_sha256": _sha(executed_comm.encode()),
            }
        (results / "controles" / "controles_d.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
        (results / "vues" / "a.png").write_bytes(b"\x89PNG factice a")
        (results / "vues" / "b.png").write_bytes(b"\x89PNG factice b")
        (results / "tableau.csv").write_text("x;y\n1;2\n", encoding="utf-8")
        (results / "validation.json").write_text(
            json.dumps(
                {
                    "validation_level": "B",
                    "valid": True,
                    "commands_checked": [{}, {}],
                    "commands_not_checked": [],
                    "errors": [],
                }
            ),
            encoding="utf-8",
        )
        mesh_report = results / "rapport_mesh_check.txt"
        mesh_report.write_text("1/1 invariants tenus\n", encoding="utf-8")
        save_state(
            ctx,
            ProjectState(
                mesh_med=str(mesh),
                mesh_check_report=str(mesh_report),
                comm=str(comm),
                validation={
                    "validation_level": "B",
                    "valid": True,
                    "commands_checked": 2,
                    "commands_total": 2,
                    "errors": 0,
                },
                execution_dir=str(run),
            ),
        )
        return ctx

    return make


def _manifest(ctx: ProjectContext) -> dict[str, Any]:
    path = ctx.results_dir / "paquet" / MANIFEST_NAME
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def test_the_package_holds_tables_figures_fingerprints_and_the_level(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready()

    result = export_results(ctx, Runtime(ctx.repo_root))

    out = ctx.results_dir / "paquet"
    assert result.directory == out
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == [
        "cas/a.png",
        "cas/b.png",
        "cas/tableau.csv",
        "controles/controles_d.json",
        "execution/compte_rendu.json",
        "maillage/rapport_mesh_check.txt",
        MANIFEST_NAME,
        "validation/validation.json",
    ]
    assert not any(p.suffix in (".med", ".mmed", ".rmed") for p in out.rglob("*"))
    manifest = _manifest(ctx)
    assert manifest["sections"] == [
        "cas",
        "controles",
        "execution",
        "maillage",
        "validation",
    ]
    prints = manifest["empreintes"]
    assert prints["comm"]["sha256"] == _sha(_COMM.encode())
    assert prints["fiche"]["sha256"] == _sha(ctx.fiche_path.read_bytes())
    assert prints["donnees"]["sha256"] == _sha(ctx.data_path.read_bytes())
    assert prints["maillage"]["sha256"] == _sha(b"MED factice")
    assert prints["execution"]["mess_sha256"] == _sha(_MESS.encode())
    assert manifest["code_aster"] == {"version": "17.4.0", "image_digest": _DIGEST}
    assert all(c["ok"] for c in manifest["coherence"])
    assert len(manifest["coherence"]) == 4
    figure = next(f for f in manifest["fichiers"] if f["chemin"] == "cas/a.png")
    assert figure["type"] == "figure"
    assert figure["libelle"] == "vue"
    assert figure["sha256"] == _sha(b"\x89PNG factice a")
    assert manifest["taille_octets"] == sum(f["octets"] for f in manifest["fichiers"])
    assert manifest["plafond_octets"] == PACKAGE_MAX_BYTES
    level = manifest["niveau"]
    assert level["atteint"] == "D"
    assert [s["atteint"] for s in level["par_niveau"]] == [True, True, True, False]
    assert level["par_niveau"][3]["motif"] == "aucune référence déclarée"
    regeneration = manifest["regeneration_comm"]
    assert regeneration["statut"] == "identique"
    assert regeneration["sha256"] == _sha(_COMM.encode())
    assert regeneration["identique_hors_commentaires"] is True
    assert regeneration["difference"] == []
    assert result.lines[-1] == "Niveau atteint : D"


def test_a_second_export_replaces_the_previous_package(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready()
    export_results(ctx, Runtime(ctx.repo_root))
    (ctx.results_dir / "vues" / "b.png").unlink()

    export_results(ctx, Runtime(ctx.repo_root))

    assert not (ctx.results_dir / "paquet" / "cas" / "b.png").exists()
    assert not (ctx.results_dir / "paquet.en_cours").exists()


def test_controls_without_provenance_stop_the_level_at_c(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(provenance=False)

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["niveau"]["atteint"] == "C"
    d = manifest["niveau"]["par_niveau"][2]
    assert d["atteint"] is False
    assert "NON rattachés" in d["motif"]


def test_a_comm_differing_from_the_execution_stops_the_level_at_b(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(executed_comm=_COMM.replace("FIN()", "IMPR_TABLE(TABLE=T)\nFIN()"))

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["coherence"][0]["ok"] is False
    assert manifest["niveau"]["atteint"] == "B"
    assert "DIFFÉRENT" in manifest["niveau"]["par_niveau"][1]["motif"]


def test_a_comm_differing_only_in_comments_keeps_level_c(
    ready: Callable[..., ProjectContext],
) -> None:
    """Lot 49 : la règle de conservation (lot 45, hors commentaires et en-tête) vaut
    aussi pour le niveau C ; le motif le dit."""
    ctx = ready(executed_comm=_COMM.replace("2.0", "3.0"))

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["coherence"][0]["ok"] is True
    assert "règle de conservation" in manifest["coherence"][0]["regle"]
    c = manifest["niveau"]["par_niveau"][1]
    assert c["atteint"] and "hors commentaires et en-tête" in c["motif"]


def test_a_regenerated_comm_that_differs_is_shown_line_by_line(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready()
    data = ctx.data_path.read_text(encoding="utf-8").replace("value: 2.0", "value: 2.5")
    ctx.data_path.write_text(data, encoding="utf-8")
    ctx.cache.clear()

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["regeneration_comm"]["statut"] == "different"
    assert manifest["regeneration_comm"]["difference"] == ["-# L = 2.0", "+# L = 2.5"]
    off = export_results(ctx, Runtime(ctx.repo_root), regenerate=False).manifest
    assert off["regeneration_comm"] == {"statut": "non_demandee"}


def _level_e(ctx: ProjectContext, verdicts: dict[str, str], comm: str) -> None:
    references = ctx.project_dir / "references"
    references.mkdir(exist_ok=True)
    (references / "niveau_e.json").write_text(
        json.dumps({"verdicts": {k: {"verdict": v} for k, v in verdicts.items()}}),
        encoding="utf-8",
    )
    (references / "cas.comm").write_text(comm, encoding="utf-8")


_E_SPEC = {
    "results": "references/niveau_e.json",
    "criteria_ids": ["E1", "E2"],
    "comm": "references/cas.comm",
}


def test_level_e_is_reached_only_on_the_comm_of_the_execution(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(level_e=_E_SPEC))
    # F4 en échec et D7 informatif : hors des critères de niveau E déclarés
    verdicts = {"E1": "RÉUSSI", "E2": "RÉUSSI", "F4": "ÉCHEC", "D7": "INFORMATIF"}
    _level_e(ctx, verdicts, _COMM)

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["niveau"]["atteint"] == "E"
    assert manifest["niveau_e"]["verdicts"]["F4"] == "ÉCHEC"
    assert manifest["niveau_e"]["meme_comm_que_l_execution"] is True


def test_level_e_on_another_comm_is_not_carried_over(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(level_e=_E_SPEC))
    other = _COMM.replace("DEBUT()", "DEBUT(PAR=1)")
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "RÉUSSI"}, other)

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["niveau"]["atteint"] == "D"
    assert manifest["niveau_e"]["difference_comm"] == ["-DEBUT(PAR=1)", "+DEBUT()"]
    assert manifest["niveau_e"]["meme_comm_que_l_execution"] is False
    motif = manifest["niveau"]["par_niveau"][3]["motif"]
    assert "ne se reporte pas" in motif
    # Lot 45 : l'énoncé de MM, avec l'empreinte du .comm qui avait obtenu le niveau.
    assert f"niveau E obtenu sur le .comm d'empreinte {_sha(other.encode())}" in motif
    assert ", à rejouer" in motif


def test_level_e_with_a_failed_criterion_or_a_missing_one(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(level_e=_E_SPEC))
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "ÉCHEC"}, _COMM)
    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest
    assert manifest["niveau"]["atteint"] == "D"
    assert "en échec" in manifest["niveau"]["par_niveau"][3]["motif"]

    _level_e(ctx, {"E1": "RÉUSSI"}, _COMM)
    with pytest.raises(ProjectError, match="critères absents .* E2"):
        export_results(ctx, Runtime(ctx.repo_root))


def test_a_med_file_is_refused_by_suffix_and_by_signature(
    ready: Callable[..., ProjectContext],
) -> None:
    items = [{"section": "cas", "source": "maillage.med"}]
    ctx = ready(package=_package(items=items))
    with pytest.raises(ProjectError, match="fichier MED refusé"):
        export_results(ctx, Runtime(ctx.repo_root))

    ctx2 = ready(package=_package(items=[{"section": "cas", "source": "x.json"}]))
    (ctx2.project_dir / "x.json").write_bytes(b"\x89HDF\r\n\x1a\n...")
    with pytest.raises(ProjectError, match="fichier MED refusé"):
        export_results(ctx2, Runtime(ctx2.repo_root))
    assert not (ctx2.results_dir / "paquet").exists()


def test_other_extensions_are_refused(ready: Callable[..., ProjectContext]) -> None:
    ctx = ready(package=_package(items=[{"section": "cas", "source": "fiche.json"}]))
    export_results(ctx, Runtime(ctx.repo_root))
    (ctx.project_dir / "notes.md").write_text("# prose\n", encoding="utf-8")
    ctx2 = ready(package=_package(items=[{"section": "cas", "source": "*.md"}]))
    (ctx2.project_dir / "notes.md").write_text("# prose\n", encoding="utf-8")
    with pytest.raises(ProjectError, match="extensions admises"):
        export_results(ctx2, Runtime(ctx2.repo_root))


def test_the_ceiling_refuses_and_writes_nothing(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(max_bytes=10))

    with pytest.raises(ProjectError, match="plafond 10"):
        export_results(ctx, Runtime(ctx.repo_root))
    assert not (ctx.results_dir / "paquet").exists()


def test_a_missing_required_item_is_refused_an_optional_one_is_not(
    ready: Callable[..., ProjectContext],
) -> None:
    items = [{"section": "ferraillage", "source": "resultats/absent/*.csv"}]
    ctx = ready(package=_package(items=items))
    with pytest.raises(ProjectError, match="aucun fichier pour"):
        export_results(ctx, Runtime(ctx.repo_root))

    optional = [{**items[0], "required": False}]
    ctx2 = ready(package=_package(items=optional))
    manifest = export_results(ctx2, Runtime(ctx2.repo_root)).manifest
    assert "ferraillage" not in manifest["sections"]


def test_two_sources_for_one_destination_are_refused(
    ready: Callable[..., ProjectContext],
) -> None:
    items = [
        {"section": "cas", "source": "resultats/tableau.csv"},
        {"section": "cas", "source": "autre/tableau.csv"},
    ]
    ctx = ready(package=_package(items=items))
    (ctx.project_dir / "autre").mkdir()
    (ctx.project_dir / "autre" / "tableau.csv").write_text("z\n", encoding="utf-8")

    with pytest.raises(ProjectError, match="deux fichiers pour cas/tableau.csv"):
        export_results(ctx, Runtime(ctx.repo_root))


def test_the_declaration_bounds_the_package(fake_project: Factory) -> None:
    project = fake_project(results_package=_package(max_bytes=PACKAGE_MAX_BYTES + 1))
    with pytest.raises(ProjectError, match="plafond"):
        load_project(project.name, project.repo_root)
    project = fake_project(results_package=_package(output="../ailleurs"))
    with pytest.raises(ProjectError, match="sous les résultats"):
        load_project(project.name, project.repo_root)


def test_a_project_without_package_is_refused(fake_project: Factory) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    with pytest.raises(ProjectError, match="ne déclare pas de paquet"):
        export_results(ctx, Runtime(ctx.repo_root))


def test_criteria_documents_carry_the_commit_that_introduced_them(
    ready: Callable[..., ProjectContext],
) -> None:
    criteria = [{"level": "D", "document": "docs/criteres.md"}]
    ctx = ready(package=_package(criteria=criteria))
    root = ctx.repo_root
    (root / "docs").mkdir()
    (root / "docs" / "criteres.md").write_text("# Critères\n", encoding="utf-8")
    env = ["-c", "user.name=Essai", "-c", "user.email=essai@example.invalid"]
    for args in (
        ["init", "-q"],
        ["add", "docs/criteres.md"],
        [*env, "commit", "-q", "-m", "Critères avant exécution"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True)  # noqa: S603, S607

    manifest = export_results(ctx, Runtime(root)).manifest

    (criterion,) = manifest["criteres"]
    assert criterion["niveau"] == "D"
    assert criterion["message"] == "Critères avant exécution"
    assert len(criterion["commit_introduction"]) == 40
    assert manifest["depot"]["commit"] == criterion["commit_introduction"]
    assert manifest["depot"]["arbre_modifie"] is True


def test_the_cli_exports_and_refuses_readably(
    ready: Callable[..., ProjectContext], monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = ready()
    monkeypatch.setattr("aster_expert.cli._project_root", lambda: ctx.repo_root)
    runner = CliRunner()

    done = runner.invoke(
        app,
        ["projet", "exporter-resultats", ctx.declaration.name, "--sans-regeneration"],
    )
    assert done.exit_code == 0, done.output
    assert "Niveau atteint : D" in done.output
    assert "Régénération du .comm : non_demandee" in done.output

    (ctx.results_dir / "tableau.csv").unlink()
    refused = runner.invoke(app, ["projet", "exporter-resultats", ctx.declaration.name])
    assert refused.exit_code == 1
    assert "projet exporter-resultats" in refused.output
    assert "ÉCHEC" in refused.output


# --- règle de conservation d'un niveau (lot 45) -------------------------------


def test_the_rule_ignores_comments_and_the_header_but_not_code() -> None:
    reference = (
        "# en-tête\n# Fiche : sha256:aaa\nDEBUT()\n"
        'A = F(NOM="a # b")  # note\n\nFIN()\n'
    )
    changed_header = reference.replace("sha256:aaa", "sha256:bbb")
    commented = reference.replace("# note", "# autre note  ").replace("\n\n", "\n")
    changed_value = reference.replace('"a # b"', '"a # c"')
    changed_number = "DEBUT()\nB = 210e9\n"

    assert normalize_comm(reference) == normalize_comm(changed_header)
    assert normalize_comm(reference) == normalize_comm(commented)
    assert 'NOM="a # b"' in normalize_comm(reference)  # le # d'une chaîne reste
    assert normalize_comm(reference) != normalize_comm(changed_value)
    assert normalize_comm(changed_number) != normalize_comm("DEBUT()\nB = 200e9\n")
    result = compare_comm(reference, changed_header)
    assert result["identique_octets"] is False
    assert result["identique_hors_commentaires"] is True
    assert compare_comm(reference, reference)["difference"] == []


def test_a_recorded_difference_is_judged_on_its_lines() -> None:
    assert lines_only_comments(["-# a", "+# b"]) is True
    assert lines_only_comments(["-X = 1  # a", "+X = 1  # b"]) is True
    assert lines_only_comments(["-X = 1", "+X = 2"]) is False
    assert lines_only_comments(["-# a", "+# b", "... (12 lignes de plus)"]) is None
    assert lines_only_comments([]) is True


def test_level_e_on_a_comm_differing_by_comments_only_is_conserved(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(level_e=_E_SPEC))
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "RÉUSSI"}, _COMM.replace("2.0", "2.1"))

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["niveau"]["atteint"] == "E"
    assert manifest["niveau_e"]["meme_comm_octets"] is False
    assert manifest["niveau_e"]["meme_comm_que_l_execution"] is True
    assert "règle de conservation" in manifest["niveau"]["par_niveau"][3]["motif"]


def test_a_regenerated_comm_differing_by_comments_conserves_the_levels(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready()
    data = ctx.data_path.read_text(encoding="utf-8").replace("value: 2.0", "value: 2.5")
    ctx.data_path.write_text(data, encoding="utf-8")
    ctx.cache.clear()

    manifest = export_results(ctx, Runtime(ctx.repo_root)).manifest

    assert manifest["regeneration_comm"]["statut"] == "different"
    assert manifest["regeneration_comm"]["identique_hors_commentaires"] is True
    assert manifest["niveau"]["atteint"] == "D"
    assert manifest["niveau"]["conservation"]["valable"] is True
    assert "conservés" in manifest["niveau"]["conservation"]["motif"]


def _commit(root: Any, message: str, date: str | None = None) -> None:
    env = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date} if date else {}
    git = ["git", "-c", "user.name=Essai", "-c", "user.email=essai@example.invalid"]
    import os  # noqa: PLC0415

    merged = {**os.environ, **env}
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S603, S607
    subprocess.run(["git", "add", "-A", "docs", "rapports"], cwd=root, check=True)  # noqa: S603, S607
    subprocess.run(
        [*git, "commit", "-q", "-m", message], cwd=root, check=True, env=merged
    )  # noqa: S603


def test_a_criterion_committed_before_the_execution_alone_is_demonstrable(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(criteria=[{"level": "D", "document": "docs/c.md"}]))
    (ctx.repo_root / "docs").mkdir()
    (ctx.repo_root / "docs" / "c.md").write_text("# Critères\n", encoding="utf-8")
    (ctx.repo_root / "rapports").mkdir()
    _commit(ctx.repo_root, "Critères", "2026-09-01T10:00:00+00:00")

    (criterion,) = export_results(ctx, Runtime(ctx.repo_root)).manifest["criteres"]

    assert criterion["posterieur_a_l_execution"] is False
    assert criterion["resultats_dans_le_commit"] == []
    assert criterion["anteriorite_demontrable"] is True


def test_a_criterion_committed_after_the_execution_is_flagged(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(criteria=[{"level": "D", "document": "docs/c.md"}]))
    (ctx.repo_root / "docs").mkdir()
    (ctx.repo_root / "docs" / "c.md").write_text("# Critères\n", encoding="utf-8")
    (ctx.repo_root / "rapports").mkdir()
    _commit(ctx.repo_root, "Critères", "2026-10-03T10:00:00+00:00")

    result = export_results(ctx, Runtime(ctx.repo_root))

    (criterion,) = result.manifest["criteres"]
    assert criterion["posterieur_a_l_execution"] is True
    assert criterion["anteriorite_demontrable"] is False
    assert "commité après l'exécution" in criterion["anteriorite_motif"]
    assert any("CRITÈRE D docs/c.md" in line for line in result.lines)


def test_a_criterion_committed_with_execution_results_is_flagged(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(criteria=[{"level": "D", "document": "docs/c.md"}]))
    (ctx.repo_root / "docs").mkdir()
    (ctx.repo_root / "docs" / "c.md").write_text("# Critères\n", encoding="utf-8")
    (ctx.repo_root / "rapports").mkdir()
    (ctx.repo_root / "rapports" / "executions.json").write_text("{}", encoding="utf-8")
    _commit(ctx.repo_root, "Critères et résultats", "2026-09-01T10:00:00+00:00")

    (criterion,) = export_results(ctx, Runtime(ctx.repo_root)).manifest["criteres"]

    assert criterion["posterieur_a_l_execution"] is False
    assert criterion["resultats_dans_le_commit"] == ["rapports/executions.json"]
    assert criterion["anteriorite_demontrable"] is False
    assert "antériorité non démontrable" in criterion["anteriorite_motif"]


def test_an_existing_package_is_reevaluated_from_its_own_files(
    ready: Callable[..., ProjectContext],
) -> None:
    ctx = ready(package=_package(level_e=_E_SPEC))
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "RÉUSSI"}, _COMM.replace("2.0", "2.1"))
    exported = export_results(ctx, Runtime(ctx.repo_root)).manifest
    path = ctx.results_dir / "paquet" / MANIFEST_NAME
    # Paquet d'avant la règle : l'octet près seul était connu.
    old = json.loads(path.read_text(encoding="utf-8"))
    old["niveau_e"].pop("meme_comm_octets")
    old["niveau_e"]["meme_comm_que_l_execution"] = False
    old["regeneration_comm"].pop("identique_hors_commentaires", None)
    path.write_text(json.dumps(old), encoding="utf-8")

    again = reevaluate_package(ctx.results_dir / "paquet", ctx.repo_root).manifest

    assert again["niveau_e"]["meme_comm_que_l_execution"] is True
    assert again["niveau"]["atteint"] == "E"
    assert again["niveau"]["par_niveau"] == exported["niveau"]["par_niveau"]
    assert (
        again["regeneration_comm"]["statut"] == exported["regeneration_comm"]["statut"]
    )


def test_the_cli_reevaluates_a_package_and_refuses_when_there_is_none(
    ready: Callable[..., ProjectContext], monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = ready()
    monkeypatch.setattr("aster_expert.cli._project_root", lambda: ctx.repo_root)
    runner = CliRunner()
    name = ctx.declaration.name
    argv = ["projet", "exporter-resultats", name, "--reevaluer"]

    missing = runner.invoke(app, argv)
    assert missing.exit_code == 1
    assert "paquet absent" in missing.output

    assert runner.invoke(app, ["projet", "exporter-resultats", name]).exit_code == 0
    done = runner.invoke(app, argv)
    assert done.exit_code == 0, done.output
    assert "Niveau atteint : D" in done.output


def test_a_level_e_replayed_after_the_export_is_judged_from_the_package(
    ready: Callable[..., ProjectContext],
) -> None:
    items = [
        *_package()["items"],
        {"section": "niveau_e", "source": "references/niveau_e.json"},
    ]
    ctx = ready(package=_package(items=items, level_e=_E_SPEC))
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "ÉCHEC"}, _COMM)
    export_results(ctx, Runtime(ctx.repo_root))
    # Rejeu des critères d'origine sur un .comm qui ne diffère que par un commentaire.
    _level_e(ctx, {"E1": "RÉUSSI", "E2": "RÉUSSI"}, _COMM.replace("2.0", "2.7"))

    result = reevaluate_package(ctx.results_dir / "paquet", ctx.repo_root, ctx)

    manifest = result.manifest
    assert manifest["niveau"]["atteint"] == "E"
    assert manifest["niveau_e"]["meme_comm_octets"] is False
    assert manifest["niveau_e"]["meme_comm_que_l_execution"] is True
    copied = json.loads(
        (ctx.results_dir / "paquet" / "niveau_e" / "niveau_e.json").read_text("utf-8")
    )
    assert copied["verdicts"]["E2"]["verdict"] == "RÉUSSI"
    assert "niveau_e/niveau_e.json" in [f["chemin"] for f in manifest["fichiers"]]
    assert manifest["taille_octets"] == sum(f["octets"] for f in manifest["fichiers"])
