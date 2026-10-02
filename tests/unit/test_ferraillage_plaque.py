"""Ferraillage 2D d'une plaque dans le tronc commun (lot 43) : déclaration,
commandes écrites pour le générateur, lecture des tables titrées, contrôle
indépendant par le module `aster_expert.rebar`, minima de l'EN 1992-1-1."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from aster_expert.combinaisons.enumeration import enumerate_combinations
from aster_expert.ferraillage.plaque import (
    DENSITIES,
    FORCES,
    _densities,
    analyze_plate,
    check_group_block,
    efge_title,
    ferr_title,
    minimum_areas,
    plate_rebar_block,
    plate_values,
    rebar_combinations,
    titled_table,
)
from aster_expert.projet.check import check_project
from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.declaration import CombinationsSection
from aster_expert.projet.errors import ProjectError

Factory = Callable[..., Any]

_PLATE: dict[str, Any] = {
    "group": "BARRE",
    "label": "dalle d'essai",
    "thickness_m": 0.30,
    "cover_mm": 48.0,
    "fck_mpa": 30.0,
    "fyk_mpa": 500.0,
    "fctm_mpa": 2.9,
    "eys_mpa": 210000.0,
    "alpha_cc": 1.0,
    "sigma_s_ratio": 0.8,
    "sigma_c_els_mpa": 18.0,
    "sigma_c_els_qp_mpa": 13.5,
    "alpha_e": 15.0,
    "kt": 0.4,
    "wk_mm": 0.4,
    "phi_mm": 12.0,
    "families": [
        {
            "family": "ELU fondamentale",
            "type_comb": "ELU",
            "gamma_c": 1.5,
            "gamma_s": 1.15,
        },
        {"family": "ELS caractéristique", "type_comb": "ELS"},
        {"family": "ELS quasi permanente", "type_comb": "ELS_QP"},
    ],
    "check_node": "APPUI",
}


def _ctx(fake_project: Factory, **plate: Any) -> ProjectContext:
    combinations = {
        "permanent": ["G"],
        "gamma_g_unfavourable": 1.35,
        "gamma_q": 1.5,
        "variables": [{"name": "Q", "psi0": 1.0, "psi1": 0.9, "psi2": 0.8}],
    }
    project = fake_project(
        combinations=combinations, rebar={"plates": [{**_PLATE, **plate}]}
    )
    return load_project(project.name, project.repo_root)


def test_a_plate_declaration_is_accepted_and_checked(fake_project: Factory) -> None:
    ctx = _ctx(fake_project)
    assert check_project(ctx) == []

    ctx = _ctx(fake_project, group="ABSENT")
    assert any("ABSENT (plaque à ferrailler" in p for p in check_project(ctx))


def test_a_uls_family_without_partial_factors_is_refused(fake_project: Factory) -> None:
    families = [{"family": "ELU fondamentale", "type_comb": "ELU"}]
    with pytest.raises(ProjectError, match="gamma_c et gamma_s sont requis"):
        _ctx(fake_project, families=families)


def test_an_empty_rebar_section_is_refused(fake_project: Factory) -> None:
    project = fake_project(rebar={})
    with pytest.raises(ProjectError, match="ni `members`"):
        load_project(project.name, project.repo_root)


def test_without_a_favourable_gamma_no_favourable_combination() -> None:
    section = CombinationsSection.model_validate(
        {
            "permanent": ["G"],
            "gamma_g_unfavourable": 1.35,
            "gamma_q": 1.5,
            "variables": [{"name": "Q", "psi0": 1.0, "psi1": 0.9, "psi2": 0.8}],
        }
    )
    combos = enumerate_combinations(section, float)  # type: ignore[arg-type]
    names = [c.name for c in combos]
    assert names == [
        "ELU_FOND_Q_DOM_G_defav",
        "ELS_CARA_Q_DOM",
        "ELS_FREQ_Q_DOM",
        "ELS_QUASI_PERMANENTE",
    ]
    assert combos[0].coefficients == {"G": 1.35, "Q": 1.5}
    assert combos[-1].coefficients == {"G": 1.0, "Q": 0.8}


def test_plate_values_convert_to_model_units(fake_project: Factory) -> None:
    v = plate_values(_ctx(fake_project), _ctx(fake_project).declaration.rebar.plates[0])  # type: ignore[union-attr]
    assert v.cover == pytest.approx(0.048)
    assert v.fck == pytest.approx(30e6)
    assert v.sigs_els == pytest.approx(400e6)
    assert v.wk == pytest.approx(4e-4)
    assert v.phi == pytest.approx(0.012)


def test_the_commands_name_every_parameter_of_their_family(
    fake_project: Factory,
) -> None:
    ctx = _ctx(fake_project)
    plate = ctx.declaration.rebar.plates[0]  # type: ignore[union-attr]
    combos = rebar_combinations(ctx, plate)
    assert [c.name for _, c, _ in combos] == [
        "ELU_FOND_Q_DOM_G_defav",
        "ELS_CARA_Q_DOM",
        "ELS_QUASI_PERMANENTE",
    ]
    result_of = {c.name: f"R{i}" for i, c, _ in combos}
    text = plate_rebar_block(ctx, plate, result_of=result_of, cara="CARA")

    assert text.count("CALC_FERRAILLAGE(") == 3
    assert text.count("ALPHA_CC=1.0") == 3
    assert text.count('UNITE_CONTRAINTE="Pa"') == 3
    assert "C_INF=0.048" in text
    assert "GAMMA_C=1.5" in text and "GAMMA_S=1.15" in text
    assert "SIGC_INF_ELS=18000000.0" in text and "SIGS_ELS=400000000.0" in text
    assert "SIGC_ELS_QP=13500000.0" in text and "WMAX_INF=0.0004" in text
    assert "KT=0.4" in text and "PHI_SUP_Y=0.012" in text
    assert 'TITRE="FER01"' in text and 'TITRE="EFG03"' in text
    assert 'GROUP_MA="APPUI_V"' in text
    override = plate_rebar_block(
        ctx, plate, result_of=result_of, cara="CARA", sigc_els_override=1e9
    )
    assert "SIGC_INF_ELS=1000000000.0" in override
    assert 'OPTION="APPUI"' in check_group_block(plate, "MAIL")


_HEADER = "RESULTAT NOM_CHAM INST NUME_ORDRE MAILLE"


def _ferr_table(title: str, rows: dict[str, dict[str, float]]) -> str:
    lines = [
        f"##{title}ASTER 17.04.00 CONCEPT 0000000c",
        f"{_HEADER} {' '.join(DENSITIES)}",
    ]
    lines += [
        f"R FERR_ELEM 0.0 1 {cell} " + " ".join(f"{v[c]:.12E}" for c in DENSITIES)
        for cell, v in rows.items()
    ]
    return "\n".join([*lines, ""])


def _efge_table(title: str, rows: list[tuple[str, str, dict[str, float]]]) -> str:
    lines = [f"##{title}ASTER 17.04.00", f"{_HEADER} NOEUD {' '.join(FORCES)}"]
    lines += [
        f"R EFGE_ELNO 0.0 1 {cell} {node} " + " ".join(f"{f[c]:.12E}" for c in FORCES)
        for cell, node, f in rows
    ]
    return "\n".join([*lines, ""])


def test_titled_tables_are_read_and_their_defects_named() -> None:
    text = _ferr_table("FER01", {"7": dict.fromkeys(DENSITIES, 1e-4)})
    rows = titled_table(text, "FER01")
    assert rows[0]["MAILLE"] == "7"
    assert float(rows[0]["DNSYS"]) == pytest.approx(1e-4)
    with pytest.raises(ProjectError, match="table FER011 absente"):
        titled_table(text, "FER011")
    with pytest.raises(ProjectError, match="cellules pour"):
        titled_table(text.replace(" 7 ", " 7 X "), "FER01")


def test_the_independent_check_reproduces_the_uls_densities(
    fake_project: Factory, tmp_path: Path
) -> None:
    ctx = _ctx(fake_project)
    plate = ctx.declaration.rebar.plates[0]  # type: ignore[union-attr]
    v = plate_values(ctx, plate)
    combos = rebar_combinations(ctx, plate)
    uls = next(c for c in combos if c[2].type_comb == "ELU")
    nodes = [
        (
            "1",
            "N1",
            {
                "NXX": 0.0,
                "NYY": 0.0,
                "NXY": 0.0,
                "MXX": -60e3,
                "MYY": -30e3,
                "MXY": 0.0,
            },
        ),
        (
            "1",
            "N2",
            {
                "NXX": 0.0,
                "NYY": 0.0,
                "NXY": 0.0,
                "MXX": -62e3,
                "MYY": -31e3,
                "MXY": 0.0,
            },
        ),
    ]
    mean = {c: (nodes[0][2][c] + nodes[1][2][c]) / 2 for c in FORCES}
    expected = _densities(v, uls[2], mean)
    # Sagging (MXX < 0) stretches the lower face: DNSXI and DNSYI only (CA-045).
    assert expected["DNSXS"] == 0.0 and expected["DNSXI"] > expected["DNSYI"] > 0.0
    parts = []
    for index, _, family in combos:
        densities = (
            expected if family.type_comb == "ELU" else dict.fromkeys(DENSITIES, 0.0)
        )
        parts.append(_ferr_table(ferr_title(index), {"1": densities}))
        if family.type_comb == "ELU":
            parts.append(_efge_table(efge_title(index), nodes))
    mess = tmp_path / "fort.6"
    mess.write_text("\n".join(parts), encoding="utf-8")

    result = analyze_plate(ctx, plate, mess, tmp_path / "out")
    chk = result["controle_independant"]
    assert (chk["reussites_moyenne"], chk["comparaisons"]) == (1, 1)
    assert result["enveloppe_besoins_elu_els_qp_m2_par_m"]["DNSXI"] == pytest.approx(
        expected["DNSXI"]
    )
    assert (tmp_path / "out" / "ferraillage_BARRE.md").is_file()

    wrong = {**expected, "DNSXI": expected["DNSXI"] * 1.01}
    mess.write_text(
        "\n".join(
            _ferr_table(
                ferr_title(i),
                {"1": wrong if f.type_comb == "ELU" else dict.fromkeys(DENSITIES, 0.0)},
            )
            + (_efge_table(efge_title(i), nodes) if f.type_comb == "ELU" else "")
            for i, _, f in combos
        ),
        encoding="utf-8",
    )
    result = analyze_plate(ctx, plate, mess, tmp_path / "out")
    assert result["controle_independant"]["reussites_moyenne"] == 0


def test_minimum_areas_of_en_1992() -> None:
    from aster_expert.ferraillage.plaque import PlateValues

    v = PlateValues(
        thickness=0.30,
        cover=0.048,
        fck=30e6,
        fyk=500e6,
        fctm=2.9e6,
        eys=210e9,
        alpha_cc=1.0,
        sigs_els=400e6,
        sigc_els=18e6,
        sigc_els_qp=13.5e6,
        alpha_e=15.0,
        kt=0.4,
        wk=4e-4,
        phi=0.012,
    )
    m = minimum_areas(v)
    assert m["d_m"] == pytest.approx(0.252)
    assert m["as_min_9_2_1_1_m2_per_m"] == pytest.approx(0.26 * 2.9 / 500 * 0.252)
    assert m["as_min_7_3_2_m2_per_m"] == pytest.approx(0.4 * 1.0 * 2.9 * 0.15 / 500)
    assert m["as_min_m2_per_m"] == pytest.approx(max(0.26 * 2.9 / 500 * 0.252, 3.48e-4))
