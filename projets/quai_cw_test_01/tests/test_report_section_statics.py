"""Lot 37 : forces extérieures du corps inférieur et bilan de statique, sur un maillage
synthétique d'une seule maille (pas de conteneur, pas de MED)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from quai_cw_test_01.generation.values import ModelValues
from quai_cw_test_01.report import section_statics as ss
from quai_cw_test_01.report.med_source import MedData
from quai_cw_test_01.report.quantities import SpringNode


class _FakeValues:
    """Le sous-ensemble de `ModelValues` que `lower_body_loads` lit."""

    def profile_si(self, key: str) -> list[tuple[float, float, str | None, str | None]]:
        return [(-30.0, 100.0, None, None), (10.0, 100.0, None, None)]

    def si(self, key: str) -> float:  # pragma: no cover - cas sans poids
        raise AssertionError(key)


def _values() -> ModelValues:
    return cast(ModelValues, _FakeValues())


def _med() -> MedData:
    # une maille de l'écran dans le plan Y = 0, x de 0 à 1, z de -13 à -12,
    # (la règle géométrique de `quad_pressure_force` oriente la normale vers +Y)
    coords = np.array(
        [
            [0.0, 0.0, -13.0],
            [1.0, 0.0, -13.0],
            [1.0, 0.0, -12.0],
            [0.0, 0.0, -12.0],
            [0.5, 0.0, -13.0],  # nœud à ressort (POI1)
            [0.5, 0.0, -12.0],  # nœud à ressort à la cote de la coupure
        ]
    )
    return MedData(
        path=Path("synthetic.med"),
        coords=coords,
        conn={
            0: np.array([[0, 1, 2, 3]]),
            -2: np.array([[4], [5]]),
        },
        node_groups={"PIED_TUBES": np.array([], dtype=np.int64)},
        cell_groups={
            0: {
                "ECRAN_POUSSEE": np.array([0]),
                "TUBES": np.array([], dtype=np.int64),
                "PALPS": np.array([0]),
            }
        },
        arrays={
            "EAU_P___DEPL": np.array(
                [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, -0.01, 0], [0, 0, 0]],
                dtype=float,
            ),
            "EAU_P___REAC_NODA": np.zeros((6, 3)),
        },
        components={},
        cases=("EAU_P",),
    )


def _springs() -> dict[tuple[float, float, float], SpringNode]:
    def node(z: float) -> SpringNode:
        return SpringNode(
            x=0.5,
            y=0.0,
            z=z,
            stiffness=1000.0,
            area=1.0,
            capacity_n=1.0e9,
            band_stiffness={"RESS_AV_ARGI": 1000.0},
        )

    return {(0.5, 0.0, -13.0): node(-13.0), (0.5, 0.0, -12.0): node(-12.0)}


def test_lower_body_loads_pressure_springs_and_their_moment() -> None:
    loads: dict[str, Any] = ss.lower_body_loads(
        _med(),
        _values(),
        "EAU_P",
        -12.0,
        _springs(),
        None,
    )
    # pression 100 Pa sur 1 m^2, normale +Y : force -100 selon Y (vers le bassin)
    assert loads["pression"][0] == pytest.approx(-100.0, rel=1e-12)
    # moment : (z - z_cut) F_y au centre de la maille (z = -12,5) : (-0,5)(-100) = +50
    assert loads["pression"][2] == pytest.approx(50.0, rel=1e-12)
    # ressorts : -k DY = +10 N (DY = -0,01), nœud à z = -13 : (-1)(10) ; le nœud de la
    # coupure (z = -12, DY = 0) ne porte rien
    assert loads["ressorts"][0] == pytest.approx(10.0, rel=1e-12)
    assert loads["ressorts"][2] == pytest.approx(-10.0, rel=1e-12)
    assert loads["pied"] == (0.0, 0.0, 0.0)
    assert loads["poids"] == (0.0, 0.0, 0.0)


def test_only_cells_below_the_cut_are_loaded_and_x_range_shares_them() -> None:
    above = ss.lower_body_loads(
        _med(),
        _values(),
        "EAU_P",
        -12.5,
        _springs(),
        None,
    )
    assert above["pression"][0] == 0.0  # la maille dépasse la coupure
    half = ss.lower_body_loads(
        _med(),
        _values(),
        "EAU_P",
        -12.0,
        _springs(),
        (0.0, 0.5),
    )
    assert half["pression"][0] == pytest.approx(-50.0, rel=1e-12)
    assert half["ressorts"][0] == pytest.approx(10.0, rel=1e-12)  # nœud à x = 0,5


def test_balance_gap_is_relative_to_the_larger_of_the_two() -> None:
    b = ss.balance(90.0, 100.0)
    assert b.absolute_gap == pytest.approx(10.0)
    assert b.relative_gap == pytest.approx(0.1)
    assert ss.balance(0.0, 0.0).relative_gap is None


def test_x_fraction_is_the_share_of_the_cell_inside_the_range() -> None:
    points = np.array([[0.0, 0, 0], [1.0, 0, 0], [1.0, 0, 1], [0.0, 0, 1]])
    assert ss._x_fraction(points, None) == 1.0
    assert ss._x_fraction(points, (0.25, 0.75)) == pytest.approx(0.5)
    assert ss._x_fraction(points, (2.0, 3.0)) == 0.0


def test_a_cut_through_spring_nodes_is_refused() -> None:
    with pytest.raises(ValueError, match="nœuds à ressort"):
        ss.section_statics(
            _med(),
            _values(),
            "EAU_P",
            -12.0,
            [0.0],
            _springs(),
        )
