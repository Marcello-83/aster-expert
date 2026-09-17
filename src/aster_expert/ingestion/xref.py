"""Graphe de références croisées internes au corpus (lot 6, I4 ; lot 6b, X1).

Relève, dans les sources `.rst`, les renvois `:ref:` / `:external:ref:` vers
un autre document — la seule convention de renvoi observée sur le corpus
17.4.0 (docs/development-plan.md, lot 6 ; compte rendu du lot 6, I3/I4) —
et les résout contre l'inventaire (`aster_expert.ingestion.inventory`).

Ce graphe est établi ici, pas exploité (instruction du lot 6, I4) : il
reliera U, R et V à un lot ultérieur. `:numref:`/`:eq:` existent aussi dans
le corpus (relevés au lot 6, I3) mais visent des labels de figure/équation
internes à un document, pas des identifiants documentaires — hors du
périmètre de ce graphe, jamais confondus avec `:ref:`/`:external:ref:`.

**Amendement lot 6b (X1).** Le taux de résolution mesuré au lot 6
(6757/15560) confondait deux choses distinctes présentes dans
`source/conf.py` :

- `sphinx.ext.autosectionlabel` (`autosectionlabel_maxdepth = 1`,
  `autosectionlabel_prefix_document` absent donc `False` par défaut) fait
  de la section de tête de **chaque fichier** (pas seulement `index.rst` :
  chaque fichier `.rst` est son propre document Sphinx, la profondeur
  0 s'évalue par fichier) un label implicite, nommé
  `fully_normalize_name(title.rawsource)` — le texte brut de la ligne de
  titre, marqueurs `**...**` compris, jamais le texte rendu. Vérifié par
  lecture directe de `sphinx.ext.autosectionlabel.register_sections_as_label`
  et de `sphinx.environment` (`doctitle_xform: False` dans les réglages
  par défaut de Sphinx — sans ce réglage, `docutils` fusionnerait la
  section de tête dans `document['title']` et ne la verrait jamais comme
  une section). `build_autosectionlabel_index` construit ce registre
  exactement selon cet algorithme, jamais deviné.
- `sphinx.ext.intersphinx` : un renvoi `:external:ref:` est **toujours**
  distribué vers l'inventaire externe (`intersphinx_mapping`), jamais vers
  le domaine local, quelle que soit la forme de sa cible — donc jamais un
  renvoi local cassé, une catégorie à part.

**Mesuré, pas supposé (compte rendu du lot 6b) :** sur le corpus entier,
l'ensemble des cibles `:ref:` (hors identifiant de document déjà résolu)
n'intersecte **aucun** des 4175 labels `autosectionlabel` réellement
enregistrés (aucune des clés generées, illisibles pour un humain dès qu'un
titre porte lui-même un rôle imbriqué, n'est jamais tapée comme cible) :
`autosectionlabel` n'explique aucune part de la non-résolution sur ce
corpus, contrairement à l'hypothèse initiale — gardé néanmoins comme
mécanisme réel, testé, pour ne jamais deviner une fois pour toutes.
`intersphinx`, lui, reclasse réellement ~22 % des renvois du corpus
(`:external:ref:`, jamais une part des « non résolubles »).

Chaque fichier n'est lu qu'une fois par passe : la construction du graphe
et celle de l'index `autosectionlabel` sont deux passes séparées (l'une
regex, l'autre `docutils`), jamais les 13 116 fichiers `.rst` du corpus
chargés en mémoire simultanément (contrainte mémoire,
docs/development-plan.md, lot 6).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from docutils import nodes
from docutils.core import publish_doctree

from aster_expert.ingestion.models import (
    AmbiguousReference,
    CrossReferenceEdge,
    CrossReferenceGraphResult,
    CrossReferenceVia,
    ExternalReference,
    UnresolvedReference,
)

_REFERENCE_RE = re.compile(r":(external:)?ref:`[^`]*?<([^>]+)>`")

# source/conf.py : autosectionlabel_maxdepth = 1 (seule la section de tête
# de chaque fichier est retenue) ; autosectionlabel_prefix_document n'est
# pas déclaré (défaut Sphinx : False, vérifié dans
# `sphinx.ext.autosectionlabel.setup`) — jamais supposés, lus une fois ici
# pour documenter d'où viennent ces deux constantes.
AUTOSECTIONLABEL_MAXDEPTH = 1
AUTOSECTIONLABEL_PREFIX_DOCUMENT = False

# Réglages reproduisant exactement l'environnement Sphinx par défaut pour
# la promotion de titre (`doctitle_xform: False`,
# `sphinx/environment/__init__.py`) — sans ce réglage, `docutils` fusionne
# la section de tête d'un fichier à un seul titre dans `document['title']`
# et `register_sections_as_label` (qui parcourt `document.findall(nodes.
# section)`) ne la verrait jamais.
_AUTOSECTIONLABEL_SETTINGS = {
    "report_level": 5,
    "halt_level": 5,
    "language_code": "fr",
    "doctitle_xform": False,
}


def normalize_label_name(text: str) -> str:
    """Mirror `docutils.nodes.fully_normalize_name` : lowercase + espaces
    réduits à un seul — jamais une normalisation inventée."""
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class ReferenceOccurrence:
    """One `:ref:`/`:external:ref:` occurrence found in one file."""

    role: Literal["ref", "external:ref"]
    raw_target: str


def extract_references(text: str) -> list[ReferenceOccurrence]:
    """Every `:ref:`/`:external:ref:` occurrence in one file's raw text."""
    occurrences = []
    for match in _REFERENCE_RE.finditer(text):
        role: Literal["ref", "external:ref"] = (
            "external:ref" if match.group(1) else "ref"
        )
        occurrences.append(ReferenceOccurrence(role=role, raw_target=match.group(2)))
    return occurrences


