"""Trial cases and analysis of lot 23 (`scripts/build_lot23_essais.py`,
`scripts/analyze_lot23_essais.py`).

Replays both scripts in a temporary directory and compares byte for byte with
the versioned files, checks the analysis against the physical references
(cantilever strip, per unit width) and every executed source of
`combiwall_inputs/lot23_essais.json` against the analysis. No Docker, no
network: the executions themselves are reported in `docs/essais_lot23.md`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_BUILD = _ROOT / "scripts" / "build_lot23_essais.py"
_ANALYZE = _ROOT / "scripts" / "analyze_lot23_essais.py"
_VERSIONED = _ROOT / "data" / "examples" / "lot23_essais"
_INPUT = _ROOT / "data" / "examples" / "combiwall_inputs" / "lot23_essais.json"

_CASES = (
    "essai_d1/d1",
    "essai_d2/d2a",
    "essai_d2/d2b",
    "essai_d3/d3",
    "essai_d4/d4",
    "essai_d5/d5a",
    "essai_d5/d5b",
)


def _load(name: str, path: Path):  # type: ignore[no-untyped-def]
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_analyze = _load("analyze_lot23_essais", _ANALYZE)


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
    assert all(analysis["alarms"].values())
    assert len(analysis["alarms"]) == 7


def test_case_variants_differ_only_where_intended() -> None:
    d1 = (_VERSIONED / "essai_d1/d1.comm").read_text("utf-8")
    d2a = (_VERSIONED / "essai_d2/d2a.comm").read_text("utf-8")
    d3 = (_VERSIONED / "essai_d3/d3.comm").read_text("utf-8")
    assert "EPAIS=0.01" in d1 and "EPAIS=0.02" in d2a
    assert "CISA_L=10000000000.0" in d1 and "CISA_L=10000000000000.0" in d3
    # D2 leaves every ELAS_COQUE coefficient untouched.
    assert d1.split("MAT = ")[1].split("\n")[0] == d2a.split("MAT = ")[1].split("\n")[0]
    d4 = (_VERSIONED / "essai_d4/d4.comm").read_text("utf-8")
    assert "RHO=0.0" in d4 and "RHO=7850.0" in d4


@pytest.mark.parametrize("case", ["d1", "d2a", "d2b", "d3"])
def test_generalised_forces_are_exact_whatever_epais_and_cisa(
    analysis: dict[str, Any], case: str
) -> None:
    for field in ("EFGE_ELNO", "EFGE_NOEU"):
        f = analysis[case][field]
        assert f["MXX_x0"]["mean"] == pytest.approx(20.0, rel=1e-9)
        assert f["MXX_mid"]["mean"] == pytest.approx(10.0, rel=1e-9)
        assert abs(f["QX_mid"]["mean"]) == pytest.approx(10.0, rel=1e-9)
        assert f["max_abs_MXX_error_all_points"] < 1e-8
    assert abs(analysis[case]["deflection_tip"]["mean"]) == pytest.approx(
        40.0 / 1500.0, rel=1e-9
    )


@pytest.mark.parametrize(
    ("case", "factor"), [("d1", 1.0), ("d2a", 4.0), ("d2b", 0.25), ("d3", 1.0)]
)
def test_nodal_forces_scale_as_epais_squared(
    analysis: dict[str, Any], case: str, factor: float
) -> None:
    base = 5.0 * 1e7 * 0.01**2 / 12.0 / 1000.0  # MEMB * EPAIS^2 / (12 FLEX) * P
    for key in ("REAC_NODA_clamp", "FORC_NODA_clamp"):
        assert analysis[case][key]["RESULT_Z"] == pytest.approx(base * factor, rel=1e-9)
    ratio = analysis[case]["SIEF_ELGA"]["M_equivalent_over_M_ref"]
    assert ratio["mean"] == pytest.approx(factor / 12.0, rel=1e-9)
    assert ratio["max"] - ratio["min"] < 1e-12
    # The sum over all nodes cannot reveal the error.
    assert abs(analysis[case]["FORC_NODA_all_nodes"]["RESULT_Z"]) < 1e-12


def test_zero_rho_is_silent_and_witness_is_exact(analysis: dict[str, Any]) -> None:
    assert analysis["d4"]["plate_1"]["DZ"] == pytest.approx(770.085, rel=1e-12)
    assert analysis["d4"]["plate_2"]["DZ"] == 0.0


def test_equilibrium_is_read_off_springs_or_supports_not_off_elas_coque(
    analysis: dict[str, Any],
) -> None:
    d5a, d5b = analysis["d5a"], analysis["d5b"]
    assert abs(d5a["springs_resultant"]["RESULT_Z"]) == pytest.approx(5.0, rel=1e-8)
    assert abs(d5b["reac_noda_x2"]["RESULT_Z"]) == pytest.approx(5.0, rel=1e-8)
    assert abs(d5b["reac_noda_x2"]["MOMENT_X"]) == pytest.approx(1.25, rel=1e-8)
    assert abs(d5b["reac_noda_x2"]["MOMENT_Y"]) < 1e-8
    # Nodes carried by ELAS_COQUE only: a reaction where none is expected ...
    assert d5b["reac_noda_x0_loaded_end"]["RESULT_Z"] == pytest.approx(
        5.0 * (1 - 1 / 12), rel=1e-9
    )
    # ... yet the sum over every node still reads 5 N.
    assert d5b["reac_noda_all"]["RESULT_Z"] == pytest.approx(5.0, rel=1e-9)


def test_every_executed_source_matches_the_analysis(analysis: dict[str, Any]) -> None:
    """Values of `lot23_essais.json` must be values of `analyse.json`."""
    known: list[float] = []

    def collect(node: object) -> None:
        if isinstance(node, dict):
            for v in node.values():
                collect(v)
        elif isinstance(node, float):
            known.extend([node, abs(node)])

    collect(analysis)
    data = json.loads(_INPUT.read_text("utf-8"))
    for finding in data["findings"]:
        for source in finding["sources"]:
            value = source["value_obtained"]
            if source["case_path"].endswith("d4.comm"):
                assert value == 770.085
                continue
            assert any(value == pytest.approx(k, rel=1e-12) for k in known), source[
                "quantity"
            ]
