"""Tests of lot 51 bis for PONTONS-ALU-01: pier types on pin bearings (levels, footing,
invariants, variants, pin relations, generated `.comm`, buoyancy DEJ), the combination
rules with DEJ tied to G (P49), the deflection rule P51 and the delivered recombiner.
No Docker, no Salome."""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51 import (
    counts,
    enumerate_branch,
    envelope,
    event_rows,
    magnitudes,
    rule_rows,
)
from pontons_alu_01.combinaisons_lot51bis import branches, events
from pontons_alu_01.exports_lot51 import write
from pontons_alu_01.exports_lot51bis import without_tangential
from pontons_alu_01.extensions_lot51 import tributary_areas
from pontons_alu_01.generation_lot51bis import (
    all_cases,
    applied_loads,
    build_comm,
    concrete_volumes,
    pin_relations,
    values,
)
from pontons_alu_01.geometrie_lot51 import ParameterError, expected_counts
from pontons_alu_01.geometrie_lot51bis import geometry, params_json, read_parameters
from pontons_alu_01.invariants_lot51bis import invariants
from pontons_alu_01.variantes_lot51bis import variants

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"
H80C = {"H_ANNEAU": 0.8, "H_PILES": 1.3}


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


@pytest.fixture(scope="module")
def data(ctx: ProjectContext) -> dict[str, object]:
    return {k: v.value for k, v in ctx.data().items().items()}


def _recombiner() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51bis", PROJECT / "scripts" / "recombiner_lot51bis.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- geometry


def test_levels_follow_p47_and_the_consigne() -> None:
    """Axis 0,17 m under the main beams, cap beam top 0,10 m under the axis: +1,488."""
    for h_ring, h_piles, axis_ring, head, foot in (
        (0.4, 1.7, 1.288, 1.088, -0.612),
        (0.4, 4.3, 1.288, 1.088, -3.212),
        (0.8, 1.3, 1.088, 0.688, -0.612),
        (0.8, 3.9, 1.088, 0.688, -3.212),
    ):
        lv = geometry({"H_ANNEAU": h_ring, "H_PILES": h_piles}).levels
        assert lv["plan_moyen"] == 1.858
        assert lv["sous_face_poutres"] == 1.758
        assert lv["axe_appui"] == 1.588
        assert lv["dessus_chevetre"] == 1.488
        assert lv["axe_anneau"] == axis_ring
        assert lv["tete_piles"] == head
        assert lv["dessus_semelle"] == foot
        assert lv["plan_moyen_semelle"] == pytest.approx(foot - 0.10, abs=1e-12)


def test_only_ring_and_pile_heights_are_overridable() -> None:
    assert read_parameters(overrides=H80C)["H_ANNEAU"] == 0.8
    with pytest.raises(ParameterError, match="non modifiable"):
        read_parameters(overrides={"EP_SEMELLE": 0.25})
    assert params_json(H80C) == b'{"H_ANNEAU": 0.8, "H_PILES": 1.3}\n'


def test_counts_equal_those_of_the_salome_runs() -> None:
    """Counts of the four meshes produced in lot 51 bis (mesh check 1108/1108)."""
    expected = {
        (0.4, 1.7): (895, 812),
        (0.4, 4.3): (939, 856),
        (0.8, 1.3): (891, 808),
        (0.8, 3.9): (931, 848),
    }
    for (a, p), (nodes, seg2) in expected.items():
        assert expected_counts(geometry({"H_ANNEAU": a, "H_PILES": p})) == {
            "nodes": nodes,
            "SEG2": seg2,
            "QUAD4": 156,
        }


def test_versioned_invariants_are_those_of_h80c() -> None:
    text = (PROJECT / "maillage" / "invariants_palee_51bis.yaml").read_text("utf-8")
    assert yaml.safe_load(text) == invariants(geometry(H80C))


def test_footing_follows_p48(data: dict[str, object]) -> None:
    g = geometry(H80C)
    assert (g.footing_x[0], g.footing_x[-1]) == (5.71, 8.31)
    assert (g.footing_y[0], g.footing_y[-1]) == (-1.3, 1.3)
    assert (g.footing_x[0] + g.footing_x[-1]) / 2.0 == pytest.approx(7.01, abs=1e-12)
    assert data["palee_lot51bis.semelle_epaisseur"] == g.parameters["EP_SEMELLE"]
    assert sum(tributary_areas(g).values()) == pytest.approx(2.6 * 2.6, rel=1e-12)
    assert g.spans == {"T1": (0.0, 6.25), "PT": (6.251, 7.769), "T2": (7.77, 14.02)}


