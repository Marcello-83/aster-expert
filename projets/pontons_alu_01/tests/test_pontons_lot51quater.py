"""Tests of lot 51 quater for PONTONS-ALU-01: houle « tablier noyé » (P60) and
quasi-static impact (P61) on the unit cases of lot 51 ter, the HU_S5 sensitivity, the
rules (identity with lot 51 ter under P56, impacts only at the fundamental ULS and the
characteristic SLS), the decomposition against brute force with impacts, the governing
houle event, the independent reader of the `.npz`, the section view and the delivery
plan. No Docker, no Salome, no run of lot 51 ter needed."""

from __future__ import annotations

import csv
import importlib.util
import math
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01 import combinaisons_lot51ter as c3
from pontons_alu_01.combinaisons_lot51quater import (
    IMPACT,
    IMPACT_STATES,
    S5_PRESSURE_KPA,
    branches,
    check_exclusions,
    events_p60_p61,
    events_s5,
    magnitudes_p60,
)
from pontons_alu_01.depot_lot51quater import delivery_plan
from pontons_alu_01.exports_lot51quater import houle_of, is_wave_case
from pontons_alu_01.generation_lot51ter import applied_loads, values, zone_names
from pontons_alu_01.geometrie_lot51ter import geometry, span_length
from pontons_alu_01.variantes_lot51ter import variants
from pontons_alu_01.vues_lot51quater import png_size, section_view

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"
RHO_G = 10.05


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


@pytest.fixture(scope="module")
def data(ctx: ProjectContext) -> dict[str, Any]:
    return {k: v.value for k, v in ctx.data().items().items()}


def _kw(code: str) -> dict[str, Any]:
    g = geometry(variants()[code].mesh_overrides)
    return {
        "zones": zone_names(g),
        "cleats": [n for n, _, _ in g.cleats],
        "modules": list(g.modules()),
    }


def test_p60_coefficients_follow_the_flooded_deck_principle(
    data: dict[str, Any],
) -> None:
    """2 ρg (1,445 − z sous-face), rounded to the hundredth as MM wrote them; HD :
    ρg × 0,10 rounded up."""
    for z, key in ((1.20, "hu_tubes"), (1.35, "hu_pannes_50"), (1.34, "hu_pannes_60")):
        assert data[f"houle_lot51quater.{key}"] == round(2 * RHO_G * (1.445 - z), 2)
    assert data["houle_lot51quater.hu_platelage"] == round(2 * RHO_G * 0.045, 2)
    assert data["houle_lot51quater.hd_tablier"] == math.ceil(RHO_G * 0.10 * 100) / 100
    # P61 : 5,9 kPa décidé ; 5,84 avec w = 1,1 m/s, 5,94 avec w = 2π Hmax / T
    w = 2 * math.pi * 2.03 / 11.5
    assert data["houle_lot51quater.p_impact"] == round(
        1.5 * 0.5 * 1.025 * 2 * math.pi * w**2, 1
    )


def test_events_take_the_purlin_size_of_the_variant(data: dict[str, Any]) -> None:
    for code, purlins in (("A10", 1.91), ("B10", 1.91), ("A12", 2.11), ("B12", 2.11)):
        m = magnitudes_p60(data, variants()[code].purlin_side_mm)
        ev = events_p60_p61(m, **_kw(code))
        assert ev["HU"].coefficients == {
            "HU_TUBES": 4.92,
            "HU_PANNES": purlins,
            "HU_PLATELAGE": 0.90,
        }
        assert ev["HD"].coefficients == {"HD_TABLIER": 1.01}
        assert ev["HU_F"].coefficients == {
            "HU_TUBES": 2.36,
            "HU_PANNES": 0.85,
            "HU_PLATELAGE": 0.35,
        }
        impacts = [e for e in ev.values() if e.action == IMPACT]
        assert [e.name for e in impacts] == [f"HU_IMP_M{k}" for k in range(6)]
        assert ev["HU_IMP_M3"].coefficients == {
            "HU_TUBES_M3": 5.9,
            "HU_PANNES_M3": 5.9,
            "HU_PLATELAGE_M3": 5.9,
        }
    with pytest.raises(ValueError, match="pannes de 70"):
        magnitudes_p60(data, 70.0)


def test_s5_replaces_hu_and_drops_the_impacts(data: dict[str, Any]) -> None:
    m = magnitudes_p60(data, 50.0)
    ev = events_s5(m, **_kw("B10"))
    assert "HU" not in ev
    assert ev["HU_S5"].coefficients == dict.fromkeys(
        ("HU_TUBES", "HU_PANNES", "HU_PLATELAGE"), S5_PRESSURE_KPA
    )
    assert not [e for e in ev.values() if e.action == IMPACT]
    assert ev["HD"].coefficients == {"HD_TABLIER": 1.01}


