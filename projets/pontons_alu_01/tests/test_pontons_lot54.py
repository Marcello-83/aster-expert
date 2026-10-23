"""Tests of lot 54 for PONTONS-ALU-01: the final PRO geometry (P67: regular truss, posts
at Xd + k × 1,25; P68: cap beams 0,60 × 0,40 from Y = −1,20 to +1,20), its invariants,
the generated `.comm`, the houle of P69, the rule P70 (forbidden pairs, joint
maximisation of two slots, counts, delivered recombiner), the decisions P67 to P76 in
the fiche, the declaration of the project. No Docker, no Salome."""

from __future__ import annotations

import importlib.util
import itertools
import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51ter import (
    Branch,
    Event,
    Exclusion,
    Slot,
    brute_force,
    counts,
    enumerate_branch,
    envelope,
    expanded_counts,
    governing,
    joint_best,
    rule_rows,
)
from pontons_alu_01.combinaisons_lot51ter import branches as branches_51ter
from pontons_alu_01.combinaisons_lot54 import (
    POST_HALF_WIDTH,
    branches_p70,
    check_rules,
    events_p69,
    expected_centres,
    forbidden_pairs,
    incompatibilities,
    magnitudes_p69,
    with_exclusions,
    zone_centres,
)
from pontons_alu_01.exports_lot52 import node_geometry, node_summary
from pontons_alu_01.exports_lot54 import incompatibility_rows
from pontons_alu_01.generation_lot51ter import (
    all_cases,
    applied_loads,
    concrete_volumes_by_pier,
    weights,
    zone_names,
)
from pontons_alu_01.generation_lot54 import build_comm, geometry_of, values
from pontons_alu_01.geometrie_lot51ter import expected_counts, read_parameters
from pontons_alu_01.geometrie_lot54 import OVERRIDABLE, SCRIPT, diagonal_lengths
from pontons_alu_01.invariants_lot52 import invariants
from pontons_alu_01.invariants_lot54 import VERSIONED
from pontons_alu_01.variantes_lot54 import variants

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


@pytest.fixture(scope="module")
def ev(ctx: ProjectContext) -> dict[str, Event]:
    g = geometry_of(variants()["B54"])
    data = {k: i.value for k, i in ctx.data().items().items()}
    return events_p69(
        magnitudes_p69(data),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )


# --------------------------------------------------------------------------- geometry


def test_two_variants_as_in_the_consigne() -> None:
    vs = variants()
    assert list(vs) == ["B54", "A54"]
    for v in vs.values():
        assert (v.beam_side_mm, v.beam_thickness_mm) == (200, 12)
        assert (v.purlin_side_mm, v.purlin_thickness_mm) == (50, 5)
        assert (v.post_side_mm, v.post_thickness_mm) == (120, 6)
        assert v.inner_posts == (1.25, 2.5, 3.75, 5.0)
        assert v.cap_width == 0.6 and v.cap_ends == (-1.2, 1.2)
    assert vs["B54"].geometry == "B" and vs["A54"].geometry == "A"
    assert vs["B54"].mesh_overrides["X_MONTANTS"] == [1.25, 2.5, 3.75, 5.0]


def test_regular_truss_of_p67() -> None:
    for v in variants().values():
        g = geometry_of(v)
        for s in g.spans:
            if s.nature != "grande":
                continue
            xs = sorted(
                {m.points[0][0] for m in g.family("MONTANTS") if m.span == s.name}
            )
            assert [round(x - s.x0, 6) for x in xs] == [0, 1.25, 2.5, 3.75, 5.0, 6.25]
        lengths = diagonal_lengths(g)
        assert len(lengths) == 25
        assert max(lengths.values()) - min(lengths.values()) < 1e-9
        assert math.isclose(min(lengths.values()), math.hypot(1.25, 1.36))
        assert [x for _, x, _ in g.cleats][:2] == [1.6, 4.6]


def test_cap_beams_of_p68() -> None:
    g = geometry_of(variants()["B54"])
    for m in g.family("CHEVETRES"):
        assert (m.points[0][1], m.points[-1][1]) == (-1.2, 1.2), m.name
    corners = {round(c[1][0] - c[0][0], 6) for c in g.corners}
    assert corners == {0.299}  # nu à xc1 + 0,30, longrine depuis xc1 + JEU
    assert {round(a.cap[1], 6) for a in g.axes if a.cap is not None} == {-0.93, 0.93}


