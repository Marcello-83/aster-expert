"""Data models for the lexical index and its search results (lot 7, D4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.parsing.fragment_models import FragmentGranularity

TextEnrichment = Literal["none", "e1_title_section_keywords"]


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


class IndexBuildSummary(BaseModel):
    """Result of `aster-expert index build` (lot 7, D4)."""

    model_config = ConfigDict(frozen=True)

    granularity: FragmentGranularity
    fragment_count: int
    vocabulary_size: int
    index_dir: str
    text_enrichment: TextEnrichment = "none"
