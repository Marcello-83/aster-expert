"""Harnais de niveau D par défaut (lot 46, étape 6)."""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from aster_expert.connaissances.base import load_knowledge
from aster_expert.connaissances.modeles import Control
from aster_expert.controles import harnais
from aster_expert.controles.equilibre import summarize
from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.declaration import DisabledControl
from aster_expert.projet.errors import ProjectError

_ROOT = Path(__file__).resolve().parents[2]
_PROJECTS = ("dalle_appuyee_01", "quai_cw_test_01")


def _paquet(project: str, name: str) -> dict[str, Any]:
    path = _ROOT / "projets" / project / "resultats" / "paquet" / "controles" / name
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _ctx(project: str) -> ProjectContext:
    return load_project(project, _ROOT)


def test_les_controles_par_defaut_sont_ceux_de_la_base() -> None:
    base = load_knowledge(_ROOT)
    flagged = {
        e.id
        for e in base.entries.values()
        if isinstance(e, Control) and e.default_harness
    }
    assert (
        flagged == set(harnais.PROMOTED_DEFAULTS) == {"CTL-005", "CTL-006", "CTL-012"}
    )
    for control_id in harnais.DEFAULT_CONTROLS:
        assert control_id in harnais._IMPLEMENTATIONS
        assert isinstance(base.entries[control_id], Control)
    # le contrôle générique n'est pas promu : il n'est pas dans le drapeau de la base
    generic = base.entries["CTL-013"]
    assert isinstance(generic, Control) and not generic.default_harness


@pytest.mark.parametrize("project", _PROJECTS)
def test_le_harnais_redonne_les_verdicts_d_du_paquet(project: str) -> None:
    """Relecture du paquet de résultats, sans exécution : le résultat d'équilibre
    versionné, passé au résumé du tronc commun, redonne exactement les verdicts D du
    paquet (équilibre, pesanteur, symétrie, verdict d'ensemble)."""
    ctx = _ctx(project)
    summary = summarize(ctx, _paquet(project, "equilibre.json"))
    reference = _paquet(project, "controles_d.json")
    for key in (
        "project",
        "level",
        "threshold",
        "equilibrium",
        "gravity",
        "symmetry",
        "informative",
        "verdict",
    ):
        assert summary[key] == reference[key], key
    controls = summary["harness"]["controls"]
    assert controls["CTL-005"]["verdict"] == "RÉUSSI"
    assert controls["CTL-006"]["verdict"] == "RÉUSSI"
    assert controls["CTL-013"]["verdict"] == "RÉUSSI"


def test_la_convergence_s_applique_a_la_dalle_seule() -> None:
    dalle = summarize(
        _ctx("dalle_appuyee_01"), _paquet("dalle_appuyee_01", "equilibre.json")
    )
    quai = summarize(
        _ctx("quai_cw_test_01"), _paquet("quai_cw_test_01", "equilibre.json")
    )
    ctl12 = dalle["harness"]["controls"]["CTL-012"]
    assert ctl12["verdict"] == "RÉUSSI"
    assert ctl12["worst_finest_error"] == pytest.approx(5.171300778781434e-4)
    assert all(ctl12["decreasing"].values()) and len(ctl12["decreasing"]) == 6
    assert quai["harness"]["controls"]["CTL-012"] == {
        "verdict": "NON APPLICABLE",
        "reason": "niveau E non visé par le projet",
    }


def test_niveau_e_vise_sans_serie_de_convergence_echoue_au_lieu_de_passer() -> None:
    ctx = _ctx("dalle_appuyee_01")
    controls = ctx.declaration.controls
    assert controls is not None
    declaration = ctx.declaration.model_copy(
        update={"controls": controls.model_copy(update={"convergence": None})}
    )
    summary = summarize(
        dataclasses.replace(ctx, declaration=declaration),
        _paquet("dalle_appuyee_01", "equilibre.json"),
    )
    ctl12 = summary["harness"]["controls"]["CTL-012"]
    assert ctl12["verdict"] == "ÉCHEC" and "niveau E visé" in ctl12["reason"]
    assert summary["verdict"] == "ÉCHEC"  # le verdict d'ensemble en tient compte


def test_resultante_differente_de_la_charge_declaree_echoue() -> None:
    ctx = _ctx("quai_cw_test_01")
    result = copy.deepcopy(_paquet("quai_cw_test_01", "equilibre.json"))
    term = result["cases"]["G"]["components"]["DZ"]
    term["applied_specified_n"] = term["applied_as_evaluated_n"] * 1.001
    out = harnais._resultant(ctx, result, {})
    assert out["verdict"] == "ÉCHEC"
    assert out["relative_gap_by_case"]["G"] > ctx.declaration.controls.threshold  # type: ignore[union-attr]
    assert summarize(ctx, result)["verdict"] == "ÉCHEC"


def test_convergence_verdict() -> None:
    bon = harnais.convergence_verdict({"w": [4e-3, 1e-3, 2.5e-4]}, 1e-2)
    assert bon["verdict"] == "RÉUSSI"
    assert (
        harnais.convergence_verdict({"w": [4e-3, 1e-3, 2e-3]}, 1e-2)["verdict"]
        == "ÉCHEC"
    )
    assert (
        harnais.convergence_verdict({"w": [4e-2, 2e-2, 1.5e-2]}, 1e-2)["verdict"]
        == "ÉCHEC"
    )
    assert harnais.convergence_verdict({"w": [1e-3]}, 1e-2)["verdict"] == "ÉCHEC"


def test_desactiver_un_controle_exige_un_motif_ecrit() -> None:
    with pytest.raises(ValueError, match="motif écrit"):
        DisabledControl(id="CTL-013", reason="inutile")
    ok = DisabledControl(
        id="CTL-013",
        reason="Charges réparties sans résultante déclarée : contrôle sans objet.",
    )
    assert ok.id == "CTL-013"


def test_un_controle_desactive_est_affiche_avec_son_motif_et_ne_compte_pas() -> None:
    ctx = _ctx("quai_cw_test_01")
    controls = ctx.declaration.controls
    assert controls is not None
    motif = "Résultante non déclarée pour ce cas : contrôle sans objet ici."
    declaration = ctx.declaration.model_copy(
        update={
            "controls": controls.model_copy(
                update={"disabled": (DisabledControl(id="CTL-013", reason=motif),)}
            )
        }
    )
    ctx2 = dataclasses.replace(ctx, declaration=declaration)
    result = copy.deepcopy(_paquet("quai_cw_test_01", "equilibre.json"))
    result["cases"]["G"]["components"]["DZ"]["applied_specified_n"] *= 1.01
    summary = summarize(ctx2, result)
    assert summary["harness"]["controls"]["CTL-013"] == {
        "verdict": "DÉSACTIVÉ",
        "reason": motif,
    }
    assert summary["harness"]["disabled"] == {"CTL-013": motif}
    assert summary["verdict"] == "RÉUSSI"  # un contrôle désactivé ne fait pas échouer


def test_desactiver_un_controle_inconnu_est_refuse() -> None:
    ctx = _ctx("quai_cw_test_01")
    controls = ctx.declaration.controls
    assert controls is not None
    declaration = ctx.declaration.model_copy(
        update={
            "controls": controls.model_copy(
                update={
                    "disabled": (
                        DisabledControl(
                            id="CTL-999", reason="Motif écrit en toutes lettres ici."
                        ),
                    )
                }
            )
        }
    )
    with pytest.raises(ProjectError, match="CTL-999"):
        harnais.disabled_controls(dataclasses.replace(ctx, declaration=declaration))
