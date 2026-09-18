"""Response envelopes for the MCP tools (lot 8, H1/H2).

`docs/development-plan.md` (lot 8) requires every tool contract to be
defined by the pydantic models the project already has, never redefined by
hand. Three of the four tools have no existing model that also carries a
validation level, so a thin envelope is added here for those — it only ever
wraps an existing model (`SearchHit`, `CommandSchema`, `KeywordSchema`,
`CommFileAnalysis`) as a field, never repeats or renames one of its
attributes. `validate_comm`'s output needs no envelope: `ValidationReport`
(`aster_expert.validation.models`) already carries its own
`validation_level` field (always `"B"`), so the MCP tool returns it
unwrapped.

Every envelope's `validation_level` is `"A"` for the same reason in all
three cases: none of `search_codeaster_docs`, `get_command_schema`, or
`analyze_comm` confronts a specific file to the catalogue, executes
anything, or checks a physical result — each is a documentary answer, not
executed here (CLAUDE.md, level A), even though `get_command_schema` reads
the catalogue itself (the syntactic ground truth, ADR-001) rather than a
manual: that distinction is carried by `command_schema`/`keyword_variants`
being present at all, not by a different letter grade the project's fixed
A-E scale has no room for.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.catalogue.models import CommandSchema, KeywordSchema
from aster_expert.indexing.models import SearchHit
from aster_expert.parsing.models import CommFileAnalysis


class SearchDocsResult(BaseModel):
    """`search_codeaster_docs` (lot 8, H1)."""

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    query: str
    profile: str
    priority_families: tuple[str, ...]
    priority_mode: Literal["soft", "hard"]
    results: list[SearchHit]


class CommandSchemaResult(BaseModel):
    """`get_command_schema` (lot 8, H1).

    `keyword_variants` is populated only when a `keyword` path was given, and
    lists *every* variant of that path (docs/metadata.md §2: `path` alone
    never identifies a single node) -- `None` when no `keyword` was given,
    distinct from an empty list: a path that matches nothing raises rather
    than being reported as zero variants
    (`aster_expert.catalogue.query.find_keyword_variants`).
    """

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    command_schema: CommandSchema
    keyword_variants: list[KeywordSchema] | None = None


class CommAnalysisResult(BaseModel):
    """`analyze_comm` (lot 8, H1)."""

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    analysis: CommFileAnalysis
