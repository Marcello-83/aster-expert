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

from aster_expert.indexing.enrichment import enrich_indexed_text
from aster_expert.indexing.models import DocumentSection, IndexBuildSummary, SearchHit
from aster_expert.parsing.fragment_models import FragmentGranularity

_EXCERPT_CHARS = 280


def build_bm25_index(
    fragments_path: Path,
    index_dir: Path,
    *,
    keyword_names_by_command: dict[str, tuple[str, ...]] | None = None,
) -> IndexBuildSummary:
    """Build and persist a BM25 index from one granularity's fragment JSONL.

    Reads `fragments_path` once, line by line: the whole fragment set for
    one granularity is small enough to hold in memory as a flat list at
    build time (the corpus text alone is ~48 MB corpus-wide, lot 6 compte
    rendu) — this is the single heavy operation of the indexing step, run
    alone, never concurrently with fragment building itself
    (docs/development-plan.md, lot 7, memory constraint).

    `keyword_names_by_command` (lot 7b, E1) : when given, the text handed to
    the tokenizer for each fragment is enriched (`enrich_indexed_text`) with
    the fragment's document title, section path, and — for every command
    already linked to it — that command's name and top-level keyword names.
    `None` (the default) reproduces the lot 7 index byte-for-byte: the
    tokenized text is `fragment["content"]` alone, nothing else. Either way,
    the persisted `corpus` metadata's own `"content"` stays the fragment's
    raw content — enrichment only ever changes what is tokenized, never what
    is stored, cited or excerpted (`_to_hit`).
    """
    texts: list[str] = []
    corpus: list[dict[str, Any]] = []
    granularity: FragmentGranularity = "by_file"
    enrich = keyword_names_by_command is not None

    with fragments_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            fragment = json.loads(line)
            granularity = fragment["granularity"]
            section_path = tuple(fragment["section_path"])
            related_commands = tuple(fragment.get("related_commands", ()))
            if enrich:
                indexed_text = enrich_indexed_text(
                    content=fragment["content"],
                    document_title=fragment.get("document_title"),
                    section_path=section_path,
                    related_commands=related_commands,
                    keyword_names_by_command=keyword_names_by_command or {},
                )
            else:
                indexed_text = fragment["content"]
            texts.append(indexed_text)
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
        text_enrichment="e1_title_section_keywords_scoped" if enrich else "none",
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
    family_in: tuple[str, ...] | None,
    document_id: str | None,
    command: str | None,
    section_contains: str | None,
) -> bool:
    if version is not None and entry["aster_version"] != version:
        return False
    if family is not None and entry["family"] != family:
        return False
    if family_in is not None and entry["family"] not in family_in:
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
    family_in: tuple[str, ...] | None = None,
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

    `family_in` (lot 7b, E2a) is independent of `family`: `family` is the
    single-value exact filter already exposed by `aster-expert search
    --family`, `family_in` is the "belongs to this set" filter the hard
    source-priority variant needs — both can be combined, though no caller
    does so today.
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
                family_in=family_in,
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
            family_in=family_in,
            document_id=document_id,
            command=command,
            section_contains=section_contains,
        ):
            continue
        hits.append(_to_hit(entry, float(score)))
        if len(hits) >= k:
            break
    return hits


def to_document_section(entry: dict[str, Any]) -> DocumentSection:
    """One corpus entry, whole -- the untruncated counterpart of `_to_hit` (lot 8c, K1).

    `content` is the corpus entry's own raw content, exactly as persisted by
    `build_bm25_index` (never re-read from the fragments JSONL, which would
    be a second, divergence-prone source of the same text) -- no
    `_EXCERPT_CHARS` cut applied.
    """
    content = entry.get("content", "")
    return DocumentSection(
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
        content=content,
        content_length=len(content),
    )


def find_fragments(
    corpus: list[dict[str, Any]],
    *,
    fragment_id: str | None = None,
    document_id: str | None = None,
    section_path: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Exact lookup of corpus entries, never ranked (lot 8c, K1).

    Given `fragment_id`, matches on that identifier alone. Otherwise matches
    on `document_id` and `section_path` together (both required in that
    case): a fragment's `section_path` is exactly what `SearchHit` already
    exposes, so a caller that only has a search result's section path, not
    its `fragment_id`, can still look the fragment up. Ambiguity (more than
    one match) or absence is left entirely to the caller to decide what to
    do with -- this function never guesses which candidate was meant.
    """
    if fragment_id is not None:
        return [entry for entry in corpus if entry["fragment_id"] == fragment_id]
    return [
        entry
        for entry in corpus
        if entry["document_id"] == document_id
        and tuple(entry["section_path"]) == section_path
    ]


def default_index_dir(
    project_root: Path, granularity: FragmentGranularity, variant: str | None = None
) -> Path:
    """`data/indexes/bm25_<granularity>[_<variant>]`.

    `variant=None` (every lot 7 caller) reproduces the lot 7 path exactly —
    this default must never change, or every already-built index on disk
    would silently stop resolving. `variant` (lot 7b) names a sibling index
    built with a different pipeline (e.g. `"e1"`, the E1 text-enrichment
    index) without overwriting the lot 7 reference index it is measured
    against.
    """
    name = f"bm25_{granularity}" if variant is None else f"bm25_{granularity}_{variant}"
    return project_root / "data" / "indexes" / name
