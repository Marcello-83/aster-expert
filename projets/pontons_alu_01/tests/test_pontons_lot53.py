"""Tests of lot 53 for PONTONS-ALU-01: output points (pin point carried by a node,
deck − cap beam difference, centre of a footing by interpolation), events and their
linearity, envelopes « total », « hors T », « variables seules » against the explicit
enumeration, labels without the excluded actions, the versioned listing of the lot,
the delivery plan. No Docker, no Salome."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51quater import (
    branches,
    events_p60_p61,
    magnitudes_p60,
)
from pontons_alu_01.combinaisons_lot51ter import Event, brute_force
from pontons_alu_01.deplacements_lot53 import (
    EXCLUDED_CASES,
    STATES,
    SYNTHESIS_COLUMNS,
    VARIANTS,
    OutPoint,
    Quantity,
    Term,
    _strip,
    combined_extremes,
    event_value,
    footing_centre_terms,
    point_value,
)
from pontons_alu_01.generation_lot51ter import all_cases, zone_names
from pontons_alu_01.generation_lot52 import geometry_of
from pontons_alu_01.variantes_lot52 import variants
from pontons_alu_01.vues_lot53 import amplification

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"
LISTING = PROJECT / "references" / "post_traitement_lot53"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


@pytest.fixture(scope="module")
def rules(ctx: ProjectContext) -> SimpleNamespace:
    g = geometry_of(variants()["B52"])
    data = {k: item.value for k, item in ctx.data().items().items()}
    ev = events_p60_p61(
        magnitudes_p60(data, 50.0),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )
    return SimpleNamespace(ev=ev, bs=branches(ev), cases=all_cases(g))


def _point(kind: str, terms: tuple[Term, ...]) -> OutPoint:
    return OutPoint("p", kind, "P1", "YM", 0.0, 0.0, 0.0, terms)


def test_pin_point_carried_by_a_node() -> None:
    coords = np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 2.0]])
    depl = {
        1: np.array([1e-3, 2e-3, 3e-3, 1e-2, 0.0, 0.0]),
        2: np.array([1e-3, 1e-3, 3e-3, 0.0, 0.0, 0.0]),
    }
    pin = (1.0, 2.0, 2.5)
    # u + θ ∧ (P − N) : θ = 0,01 rad autour de X, P − N = (0, 0, −0,5) → ΔY = +0,005.
    axe = point_value(_point("axe", (Term(1, 1.0, pin),)), depl, coords)
    assert np.allclose(axe[:3], [1e-3, 2e-3 + 5e-3, 3e-3])
    assert np.allclose(axe[3:], [1e-2, 0.0, 0.0])
    rel = point_value(
        _point("relatif", (Term(1, 1.0, pin), Term(2, -1.0, pin))), depl, coords
    )
    assert np.allclose(rel[:3], [0.0, 6e-3, 0.0])


def test_footing_centre_is_the_mean_of_two_symmetric_nodes() -> None:
    coords = np.array(
        [[0.0, 0.0, -1.0], [1.0, 0.0, -1.0], [2.0, 0.0, -1.0], [1.0, 0.5, -1.0]]
    )
    footing = SimpleNamespace(pier="P1", centre=(1.0, 0.0, -1.0))
    vd: Any = SimpleNamespace(
        g=SimpleNamespace(footings=[footing]),
        model=SimpleNamespace(coords=coords, group_nodes={"SEMELLE_P1": [1, 3, 4]}),
    )
    terms = footing_centre_terms(vd, "P1")
    assert [(t.node, t.weight) for t in terms] == [(1, 0.5), (3, 0.5)]
    vd.model.group_nodes["SEMELLE_P1"] = [1, 2, 3]
    assert [(t.node, t.weight) for t in footing_centre_terms(vd, "P1")] == [(2, 1.0)]
    vd.model.coords = np.array([[0.0, 0.0, -1.0], [2.5, 0.0, -1.0], [1.0, 0.5, -1.0]])
    vd.model.group_nodes["SEMELLE_P1"] = [1, 2]
    with pytest.raises(ValueError, match="non symétriques"):
        footing_centre_terms(vd, "P1")


def test_event_value_is_linear_and_refuses_modules() -> None:
    unit = {"A": np.ones((2, 6)), "B": 2.0 * np.ones((2, 6))}
    ev = Event("E", "AC", {"A": 3.0, "B": -1.0})
    assert np.allclose(event_value(ev, unit), 1.0)
    with pytest.raises(ValueError, match="modules"):
        event_value(Event("Q", "Q", {}, (("M0", {"A": 1.0}),)), unit)


def test_label_omits_the_excluded_actions(rules: SimpleNamespace) -> None:
    label = "ELS_caracteristique: G_DEJ_100×1 + TP×1 + AM1_+X×0.77 + Q[M0+M1]×0.77"
    assert _strip(label, rules.ev, ("G",)) == (
        "ELS_caracteristique: TP×1 + AM1_+X×0.77 + Q[M0+M1]×0.77"
    )
    assert _strip(label, rules.ev, ("G", "T")) == (
        "ELS_caracteristique: AM1_+X×0.77 + Q[M0+M1]×0.77"
    )
    assert _strip("ELU_accidentel: G×1 + TM×0.5", rules.ev, ("G", "T")).endswith(
        "aucune action"
    )


def test_envelopes_against_explicit_enumeration(rules: SimpleNamespace) -> None:
    """Small integer unit values (the enumeration stays small after np.unique): every
    state and variant of the lot, max and min, against brute_force."""
    rng = random.Random(53)
    f = {c: np.array([float(rng.randint(-3, 3))]) for c in rules.cases}
    vd: Any = SimpleNamespace(bs=rules.bs, ev=rules.ev)
    combos = combined_extremes(vd, f, [Quantity(0, 0)])
    for state in STATES:
        for variant, without in VARIANTS:
            excluded = {c for a in without for c in EXCLUDED_CASES[a]}
            values = {c: (0.0 if c in excluded else float(a[0])) for c, a in f.items()}
            hi, lo = combos[(state, variant)][0]
            for sign, got in ((1.0, hi), (-1.0, lo)):
                found = [
                    brute_force(b, rules.ev, values, sign)
                    for b in rules.bs
                    if b.state == state
                ]
                best = max(found) if sign > 0 else min(found)
                assert got.value == pytest.approx(best * 1e3, abs=1e-9)
                again = sum(c * f[k][0] for k, c in got.coefficients.items()) * 1e3
                assert again == pytest.approx(got.value, abs=1e-9)
                assert not excluded & set(got.coefficients)


def test_amplification_is_round_and_bounded() -> None:
    assert amplification(0.0569, 0.9) == 10
    assert amplification(0.0317, 1.2) == 25
    assert amplification(10.0, 0.9) == 1


def test_versioned_listing_of_lot_53() -> None:
    summary = json.loads((LISTING / "synthese_lot53.json").read_text("utf-8"))
    for key in (
        "controle_empreintes",
        "controle_relecture",
        "controle_TP_P5",
        "controle_liaisons",
        "controle_enumeration",
        "controle_champs_points",
        "controle_med",
        "controle_vues",
    ):
        assert summary[key]["reussi"] is True, key
    assert summary["controle_linearite_lecteur_independant"]["code"] == 0
    assert summary["points"] == 99
    assert summary["evenements"] == {"AC": 168, "ACA": 168, "AM": 64, "AMF": 60}
    assert summary["controle_med"]["relecture"]["champs_source"] == 18
    assert len(summary["controle_med"]["relecture"]["champs"]) == 38
    assert summary["controle_empreintes"]["comm_execution"].startswith("bd8663c6")
    with (LISTING / "deplacements_synthese.csv").open(encoding="utf-8") as stream:
        next(stream)
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert [r["palee"] for r in rows] == ["P1", "P2", "P3", "P4", "P5"]
    assert list(rows[0]) == SYNTHESIS_COLUMNS
    assert all(abs(float(r["jeu_Y_relatif_YP_max_controle"])) < 1e-9 for r in rows)


def test_delivery_plan_has_new_names_only(ctx: ProjectContext) -> None:
    from pontons_alu_01.depot_lot53 import delivery_plan  # noqa: PLC0415

    if not (ctx.results_dir / "lot53" / "exports").is_dir():
        pytest.skip("résultats du lot 53 absents (dépôt non versionné)")
    plan = delivery_plan(ctx)
    lot52 = ctx.results_dir / "lot52" / "exports" / "B52"
    old = {p.name for p in lot52.iterdir()} | {"resultats.med", "charges.med"}
    assert not old & {Path(n).name for n in plan}
    assert "B52/MED/resultats_deplacements_lot53.med" in plan
