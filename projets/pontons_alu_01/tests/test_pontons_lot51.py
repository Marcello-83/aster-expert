"""Tests of lot 51 for PONTONS-ALU-01: the pier and three spans (geometry, invariants,
variants, generated `.comm`, bearings), the combination rules (counts, duplicates,
decomposition against enumeration), the reading of the tables and the delivered
recombiner. No Docker, no Salome."""

from __future__ import annotations

import importlib.util
import itertools
import math
import re
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51 import (
    branches,
    counts,
    enumerate_branch,
    envelope,
    event_rows,
    events,
    governing,
    magnitudes,
    rule_rows,
)
from pontons_alu_01.exports_lot51 import parse_tableau, write
from pontons_alu_01.extensions_lot51 import tributary_areas
from pontons_alu_01.generation_lot51 import (
    all_cases,
    applied_loads,
    arm_terms,
    bearing_stiffness,
    build_comm,
    link_plan,
    values,
)
from pontons_alu_01.geometrie_lot51 import (
    ParameterError,
    expected_counts,
    geometry,
    params_json,
    read_parameters,
)
from pontons_alu_01.invariants_lot51 import invariants
from pontons_alu_01.variantes_lot51 import variants

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
        "recombiner_lot51", PROJECT / "scripts" / "recombiner_lot51.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- geometry


def test_counts_equal_those_of_the_salome_runs() -> None:
    """Counts of the two meshes produced in lot 51 (mesh check 1232/1232)."""
    assert expected_counts(geometry({"H_PILES": 1.32})) == {
        "nodes": 901,
        "SEG2": 830,
        "QUAD4": 132,
    }
    assert expected_counts(geometry({"H_PILES": 4.0})) == {
        "nodes": 941,
        "SEG2": 870,
        "QUAD4": 132,
    }


def test_only_the_pile_height_is_overridable() -> None:
    assert read_parameters(overrides={"H_PILES": 4.0})["H_PILES"] == 4.0
    with pytest.raises(ParameterError, match="non modifiable"):
        read_parameters(overrides={"L": 7.0})
    assert params_json({"H_PILES": 4.0}) == b'{"H_PILES": 4.0}\n'


def test_versioned_invariants_are_those_of_the_reference() -> None:
    text = (PROJECT / "maillage" / "invariants_palee.yaml").read_text("utf-8")
    assert yaml.safe_load(text) == invariants(geometry({"H_PILES": 1.32}))


def test_linked_nodes_are_distinct_and_one_millimetre_apart_at_the_splices() -> None:
    g = geometry()
    for lk in g.links:
        assert lk.a != lk.b
    for name in ("EC_A1_YM", "EC_A2_YP", "LG_C1_YM", "LG_C2_YP"):
        lk = g.link(name)
        assert math.dist(lk.a, lk.b) == pytest.approx(0.001, abs=1e-12)
    assert g.member("NEO_A1_YM").length == pytest.approx(0.001, abs=1e-12)
    assert g.member("NEO_A1_YM").elements == 1


def test_pier_geometry_follows_the_consigne() -> None:
    g = geometry()
    assert g.spans == {"T1": (0.0, 6.25), "PT": (6.251, 7.769), "T2": (7.77, 14.02)}
    assert (g.footing_x[0], g.footing_x[-1]) == (5.75, 8.27)
    assert (g.footing_y[0], g.footing_y[-1]) == (-1.45, 1.45)
    assert g.footing_z == -0.755
    assert geometry({"H_PILES": 4.0}).footing_z == pytest.approx(0.69 - 4.0 - 0.125)
    heads = sorted(lk.a for lk in g.links if lk.name.startswith("TP_"))
    assert heads == [
        (6.25, -0.75, 0.69),
        (6.25, 0.75, 0.69),
        (7.77, -0.75, 0.69),
        (7.77, 0.75, 0.69),
    ]
    cleats = sorted(g.node_groups[n][0][0] for n in g.node_groups if n.startswith("TQ"))
    assert sorted(set(cleats)) == [1.6, 4.6, 9.37, 12.37]
    zones = {z.name: (z.x0, z.x1) for z in g.zones}
    assert zones["ACC_PT_YM"] == (6.51, 7.51)
    assert zones["ACC_PA2_YP"] == (7.77, 8.77)
    assert len(zones) == 10


def test_tributary_areas_sum_to_the_footing() -> None:
    g = geometry()
    assert sum(tributary_areas(g).values()) == pytest.approx(2.52 * 2.90, rel=1e-12)


# --------------------------------------------------------------------------- bearings


def test_bearing_stiffness_follows_p38(data: dict[str, object]) -> None:
    kx, kz = bearing_stiffness(data)
    assert kx == pytest.approx(2.25e6, rel=1e-12)
    assert kz == pytest.approx(476e6, abs=1e6)
    assert kz / 1e6 == pytest.approx(476.586, abs=1e-3)