def test_bearings_have_no_support_profile_nor_spring() -> None:
    g = geometry(H80C)
    families = {m.family for m in g.members}
    assert "SUPPORTS" not in families
    assert "NEOPRENES" not in families
    assert len(g.axes) == 6
    a1 = g.axis("A1_YP")
    assert a1.ears == ((6.25, 0.93, 1.858), (6.251, 0.93, 1.858))
    assert a1.cap == (6.25, 0.93, 1.088)
    assert a1.pin == (6.25, 0.93, 1.588)
    assert a1.blocks_y
    assert not g.axis("A2_YM").blocks_y
    assert g.axis("A3_YP").cap is None
    assert len(g.axis("A3_YP").ears) == 1


# --------------------------------------------------------------------------- pins


def _nodal(
    g_points: dict[str, tuple[float, float, float]],
    t0: np.ndarray,
    theta: np.ndarray,
) -> dict[str, dict[str, float]]:
    out = {}
    for group, p in g_points.items():
        u = t0 + np.cross(theta, np.array(p))
        out[group] = dict(
            zip(("DX", "DY", "DZ", "DRX", "DRY", "DRZ"), [*u, *theta], strict=True)
        )
    return out


def _evaluate(
    terms: list[tuple[str, str, float]], u: dict[str, dict[str, float]]
) -> float:
    return sum(c * u[g][d] for g, d, c in terms)


def test_pin_relations_hold_for_a_rigid_motion() -> None:
    g = geometry(H80C)
    theta = np.array([0.01, -0.02, 0.03])
    t0 = np.array([0.1, 0.2, 0.3])
    for a in g.axes:
        points = {a.ear_group(k): e for k, e in enumerate(a.ears, start=1)}
        if a.cap is not None:
            points[a.cap_group] = a.cap
        u = _nodal(points, t0, theta)
        for label, terms in pin_relations(a):
            if a.cap is None and "support fixe" in label:
                continue
            assert abs(_evaluate(terms, u)) < 1e-12, (a.name, label)


def test_pin_leaves_x_and_rotation_about_y_free() -> None:
    """A slide in X of the deck and a rotation about the axis of one ear satisfy the
    relations to the cap beam; a vertical or (YP) transverse offset does not."""
    g = geometry(H80C)
    a = g.axis("A1_YP")
    zero = dict.fromkeys(("DX", "DY", "DZ", "DRX", "DRY", "DRZ"), 0.0)
    pin = np.array(a.pin)
    ear = np.array(a.ears[0])
    # ear 1 turns by 0.01 about the axis (Y through the pin) and slides 0.02 in X
    theta = np.array([0.0, 0.01, 0.0])
    u1 = np.cross(theta, ear - pin) + np.array([0.02, 0.0, 0.0])
    moved = {
        a.ear_group(1): {
            **zero,
            "DX": float(u1[0]),
            "DY": float(u1[1]),
            "DZ": float(u1[2]),
            "DRY": 0.01,
        },
        a.cap_group: dict(zero),
    }
    for label, terms in pin_relations(a):
        if "chevêtre" in label:
            assert abs(_evaluate(terms, moved)) < 1e-12, label
    lifted = {a.ear_group(1): {**zero, "DZ": 0.001}, a.cap_group: dict(zero)}
    shifted = {a.ear_group(1): {**zero, "DY": 0.001}, a.cap_group: dict(zero)}
    rel = dict(pin_relations(a))
    assert _evaluate(rel["appui sur le chevêtre, DZ"], lifted) != 0.0
    assert _evaluate(rel["appui sur le chevêtre, DY"], shifted) != 0.0
    assert "appui sur le chevêtre, DY" not in dict(pin_relations(g.axis("A1_YM")))


# --------------------------------------------------------------------------- variants