def test_rules_without_impact_are_those_of_lot51ter(data: dict[str, Any]) -> None:
    """Identity with lot 51 ter: the P56 events through the rule builder of the lot."""
    ev = c3.events(c3.magnitudes(data), **_kw("B10"))
    assert branches(ev) == c3.branches(ev)


def test_counts_and_exclusions_with_impacts(data: dict[str, Any]) -> None:
    ev = events_p60_p61(magnitudes_p60(data, 50.0), **_kw("B10"))
    bs = branches(ev)
    tally = c3.counts(bs)
    assert sum(tally.values()) == 2_364_008
    assert tally["ELU_accidentel"] == 836_856
    assert tally["ELS_frequent"] == 199_662
    assert tally["ELS_quasi_permanent"] == 1_170
    assert sum(c3.expanded_counts(bs, ev).values()) == 107_534_360
    assert check_exclusions(bs, ev) == []
    for b in bs:
        names = {n for s in b.slots for n, _ in s.options if n is not None}
        has_impact = any(ev[n].action == IMPACT for n in names)
        assert has_impact == (
            b.state in IMPACT_STATES
            and "dominante AC" not in b.name
            and "dominante Q" not in b.name
            and "(avec AC)" not in b.name
        )


def test_impact_factors_are_those_of_hu(data: dict[str, Any]) -> None:
    ev = events_p60_p61(magnitudes_p60(data, 50.0), **_kw("B10"))
    for b in branches(ev):
        for s in b.slots:
            factors = {n: f for n, f in s.options if n is not None}
            if "HU_IMP_M0" in factors:
                assert {factors[f"HU_IMP_M{k}"] for k in range(6)} == {factors["HU"]}


def test_decomposition_equals_brute_force_with_impacts(data: dict[str, Any]) -> None:
    """Random unit values: the decomposition against the explicit enumeration, every
    state and both senses (the impacts are options of the houle slot)."""
    ev = events_p60_p61(magnitudes_p60(data, 50.0), **_kw("B10"))
    bs = branches(ev)
    cases = sorted(
        {k for e in ev.values() for k in e.coefficients}
        | {k for e in ev.values() for _, mc in e.modules for k in mc}
    )
    rng = random.Random(514)
    for _ in range(2):
        values_q = {c: rng.uniform(-1.0, 1.0) for c in cases}
        f = {c: np.array([v]) for c, v in values_q.items()}
        for state in ("ELU_fondamental", "ELS_caracteristique"):
            for sign in (1.0, -1.0):
                got = float(c3.envelope(bs, ev, f, state, sign=sign).value[0])
                explicit = [
                    c3.brute_force(b, ev, values_q, sign)
                    for b in bs
                    if b.state == state
                ]
                want = max(explicit) if sign > 0 else min(explicit)
                assert got == pytest.approx(want, rel=1e-12, abs=1e-12)


def test_impact_resultant_is_p_times_widths_times_module_length(
    ctx: ProjectContext, data: dict[str, Any]
) -> None:
    v = variants()["B10"]
    g = geometry(v.mesh_overrides)
    loads = applied_loads(values(ctx, v), g)
    ev = events_p60_p61(magnitudes_p60(data, 50.0), **_kw("B10"))
    for module, spans in g.modules().items():
        e = ev[f"HU_IMP_{module}"]
        got = sum(c * loads[k]["DZ"] for k, c in e.coefficients.items())
        length = sum(span_length(g, s) for s in spans)
        assert got == pytest.approx(5.9 * 1.927 * length * 1000.0, rel=1e-12)
    hu = ev["HU"]
    got = sum(c * loads[k]["DZ"] for k, c in hu.coefficients.items())
    length = sum(span_length(g, s.name) for s in g.spans)
    assert got == pytest.approx(
        (4.92 * 0.40 + 1.91 * 0.20 + 0.90 * 1.327) * length * 1000.0
    )


def test_houle_of_reads_the_governing_combination(data: dict[str, Any]) -> None:
    ev = events_p60_p61(magnitudes_p60(data, 50.0), **_kw("B10"))
    assert (
        houle_of("ELU_fondamental: G×1.2 + HU_IMP_M1×1.5 + AM1_+X×1.155", ev)
        == "HU_IMP_M1"
    )
    assert houle_of("ELS_caracteristique: G_DEJ_100×1 + HU×1", ev) == "HU"
    assert houle_of("ELU_fondamental: G×1.2 + Q[M1+M2]×1.3", ev) == "aucun"
    assert is_wave_case("HU_TUBES_M3")
    assert is_wave_case("HD_TABLIER")
    assert not is_wave_case("G2_M0")


