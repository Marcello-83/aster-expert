"""Tests of lot 51 ter for PONTONS-ALU-01: the whole pontoon (AVP levels, stations,
piers, footings, invariants, variants, generated `.comm`, ring corners counted once,
houle by surfaces), the combination rules (P56, P57, P59, Q and QD by modules), the
decomposition against brute force and the delivered recombiner. No Docker, no Salome."""

from __future__ import annotations

import importlib.util
import json
import math
import random
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51ter import (
    ACTIONS,
    Branch,
    Event,
    branches,
    brute_force,
    check_exclusions,
    counts,
    enumerate_branch,
    envelope,
    event_rows,
    events,
    expanded_counts,
    governing,
    magnitudes,
    rule_rows,
)
from pontons_alu_01.exports_lot51 import write
from pontons_alu_01.generation_lot51ter import (
    HARNESS_TABLES,
    all_cases,
    applied_loads,
    build_comm,
    concrete_volumes_by_pier,
    values,
    zone_names,
)
from pontons_alu_01.geometrie_lot51 import ParameterError
from pontons_alu_01.geometrie_lot51ter import (
    expected_counts,
    geometry,
    pier_levels,
    read_parameters,
    span_length,
    tributary_areas,
)
from pontons_alu_01.invariants_lot51ter import invariants
from pontons_alu_01.variantes_lot51ter import variants

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


@pytest.fixture(scope="module")
def data(ctx: ProjectContext) -> dict[str, object]:
    return {k: v.value for k, v in ctx.data().items().items()}


def _recombiner() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51ter", PROJECT / "scripts" / "recombiner_lot51ter.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- geometry


def test_levels_follow_p53_and_p54() -> None:
    for code, purlin in (("A10", 1.375), ("A12", 1.37), ("B10", 1.375), ("B12", 1.37)):
        lv = geometry(variants()[code].mesh_overrides).levels
        assert lv["dessus_tablier"] == 1.40
        assert lv["poutres"] == 1.30
        assert lv["sous_face_poutres"] == 1.20
        assert lv["pannes"] == purlin
        assert lv["axe_appui"] == 1.16
        assert lv["dessus_chevetre"] == 1.09
        assert lv["axe_anneau"] == 0.89
        assert lv["tete_piles"] == 0.69


def test_stations_spans_and_cantilever_follow_the_consigne() -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    spans = {s.name: (s.x0, s.x1) for s in g.spans}
    assert spans["T1"] == (0.0, 6.25)
    assert spans["PT1"] == (6.251, 7.769)
    assert spans["T3"] == (15.54, 21.79)
    assert spans["PT5"] == (37.331, 38.85)
    assert spans["PF"] == (38.85, 40.1)
    assert geometry(variants()["A10"].mesh_overrides).length == 39.9
    assert g.modules()["M0"] == ("T1",)
    assert g.modules()["M3"] == ("PT3", "T4")
    assert g.modules()["M5"] == ("PT5", "PF")
    # Deux oreilles partout, sauf sur C2 de P5 (petite travée continue avec PF).
    ears = {a.name: len(a.ears) for a in g.axes}
    assert ears["P5C2_YM"] == ears["P5C2_YP"] == 1
    assert sum(1 for n in ears.values() if n == 2) == 18
    assert len(g.zones) == 42 and len(zone_names(g)) == 21
    assert len(g.cleats) == 10  # 10 positions × 2 rives = 20 taquets
    assert [x for _, x, _ in g.cleats][:2] == [1.6, 4.6]


def test_footings_follow_the_pile_heights_of_the_diagnostic() -> None:
    for code, heights in (
        ("A10", (1.50, 2.00, 2.50, 3.30, 3.90)),
        ("B10", (1.30, 1.95, 2.50, 3.50, 3.90)),
    ):
        p = geometry(variants()[code].mesh_overrides).parameters
        for k, h in enumerate(heights, start=1):
            lv = pier_levels(p, k)
            assert lv["dessus_semelle"] == round(0.69 - h, 3)
            assert lv["dessous_semelle"] == round(0.49 - h, 3)
    g = geometry(variants()["B10"].mesh_overrides)
    assert [f.z for f in g.footings] == [-0.71, -1.36, -1.91, -2.91, -3.31]
    assert all(f.area == pytest.approx(2.6 * 2.6) for f in g.footings)
    areas = tributary_areas(g)
    for f in g.footings:
        total = sum(a for pier, a in areas.values() if pier == f.pier)
        assert total == pytest.approx(f.area)


