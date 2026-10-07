"""Base de connaissances (lot 42) : schémas des six couches, règles de statut et de
promotion, recherche, signatures d'erreur et diagnostics, compte rendu
d'exécution, retour d'expérience, rejeu des références, outil MCP et commandes.

Les tests qui lisent la base versionnée vérifient l'amorçage du lot 42 ; les
autres travaillent sur un dépôt minimal en répertoire temporaire, sans Docker."""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from aster_expert.cli import app
from aster_expert.connaissances.base import (
    KnowledgeBaseError,
    load_knowledge,
    verify_against_repository,
    write_entry,
)
from aster_expert.connaissances.modeles import (
    CaughtError,
    CodeEvidence,
    Control,
    DecisionEvidence,
    Diagnostic,
    DocumentEvidence,
    ExecutionEvidence,
    Pattern,
    Precedent,
    ReferenceQuantity,
    Reuse,
    Signature,
    TestEvidence,
)
from aster_expert.connaissances.precedents import propose_precedent
from aster_expert.connaissances.promotion import (
    PromotionRefusedError,
    promote,
    promotion_conditions,
)
from aster_expert.connaissances.recherche import search_knowledge
from aster_expert.connaissances.references import replay_references
from aster_expert.connaissances.rex import (
    Classification,
    RexRegistry,
    load_registry,
    read_log_tolerant,
    record_manifest,
    render_dashboard,
    render_report,
    review_project,
    write_metrics,
    write_registry,
)
from aster_expert.connaissances.signatures import (
    RunMessage,
    listing_messages,
    match_diagnostics,
    primary_signature,
)
from aster_expert.execution.compte_rendu import build_record, render_markdown
from aster_expert.execution.models import ExecutionMessage, ExecutionReport
from aster_expert.mcp import tools

ROOT = Path(__file__).resolve().parents[2]
SHA = "0" * 64


def _pattern(**update: Any) -> Pattern:
    data: dict[str, Any] = {
        "id": "PAT-001",
        "title": "Patron d'essai",
        "summary": "Un patron d'essai pour les tests.",
        "origin_project": "projet_a",
        "date": dt.date(2026, 10, 1),
        "validation_level": "B",
        "status": "établi",
        "sources": [{"kind": "test", "path": "tests/t.py", "function": "test_x"}],
        "commands": ["AFFE_MODELE"],
        "keywords": ["DKT"],
        "problem": "Un problème.",
        "solution": "Une solution.",
        "fragment": "DEBUT()",
        "fragment_language": "comm",
        "conditions": "Aucune.",
    }
    data.update(update)
    return Pattern.model_validate(data)


def _mini_repo(tmp_path: Path) -> Path:
    root = tmp_path / "depot"
    (root / "connaissances" / "constats_code_aster").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "tests" / "t.py").write_text("def test_x() -> None:\n    pass\n", "utf-8")
    return root


# --------------------------------------------------------------------------
# Schémas et statuts
# --------------------------------------------------------------------------


def test_an_entry_without_proof_is_refused() -> None:
    with pytest.raises(ValidationError, match="sans preuve"):
        _pattern(sources=[])


def test_established_requires_a_replayable_proof() -> None:
    doc = {"kind": "document", "path": "docs/x.md"}
    with pytest.raises(ValidationError, match="sans preuve rejouable"):
        _pattern(sources=[doc])
    assert _pattern(sources=[doc], status="observé", validation_level="A")


def test_a_failed_run_without_a_versioned_case_is_not_replayable() -> None:
    run = {
        "kind": "execution",
        "run": "20260923T093604-686ef117",
        "outcome": "échec",
        "note": "n",
    }
    with pytest.raises(ValidationError, match="sans preuve rejouable"):
        _pattern(sources=[run])