def test_arm_relation_is_a_rigid_rotation() -> None:
    """u_A − u_B − θ_B ∧ (A − B) = 0 for a rigid motion (translation + rotation)."""
    g = geometry()
    lk = g.link("TP_C1_YM")
    terms = arm_terms(lk)
    theta = np.array([0.01, -0.02, 0.03])
    t0 = np.array([0.1, 0.2, 0.3])

    def motion(p: tuple[float, float, float]) -> dict[str, float]:
        u = t0 + np.cross(theta, np.array(p))
        return dict(
            zip(("DX", "DY", "DZ", "DRX", "DRY", "DRZ"), [*u, *theta], strict=True)
        )

    nodes = {f"{lk.name}_A": motion(lk.a), f"{lk.name}_B": motion(lk.b)}
    total = 0.0
    for group, ddl, coef in terms:
        if group == "":
            assert abs(total) < 1e-12
            total = 0.0
        else:
            total += coef * nodes[group][ddl]


# --------------------------------------------------------------------------- variants


def test_twelve_variants_as_in_the_consigne() -> None:
    v = variants()
    assert list(v) == [
        "R",
        "E",
        "T1",
        "T2",
        "A",
        "P4",
        "P4E",
        "N-",
        "N+",
        "M",
        "S1",
        "S3",
    ]
    assert set(v["T1"].heads.values()) == {"rotule", "encastrement"}
    assert v["T1"].heads["C1_YM"] == "encastrement"
    assert v["T1"].heads["C1_YP"] == "rotule"
    assert set(v["T2"].heads.values()) == {"encastrement"}
    assert v["P4E"].pile_height == 4.0 and v["P4"].heads == v["R"].heads
    assert (v["N-"].kh_factor, v["N+"].kh_factor) == (0.5, 2.0)
    assert (v["S1"].beam_side_mm, v["S3"].beam_thickness_mm) == (180.0, 10.0)
    assert v["E"].splice == "continu" and v["A"].ring == "independant"


def test_link_plan_follows_each_variant() -> None:
    g = geometry()
    v = variants()

    def kinds(code: str) -> dict[str, str]:
        return {
            lk.name: k for k, items in link_plan(g, v[code]).items() for lk in items
        }

    r = kinds("R")
    assert r["TP_C1_YM"] == "bras" and r["EC_A1_YM"] == "bras_torsion"
    assert r["LG_C1_YM"] == "solide"
    assert kinds("T2")["TP_C2_YP"] == "solide"
    assert kinds("E")["EC_A2_YP"] == "solide"
    plan_a = link_plan(g, v["A"])
    tie = next(lk for lk in plan_a["bras"] if lk.name == "LG_C1_YM")
    assert tie.b == g.link("TP_C1_YM").a


def test_generated_comm_of_each_variant(ctx: ProjectContext) -> None:
    for code, v in variants().items():
        text, report = build_comm(ctx, mesh_label="maillage_palee.med", variant=v)
        concepts = re.findall(r"^(\w+) = ", text, flags=re.MULTILINE)
        assert max(len(c) for c in concepts) <= 8, code
        groups = re.findall(r'GROUP_(?:MA|NO)="(\w+)"', text)
        assert max(len(gr) for gr in groups) <= 24, code
        assert len(report["cases"]) == 68
        assert ('MODELISATION="DIS_T"' in text) and ('REPERE="GLOBAL"' in text)
        if code == "M":
            assert 'GROUP_NO=("BR_A1_YM_A", "NB_A1_YM"), DDL=("DY", "DY")' in text
            assert "VALE=(0.0, 0.0, 0.0)" in text
        if code == "N+":
            assert "VALE=(4500000.0, 4500000.0, " in text


def test_unit_cases_apply_one_kilonewton(ctx: ProjectContext) -> None:
    g = geometry()
    loads = applied_loads(values(ctx, variants()["R"]), g)
    assert len(loads) == len(all_cases(g)) == 68
    for case, r in loads.items():
        if case[:3] in ("ACN", "ACX", "ACZ", "AMY", "AMX"):
            assert sorted(abs(x) for x in r.values()) == [
                0.0,
                0.0,
                pytest.approx(1000.0, rel=1e-12),
            ]
    assert loads["ACN_MI1_YM"]["DY"] > 0 > loads["ACN_MI1_YP"]["DY"]
    assert loads["AMY_TQ1_YM"]["DY"] < 0 < loads["AMY_TQ1_YP"]["DY"]
    total = loads["G2"]["DZ"]
    parts = sum(loads[f"G2_{t}"]["DZ"] for t in ("T1", "PT", "T2"))
    assert total == pytest.approx(parts, rel=1e-12)
    assert total == pytest.approx(-1000.0 * 2.0 * (6.25 + 1.518 + 6.25), rel=1e-12)


# ------------------------------------------------------------------------ combinations


def test_combination_counts_and_no_duplicate(data: dict[str, object]) -> None:
    ev = events(magnitudes(data), split=False)
    bs = branches(ev)
    assert counts(bs) == {
        "ELU_fondamental": 121556,
        "ELU_accidentel": 75008,
        "ELS_caracteristique": 60778,
        "ELS_frequent": 18458,
        "ELS_quasi_permanent": 435,
    }
    seen = set()
    total = 0
    for b in bs:
        for _, coefs in enumerate_branch(b, ev):
            key = (b.state, *sorted((k, round(v, 12)) for k, v in coefs.items() if v))
            seen.add(key)
            total += 1
    assert total == len(seen) == 276235
    split = branches(events(magnitudes(data), split=True))
    assert sum(counts(split).values()) == 5416185