def test_counts_equal_those_of_the_salome_runs() -> None:
    """3 215 nœuds, 2 776 SEG2, 780 QUAD4 : relevés par mesh check sur les MED des
    quatre variantes (3 526 invariants sur 3 526)."""
    for v in variants().values():
        assert expected_counts(geometry(v.mesh_overrides)) == {
            "nodes": 3215,
            "SEG2": 2776,
            "QUAD4": 780,
        }


def test_versioned_invariants_are_those_of_b10() -> None:
    versioned = yaml.safe_load(
        (PROJECT / "maillage" / "invariants_ponton_51ter.yaml").read_text("utf-8")
    )
    assert versioned == invariants(geometry(variants()["B10"].mesh_overrides))


def test_only_the_declared_parameters_are_overridable() -> None:
    with pytest.raises(ParameterError, match="non modifiable"):
        read_parameters(overrides={"H_ANNEAU": 0.8})
    with pytest.raises(ParameterError, match="une hauteur de piles par palée"):
        read_parameters(overrides={"H_PILES": [1.0, 2.0]})


def test_four_variants_as_in_the_consigne() -> None:
    v = variants()
    assert list(v) == ["A10", "A12", "B10", "B12"]
    assert (v["A10"].beam_thickness_mm, v["A10"].purlin_side_mm) == (10, 50)
    assert (v["A12"].beam_thickness_mm, v["A12"].purlin_side_mm) == (12, 60)
    assert v["B12"].cantilever == 1.25 and v["A12"].cantilever == 1.05
    assert v["B10"].stations == (6.25, 14.02, 21.79, 29.56, 37.33)


# --------------------------------------------------------------------------- loads


def test_ring_corners_are_counted_once(ctx: ProjectContext) -> None:
    """Correction 2 du lot 51 ter : volume de l'anneau = 2 chevêtres de 2,10 m + 2
    longrines de 1,52 − 0,40 m, section 0,40 × 0,40."""
    v = variants()["B10"]
    g = geometry(v.mesh_overrides)
    vol = concrete_volumes_by_pier(values(ctx, v), g)
    for pier in g.piers:
        ring = vol[pier]["CHEVETRES"] + vol[pier]["LONGRINES"]
        assert ring == pytest.approx(2 * 2.10 * 0.16 + 2 * 1.12 * 0.16, rel=1e-12)
        assert vol[pier]["SEMELLE"] == pytest.approx(0.20 * 2.6 * 2.6)
    loads = applied_loads(values(ctx, v), g)
    total = sum(sum(x.values()) for x in vol.values())
    assert loads["DEJ"]["DZ"] == pytest.approx(10e3 * total, rel=1e-12)


def test_deck_cases_carry_width_times_length(ctx: ProjectContext) -> None:
    v = variants()["B10"]
    g = geometry(v.mesh_overrides)
    loads = applied_loads(values(ctx, v), g)
    length = sum(span_length(g, s.name) for s in g.spans)
    assert length == pytest.approx(g.length - 0.009)
    for case, width, sign in (
        ("HU_PLATELAGE", 1.327, 1.0),
        ("HD_TABLIER", 1.895, -1.0),
        ("HU_TUBES", 2 * 0.20, 1.0),
        ("HU_PANNES", 4 * 0.05, 1.0),
        ("G2", 2.00, -1.0),
    ):
        assert loads[case]["DZ"] == pytest.approx(
            sign * 1e3 * width * length, rel=1e-12
        )
        parts = sum(loads[f"{case}_{m}"]["DZ"] for m in g.modules())
        assert parts == pytest.approx(loads[case]["DZ"], rel=1e-12)


def test_221_cases_and_short_harness_titles() -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    cases = all_cases(g)
    assert len(cases) == 221
    assert sum(c.startswith(("ACN", "ACX", "ACZ")) for c in cases) == 126
    assert sum(c.startswith(("AMY", "AMX")) for c in cases) == 40
    assert max(len(p + c) for p, *_ in HARNESS_TABLES for c in cases) <= 16


