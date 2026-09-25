"""Lot 37, étape 1 : demi-section des tirants situés dans un plan de symétrie
(décision 8, point 7) et contrôle générique `check_symmetry_plane_sections`.
Pas de Salomé/Docker : un MED synthétique suffit (`generate_comm` ne le lit jamais)."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation import comm
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import (
    POUTRE_EXEMPT_MOTIF,
    _params_json_bytes,
    generate_comm,
)
from aster_expert.meshing.combiwall import build_params
from aster_expert.meshing.run import MeshRunReport, record_verified_mesh, sha256_file

_ROOT = Path(__file__).resolve().parents[2]
_FICHE = _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
_DATA = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"


@pytest.fixture
def verified_mesh(tmp_path: Path) -> Path:
    params = build_params(load_model_data(_DATA))
    sha = hashlib.sha256(_params_json_bytes(params)).hexdigest()
    run_dir = tmp_path / "mesh_runs" / "20260101T000000-deadbeef"
    run_dir.mkdir(parents=True)
    med_path = run_dir / "combiwall_mesh.med"
    med_path.write_bytes(b"not a real MED, only its hash matters here")
    report = MeshRunReport(
        work_dir=str(run_dir),
        script_name="combiwall_mesh.py",
        script_sha256="a" * 64,
        params_name="params.json",
        params_sha256=sha,
        params_sha256_recorded_by_script=sha,
        med_path=str(med_path),
        med_sha256=sha256_file(med_path),
        log_path=str(run_dir / "salome.log"),
        salome_version="V2024.1.0_scibian_univ",
        expected_version="V2024.1.0_scibian_univ",
        image_path="/dummy.sif",
        image_sha256="b" * 64,
        image_sha256_source="cache",
        command=("salome",),
        duration_s=1.0,
        executed_at=datetime.now(UTC),
    )
    (run_dir / "mesh_run_report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    record_verified_mesh(tmp_path / "mesh_runs", report)
    return med_path


_LOT36_COMM = _ROOT / "data" / "examples" / "lot36_butee" / "complet_base.comm"
_AREA = 0.00442
_IN_PLANE = {"TIRANT_01": ("BARRE", _AREA), "TIRANT_09": ("BARRE", _AREA)}
_TIRANTS = [f"TIRANT_{k:02d}" for k in range(1, 10)]


def _check(text: str, **kwargs: object) -> None:
    args: dict[str, object] = {
        "in_plane": _IN_PLANE,
        "exempt": {"POUTRE_COUR": POUTRE_EXEMPT_MOTIF},
        "off_plane": dict.fromkeys(_TIRANTS[1:-1], ("BARRE", _AREA)),
        "umbrella": dict.fromkeys(_TIRANTS, "TIRANTS"),
    }
    args.update(kwargs)
    comm.check_symmetry_plane_sections(text, **args)  # type: ignore[arg-type]


def test_check_fails_on_the_lot36_comm() -> None:
    text = _LOT36_COMM.read_text(encoding="utf-8")
    assert 'GROUP_MA=("TIRANTS",), SECTION="GENERALE", CARA="A", VALE=0.00442' in text
    with pytest.raises(GenerationError, match="demi-section"):
        _check(text)


def test_generated_comm_gives_half_section_to_the_edge_tie_rods_only(
    verified_mesh: Path,
    tmp_path: Path,
) -> None:
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    _check(text)  # déjà appelé par generate_comm : rejoué ici
    barre = re.search(r"BARRE=\((.*?)\n    \),\n    POUTRE", text, re.S)
    assert barre is not None
    assert 'GROUP_MA=("TIRANT_01", "TIRANT_09",), SECTION="GENERALE"' in barre.group(1)
    assert "VALE=0.00221" in barre.group(1)
    assert "VALE=0.00442" in barre.group(1)
    assert '"TIRANT_05"' in barre.group(1)
    assert '"TIRANTS"' not in barre.group(1)


def test_check_refuses_an_exemption_without_motif() -> None:
    with pytest.raises(GenerationError, match="motif"):
        _check("", exempt={"POUTRE_COUR": "  "})


def test_check_refuses_full_section_on_an_edge_tie_rod_and_half_inside() -> None:
    generic = comm._barre_keyword(False, _AREA, _TIRANTS, ())
    text = f"CARA = AFFE_CARA_ELEM(MODELE=MO, {generic})\n"
    with pytest.raises(GenerationError, match="TIRANT_01"):
        _check(text)
    halved = comm._barre_keyword(False, _AREA, _TIRANTS, _TIRANTS)
    text = f"CARA = AFFE_CARA_ELEM(MODELE=MO, {halved})\n"
    with pytest.raises(GenerationError, match="hors de tout plan"):
        _check(text, in_plane={})


def test_barre_keyword_single_occurrence_without_symmetry_plane() -> None:
    assert comm._barre_keyword(False, 0.5).count("_F(") == 1
    assert 'GROUP_MA=("TIRANTS",)' in comm._barre_keyword(False, 0.5)
