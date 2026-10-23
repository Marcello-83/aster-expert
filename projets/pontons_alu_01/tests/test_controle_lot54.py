"""Contrôle post-lot 54: reading of the labels of the combinations (no Code_Aster)."""

from __future__ import annotations

from pontons_alu_01.controle_lot54 import label_coefficients

TABLE = {
    "G": {"G1": 1.0, "G2": 1.0},
    "G_DEJ_100": {"G1": 1.0, "G2": 1.0, "DEJ": 1.0},
    "TM": {"TM": 1.0},
    "QD": {"QD_M0": 1.0, "QD_M4": 1.0, "QD_M5": 1.0},
    "Q": {"Q_M0": 1.0, "Q_M1": 1.0},
}


def test_label_with_modules_and_factors() -> None:
    state, coefs = label_coefficients(
        "ELS_caracteristique: G_DEJ_100×1 + TM×0.6 + QD[M4+M5]×0.77", TABLE
    )
    assert state == "ELS_caracteristique"
    assert coefs == {
        "G1": 1.0,
        "G2": 1.0,
        "DEJ": 1.0,
        "TM": 0.6,
        "QD_M4": 0.77,
        "QD_M5": 0.77,
    }


def test_q_and_qd_are_distinct_families() -> None:
    _, coefs = label_coefficients("ELU_accidentel: Q[M0+M1]×0.5", TABLE)
    assert coefs == {"Q_M0": 0.5, "Q_M1": 0.5}