def extract_top_section_labels(text: str) -> list[str]:
    """Every depth-0 section's `autosectionlabel` key for one file.

    Mirrors `sphinx.ext.autosectionlabel.register_sections_as_label`
    exactly (lot 6b, X1): only sections that are direct children of the
    document root are depth 0 — `autosectionlabel_maxdepth = 1` skips
    everything deeper — and the label name is
    `fully_normalize_name(title.rawsource)` (the *raw*, unparsed source
    text of the title line — `**id**` markers, or a nested role, kept
    verbatim if present), never the resolved/rendered text.
    `autosectionlabel_prefix_document` is not set in `source/conf.py`
    (defaults to `False`), so the key is never prefixed by the docname.
    """
    doctree = publish_doctree(text, settings_overrides=_AUTOSECTIONLABEL_SETTINGS)
    labels: list[str] = []
    for node in doctree.children:
        if isinstance(node, nodes.section):
            title_node = node[0]
            raw = getattr(title_node, "rawsource", "") or title_node.astext()
            labels.append(normalize_label_name(raw))
    return labels


def build_autosectionlabel_index(
    document_dirs_by_id: dict[str, Path],
) -> dict[str, list[tuple[str, str]]]:
    """`label -> [(document_id, file_relative_path), ...]`.

    Every `.rst` file of every document is probed, not just `index.rst`:
    each file is read by Sphinx as its own document, so
    `autosectionlabel_maxdepth = 1` applies to *each file's own* top-level
    section independently.
    """
    index: dict[str, list[tuple[str, str]]] = {}
    for document_id, doc_dir in document_dirs_by_id.items():
        for rst_path in sorted(doc_dir.rglob("*.rst")):
            text = rst_path.read_text(encoding="utf-8", errors="replace")
            for label in extract_top_section_labels(text):
                index.setdefault(label, []).append(
                    (document_id, rst_path.relative_to(doc_dir).as_posix())
                )
    return index


@dataclass(frozen=True)
class CrossReferenceGraph:
    """Full result of scanning every composing file of every document."""

    total_references: int
    internal_resolved_references: int
    external_references: int
    ambiguous_references: int
    unresolved_references: int
    # (source_document_id, target_document_id, via) -> occurrence count.
    # `via` is "explicit_label" (matched an inventory document id) or
    # "autosectionlabel" (matched exactly one document's registered
    # section-title key) — kept distinct so the provenance of every edge
    # is always traceable, never merged into one undifferentiated bucket.
    edges: Counter[tuple[str, str, CrossReferenceVia]]
    # (source_document_id, raw_target) -> count : an `:external:ref:`
    # occurrence, always dispatched to intersphinx by construction
    # (lot 6b, X1) — never checked against the local domain, never counted
    # as broken.
    external: Counter[tuple[str, str]]
    # (source_document_id, raw_target, candidate_document_ids) -> count :
    # the normalized target matches an autosectionlabel key registered by
    # more than one distinct document. Sphinx itself would pick whichever
    # was processed last (a real build-order dependency, not something we
    # can replicate without running Sphinx) — never guessed here.
    ambiguous: Counter[tuple[str, str, tuple[str, ...]]]
    # (source_document_id, raw_target) -> count : matches neither an
    # explicit document id nor any autosectionlabel key.
    unresolved: Counter[tuple[str, str]]


