"""Index lexical BM25 et recherche filtrée par métadonnées (lot 7, D4).

ADR-004 (`docs/architecture.md`) : un seul moteur, lexical, avec des filtres
de métadonnées stricts — jamais de fusion ni de reranking tant que la mesure
(lot 7, D5) ne le justifie pas. `bm25s` est utilisé tel quel : ni sa
tokenisation ni son calcul de score ne sont réimplémentés ici.

Les filtres de version/famille/document/commande/section ne sont jamais de
simples heuristiques de tri après coup : `weight_mask` (paramètre natif de
`bm25s.BM25.retrieve`) met à zéro le score de tout fragment ne correspondant
pas au filtre *avant* la sélection du top-k, pour que le classement lui-même
ne soit jamais pollué par des candidats hors filtre proches du seuil. Le
filtre est ensuite revérifié explicitement sur chaque résultat retenu
(`_matches`) : un score à zéro n'est jamais interprété comme une preuve
d'exclusion à lui seul (`weight_mask` agit sur le score, pas sur
l'appartenance), CLAUDE.md, « Un fragment issu d'une version différente de
la version interrogée n'est jamais renvoyé silencieusement ».
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import bm25s
import numpy as np

from aster_expert.indexing.models import IndexBuildSummary, SearchHit
from aster_expert.parsing.fragment_models import FragmentGranularity

_EXCERPT_CHARS = 280


def build_bm25_index(fragments_path: Path, index_dir: Path) -> IndexBuildSummary:
    """Build and persist a BM25 index from one granularity's fragment JSONL.

    Reads `fragments_path` once, line by line: the whole fragment set for
    one granularity is small enough to hold in memory as a flat list at
    build time (the corpus text alone is ~48 MB corpus-wide, lot 6 compte
    rendu) — this is the single heavy operation of the indexing step, run
    alone, never concurrently with fragment building itself
    (docs/development-plan.md, lot 7, memory constraint).
    """
    texts: list[str] = []
    corpus: list[dict[str, Any]] = []
    granularity: FragmentGranularity = "by_file"

    with fragments_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            fragment = json.loads(line)
            granularity = fragment["granularity"]
            texts.append(fragment["content"])
            corpus.append(
                {
                    "fragment_id": fragment["fragment_id"],
                    "granularity": fragment["granularity"],
                    "document_id": fragment["document_id"],
                    "document_title": fragment.get("document_title"),
                    "family": fragment["family"],
                    "aster_version": fragment["aster_version"],
                    "section_path": fragment["section_path"],
                    "source_path": fragment["source_path"],
                    "source_commit": fragment["source_commit"],
                    "line_start": fragment["line_start"],
                    "line_end": fragment["line_end"],
                    "related_commands": fragment.get("related_commands", []),
                    "content": fragment["content"],
                }
            )

    tokenized = bm25s.tokenize(texts, stopwords="french", show_progress=False)
    retriever = bm25s.BM25(corpus=corpus)
    retriever.index(tokenized, show_progress=False)

    index_dir.mkdir(parents=True, exist_ok=True)
    retriever.save(index_dir, show_progress=False)

    return IndexBuildSummary(
        granularity=granularity,
        fragment_count=len(corpus),
        vocabulary_size=len(tokenized.vocab),
        index_dir=str(index_dir),
    )


def load_bm25_index(index_dir: Path) -> tuple[bm25s.BM25, list[dict[str, Any]]]:
    retriever = bm25s.BM25.load(str(index_dir), load_corpus=True, show_progress=False)
    corpus = retriever.corpus
    if corpus is None:
        raise ValueError(f"index sans corpus persisté : {index_dir}")
    return retriever, corpus


def _matches(
    entry: dict[str, Any],
    *,
    version: str | None,
    family: str | None,
    document_id: str | None,
    command: str | None,
    section_contains: str | None,
) -> bool:
    if version is not None and entry["aster_version"] != version:
        return False
    if family is not None and entry["family"] != family:
        return False
    if document_id is not None and entry["document_id"] != document_id:
        return False
    if command is not None and command.upper() not in entry.get("related_commands", ()):
        return False
    return not (
        section_contains is not None
        and section_contains.lower() not in " / ".join(entry["section_path"]).lower()
    )


def _to_hit(entry: dict[str, Any], score: float) -> SearchHit:
    content = entry.get("content", "")
    excerpt = " ".join(content[:_EXCERPT_CHARS].split())
    return SearchHit(
        score=score,
        fragment_id=entry["fragment_id"],
        document_id=entry["document_id"],
        document_title=entry.get("document_title"),
        family=entry["family"],
        aster_version=entry["aster_version"],
        section_path=tuple(entry["section_path"]),
        source_path=entry["source_path"],
        source_commit=entry["source_commit"],
        line_start=entry["line_start"],
        line_end=entry["line_end"],
        related_commands=tuple(entry.get("related_commands", ())),
        granularity=entry["granularity"],
        excerpt=excerpt,
    )


def search(
    retriever: bm25s.BM25,
    corpus: list[dict[str, Any]],
    query: str,
    *,
    k: int = 10,
    version: str | None = None,
    family: str | None = None,
    document_id: str | None = None,
    command: str | None = None,
    section_contains: str | None = None,
) -> list[SearchHit]:
    """Rank `corpus` fragments against `query`, honoring every metadata filter given.

    `weight_mask` restricts the candidate pool bm25s itself ranks over, so a
    filter never has to "hope" enough matches survive after the fact; the
    explicit `_matches` re-check on every returned entry is a second,
    independent guard, never trusting a zero score alone to mean "excluded
    by filter" (see module docstring).
    """
    num_docs = len(corpus)
    if num_docs == 0:
        return []

    mask = np.array(
        [
            1.0
            if _matches(
                entry,
                version=version,
                family=family,
                document_id=document_id,
                command=command,
                section_contains=section_contains,
            )
            else 0.0
            for entry in corpus
        ],
        dtype="float32",
    )
    if not mask.any():
        return []

    query_tokens = bm25s.tokenize(query, stopwords="french", show_progress=False)
    retrieve_k = min(num_docs, max(k, 200))
    documents, scores = retriever.retrieve(
        query_tokens,
        corpus=corpus,
        k=retrieve_k,
        weight_mask=mask,
        show_progress=False,
    )

    hits: list[SearchHit] = []
    for entry, score in zip(documents[0], scores[0], strict=True):
        if float(score) <= 0.0:
            continue
        if not _matches(
            entry,
            version=version,
            family=family,
            document_id=document_id,
            command=command,
            section_contains=section_contains,
        ):
            continue
        hits.append(_to_hit(entry, float(score)))
        if len(hits) >= k:
            break
    return hits


def default_index_dir(project_root: Path, granularity: FragmentGranularity) -> Path:
    return project_root / "data" / "indexes" / f"bm25_{granularity}"
