"""Lot 39, step 1 bis: MM's decision D19 (point 14), as worded."""

from __future__ import annotations

from pathlib import Path

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.constats.base import load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[3]
_PROJECT = _ROOT / "projets" / "quai_cw_test_01"
_TOPIC = (
    "Position de l'axe des armatures longitudinales dans les calculs de section "
    "(poutre de couronnement)"
)


def _sheet() -> HypothesesSheet:
    return load_resolved_sheet(
        _PROJECT / "fiche" / "hypotheses_combiwall_reference_arbitree.json"
    )


def _d19() -> PracticeHypothesisEntry:
    found = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == "14"
        and e.topic == _TOPIC
    ]
    assert len(found) == 1
    return found[0]


def test_d19_is_recorded_as_worded() -> None:
    entry = _d19()
    assert entry.status == "tranche"
    assert entry.decided_by == "MM"
    assert entry.option_retained == (
        "Dans les calculs de section, la distance entre le parement et l'axe des "
        "armatures longitudinales est de 0,10 m sur toutes les faces. Ce sont les "
        "valeurs `C_SUP_*` et `C_INF_*` de `CALC_FERRAILLAGE`, ou ds et di du "
        "logiciel de MM. Le diamètre équivalent des armatures longitudinales est de "
        "40 mm."
    )
    assert entry.justification == (
        "L'enrobage nominal de 65 mm de D18 se mesure au nu de l'armature la plus "
        "proche du parement, c'est-à-dire l'étrier. L'axe des armatures "
        "longitudinales se trouve donc à environ 65 + diamètre de l'étrier + la "
        "moitié du diamètre longitudinal, soit environ 0,10 m. Le lot 38 avait pris "
        "0,065 m comme distance à l'axe, ce qui surestime le bras de levier."
    )
    assert entry.validity_domain == (
        "La valeur est forfaitaire ; elle sera à ajuster au ferraillage réellement "
        "retenu."
    )
    assert [(v.description, v.reason) for v in entry.discarded_variants] == [
        (
            "distance à l'axe égale à l'enrobage nominal, 0,065 m (lot 38).",
            "confond l'enrobage, mesuré au nu de l'étrier, avec la position de "
            "l'axe des barres longitudinales.",
        )
    ]
    assert entry.decided_at is not None
    assert entry.decided_at.isoformat() == "2026-09-28T05:45:12-04:00"


def test_d18_is_left_unchanged() -> None:
    d18 = [
        e
        for e in _sheet().entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == "14"
        and e.topic.startswith("Durabilité, enrobage")
    ]
    assert len(d18) == 1
    assert d18[0].option_retained is not None
    assert "Enrobage nominal de 65 mm." in d18[0].option_retained
    assert not d18[0].decision_history


def test_d19_values_in_model_data() -> None:
    values = load_model_data(_PROJECT / "donnees" / "combiwall_model_data.yaml").items()
    axis = values["durabilite.distance_parement_axe_armatures_longitudinales"]
    diameter = values["durabilite.diametre_equivalent_armatures_longitudinales"]
    assert (axis.value, axis.unit) == (0.10, "m")
    assert (diameter.value, diameter.unit) == (40, "mm")


def test_model_data_still_consistent_with_the_sheet() -> None:
    data = load_model_data(_PROJECT / "donnees" / "combiwall_model_data.yaml")
    assert (
        check_consistency(data, _sheet(), _PROJECT / "donnees" / "combiwall_inputs")
        == []
    )
