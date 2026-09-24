"""Analytic module of the quay mesh (lot 27): parameters, counts, invariants.

The closed-form counts are confronted with an explicit enumeration of the nodes and
cells of the same structured mesh, built here node by node from the parameters
(a different route from the formulas). No Salome, no Docker.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml

from aster_expert.agent.model_data import load_model_data
from aster_expert.meshing.combiwall import (
    CombiwallMeshError,
    band_projected_width,
    build_params,
    expected_invariants,
    expected_masses,
    expected_segments,
    group_names,
    segment_count,
    spring_node_areas,
    tube_head_ring_points,
)
from aster_expert.meshing.invariants import Invariants

_ROOT = Path(__file__).resolve().parents[2]
_YAML = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"
_INVARIANTS = _ROOT / "data" / "examples" / "combiwall_mesh_invariants.yaml"
_PARAMS = _ROOT / "data" / "examples" / "lot27_maillage" / "params.json"


def _params() -> dict[str, Any]:
    return build_params(load_model_data(_YAML))


def _levels(low: float, high: float, size: float) -> list[float]:
    n = segment_count(high - low, size)
    return [low + (high - low) * i / n for i in range(n + 1)]


def _enumerate(params: dict[str, Any]) -> tuple[set[tuple[float, ...]], int, int]:
    """Nodes (rounded coordinates) and cell counts, by explicit construction."""
    t, s = params["tube"], params["palplanche"]
    size, r, n = params["taille_verticale"], t["rayon"], t["facettes"]

    def key(x: float, y: float, z: float) -> tuple[float, float, float]:
        return (round(x, 7) + 0.0, round(y, 7) + 0.0, round(z, 7) + 0.0)

    def zs(levels: list[float]) -> list[float]:
        out: list[float] = []
        for a, b in zip(levels[:-1], levels[1:], strict=True):
            out += _levels(a, b, size)[:-1]
        return [*out, levels[-1]]

    nodes: set[tuple[float, ...]] = set()
    quads = seg2 = 0
    z_tube, z_sheet = zs(t["cotes"]), zs(s["cotes"])
    for axe, (j0, j1) in zip(t["axes_x"], t["secteurs"], strict=True):
        ring = [
            (axe + r * math.cos(2 * math.pi * j / n), r * math.sin(2 * math.pi * j / n))
            for j in range(j0, j1 + 1)
        ]
        if j1 - j0 == n:
            ring = ring[:-1]
        nodes |= {key(x, y, z) for x, y in ring for z in z_tube}
        facets = j1 - j0
        quads += facets * (len(z_tube) - 1)
        seg2 += facets * len(t["cotes"])  # horizontal, one segment per facet
        seg2 += len(ring) * (len(z_tube) - 1)  # generatrices
    cols = s["segments_largeur"]
    for k in range(len(t["axes_x"]) - 1):
        x0 = t["axes_x"][k] + r
        x1 = t["axes_x"][k + 1] - r
        nodes |= {
            key(x0 + (x1 - x0) * c / cols, 0.0, z)
            for c in range(cols + 1)
            for z in z_sheet
        }
        quads += cols * (len(z_sheet) - 1)
        seg2 += cols * len(s["cotes"])
    p, b, ro = params["poutre"], params["tirants"], params["tirants"]
    bay = p["segments_par_entraxe"]
    for a, c in zip(t["axes_x"][:-1], t["axes_x"][1:], strict=True):
        nodes |= {key(a + (c - a) * i / bay, p["y"], p["z"]) for i in range(bay + 1)}
        seg2 += bay
    for axe in t["axes_x"]:
        for i in range(ro["segments"] + 1):
            f = i / ro["segments"]
            nodes.add(
                key(
                    axe,
                    b["debut_y"] + (b["fin_y"] - b["debut_y"]) * f,
                    b["debut_z"] + (b["fin_z"] - b["debut_z"]) * f,
                )
            )
        seg2 += ro["segments"]
    return nodes, quads, seg2


def test_segment_count_is_an_explicit_integer_rule() -> None:
    assert segment_count(8.0, 0.25) == 32
    assert segment_count(0.1, 0.25) == 1  # never zero
    assert segment_count(0.125, 0.25) == 1  # half-way rounds up
    assert segment_count(0.375, 0.25) == 2
    assert segment_count(0.10000000000000009, 0.25) == 1
    with pytest.raises(CombiwallMeshError):
        segment_count(0.0, 0.25)


def test_closed_form_counts_match_an_explicit_enumeration() -> None:
    params = _params()
    nodes, quads, seg2 = _enumerate(params)
    counts = expected_invariants(params)["counts"]
    assert counts["nodes"] == len(nodes) == 40114
    assert counts["cells"] == {"QUAD4": quads, "SEG2": seg2}
    assert (quads, seg2) == (40120, 39583)


def test_segments_per_edge_type() -> None:
    seg = expected_segments(_params())
    vertical = seg["aretes_verticales_tube_et_palplanche"]
    assert [v["segments"] for v in vertical.values()] == [32, 24, 52, 4, 2, 1]
    assert seg["aretes_horizontales_facette"]["segments"] == 1
    assert seg["aretes_horizontales_palplanche"]["segments"] == 5
    assert seg["aretes_poutre"]["segments"] == 8
    assert seg["aretes_tirant"]["segments"] == 1


def test_the_convention_has_58_groups_and_the_invariants_cover_them_all() -> None:
    params = _params()
    names = group_names(params)
    assert len(names["maille"]) + len(names["noeud"]) == 58
    inv = expected_invariants(params)
    assert sorted(g["name"] for g in inv["groups"]) == sorted(
        names["maille"] + names["noeud"]
    )
    Invariants.model_validate(inv)  # the schema of `mesh check` accepts it


def test_pied_tubes_is_the_foot_ring_of_every_tube() -> None:
    """Decision 12 (point 11, lot 28): 7 full tubes (40 nodes) + 2 half tubes
    (21 nodes each) = 322, all at Z = -26.00 (the only level any node sits at)."""
    inv = expected_invariants(_params())
    (group,) = [g for g in inv["groups"] if g["name"] == "PIED_TUBES"]
    assert group["kind"] == "node"
    assert group["count"] == 322 == 7 * 40 + 2 * 21
    assert group["bbox"][4] == group["bbox"][5] == -26.00
    (plane,) = [p for p in inv["plane_nodes"] if p["group"] == "PIED_TUBES"]
    assert plane["axis"] == "z" and plane["value"] == -26.00


def test_tube_head_ring_points_match_the_tete_tube_group() -> None:
    """Lot 31, étape 2: `tube_head_ring_points` (junction candidates) must
    enumerate exactly the `TETE_TUBE_<k>` node group `expected_invariants`
    already counts and bounds, for a full tube (05, 40 nodes) and a half
    tube at a plan of symmetry (01, 21 nodes)."""
    params = _params()
    inv = expected_invariants(params)
    for number, name in ((5, "TETE_TUBE_05"), (1, "TETE_TUBE_01")):
        (group,) = [g for g in inv["groups"] if g["name"] == name]
        points = tube_head_ring_points(params, number)
        assert len(points) == group["count"]
        assert len({round(p[2], 9) for p in points}) == 1
        z_head = points[0][2]
        assert z_head == group["bbox"][4] == group["bbox"][5]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        assert min(xs) == pytest.approx(group["bbox"][0])
        assert max(xs) == pytest.approx(group["bbox"][1])
        assert min(ys) == pytest.approx(group["bbox"][2])
        assert max(ys) == pytest.approx(group["bbox"][3])
        assert len(
            {(round(x, 9), round(y, 9)) for x, y in zip(xs, ys, strict=True)}
        ) == len(points)


def test_geometric_controls_of_the_specification() -> None:
    inv = expected_invariants(_params())
    widths = {w["z"] < -18: w["width"] for w in inv["projected_widths"]}
    assert widths[False] == pytest.approx(20.80, abs=1e-12)
    assert widths[True] == pytest.approx(11.36, abs=1e-12)
    (area,) = inv["group_areas"]
    assert area["reference_area"] == pytest.approx(2 * math.pi / 4 * 0.71)
    assert area["area"] - area["reference_area"] == pytest.approx(-0.001146, abs=1e-6)
    assert area["area"] == pytest.approx(10 * 2 * 0.71 * math.sin(math.pi / 40))


def test_the_masses_are_areas_and_lengths() -> None:
    masses = expected_masses(_params())
    assert masses["POUTRE_COUR"] == {"kind": "beam", "mass": pytest.approx(20.8)}
    assert masses["PALP_01"]["mass"] == pytest.approx(1.18 * 20.6)
    assert masses["TUBE_05"]["mass"] == pytest.approx(
        40 * 2 * 0.71 * math.sin(math.pi / 40) * 28.6
    )
    assert masses["TUBE_01"]["mass"] == pytest.approx(masses["TUBE_05"]["mass"] / 2)
    assert masses["ECRAN"]["mass"] == pytest.approx(
        masses["TUBES"]["mass"] + masses["PALPS"]["mass"]
    )


def test_band_projected_width_matches_the_generator_own_former_constants() -> None:
    """Lot 30, étape 2 : `aster_expert.generation.generate` hardcodait ces deux
    largeurs (20,80 m / 11,36 m) pour `check_spring_sum` -- valeurs propres au
    quai complet (huit entraxes), fausses pour toute autre tranche. Cette
    fonction les reproduit analytiquement à partir des mêmes paramètres."""
    params = _params()
    argi = params["bandes"]["RESS_AV_ARGI"]
    marne = params["bandes"]["RESS_AV_MARNE"]
    assert band_projected_width(params, argi) == pytest.approx(20.80)
    assert band_projected_width(params, marne) == pytest.approx(11.36)


def test_the_versioned_files_are_those_of_the_module() -> None:
    import json

    params = _params()
    assert json.loads(_PARAMS.read_text("utf-8")) == json.loads(json.dumps(params))
    text = _INVARIANTS.read_text("utf-8")
    assert yaml.safe_load(text) == yaml.safe_load(
        yaml.safe_dump(expected_invariants(params), sort_keys=False)
    )


def test_spring_node_areas_sum_to_the_projected_band_area() -> None:
    """Decision 5 / point 4 (lot 28): Sigma of the nodal tributary areas of each
    band equals its projected width (bassin side, by symmetry with the terre
    side already checked in `test_geometric_controls_of_the_specification`)
    times its height -- a closed-form identity, independent of mesh density."""
    areas = spring_node_areas(_params())
    assert sum(areas["RESS_AV_ARGI"].values()) == pytest.approx(20.80 * 6.00)
    assert sum(areas["RESS_AV_MARNE"].values()) == pytest.approx(11.36 * 8.00)
    # every node lies at Y <= 0 (bassin side only) with a tiny numeric slack for
    # the vertex() trig round-off cleaned by combiwall_mesh.py's own `clean()`
    for band in areas.values():
        assert all(y <= 1e-9 for _, y, _ in band)
    # no negative or zero-area entry: `add()` never creates a spurious node
    assert all(v > 0 for band in areas.values() for v in band.values())


def test_spring_node_areas_share_the_lock_line_node_once() -> None:
    """A lock-line node (tube generatrix at angle 180 degrees, Y = 0) is shared
    between a tube's own bassin-side quads and its neighbouring sheet-pile's
    quads: removing the sheet-pile's contribution (`avec_palplanches=False`)
    changes exactly the lock-line nodes' value, never a tube-interior node far
    from any lock line -- confirming the two contributions are summed onto one
    entry, not kept apart or double-counted."""
    params = _params()
    radius = params["tube"]["rayon"]
    axis2 = params["tube"]["axes_x"][1]
    with_sheets = spring_node_areas(params)["RESS_AV_ARGI"]

    without_sheets_params = {
        **params,
        "bandes": {
            **params["bandes"],
            "RESS_AV_ARGI": {
                **params["bandes"]["RESS_AV_ARGI"],
                "avec_palplanches": False,
            },
        },
    }
    without_sheets = spring_node_areas(without_sheets_params)["RESS_AV_ARGI"]

    lock_key = (round(axis2 - radius, 9), 0.0, -15.0)
    assert lock_key in with_sheets and lock_key in without_sheets
    assert with_sheets[lock_key] > without_sheets[lock_key]

    # the tube's own bassin-most generatrix (opposite the locks): untouched
    basin_key = (round(axis2, 9), round(-radius, 9), -15.0)
    assert basin_key in with_sheets and basin_key in without_sheets
    assert with_sheets[basin_key] == pytest.approx(without_sheets[basin_key])


def test_inconsistent_data_are_refused(tmp_path: Path) -> None:
    raw = yaml.safe_load(_YAML.read_text("utf-8"))
    raw["groups"]["maillage"]["nombre_facettes_par_tube"]["value"] = 42
    bad = tmp_path / "d.yaml"
    bad.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(CombiwallMeshError, match="multiple de 4"):
        build_params(load_model_data(bad))
    raw["groups"]["maillage"]["nombre_facettes_par_tube"]["value"] = 40
    raw["groups"]["maillage"]["cotes_imposees"]["value"] = [
        -26.0,
        -18.0,
        -12.0,
        2.0,
        2.5,
        2.6,
    ]
    bad.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(CombiwallMeshError, match="cote imposée"):
        build_params(load_model_data(bad))


def test_the_build_script_reproduces_every_versioned_file() -> None:
    import importlib.util

    path = _ROOT / "scripts" / "build_lot27_maillage.py"
    spec = importlib.util.spec_from_file_location("build_lot27_maillage", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for target, content in module.files().items():
        assert target.read_text("utf-8") == content, target.name
