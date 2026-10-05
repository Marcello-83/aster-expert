"""Déclaration des connaissances appliquées et règles d'épreuve (lot 46, étape 5)."""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

import pytest
import yaml

from aster_expert.connaissances.base import load_knowledge
from aster_expert.connaissances.declaration import (
    DeclarationError,
    companion_path,
    load_for_run,
    project_of,
)
from aster_expert.connaissances.epreuve import evaluate_run, record_proofs
from aster_expert.execution.compte_rendu import build_record, sha256_file, write_record
from aster_expert.execution.models import ExecutionReport

_REPO = Path(__file__).resolve().parents[2]
_CASE = "projets/dalle_appuyee_01/references/cas/dalle_h0p125.comm"
_IDS = {"REF-014", "PAT-009", "PAT-011", "CTL-005", "CTL-010", "CA-045", "PRE-032"}


def _depot(tmp_path: Path) -> Path:
    """Dépôt factice : la base de connaissances réelle, un projet `p`, un cas."""
    root = tmp_path / "depot"
    shutil.copytree(_REPO / "connaissances", root / "connaissances")
    case_dir = root / "projets" / "dalle_appuyee_01" / "references" / "cas"
    case_dir.mkdir(parents=True)
    (root / "projets" / "dalle_appuyee_01" / "projet.yaml").write_text(
        "name: dalle_appuyee_01\n", "utf-8"
    )
    shutil.copy(_REPO / _CASE, case_dir / "dalle_h0p125.comm")
    return root


def _declare(
    root: Path,
    applied: list[dict[str, str]],
    *,
    name: str = "dalle_h0p125.comm",
    **extra: object,
) -> Path:
    comm = (root / _CASE).with_name(name)
    companion_path(comm).write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "project": "dalle_appuyee_01",
                "applied": applied,
                **extra,
            },
            allow_unicode=True,
        ),
        "utf-8",
    )
    return comm


def _ids(root: Path) -> set[str]:
    base = load_knowledge(root)
    return {*base.entries, *base.constats}


