"""Lot 38, step 1: D14 bis, D17 and D18 of MM's arbitration v6, as worded."""

from __future__ import annotations

from pathlib import Path

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.constats.base import load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[3]
_PROJECT = _ROOT / "projets" / "quai_cw_test_01"
_INPUTS = _PROJECT / "donnees" / "combiwall_inputs"
_SHARED = Path("/media/sf_partage/echanges/arbitrage_combiwall_MM_v6.md")


def _sheet() -> HypothesesSheet:
    return load_resolved_sheet(
        _PROJECT / "fiche" / "hypotheses_combiwall_reference_arbitree.json"
    )


def _practice(point: str, prefix: str) -> PracticeHypothesisEntry:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == point
        and e.topic.startswith(prefix)
    ]
    assert len(found) == 1
    return found[0]


def test_arbitration_v6_is_copied_verbatim() -> None:
    if _SHARED.is_file():
        assert (
            _SHARED.read_bytes()
            == (_INPUTS / "arbitrage_combiwall_MM_v6.md").read_bytes()
        )


def test_decision_14_bis_replaces_14_and_keeps_the_history() -> None:
    entry = _practice("3", "Choix entre maillage coïncident")
    assert entry.option_retained is not None
    assert entry.option_retained.startswith(
        "Maillage coïncident, généré par la chaîne."
    )
    assert "poutre de Timoshenko" in entry.option_retained
    assert "un seul nœud" in entry.option_retained
    assert entry.justification is not None
    assert "2,50 m" in entry.justification
    assert entry.validity_domain is not None
    assert "plus raide que l'encastrement réel sur 0,80 m" in entry.validity_domain
    assert [v.description for v in entry.discarded_variants] == [
        "Raccord par méthode variationnelle entre maillages non coïncidents.",
        "Poutre en coques ou en éléments volumiques.",
        "Élément de poutre d'Euler-Bernoulli.",
    ]
    assert entry.decided_by == "MM"
    assert len(entry.decision_history) == 2
    assert entry.decision_history[-1].option_retained.startswith(
        "La poutre de couronnement reste représentée"
    )


def test_decision_17_opens_point_13_with_the_dictated_variants() -> None:
    entry = _practice("13", "Combinaisons d'actions ELU et ELS")
    assert entry.status == "tranche"
    assert entry.decided_by == "MM"
    assert entry.option_retained is not None
    assert "γG = 1,35 (défavorable) ou 1,00 (favorable)" in entry.option_retained
    assert "ELS quasi permanente" in entry.option_retained
    assert entry.validity_domain is not None
    assert "ne sont pas des efforts de dimensionnement des tubes" in (
        entry.validity_domain
    )
    assert [v.description for v in entry.discarded_variants] == [
        "Amarrage (Q3) et accostage (A) simultanés.",
        "Pression d'eau permanente (EAU_P) traitée comme action variable.",
        "Accostage traité comme action variable en combinaison fondamentale "
        "(γQ = 1,5).",
        "Coefficients γG distincts pour G et pour EAU_P.",
    ]
    assert entry.sources[0].reference.endswith("arbitrage v6 en séance de travail")


def test_decision_18_opens_point_14_with_the_dictated_variants() -> None:
    entry = _practice("14", "Durabilité, enrobage")
    assert entry.option_retained is not None
    assert "Enrobage nominal de 65 mm." in entry.option_retained
    assert "wk = 0,2 mm" in entry.option_retained
    assert len(entry.discarded_variants) == 3
    assert entry.discarded_variants[0].reason.startswith(
        "Valeur recommandée de l'EN 1992-1-1 (tableau 7.1N)"
    )


def test_lot38_data_values_match_their_decision_text() -> None:
    data = load_model_data(_PROJECT / "donnees" / "combiwall_model_data.yaml")
    values = data.items()
    assert values["combinaisons.gamma_g_defavorable"].value == 1.35
    assert values["combinaisons.q3_psi2"].value == 0
    assert values["durabilite.enrobage_nominal"].value == 65
    assert values["durabilite.ouverture_fissure_limite_wk"].value == 0.2
    assert values["durabilite.classe_exposition"].value == "XS3"
    assert check_consistency(data, _sheet(), _INPUTS) == []


def test_pou_d_t_symmetry_finding_is_sourced() -> None:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.point_label == "7"
        and "POU_D_T" in e.topic
    ]
    assert len(found) == 1
    (finding,) = found
    assert finding.option_retained is not None
    assert "DX=0.0, DRY=0.0, DRZ=0.0" in finding.option_retained
    assert "GRX" in finding.option_retained
    kinds = {type(s).__name__ for s in finding.sources}
    assert kinds == {"DocumentarySource", "CatalogueSource"}
