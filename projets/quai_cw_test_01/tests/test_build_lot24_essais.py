"""Trial cases and analysis of lot 24 (`scripts/build_lot24_essais.py`,
`scripts/analyze_lot24_essais.py`), and the recording of MM's v5 decision 2.

Replays both scripts in a temporary directory and compares byte for byte with
the versioned files, checks the analysis against the physical references (plate
under membrane traction, cylindrical bending, pure shear), every executed source
of `combiwall_inputs/lot24_essais.json` against the analysis, and the recorded
decision against the verbatim v5 file. No Docker, no network: the executions
themselves are reported in `docs/essais_lot24.md`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    PracticeHypothesisEntry,
)
from aster_expert.constats.base import load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[3]
_BUILD = _ROOT / "scripts" / "build_lot24_essais.py"
_ANALYZE = _ROOT / "scripts" / "analyze_lot24_essais.py"
_VERSIONED = _ROOT / "data" / "examples" / "lot24_essais"
_INPUTS = _ROOT / "projets" / "quai_cw_test_01" / "donnees" / "combiwall_inputs"
_SHEET = (
    _ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)

_CASES = ("essai_d6a/d6a", "essai_d6b/d6b", "essai_d6b/d6b16", "essai_d6c/d6c")


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


def _load_builder() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_lot24_essais", _BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(_BUILD.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(_BUILD.parent))
    return module


@pytest.mark.parametrize("n", [8, 16])
def test_plate_mesh_edge_segments_join_neighbouring_nodes(n: int) -> None:
    """Regression: `BORD_XA` and `BORD_YA` mixed `n` and `N` (lot 24), so at
    n != N a segment joined two nodes that are not neighbours."""
    builder = _load_builder()
    mesh = builder.plate_mesh("essai", n)
    length = builder.SIDE / n
    for group in ("BORD_X0", "BORD_XA", "BORD_Y0", "BORD_YA"):
        members = mesh.groups_ma[group]
        assert len(members) == n, group
        for member in members:
            first, second = mesh.segs[int(member.removeprefix("SG"))]
            distance = (
                sum(
                    (a - b) ** 2
                    for a, b in zip(mesh.nodes[first], mesh.nodes[second], strict=True)
                )
                ** 0.5
            )
            assert distance == pytest.approx(length, rel=1e-9), (group, member)


@pytest.fixture(scope="module")
def analysis() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((_VERSIONED / "analyse.json").read_text("utf-8"))
    return data


def test_every_run_is_free_of_alarms(analysis: dict[str, Any]) -> None:
    assert all(analysis["alarms"].values())
    assert len(analysis["alarms"]) == 4


def test_the_cases_carry_the_coefficients_of_decision_2_v5() -> None:
    comm = (_VERSIONED / "essai_d6a/d6a.comm").read_text("utf-8")
    for expected in (
        "MEMB_L=2908000000.0",
        "MEMB_T=81000.0",
        "MEMB_G_LT=526000000.0",
        "FLEX_L=89000000.0",
        "FLEX_T=11300.0",
        "FLEX_G_LT=8400.0",
        "CISA_L=526000000.0",
        "RHO=7850.0",
        "EPAIS=0.01385",
        "ANGL_REP=(90.0, 0.0)",
    ):
        assert expected in comm, expected
    assert "MEMB_LT=0.0" in comm and "FLEX_LT=0.0" in comm


def test_membrane_traction_along_t(analysis: dict[str, Any]) -> None:
    a = analysis["d6a"]
    assert a["elongation"]["mean"] == pytest.approx(100.0 / 81000.0, rel=1e-10)
    for field in ("EFGE_ELNO", "EFGE_NOEU"):
        assert a[field]["NYY"]["min"] == pytest.approx(100.0, rel=1e-10)
        assert a[field]["NYY"]["max"] == pytest.approx(100.0, rel=1e-10)
        assert a[field]["max_abs_other_components"] < 1e-6
    # membrane reactions are right (the anomaly of lot 23 concerns bending)
    assert a["reactions"]["NX0"]["RESULT_X"] == pytest.approx(-100.0, rel=1e-10)


def test_cylindrical_bending_along_t(analysis: dict[str, Any]) -> None:
    b, fine = analysis["d6b"], analysis["d6b16"]
    ref = 5 * 100.0 / (384 * 11300.0)
    # discretisation error, divided by four when the mesh is halved
    err = abs(b["deflection_mid"]["mean"]) / ref - 1
    err_fine = abs(fine["deflection_mid"]["mean"]) / ref - 1
    assert err == pytest.approx(-0.0125, rel=1e-6)
    assert err_fine == pytest.approx(err / 4, rel=1e-4)
    for case in (b, fine):
        f = case["EFGE_NOEU"]
        assert abs(f["MYY_mid"]["mean"]) == pytest.approx(12.5, rel=1e-8)
        assert f["MYY_max_abs_error_all_points"] < 1e-6
        assert f["max_abs_other_components"] < 1e-6
        assert case["DZ_supports_max_abs"] < 1e-15
    assert b["EFGE_NOEU"]["QY_by_x"]["0.250"]["mean"] == pytest.approx(25.0, rel=1e-9)
    # QY at a support node is the constant shear of the adjacent element
    assert b["EFGE_NOEU"]["QY_x0"]["mean"] == pytest.approx(50 * (1 - 1 / 8), rel=1e-9)
    assert fine["EFGE_NOEU"]["QY_x0"]["mean"] == pytest.approx(
        50 * (1 - 1 / 16), rel=1e-8
    )


def test_bending_reactions_are_the_nodal_load_share_not_the_support_reaction(
    analysis: dict[str, Any],
) -> None:
    for case, n in (("d6b", 8), ("d6b16", 16)):
        reac = analysis[case]["reactions"]
        share = 100.0 * 1.0 * (1.0 / n) / 2  # p * a * h / 2
        assert reac["NX0"]["RESULT_Z"] == pytest.approx(share, rel=3e-3)
        assert reac["TOUS"]["RESULT_Z"] == pytest.approx(100.0, rel=1e-9)


def test_pure_membrane_shear(analysis: dict[str, Any]) -> None:
    c = analysis["d6c"]
    gamma = 1.0e5 / 526.0e6
    assert c["DX_top"]["mean"] == pytest.approx(gamma, rel=1e-9)
    assert c["DX_max_abs_error_vs_gamma_y"] < 1e-12
    assert c["DY_max_abs"] < 1e-12
    for field in ("EFGE_ELNO", "EFGE_NOEU"):
        assert abs(c[field]["NXY"]["mean"]) == pytest.approx(1.0e5, rel=1e-9)
        assert c[field]["max_abs_other_components"] < 1e-6
    for group in c["reactions"].values():
        assert max(abs(v) for v in group.values()) < 1e-8


def test_every_executed_source_matches_the_analysis(analysis: dict[str, Any]) -> None:
    """Values of `lot24_essais.json` must be values of `analyse.json`."""
    known: list[float] = []

    def collect(node: object) -> None:
        if isinstance(node, dict):
            for v in node.values():
                collect(v)
        elif isinstance(node, float):
            known.extend([node, abs(node)])

    collect(analysis)
    data = json.loads((_INPUTS / "lot24_essais.json").read_text("utf-8"))
    (finding,) = data["findings"]
    assert len(finding["sources"]) == 13
    for source in finding["sources"]:
        value = source["value_obtained"]
        assert any(value == pytest.approx(k, rel=1e-12) for k in known), source[
            "quantity"
        ]


def _norm(text: str) -> str:
    return " ".join(text.split())


def test_decision_2_v5_is_recorded_as_worded_and_closes_the_revision() -> None:
    sheet = load_resolved_sheet(_SHEET)
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.topic.startswith("Homogénéisation ou représentation distincte")
    ]
    v5 = (_INPUTS / "arbitrage_combiwall_MM_v5_decision2.md").read_text("utf-8")
    body = v5.split("## Décision 2 — révisée")[1]
    option = body.split("**option_retained**")[1].split("**justification**")[0]
    justification = body.split("**justification**")[1].split("**validity_domain**")[0]
    validity = body.split("**validity_domain**")[1].split("**discarded_variants**")[0]
    assert entry.option_retained is not None
    assert _norm(entry.option_retained) == _norm(option)
    # the rigidity table keeps one row per line
    rows = [line for line in entry.option_retained.split("\n") if line.startswith("|")]
    assert len(rows) == 10 and rows[0].startswith("| Rigidité")
    assert entry.justification is not None and entry.validity_domain is not None
    assert _norm(entry.justification) == _norm(justification)
    assert _norm(entry.validity_domain) == _norm(validity)
    assert len(entry.discarded_variants) == 5
    # closed revision, v2 kept in history, time declared as the recording time
    assert not entry.under_revision
    assert [(ev.kind, ev.by) for ev in entry.revision_history][-1] == ("lifted", "MM")
    assert len(entry.decision_history) == 1
    record = json.loads((_INPUTS / "lot24_enregistrement.json").read_text("utf-8"))
    assert entry.decided_at is not None
    assert entry.decided_at.isoformat() == record["decision_2_v5"]["decided_at"]
    assert "MM n'a pas écrit" not in record["decision_2_v5"]["origin"]
    assert "ne porte ni date ni heure" in record["decision_2_v5"]["origin"]
    assert "À CONFIRMER" not in v5
    assert re.search(r"`decided_at` : `\d", v5) is None  # MM wrote none


def test_the_efge_finding_carries_the_lot_23_and_lot_24_sources() -> None:
    sheet = load_resolved_sheet(_SHEET)
    (entry,) = [
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.topic.startswith("Efforts généralisés (EFGE_ELNO, EFGE_NOEU)")
    ]
    cases = {
        s.case_path.rsplit("/", 1)[-1] for s in entry.sources if hasattr(s, "case_path")
    }
    assert {"d1.comm", "d3.comm", "d6a.comm", "d6b.comm", "d6b16.comm", "d6c.comm"} <= (
        cases
    )
    assert entry.notes is not None
    assert "Non testés" in entry.notes and "FLEX_G_LT" in entry.notes
    assert "Historique du constat remplacé (lot 23" in entry.notes
