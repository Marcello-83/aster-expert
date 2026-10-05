"""Sous-commandes de `aster-expert` (lot 41, étape 5.3 : couverture de `cli.py`).

Deux familles de tests :

- les commandes qui lisent seulement des données du dépôt (jeu d'évaluation,
  index BM25, catalogue extrait, base de constats) sont lancées pour de bon, et
  sautées si ces données locales manquent ;
- celles qui lancent le conteneur, Salomé, Git ou qui écrivent des données
  dérivées sont lancées avec leurs fonctions de travail remplacées (attributs du
  module `aster_expert.cli`), dans un dépôt temporaire : on éprouve la commande
  (options, messages, codes de sortie), jamais le travail qu'elle délègue.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

import aster_expert.cli as cli
from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.execution.errors import EnvironmentDetectionError, ExecutionRunError
from aster_expert.ingestion.errors import SourcesConfigError
from aster_expert.ingestion.sync import load_sources_config
from aster_expert.validation.errors import ValidationRunError

_ROOT = Path(__file__).resolve().parents[2]
_HAS_INDEX = (_ROOT / "data" / "indexes" / "bm25_by_file").is_dir()
_HAS_CATALOGUE = (_ROOT / "data" / "processed" / "catalogue").is_dir()
_HAS_CORPUS = (_ROOT / "data" / "processed" / "command_document_map.json").is_file()

runner = CliRunner()


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(_ROOT))
    return _ROOT


@pytest.fixture
def depot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Dépôt temporaire : configuration copiée, rien d'autre."""
    root = tmp_path / "depot"
    (root / "config").mkdir(parents=True)
    for name in ("versions.yaml", "sources.yaml", "validation.yaml", "retrieval.yaml"):
        shutil.copyfile(_ROOT / "config" / name, root / "config" / name)
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(root))
    monkeypatch.setenv("ASTER_CONTAINER_WORKROOT", str(tmp_path / "workroot"))
    return root


def _detected() -> Any:
    return SimpleNamespace(
        container=SimpleNamespace(
            image_repository="simvia/code_aster",
            image_digest="sha256:" + "d" * 64,
            image_tag="17.4.0",
        ),
        run_aster=SimpleNamespace(version_raw="17.4.0"),
        catalogue=SimpleNamespace(path_in_container="/opt/catalogue"),
    )


# --- env, sources, catalogue ---------------------------------------------------------


