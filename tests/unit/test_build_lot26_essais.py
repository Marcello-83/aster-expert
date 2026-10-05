"""Qualification meshes of lot 26: generators, versioned evidence, CLI wiring.

Replays the generators in a temporary directory and compares byte for byte with
the versioned files, checks that every run report matches the versioned script,
parameters and MED fingerprints, and that the analysis meets the written
criterion. Reading a MED needs the Docker image: the `mesh check` runs
themselves are reported in `docs/essais_lot26.md`. No Docker, no Salome, no
network.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.meshing.invariants import Invariants

_ROOT = Path(__file__).resolve().parents[2]
_BUILD = _ROOT / "scripts" / "build_lot26_essais.py"
_ANALYZE = _ROOT / "scripts" / "analyze_lot26_essais.py"
_DIR = _ROOT / "data" / "examples" / "lot26_essais"
_SALOME = _ROOT / "scripts" / "salome"

# case -> (geometry directory, script, params file, versioned script for the run)
_RUNS = {
    "g1": ("plaque_raidisseur", "lot26_plaque_raidisseur.py", "params.json"),
    "g1alt": ("plaque_raidisseur", "altere_sans_partition.py", "params.json"),
    "g2": ("tube_plaques", "lot26_tube_plaques.py", "params.json"),
    "g2a": ("tube_plaques", "lot26_tube_plaques.py", "altere_36_facettes.json"),
    "g2b": ("tube_plaques", "lot26_tube_plaques.py", "altere_sans_cote_1.json"),
    "g3": ("poutre_barre", "lot26_poutre_barre.py", "params.json"),
    "g3alt": ("poutre_barre", "altere_barre_non_reliee.py", "params.json"),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_replaying_the_generator_reproduces_the_versioned_files(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(_BUILD), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    produced = sorted(
        p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file()
    )
    assert len(produced) == 17
    for relative in produced:
        assert (tmp_path / relative).read_text("utf-8") == (_DIR / relative).read_text(
            "utf-8"
        ), relative


def test_replaying_the_analysis_reproduces_the_versioned_json(tmp_path: Path) -> None:
    out = tmp_path / "analyse.json"
    subprocess.run(
        [sys.executable, str(_ANALYZE), "--output", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert out.read_text("utf-8") == (_DIR / "analyse.json").read_text("utf-8")


def test_the_analysis_meets_the_written_criterion() -> None:
    analysis: dict[str, Any] = json.loads((_DIR / "analyse.json").read_text("utf-8"))
    assert set(analysis) == {"g1", "g2", "g3"}
    for case, result in analysis.items():
        assert all(result["verdict"].values()), (case, result["verdict"])
        assert not result["alarms"]
        assert all(abs(e) <= 1e-6 for e in result["mass_relative_errors"].values())


def test_every_invariants_file_is_valid_and_analytic() -> None:
    for directory in ("plaque_raidisseur", "tube_plaques", "poutre_barre"):
        data = yaml.safe_load((_DIR / directory / "invariants.yaml").read_text("utf-8"))
        invariants = Invariants.model_validate(data)
        assert invariants.no_orphan_nodes
        assert invariants.no_coincident_nodes is not None
    g2 = yaml.safe_load((_DIR / "tube_plaques" / "invariants.yaml").read_text("utf-8"))
    assert g2["counts"]["nodes"] == 836
    # 40 facets: generatrices exactly at Y = 0 and at +-45 degrees of the basin side
    imprint = next(g for g in g2["groups"] if g["name"] == "EMPREINTE")
    assert imprint["count"] == 10 * 18


@pytest.mark.parametrize("case", sorted(_RUNS))
def test_run_reports_match_the_versioned_fingerprints(case: str) -> None:
    directory, script, params = _RUNS[case]
    report = json.loads((_DIR / "rapports" / f"{case}_run.json").read_text("utf-8"))
    script_path = (
        _SALOME / script if script.startswith("lot26_") else _DIR / directory / script
    )
    assert report["script_sha256"] == _sha(script_path)
    assert report["params_sha256"] == _sha(_DIR / directory / params)
    assert report["params_sha256_recorded_by_script"] == report["params_sha256"]
    assert report["med_sha256"] == _sha(_DIR / report["med_versioned_as"])
    assert report["salome_version"] == report["expected_version"]
    assert report["image_sha256"] == (
        "48beffc5062a2701be2a5af9a52124b1ff1a0b674445408dcdbb61d056094326"
    )


def test_the_check_reports_hold_the_expected_verdicts() -> None:
    for case in _RUNS:
        text = (_DIR / "rapports" / f"{case}_check.txt").read_text("utf-8")
        header = re.search(r"tenus : (\d+), en écart : (\d+)", text)
        assert header is not None
        if case in ("g1", "g2", "g3"):
            assert header.group(2) == "0", case
            assert "Tous les invariants sont tenus." in text
        else:
            assert int(header.group(2)) >= 1, case
            assert "PREMIER INVARIANT NON TENU" in text


def test_the_med_read_by_code_aster_is_the_med_that_was_checked() -> None:
    for case, directory in (
        ("g1", "plaque_raidisseur"),
        ("g2", "tube_plaques"),
        ("g3", "poutre_barre"),
    ):
        assert _sha(_DIR / directory / "aster" / f"lot26_{case}.mmed") == _sha(
            _DIR / directory / "med" / f"lot26_{case}.med"
        )


@pytest.mark.parametrize(
    "script",
    [
        "lot26_plaque_raidisseur.py",
        "lot26_tube_plaques.py",
        "lot26_poutre_barre.py",
    ],
)
def test_salome_scripts_follow_the_writing_rules(script: str) -> None:
    text = (_SALOME / script).read_text("utf-8")
    assert text.count("geompy.MakePartition(") == 1  # one single partition
    assert (
        "MakeCompound("
        not in text.split("# ASSEMBLY end")[0].split("# ASSEMBLY begin")[1]
    )
    assert "CreateGroup(" in text and "GroupOnGeom(" in text  # geometry groups
    assert "params_sha256" in text  # fingerprint of the parameters
    assert "PARAMS[" in text  # values read from the parameters file
    # no numeric literal other than 0 / 1 / 2 / 360 in a coordinate position
    assert not re.search(r"MakeVertex\(\s*-?\d*\.\d", text)


def test_mesh_commands_are_registered() -> None:
    result = CliRunner().invoke(app, ["mesh", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output and "check" in result.output


def test_mesh_run_fails_loudly_on_a_missing_script(lecture_sous_tmp: Path) -> None:
    absent = lecture_sous_tmp / "script.py"
    result = CliRunner().invoke(app, ["mesh", "run", str(absent)])
    assert result.exit_code == 1
    assert "introuvable" in result.output


def test_mesh_check_fails_loudly_on_a_missing_med(
    tmp_path: Path, lecture_sous_tmp: Path
) -> None:
    invariants = tmp_path / "i.yaml"
    invariants.write_text("schema_version: 1\n", encoding="utf-8")
    result = CliRunner().invoke(
        app, ["mesh", "check", str(tmp_path / "absent.med"), str(invariants)]
    )
    assert result.exit_code == 1
    assert "introuvable" in result.output
