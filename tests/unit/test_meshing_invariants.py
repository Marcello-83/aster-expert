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