def test_lot_52_defaults_are_unchanged() -> None:
    p = read_parameters(SCRIPT, None, OVERRIDABLE)
    assert p["X_MONTANTS"] == (0.75, 2.25, 3.75, 5.25)
    assert p["B_CHEVETRE"] == p["B_ANNEAU"] == 0.4
    assert p["Y_CHEVETRE"] == (-1.05, 1.05)


def test_versioned_invariants_are_those_of_b54() -> None:
    versioned = yaml.safe_load(VERSIONED.read_text("utf-8"))
    assert versioned == invariants(geometry_of(variants()["B54"]))
    for v in variants().values():
        assert set(expected_counts(geometry_of(v))) == {"nodes", "SEG2", "QUAD4"}


def test_node_geometry_has_no_overlap() -> None:
    for v in variants().values():
        s = node_summary(node_geometry(v, geometry_of(v)))
        assert s["reussi"], s


# --------------------------------------------------------------------------- .comm


def test_generated_comm_of_lot_54(ctx: ProjectContext) -> None:
    for v in variants().values():
        text_, report = build_comm(ctx, mesh_label="maillage_ponton_52.med", variant=v)
        assert "lot 54" in text_.splitlines()[0]
        assert (
            '_F(GROUP_MA="CHEVETRES", SECTION="RECTANGLE", CARA=("HY", "HZ"), '
            "VALE=(0.6, 0.4))," in text_
        )
        assert (
            '_F(GROUP_MA="LONGRINES", SECTION="RECTANGLE", CARA=("HY", "HZ"), '
            "VALE=(0.4, 0.4))," in text_
        )
        assert '_F(GROUP_MA="CHEVETRES", FZ=2400.0),' in text_
        assert report["cap_width_m"] == 0.6
        assert values(ctx, v).cap_width == 0.6


def test_cap_beam_self_weight_is_14_4_kn(ctx: ProjectContext) -> None:
    v = variants()["B54"]
    g = geometry_of(v)
    vals = values(ctx, v)
    assert math.isclose(weights(vals, g)["CHEVETRES"], 10 * 14.4e3, rel_tol=1e-12)
    vol = concrete_volumes_by_pier(vals, g)["P1"]
    assert math.isclose(vol["CHEVETRES"], 2 * 0.6 * 0.4 * 2.4, rel_tol=1e-12)
    # longrines : 1,52 − 2 × 0,30 entre les nus, deux longrines par palée
    assert math.isclose(vol["LONGRINES"], 2 * 0.4 * 0.4 * (1.52 - 0.6), rel_tol=1e-9)


def test_projet_yaml_points_to_lot_54(ctx: ProjectContext) -> None:
    decl = ctx.declaration
    assert decl.mesh is not None and decl.comm is not None
    assert str(decl.mesh.invariants).endswith("invariants_ponton_54.yaml")
    assert "extensions_lot54" in str(decl.comm.generator)
    assert decl.controls is not None
    assert [c.name for c in decl.controls.cases] == all_cases(
        geometry_of(variants()["B54"])
    )


# --------------------------------------------------------------------------- P69


def test_houle_of_p69(ev: dict[str, Event]) -> None:
    assert ev["HU"].coefficients == {
        "HU_TUBES": 5.0,
        "HU_PANNES": 5.0,
        "HU_PLATELAGE": 5.0,
    }
    assert ev["HD"].coefficients == {"HD_TABLIER": 5.0}
    assert ev["HU_F"].coefficients == {
        "HU_TUBES": 2.728,
        "HU_PANNES": 2.516,
        "HU_PLATELAGE": 2.425,
    }
    assert not [n for n in ev if n.startswith("HU_IMP")]


def test_houle_resultant_formula(ctx: ProjectContext, ev: dict[str, Event]) -> None:
    v = variants()["B54"]
    g = geometry_of(v)
    loads = applied_loads(values(ctx, v), g)
    length = sum(s.x1 - s.x0 for s in g.spans)
    hu = sum(c * loads[k]["DZ"] for k, c in ev["HU"].coefficients.items())
    assert math.isclose(hu, 5.0 * (0.40 + 0.20 + 1.327) * length * 1e3, rel_tol=1e-9)


# --------------------------------------------------------------------------- P70


def test_forbidden_pairs_of_p70(ctx: ProjectContext, ev: dict[str, Event]) -> None:
    g = geometry_of(variants()["B54"])
    items = incompatibilities(ev, g)
    assert len(items) == 1920
    assert all(i.distance < POST_HALF_WIDTH for i in items)
    triplets = {(i.cleat, i.side, i.zone) for i in items}
    assert len(triplets) == 40
    # Taquet 1 (Xd + 1,6 de T1) : zones T1D (1,1 m) et T1M (1,525 m) interdites, T1F non
    assert {z for c, s, z in triplets if c == 1 and s == "YM"} == {"T1D", "T1M"}
    assert not any(
        i.mooring.startswith("AM1") or i.mooring.startswith("AM2") for i in items
    )
    centres, expected = zone_centres(g), expected_centres(g)
    assert max(abs(centres[z] - expected[z]) for z in centres) < 1e-9
    assert len(incompatibility_rows(items)) == 1920


