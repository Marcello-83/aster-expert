"""Graphe de références croisées internes au corpus (lot 6, I4).

Relève, dans les sources `.rst`, les renvois `:ref:` / `:external:ref:` vers
un autre document — la seule convention de renvoi observée sur le corpus
17.4.0 (docs/development-plan.md, lot 6 ; compte rendu du lot 6, I3/I4) —
et les résout contre l'inventaire (`aster_expert.ingestion.inventory`).

Ce graphe est établi ici, pas exploité (instruction du lot 6, I4) : il
reliera U, R et V à un lot ultérieur. `:numref:`/`:eq:` existent aussi dans
le corpus (relevés au lot 6, I3) mais visent des labels de figure/équation
internes à un document, pas des identifiants documentaires — hors du
périmètre de ce graphe, jamais confondus avec `:ref:`/`:external:ref:`.

Chaque fichier n'est lu qu'une fois, en flux : jamais les 13 116 fichiers
`.rst` du corpus chargés en mémoire simultanément (contrainte mémoire,
docs/development-plan.md, lot 6).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.models import (
    CrossReferenceEdge,
    CrossReferenceGraphResult,
    UnresolvedReference,
)

_REFERENCE_RE = re.compile(r":(?:external:)?ref:`[^`]*?<([^>]+)>`")


@dataclass(frozen=True)
class ReferenceOccurrence:
    """One `:ref:`/`:external:ref:` occurrence found in one file."""

    raw_target: str
    file_relative_path: str


def extract_references(text: str) -> list[str]:
    """Every `:ref:`/`:external:ref:` target in one file's raw text, in order."""
    return _REFERENCE_RE.findall(text)


@dataclass(frozen=True)
class CrossReferenceGraph:
    """Full result of scanning every composing file of every document."""

    total_references: int
    resolvable_references: int
    unresolvable_references: int
    # (source_document_id, target_document_id) -> occurrence count. Only
    # resolvable edges: this is the graph itself.
    edges: Counter[tuple[str, str]]
    # (source_document_id, raw_target) -> occurrence count, for every
    # target that does not resolve to a document in the inventory. Kept
    # distinct from `edges`, never merged or silently dropped.
    unresolved: Counter[tuple[str, str]]


def build_reference_graph(
    document_dirs_by_id: dict[str, Path],
    known_document_ids: set[str],
) -> CrossReferenceGraph:
    """Scan every `.rst` file of every given document for cross-references.

    `known_document_ids` is the inventory's own set of normalized ids
    (docs/corpus.md §6): a target resolves if and only if its normalized
    (uppercased) form is a member of that exact set — never a fuzzy or
    partial match.
    """
    edges: Counter[tuple[str, str]] = Counter()
    unresolved: Counter[tuple[str, str]] = Counter()
    total = 0

    for document_id, doc_dir in document_dirs_by_id.items():
        for rst_path in sorted(doc_dir.rglob("*.rst")):
            text = rst_path.read_text(encoding="utf-8", errors="replace")
            for raw_target in extract_references(text):
                total += 1
                normalized = raw_target.strip().upper()
                if normalized in known_document_ids:
                    edges[(document_id, normalized)] += 1
                else:
                    unresolved[(document_id, raw_target)] += 1

    resolvable = sum(edges.values())
    unresolvable = sum(unresolved.values())
    return CrossReferenceGraph(
        total_references=total,
        resolvable_references=resolvable,
        unresolvable_references=unresolvable,
        edges=edges,
        unresolved=unresolved,
    )


def load_inventory_documents(inventory_path: Path) -> dict[str, str]:
    """Read `data/raw/inventory.jsonl`: document id -> relative path."""
    relative_path_by_id: dict[str, str] = {}
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        relative_path_by_id[entry["document_id"]] = entry["relative_path"]
    return relative_path_by_id


def build_reference_graph_result(
    *,
    inventory_path: Path,
    repo_root: Path,
    source_name: str,
    source_commit: str,
    now: datetime | None = None,
) -> CrossReferenceGraphResult:
    """Build the full-corpus cross-reference graph from an existing inventory."""
    resolved_now = now if now is not None else datetime.now(UTC)
    relative_path_by_id = load_inventory_documents(inventory_path)
    document_dirs_by_id = {
        doc_id: repo_root / rel for doc_id, rel in relative_path_by_id.items()
    }

    graph = build_reference_graph(document_dirs_by_id, set(relative_path_by_id))

    edges = tuple(
        CrossReferenceEdge(source_document_id=src, target_document_id=dst, count=count)
        for (src, dst), count in sorted(graph.edges.items())
    )
    unresolved = tuple(
        UnresolvedReference(source_document_id=src, raw_target=target, count=count)
        for (src, target), count in sorted(graph.unresolved.items())
    )

    return CrossReferenceGraphResult(
        generated_at=resolved_now,
        source_name=source_name,
        source_commit=source_commit,
        total_references=graph.total_references,
        resolvable_references=graph.resolvable_references,
        unresolvable_references=graph.unresolvable_references,
        edges=edges,
        unresolved=unresolved,
    )


def default_xref_path(project_root: Path) -> Path:
    return project_root / "data" / "processed" / "xref_graph.json"


def write_xref_json(result: CrossReferenceGraphResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json.loads(result.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
