"""Trial cases and analysis of lot 25 (`scripts/build_lot25_essais.py`,
`scripts/analyze_lot25_essais.py`), and the recording of the D7 finding and of MM's
frame decision (point 9).

Replays both scripts in a temporary directory and compares byte for byte with the
versioned files, checks the analysis against the criterion written before the runs
(`docs/essais_lot25.md`) -- including the criterion that failed, reported as such --
and the recorded decision against the verbatim lot 25 file. No Docker, no network:
the executions themselves are reported in `docs/essais_lot25.md`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    ExecutionSource,
    HypothesesSheet,
    PracticeHypothesisEntry,
)

_ROOT = Path(__file__).resolve().parents[2]
_BUILD = _ROOT / "scripts" / "build_lot25_essais.py"
_ANALYZE = _ROOT / "scripts" / "analyze_lot25_essais.py"
_VERSIONED = _ROOT / "data" / "examples" / "lot25_essais"
_INPUTS = _ROOT / "data" / "examples" / "combiwall_inputs"
_SHEET = _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"

_CASES = (
    "essai_d7a/d7a",
    "essai_d7a/d7a16",
    "essai_d7b/d7b",
    "essai_d7b/d7b16",
    "essai_d7c/d7c",
)


def test_replaying_the_generator_reproduces_the_versioned_files(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(_BUILD), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for case in _CASES:
        for suffix in (".mail", ".comm", ".export"):
            name = case + suffix
            assert (tmp_path / name).read_text("utf-8") == (
                _VERSIONED / name
            ).read_text("utf-8"), name


def test_replaying_the_analysis_reproduces_the_versioned_json(tmp_path: Path) -> None:
    out = tmp_path / "analyse.json"
    subprocess.run(
        [sys.executable, str(_ANALYZE), "--output", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert out.read_text("utf-8") == (_VERSIONED / "analyse.json").read_text("utf-8")


@pytest.fixture(scope="module")
def analysis() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_VERSIONED / "analyse.json").read_text("utf-8"))
    return data


def test_every_run_is_free_of_alarms(analysis: dict[str, Any]) -> None:
    assert len(analysis["alarms"]) == 5
    assert all(analysis["alarms"].values())


def test_the_plate_lies_in_the_xz_plane_with_the_expected_orientations() -> None:
    mesh = (_VERSIONED / "essai_d7a/d7a.mail").read_text("utf-8")
    coordinates = [
        line.split()
        for line in mesh.split("COOR_3D")[1].split("FINSF")[0].splitlines()
        if line.startswith("N")
    ]
    assert len(coordinates) == 81
    assert {float(row[2]) for row in coordinates} == {0.0}  # Y = 0
    assert max(float(row[3]) for row in coordinates) == 1.0  # Z up to H
    assert "VECTEUR=(0.0, 0.0, 1.0)" in (_VERSIONED / "essai_d7a/d7a.comm").read_text()
    assert "VECTEUR=(1.0, 0.0, 0.0)" in (_VERSIONED / "essai_d7b/d7b.comm").read_text()
    assert "ANGL_REP=(0.0, -90.0)" in (_VERSIONED / "essai_d7c/d7c.comm").read_text()


def test_criterion_1_bending_moment_is_exact(analysis: dict[str, Any]) -> None:
    for name in ("d7a", "d7a16", "d7b", "d7b16"):
        assert analysis[name]["moment_max_abs_error_over_qH"] <= 1e-6, name
        assert analysis[name]["other_bending_max_abs_over_qH"] <= 1e-6, name
        assert analysis[name]["MXY_max_abs_over_qH"] <= 1e-6, name
    assert analysis["d7a"]["moment_component"] == "MXX"
    assert analysis["d7b"]["moment_component"] == "MYY"
    assert analysis["verdict"]["1_moment_exact"] is True


def test_criterion_2_is_reported_as_failed(analysis: dict[str, Any]) -> None:
    """The error of the tip deflection does not decrease with the refinement: the
    criterion written before the runs is not met, and stays reported as failed."""
    verdict = analysis["verdict"]
    for key in ("2_error_decreases_d7a", "2_error_decreases_d7b"):
        assert verdict[key]["ok"] is False
        assert verdict[key]["err_16"] > verdict[key]["err_8"]
        assert verdict[key]["err_16"] < 1e-6  # yet far below the exact threshold


def test_criterion_3_the_axis_is_identified(analysis: dict[str, Any]) -> None:
    for key in ("3_axis_identified_d7a", "3_axis_identified_d7b"):
        assert analysis["verdict"][key]["ok"] is True
    ratio = analysis["constants"]["flex_ratio"]
    w_a = analysis["d7a16"]["tip_deflection"]["mean"]
    w_b = analysis["d7b16"]["tip_deflection"]["mean"]
    assert w_b / w_a == pytest.approx(ratio, rel=1e-6)


def test_criterion_4_angl_rep_equals_vecteur(analysis: dict[str, Any]) -> None:
    assert analysis["verdict"]["4_angl_rep_equals_vecteur"]["ok"] is True
    assert (
        analysis["d7c"]["tip_deflection"]["mean"]
        == (analysis["d7a"]["tip_deflection"]["mean"])
    )


def _sheet() -> HypothesesSheet:
    return HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))


def test_the_d7_finding_is_recorded_at_point_1_with_its_failure() -> None:
    topic = (
        "Orientation des axes L et T d'ELAS_COQUE pour une coque dans un plan vertical"
    )
    (entry,) = [
        e
        for e in _sheet().entries
        if isinstance(e, CodeAsterHypothesisEntry) and e.topic.startswith(topic)
    ]
    assert entry.point_label == "1"
    assert entry.status == "tranche"
    assert "VECTEUR = (0, 0, 1)" in (entry.option_retained or "")
    assert "ÉCHEC du critère 2" in (entry.notes or "")
    executions = [s for s in entry.sources if isinstance(s, ExecutionSource)]
    assert len(executions) == 7
    assert {s.validation_level for s in executions} == {"D"}
    assert all(abs(s.relative_deviation) < 1e-6 for s in executions)


def test_the_frame_decision_is_recorded_as_worded() -> None:
    (entry,) = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == "9"
    ]
    text = (_INPUTS / "arbitrage_combiwall_MM_lot25_repere.md").read_text("utf-8")
    assert entry.topic == "Repère global et origine du modèle"
    assert entry.decided_by == "MM"
    assert entry.status == "tranche"
    assert entry.decided_at is not None
    record = json.loads((_INPUTS / "lot25_enregistrement.json").read_text("utf-8"))
    assert entry.decided_at.isoformat() == record["decision_repere"]["decided_at"]
    for expected in (
        "X = 0 dans l'axe de `TUBE_05`",
        "Les faces de coupe sont à X = −10,40 et X = +10,40.",
        "à X = ±0,71 m de l'axe du tube",
        "mètre,\nnewton, pascal, kilogramme.",
    ):
        assert expected in text
    assert "X = 0 dans l'axe de `TUBE_05`" in (entry.option_retained or "")
    assert "X = ±0,71 m" in (entry.option_retained or "")
    assert entry.sources[0].origin == "decision_ingenieur"
    assert len(entry.discarded_variants) == 1
