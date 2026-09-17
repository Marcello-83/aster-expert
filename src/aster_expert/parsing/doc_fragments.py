"""Découpage du corpus documentaire en fragments (lot 7, D1/D2/D3).

Réutilise l'analyse structurelle du lot 6 (`aster_expert.ingestion.inventory`)
plutôt qu'un nouveau parseur : un document est un répertoire, une section est
un fichier `.rst` de ce répertoire (`docs/corpus.md` §7, `DocumentEntry.files`
du lot 6). Ce module ne relit jamais l'arborescence lui-même — il consomme
`data/raw/inventory.jsonl` — et ne reconstruit jamais la notion de famille ou
d'identifiant documentaire, déjà établie par l'inventaire.

Deux granularités (lot 7, D2), tranchées par la mesure sur le banc
d'évaluation, jamais par préférence esthétique :

- ``by_file`` : un fragment par fichier de section, tel que la structure du
  dépôt le donne — la règle par défaut de `docs/corpus.md` §7.
- ``by_subsection`` : identique à ``by_file`` pour tout fichier dont le
  nombre de lignes ne dépasse pas ``DEFAULT_SUBSECTION_LINE_THRESHOLD``, et
  découpé au niveau de chaque en-tête reStructuredText sinon.

Le contenu d'un fragment est toujours une tranche brute du texte source
(``str.splitlines()`` puis rejointe), jamais un rendu docutils : c'est ce qui
garantit qu'une formule ``.. math::``/``:math:`` apparaît dans le fragment
exactement comme dans la source (lot 7, instruction D1), et c'est aussi ce
qui rend le contrôle de non-perte (D3) trivial à vérifier — une tranche ne
peut pas perdre de texte, seul un découpage incorrect des bornes le pourrait,
ce que `verify_full_coverage` vérifie explicitement plutôt que de le
supposer.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.ingestion.models import DocumentEntry
from aster_expert.parsing.fragment_models import (
    DocumentFragment,
    FragmentGranularity,
)

# Choisi par mesure, pas deviné (lot 7, D2) : la distribution réelle des
# 13116 fichiers de section du corpus 17.4.0 synchronisé (hors
# `other_pages`) a une médiane de 41 lignes et un 90e centile à 155 lignes
# (`wc -l` sur chaque fichier, script de mesure du compte rendu de ce lot).
# 150 est retenu, juste sous ce 90e centile : la grande majorité des
# fichiers de section (~90 %) restent un fragment unique, identique à la
# granularité `by_file` ; seule la longue traîne (dictionnaires de
# mots-clés, syntaxes complètes, chapitres théoriques) est effectivement
# redécoupée. Confirmé ou infirmé par le banc du lot 7, jamais présenté
# comme un optimum démontré au-delà de cette mesure.
DEFAULT_SUBSECTION_LINE_THRESHOLD = 150


class FragmentBuildError(Exception):
    """Raised when a fragment's boundaries fail the no-loss control (D3).

    Never caught silently: a bug in the line-range arithmetic here would
    otherwise produce a fragment set that quietly drops or duplicates
    source text, exactly what CLAUDE.md forbids ("ne jamais neutraliser
    une alarme sans en expliquer la cause").
    """


@dataclass(frozen=True)
class SectionHeader:
    """One detected reStructuredText title line (underline style only)."""

    line_index: int  # 0-indexed index of the title line itself
    title: str
    level: int  # 1-based, by order of first-seen underline character


def _adornment_char(line: str) -> str | None:
    """The single repeated punctuation character of a pure adornment line.

    `None` for a blank line, a line with mixed characters, or one made of
    letters/digits/whitespace (never an adornment in reStructuredText).
    """
    stripped = line.strip()
    if not stripped or len(set(stripped)) != 1:
        return None
    char = stripped[0]
    if char.isalnum():
        return None
    return char


def find_section_headers(lines: list[str]) -> list[SectionHeader]:
    """Every underline-style reST title in `lines` (0-indexed, no line terminators).

    Deliberately narrow: only the common underline-only convention observed
    on this corpus (title line, then an adornment line at least as long as
    the title — the docutils rule) is recognized; an overline+underline
    pair is not distinguished from a plain underline (never observed in the
    sampled corpus files for this lot, see the batch report) — a known,
    documented limitation, not a silent guess. A title line is never itself
    a pure adornment line, which rules out mistaking a transition marker or
    a table border for a title sitting above another adornment line.
    """
    headers: list[SectionHeader] = []
    level_by_char: dict[str, int] = {}
    i = 0
    n = len(lines)
    while i < n - 1:
        title_line = lines[i]
        stripped_title = title_line.strip()
        underline_char = _adornment_char(lines[i + 1])
        if (
            stripped_title
            and underline_char is not None
            and len(lines[i + 1].strip()) >= len(stripped_title)
            and _adornment_char(title_line) is None
        ):
            if underline_char not in level_by_char:
                level_by_char[underline_char] = len(level_by_char) + 1
            headers.append(
                SectionHeader(
                    line_index=i,
                    title=stripped_title,
                    level=level_by_char[underline_char],
                )
            )
            i += 2
            continue
        i += 1
    return headers


def _section_path_stack(headers: list[SectionHeader]) -> list[tuple[str, ...]]:
    """The hierarchical title stack active at each header, outermost first.

    A header at level L closes every open header at level >= L before
    pushing itself — the same nesting rule docutils applies to underline
    adornment characters, never a fixed depth guessed from indentation
    (reST headers carry no indentation of their own).
    """
    stack: list[tuple[int, str]] = []
    paths: list[tuple[str, ...]] = []
    for header in headers:
        while stack and stack[-1][0] >= header.level:
            stack.pop()
        stack.append((header.level, header.title))
        paths.append(tuple(title for _, title in stack))
    return paths


@dataclass(frozen=True)
class SubsectionSpan:
    """One contiguous, non-overlapping slice of a section file's raw lines.

    `title_path` is empty for a file with no detected header at all, or for
    the leading content of a file that precedes its first header — never
    guessed from the file name.
    """

    title_path: tuple[str, ...]
    line_start: int  # 1-indexed, inclusive
    line_end: int  # 1-indexed, inclusive
    content: str


def split_into_subsections(text: str) -> list[SubsectionSpan]:
    """Partition `text` into header-bounded spans covering every line exactly once.

    Never called on a file at or under `DEFAULT_SUBSECTION_LINE_THRESHOLD`
    lines by `build_fragments_for_document` (the whole file is then already
    one fragment, identical to the `by_file` granularity) — this function
    itself does not apply the threshold, so it can be exercised directly by
    tests regardless of length.
    """
    lines = text.splitlines()
    headers = find_section_headers(lines)
    if not headers:
        return [
            SubsectionSpan(
                title_path=(), line_start=1, line_end=len(lines), content=text
            )
        ]

    paths = _section_path_stack(headers)
    spans: list[SubsectionSpan] = []
    if headers[0].line_index > 0:
        spans.append(
            SubsectionSpan(
                title_path=(),
                line_start=1,
                line_end=headers[0].line_index,
                content="\n".join(lines[: headers[0].line_index]),
            )
        )
    for idx, header in enumerate(headers):
        start0 = header.line_index
        end0 = headers[idx + 1].line_index if idx + 1 < len(headers) else len(lines)
        spans.append(
            SubsectionSpan(
                title_path=paths[idx],
                line_start=start0 + 1,
                line_end=end0,
                content="\n".join(lines[start0:end0]),
            )
        )
    return spans


def verify_full_coverage(text: str, spans: list[SubsectionSpan]) -> None:
    """Raise `FragmentBuildError` unless `spans` partitions every line once.

    The concrete, checked form of the no-loss control (docs/corpus.md §7,
    lot 7 D3): reconstructs the file's lines from the spans' declared
    ranges and compares them, line for line, against the source — never a
    byte-count heuristic, which a compensating pair of errors (one span too
    long, the next too short by the same amount) could pass unnoticed.
    """
    lines = text.splitlines()
    reconstructed: list[str] = []
    for span in spans:
        reconstructed.extend(lines[span.line_start - 1 : span.line_end])
    if reconstructed != lines:
        raise FragmentBuildError(
            f"couverture incomplète ou incorrecte : {len(reconstructed)} lignes "
            f"reconstruites contre {len(lines)} lignes sources"
        )


def slugify(text: str) -> str:
    """Deterministic, filesystem/id-safe token for a section title.

    Never used for `content` or `section_path` themselves (those keep the
    exact source text) — only to build the `#`-suffix of `fragment_id`.
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    token = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return token or "section"


def load_related_commands(command_map_path: Path) -> dict[str, tuple[str, ...]]:
    """Document id -> catalogue (or confirmed uncatalogued) command names.

    Reuses the lot 6/6b table (`data/processed/command_document_map.json`)
    as-is: never re-derives a command/document link from fragment text,
    which would risk a looser, undocumented match than the one already
    established from the document's own title (lot 6, I5).
    """
    raw = json.loads(command_map_path.read_text(encoding="utf-8"))
    by_document: dict[str, list[str]] = defaultdict(list)
    for edge in raw["edges"]:
        by_document[edge["document_id"]].append(edge["command"])
    for mention in raw.get("documents_naming_uncatalogued_command", []):
        by_document[mention["document_id"]].append(mention["command"])
    return {
        document_id: tuple(sorted(set(commands)))
        for document_id, commands in by_document.items()
    }


def load_related_documents(xref_path: Path) -> dict[str, tuple[str, ...]]:
    """Source document id -> resolved internal cross-reference targets.

    Reuses the lot 6/6b graph (`data/processed/xref_graph.json`) edges
    as-is (`via`-agnostic: both `explicit_label` and `autosectionlabel`
    resolutions count) — never a fresh scan of `:ref:` roles here.
    """
    raw = json.loads(xref_path.read_text(encoding="utf-8"))
    by_document: dict[str, list[str]] = defaultdict(list)
    for edge in raw["edges"]:
        by_document[edge["source_document_id"]].append(edge["target_document_id"])
    return {
        document_id: tuple(sorted(set(targets)))
        for document_id, targets in by_document.items()
    }


def build_fragments_for_document(
    document: DocumentEntry,
    *,
    repo_root: Path,
    granularity: FragmentGranularity,
    aster_version: str,
    related_commands: tuple[str, ...] = (),
    related_documents: tuple[str, ...] = (),
    subsection_line_threshold: int = DEFAULT_SUBSECTION_LINE_THRESHOLD,
    now: datetime,
) -> Iterator[DocumentFragment]:
    """Every fragment of one document, at the requested granularity.

    Reads each `.rst` file composing the document once, never more than one
    file's content held in memory at a time beyond what `str.splitlines()`
    itself needs for that single file (memory constraint,
    docs/development-plan.md, lot 7).
    """
    doc_dir = repo_root / document.relative_path
    seen_ids: set[str] = set()

    for file_rel in document.files:
        if not file_rel.endswith(".rst"):
            continue
        file_path = doc_dir / file_rel
        text = file_path.read_text(encoding="utf-8", errors="replace")
        section_stem = file_rel[: -len(".rst")]
        line_count = len(text.splitlines())

        if granularity == "by_file" or line_count <= subsection_line_threshold:
            spans = [
                SubsectionSpan(
                    title_path=(),
                    line_start=1,
                    line_end=line_count,
                    content=text,
                )
            ]
        else:
            spans = split_into_subsections(text)
            verify_full_coverage(text, spans)

        for span in spans:
            section_path = (section_stem, *span.title_path)
            base_id = f"{document.document_id}#{section_stem}"
            if span.title_path:
                base_id += "::" + "/".join(slugify(t) for t in span.title_path)
            fragment_id = base_id
            disambiguator = 2
            while fragment_id in seen_ids:
                fragment_id = f"{base_id}~{disambiguator}"
                disambiguator += 1
            seen_ids.add(fragment_id)

            yield DocumentFragment(
                fragment_id=fragment_id,
                granularity=granularity,
                source_name=document.source_name,
                source_commit=document.source_commit,
                document_id=document.document_id,
                document_title=document.title,
                family=document.family,
                aster_version=aster_version,
                section_path=section_path,
                content=span.content,
                content_hash=(
                    "sha256:" + hashlib.sha256(span.content.encode("utf-8")).hexdigest()
                ),
                source_path=f"{document.relative_path}/{file_rel}",
                line_start=span.line_start,
                line_end=span.line_end,
                related_commands=related_commands,
                related_documents=related_documents,
                language="fr",
                extracted_at=now,
            )


@dataclass(frozen=True)
class FragmentBuildSummary:
    granularity: FragmentGranularity
    documents_processed: int
    fragment_count: int
    median_content_chars: int
    threshold_lines: int


def _median(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def build_fragments_streaming(
    *,
    inventory_path: Path,
    repo_root: Path,
    granularity: FragmentGranularity,
    aster_version: str,
    command_map_path: Path,
    xref_path: Path,
    output_path: Path,
    subsection_line_threshold: int = DEFAULT_SUBSECTION_LINE_THRESHOLD,
    now: datetime | None = None,
) -> FragmentBuildSummary:
    """Build one granularity's fragment set over the whole inventory.

    Streams: `inventory.jsonl` (small, metadata only) is read whole, but the
    corpus text itself is never loaded beyond one document's own files at a
    time — fragments are written to `output_path` as they are produced,
    never accumulated in a list first (docs/development-plan.md, lot 7,
    memory constraint on the 13116-file corpus).
    """
    resolved_now = now if now is not None else datetime.now(UTC)
    related_commands_by_document = load_related_commands(command_map_path)
    related_documents_by_document = load_related_documents(xref_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    documents_processed = 0
    fragment_count = 0
    content_lengths: list[int] = []

    with output_path.open("w", encoding="utf-8") as handle:
        for line in inventory_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            document = DocumentEntry.model_validate_json(line)
            fragments = build_fragments_for_document(
                document,
                repo_root=repo_root,
                granularity=granularity,
                aster_version=aster_version,
                related_commands=related_commands_by_document.get(
                    document.document_id, ()
                ),
                related_documents=related_documents_by_document.get(
                    document.document_id, ()
                ),
                subsection_line_threshold=subsection_line_threshold,
                now=resolved_now,
            )
            for fragment in fragments:
                handle.write(fragment.model_dump_json())
                handle.write("\n")
                fragment_count += 1
                content_lengths.append(len(fragment.content))
            documents_processed += 1

    return FragmentBuildSummary(
        granularity=granularity,
        documents_processed=documents_processed,
        fragment_count=fragment_count,
        median_content_chars=_median(content_lengths),
        threshold_lines=subsection_line_threshold,
    )


def default_fragments_path(
    project_root: Path, granularity: FragmentGranularity
) -> Path:
    return project_root / "data" / "processed" / f"fragments_{granularity}.jsonl"
