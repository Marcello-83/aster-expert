"""FORCE_COQUE trial case of lot 21 (`scripts/build_fcoque_essai.py`).

Replays the generator in a temporary directory and compares the three files
byte for byte with the versioned ones, and checks the mesh against its own
geometry. No Docker, no network: the execution itself (level C) is reported in
`docs/essai_lot21_force_coque.md`, not replayed by the unit tests.
"""

from __future__ import annotations

import importlib.util
import math
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "build_fcoque_essai.py"
_VERSIONED = _ROOT / "data" / "examples" / "fcoque_essai"

_spec = importlib.util.spec_from_file_location("build_fcoque_essai", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["build_fcoque_essai"] = _module
_spec.loader.exec_module(_module)


def test_replaying_the_generator_reproduces_the_versioned_files(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(_SCRIPT), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    for name in ("demi_cylindre.mail", "demi_cylindre.comm", "demi_cylindre.export"):
        assert (tmp_path / name).read_text("utf-8") == (_VERSIONED / name).read_text(
            "utf-8"
        )


def test_mesh_counts_and_groups() -> None:
    mesh = (_VERSIONED / "demi_cylindre.mail").read_text("utf-8")

    nodes = re.findall(r"^N\d+ ", mesh, flags=re.M)
    quads = re.findall(r"^MA\d+ N\d+ N\d+ N\d+ N\d+$", mesh, flags=re.M)
    assert len(nodes) == (_module.N_THETA + 1) * (_module.N_Z + 1) == 407
    assert len(quads) == _module.N_THETA * _module.N_Z == 360
    # every element of the shell group is a listed QUAD4, listed once
    group = mesh.split("GROUP_MA\nCOQUE\n")[1].split("FINSF")[0].split()
    assert group == [f"MA{k}" for k in range(1, 361)]
    for name in ("NA", "NB", "NC", "APPUIS"):
        assert f"\n{name} N" in mesh


def test_mesh_nodes_lie_on_the_half_cylinder() -> None:
    mesh = (_VERSIONED / "demi_cylindre.mail").read_text("utf-8")

    for x, y, z in re.findall(
        r"^N\d+ (\S+) (\S+) (\S+)$", mesh.split("QUAD4")[0], flags=re.M
    ):
        assert math.hypot(float(x), float(y)) == _approx(_module.RADIUS)
        assert float(x) >= 0.0
        assert 0.0 <= float(z) <= _module.HEIGHT


def _approx(value: float) -> object:
    import pytest

    return pytest.approx(value, abs=1e-9)


def test_facet_area_is_close_to_but_below_the_developed_area() -> None:
    developed = math.pi * _module.RADIUS * _module.HEIGHT
    projected = 2.0 * _module.RADIUS * _module.HEIGHT

    assert _module.facet_area() < developed
    assert abs(_module.facet_area() - developed) / developed < 1e-3
    assert projected == _approx(1.42)


def test_command_file_carries_the_trial_load_and_supports() -> None:
    comm = (_VERSIONED / "demi_cylindre.comm").read_text("utf-8")

    assert 'MODELISATION="DKT"' in comm
    assert 'FORCE_COQUE=_F(GROUP_MA="COQUE", FX=1.0)' in comm
    assert 'NOM_CHAM="REAC_NODA"' in comm
    assert comm.rstrip().endswith("FIN()")
    assert "..." not in comm


def test_export_stages_the_mesh_with_the_command_file() -> None:
    export = (_VERSIONED / "demi_cylindre.export").read_text("utf-8")

    assert "F comm demi_cylindre.comm D 1" in export
    assert "F mail demi_cylindre.mail D 20" in export
