"""Lecture des tables `IMPR_TABLE` d'un `.mess` (lot 35), sur un listing de synthèse
qui reprend la forme réelle des deux familles de tables (`POST_RELEVE_T` et
`CREA_TABLE` avec `IMPR_TABLE/TITRE`)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.report.tables import TableError, iter_tables, read_tables, records

_MESS = """\
# du bruit avant les tables
.. _stg1_txt1
##ASTER 17.04.00 CONCEPT 00000052 CALCULE LE 25/09/2026 A 07:17:28 DE TYPE
INTITULE         NOEUD    RESU     NOM_CHAM   NUME_ORDRE   INST   COOR_X   COOR_Y   COOR_Z   DY
RESSORTS_G       65       0000001b DEPL       1   0.0E+00   -1.5E+00   -1.1E-01   -1.8E+01  -3.3E-03
RESSORTS_G       66       0000001b DEPL       1   0.0E+00   -1.4E+00   -1.0E-01   -1.7E+01  -4.4E-03

# entre deux tables
##EFTIR_GASTER 17.04.00 CONCEPT 00000057 CALCULE LE 25/09/2026 A 07:17:30 DE TYPE
RESULTAT   NOM_CHAM   INST   NUME_ORDRE   MAILLE   NOEUD   SOUS_POINT   COOR_X   COOR_Y   COOR_Z   N
EFA_G      EFGE_ELNO  0.0E+00   1 10067    146   1  -2.6E+00   7.1E-01   2.5E+00   2.684E+05
EFA_G      EFGE_ELNO  0.0E+00   1 10067    578   1  -2.6E+00   2.5E+01  -6.4E+00   2.684E+05
#
##ASTER 17.04.00 CONCEPT 00000053 CALCULE LE 25/09/2026 A 07:17:30 DE TYPE
INTITULE   RESU   NOM_CHAM   NUME_ORDRE   INST   DX   DY   DZ
AUTRE_G    00000021 REAC_NODA   1   0.0E+00   1.0E+00   2.0E+00   3.0E+00
"""


@pytest.fixture
def mess(tmp_path: Path) -> Path:
    path = tmp_path / "fort.6"
    path.write_text(_MESS, encoding="utf-8")
    return path


def test_both_families_of_tables_are_read_by_their_name(mess: Path) -> None:
    tables = read_tables(mess, ["RESSORTS_G", "EFTIR_G"])

    springs = tables["RESSORTS_G"]
    assert len(springs) == 2
    assert springs[0]["DY"] == pytest.approx(-3.3e-3)
    assert springs[1]["COOR_Z"] == pytest.approx(-17.0)
    ties = tables["EFTIR_G"]
    assert len(ties) == 2
    assert ties[0]["MAILLE"] == "10067"
    assert ties[0]["N"] == pytest.approx(2.684e5)
    assert ties[1]["COOR_Z"] == pytest.approx(-6.4)


def test_a_missing_table_is_an_error_never_an_empty_table(mess: Path) -> None:
    with pytest.raises(TableError, match="ABSENTE_G"):
        read_tables(mess, ["RESSORTS_G", "ABSENTE_G"])


def test_only_the_wanted_tables_are_cut_into_cells(mess: Path) -> None:
    names = [name for name, _, _ in iter_tables(mess, {"AUTRE_G"})]

    assert names == ["AUTRE_G"]
    assert [n for n, _, _ in iter_tables(mess)] == ["RESSORTS_G", "EFTIR_G", "AUTRE_G"]


def test_a_row_with_an_empty_cell_is_aligned_on_its_numeric_tail() -> None:
    header = ["INTITULE", "A", "B", "C"]

    (row,) = records(header, [["T", "1.0E+00", "2.0E+00"]])

    assert row["B"] == pytest.approx(1.0)
    assert row["C"] == pytest.approx(2.0)
    assert row["_head"] == "T"