def test_projet_de_l_execution(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    assert project_of(root / _CASE, root) == "dalle_appuyee_01"
    assert project_of(root / "data" / "x.comm", root) is None


def test_execution_de_projet_sans_declaration_refusee(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    with pytest.raises(DeclarationError, match="sans déclaration"):
        load_for_run(root / _CASE, root, _ids(root))


def test_execution_hors_projet_sans_declaration_permise(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    hors = root / "data" / "examples" / "cas.comm"
    hors.parent.mkdir(parents=True)
    hors.write_text("DEBUT()\nFIN()\n", "utf-8")
    assert load_for_run(hors, root, _ids(root)) is None


def test_declaration_validee(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    comm = _declare(root, [{"id": "REF-014", "how": "rejeu"}])
    known = load_for_run(comm, root, _ids(root))
    assert known is not None and [e.id for e in known.applied] == ["REF-014"]
    assert known.file.endswith("dalle_h0p125.connaissances.yaml")


def test_declaration_refusee(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    comm = _declare(root, [{"id": "PAT-999", "how": "x"}])
    with pytest.raises(DeclarationError, match="PAT-999"):
        load_for_run(comm, root, _ids(root))
    comm = _declare(root, [{"id": "REF-014", "how": "  "}])
    with pytest.raises(DeclarationError, match="illisible"):
        load_for_run(comm, root, _ids(root))
    comm = _declare(root, [], none_reason=None)
    with pytest.raises(DeclarationError, match="aucun motif"):
        load_for_run(comm, root, _ids(root))
    _declare(root, [], none_reason="calcul de contrôle sans connaissance appliquée")
    assert load_for_run(comm, root, _ids(root)) is not None
    comm_path = companion_path(comm)
    data = yaml.safe_load(comm_path.read_text("utf-8"))
    data["project"] = "autre"
    comm_path.write_text(yaml.safe_dump(data), "utf-8")
    with pytest.raises(DeclarationError, match="autre"):
        load_for_run(comm, root, _ids(root))


def _run(
    root: Path,
    applied: list[dict[str, str]],
    *,
    status: str = "completed_ok",
    comm_name: str = "dalle_h0p125.comm",
    d_verdict: str | None = None,
    d_provenance_ok: bool = True,
    controls: dict[str, dict[str, str]] | None = None,
) -> Path:
    comm = _declare(root, applied, name=comm_name)
    if comm_name != "dalle_h0p125.comm":
        comm.write_text("DEBUT()\nFIN()\n", "utf-8")
    run_dir = root / "data" / "processed" / "runs" / "20261005T120000-abcdef01"
    (run_dir / "proc.0").mkdir(parents=True)
    mess = run_dir / "proc.0" / "fort.6"
    mess.write_text("listing\n", "utf-8")
    known = load_for_run(comm, root, _ids(root))
    report = ExecutionReport(
        comm_path=str(comm),
        aster_version="17.4.0",
        image_digest="sha256:" + "0" * 64,
        status=status,  # type: ignore[arg-type]
        diag="OK",
        return_code=0,
        work_dir=str(run_dir),
        mess_path=str(mess),
        result_files=(),
        duration_s=1.0,
        extracted_by="run_aster.status",
        executed_at=dt.datetime(2026, 10, 5, 12, 0, tzinfo=dt.UTC),
    )
    record = build_record(
        report,
        command="x",
        image="i",
        inputs_sha256={comm.name: sha256_file(comm)},
        knowledge=known,
    )
    write_record(record)
    if d_verdict is not None:
        d_dir = root / "projets" / "dalle_appuyee_01" / "resultats" / "controles"
        d_dir.mkdir(parents=True, exist_ok=True)
        provenance = {
            "comm_sha256": sha256_file(comm) if d_provenance_ok else "0" * 64,
            "mess_sha256": sha256_file(mess),
        }
        (d_dir / "controles_d.json").write_text(
            json.dumps(
                {
                    "verdict": d_verdict,
                    "provenance": provenance,
                    "harness": {"controls": controls or {}},
                }
            ),
            "utf-8",
        )
    return run_dir


def _verdicts(root: Path, run_dir: Path) -> dict[str, tuple[bool, str]]:
    return {
        v.entry_id: (v.proven, v.reason)
        for v in evaluate_run(root, run_dir, load_knowledge(root))
    }


def test_un_constat_et_un_precedent_ne_s_eprouvent_jamais(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    run_dir = _run(
        root,
        [{"id": "CA-045", "how": "x"}, {"id": "PRE-032", "how": "x"}],
        d_verdict="RÉUSSI",
    )
    out = _verdicts(root, run_dir)
    assert out["CA-045"][0] is False and "rejeu de son cas" in out["CA-045"][1]
    assert out["PRE-032"][0] is False and "reste un précédent" in out["PRE-032"][1]


def test_un_patron_exige_un_succes_et_des_controles_d_reussis(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "PAT-009", "how": "x"}], d_verdict="RÉUSSI")
    assert _verdicts(root, run_dir)["PAT-009"][0] is True


def test_un_patron_sans_controle_d_ou_avec_un_echec_n_est_pas_eprouve(
    tmp_path: Path,
) -> None:
    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "PAT-009", "how": "x"}])
    assert "aucun résultat de contrôle D" in _verdicts(root, run_dir)["PAT-009"][1]
    shutil.rmtree(root / "data")
    run_dir = _run(root, [{"id": "PAT-009", "how": "x"}], d_verdict="ÉCHEC")
    assert "ÉCHEC" in _verdicts(root, run_dir)["PAT-009"][1]
    shutil.rmtree(root / "data")
    run_dir = _run(
        root, [{"id": "PAT-009", "how": "x"}], d_verdict="RÉUSSI", d_provenance_ok=False
    )
    assert "ne portent pas sur les résultats" in _verdicts(root, run_dir)["PAT-009"][1]
    shutil.rmtree(root / "data")
    run_dir = _run(
        root, [{"id": "PAT-009", "how": "x"}], status="failed", d_verdict="RÉUSSI"
    )
    assert "non réussie" in _verdicts(root, run_dir)["PAT-009"][1]


def test_un_controle_est_eprouve_s_il_s_est_execute_et_reussi(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    run_dir = _run(
        root,
        [{"id": "CTL-005", "how": "x"}, {"id": "CTL-010", "how": "x"}],
        d_verdict="RÉUSSI",
        controls={"CTL-005": {"verdict": "RÉUSSI"}},
    )
    out = _verdicts(root, run_dir)
    assert out["CTL-005"][0] is True
    assert out["CTL-010"][0] is False and "n'apparaît pas" in out["CTL-010"][1]


def test_un_controle_en_echec_sur_un_defaut_corrige_est_propose_pas_prouve(
    tmp_path: Path,
) -> None:
    root = _depot(tmp_path)
    run_dir = _run(
        root,
        [
            {
                "id": "CTL-005",
                "how": "x",
                "corrected_defect": "tirant en section entière",
            }
        ],
        d_verdict="ÉCHEC",
        controls={"CTL-005": {"verdict": "ÉCHEC"}},
    )
    proven, reason = _verdicts(root, run_dir)["CTL-005"]
    assert proven is False and "à proposer à MM" in reason


def test_une_reference_est_eprouvee_par_le_rejeu_reussi_d_un_de_ses_cas(
    tmp_path: Path,
) -> None:
    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "REF-014", "how": "rejeu"}])
    assert _verdicts(root, run_dir)["REF-014"][0] is True
    shutil.rmtree(root / "data")
    run_dir = _run(root, [{"id": "REF-014", "how": "rejeu"}], comm_name="autre.comm")
    assert "aucun des cas versionnés" in _verdicts(root, run_dir)["REF-014"][1]