def test_promoted_requires_two_projects_and_a_recorded_promotion() -> None:
    event = {"status": "promu", "date": "2026-10-02", "by": "MM", "reason": "r"}
    with pytest.raises(ValidationError, match="second projet"):
        _pattern(status="promu", status_history=[event])
    reuse = Reuse(
        project="projet_b",
        date=dt.date(2026, 10, 2),
        evidence=TestEvidence(path="tests/t.py", function="test_x"),
        note="réutilisé",
    )
    with pytest.raises(ValidationError, match="connaissances promouvoir"):
        _pattern(status="promu", reuses=[reuse])
    assert (
        _pattern(status="promu", reuses=[reuse], status_history=[event]).status
        == "promu"
    )


def test_a_reuse_in_the_origin_project_does_not_count() -> None:
    reuse = Reuse(
        project="projet_a",
        date=dt.date(2026, 10, 2),
        evidence=TestEvidence(path="tests/t.py", function="test_x"),
        note="même projet",
    )
    with pytest.raises(ValidationError, match="autre projet"):
        _pattern(reuses=[reuse])


def test_identifiers_follow_the_layer_and_official_case() -> None:
    with pytest.raises(ValidationError, match="PAT-"):
        _pattern(id="DIAG-001")
    with pytest.raises(ValidationError, match="casse officielle"):
        _pattern(keywords=["dkt"])


def test_execution_evidence_rules() -> None:
    with pytest.raises(ValidationError, match="empreinte"):
        ExecutionEvidence(case_path="a/b.comm", outcome="réussite", level="C", note="n")
    with pytest.raises(ValidationError, match="aucun niveau"):
        ExecutionEvidence(
            case_path="a/b.comm", case_sha256=SHA, outcome="échec", level="C", note="n"
        )
    with pytest.raises(ValidationError, match="déclare le niveau"):
        ExecutionEvidence(
            case_path="a/b.comm", case_sha256=SHA, outcome="réussite", note="n"
        )


def test_signature_and_environment_rules() -> None:
    with pytest.raises(ValidationError, match="identifiants ou un motif"):
        Signature(kind="<F>")
    common: dict[str, Any] = {
        "title": "t",
        "summary": "Un diagnostic.",
        "origin_project": "p",
        "date": "2026-10-01",
        "validation_level": "A",
        "status": "observé",
        "sources": [{"kind": "document", "path": "docs/x.md"}],
        "cause": "c",
        "cause_established": True,
        "correction": "c",
    }
    with pytest.raises(ValidationError, match="ENV-nnn"):
        Diagnostic.model_validate(
            {
                **common,
                "id": "DIAG-099",
                "category": "environnement",
                "signature": {"kind": "environnement", "pattern": "x"},
            }
        )


def test_only_a_promoted_control_enters_the_default_harness() -> None:
    with pytest.raises(ValidationError, match="harnais par défaut"):
        Control.model_validate(
            {
                "id": "CTL-099",
                "title": "t",
                "summary": "Un contrôle.",
                "origin_project": "p",
                "date": "2026-10-01",
                "validation_level": "B",
                "status": "établi",
                "sources": [
                    {"kind": "test", "path": "tests/t.py", "function": "test_x"}
                ],
                "detects": "d",
                "parameters": "p",
                "implementation": CodeEvidence(path="src/x.py", symbol="f"),
                "scope": "tronc commun",
                "caught_error": CaughtError(mode="aucune consignée", description="d"),
                "default_harness": True,
            }
        )


def test_a_reference_result_is_recomputed_from_its_criterion() -> None:
    with pytest.raises(ValidationError, match="critère appliqué"):
        ReferenceQuantity(
            name="q",
            value_obtained=1.01,
            reference_value=1.0,
            criterion="exact",
            tolerance=1e-6,
            result="réussi",
        )
    refined = ReferenceQuantity(
        name="q",
        value_obtained=0.98,
        reference_value=1.0,
        criterion="raffinement",
        refined_case_path="a/fin.comm",
        refined_value=0.995,
        result="réussi",
    )
    assert refined.computed_result() == "réussi"


# --------------------------------------------------------------------------
# Base versionnée (amorçage du lot 42)
# --------------------------------------------------------------------------


