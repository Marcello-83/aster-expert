"""Tests of the export of lot 50 ter (PONTONS-ALU-01): section properties of U4.42.01,
local axes, parsing of the `.comm`, combinations, CSV format, and the full export with
its recombination check when the deliverables of lot 50 bis are present (they are not
versioned: the test is skipped otherwise). No Docker, no Salome."""

from __future__ import annotations

import csv
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from pontons_alu_01.combinaisons import set_b, set_b_prime
from pontons_alu_01.lot50ter import (
    CASES,
    Concept,
    combination_rows,
    command,
    geo,
    local_axes,
    number,
    occurrences,
    read_comm,
    section_properties,
    shear_circle,
    shear_rectangle,
    write,
)

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "pontons_alu_01"
COMM = PROJECT / "references" / "execution_lot50bis" / "pontons_alu_01.comm"
LIVRABLES = PROJECT / "resultats" / "livrables" / "donnees"


def _props(occurrence: dict[str, object]) -> dict[str, float]:
    return {r.cara: r.value for r in section_properties(occurrence)}


def test_hollow_square_follows_u4_42_01() -> None:
    p = _props({"SECTION": "RECTANGLE", "CARA": ("H", "EP"), "VALE": (0.15, 0.007)})
    h, t = 0.15, 0.007
    assert p["A"] == pytest.approx(h**2 - (h - 2 * t) ** 2, rel=1e-15)
    assert p["IY"] == pytest.approx((h**4 - (h - 2 * t) ** 4) / 12.0, rel=1e-14)
    assert p["IZ"] == pytest.approx(p["IY"], rel=1e-15)
    # Bredt, U4.42.01 : 2·t²·(h − t)⁴ / (2·h·t − 2·t²) = t·(h − t)³.
    assert p["JX"] == pytest.approx(t * (h - t) ** 3, rel=1e-14)
    assert p["AY"] == pytest.approx(p["AZ"], rel=1e-15)


def test_shear_tables_are_read_and_interpolated() -> None:
    assert shear_rectangle(0.80, 0.80) == pytest.approx(2.252)
    assert shear_rectangle(0.0, 0.0) == pytest.approx(1.2)
    assert shear_rectangle(0.05, 0.10) == pytest.approx(1.229)  # Tab(colonne, ligne)
    assert shear_rectangle(0.10, 0.05) == pytest.approx(1.212)
    assert shear_rectangle(0.85, 0.80) == pytest.approx((2.252 + 1.771) / 2.0)
    assert shear_circle(0.0) == pytest.approx(1.167)
    assert shear_circle(0.95) == pytest.approx((1.991 + 2.000) / 2.0)
    with pytest.raises(ValueError, match="hors du tableau"):
        shear_rectangle(0.96, 0.5)


def test_solid_sections() -> None:
    cap = _props({"SECTION": "RECTANGLE", "CARA": ("HY", "HZ"), "VALE": (0.25, 0.4)})
    assert cap["A"] == pytest.approx(0.1)
    assert cap["IY"] == pytest.approx(0.25 * 0.4**3 / 12.0)
    assert cap["IZ"] == pytest.approx(0.4 * 0.25**3 / 12.0)
    pile = _props({"SECTION": "CERCLE", "CARA": ("R",), "VALE": (0.25,)})
    assert pile["A"] == pytest.approx(math.pi * 0.25**2)
    assert pile["JX"] == pytest.approx(2.0 * pile["IY"])
    assert pile["AY"] == pytest.approx(1.167)


def test_generale_keeps_only_the_assigned_keywords() -> None:
    rows = section_properties(
        {"SECTION": "GENERALE", "CARA": ("A", "IY"), "VALE": (1.0, 2.0)}
    )
    assert [(r.cara, r.value) for r in rows] == [("A", 1.0), ("IY", 2.0)]
    assert all(r.origin.startswith("affecté") for r in rows)