def build_reference_graph(
    document_dirs_by_id: dict[str, Path],
    known_document_ids: set[str],
    autosectionlabel_index: dict[str, list[tuple[str, str]]],
) -> CrossReferenceGraph:
    """Scan every `.rst` file of every given document for cross-references.

    `known_document_ids` is the inventory's own set of normalized ids
    (docs/corpus.md §6): a plain `:ref:` target resolves internally,
    `via="explicit_label"`, if and only if its normalized (uppercased)
    form is a member of that exact set — never a fuzzy or partial match.
    Otherwise it is checked against `autosectionlabel_index`
    (`via="autosectionlabel"`). An `:external:ref:` is never checked
    against either registry: it is always external, by construction
    (lot 6b, X1).
    """
    edges: Counter[tuple[str, str, CrossReferenceVia]] = Counter()
    external: Counter[tuple[str, str]] = Counter()
    ambiguous: Counter[tuple[str, str, tuple[str, ...]]] = Counter()
    unresolved: Counter[tuple[str, str]] = Counter()
    total = 0

    for document_id, doc_dir in document_dirs_by_id.items():
        for rst_path in sorted(doc_dir.rglob("*.rst")):
            text = rst_path.read_text(encoding="utf-8", errors="replace")
            for occurrence in extract_references(text):
                total += 1
                if occurrence.role == "external:ref":
                    external[(document_id, occurrence.raw_target)] += 1
                    continue

                normalized_id = occurrence.raw_target.strip().upper()
                if normalized_id in known_document_ids:
                    edges[(document_id, normalized_id, "explicit_label")] += 1
                    continue

                normalized_title = normalize_label_name(occurrence.raw_target)
                candidates = autosectionlabel_index.get(normalized_title, [])
                distinct_doc_ids = tuple(sorted({doc for doc, _file in candidates}))
                if len(distinct_doc_ids) == 1:
                    edges[(document_id, distinct_doc_ids[0], "autosectionlabel")] += 1
                elif len(distinct_doc_ids) > 1:
                    ambiguous[
                        (document_id, occurrence.raw_target, distinct_doc_ids)
                    ] += 1
                else:
                    unresolved[(document_id, occurrence.raw_target)] += 1

    return CrossReferenceGraph(
        total_references=total,
        internal_resolved_references=sum(edges.values()),
        external_references=sum(external.values()),
        ambiguous_references=sum(ambiguous.values()),
        unresolved_references=sum(unresolved.values()),
        edges=edges,
        external=external,
        ambiguous=ambiguous,
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

    autosectionlabel_index = build_autosectionlabel_index(document_dirs_by_id)
    graph = build_reference_graph(
        document_dirs_by_id, set(relative_path_by_id), autosectionlabel_index
    )

    edges = tuple(
        CrossReferenceEdge(
            source_document_id=src, target_document_id=dst, via=via, count=count
        )
        for (src, dst, via), count in sorted(graph.edges.items())
    )
    external = tuple(
        ExternalReference(source_document_id=src, raw_target=target, count=count)
        for (src, target), count in sorted(graph.external.items())
    )
    ambiguous = tuple(
        AmbiguousReference(
            source_document_id=src,
            raw_target=target,
            candidate_document_ids=candidates,
            count=count,
        )
        for (src, target, candidates), count in sorted(graph.ambiguous.items())
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
        internal_resolved_references=graph.internal_resolved_references,
        external_references=graph.external_references,
        ambiguous_references=graph.ambiguous_references,
        unresolved_references=graph.unresolved_references,
        edges=edges,
        external=external,
        ambiguous=ambiguous,
        unresolved=unresolved,
        autosectionlabel_prefix_document=AUTOSECTIONLABEL_PREFIX_DOCUMENT,
        autosectionlabel_maxdepth=AUTOSECTIONLABEL_MAXDEPTH,
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