def test_une_execution_sans_declaration_n_eprouve_rien(tmp_path: Path) -> None:
    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "REF-014", "how": "rejeu"}])
    record = json.loads((run_dir / "compte_rendu.json").read_text("utf-8"))
    record["knowledge"] = None
    (run_dir / "compte_rendu.json").write_text(json.dumps(record), "utf-8")
    assert evaluate_run(root, run_dir, load_knowledge(root)) == []


def test_l_enregistrement_ajoute_une_reutilisation_sans_promotion(
    tmp_path: Path,
) -> None:
    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "PAT-009", "how": "x"}], d_verdict="RÉUSSI")
    base = load_knowledge(root)
    before = base.entries["PAT-009"]
    verdicts = evaluate_run(root, run_dir, base)
    written = record_proofs(root, run_dir, verdicts, base, today=dt.date(2026, 10, 5))
    assert len(written) == 1
    after = load_knowledge(root).entries["PAT-009"]
    assert len(after.reuses) == len(before.reuses) + 1
    assert after.status == before.status
    new = after.reuses[-1]
    assert new.proven and new.project == "dalle_appuyee_01"
    # idempotent
    again = record_proofs(root, run_dir, verdicts, load_knowledge(root))
    assert again == []


def test_la_commande_eprouver_refuse_une_execution_sans_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lecture_sous_tmp: Path
) -> None:
    from typer.testing import CliRunner

    from aster_expert.cli import app

    root = _depot(tmp_path)
    run_dir = _run(root, [{"id": "REF-014", "how": "rejeu"}])
    record = json.loads((run_dir / "compte_rendu.json").read_text("utf-8"))
    record["knowledge"] = None
    (run_dir / "compte_rendu.json").write_text(json.dumps(record), "utf-8")
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(root))
    monkeypatch.chdir(root)
    result = CliRunner().invoke(app, ["connaissances", "eprouver", run_dir.name])
    assert result.exit_code == 1
    assert "pas d'attribution rétroactive" in result.output


def test_l_execution_d_un_projet_sans_declaration_est_refusee_avant_le_conteneur(
    tmp_path: Path,
) -> None:
    from aster_expert.execution.config import ExecutionConfig
    from aster_expert.execution.errors import ExecutionRunError
    from aster_expert.execution.execute import execute_comm_file

    root = _depot(tmp_path)
    config = ExecutionConfig(
        enabled=True,
        allowed_roots=("projets",),
        work_dir_root="data/processed/runs",
        keep_work_dir=True,
        timeout_seconds=10,
        memory_mb=512,
        cpus_limit="1",
        mpi_processes=1,
        write_outside_work_dir=False,
    )
    with pytest.raises(ExecutionRunError, match="sans déclaration"):
        execute_comm_file(
            root / _CASE,
            project_root=root,
            config=config,
            docker_bin=Path("/nonexistent/docker"),
            image_repository="r",
            image_digest="sha256:" + "0" * 64,
            aster_version="17.4.0",
        )
    assert not (root / "data" / "processed" / "runs").exists()


def test_rex_signale_une_execution_de_projet_sans_declaration(tmp_path: Path) -> None:
    from aster_expert.connaissances.rex import (
        RexRegistry,
        record_manifest,
        render_report,
        review_project,
        write_registry,
    )

    root = _depot(tmp_path)
    for layer in ("controles", "patrons"):
        assert (root / "connaissances" / layer).is_dir()
    run_dir = _run(root, [{"id": "REF-014", "how": "rejeu"}])
    record = json.loads((run_dir / "compte_rendu.json").read_text("utf-8"))
    record["knowledge"] = None
    (run_dir / "compte_rendu.json").write_text(json.dumps(record), "utf-8")
    write_registry(
        root,
        RexRegistry(
            project="dalle_appuyee_01",
            case_roots=("projets/dalle_appuyee_01",),
            declaration_required_since=dt.datetime(2026, 10, 5),
        ),
    )
    record_manifest(root, "dalle_appuyee_01")
    report = review_project(root, "dalle_appuyee_01")
    assert report.runs_without_declaration == (run_dir.name,)
    assert report.blocking == []
    assert any("sans déclaration" in line for line in render_report(report))
