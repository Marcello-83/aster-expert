"""Tests of the PONTONS-ALU-01 model (lot 50): parameters, geometry, invariants, fiche,
combinations, generated `.comm`. No Docker, no Salome."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons import counts, set_a, set_b
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
    # Lot 50, run 20261012T124823-5f1c4fcd: PONTONS_MESH_OK 405 72 373.
    assert expected_counts(geometry()) == {"nodes": 405, "SEG2": 373, "QUAD4": 72}


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


def test_influence_widths_cover_the_deck_between_main_beams() -> None:
    g = geometry()
    assert sum(influence_widths(g).values()) == pytest.approx(1.50, abs=1e-12)
    assert sum(half_deck_widths(g).values()) == pytest.approx(0.75, abs=1e-12)


def test_tributary_areas_sum_to_the_footing() -> None:
    assert sum(tributary_areas(geometry()).values()) == pytest.approx(
        1.26 * 2.90, rel=1e-12
    )


def test_self_weight_is_the_hand_computation_of_the_trial_report(
    ctx: ProjectContext,
) -> None:
    # docs/essais_lot50.md § 2.1 : 44 988,4 N.
    total = sum(weights(values(ctx), geometry()).values())
    assert total == pytest.approx(44988.4, abs=0.05)


def test_berthing_and_mooring_resultants(ctx: ProjectContext) -> None:
    loads = applied_loads(values(ctx), geometry())
    assert loads["ACM"]["DY"] == pytest.approx(32000.0)
    assert loads["AAP"]["DY"] == pytest.approx(-154000.0)
    assert loads["AMM"]["DY"] == pytest.approx(-16000.0)
    assert loads["Q"]["DZ"] == pytest.approx(-5000.0 * 1.5 * 6.25)


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


def test_reference_comm_is_the_generated_one(ctx: ProjectContext) -> None:
    text, report = build_comm(ctx, mesh_label="maillage_pontons.med")
    reference = PROJECT / "references" / "execution_lot50" / "pontons_alu_01.comm"
    assert text == reference.read_text(encoding="utf-8")
    assert report["rigid_links"] == 51
    assert len(text.splitlines()) < 400
