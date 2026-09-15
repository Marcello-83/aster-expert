"""M1: concept -> Aster type table (docs/development-plan.md, lot 10).

Built entirely from data already on disk (the lot 9 analysis and the lot 4
catalogue): no container invocation is needed for this step.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import CommandSchema
from aster_expert.catalogue.query import load_command_schema
from aster_expert.parsing.models import CommFileAnalysis

REASON_COMMAND_NOT_IN_CATALOGUE = (
    "producing command {command!r} not found in the catalogue"
)
REASON_RESULT_TYPE_DYNAMIC = (
    "producing command {command!r} has a dynamic result type "
    "(result_type_dynamic=true): not determinable without executing it"
)
REASON_CONFLICTING_TYPES = "conflicting types across producing statements: {types}"
REASON_NOT_PRODUCED = (
    "no statement in this file assigns this concept (its producing command "
    "was not captured by the lot 9 parser, or it is not produced here)"
)


@dataclass(frozen=True)
class ConceptType:
    """The resolved type of one concept name, or the reason it is unknown."""

    aster_type: str | None
    reason: str


def build_concept_type_table(
    analysis: CommFileAnalysis, *, catalogue_root: Path, digest: str
) -> tuple[dict[str, ConceptType], list[str]]:
    """Build the concept -> Aster type table.

    Returns `(table, warnings)`. `table` covers every concept name assigned
    by at least one statement in `analysis` (`reuse=` targets included, since
    a `reuse=` value is always also an `assigned_concept` of some earlier
    statement by construction — lot 9 only records `reuse` when the value is
    a plain name). A concept name absent from `table` was never produced in
    this file at all; `resolve_concept_type` below gives both cases the same
    "unknown" treatment.
    """
    producers: dict[str, list[str]] = {}
    for statement in analysis.statements:
        if statement.assigned_concept:
            producers.setdefault(statement.assigned_concept, []).append(
                statement.command
            )

    schema_cache: dict[str, CommandSchema | None] = {}
    table: dict[str, ConceptType] = {}
    warnings: list[str] = []

    for concept, commands in sorted(producers.items()):
        resolved_types: set[str] = set()
        reasons: list[str] = []
        for command in commands:
            if command not in schema_cache:
                try:
                    schema_cache[command] = load_command_schema(
                        catalogue_root, digest, command
                    )
                except CatalogueExtractionError:
                    schema_cache[command] = None
            schema = schema_cache[command]
            if schema is None:
                reasons.append(REASON_COMMAND_NOT_IN_CATALOGUE.format(command=command))
                continue
            if schema.result_type_dynamic or schema.result_type is None:
                reasons.append(REASON_RESULT_TYPE_DYNAMIC.format(command=command))
                continue
            resolved_types.add(schema.result_type)

        if len(resolved_types) == 1:
            table[concept] = ConceptType(
                aster_type=next(iter(resolved_types)), reason=""
            )
        elif len(resolved_types) > 1:
            reason = REASON_CONFLICTING_TYPES.format(types=sorted(resolved_types))
            table[concept] = ConceptType(aster_type=None, reason=reason)
            warnings.append(f"concept {concept!r}: {reason}")
        else:
            table[concept] = ConceptType(
                aster_type=None,
                reason="; ".join(reasons) or "no producing command resolved a type",
            )

    return table, warnings


def resolve_concept_type(table: dict[str, ConceptType], name: str) -> ConceptType:
    """Look up `name`, treating an absent entry the same as a known-unknown one."""
    return table.get(name, ConceptType(aster_type=None, reason=REASON_NOT_PRODUCED))
