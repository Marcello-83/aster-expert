"""Combinations 100 to 115 of the source model (table B5), reproduced as they are (E11).

Each number has four families: ELS f (frequent), ELS c (characteristic), ELU+ (gamma_G
= 1.35) and ELU- (gamma_G = 1.00). G = PP + G2; LM1 = UDL + TR + TS, enveloped over the
TS positions: "axé" for 102 to 108, "bord de voie" for 109 to 115 (B5). The
coefficients below are those of B5, transcribed once here; a test reads them again in
the text of the annex (`donnees/sources/annexe_B_lot47.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

FAMILIES = ("ELS_f", "ELS_c", "ELU+", "ELU-")
GAMMA_G = {"ELS_f": 1.0, "ELS_c": 1.0, "ELU+": 1.35, "ELU-": 1.0}

# Coefficients (LM1, FR, TE) of each base row of B5, per family (ELS f, ELS c, ELU).
_BASE: dict[str, dict[str, dict[str, float]]] = {
    "100": {
        "ELS_f": {"TR": 0.5},
        "ELS_c": {"TR": 1.0},
        "ELU": {"TR": 1.5},
    },
    "101": {
        "ELS_f": {"FR": 0.5},
        "ELS_c": {"FR": 1.0},
        "ELU": {"FR": 1.5},
    },
    "102": {
        "ELS_f": {"LM1": 0.5},
        "ELS_c": {"LM1": 1.0},
        "ELU": {"LM1": 1.5},
    },
    "103": {
        "ELS_f": {"LM1": 0.5, "FR": 0.3},
        "ELS_c": {"LM1": 1.0, "FR": 0.7},
        "ELU": {"LM1": 1.5, "FR": 1.05},
    },
    "106": {
        "ELS_f": {"LM1": 0.3, "FR": 0.5},
        "ELS_c": {"LM1": 0.7, "FR": 1.0},
        "ELU": {"LM1": 1.05, "FR": 1.5},
    },
}
_TE = {"ELS_f": 0.5, "ELS_c": 0.6, "ELU": 0.9}
"""Coefficient of TE+ (rows 104, 107) or TE- (rows 105, 108) added to 103 or 106."""


@dataclass(frozen=True)
class Combination:
    number: int
    family: str
    gamma_g: float
    coefficients: dict[str, float]
    """Coefficients of the variable actions: TR, FR, LM1, TE+, TE-."""
    ts_position: str | None
    """`axe`, `bord` or None (no LM1)."""

    @property
    def name(self) -> str:
        return f"{self.number} {self.family}"


def _rows() -> dict[int, dict[str, dict[str, float]]]:
    rows: dict[int, dict[str, dict[str, float]]] = {
        100: _BASE["100"],
        101: _BASE["101"],
        102: _BASE["102"],
        103: _BASE["103"],
        106: _BASE["106"],
    }
    for number, base, te in (
        (104, "103", "TE+"),
        (105, "103", "TE-"),
        (107, "106", "TE+"),
        (108, "106", "TE-"),
    ):
        rows[number] = {
            fam: {**coefs, te: _TE[fam]} for fam, coefs in _BASE[base].items()
        }
    for number in range(102, 109):
        rows[number + 7] = rows[number]
    return dict(sorted(rows.items()))


def combinations() -> tuple[Combination, ...]:
    out: list[Combination] = []
    for number, row in _rows().items():
        position = None
        if "LM1" in row["ELS_c"]:
            position = "axe" if number <= 108 else "bord"
        for family in FAMILIES:
            key = "ELU" if family.startswith("ELU") else family
            out.append(
                Combination(
                    number=number,
                    family=family,
                    gamma_g=GAMMA_G[family],
                    coefficients=dict(row[key]),
                    ts_position=position,
                )
            )
    return tuple(out)


def find(number: int, family: str) -> Combination:
    for c in combinations():
        if c.number == number and c.family == family:
            return c
    message = f"combinaison {number} {family} absente de B5"
    raise KeyError(message)


__all__ = ["FAMILIES", "GAMMA_G", "Combination", "combinations", "find"]