def test_events_follow_the_annex(data: dict[str, object]) -> None:
    ev = events(magnitudes(data), split=False)
    assert ev["AC_MI1_YM_-Z"].coefficients == {"ACN_MI1_YM": 23.5, "ACZ_MI1_YM": -16.45}
    assert ev["ACA_PT_YP_+X"].coefficients == {"ACN_PT_YP": 45.0, "ACX_PT_YP": 31.5}
    assert ev["AML_TQ2_YP_PERP"].coefficients == {"AMY_TQ2_YP": 27.5}
    assert ev["AMF_TQ3_YM_-X"].coefficients == {"AMX_TQ3_YM": -49.0}
    am1 = ev["AM1_-X"].coefficients
    assert len(am1) == 16 and am1["AMY_TQ4_YM"] == 23.8 and am1["AMX_TQ1_YP"] == -13.7
    assert ev["AM2_YM"].coefficients == {f"AMY_TQ{k}_YM": 10.6 for k in range(1, 5)}
    assert len([e for e in ev.values() if e.action == "AC"]) == 40
    assert len([e for e in ev.values() if e.action == "AM"]) == 28
    assert len([e for e in ev.values() if e.action == "AMF"]) == 24


def test_b_prime_and_exclusive_events(data: dict[str, object]) -> None:
    ev = events(magnitudes(data), split=False)
    for b in branches(ev):
        for name, coefs in itertools.islice(enumerate_branch(b, ev), 0, None, 97):
            crowd = any(c in coefs for c in ("Q", "QD"))
            wave = any(c in coefs for c in ("HU", "HD"))
            assert not (crowd and wave), name
            assert name.count("AC_") + name.count("ACA_") <= 1, name
            assert (
                name.count("AML_")
                + name.count("AM1_")
                + name.count("AM2_")
                + name.count("AMF_")
                <= 1
            ), name


def test_decomposition_equals_enumeration(data: dict[str, object]) -> None:
    """Criterion 5 on random quantities: the sum of the best option of each slot is
    the extreme of every combination enumerated one by one."""
    rng = np.random.default_rng(51)
    for split, states in (
        (False, ("ELU_fondamental", "ELU_accidentel", "ELS_frequent")),
        (True, ("ELS_quasi_permanent", "ELS_frequent")),
    ):
        ev = events(magnitudes(data), split=split)
        bs = branches(ev)
        cases = sorted({c for e in ev.values() for c in e.coefficients})
        f = {c: rng.normal(size=3) for c in cases}
        for state in states:
            for sign in (1.0, -1.0):
                ext = envelope(bs, ev, f, state, sign=sign)
                best: np.ndarray | None = None
                for b in (b for b in bs if b.state == state):
                    for _, coefs in enumerate_branch(b, ev):
                        v = np.zeros(3)
                        for k, c in coefs.items():
                            v = v + c * f[k]
                        best = (
                            v
                            if best is None
                            else (
                                np.maximum(best, v) if sign > 0 else np.minimum(best, v)
                            )
                        )
                assert best is not None
                assert np.allclose(ext.value, best, rtol=1e-12, atol=1e-12)
                _, coefs = governing(bs, ev, ext, 0)
                assert sum(c * f[k][0] for k, c in coefs.items()) == pytest.approx(
                    ext.value[0], rel=1e-12
                )


def test_recombiner_reads_back_the_rules(
    tmp_path: Path, data: dict[str, object]
) -> None:
    ev = events(magnitudes(data), split=False)
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
    assert events_csv["AC_QU_YP_+Z"] == ev["AC_QU_YP_+Z"].coefficients
    qp = [r for r in rules if r[0] == "ELS_quasi_permanent"]
    assert sum(1 for _ in rec.combinations(qp, events_csv)) == 435


# --------------------------------------------------------------------------- tables


def test_tableau_reading_keeps_absent_values_empty() -> None:
    text = (
        "#\n##ASTER 17.04.00 CONCEPT\n"
        "RESULTAT NOM_CHAM NUME_ORDRE NOEUD DX DRX\n"
        "ELEM DEPL 1 7 1.0E+00 -\n"
        "ELEM DEPL 1 8 -2.5E-01 3.0E-03\n\n"
    )
    ((cols, rows),) = parse_tableau(text)
    assert cols[-1] == "DRX"
    assert rows[0]["DRX"] == "" and rows[1]["DX"] == "-2.5E-01"


def test_archived_comms_are_the_generated_ones(ctx: ProjectContext) -> None:
    """The `.comm` of each run of lot 51 is regenerated byte for byte."""
    root = PROJECT / "references" / "execution_lot51"
    for code, v in variants().items():
        text, _ = build_comm(ctx, mesh_label="maillage_palee.med", variant=v)
        assert text == (root / code / "pontons_alu_01.comm").read_text("utf-8"), code
