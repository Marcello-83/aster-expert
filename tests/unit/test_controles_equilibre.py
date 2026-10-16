"""Contrôles de niveau D du tronc commun (lot 41) : équilibre, pesanteur, symétrie,
sur un listing synthétique et le projet factice (`tests/conftest.py`). Aucun
Docker : les tables sont écrites comme `IMPR_TABLE` les imprime."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

from aster_expert.controles.equilibre import (
    balance_terms,
    level_d_controls,
    symmetry_check,
    term_passes,
    worst_gap,
)
from aster_expert.controles.tables import TableIndex, find_table
from aster_expert.projet.context import load_project
from aster_expert.projet.declaration import ControlsSection, SymmetryPlane
from aster_expert.projet.errors import ProjectError

Factory = Callable[..., Any]


def _num(v: float) -> str:
    return f"{v:.12E}"


def _reaction(title: str, dx: float, dy: float, dz: float) -> str:
    return (
        "##ASTER 17.04.00 CONCEPT TAB CALCULE LE 29/09/2026\n"
        "INTITULE RESULTAT NOM_CHAM DX DY DZ\n"
        f"{title} RESU REAC_NODA {_num(dx)} {_num(dy)} {_num(dz)}\n\n"
    )


def _symmetry(case: str, rows: Sequence[tuple[float, ...]]) -> str:
    body = "".join(
        f"SYMETRIE_{case} N{i} " + " ".join(_num(v) for v in r) + "\n"
        for i, r in enumerate(rows, start=1)
    )
    return (
        "##ASTER 17.04.00 CONCEPT TAB\n"
        "INTITULE NOEUD COOR_X COOR_Y COOR_Z DX DY DZ\n" + body + "\n"
    )


def _mess(dz_g: float = 100.0) -> str:
    rows = [
        # (x, y, z, dx, dy, dz) : paires symétriques par rapport au plan X = 1
        (0.0, 0.0, 0.0, 1.0e-3, 2.0e-3, -1.0e-3),
        (2.0, 0.0, 0.0, -1.0e-3, 2.0e-3, -1.0e-3),
        (1.0, 0.0, 0.0, 0.0, 5.0e-3, -2.0e-3),
    ]
    return (
        _reaction("REAC_APPUI_G", 0.0, 0.0, dz_g)
        + _reaction("REAC_TOUS_G", 0.0, 0.0, dz_g)
        + _reaction("REAC_APPUI_Q", 0.0, 0.0, 50.0)
        + _reaction("REAC_TOUS_Q", 0.0, 0.0, 50.0)
        + _symmetry("G", rows)
        + _symmetry("Q", rows)
        + "  --- DIAGNOSTIC JOB : OK\n"
    )


def _run(project: Any, mess: str, tmp_path: Path) -> tuple[dict[str, Any], Path]:
    ctx = load_project(project.name, project.repo_root)
    mess_path = tmp_path / "fort.6"
    mess_path.write_text(mess, encoding="utf-8")
    comm = tmp_path / "barre.comm"
    comm.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    out = tmp_path / "controles"
    result = level_d_controls(
        ctx,
        mess_path=mess_path,
        comm_path=comm,
        mesh_path=project.directory / "maillage.med",
        out_dir=out,
    )
    return result, out


def test_a_balanced_model_passes_equilibrium_gravity_and_symmetry(
    fake_project: Factory, tmp_path: Path
) -> None:
    result, out = _run(fake_project(), _mess(), tmp_path)

    assert result["cases"]["G"]["verdict"] == "RÉUSSI"
    assert result["cases"]["Q"]["verdict"] == "RÉUSSI"
    assert result["cases"]["G"]["reaction_sum_all_nodes_n"]["DZ"] == 100.0
    assert result["spring_stiffness"] == {"n_nodes": 0}
    assert result["symmetry"]["G"]["n_pairs_checked"] == 1
    # le nœud du plan est sa propre image (même règle qu'au lot 33)
    assert result["symmetry"]["G"]["n_unmatched"] == 0
    summary = json.loads((out / "controles_d.json").read_text(encoding="utf-8"))
    assert summary["verdict"] == "RÉUSSI"
    assert summary["level"] == "D"
    assert summary["gravity"]["G"]["component"] == "DZ"
    assert summary["gravity"]["G"]["applied_n"] == -100.0
    # lot 45 : les verdicts portent les empreintes de ce qui a été contrôlé
    assert summary["provenance"] == {
        "mess_sha256": hashlib.sha256((tmp_path / "fort.6").read_bytes()).hexdigest(),
        "comm_sha256": hashlib.sha256(b"DEBUT()\nFIN()\n").hexdigest(),
    }
    text = (out / "controles_d.md").read_text(encoding="utf-8")
    assert "jamais une validation par comparaison à une référence" in text
    assert (out / "equilibre.json").read_text(encoding="utf-8").endswith("}\n")


def test_an_unbalanced_case_fails(fake_project: Factory, tmp_path: Path) -> None:
    result, out = _run(fake_project(), _mess(dz_g=90.0), tmp_path)

    assert result["cases"]["G"]["verdict"] == "ÉCHEC"
    assert result["cases"]["G"]["components"]["DZ"]["relative_gap"] == pytest.approx(
        -0.1
    )
    summary = json.loads((out / "controles_d.json").read_text(encoding="utf-8"))
    assert summary["verdict"] == "ÉCHEC"
    assert summary["gravity"]["G"]["verdict"] == "ÉCHEC"


def test_a_missing_reaction_table_is_named(
    fake_project: Factory, tmp_path: Path
) -> None:
    mess = _mess().replace("REAC_APPUI_Q", "AUTRE_TITRE")
    with pytest.raises(ProjectError, match="table de réactions REAC_APPUI_Q absente"):
        _run(fake_project(), mess, tmp_path)


def test_a_project_without_controls_is_refused(
    fake_project: Factory, tmp_path: Path
) -> None:
    project = fake_project()
    data = project.declaration()
    del data["controls"]
    data.pop("combinations")
    project.write_declaration(data)
    with pytest.raises(ProjectError, match="ne déclare aucun contrôle D"):
        _run(project, _mess(), tmp_path)


def test_only_blocked_components_enter_the_balance() -> None:
    controls = ControlsSection.model_validate(
        {
            "supports": [
                {"group": "A", "blocked": ["DX"], "table": "RA_{case}"},
                {"group": "B", "blocked": ["DZ"], "table": "RB_{case}"},
            ],
            "cases": [{"name": "G", "expected_resultant": {"DX": 0, "DY": 0, "DZ": 0}}],
        }
    )
    reactions = {
        "A": {"DX": 1.0, "DY": 7.0, "DZ": 3.0},
        "B": {"DX": 2.0, "DY": 0.0, "DZ": 5.0},
    }
    applied = {"DX": -1.0, "DY": 0.0, "DZ": -5.0}

    terms = balance_terms(controls, applied, applied, reactions, {})

    assert terms["DX"]["reactions_blocked_n"] == 1.0
    assert terms["DX"]["reactions_free_components_n"] == 2.0
    assert terms["DZ"]["balance_n"] == 0.0
    assert terms["DY"]["reactions_free_components_n"] == 7.0
    zero = balance_terms(
        controls,
        dict.fromkeys(applied, 0.0),
        dict.fromkeys(applied, 0.0),
        reactions,
        {},
    )
    assert math.isnan(zero["DX"]["relative_gap"])


def _spring_controls(direction: object) -> ControlsSection:
    return ControlsSection.model_validate(
        {
            "supports": [{"group": "P", "blocked": ["DZ"], "table": "RP_{case}"}],
            "springs": {
                "groups": ["K"],
                "direction": direction,
                "forces": "projet_fictif.ext:forces",
            },
            "cases": [{"name": "W", "expected_resultant": {"DX": 0, "DY": 0, "DZ": 0}}],
        }
    )


def test_springs_along_two_directions_enter_both_balances() -> None:
    # Lot 47 : ressorts horizontaux kx = ky, la force de chaque classe selon DX et DY.
    controls = _spring_controls(["DX", "DY"])
    reactions = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 10.0}}
    applied = {"DX": 4.0, "DY": -1.0, "DZ": -10.0}
    springs = {"K1": {"DX": 3.0, "DY": -0.5}, "K2": {"DX": 1.0, "DY": -0.5}}

    terms = balance_terms(controls, applied, applied, reactions, springs)

    assert terms["DX"]["springs_on_structure_n"] == -4.0
    assert terms["DY"]["springs_on_structure_n"] == 1.0
    assert terms["DZ"]["springs_on_structure_n"] == 0.0
    assert all(t["balance_n"] == 0.0 for t in terms.values())
    with pytest.raises(ProjectError, match="plusieurs directions"):
        balance_terms(controls, applied, applied, reactions, {"K1": 4.0})


def test_springs_along_one_direction_keep_their_single_sum() -> None:
    controls = _spring_controls("DY")
    reactions = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 0.0}}
    applied = {"DX": 0.0, "DY": 2.5, "DZ": 0.0}

    terms = balance_terms(controls, applied, applied, reactions, {"A": 2.0, "B": 0.5})

    assert terms["DY"]["balance_n"] == 0.0
    with pytest.raises(ProjectError, match="une seule direction"):
        balance_terms(controls, applied, applied, reactions, {"A": {"DY": 2.5}})


def test_repeated_spring_directions_are_refused() -> None:
    with pytest.raises(ValueError, match="répétées"):
        _spring_controls(["DX", "DX"])


def test_symmetry_about_an_offset_plane() -> None:
    plane = SymmetryPlane(normal="X", position=1.0, cases=("G",))
    tables = TableIndex(
        _symmetry(
            "G", [(0.5, 1.0, 0.0, 1e-3, 0.0, 0.0), (1.5, 1.0, 0.0, -1e-3, 1e-9, 0.0)]
        )
    )

    check = symmetry_check(tables, plane, "G")

    assert check["n_pairs_checked"] == 1
    assert check["worst_gap_m"] == pytest.approx(1e-9)
    assert check["worst_detail"]["dy_gap"] == pytest.approx(1e-9)


def test_find_table_reports_an_absent_title() -> None:
    with pytest.raises(KeyError, match="table introuvable : ABSENTE"):
        find_table(_mess(), "ABSENTE")
    assert find_table(_mess(), "REAC_APPUI_G")[0]["DZ"] == 100.0


def test_a_self_equilibrated_case_uses_its_declared_scale() -> None:
    # Lot 47 bis (CTL-005, version 2) : une charge nulle par construction (TE±)
    # rapporte son bilan à l'échelle déclarée par le projet, au lieu de NaN.
    controls = _spring_controls(["DX", "DY"])
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    reactions = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 2.0e-5}}
    springs = {"K1": {"DX": 5.0e5, "DY": 0.0}, "K2": {"DX": -5.0e5, "DY": 0.0}}
    scale = {"value_n": 1.0e6, "definition": "Σ |k·u|"}

    v1 = balance_terms(controls, zero, zero, reactions, springs)
    v2 = balance_terms(controls, zero, zero, reactions, springs, scale)

    assert math.isnan(v1["DZ"]["relative_gap"])
    assert v2["DZ"]["relative_gap"] == pytest.approx(2.0e-11)
    assert v2["DX"]["scale_n"] == 1.0e6 and v2["DX"]["scale_definition"] == "Σ |k·u|"
    assert "scale_n" not in v1["DX"]


def test_a_declared_scale_is_refused_on_a_loaded_case_or_if_not_positive() -> None:
    controls = _spring_controls(["DX", "DY"])
    reactions = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 10.0}}
    loaded = {"DX": 0.0, "DY": 0.0, "DZ": -10.0}
    zero = dict.fromkeys(loaded, 0.0)
    with pytest.raises(ProjectError, match="pas nulle"):
        balance_terms(
            controls, loaded, loaded, reactions, {}, {"value_n": 1.0, "definition": "x"}
        )
    with pytest.raises(ProjectError, match="non positive"):
        balance_terms(
            controls, zero, zero, reactions, {}, {"value_n": 0.0, "definition": "x"}
        )


def _absolute_controls() -> ControlsSection:
    return ControlsSection.model_validate(
        {
            "supports": [{"group": "P", "blocked": ["DZ"], "table": "RP_{case}"}],
            "springs": {
                "groups": ["K"],
                "direction": ["DX", "DY"],
                "forces": "projet_fictif.ext:forces",
            },
            "cases": [{"name": "W", "expected_resultant": {"DX": 0, "DY": 0, "DZ": 0}}],
            "absolute_threshold_n": 1.0,
        }
    )


def test_a_null_scale_is_judged_on_the_absolute_criterion() -> None:
    # Lot 51 ter (version 3) : un cas thermique sans effort (dilatation libre) a une
    # échelle de bruit numérique ; le rapport de deux bruits n'a pas de sens, le
    # critère devient absolu : Σ|F| ≤ 1 N.
    controls = _absolute_controls()
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    reactions = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 3.0e-8}}
    springs = {"K1": {"DX": 2.0e-9, "DY": 0.0}, "K2": {"DX": -1.0e-9, "DY": 0.0}}
    noise = {"value_n": 3.0e-9, "definition": "Σ |k·u|"}

    terms = balance_terms(controls, zero, zero, reactions, springs, noise)

    assert all(t["criterion"] == "absolu" for t in terms.values())
    assert math.isnan(terms["DZ"]["relative_gap"])
    assert terms["DZ"]["absolute_sum_n"] == pytest.approx(3.0e-8 + 3.0e-9)
    assert all(term_passes(t, controls.threshold) for t in terms.values())
    # Une échelle exactement nulle est admise sous le critère absolu.
    exact = balance_terms(
        controls, zero, zero, reactions, {}, {"value_n": 0.0, "definition": "x"}
    )
    assert exact["DZ"]["absolute_sum_n"] == pytest.approx(3.0e-8)


def test_the_absolute_criterion_fails_above_one_newton_and_spares_real_scales() -> None:
    controls = _absolute_controls()
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    loud = {"P": {"DX": 0.0, "DY": 0.0, "DZ": 2.5}}
    terms = balance_terms(
        controls, zero, zero, loud, {}, {"value_n": 0.5, "definition": "x"}
    )
    assert not term_passes(terms["DZ"], controls.threshold)
    # Une échelle réelle (au-dessus du seuil absolu) garde le critère relatif.
    real = balance_terms(
        controls,
        zero,
        zero,
        {"P": {"DX": 0.0, "DY": 0.0, "DZ": 2.0e-5}},
        {},
        {"value_n": 1.0e6, "definition": "x"},
    )
    assert "criterion" not in real["DZ"]
    assert real["DZ"]["relative_gap"] == pytest.approx(2.0e-11)
    assert worst_gap([math.nan, -3.0, 2.0]) == 3.0
    assert math.isnan(worst_gap([math.nan]))
