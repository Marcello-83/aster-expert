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


class DocumentSection(BaseModel):
    """The full, untruncated content of one fragment (lot 8c, K1).

    Carries the same citation fields as `SearchHit` (document id, section,
    version, source path, source revision) plus the fragment's exact
    content, never re-rendered and never cut short: `SearchHit.excerpt` is
    capped at `_EXCERPT_CHARS` (280) for a ranked list of many results, a
    limit this model deliberately has no equivalent of. `content_length` is
    reported alongside `content` so a caller can see a section is large
    without that size ever being a reason to cut it (CLAUDE.md, "une
    troncature muette est précisément le défaut qu'on corrige").
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
    content: str
    content_length: int


class IndexBuildSummary(BaseModel):
    """Result of `aster-expert index build` (lot 7, D4)."""

    model_config = ConfigDict(frozen=True)

    granularity: FragmentGranularity
    fragment_count: int
    vocabulary_size: int
    index_dir: str
    text_enrichment: TextEnrichment = "none"
