"""Command line entry point.

Nothing here guesses a Code_Aster version or an installation path.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

import typer
import yaml

from aster_expert import __version__
from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.extract import extract_catalogue
from aster_expert.catalogue.query import (
    find_keyword_variants,
    load_command_schema,
    resolve_active_digest,
    resolve_digest_for_aster_version,
)
from aster_expert.execution.config import load_execution_config
from aster_expert.execution.detect import detect_environment, write_detected_section
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.execution.errors import EnvironmentDetectionError, ExecutionRunError
from aster_expert.execution.execute import (
    check_allowed,
    execute_comm_file,
    plan_resources,
)
from aster_expert.execution.models import DetectedEnvironment
from aster_expert.indexing.bm25_index import (
    build_bm25_index,
    default_index_dir,
    find_fragments,
    load_bm25_index,
    to_document_section,
)
from aster_expert.indexing.enrichment import (
    collect_related_commands,
    load_command_keyword_names,
)
from aster_expert.indexing.naive_search import build_documents_by_command
from aster_expert.ingestion.command_map import (
    build_command_mapping,
    default_command_map_path,
    load_catalogue_commands,
    load_u4_u7_documents,
    write_command_mapping_json,
)
from aster_expert.ingestion.errors import SourcesConfigError
from aster_expert.ingestion.inventory import (
    build_inventory,
    default_inventory_path,
    write_inventory_jsonl,
)
from aster_expert.ingestion.rst_probe import (
    build_probe_report,
    default_probe_report_path,
    write_probe_report_json,
)
from aster_expert.ingestion.sync import (
    default_manifest_path,
    default_sources_yaml_path,
    load_sources_config,
    sync_sources,
)
from aster_expert.ingestion.xref import (
    build_reference_graph_result,
    default_xref_path,
    write_xref_json,
)
from aster_expert.parsing.comm_parser import parse_comm_file
from aster_expert.parsing.doc_fragments import (
    DEFAULT_SUBSECTION_LINE_THRESHOLD,
    build_fragments_streaming,
    default_fragments_path,
)
from aster_expert.parsing.errors import CommParseError
from aster_expert.projet.context import ProjectContext
from aster_expert.retrieval.bench import (
    run_granularity_bench,
    run_lot7b_decomposition,
    run_naive_baseline_comparison,
    run_profile_routed_bench,
)
from aster_expert.retrieval.evaluation import (
    evaluate_retrieval,
    load_questions,
    load_ranked_results,
    summarize_question_set,
)
from aster_expert.retrieval.query_profiles import (
    DEFAULT_QUERY_PROFILE,
    default_query_profiles_path,
    load_query_profiles,
)
from aster_expert.retrieval.source_priority import (
    hard_filter_search,
    load_source_priority,
    soft_reweight_search,
)
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.validate import (
    resolve_digest_for_version,
    validate_comm_file,
)

if TYPE_CHECKING:
    from aster_expert.connaissances.base import KnowledgeBase
    from aster_expert.notes.controle import NoteCheck

app = typer.Typer(
    add_completion=False,
    help="Agent expert Code_Aster : corpus, catalogue, validation, exécution.",
)

env_app = typer.Typer(no_args_is_help=True, help="Environnement Code_Aster.")
sources_app = typer.Typer(no_args_is_help=True, help="Dépôts sources.")
catalogue_app = typer.Typer(no_args_is_help=True, help="Catalogue des commandes.")
comm_app = typer.Typer(no_args_is_help=True, help="Fichiers de commandes .comm.")
eval_app = typer.Typer(
    no_args_is_help=True, help="Jeu d'évaluation de la recherche (lot 5)."
)
fragments_app = typer.Typer(
    no_args_is_help=True, help="Découpage du corpus en fragments (lot 7)."
)
index_app = typer.Typer(no_args_is_help=True, help="Index lexical (lot 7).")
mesh_app = typer.Typer(
    no_args_is_help=True, help="Maillage : scripts Salomé et vérificateur MED (lot 26)."
)
app.add_typer(env_app, name="env")
app.add_typer(sources_app, name="sources")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(comm_app, name="comm")
app.add_typer(eval_app, name="eval")
app.add_typer(fragments_app, name="fragments")
app.add_typer(index_app, name="index")
app.add_typer(mesh_app, name="mesh")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", help="Afficher la version du projet."
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit(0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


def _project_root() -> Path:
    return Path(os.environ.get("ASTER_EXPERT_ROOT") or Path.cwd())


def _require_workroot() -> Path:
    workroot_raw = (os.environ.get("ASTER_CONTAINER_WORKROOT") or "").strip()
    if not workroot_raw:
        typer.echo(
            "ASTER_CONTAINER_WORKROOT n'est pas renseigné : aucune introspection "
            "n'est autorisée sans répertoire de travail dédié (voir .env.example).",
            err=True,
        )
        raise typer.Exit(1)
    return Path(workroot_raw)


def _resolve_aster_version_tag(versions_path: Path) -> str:
    """The human-readable version tag of the last detected environment.

    Distinct from `resolve_active_digest` (the identity that actually
    faces authority, docs/architecture.md ADR-002): a documentary fragment
    cites the readable tag for humans (docs/metadata.md §2, `aster_version`
    on a catalogue schema follows the same convention), never `stable`.
    """
    data = yaml.safe_load(versions_path.read_text(encoding="utf-8")) or {}
    tag = (
        (data.get("detected") or {}).get("container", {}).get("image_tag")
        if isinstance(data.get("detected"), dict)
        else None
    )
    if not tag:
        typer.echo(
            "config/versions.yaml : aucun tag d'image détecté ; lancez "
            "'aster-expert env detect' d'abord",
            err=True,
        )
        raise typer.Exit(1)
    return str(tag)


def _lecture(
    chemin: str | Path,
    *suffixes: str,
    kind: str | None = "file",
) -> Path:
    """Path to read, through the read policy (lot 46), or a readable refusal."""
    from aster_expert.chemins import (
        PathRefusedError,
        load_read_policy,
        resolve_input_path,
    )

    try:
        return resolve_input_path(
            chemin,
            policy=load_read_policy(_project_root()),
            base=Path.cwd(),
            suffixes=suffixes or None,
            kind=kind,
        )
    except PathRefusedError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


def _default_manifest_commit(project_root: Path, source_name: str) -> str:
    manifest_path = default_manifest_path(project_root)
    if not manifest_path.is_file():
        typer.echo(f"Manifeste introuvable ({manifest_path})", err=True)
        raise typer.Exit(1)
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(
        (s for s in manifest_raw.get("sources", []) if s.get("name") == source_name),
        None,
    )
    if entry is None or not entry.get("commit"):
        typer.echo(
            f"Aucune révision synchronisée pour '{source_name}' dans le manifeste",
            err=True,
        )
        raise typer.Exit(1)
    return str(entry["commit"])


def _detect_from_env(workroot: Path) -> DetectedEnvironment:
    return detect_environment(
        workroot=workroot,
        image_repository=os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster"),
        image_ref_env=os.environ.get("ASTER_IMAGE_REF") or None,
        docker_bin_env=os.environ.get("ASTER_DOCKER_BIN") or None,
        network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
        memory=os.environ.get("ASTER_CONTAINER_MEMORY") or None,
        cpus=os.environ.get("ASTER_CONTAINER_CPUS") or None,
        timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
    )


@env_app.command("detect")
def env_detect() -> None:
    """Détecter l'installation Code_Aster et écrire config/versions.yaml."""
    versions_path = _project_root() / "config" / "versions.yaml"
    if not versions_path.is_file():
        typer.echo(f"config/versions.yaml introuvable : {versions_path}", err=True)
        raise typer.Exit(1)

    workroot = _require_workroot()

    try:
        detected = _detect_from_env(workroot)
    except EnvironmentDetectionError as exc:
        typer.echo(f"Détection de l'environnement Aster échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    write_detected_section(versions_path, detected)

    typer.echo(f"Dépôt image : {detected.container.image_repository}")
    typer.echo(f"Digest      : {detected.container.image_digest}")
    typer.echo(
        f"Tag         : {detected.container.image_tag or '(aucun, résolu par digest)'}"
    )
    typer.echo(f"run_aster   : {detected.run_aster.version_raw}")
    typer.echo(f"Catalogue   : {detected.catalogue.path_in_container}")
    typer.echo(f"Écrit dans {versions_path}")


@sources_app.command("sync")
def sources_sync() -> None:
    """Synchroniser les dépôts déclarés dans config/sources.yaml."""
    project_root = _project_root()

    try:
        manifest = sync_sources(
            project_root=project_root,
            timeout=int(os.environ.get("ASTER_GIT_TIMEOUT", "600")),
        )
    except SourcesConfigError as exc:
        typer.echo(f"Synchronisation des sources échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    blocked = False
    for entry in manifest.sources:
        typer.echo(f"{entry.name} [{entry.status}] {entry.ref} @ {entry.commit or '?'}")
        if entry.detail:
            typer.echo(f"  {entry.detail}", err=entry.status.startswith("blocked"))
        if entry.status.startswith("blocked"):
            blocked = True

    typer.echo(f"Manifeste écrit dans {default_manifest_path(project_root)}")
    if blocked:
        raise typer.Exit(1)


@sources_app.command("inventory")
def sources_inventory() -> None:
    """Inventorier le corpus documentaire codeaster-doc (lot 6)."""
    project_root = _project_root()

    try:
        config = load_sources_config(default_sources_yaml_path(project_root))
    except SourcesConfigError as exc:
        typer.echo(f"Inventaire échoué : {exc}", err=True)
        raise typer.Exit(1) from exc

    source = next((s for s in config.sources if s.name == "codeaster-doc"), None)
    if source is None:
        typer.echo(
            "Inventaire échoué : source 'codeaster-doc' non déclarée dans "
            "config/sources.yaml",
            err=True,
        )
        raise typer.Exit(1)

    manuals_family = source.families.get("manuals")
    if manuals_family is None or not manuals_family.paths:
        typer.echo(
            "Inventaire échoué : config/sources.yaml ne déclare aucun chemin "
            "pour la famille 'manuals' de 'codeaster-doc'",
            err=True,
        )
        raise typer.Exit(1)

    manifest_path = default_manifest_path(project_root)
    if not manifest_path.is_file():
        typer.echo(
            f"Inventaire échoué : manifeste introuvable ({manifest_path}) ; "
            "lancez 'aster-expert sources sync' d'abord",
            err=True,
        )
        raise typer.Exit(1)
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sources = manifest_raw.get("sources", [])
    manifest_entry = next(
        (s for s in manifest_sources if s.get("name") == "codeaster-doc"), None
    )
    if manifest_entry is None or not manifest_entry.get("commit"):
        typer.echo(
            "Inventaire échoué : aucune révision synchronisée pour "
            "'codeaster-doc' dans le manifeste",
            err=True,
        )
        raise typer.Exit(1)

    repo_root = project_root / source.local_path
    manuals_root = repo_root / manuals_family.paths[0]
    if not manuals_root.is_dir():
        typer.echo(
            f"Inventaire échoué : répertoire introuvable ({manuals_root})", err=True
        )
        raise typer.Exit(1)

    result = build_inventory(
        manuals_root,
        repo_root=repo_root,
        source_name=source.name,
        source_commit=manifest_entry["commit"],
    )

    output_path = default_inventory_path(project_root)
    write_inventory_jsonl(result, output_path)

    family_counts = Counter(d.family for d in result.documents)
    anomaly_counts = Counter(a.kind for a in result.anomalies)

    typer.echo(f"Documents inventoriés : {len(result.documents)}")
    for family, count in sorted(family_counts.items()):
        typer.echo(f"  {family}: {count}")
    typer.echo(
        f"Anomalies relevées : {len(result.anomalies)}", err=bool(result.anomalies)
    )
    for kind, count in sorted(anomaly_counts.items()):
        typer.echo(f"  [{kind}] {count}", err=True)
    typer.echo(f"Écrit dans {output_path}")


# Échantillon stratifié par défaut (lot 6, I3) : au moins 60 documents,
# couvrant chacune des sept familles nommées par l'instruction du lot
# (U2, U4, U7, R, V, D, man_s). `man_s` (SU + SV réunies, 10 documents au
# total sur le corpus 17.4.0) est pris intégralement plutôt qu'échantillonné
# : c'est la plus petite famille et la seule non anticipée par
# docs/corpus.md §3 avant ce lot.
_DEFAULT_PROBE_SAMPLE = {
    "U2": 8,
    "U4": 10,
    "U7": 8,
    "R": 10,
    "V": 15,
    "D": 8,
    "man_s": 10,
}


@sources_app.command("probe")
def sources_probe() -> None:
    """Sonder le corpus documentaire avec docutils (lot 6, I3)."""
    project_root = _project_root()

    try:
        config = load_sources_config(default_sources_yaml_path(project_root))
    except SourcesConfigError as exc:
        typer.echo(f"Sonde échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    source = next((s for s in config.sources if s.name == "codeaster-doc"), None)
    manuals_family = source.families.get("manuals") if source else None
    if source is None or manuals_family is None or not manuals_family.paths:
        typer.echo(
            "Sonde échouée : source 'codeaster-doc' ou famille 'manuals' non "
            "déclarée dans config/sources.yaml",
            err=True,
        )
        raise typer.Exit(1)

    inventory_path = default_inventory_path(project_root)
    if not inventory_path.is_file():
        typer.echo(
            f"Sonde échouée : inventaire introuvable ({inventory_path}) ; "
            "lancez 'aster-expert sources inventory' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    manifest_path = default_manifest_path(project_root)
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    probe_manifest_sources = manifest_raw.get("sources", [])
    manifest_entry = next(
        (s for s in probe_manifest_sources if s.get("name") == "codeaster-doc"), None
    )
    if manifest_entry is None or not manifest_entry.get("commit"):
        typer.echo(
            "Sonde échouée : aucune révision synchronisée pour 'codeaster-doc' "
            "dans le manifeste",
            err=True,
        )
        raise typer.Exit(1)

    repo_root = project_root / source.local_path
    manuals_path = Path(manuals_family.paths[0])
    conf_py_path = repo_root / manuals_path.parent / "conf.py"
    if not conf_py_path.is_file():
        typer.echo(f"Sonde échouée : conf.py introuvable ({conf_py_path})", err=True)
        raise typer.Exit(1)

    report = build_probe_report(
        inventory_path=inventory_path,
        repo_root=repo_root,
        conf_py_path=conf_py_path,
        source_name=source.name,
        source_commit=manifest_entry["commit"],
        per_family=_DEFAULT_PROBE_SAMPLE,
    )

    output_path = default_probe_report_path(project_root)
    write_probe_report_json(report, output_path)

    typer.echo(f"Documents sondés : {report.sampled_documents}")
    typer.echo(f"Fichiers sondés  : {report.sampled_files}")
    typer.echo(f"Taux de récupération textuelle : {report.recovery_ratio * 100:.1f} %")
    typer.echo(f"Directives inconnues : {[d.name for d in report.unknown_directives]}")
    typer.echo(f"Rôles inconnus       : {[r.name for r in report.unknown_roles]}")
    typer.echo(
        f"Cibles include non résolues : {[i.name for i in report.unresolved_includes]}"
    )
    typer.echo(f"Extensions Sphinx déclarées (conf.py) : {report.conf_py_extensions}")
    if report.parse_errors:
        typer.echo(f"Erreurs d'analyse : {report.parse_errors}", err=True)
    typer.echo(f"Écrit dans {output_path}")


@sources_app.command("xref")
def sources_xref() -> None:
    """Établir le graphe de références croisées du corpus (lot 6, I4 ; lot 6b, X1)."""
    project_root = _project_root()

    try:
        config = load_sources_config(default_sources_yaml_path(project_root))
    except SourcesConfigError as exc:
        typer.echo(f"Graphe de références échoué : {exc}", err=True)
        raise typer.Exit(1) from exc

    source = next((s for s in config.sources if s.name == "codeaster-doc"), None)
    if source is None:
        typer.echo(
            "Graphe de références échoué : source 'codeaster-doc' non "
            "déclarée dans config/sources.yaml",
            err=True,
        )
        raise typer.Exit(1)

    inventory_path = default_inventory_path(project_root)
    if not inventory_path.is_file():
        typer.echo(
            f"Graphe de références échoué : inventaire introuvable "
            f"({inventory_path}) ; lancez 'aster-expert sources inventory' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    manifest_path = default_manifest_path(project_root)
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    xref_manifest_sources = manifest_raw.get("sources", [])
    manifest_entry = next(
        (s for s in xref_manifest_sources if s.get("name") == "codeaster-doc"), None
    )
    if manifest_entry is None or not manifest_entry.get("commit"):
        typer.echo(
            "Graphe de références échoué : aucune révision synchronisée pour "
            "'codeaster-doc' dans le manifeste",
            err=True,
        )
        raise typer.Exit(1)

    repo_root = project_root / source.local_path

    result = build_reference_graph_result(
        inventory_path=inventory_path,
        repo_root=repo_root,
        source_name=source.name,
        source_commit=manifest_entry["commit"],
    )

    output_path = default_xref_path(project_root)
    write_xref_json(result, output_path)

    total = result.total_references or 1
    typer.echo(f"Références relevées      : {result.total_references}")
    typer.echo(
        f"Résolues internes        : {result.internal_resolved_references} "
        f"({100 * result.internal_resolved_references / total:.1f} %)"
    )
    typer.echo(
        f"Externes (intersphinx)   : {result.external_references} "
        f"({100 * result.external_references / total:.1f} %)"
    )
    typer.echo(
        f"Ambiguës (autosectionlabel) : {result.ambiguous_references} "
        f"({100 * result.ambiguous_references / total:.1f} %)"
    )
    typer.echo(
        f"Réellement non résolues  : {result.unresolved_references} "
        f"({100 * result.unresolved_references / total:.1f} %)"
    )
    typer.echo(f"Arêtes distinctes         : {len(result.edges)}")
    typer.echo(f"Écrit dans {output_path}")


@sources_app.command("command-map")
def sources_command_map() -> None:
    """Établir la table commande -> document U4/U7 (lot 6, I5)."""
    project_root = _project_root()
    versions_path = project_root / "config" / "versions.yaml"

    inventory_path = default_inventory_path(project_root)
    if not inventory_path.is_file():
        typer.echo(
            f"Table commande -> document échouée : inventaire introuvable "
            f"({inventory_path}) ; lancez 'aster-expert sources inventory' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    try:
        digest = resolve_active_digest(versions_path)
    except CatalogueExtractionError as exc:
        typer.echo(f"Table commande -> document échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    catalogue_dir = project_root / "data" / "processed" / "catalogue" / digest
    if not catalogue_dir.is_dir():
        typer.echo(
            f"Table commande -> document échouée : catalogue introuvable "
            f"({catalogue_dir}) ; lancez 'aster-expert catalogue extract' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    manifest_path = default_manifest_path(project_root)
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    cmap_manifest_sources = manifest_raw.get("sources", [])
    manifest_entry = next(
        (s for s in cmap_manifest_sources if s.get("name") == "codeaster-doc"), None
    )
    if manifest_entry is None or not manifest_entry.get("commit"):
        typer.echo(
            "Table commande -> document échouée : aucune révision "
            "synchronisée pour 'codeaster-doc' dans le manifeste",
            err=True,
        )
        raise typer.Exit(1)

    documents = load_u4_u7_documents(inventory_path)
    catalogue_commands = load_catalogue_commands(catalogue_dir)

    result = build_command_mapping(
        documents,
        catalogue_commands,
        source_name="codeaster-doc",
        source_commit=manifest_entry["commit"],
    )

    output_path = default_command_map_path(project_root)
    write_command_mapping_json(result, output_path)

    rate = (
        100 * result.matched_catalogue_commands / result.total_catalogue_commands
        if result.total_catalogue_commands
        else 0.0
    )
    typer.echo(
        f"Commandes couvertes : {result.matched_catalogue_commands}/"
        f"{result.total_catalogue_commands} ({rate:.1f} %)"
    )
    typer.echo(f"Commandes sans document : {len(result.commands_without_document)}")
    typer.echo(f"{result.commands_without_document}")
    typer.echo(
        f"Documents U4/U7 sans commande : {len(result.documents_without_command)}"
    )
    typer.echo(
        "Documents nommant une commande documentée hors catalogue : "
        f"{len(result.documents_naming_uncatalogued_command)}"
    )
    typer.echo(f"Écrit dans {output_path}")


@catalogue_app.command("extract")
def catalogue_extract() -> None:
    """Extraire les schémas de commandes du catalogue installé."""
    project_root = _project_root()
    versions_path = project_root / "config" / "versions.yaml"
    if not versions_path.is_file():
        typer.echo(f"config/versions.yaml introuvable : {versions_path}", err=True)
        raise typer.Exit(1)

    workroot = _require_workroot()

    try:
        detected = _detect_from_env(workroot)
        write_detected_section(versions_path, detected)
        digest_dir, summary = extract_catalogue(
            detected=detected,
            workroot=workroot,
            output_root=project_root / "data" / "processed" / "catalogue",
            docker_bin_env=os.environ.get("ASTER_DOCKER_BIN") or None,
            network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
            memory=os.environ.get("ASTER_CONTAINER_MEMORY") or None,
            cpus=os.environ.get("ASTER_CONTAINER_CPUS") or None,
            timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
        )
    except (EnvironmentDetectionError, CatalogueExtractionError) as exc:
        typer.echo(f"Extraction du catalogue échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Commandes exposées  : {summary.total_exposed}")
    typer.echo(f"Commandes extraites : {summary.total_extracted}")
    typer.echo(f"Répartition par type : {summary.kind_counts}")
    typer.echo(f"Sans docu exploitable : {summary.commands_without_usable_docu}")
    if summary.anomalies:
        typer.echo(f"Anomalies relevées : {len(summary.anomalies)}", err=True)
        for anomaly in summary.anomalies:
            typer.echo(
                f"  - [{anomaly.kind}] {anomaly.command} : {anomaly.detail}", err=True
            )
    typer.echo(f"Écrit dans {digest_dir}")

    hard_errors = [a for a in summary.anomalies if a.kind == "extraction_error"]
    if hard_errors:
        raise typer.Exit(1)


@catalogue_app.command("show")
def catalogue_show(
    command: str,
    keyword: str = typer.Option(
        "",
        "--keyword",
        help="Chemin de mot-clé, ex. COMPORTEMENT.RELATION.",
    ),
) -> None:
    """Afficher le schéma exact d'une commande."""
    project_root = _project_root()
    versions_path = project_root / "config" / "versions.yaml"
    catalogue_root = project_root / "data" / "processed" / "catalogue"

    try:
        digest = resolve_active_digest(versions_path)
        schema = load_command_schema(catalogue_root, digest, command)
        if keyword:
            # Always a list, even for a single variant: `path` does not
            # identify a unique node (lot 4b, C1), so the shape must never
            # silently hide the fact that more variants could exist.
            variants = find_keyword_variants(schema, keyword.split("."))
            payload = [json.loads(v.model_dump_json()) for v in variants]
        else:
            payload = json.loads(schema.model_dump_json())
    except CatalogueExtractionError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False))


@comm_app.command("parse")
def comm_parse(comm_path: str) -> None:
    """Analyser la structure d'un fichier .comm sans jamais l'exécuter (lot 9)."""
    try:
        analysis = parse_comm_file(_lecture(comm_path, ".comm"))
    except CommParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(json.loads(analysis.model_dump_json()), indent=2, ensure_ascii=False)
    )

    dynamic_count = sum(1 for s in analysis.statements if s.dynamic)
    typer.echo(f"Commandes analysées : {len(analysis.statements)}", err=True)
    typer.echo(f"Commandes dynamic   : {dynamic_count}", err=True)
    typer.echo(f"Avertissements      : {len(analysis.parse_warnings)}", err=True)


def _default_questions_path(project_root: Path) -> Path:
    return project_root / "data" / "evaluations" / "questions.jsonl"


@eval_app.command("summary")
def eval_summary(
    questions_path: str = typer.Option(
        "", "--questions", help="Défaut : data/evaluations/questions.jsonl."
    ),
) -> None:
    """Compter les questions résolues/non résolues du jeu d'évaluation (lot 5)."""
    project_root = _project_root()
    path = (
        _lecture(questions_path, ".jsonl")
        if questions_path
        else _default_questions_path(project_root)
    )
    if not path.is_file():
        typer.echo(f"Jeu d'évaluation introuvable : {path}", err=True)
        raise typer.Exit(1)

    questions = load_questions(path)
    summary = summarize_question_set(questions)

    typer.echo(
        json.dumps(json.loads(summary.model_dump_json()), indent=2, ensure_ascii=False)
    )
    typer.echo(f"Total       : {summary.total}", err=True)
    typer.echo(f"Résolues    : {summary.resolved}", err=True)
    typer.echo(f"Non résolues: {summary.unresolved}", err=True)
    typer.echo(f"Hors corpus : {len(summary.outside_corpus_ids)}", err=True)


@eval_app.command("candidats")
def eval_candidats(
    sortie: str = typer.Option(
        "data/evaluations/questions_candidates.jsonl",
        "--sortie",
        help="Fichier JSONL des questions candidates (relatif à la racine).",
    ),
) -> None:
    """Questions candidates du banc (lot 42) : requêtes documentaires du journal
    qui n'ont pas trouvé de réponse utile (suivies d'une autre requête ou de la
    lecture d'un autre document), à valider par MM."""
    from aster_expert.mcp.logging import default_query_log_path
    from aster_expert.retrieval.candidates import (
        candidate_questions,
        known_questions,
        read_journal,
        write_candidates,
    )

    root = _project_root()
    entries, bad = read_journal(default_query_log_path(root))
    candidates = candidate_questions(
        entries, known=known_questions(_default_questions_path(root))
    )
    path = write_candidates(root / sortie, candidates)
    by_motive = Counter(c.motive for c in candidates)
    typer.echo(
        f"{len(entries)} appels lus ({bad} ligne(s) illisible(s) écartée(s)) ; "
        f"{len(candidates)} question(s) candidate(s) à valider par MM : "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_motive.items()))
        + f" -> {path.relative_to(root) if path.is_relative_to(root) else path}"
    )


@eval_app.command("score")
def eval_score(
    results_path: str,
    questions_path: str = typer.Option(
        "", "--questions", help="Défaut : data/evaluations/questions.jsonl."
    ),
    k: int = typer.Option(
        10, "--k", help="Profondeur de coupe pour recall@k/precision@k."
    ),
) -> None:
    """Calculer rappel et précision d'une liste de résultats classés (lot 5).

    `results_path` est un JSONL de `{"id": ..., "ranked_documents": [...]}`,
    utilisable avant qu'aucun index n'existe : ce n'est jamais le module qui
    produit ce classement, seulement celui qui le mesure.
    """
    project_root = _project_root()
    path = (
        _lecture(questions_path, ".jsonl")
        if questions_path
        else _default_questions_path(project_root)
    )
    if not path.is_file():
        typer.echo(f"Jeu d'évaluation introuvable : {path}", err=True)
        raise typer.Exit(1)
    results_file = _lecture(results_path, ".json", ".jsonl", kind=None)
    if not results_file.is_file():
        typer.echo(f"Résultats introuvables : {results_file}", err=True)
        raise typer.Exit(1)

    questions = load_questions(path)
    results = load_ranked_results(results_file)
    report = evaluate_retrieval(questions, results, k=k)

    typer.echo(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    typer.echo(
        f"Questions évaluées : {report.n_questions_evaluated}/"
        f"{report.n_questions_total} "
        f"({report.n_questions_excluded_unresolved} non résolues exclues)",
        err=True,
    )
    typer.echo(f"Hit@{k}       : {report.hit_rate_at_k * 100:.1f} %", err=True)
    typer.echo(f"Precision@{k} : {report.mean_precision_at_k * 100:.1f} %", err=True)
    typer.echo(f"Recall@{k}    : {report.mean_recall_at_k * 100:.1f} %", err=True)
    typer.echo(f"MRR          : {report.mean_reciprocal_rank:.3f}", err=True)


_FRAGMENT_GRANULARITIES = ("by_file", "by_subsection")


@eval_app.command("bench")
def eval_bench(
    granularity: str = typer.Option(
        "by_file", "--granularity", help="by_file ou by_subsection."
    ),
    k_values: str = typer.Option(
        "5,10,20", "--k", help="Profondeurs, séparées par des virgules."
    ),
    questions_path: str = typer.Option(
        "", "--questions", help="Défaut : data/evaluations/questions.jsonl."
    ),
    output_path: str = typer.Option(
        "", "--output", help="Chemin du rapport JSON à écrire."
    ),
    naive_baseline: bool = typer.Option(
        True,
        "--naive-baseline/--no-naive-baseline",
        help="Inclure la référence naïve (D6).",
    ),
) -> None:
    """Mesurer hit@k/recall@k/MRR ventilés sur le jeu d'évaluation (lot 7, D5/D6)."""
    project_root = _project_root()
    if granularity not in _FRAGMENT_GRANULARITIES:
        typer.echo(f"Granularité inconnue : {granularity}", err=True)
        raise typer.Exit(1)

    path = (
        _lecture(questions_path, ".jsonl")
        if questions_path
        else _default_questions_path(project_root)
    )
    if not path.is_file():
        typer.echo(f"Jeu d'évaluation introuvable : {path}", err=True)
        raise typer.Exit(1)

    index_dir = default_index_dir(project_root, granularity)  # type: ignore[arg-type]
    if not index_dir.is_dir():
        typer.echo(
            f"Banc échoué : index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    versions_path = project_root / "config" / "versions.yaml"
    aster_version = _resolve_aster_version_tag(versions_path)
    ks = tuple(int(x) for x in k_values.split(","))

    questions = load_questions(path)
    retriever, corpus = load_bm25_index(index_dir)

    report = run_granularity_bench(
        retriever,
        corpus,
        questions,
        granularity=granularity,
        fragment_count=len(corpus),
        version=aster_version,
        k_values=ks,
    )

    payload: dict[str, object] = {
        "granularity_report": json.loads(report.model_dump_json())
    }

    if naive_baseline:
        command_map_path = default_command_map_path(project_root)
        if not command_map_path.is_file():
            typer.echo(
                f"Table commande -> document introuvable ({command_map_path})", err=True
            )
            raise typer.Exit(1)
        documents_by_command = build_documents_by_command(command_map_path)
        baseline = run_naive_baseline_comparison(
            retriever,
            corpus,
            questions,
            documents_by_command,
            version=aster_version,
            k_values=ks,
        )
        payload["naive_baseline"] = json.loads(baseline.model_dump_json())

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    typer.echo(rendered)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Écrit dans {out}", err=True)

    reference = report.reports_by_k.get(10) or next(iter(report.reports_by_k.values()))
    typer.echo(
        f"[{granularity}] questions évaluées : {report.n_questions_evaluated} "
        f"({report.n_questions_excluded_unresolved} non résolues exclues)",
        err=True,
    )
    typer.echo(
        f"[{granularity}] hit@10 : {reference.hit_rate_at_k * 100:.1f} %", err=True
    )
    typer.echo(
        f"[{granularity}] MRR    : {reference.mean_reciprocal_rank:.3f}", err=True
    )


@eval_app.command("decompose")
def eval_decompose(
    profile: str = typer.Option(
        "syntaxe",
        "--profile",
        help=(
            "Profil de priorité des sources (config/retrieval.yaml, "
            "defaults.source_priority) : syntaxe, theorie ou methode. "
            "Jamais détecté automatiquement (lot 7b, E2 ; lot 7c, G1)."
        ),
    ),
    k_values: str = typer.Option(
        "5,10,20", "--k", help="Profondeurs, séparées par des virgules."
    ),
    questions_path: str = typer.Option(
        "", "--questions", help="Défaut : data/evaluations/questions.jsonl."
    ),
    output_path: str = typer.Option(
        "", "--output", help="Chemin du rapport JSON à écrire."
    ),
) -> None:
    """Décomposition du gain lot 7b (E4) : référence lot 7, E1, E1+E2a, E1+E2b.

    Compare, à granularité `by_file` fixe (consigne : ne pas changer la
    granularité par défaut du lot 7), l'index de référence du lot 7 et
    l'index enrichi E1 (`aster-expert index build --granularity by_file
    --enrich-text`, requis au préalable) sous les quatre variantes de la
    décomposition E4.
    """
    project_root = _project_root()
    path = (
        _lecture(questions_path, ".jsonl")
        if questions_path
        else _default_questions_path(project_root)
    )
    if not path.is_file():
        typer.echo(f"Jeu d'évaluation introuvable : {path}", err=True)
        raise typer.Exit(1)

    reference_dir = default_index_dir(project_root, "by_file")
    e1_dir = default_index_dir(project_root, "by_file", variant="e1")
    for label, index_dir, build_hint in (
        (
            "référence (lot 7)",
            reference_dir,
            "aster-expert index build --granularity by_file",
        ),
        (
            "E1 (enrichi)",
            e1_dir,
            "aster-expert index build --granularity by_file --enrich-text",
        ),
    ):
        if not index_dir.is_dir():
            typer.echo(
                f"Décomposition échouée : index {label} introuvable ({index_dir}) ; "
                f"lancez '{build_hint}' d'abord",
                err=True,
            )
            raise typer.Exit(1)

    retrieval_config_path = project_root / "config" / "retrieval.yaml"
    source_priority = load_source_priority(retrieval_config_path)
    if profile not in source_priority:
        typer.echo(
            f"Profil inconnu : {profile!r} ; profils déclarés dans "
            f"config/retrieval.yaml : {sorted(source_priority)}",
            err=True,
        )
        raise typer.Exit(1)
    priority_families = source_priority[profile]

    versions_path = project_root / "config" / "versions.yaml"
    aster_version = _resolve_aster_version_tag(versions_path)
    ks = tuple(int(x) for x in k_values.split(","))

    questions = load_questions(path)
    reference_retriever, reference_corpus = load_bm25_index(reference_dir)
    e1_retriever, e1_corpus = load_bm25_index(e1_dir)

    report = run_lot7b_decomposition(
        reference_retriever=reference_retriever,
        reference_corpus=reference_corpus,
        e1_retriever=e1_retriever,
        e1_corpus=e1_corpus,
        questions=questions,
        version=aster_version,
        priority_families=priority_families,
        granularity="by_file",
        k_values=ks,
    )

    rendered = json.dumps(
        json.loads(report.model_dump_json()), indent=2, ensure_ascii=False
    )
    typer.echo(rendered)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Écrit dans {out}", err=True)

    typer.echo(f"Profil de priorité : {profile} {priority_families}", err=True)
    typer.echo("Décomposition du gain (hit@k) :", err=True)
    for variant_name, variant_report in report.reports.items():
        row = " ".join(
            f"hit@{k}={variant_report.reports_by_k[k].hit_rate_at_k * 100:5.1f}%"
            for k in ks
            if k in variant_report.reports_by_k
        )
        typer.echo(f"  {variant_name:14s} {row}", err=True)

    if 10 in ks:
        typer.echo(
            "Cible : 85 % de hit@10 sur les questions d'answerability 'explicit' :",
            err=True,
        )
        for variant_name, variant_report in report.reports.items():
            explicit_bucket = variant_report.ventilation_by_answerability.get(
                10, {}
            ).get("explicit")
            if explicit_bucket is None:
                continue
            reached = explicit_bucket.hit_rate >= 0.85
            gap = (0.85 - explicit_bucket.hit_rate) * 100
            status = "atteinte" if reached else f"manque {gap:.1f} points"
            typer.echo(
                f"  {variant_name:14s} hit@10 explicit = "
                f"{explicit_bucket.hit_rate * 100:.1f} % "
                f"({explicit_bucket.n_questions} questions) -- {status}",
                err=True,
            )

    typer.echo("Impact sur les questions non 'explicit' (E3) :", err=True)
    for variant_name, impacts in report.non_explicit_impact.items():
        for impact in impacts:
            marker = (
                "="
                if impact.hit_at_k10_variant == impact.hit_at_k10_lot7_reference
                else ("+" if impact.hit_at_k10_variant else "-")
            )
            typer.echo(
                f"  {variant_name:14s} {marker} {impact.id} "
                f"({impact.answerability}) : "
                f"réf={impact.hit_at_k10_lot7_reference} "
                f"variante={impact.hit_at_k10_variant}",
                err=True,
            )


@eval_app.command("profile-bench")
def eval_profile_bench(
    granularity: str = typer.Option(
        "by_file", "--granularity", help="by_file ou by_subsection."
    ),
    mode: str = typer.Option(
        "soft", "--mode", help="soft (défaut) ou hard (lot 7b, E2)."
    ),
    default_profile: str = typer.Option(
        DEFAULT_QUERY_PROFILE,
        "--default-profile",
        help="Profil appliqué à toutes les questions pour la mesure 'plancher'.",
    ),
    k_values: str = typer.Option(
        "5,10,20", "--k", help="Profondeurs, séparées par des virgules."
    ),
    questions_path: str = typer.Option(
        "", "--questions", help="Défaut : data/evaluations/questions.jsonl."
    ),
    profiles_path: str = typer.Option(
        "", "--profiles", help="Défaut : data/evaluations/query_profiles.jsonl."
    ),
    output_path: str = typer.Option(
        "", "--output", help="Chemin du rapport JSON à écrire."
    ),
) -> None:
    """Lot 7c, G5 : plancher (un profil pour toutes les questions) contre
    réaliste (chaque question servie avec son profil annoté), sur l'index
    de référence (lot 7, sans enrichissement E1 -- lot 7c, G4 : mesuré sans
    gain net, retiré du chemin par défaut).
    """
    project_root = _project_root()
    if granularity not in _FRAGMENT_GRANULARITIES:
        typer.echo(f"Granularité inconnue : {granularity}", err=True)
        raise typer.Exit(1)
    if mode not in ("soft", "hard"):
        typer.echo(f"Mode de priorité inconnu : {mode!r}", err=True)
        raise typer.Exit(1)

    path = (
        _lecture(questions_path, ".jsonl")
        if questions_path
        else _default_questions_path(project_root)
    )
    if not path.is_file():
        typer.echo(f"Jeu d'évaluation introuvable : {path}", err=True)
        raise typer.Exit(1)

    profiles_file = (
        _lecture(profiles_path, ".jsonl")
        if profiles_path
        else default_query_profiles_path(project_root)
    )
    if not profiles_file.is_file():
        typer.echo(f"Annotations de profil introuvables : {profiles_file}", err=True)
        raise typer.Exit(1)

    index_dir = default_index_dir(project_root, granularity)  # type: ignore[arg-type]
    if not index_dir.is_dir():
        typer.echo(
            f"Banc échoué : index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    retrieval_config_path = project_root / "config" / "retrieval.yaml"
    source_priority = load_source_priority(retrieval_config_path)
    if default_profile not in source_priority:
        typer.echo(
            f"Profil inconnu : {default_profile!r} ; profils déclarés dans "
            f"config/retrieval.yaml : {sorted(source_priority)}",
            err=True,
        )
        raise typer.Exit(1)

    versions_path = project_root / "config" / "versions.yaml"
    aster_version = _resolve_aster_version_tag(versions_path)
    ks = tuple(int(x) for x in k_values.split(","))

    questions = load_questions(path)
    profile_by_question_id = load_query_profiles(profiles_file)
    retriever, corpus = load_bm25_index(index_dir)

    report = run_profile_routed_bench(
        retriever,
        corpus,
        questions,
        granularity=granularity,
        fragment_count=len(corpus),
        version=aster_version,
        profile_by_question_id=profile_by_question_id,
        source_priority_by_profile=source_priority,
        default_profile=default_profile,  # type: ignore[arg-type]
        mode=mode,  # type: ignore[arg-type]
        k_values=ks,
    )

    rendered = json.dumps(
        json.loads(report.model_dump_json()), indent=2, ensure_ascii=False
    )
    typer.echo(rendered)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Écrit dans {out}", err=True)

    typer.echo(
        f"Questions sans profil annoté (repli sur '{default_profile}') : "
        f"{report.unannotated_question_ids}",
        err=True,
    )
    for label, bench_report in (
        ("plancher", report.floor),
        ("réaliste", report.realistic),
    ):
        row = " ".join(
            f"hit@{k}={bench_report.reports_by_k[k].hit_rate_at_k * 100:5.1f}%"
            for k in ks
            if k in bench_report.reports_by_k
        )
        typer.echo(f"  {label:10s} {row}", err=True)

    if 10 in ks:
        typer.echo("Ventilation par profil (hit@10, réaliste) :", err=True)
        for prof, bucket in report.ventilation_by_profile[10].items():
            typer.echo(
                f"  {prof:10s} n={bucket.n_questions:2d} "
                f"hit@10={bucket.hit_rate * 100:.1f} %",
                err=True,
            )

        typer.echo("Échecs à k=10 (réaliste), avec le profil utilisé :", err=True)
        for failure in report.failures_at_k10_with_profile:
            typer.echo(
                f"  {failure.id:10s} [{failure.profile_used:8s}] {failure.domain} "
                f"requis={failure.required_documents}",
                err=True,
            )


@fragments_app.command("build")
def fragments_build(
    granularity: str = typer.Option(
        "both",
        "--granularity",
        help="by_file, by_subsection, ou both (les deux, l'une après l'autre).",
    ),
    threshold: int = typer.Option(
        DEFAULT_SUBSECTION_LINE_THRESHOLD,
        "--threshold",
        help="Seuil (lignes) au-delà duquel un fichier est redécoupé (by_subsection).",
    ),
) -> None:
    """Découper le corpus documentaire en fragments (lot 7, D1/D2)."""
    project_root = _project_root()
    inventory_path = default_inventory_path(project_root)
    if not inventory_path.is_file():
        typer.echo(
            f"Découpage échoué : inventaire introuvable ({inventory_path}) ; "
            "lancez 'aster-expert sources inventory' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    command_map_path = default_command_map_path(project_root)
    xref_path = default_xref_path(project_root)
    for path in (command_map_path, xref_path):
        if not path.is_file():
            typer.echo(f"Découpage échoué : introuvable ({path})", err=True)
            raise typer.Exit(1)

    versions_path = project_root / "config" / "versions.yaml"
    aster_version = _resolve_aster_version_tag(versions_path)
    repo_root = project_root / "external" / "codeaster-doc"

    granularities = _FRAGMENT_GRANULARITIES if granularity == "both" else (granularity,)
    for one_granularity in granularities:
        if one_granularity not in _FRAGMENT_GRANULARITIES:
            typer.echo(f"Granularité inconnue : {one_granularity}", err=True)
            raise typer.Exit(1)
        output_path = default_fragments_path(project_root, one_granularity)  # type: ignore[arg-type]
        summary = build_fragments_streaming(
            inventory_path=inventory_path,
            repo_root=repo_root,
            granularity=one_granularity,  # type: ignore[arg-type]
            aster_version=aster_version,
            command_map_path=command_map_path,
            xref_path=xref_path,
            output_path=output_path,
            subsection_line_threshold=threshold,
        )
        typer.echo(
            f"[{one_granularity}] documents traités : {summary.documents_processed}"
        )
        typer.echo(f"[{one_granularity}] fragments produits : {summary.fragment_count}")
        typer.echo(
            f"[{one_granularity}] taille médiane (car.) : "
            f"{summary.median_content_chars}"
        )
        typer.echo(f"[{one_granularity}] écrit dans {output_path}")


@index_app.command("build")
def index_build(
    granularity: str = typer.Option(
        "both", "--granularity", help="by_file, by_subsection, ou both."
    ),
    enrich_text: bool = typer.Option(
        False,
        "--enrich-text/--no-enrich-text",
        help=(
            "Lot 7b, E1 : enrichir le texte indexé (titre, section, "
            "commandes liées, mots-clés de premier niveau du catalogue), "
            "écrit dans un index distinct suffixé '_e1' — l'index de "
            "référence du lot 7 n'est jamais modifié par cette option."
        ),
    ),
) -> None:
    """Construire l'index lexical BM25 (lot 7, D4 ; lot 7b, E1 : --enrich-text)."""
    project_root = _project_root()
    granularities = _FRAGMENT_GRANULARITIES if granularity == "both" else (granularity,)
    for one_granularity in granularities:
        if one_granularity not in _FRAGMENT_GRANULARITIES:
            typer.echo(f"Granularité inconnue : {one_granularity}", err=True)
            raise typer.Exit(1)
        fragments_path = default_fragments_path(project_root, one_granularity)  # type: ignore[arg-type]
        if not fragments_path.is_file():
            typer.echo(
                f"Index échoué : fragments introuvables ({fragments_path}) ; "
                f"lancez 'aster-expert fragments build "
                f"--granularity {one_granularity}' d'abord",
                err=True,
            )
            raise typer.Exit(1)

        keyword_names_by_command = None
        if enrich_text:
            versions_path = project_root / "config" / "versions.yaml"
            aster_version = _resolve_aster_version_tag(versions_path)
            catalogue_root = project_root / "data" / "processed" / "catalogue"
            try:
                digest = resolve_digest_for_aster_version(catalogue_root, aster_version)
            except CatalogueExtractionError as exc:
                typer.echo(f"Index échoué (E1) : {exc}", err=True)
                raise typer.Exit(1) from exc
            commands = collect_related_commands(fragments_path)
            keyword_names_by_command = load_command_keyword_names(
                catalogue_root / digest, commands
            )

        index_dir = default_index_dir(
            project_root,
            one_granularity,  # type: ignore[arg-type]
            variant="e1" if enrich_text else None,
        )
        summary = build_bm25_index(
            fragments_path, index_dir, keyword_names_by_command=keyword_names_by_command
        )
        typer.echo(f"[{one_granularity}] fragments indexés : {summary.fragment_count}")
        typer.echo(f"[{one_granularity}] vocabulaire       : {summary.vocabulary_size}")
        typer.echo(f"[{one_granularity}] enrichissement    : {summary.text_enrichment}")
        typer.echo(f"[{one_granularity}] écrit dans {index_dir}")


@app.command("search")
def search(
    query: str,
    granularity: str = typer.Option(
        "by_file", "--granularity", help="by_file ou by_subsection (lot 7, D2)."
    ),
    version: str = typer.Option("", "--version", help="Filtre sur aster_version."),
    family: str = typer.Option(
        "", "--family", help="Filtre sur la famille documentaire."
    ),
    document: str = typer.Option(
        "", "--document", help="Filtre sur l'identifiant de document."
    ),
    command: str = typer.Option("", "--command", help="Filtre sur une commande liée."),
    section: str = typer.Option(
        "", "--section", help="Sous-chaîne du chemin de section."
    ),
    k: int = typer.Option(10, "--k", help="Nombre de résultats."),
    profile: str = typer.Option(
        DEFAULT_QUERY_PROFILE,
        "--profile",
        help=(
            "Profil de priorité des sources (config/retrieval.yaml, "
            "defaults.source_priority) : syntaxe, theorie ou methode. "
            "Toujours un paramètre explicite de l'appelant, jamais détecté "
            "depuis le texte de la requête (ADR-007)."
        ),
    ),
    priority_mode: str = typer.Option(
        "soft",
        "--priority-mode",
        help=(
            "soft (défaut, domine au banc du lot 7b/7c) ou hard : mode "
            "d'application du profil de priorité des sources."
        ),
    ),
) -> None:
    """Interroger le corpus documentaire (lot 7, D4 ; lot 7c, G1 : --profile)."""
    project_root = _project_root()
    if granularity not in _FRAGMENT_GRANULARITIES:
        typer.echo(f"Granularité inconnue : {granularity}", err=True)
        raise typer.Exit(1)
    if priority_mode not in ("soft", "hard"):
        typer.echo(f"Mode de priorité inconnu : {priority_mode!r}", err=True)
        raise typer.Exit(1)

    retrieval_config_path = project_root / "config" / "retrieval.yaml"
    source_priority = load_source_priority(retrieval_config_path)
    if profile not in source_priority:
        typer.echo(
            f"Profil inconnu : {profile!r} ; profils déclarés dans "
            f"config/retrieval.yaml : {sorted(source_priority)}",
            err=True,
        )
        raise typer.Exit(1)
    priority_families = source_priority[profile]

    index_dir = default_index_dir(project_root, granularity)  # type: ignore[arg-type]
    if not index_dir.is_dir():
        typer.echo(
            f"Recherche échouée : index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    retriever, corpus = load_bm25_index(index_dir)
    priority_search = (
        hard_filter_search if priority_mode == "hard" else soft_reweight_search
    )
    hits = priority_search(
        retriever,
        corpus,
        query,
        k=k,
        priority_families=priority_families,
        version=version or None,
        family=family or None,
        document_id=document or None,
        command=command or None,
        section_contains=section or None,
    )

    if not hits:
        typer.echo("Aucun résultat.", err=True)
        raise typer.Exit(0)

    typer.echo(
        f"Profil : {profile} {priority_families} (mode {priority_mode})", err=True
    )

    for hit in hits:
        typer.echo(
            f"{hit.score:.3f}  {hit.document_id}  "
            f"[{' / '.join(hit.section_path)}]  "
            f"{hit.source_path}@{hit.source_commit[:12]}"
        )
        typer.echo(f"    {hit.excerpt}")


@app.command("section")
def section(
    fragment_id: str = typer.Option(
        "",
        "--fragment-id",
        help=(
            "Identifiant exact d'un fragment, tel que renvoyé par "
            "'aster-expert search' (colonne document_id, valeur "
            "fragment_id sous-jacente)."
        ),
    ),
    document: str = typer.Option(
        "",
        "--document",
        help="Identifiant de document ; à combiner avec --section-path.",
    ),
    section_path: str = typer.Option(
        "",
        "--section-path",
        help=(
            "Chemin de section séparé par '/', identique au chemin affiché "
            "entre crochets par 'aster-expert search' (ex. "
            "'M_canique/Mécanique/Résolution')."
        ),
    ),
    granularity: str = typer.Option(
        "by_file",
        "--granularity",
        help=(
            "by_file ou by_subsection (lot 7, D2) ; doit correspondre à la "
            "granularité de la recherche d'origine."
        ),
    ),
    line_start: int = typer.Option(
        0,
        "--line-start",
        help=(
            "Ligne absolue de début (incluse), à donner avec --line-end. "
            "Sans plage, la section entière est demandée -- au-delà du "
            "seuil de taille, la réponse renvoie l'en-tête, le plan des "
            "sous-sections et la taille plutôt que le contenu (lot 14, L1)."
        ),
    ),
    line_end: int = typer.Option(
        0, "--line-end", help="Ligne absolue de fin (incluse), avec --line-start."
    ),
) -> None:
    """Texte d'un fragment/section, par défaut intégral (lot 8c K1 ; lot 14 L1)."""
    project_root = _project_root()
    if granularity not in _FRAGMENT_GRANULARITIES:
        typer.echo(f"Granularité inconnue : {granularity}", err=True)
        raise typer.Exit(1)

    has_fragment_id = bool(fragment_id)
    has_document = bool(document)
    has_section_path = bool(section_path)
    if has_fragment_id and (has_document or has_section_path):
        typer.echo(
            "Donner soit --fragment-id, soit --document et --section-path "
            "ensemble, jamais les deux à la fois.",
            err=True,
        )
        raise typer.Exit(1)
    if not has_fragment_id and (has_document != has_section_path):
        typer.echo(
            "--document et --section-path doivent être donnés ensemble.",
            err=True,
        )
        raise typer.Exit(1)
    if not has_fragment_id and not has_document:
        typer.echo(
            "--fragment-id, ou --document et --section-path, sont requis.",
            err=True,
        )
        raise typer.Exit(1)

    index_dir = default_index_dir(project_root, granularity)  # type: ignore[arg-type]
    if not index_dir.is_dir():
        typer.echo(
            f"Section introuvable : index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord",
            err=True,
        )
        raise typer.Exit(1)

    _, corpus = load_bm25_index(index_dir)
    section_path_tuple = tuple(section_path.split("/")) if has_section_path else None
    matches = find_fragments(
        corpus,
        fragment_id=fragment_id or None,
        document_id=document or None,
        section_path=section_path_tuple,
    )
    target = fragment_id or f"{document}#{section_path}"
    if not matches:
        typer.echo(
            f"Aucun fragment ne correspond à {target!r} dans l'index "
            f"{granularity!r} ({index_dir}).",
            err=True,
        )
        raise typer.Exit(1)
    if len(matches) > 1:
        typer.echo(
            f"Plusieurs fragments correspondent à {target!r} : identifiant "
            "ambigu, jamais résolu en silence -- utilisez --fragment-id.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        doc_section = to_document_section(
            matches[0],
            line_start=line_start or None,
            line_end=line_end or None,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(
            json.loads(doc_section.model_dump_json()), indent=2, ensure_ascii=False
        )
    )
    typer.echo(f"Taille totale : {doc_section.content_length} caractères", err=True)
    if doc_section.content is None:
        typer.echo(doc_section.guidance, err=True)


@app.command("validate")
def validate(
    comm_path: str,
    version: str = typer.Option(
        "",
        "--version",
        help=(
            "Version cible (ex. 17.4.0). À défaut, la dernière détection "
            "dans config/versions.yaml est utilisée. Échoue explicitement "
            "si aucun catalogue extrait ne correspond."
        ),
    ),
) -> None:
    """Valider un fichier de commandes contre le catalogue (niveau B)."""
    project_root = _project_root()
    workroot = _require_workroot()

    try:
        docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
        report = validate_comm_file(
            _lecture(comm_path, ".comm"),
            project_root=project_root,
            workroot=workroot,
            docker_bin=docker_bin,
            version=version or None,
            image_repository=os.environ.get(
                "ASTER_IMAGE_REPOSITORY", "simvia/code_aster"
            ),
            network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
            memory=os.environ.get("ASTER_CONTAINER_MEMORY") or None,
            cpus=os.environ.get("ASTER_CONTAINER_CPUS") or None,
            timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
        )
    except (EnvironmentDetectionError, ValidationRunError) as exc:
        typer.echo(f"Validation échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )

    n_checked = len(report.commands_checked)
    n_not_checked = len(report.commands_not_checked)
    n_total = n_checked + n_not_checked
    rate = 100 * n_checked / n_total if n_total else 0.0
    typer.echo(f"Niveau de validation : {report.validation_level}", err=True)
    typer.echo(
        f"Commandes vérifiées   : {n_checked}/{n_total} ({rate:.1f} %)", err=True
    )
    typer.echo(f"Commandes non vérifiées : {n_not_checked}", err=True)
    typer.echo(f"Erreurs remontées     : {len(report.errors)}", err=True)
    if report.warnings:
        typer.echo(f"Avertissements        : {len(report.warnings)}", err=True)

    typer.echo(f"Verdict               : {report.verdict}", err=True)
    for entry in report.commands_not_checked:
        typer.echo(
            f"  non vérifiée : {entry.command} (ligne {entry.line}) -- "
            f"{'; '.join(entry.reasons)}",
            err=True,
        )

    if report.errors:
        raise typer.Exit(1)
    if report.verdict == "partiel":
        # Lot 48 bis (A16) : une commande hors catalogue n'est jamais « valide ».
        raise typer.Exit(2)


@app.command("env-check")
def env_check() -> None:
    """Vérifier l'environnement : .venv, Docker, cave, Salomé, partage, MCP.

    Le profil (`vm`, `cloud` ou `ci`, lots 41 ter et 46 bis) est annoncé en tête ;
    en profil `cloud`, l'absence de `cave`, de Salomé et du dossier partagé est
    attendue ; en profil `ci` (GitHub Actions), celle du serveur MCP aussi, et
    `ASTER_IMAGE_REF` est obligatoire.
    """
    from aster_expert.environnement.verification import (
        CHECK_NAMES,
        CheckResult,
        EnvCheckError,
        detect_profile,
        from_machine,
        run_checks,
    )

    try:
        profile, reason = detect_profile()
        ctx = from_machine(_project_root())
    except EnvCheckError as exc:
        typer.echo(f"env-check ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Profil : {profile} ({reason})")
    passed: list[CheckResult] = []

    def show(result: CheckResult) -> None:
        passed.append(result)
        mark = "--" if result.expected_absent else "OK"
        typer.echo(f"  {mark} {result.name} : {result.detail}")

    try:
        run_checks(ctx, on_result=show)
    except EnvCheckError as exc:
        typer.echo(f"env-check ÉCHEC : {exc}", err=True)
        remaining = CHECK_NAMES[len(passed) + 1 :]
        if remaining:
            typer.echo(f"Non évalués : {', '.join(remaining)}", err=True)
        raise typer.Exit(1) from exc
    absent = sum(1 for result in passed if result.expected_absent)
    suffix = f", dont {absent} absences attendues" if absent else ""
    typer.echo(
        f"env-check OK (profil {profile}) : {len(passed)} vérifications{suffix}."
    )


@app.command("mcp-check")
def mcp_check() -> None:
    """Démarrer un serveur MCP neuf (comme `.mcp.json`) et appeler chaque outil."""
    import asyncio

    from aster_expert.mcp.check import McpCheckError, declared_tools, run_check

    project_root = _project_root()
    expected = declared_tools()
    typer.echo(
        f"Outils déclarés dans le code ({len(expected)}) : {', '.join(expected)}"
    )
    try:
        checks = asyncio.run(run_check(project_root, expected=expected))
    except McpCheckError as exc:
        typer.echo(f"mcp-check ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for check in checks:
        typer.echo(f"  OK {check.tool} {json.dumps(check.request)} -> {check.summary}")
    typer.echo(
        f"mcp-check OK : {len(checks)} outils appelés sur un serveur neuf, "
        "identiques aux outils du code."
    )


@app.command("run")
def run(
    comm_path: str,
    version: str = typer.Option(
        "",
        "--version",
        help=(
            "Version cible (ex. 17.4.0). À défaut, la dernière détection "
            "dans config/versions.yaml est utilisée."
        ),
    ),
    timeout: int = typer.Option(
        0,
        "--timeout",
        help=(
            "Délai maximal en secondes ; à défaut, P time_limit de l'.export, puis "
            "config/machine.local.yaml et config/validation.yaml, puis 86 400 s "
            "(défaut de run_aster)."
        ),
    ),
    memory_mb: int = typer.Option(
        0,
        "--memory-mb",
        help=(
            "Limite mémoire par processus MPI en Mio ; à défaut, P memory_limit de "
            "l'.export, puis la configuration, puis une part de la mémoire disponible."
        ),
    ),
) -> None:
    """Exécuter un fichier de commandes sous contrôle, dans le conteneur (niveau C)."""
    project_root = _project_root()
    versions_path = project_root / "config" / "versions.yaml"
    validation_config_path = project_root / "config" / "validation.yaml"
    catalogue_root = project_root / "data" / "processed" / "catalogue"

    try:
        exec_config = load_execution_config(validation_config_path)
        # Checked before resolving a catalogue digest: a file outside the
        # allowed roots is refused on its own terms (lot 11, O2), never
        # blocked behind an unrelated "no catalogue extracted yet" error.
        check_allowed(Path(comm_path), config=exec_config, project_root=project_root)
        digest, aster_version = resolve_digest_for_version(
            catalogue_root, version or None, versions_path
        )
        docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
        planned = plan_resources(
            Path(comm_path).resolve(),
            config=exec_config,
            project_root=project_root,
            timeout_seconds=timeout or None,
            memory_mb=memory_mb or None,
        )
        typer.echo(f"Ressources : {planned.summary()}")
        report = execute_comm_file(
            Path(comm_path),
            project_root=project_root,
            config=exec_config,
            docker_bin=docker_bin,
            image_repository=os.environ.get(
                "ASTER_IMAGE_REPOSITORY", "simvia/code_aster"
            ),
            image_digest=digest,
            aster_version=aster_version,
            network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
            timeout_seconds=timeout or None,
            memory_mb=memory_mb or None,
        )
    except (EnvironmentDetectionError, ExecutionRunError, ValidationRunError) as exc:
        typer.echo(f"Exécution échouée : {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )

    typer.echo(f"Statut         : {report.status}", err=True)
    if report.diag:
        typer.echo(f"Diagnostic     : {report.diag}", err=True)
    typer.echo(f"Répertoire     : {report.work_dir}", err=True)
    if report.mess_path:
        typer.echo(f".mess          : {report.mess_path}", err=True)
    typer.echo(f"Fichiers produits : {len(report.result_files)}", err=True)
    if report.duration_s is not None:
        typer.echo(f"Durée          : {report.duration_s:.1f} s", err=True)

    if report.status not in ("completed_ok", "completed_with_alarms"):
        _show_diagnostics(Path(report.work_dir))
        raise typer.Exit(1)


def _show_diagnostics(work_dir: Path) -> None:
    """Lot 42 : diagnostics of the knowledge base matching a failed run, read
    from its compte rendu (written only when the work directory is kept)."""
    from aster_expert.execution.compte_rendu import REPORT_JSON, load_record

    if not (work_dir / REPORT_JSON).is_file():
        return
    record = load_record(work_dir)
    if record.diagnostics_error:
        typer.echo(f"Diagnostics     : {record.diagnostics_error}", err=True)
    elif not record.diagnostics:
        typer.echo(
            "Diagnostics     : aucun diagnostic connu ne correspond (échec à classer "
            "au retour d'expérience, aster-expert rex).",
            err=True,
        )
    for d in record.diagnostics:
        typer.echo(
            f"Diagnostic connu : {d.diagnostic_id} [{d.status}] {d.title} -- "
            f"correction : {d.correction} ({d.file})",
            err=True,
        )


@mesh_app.command("run")
def mesh_run(
    script: Path,
    params: str = typer.Option(
        "",
        "--params",
        help="Fichier de paramètres JSON passé au script (empreinte vérifiée).",
    ),
) -> None:
    """Exécuter un script Salomé sans interface (config/validation.yaml, mesh)."""
    from aster_expert.meshing.config import load_mesh_config
    from aster_expert.meshing.errors import MeshError
    from aster_expert.meshing.run import run_salome_script

    project_root = _project_root()
    try:
        config = load_mesh_config(project_root / "config" / "validation.yaml")
        report = run_salome_script(
            _lecture(script, ".py"),
            project_root=project_root,
            config=config,
            params=_lecture(params, ".json") if params else None,
        )
    except MeshError as exc:
        typer.echo(f"mesh run ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    if report.from_cache:
        typer.echo(
            "MED déjà vérifié par mesh check pour cette empreinte "
            "script/paramètres : Salomé non relancé.",
            err=True,
        )
    typer.echo(f"MED produit : {report.med_path}", err=True)
    typer.echo(f"Journal     : {report.log_path}", err=True)


@mesh_app.command("check")
def mesh_check(
    med: str = typer.Argument("", help="MED à vérifier."),
    invariants: str = typer.Argument("", help="Fichier d'invariants (YAML)."),
    projet: str = typer.Option(
        "",
        "--projet",
        help=(
            "Projet : ses invariants, et le MED de son étape `maillage` à défaut de "
            "MED donné."
        ),
    ),
    version: str = typer.Option(
        "",
        "--version",
        help="Version cible (ex. 17.4.0) de l'image lisant le MED.",
    ),
) -> None:
    """Vérifier un MED contre un fichier d'invariants (medcoupling, sans Salomé)."""
    from aster_expert.meshing.check import check_med
    from aster_expert.meshing.config import load_mesh_config
    from aster_expert.meshing.errors import MeshError

    project_root = _project_root()
    med_path = _lecture(med, ".med") if med else None
    invariants_path = _lecture(invariants, ".yaml", ".yml") if invariants else None
    if projet:
        from aster_expert.projet.pipeline import load_state

        ctx = _load_project_or_exit("mesh check", projet)
        invariants_path = invariants_path or ctx.path(ctx.declaration.mesh.invariants)
        if med_path is None:
            known = load_state(ctx).mesh_med
            med_path = Path(known) if known else None
    if med_path is None or invariants_path is None:
        typer.echo(
            "mesh check ÉCHEC : donner le MED et le fichier d'invariants, ou "
            "--projet <nom> (après son étape `maillage`)",
            err=True,
        )
        raise typer.Exit(1)
    try:
        config = load_mesh_config(project_root / "config" / "validation.yaml")
        digest, _aster_version = resolve_digest_for_version(
            project_root / "data" / "processed" / "catalogue",
            version or None,
            project_root / "config" / "versions.yaml",
        )
        docker_bin = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
        repository = os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")
        report = check_med(
            med_path,
            invariants_path,
            project_root=project_root,
            config=config,
            docker_bin=docker_bin,
            image_ref=f"{repository}@{digest}",
        )
    except (MeshError, EnvironmentDetectionError, ValidationRunError) as exc:
        typer.echo(f"mesh check ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(Path(report.report_path).read_text(encoding="utf-8"), nl=False)
    typer.echo(f"Rapport : {report.report_path}", err=True)
    if not report.ok:
        raise typer.Exit(1)


def _load_project_or_exit(
    command: str,
    projet: str,
    *,
    fiche: str = "",
    donnees: str = "",
) -> ProjectContext:
    """The project context, or a readable refusal (`<commande> ÉCHEC : ...`)."""
    from aster_expert.projet.context import load_project
    from aster_expert.projet.errors import ProjectError

    try:
        return load_project(
            projet,
            _project_root(),
            fiche=_lecture(fiche) if fiche else None,
            data=_lecture(donnees) if donnees else None,
        )
    except ProjectError as exc:
        typer.echo(f"{command} ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command("report")
def report(
    resultat: Path,
    projet: str = typer.Option(
        ...,
        "--projet",
        help="Projet (projets/<nom>/projet.yaml) dont le calcul est synthétisé.",
    ),
    donnees: str = typer.Option(
        "",
        "--donnees",
        help="Fichier de données du modèle exécuté (défaut : celui du projet).",
    ),
    comm: str = typer.Option(
        "", "--comm", help="`.comm` exécuté (empreinte consignée dans la synthèse)."
    ),
    controles_d: str = typer.Option(
        "",
        "--controles-d",
        help=(
            "JSON d'équilibre des contrôles D (`aster-expert projet <nom> controles`)."
        ),
    ),
    sortie: str = typer.Option(
        "", "--sortie", help="Répertoire de sortie (par défaut : celui du résultat)."
    ),
    med: str = typer.Option(
        "",
        "--med",
        help="MED de résultats (défaut : proc.0/fort.80 de l'exécution).",
    ),
    etiquette: str = typer.Option(
        "", "--etiquette", help="Étiquette portée par le titre des vues (`base`, `V1`)."
    ),
    sans_vues: bool = typer.Option(
        False, "--sans-vues", help="Ne pas produire les vues PNG."
    ),
) -> None:
    """Synthèse d'un calcul, par l'extension de synthèse déclarée par le projet.

    `resultat` : le répertoire d'exécution (`aster-expert run`) ou son listing
    `.mess`. Le tronc commun ne sait rien de l'ouvrage : il vérifie la déclaration
    (données du même ouvrage, extension présente) puis appelle l'extension du
    projet, qui écrit ses propres fichiers (par exemple `synthese.md`, `controles.md`,
    `synthese.json`, vues PNG)."""
    from aster_expert.projet.check import FOR_REPORT, require_valid_project
    from aster_expert.projet.errors import ProjectError

    ctx = _load_project_or_exit("report", projet, donnees=donnees)
    resultat = _lecture(resultat, kind="either")
    try:
        require_valid_project(ctx, FOR_REPORT)
        if ctx.declaration.synthesis is None:
            message = f"le projet {ctx.declaration.name} ne déclare pas de synthèse"
            raise ProjectError(message)
        run_dir = resultat if resultat.is_dir() else resultat.parent
        lines = ctx.extension(ctx.declaration.synthesis.extension)(
            ctx,
            result=resultat,
            out_dir=Path(sortie) if sortie else run_dir,
            data_path=_lecture(donnees) if donnees else ctx.data_path,
            comm_path=_lecture(comm, ".comm") if comm else None,
            level_d_path=_lecture(controles_d, ".json") if controles_d else None,
            med_path=_lecture(med) if med else None,
            label=etiquette,
            views=not sans_vues,
        )
    except (ProjectError, ValueError, OSError, KeyError) as exc:
        typer.echo(f"report ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in lines:
        typer.echo(line, err=True)


@app.command("generate")
def generate(
    projet: str,
    fiche: str = typer.Option("", "--fiche", help="Fiche (défaut : celle du projet)."),
    donnees: str = typer.Option(
        "", "--donnees", help="Fichier de données (défaut : celui du projet)."
    ),
    maillage: str = typer.Option(
        "",
        "--maillage",
        help="MED vérifié (défaut : celui de l'étape `maillage` du projet).",
    ),
    sortie: str = typer.Option(
        "", "--sortie", help="Fichier .comm écrit (défaut : `comm.output` du projet)."
    ),
) -> None:
    """Générer le .comm d'un projet par le générateur qu'il déclare.

    Refusé, avec la liste des motifs, si la déclaration ne correspond pas à ses
    fichiers (données d'un autre ouvrage, donnée exigée par le générateur absente,
    groupe absent du maillage, cas sans résultante attendue) ou si la fiche porte
    un bloqueur de génération."""
    from aster_expert.projet.errors import ProjectError
    from aster_expert.projet.pipeline import Runtime
    from aster_expert.projet.pipeline import generate as generate_project

    ctx = _load_project_or_exit("generate", projet, fiche=fiche, donnees=donnees)
    try:
        target, report_data = generate_project(
            ctx,
            Runtime(_project_root()),
            med=_lecture(maillage, ".med") if maillage else None,
            output=Path(sortie) if sortie else None,
        )
    except ProjectError as exc:
        typer.echo(f"generate ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps(report_data, indent=2, ensure_ascii=False))
    typer.echo(f".comm écrit dans {target}", err=True)


@app.command("projet")
def projet(
    nom: str,
    etape: str = typer.Argument(
        "verifier",
        help=(
            "verifier, maillage, generer, valider, executer, controles, synthese, "
            "combinaisons, ferraillage, livrables, ou tout (toutes, dans l'ordre) ; "
            "livraison (dépôt avec empreintes, --dossier, --verifier)."
        ),
    ),
    sans_vues: bool = typer.Option(
        False, "--sans-vues", help="Synthèse sans les vues PNG."
    ),
    sous_etape: str = typer.Option(
        "",
        "--sous-etape",
        help=(
            "livrables : une seule sous-étape (preparer, executer, verifier, traiter, "
            "charges, vues, ingenieur, images, classeur ; charges_avance : par son "
            "nom seulement)."
        ),
    ),
    ncpus: int = typer.Option(
        0,
        "--ncpus",
        help=(
            "livrables : fils de l'exécution de post-traitement (défaut : règle du "
            "lot 49, processeurs ÷ exécutions simultanées)."
        ),
    ),
    simultanees: int = typer.Option(
        1,
        "--simultanees",
        help="livrables : nombre d'exécutions lancées en même temps (règle des fils).",
    ),
    dossier: str = typer.Option(
        "",
        "--dossier",
        help=(
            "livraison : dossier de dépôt des livrables (classeur, flexion composée, "
            "diagrammes, comparaison) avec leur manifeste d'empreintes SHA-256."
        ),
    ),
    verifier_livraison: bool = typer.Option(
        False,
        "--verifier",
        help=(
            "livraison : relire le dossier et signaler tout fichier modifié, absent "
            "ou ajouté depuis la livraison (code 1)."
        ),
    ),
    modele: str = typer.Option(
        "",
        "--modele",
        help=(
            "livrables : modèle dérivé déclaré (engineering_summary.derived_models, "
            "lot 49 ter) au lieu de la référence ; sous-étapes preparer, executer, "
            "verifier, traiter, controler."
        ),
    ),
    description: str = typer.Option(
        "Ouvrage à décrire.", "--description", help="projet creer : description."
    ),
    sans_regeneration: bool = typer.Option(
        False,
        "--sans-regeneration",
        help="projet exporter-resultats : ne pas régénérer le .comm pour le comparer.",
    ),
    reevaluer: bool = typer.Option(
        False,
        "--reevaluer",
        help=(
            "projet exporter-resultats : ré-appliquer la règle de conservation des "
            "niveaux et les signalements de critères au paquet existant, à partir de "
            "ses seuls fichiers (sans archive d'exécution, utilisable dans le Cloud)."
        ),
    ),
) -> None:
    """Enchaîner les commandes existantes sur un projet (`projets/<nom>/`).

    Chaque étape écrit sous le répertoire de résultats du projet et consigne dans
    `etat.json` ce qu'elle a produit ; une étape seule reprend ce que les
    précédentes ont laissé. Aucune étape ne s'exécute sur une déclaration
    refusée.

    `aster-expert projet creer <nom>` (lot 44) crée un projet : arborescence,
    `projet.yaml` minimal, racines d'exécution dans config/validation.yaml et
    registre rex.

    `aster-expert projet exporter-resultats <nom>` (lot 45) écrit le paquet de
    résultats versionnable du projet (tableaux, figures, empreintes, niveau
    atteint ; jamais de MED) dans `resultats/paquet/`."""
    from aster_expert.projet.errors import ProjectError
    from aster_expert.projet.pipeline import Runtime, run_step

    if nom == "creer":
        _create_project(etape, description)
        return
    if nom == "exporter-resultats":
        _export_results(etape, regenerate=not sans_regeneration, reevaluate=reevaluer)
        return
    ctx = _load_project_or_exit("projet", nom)
    try:
        if etape == "livraison":
            from aster_expert.livrables.livraison import run as deliver  # noqa: PLC0415

            if not dossier:
                message = "livraison : --dossier <chemin> exigé"
                raise ProjectError(message)
            lines = deliver(ctx, Path(dossier), check=verifier_livraison)
        elif etape == "livrables":
            from aster_expert.execution.regle_fils import threads_for  # noqa: PLC0415
            from aster_expert.projet.pipeline import step_livrables  # noqa: PLC0415

            lines = step_livrables(
                ctx,
                Runtime(_project_root()),
                only=sous_etape or None,
                ncpus=ncpus or threads_for(_project_root(), simultanees),
                model=modele or None,
            )
        else:
            lines = run_step(ctx, Runtime(_project_root()), etape, views=not sans_vues)
    except ProjectError as exc:
        typer.echo(f"projet {nom} {etape} ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in lines:
        typer.echo(line)


def _export_results(name: str, *, regenerate: bool, reevaluate: bool = False) -> None:
    from aster_expert.projet.errors import ProjectError
    from aster_expert.projet.paquet import export_results, reevaluate_package
    from aster_expert.projet.pipeline import Runtime

    ctx = _load_project_or_exit("projet exporter-resultats", name)
    try:
        if reevaluate:
            section = ctx.declaration.results_package
            if section is None:
                message = f"le projet {name} ne déclare pas de paquet de résultats"
                raise ProjectError(message)
            result = reevaluate_package(
                ctx.results_dir / section.output, ctx.repo_root, ctx
            )
        else:
            result = export_results(
                ctx, Runtime(_project_root()), regenerate=regenerate
            )
    except ProjectError as exc:
        typer.echo(f"projet exporter-resultats {name} ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in result.lines:
        typer.echo(line)


def _create_project(name: str, description: str) -> None:
    from aster_expert.projet.creation import create_project
    from aster_expert.projet.errors import ProjectError

    root = _project_root()
    try:
        created = create_project(root, name, description=description)
    except ProjectError as exc:
        typer.echo(f"projet creer ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Projet créé : {created.project_dir.relative_to(root)}")
    for path in created.files:
        typer.echo(f"  {path.relative_to(root)}")
    for r in created.roots_added:
        typer.echo(f"Racine d'exécution ajoutée (config/validation.yaml) : {r}")
    typer.echo(f"Registre rex : {created.registry.relative_to(root)}")
    typer.echo(f"Suite : aster-expert projet {name} verifier (liste ce qui manque).")


constats_app = typer.Typer(
    no_args_is_help=True,
    help="Base partagée des constats Code_Aster (connaissances/constats_code_aster).",
)
app.add_typer(constats_app, name="constats")

resultats_app = typer.Typer(
    help=(
        "Interroger les résultats livrés d'un projet (lot 49) : lecture des tableaux "
        "des livrables, jamais de mémoire ni par script jetable."
    ),
    no_args_is_help=True,
)
app.add_typer(resultats_app, name="resultats")


@resultats_app.command("lire")
def resultats_lire(
    projet: str,
    groupe: list[str] = typer.Option(  # noqa: B008
        [], "--groupe", help="Groupe de mailles ou de nœuds (répétable)."
    ),
    champ: str = typer.Option(
        "", "--champ", help="Clé du champ livré (DEPL, EFGE_NOEU, EFGE_ELNO_2...)."
    ),
    noeuds: str = typer.Option(
        "", "--noeuds", help="Groupe de nœuds portant chaque ligne (ET avec --groupe)."
    ),
    composante: list[str] = typer.Option(  # noqa: B008
        [], "--composante", help="Composante (répétable)."
    ),
    cas: list[str] = typer.Option(  # noqa: B008
        [],
        "--cas",
        help="Cas élémentaire, combinaison (par son nom) ou « enveloppe » (répétable).",
    ),
    mode: str = typer.Option(
        "extremum", "--mode", help="extremum, point, coupe, somme ou tout."
    ),
    point: str = typer.Option("", "--point", help="mode point : x,y[,z] (m)."),
    coupe: str = typer.Option("", "--coupe", help="mode coupe : AXE=valeur (ex. Y=0)."),
    tolerance: float = typer.Option(
        1.0e-6, "--tolerance", help="mode coupe : tolérance (m)."
    ),
    sans_disques: bool = typer.Option(
        False,
        "--sans-disques",
        help="Ne pas appliquer les disques d'exclusion déclarés (PAT-013).",
    ),
    disque_groupe: str = typer.Option(
        "", "--disque-groupe", help="Centres d'un disque d'exclusion (groupe de nœuds)."
    ),
    disque_rayon: float = typer.Option(
        0.0, "--disque-rayon", help="Rayon du disque d'exclusion (m)."
    ),
    limite: int = typer.Option(100000, "--limite", help="Nombre maximal de lignes."),
    sortie: str = typer.Option("", "--sortie", help="Écrire le CSV dans ce fichier."),
) -> None:
    """Lire les résultats livrés d'un projet : CSV (valeurs SI et affichées, lieu,
    combinaison et position mobile qui gouvernent) et une ligne de provenance."""
    from aster_expert.livrables.lecture import Query, query
    from aster_expert.projet.errors import ProjectError

    if mode not in ("extremum", "point", "coupe", "somme", "tout"):
        typer.echo(f"resultats lire ÉCHEC : mode inconnu {mode}", err=True)
        raise typer.Exit(1)
    ctx = _load_project_or_exit("resultats lire", projet)
    try:
        answer = query(
            ctx,
            Query(
                groupes=tuple(groupe),
                noeuds=noeuds or None,
                champ=champ or None,
                composantes=tuple(composante),
                cas=tuple(cas),
                mode=mode,  # type: ignore[arg-type]
                point=tuple(float(x) for x in point.split(",")) if point else None,
                coupe=coupe or None,
                tolerance=tolerance,
                disques=not sans_disques,
                disque_groupe=disque_groupe or None,
                disque_rayon=disque_rayon or None,
                limite=limite,
            ),
        )
    except (ProjectError, ValueError) as exc:
        typer.echo(f"resultats lire ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    text = answer.csv()
    if sortie:
        Path(sortie).write_text(text, encoding="utf-8")
        typer.echo(f"{len(answer.rows)} ligne(s) écrites dans {sortie}", err=True)
    else:
        typer.echo(text, nl=False)
    typer.echo(answer.provenance, err=True)


@constats_app.command("chercher")
def constats_chercher(
    texte: str = typer.Argument("", help="Texte libre (tous les mots)."),
    commande: str = typer.Option("", "--commande", help="Commande du catalogue."),
    mot_cle: str = typer.Option(
        "", "--mot-cle", help="Mot-clé ou valeur du catalogue."
    ),
    limite: int = typer.Option(20, "--limite"),
) -> None:
    """Chercher des constats par commande, mot-clé ou texte."""
    from aster_expert.constats.base import ConstatBaseError, base_dir, load_base
    from aster_expert.constats.search import search_constats

    try:
        base = load_base(base_dir(_project_root()))
        hits = search_constats(
            base,
            text=texte or None,
            command=commande or None,
            keyword=mot_cle or None,
            limit=limite,
        )
    except (ConstatBaseError, ValueError) as exc:
        typer.echo(f"constats chercher ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for hit in hits:
        c = hit.constat
        typer.echo(f"{c.constat_id} [niveau {c.validation_level}] {c.summary}")
    typer.echo(f"{len(hits)} constat(s) sur {len(base)}.", err=True)


@constats_app.command("rejouer")
def constats_rejouer(
    constat: list[str] | None = typer.Option(  # noqa: B008
        None, "--constat", help="Identifiant(s) CA-nnn ; défaut : tous."
    ),
    sortie: str = typer.Option(
        "", "--sortie", help="Rapport JSON (défaut : data/processed/rejeu_constats)."
    ),
) -> None:
    """Rejouer, dans le conteneur, les cas d'essai des constats établis par
    exécution, et vérifier que chaque valeur obtenue est encore imprimée.

    Code de sortie 1 si un constat est à réexaminer (valeur absente, exécution en
    échec, cas modifié) ; code 2 si un cas est non rejouable tel que versionné
    (lot 48 bis : jamais un succès)."""
    from aster_expert.constats.rejeu import ReplayError, replay_base

    root = _project_root()
    try:
        result = replay_base(
            root,
            only=tuple(constat or ()),
            output_dir=Path(sortie) if sortie else None,
        )
    except ReplayError as exc:
        typer.echo(f"constats rejouer ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in result.lines():
        typer.echo(line)
    if result.to_review:
        raise typer.Exit(1)
    if result.not_replayable:
        # Lot 48 bis (A15) : un cas non rejouable n'est plus un succès silencieux.
        typer.echo(
            f"constats rejouer : non rejouable(s) : {', '.join(result.not_replayable)}",
            err=True,
        )
        raise typer.Exit(2)


connaissances_app = typer.Typer(
    no_args_is_help=True,
    help="Base de connaissances : six couches sous connaissances/ (lot 42).",
)
app.add_typer(connaissances_app, name="connaissances")


def _load_knowledge_or_exit() -> KnowledgeBase:
    from aster_expert.connaissances.base import KnowledgeBaseError, load_knowledge

    try:
        return load_knowledge(_project_root())
    except KnowledgeBaseError as exc:
        typer.echo(f"connaissances ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc


@connaissances_app.command("chercher")
def connaissances_chercher(
    texte: str = typer.Argument("", help="Texte libre (tous les mots)."),
    commande: str = typer.Option("", "--commande", help="Commande du catalogue."),
    mot_cle: str = typer.Option("", "--mot-cle", help="Mot-clé ou valeur."),
    couche: list[str] | None = typer.Option(  # noqa: B008
        None, "--couche", help="Couche(s) : constats_code_aster, diagnostics, …"
    ),
    statut: str = typer.Option("", "--statut", help="observé, établi ou promu."),
    limite: int = typer.Option(20, "--limite"),
) -> None:
    """Chercher dans les six couches par texte, commande, mot-clé, couche, statut."""
    from aster_expert.connaissances.recherche import search_knowledge

    base = _load_knowledge_or_exit()
    try:
        hits = search_knowledge(
            base,
            text=texte or None,
            command=commande or None,
            keyword=mot_cle or None,
            layers=tuple(couche or ()),
            status=statut or None,
            limit=limite,
        )
    except ValueError as exc:
        typer.echo(f"connaissances chercher ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for hit in hits:
        e = base.get(hit.entry_id)
        assert e is not None
        typer.echo(
            f"{e.id} [{hit.layer}, {e.status}, niveau {e.validation_level}] {e.summary}"
        )
    typer.echo(f"{len(hits)} entrée(s).", err=True)


@connaissances_app.command("verifier")
def connaissances_verifier() -> None:
    """Charger la base (schémas, références croisées, niveaux) et confronter ses
    preuves au dépôt (cas et empreintes, tests, code, documents, exécutions)."""
    from aster_expert.connaissances.base import verify_against_repository

    base = _load_knowledge_or_exit()
    for layer, row in base.counts().items():
        total = sum(row.values())
        detail = ", ".join(f"{k} {v}" for k, v in row.items())
        typer.echo(f"{layer} : {total} ({detail})")
    for a in base.anomalies:
        signatures = ", ".join(sig.entry for sig in a.signatures)
        typer.echo(f"Anomalie {a.status} {a.id} ({signatures}) : {a.title}")
    check = verify_against_repository(base)
    typer.echo(f"Preuves confrontées au dépôt : {check.checked}.")
    if check.unverifiable:
        typer.echo(
            f"Exécutions archivées non vérifiables (archives absentes) : "
            f"{len(check.unverifiable)}."
        )
    for problem in check.problems:
        typer.echo(f"  ÉCART {problem}")
    if check.problems:
        typer.echo(f"connaissances verifier ÉCHEC : {len(check.problems)} écart(s).")
        raise typer.Exit(1)
    typer.echo("connaissances verifier OK.")


@connaissances_app.command("promouvoir")
def connaissances_promouvoir(
    identifiant: str,
    motif: str = typer.Option(..., "--motif", help="Motif de la promotion."),
    par: str = typer.Option("MM", "--par", help="Auteur de la promotion."),
) -> None:
    """Promouvoir une entrée établie au statut promu, si elle a été réutilisée
    avec succès dans au moins deux projets ou validée au niveau E. Échoue sinon."""
    from aster_expert.connaissances.base import KnowledgeBaseError
    from aster_expert.connaissances.promotion import PromotionRefusedError, promote

    try:
        typer.echo(promote(_project_root(), identifiant, by=par, reason=motif))
    except (PromotionRefusedError, KnowledgeBaseError) as exc:
        typer.echo(f"promotion refusée : {exc}", err=True)
        raise typer.Exit(1) from exc


@connaissances_app.command("eligibilite")
def connaissances_eligibilite(
    toutes: bool = typer.Option(
        False, "--toutes", help="Lister aussi les entrées sans aucune réutilisation."
    ),
) -> None:
    """Rejouer la règle de promotion (lot 44) sur toutes les entrées : une
    réutilisation ne compte que si le projet l'a éprouvée (exécution réussie ou test
    versionné) ; une citation dans une fiche ne compte pas. Rien n'est écrit."""
    from aster_expert.connaissances.promotion import eligibility

    rows = eligibility(_project_root())
    shown = [
        r for r in rows if toutes or r.eligible or r.cited_by or len(r.proved_in) > 1
    ]
    for r in shown:
        mark = "ÉLIGIBLE" if r.eligible else "non"
        cited = f" ; cité sans épreuve : {', '.join(r.cited_by)}" if r.cited_by else ""
        typer.echo(
            f"{r.id} [{r.status}, niveau {r.validation_level}] {mark} -- éprouvé : "
            f"{', '.join(r.proved_in) or '-'}{cited} -- {r.reason}"
        )
    eligible = [r.id for r in rows if r.eligible]
    typer.echo(
        f"{len(rows)} entrées ; éligibles : {len(eligible)} "
        f"({', '.join(eligible) or 'aucune'})."
    )


@connaissances_app.command("eprouver")
def connaissances_eprouver(
    execution: str = typer.Argument(
        ..., help="Répertoire d'exécution ou identifiant (data/processed/runs/<id>)."
    ),
    enregistrer: bool = typer.Option(
        False,
        "--enregistrer",
        help=(
            "Inscrire une réutilisation éprouvée sur chaque entrée reconnue "
            "(jamais une promotion)."
        ),
    ),
) -> None:
    """Épreuve des connaissances déclarées par une exécution (lot 46) : constat,
    précédent et diagnostic ne s'éprouvent pas par déclaration ; patron et contrôle
    exigent une exécution réussie aux contrôles D réussis sur ses propres résultats ;
    référence, le rejeu réussi d'un de ses cas. Code 1 si l'exécution ne porte aucune
    déclaration."""
    from aster_expert.connaissances.base import KnowledgeBaseError, load_knowledge
    from aster_expert.connaissances.epreuve import evaluate_run, record_proofs

    root = _project_root()
    run_dir = Path(execution)
    if not run_dir.is_dir():
        run_dir = root / "data" / "processed" / "runs" / execution
    run_dir = _lecture(run_dir, kind="dir")
    try:
        base = load_knowledge(root)
        verdicts = evaluate_run(root, run_dir, base)
    except (KnowledgeBaseError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"connaissances eprouver ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    if not verdicts:
        typer.echo(
            "Aucune déclaration dans cette exécution : rien n'est éprouvé "
            "(pas d'attribution rétroactive).",
            err=True,
        )
        raise typer.Exit(1)
    for v in verdicts:
        state = f"ÉPROUVÉ (niveau {v.level})" if v.proven else "non éprouvé"
        typer.echo(f"{v.entry_id} [{v.layer}] : {state} -- {v.reason}")
    if enregistrer:
        for path in record_proofs(root, run_dir, verdicts, base):
            typer.echo(f"Réutilisation éprouvée inscrite : {path.relative_to(root)}")


@connaissances_app.command("proposer-precedent")
def connaissances_proposer_precedent(
    identifiant: str,
    point: str = typer.Option(..., "--point", help="Point de la nouvelle fiche."),
) -> None:
    """Écrire (sortie standard, JSON) la proposition d'un précédent pour une
    nouvelle fiche : une entrée pratique NON TRANCHÉE et la source
    `precedent_projet` que MM pourra citer s'il le retient. Rien n'est appliqué."""
    from aster_expert.connaissances.modeles import Precedent
    from aster_expert.connaissances.precedents import propose_precedent

    base = _load_knowledge_or_exit()
    entry = base.entries.get(identifiant)
    if not isinstance(entry, Precedent):
        typer.echo(f"{identifiant} n'est pas un précédent de la base", err=True)
        raise typer.Exit(1)
    proposal, source = propose_precedent(entry, point_label=point)
    typer.echo(
        json.dumps(
            {
                "entree_proposee": json.loads(proposal.model_dump_json()),
                "source_si_retenu": json.loads(source.model_dump_json()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    typer.echo(
        "Proposition seulement : l'entrée reste non tranchée (bloqueur de "
        "génération) jusqu'à l'arbitrage de MM.",
        err=True,
    )


@connaissances_app.command("rejouer-references")
def connaissances_rejouer_references(
    reference: list[str] | None = typer.Option(  # noqa: B008
        None, "--reference", help="Identifiant(s) REF-nnn ; défaut : toutes."
    ),
    sortie: str = typer.Option("", "--sortie", help="Répertoire du rapport."),
) -> None:
    """Rejouer, dans le conteneur, les cas des références de validation et
    vérifier que chaque valeur enregistrée est de nouveau imprimée."""
    from aster_expert.connaissances.references import replay_references
    from aster_expert.constats.rejeu import ReplayError

    try:
        result = replay_references(
            _project_root(),
            only=tuple(reference or ()),
            output_dir=Path(sortie) if sortie else None,
        )
    except ReplayError as exc:
        typer.echo(f"rejeu des références ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in result.lines():
        typer.echo(line)
    if result.to_review:
        raise typer.Exit(1)
    if result.not_replayable:
        # Lot 48 bis (A15) : un cas non rejouable n'est plus un succès silencieux.
        typer.echo(
            f"rejeu des références : non rejouable(s) : "
            f"{', '.join(result.not_replayable)}",
            err=True,
        )
        raise typer.Exit(2)


etat_app = typer.Typer(
    no_args_is_help=True,
    help="État du projet lisible par la machine, docs/etat.yaml (lot 46).",
)
app.add_typer(etat_app, name="etat")


@etat_app.command("readme")
def etat_readme() -> None:
    """Réécrire la section « État du projet » du README depuis docs/etat.yaml."""
    from aster_expert import etat

    try:
        changed = etat.update_readme(_project_root())
    except (etat.StateError, ValueError) as exc:
        typer.echo(f"etat readme ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo("README.md mis à jour." if changed else "README.md déjà à jour.")


@etat_app.command("verifier")
def etat_verifier() -> None:
    """Contrôler docs/etat.yaml : schéma, fichiers cités, commits, README généré."""
    from aster_expert import etat

    root = _project_root()
    try:
        problems = [*etat.check_references(root), *etat.check_readme(root)]
    except (etat.StateError, ValueError) as exc:
        typer.echo(f"etat verifier ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for problem in problems:
        typer.echo(f"  {problem}", err=True)
    if problems:
        raise typer.Exit(1)
    typer.echo("docs/etat.yaml cohérent (schéma, fichiers cités, commits, README).")


fiche_app = typer.Typer(
    no_args_is_help=True,
    help="Fiche d'hypothèses : contrôles à la rédaction (lot 44).",
)
app.add_typer(fiche_app, name="fiche")


@fiche_app.command("obligatoires")
def fiche_obligatoires(
    fiche: Path,
    donnees: str = typer.Option(
        "", "--donnees", help="Fichier de données du modèle (YAML)."
    ),
    sortie: str = typer.Option(
        "", "--sortie", help="Écrire la fiche complétée des questions (JSON)."
    ),
    version: str = typer.Option("", "--version", help="Version Code_Aster."),
) -> None:
    """Lister les mots-clés obligatoires des commandes prévues par la fiche
    (`planned_commands`) que ni une donnée ni une question ne couvrent : catalogue
    de la version cible, puis table des obligations d'exécution
    (data/config/obligations_execution.yaml). Avec --sortie, chaque mot-clé manquant
    devient une question non tranchée de la fiche, dans sa catégorie (MM ou choix
    de l'agent). Code 1 s'il en manque."""
    from aster_expert.agent.hypotheses import HypothesesSheet
    from aster_expert.agent.model_data import load_model_data
    from aster_expert.agent.obligatoires import (
        add_missing_parameters,
        default_rules_path,
        load_execution_rules,
        missing_parameters,
    )

    root = _project_root()
    catalogue_root = root / "data" / "processed" / "catalogue"
    try:
        sheet = HypothesesSheet.model_validate_json(
            _lecture(fiche, ".json").read_text(encoding="utf-8")
        )
        data = load_model_data(_lecture(donnees)) if donnees else None
        rules = load_execution_rules(default_rules_path(root))
        digest, aster_version = resolve_digest_for_version(
            catalogue_root, version or None, root / "config" / "versions.yaml"
        )
        if aster_version != rules.aster_version:
            message = (
                f"table des obligations d'exécution écrite pour {rules.aster_version}, "
                f"catalogue {aster_version} : versions mêlées refusées"
            )
            raise ValueError(message)
        schemas = {
            p.command: load_command_schema(catalogue_root, digest, p.command)
            for p in sheet.planned_commands
        }
        uninterpreted: list[str] = []
        exempt: list[str] = []
        missing = missing_parameters(
            sheet, data, schemas, rules, uninterpreted, without_question=exempt
        )
    except (OSError, ValueError, ValidationRunError, CatalogueExtractionError) as exc:
        typer.echo(f"fiche obligatoires ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    planned = len(sheet.planned_commands)
    typer.echo(f"Commandes prévues : {planned} ; catalogue {aster_version}.")
    by_keyword: dict[str, int] = {}
    for condition in uninterpreted:
        keyword = condition.split(" : ", 1)[0]
        by_keyword[keyword] = by_keyword.get(keyword, 0) + 1
    for keyword, count in sorted(by_keyword.items()):
        typer.echo(
            f"  NON INTERPRÉTÉE {keyword} ({count} condition(s) inconnue(s) du "
            "lecteur : le mot-clé n'est compté ni obligatoire ni absent)"
        )
    for line in sorted(set(exempt)):
        typer.echo(f"  SANS QUESTION {line}")
    for parameter in missing:
        typer.echo(f"  MANQUE {parameter.label()}")
    if sortie:
        augmented = add_missing_parameters(sheet, missing)
        Path(sortie).write_text(
            json.dumps(augmented.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        typer.echo(
            f"Fiche complétée : {sortie} "
            f"({len(augmented.entries) - len(sheet.entries)} question(s) ajoutée(s))."
        )
    if missing:
        raise typer.Exit(1)
    typer.echo("Aucun paramètre obligatoire sans donnée ni question.")


@fiche_app.command("prevoir")
def fiche_prevoir(
    projet: str,
    comm: str = typer.Option(
        "",
        "--comm",
        help="`.comm` à lire (défaut : la sortie déclarée du projet).",
    ),
    ecrire: bool = typer.Option(
        False, "--ecrire", help="Écrire `planned_commands` dans la fiche du projet."
    ),
    couvrir: list[str] = typer.Option(  # noqa: B008
        [],
        "--couvrir",
        help=(
            "Couverture explicite d'un mot-clé obligatoire, COMMANDE/MOT_CLE=cible "
            "(data:<groupe.clé> ou point:<p>) ; répétable. Une couverture est une "
            "décision : la cible doit exister (vérifié par fiche obligatoires)."
        ),
    ),
) -> None:
    """Déduire de la `.comm` d'un projet les commandes prévues de sa fiche
    (`planned_commands`, lot 48 bis) : une par commande et par combinaison d'options
    écrites en clair que le catalogue teste ; aucune couverture n'est déduite, mais
    celles que la fiche porte déjà sont conservées et --couvrir en ajoute (lot 49).
    Sans --ecrire, la liste est seulement affichée."""
    from aster_expert.agent.hypotheses import HypothesesSheet
    from aster_expert.agent.prevues import (
        apply_coverages,
        derive_planned_commands,
        write_planned_commands,
    )

    ctx = _load_project_or_exit("fiche prevoir", projet)
    source = _lecture(comm) if comm else ctx.path(ctx.declaration.comm.output)
    if not source.is_file():
        typer.echo(
            f"fiche prevoir ÉCHEC : {source} introuvable (générer le `.comm` ou "
            "passer --comm).",
            err=True,
        )
        raise typer.Exit(1)
    try:
        planned, skipped = derive_planned_commands(
            ctx.fiche_path, source, _project_root()
        )
        previous = HypothesesSheet.model_validate_json(
            ctx.fiche_path.read_text(encoding="utf-8")
        ).planned_commands
        planned = apply_coverages(planned, previous, tuple(couvrir))
        if ecrire:
            write_planned_commands(ctx.fiche_path, planned)
    except (OSError, ValueError, ValidationRunError, CatalogueExtractionError) as exc:
        typer.echo(f"fiche prevoir ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for p in planned:
        options = ", ".join(f"{k}={v}" for k, v in sorted(p.options.items()))
        covered = ", ".join(f"{k} ← {v}" for k, v in sorted(p.covered_by.items()))
        typer.echo(
            f"  {p.command} (point {p.point_label}){' : ' + options if options else ''}"
            f"{' ; couvert : ' + covered if covered else ''}"
        )
    typer.echo(
        f"{len(planned)} commande(s) prévue(s) ; "
        f"sans schéma : {', '.join(skipped) or 'aucune'}."
    )
    if ecrire:
        typer.echo(f"planned_commands écrit dans {ctx.fiche_path}.")


@fiche_app.command("enregistrer")
def fiche_enregistrer(
    projet: str,
    arbitrage: str,
    simuler: bool = typer.Option(
        False, "--simuler", help="Afficher ce qui serait enregistré, sans écrire."
    ),
) -> None:
    """Enregistrer dans la fiche d'un projet les décisions d'un fichier d'arbitrage
    structuré (lot 48 bis ; format : `aster_expert.agent.enregistrement`). Le texte
    cité de chaque décision doit figurer à l'identique dans le fichier source de
    MM ; la décision passe par `record_practice_decision` (une décision déjà
    tranchée est conservée dans l'historique). Remplace les scripts de lot."""
    from aster_expert.agent.enregistrement import (
        RecordingError,
        check_quotes,
        parse_arbitration,
        record_decisions,
    )
    from aster_expert.agent.hypotheses import HypothesesSheet

    ctx = _load_project_or_exit("fiche enregistrer", projet)
    try:
        arbitration = parse_arbitration(_lecture(arbitrage).read_text(encoding="utf-8"))
        source = ctx.path(arbitration.source)
        if not source.is_file():
            message = f"fichier source du texte introuvable : {source}"
            raise RecordingError(message)
        check_quotes(arbitration, source.read_text(encoding="utf-8"))
        sheet = HypothesesSheet.model_validate_json(
            ctx.fiche_path.read_text(encoding="utf-8")
        )
        sheet, done = record_decisions(sheet, arbitration)
    except (OSError, ValueError) as exc:
        typer.echo(f"fiche enregistrer ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in done:
        typer.echo(f"  {line}")
    if simuler:
        typer.echo("Simulation : fiche non modifiée.")
        return
    ctx.fiche_path.write_text(
        json.dumps(json.loads(sheet.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    typer.echo(f"{len(done)} décision(s) enregistrée(s) dans {ctx.fiche_path}.")


@app.command("rex")
def rex(
    projet: str,
    enregistrer: bool = typer.Option(
        False, "--enregistrer", help="Inscrire la revue dans le registre du projet."
    ),
    lot: str = typer.Option("", "--lot", help="Lot de la revue (avec --enregistrer)."),
    manifeste: bool = typer.Option(
        False,
        "--manifeste",
        help=(
            "Enregistrer le manifeste de l'archive d'exécution (VM, archive complète) "
            "dans le registre du projet ; refusé si l'archive contredit un manifeste "
            "déjà enregistré."
        ),
    ),
) -> None:
    """Retour d'expérience d'un projet (lot 42) : échecs à classer, constats à
    verser, candidats patrons, métriques et tableau de bord. Code 1 si un échec
    n'est pas classé (la clôture du lot est bloquée).

    Lot 46 : les métriques mesurées ne sont écrites que si l'archive d'exécution est
    conforme au manifeste du registre. Absente, partielle (Cloud) ou non conforme,
    l'archive est refusée avec son motif et seuls les champs déclarés (interventions,
    erreurs évitées, notes) sont mis à jour ; le code de sortie reste 0."""
    from aster_expert.connaissances.base import KnowledgeBaseError
    from aster_expert.connaissances.rex import (
        record_manifest,
        record_review,
        render_report,
        review_project,
        write_dashboard,
        write_declared_metrics,
        write_metrics,
    )

    root = _project_root()
    if enregistrer and not lot:
        typer.echo("rex : --enregistrer exige --lot", err=True)
        raise typer.Exit(2)
    if manifeste:
        try:
            recorded = record_manifest(root, projet)
        except (FileNotFoundError, ValueError, KnowledgeBaseError) as exc:
            typer.echo(f"rex --manifeste ÉCHEC : {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(
            f"Manifeste enregistré : {recorded.runs} exécution(s) du projet, "
            f"empreinte {recorded.sha256[:16]}…"
        )
    try:
        report = review_project(root, projet)
    except (FileNotFoundError, ValueError, KnowledgeBaseError) as exc:
        typer.echo(f"rex ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    for line in render_report(report):
        typer.echo(line)
    if report.archives_present:
        path = write_metrics(root, report.metrics)
        typer.echo(f"Métriques : {path.relative_to(root)}")
        dashboard = write_dashboard(root)
        typer.echo(f"Tableau de bord : {dashboard.relative_to(root)}")
        if enregistrer:
            registry = record_review(root, report, lot=lot)
            typer.echo(f"Revue inscrite : {registry.relative_to(root)}")
            record_manifest(root, projet)
    else:
        path = write_declared_metrics(root, report.metrics)
        typer.echo(f"Champs déclarés seuls mis à jour : {path.relative_to(root)}")
        write_dashboard(root)
        if enregistrer:
            typer.echo("Revue non inscrite : archive d'exécution refusée.")
    if report.blocking:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()


note_app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Notes Word génériques d'un projet (lot 45) : hypothèses et résultats, "
        "dans projets/<nom>/livrables/notes/."
    ),
)
app.add_typer(note_app, name="note")


def _note_output(ctx: ProjectContext, kind: str, sortie: str) -> Path:
    from aster_expert.notes.hypotheses import NOTE_NAME as HYPOTHESES_NAME
    from aster_expert.notes.resultats import NOTE_NAME as RESULTS_NAME

    if sortie:
        return Path(sortie)
    name = HYPOTHESES_NAME if kind == "hypotheses" else RESULTS_NAME
    return ctx.project_dir / "livrables" / "notes" / name


def _print_check(check: NoteCheck) -> None:
    status = "OK" if check.ok else "ÉCHEC"
    typer.echo(f"Contrôle de {check.note} : {status}")
    for key, value in sorted(check.counts.items()):
        typer.echo(f"  {key} : {value}")
    for problem in check.problems:
        typer.echo(f"  PROBLÈME {problem}")


def _build_and_check_note(
    kind: str, projet: str, sortie: str, sans_controle: bool
) -> None:
    from aster_expert.notes.controle import check_hypotheses_note, check_results_note
    from aster_expert.notes.hypotheses import build_hypotheses_note
    from aster_expert.notes.resultats import build_results_note
    from aster_expert.projet.errors import ProjectError

    ctx = _load_project_or_exit(f"note {kind}", projet)
    target = _note_output(ctx, kind, sortie)
    try:
        if kind == "hypotheses":
            build_hypotheses_note(ctx, target)
        else:
            build_results_note(ctx, target)
    except ProjectError as exc:
        typer.echo(f"note {kind} {projet} ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Note écrite : {target} ({target.stat().st_size} octets)")
    if sans_controle:
        return
    check = (
        check_hypotheses_note(ctx, target)
        if kind == "hypotheses"
        else check_results_note(ctx, target)
    )
    _print_check(check)
    if not check.ok:
        raise typer.Exit(1)


@note_app.command("hypotheses")
def note_hypotheses(
    projet: str = typer.Argument(..., help="Nom du projet (projets/<nom>/)."),
    sortie: str = typer.Option("", "--sortie", help="Chemin du .docx à écrire."),
    sans_controle: bool = typer.Option(False, "--sans-controle"),
) -> None:
    """Note d'hypothèses : fiche, données et convention de nommage (lot 45)."""
    _build_and_check_note("hypotheses", projet, sortie, sans_controle)


@note_app.command("resultats")
def note_resultats(
    projet: str = typer.Argument(..., help="Nom du projet (projets/<nom>/)."),
    sortie: str = typer.Option("", "--sortie", help="Chemin du .docx à écrire."),
    sans_controle: bool = typer.Option(False, "--sans-controle"),
) -> None:
    """Note de résultats, lue dans le paquet de résultats du projet (lot 45)."""
    _build_and_check_note("resultats", projet, sortie, sans_controle)


@note_app.command("controler")
def note_controler(
    projet: str = typer.Argument(..., help="Nom du projet (projets/<nom>/)."),
) -> None:
    """Contrôler les deux notes déjà écrites d'un projet (lot 45)."""
    from aster_expert.notes.controle import check_hypotheses_note, check_results_note

    ctx = _load_project_or_exit("note controler", projet)
    failed = False
    for kind, check in (
        ("hypotheses", check_hypotheses_note),
        ("resultats", check_results_note),
    ):
        path = _note_output(ctx, kind, "")
        if not path.is_file():
            typer.echo(f"Note absente : {path}", err=True)
            failed = True
            continue
        result = check(ctx, path)
        _print_check(result)
        failed = failed or not result.ok
    if failed:
        raise typer.Exit(1)
