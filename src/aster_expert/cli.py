"""Command line entry point.

Every subcommand that is not implemented yet fails loudly and names the batch
("lot") in which it is scheduled. Nothing here guesses a Code_Aster version or
an installation path.
"""

from __future__ import annotations

import json
import os
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
from aster_expert.ingestion.errors import SourcesConfigError
from aster_expert.ingestion.sync import default_manifest_path, sync_sources
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
