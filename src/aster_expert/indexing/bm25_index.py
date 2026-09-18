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
from aster_expert.indexing.models import (
    DocumentSection,
    IndexBuildSummary,
    SearchHit,
    SectionOutlineEntry,
)
from aster_expert.parsing.doc_fragments import split_into_subsections
from aster_expert.parsing.fragment_models import FragmentGranularity

_EXCERPT_CHARS = 280

# "Raisonnable" mesuré, pas deviné (lot 14, L1) : sur le corpus 17.4.0
# synchronisé, 20000 caractères se situe entre le 95e et le 99e centile de
# `content_length` en granularité by_file (p95 13909, p99 38014 sur 13116
# fragments) et bien au-delà du 99e centile en by_subsection (p99 12837 sur
# 26553 fragments) -- l'écrasante majorité des sections passent donc
# toujours en entier, sans jamais toucher ce seuil, tout en couvrant
# confortablement les deux cas réels du lot 8c qui devaient rester lisibles
# d'un coup (U2.02.01, 5252 caractères ; U2.04.06, 14341 caractères) et en
# arrêtant les deux qui posaient effectivement problème (U2.03.09, 180063 et
# 387825 caractères). Script de mesure : compte rendu du lot 14.
_DEFAULT_MAX_SECTION_CHARS = 20_000


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


def _section_outline(
    content: str, *, line_offset: int
) -> tuple[SectionOutlineEntry, ...]:
    """Headings found *inside* `content`, absolute lines, self-heading dropped.

    Reuses `split_into_subsections` (lot 7) exactly as-is -- no second
    heading detector. Its first returned span is either `content`'s own
    heading (already known to the caller as `DocumentSection.section_path`,
    so dropped here) or, when `content` has no heading at all, the entire
    text under an empty `title_path`, also dropped: either way, an empty
    result correctly means "no finer navigation inside this fragment, only
    line ranges do." `line_offset` converts the spans' own 1-indexed
    relative line numbers to the absolute source-file lines a caller can
    feed straight back into `line_start`/`line_end`.
    """
    spans = split_into_subsections(content)
    if not spans or not spans[0].title_path:
        return ()
    return tuple(
        SectionOutlineEntry(
            title_path=span.title_path,
            line_start=span.line_start + line_offset,
            line_end=span.line_end + line_offset,
        )
        for span in spans[1:]
    )


def to_document_section(
    entry: dict[str, Any],
    *,
    line_start: int | None = None,
    line_end: int | None = None,
    max_chars: int = _DEFAULT_MAX_SECTION_CHARS,
) -> DocumentSection:
    """One corpus entry, by default whole (lot 8c, K1; ranged, lot 14, L1).

    `content` is the corpus entry's own raw content, exactly as persisted by
    `build_bm25_index` (never re-read from the fragments JSONL, which would
    be a second, divergence-prone source of the same text). `line_start`/
    `line_end` (both required together, absolute source-file lines,
    1-indexed inclusive) select a sub-range of that content; omitted, the
    whole fragment is the implicit request. Either way, if the resulting
    slice is longer than `max_chars`, `content` comes back `None` rather
    than cut short -- `outline`/`guidance` explain what is available and
    how to ask for a narrower range instead, computed over the *whole*
    fragment so every navigable heading is visible regardless of which
    slice was actually requested (CLAUDE.md, "jamais de troncature muette").

    Raises `ValueError` for a range outside the fragment's own bounds, or
    with `line_start > line_end` -- never silently clamped to what exists.
    """
    full_content = entry.get("content", "")
    total_line_start: int = entry["line_start"]
    total_line_end: int = entry["line_end"]
    # `keepends=True` + `"".join(...)` round-trips `full_content` exactly,
    # trailing blank lines included (`"".join(s.splitlines(keepends=True))
    # == s` for any `s`) -- `splitlines()` + `"\n".join(...)` (lot 7's own
    # fragment-building convention, `doc_fragments.py`) drops a final blank
    # line's newline on a *second* such round-trip, which this function
    # would otherwise perform on every full-section request: a silent,
    # unintended edit of already-persisted content this project never
    # allows (CLAUDE.md, "ne jamais modifier ni tronquer ... sans
    # nécessité").
    lines = full_content.splitlines(keepends=True)

    if (line_start is None) != (line_end is None):
        message = "line_start et line_end doivent être donnés ensemble."
        raise ValueError(message)

    requested_start = total_line_start if line_start is None else line_start
    requested_end = total_line_end if line_end is None else line_end
    if requested_start > requested_end:
        message = f"line_start ({requested_start}) > line_end ({requested_end})."
        raise ValueError(message)
    if requested_start < total_line_start or requested_end > total_line_end:
        message = (
            f"Plage demandée ({requested_start}-{requested_end}) hors des bornes "
            f"du fragment ({total_line_start}-{total_line_end})."
        )
        raise ValueError(message)

    relative_start = requested_start - total_line_start
    relative_end = requested_end - total_line_start
    requested_content = "".join(lines[relative_start : relative_end + 1])
    is_full_section = (
        requested_start == total_line_start and requested_end == total_line_end
    )

    content: str | None = requested_content
    outline: tuple[SectionOutlineEntry, ...] = ()
    guidance: str | None = None
    if len(requested_content) > max_chars:
        content = None
        outline = _section_outline(full_content, line_offset=total_line_start - 1)
        guidance = (
            f"Section trop volumineuse pour être renvoyée en une fois "
            f"({len(requested_content)} caractères pour les lignes "
            f"{requested_start}-{requested_end}, seuil {max_chars}). Demandez une "
            "plage plus étroite via line_start/line_end (bornes valides : "
            f"{total_line_start}-{total_line_end})"
            + (
                ", en s'appuyant si besoin sur le plan des sous-sections ci-dessus."
                if outline
                else " : aucune sous-section détectée à l'intérieur de ce fragment."
            )
        )

    return DocumentSection(
        fragment_id=entry["fragment_id"],
        document_id=entry["document_id"],
        document_title=entry.get("document_title"),
        family=entry["family"],
        aster_version=entry["aster_version"],
        section_path=tuple(entry["section_path"]),
        source_path=entry["source_path"],
        source_commit=entry["source_commit"],
        line_start=total_line_start,
        line_end=total_line_end,
        related_commands=tuple(entry.get("related_commands", ())),
        granularity=entry["granularity"],
        content_length=len(full_content),
        requested_line_start=requested_start,
        requested_line_end=requested_end,
        requested_length=len(requested_content),
        is_full_section=is_full_section,
        content=content,
        outline=outline,
        guidance=guidance,
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
