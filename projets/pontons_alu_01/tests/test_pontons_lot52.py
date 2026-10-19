"""Tests of lot 52 for PONTONS-ALU-01: the PRO geometry (P63 to P65: posts and diagonals
120 × 120 × 6 under the purlins, rigid links of 0,01 m and 0,085 m, diagonal nodes at
e_diag, pin axis at +1,175), its invariants, the generated `.comm`, the node geometry,
the decisions P62 to P66 in the fiche, the declaration of the project, the delivery
plan. No Docker, no Salome."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.combinaisons_lot51quater import (
    branches,
    check_exclusions,
    events_p60_p61,
    magnitudes_p60,
)
from pontons_alu_01.combinaisons_lot51ter import counts
from pontons_alu_01.exports_lot52 import (
    WELD_LIMIT_MM,
    family_columns,
    node_geometry,
    node_summary,
)
from pontons_alu_01.generation_lot51ter import all_cases, zone_names
from pontons_alu_01.generation_lot52 import build_comm, geometry_of, values
from pontons_alu_01.geometrie_lot51 import ParameterError
from pontons_alu_01.geometrie_lot51ter import expected_counts, read_parameters
from pontons_alu_01.geometrie_lot52 import (
    OVERRIDABLE,
    SCRIPT,
    diagonal_node,
    post_pieces,
)
from pontons_alu_01.invariants_lot52 import VERSIONED, invariants, text
from pontons_alu_01.variantes_lot52 import variants

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("pontons_alu_01", ROOT)


def test_three_variants_as_in_the_consigne() -> None:
    vs = variants()
    assert list(vs) == ["B52", "A52", "B52P4"]
    for v in vs.values():
        assert (v.beam_side_mm, v.beam_thickness_mm) == (200, 12)
        assert (v.post_side_mm, v.post_thickness_mm) == (120, 6)
        assert v.purlin_side_mm == 50
        assert v.e_diag == 0.25
    assert vs["B52"].purlin_thickness_mm == 5
    assert vs["B52P4"].purlin_thickness_mm == 4
    assert vs["A52"].geometry == "A" and vs["B52"].geometry == "B"


def test_levels_of_p64_and_p65() -> None:
    g = geometry_of(variants()["B52"])
    assert g.levels["montants"] == 1.29
    assert g.levels["pannes"] == 1.375
    assert g.levels["axe_appui"] == 1.175
    assert all(a.pin[2] == 1.175 for a in g.axes)
    assert math.isclose(diagonal_node(g.parameters), 0.68)


def test_truss_of_p64() -> None:
    g = geometry_of(variants()["B52"])
    for m in g.family("MONTANTS") + g.family("DIAGONALES"):
        assert {p[2] for p in m.points} == {1.29}, m.name
    for m in g.family("DIAGONALES"):
        assert (m.points[0][1], m.points[-1][1]) == (0.68, -0.68), m.name
    for m in g.family("MONTANTS"):
        ys = [p[1] for p in m.points]
        assert ys[0] == -0.93 and ys[-1] == 0.93 and -0.68 in ys and 0.68 in ys
    lm = [lk for lk in g.links if lk.name.startswith("LM_")]
    assert len(lm) == 2 * len(g.family("MONTANTS")) == 80
    assert {round(lk.b[2] - lk.a[2], 6) for lk in lm} == {0.01}
    lr = [lk for lk in g.links if lk.name.startswith("LR_") and "_PF_" not in lk.name]
    assert {round(lk.a[2] - lk.b[2], 6) for lk in lr} == {0.085}
    assert len(post_pieces(g)) == 80


def test_counts_equal_those_of_the_salome_runs() -> None:
    """3 295 nœuds, 2 776 SEG2, 780 QUAD4 : relevés par mesh check sur les MED des
    géométries A et B (4 011 invariants sur 4 011)."""
    for v in variants().values():
        assert expected_counts(geometry_of(v)) == {
            "nodes": 3295,
            "SEG2": 2776,
            "QUAD4": 780,
        }
        assert len(text(geometry_of(v)).splitlines()) > 0


def test_versioned_invariants_are_those_of_b52() -> None:
    versioned = yaml.safe_load(VERSIONED.read_text("utf-8"))
    assert versioned == invariants(geometry_of(variants()["B52"]))
    names = {g["name"] for g in versioned["groups"]}
    assert "MONTANTS_TRONCONS" in names and "LM_T1_1_YM_A" in names


def test_only_the_declared_parameters_are_overridable() -> None:
    with pytest.raises(ParameterError, match="non modifiable"):
        read_parameters(SCRIPT, {"Z_AXE": 1.2}, OVERRIDABLE)
    params = read_parameters(SCRIPT, {"E_DIAG": 0.3}, OVERRIDABLE)
    assert params["E_DIAG"] == 0.3 and params["Z_AXE"] == 1.175


def test_generated_comm_of_lot_52(ctx: ProjectContext) -> None:
    for code, v in variants().items():
        text_, report = build_comm(ctx, mesh_label="maillage_ponton_52.med", variant=v)
        assert "lot 52" in text_.splitlines()[0]
        assert 'GROUP_MA=("MONTANTS", "DIAGONALES"), SECTION="RECTANGLE"' in text_
        assert "VALE=(0.12, 0.006)" in text_
        assert "Z = +1,175" in text_
        assert '_F(GROUP_NO=("LM_T1_1_YM_A", "LM_T1_1_YM_B")),' in text_
        thickness = v.purlin_thickness_mm * 1e-3
        assert f"VALE=(0.05, {thickness:g})" in text_, code
        assert report["post_section"] == "120 × 120 × 6"
        assert values(ctx, v).t150 == 0.12


def test_archived_comms_are_the_generated_ones(ctx: ProjectContext) -> None:
    """The `.comm` of each run of lot 52 is regenerated byte for byte."""
    root = PROJECT / "references" / "execution_lot52"
    for code, v in variants().items():
        text_, _ = build_comm(ctx, mesh_label="maillage_ponton_52.med", variant=v)
        assert text_ == (root / code / "pontons_alu_01.comm").read_text("utf-8"), code


def test_node_geometry_has_no_overlap() -> None:
    for v in variants().values():
        rows = node_geometry(v, geometry_of(v))
        summary = node_summary(rows)
        assert summary["reussi"]
        assert summary["montant/poutre"]["nombre"] == 80
        assert (
            summary["montant/poutre"]["zone_soudure_max_mm"] == 180.0 <= WELD_LIMIT_MM
        )
        assert summary["panne/montant"]["nombre"] == 160
        assert summary["panne/diagonale"]["nombre"] == 120
        for kind in ("panne/montant", "panne/diagonale"):
            assert summary[kind]["jeu_min_mm"] == summary[kind]["jeu_max_mm"] == 0.0
        assert summary["montant/poutre"]["jeu_min_mm"] == 30.0


def test_node_geometry_detects_an_overlap() -> None:
    """Contrôle discriminant : des montants de 130 sous des pannes calées pour 120
    recouvrent les pannes de 5 mm."""
    import dataclasses  # noqa: PLC0415

    v = variants()["B52"]
    g = geometry_of(v)
    rows = node_geometry(dataclasses.replace(v, post_side_mm=130.0), g)
    assert not node_summary(rows)["reussi"]
    assert min(r["jeu_mm"] for r in rows if r["croisement"] == "panne/montant") == -5.0


def test_rules_of_lot_51_quater_unchanged(ctx: ProjectContext) -> None:
    data = {k: item.value for k, item in ctx.data().items().items()}
    g = geometry_of(variants()["B52"])
    ev = events_p60_p61(
        magnitudes_p60(data, 50.0),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )
    bs = branches(ev)
    assert sum(counts(bs).values()) == 2_364_008
    assert check_exclusions(bs, ev) == []
    assert ev["HU"].coefficients["HU_PANNES"] == 1.91


def test_family_columns() -> None:
    cols = family_columns()
    assert len(cols) == 25
    assert "FAM_TRONCON_My" in cols and "FAM_PANNES_N_min" in cols


def test_fiche_carries_the_decisions_of_lot_52() -> None:
    fiche = json.loads(
        (PROJECT / "fiche" / "hypotheses_pontons_alu_01.json").read_text("utf-8")
    )
    by_label = {e.get("point_label"): e for e in fiche["entries"]}
    for label in ("P62", "P63", "P64", "P65", "P66"):
        assert by_label[label]["status"] == "tranche", label
    for label in ("P53", "P54"):
        assert by_label[label]["decision_history"], label
    assert "+1,175" in by_label["P54"]["option_retained"]


def test_projet_yaml_points_to_lot_52(ctx: ProjectContext) -> None:
    decl = ctx.declaration
    assert decl.mesh is not None
    assert str(decl.mesh.script).endswith("maillage_ponton_52.py")
    assert decl.comm is not None and "extensions_lot52" in str(decl.comm.generator)
    controls = decl.controls
    assert controls is not None
    assert [c.name for c in controls.cases] == all_cases(geometry_of(variants()["B52"]))


def test_link_reactions_are_folded_on_the_supports() -> None:
    """CA-036 : l'effort de la liaison LM_ porté par le bout du montant s'ajoute au
    nœud d'appui (culée, oreilles), et le bout du montant quitte la table."""
    from types import SimpleNamespace  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    from pontons_alu_01.exports_lot51ter import RunTables  # noqa: PLC0415
    from pontons_alu_01.exports_lot52 import fold_link_reactions  # noqa: PLC0415

    g = geometry_of(variants()["B52"])
    linked = [
        lk
        for lk in g.links
        if lk.name.startswith("LM_")
        and (lk.b in g.node_groups["APP_CULEE"] or any(lk.b in a.ears for a in g.axes))
    ]
    groups: dict[str, list[int]] = {}
    reac: dict[int, np.ndarray] = {}
    for k, lk in enumerate(linked):
        a, b = 2 * k + 1, 2 * k + 2
        groups[f"{lk.name}_A"], groups[f"{lk.name}_B"] = [a], [b]
        reac[a] = np.array([1.0, 2.0, 3.0])
        reac[b] = np.array([10.0, 0.0, -3.0])
    tables = RunTables({}, {}, {"G1": reac}, {})
    folded = fold_link_reactions(tables, SimpleNamespace(group_nodes=groups), g)
    assert folded == {"APP_CULEE": 2, "AXES": 38}
    assert len(tables.reac["G1"]) == len(linked)
    assert all(list(v) == [11.0, 2.0, 0.0] for v in tables.reac["G1"].values())
