"""Lot 33, étape 3 : résultante appliquée, intégrée sur la géométrie réelle
d'un maillage synthétique (aucun Docker, aucun Code_Aster) -- même esprit que
`tests/unit/test_meshing_invariants.py`."""

from __future__ import annotations

import pytest

from aster_expert.meshing.invariants import MedDump
from quai_cw_test_01.meshing.equilibrium import (
    group_pressure_resultant,
    quad_pressure_force,
)


def _square_dump(corners: list[tuple[float, float, float]]) -> MedDump:
    return MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": corners,
            "levels": {"0": {"types": ["NORM_QUAD4"], "connectivity": [[0, 1, 2, 3]]}},
            "groups": [{"name": "ECRAN", "level": 0, "ids": [0]}],
        }
    )


def test_uniform_pressure_on_a_unit_square_gives_area_times_pressure() -> None:
    """Carré unité dans le plan Y = 0 (X, Z), aire = 1 ; pression constante
    p = 10 : force = (0, -10, 0) -- signe FORCE_COQUE/PRES (U4.44.01),
    normale réorientée en Y >= 0 par ce module, donc la force pousse en -Y."""
    corners = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    fx, fy, fz = quad_pressure_force(corners, [(0.0, 10.0), (1.0, 10.0)])
    assert fx == pytest.approx(0.0, abs=1e-12)
    assert fy == pytest.approx(-10.0)
    assert fz == pytest.approx(0.0, abs=1e-12)


def test_the_normal_orientation_is_independent_of_the_winding_order() -> None:
    """Le même carré, décrit dans l'ordre inverse (winding opposé) : la
    règle de réorientation (Y >= 0) donne exactement la même force -- la
    méthode ne dépend donc pas de l'ordre de connectivité du MED source
    (jamais garanti conforme à ORIE_NORM_COQUE, voir le docstring du
    module)."""
    reversed_corners = (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 1.0),
        (1.0, 0.0, 0.0),
    )
    fx, fy, fz = quad_pressure_force(reversed_corners, [(0.0, 10.0), (1.0, 10.0)])
    assert fy == pytest.approx(-10.0)
    assert fx == pytest.approx(0.0, abs=1e-12)
    assert fz == pytest.approx(0.0, abs=1e-12)


def test_a_linear_profile_integrates_exactly_on_the_unit_square() -> None:
    """p(z) = z sur le carré unité (X in [0,1], Z in [0,1]) : intégrale de z
    sur le carré = 0,5 (aire 1, z moyen 0,5) -- force en Y = -0,5."""
    corners = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    _, fy, _ = quad_pressure_force(corners, [(0.0, 0.0), (1.0, 1.0)])
    assert fy == pytest.approx(-0.5)


def test_group_pressure_resultant_sums_every_cell_of_the_group() -> None:
    """Deux carrés unité côte à côte (X in [0,1] et [1,2], Z in [0,1]),
    pression constante 10 : résultante = (0, -20, 0)."""
    coords = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 0.0, 1.0),
        (0.0, 0.0, 1.0),
        (2.0, 0.0, 0.0),
        (2.0, 0.0, 1.0),
    ]
    dump = MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4", "NORM_QUAD4"],
                    "connectivity": [[0, 1, 2, 3], [1, 4, 5, 2]],
                }
            },
            "groups": [{"name": "ECRAN", "level": 0, "ids": [0, 1]}],
        }
    )
    fx, fy, fz = group_pressure_resultant(dump, "ECRAN", [(0.0, 10.0), (1.0, 10.0)])
    assert fx == pytest.approx(0.0, abs=1e-12)
    assert fy == pytest.approx(-20.0)
    assert fz == pytest.approx(0.0, abs=1e-12)


def test_group_pressure_resultant_refuses_a_non_quad4_cell() -> None:
    dump = MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0)],
            "levels": {"0": {"types": ["NORM_TRIA3"], "connectivity": [[0, 1, 2]]}},
            "groups": [{"name": "ECRAN", "level": 0, "ids": [0]}],
        }
    )
    with pytest.raises(ValueError, match="non QUAD4"):
        group_pressure_resultant(dump, "ECRAN", [(0.0, 1.0), (1.0, 1.0)])


def test_group_pressure_resultant_refuses_an_absent_group() -> None:
    dump = _square_dump(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0)]
    )
    with pytest.raises(ValueError, match="absent"):
        group_pressure_resultant(dump, "AUTRE", [(0.0, 1.0), (1.0, 1.0)])


_STEP_AT_THE_BOTTOM_EDGE = [(-1.0, 0.0), (-0.001, 0.0), (0.001, 100.0), (2.0, 100.0)]


def test_a_step_at_an_element_edge_is_read_differently_by_the_two_rules() -> None:
    """Un palier écrit comme une rampe de 2 mm exactement sur l'arête basse d'une
    maille (le doublement à 1 mm du générateur) : à l'intégration de Gauss la
    maille voit 100 partout ; évaluée aux nœuds, elle voit la valeur de mi-rampe
    (50) au nœud du bas et 100 en haut, soit 75 en moyenne. Code_Aster évalue
    la fonction de `FORCE_COQUE/PRES` aux nœuds (lot 34, nœud par nœud)."""
    corners = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    _, fy_gauss, _ = quad_pressure_force(corners, _STEP_AT_THE_BOTTOM_EDGE)
    _, fy_nodes, _ = quad_pressure_force(corners, _STEP_AT_THE_BOTTOM_EDGE, "nodes")
    assert fy_gauss == pytest.approx(-100.0)
    assert fy_nodes == pytest.approx(-75.0)


def test_the_two_rules_agree_on_a_profile_linear_across_the_element() -> None:
    corners = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    ramp = [(0.0, 10.0), (1.0, 20.0)]
    gauss = quad_pressure_force(corners, ramp)
    nodes = quad_pressure_force(corners, ramp, "nodes")
    assert nodes == pytest.approx(gauss)
    assert gauss[1] == pytest.approx(-30.0)  # -15 x aire 2


def test_group_resultant_takes_the_evaluation_rule() -> None:
    corners = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0)]
    dump = _square_dump(corners)
    _, gauss, _ = group_pressure_resultant(dump, "ECRAN", _STEP_AT_THE_BOTTOM_EDGE)
    _, nodes, _ = group_pressure_resultant(
        dump, "ECRAN", _STEP_AT_THE_BOTTOM_EDGE, "nodes"
    )
    assert gauss == pytest.approx(-100.0)
    assert nodes == pytest.approx(-75.0)
