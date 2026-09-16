"""Command line entry point.

Every subcommand that is not implemented yet fails loudly and names the batch
("lot") in which it is scheduled. Nothing here guesses a Code_Aster version or
an installation path.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import typer

from aster_expert import __version__
from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.extract import extract_catalogue
from aster_expert.catalogue.query import (
    find_keyword_variants,
    load_command_schema,
    resolve_active_digest,
)
from aster_expert.execution.detect import detect_environment, write_detected_section
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.execution.models import DetectedEnvironment
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
from aster_expert.parsing.errors import CommParseError
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.validate import validate_comm_file

app = typer.Typer(
    add_completion=False,
    help="Agent expert Code_Aster : corpus, catalogue, validation, exécution.",
)

env_app = typer.Typer(no_args_is_help=True, help="Environnement Code_Aster.")
sources_app = typer.Typer(no_args_is_help=True, help="Dépôts sources.")
catalogue_app = typer.Typer(no_args_is_help=True, help="Catalogue des commandes.")
comm_app = typer.Typer(no_args_is_help=True, help="Fichiers de commandes .comm.")
app.add_typer(env_app, name="env")
app.add_typer(sources_app, name="sources")
app.add_typer(catalogue_app, name="catalogue")
app.add_typer(comm_app, name="comm")


def _not_implemented(batch: int, what: str) -> None:
    """Fail explicitly rather than returning an empty or fabricated result."""
    typer.echo(f"Non implémenté : {what} (lot {batch}).", err=True)
    raise typer.Exit(1)


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
    """Établir le graphe de références croisées du corpus (lot 6, I4)."""
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

    rate = (
        100 * result.resolvable_references / result.total_references
        if result.total_references
        else 0.0
    )
    typer.echo(f"Références relevées   : {result.total_references}")
    typer.echo(
        f"Résolubles             : {result.resolvable_references} ({rate:.1f} %)"
    )
    typer.echo(f"Non résolubles         : {result.unresolvable_references}")
    typer.echo(f"Arêtes distinctes       : {len(result.edges)}")
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
        "Documents nommant une commande MacroCommands hors catalogue : "
        f"{len(result.documents_naming_known_macro_command)}"
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
        analysis = parse_comm_file(Path(comm_path))
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


@app.command("search")
def search(query: str) -> None:
    """Interroger le corpus documentaire."""
    _not_implemented(7, f"recherche dans le corpus : {query}")


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
            Path(comm_path),
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

    if report.errors:
        raise typer.Exit(1)


@app.command("run")
def run(comm_path: str) -> None:
    """Exécuter un fichier de commandes sous contrôle (niveau C)."""
    _not_implemented(12, f"exécution de {comm_path}")


if __name__ == "__main__":
    app()
