"""Tests of the model of ESTACADE-PIEUX-01 (lot 47): data, combinations of B5,
moving positions, discretisation, fiche and generator. No Docker, no Salome."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from aster_expert.projet.context import ProjectContext, load_project
from estacade_pieux_01.charges_mobiles import all_cases, check_alignment, ts_cases
from estacade_pieux_01.combinaisons import combinations, find
from estacade_pieux_01.discretisation import CONVERGENCE_SIZES, JettyMesh
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.extensions import applied_loads, weights
from estacade_pieux_01.generation import (
    TITLE_MAX,
    Options,
    build_comm,
    spring_classes,
)

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "estacade_pieux_01"
ANNEX = PROJECT / "donnees" / "sources" / "annexe_B_lot47.md"


@pytest.fixture(scope="module")
def ctx() -> ProjectContext:
    return load_project("estacade_pieux_01", ROOT)


def test_springs_follow_b3_and_e6(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    rive = {s.z: s.k for s in v.spring_levels("RIVE")}
    eau = {s.z: s.k for s in v.spring_levels("EAU")}
    assert len(rive) == 29 and len(eau) == 23  # +1,00 à -13,00 ; -2,00 à -13,00
    for z in (-8.0, -8.5, -10.0, -10.5):  # E6
        assert rive[z] == 21_200e3
    assert rive[1.0] == 3_500e3 and rive[-13.0] == 10_600e3
    assert eau[-2.0] == 900e3 and eau[-3.5] == 3_400e3


def test_equivalent_tube_reproduces_the_section_modulus_of_b2(
    ctx: ProjectContext,
) -> None:
    v = model_values(ctx)
    published = ctx.data().items()["pieu.modules_troncons"].value
    assert isinstance(published, tuple)
    for section, w in zip(v.sections, published, strict=True):
        assert section.section_modulus() * 1e6 == pytest.approx(float(w), abs=0.05)


def _b5_rows() -> dict[str, list[str]]:
    rows = {}
    for line in ANNEX.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and re.fullmatch(r"1\d\d( / 1\d\d)?", cells[0]):
            rows[cells[0]] = cells[1:]
    return rows


def _terms(text: str, rows: dict[str, list[str]], column: int) -> dict[str, float]:
    if text.startswith("idem "):
        base, extra = re.fullmatch(r"idem (\d+) \+ (.*)", text).groups()  # type: ignore[union-attr]
        key = next(k for k in rows if k.startswith(base))
        terms = _terms(rows[key][column], rows, column)
        terms.update(_terms("G + " + extra, rows, column))
        return terms
    out: dict[str, float] = {}
    for part in text.replace("γG G", "G").split(" + "):
        bits = part.split()
        if bits[-1] == "G":
            continue
        coef = float(bits[0].replace(",", ".")) if len(bits) == 2 else 1.0
        out[bits[-1].replace("−", "-")] = coef
    return out


def test_combinations_are_those_of_b5() -> None:
    rows = _b5_rows()
    assert len(combinations()) == 16 * 4
    for key, cells in rows.items():
        for number in (int(n) for n in key.split(" / ")):
            for column, families in (
                (0, ("ELS_f",)),
                (1, ("ELS_c",)),
                (2, ("ELU+", "ELU-")),
            ):
                expected = _terms(cells[column], rows, column)
                for family in families:
                    assert find(number, family).coefficients == expected, (
                        number,
                        family,
                    )
    assert find(112, "ELU+").gamma_g == 1.35 and find(112, "ELU-").gamma_g == 1.0
    assert find(105, "ELS_c").ts_position == "axe"
    assert find(112, "ELS_c").ts_position == "bord"
    assert find(100, "ELU+").ts_position is None


def test_moving_positions(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    cases = all_cases(v, 0.05)
    assert [
        sum(c.name.startswith(p) for c in cases) for p in ("TSA", "TSB", "L2A", "L2B")
    ] == [59, 59, 62, 62]
    assert check_alignment(cases, 0.05) == []
    ts = ts_cases(v, "axe")
    assert [c.x for c in ts] == [round(31.2 - c.x, 9) for c in reversed(ts)]  # symétrie
    bord = ts_cases(v, "bord")[0]
    assert bord.axles[0].wheels_y == (-0.7, 1.3)  # roue extérieure tangente à Y = 1,50
    lm2 = [c for c in cases if c.name.startswith("L2B")][0]
    assert lm2.axles[0].wheels_y == (-0.8, 1.2)  # E16, règle appliquée (pas ±1,325)
    assert all(c.total == 540e3 for c in cases if c.model == "TS")
    assert all(c.total == 320e3 for c in cases if c.model == "LM2")


def test_double_count_of_e2(ctx: ProjectContext) -> None:
    w = weights(model_values(ctx))
    assert w["double_compte_par_chevetre_n"] == pytest.approx(72.0e3)
    assert w["double_compte_total_n"] == pytest.approx(504.0e3)
    loads = applied_loads(model_values(ctx))
    assert loads["FR"]["DX"] == 381e3
    assert loads["UDL"]["DZ"] == pytest.approx(-6300 * 3 * 31.2)


def test_mesh_counts(ctx: ProjectContext) -> None:
    v = model_values(ctx)
    m = JettyMesh(v, 0.05)
    assert (m.nx, m.ny, m.quads, m.nodes) == (624, 120, 74880, 76073)
    assert [JettyMesh(v, h).label() for h in CONVERGENCE_SIZES] == [
        "h0p100",
        "h0p050",
        "h0p025",
    ]


def _replay(script: str, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    return __import__(script)


def test_invariants_and_parameters_are_reproducible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _replay("invariants_lot47", monkeypatch)
    for path, data in module.outputs().items():  # type: ignore[attr-defined]
        assert path.read_bytes() == data, path


def test_fiche_is_reproducible_and_ready(
    monkeypatch: pytest.MonkeyPatch, ctx: ProjectContext
) -> None:
    module = _replay("fiche_lot47", monkeypatch)
    sheet = module.build_sheet()  # type: ignore[attr-defined]
    import json

    written = json.loads(
        (PROJECT / "fiche" / "hypotheses_estacade_pieux_01.json").read_text("utf-8")
    )
    assert json.loads(sheet.model_dump_json()) == written
    assert ctx.sheet().generation_blockers(ctx.data()) == ()
    labels = {e.point_label for e in sheet.entries}
    # E1 à E16 (lot 47), E17 à E19 (lot 47 bis).
    assert {f"E{i}" for i in range(1, 20)} <= labels
    assert {f"U{i}" for i in range(1, 7)} <= labels
    agent = sheet.agent_choices()
    assert len(agent) == 6 and all(s.verified_by for e in agent for s in e.sources)
    mm = [e for e in sheet.entries if getattr(e, "decided_by", None) == "MM"]
    assert len(mm) == 19 and all(
        s.origin == "arbitrage_mm" for e in mm for s in e.sources
    )


def test_generator_is_deterministic_and_respects_the_known_traps(
    ctx: ProjectContext,
) -> None:
    text, report = build_comm(ctx, mesh_label="m.med")
    again, _ = build_comm(ctx, mesh_label="m.med")
    assert text == again
    # Validateur de niveau B : jamais de tuple de concepts (lacune relevée au lot 47).
    assert not re.search(r"CHAR_MECA(_GLOBAL)?=\(", text)
    titles = report["tables"]
    assert len(titles) == len(set(titles)) and max(len(t) for t in titles) <= TITLE_MAX
    # CA-034 : chaque groupe de ressorts dans une seule classe.
    groups = [g for gs in spring_classes(model_values(ctx)).values() for g in gs]
    assert len(groups) == len(set(groups)) == 52
    # DIAG-004 : masse nulle des ressorts ; DIAG-011 : EFGE_NOEU restreint à la dalle.
    assert text.count('CARA="M_T_D_N"') == len(spring_classes(model_values(ctx)))
    assert all(
        'GROUP_MA="DALLE"' in line
        for line in text.splitlines()
        if '"EFGE_NOEU",)' in line
    )
    assert (
        "LIAISON_SOLIDE" not in text and 'DDL_IMPO=_F(GROUP_NO="PIEDS", DZ=0.0)' in text
    )
    assert sum(len(lot["cas"]) for lot in report["lots"]) == 5 + 242
    # DIAG-010 : jamais plusieurs GROUP_MA dans une occurrence de CREA_GROUP_NO.
    for occurrence in re.findall(r"_F\(GROUP_MA=\(([^)]*)\), NOM=", text):
        assert "," not in occurrence.strip().rstrip(","), occurrence


def test_variants_change_only_the_element_formulation(ctx: ProjectContext) -> None:
    ref, _ = build_comm(ctx, mesh_label="m.med")
    for variant, needle in (
        ("dst", 'MODELISATION="DST"'),
        ("pou_d_e_chevetres", 'MODELISATION="POU_D_E"'),
    ):
        text, _ = build_comm(ctx, mesh_label="m.med", options=Options(variant=variant))
        diff = [
            a
            for a, b in zip(ref.splitlines(), text.splitlines(), strict=True)
            if a != b
        ]
        assert any(needle in line for line in text.splitlines())
        assert all(
            "variante" in d or "MODELISATION" in d or "E13" in d for d in diff
        ), diff


def test_convergence_mode_keeps_two_positions(ctx: ProjectContext) -> None:
    for size in CONVERGENCE_SIZES:
        _, report = build_comm(
            ctx, mesh_label="m.med", options=Options(mode="convergence", cell=size)
        )
        assert report["lots"] == [{"resultat": "MB01", "cas": ["TSA_M15", "TSA_M20"]}]
        assert report["positions"]["TSA_M15"]["x"] == 8.1
        assert report["positions"]["TSA_M20"]["x"] == 5.6


def test_project_scripts_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    for name in (
        "constats_lot47",
        "convergence_lot47",
        "comparer_lot47",
        "sonde_lot47",
        "comparer_lot47bis",
        "constats_lot47bis",
        "executions_lot47bis",
        "executions_lot47ter",
        "sonde_lot47bis",
        "analyse_sonde_lot47bis",
    ):
        assert __import__(name) is not None
    assert "estacade_pieux_01" in sys.modules


def test_the_results_note_says_it_is_a_counter_calculation() -> None:
    from docx import Document

    from aster_expert.notes.resultats import COUNTER_CALCULATION

    note = PROJECT / "livrables" / "notes" / "note_resultats.docx"
    text = " ".join(p.text for p in Document(str(note)).paragraphs)
    assert "Contre-calcul d'un modèle non validé" in text
    assert COUNTER_CALCULATION in text
    assert "jamais un niveau E" in text


# --------------------------------------------------------------------------
# Lot 47 bis : E17 (lecture v2), E18 (essieu de trottoir), E19 (chevêtre 0,80 m)
# --------------------------------------------------------------------------


def test_sidewalk_axle_of_e18(ctx: ProjectContext) -> None:
    from estacade_pieux_01.charges_mobiles import tr_axle_cases

    v = model_values(ctx)
    cases = tr_axle_cases(v)
    assert len(cases) == 57 and cases[0].name == "TRE_M28"
    assert {c.total for c in cases} == {160e3}
    for c in cases:
        assert [a.wheels_y for a in c.axles] == [(2.25,), (2.25,)]
        assert c.axles[1].x - c.axles[0].x == pytest.approx(2.0)
        assert c.axles[0].x - 0.2 >= -1e-9 and c.axles[1].x + 0.2 <= v.length + 1e-9
    assert check_alignment(cases, 0.05) == []
    text, report = build_comm(
        ctx, mesh_label="m.med", options=Options(mode="tr_essieu")
    )
    assert len(report["positions"]) == 57
    assert "PESANTEUR" not in text and "TEP = MECA_STATIQUE" not in text
    prints = re.findall(r'INTERSEC=\("BX_\d{5}T", "BY_TR_TROTTOIR", "(\w+)"\)', text)
    assert prints and set(prints) == {"TROTT"}
    assert "UNION" not in text.split("CREA_POI1")[0].split("Empreintes")[1]


def test_production_comm_is_unchanged_by_lot47bis(ctx: ProjectContext) -> None:
    # Les options du lot 47 bis ne touchent pas la référence : le .comm de production
    # est identique, octet pour octet, au cas versionné du lot 47.
    reference = PROJECT / "references" / "cas" / "estacade_pieux_01.comm"
    text, _ = build_comm(ctx, mesh_label="estacade_mesh.med")
    assert text == reference.read_text(encoding="utf-8")


def test_variant_e19_changes_only_the_cap_height(ctx: ProjectContext) -> None:
    ref, _ = build_comm(ctx, mesh_label="m.med", options=Options(tr_axle=True))
    text, report = build_comm(
        ctx, mesh_label="m.med", options=Options(variant="chevetre_0p80", tr_axle=True)
    )
    diff = [
        (a, b)
        for a, b in zip(ref.splitlines(), text.splitlines(), strict=True)
        if a != b
    ]
    assert len(diff) == 3, diff
    assert any("VALE=(1.2, 0.8)" in b for _, b in diff)
    assert len(report["positions"]) == 242 + 57


def test_lecture_v2_exclut_les_disques_des_tetes_de_pieux(ctx: ProjectContext) -> None:
    import numpy as np

    from estacade_pieux_01.comparaison_v2 import RADIUS, ComparisonV2

    v = model_values(ctx)
    xs = np.round(np.arange(0, 625) * 0.05, 9)
    ys = np.round(-3.0 + np.arange(0, 121) * 0.05, 9)
    gx, gy = np.meshgrid(xs, ys)
    cmp = ComparisonV2.__new__(ComparisonV2)
    cmp.v, cmp.x, cmp.y = v, gx.ravel(), gy.ravel()
    away = cmp._away()
    # Disque fermé de 0,60 m autour de chacune des 14 têtes (disques disjoints).
    per_disc = sum(
        1
        for i in range(-12, 13)
        for j in range(-12, 13)
        if np.hypot(i * 0.05, j * 0.05) <= RADIUS + 1e-9
    )
    assert (~away).sum() == 14 * per_disc

    def at(x: float, y: float) -> bool:
        k = int(
            np.nonzero((np.abs(cmp.x - x) < 1e-9) & (np.abs(cmp.y - y) < 1e-9))[0][0]
        )
        return bool(away[k])

    assert not at(5.6, 2.0) and not at(6.2, 2.0) and not at(5.6, 1.4)
    assert at(6.25, 2.0) and at(5.6, 1.35)
