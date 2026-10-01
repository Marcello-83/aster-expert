"""Lot 29 reproducer generator (`projets/quai_cw_test_01/scripts/build_lot29_repro.py`).

No Docker, no network: the executions themselves (level C) are reported in
`docs/essais_lot29.md`, not replayed here. These tests cover the mesh/comm
generator's own arithmetic and determinism, the same way
`tests/unit/test_build_fcoque_essai.py` covers lot 21's.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "projets" / "quai_cw_test_01" / "scripts" / "build_lot29_repro.py"

_spec = importlib.util.spec_from_file_location("build_lot29_repro", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["build_lot29_repro"] = _module
_spec.loader.exec_module(_module)


def test_nodes_per_layer_full_and_half_tube() -> None:
    assert _module.nodes_per_layer(facets=40, symmetry=False) == 40
    assert _module.nodes_per_layer(facets=40, symmetry=True) == 21


def test_total_layers_never_shorter_than_the_2m_default() -> None:
    assert _module.total_layers(n_springs=0, facets=40, symmetry=False) == 8
    assert _module.total_layers(n_springs=10, facets=40, symmetry=False) == 8


def test_total_layers_grows_with_spring_count() -> None:
    # 10000 springs / 40 nodes per layer -> 250 layers needed, +1 for TETE.
    assert _module.total_layers(n_springs=10000, facets=40, symmetry=False) == 251


def test_mesh_is_deterministic(tmp_path: Path) -> None:
    meta1 = _module.build_case(
        "x",
        n_springs=10,
        stiffness_n_per_m=1.0e6,
        symmetry=False,
        redundant_bc=False,
        output_dir=tmp_path,
    )
    meta2 = _module.build_case(
        "x",
        n_springs=10,
        stiffness_n_per_m=1.0e6,
        symmetry=False,
        redundant_bc=False,
        output_dir=tmp_path,
    )
    assert meta1["mesh_sha256"] == meta2["mesh_sha256"]
    assert meta1["comm_sha256"] == meta2["comm_sha256"]


def test_mesh_node_and_quad_counts_match_the_formula() -> None:
    mesh_text, meta = _module.build_mesh(n_springs=0, symmetry=False)
    nodes = re.findall(r"^N\d+ ", mesh_text, flags=re.M)
    quads = re.findall(r"^MA\d+ N\d+ N\d+ N\d+ N\d+$", mesh_text, flags=re.M)
    # +2 for the two beam nodes.
    assert len(nodes) == meta["n_tube_nodes"] + 2
    assert len(quads) == meta["n_quads"] == 8 * 40


def test_half_tube_ring_has_21_nodes_and_two_on_the_plane() -> None:
    mesh_text, meta = _module.build_mesh(n_springs=0, symmetry=True)
    assert meta["npl"] == 21
    assert meta["plan_x0_ring"] == 2
    tete_block = mesh_text.split("GROUP_NO\nTETE\n")[1].split("FINSF")[0]
    assert len(tete_block.split()) == 21


def test_redundant_bc_requires_symmetry() -> None:
    with pytest.raises(ValueError, match="symmetry"):
        _module.build_comm(
            n_springs=0, stiffness_n_per_m=1.0e6, symmetry=False, redundant_bc=True
        )


def test_no_springs_means_no_discret_or_crea_poi1() -> None:
    comm = _module.build_comm(
        n_springs=0, stiffness_n_per_m=1.0e6, symmetry=False, redundant_bc=False
    )
    assert "CREA_POI1" not in comm
    assert 'MODELISATION="DIS_T"' not in comm
    assert "DISCRET=" not in comm


def test_springs_use_crea_poi1_never_a_hand_written_poi1_cell() -> None:
    comm = _module.build_comm(
        n_springs=10, stiffness_n_per_m=1.0e6, symmetry=False, redundant_bc=False
    )
    assert "CREA_POI1" in comm
    assert 'MODELISATION="DIS_T"' in comm
    mesh_text, _ = _module.build_mesh(n_springs=10, symmetry=False)
    assert "\nPOI1\n" not in mesh_text


def test_symmetry_bc_excludes_ring_nodes_from_rotation_unless_redundant() -> None:
    fixed = _module.build_comm(
        n_springs=0, stiffness_n_per_m=1.0e6, symmetry=True, redundant_bc=False
    )
    redundant = _module.build_comm(
        n_springs=0, stiffness_n_per_m=1.0e6, symmetry=True, redundant_bc=True
    )
    assert 'GROUP_NO=("PLAN_X0_REST",), DRY=0.0, DRZ=0.0' in fixed
    assert 'GROUP_NO=("PLAN_X0",), DRY=0.0, DRZ=0.0' in redundant
    assert 'GROUP_NO=("PLAN_X0_REST",), DRY=0.0, DRZ=0.0' not in redundant


def test_comm_carries_the_liaison_solide_and_beam_load() -> None:
    comm = _module.build_comm(
        n_springs=0, stiffness_n_per_m=1.0e6, symmetry=False, redundant_bc=False
    )
    assert 'LIAISON_SOLIDE=_F(GROUP_NO=("TETE", "POUTRE_N"))' in comm
    assert 'MODELISATION="POU_D_E"' in comm
    assert comm.rstrip().endswith("FIN()")
    assert "..." not in comm


def test_export_stages_the_mesh_with_the_command_file() -> None:
    export = _module.build_export("repro")
    assert "F comm repro.comm D 1" in export
    assert "F mail repro.mail D 20" in export