def test_the_versioned_base_loads_with_its_seeding_counts() -> None:
    """Amorçage par le quai (lot 42), puis apport de la dalle (lot 43) : 7
    constats, 2 patrons, 1 contrôle, 1 référence, 10 précédents ; lot 44 : CA-053
    et les précédents de D20 et D21 (PRE-019, PRE-020) ; lot 45 : PRE-032 (Es) ;
    lot 46 : CTL-013 ; lot 47 (estacade) : CA-054 à CA-057, PAT-012, CTL-014, REF-015
    (calcul externe non validé), PRE-033 à PRE-038 ; lot 47 bis : CA-058, PAT-013 ;
    lot 47 ter : ENV-002, ENV-003, DIAG-025 ; lot 47 quater : ENV-004, DIAG-026,
    DIAG-027, PRE-039."""
    base = load_knowledge(ROOT)
    counts = {layer: sum(row.values()) for layer, row in base.counts().items()}
    assert counts == {
        "constats_code_aster": 58,
        "diagnostics": 31,
        "patrons": 13,
        "controles": 14,
        "references_validation": 15,
        "precedents": 38,
    }
    # Lot 44 : cinq promotions, par la commande, sous la règle corrigée.
    promoted = sorted(e.id for e in base.all_entries() if e.status == "promu")
    assert promoted == ["CTL-005", "CTL-006", "CTL-012", "PAT-011", "REF-014"]


def test_every_proof_of_the_versioned_base_holds_against_the_repository() -> None:
    check = verify_against_repository(load_knowledge(ROOT))
    assert check.problems == ()


def test_nothing_from_the_single_project_can_be_promoted() -> None:
    allowed, reason, projects = promotion_conditions(ROOT, "PAT-001")
    assert not allowed and "un seul projet" in reason and len(projects) == 1
    allowed, reason, _ = promotion_conditions(ROOT, "CA-021")
    assert not allowed


def test_the_second_project_owns_its_findings_and_opens_promotions() -> None:
    """Lot 43 : un constat d'un projet sans `fiche_project_name` est attribué par
    sa `structure`. Lot 44 : seule une réutilisation éprouvée (exécution réussie,
    test) compte ; une citation par la fiche de la dalle ne compte plus."""
    base = load_knowledge(ROOT)
    assert "dalle_appuyee_01" in base.constats["CA-052"].projects
    assert base.constats["CA-045"].projects == ("quai_cw_test_01",)
    # Lot 47 : la fiche de l'estacade cite aussi CA-045, sans l'éprouver.
    assert base.constats["CA-045"].cited_by == ("dalle_appuyee_01", "estacade_pieux_01")
    # Code seul (script de maillage) : pas une épreuve.
    allowed, reason, projects = promotion_conditions(ROOT, "PAT-008")
    assert not allowed and "cité sans épreuve par dalle_appuyee_01" in reason
    # REF-014 (niveau E) a été promu au lot 44.
    allowed, reason, _ = promotion_conditions(ROOT, "REF-014")
    assert not allowed and "déjà promu" in reason
    assert not promotion_conditions(ROOT, "PRE-018")[0]  # observé : jamais promu
    from aster_expert.connaissances.rex import knowledge_counts  # noqa: PLC0415

    counts = knowledge_counts(ROOT, "dalle_appuyee_01", base)
    assert sum(counts["constats_code_aster"].values()) == 8  # lot 44 : CA-053


def test_formal_eligibility_of_lot_43_is_gone() -> None:
    """CA-025 et CA-041 n'étaient éligibles qu'en étant cités par la dalle."""
    for cid in ("CA-025", "CA-041"):
        allowed, reason, projects = promotion_conditions(ROOT, cid)
        assert not allowed, cid
        assert projects == ["quai_cw_test_01"]
        assert "cité sans épreuve" in reason


