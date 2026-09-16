"""Level B validation report models, conforming to docs/metadata.md, section 4."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ValidationFinding(BaseModel):
    """One entry of the report's `errors` list.

    `source` distinguishes a finding `checkCommandSyntax` itself raised
    (the checker was actually called and rejected the reconstructed
    arguments) from one this project determined directly against the local
    catalogue without calling the checker (`UNKNOWN_COMMAND`: there is no
    command object to pass to `checkCommandSyntax` in the first place —
    docs/development-plan.md, lot 10, mechanism M4).
    """

    model_config = ConfigDict(frozen=True)

    code: str
    command: str
    statement_index: int
    line: int
    path: list[str]
    variant_id: str | None
    message: str
    suggestion: str | None
    source: Literal["checkCommandSyntax", "catalogue"]


class CheckedEntry(BaseModel):
    """One command that was actually confronted with the catalogue.

    `ok` is `false` exactly when at least one `ValidationFinding` in the
    report carries this same `statement_index` — kept alongside for a report
    reader who does not want to cross-reference.

    `warnings` (amendment lot 10c, point P1) is non-empty exactly when this
    statement was checked — regardless of its own `ok` — only because a
    concept it directly references got a placeholder from the two-branch
    static rule (`docs/metadata.md` §4) even though that concept's own
    producing statement is itself in `errors` (a real `checkCommandSyntax`
    rejection — never merely `commands_not_checked`: an excluded producer
    triggers no warning here, since its placeholder, if any, is just as
    reliable a catalogue fact as any other static one). This is what keeps
    "non vérifié" and "en erreur" distinct in the report: a warning here
    always names the exact statement in error, never a vague "may be
    unreliable."
    """

    model_config = ConfigDict(frozen=True)

    statement_index: int
    command: str
    line: int
    ok: bool
    warnings: list[str] = []


class NotCheckedEntry(BaseModel):
    """One command declared NOT VERIFIED (docs/development-plan.md, lot 10).

    `reasons` lists every condition that applied among: an unresolved
    keyword, a concept of unknown type, a lot 9 `parse_warning` naming this
    statement, or a non-empty `control_flow` — never just the first one
    found, so a report reader sees the full picture.
    """

    model_config = ConfigDict(frozen=True)

    statement_index: int
    command: str
    line: int
    reasons: list[str]


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_path: str
    aster_version: str
    image_digest: str
    validation_level: Literal["B"]
    catalogue_hash: str
    valid: bool
    errors: list[ValidationFinding]
    warnings: list[str]
    commands_checked: list[CheckedEntry]
    commands_not_checked: list[NotCheckedEntry]
    checked_at: datetime
