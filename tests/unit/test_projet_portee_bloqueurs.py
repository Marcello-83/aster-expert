"""Lot 48 bis (audit R6 et R8) : commandes prévues exigées par `projet verifier`, et
bloqueurs de révision limités aux étapes qui en dépendent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aster_expert.projet.context import load_project
from aster_expert.projet.errors import ProjectError
from aster_expert.projet.pipeline import Runtime, step_ferraillage, step_verifier

ROOT = Path(__file__).resolve().parents[2]
ES_POINT = ("14", "Module d'élasticité de l'acier de ferraillage (Es)")


def test_the_revision_of_es_blocks_only_the_reinforcement() -> None:
    ctx = load_project("quai_cw_test_01", ROOT)
    assert ctx.sheet().entries_under_revision()
    for step in ("verifier", "maillage", "generer", "valider", "executer"):
        assert ctx.blockers_for(step) == (), step
    blockers = ctx.blockers_for("ferraillage")
    assert len(blockers) == 1 and "(Es)" in blockers[0]
    # La levée de la dérogation rétablit le blocage de toutes les étapes.
    assert ctx.sheet().generation_blockers(ctx.data())


def test_verifier_passes_on_the_quai_and_names_the_waived_revision() -> None:
    ctx = load_project("quai_cw_test_01", ROOT)
    lines = step_verifier(ctx, Runtime(ROOT))
    assert any("non bloquante pour `verifier`" in line for line in lines)
    assert any("exemption déclarée" in line for line in lines)


def test_the_reinforcement_of_the_quai_stays_refused() -> None:
    ctx = load_project("quai_cw_test_01", ROOT)
    with pytest.raises(ProjectError, match="ferraillage refusé") as raised:
        step_ferraillage(ctx, Runtime(ROOT))
    assert any("(Es)" in p for p in raised.value.problems)


def test_only_a_revision_can_be_waived() -> None:
    ctx = load_project("quai_cw_test_01", ROOT)
    sheet = ctx.sheet()
    blockers = sheet.generation_blockers(ctx.data(), waived_revisions=[ES_POINT])
    assert blockers == ()
    # Un point inconnu ne neutralise rien.
    assert sheet.generation_blockers(ctx.data(), waived_revisions=[("99", "x")])


def test_the_quai_generator_waives_the_declared_revision(tmp_path: Path) -> None:
    from quai_cw_test_01.generation.errors import GenerationError
    from quai_cw_test_01.generation.generate import generate_comm

    ctx = load_project("quai_cw_test_01", ROOT)
    med = tmp_path / "faux.med"
    med.write_bytes(b"x")
    kwargs = {
        "fiche_path": ctx.fiche_path,
        "data_path": ctx.data_path,
        "med_path": med,
        "project_root": ROOT,
        "work_dir_root": "essai",
        "aster_version": "17.4.0",
    }
    with pytest.raises(GenerationError, match="ne sont pas prêtes"):
        generate_comm(**kwargs)  # type: ignore[arg-type]
    try:
        generate_comm(**kwargs, waived_revisions=ctx.waived_revisions("generer"))  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001 - le faux MED échoue plus loin
        assert "ne sont pas prêtes" not in str(exc)


def _without_planned(project: str, tmp_path: Path) -> Path:
    ctx = load_project(project, ROOT)
    raw = json.loads(ctx.fiche_path.read_text(encoding="utf-8"))
    raw.pop("planned_commands", None)
    out = tmp_path / "fiche.json"
    out.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return out


@pytest.mark.parametrize("project", ["dalle_appuyee_01", "estacade_pieux_01"])
def test_verifier_demands_planned_commands(project: str, tmp_path: Path) -> None:
    assert step_verifier(load_project(project, ROOT), Runtime(ROOT))
    ctx = load_project(project, ROOT, fiche=_without_planned(project, tmp_path))
    with pytest.raises(ProjectError, match="aucune commande prévue") as raised:
        step_verifier(ctx, Runtime(ROOT))
    assert any("fiche prevoir" in p for p in raised.value.problems)


@pytest.mark.skipif(
    not (ROOT / "data" / "processed" / "catalogue").is_dir(),
    reason="catalogue extrait absent (aster-expert catalogue extract)",
)
def test_the_planned_commands_match_the_comm_of_each_project() -> None:
    """Les commandes déclarées sont celles du `.comm` (dérivation rejouée)."""
    from aster_expert.agent.prevues import derive_planned_commands

    cas = {
        "dalle_appuyee_01": "references/cas/dalle_h0p125.comm",
        "estacade_pieux_01": "references/cas/estacade_pieux_01.comm",
    }
    for project, comm in cas.items():
        ctx = load_project(project, ROOT)
        derived, _ = derive_planned_commands(ctx.fiche_path, ctx.path(comm), ROOT)
        declared = ctx.sheet().planned_commands
        key = lambda p: (p.command, p.point_label, sorted(p.options.items()))  # noqa: E731
        assert sorted(map(key, derived)) == sorted(map(key, declared)), project


def test_a_keyword_with_an_unknown_condition_is_reported_not_swallowed() -> None:
    from aster_expert.agent.obligatoires import UninterpretedConditionError, _holds

    with pytest.raises(UninterpretedConditionError):
        _holds('is_type("RESULTAT") in (evol_noli,)', {})


def test_planned_from_comm_keeps_only_catalogue_options() -> None:
    from aster_expert.agent.obligatoires import planned_from_comm
    from aster_expert.parsing.comm_parser import parse_comm_source

    # Sans schéma pour DEBUT, avec un schéma factice pour le reste : pas de catalogue.
    analysis = parse_comm_source(
        'DEBUT()\nR = MACRO_ELAS_MULT(METHODE="MUMPS")\n', file_path="t.comm"
    )
    planned, skipped = planned_from_comm(
        analysis,
        lambda _c: None,
        lambda _c: "0",
        rules=None,  # type: ignore[arg-type]
    )
    assert planned == () and skipped == ("DEBUT", "MACRO_ELAS_MULT")
