"""Lot 45, étape 1 : D20 et D21 au texte de MM, décision Es en attente d'application."""

from __future__ import annotations

from pathlib import Path

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.constats.base import load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[3]
_PROJECT = _ROOT / "projets" / "quai_cw_test_01"
_D20 = (
    "Coefficients partiels des matériaux en situation accidentelle (ELU accidentelle)"
)
_D21 = (
    "Maîtrise de la fissuration de la poutre de couronnement (section minimale, "
    "contrainte de l'acier)"
)
_ES = "Module d'élasticité de l'acier de ferraillage (Es)"


def _sheet() -> HypothesesSheet:
    return load_resolved_sheet(
        _PROJECT / "fiche" / "hypotheses_combiwall_reference_arbitree.json"
    )


def _entry(topic: str) -> PracticeHypothesisEntry:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry) and e.topic == topic
    ]
    assert len(found) == 1
    return found[0]


def test_d20_carries_the_text_of_the_decision() -> None:
    entry = _entry(_D20)
    assert entry.option_retained == "ELU accidentelle, γc = 1,2 et γs = 1,0."
    assert entry.validity_domain == "Combinaison ELU accidentelle uniquement."
    assert entry.discarded_variants[0].description.startswith("Conserver γc = 1,5")
    (prior,) = entry.decision_history
    assert "Situation accidentelle" in prior.option_retained


def test_d21_is_the_literal_reading_of_7_3_2_not_the_lot_44_wording() -> None:
    entry = _entry(_D21)
    option = entry.option_retained or ""
    assert "soit b·h/2 en flexion" in option
    assert "0,65 pour h ≥ 800 mm" in option
    assert "b·h, l'élément étant tendu" not in option
    domain = entry.validity_domain or ""
    assert "68 cm²" in domain
    assert "91 cm²" in domain
    assert "bornée à 160 MPa" in domain
    assert "hc,eff" in entry.discarded_variants[0].description
    assert {s.origin for s in entry.sources} == {"decision_ingenieur", "norme"}
    (prior,) = entry.decision_history
    assert "flexion simple" in prior.validity_domain


def test_es_is_decided_and_blocks_generation_until_the_quai_is_recomputed() -> None:
    entry = _entry(_ES)
    assert entry.status == "tranche"
    # Lot 46 : texte de MM (consigne, décision 1), qui remplace celui du lot 45.
    assert entry.option_retained == (
        "Module d'élasticité des armatures de béton armé, Es = 200 GPa, pour tous les "
        "projets."
    )
    assert "EN 1992-1-1, 3.2.7(4)" in (entry.justification or "")
    assert "EN 1993-1-1, 3.2.6" in (entry.justification or "")
    assert "Hors domaine : acier de construction" in (entry.validity_domain or "")
    assert [v.description for v in entry.discarded_variants] == [
        "Es = 210 GPa pour les armatures."
    ]
    assert entry.discarded_variants[0].reason == (
        "Valeur de l'EN 1993, non conforme à l'EN 1992-1-1."
    )
    (prior,) = entry.decision_history  # le texte du lot 45 est conservé
    assert "210 GPa" in (prior.option_retained or "")
    assert entry.under_revision
    sheet = _sheet()
    assert any(_ES in b for b in sheet.generation_blockers())
    assert sheet.is_ready_for_generation is False
