"""Table commande -> document (lot 6, I5 ; lot 6b, X2/X3).

Les documents U4/U7 sont organisés par commande (docs/corpus.md §3 : « U4,
U7 : documentation des commandes »). La correspondance est construite
depuis un fait observé dans la source — le nom de commande apparaît tel
quel (casse et ponctuation officielles, `CLAUDE.md`, « Langue ») dans le
titre du document — jamais une ressemblance devinée : un nom de commande
plus long ne matche jamais le titre d'un document consacré à un nom plus
court qui en est un préfixe (`AFFE_CHAR_MECA` ne matche jamais le titre
d'`AFFE_CHAR_MECA_C`), grâce à une bordure d'identifiant explicite.

Un document peut légitimement documenter plusieurs commandes ensemble
(`U4.44.01`, « Opérateurs AFFE_CHAR_MECA, AFFE_CHAR_MECA_C et
AFFE_CHAR_MECA_F ») : chacune reçoit sa propre arête, aucune n'est
retenue au détriment d'une autre. Une commande peut symétriquement être
documentée par plusieurs documents (`IMPR_RESU`, quatre documents — un par
format de sortie) : le fait est conservé tel quel, jamais réduit à un seul
document choisi arbitrairement.

Chaque arête porte le titre exact et le chemin du fichier source d'où
provient le rapprochement (lot 6b, X2 ; `CLAUDE.md`, « Toute donnée
indexée conserve sa source, son chemin ») : ni `command`/`document_id`
seuls ne permettent de revérifier le rapprochement sans rejouer
l'extraction.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.models import (
    CommandDocumentEdge,
    CommandMappingResult,
    UncataloguedCommandMention,
)

# Commandes réelles, documentées, mais absentes du catalogue introspecté au
# lot 4 (`code_aster.Cata.Commands` seul parcouru) : la commande vit
# ailleurs dans `code_aster` (`MacroCommands`, `CodeCommands`), jamais dans
# le module que l'extracteur du lot 4 parcourt. Chaque entrée est vérifiée
# par lecture directe de `external/codeaster-src` (jamais devinée) :
#
# - `DEFI_CONT`, `F_FONC`, `F_ACS2C11`, `CALC_SPEC`, `F_ACC_X`,
#   `MACR_ROTA_GLOBALE`, `CHAR_GRAD_INI`, `F_ACCEL`, `TEST_INIT`,
#   `F_FLBNS`, `MACRO_TEST` : déjà établies au lot 10b, depuis la fréquence
#   d'usage dans les cas tests (docs/development-plan.md, lot 4) — `DEFI_CONT`
#   et `CALC_SPEC` sont les deux seules de cette liste nommées dans un titre
#   U4/U7 (`U4.44.13`, `U4.32.21`), confirmant par une source indépendante
#   (la documentation officielle, pas les cas tests) qu'elles sont bien
#   réelles et documentées, pas un artefact des cas tests.
# - `CALC_FORC_AJOU` (lot 6b, X3, révélée par cette table — absente de
#   l'énumération du lot 10b) : `UserMacro`-like, définie dans
#   `code_aster/MacroCommands/Utils/calc_forc_ajou.py` (`CALC_FORC_AJOU =
#   CalcForcAjou.run`), catalogue `OPER(nom="CALC_FORC_AJOU", ...)` dans
#   `calc_forc_ajou_cata.py` du même répertoire — un `MacroCommands` de
#   plus, jamais dans `code_aster.Cata.Commands`.
# - `POURSUITE` (lot 6b, X3, révélée par cette table) : cas différent des
#   précédentes — jamais un `MacroCommands`. Définie dans
#   `code_aster/CodeCommands/debut.py` (`POURSUITE = partial(Starter.run,
#   caller="POURSUITE")`), un alias d'exécution de `DEBUT` sous un autre
#   nom d'appelant ; `code_aster.Cata.Commands` ne porte "POURSUITE" sous
#   aucune forme (seulement comme valeur autorisée du mot-clé `MODE` de
#   `DEBUT`, `into=("AUTO", "DEBUT", "POURSUITE")` — jamais une commande à
#   part entière dans ce module).
KNOWN_COMMANDS_OUTSIDE_CATALOGUE: dict[str, str] = {
    "DEFI_CONT": "code_aster/MacroCommands/defi_cont.py",
    "F_FONC": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "F_ACS2C11": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "CALC_SPEC": "code_aster/MacroCommands/Contrib/calc_spec.py",
    "F_ACC_X": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "MACR_ROTA_GLOBALE": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "CHAR_GRAD_INI": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "F_ACCEL": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "TEST_INIT": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "F_FLBNS": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "MACRO_TEST": "code_aster/MacroCommands (lot 10b, non relocalisée ici)",
    "CALC_FORC_AJOU": "code_aster/MacroCommands/Utils/calc_forc_ajou.py",
    "POURSUITE": "code_aster/CodeCommands/debut.py (alias d'exécution de DEBUT)",
}


def find_commands_in_title(
    title: str, catalogue_commands: list[str]
) -> tuple[str, ...]:
    """Every catalogue command name appearing in `title` as a whole identifier.

    Never a substring match: a command name is only counted when it is not
    immediately preceded or followed by another identifier character
    (`[A-Z0-9_]`) — otherwise `AFFE_CHAR_MECA` would incorrectly match
    inside the title of the `AFFE_CHAR_MECA_C`/`_F` documents.
    """
    found = []
    for command in catalogue_commands:
        pattern = re.compile(r"(?<![A-Z0-9_])" + re.escape(command) + r"(?![A-Z0-9_])")
        if pattern.search(title):
            found.append(command)
    return tuple(found)


@dataclass(frozen=True)
class _RawMappingResult:
    edges_by_command: dict[str, list[str]]
    documents_without_command: list[str]
    uncatalogued_mentions: list[tuple[str, str]]  # (document_id, command)


def _build_raw_mapping(
    documents: list[tuple[str, str | None, str]],
    catalogue_commands: list[str],
) -> _RawMappingResult:
    """`documents` is `(document_id, title, relative_path)` for U4/U7 docs."""
    edges_by_command: dict[str, list[str]] = defaultdict(list)
    documents_without_command: list[str] = []
    uncatalogued_mentions: list[tuple[str, str]] = []

    for document_id, title, _relative_path in documents:
        text = title or ""
        matched = find_commands_in_title(text, catalogue_commands)
        if matched:
            for command in matched:
                edges_by_command[command].append(document_id)
            continue

        for known_command in KNOWN_COMMANDS_OUTSIDE_CATALOGUE:
            pattern = re.compile(
                r"(?<![A-Z0-9_])" + re.escape(known_command) + r"(?![A-Z0-9_])"
            )
            if pattern.search(text):
                uncatalogued_mentions.append((document_id, known_command))
                break
        else:
            documents_without_command.append(document_id)

    return _RawMappingResult(
        edges_by_command=dict(edges_by_command),
        documents_without_command=documents_without_command,
        uncatalogued_mentions=uncatalogued_mentions,
    )


def build_command_mapping(
    documents: list[tuple[str, str | None, str]],
    catalogue_commands: list[str],
    *,
    source_name: str,
    source_commit: str,
    now: datetime | None = None,
) -> CommandMappingResult:
    resolved_now = now if now is not None else datetime.now(UTC)
    raw = _build_raw_mapping(documents, catalogue_commands)
    title_and_path_by_id = {
        document_id: (title, relative_path)
        for document_id, title, relative_path in documents
    }

    edges = tuple(
        CommandDocumentEdge(
            command=command,
            document_id=document_id,
            document_title=title_and_path_by_id[document_id][0] or "",
            source_path=f"{title_and_path_by_id[document_id][1]}/index.rst",
        )
        for command in sorted(raw.edges_by_command)
        for document_id in sorted(raw.edges_by_command[command])
    )
    commands_without_document = tuple(
        sorted(set(catalogue_commands) - set(raw.edges_by_command))
    )
    uncatalogued_mentions = tuple(
        UncataloguedCommandMention(
            document_id=document_id,
            command=command,
            document_title=title_and_path_by_id[document_id][0] or "",
            source_path=f"{title_and_path_by_id[document_id][1]}/index.rst",
            known_location=KNOWN_COMMANDS_OUTSIDE_CATALOGUE[command],
        )
        for document_id, command in sorted(raw.uncatalogued_mentions)
    )

    return CommandMappingResult(
        generated_at=resolved_now,
        source_name=source_name,
        source_commit=source_commit,
        total_catalogue_commands=len(catalogue_commands),
        matched_catalogue_commands=len(raw.edges_by_command),
        edges=edges,
        commands_without_document=commands_without_document,
        documents_without_command=tuple(sorted(raw.documents_without_command)),
        documents_naming_uncatalogued_command=uncatalogued_mentions,
    )


def load_u4_u7_documents(inventory_path: Path) -> list[tuple[str, str | None, str]]:
    """Read `data/raw/inventory.jsonl`, keeping only U4/U7 documents.

    Returns `(document_id, title, relative_path)`: `relative_path` is
    carried through so every edge can cite its exact source file (lot 6b,
    X2), never just the bare ids.
    """
    documents: list[tuple[str, str | None, str]] = []
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["family"] in ("U4", "U7"):
            documents.append(
                (entry["document_id"], entry.get("title"), entry["relative_path"])
            )
    return documents


def load_catalogue_commands(catalogue_digest_dir: Path) -> list[str]:
    """List every command name extracted by the lot 4 catalogue introspection.

    Sorted longest-first: irrelevant for correctness (boundary matching in
    `find_commands_in_title` already prevents a shorter command from
    matching inside a longer one's name), kept only so the emitted table is
    reproducible in a stable, readable order when commands tie elsewhere.
    """
    return sorted((p.stem for p in catalogue_digest_dir.glob("*.json")), reverse=True)


def default_command_map_path(project_root: Path) -> Path:
    return project_root / "data" / "processed" / "command_document_map.json"


def write_command_mapping_json(result: CommandMappingResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json.loads(result.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
