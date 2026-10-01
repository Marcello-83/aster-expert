"""Lot 39, étapes 3 et 5: the versioned beam case is what the generator writes, its
recorded results keep the criterion's outcome, and the comparison lines for MM
leave MM's columns empty."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_POUTRE = _ROOT / "data" / "examples" / "lot39_poutre"
_ESSAIS = _ROOT / "data" / "examples" / "lot39_essais"
_MESS = (
    _ROOT
    / "data"
    / "processed"
    / "runs"
    / "20260925T125131-c67e28a1"
    / "proc.0"
    / "fort.6"
)


def _load(name: str) -> ModuleType:
    # Scripts du projet (poutre) ou scripts génériques des essais (lot 41).
    project_scripts = _ROOT / "projets" / "quai_cw_test_01" / "scripts"
    folder = (
        project_scripts
        if (project_scripts / f"{name}.py").is_file()
        else (_ROOT / "scripts")
    )
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location(name, folder / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_essais_comm_are_what_the_generator_writes() -> None:
    build = _load("build_lot39_essais")
    for name, (title, cases, calls) in build.ESSAIS.items():
        units = build.UNITS.get(name, build.SI)
        expected = build.build_comm(title, cases, calls, units)
        assert (_ESSAIS / name / f"{name}.comm").read_text("utf-8") == expected, name


def test_plaque_comm_is_what_the_generator_writes() -> None:
    build = _load("build_lot39_plaque")
    assert (_ESSAIS / "plaque" / "plaque.comm").read_text("utf-8") == build.build_comm()


@pytest.mark.skipif(not _MESS.is_file(), reason="listing du modèle complet absent")
def test_beam_comm_is_what_the_trunk_writes(tmp_path: Path) -> None:
    """Lot 41 : le cas CALC_FERRAILLAGE de la poutre est écrit par le tronc commun
    (`aster_expert.ferraillage.poutre`, déclaration `rebar` du projet) ; il ne
    diffère du `.comm` du lot 39 que par le chemin de son producteur."""
    from aster_expert.ferraillage.poutre import member_combinations, prepare_member
    from aster_expert.projet.context import load_project

    ctx = load_project("quai_cw_test_01", _ROOT)
    assert ctx.declaration.rebar is not None
    member = ctx.declaration.rebar.members[0]
    assert len(member_combinations(ctx, member)) == 14
    written = prepare_member(ctx, member, _MESS, tmp_path).read_text("utf-8")
    versioned = (_POUTRE / "poutre.comm").read_text("utf-8")
    producer_old = "# Produit par scripts/build_lot39_poutre.py -- ne pas éditer."
    producer_new = (
        "# Produit par src/aster_expert/ferraillage/poutre.py -- ne pas éditer."
    )
    assert written == versioned.replace(producer_old, producer_new)
    for name in ("poutre.mail", "poutre.export", "sections.csv", "efforts.csv"):
        assert (tmp_path / name).read_bytes() == (_POUTRE / name).read_bytes(), name


def test_beam_case_uses_d19_and_d18() -> None:
    text = (_POUTRE / "poutre.comm").read_text("utf-8")
    for key in ("C_SUP_Y", "C_INF_Y", "C_SUP_Z", "C_INF_Z"):
        assert f"{key}=0.1," in text
    assert "PHI_INF_Y=0.04," in text
    assert "WMAX_SUP_Z=0.0002," in text
    assert text.count("CALC_FERRAILLAGE(") == 4
    assert "FERR_MIN" not in text


def test_hand_check_outcome_is_recorded_as_run() -> None:
    record = json.loads((_POUTRE / "controle_main.json").read_text("utf-8"))
    assert record["nombre_de_comparaisons"] == 63
    assert record["dans_le_critere"] == 63
    # Two comparisons at the bollard under Q1-dominant combinations, where the
    # moments are numerical noise (1e-5 N.m): Code_Aster prints 4,8e-12 and
    # 1,2e-11 m2 against the written absolute threshold of 1e-12 m2 -- reported
    # as failures, the criterion is not changed after the run.
    assert record["echecs"] == 2
    failed = [c for c in record["comparaisons"] if c["reussite"] is False]
    assert {c["section"] for c in failed} == {"bollard (X = 0)"}
    assert all(abs(c["MFY_MNm"]) < 1e-9 and abs(c["MFZ_MNm"]) < 1e-9 for c in failed)
    passed = [c for c in record["comparaisons"] if c["reussite"]]
    assert max(c["ecart_relatif_max"] for c in passed) <= 1e-6


def test_synthesis_retains_the_largest_of_calc_ferraillage_and_minima() -> None:
    with (_POUTRE / "synthese.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 65
    for row in rows:
        for face, group in (("AYS", "AY"), ("AYI", "AY"), ("AZS", "AZ"), ("AZI", "AZ")):
            retained = float(row[f"{face}_retenu"])
            assert retained == pytest.approx(
                max(
                    float(row[f"{face}_calc_ferraillage"]),
                    float(row[f"As_min_{group}_9_2_1_1"]),
                    float(row[f"As_min_{group}_7_3_2"]),
                ),
                rel=1e-6,
            )


def test_comparison_lines_leave_mm_columns_empty() -> None:
    path = _ROOT / "data" / "examples" / "lot38_essais" / "ligne_comparaison_mm.csv"
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 10
    for row in rows:
        assert row["As_tendue_MM_m2"] == ""
        assert row["As_comprimee_MM_m2"] == ""
        assert row["ecart_tendue"] == ""
        assert row["ds_m"] == row["di_m"] == "0.1"
        assert row["etat_limite"] in (
            "ELU fondamentale",
            "ELS caractéristique",
            "ELS quasi permanente",
        )
        # h is the dimension in the bending plane: never MM's first-try 1,00 m.
        if "MFZ" in row["plan_de_flexion"]:
            assert (row["h_m"], row["b_m"]) == ("2.5", "1.4")
        else:
            assert (row["h_m"], row["b_m"]) == ("1.4", "2.5")
        assert row["fibre_inferieure_logiciel_face_tendue"]
        assert row["fibre_superieure_logiciel_face_comprimee"]