def test_projet_yaml_declares_every_case(ctx: ProjectContext) -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    controls = ctx.declaration.controls
    assert controls is not None
    assert [c.name for c in controls.cases] == all_cases(g)
    assert controls.absolute_threshold_n == 1.0


def test_generated_comm_of_each_variant(ctx: ProjectContext) -> None:
    for code, v in variants().items():
        text, report = build_comm(ctx, mesh_label="ponton.med", variant=v)
        assert text.count("    LIAISON_DDL=(") == 1
        assert report["pin_relations"] == 102
        assert (
            text.count("RIGI_PARASOL") == 1 and text.count('GROUP_MA_POI1="SOL_P') == 5
        )
        assert 'GROUP_MA="ANGLES_ANNEAU", MATER=BETON0' in text
        assert f"Variante {code}" in text


def test_archived_comms_are_the_generated_ones(ctx: ProjectContext) -> None:
    """The `.comm` of each run of lot 51 ter is regenerated byte for byte."""
    root = PROJECT / "references" / "execution_lot51ter"
    for code, v in variants().items():
        text, _ = build_comm(ctx, mesh_label="maillage_ponton_51ter.med", variant=v)
        assert text == (root / code / "pontons_alu_01.comm").read_text("utf-8"), code


# ---------------------------------------------------------------- combinations


def _small(data: dict[str, object]) -> tuple[dict[str, Event], list[Branch]]:
    ev = events(magnitudes(data), zones=["Z"], cleats=[1], modules=["M0", "M1", "M2"])
    return ev, branches(ev)


def test_counts_and_exclusions_of_the_full_rules(data: dict[str, object]) -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    ev = events(
        magnitudes(data),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )
    bs = branches(ev)
    assert sum(counts(bs).values()) == 2_351_600
    assert sum(expanded_counts(bs, ev).values()) == 107_521_952
    assert check_exclusions(bs, ev) == []
    assert sum(1 for e in ev.values() if e.action == "AC") == 168
    assert sum(1 for e in ev.values() if e.action == "AM") == 64


def test_factors_of_houle_and_mooring(data: dict[str, object]) -> None:
    """P56 et P59 : facteurs par état limite, en tête et en accompagnement."""
    ev, bs = _small(data)
    assert ACTIONS["AM"].psi0 == ACTIONS["AM"].psi1 == 0.77
    assert ACTIONS["AM"].psi2 == 0.2 and ACTIONS["H"].psi2 == 0.0

    def factors(state: str, action: str) -> set[tuple[str, float]]:
        out = set()
        for b in bs:
            if b.state != state:
                continue
            for k, s in enumerate(b.slots):
                for n, f in s.options:
                    if n is not None and ev[n].action == action:
                        out.add(("tête" if k == 1 else "acc.", round(f, 6)))
        return out

    assert factors("ELU_fondamental", "H") == {("tête", 1.5), ("acc.", 1.155)}
    assert factors("ELS_caracteristique", "H") == {("tête", 1.0), ("acc.", 0.77)}
    assert factors("ELS_frequent", "HF") == {("tête", 1.0)}
    assert factors("ELS_frequent", "H") == set()
    assert factors("ELS_quasi_permanent", "H") == set()
    # ELU accidentel : HU ou HD × 0,77 comme action variable de tête (emplacement 3,
    # après G et l'action accidentelle), jamais en accompagnement (ψ2 = 0).
    assert factors("ELU_accidentel", "H") == {("acc.", 0.77)}
    assert factors("ELU_fondamental", "AM") == {("tête", 1.5), ("acc.", 1.155)}
    assert factors("ELS_caracteristique", "AM") == {("tête", 1.0), ("acc.", 0.77)}
    assert factors("ELS_frequent", "AM") == {("tête", 0.77), ("acc.", 0.2)}
    assert factors("ELS_quasi_permanent", "AM") == {("acc.", 0.2)}


