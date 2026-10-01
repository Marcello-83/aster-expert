"""Lot 37, étape 2 : décisions 14, 15 et 16 de MM enregistrées telles qu'énoncées
dans la fiche de référence, et identifiant de la poutre de Timoshenko."""

from __future__ import annotations

from pathlib import Path

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.constats.base import load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[3]
_FICHE = (
    _ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)

_D15 = (
    "Les contrôles du lot 35 montrent que, sous les cas G, EAU_P, EAU_A et Q1, la "
    "pression de réaction des ressorts dépasse la butée limite sur une large part "
    "de la fiche. Sous Q3 et A, elle reste inférieure à 10 % de la butée limite. "
    "Le modèle linéaire est donc représentatif pour les effets des charges "
    "localisées (Q3, A), qui sont son objet (décision 0). Les efforts sous charges "
    "de terre et d'eau sont à prendre dans le calcul géotechnique amont."
)
_D16 = (
    "La poussée est appliquée sur la seule moitié terre des tubes, et les ressorts "
    "sur la seule moitié bassin. La section du tube s'ovalise donc artificiellement, "
    "jusqu'à 3,5 mm d'écart entre génératrices en pied sous G. Les efforts "
    "circonférentiels (NYY, MYY) des tubes ne sont pas exploitables pour le "
    "dimensionnement. Seuls les efforts de flexion d'ensemble du tube, obtenus par "
    "intégration de NXX sur la section, le sont."
)


def _sheet() -> HypothesesSheet:
    return load_resolved_sheet(_FICHE)


def _decided(prefix: str) -> PracticeHypothesisEntry:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.decided_at is not None
        and e.topic.startswith(prefix)
    ]
    assert len(found) == 1
    return found[0]


def test_decision_14_is_recorded_as_worded_and_kept_in_the_history() -> None:
    """Lot 38: D14 bis replaces D14 (`test_lot38_decisions.py`); D14, as worded at
    lot 37, is now the last `decision_history` item, the lot 32 decision before it."""
    entry = _decided("Choix entre maillage coïncident")
    assert len(entry.decision_history) == 2
    d14 = entry.decision_history[-1]
    assert d14.option_retained == (
        "La poutre de couronnement reste représentée par un élément de poutre sur "
        "son axe, mais avec la formulation qui prend en compte la déformation "
        "d'effort tranchant. L'identifiant de modélisation est à établir par la "
        "documentation et le catalogue."
    )
    assert d14.validity_domain == (
        "La poutre sur son axe ne représente pas les effets locaux : zone "
        "d'encastrement des tubes, ancrage du bollard, diffusion sous platine. Ces "
        "effets relèvent de vérifications locales séparées."
    )
    assert [v.description for v in d14.discarded_variants] == [
        "poutre en coques ou en éléments volumiques",
        "élément d'Euler-Bernoulli (état actuel)",
    ]
    assert "Maillage coïncident" in entry.decision_history[0].option_retained


def test_decisions_15_and_16_append_to_the_validity_domain_only() -> None:
    for prefix, addition in (
        ("Phasage construction/excavation", _D15),
        ("Choix entre contact surfacique", _D16),
    ):
        entry = _decided(prefix)
        previous = entry.decision_history[-1]
        assert entry.validity_domain == f"{previous.validity_domain}\n\n{addition}"
        assert entry.option_retained == previous.option_retained
        assert entry.justification == previous.justification
        assert entry.decided_at is not None
        assert entry.decided_at.date().isoformat() == "2026-09-25"


def test_timoshenko_beam_identifier_is_established_by_a_sourced_finding() -> None:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.topic.startswith("Identifiant de la modélisation de poutre")
    ]
    assert len(found) == 1
    assert found[0].option_retained is not None
    assert found[0].option_retained.startswith("POU_D_T.")
    # deux extraits documentaires (U3.11.01, U4.42.01) et deux références de catalogue
    assert len(found[0].sources) == 4
