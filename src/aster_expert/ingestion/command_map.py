"""Table commande -> document (lot 6, I5).

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
)

# docs/development-plan.md, lot 4 (note reprise au lot 10b) : commandes
# réelles mais absentes du catalogue introspecté (`code_aster.Cata.Commands`
# seul parcouru par le lot 4) parce qu'elles vivent dans
# `code_aster.MacroCommands` — fait déjà établi et vérifié à ce lot-là,
# jamais redéduit ici. Sert uniquement à annoter, jamais à créer une arête
# commande -> document : ces noms ne sont pas dans le catalogue des 268
# commandes, donc hors du périmètre de la table (I5 mesure la couverture
# sur CES 268 commandes précisément).
KNOWN_MACRO_COMMANDS_OUTSIDE_CATALOGUE = frozenset(
    {
        "DEFI_CONT",
        "F_FONC",
        "F_ACS2C11",
        "CALC_SPEC",
        "F_ACC_X",
        "MACR_ROTA_GLOBALE",
        "CHAR_GRAD_INI",
        "F_ACCEL",
        "TEST_INIT",
        "F_FLBNS",
        "MACRO_TEST",
    }
)


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
    documents_naming_known_macro_command: list[tuple[str, str]]


def _build_raw_mapping(
    documents: list[tuple[str, str | None]],
    catalogue_commands: list[str],
) -> _RawMappingResult:
    """`documents` is a list of `(document_id, title)` for U4/U7 documents."""
    edges_by_command: dict[str, list[str]] = defaultdict(list)
    documents_without_command: list[str] = []
    documents_naming_known_macro_command: list[tuple[str, str]] = []

    for document_id, title in documents:
        text = title or ""
        matched = find_commands_in_title(text, catalogue_commands)
        if matched:
            for command in matched:
                edges_by_command[command].append(document_id)
            continue

        for macro_command in KNOWN_MACRO_COMMANDS_OUTSIDE_CATALOGUE:
            pattern = re.compile(
                r"(?<![A-Z0-9_])" + re.escape(macro_command) + r"(?![A-Z0-9_])"
            )
            if pattern.search(text):
                documents_naming_known_macro_command.append(
                    (document_id, macro_command)
                )
                break
        else:
            documents_without_command.append(document_id)

    return _RawMappingResult(
        edges_by_command=dict(edges_by_command),
        documents_without_command=documents_without_command,
        documents_naming_known_macro_command=documents_naming_known_macro_command,
    )


def build_command_mapping(
    documents: list[tuple[str, str | None]],
    catalogue_commands: list[str],
    *,
    source_name: str,
    source_commit: str,
    now: datetime | None = None,
) -> CommandMappingResult:
    resolved_now = now if now is not None else datetime.now(UTC)
    raw = _build_raw_mapping(documents, catalogue_commands)

    edges = tuple(
        CommandDocumentEdge(command=command, document_id=document_id)
        for command in sorted(raw.edges_by_command)
        for document_id in sorted(raw.edges_by_command[command])
    )
    commands_without_document = tuple(
        sorted(set(catalogue_commands) - set(raw.edges_by_command))
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
        documents_naming_known_macro_command=tuple(
            sorted(raw.documents_naming_known_macro_command)
        ),
    )


def load_u4_u7_documents(inventory_path: Path) -> list[tuple[str, str | None]]:
    """Read `data/raw/inventory.jsonl`, keeping only U4/U7 documents."""
    documents: list[tuple[str, str | None]] = []
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["family"] in ("U4", "U7"):
            documents.append((entry["document_id"], entry.get("title")))
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
