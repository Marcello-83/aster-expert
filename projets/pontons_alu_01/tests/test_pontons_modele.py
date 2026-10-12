"""Tests of the PONTONS-ALU-01 model (lots 50 and 50 bis): parameters, geometry,
invariants, fiche, combinations, generated `.comm`, simplified ratio. No Docker, no
Salome."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons import counts, set_a, set_b, set_b_prime
from pontons_alu_01.extensions import tributary_areas
from pontons_alu_01.generation import applied_loads, build_comm, values, weights
from pontons_alu_01.geometrie import (
    ParameterError,
    expected_counts,
    geometry,
    half_deck_widths,
    influence_widths,
    read_parameters,
)
from pontons_alu_01.invariants import invariants

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


def test_parameters_are_read_from_the_script() -> None:
    p = read_parameters()
    assert p["L"] == 6.25
    assert p["X_SEMELLE"] == pytest.approx((5.75, 7.01))  # L − 0,50 ; L + 0,76 (P19)


def test_a_statement_other_than_a_number_is_refused(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    script.write_text(
        "# PARAMETRES begin\nL = open('x')\n# PARAMETRES end\n", encoding="utf-8"
    )
    with pytest.raises(ParameterError):
        read_parameters(script)


def test_counts_equal_those_of_the_salome_run() -> None:
    # Lot 50 bis (P24), mesh run 20261012T144146-7a1698f2: mesh check 356/356.
    assert expected_counts(geometry()) == {"nodes": 416, "SEG2": 384, "QUAD4": 72}


def test_p24_transverse_geometry() -> None:
    p = read_parameters()
    assert p["B"] == 1.86
    assert p["Y_SUPPORTS"] == (-0.93, 0.0, 0.93)
    assert p["Y_CHEVETRE"] == (-1.05, 1.05)
    ys = sorted({pt[1] for pt in geometry().member("MONT_1").points})
    assert (ys[0], ys[-1]) == (-0.93, 0.93)


def test_every_bar_has_at_least_four_elements_of_at_most_25_cm() -> None:
    for m in geometry().members:
        assert m.elements >= 4, m.name
        for (a, b), n in zip(
            zip(m.points, m.points[1:], strict=False), m.counts, strict=False
        ):
            assert math.dist(a, b) / n <= 0.25 + 1e-9, m.name


def test_versioned_invariants_are_those_of_the_parameters() -> None:
    text = (PROJECT / "maillage" / "invariants.yaml").read_text(encoding="utf-8")
    assert yaml.safe_load(text) == invariants(geometry())


def test_influence_widths_cover_the_deck_of_two_metres() -> None:
    # P24: loaded width 2,00 m, outer strips beyond the main beams' axes.
    g = geometry()
    widths = influence_widths(g)
    assert sum(widths.values()) == pytest.approx(2.00, abs=1e-12)
    assert widths["PP_YM"] == pytest.approx(0.26, abs=1e-12)
    assert widths["PP_YP"] == pytest.approx(0.255, abs=1e-12)
    assert sum(half_deck_widths(g).values()) == pytest.approx(1.00, abs=1e-12)


def test_tributary_areas_sum_to_the_footing() -> None:
    assert sum(tributary_areas(geometry()).values()) == pytest.approx(
        1.26 * 2.90, rel=1e-12
    )


def test_self_weight_is_the_hand_computation(ctx: ProjectContext) -> None:
    # Lot 50 bis geometry (P24), by hand: montants 6 × 1,86 m, diagonals recomputed,
    # cap beam 2,10 m long; lot 50: 44 988,4 N (docs/essais_lot50.md § 2.1).
    a150, gamma = 4004e-6, 27000.0
    diagonals = (
        math.hypot(0.75, 1.86) + 3 * math.hypot(1.5, 1.86) + math.hypot(1.0, 1.86)
    )
    hand = (
        2 * 6.25 * 4440e-6 * gamma
        + 6 * 1.86 * a150 * gamma
        + diagonals * a150 * gamma
        + 4 * 6.25 * 900e-6 * gamma
        + 3 * 0.15 * a150 * gamma
        + 2.10 * 0.25 * 0.40 * 25000.0
        + 2 * 1.32 * math.pi * 0.25**2 * 25000.0
        + 1.26 * 2.90 * 0.25 * 25000.0
    )
    total = sum(weights(values(ctx), geometry()).values())
    # 1e-7: crossings of the diagonals snapped to the 1 mm grid (8e-9 relative).
    assert total == pytest.approx(hand, rel=1e-7)
    assert total == pytest.approx(45627.8, abs=0.05)


def test_berthing_and_mooring_resultants(ctx: ProjectContext) -> None:
    loads = applied_loads(values(ctx), geometry())
    assert loads["ACM"]["DY"] == pytest.approx(32000.0)
    assert loads["AAP"]["DY"] == pytest.approx(-154000.0)
    assert loads["AMM"]["DY"] == pytest.approx(-16000.0)
    assert loads["Q"]["DZ"] == pytest.approx(-5000.0 * 2.0 * 6.25)


def test_combination_counts() -> None:
    assert counts() == {
        "A_ELU": 80,
        "A_ELUA": 16,
        "A_ELS_C": 40,
        "B_ELU": 1620,
        "B_ELUA": 594,
        "B_ELS_C": 810,
        "B_ELS_F": 297,
        "B_ELS_QP": 81,
    }


def test_set_a_reproduces_s2_combination_10() -> None:
    c = next(c for c in set_a() if c.name == "A10_G1.2_HU_TAP_Q_ACM")
    assert c.coefficients == {
        "G1": 1.2,
        "G2": 1.2,
        "HU": 20.0,
        "TAP": 0.6,
        "Q": 1.3,
        "ACM": 1.0,
    }


def test_set_b_rules() -> None:
    combos = set_b()
    for c in combos:
        keys = set(c.coefficients)
        for pair in (("HU", "HD"), ("TP", "TM"), ("AMM", "AMP"), ("ACM", "ACP")):
            assert not set(pair) <= keys, c.name
        assert not {"Q", "QD"} <= keys, c.name
        if c.family == "B_ELUA":
            assert keys & {"AAM", "AAP"} and not keys & {"ACM", "ACP"}, c.name
        else:
            assert not keys & {"AAM", "AAP"}, c.name
    lead = next(c for c in combos if c.name == "B_ELU_G1.2_HU_TP_AMM_ACM_Q")
    assert lead.coefficients["HU"] == pytest.approx(7.5)  # γ 1,5 × 5 kPa
    assert lead.coefficients["TP"] == pytest.approx(1.5 * 0.6)
    assert lead.coefficients["Q"] == pytest.approx(1.3 * 0.77)


def test_set_b_prime_drops_crowd_with_houle() -> None:
    # P27: Q (or Q½) and the houle are never together; everything else is set B.
    b, prime = set_b(), set_b_prime()
    for c in prime:
        keys = set(c.coefficients)
        assert not (keys & {"Q", "QD"} and keys & {"HU", "HD"}), c.name
    names = {c.name for c in prime}
    for c in b:
        keys = set(c.coefficients)
        both = keys & {"Q", "QD"} and keys & {"HU", "HD"}
        assert (c.name in names) != bool(both), c.name
    tally: dict[str, int] = {}
    for c in prime:
        tally[c.family] = tally.get(c.family, 0) + 1
    assert tally == {
        "B_ELU": 756,
        "B_ELUA": 282,
        "B_ELS_C": 378,
        "B_ELS_F": 141,
        "B_ELS_QP": 45,
    }


def test_versioned_fiche_is_rebuilt_byte_for_byte() -> None:
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "fiche_lot50", PROJECT / "scripts" / "fiche_lot50.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from aster_expert.agent.prevues import carry_planned_commands  # noqa: PLC0415

    sheet = carry_planned_commands(module.build_sheet(), module.FICHE)
    text = json.dumps(json.loads(sheet.model_dump_json()), indent=2, ensure_ascii=False)
    assert text + "\n" == module.FICHE.read_text(encoding="utf-8")


def test_reference_comm_is_the_generated_one(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PONTONS_K_IY", raising=False)
    text, report = build_comm(ctx, mesh_label="maillage_pontons.med")
    reference = PROJECT / "references" / "execution_lot50bis" / "pontons_alu_01.comm"
    assert text == reference.read_text(encoding="utf-8")
    assert report["rigid_links"] == 51
    assert len(text.splitlines()) < 400


def test_quay_hinges_follow_p25(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PONTONS_K_IY", raising=False)
    text, _ = build_comm(ctx, mesh_label="maillage_pontons.med")
    assert (
        'DDL_IMPO=(_F(GROUP_NO="APP_QUAI_YP", DX=0.0, DY=0.0, DZ=0.0), '
        '_F(GROUP_NO="APP_QUAI_YM", DX=0.0, DZ=0.0)),'
    ) in text
    groups = {g["name"]: g for g in invariants(geometry())["groups"]}
    assert groups["APP_QUAI_YM"]["count"] == 1
    assert groups["APP_QUAI_YP"]["count"] == 1


def test_inertia_sweep_changes_iy_only(
    ctx: ProjectContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PONTONS_K_IY", raising=False)
    base, _ = build_comm(ctx, mesh_label="maillage_pontons.med")
    monkeypatch.setenv("PONTONS_K_IY", "3")
    swept, report = build_comm(ctx, mesh_label="maillage_pontons.med")
    assert report["pp_inertia_factor"] == 3.0
    old, new = base.splitlines(), swept.splitlines()
    added = [line for line in new if line not in old]
    removed = [line for line in old if line not in new]
    assert len(removed) == 1
    assert len(added) == 2
    assert added[0].startswith("# Balayage du lot 50 bis : IY = 3 ×")
    assert "7.6924533e-05" in added[1]
    assert "2.5641511e-05" in removed[0]
    monkeypatch.setenv("PONTONS_K_IY", "0")
    with pytest.raises(ValueError, match="PONTONS_K_IY"):
        build_comm(ctx, mesh_label="maillage_pontons.med")


def test_simplified_ratio_formulas(ctx: ProjectContext) -> None:
    import numpy as np  # noqa: PLC0415

    from pontons_alu_01.lot50bis import fit_inverse, ratios, sections  # noqa: PLC0415

    s = sections(ctx)
    tube = s["tube_150"]
    assert tube.w_y * 1e9 == pytest.approx((150**4 - 136**4) / 12 / 75, rel=1e-12)
    assert tube.a_v * 1e6 == pytest.approx(4004 / 2, rel=1e-12)
    assert (tube.f0, tube.f0_haz, tube.gamma_m1) == (260e6, 125e6, 1.10)
    pp = s["mp1200"]
    comps = ["N", "VY", "VZ", "MT", "MFY", "MFZ"]
    stack = np.array([[[-10e3, 3e3, 4e3, 0.0, 2e3, -1e3]]])
    r = ratios(stack, comps, pp)
    sigma = 10e3 / pp.area + 2e3 / pp.w_y + 1e3 / pp.w_z
    assert r["sigma"][0, 0] == pytest.approx(sigma, rel=1e-12)
    assert r["taux_sigma_f0"][0, 0] == pytest.approx(sigma * 1.10 / 215e6, rel=1e-12)
    assert r["taux_tau_haz"][0, 0] == pytest.approx(
        5e3 / pp.a_v * math.sqrt(3.0) * 1.10 / 115e6, rel=1e-12
    )
    a, b, residual = fit_inverse([1.0, 3.0, 5.0], [7.0 + 60.0, 7.0 + 20.0, 7.0 + 12.0])
    assert a == pytest.approx(7.0)
    assert b == pytest.approx(60.0)
    assert residual < 1e-9


def test_avp_comparison_covers_the_table_of_d6() -> None:
    from pontons_alu_01.syntheses import AVP, BEAM_FAMILIES  # noqa: PLC0415

    assert set(AVP) <= set(BEAM_FAMILIES)
    assert AVP["poutres_principales"]["ELU_fondamental"]["N"] == (-139, 78)
