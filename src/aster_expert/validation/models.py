"""Level B validation report models, conforming to docs/metadata.md, section 4."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


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


class CommandCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    checked: int = 0
    not_checked: int = 0
    errors: int = 0


class ValidationSummary(BaseModel):
    """Summary mode of a report (lot 48 bis, audit R10 c).

    Counts by command and the coverage; the full lists stay available by asking for
    a command or a range of lines."""

    model_config = ConfigDict(frozen=True)

    statements_total: int
    checked: int
    not_checked: int
    errors: int
    coverage_rate: float
    by_command: dict[str, CommandCounts]
    errors_omitted: int = 0
    not_checked_omitted: int = 0


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_path: str
    aster_version: str
    image_digest: str
    validation_level: Literal["B"]
    catalogue_hash: str
    # Lot 48 bis (audit A16) : `valid` n'est vrai que si AUCUNE commande n'est
    # restée hors du catalogue. `verdict` distingue « invalide » (une erreur),
    # « partiel » (aucune erreur, mais des commandes non confrontées) et
    # « valide » (toutes confrontées, aucune erreur). Les deux champs sont
    # toujours dérivés de `errors` et `commands_not_checked`.
    verdict: Literal["valide", "partiel", "invalide"] = "valide"
    valid: bool = True
    errors: list[ValidationFinding]
    warnings: list[str]
    commands_checked: list[CheckedEntry]
    commands_not_checked: list[NotCheckedEntry]
    checked_at: datetime
    detail: Literal["complet", "resume", "filtre"] = "complet"
    """`complet`: every list in full. `resume`: `commands_checked` replaced by
    `summary`, errors and unverified commands capped. `filtre`: only the asked
    command or lines. The verdict is the one of the whole file in every mode."""
    summary: ValidationSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_verdict(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "verdict" in data:
            return data
        errors = data.get("errors") or []
        not_checked = data.get("commands_not_checked") or []
        verdict = "invalide" if errors else ("partiel" if not_checked else "valide")
        return {**data, "verdict": verdict, "valid": verdict == "valide"}
