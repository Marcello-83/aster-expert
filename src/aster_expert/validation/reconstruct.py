"""M2: reconstruct `checkCommandSyntax`-ready arguments per statement.

Decides, per statement, whether it is even attempted (the ABSOLUTE RULE from
docs/development-plan.md, lot 10: no false positive, ever). A statement with
any of three purely structural disqualifying conditions -- nested inside
Python control flow, a keyword value lot 9 could not resolve statically, or a
lot 9 `parse_warning` naming it -- is excluded before any argument is built,
never fed a half-reconstructed guess.

Concept-type resolution is deliberately **not** attempted here (amendment,
lot 10b, point A): it used to be, against an offline table built from the
catalogue's static `result_type` alone, which could never resolve a concept
produced by a `result_type_dynamic` command (`sd_prod` is a function) without
guessing. A concept reference is instead reconstructed as a
``{"__concept_ref__": "<name>"}`` marker naming the concept, resolved live,
in file order, by `scripts/check_command_syntax.py` itself -- which calls the
official `Command.get_type_sd_prod` (delegating to the real `sd_prod`,
static or dynamic) once a producing statement's own syntax has been checked.
This is always safe here: every concept reference lot 9 records is, by
construction, the name of a concept assigned by some statement in the same
file (`aster_expert.parsing.comm_parser` never records a
`ConceptReferenceValue` for anything else) -- so this module never needs to
know, or guess, whether that producing statement will actually resolve a
type; it just names the dependency and lets the batch resolve it in order.
The same marker is used for `reuse=`: a reentrant command's produced type is
the reused concept's own type by construction (verified empirically, see the
lot 10b batch report), so no separate case is needed here either -- the
container-side `get_type_sd_prod` call already returns the right answer for
this using the exact same live placeholder.
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

# FORMULE accepts arbitrary extra simple keywords beyond its catalog-declared
# VALE/VALE_C/NOM_PARA: named constants referenced by the expression itself
# (docs/development-plan.md, lot 10b, point E), e.g.
# `FORMULE(NOM_PARA="X", VALE="A*X+B", A=2.0, B=1.0)`. The *official*
# mechanism that strips them before syntax checking is
# `FormulaDefinition.change_syntax` (code_aster/CodeCommands/formule.py):
# it pops every keyword except those three into a private evaluation
# context. That method lives in the executor layer (needs `libaster`,
# unavailable in this container -- docs/architecture.md, ADR-002) and cannot
# be replayed like a catalog `compat_syntax` function can (point B). This is
# a narrow, explicit, empirically-verified substitute for that one method,
# not a hand-rolled grammar: it reproduces exactly the same filter
# (everything but VALE/VALE_C/NOM_PARA is dropped), nothing more.
_FORMULE_CATALOGUE_KEYWORDS = frozenset({"VALE", "VALE_C", "NOM_PARA"})


@dataclass(frozen=True)
class CheckRequest:
    statement_index: int
    command: str
    assigned_concept: str | None
    keywords: dict[str, Any]


@dataclass(frozen=True)
class Excluded:
    statement_index: int
    command: str
    reasons: list[str]


def plan_statements(
    analysis: CommFileAnalysis,
) -> tuple[list[CheckRequest], list[Excluded], set[int]]:
    """Plan every statement. Returns (requests, excluded, matched_warning_ids).

    `requests` is in the same order as `analysis.statements` -- the caller
    (`aster_expert.validation.validate`) must preserve this order when
    sending requests to `scripts/check_command_syntax.py`, which resolves
    `__concept_ref__` markers against a live table built as it processes
    requests in the order given, and therefore depends on producers coming
    before consumers.

    `matched_warning_ids` are indices into `analysis.parse_warnings` (lot 9
    warnings have no `statement_index` of their own) that were attributed to
    at least one statement by line-range overlap -- the caller can report the
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

    keywords = _reconstruct_keywords(statement.keywords)
    if statement.command == "FORMULE":
        keywords = {
            k: v for k, v in keywords.items() if k in _FORMULE_CATALOGUE_KEYWORDS
        }

    if statement.reuse is not None:
        keywords["reuse"] = {"__concept_ref__": statement.reuse}

    return CheckRequest(
        statement.index, statement.command, statement.assigned_concept, keywords
    )


def _reconstruct_keywords(
    keywords: Mapping[str, KeywordNode], prefix: str = ""
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, node in keywords.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(node, SimpleKeywordValue):
            result[name] = _reconstruct_value(node.value, path)
        else:
            occurrences = [
                _reconstruct_keywords(occurrence.keywords, f"{path}[{i}]")
                for i, occurrence in enumerate(node.occurrences)
            ]
            result[name] = occurrences[0] if len(occurrences) == 1 else occurrences
    return result


def _reconstruct_value(value: SimpleValue, path: str) -> Any:
    if isinstance(value, LiteralValue):
        return _json_safe(value.value)
    if isinstance(value, ConceptReferenceValue):
        return {"__concept_ref__": value.concept}
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


__all__ = ["CheckRequest", "Excluded", "plan_statement", "plan_statements"]
