"""Invariants of a MED mesh, evaluated on synthetic dumps (lot 26).

No Docker, no Salome: the dump is a plain structure, built here by hand for two
quadrangles sharing an edge, a bar starting from one of their nodes, and the
same mesh with the bar's start node superposed but not merged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.meshing.errors import MeshCheckError
from aster_expert.meshing.invariants import (
    Invariants,
    MedDump,
    evaluate,
    find_coincident_pairs,
    format_report,
    load_invariants,
)

# Two unit quadrangles side by side (nodes 0..5), one bar from node 1 downwards.
_COORDS = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (2.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (1.0, 1.0, 0.0),
    (2.0, 1.0, 0.0),
]


def _dump(
    *, bar_start: int = 1, extra_coords: tuple[tuple[float, float, float], ...] = ()
) -> MedDump:
    coords = [*_COORDS, (1.0, 0.0, -1.0), *extra_coords]
    return MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4", "NORM_QUAD4"],
                    "connectivity": [[0, 1, 4, 3], [1, 2, 5, 4]],
                },
                "-1": {"types": ["NORM_SEG2"], "connectivity": [[bar_start, 6]]},
            },
            "groups": [
                {"name": "LEFT", "level": 0, "ids": [0]},
                {"name": "RIGHT", "level": 0, "ids": [1]},
                {"name": "BAR", "level": -1, "ids": [0]},
                {"name": "TOP", "level": 1, "ids": [3, 4, 5]},
            ],
        }
    )


def _invariants(**overrides: object) -> Invariants:
    data: dict[str, object] = {
        "schema_version": 1,
        "counts": {"nodes": 7, "cells": {"QUAD4": 2, "SEG2": 1}},
        "groups": [
            {
                "name": "LEFT",
                "count": 1,
                "cell_type": "QUAD4",
                "bbox": [0, 1, 0, 1, 0, 0],
            },
            {"name": "TOP", "kind": "node", "count": 3},
        ],
        "nodes_at": [{"label": "corner", "point": [2, 1, 0]}],
        "shared_nodes": [
            {
                "label": "edge",
                "groups": ["LEFT", "RIGHT"],
                "count": 2,
                "at": [[1, 0, 0]],
            },
            {"label": "bar", "groups": ["BAR", "LEFT"], "count": 1, "at": [[1, 0, 0]]},
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": 1e-9},
    }
    data.update(overrides)
    return Invariants.model_validate(data)


def test_a_consistent_mesh_holds_every_invariant() -> None:
    results = evaluate(_dump(), _invariants())
    assert all(r.ok for r in results), [r for r in results if not r.ok]
    assert len(results) >= 12


def test_a_superposed_unmerged_node_is_detected_twice() -> None:
    """The bar starts from a node superposed on node 1, not from node 1."""
    dump = _dump(bar_start=7, extra_coords=((1.0, 0.0, 0.0),))
    failed = {r.label for r in evaluate(dump, _invariants()) if not r.ok}
    assert "nœuds partagés BAR / LEFT (bar)" in failed
    assert "paires de nœuds à moins de 1e-09" in failed


def test_orphan_nodes_are_reported() -> None:
    dump = _dump(extra_coords=((5.0, 5.0, 5.0),))
    results = evaluate(dump, _invariants(counts=None))
    orphan = next(r for r in results if r.kind == "nœuds orphelins")
    assert not orphan.ok and "1" in orphan.obtained


def test_missing_group_and_wrong_type_and_bbox_are_reported() -> None:
    inv = _invariants(
        counts=None,
        groups=[
            {"name": "ABSENT", "count": 1},
            {"name": "LEFT", "cell_type": "SEG2", "bbox": [0, 2, 0, 1, 0, 0]},
        ],
        nodes_at=[],
        shared_nodes=[],
        no_orphan_nodes=False,
        no_coincident_nodes=None,
    )
    by_label = {r.label: r for r in evaluate(_dump(), inv)}
    assert not by_label["groupe ABSENT : présence"].ok
    assert not by_label["groupe LEFT : type des mailles"].ok
    bbox = next(r for k, r in by_label.items() if "boîte englobante" in k)
    assert not bbox.ok


def test_node_at_a_missing_position_is_reported() -> None:
    inv = _invariants(
        counts=None,
        groups=[],
        shared_nodes=[],
        nodes_at=[{"label": "nowhere", "point": [9, 9, 9]}],
    )
    (result,) = [r for r in evaluate(_dump(), inv) if r.kind == "nœud imposé"]
    assert not result.ok


def test_tolerance_is_honoured_for_coincident_nodes() -> None:
    coords = tuple((float(i), 0.0, 0.0) for i in range(3))
    assert find_coincident_pairs(coords, 0.1) == []
    close = (*coords, (1.05, 0.0, 0.0))
    assert find_coincident_pairs(close, 0.1) == [(1, 3)]
    assert find_coincident_pairs(close, 0.01) == []


def test_report_lists_every_invariant_and_names_the_first_failure() -> None:
    results = evaluate(
        _dump(bar_start=7, extra_coords=((1.0, 0.0, 0.0),)), _invariants()
    )
    text = format_report("m.med", results)
    assert text.count("[OK    ]") + text.count("[ÉCART ]") == len(results)
    assert "PREMIER INVARIANT NON TENU" in text
    ok_text = format_report("m.med", evaluate(_dump(), _invariants()))
    assert "Tous les invariants sont tenus." in ok_text


def test_invalid_or_missing_invariants_files_are_refused(tmp_path: Path) -> None:
    with pytest.raises(MeshCheckError, match="not found"):
        load_invariants(tmp_path / "absent.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("schema_version: 1\nunknown_key: 3\n", encoding="utf-8")
    with pytest.raises(MeshCheckError, match="invalid"):
        load_invariants(bad)


# --- lot 27 invariants: areas, projected widths, subsets, planes, symmetry ---------

_INV_BASE = {"schema_version": 1}


def _wall_dump() -> MedDump:
    """Two vertical quadrangles in the plane Y = 0 (x in [-1, 0] and [0, 1], z in
    [0, 2]) and a third one folded at 45 degrees (x in [1, 2], y in [0, 1], z in
    [0, 2]) : projected on Y = 0 it is 1 wide, developed it is sqrt(2) * 2 in area."""
    coords = [
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 2.0),
        (0.0, 0.0, 2.0),
        (1.0, 0.0, 2.0),
        (2.0, 1.0, 0.0),
        (2.0, 1.0, 2.0),
    ]
    return MedDump.model_validate(
        {
            "mesh_name": "wall",
            "space_dimension": 3,
            "coords": coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4"] * 3,
                    "connectivity": [[0, 1, 4, 3], [1, 2, 5, 4], [2, 6, 7, 5]],
                }
            },
            "groups": [
                {"name": "WALL", "level": 0, "ids": [0, 1, 2]},
                {"name": "FOLD", "level": 0, "ids": [2]},
                {"name": "PLANE", "level": 1, "ids": [2, 5]},
                {"name": "PLANE_BAD", "level": 1, "ids": [2]},
            ],
        }
    )


def _run(dump: MedDump, **spec: object) -> list[bool]:
    invariants = Invariants.model_validate({**_INV_BASE, **spec})
    return [r.ok for r in evaluate(dump, invariants)]


def test_the_developed_area_and_its_gap_to_a_reference_are_checked() -> None:
    dump = _wall_dump()
    total = 2.0 + 2.0 + 2.0 * 2**0.5  # two 1 x 2 walls, one 45-degree fold
    hit = {"group": "WALL", "area": total, "tolerance": 1e-9, "reference_area": 6.0}
    assert _run(dump, group_areas=[hit]) == [True, True]
    miss = {**hit, "area": total + 1e-3}
    assert _run(dump, group_areas=[miss]) == [False, False]
    assert _run(dump, group_areas=[{**hit, "group": "ABSENT"}]) == [False]


def test_the_projected_width_counts_the_projection_not_the_developed_width() -> None:
    dump = _wall_dump()
    spec = {"label": "band", "group": "WALL", "z": 1.0, "tolerance": 1e-9}
    # 1 + 1 + (the fold: x from 1 to 2 and y from 0 to 1 -> projected width 1)
    assert _run(dump, projected_widths=[{**spec, "width": 3.0}]) == [True]
    # the developed width of the fold, 2**0.5, is not what is asked
    assert _run(dump, projected_widths=[{**spec, "width": 2.0 + 2**0.5}]) == [False]
    # a level above the cells counts nothing: width 0, so 3 is a mismatch
    assert _run(dump, projected_widths=[{**spec, "z": 5.0, "width": 3.0}]) == [False]


def test_a_subset_is_an_inclusion_of_cells() -> None:
    dump = _wall_dump()
    assert _run(dump, subsets=[{"group": "FOLD", "of": "WALL"}]) == [True]
    assert _run(dump, subsets=[{"group": "WALL", "of": "FOLD"}]) == [False]


def test_a_node_group_must_be_the_whole_set_of_nodes_of_its_plane() -> None:
    dump = _wall_dump()
    spec = {"axis": "z", "value": 0.0, "tolerance": 1e-9}
    # nodes 0, 1, 2, 6 are at z = 0; PLANE has 2 and 5 (z = 2): not the plane
    assert _run(dump, plane_nodes=[{**spec, "group": "PLANE"}]) == [False]
    assert _run(dump, plane_nodes=[{**spec, "group": "ABSENT"}]) == [False]
    top = {"axis": "z", "value": 2.0, "tolerance": 1e-9, "group": "PLANE"}
    assert _run(dump, plane_nodes=[top]) == [False]  # 3 nodes at z = 2, group has 2


def test_the_x_symmetry_is_checked_on_every_node() -> None:
    sym = MedDump.model_validate(
        {
            "mesh_name": "s",
            "space_dimension": 3,
            "coords": [(-1.0, 2.0, 3.0), (1.0, 2.0, 3.0), (0.0, 0.0, 0.0)],
            "levels": {"0": {"types": ["NORM_TRI3"], "connectivity": [[0, 1, 2]]}},
            "groups": [],
        }
    )
    spec = {"symmetry": {"tolerance": 1e-9}}
    assert _run(sym, **spec) == [True]
    assert _run(_wall_dump(), **spec) == [False]
    shifted = sym.model_copy(
        update={"coords": ((-1.0, 2.0, 3.0), (1.0, 2.0, 3.001), (0.0, 0.0, 0.0))}
    )
    assert _run(shifted, **spec) == [False]


def _mirrored_quads_dump() -> MedDump:
    """Two QUAD4 mailles, image miroir l'une de l'autre par rapport à
    X = 0, partageant leur arête commune (x = 0)."""
    coords = (
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (-1.0, 1.0, 0.0),
    )
    return MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4", "NORM_QUAD4"],
                    "connectivity": [[0, 1, 2, 3], [0, 4, 5, 3]],
                }
            },
            "groups": [],
        }
    )


def test_lot33_connectivity_symmetry_holds_for_a_mirrored_pair_of_quads() -> None:
    """Lot 33, étape 4 : deux mailles QUAD4 en miroir exact -- le nœud ET la
    connectivité se correspondent."""
    spec = {"symmetry": {"tolerance": 1e-9, "check_connectivity": True}}
    assert _run(_mirrored_quads_dump(), **spec) == [True, True]


def test_lot33_connectivity_symmetry_fails_when_a_cell_has_no_mirror() -> None:
    """Les nœuds restent en miroir mais une des deux mailles est un
    triangle, sans correspondance de type -- la connectivité échoue même si
    la seule condition sur les nœuds réussit encore."""
    broken = MedDump.model_validate(
        {
            "mesh_name": "m",
            "space_dimension": 3,
            "coords": _mirrored_quads_dump().coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4", "NORM_TRI3"],
                    "connectivity": [[0, 1, 2, 3], [0, 4, 3]],
                }
            },
            "groups": [],
        }
    )
    spec = {"symmetry": {"tolerance": 1e-9, "check_connectivity": True}}
    assert _run(broken, **spec) == [True, False]


def test_the_model_bbox_and_node_group_kinds_of_shared_nodes() -> None:
    dump = _wall_dump()
    assert _run(dump, bbox=[-1, 2, 0, 1, 0, 2]) == [True]
    assert _run(dump, bbox=[-1, 2, 0, 1, 0, 3]) == [False]
    # a node group against a cell group: PLANE (nodes 2, 5) and FOLD (nodes 2, 6, 7, 5)
    shared = {
        "label": "kinds",
        "groups": ["PLANE", "FOLD"],
        "kinds": ["node", "cell"],
        "count": 2,
    }
    assert _run(dump, shared_nodes=[shared]) == [True]
    assert _run(dump, shared_nodes=[{**shared, "kinds": ["cell", "cell"]}]) == [False]


# --- lot 35 : invariant de couche (charge de poussée par couche) -------------


def _wall(z_levels: list[float]) -> MedDump:
    """Un mur vertical de quadrangles empilés (plan Y = 0), un par intervalle."""
    coords = [(x, 0.0, z) for z in z_levels for x in (0.0, 1.0)]
    conn = [[2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2] for k in range(len(z_levels) - 1)]
    return MedDump.model_validate(
        {
            "mesh_name": "wall",
            "space_dimension": 3,
            "coords": coords,
            "levels": {
                "0": {"types": ["NORM_QUAD4"] * len(conn), "connectivity": conn}
            },
            "groups": [{"name": "ECRAN", "level": 0, "ids": list(range(len(conn)))}],
        }
    )


def _bands(levels: list[float]) -> Invariants:
    return Invariants.model_validate(
        {
            "schema_version": 1,
            "layer_bands": [{"group": "ECRAN", "levels": levels, "tolerance": 1e-9}],
        }
    )


def test_lot35_layers_aligned_on_the_rows_hold() -> None:
    results = evaluate(_wall([0.0, 1.0, 2.0, 3.0, 4.0]), _bands([0.0, 2.0, 4.0]))

    assert all(r.ok for r in results), [r for r in results if not r.ok]
    kinds = {r.kind for r in results}
    assert kinds == {"couches"}
    # deux couches bordées exactement, plus les deux contrôles globaux
    assert len(results) == 4


def test_lot35_a_top_layer_above_the_group_is_bordered_by_the_group_head() -> None:
    results = evaluate(_wall([0.0, 1.0, 2.0]), _bands([0.0, 1.0, 5.0]))

    assert all(r.ok for r in results), [r for r in results if not r.ok]
    assert "[1, 1]" not in results[-1].expected
    assert results[-1].expected == "[1, 2]"


def test_lot35_altered_mesh_with_a_cell_straddling_an_interface_is_rejected() -> None:
    """Altération : une rangée décalée de 0,5 m fait chevaucher l'interface z = 2."""
    results = evaluate(_wall([0.0, 1.0, 2.5, 3.5, 4.0]), _bands([0.0, 2.0, 4.0]))

    failed = [r for r in results if not r.ok]
    assert failed
    assert failed[0].label.startswith("couches de ECRAN : mailles à cheval")
    assert failed[0].obtained == "1"