@pytest.fixture(autouse=True)
def _lecture_sous_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Les fichiers d'entrée de ces tests vivent sous `tmp_path` : racine de lecture
    factice. La politique réelle est testée dans `test_chemins.py`."""
    from aster_expert import chemins

    politique = chemins.PathPolicy("lecture", (tmp_path.resolve(),), "")
    monkeypatch.setattr(chemins, "load_read_policy", lambda _root: politique)


def test_env_detect_writes_the_detected_section(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written: list[Path] = []
    monkeypatch.setattr(cli, "_detect_from_env", lambda workroot: _detected())
    monkeypatch.setattr(
        cli, "write_detected_section", lambda path, detected: written.append(path)
    )

    result = runner.invoke(cli.app, ["env", "detect"])

    assert result.exit_code == 0, result.output
    assert "Tag         : 17.4.0" in result.output
    assert written == [depot / "config" / "versions.yaml"]


def test_env_detect_failures(depot: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(workroot: Path) -> Any:
        raise EnvironmentDetectionError("aucune image")

    monkeypatch.setattr(cli, "_detect_from_env", fail)
    result = runner.invoke(cli.app, ["env", "detect"])
    assert result.exit_code == 1
    assert "Détection de l'environnement Aster échouée : aucune image" in result.output

    monkeypatch.delenv("ASTER_CONTAINER_WORKROOT")
    result = runner.invoke(cli.app, ["env", "detect"])
    assert result.exit_code == 1
    assert "ASTER_CONTAINER_WORKROOT n'est pas renseigné" in result.output

    (depot / "config" / "versions.yaml").unlink()
    result = runner.invoke(cli.app, ["env", "detect"])
    assert result.exit_code == 1
    assert "config/versions.yaml introuvable" in result.output


def test_sources_sync_reports_each_source(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = [
        SimpleNamespace(name="doc", status="ok", ref="main", commit="abc", detail=""),
        SimpleNamespace(
            name="src",
            status="blocked_local_changes",
            ref="v17",
            commit=None,
            detail="modifications locales",
        ),
    ]
    monkeypatch.setattr(
        cli, "sync_sources", lambda **kwargs: SimpleNamespace(sources=entries)
    )

    result = runner.invoke(cli.app, ["sources", "sync"])

    assert result.exit_code == 1  # une source bloquée
    assert "doc [ok] main @ abc" in result.output
    assert "src [blocked_local_changes] v17 @ ?" in result.output

    def fail(**kwargs: Any) -> Any:
        raise SourcesConfigError("sources.yaml invalide")

    monkeypatch.setattr(cli, "sync_sources", fail)
    result = runner.invoke(cli.app, ["sources", "sync"])
    assert result.exit_code == 1
    assert "sources.yaml invalide" in result.output


def _manifest(depot: Path, commit: str | None = "c" * 40) -> None:
    (depot / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (depot / "data" / "raw" / "manifest.json").write_text(
        json.dumps({"sources": [{"name": "codeaster-doc", "commit": commit}]}),
        encoding="utf-8",
    )


def test_sources_inventory(depot: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = runner.invoke(cli.app, ["sources", "inventory"])
    assert result.exit_code == 1
    assert "manifeste introuvable" in result.output

    _manifest(depot, commit=None)
    result = runner.invoke(cli.app, ["sources", "inventory"])
    assert result.exit_code == 1
    assert "aucune révision synchronisée" in result.output

    _manifest(depot)
    result = runner.invoke(cli.app, ["sources", "inventory"])
    assert result.exit_code == 1
    assert "répertoire introuvable" in result.output

    config = load_sources_config(depot / "config" / "sources.yaml")
    source = next(s for s in config.sources if s.name == "codeaster-doc")
    (depot / source.local_path / source.families["manuals"].paths[0]).mkdir(
        parents=True
    )
    written: list[Path] = []
    monkeypatch.setattr(
        cli,
        "build_inventory",
        lambda *a, **k: SimpleNamespace(
            documents=[SimpleNamespace(family="U4"), SimpleNamespace(family="R")],
            anomalies=[SimpleNamespace(kind="sans_titre")],
        ),
    )
    monkeypatch.setattr(
        cli, "write_inventory_jsonl", lambda result, path: written.append(path)
    )
    result = runner.invoke(cli.app, ["sources", "inventory"])
    assert result.exit_code == 0, result.output
    assert "Documents inventoriés : 2" in result.output
    assert "[sans_titre] 1" in result.output
    assert written


def test_sources_probe_xref_and_command_map(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for command in ("probe", "xref", "command-map"):
        result = runner.invoke(cli.app, ["sources", command])
        assert result.exit_code == 1
        assert "inventaire introuvable" in result.output

    inventory = depot / "data" / "raw" / "inventory.jsonl"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("", encoding="utf-8")
    _manifest(depot)
    config = load_sources_config(depot / "config" / "sources.yaml")
    source = next(s for s in config.sources if s.name == "codeaster-doc")
    manuals = Path(source.families["manuals"].paths[0])
    conf = depot / source.local_path / manuals.parent / "conf.py"
    result = runner.invoke(cli.app, ["sources", "probe"])
    assert result.exit_code == 1
    assert "conf.py introuvable" in result.output

    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text("extensions = []\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "build_probe_report",
        lambda **k: SimpleNamespace(
            sampled_documents=3,
            sampled_files=4,
            recovery_ratio=0.95,
            unknown_directives=[],
            unknown_roles=[],
            unresolved_includes=[],
            conf_py_extensions=[],
            parse_errors=["x"],
        ),
    )
    monkeypatch.setattr(cli, "write_probe_report_json", lambda report, path: None)
    result = runner.invoke(cli.app, ["sources", "probe"])
    assert result.exit_code == 0, result.output
    assert "Taux de récupération textuelle : 95.0 %" in result.output

    monkeypatch.setattr(
        cli,
        "build_reference_graph_result",
        lambda **k: SimpleNamespace(
            total_references=10,
            internal_resolved_references=7,
            external_references=1,
            ambiguous_references=1,
            unresolved_references=1,
            edges=[1, 2],
        ),
    )
    monkeypatch.setattr(cli, "write_xref_json", lambda result, path: None)
    result = runner.invoke(cli.app, ["sources", "xref"])
    assert result.exit_code == 0, result.output
    assert "Résolues internes        : 7 (70.0 %)" in result.output

    monkeypatch.setattr(cli, "resolve_active_digest", lambda path: "sha256:x")
    result = runner.invoke(cli.app, ["sources", "command-map"])
    assert result.exit_code == 1
    assert "catalogue introuvable" in result.output

    (depot / "data" / "processed" / "catalogue" / "sha256:x").mkdir(parents=True)
    monkeypatch.setattr(cli, "load_u4_u7_documents", lambda path: [])
    monkeypatch.setattr(cli, "load_catalogue_commands", lambda path: [])
    monkeypatch.setattr(
        cli,
        "build_command_mapping",
        lambda *a, **k: SimpleNamespace(
            matched_catalogue_commands=9,
            total_catalogue_commands=10,
            commands_without_document=["X"],
            documents_without_command=[],
            documents_naming_uncatalogued_command=[],
        ),
    )
    monkeypatch.setattr(cli, "write_command_mapping_json", lambda result, path: None)
    result = runner.invoke(cli.app, ["sources", "command-map"])
    assert result.exit_code == 0, result.output
    assert "Commandes couvertes : 9/10 (90.0 %)" in result.output


def test_catalogue_extract(depot: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_detect_from_env", lambda workroot: _detected())
    monkeypatch.setattr(cli, "write_detected_section", lambda path, detected: None)
    summary = SimpleNamespace(
        total_exposed=3,
        total_extracted=3,
        kind_counts={"operator": 3},
        commands_without_usable_docu=[],
        anomalies=[
            SimpleNamespace(kind="extraction_error", command="X", detail="échec")
        ],
    )
    monkeypatch.setattr(
        cli, "extract_catalogue", lambda **k: (depot / "catalogue", summary)
    )

    result = runner.invoke(cli.app, ["catalogue", "extract"])

    assert result.exit_code == 1  # une anomalie d'extraction
    assert "Commandes extraites : 3" in result.output
    assert "[extraction_error] X : échec" in result.output

    def fail(**k: Any) -> Any:
        raise CatalogueExtractionError("image absente")

    monkeypatch.setattr(cli, "extract_catalogue", fail)
    result = runner.invoke(cli.app, ["catalogue", "extract"])
    assert result.exit_code == 1
    assert "Extraction du catalogue échouée : image absente" in result.output


@pytest.mark.skipif(not _HAS_CATALOGUE, reason="catalogue extrait absent")
def test_catalogue_show_reads_the_extracted_catalogue(repo: Path) -> None:
    result = runner.invoke(cli.app, ["catalogue", "show", "DEBUT"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["command"] == "DEBUT"

    result = runner.invoke(
        cli.app, ["catalogue", "show", "AFFE_CHAR_MECA", "--keyword", "DDL_IMPO.DX"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["path"] == ["DDL_IMPO", "DX"]

    result = runner.invoke(cli.app, ["catalogue", "show", "COMMANDE_INEXISTANTE"])
    assert result.exit_code == 1


# --- évaluation, fragments, index, recherche ----------------------------------------


def test_eval_summary_and_score(repo: Path, tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["eval", "summary"])
    assert result.exit_code == 0, result.output
    summary = json.loads(result.stdout)
    assert summary["total"] > 0

    questions = [
        json.loads(line)
        for line in (repo / "data" / "evaluations" / "questions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    results = tmp_path / "resultats.jsonl"
    results.write_text(
        "".join(
            json.dumps({"id": q["id"], "ranked_documents": ["U4.51.11"]}) + "\n"
            for q in questions
        ),
        encoding="utf-8",
    )
    result = runner.invoke(cli.app, ["eval", "score", str(results), "--k", "5"])
    assert result.exit_code == 0, result.output
    assert "Hit@5" in result.output

    result = runner.invoke(cli.app, ["eval", "score", str(tmp_path / "absent.jsonl")])
    assert result.exit_code == 1
    result = runner.invoke(
        cli.app, ["eval", "summary", "--questions", str(tmp_path / "absent")]
    )
    assert result.exit_code == 1


@pytest.mark.skipif(not (_HAS_INDEX and _HAS_CORPUS), reason="index BM25 absent")
def test_eval_benches_run_on_the_local_index(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "banc.json"
    result = runner.invoke(cli.app, ["eval", "bench", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "granularity_report" in json.loads(out.read_text(encoding="utf-8"))

    out = tmp_path / "decompose.json"
    result = runner.invoke(cli.app, ["eval", "decompose", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert out.is_file()

    out = tmp_path / "profils.json"
    result = runner.invoke(cli.app, ["eval", "profile-bench", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert out.is_file()

    for command in (["eval", "bench"], ["eval", "profile-bench"]):
        result = runner.invoke(cli.app, [*command, "--granularity", "par_page"])
        assert result.exit_code == 1
        assert "Granularité inconnue" in result.output


@pytest.mark.skipif(not _HAS_INDEX, reason="index BM25 absent")
def test_search_on_the_local_index(repo: Path) -> None:
    result = runner.invoke(
        cli.app,
        ["search", "STAT_NON_LINE comportement", "--profile", "syntaxe", "--k", "3"],
    )
    assert result.exit_code == 0, result.output
    assert "Profil : syntaxe" in result.output

    result = runner.invoke(cli.app, ["search", "x", "--priority-mode", "tiède"])
    assert result.exit_code == 1
    result = runner.invoke(cli.app, ["search", "x", "--granularity", "par_page"])
    assert result.exit_code == 1


def test_fragments_and_index_build(
    depot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = runner.invoke(cli.app, ["fragments", "build"])
    assert result.exit_code == 1
    assert "inventaire introuvable" in result.output

    for path in (
        depot / "data" / "raw" / "inventory.jsonl",
        depot / "data" / "processed" / "command_document_map.json",
        depot / "data" / "processed" / "xref_graph.json",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "build_fragments_streaming",
        lambda **k: SimpleNamespace(
            documents_processed=2, fragment_count=5, median_content_chars=100
        ),
    )
    result = runner.invoke(cli.app, ["fragments", "build"])
    assert result.exit_code == 0, result.output
    assert "[by_subsection] fragments produits : 5" in result.output
    result = runner.invoke(cli.app, ["fragments", "build", "--granularity", "x"])
    assert result.exit_code == 1

    result = runner.invoke(cli.app, ["index", "build"])
    assert result.exit_code == 1
    assert "fragments introuvables" in result.output
    for granularity in ("by_file", "by_subsection"):
        (depot / "data" / "processed" / f"fragments_{granularity}.jsonl").write_text(
            "", encoding="utf-8"
        )
    monkeypatch.setattr(
        cli,
        "build_bm25_index",
        lambda *a, **k: SimpleNamespace(
            fragment_count=5, vocabulary_size=50, text_enrichment=None
        ),
    )
    result = runner.invoke(cli.app, ["index", "build"])
    assert result.exit_code == 0, result.output
    assert "[by_file] vocabulaire       : 50" in result.output
    result = runner.invoke(cli.app, ["index", "build", "--granularity", "x"])
    assert result.exit_code == 1


# --- validation, exécution, maillage --------------------------------------------------


def _validation(errors: int) -> Any:
    return SimpleNamespace(
        commands_checked=[1, 2],
        commands_not_checked=[3],
        validation_level="B",
        errors=[1] * errors,
        warnings=["attention"],
        model_dump_json=lambda: json.dumps({"valid": errors == 0}),
    )


def test_validate(depot: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    comm = tmp_path / "a.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    monkeypatch.setattr(cli, "find_docker_binary", lambda env: Path("/usr/bin/docker"))
    monkeypatch.setattr(cli, "validate_comm_file", lambda *a, **k: _validation(0))

    result = runner.invoke(cli.app, ["validate", str(comm)])
    assert result.exit_code == 0, result.output
    assert "Commandes vérifiées   : 2/3 (66.7 %)" in result.output
    assert "Avertissements        : 1" in result.output

    monkeypatch.setattr(cli, "validate_comm_file", lambda *a, **k: _validation(2))
    result = runner.invoke(cli.app, ["validate", str(comm)])
    assert result.exit_code == 1

    def fail(*a: Any, **k: Any) -> Any:
        raise ValidationRunError("catalogue absent")

    monkeypatch.setattr(cli, "validate_comm_file", fail)
    result = runner.invoke(cli.app, ["validate", str(comm)])
    assert result.exit_code == 1
    assert "Validation échouée : catalogue absent" in result.output


def _execution(status: str) -> Any:
    return SimpleNamespace(
        status=status,
        diag="OK",
        work_dir="/tmp/run",
        mess_path="/tmp/run/fort.6",
        result_files=("a",),
        duration_s=1.5,
        model_dump_json=lambda: json.dumps({"status": status}),
    )


def test_run(depot: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    comm = tmp_path / "a.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    monkeypatch.setattr(cli, "check_allowed", lambda *a, **k: comm)
    monkeypatch.setattr(
        cli, "resolve_digest_for_version", lambda *a: ("sha256:x", "17.4.0")
    )
    monkeypatch.setattr(cli, "find_docker_binary", lambda env: Path("/usr/bin/docker"))
    monkeypatch.setattr(
        cli, "execute_comm_file", lambda *a, **k: _execution("completed_ok")
    )

    result = runner.invoke(cli.app, ["run", str(comm)])
    assert result.exit_code == 0, result.output
    assert "Durée          : 1.5 s" in result.output

    monkeypatch.setattr(cli, "execute_comm_file", lambda *a, **k: _execution("failed"))
    assert runner.invoke(cli.app, ["run", str(comm)]).exit_code == 1

    def fail(*a: Any, **k: Any) -> Any:
        raise ExecutionRunError("hors des racines")

    monkeypatch.setattr(cli, "execute_comm_file", fail)
    result = runner.invoke(cli.app, ["run", str(comm)])
    assert result.exit_code == 1
    assert "Exécution échouée : hors des racines" in result.output


def test_mesh_run_and_check(
    depot: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import aster_expert.meshing.check as check_module
    import aster_expert.meshing.run as run_module
    from aster_expert.meshing.errors import MeshRunError

    for nom in ("script.py", "p.json", "m.med", "inv.yaml"):
        (tmp_path / nom).write_text("x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    report = SimpleNamespace(
        from_cache=True,
        med_path="m.med",
        log_path="salome.log",
        model_dump_json=lambda: json.dumps({"med_path": "m.med"}),
    )
    monkeypatch.setattr(run_module, "run_salome_script", lambda *a, **k: report)
    result = runner.invoke(cli.app, ["mesh", "run", "script.py", "--params", "p.json"])
    assert result.exit_code == 0, result.output
    assert "Salomé non relancé" in result.output

    def fail(*a: Any, **k: Any) -> Any:
        raise MeshRunError("Salomé absent")

    monkeypatch.setattr(run_module, "run_salome_script", fail)
    result = runner.invoke(cli.app, ["mesh", "run", "script.py"])
    assert result.exit_code == 1
    assert "mesh run ÉCHEC : Salomé absent" in result.output

    rapport = tmp_path / "rapport.txt"
    rapport.write_text("Tous les invariants sont tenus.\n", encoding="utf-8")
    monkeypatch.setattr(
        cli, "resolve_digest_for_version", lambda *a: ("sha256:x", "17.4.0")
    )
    monkeypatch.setattr(cli, "find_docker_binary", lambda env: Path("/usr/bin/docker"))
    monkeypatch.setattr(
        check_module,
        "check_med",
        lambda *a, **k: SimpleNamespace(report_path=str(rapport), ok=False),
    )
    result = runner.invoke(cli.app, ["mesh", "check", "m.med", "inv.yaml"])
    assert result.exit_code == 1  # rapport en écart
    assert "Tous les invariants sont tenus." in result.output


# --- constats ------------------------------------------------------------------------


def test_constats_chercher(repo: Path) -> None:
    result = runner.invoke(
        cli.app, ["constats", "chercher", "--commande", "CREA_MAILLAGE"]
    )
    assert result.exit_code == 0, result.output
    assert "CA-034 [niveau D]" in result.output

    result = runner.invoke(cli.app, ["constats", "chercher"])
    assert result.exit_code == 1
    assert "au moins un critère" in result.output


def test_constats_rejouer(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aster_expert.constats.rejeu as rejeu

    fake = SimpleNamespace(lines=lambda: ["CA-001 : tient"], to_review=[])
    monkeypatch.setattr(rejeu, "replay_base", lambda *a, **k: fake)
    result = runner.invoke(cli.app, ["constats", "rejouer", "--constat", "CA-001"])
    assert result.exit_code == 0
    assert "CA-001 : tient" in result.output

    fake.to_review = ["CA-001"]
    assert runner.invoke(cli.app, ["constats", "rejouer"]).exit_code == 1

    def fail(*a: Any, **k: Any) -> Any:
        raise rejeu.ReplayError("pas de conteneur")

    monkeypatch.setattr(rejeu, "replay_base", fail)
    result = runner.invoke(cli.app, ["constats", "rejouer"])
    assert result.exit_code == 1
    assert "constats rejouer ÉCHEC : pas de conteneur" in result.output
