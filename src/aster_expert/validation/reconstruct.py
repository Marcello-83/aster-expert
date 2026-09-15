"""M2: reconstruct `checkCommandSyntax`-ready arguments per statement.

Decides, per statement, whether it is even attempted (the ABSOLUTE RULE from
docs/development-plan.md, lot 10: no false positive, ever — a statement with
any of the four disqualifying conditions is excluded before any argument is
built, never fed a half-reconstructed guess). For the statements that pass,
builds a JSON-safe keyword tree: literal values as-is (a `complex` value gets
the `__complex__` marker, not JSON-native otherwise), concept references
replaced by a `__concept_type__` marker naming the Aster type established by
`aster_expert.validation.concept_types` (M1), factor keywords turned into a
single dict (one occurrence) or a list of dicts (several) — see
scripts/check_command_syntax.py for how these markers are consumed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aster_expert.parsing.models import (
    CommFileAnalysis,
    ConceptReferenceValue,
    KeywordNode,
    LiteralValue,
    ParseWarning,
    SimpleKeywordValue,
    SimpleValue,
    Statement,
)
from aster_expert.validation.concept_types import ConceptType, resolve_concept_type


@dataclass(frozen=True)
class CheckRequest:
    statement_index: int
    command: str
    keywords: dict[str, Any]


@dataclass(frozen=True)
class Excluded:
    statement_index: int
    command: str
    reasons: list[str]


def plan_statements(
    analysis: CommFileAnalysis, concept_types: dict[str, ConceptType]
) -> tuple[list[CheckRequest], list[Excluded], set[int]]:
    """Plan every statement. Returns (requests, excluded, matched_warning_ids).

    `matched_warning_ids` are indices into `analysis.parse_warnings` (lot 9
    warnings have no `statement_index` of their own) that were attributed to
    at least one statement by line-range overlap — the caller can report the
    remainder as concerning no captured statement at all.
    """
    requests: list[CheckRequest] = []
    excluded: list[Excluded] = []
    matched_warning_ids: set[int] = set()

    for statement in analysis.statements:
        overlapping = _overlapping_warning_ids(statement, analysis.parse_warnings)
        matched_warning_ids |= overlapping
        outcome = plan_statement(
            statement,
            concept_types=concept_types,
            parse_warnings=analysis.parse_warnings,
            overlapping_warning_ids=overlapping,
        )
        if isinstance(outcome, CheckRequest):
            requests.append(outcome)
        else:
            excluded.append(outcome)

    return requests, excluded, matched_warning_ids


def _overlapping_warning_ids(
    statement: Statement, parse_warnings: list[ParseWarning]
) -> set[int]:
    return {
        i
        for i, warning in enumerate(parse_warnings)
        if warning.line is not None
        and statement.line_start <= warning.line <= statement.line_end
    }


def plan_statement(
    statement: Statement,
    *,
    concept_types: dict[str, ConceptType],
    parse_warnings: list[ParseWarning],
    overlapping_warning_ids: set[int],
) -> CheckRequest | Excluded:
    reasons: list[str] = []

    if statement.control_flow:
        reasons.append(
            "nested inside Python control flow ("
            + ".".join(statement.control_flow)
            + "): lot 9 does not determine whether, or how many times, it runs"
        )
    if statement.dynamic:
        reasons.extend(f"unresolved keyword: {path}" for path in statement.unresolved)
    for warning_id in sorted(overlapping_warning_ids):
        warning = parse_warnings[warning_id]
        reasons.append(
            f"lot 9 parse_warning at line {warning.line} "
            f"({warning.node_type}): {warning.message}"
        )

    if reasons:
        # A statement already known unreliable is never fed to
        # checkCommandSyntax: reconstructing a half-built dict from it would
        # itself be a guess, exactly what the ABSOLUTE RULE forbids.
        return Excluded(statement.index, statement.command, reasons)

    keywords, concept_reasons = _reconstruct_keywords(statement.keywords, concept_types)
    reasons.extend(concept_reasons)

    if statement.reuse is not None:
        info = resolve_concept_type(concept_types, statement.reuse)
        if info.aster_type is None:
            reasons.append(
                f"reuse= references concept {statement.reuse!r} of unknown "
                f"type: {info.reason}"
            )
        else:
            keywords["reuse"] = {"__concept_type__": info.aster_type}

    if reasons:
        return Excluded(statement.index, statement.command, reasons)
    return CheckRequest(statement.index, statement.command, keywords)


def _reconstruct_keywords(
    keywords: Mapping[str, KeywordNode],
    concept_types: dict[str, ConceptType],
    prefix: str = "",
) -> tuple[dict[str, Any], list[str]]:
    result: dict[str, Any] = {}
    reasons: list[str] = []
    for name, node in keywords.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(node, SimpleKeywordValue):
            value, value_reasons = _reconstruct_value(node.value, path, concept_types)
            reasons.extend(value_reasons)
            if not value_reasons:
                result[name] = value
        else:
            occurrences: list[dict[str, Any]] = []
            for i, occurrence in enumerate(node.occurrences):
                occ_dict, occ_reasons = _reconstruct_keywords(
                    occurrence.keywords, concept_types, f"{path}[{i}]"
                )
                reasons.extend(occ_reasons)
                occurrences.append(occ_dict)
            result[name] = occurrences[0] if len(occurrences) == 1 else occurrences
    return result, reasons


def _reconstruct_value(
    value: SimpleValue, path: str, concept_types: dict[str, ConceptType]
) -> tuple[Any, list[str]]:
    if isinstance(value, LiteralValue):
        return _json_safe(value.value), []
    if isinstance(value, ConceptReferenceValue):
        info = resolve_concept_type(concept_types, value.concept)
        if info.aster_type is None:
            reason = (
                f"keyword {path!r} references concept {value.concept!r} of "
                f"unknown type: {info.reason}"
            )
            return None, [reason]
        return {"__concept_type__": info.aster_type}, []
    message = (
        f"unrecognized simple keyword value kind at {path!r}: {type(value).__name__}"
    )
    raise TypeError(message)  # pragma: no cover - exhaustive over SimpleValue


def _json_safe(value: Any) -> Any:
    if isinstance(value, complex):
        return {"__complex__": {"real": value.real, "imag": value.imag}}
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    return value
