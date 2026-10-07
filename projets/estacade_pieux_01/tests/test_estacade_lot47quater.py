"""Tests of the lot 47 quater variants H1 (mixed plug) and H2 (deck at +1.50)
(docs/essais_lot47quater.md § 2). No Docker, no Salome."""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from aster_expert.projet.context import ProjectContext, load_project
from estacade_pieux_01.donnees import DataError, model_values
from estacade_pieux_01.extensions import weights
from estacade_pieux_01.generation import Options, build_comm
from estacade_pieux_01.transcription import (
    DECK_LEVEL_H2,
    mixed_sections,
    plug_concrete_weight,
    with_deck_level,
)

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "estacade_pieux_01"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("estacade_pieux_01", ROOT)


def test_mixed_section_is_homogenised_in_steel(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    mixed = mixed_sections(v)
    assert [m.name for m in mixed] == ["T1", "T2", "T3"]  # head down to -0.80
    t1 = mixed[0]
    ac = math.pi * 0.622**2 / 4.0
    ic = math.pi * 0.622**4 / 64.0
    n = 210.0 / 34.0
    assert t1.area == pytest.approx(0.03053 + ac / n, rel=1e-12)
    assert t1.inertia == pytest.approx(0.00155063 + ic / n, rel=1e-12)
    # The core adds about 250 MN·m2 to about 325 MN·m2 (instruction of the lot).
    assert 34.0e9 * ic / 1e6 == pytest.approx(249.81, abs=0.01)
    assert v.e_steel * t1.inertia / 1e6 == pytest.approx(575.44, abs=0.01)
    # Weight of steel and concrete, exactly, through the density of the segment.
    weight = t1.density * v.gravity * t1.area
    assert weight == pytest.approx(78.5e3 * 0.03053 + 25.0e3 * ac, rel=1e-12)
    r, ep = t1.equivalent_tube()
    r_in = r - ep
    assert math.pi * (r**2 - r_in**2) == pytest.approx(t1.area, rel=1e-12)
    assert math.pi * (r**4 - r_in**4) / 4.0 == pytest.approx(t1.inertia, rel=1e-12)


def test_deck_level_moves_only_the_head(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    h2 = with_deck_level(v, DECK_LEVEL_H2)
    assert h2.z_mid == 1.5 and h2.sections[0].z_top == 1.5
    assert h2.sections[1:] == v.sections[1:] and h2.springs == v.springs
    assert h2.pile_levels() == (1.5, *v.pile_levels()[1:])
    with pytest.raises(DataError, match="ressort au-dessus"):
        with_deck_level(v, 0.9)
    # Weights of the criterion table (§ 2.4).
    assert weights(h2)["pieux_n"] == pytest.approx(554008.098, abs=1e-3)
    assert plug_concrete_weight(v) == pytest.approx(223335.618, abs=1e-3)
    assert plug_concrete_weight(h2) == pytest.approx(244605.676, abs=1e-3)


def test_h1_changes_only_the_pile_sections_and_materials(ctx: ProjectContext) -> None:
    ref, _ = build_comm(ctx, mesh_label="m.med", options=Options(variant="dst"))
    text, report = build_comm(
        ctx, mesh_label="m.med", options=Options(variant="dst", mixed_plug=True)
    )
    assert report["section_mixte_bouchon"] is True and report["plan_tablier"] == 1.3
    for name in ("T1", "T2", "T3"):
        assert f"ACIER_{name} = DEFI_MATERIAU(" in text
        # Mechanical and thermal fields both carry the mixed material.
        assert text.count(f'GROUP_MA=("PIEU_{name}",), MATER=ACIER_{name}') == 3
    assert text.count('GROUP_MA=("PIEU_T4", "PIEU_T5",), MATER=ACIER') == 3
    assert 'GROUP_MA=("PIEUX",), MATER=ACIER' not in text
    assert 'PIEU_T1", SECTION="CERCLE", CARA=("R", "EP"), VALE=(0.2853' in text
    removed = set(ref.splitlines()) - set(text.splitlines())
    assert all(re.search(r"PIEU|PIEUX|^# Estacade", line) for line in removed), removed


def test_h2_changes_nothing_in_the_comm_but_the_header(ctx: ProjectContext) -> None:
    # The deck level lives in the mesh (H2 mesh); the springs, sections and loads of
    # the .comm are the same, only the header and the report say so.
    ref, _ = build_comm(ctx, mesh_label="m.med", options=Options(variant="dst"))
    text, report = build_comm(
        ctx, mesh_label="m.med", options=Options(variant="dst", deck_level=1.5)
    )
    assert report["plan_tablier"] == 1.5
    added = [
        line
        for line in text.splitlines()
        if line.startswith("# Lot 47 quater, variante déclarée H2")
    ]
    assert added == ["# Lot 47 quater, variante déclarée H2 : plan du tablier à 1.5."]
    assert [line for line in text.splitlines() if line not in added] == ref.splitlines()


def test_reference_comm_is_unchanged_by_lot47quater(ctx: ProjectContext) -> None:
    reference = PROJECT / "references" / "cas" / "estacade_pieux_01.comm"
    text, _ = build_comm(ctx, mesh_label="estacade_mesh.med")
    assert text == reference.read_text(encoding="utf-8")


def test_h2_mesh_files_are_reproducible() -> None:
    import importlib.util  # noqa: PLC0415

    path = PROJECT / "scripts" / "variantes_lot47quater.py"
    spec = importlib.util.spec_from_file_location("variantes_lot47quater", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    outputs = module.mesh_outputs()
    assert len(outputs) == 2
    for target, data in outputs.items():
        assert target.read_bytes() == data, target
    params = (PROJECT / "maillage" / "params_h0p050_plan1p50.json").read_text("utf-8")
    production = (PROJECT / "maillage" / "params_h0p050.json").read_text("utf-8")
    changed = [
        (a, b)
        for a, b in zip(production.splitlines(), params.splitlines(), strict=True)
        if a != b
    ]
    assert [b.strip() for _, b in changed] == ["1.5,", '"haut": 1.5', '"z_dalle": 1.5']


def test_pre_039_is_the_decision_e20_replayed() -> None:
    import importlib.util  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    from aster_expert.connaissances.modeles import Precedent  # noqa: PLC0415

    path = PROJECT / "scripts" / "connaissances_lot47quater.py"
    spec = importlib.util.spec_from_file_location("connaissances_lot47quater", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stored = ROOT / "connaissances" / "precedents" / "PRE-039.yaml"
    written = Precedent.model_validate(yaml.safe_load(stored.read_text("utf-8")))
    assert module.pre_039() == written
    assert written.point_label == "E20" and "h/L ≤ 1/10" in written.validity_domain
