"""Combinaisons du tronc commun (lot 41) : règles EN 1990 lues de la déclaration,
efforts combinés d'un listing, contrôle manuel indépendant. Les combinaisons du
quai (D17) sont éprouvées dans son projet (`test_combinaisons_d17.py`)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from aster_expert.combinaisons.efforts import (
    average_by_node,
    combined_forces,
    extrema,
    parse_element_tables,
    write_combined_forces,
)
from aster_expert.combinaisons.enumeration import (
    combine,
    enumerate_combinations,
    grouped_by_coefficient,
)
from aster_expert.projet.context import load_project
from aster_expert.projet.declaration import CombinationsSection, ElementForces
from aster_expert.projet.errors import ProjectError

Factory = Callable[..., Any]


def _section(**changes: Any) -> CombinationsSection:
    base: dict[str, Any] = {
        "permanent": ["G"],
        "gamma_g_unfavourable": 1.35,
        "gamma_g_favourable": 1.0,
        "gamma_q": 1.5,
        "variables": [
            {"name": "Q1", "psi0": 0.7, "psi1": 0.5, "psi2": 0.3},
            {"name": "Q2", "psi0": 0.6, "psi1": 0.2, "psi2": 0.0},
            {"name": "Q3", "psi0": 0.5, "psi1": 0.4, "psi2": 0.1},
        ],
    }
    base.update(changes)
    return CombinationsSection.model_validate(base)


def test_three_variable_actions_follow_en_1990() -> None:
    combos = enumerate_combinations(_section(), float)  # type: ignore[arg-type]
    by_name = {c.name: c for c in combos}

    assert len(combos) == 3 * 4 + 3 * 2 + 3 * 2 + 1
    fond = by_name["ELU_FOND_Q2_DOM_Q1_Q3_ACC_G_defav"]
    assert fond.coefficients == {"G": 1.35, "Q2": 1.5, "Q1": 1.5 * 0.7, "Q3": 1.5 * 0.5}
    # fréquente : dominante à psi1, accompagnement à psi2 par défaut (6.15b)
    assert by_name["ELS_FREQ_Q1_DOM_Q2_Q3_ACC"].coefficients == {
        "G": 1.0,
        "Q1": 0.5,
        "Q2": 0.0,
        "Q3": 0.1,
    }
    assert by_name["ELS_CARA_Q3_DOM"].coefficients == {"G": 1.0, "Q3": 1.0}
    assert by_name["ELS_QUASI_PERMANENTE"].coefficients == {
        "G": 1.0,
        "Q1": 0.3,
        "Q2": 0.0,
        "Q3": 0.1,
    }


def test_a_single_variable_action_has_no_accompanying_variant() -> None:
    section = _section(variables=[{"name": "Q", "psi0": 0.7, "psi1": 0.5, "psi2": 0.3}])
    names = [c.name for c in enumerate_combinations(section, float)]  # type: ignore[arg-type]

    assert names == [
        "ELU_FOND_Q_DOM_G_defav",
        "ELU_FOND_Q_DOM_G_favo",
        "ELS_CARA_Q_DOM",
        "ELS_FREQ_Q_DOM",
        "ELS_QUASI_PERMANENTE",
    ]


def test_accidental_combinations_are_written_out() -> None:
    section = _section(
        accidental=[
            {
                "name": "ACC",
                "family": "ELU accidentelle",
                "coefficients": {"G": 1.0, "A": 1.0},
            }
        ]
    )
    combos = enumerate_combinations(section, float)  # type: ignore[arg-type]
    acc = next(c for c in combos if c.name == "ACC")
    assert acc.coefficients == {"G": 1.0, "A": 1.0}
    assert combos.index(acc) == 12  # après les 12 fondamentales


def test_the_hand_check_groups_cases_by_coefficient() -> None:
    coefficients = {"G": 1.35, "EAU": 1.35, "Q": 1.5}
    values = {"G": 0.1, "EAU": 0.2, "Q": 0.3}

    assert (
        grouped_by_coefficient(coefficients, values) == 1.35 * (0.1 + 0.2) + 1.5 * 0.3
    )
    assert combine(coefficients, values) == pytest.approx(
        grouped_by_coefficient(coefficients, values), rel=1e-15
    )


def _table(case: str, rows: list[tuple[int, int, float, float]]) -> str:
    lines = [
        f"##EFPOUT_{case}ASTER 17.04.00 CONCEPT T CALCULE LE 29/09/2026",
        "RESULTAT NOM_CHAM MAILLE NOEUD SOUS_POINT COOR_X COOR_Y COOR_Z "
        "N VY VZ MT MFY MFZ",
    ]
    for maille, noeud, x, n in rows:
        numbers = [maille, noeud, 1, x, 0.0, 0.0, n, 0.0, 0.0, 0.0, 0.0, 2 * n]
        lines.append("RESU EFGE_ELNO " + " ".join(f"{float(v):.12E}" for v in numbers))
    return "\n".join(lines) + "\n\n"


_FORCES = ElementForces(
    table="EFPOUT_{case}",
    components=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
    cases=("G", "Q"),
    reference_case="G",
)


def test_element_tables_are_read_and_averaged_per_node() -> None:
    text = _table("G", [(1, 1, 0.0, 10.0), (1, 2, 1.0, 20.0), (2, 2, 1.0, 40.0)])
    raw = parse_element_tables(text.splitlines(), _FORCES)

    nodes = average_by_node(raw["G"], _FORCES.components)

    assert nodes[2]["N"] == 30.0
    assert nodes[1]["x"] == 0.0
    top = extrema(nodes, _FORCES.components)
    assert top["N"]["node"] == 2
    assert top["MFZ"]["MFZ"] == 60.0


def test_combined_forces_of_the_fake_project(
    fake_project: Factory, tmp_path: Path
) -> None:
    project = fake_project()
    data = project.declaration()
    data["combinations"]["forces"] = json.loads(_FORCES.model_dump_json())
    data["combinations"]["manual_check"] = {
        "combination": "ELU_FOND_Q_DOM_G_defav",
        "node_nearest_x": 1.0,
    }
    project.write_declaration(data)
    ctx = load_project(project.name, project.repo_root)
    mess = tmp_path / "fort.6"
    mess.write_text(
        _table("G", [(1, 1, 0.0, 10.0), (1, 2, 1.0, 20.0)])
        + _table("Q", [(1, 1, 0.0, 1.0), (1, 2, 1.0, 2.0)])
        + " --- DIAGNOSTIC JOB : OK\n",
        encoding="utf-8",
    )

    result = combined_forces(ctx, mess)
    written = write_combined_forces(ctx, result, tmp_path / "out")

    assert result.diagnostic == "--- DIAGNOSTIC JOB : OK"
    assert result.combined["ELU_FOND_Q_DOM_G_defav"][2]["N"] == 1.35 * 20.0 + 1.5 * 2.0
    assert result.manual_check is not None
    assert result.manual_check["node"] == 2
    assert result.manual_check["max_absolute_gap"] == 0.0
    names = sorted(p.name for p in written)
    assert names == [
        "combinaisons.csv",
        "controle_manuel.json",
        "extrema.csv",
        "rapport.md",
    ]
    assert (tmp_path / "out" / "rapport.md").read_text("utf-8") == "5 combinaisons\n"


def test_a_missing_case_table_is_named(fake_project: Factory, tmp_path: Path) -> None:
    project = fake_project()
    data = project.declaration()
    data["combinations"]["forces"] = json.loads(_FORCES.model_dump_json())
    project.write_declaration(data)
    ctx = load_project(project.name, project.repo_root)
    mess = tmp_path / "fort.6"
    mess.write_text(_table("G", [(1, 1, 0.0, 1.0)]), encoding="utf-8")

    with pytest.raises(ProjectError, match=r"tables d'efforts absentes .*\['Q'\]"):
        combined_forces(ctx, mess)


def test_a_project_without_forces_is_refused(
    fake_project: Factory, tmp_path: Path
) -> None:
    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    with pytest.raises(ProjectError, match="ne déclare pas d'efforts à combiner"):
        combined_forces(ctx, tmp_path / "fort.6")