def test_houle_never_with_berthing_nor_crowd(data: dict[str, object]) -> None:
    ev, bs = _small(data)
    assert check_exclusions(bs, ev) == []
    for b in bs:
        for _, coefs in enumerate_branch(b, ev):
            houle = any(k.startswith(("HU_", "HD_")) for k in coefs)
            if houle:
                assert not any(
                    k.startswith(("Q_", "QD_", "ACN", "ACX", "ACZ")) for k in coefs
                )


def test_envelope_equals_brute_force_with_every_pattern(
    data: dict[str, object],
) -> None:
    """Q et QD par lignes d'influence contre l'énumération des 2³ − 1 dispositions."""
    ev, bs = _small(data)
    cases = sorted(
        {c for e in ev.values() for c in e.coefficients}
        | {c for e in ev.values() for _, mc in e.modules for c in mc}
    )
    rng = random.Random(51)
    for _ in range(5):
        values_ = {c: rng.uniform(-1.0, 1.0) for c in cases}
        f = {c: np.array([v]) for c, v in values_.items()}
        for state in {b.state for b in bs}:
            for sign in (1.0, -1.0):
                ext = envelope(bs, ev, f, state, sign=sign)
                brute = [
                    brute_force(b, ev, values_, sign) for b in bs if b.state == state
                ]
                ref = max(brute) if sign > 0 else min(brute)
                assert float(ext.value[0]) == pytest.approx(ref, rel=1e-12, abs=1e-12)
                name, coefs = governing(bs, ev, ext, 0)
                assert sum(c * values_[k] for k, c in coefs.items()) == pytest.approx(
                    ref, rel=1e-12, abs=1e-12
                )
                assert "aucun module" not in name or "Q[" not in name


def test_recombiner_reads_back_the_rules(
    data: dict[str, object], tmp_path: Path
) -> None:
    ev, bs = _small(data)
    write(
        tmp_path / "combinaisons.csv",
        "essai",
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
        rule_rows(bs, ev),
    )
    write(
        tmp_path / "evenements.csv",
        "essai",
        ["action", "evenement", "portee", "cas", "coefficient"],
        event_rows(ev),
    )
    rec = _recombiner()
    rules = rec.read_rules(tmp_path)
    evs = rec.read_events(tmp_path)
    assert rec.count(rules) == counts(bs)
    assert rec.count(rules, evs) == expanded_counts(bs, ev)
    cases = sorted({r[3] for r in event_rows(ev)})
    rng = random.Random(7)
    values_ = {c: rng.uniform(-1.0, 1.0) for c in cases}
    f = {c: np.array([v]) for c, v in values_.items()}
    got = rec.extremes(rules, evs, values_)
    for state, (hi, _, lo, _) in got.items():
        assert envelope(bs, ev, f, state, sign=1.0).value[0] == pytest.approx(
            hi, rel=1e-12
        )
        assert envelope(bs, ev, f, state, sign=-1.0).value[0] == pytest.approx(
            lo, rel=1e-12
        )


def test_characteristic_deflection_leaves_the_tangential_berthing_out() -> None:
    from pontons_alu_01.exports_lot51ter import without_tangential  # noqa: PLC0415

    f = {"ACX_T1D_YM": np.ones(2), "ACZ_PF_YP": np.ones(2), "ACN_T1D_YM": np.ones(2)}
    out = without_tangential(f)
    assert not out["ACX_T1D_YM"].any() and not out["ACZ_PF_YP"].any()
    assert out["ACN_T1D_YM"].all()


# --------------------------------------------------------------------------- fiche


def test_fiche_carries_the_decisions_of_lot_51_ter(ctx: ProjectContext) -> None:
    fiche = json.loads(
        (PROJECT / "fiche" / "hypotheses_pontons_alu_01.json").read_text("utf-8")
    )
    by_label = {e.get("point_label"): e for e in fiche["entries"]}
    for label in ("P53", "P54", "P55", "P56", "P57", "P58", "P59", "A10", "A11"):
        assert by_label[label]["status"] == "tranche", label
    for label in ("P47", "P50"):
        assert by_label[label]["decision_history"], label
    assert "P47 annulée" in by_label["P53"]["option_retained"]
    value = ctx.data().items()["houle_lot51ter.hu_tubes"].value
    assert isinstance(value, float)
    assert math.isclose(value, 14.49)
