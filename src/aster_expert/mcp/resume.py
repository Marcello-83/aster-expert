"""Summary and filters of `analyze_comm` / `validate_comm` (lot 48 bis, audit R10 c).

On the 1 695-line `.comm` of the jetty, `analyze_comm` answered 892 461 characters
and `validate_comm` about 50 000: unusable in a session. Above `AUTO_THRESHOLD`
statements the answer is a summary (commands by type, concepts, errors, warnings,
coverage); the detail stays available, filtered by command or by range of lines.
Nothing is computed twice: the summary is read from the analysis and the report the
tools already produce.
"""

from __future__ import annotations

from typing import Literal

from aster_expert.mcp.models import CommSummary
from aster_expert.parsing.models import CommFileAnalysis, Statement
from aster_expert.validation.models import (
    CommandCounts,
    ValidationReport,
    ValidationSummary,
)

AUTO_THRESHOLD = 150
"""Statements above which the default answer is the summary."""
CONCEPTS_SHOWN = 100
WARNINGS_SHOWN = 30
ERRORS_SHOWN = 50

Detail = Literal["auto", "resume", "complet"]


def wants_summary(
    detail: Detail,
    statements: int,
    *,
    command: str | None,
    line_start: int | None,
    line_end: int | None,
) -> Literal["complet", "resume", "filtre"]:
    if command is not None or line_start is not None or line_end is not None:
        return "filtre"
    if detail == "resume":
        return "resume"
    if detail == "complet":
        return "complet"
    return "resume" if statements > AUTO_THRESHOLD else "complet"


def _in_range(
    line_start: int, line_end: int, first: int | None, last: int | None
) -> bool:
    return (first is None or line_end >= first) and (last is None or line_start <= last)


def summarize_analysis(analysis: CommFileAnalysis, line_count: int) -> CommSummary:
    by_type: dict[str, int] = {}
    for statement in analysis.statements:
        by_type[statement.command] = by_type.get(statement.command, 0) + 1
    concepts = [s.assigned_concept for s in analysis.statements if s.assigned_concept]
    unique = list(dict.fromkeys(concepts))
    warnings = [
        f"ligne {w.line} ({w.node_type}) : {w.message}" for w in analysis.parse_warnings
    ]
    return CommSummary(
        file_path=analysis.file_path,
        file_hash=analysis.file_hash,
        line_count=line_count,
        statements_total=len(analysis.statements),
        commands_by_type=dict(sorted(by_type.items())),
        concepts_count=len(unique),
        concepts=unique[:CONCEPTS_SHOWN],
        external_files=len(analysis.external_files),
        imported_names=analysis.imported_names,
        dynamic_statements=sum(s.dynamic for s in analysis.statements),
        control_flow_statements=sum(bool(s.control_flow) for s in analysis.statements),
        test_statements=len(analysis.test_statements),
        parse_warnings_count=len(warnings),
        parse_warnings=warnings[:WARNINGS_SHOWN],
        warnings_omitted=max(0, len(warnings) - WARNINGS_SHOWN),
    )


def filter_analysis(
    analysis: CommFileAnalysis,
    *,
    command: str | None,
    line_start: int | None,
    line_end: int | None,
) -> CommFileAnalysis:
    kept: list[Statement] = [
        s
        for s in analysis.statements
        if (command is None or s.command == command)
        and _in_range(s.line_start, s.line_end, line_start, line_end)
    ]
    indexes = {s.index for s in kept}
    return analysis.model_copy(
        update={
            "statements": kept,
            "test_statements": [i for i in analysis.test_statements if i in indexes],
            "external_files": [
                e for e in analysis.external_files if e.statement_index in indexes
            ],
            "parse_warnings": [
                w
                for w in analysis.parse_warnings
                if w.line is not None
                and _in_range(w.line, w.line, line_start, line_end)
            ],
        }
    )


def summarize_report(report: ValidationReport) -> ValidationReport:
    counts: dict[str, CommandCounts] = {}

    def bump(command: str, field: str) -> None:
        current = counts.get(command, CommandCounts())
        counts[command] = current.model_copy(
            update={field: getattr(current, field) + 1}
        )

    for done in report.commands_checked:
        bump(done.command, "checked")
    for skipped in report.commands_not_checked:
        bump(skipped.command, "not_checked")
    for finding in report.errors:
        bump(finding.command, "errors")
    total = len(report.commands_checked) + len(report.commands_not_checked)
    summary = ValidationSummary(
        statements_total=total,
        checked=len(report.commands_checked),
        not_checked=len(report.commands_not_checked),
        errors=len(report.errors),
        coverage_rate=(len(report.commands_checked) / total) if total else 0.0,
        by_command=dict(sorted(counts.items())),
        errors_omitted=max(0, len(report.errors) - ERRORS_SHOWN),
        not_checked_omitted=max(0, len(report.commands_not_checked) - ERRORS_SHOWN),
    )
    return report.model_copy(
        update={
            "detail": "resume",
            "summary": summary,
            "commands_checked": [],
            "errors": report.errors[:ERRORS_SHOWN],
            "commands_not_checked": report.commands_not_checked[:ERRORS_SHOWN],
        }
    )


def filter_report(
    report: ValidationReport,
    *,
    command: str | None,
    line_start: int | None,
    line_end: int | None,
) -> ValidationReport:
    def keep(name: str, line: int) -> bool:
        return (command is None or name == command) and _in_range(
            line, line, line_start, line_end
        )

    return report.model_copy(
        update={
            "detail": "filtre",
            "commands_checked": [
                c for c in report.commands_checked if keep(c.command, c.line)
            ],
            "errors": [e for e in report.errors if keep(e.command, e.line)],
            "commands_not_checked": [
                c for c in report.commands_not_checked if keep(c.command, c.line)
            ],
        }
    )
