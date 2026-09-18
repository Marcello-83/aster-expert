"""MCP server (lot 8): registers the four tools over `aster_expert.mcp.tools`.

This module carries no business logic (CLAUDE.md, lot 8 scope): it only
reads the same environment variables `aster_expert.cli` reads (never
diverging from it) and wires them to `aster_expert.mcp.tools`, whose
functions do the actual work and the actual journaling
(`aster_expert.mcp.logging`). A tool's description is the only place a
caller is told how to use it (H1, "la description doit dire à l'appelant
comment choisir son profil") — nothing here infers a choice on the
caller's behalf.

Run with `aster-expert-mcp` (stdio transport, the only one a Claude Code
`claude mcp add` stdio declaration needs — see README.md for the exact
command verified on this machine).
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from aster_expert import __version__
from aster_expert.mcp import tools
from aster_expert.mcp.models import (
    CommAnalysisResult,
    CommandSchemaResult,
    SearchDocsResult,
)
from aster_expert.retrieval.query_profiles import DEFAULT_QUERY_PROFILE
from aster_expert.validation.models import ValidationReport


def _project_root() -> Path:
    return Path(os.environ.get("ASTER_EXPERT_ROOT") or Path.cwd())


def _workroot() -> Path | None:
    raw = (os.environ.get("ASTER_CONTAINER_WORKROOT") or "").strip()
    return Path(raw) if raw else None


app = MCPServer(
    name="aster-expert",
    version=__version__,
    instructions=(
        "Outils de l'agent expert Code_Aster : recherche documentaire "
        "(search_codeaster_docs), schéma exact d'une commande "
        "(get_command_schema), analyse structurelle "
        "(analyze_comm) et validation de niveau B (validate_comm) d'un "
        "fichier .comm. Chaque réponse porte explicitement son niveau de "
        "validation (validation_level : 'A' documentaire, 'B' syntaxe "
        "confrontée au catalogue) : un niveau 'A' n'est jamais une preuve "
        "de validité syntaxique, d'exécution, ni de validité physique "
        "(niveaux C/D/E, hors périmètre de ce serveur). Ne jamais présenter "
        "une réponse de niveau 'A' comme vérifiée."
    ),
)


_SEARCH_DESCRIPTION = (
    "Recherche lexicale (BM25) dans le corpus documentaire Code_Aster "
    "indexé (manuels U2/U3/U4/U7, documents R/V, cas tests) — niveau A : "
    "réponse documentaire, jamais exécutée, jamais confrontée au "
    "catalogue.\n\n"
    "`profile` DOIT être choisi par l'appelant selon la nature de la "
    "question ; il n'est jamais deviné par ce serveur à partir du texte de "
    "la requête (ADR-007, docs/architecture.md — un profil mal choisi "
    "dégrade la pertinence sans jamais provoquer d'erreur, voir "
    "docs/development-plan.md, lot 7c) :\n"
    "- 'syntaxe' (défaut) : le nom exact d'une commande ou d'un mot-clé, "
    "la syntaxe à respecter — privilégie catalogue/U4/U7/cas "
    "tests/sources ;\n"
    "- 'theorie' : un fondement physique ou mathématique, une hypothèse, "
    "une formulation — privilégie R/U2/U4/U3/V ;\n"
    "- 'methode' : un choix de modélisation, une comparaison d'éléments "
    "finis disponibles, un cas d'usage — privilégie U2/U4/R/U3.\n\n"
    "Combinable avec des filtres exacts (`version`, `family`, "
    "`document_id`, `command`, `section_contains`)."
)


@app.tool(description=_SEARCH_DESCRIPTION)
def search_codeaster_docs(
    query: str,
    profile: str = DEFAULT_QUERY_PROFILE,
    k: int = 10,
    granularity: str = "by_file",
    priority_mode: str = "soft",
    version: str | None = None,
    family: str | None = None,
    document_id: str | None = None,
    command: str | None = None,
    section_contains: str | None = None,
) -> SearchDocsResult:
    return tools.search_codeaster_docs(
        project_root=_project_root(),
        query=query,
        profile=profile,
        k=k,
        granularity=granularity,
        priority_mode=priority_mode,
        version=version,
        family=family,
        document_id=document_id,
        command=command,
        section_contains=section_contains,
    )


_GET_SCHEMA_DESCRIPTION = (
    "Schéma exact d'une commande Code_Aster, extrait par introspection du "
    "catalogue de la version cible (ADR-001, docs/architecture.md) — "
    "jamais déduit des manuels. Niveau A : réponse documentaire directe, "
    "non confrontée à un fichier de l'utilisateur (c'est validate_comm qui "
    "confronte un fichier réel à ce même catalogue, niveau B).\n\n"
    "Donner `keyword` (chemin pointé, ex. 'COMPORTEMENT.RELATION') pour "
    "obtenir toutes les variantes de ce mot-clé quand un même chemin en a "
    "plusieurs (docs/metadata.md §2) : jamais une seule variante choisie "
    "silencieusement.\n\n"
    "Sans `version`, la dernière installation détectée est utilisée."
)


@app.tool(description=_GET_SCHEMA_DESCRIPTION)
def get_command_schema(
    command: str,
    keyword: str | None = None,
    version: str | None = None,
) -> CommandSchemaResult:
    return tools.get_command_schema(
        project_root=_project_root(),
        command=command,
        keyword=keyword,
        version=version,
    )


_ANALYZE_DESCRIPTION = (
    "Analyse structurelle d'un fichier de commandes .comm par inspection "
    "statique du module ast — le fichier n'est jamais exécuté "
    "(docs/architecture.md §5). Niveau A : structure et intentions du "
    "fichier (commandes, concepts, mots-clés, groupes, modélisations), "
    "jamais une preuve de validité syntaxique (voir validate_comm) ni "
    "d'exécution. Une construction dynamique (boucle, dictionnaire "
    "assemblé, appel de fonction, référence non résolue) est déclarée "
    "explicitement (`dynamic`/`unresolved`), jamais devinée."
)


@app.tool(description=_ANALYZE_DESCRIPTION)
def analyze_comm(comm_path: str) -> CommAnalysisResult:
    return tools.analyze_comm(project_root=_project_root(), comm_path=comm_path)


_VALIDATE_DESCRIPTION = (
    "Validation de niveau B d'un fichier .comm : confrontation de sa "
    "syntaxe reconstruite au catalogue de la version cible via "
    "checkCommandSyntax, exécuté dans le conteneur Code_Aster (jamais une "
    "grammaire réimplémentée par ce projet).\n\n"
    "`valid=true` signifie seulement que les commandes effectivement "
    "confrontées sont syntaxiquement correctes — jamais que le fichier "
    "s'exécute (niveau C), ni qu'il est physiquement correct (niveaux D/E), "
    "hors de portée de cet outil. `commands_not_checked` liste, sans jamais "
    "les masquer, les commandes qui n'ont pas pu être confrontées (mot-clé "
    "non résolu, construction dynamique, concept jamais résolu) : un taux "
    "de couverture partiel est toujours rapporté, jamais dissimulé.\n\n"
    "Nécessite un catalogue déjà extrait pour la version visée et un "
    "conteneur Docker joignable (ASTER_CONTAINER_WORKROOT, "
    "ASTER_DOCKER_BIN) : voir README.md."
)


@app.tool(description=_VALIDATE_DESCRIPTION)
def validate_comm(comm_path: str, version: str | None = None) -> ValidationReport:
    return tools.validate_comm(
        project_root=_project_root(),
        comm_path=comm_path,
        version=version,
        workroot=_workroot(),
        docker_bin_env=os.environ.get("ASTER_DOCKER_BIN") or None,
        image_repository=os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster"),
        network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
        memory=os.environ.get("ASTER_CONTAINER_MEMORY") or None,
        cpus=os.environ.get("ASTER_CONTAINER_CPUS") or None,
        timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
    )


def main() -> None:
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