def test_lot35_a_cell_outside_the_layers_is_rejected() -> None:
    results = evaluate(_wall([0.0, 1.0, 2.0, 3.0, 4.0]), _bands([0.0, 2.0, 3.0]))

    assert any(not r.ok and "hors de" in r.label for r in results)


def test_lot35_a_layer_not_bordered_by_its_levels_is_rejected() -> None:
    """Une rangée manque (z de 2 à 3) : la couche [2, 4] ne commence qu'à 3."""
    full = _wall([0.0, 1.0, 2.0, 3.0, 4.0])
    gap = MedDump.model_validate(
        {
            "mesh_name": "wall",
            "space_dimension": 3,
            "coords": full.coords,
            "levels": {
                "0": {
                    "types": ["NORM_QUAD4"] * 3,
                    "connectivity": [
                        full.levels["0"].connectivity[k] for k in (0, 1, 3)
                    ],
                }
            },
            "groups": [{"name": "ECRAN", "level": 0, "ids": [0, 1, 2]}],
        }
    )

    results = evaluate(gap, _bands([0.0, 2.0, 4.0]))

    failed = [r for r in results if not r.ok]
    assert len(failed) == 1
    assert "couche [2, 4]" in failed[0].label
    assert failed[0].expected == "[2, 4]"
    assert failed[0].obtained == "[3, 4]"
