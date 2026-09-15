"""Command schema models, conforming to docs/metadata.md, section 2."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["required", "optional", "hidden", "default"]


class SimpleKeywordSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: list[str]
    kind: Literal["simple"]
    status: Status
    value_type: str | list[str]
    allowed_values: list[str | int | float] | None
    default: Any
    min_values: int | None
    max_values: int | None
    condition: list[str]


class FactorKeywordSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: list[str]
    kind: Literal["factor"]
    status: Status
    min_occurrences: int | None
    max_occurrences: int | None
    condition: list[str]
    children: list[KeywordSchema]


KeywordSchema = Annotated[
    SimpleKeywordSchema | FactorKeywordSchema, Field(discriminator="kind")
]

FactorKeywordSchema.model_rebuild()


class CommandSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str
    aster_version: str
    image_digest: str
    catalogue_source: str
    catalogue_hash: str
    kind: Literal["operator", "macro", "procedure", "formule"]
    result_type: str | None
    result_type_dynamic: bool
    docu: str | None
    keywords: list[KeywordSchema]
    extracted_at: datetime


class ExtractionAnomaly(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str
    kind: str
    detail: str


class ExtractionSummary(BaseModel):
    """Conforms to the `catalogue_summary.json` deliverable of lot 4."""

    model_config = ConfigDict(frozen=True)

    total_exposed: int
    total_extracted: int
    kind_counts: dict[str, int]
    encountered_classes: list[str]
    anomalies: list[ExtractionAnomaly]
