"""Lot 47 ter, ENV-003: a full disk left two runs with an empty `compte_rendu.json`
and `rex` stopped on it (`JSONDecodeError`). Such a run is now attributed by the
SHA-256 of its .comm, found under the case roots, and read as a failure to classify."""

from __future__ import annotations

from pathlib import Path

from aster_expert.connaissances.archive import RUNS_RELATIVE, attributed_runs
from aster_expert.connaissances.rex import RexRegistry, project_runs

COMM = "DEBUT()\nFIN()\n"


def _repo(tmp_path: Path) -> Path:
    case = tmp_path / "projets" / "p" / "resultats"
    case.mkdir(parents=True)
    (case / "cas.comm").write_text(COMM, "utf-8")
    for run_id, comm in (
        ("20261006T125858-7291dc7a", COMM),  # empty report, .comm of the project
        ("20261006T130308-683933a3", "DEBUT()\n"),  # empty report, foreign .comm
    ):
        run = tmp_path / RUNS_RELATIVE / run_id
        run.mkdir(parents=True)
        (run / "cas.comm").write_text(comm, "utf-8")
        (run / "compte_rendu.json").write_text("", "utf-8")
    return tmp_path


def test_an_empty_report_is_a_failure_to_classify_attributed_by_its_comm(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    ids = attributed_runs(repo, ("projets/p",), None)
    assert ids == ["20261006T125858-7291dc7a"]
    registry = RexRegistry(project="p", case_roots=("projets/p",))
    runs = project_runs(repo, registry, None)
    assert [r.run for r in runs] == ids
    assert runs[0].failed is True
    assert runs[0].signature == "(signature inconnue)"
    assert runs[0].comm == "cas.comm"
