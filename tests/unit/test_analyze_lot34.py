"""Lot 34 : fonctions pures des scripts d'analyse de l'équilibre (aucun Docker,
aucun Code_Aster) -- lecture des tables du `.mess`, charge assemblée, écarts,
appariement des ressorts par bande."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from aster_expert.generation.springs import SpringClass

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "scripts" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


charge = _load("analyze_lot34_charge_assemblee")
equilibre = _load("analyze_lot34_equilibre")
ressorts = _load("analyze_lot34_ressorts")
report = _load("report_lot34")


def _table(title: str, columns: str, values: list[float], coords: bool = False) -> str:
    cells = " ".join(f"{v:.12E}" for v in values)
    return (
        "##ASTER 17.04.00 CONCEPT 00000001 CALCULE LE 24/09/2026 A 15:00:00\n"
        f"INTITULE RESU NOM_CHAM NUME_ORDRE INST {columns}\n"
        f"{title} 0000001b REAC_NODA 1 {0.0:.12E} {cells}\n\n"
    )


def test_assembled_load_is_the_opposite_of_the_summed_reactions() -> None:
    """Déplacements nuls : `REAC_NODA` = -(charge assemblée)."""
    mess = _table("CHARGE_G", "DX DY DZ", [1.0, -2.5e6, 3.0e5])
    assert charge.assembled_load(mess, "G") == pytest.approx(
        {"DX": -1.0, "DY": 2.5e6, "DZ": -3.0e5}
    )


def test_relative_gaps_are_scaled_by_the_largest_integrated_component() -> None:
    gaps = charge.relative_gaps(
        {"DX": 0.0, "DY": -1.0e6 + 5.0, "DZ": 0.0},
        {"DX": 0.0, "DY": -1.0e6, "DZ": 2.0e5},
    )
    assert gaps["DY"] == pytest.approx(5.0e-6)
    assert gaps["DZ"] == pytest.approx(-0.2)


def test_relative_gaps_of_a_case_without_any_load_are_absolute() -> None:
    gaps = charge.relative_gaps(
        {"DX": 0.0, "DY": 3.0, "DZ": 0.0}, {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    )
    assert gaps["DY"] == 3.0


def _class(
    name: str, band: str, k_mn: float, nodes: list[tuple[float, float, float]]
) -> SpringClass:
    return SpringClass(
        band=band, group_name=name, stiffness_mn_per_m=k_mn, nodes=tuple(nodes)
    )


def _springs_mess(rows: list[tuple[float, float, float, float]]) -> str:
    text = ""
    for x, y, z, dy in rows:
        cells = " ".join(f"{v:.12E}" for v in (x, y, z, dy))
        text += f"RESSORTS_G 0000001b DEPL 1 0.0E+00 {cells}\n"
    header = "INTITULE RESU NOM_CHAM NUME_ORDRE INST COOR_X COOR_Y COOR_Z DY\n"
    return "##ASTER 17.04.00 CONCEPT 00000002\n" + header + text + "\n"


def test_springs_are_summed_per_band_and_a_shared_node_counts_both() -> None:
    classes = [
        _class("A1", "RESS_AV_ARGI", 2.0, [(0.0, 0.0, -20.0), (0.0, 0.0, -18.0)]),
        _class("M1", "RESS_AV_MARNE", 3.0, [(0.0, 0.0, -18.0)]),
    ]
    mess = _springs_mess([(0.0, 0.0, -20.0, -0.5), (0.0, 0.0, -18.0, -0.25)])
    totals = equilibre.spring_by_band(mess, "G", classes)
    assert totals["RESS_AV_ARGI"] == pytest.approx(2.0e6 * (-0.5 - 0.25))
    assert totals["RESS_AV_MARNE"] == pytest.approx(3.0e6 * -0.25)


def test_a_missing_spring_row_is_an_error_not_a_silent_gap() -> None:
    classes = [_class("A1", "RESS_AV_ARGI", 2.0, [(0.0, 0.0, -20.0), (1.0, 0.0, 0.0)])]
    with pytest.raises(ValueError, match="absents de TAB_RESS"):
        equilibre.spring_by_band(_springs_mess([(0.0, 0.0, -20.0, -0.5)]), "G", classes)


def test_an_unknown_spring_row_is_an_error() -> None:
    classes = [_class("A1", "RESS_AV_ARGI", 2.0, [(0.0, 0.0, -20.0)])]
    with pytest.raises(ValueError, match="non retrouvé"):
        equilibre.spring_by_band(
            _springs_mess([(0.0, 0.0, -20.0, -0.5), (9.0, 9.0, 9.0, -0.5)]),
            "G",
            classes,
        )


def test_only_the_really_blocked_components_enter_the_sum() -> None:
    """`SYM_G`/`SYM_D` ne bloquent que DX ; `PIED_TUBES` que DZ ; seuls les
    ancrages bloquent les trois. Les réactions relevées sur une composante libre
    (forces de liaison de `LIAISON_SOLIDE`) ne se somment pas."""
    assert equilibre.BLOCKED["SYM_G"] == ("DX",)
    assert equilibre.BLOCKED["SYM_D"] == ("DX",)
    assert equilibre.BLOCKED["PIED_TUBES"] == ("DZ",)
    assert equilibre.BLOCKED["ANCRAGES"] == ("DX", "DY", "DZ")


def _row(x: float, y: float, z: float, dy: float) -> dict[str, float]:
    return {"COOR_X": x, "COOR_Y": y, "COOR_Z": z, "DY": dy}


def test_a_node_carrying_less_stiffness_than_read_is_reported() -> None:
    """Le défaut du lot 34 : sur un nœud partagé par deux bandes, Code_Aster
    n'appliquait qu'une des deux raideurs (ici k effectif 1,5 contre 2,5 lu)."""
    stiffness = {(0.0, 0.0, -18.0): 2.5e6, (0.0, 0.0, -20.0): 1.0e6}
    displacements = [_row(0.0, 0.0, -18.0, -0.01), _row(0.0, 0.0, -20.0, -0.02)]
    forces = [_row(0.0, 0.0, -18.0, -1.5e4), _row(0.0, 0.0, -20.0, -2.0e4)]
    result = ressorts.compare_spring_forces(displacements, forces, stiffness)
    assert result["n_mismatches"] == 1
    (bad,) = result["mismatches"]
    assert bad["node"] == (0.0, 0.0, -18.0)
    assert bad["k_effective_n_per_m"] == pytest.approx(1.5e6)
    assert result["sum_gap_n"] == pytest.approx(-1.5e4 + 2.5e4)


def test_springs_agree_when_the_forces_are_k_times_dy() -> None:
    stiffness = {(1.0, 2.0, 3.0): 4.0e5}
    result = ressorts.compare_spring_forces(
        [_row(1.0, 2.0, 3.0, -0.5)], [_row(1.0, 2.0, 3.0, -2.0e5)], stiffness
    )
    assert result["n_mismatches"] == 0
    assert result["sum_gap_n"] == pytest.approx(0.0)


def test_an_unknown_node_is_an_error_in_the_spring_force_comparison() -> None:
    with pytest.raises(ValueError, match="non retrouvé"):
        ressorts.compare_spring_forces(
            [_row(9.0, 9.0, 9.0, -0.5)], [], {(0.0, 0.0, 0.0): 1.0}
        )


def test_the_report_tables_are_generated_from_the_versioned_reports() -> None:
    text = report.full_report()
    assert "Modèle complet" in text
    assert "Pesanteur, cas G" in text
    assert text.count("| G |") >= 3  # une ligne G par table de sonde
    balance = report._load("equilibre_modele_complet.json")
    for case in ("G", "Q1", "EAU_P", "EAU_A"):
        assert balance["cases"][case]["verdict"] == "RÉUSSI"
        for c in report.COMPONENTS:
            assert abs(balance["cases"][case]["components"][c]["relative_gap"]) <= 1e-6
    for case, v in balance["symmetry"].items():
        assert v["worst_relative_gap"] <= 1e-6, case
