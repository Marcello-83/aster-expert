"""Mode résumé et filtres d'`analyze_comm` et `validate_comm` (lot 48 bis, R10 c)."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.mcp import tools
from aster_expert.mcp.resume import (
    AUTO_THRESHOLD,
    filter_report,
    summarize_report,
)
from aster_expert.validation.models import (
    CheckedEntry,
    NotCheckedEntry,
    ValidationFinding,
    ValidationReport,
)

ROOT = Path(__file__).resolve().parents[2]
ESTACADE = "projets/estacade_pieux_01/references/cas/estacade_pieux_01.comm"
LIMIT = 20_000


def _estacade_analysis(**kwargs: object):  # type: ignore[no-untyped-def]
    return tools.analyze_comm(
        project_root=ROOT,
        comm_path=str(ROOT / ESTACADE),
        log_path=Path(os.devnull),
        **kwargs,  # type: ignore[arg-type]
    )


def test_a_large_comm_is_summarised_by_default_under_the_target() -> None:
    result = _estacade_analysis()
    assert result.detail == "resume" and result.analysis is None
    assert result.summary is not None
    assert result.summary.statements_total > AUTO_THRESHOLD
    assert result.summary.commands_by_type["AFFE_CHAR_MECA"] > 0
    assert len(result.model_dump_json()) < LIMIT


def test_the_detail_is_available_filtered_or_in_full() -> None:
    by_command = _estacade_analysis(command="MECA_STATIQUE")
    assert by_command.detail == "filtre" and by_command.analysis is not None
    assert {s.command for s in by_command.analysis.statements} == {"MECA_STATIQUE"}
    lines = _estacade_analysis(line_start=1, line_end=30)
    assert lines.analysis is not None
    assert lines.analysis.statements
    assert all(s.line_start <= 30 for s in lines.analysis.statements)
    full = _estacade_analysis(detail="complet")
    assert full.detail == "complet" and full.analysis is not None
    assert len(full.model_dump_json()) > 10 * LIMIT


def test_a_small_comm_keeps_the_full_answer() -> None:
    result = tools.analyze_comm(
        project_root=ROOT,
        comm_path=str(ROOT / "data/examples/lot22_essais/essai_a/a1.comm"),
        log_path=Path(os.devnull),
    )
    assert result.detail == "complet" and result.analysis is not None


def _report() -> ValidationReport:
    checked = [
        CheckedEntry(statement_index=i, command="AFFE_CHAR_MECA", line=i, ok=True)
        for i in range(1, 301)
    ]
    not_checked = [
        NotCheckedEntry(
            statement_index=400, command="CALC_CHAMP", line=400, reasons=["dynamique"]
        )
    ]
    return ValidationReport(
        file_path="x.comm",
        aster_version="17.4.0",
        image_digest="sha256:" + "0" * 64,
        validation_level="B",
        catalogue_hash="h",
        errors=[],
        warnings=[],
        commands_checked=checked,
        commands_not_checked=not_checked,
        checked_at=datetime.now(UTC),
    )


def test_the_summary_of_a_report_keeps_the_verdict_and_the_counts() -> None:
    report = _report()
    assert report.verdict == "partiel" and report.valid is False
    summary = summarize_report(report)
    assert summary.detail == "resume" and summary.commands_checked == []
    assert summary.verdict == "partiel" and summary.valid is False
    assert summary.summary is not None
    assert summary.summary.checked == 300 and summary.summary.not_checked == 1
    assert summary.summary.by_command["CALC_CHAMP"].not_checked == 1
    assert len(summary.model_dump_json()) < 5_000


def test_a_filter_never_changes_the_verdict_of_the_whole_file() -> None:
    report = _report()
    only = filter_report(report, command="AFFE_CHAR_MECA", line_start=1, line_end=5)
    assert len(only.commands_checked) == 5 and only.commands_not_checked == []
    assert only.verdict == "partiel" and only.valid is False and only.detail == "filtre"


def test_errors_are_capped_in_the_summary_and_counted() -> None:
    finding = ValidationFinding(
        code="UNKNOWN_KEYWORD",
        command="CALC_CHAMP",
        statement_index=1,
        line=1,
        path=["X"],
        variant_id=None,
        message="m",
        suggestion=None,
        source="checkCommandSyntax",
    )
    report = _report().model_copy(update={"errors": [finding] * 60})
    summary = summarize_report(report)
    assert len(summary.errors) == 50
    assert summary.summary is not None and summary.summary.errors_omitted == 10


@pytest.mark.skipif(
    shutil.which("docker") is None
    or not (ROOT / "data" / "processed" / "catalogue").is_dir(),
    reason="Docker ou catalogue extrait absent",
)
def test_the_validation_of_the_jetty_comm_is_small(tmp_path: Path) -> None:
    workroot = Path(os.environ.get("ASTER_CONTAINER_WORKROOT", tmp_path))
    if not workroot.is_dir():
        pytest.skip("ASTER_CONTAINER_WORKROOT absent")
    report = tools.validate_comm(
        project_root=ROOT,
        comm_path=str(ROOT / ESTACADE),
        workroot=workroot,
        log_path=Path(os.devnull),
    )
    assert report.detail == "resume" and report.verdict == "valide"
    assert len(report.model_dump_json()) < LIMIT