def test_branches_of_p70_and_counts(ev: dict[str, Event]) -> None:
    g = geometry_of(variants()["B54"])
    bs = branches_p70(ev, g)
    assert not check_rules(bs, ev)
    assert sum(1 for b in bs if b.exclusions) == 14
    assert sum(counts(branches_51ter(ev)).values()) == 2351600
    assert sum(counts(bs).values()) == 2247920
    free = with_exclusions(bs, set())
    assert counts(free) == counts(branches_51ter(ev))
    assert expanded_counts(free, ev) == expanded_counts(branches_51ter(ev), ev)


def _toy() -> tuple[dict[str, Event], Branch]:
    ev = {
        "A1": Event("A1", "AM", {"c1": 1.0}),
        "A2": Event("A2", "AM", {"c2": 1.0}),
        "B1": Event("B1", "AC", {"c1": -1.0, "c3": 1.0}),
        "B2": Event("B2", "AC", {"c2": 1.0}),
        "B3": Event("B3", "AC", {"c3": 2.0}),
        "Q": Event("Q", "Q", {}, (("M0", {"q0": 1.0}), ("M1", {"q1": 1.0}))),
    }
    slots = (
        Slot("AM", ((None, 0.0), ("A1", 1.5), ("A2", 1.5))),
        Slot("AC", (("B1", 1.0), ("B2", 1.0), ("B3", 1.0))),
        Slot("Q", ((None, 0.0), ("Q", 1.3))),
    )
    pairs = frozenset({(1, 0), (1, 2), (2, 1)})
    return ev, Branch("ELU_fondamental", "jouet", slots, (Exclusion(0, 1, pairs),))


def test_joint_envelope_equals_enumeration() -> None:
    ev, b = _toy()
    rng = np.random.default_rng(54)
    cases = ("c1", "c2", "c3", "q0", "q1")
    f = {c: rng.normal(size=200) for c in cases}
    for sign in (1.0, -1.0):
        ext = envelope([b], ev, f, "ELU_fondamental", sign=sign)
        for q in range(200):
            vals = {c: float(f[c][q]) for c in cases}
            ref = brute_force(b, ev, vals, sign)
            assert math.isclose(float(ext.value[q]), ref, rel_tol=1e-12, abs_tol=1e-12)
            name, coefs = governing([b], ev, ext, q)
            assert "A1×1.5 + B1" not in name and "A1×1.5 + B3" not in name
            assert "A2×1.5 + B2" not in name
            assert math.isclose(
                sum(c * vals[k] for k, c in coefs.items()), ref, abs_tol=1e-12
            )


def test_joint_best_against_loops() -> None:
    rng = np.random.default_rng(7)
    a = rng.normal(size=(6, 50))
    c = rng.normal(size=(9, 50))
    pairs = frozenset({(0, 0), (0, 1), (2, 3), (2, 4), (2, 5), (5, 8)})
    value, ja, jb = joint_best(a, c, Exclusion(0, 1, pairs))
    for q in range(50):
        best = max(
            a[i, q] + c[j, q] for i in range(6) for j in range(9) if (i, j) not in pairs
        )
        assert value[q] == best
        assert (int(ja[q]), int(jb[q])) not in pairs
        assert a[ja[q], q] + c[jb[q], q] == best


def test_counts_and_enumeration_with_exclusion() -> None:
    ev, b = _toy()
    combos = list(enumerate_branch(b, ev))
    assert b.count == 3 * 3 * 2 - 3 * 2
    assert len(combos) == b.expanded_count(ev) == (3 * 3 - 3) * (1 + 3)
    for name, _ in combos:
        assert not ("A1" in name and ("B1" in name or "B3" in name))
        assert not ("A2" in name and "B2" in name)


