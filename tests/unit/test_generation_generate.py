"""`generate_comm` orchestration (lot 28, Étape 3): refusal conditions,
determinism, on the real combi-wall fiche/data with a synthetic mesh cache
(no Salomé/Docker: `generate_comm` never reads the MED's own content, only
its fingerprint against the mesh cache -- exactly what this test exercises)."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.arbitration import lift_revision
from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import _params_json_bytes, generate_comm
from aster_expert.meshing.combiwall import build_params
from aster_expert.meshing.run import MeshRunReport, record_verified_mesh, sha256_file

_ROOT = Path(__file__).resolve().parents[2]
_REFERENCE_FICHE = (
    _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
)
_DATA = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"


def _resolved_fiche_path() -> Path:
    """The real fiche, with the point-3 junction revision (lot 31) lifted in
    memory only -- never written back to the versioned file. This module
    tests `generate_comm`'s own mechanics (determinism, spring sums,
    diagnostics), a question independent of whether MM has closed that
    revision; the versioned fiche itself stays a faithful, blocked record."""
    sheet = HypothesesSheet.model_validate_json(
        _REFERENCE_FICHE.read_text(encoding="utf-8")
    )
    entries = list(sheet.entries)
    for i, e in enumerate(entries):
        if (
            isinstance(e, PracticeHypothesisEntry)
            and e.point_label == "3"
            and e.under_revision
        ):
            entries[i] = lift_revision(
                e,
                reason="Levée locale, pour les seuls besoins de ce test (mécanique du "
                "générateur, indépendante de la décision) -- jamais écrite dans la "
                "fiche versionnée.",
                lifted_by="tests/unit/test_generation_generate.py",
                lifted_at=datetime.now(UTC),
            )
    resolved = sheet.model_copy(update={"entries": tuple(entries)})
    directory = Path(tempfile.mkdtemp(prefix="aster-expert-resolved-fiche-"))
    path = directory / "fiche_resolue.json"
    path.write_text(resolved.model_dump_json(), encoding="utf-8")
    return path


_FICHE = _resolved_fiche_path()


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
    assert report.n_spring_classes == 48


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
        assert f"_F(RESULTAT={name}, CARA_ELEM=CARA)," in text


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
