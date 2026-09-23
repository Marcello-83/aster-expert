"""Lot 29 two-unit extension (`scripts/build_lot29_repro_two_units.py`).

No Docker, no network -- see `docs/essais_lot29.md` for the executions
themselves (E0_two_units, level C).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "build_lot29_repro_two_units.py"

_spec = importlib.util.spec_from_file_location("build_lot29_repro_two_units", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["build_lot29_repro_two_units"] = _module
_spec.loader.exec_module(_module)


def test_mesh_is_deterministic(tmp_path: Path) -> None:
    meta1 = _module.build_case(
        "x", n_springs_total=100, stiffness_n_per_m=1.0e6, output_dir=tmp_path
    )
    meta2 = _module.build_case(
        "x", n_springs_total=100, stiffness_n_per_m=1.0e6, output_dir=tmp_path
    )
    assert meta1["mesh_sha256"] == meta2["mesh_sha256"]
    assert meta1["comm_sha256"] == meta2["comm_sha256"]


def test_the_two_units_never_share_a_node_name() -> None:
    mesh_text, _ = _module.build_mesh(n_springs_total=100)
    names_a = set(re.findall(r"^(NA\S*) ", mesh_text, flags=re.M))
    names_b = set(re.findall(r"^(NB\S*) ", mesh_text, flags=re.M))
    assert names_a
    assert names_b
    assert names_a.isdisjoint(names_b)


def test_springs_are_split_between_the_two_units() -> None:
    _, meta = _module.build_mesh(n_springs_total=101)
    assert meta["unit_a"]["n_springs"] == 50
    assert meta["unit_b"]["n_springs"] == 51


def test_unit_b_is_offset_along_x() -> None:
    mesh_text, _ = _module.build_mesh(n_springs_total=0)
    first_b_coord = re.search(r"^NB1 (\S+) ", mesh_text, flags=re.M)
    assert first_b_coord is not None
    assert float(first_b_coord.group(1)) > _module.UNIT_X_OFFSET - 1.0


def test_comm_carries_two_independent_liaison_solide_occurrences() -> None:
    comm = _module.build_comm(n_springs_total=100, stiffness_n_per_m=1.0e6)
    assert 'GROUP_NO=("TETE_A", "POUTRE_N_A")' in comm
    assert 'GROUP_NO=("TETE_B", "POUTRE_N_B")' in comm
    assert comm.rstrip().endswith("FIN()")
    assert "..." not in comm


def test_comm_has_no_springs_block_when_n_springs_total_is_zero() -> None:
    comm = _module.build_comm(n_springs_total=0, stiffness_n_per_m=1.0e6)
    assert "CREA_POI1" not in comm
    assert 'MODELISATION="DIS_T"' not in comm
