"""Projet de la dalle (lot 43) : déclaration, fiche arbitrée, discrétisation
analytique, générateur du `.comm` (sans Docker ni Salomé)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.projet.check import check_project
from aster_expert.projet.context import load_project
from dalle_appuyee_01.discretisation import SlabMesh, segment_count
from dalle_appuyee_01.extensions import reference_mesh, resultant
from dalle_appuyee_01.generation import GenerationError, _title, build_comm

_ROOT = Path(__file__).resolve().parents[3]
_PROJECT = _ROOT / "projets" / "dalle_appuyee_01"


@pytest.fixture(scope="module")
def ctx():  # type: ignore[no-untyped-def]
    return load_project("dalle_appuyee_01", _ROOT)


def test_the_declaration_is_coherent_and_ready(ctx) -> None:  # type: ignore[no-untyped-def]
    assert check_project(ctx) == []
    assert ctx.sheet().generation_blockers(ctx.data()) == ()


def test_every_practice_decision_comes_from_mm(ctx) -> None:  # type: ignore[no-untyped-def]
    sheet: HypothesesSheet = ctx.sheet()
    practice = [e for e in sheet.entries if isinstance(e, PracticeHypothesisEntry)]
    assert len(practice) == 10
    for e in practice:
        assert e.status == "tranche"
        assert any(s.origin == "arbitrage_mm" for s in e.sources)
        assert e.discarded_variants and e.validity_domain


def test_the_arbitrated_fiche_is_reproduced_byte_for_byte() -> None:
    sys.path.insert(0, str(_PROJECT / "scripts"))
    import arbitrer_fiche_lot43 as script  # noqa: PLC0415
    from build_fiche_lot43 import build_sheet  # noqa: PLC0415

    sheet = script.arbitrate(build_sheet())
    text = (
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    )
    assert script.FICHE.read_text(encoding="utf-8") == text
    assert script.DOCUMENT.read_text(encoding="utf-8") == script.render(sheet)


def test_the_arbitration_is_copied_verbatim() -> None:
    copy = _PROJECT / "donnees" / "sources" / "arbitrage_dalle_appuyee_01_v1.md"
    original = Path("/media/sf_partage/echanges/arbitrage_dalle_appuyee_01_v1.md")
    if not original.is_file():
        pytest.skip("dossier partagé absent (profil cloud)")
    assert copy.read_bytes() == original.read_bytes()


@pytest.mark.parametrize(
    ("size", "nx", "ny", "nodes"),
    [(0.5, 12, 8, 117), (0.25, 24, 16, 425), (0.125, 48, 32, 1617)],
)
def test_counts_of_the_convergence_series(
    size: float, nx: int, ny: int, nodes: int
) -> None:
    mesh = SlabMesh(6.0, 4.0, size)
    assert (mesh.nx, mesh.ny, mesh.nodes) == (nx, ny, nodes)
    assert mesh.quads == nx * ny
    assert mesh.segments == 3 * (nx + ny)
    assert segment_count(3.0, size) == nx // 2


def test_versioned_invariants_are_those_of_the_parameters() -> None:
    for size, label in ((0.5, "h0p500"), (0.25, "h0p250"), (0.125, "h0p125")):
        path = _PROJECT / "maillage" / f"invariants_{label}.yaml"
        assert (
            yaml.safe_load(path.read_text(encoding="utf-8"))
            == SlabMesh(6.0, 4.0, size).invariants()
        )


def test_the_project_chain_uses_the_finest_mesh(ctx) -> None:  # type: ignore[no-untyped-def]
    assert reference_mesh(ctx).size == 0.125


def test_resultants_computed_and_specified_agree(ctx) -> None:  # type: ignore[no-untyped-def]
    for case, value in (("G", -180000.0), ("Q", -240000.0)):
        r = resultant(ctx, case)
        assert r["as_evaluated"]["DZ"] == pytest.approx(value, rel=1e-12)
        assert r["specified"]["DZ"] == pytest.approx(value, rel=1e-12)


def test_the_generated_comm_carries_every_decision(ctx) -> None:  # type: ignore[no-untyped-def]
    text, report = build_comm(ctx, mesh_label="essai")
    assert 'MODELISATION="DKT"' in text
    assert "E=33000000000.0, NU=0.2" in text
    assert f"RHO={25000.0 / 9.81!r}" in text
    assert 'FORCE_COQUE=_F(GROUP_MA="DALLE", FZ=-10000.0)' in text
    assert '_F(GROUP_NO="APPUIS", DZ=0.0)' in text
    assert '_F(GROUP_NO="P_A", DX=0.0, DY=0.0)' in text
    assert '_F(GROUP_NO="P_B", DY=0.0)' in text
    assert "VECT_NORM=(0.0, 0.0, 1.0)" in text
    assert text.count("CALC_FERRAILLAGE(") == 4  # ELU, ELS car., ELS QP, sensibilité
    assert text.count("ALPHA_CC=1.0") == 4
    assert report["combinaisons"] == [
        "ELU_FOND_Q_DOM_G_defav",
        "ELS_CARA_Q_DOM",
        "ELS_FREQ_Q_DOM",
        "ELS_QUASI_PERMANENTE",
    ]
    assert all(len(t) <= 16 for t in report["tables"])


def test_a_long_or_repeated_table_title_is_refused() -> None:
    seen: set[str] = set()
    _title("REAC_APPUIS_G", seen)
    with pytest.raises(GenerationError, match="en double"):
        _title("REAC_APPUIS_G", seen)
    with pytest.raises(GenerationError, match="trop long"):
        _title("X" * 17, seen)
