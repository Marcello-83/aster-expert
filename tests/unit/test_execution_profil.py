"""Time profile by command, read from the timer table of a listing (lot 47 quater)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.execution.profil import read_profile

TABLE = """\
 <I>       FIN D'EXECUTION LE : MA-06-OCTO-2026 14:38:35

 ********************************************************************************
 * COMMAND                  :       USER :     SYSTEM :   USER+SYS :    ELAPSED *
 ********************************************************************************
 * DEBUT                    :       0.02 :       0.15 :       0.17 :       0.20 *
 * LIRE_MAILLAGE            :       0.13 :       0.17 :       0.30 :       0.44 *
 * MACRO_ELAS_MULT          :      93.00 :       5.79 :      98.79 :     126.46 *
 * CALC_CHAMP               :      51.67 :       5.92 :      57.59 :      59.11 *
 * CALC_CHAMP               :       0.78 :       0.01 :       0.79 :       0.80 *
 * MACRO_ELAS_MULT          :      88.12 :       7.34 :      95.46 :     160.30 *
 * IMPR_RESU                :       2.34 :       0.10 :       2.44 :       2.44 *
 * FIN                      :       0.08 :       0.18 :       0.26 :       0.54 *
 *  . check syntax          :       1.73 :       0.78 :       2.51 :       4.87 *
 * after 500 timers         :       0.57 :       0.22 :       0.79 :       1.08 *
 *  . fortran               :     240.82 :      21.88 :     262.70 :     300.77 *
 ********************************************************************************
 * TOTAL_JOB                :     244.26 :      26.72 :     270.98 :     351.37 *
 ********************************************************************************
"""


def test_the_timer_table_is_summed_by_command(tmp_path: Path) -> None:
    mess = tmp_path / "fort.6"
    mess.write_text("début du listing\n" + TABLE, encoding="utf-8")
    profile = read_profile(mess)
    assert profile.total is not None and profile.total.elapsed == 351.37
    assert profile.by_command["MACRO_ELAS_MULT"].elapsed == pytest.approx(286.76)
    assert profile.occurrences["CALC_CHAMP"] == 2
    # « . fortran » breaks TOTAL_JOB down by nature: never added to the commands.
    assert "fortran" in profile.breakdown and ". fortran" not in profile.by_command
    groups = profile.grouped(
        {"maillage": ("LIRE_MAILLAGE",), "résolution": ("MACRO_ELAS_MULT",)}
    )
    assert groups["résolution"] == pytest.approx(286.76)
    # The rest holds the other commands and the « after 500 timers » line.
    assert groups["reste"] == pytest.approx(0.20 + 59.11 + 0.80 + 2.44 + 0.54 + 1.08)
    assert sum(groups.values()) == pytest.approx(351.37, abs=0.01)


def test_a_listing_without_table_is_refused(tmp_path: Path) -> None:
    mess = tmp_path / "fort.6"
    mess.write_text("rien\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aucun tableau des temps"):
        read_profile(mess)
