"""Tests of the lot 47 ter additions: variant DST + cap beam of 0.80 m, coarse slab
meshes and wheel prints by fractions of cells (docs/essais_lot47ter.md § 2, § 3).
No Docker, no Salome."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aster_expert.projet.context import ProjectContext, load_project
from estacade_pieux_01.charges_mobiles import all_cases, tr_axle_cases
from estacade_pieux_01.discretisation import (
    COARSE_SIZES,
    DiscretisationError,
    JettyMesh,
)
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.generation import (
    GenerationError,
    Options,
    build_comm,
    fractional_prints,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("estacade_pieux_01", ROOT)


def test_coarse_meshes_round_the_about_only(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    with pytest.raises(DiscretisationError):
        JettyMesh(v, 0.25).x_segments()
    m25 = JettyMesh(v, 0.25, exact=False)
    m50 = JettyMesh(v, 0.5, exact=False)
    assert m25.x_segments() == (2, 20, 20, 20, 20, 20, 20, 2)
    assert m50.x_segments() == (1, 10, 10, 10, 10, 10, 10, 1)
    assert (m25.nodes, m25.quads, m50.nodes, m50.quads) == (3573, 2976, 1267, 744)
    for m in (m25, m50):
        xs = m.x_nodes()
        assert len(xs) == m.nx + 1 and xs[0] == 0.0 and xs[-1] == v.length
        assert all(any(abs(x - f) < 1e-9 for x in xs) for f in v.x_files)
        assert len(m.y_nodes()) == m.ny + 1
    # Exact mesh: the node lines of 0.05 m are unchanged.
    assert JettyMesh(v, 0.05).x_nodes()[:3] == (0.0, 0.05, 0.1)
    assert COARSE_SIZES == (0.25, 0.5)


@pytest.mark.parametrize("size", [0.25, 0.5])
def test_fractional_prints_carry_the_exact_load(
    ctx: ProjectContext, size: float
) -> None:
    v = model_values(ctx)
    mesh = JettyMesh(v, size, exact=False)
    xs, ys = mesh.x_nodes(), mesh.y_nodes()
    cases = (*all_cases(v, 0.05), *tr_axle_cases(v))
    cells, loads = fractional_prints(v, cases, xs, ys)
    assert len(loads) == 299
    for case in cases:
        total = sum(
            p * (cells[ij][1] - cells[ij][0]) * (cells[ij][3] - cells[ij][2])
            for ij, p in loads[case.name].items()
        )
        assert total == pytest.approx(case.total, rel=1e-12)
        for ij, p in loads[case.name].items():
            assert 0.0 < p <= 2.0 * case.pressure + 1e-6  # two prints at most
            y0, y1 = cells[ij][2], cells[ij][3]
            if case.model == "TR":
                assert y0 >= v.lane[1] - 1e-9  # sidewalk Y > 0 (E18)
            else:
                assert y0 >= v.lane[0] - 1e-9 and y1 <= v.lane[1] + 1e-9


def test_a_print_outside_its_group_is_refused(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    mesh = JettyMesh(v, 0.5, exact=False)
    shifted = all_cases(v, 0.05)[0]
    from dataclasses import replace  # noqa: PLC0415

    axles = tuple(replace(a, wheels_y=(1.5, 3.5)) for a in shifted.axles)
    with pytest.raises(GenerationError, match="charge représentée"):
        fractional_prints(
            v, (replace(shifted, axles=axles),), mesh.x_nodes(), mesh.y_nodes()
        )


def test_variant_dst_cap_0p80_and_coarse_comm(ctx: ProjectContext) -> None:
    text, report = build_comm(
        ctx,
        mesh_label="m.mmed",
        options=Options(variant="dst_chevetre_0p80", tr_axle=True),
    )
    assert 'MODELISATION="DST"' in text and 'MODELISATION="DKT"' not in text
    assert '"HZ"), VALE=(1.2, 0.8)' in text
    assert report["variante"] == "dst_chevetre_0p80" and len(report["positions"]) == 299
    coarse, rep = build_comm(
        ctx,
        mesh_label="m.mmed",
        options=Options(variant="dst_chevetre_0p80", tr_axle=True, mesh_size=0.5),
    )
    assert rep["taille_dalle"] == 0.5
    assert "fractions de mailles" in coarse
    # Same positions as the production mesh; one charge per position.
    assert rep["positions"] == report["positions"]
    assert len(re.findall(r"^CH_(TS|L2|TRE)\w* = AFFE_CHAR_MECA", coarse, re.M)) == 299
    # No group name over 24 characters, every cell group created before use.
    used = set(re.findall(r"'(Q\d{3}_\d{2})'", coarse))
    created = set(re.findall(r'NOM="(Q\d{3}_\d{2})"', coarse))
    assert used and used <= created
