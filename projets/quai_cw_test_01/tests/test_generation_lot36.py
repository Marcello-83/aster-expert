"""Lot 36 : variante V1 (pression initiale au repos côté bassin), MED de résultats
explicite, butée côté terre. `generate_comm` par défaut reste le `.comm` de
production ; la variante ajoute ses seuls groupes, fonctions et charge. Pas de
Salomé/Docker : un MED synthétique suffit (`generate_comm` ne le lit jamais)."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.meshing.run import MeshRunReport, record_verified_mesh, sha256_file
from quai_cw_test_01.generation import comm, terre
from quai_cw_test_01.generation.generate import (
    InitialPressureDiagnostic,
    _params_json_bytes,
    generate_comm,
)
from quai_cw_test_01.meshing.combiwall import build_params
from quai_cw_test_01.testing import fiche_generable

_ROOT = Path(__file__).resolve().parents[3]
_FICHE = fiche_generable()
_DATA = _ROOT / "projets" / "quai_cw_test_01" / "donnees" / "combiwall_model_data.yaml"


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


def _generate(
    mesh: Path, tmp_path: Path, initial: InitialPressureDiagnostic | None
) -> str:
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
        initial_pressure=initial,
    )
    return text


# --- V1 : pression initiale au repos côté bassin ------------------------------------


def test_default_initial_pressure_option_is_the_production_comm(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text_none = _generate(verified_mesh, tmp_path, None)
    text_off = _generate(verified_mesh, tmp_path, InitialPressureDiagnostic())
    assert text_none == text_off
    assert "GEN_REPOS" not in text_none
    assert "CH_G_REPOS" not in text_none


def test_v1_adds_its_groups_functions_and_load_to_case_g_only(
    verified_mesh: Path, tmp_path: Path
) -> None:
    base = _generate(verified_mesh, tmp_path, None)
    v1 = _generate(
        verified_mesh, tmp_path, InitialPressureDiagnostic(pression_repos_bassin=True)
    )
    assert v1.count("CH_G_REPOS") == 2  # définition + un seul EXCIT (cas G)
    assert "_F(CHARGE=CH_G_REPOS)," in v1
    # les faces bassin : bandes de ressorts moins l'écran de poussée ; palplanches de la
    # bande d'argile
    assert '"RESS_AV_ARGI", "ECRAN_POUSSEE"' in v1
    assert '"RESS_AV_MARNE", "ECRAN_POUSSEE"' in v1
    assert 'INTERSEC=("RESS_AV_ARGI", "PALPS")' in v1
    # la variante n'ajoute que des lignes : la base en est une sous-suite exacte
    v1_lines = iter(v1.splitlines())
    assert all(line in v1_lines for line in base.splitlines())
    added = "\n".join(ln for ln in v1.splitlines() if ln not in set(base.splitlines()))
    for token in (
        "GEN_REPOS_ARGI_TUBES",
        "F_REPOS_MARNE",
        "F_REPOS_PALPS",
        "CH_G_REPOS",
    ):
        assert token in added
    assert "CH_EAU" not in added and "CH_Q1" not in added  # les autres cas intacts


def test_v1_pressure_functions_follow_the_statement_table_with_signs() -> None:
    block = comm.initial_pressure_load_block("CH", terre.REPOS_TABLE_KPA)
    # argile : 0 à -12,00 et 36,4 kPa à -18,00 (abscisses croissantes)
    assert "ABSCISSE=(-18.0, -12.0)" in block
    assert "ORDONNEE=(36400.0, 0.0)" in block
    # marne : 31,5 kPa à -18,00 et 77,5 kPa à -26,00
    assert "ABSCISSE=(-26.0, -18.0)" in block
    assert "ORDONNEE=(77500.0, 31500.0)" in block
    # palplanches : la même pression, écrite négative (normale +Y de ORIE_NORM_COQUE)
    assert "ORDONNEE=(-36400.0, 0.0)" in block
    assert "-0.0" not in block
    assert block.count("_F(GROUP_MA=") == 3


def test_v1_group_names_respect_the_group_name_limit() -> None:
    for name in (
        comm.REPOS_ARGI_TUBES,
        comm.REPOS_MARNE_TUBES,
        comm.REPOS_ARGI_PALPS,
    ):
        assert name.startswith("GEN_")
        assert len(name) <= comm.MAX_GROUP_NAME_LEN


# --- MED de résultats explicite -----------------------------------------------------


def test_result_med_holds_named_fields_and_no_sief_elga(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _generate(verified_mesh, tmp_path, None)
    assert "SIEF_ELGA" not in text
    assert 'NOM_CHAM=("DEPL", "REAC_NODA", "FORC_NODA",)' in text
    for case in ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A"):
        assert f'NOM_RESU_MED="{case}_ET"' in text
        assert f'NOM_RESU_MED="{case}_EP"' in text
        # écrits avant la destruction des résultats temporaires
        assert text.index(f'NOM_RESU_MED="{case}_ET"') < text.index(
            f"DETRUIRE(NOM=EFA_{case})"
        )


def test_every_nom_resu_med_fits_eight_characters(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _generate(verified_mesh, tmp_path, None)
    import re

    names = re.findall(r'NOM_RESU_MED="([^"]+)"', text)
    assert names
    assert all(len(n) <= comm.MAX_NOM_RESU_MED_LEN for n in names)
    assert len(set(names)) == len(names)


# --- butée côté terre, K0, poussée : les mêmes profils que les données --------------


def test_bassin_passive_profile_matches_the_lot35_data() -> None:
    """La formule (Rankine, σ'v bassin) retrouve les quatre points de
    `donnees_butee_combiwall_v1.md` (kPa)."""
    assert terre.passive_bassin(-12.0, below=True) == pytest.approx(47.1, abs=0.05)
    assert terre.passive_bassin(-18.0, below=False) == pytest.approx(202.3, abs=0.05)
    assert terre.passive_bassin(-18.0, below=True) == pytest.approx(327.6, abs=0.05)
    assert terre.passive_bassin(-26.0, below=False) == pytest.approx(603.6, abs=0.05)


def test_earth_side_stress_reproduces_the_active_thrust_profile_g() -> None:
    """σ'v côté terre (nappe +2,00, γ/γ') retrouve la poussée active du tableau A.4
    (`donnees_complementaires_combiwall_v1.md`), à l'arrondi de Ka près (0,1 kPa)."""
    expected = {
        (2.0, True): 11.7,
        (-2.0, False): 24.0,
        (-9.0, False): 41.1,
        (-9.0, True): 42.4,
        (-18.0, True): 35.8,
        (-26.0, False): 66.5,
    }
    for (z, below), value in expected.items():
        assert terre.active_terre(z, below=below) == pytest.approx(value, abs=0.1)