def test_local_axes_of_vect_z_and_vect_y() -> None:
    o = np.zeros(3)
    _, y, z = local_axes(o, np.array([1.0, 0, 0]), "VECT_Z", (0.0, 0.0, 1.0))
    assert y.tolist() == [0.0, 1.0, 0.0] and z.tolist() == [0.0, 0.0, 1.0]
    _, y, _ = local_axes(o, np.array([0, 2.0, 0]), "VECT_Z", (0.0, 0.0, 1.0))
    assert y.tolist() == [-1.0, 0.0, 0.0]  # montants, chevêtre : y_l = −X
    _, y, z = local_axes(o, np.array([0, 0, 1.0]), "VECT_Y", (1.0, 0.0, 0.0))
    assert y.tolist() == [1.0, 0.0, 0.0] and z.tolist() == [0.0, 1.0, 0.0]
    # Projection d'un vecteur non orthogonal (U4.42.01) :
    _, _, z = local_axes(o, np.array([1.0, 0, 1.0]), "VECT_Z", (0.0, 0.0, 1.0))
    assert z == pytest.approx([-math.sqrt(0.5), 0.0, math.sqrt(0.5)])


def test_comm_is_parsed_not_executed() -> None:
    comm = read_comm(COMM)
    cara = next(k for _, n, k in comm if n == "AFFE_CARA_ELEM")
    groups = [o["GROUP_MA"] for o in occurrences(cara["POUTRE"])]
    assert groups[0] == "POUTRES_PRINC"
    mult = next(k for _, n, k in comm if n == "MACRO_ELAS_MULT")
    cases = [o["NOM_CAS"] for o in occurrences(mult["CAS_CHARGE"])]
    assert cases == list(CASES[:12])
    charge = occurrences(mult["CAS_CHARGE"])[2]["CHAR_MECA"]
    assert charge == Concept("CH_Q")
    assert "FORCE_POUTRE" in command(comm, "CH_Q")


def test_combinations_cover_sets_b_and_b_prime() -> None:
    rows = combination_rows()
    assert len(rows) == len(set_b()) + len(set_b_prime())
    first = set_b()[0]
    row = next(r for r in rows if r[0] == first.name and r[2] == "B")
    for case, coef in first.coefficients.items():
        assert row[3 + CASES.index(case)] == coef
    houle = [r for r in rows if r[3 + CASES.index("HU")] != 0.0]
    assert {r[3 + CASES.index("HU")] for r in houle} >= {7.5}  # 1,5 × 5 kPa
    b_prime = [r for r in rows if r[2] == "B′"]
    for r in b_prime:
        crowd = r[3 + CASES.index("Q")] or r[3 + CASES.index("QD")]
        wave = r[3 + CASES.index("HU")] or r[3 + CASES.index("HD")]
        assert not (crowd and wave)


def test_numbers_and_format(tmp_path: Path) -> None:
    assert number(-0.0) == "0.0"
    assert float(number(53217.46915097667)) == 53217.46915097667
    assert geo(1.3579999999999999) == 1.358
    assert geo(0.3988746670321393) == 0.398874667032
    path = tmp_path / "t.csv"
    assert write(path, "source ; unités", ["a", "b"], [[1, 0.1 + 0.2]]) == 1
    raw = path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8").splitlines()
    assert lines[0].startswith("# ")
    assert lines[2] == "1;0.30000000000000004"


@pytest.mark.skipif(not LIVRABLES.is_dir(), reason="livrables du lot 50 bis absents")
def test_full_export_and_recombination(tmp_path: Path) -> None:
    script = PROJECT / "scripts" / "export_lot50ter.py"
    result = subprocess.run(
        [sys.executable, str(script), "--sortie", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "projets")},
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "contrôle de recombinaison : réussi" in result.stdout

    def table(name: str) -> list[dict[str, str]]:
        with (tmp_path / name).open(encoding="utf-8") as stream:
            assert stream.readline().startswith("# ")
            return list(csv.DictReader(stream, delimiter=";"))

    elements = table("elements.csv")
    members = table("membres.csv")
    bars = [e for e in elements if e["type"] == "SEG2 POU_D_T"]
    assert len(bars) == 324
    listed = [int(x) for m in members for x in m["elements"].split()]
    assert sorted(listed) == sorted(int(e["element"]) for e in bars)
    total: dict[str, float] = {}
    for m in members:
        total[m["groupe"]] = total.get(m["groupe"], 0.0) + float(m["longueur"])
    assert total["PP_YM"] == pytest.approx(6.25, abs=1e-9)
    assert total["MONT_2"] == pytest.approx(1.86, abs=1e-9)
    hashes = (tmp_path / "empreintes.sha256").read_text("utf-8").splitlines()
    assert len(hashes) == 10