def test_only_a_successful_run_or_a_test_proves_a_reuse() -> None:
    from aster_expert.connaissances.modeles import is_proof  # noqa: PLC0415

    run = ExecutionEvidence(
        case_path="c.comm", case_sha256=SHA, outcome="réussite", level="D", note="n"
    )
    failed = ExecutionEvidence(
        case_path="c.comm", case_sha256=SHA, outcome="échec", note="n"
    )
    assert is_proof(run)
    assert not is_proof(failed)
    assert is_proof(TestEvidence(path="tests/t.py", function="test_x"))
    assert not is_proof(DocumentEvidence(path="docs/x.md"))
    assert not is_proof(CodeEvidence(path="src/x.py", symbol="f"))
    decision = DecisionEvidence(
        fiche="f.json",
        point_label="1",
        decided_by="MM",
        decided_at=dt.datetime(2026, 10, 2, tzinfo=dt.UTC),
    )
    assert not is_proof(decision)
    cited = Reuse(
        project="projet_b", date=dt.date(2026, 10, 2), evidence=decision, note="n"
    )
    entry = _pattern(reuses=[cited])
    assert entry.projects() == {"projet_a"}
    assert entry.cited_projects() == {"projet_b"}


def test_a_finding_is_proved_by_an_epreuve_never_by_a_citation(tmp_path: Path) -> None:
    from aster_expert.connaissances.base import ConstatProof  # noqa: PLC0415

    with pytest.raises(ValidationError, match="jamais une citation"):
        ConstatProof(
            constat_id="CA-001",
            reuse=Reuse(
                project="p",
                date=dt.date(2026, 10, 2),
                evidence=DocumentEvidence(path="docs/x.md"),
                note="n",
            ),
        )
    root = _mini_repo(tmp_path)
    (root / "connaissances" / "epreuves_constats.yaml").write_text(
        "epreuves:\n- constat_id: CA-999\n  reuse:\n    project: p\n"
        "    date: '2026-10-02'\n    evidence: {kind: test, path: tests/t.py, "
        "function: test_x}\n    note: n\n",
        encoding="utf-8",
    )
    with pytest.raises(KnowledgeBaseError, match="CA-999 absent de la base"):
        load_knowledge(root)


def test_a_base_with_a_wrong_file_name_or_unknown_finding_is_refused(
    tmp_path: Path,
) -> None:
    root = _mini_repo(tmp_path)
    write_entry(root, _pattern())
    shutil.move(
        root / "connaissances" / "patrons" / "PAT-001.yaml",
        root / "connaissances" / "patrons" / "PAT-002.yaml",
    )
    with pytest.raises(KnowledgeBaseError, match="porte l'identifiant"):
        load_knowledge(root)
    (root / "connaissances" / "patrons" / "PAT-002.yaml").unlink()
    write_entry(root, _pattern(constats=("CA-999",)))
    with pytest.raises(KnowledgeBaseError, match="CA-999 absent"):
        load_knowledge(root)