def test_five_variants_as_in_the_consigne() -> None:
    v = variants()
    assert list(v) == ["H40C", "H40P", "H80C", "H80P", "H80C-S3"]
    assert [(x.ring_height, x.pile_height) for x in v.values()] == [
        (0.4, 1.7),
        (0.4, 4.3),
        (0.8, 1.3),
        (0.8, 3.9),
        (0.8, 1.3),
    ]
    assert v["H80C-S3"].beam_thickness_mm == 10.0
    assert {x.beam_thickness_mm for c, x in v.items() if c != "H80C-S3"} == {8.0}


def test_generated_comm_of_each_variant(ctx: ProjectContext) -> None:
    for code, v in variants().items():
        text, report = build_comm(ctx, mesh_label="maillage_palee_51bis.med", variant=v)
        concepts = re.findall(r"^(\w+) = ", text, flags=re.MULTILINE)
        assert max(len(c) for c in concepts) <= 8, code
        groups = re.findall(r'GROUP_(?:MA|NO)="(\w+)"', text)
        assert max(len(gr) for gr in groups) <= 24, code
        titles = re.findall(r'INTITULE="(\w+)"', text)
        assert max(len(t) for t in titles) <= 16, code
        assert len(report["cases"]) == 69
        assert "NEOPRENES" not in text and "SUPPORTS" not in text
        assert (
            report["pin_relations"] == 2 * 5 + 2 * 6 + 1 + 2
        )  # YM, YP sur chevêtres ; A3
        assert (
            f"VALE=({v.beam_side_mm / 1000!r}, {v.beam_thickness_mm / 1000!r})" in text
        )
        assert 'FORCE_COQUE=_F(GROUP_MA="SEMELLE", FZ=2000.0)' in text


def test_buoyancy_is_ten_kilonewtons_per_cubic_metre(ctx: ProjectContext) -> None:
    v = variants()["H80C"]
    g = geometry(v.mesh_overrides)
    vals = values(ctx, v)
    vol = concrete_volumes(vals, g)
    assert vol["SEMELLE"] == pytest.approx(2.6 * 2.6 * 0.2, rel=1e-12)
    assert vol["CHEVETRES"] == pytest.approx(2 * 2.10 * 0.4 * 0.8, rel=1e-12)
    assert vol["LONGRINES"] == pytest.approx(2 * 1.518 * 0.4 * 0.8, rel=1e-12)
    assert vol["PILES"] == pytest.approx(4 * math.pi * 0.25**2 * 1.3, rel=1e-12)
    loads = applied_loads(vals, g)
    assert len(loads) == len(all_cases(g)) == 69
    assert loads["DEJ"] == {
        "DX": 0.0,
        "DY": 0.0,
        "DZ": pytest.approx(1e4 * sum(vol.values()), rel=1e-15),
    }


def test_lighter_footing_than_lot_51_once_buoyant() -> None:
    """P48: about 7 kN less than the footing of lot 51 (2,52 × 2,90 × 0,25 m)."""
    delta = (2.52 * 2.90 * 0.25 - 2.60 * 2.60 * 0.20) * (25.0 - 10.0)
    assert delta == pytest.approx(7.1, abs=0.05)


# ------------------------------------------------------------------------ combinations


def test_counts_and_no_duplicate(data: dict[str, object]) -> None:
    ev = events(magnitudes(data))
    bs = branches(ev)
    assert counts(bs) == {
        "ELU_fondamental": 121556,
        "ELU_accidentel": 150016,
        "ELS_caracteristique": 121556,
        "ELS_frequent": 36916,
        "ELS_quasi_permanent": 870,
    }
    seen = set()
    total = 0
    for b in bs:
        for _, coefs in enumerate_branch(b, ev):
            key = (b.state, *sorted((k, round(v, 12)) for k, v in coefs.items() if v))
            seen.add(key)
            total += 1
    assert total == len(seen) == 430914