def _delivered(tmp: Path, ev: dict[str, Event], b: Branch) -> Any:
    """The toy written as the export files, read by the delivered recombiner."""
    from pontons_alu_01.combinaisons_lot51ter import event_rows  # noqa: PLC0415
    from pontons_alu_01.exports_lot51 import write  # noqa: PLC0415

    write(
        tmp / "combinaisons.csv",
        "jouet",
        [
            "etat_limite",
            "branche",
            "emplacement",
            "action",
            "nombre_options",
            "effectif_branche",
            "effectif_dispositions",
            "options",
        ],
        rule_rows([b], ev),
    )
    write(
        tmp / "evenements.csv",
        "jouet",
        ["action", "evenement", "portee", "cas", "coefficient"],
        event_rows(ev),
    )
    write(
        tmp / "incompatibilites.csv",
        "jouet",
        ["evenement_amarrage", "evenement_accostage"],
        [["A1", "B1"], ["A1", "B3"], ["A2", "B2"]],
    )
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot54", PROJECT / "scripts" / "recombiner_lot54.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    return rec


def test_delivered_recombiner_applies_p70(tmp_path: Path) -> None:
    ev, b = _toy()
    rec = _delivered(tmp_path, ev, b)
    rules = rec.read_rules(tmp_path)
    events_csv = rec.read_events(tmp_path)
    forbidden = rec.read_forbidden(tmp_path)
    assert rec.count(rules, forbidden) == {"ELU_fondamental": b.count}
    assert rec.count(rules, forbidden, events_csv) == {
        "ELU_fondamental": b.expanded_count(ev)
    }
    rng = random.Random(54)
    for _ in range(30):
        vals = {c: rng.uniform(-1, 1) for c in ("c1", "c2", "c3", "q0", "q1")}
        hi, _, lo, _ = rec.extremes(rules, events_csv, vals, forbidden)[
            "ELU_fondamental"
        ]
        assert math.isclose(hi, brute_force(b, ev, vals, 1.0), abs_tol=1e-12)
        assert math.isclose(lo, brute_force(b, ev, vals, -1.0), abs_tol=1e-12)


def test_branches_without_exclusion_keep_the_engine_of_lot_51_ter(
    ev: dict[str, Event],
) -> None:
    bs = branches_51ter(ev)
    rng = np.random.default_rng(3)
    f = {c: rng.normal(size=40) for c in all_cases(geometry_of(variants()["B54"]))}
    for b in bs:
        assert not b.exclusions
    a = envelope(bs, ev, f, "ELS_caracteristique", sign=1.0)
    b2 = envelope(with_exclusions(bs, set()), ev, f, "ELS_caracteristique", sign=1.0)
    assert np.array_equal(a.value, b2.value)
    assert all(
        b.allows(p)
        for b in bs[:2]
        for p in itertools.islice(
            itertools.product(*(range(len(s.options)) for s in b.slots)), 50
        )
    )


def test_p70_never_lets_a_forbidden_pair_govern(ev: dict[str, Event]) -> None:
    g = geometry_of(variants()["B54"])
    bs = branches_p70(ev, g)
    forbidden = forbidden_pairs(incompatibilities(ev, g))
    rng = np.random.default_rng(70)
    f = {c: rng.normal(size=60) for c in all_cases(g)}
    for state in ("ELU_fondamental", "ELU_accidentel", "ELS_caracteristique"):
        ext = envelope(bs, ev, f, state, sign=1.0)
        for q in range(60):
            name, _ = governing(bs, ev, ext, q)
            parts = [
                p.split("[", 1)[0].rsplit("×", 1)[0]
                for p in name.split(": ", 1)[1].split(" + ")
            ]
            assert not any(
                frozenset((x, y)) in forbidden
                for x, y in itertools.combinations(parts, 2)
            ), name


# --------------------------------------------------------------------------- fiche


def test_fiche_carries_the_decisions_of_lot_54() -> None:
    fiche = json.loads(
        (PROJECT / "fiche" / "hypotheses_pontons_alu_01.json").read_text("utf-8")
    )
    by_label = {e["point_label"]: e for e in fiche["entries"]}
    for label in [f"P{k}" for k in range(67, 77)]:
        assert by_label[label]["status"] == "tranche", label
    for label in ("P43", "P48", "P56", "P60", "P61", "P62", "P64"):
        assert by_label[label]["decision_history"], label
    assert "P61 est annulée" in by_label["P61"]["option_retained"]
    assert "Xd + k × 1,25" in by_label["P64"]["option_retained"]
    assert "b = 0,60 m" in by_label["P43"]["option_retained"]
    assert len(fiche["entries"]) == 86


def test_archived_comms_are_the_generated_ones(ctx: ProjectContext) -> None:
    """The `.comm` of each run of lot 54 is regenerated byte for byte."""
    root = PROJECT / "references" / "execution_lot54"
    for code, v in variants().items():
        text_, _ = build_comm(ctx, mesh_label="maillage_ponton_52.med", variant=v)
        assert text_ == (root / code / "pontons_alu_01.comm").read_text("utf-8"), code
