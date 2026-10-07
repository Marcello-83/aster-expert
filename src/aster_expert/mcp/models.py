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
from aster_expert.indexing.models import DocumentSection, SearchHit
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

    Before lot 44 a filtered call also returned the whole schema (721 000
    characters for `DEFI_MATERIAU`/`ELAS`, lot 43): the filter lightened
    nothing.
    """

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    command_schema: CommandSchema
    keyword_variants: list[KeywordSchema] | None = None
    keywords_omitted: int = 0
    """Lot 44: with a `keyword` filter, `command_schema` keeps the command's
    metadata only (`keywords` emptied) and the requested subtree is in
    `keyword_variants`; this counts the top-level keywords left out, so the
    omission is stated, never silent. 0 without a filter."""


class CommSummary(BaseModel):
    """Summary mode of `analyze_comm` (lot 48 bis, audit R10 c): the commands by type,
    the concepts, the warnings. The detail of a command or of a range of lines is asked
    for with `command` or `line_start`/`line_end`."""

    model_config = ConfigDict(frozen=True)

    file_path: str
    file_hash: str
    line_count: int
    statements_total: int
    commands_by_type: dict[str, int]
    concepts_count: int
    concepts: list[str]
    """The first concepts in file order, at most `CONCEPTS_SHOWN`."""
    external_files: int
    imported_names: list[str]
    dynamic_statements: int
    control_flow_statements: int
    test_statements: int
    parse_warnings_count: int
    parse_warnings: list[str]
    """The first warnings (`line N (type): message`), at most `WARNINGS_SHOWN`."""
    warnings_omitted: int = 0


class CommAnalysisResult(BaseModel):
    """`analyze_comm` (lot 8, H1; lot 48 bis: summary and filters).

    `detail` is `complet` (the whole analysis), `resume` (`summary` only, chosen
    automatically for a large file) or `filtre` (the statements of one command or of a
    range of lines, in full)."""

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    detail: Literal["complet", "resume", "filtre"] = "complet"
    analysis: CommFileAnalysis | None = None
    summary: CommSummary | None = None


class DocumentSectionResult(BaseModel):
    """`get_document_section` (lot 8c, K1).

    Wraps `DocumentSection` exactly like the three envelopes above wrap
    their own existing model -- `section` is never flattened into this
    envelope's own fields, so `DocumentSection` stays the single place that
    defines what a section is.
    """

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    section: DocumentSection


class ConstatHitResult(BaseModel):
    """One finding of the shared base (lot 41), as `search_constats` returns it.

    `constat_validation_level` is the level the finding itself reached (A
    documentary, B catalogue introspection, C/D execution), distinct from the
    level of the answer (always A: a reading of the base, nothing executed)."""

    model_config = ConfigDict(frozen=True)

    constat_id: str
    summary: str
    topic: str
    option_retained: str | None
    constat_validation_level: Literal["A", "B", "C", "D"]
    aster_version: str
    commands: tuple[str, ...]
    keywords: tuple[str, ...]
    trial_cases: tuple[str, ...]
    origin_project: str
    file: str
    score: int


class SearchConstatsResult(BaseModel):
    """`search_constats` (lot 41, étape 4.3)."""

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    text: str | None
    command: str | None
    keyword: str | None
    total_in_base: int
    results: list[ConstatHitResult]
    guidance: str


class KnowledgeHitResult(BaseModel):
    """One entry of the knowledge base (lot 42), as `search_connaissances`
    returns it. `entry_validation_level` is the level the entry itself reached
    (A to E), `status` its status (`observé`, `établi`, `promu`); the level of
    the answer stays A (a reading of the base, nothing executed)."""

    model_config = ConfigDict(frozen=True)

    id: str
    layer: str
    title: str
    summary: str
    status: Literal["observé", "établi", "promu"]
    entry_validation_level: Literal["A", "B", "C", "D", "E"]
    origin_project: str
    commands: tuple[str, ...]
    keywords: tuple[str, ...]
    file: str
    score: int


class SearchConnaissancesResult(BaseModel):
    """`search_connaissances` (lot 42, étape 3.1)."""

    model_config = ConfigDict(frozen=True)

    validation_level: Literal["A"] = "A"
    text: str | None
    command: str | None
    keyword: str | None
    layers: list[str]
    status: str | None
    total_by_layer: dict[str, int]
    results: list[KnowledgeHitResult]
    guidance: str