def _write_pair(folder: Path, value_csv: float) -> tuple[Path, Path]:
    forces = np.arange(2 * 3 * 6, dtype=np.float64).reshape(2, 3, 6) + 0.123456789
    npz = folder / "efforts_elementaires.npz"
    np.savez_compressed(
        npz,
        cas=np.array(["G1", "Q"]),
        elements=np.array([1, 1, 2], dtype=np.int32),
        noeuds=np.array([10, 11, 11], dtype=np.int32),
        composantes=np.array(["N", "VY", "VZ", "MT", "MFY", "MFZ"]),
        efforts=forces.astype(np.float32),
    )
    path = folder / "efforts_elementaires.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write("# en-tête\n")
        w = csv.writer(stream, delimiter=";")
        w.writerow(["cas", "element", "noeud", "N", "VY", "VZ", "MT", "MFY", "MFZ"])
        for i, case in enumerate(("G1", "Q")):
            for j, (e, n) in enumerate(((1, 10), (1, 11), (2, 11))):
                row = forces[i, j].copy()
                row[:] = row + value_csv
                w.writerow([case, e, n, *(repr(float(x)) for x in row)])
    return npz, path


@pytest.mark.parametrize(("offset", "code"), [(0.0, 0), (0.5, 1)])
def test_npz_reader_compares_to_the_csv(
    tmp_path: Path, offset: float, code: int
) -> None:
    npz, path = _write_pair(tmp_path, offset)
    result = subprocess.run(  # noqa: S603 -- fixed argv
        [
            sys.executable,
            "-I",
            str(PROJECT / "scripts" / "lire_npz_lot51quater.py"),
            str(npz),
            str(path),
            "--tirages",
            "8",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == code, result.stdout + result.stderr


def test_section_view_is_1920_by_1080(tmp_path: Path) -> None:
    exports = tmp_path / "B10"
    exports.mkdir()
    rows = [
        ("1", "0", "-0.93", "1.3", "POUTRES_PRINC"),
        ("2", "0", "0.93", "1.3", "POUTRES_PRINC"),
        ("3", "0", "-0.55", "1.375", "PANNES_SEC"),
        ("4", "0", "0.56", "1.375", "PANNES_SEC"),
        ("5", "6.25", "-0.75", "0.69", "PILES"),
        ("6", "6.25", "0.75", "0.69", "PILES"),
        ("7", "6.25", "-1.05", "0.89", "CHEV_P1_C1"),
        ("8", "6.25", "1.05", "0.89", "CHEV_P1_C1"),
    ]
    with (exports / "noeuds.csv").open("w", encoding="utf-8") as stream:
        stream.write("# en-tête\nnoeud;x;y;z;groupes\n")
        stream.writelines(";".join(r) + "\n" for r in rows)
    out = tmp_path / "coupe.png"
    section_view("B10", exports, out)
    assert png_size(out) == (1920, 1080)


def test_delivery_plan_keeps_one_forces_csv(tmp_path: Path) -> None:
    root = tmp_path / "lot51quater"
    for code in ("A10", "B10"):
        folder = root / "exports" / code
        folder.mkdir(parents=True)
        for name in (
            "ancrage.csv",
            "efforts_elementaires.csv",
            "efforts_elementaires.npz",
        ):
            (folder / name).write_text("x", "utf-8")
    (root / "B10" / "MED").mkdir(parents=True)
    (root / "B10" / "MED" / "structure.med").write_text("x", "utf-8")
    for name in ("comparaison_variantes.csv", "comparaison_variantes_detail.csv"):
        (root / "exports" / name).write_text("x", "utf-8")
    (root / "vues").mkdir()
    (root / "vues" / "B10_vue1_x.png").write_text("x", "utf-8")
    plan = delivery_plan(SimpleNamespace(results_dir=tmp_path), ["A10", "B10"])  # type: ignore[arg-type]
    assert "B10/efforts_elementaires.csv" in plan
    assert "A10/efforts_elementaires.csv" not in plan
    assert "A10/efforts_elementaires.npz" in plan
    assert "B10/MED/structure.med" in plan
    assert "vues/B10_vue1_x.png" in plan
    assert {"scripts/vues_3d_pontons.py", "scripts/afficher_pontons_salome.py"} <= set(
        plan
    )


def test_delivered_recombiner_counts_the_impacts() -> None:
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51quater", PROJECT / "scripts" / "recombiner_lot51quater.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    events_csv: dict[str, Any] = {"HU_IMP_M0": ({"HU_TUBES_M0": 5.9}, [])}
    rules = [("ELU_fondamental", "b", [[(None, 0.0), ("HU_IMP_M0", 1.5)]])]
    assert rec.count(rules) == {"ELU_fondamental": 2}
    got = rec.extremes(rules, events_csv, {"HU_TUBES_M0": 2.0})["ELU_fondamental"]
    assert got[0] == pytest.approx(17.7)
    assert got[2] == 0.0