def test_a_level_above_the_proofs_is_refused(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    write_entry(root, _pattern(validation_level="D"))
    with pytest.raises(KnowledgeBaseError, match="niveau D déclaré, B atteint"):
        load_knowledge(root)


# --------------------------------------------------------------------------
# Recherche
# --------------------------------------------------------------------------


def test_search_by_message_identifier_finds_the_diagnostic() -> None:
    base = load_knowledge(ROOT)
    hits = search_knowledge(base, keyword="FACTOR_11", layers=("diagnostics",))
    assert [h.entry_id for h in hits] == ["DIAG-001"]


def test_search_spans_the_layers_and_ignores_accents() -> None:
    base = load_knowledge(ROOT)
    layers = {
        h.layer for h in search_knowledge(base, text="surface developpee", limit=50)
    }
    assert {"constats_code_aster", "patrons", "references_validation"} <= layers


def test_search_refuses_an_unknown_layer_or_status() -> None:
    base = load_knowledge(ROOT)
    with pytest.raises(ValueError, match="couche"):
        search_knowledge(base, layers=("inconnue",))
    with pytest.raises(ValueError, match="statut"):
        search_knowledge(base, status="validé")
    with pytest.raises(ValueError, match="au moins un critère"):
        search_knowledge(base)


# --------------------------------------------------------------------------
# Signatures et diagnostics
# --------------------------------------------------------------------------

_LISTING = """
 ║ <E> <CATAMESS_3>                    ║
 ║ L'alarme DISCRETS_26 est aggravée en erreur. ║
 ║ <F> <DISCRETS_26>                   ║
 ║ vous utilisez la matrice de MASSE   ║
--- DIAGNOSTIC JOB : <F>_ERROR
"""


def test_the_announcer_is_skipped_by_the_primary_signature() -> None:
    messages = listing_messages(_LISTING)
    assert [m.identifier for m in messages] == ["CATAMESS_3", "DISCRETS_26"]
    assert primary_signature(messages, "<F>_ERROR", _LISTING) == "<F> <DISCRETS_26>"


def test_an_abnormal_stop_is_named_by_the_listing() -> None:
    listing = (
        "Segmentation fault (core dumped)\n--- DIAGNOSTIC JOB : <F>_ABNORMAL_ABORT\n"
    )
    sig = primary_signature([], "<F>_ABNORMAL_ABORT", listing)
    assert sig == "arrêt anormal (Segmentation fault)"
    base = load_knowledge(ROOT)
    matches = match_diagnostics(base, [], diag="<F>_ABNORMAL_ABORT", listing=listing)
    assert [m.diagnostic_id for m in matches] == ["DIAG-022"]


def test_each_seeded_signature_matches_its_diagnostic_only() -> None:
    base = load_knowledge(ROOT)
    msg = RunMessage(kind="<F>", identifier="FACTOR_11", text="pivot nul")
    assert [m.diagnostic_id for m in match_diagnostics(base, [msg])] == ["DIAG-001"]
    msg = RunMessage(kind="<F>", identifier="INCONNU_99", text="x")
    assert match_diagnostics(base, [msg]) == []


def _failed_report(work_dir: Path, mess: Path | None = None) -> ExecutionReport:
    return ExecutionReport(
        comm_path=str(work_dir / "essai.comm"),
        aster_version="17.4.0",
        image_digest="sha256:" + SHA,
        status="failed",
        diag="<F>_ERROR",
        return_code=1,
        work_dir=str(work_dir),
        mess_path=str(mess) if mess else None,
        result_files=(),
        duration_s=1.0,
        extracted_by="run_aster.status",
        executed_at=dt.datetime(2026, 10, 1, tzinfo=dt.UTC),
        messages=(
            ExecutionMessage(
                kind="<F>",
                identifier="CALCULEL2_92",
                line=3,
                text="<F> <CALCULEL2_92> x",
            ),
        ),
        messages_source="run_aster.error_messages",
    )


def test_a_failed_run_report_lists_the_matching_diagnostics(tmp_path: Path) -> None:
    record = build_record(
        _failed_report(tmp_path),
        command="run",
        image="img",
        inputs_sha256={},
        knowledge_root=ROOT,
    )
    assert [d.diagnostic_id for d in record.diagnostics] == ["DIAG-009"]
    markdown = render_markdown(record)
    assert "## Diagnostics de la base de connaissances" in markdown
    assert "DIAG-009" in markdown


def test_an_unreadable_base_is_reported_not_fatal(tmp_path: Path) -> None:
    record = build_record(
        _failed_report(tmp_path),
        command="run",
        image="img",
        inputs_sha256={},
        knowledge_root=tmp_path,
    )
    assert record.diagnostics == () and record.diagnostics_error is not None


# --------------------------------------------------------------------------
# Précédents et promotion
# --------------------------------------------------------------------------


def test_a_precedent_is_only_proposed_never_applied() -> None:
    base = load_knowledge(ROOT)
    precedent = base.entries["PRE-001"]
    assert isinstance(precedent, Precedent)
    entry, source = propose_precedent(precedent, point_label="1")
    assert entry.status == "non_tranche" and entry.sources == ()
    assert entry.decided_by is None and "non appliqué" in (entry.notes or "")
    assert source.origin == "precedent_projet" and "PRE-001" in source.reference


def test_promotion_checks_its_conditions_and_records_itself(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    write_entry(root, _pattern())
    with pytest.raises(PromotionRefusedError, match="un seul projet"):
        promote(root, "PAT-001", by="MM", reason="essai")
    reuse = Reuse(
        project="projet_b",
        date=dt.date(2026, 10, 2),
        evidence=TestEvidence(path="tests/t.py", function="test_x"),
        note="réutilisé avec succès",
    )
    write_entry(root, _pattern(reuses=[reuse]))
    message = promote(
        root, "PAT-001", by="MM", reason="deux projets", today=dt.date(2026, 10, 3)
    )
    assert "promu" in message
    assert load_knowledge(root).entries["PAT-001"].status == "promu"
    journal = yaml.safe_load(
        (root / "connaissances" / "promotions.yaml").read_text("utf-8")
    )
    assert journal["promotions"][0]["projects"] == ["projet_a", "projet_b"]
    with pytest.raises(PromotionRefusedError, match="déjà promu"):
        promote(root, "PAT-001", by="MM", reason="encore")


def test_an_observed_entry_cannot_be_promoted(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    write_entry(
        root,
        _pattern(
            status="observé",
            validation_level="A",
            sources=[DocumentEvidence(path="docs/x.md")],
        ),
    )
    allowed, reason, _ = promotion_conditions(root, "PAT-001")
    assert not allowed and "observé" in reason


# --------------------------------------------------------------------------
# Retour d'expérience
# --------------------------------------------------------------------------


def _rex_repo(tmp_path: Path) -> Path:
    root = _mini_repo(tmp_path)
    for layer in ("constats_code_aster", "diagnostics"):
        shutil.copytree(
            ROOT / "connaissances" / layer,
            root / "connaissances" / layer,
            dirs_exist_ok=True,
        )
    runs = root / "data" / "processed" / "runs"
    for run_id, status, ident in (
        ("20261005T100000-aaaaaaaa", "failed", "FACTOR_11"),
        ("20261005T110000-bbbbbbbb", "completed_ok", None),
    ):
        work = runs / run_id
        work.mkdir(parents=True)
        errors = (
            [
                {
                    "kind": "<F>",
                    "identifier": ident,
                    "line": 1,
                    "text": f"<F> <{ident}> pivot",
                }
            ]
            if ident
            else []
        )
        record: dict[str, Any] = {
            "report": {
                "comm_path": str(root / "projets" / "p" / "cas.comm"),
                "status": status,
                "diag": "<F>_ERROR" if ident else "OK",
                "duration_s": 12.5,
                "mess_path": None,
            },
            "errors": errors,
        }
        (work / "compte_rendu.json").write_text(json.dumps(record), "utf-8")
    write_registry(root, RexRegistry(project="p", case_roots=("projets/p",)))
    record_manifest(root, "p")  # lot 46 : l'archive factice est la complète
    return root


def test_an_unclassified_failure_blocks_the_closure(tmp_path: Path) -> None:
    root = _rex_repo(tmp_path)
    report = review_project(root, "p")
    assert report.runs == 2 and len(report.failures) == 1
    assert [f.problem for f in report.blocking] == ["non classé"]
    assert report.failures[0].suggestions == ("DIAG-001",)
    assert any("BLOQUANT" in line for line in render_report(report))


def test_a_classified_failure_releases_the_closure(tmp_path: Path) -> None:
    root = _rex_repo(tmp_path)
    write_registry(
        root,
        RexRegistry(
            project="p",
            case_roots=("projets/p",),
            archive=load_registry(root, "p").archive,
            classifications=(
                Classification(
                    run="20261005T100000-aaaaaaaa",
                    signature="<F> <FACTOR_11>",
                    decision="rattaché",
                    diagnostic="DIAG-001",
                    reason="pivot nul connu",
                ),
            ),
        ),
    )
    report = review_project(root, "p")
    assert report.blocking == []
    measured = report.metrics["measured"]
    assert measured["failure_rate"] == 0.5
    assert measured["automatic_diagnosis"]["single_match_equal_to_classification"] == 1
    write_metrics(root, report.metrics)
    assert "`p`" in render_dashboard(root)


def test_a_classification_under_another_signature_blocks(tmp_path: Path) -> None:
    root = _rex_repo(tmp_path)
    write_registry(
        root,
        RexRegistry(
            project="p",
            case_roots=("projets/p",),
            archive=load_registry(root, "p").archive,
            classifications=(
                Classification(
                    run="20261005T100000-aaaaaaaa",
                    signature="<F> <MED2_4>",
                    decision="écarté",
                    reason="faute de frappe",
                ),
            ),
        ),
    )
    assert "classé sous la signature" in (
        review_project(root, "p").blocking[0].problem or ""
    )


def test_without_run_archives_rex_says_so_without_failing(tmp_path: Path) -> None:
    root = _rex_repo(tmp_path)
    shutil.rmtree(root / "data")
    report = review_project(root, "p")
    assert not report.archives_present and report.blocking == []
    assert (
        "Archive d'exécution refusée : archives d'exécution absentes"
        in (render_report(report)[1])
    )


def test_a_damaged_journal_line_is_counted_not_fatal(tmp_path: Path) -> None:
    log = tmp_path / "query_log.jsonl"
    good = {
        "timestamp": "2026-10-01T00:00:00Z",
        "tool": "search_connaissances",
        "duration_s": 0.1,
    }
    log.write_text("\x00\x00{\n" + json.dumps(good) + "\n", encoding="utf-8")
    entries, bad = read_log_tolerant(log)
    assert len(entries) == 1 and bad == 1


def test_the_registry_refuses_a_failure_set_aside_without_reason() -> None:
    with pytest.raises(ValidationError, match="motif"):
        Classification(run="r", signature="s", decision="écarté", reason=" ")
    with pytest.raises(ValidationError, match="nomme son diagnostic"):
        Classification(run="r", signature="s", decision="rattaché", reason="x")


# --------------------------------------------------------------------------
# Rejeu des références (conteneur simulé)
# --------------------------------------------------------------------------


def test_the_reference_replay_finds_every_recorded_value(tmp_path: Path) -> None:
    base = load_knowledge(ROOT)
    values = [
        q.value_obtained
        for e in base.entries.values()
        if e.layer == "references_validation"
        for c in e.cases  # type: ignore[attr-defined]
        for q in c.quantities
    ] + [
        q.refined_value
        for e in base.entries.values()
        if e.layer == "references_validation"
        for c in e.cases  # type: ignore[attr-defined]
        for q in c.quantities
        if q.refined_value is not None
    ]
    mess = tmp_path / "fake.mess"
    mess.write_text("\n".join(f"{v:.12E}" for v in values), encoding="utf-8")

    def runner(comm: Path) -> ExecutionReport:
        report = _failed_report(tmp_path, mess)
        return report.model_copy(
            update={"status": "completed_ok", "comm_path": str(comm)}
        )

    result = replay_references(
        ROOT,
        only=("REF-001", "REF-008"),
        output_dir=tmp_path / "out",
        runner=(runner, "17.4.0", "d"),
    )
    assert [r.verdict for r in result.references] == ["tient", "tient"]
    # REF-008 : trois cas et les deux maillages raffinés (×2), rejoués aussi.
    assert len(result.references[1].cases) == 5
    assert (tmp_path / "out" / "rejeu.md").is_file()


# --------------------------------------------------------------------------
# Outil MCP et commandes
# --------------------------------------------------------------------------


def test_the_mcp_tool_answers_level_a_and_journals_itself(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    result = tools.search_connaissances(
        project_root=ROOT,
        keyword="FACTOR_11",
        layers=["diagnostics"],
        limit=5,
        log_path=log,
    )
    assert result.validation_level == "A"
    assert [r.id for r in result.results][:1] == ["DIAG-001"]
    assert (
        result.results[0].layer == "diagnostics"
        and result.results[0].status == "établi"
    )
    assert result.total_by_layer["precedents"] == 38  # lot 47 quater : PRE-039
    line = json.loads(log.read_text("utf-8").splitlines()[0])
    assert line["tool"] == "search_connaissances"


def test_cli_verifier_chercher_and_refused_promotion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(ROOT))
    runner = CliRunner()
    out = runner.invoke(app, ["connaissances", "verifier"])
    assert out.exit_code == 0, out.output
    assert "diagnostics : 31" in out.output
    out = runner.invoke(app, ["connaissances", "chercher", "--mot-cle", "MED2_4"])
    assert out.exit_code == 0 and "DIAG-006" in out.output
    out = runner.invoke(
        app, ["connaissances", "promouvoir", "PAT-001", "--motif", "essai"]
    )
    assert out.exit_code == 1


def test_cli_proposer_precedent_prints_a_non_arbitrated_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(ROOT))
    out = CliRunner().invoke(
        app, ["connaissances", "proposer-precedent", "PRE-005", "--point", "4"]
    )
    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["entree_proposee"]["status"] == "non_tranche"
    assert payload["source_si_retenu"]["origin"] == "precedent_projet"


def test_cli_rex_blocks_on_an_unclassified_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _rex_repo(tmp_path)
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(root))
    out = CliRunner().invoke(app, ["rex", "p"])
    assert out.exit_code == 1
    assert "clôture du lot bloquée" in out.output
    assert (root / "connaissances" / "metriques" / "p.yaml").is_file()


def _external_reference(**changes: object) -> dict[str, object]:
    """A reference of kind « calcul externe non validé » (lot 47)."""
    sha = "a" * 64
    data: dict[str, object] = {
        "id": "REF-900",
        "title": "Contre-calcul d'un modèle externe",
        "summary": "Comparaison à un calcul externe non validé.",
        "origin_project": "projet_essai",
        "date": "2026-10-05",
        "validation_level": "D",
        "status": "établi",
        "replay_mode": "listing",
        "sources": [
            {
                "kind": "execution",
                "case_path": "projets/x/cas.comm",
                "case_sha256": sha,
                "outcome": "réussite",
                "level": "D",
                "note": "cas d'essai",
                "run": None,
            },
        ],
        "problem": "Estacade.",
        "reference_solution": "Valeurs publiées d'un modèle non validé.",
        "cases": [
            {
                "case_path": "projets/x/cas.comm",
                "case_sha256": sha,
                "quantities": [
                    {
                        "name": "N",
                        "value_obtained": 1.02,
                        "reference_value": 1.0,
                        "criterion": "contre_calcul",
                        "tolerance": 0.03,
                        "result": "réussi",
                    },
                ],
            }
        ],
        "result": "réussi",
        "reference_kind": "calcul_externe_non_valide",
    }
    data.update(changes)
    return data


def test_an_external_calculation_reference_is_never_level_e_nor_promoted() -> None:
    from aster_expert.connaissances.modeles import ValidationReference

    ref = ValidationReference.model_validate(_external_reference())
    assert ref.reference_kind == "calcul_externe_non_valide"
    with pytest.raises(ValueError, match="calcul externe non validé"):
        ValidationReference.model_validate(_external_reference(validation_level="E"))
    # « promu » est refusé (par cette règle ou par celle de l'historique de statut).
    with pytest.raises(ValueError, match="promu"):
        ValidationReference.model_validate(_external_reference(status="promu"))
    known = _external_reference(reference_kind="solution_connue")
    with pytest.raises(ValueError, match="réservé"):
        ValidationReference.model_validate(known)


def test_a_known_solution_reference_keeps_its_bytes() -> None:
    from aster_expert.connaissances.base import dump_entry, read_entry

    path = ROOT / "connaissances" / "references_validation" / "REF-014.yaml"
    entry = read_entry(path, "references_validation")
    assert "reference_kind" not in dump_entry(entry)
    assert dump_entry(entry) == path.read_text(encoding="utf-8")


def test_an_external_calculation_reference_serves_no_promotion(tmp_path: Path) -> None:
    from aster_expert.connaissances.base import dump_entry
    from aster_expert.connaissances.modeles import ValidationReference

    root = tmp_path
    (root / "connaissances" / "references_validation").mkdir(parents=True)
    ref = ValidationReference.model_validate(_external_reference())
    (root / "connaissances" / "references_validation" / "REF-900.yaml").write_text(
        dump_entry(ref), encoding="utf-8"
    )
    for layer in (
        "constats_code_aster",
        "diagnostics",
        "patrons",
        "controles",
        "precedents",
    ):
        (root / "connaissances" / layer).mkdir(exist_ok=True)
    allowed, reason, _ = promotion_conditions(root, "REF-900")
    assert not allowed and "aucune promotion" in reason
