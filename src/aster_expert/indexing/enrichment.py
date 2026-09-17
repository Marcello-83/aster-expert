"""E1 (lot 7b) : enrichissement du texte indexé par le vocabulaire du catalogue.

Diagnostic de départ (relecture externe du lot 7, `docs/development-plan.md`) :
`U4.44.01` manque quatre fois sur le domaine `chargements`. Le document dit
« mot-clé facteur DDL_IMPO », la question dit « bloquer des degrés de
liberté » : BM25 ne peut faire le lien qu'entre des jetons qui apparaissent
tous deux dans le texte réellement tokenisé, et le nom du mot-clé n'y figure
pas plus souvent qu'une fois, noyé dans le corps du document.

Ce module ajoute, uniquement au texte *soumis à la tokenisation* (jamais au
`content` du fragment lui-même, qui reste la tranche brute que
`aster_expert.parsing.doc_fragments` garantit non tronquée) :

- le titre du document ;
- le chemin de section ;
- pour chaque commande déjà liée au document (table commande -> document du
  lot 6b, `DocumentFragment.related_commands`) : le nom de la commande, puis
  le nom de chacun de ses mots-clés de premier niveau, facteurs et simples.

**Choix de profondeur, assumé et mesuré, pas deviné.** Seuls les mots-clés de
premier niveau (`CommandSchema.keywords`, jamais `FactorKeywordSchema.
children`) sont ajoutés. `AFFE_CHAR_MECA` porte à lui seul plusieurs
centaines de mots-clés simples imbriqués sous ses mots-clés facteurs (`DDL_
IMPO` seul en imbrique une centaine : `DX`, `DY`, `H1X`, `K1`... des jetons
courts, génériques, qui apparaîtraient identiques dans des dizaines de
commandes sans rapport). Le diagnostic de ce lot est un déficit de
*précision*, pas de rappel (consigne du lot) : noyer chaque fragment dans
des centaines de jetons à faible pouvoir discriminant irait à l'encontre de
cet objectif. Le premier niveau seul couvre déjà le cas motivant
(`DDL_IMPO` lui-même est un mot-clé facteur de premier niveau) et correspond
à la structure éditoriale des documents U4/U7, qui titrent chaque mot-clé de
premier niveau comme sa propre sous-section (« Mot-clé facteur DDL_IMPO »).
"""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.catalogue.models import CommandSchema

# Un mot-clé sans document nommant sa commande (`documents_naming_
# uncatalogued_command`, lot 6b X3 : `DEFI_CONT`, `CALC_FORC_AJOU`,
# `POURSUITE`...) n'a jamais de fichier catalogue -- absence attendue et
# documentée (`aster_expert.ingestion.command_map.
# KNOWN_COMMANDS_OUTSIDE_CATALOGUE`), jamais une erreur d'enrichissement.


def load_command_keyword_names(
    catalogue_digest_dir: Path, commands: set[str]
) -> dict[str, tuple[str, ...]]:
    """Command name -> its top-level keyword names (factor and simple), for
    every command in `commands` that has an extracted schema under
    `catalogue_digest_dir`.

    Only the commands actually needed are read (never the whole digest
    directory), since a fragment set only ever names a small subset of the
    catalogue's commands.
    """
    names: dict[str, tuple[str, ...]] = {}
    for command in sorted(commands):
        path = catalogue_digest_dir / f"{command}.json"
        if not path.is_file():
            continue
        schema = CommandSchema.model_validate_json(path.read_text(encoding="utf-8"))
        names[command] = tuple(
            dict.fromkeys(keyword.path[-1] for keyword in schema.keywords)
        )
    return names


def enrich_indexed_text(
    *,
    content: str,
    document_title: str | None,
    section_path: tuple[str, ...],
    related_commands: tuple[str, ...],
    keyword_names_by_command: dict[str, tuple[str, ...]],
) -> str:
    """The text handed to `bm25s.tokenize` for one fragment (lot 7b, E1).

    Never returned in place of `content` for citation or excerpt purposes
    (`aster_expert.indexing.bm25_index._to_hit` keeps reading the corpus
    entry's own `content` field, untouched by this function) -- this string
    exists only to be tokenized, one extra indexing-time view of the same
    fragment, not a replacement of it.
    """
    parts = [content]
    if document_title:
        parts.append(document_title)
    if section_path:
        parts.append(" / ".join(section_path))
    for command in related_commands:
        parts.append(command)
        parts.extend(keyword_names_by_command.get(command, ()))
    return "\n".join(parts)


def collect_related_commands(fragments_path: Path) -> set[str]:
    """Every distinct command named in `related_commands` across the fragment set.

    Reads the file a second time on purpose (streamed, one line at a time,
    never held whole in memory) rather than have `build_bm25_index` collect
    it as a side effect: keeping this pass separate is what lets a caller
    resolve the keyword-name table (a network- and IO-free but non-trivial
    lookup, `load_command_keyword_names`) once, before the indexing pass
    itself starts.
    """
    commands: set[str] = set()
    with fragments_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            fragment = json.loads(line)
            commands.update(fragment.get("related_commands", ()))
    return commands
