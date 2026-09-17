"""Recherche naïve par correspondance de nom de commande (lot 7, D6).

Référence honnête pour juger BM25 sur les questions qui portent sur une
commande précise (`EvaluationQuestion.expected_commands`) : ce module ne
fait rien de plus qu'un rapprochement de nom de commande exact contre la
table commande -> document du lot 6/6b
(`data/processed/command_document_map.json`, chargée via
`aster_expert.parsing.doc_fragments.load_related_commands`). Si BM25 ne bat
pas nettement cette référence triviale sur les questions qui nomment une
commande, il faut le dire (lot 7, D6), jamais le taire.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from aster_expert.parsing.doc_fragments import load_related_commands

# Un "jeton qui ressemble à une commande" : identifiant tout en majuscules
# d'au moins 3 caractères (`AFFE_CHAR_MECA`, `STAT_NON_LINE`) trouvé tel
# quel dans le texte brut de la question — jamais une correspondance floue
# ou en minuscules, puisque tout l'intérêt de cette référence est d'être le
# rapprochement le plus simple possible, pas un second moteur de recherche.
_COMMAND_TOKEN_RE = re.compile(r"[A-Z][A-Z0-9_]{2,}")


def build_documents_by_command(command_map_path: Path) -> dict[str, tuple[str, ...]]:
    """Command name -> every document naming it (inverse of the lot 6 table)."""
    related_commands_by_document = load_related_commands(command_map_path)
    by_command: dict[str, list[str]] = defaultdict(list)
    for document_id, commands in related_commands_by_document.items():
        for command in commands:
            by_command[command].append(document_id)
    return {command: tuple(sorted(set(docs))) for command, docs in by_command.items()}


def naive_command_search(
    query: str,
    documents_by_command: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Every document the command-map table names for a command found in `query`.

    Order of first appearance in the query, deduplicated — never a score,
    since this baseline makes no ranking claim beyond "found or not".
    """
    candidates: list[str] = []
    for token in _COMMAND_TOKEN_RE.findall(query):
        for document_id in documents_by_command.get(token, ()):
            if document_id not in candidates:
                candidates.append(document_id)
    return tuple(candidates)
