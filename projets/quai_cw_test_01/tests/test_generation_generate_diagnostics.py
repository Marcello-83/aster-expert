"""Lot 30, étape 3 : options de retrait de `DiagnosticOmissions` --
`generate_comm` par défaut (aucun champ à `True`) reste octet pour octet
celui de la production (déjà couvert par `test_generation_generate.py`) ;
chaque champ à `True` produit un texte syntaxiquement cohérent (pas de
`GROUP_MA`/`GROUP_NO` vide, pas de concept fantôme) pour le seul ingrédient
qu'il retire. Pas de Salomé/Docker : comme `test_generation_generate.py`,
un MED synthétique suffit (`generate_comm` ne lit jamais son contenu)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.meshing.run import MeshRunReport, record_verified_mesh, sha256_file
from quai_cw_test_01.generation.generate import (
    DiagnosticOmissions,
    EquilibriumProbe,
    GenerationReport,
    _params_json_bytes,
    generate_comm,
)
from quai_cw_test_01.meshing.combiwall import build_params
from quai_cw_test_01.testing import fiche_generable

_ROOT = Path(__file__).resolve().parents[3]
_FICHE = fiche_generable()
_DATA = _ROOT / "projets" / "quai_cw_test_01" / "donnees" / "combiwall_model_data.yaml"


def _params_sha256() -> str:
    data = load_model_data(_DATA)
    digest: str = hashlib.sha256(_params_json_bytes(build_params(data))).hexdigest()
    return digest


@pytest.fixture
def verified_mesh(tmp_path: Path) -> Path:
    run_dir = tmp_path / "mesh_runs" / "20260101T000000-deadbeef"
    run_dir.mkdir(parents=True)
    med_path = run_dir / "combiwall_mesh.med"
    med_path.write_bytes(b"not a real MED, only its hash matters here")

    report = MeshRunReport(
        work_dir=str(run_dir),
        script_name="combiwall_mesh.py",
        script_sha256="a" * 64,
        params_name="params.json",
        params_sha256=_params_sha256(),
        params_sha256_recorded_by_script=_params_sha256(),
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


def _generate(
    verified_mesh: Path, tmp_path: Path, diagnostic: DiagnosticOmissions
) -> tuple[str, GenerationReport]:
    return generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
        diagnostic=diagnostic,
    )


def test_default_diagnostic_matches_production(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text_default, report_default = _generate(
        verified_mesh, tmp_path, DiagnosticOmissions()
    )
    text_none, report_none = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert text_default == text_none
    assert report_default == report_none


def test_sans_ressorts_omits_springs_entirely(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text, report = _generate(
        verified_mesh, tmp_path, DiagnosticOmissions(sans_ressorts=True)
    )
    assert report.n_spring_classes == 0
    assert "CREA_POI1" not in text
    assert 'MODELISATION="DIS_T"' not in text
    assert "TAB_RESS_" not in text
    assert "LIAISON_SOLIDE=(" in text  # unaffected ingredient stays


def test_sans_tirants_omits_bars_and_anchor_condition(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text, _ = _generate(verified_mesh, tmp_path, DiagnosticOmissions(sans_tirants=True))
    assert 'MODELISATION="BARRE"' not in text
    assert '"ANCRAGES"' not in text
    assert 'MODELISATION="DIS_T"' in text  # unaffected ingredient stays


def test_sans_palplanches_uses_tubes_only_pressure_group(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text, _ = _generate(
        verified_mesh, tmp_path, DiagnosticOmissions(sans_palplanches=True)
    )
    assert '_F(GROUP_MA=("PALPS",), MATER=MAT_PALP)' not in text
    assert "GEN_ECRAN_POUSSEE_TUBES" in text
    assert 'VERI_NORM="NON"' in text
    assert "BARRE" in text  # unaffected ingredient stays


def test_sans_poutre_omits_liaison_solide_and_q3(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text, _ = _generate(verified_mesh, tmp_path, DiagnosticOmissions(sans_poutre=True))
    assert "CH_SOLIDE = AFFE_CHAR_MECA" not in text
    assert "LIAISON_SOLIDE=(" not in text
    assert 'MODELISATION="POU_D_T"' not in text
    assert "RESU_Q3" not in text
    assert '"BOLLARD"' not in text
    assert 'MODELISATION="BARRE"' in text  # unaffected ingredient stays


def _probe(verified_mesh: Path, tmp_path: Path, probe: EquilibriumProbe) -> str:
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
        probe=probe,
    )
    return text


def test_default_probe_matches_production(verified_mesh: Path, tmp_path: Path) -> None:
    production = _probe(verified_mesh, tmp_path, EquilibriumProbe())
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert production == text
    # `pression_sur` n'a d'effet qu'avec `blocage_total`.
    assert (
        _probe(verified_mesh, tmp_path, EquilibriumProbe(pression_sur="aucune")) == text
    )


def test_probe_blocks_every_dof_without_liaison_solide(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _probe(verified_mesh, tmp_path, EquilibriumProbe(blocage_total=True))
    assert "GEN_NOEUDS_6DDL" in text
    assert (
        'DDL_IMPO=(\n        _F(GROUP_NO=("GEN_TOUS_NOEUDS",), DX=0.0, DY=0.0, DZ=0.0)'
        in text
    )
    assert "CH_SOLIDE" not in text
    assert "LIAISON_SOLIDE=(" not in text
    for case in ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A"):
        assert f"TAB_CHARGE_{case} = POST_RELEVE_T(" in text
    assert "TAB_REAC_" not in text
    assert "TAB_RESS_" not in text
    assert "IMPR_RESU" not in text
    assert text.rstrip().endswith("FIN()")


@pytest.mark.parametrize(
    ("pression", "group", "in_excit"),
    [
        ("ecran", "ECRAN_POUSSEE", True),
        ("tubes", "GEN_ECRAN_POUSSEE_TUBES", True),
        ("palplanches", "PALPS", True),
        ("aucune", "ECRAN_POUSSEE", False),
    ],
)
def test_probe_pressure_location(
    verified_mesh: Path, tmp_path: Path, pression: str, group: str, in_excit: bool
) -> None:
    text = _probe(
        verified_mesh,
        tmp_path,
        EquilibriumProbe(blocage_total=True, pression_sur=pression),  # type: ignore[arg-type]
    )
    # La poussée G est portée par couche : chaque groupe de couche est
    # l'intersection de sa bande et du groupe qui porte la pression.
    assert f'INTERSEC=("GEN_BANDE_MARNE", "{group}")' in text
    assert (
        'FORCE_COQUE=(\n        _F(GROUP_MA=("GEN_COUCHE_MARNE",), PRES=F_G_MARNE),'
        in text
    )
    assert ("_F(CHARGE=CH_G_POUSSEE)," in text) is in_excit