def test_effective_vertical_stress_on_the_earth_side() -> None:
    assert terre.sigma_v_terre(4.0) == 0.0
    assert terre.sigma_v_terre(2.0) == pytest.approx(19.0 * 2.0)
    assert terre.sigma_v_terre(-2.0) == pytest.approx(38.0 + 10.0 * 4.0)
    assert terre.sigma_v_terre(-18.0) == pytest.approx(246.0)
    assert terre.sigma_v_terre(-26.0) == pytest.approx(338.0)


def test_rest_pressure_table_agrees_with_k0_within_the_table_rounding() -> None:
    for band, points in terre.REPOS_TABLE_KPA.items():
        for z, value in points:
            below = band == "RESS_AV_MARNE" or z == -12.0
            assert terre.k0_pressure_bassin(z, below=below) == pytest.approx(
                value, abs=0.05
            ), (band, z)
    # K0 = 1 - sin(phi'), argile 25 degrés et marne 30 degrés (énoncé du lot)
    assert 1.0 - math.sin(math.radians(25.0)) == pytest.approx(0.577, abs=1e-3)
    assert 1.0 - math.sin(math.radians(30.0)) == pytest.approx(0.5)


def test_passive_earth_side_profile_by_band_is_increasing_with_depth() -> None:
    profile = terre.butee_terre_pa()
    assert set(profile) == {"RESS_AV_ARGI", "RESS_AV_MARNE"}
    for points in profile.values():
        (z_top, p_top), (z_bottom, p_bottom) = points
        assert z_top > z_bottom
        assert p_bottom > p_top > 0.0
    # exemple à la main : argile en -12,00, Kp·σ'v + 2c√Kp
    kp = math.tan(math.radians(45.0 + 12.5)) ** 2
    hand = kp * (246.0 - 6.0 * 10.5) + 2.0 * 15.0 * math.sqrt(kp)
    assert profile["RESS_AV_ARGI"][0][1] == pytest.approx(hand * 1e3)


def test_stratigraphy_lookup_refuses_a_level_outside_the_ground() -> None:
    with pytest.raises(ValueError, match="hors de la stratigraphie"):
        terre.layer_at(-40.0)
