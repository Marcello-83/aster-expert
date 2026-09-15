"""Command line entry point.

Every subcommand that is not implemented yet fails loudly and names the batch
("lot") in which it is scheduled. Nothing here guesses a Code_Aster version or
an installation path.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from aster_expert import __version__
from aster_expert.execution.detect import detect_environment, write_detected_section
from aster_expert.execution.errors import EnvironmentDetectionError

app = typer.Typer(
    add_completion=False,
    help="Agent expert Code_Aster : corpus, catalogue, validation, exécution.",
)

env_app = typer.Typer(no_args_is_help=True, help="Environnement Code_Aster.")
sources_app = typer.Typer(no_args_is_help=True, help="Dépôts sources.")
catalogue_app = typer.Typer(no_args_is_help=True, help="Catalogue des commandes.")
app.add_typer(env_app, name="env")
app.add_typer(sources_app, name="sources")
app.add_typer(catalogue_app, name="catalogue")


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


@env_app.command("detect")
def env_detect() -> None:
    """Détecter l'installation Code_Aster et écrire config/versions.yaml."""
    project_root = Path(os.environ.get("ASTER_EXPERT_ROOT") or Path.cwd())
    versions_path = project_root / "config" / "versions.yaml"
    if not versions_path.is_file():
        typer.echo(f"config/versions.yaml introuvable : {versions_path}", err=True)
        raise typer.Exit(1)

    workroot_raw = (os.environ.get("ASTER_CONTAINER_WORKROOT") or "").strip()
    if not workroot_raw:
        typer.echo(
            "ASTER_CONTAINER_WORKROOT n'est pas renseigné : aucune introspection "
            "n'est autorisée sans répertoire de travail dédié (voir .env.example).",
            err=True,
        )
        raise typer.Exit(1)

    try:
        detected = detect_environment(
            workroot=Path(workroot_raw),
            image_repository=os.environ.get(
                "ASTER_IMAGE_REPOSITORY", "simvia/code_aster"
            ),
            image_ref_env=os.environ.get("ASTER_IMAGE_REF") or None,
            docker_bin_env=os.environ.get("ASTER_DOCKER_BIN") or None,
            network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
            memory=os.environ.get("ASTER_CONTAINER_MEMORY") or None,
            cpus=os.environ.get("ASTER_CONTAINER_CPUS") or None,
            timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
        )
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
    _not_implemented(3, "synchronisation des dépôts")


@catalogue_app.command("extract")
def catalogue_extract() -> None:
    """Extraire les schémas de commandes du catalogue installé."""
    _not_implemented(4, "introspection du catalogue")


@catalogue_app.command("show")
def catalogue_show(command: str) -> None:
    """Afficher le schéma exact d'une commande."""
    _not_implemented(4, f"affichage du schéma de {command}")


@app.command("search")
def search(query: str) -> None:
    """Interroger le corpus documentaire."""
    _not_implemented(7, f"recherche dans le corpus : {query}")


@app.command("validate")
def validate(comm_path: str) -> None:
    """Valider un fichier de commandes contre le catalogue (niveau B)."""
    _not_implemented(10, f"validation statique de {comm_path}")


@app.command("run")
def run(comm_path: str) -> None:
    """Exécuter un fichier de commandes sous contrôle (niveau C)."""
    _not_implemented(12, f"exécution de {comm_path}")


if __name__ == "__main__":
    app()
