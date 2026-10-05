"""MCP server (lot 8, extended lot 8c): registers the tools over
`aster_expert.mcp.tools`.

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
    DocumentSectionResult,
    SearchConnaissancesResult,
    SearchConstatsResult,
    SearchDocsResult,
)
from aster_expert.mcp.testcases import SearchTestcasesResult, TestcaseFileResult
from aster_expert.retrieval.query_profiles import DEFAULT_QUERY_PROFILE
from aster_expert.validation.models import ValidationReport


def _project_root() -> Path:
    # `.mcp.json` may give a relative path (`${CLAUDE_PROJECT_DIR:-.}`, lot 41
    # ter): Claude Code starts the server in the project directory.
    return Path(os.environ.get("ASTER_EXPERT_ROOT") or Path.cwd()).resolve()


def _workroot() -> Path | None:
    raw = (os.environ.get("ASTER_CONTAINER_WORKROOT") or "").strip()
    return Path(raw).resolve() if raw else None


app = MCPServer(
    name="aster-expert",
    version=__version__,
    instructions=(
        "Outils de l'agent expert Code_Aster : recherche documentaire "
        "(search_codeaster_docs), lecture d'une section ou d'un fragment, "
        "par défaut intégrale (get_document_section), schéma exact d'une "
        "commande (get_command_schema), analyse structurelle "
        "(analyze_comm) et validation de niveau B (validate_comm) d'un "
        "fichier .comm. Chaque réponse porte explicitement son niveau de "
        "validation (validation_level : 'A' documentaire, 'B' syntaxe "
        "confrontée au catalogue) : un niveau 'A' n'est jamais une preuve "
        "de validité syntaxique, d'exécution, ni de validité physique "
        "(niveaux C/D/E, hors périmètre de ce serveur). Ne jamais présenter "
        "une réponse de niveau 'A' comme vérifiée. Un extrait de "
        "search_codeaster_docs est tronqué à 280 caractères : dès qu'une "
        "réponse s'appuie sur le contenu d'une section (tableau, liste de "
        "conditions, domaine de validité), lire cette section en entier via "
        "get_document_section avant de conclure -- jamais fonder une "
        "affirmation sur le seul extrait de tête. Si get_document_section "
        "renvoie content=null (section trop volumineuse, content_length "
        "au-delà du seuil), lire par plages successives via "
        "line_start/line_end en s'appuyant sur outline/guidance -- jamais "
        "conclure sur une lecture partielle sans l'avoir annoncée. Les "
        "fichiers de commandes des cas tests officiels se cherchent par "
        "commande (search_test_cases) et se lisent par read_test_case : "
        "jamais par lecture directe du dépôt. Avant d'écrire une commande, "
        "chercher par search_connaissances (ou search_constats, constats seuls) "
        "les constats et patrons qui la concernent ; dès qu'une erreur ou une "
        "alarme apparaît dans un .mess, chercher les diagnostics avant toute "
        "autre hypothèse ; avant de proposer une décision pratique, les "
        "précédents (jamais appliqués, seulement proposés) ; avant d'écrire un "
        "contrôle, les contrôles existants."
    ),
)


_SEARCH_DESCRIPTION = (
    "Recherche lexicale (BM25) dans le corpus documentaire Code_Aster "
    "indexé (manuels U2/U3/U4/U7, documents R/V ; les cas tests n'y sont pas, "
    "voir search_test_cases) — niveau A : "
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
    "`granularity` : 'by_file' (défaut) ou 'by_subsection'. Combinable avec "
    "des filtres exacts (`version`, `family`, `document_id`, `command`, "
    "`section_contains`) ; une `family` absente de l'index est refusée avec "
    "la liste des familles présentes, jamais renvoyée vide."
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


_GET_SECTION_DESCRIPTION = (
    "Texte d'un fragment ou d'une section documentaire, par défaut intégral "
    "— niveau A : réponse documentaire, jamais exécutée, jamais confrontée "
    "au catalogue.\n\n"
    "À utiliser dès qu'une réponse doit s'appuyer sur le contenu réel d'une "
    "section (un tableau comparatif, un domaine de validité, une liste de "
    "conditions) : l'`excerpt` renvoyé par search_codeaster_docs est coupé "
    "à 280 caractères et ne fonde jamais une telle affirmation à lui seul.\n"
    "\n"
    "Désigner la section soit par `fragment_id` (le champ `fragment_id` "
    "d'un `SearchHit`, à recopier tel quel), soit par `document_id` et "
    "`section_path` ensemble (les champs `document_id`/`section_path` de "
    "ce même `SearchHit`) — jamais les deux façons à la fois. `granularity` "
    "doit correspondre à celle du résultat de recherche d'origine (champ "
    "`granularity` du `SearchHit`, ou 'by_file' par défaut si vous partez "
    "d'un `document_id` connu directement).\n\n"
    "Vérifiez toujours `content_length` avant de lire : au-delà d'un seuil "
    "(20000 caractères), `content` revient à `null` plutôt que d'être coupé "
    "en silence -- `outline` (les sous-titres détectés, avec leurs bornes "
    "de lignes) et `guidance` disent alors exactement quelle plage plus "
    "étroite demander via `line_start`/`line_end` (lignes absolues du "
    "fichier source, les deux ensemble, bornes indiquées par `line_start`/"
    "`line_end` du fragment complet ou par une entrée de `outline`)."
)


@app.tool(description=_GET_SECTION_DESCRIPTION)
def get_document_section(
    fragment_id: str | None = None,
    document_id: str | None = None,
    section_path: list[str] | None = None,
    granularity: str = "by_file",
    line_start: int | None = None,
    line_end: int | None = None,
) -> DocumentSectionResult:
    return tools.get_document_section(
        project_root=_project_root(),
        fragment_id=fragment_id,
        document_id=document_id,
        section_path=section_path,
        granularity=granularity,
        line_start=line_start,
        line_end=line_end,
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
    "silencieusement. Avec `keyword`, seul le sous-arbre demandé est renvoyé "
    "(`keyword_variants`) : `command_schema` ne garde que les métadonnées de la "
    "commande et `keywords_omitted` compte les mots-clés de premier niveau "
    "laissés de côté (lot 44). Attention : le catalogue déclare `optional` des "
    "mots-clés que la commande exige à l'exécution (data/config/"
    "obligations_execution.yaml, constat CA-053).\n\n"
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


_ANALYZE_DESCRIPTION += (
    "\n\nLecture seule, limitée aux racines de config/chemins.yaml (dépôt, corpus, "
    "racines externes déclarées) et à l'extension .comm ; un refus nomme la racine "
    "manquante et dit comment la déclarer."
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


_VALIDATE_DESCRIPTION += (
    "\n\nMême politique de lecture que analyze_comm (config/chemins.yaml, .comm)."
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


_SEARCH_TESTS_DESCRIPTION = (
    "Cherche, dans les fichiers de commandes des cas tests officiels "
    "(external/codeaster-src/astest, commit enregistré au manifeste de "
    "synchronisation), ceux qui utilisent une `command` et, facultativement, "
    "un `keyword` — nom seul (à tout niveau) ou chemin pointé de queue "
    "('COMPORTEMENT.RELATION'). La correspondance est structurelle (parseur "
    "du projet), non textuelle : un commentaire ou une chaîne ne compte pas. "
    "Niveau A : un cas test est une référence exécutable, jamais un modèle "
    "transposable (CLAUDE.md, principe 5). `files_unparsable` déclare les "
    "fichiers non analysables, jamais omis en silence. Lecture seule ; "
    "enchaîner avec read_test_case."
)


@app.tool(description=_SEARCH_TESTS_DESCRIPTION)
def search_test_cases(
    command: str, keyword: str | None = None, limit: int = 50
) -> SearchTestcasesResult:
    return tools.search_test_cases(
        project_root=_project_root(), command=command, keyword=keyword, limit=limit
    )


_READ_TEST_DESCRIPTION = (
    "Lit un fichier de commandes de cas test (`path` = nom relatif au corpus, "
    "ex. le champ `path` d'un résultat de search_test_cases). Niveau A, "
    "lecture seule. Au-delà de 20000 caractères, `content` revient à `null` "
    "et `guidance` indique la plage à demander via `line_start`/`line_end` "
    "(les deux ensemble, lignes 1..total_lines). Un chemin hors du corpus, ou "
    "qui n'est pas un fichier de commandes, est refusé."
)


@app.tool(description=_READ_TEST_DESCRIPTION)
def read_test_case(
    path: str, line_start: int | None = None, line_end: int | None = None
) -> TestcaseFileResult:
    return tools.read_test_case(
        project_root=_project_root(),
        path=path,
        line_start=line_start,
        line_end=line_end,
    )


_SEARCH_CONSTATS_DESCRIPTION = (
    "Cherche dans la base partagée des constats Code_Aster "
    "(connaissances/constats_code_aster/, un fichier par constat, versionnée) "
    "ceux qui concernent une `command` du catalogue, un `keyword` (mot-clé ou "
    "valeur, ex. 'LIAISON_SOLIDE', 'DKT', 'FERR_MIN') et/ou un `text` libre (tous "
    "les mots, accents et casse ignorés). Au moins un critère. Chaque résultat "
    "porte le résumé du piège en une phrase, la version de Code_Aster, le niveau "
    "atteint par le constat lui-même (A documentaire, B catalogue, C/D exécution "
    "d'un cas d'essai versionné) et le fichier à lire pour ses sources. Niveau "
    "de la réponse : A (lecture de la base, rien n'est exécuté). À consulter "
    "avant de générer une commande."
)


@app.tool(description=_SEARCH_CONSTATS_DESCRIPTION)
def search_constats(
    text: str | None = None,
    command: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
) -> SearchConstatsResult:
    return tools.search_constats(
        project_root=_project_root(),
        text=text,
        command=command,
        keyword=keyword,
        limit=limit,
    )


_SEARCH_CONNAISSANCES_DESCRIPTION = (
    "Cherche dans la base de connaissances de l'outil (connaissances/, six "
    "couches versionnées, lot 42) : constats_code_aster (faits établis sur "
    "Code_Aster), diagnostics (signature d'erreur <F>/<A>, cause, correction), "
    "patrons (recettes de modélisation), controles (contrôles de vérification), "
    "references_validation (cas à solution connue, critère et résultat), "
    "precedents (décisions pratiques de MM, jamais appliquées automatiquement). "
    "Critères, au moins un, combinés : `text` libre (tous les mots, accents et "
    "casse ignorés), `command` du catalogue, `keyword` (mot-clé, valeur ou "
    "identifiant de message comme 'FACTOR_11'), `layers` (liste de couches), "
    "`status` ('observé', 'établi', 'promu'). Chaque résultat porte son statut, "
    "le niveau atteint par l'entrée elle-même (A à E) et le fichier qui porte "
    "ses preuves. Niveau de la réponse : A (lecture de la base, rien n'est "
    "exécuté). Consultation obligatoire : avant d'écrire une commande "
    "(constats, patrons), dès qu'une erreur apparaît dans un .mess "
    "(diagnostics, avant toute autre hypothèse), avant de proposer une décision "
    "pratique (precedents), avant d'écrire un contrôle (controles)."
)


@app.tool(description=_SEARCH_CONNAISSANCES_DESCRIPTION)
def search_connaissances(
    text: str | None = None,
    command: str | None = None,
    keyword: str | None = None,
    layers: list[str] | None = None,
    status: str | None = None,
    limit: int = 20,
) -> SearchConnaissancesResult:
    return tools.search_connaissances(
        project_root=_project_root(),
        text=text,
        command=command,
        keyword=keyword,
        layers=layers,
        status=status,
        limit=limit,
    )


def main() -> None:
    workroot = _workroot()
    if workroot is not None and workroot.is_relative_to(_project_root()):
        # A work root inside the project is ignored by Git and so absent from
        # a fresh clone: created here rather than failing at the first call.
        workroot.mkdir(parents=True, exist_ok=True)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
