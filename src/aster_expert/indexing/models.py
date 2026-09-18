"""Data models for the lexical index and its search results (lot 7, D4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.parsing.fragment_models import FragmentGranularity

TextEnrichment = Literal["none", "e1_title_section_keywords_scoped"]


class SearchHit(BaseModel):
    """One ranked result of `aster-expert search` (lot 7, D4).

    Carries everything `docs/metadata.md` §6 requires of a citation
    (document id, section, version, source path, source revision) directly
    on the hit, so a caller never has to re-join against the fragments file
    to display or cite a result.
    """

    model_config = ConfigDict(frozen=True)

    score: float
    fragment_id: str
    document_id: str
    document_title: str | None
    family: str
    aster_version: str
    section_path: tuple[str, ...]
    source_path: str
    source_commit: str
    line_start: int
    line_end: int
    related_commands: tuple[str, ...]
    granularity: FragmentGranularity
    excerpt: str


class SectionOutlineEntry(BaseModel):
    """One heading found *inside* an over-threshold `DocumentSection` (lot 14, L1).

    `title_path` is relative to the section itself (never re-prefixed with
    `DocumentSection.section_path`, already known to the caller) --
    `line_start`/`line_end` are absolute source-file lines, directly usable
    as the next call's `line_start`/`line_end` without any arithmetic on the
    caller's part.
    """

    model_config = ConfigDict(frozen=True)

    title_path: tuple[str, ...]
    line_start: int
    line_end: int


class DocumentSection(BaseModel):
    """The content of one fragment, by default whole (lot 8c, K1; lot 14, L1).

    Carries the same citation fields as `SearchHit` (document id, section,
    version, source path, source revision). `SearchHit.excerpt` is capped at
    `_EXCERPT_CHARS` (280) for a ranked list of many results -- this model
    deliberately has no equivalent fixed cut, but it is not unconditional
    either: a request whose resulting slice would exceed
    `_DEFAULT_MAX_SECTION_CHARS` gets `content=None` rather than a silent
    truncation (CLAUDE.md, "une troncature muette est précisément le défaut
    qu'on corrige") -- `outline` and `guidance` are populated in that case,
    always explaining what is missing and how to ask for less.

    `line_start`/`line_end` are the whole fragment's own absolute bounds
    (unchanged meaning since lot 8c); `requested_line_start`/
    `requested_line_end` are the bounds of what was actually asked for
    (the whole fragment by default) and `requested_length` is that slice's
    size, reported whether or not `content` was actually returned.
    `content_length` stays the size of the *whole* fragment, regardless of
    what was requested, so a caller always knows the total before deciding
    how to page through it.
    """

    model_config = ConfigDict(frozen=True)

    fragment_id: str
    document_id: str
    document_title: str | None
    family: str
    aster_version: str
    section_path: tuple[str, ...]
    source_path: str
    source_commit: str
    line_start: int
    line_end: int
    related_commands: tuple[str, ...]
    granularity: FragmentGranularity
    content_length: int
    requested_line_start: int
    requested_line_end: int
    requested_length: int
    is_full_section: bool
    content: str | None
    outline: tuple[SectionOutlineEntry, ...] = ()
    guidance: str | None = None


class IndexBuildSummary(BaseModel):
    """Result of `aster-expert index build` (lot 7, D4)."""

    model_config = ConfigDict(frozen=True)

    granularity: FragmentGranularity
    fragment_count: int
    vocabulary_size: int
    index_dir: str
    text_enrichment: TextEnrichment = "none"
