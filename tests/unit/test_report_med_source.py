"""Lot 36 : la synthèse relue dans le MED de résultats (`med_source`). Un maillage
synthétique de quelques mailles tient lieu du MED : la lecture par `medcoupling`
(conteneur) est hors des tests unitaires, seule la reconstitution des tables en
dépend."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aster_expert.report.build import _table_names
from aster_expert.report.med_read import med_field_name
from aster_expert.report.med_source import MedData, cross_check, med_tables

CASE = "G"


def _data() -> MedData:
    # 8 nœuds : 0..3 une facette de tube (plan Y = -0,71, X 0 -> 1, Z -1 -> 0),
    # 4..5 une poutre, 6 tirant, 7 ressort
    coords = np.array(
        [
            [0.0, -0.71, 0.0],
            [1.0, -0.71, 0.0],
            [1.0, -0.71, -1.0],
            [0.0, -0.71, -1.0],
            [0.0, 0.34, 3.3],
            [1.0, 0.34, 3.3],
            [0.0, 0.71, 2.5],
            [0.0, -0.71, -1.0],
        ]
    )
    depl = np.zeros((8, 6))
    depl[:, 1] = np.arange(8) * 1e-3
    reac = np.zeros((8, 6))
    reac[1] = [1.0, 2.0, 3.0, 0, 0, 0]
    reac[2] = [10.0, 20.0, 30.0, 0, 0, 0]
    name = med_field_name
    elno_comp = [
        "N",
        "VY",
        "VZ",
        "MT",
        "MFY",
        "MFZ",
        "NXX",
        "NYY",
        "NXY",
        "MXX",
        "MYY",
        "MXY",
        "QX",
        "QY",
    ]
    shell = np.zeros((4, 14))
    shell[:, 6] = [1.0, 2.0, 3.0, 4.0]  # NXX
    shell[:, 9] = [-1.0, -2.0, -3.0, -4.0]  # MXX
    line = np.zeros((4, 14))
    line[:, 0] = [5.0, 6.0, 7.0, 8.0]  # N (poutre puis tirant)
    palp = np.zeros((2, 8))
    palp[:, 0] = [11.0, 12.0]
    arrays = {
        name(CASE, "DEPL"): depl,
        name(CASE, "REAC_NODA"): reac,
        name(CASE, "FORC_NODA"): np.zeros((8, 6)),
        name(f"{CASE}_ET", "EFGE_ELNO") + "@0": shell,
        name(f"{CASE}_ET", "EFGE_ELNO") + "@0#cells": np.array([0]),
        name(f"{CASE}_ET", "EFGE_ELNO") + "@-1": line,
        name(f"{CASE}_ET", "EFGE_ELNO") + "@-1#cells": np.array([0, 1]),
        name(f"{CASE}_EP", "EFGE_NOEU"): palp,
        name(f"{CASE}_EP", "EFGE_NOEU") + "#nodes": np.array([0, 1]),
    }
    comps = {
        name(f"{CASE}_ET", "EFGE_ELNO"): elno_comp,
        name(f"{CASE}_EP", "EFGE_NOEU"): [
            "NXX",
            "NYY",
            "NXY",
            "MXX",
            "MYY",
            "MXY",
            "QX",
            "QY",
        ],
    }
    node_groups = {
        "TETE_TUBE_05": np.array([4]),
        "GEN_NOEUDS_TUBE_05": np.array([0, 1, 2, 3]),
        "GEN_NOEUDS_TUBE_01": np.array([0, 3]),
        "GEN_TOUS_PALPS": np.array([0, 1]),
        "ANCRAGES": np.array([6]),
        "PIED_TUBES": np.array([2, 3]),
        "SYM_G": np.array([0, 3]),
        "SYM_D": np.array([1, 2]),
    }
    return MedData(
        path=Path("synthetique.med"),
        coords=coords,
        conn={
            0: np.array([[0, 1, 2, 3]]),
            -1: np.array([[4, 5], [6, 4]]),
            -2: np.array([[7]]),
        },
        node_groups=node_groups,
        cell_groups={
            0: {"TUBES": np.array([0])},
            -1: {"POUTRE_COUR": np.array([0]), "TIRANTS": np.array([1])},
        },
        arrays=arrays,
        components=comps,
        cases=(CASE,),
    )


def _tables() -> dict[str, list[dict[str, float | str]]]:
    return med_tables(_data(), _table_names((CASE,), (5, 1)), profile_tubes=(5, 1))


def test_mesh_numbering_follows_the_file_order() -> None:
    data = _data()
    assert data.offset(0) == 0
    assert data.offset(-1) == 1  # après la maille de coque
    assert data.offset(-2) == 3
    with pytest.raises(ValueError, match="niveau de maillage inconnu"):
        data.offset(-3)


def test_node_field_completes_a_field_restricted_to_a_profile() -> None:
    data = _data()
    palp = data.arrays[med_field_name("G_EP", "EFGE_NOEU")]
    assert palp.shape == (2, 8)
    full = data.node_field(CASE, "DEPL")
    assert full.shape == (8, 6)
    assert full[3, 1] == pytest.approx(3e-3)


def test_tables_are_rebuilt_with_the_columns_the_synthesis_reads() -> None:
    tables = _tables()
    assert [r["DY"] for r in tables["RESSORTS_G"]] == [pytest.approx(7e-3)]
    assert tables["RESSORTS_G"][0]["NOEUD"] == "8"  # nœud MED 7 = N8 de Code_Aster
    head = tables["TETE_G"][0]
    assert (head["COOR_X"], head["COOR_Z"]) == (0.0, 3.3)
    assert head["DY"] == pytest.approx(4e-3)
    assert len(tables["DYT05_G"]) == 4 and len(tables["DYT01_G"]) == 2
    # efforts des tubes : une ligne par (maille, nœud local)
    rows = tables["EFTUBE_G"]
    assert [r["NXX"] for r in rows] == [1.0, 2.0, 3.0, 4.0]
    assert [r["MXX"] for r in rows] == [-1.0, -2.0, -3.0, -4.0]
    assert {r["MAILLE"] for r in rows} == {"1"}
    # poutre et tirants : deux nœuds par élément, dans l'ordre de la connectivité
    beam = tables["EFPOUT_G"]
    assert [(r["MAILLE"], r["NOEUD"], r["N"]) for r in beam] == [
        ("2", "5", 5.0),
        ("2", "6", 6.0),
    ]
    tie = tables["EFTIR_G"]
    assert [(r["NOEUD"], r["N"]) for r in tie] == [("7", 7.0), ("5", 8.0)]
    # palplanches : nœuds du groupe des palplanches seulement
    assert [r["NXX"] for r in tables["EFPALP_G"]] == [11.0, 12.0]


def test_reactions_are_the_sum_over_the_support_group() -> None:
    tables = _tables()
    pied = tables["REAC_PIED_G"][0]  # nœuds 2 et 3
    assert (pied["DX"], pied["DY"], pied["DZ"]) == (10.0, 20.0, 30.0)
    symd = tables["REAC_SYMD_G"][0]  # nœuds 1 et 2
    assert (symd["DX"], symd["DY"], symd["DZ"]) == (11.0, 22.0, 33.0)
    assert tables["REAC_ANCR_G"][0]["DY"] == 0.0


def test_cross_check_is_zero_for_identical_sources_and_sees_a_gap() -> None:
    tables = _tables()
    assert all(v == 0.0 for v in cross_check(tables, tables).values())
    other = {k: [dict(r) for r in rows] for k, rows in tables.items()}
    other["TETE_G"][0]["DY"] = 4.0e-3 * (1.0 + 1.0e-6)
    gaps = cross_check(tables, other)
    assert gaps["TETE_G"] == pytest.approx(1.0e-6 / (1.0 + 1.0e-6), rel=1e-3)
    assert gaps["RESSORTS_G"] == 0.0


def test_cross_check_refuses_a_different_number_of_rows() -> None:
    tables = _tables()
    short = {**tables, "TETE_G": []}
    with pytest.raises(ValueError, match="0 dans le .mess"):
        cross_check(tables, short)


def test_sorted_comparison_ignores_row_order() -> None:
    tables = _tables()
    shuffled = {k: list(reversed(rows)) for k, rows in tables.items()}
    assert max(cross_check(tables, shuffled).values()) == 0.0