def test_buoyancy_follows_the_factor_of_g(data: dict[str, object]) -> None:
    """P49: G × 1,2 without DEJ, G × 0,9 with DEJ × 1,0; G × 1,0 with or without."""
    ev = events(magnitudes(data))
    seen: dict[str, set[tuple[float, float]]] = {}
    for b in branches(ev):
        for _, coefs in enumerate_branch(b, ev):
            pair = (round(coefs["G1"], 12), round(coefs.get("DEJ", 0.0), 12))
            seen.setdefault(b.state, set()).add(pair)
            break
        (perm,) = [s for s in b.slots if s.label.startswith("G")]
        pairs = set()
        for name, factor in perm.options:
            assert name is not None
            c = ev[name].coefficients
            pairs.add((factor * c["G1"], factor * c["G2"], factor * c.get("DEJ", 0.0)))
        if b.state == "ELU_fondamental":
            assert pairs == {(1.2, 1.2, 0.0), (0.9, 0.9, 1.0)}
        else:
            assert pairs == {(1.0, 1.0, 0.0), (1.0, 1.0, 1.0)}
    assert ev["G_DEJ_090"].action == ev["G_DEJ_100"].action == "G"


def test_decomposition_equals_enumeration(data: dict[str, object]) -> None:
    rng = np.random.default_rng(511)
    ev = events(magnitudes(data))
    bs = branches(ev)
    cases = sorted({c for e in ev.values() for c in e.coefficients})
    f = {c: rng.normal(size=2) for c in cases}
    for state in ("ELU_fondamental", "ELS_quasi_permanent", "ELS_frequent"):
        for sign in (1.0, -1.0):
            ext = envelope(bs, ev, f, state, sign=sign)
            best: np.ndarray | None = None
            for b in (b for b in bs if b.state == state):
                for _, coefs in enumerate_branch(b, ev):
                    v = np.zeros(2)
                    for k, c in coefs.items():
                        v = v + c * f[k]
                    best = (
                        v
                        if best is None
                        else (np.maximum(best, v) if sign > 0 else np.minimum(best, v))
                    )
            assert best is not None
            assert np.allclose(ext.value, best, rtol=1e-12, atol=1e-12)


def test_characteristic_deflection_leaves_the_tangential_berthing_out() -> None:
    f = {
        "ACN_QU_YM": np.array([1.0]),
        "ACX_QU_YM": np.array([2.0]),
        "ACZ_PT_YP": np.array([3.0]),
        "Q": np.array([4.0]),
    }
    g = without_tangential(f)
    assert [float(g[c][0]) for c in f] == [1.0, 0.0, 0.0, 4.0]


def test_recombiner_reads_back_the_rules(
    tmp_path: Path, data: dict[str, object]
) -> None:
    ev = events(magnitudes(data))
    bs = branches(ev)
    write(
        tmp_path / "combinaisons.csv",
        "r",
        [
            "etat_limite",
            "branche",
            "emplacement",
            "action",
            "nombre_options",
            "effectif_branche",
            "options",
        ],
        rule_rows(bs),
    )
    write(
        tmp_path / "evenements.csv",
        "e",
        ["action", "evenement", "cas", "coefficient"],
        event_rows(ev),
    )
    rec = _recombiner()
    rules = rec.read_rules(tmp_path)
    assert rec.count(rules) == counts(bs)
    events_csv = rec.read_events(tmp_path)
    assert events_csv["G_DEJ_090"] == {"G1": 0.9, "G2": 0.9, "DEJ": 1.0}
    qp = [r for r in rules if r[0] == "ELS_quasi_permanent"]
    assert sum(1 for _ in rec.combinations(qp, events_csv)) == 870


# --------------------------------------------------------------------------- fiche


def test_fiche_carries_the_decisions_of_lot_51_bis(ctx: ProjectContext) -> None:
    import json  # noqa: PLC0415

    sheet = json.loads(
        (PROJECT / "fiche" / "hypotheses_pontons_alu_01.json").read_text()
    )
    labels = {e["point_label"] for e in sheet["entries"]}
    assert {f"P{k}" for k in range(44, 52)} <= labels
    assert {"A8", "A9"} <= labels


def test_archived_comms_are_the_generated_ones(ctx: ProjectContext) -> None:
    """The `.comm` of each run of lot 51 bis is regenerated byte for byte."""
    root = PROJECT / "references" / "execution_lot51bis"
    for code, v in variants().items():
        text, _ = build_comm(ctx, mesh_label="maillage_palee_51bis.med", variant=v)
        assert text == (root / code / "pontons_alu_01.comm").read_text("utf-8"), code
