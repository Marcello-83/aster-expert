"""`generate_comm` orchestration (lot 28, Étape 3): refusal conditions,
determinism, on the real combi-wall fiche/data with a synthetic mesh cache
(no Salomé/Docker: `generate_comm` never reads the MED's own content, only
its fingerprint against the mesh cache -- exactly what this test exercises)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import (
    SolverDiagnostics,
    _params_json_bytes,
    _tributary_lengths,
    generate_comm,
)
from aster_expert.meshing.combiwall import build_params
from aster_expert.meshing.run import MeshRunReport, record_verified_mesh, sha256_file

_ROOT = Path(__file__).resolve().parents[2]
_FICHE = _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
_DATA = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"


def _params_sha256() -> str:
    data = load_model_data(_DATA)
    digest: str = hashlib.sha256(_params_json_bytes(build_params(data))).hexdigest()
    return digest


@pytest.fixture
def verified_mesh(tmp_path: Path) -> Path:
    """A dummy MED, `mesh_run_report.json` next to it, and a matching entry
    in the mesh cache -- exactly what `mesh run` + `mesh check` leave behind,
    without running either."""
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


def test_generation_is_deterministic(verified_mesh: Path, tmp_path: Path) -> None:
    text1, report1 = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    text2, report2 = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert text1 == text2
    assert report1 == report2
    assert text1.startswith("# Généré par aster-expert generate")
    assert "FIN()" in text1


def test_spring_sums_match_the_decision_5_invariant(
    verified_mesh: Path, tmp_path: Path
) -> None:
    _, report = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert report.spring_sums_mn_per_m["RESS_AV_ARGI"] == pytest.approx(
        35.0 * 20.80 * 6.00
    )
    assert report.spring_sums_mn_per_m["RESS_AV_MARNE"] == pytest.approx(
        80.0 * 11.36 * 8.00
    )
    # 48 classes de bande + 12 classes communes (nœuds partagés, lot 34)
    assert report.n_spring_classes == 60


def test_impr_resu_carries_cara_elem_for_every_result(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """Lot 31, étape 3 : sans CARA_ELEM, l'écriture MED de SIEF_ELGA (sous-
    points d'un élément COQUE) échoue en fin d'exécution (`<F> <MED2_14>`),
    jamais atteint avant ce lot (le pivot de LIAISON_SOLIDE arrêtait
    systématiquement l'exécution plus tôt)."""
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    for name in ("RESU_G", "RESU_EAU_P", "RESU_EAU_A", "RESU_Q1", "RESU_Q3", "RESU_A"):
        assert f'CARA_ELEM=CARA, NOM_RESU_MED="{name.removeprefix("RESU_")}"' in text


def test_impr_resu_nom_resu_med_avoids_the_lot31_field_collision(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """Lot 32, étape 3 : sans NOM_RESU_MED, le nom de champ MED par défaut
    tronque le nom Jeveux du concept RESULTAT à 8 caractères -- RESU_EAU_P et
    RESU_EAU_A devenaient tous deux `RESU_EAU`, d'où `<F> <MED2_4>` (lot 31).
    NOM_RESU_MED="EAU_P"/"EAU_A" (U7.05.21) restent distincts en toutes
    lettres, jamais tronqués à 8 caractères de façon à coïncider."""
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    tags = ["EAU_P", "EAU_A"]
    assert len(set(tags)) == len(tags)
    for tag in tags:
        assert f'NOM_RESU_MED="{tag}"' in text


def test_springs_carry_an_explicit_zero_mass(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """Lot 31, étape 3 : un ressort est un appui, pas de la matière -- sa
    masse est affectée à zéro explicitement (jamais omise, sous peine de
    `<F> <DISCRETS_26>` dès que PESANTEUR est calculée, U4.42.01 DISCRET)."""
    text, report = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert text.count('CARA="M_T_D_N", VALE=(0.0,)') == report.n_spring_classes
    assert text.count('CARA="K_T_D_N"') == report.n_spring_classes


def test_production_omits_the_lot28_solver_parameters(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """Lot 33, étape 1 : `SOLVEUR/RESI_RELA` et `COEF_RIGI_DRZ`, hérités des
    tentatives du lot 28 pour lever le pivot nul de `LIAISON_SOLIDE`, se sont
    révélés inutiles isolément une fois cette cause corrigée au lot 32
    (`docs/essais_lot33.md`, exécutions réelles sur le quai réduit) : la
    production ne passe plus ni l'un ni l'autre, jamais implicitement les
    deux retirés à la fois sans démonstration séparée."""
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert "RESI_RELA=" not in text
    assert "COEF_RIGI_DRZ=" not in text
    assert 'SOLVEUR=_F(METHODE="MUMPS"),' in text


def test_solver_diagnostics_can_still_reproduce_the_lot28_values(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """**Outil de diagnostic uniquement** (jamais la production) : une valeur
    explicite ajoute le mot-clé correspondant -- exactement ce que
    `scripts/generate_lot33_solveur.py` a utilisé pour l'isolation de
    l'étape 1."""
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
        solver=SolverDiagnostics(resi_rela=1.0e-4, coef_rigi_drz=1.0e-3),
    )
    assert 'SOLVEUR=_F(METHODE="MUMPS", RESI_RELA=0.0001),' in text
    assert text.count("COEF_RIGI_DRZ=0.001,") == 2


def test_refuses_when_mesh_report_fingerprint_does_not_match(
    verified_mesh: Path, tmp_path: Path
) -> None:
    run_report_path = verified_mesh.parent / "mesh_run_report.json"
    stale = json.loads(run_report_path.read_text("utf-8"))
    stale["params_sha256"] = "0" * 64
    run_report_path.write_text(json.dumps(stale), encoding="utf-8")

    with pytest.raises(GenerationError, match="mêmes empreintes de paramètres"):
        generate_comm(
            fiche_path=_FICHE,
            data_path=_DATA,
            med_path=verified_mesh,
            project_root=tmp_path,
            work_dir_root="mesh_runs",
            aster_version="17.4.0",
        )


def test_refuses_when_the_mesh_was_never_confirmed_verified(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "mesh_runs" / "unverified"
    run_dir.mkdir(parents=True)
    med_path = run_dir / "combiwall_mesh.med"
    med_path.write_bytes(b"never checked")
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
    # deliberately never call record_verified_mesh

    with pytest.raises(GenerationError, match="n'est pas confirmé vérifié"):
        generate_comm(
            fiche_path=_FICHE,
            data_path=_DATA,
            med_path=med_path,
            project_root=tmp_path,
            work_dir_root="mesh_runs",
            aster_version="17.4.0",
        )


def test_refuses_when_the_fiche_is_not_ready(
    verified_mesh: Path, tmp_path: Path
) -> None:
    from aster_expert.agent.hypotheses import HypothesesSheet

    sheet = HypothesesSheet.model_validate_json(_FICHE.read_text("utf-8"))
    not_ready = sheet.model_copy(update={"entries": ()})
    bad_fiche = tmp_path / "fiche_incomplete.json"
    bad_fiche.write_text(
        json.dumps(not_ready.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(GenerationError, match="génération refusée"):
        generate_comm(
            fiche_path=bad_fiche,
            data_path=_DATA,
            med_path=verified_mesh,
            project_root=tmp_path,
            work_dir_root="mesh_runs",
            aster_version="17.4.0",
        )


def test_tributary_lengths_sum_to_the_total_span() -> None:
    """Lot 33, étape 3 : la somme des longueurs tributaires vaut exactement
    la longueur totale (bord à bord) de la poutre, quel que soit l'espacement
    -- l'invariant que le contrôle d'équilibre global suppose (la résultante
    nodale totale reproduit exactement la résultante linéique totale)."""
    axes = [0.0, 2.6, 5.2, 10.4]  # espacement irrégulier volontaire
    lengths = _tributary_lengths(axes)
    assert len(lengths) == 4
    assert sum(lengths) == pytest.approx(axes[-1] - axes[0])


def test_tributary_lengths_of_a_uniform_spacing() -> None:
    """Espacement régulier (le cas réel, entraxe constant) : chaque nœud
    intérieur porte l'entraxe complet, chaque nœud de bord la moitié."""
    axes = [0.0, 2.6, 5.2, 7.8]
    lengths = _tributary_lengths(axes)
    assert lengths[0] == pytest.approx(1.3)
    assert lengths[1] == pytest.approx(2.6)
    assert lengths[2] == pytest.approx(2.6)
    assert lengths[3] == pytest.approx(1.3)


def test_poutre_pressure_charges_use_nodal_forces_not_force_poutre(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """Lot 33, étape 3 : `FORCE_POUTRE` a été écarté par une exécution réelle
    (`poutre_pressure_nodal_block`'s own docstring) -- la production ne
    l'utilise plus jamais pour la décision 13, seulement `FORCE_NODALE` aux
    nœuds `GEN_POUTRE_<n>`, et la somme des forces nodales de chaque charge
    reproduit exactement la résultante linéique totale (l'invariant que
    l'équilibre global de l'étape 3 vérifie)."""
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    assert "FORCE_POUTRE=" not in text
    for concept in (
        "CH_G_POUTRE",
        "CH_Q1_POUTRE",
        "CH_EAU_P_POUTRE",
        "CH_EAU_A_POUTRE",
    ):
        assert f"{concept} = AFFE_CHAR_MECA(" in text
        assert "FORCE_NODALE=(" in text


# --- lot 35 : synthèse, repère des tubes, maillage orienté --------------------


def _production(verified_mesh: Path, tmp_path: Path) -> str:
    text, _ = generate_comm(
        fiche_path=_FICHE,
        data_path=_DATA,
        med_path=verified_mesh,
        project_root=tmp_path,
        work_dir_root="mesh_runs",
        aster_version="17.4.0",
    )
    return text


def test_lot35_production_writes_the_synthesis_tables_of_every_case(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _production(verified_mesh, tmp_path)

    for case in ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A"):
        for concept in (
            f"TAB_DYT05_{case} = POST_RELEVE_T(",
            f"TAB_DYT01_{case} = POST_RELEVE_T(",
            f"TAB_TETE_{case} = POST_RELEVE_T(",
            f"TAB_EFTUBE_{case} = CREA_TABLE(",
            f"TAB_EFPALP_{case} = CREA_TABLE(",
            f"TAB_EFPOUT_{case} = CREA_TABLE(",
            f"TAB_EFTIR_{case} = CREA_TABLE(",
        ):
            assert concept in text, concept
    assert "GEN_NOEUDS_TUBE_05" in text


def test_lot35_the_combined_reaction_table_is_gone_from_production(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _production(verified_mesh, tmp_path)

    assert "REACTIONS_" not in text
    assert "TAB_REAC_G =" not in text
    assert 'INTITULE="REAC_ANCR_G"' in text  # les tables par groupe restent


def test_lot35_the_tubes_carry_a_vertical_user_frame(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _production(verified_mesh, tmp_path)

    tubes = text[text.index('GROUP_MA=("TUBES",),\n            EPAIS=') :]
    tubes = tubes[: tubes.index("        ),")]
    assert "VECTEUR=(0.0, 0.0, 1.0)" in tubes


def test_lot35_the_oriented_mesh_follows_the_layer_groups(
    verified_mesh: Path, tmp_path: Path
) -> None:
    text = _production(verified_mesh, tmp_path)

    orient = text.index("ORIE_NORM_COQUE")
    layers = text.index("GEN_COUCHE_REMBLAI")
    written = text.index('IMPR_RESU(FORMAT="MED", UNITE=81')
    assert orient < layers < written < text.index("AFFE_MODELE")


def test_lot35_the_layer_loads_still_disable_veri_norm_explicitly(
    verified_mesh: Path, tmp_path: Path
) -> None:
    """`VERI_NORM="NON"` reste sur les occurrences par couche : son remplacement est
    la vérification explicite de `aster_expert.meshing.normals`, pas un retour du
    contrôle automatique (`<F> <MESH3_99>` sur un groupe non connexe)."""
    text = _production(verified_mesh, tmp_path)

    g_load = text[text.index("CH_G_POUSSEE = AFFE_CHAR_MECA_F(") :]
    g_load = g_load[: g_load.index("FORCE_COQUE=(")]
    assert 'VERI_NORM="NON"' in g_load
