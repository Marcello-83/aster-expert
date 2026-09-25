"""Lot 36 : vues 2D (`aster_expert.report.figures`). Les fonctions pures (facteur
d'amplification, cote de pivot, échelle de couleur) sont testées exactement ; les
vues qui ne dépendent que du maillage sont produites sur un maillage synthétique
(un tube de 8 facettes sur deux niveaux) : le PNG existe, est non vide, et la
figure porte son titre, ses unités et le facteur d'amplification."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib")

from aster_expert.report import figures  # noqa: E402
from aster_expert.report.med_read import med_field_name  # noqa: E402
from aster_expert.report.med_source import MedData  # noqa: E402

RADIUS = 0.71


def test_amplification_brings_the_largest_displacement_to_about_half_a_metre() -> None:
    assert figures.amplification(0.0125) == pytest.approx(40.0)
    assert figures.amplification(0.5) == 1.0
    assert figures.amplification(0.0) == 1.0  # aucun déplacement : pas d'amplification
    # un seul chiffre significatif
    assert figures.amplification(0.0374) == pytest.approx(10.0)


def test_pivot_level_is_the_first_sign_change_going_down() -> None:
    z = np.array([-12.0, -13.0, -14.0, -15.0, -16.0])
    dy = np.array([-0.010, -0.004, -0.001, 0.001, 0.002])
    # entre -14 (DY = -1 mm) et -15 (+1 mm) : interpolation linéaire, -14,5
    assert figures.pivot_level(z, dy) == pytest.approx(-14.5)
    # l'ordre des nœuds ne compte pas
    order = np.array([3, 0, 4, 1, 2])
    assert figures.pivot_level(z[order], dy[order]) == pytest.approx(-14.5)
    assert figures.pivot_level(z, np.abs(dy)) is None
    # première alternance seulement
    assert figures.pivot_level(
        np.array([0.0, -1.0, -2.0, -3.0]), np.array([-1.0, 1.0, -1.0, 1.0])
    ) == pytest.approx(-0.5)


def test_colour_scale_is_symmetric_and_can_be_clipped() -> None:
    values = np.concatenate([np.linspace(-1.0, 1.0, 1000), [100.0]])
    full = figures._symmetric_norm(values)
    clipped = figures._symmetric_norm(values, clip=True)
    assert (full.vmin, full.vcenter, full.vmax) == (-100.0, 0.0, 100.0)
    assert clipped.vmax is not None and clipped.vmin is not None
    assert clipped.vmax < 2.0 and clipped.vmin == -clipped.vmax
    # une échelle nulle reste valide
    zero = figures._symmetric_norm(np.zeros(4))
    assert zero.vmax == 1.0


def test_spring_key_rounds_to_the_micrometre() -> None:
    assert figures._spring_key(np.array([1.0000004, -0.0, 2.5])) == (1.0, 0.0, 2.5)


def _tube() -> MedData:
    angles = np.linspace(0.0, 2.0 * math.pi, 9)[:-1]
    levels = (0.0, -1.0, -2.0)
    coords = np.array(
        [
            [RADIUS * math.cos(a), RADIUS * math.sin(a), z]
            for z in levels
            for a in angles
        ]
    )
    n = len(angles)
    quads = [
        [k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i]
        for k in range(2)
        for i in range(n)
    ]
    conn0 = np.array(quads)
    depl = np.zeros((len(coords), 6))
    depl[:, 1] = -0.002 * (1.0 + coords[:, 2] / 4.0) * np.sin(coords[:, 1] * 0.0 + 1.0)
    empty = np.zeros((len(coords), 6))
    return MedData(
        path=Path("tube.med"),
        coords=coords,
        conn={0: conn0},
        node_groups={},
        cell_groups={
            0: {"TUBES": np.arange(len(conn0)), "PALPS": np.array([], dtype=int)}
        },
        arrays={
            med_field_name("G", "DEPL"): depl,
            med_field_name("G", "REAC_NODA"): empty,
        },
        components={},
        cases=("G",),
    )


def _context() -> figures.FigureContext:
    from aster_expert.report.loads import AppliedLoads

    return figures.FigureContext(
        axes=[0.0],
        radius=RADIUS,
        spring_nodes={},
        spring_nodes_terre={},
        loads=AppliedLoads(
            pressure_pa={},
            beam={},
            bollard_n=(0.0, 0.0, 0.0),
            defense_pa=0.0,
            gravity=9.81,
            beam_axis_z=3.3,
        ),
        tie_direction=(0.94, -0.34),
        tie_head=(0.71, 2.5),
        tie_anchor=(25.14, -6.39),
        label="essai",
    )


def test_dy_map_writes_a_png_with_the_case_and_units(tmp_path: Path) -> None:
    out = figures.dy_map(_tube(), _context(), "G", tmp_path)
    assert out.case == "G" and out.kind == "dy_ecran"
    assert out.path.name == "dy_ecran_G.png"
    assert out.path.stat().st_size > 5_000
    assert out.path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_deformed_shape_states_its_amplification_factor(tmp_path: Path) -> None:
    data = _tube()
    out = figures.deformed_shape(data, _context(), "G", tmp_path)
    factor = figures.amplification(float(np.abs(data.node_field("G", "DEPL")).max()))
    assert f"×{factor:g}" in out.title
    assert out.path.exists() and out.path.stat().st_size > 5_000


def test_every_view_is_named_by_kind_and_case() -> None:
    kinds = {v.__name__ for v in figures.VIEWS}
    assert kinds == {
        "deformed_shape",
        "dy_map",
        "tube_efforts",
        "palp_efforts",
        "arrows",
        "beam_diagrams",
        "tube_profiles",
        "bearing_profile",
    }
