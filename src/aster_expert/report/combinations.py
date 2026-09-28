"""Linear combinations of D17 (point 13, lot 38), enumerated in Python.

`POST_COMBINAISON`/`COMBINAISON_FERRAILLAGE` exist in Code_Aster 17.4 for this
purpose, but the six elementary cases of the combi-wall model (`G`, `EAU_P`,
`EAU_A`, `Q1`, `Q3`, `A`) are already linear-elastic `MECA_STATIQUE` results with
their `EFGE_ELNO` printed as tables (`comm.footer`): combining them is a linear
operation on already-computed numbers, so it is done here, in the tool, from those
tables (CLAUDE.md-consistent choice stated in the lot 38 step 2 write-up) --
Code_Aster is not re-run to reproduce a combination its own elementary results
already determine linearly. `CALC_FERRAILLAGE`/`COMBINAISON_FERRAILLAGE`, which do
need a `mult_elas` `RESULTAT` in Code_Aster, are exercised on synthetic essais
(`aster_expert.rebar`), not on this combined beam export.

D17's text (`arbitrage_combiwall_MM_v6.md`) is reproduced exactly: γG = 1,35
(défavorable) or 1,00 (favorable) applied to `G + EAU_P` as one block, γQ = 1,50;
ψ0/ψ1/ψ2 of Q1 = 0,7/0,5/0,3, of Q3 = 0,7/0,5/0.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")

GAMMA_G_DEFAVORABLE = 1.35
GAMMA_G_FAVORABLE = 1.00
GAMMA_Q = 1.50
PSI = {"Q1": (0.7, 0.5, 0.3), "Q3": (0.7, 0.5, 0.0)}
"""`(psi0, psi1, psi2)` per variable action."""


class Combination(BaseModel):
    """One combination: its name, family and coefficient of each elementary case
    (absent cases carry no key, not a zero -- `coefficients.get(case, 0.0)`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    family: str
    coefficients: dict[str, float]


def _fondamentale() -> list[Combination]:
    out = []
    for dominant in ("Q1", "Q3"):
        accompanying = "Q3" if dominant == "Q1" else "Q1"
        psi0_acc = PSI[accompanying][0]
        for gamma_name, gamma_g in (
            ("defav", GAMMA_G_DEFAVORABLE),
            ("favo", GAMMA_G_FAVORABLE),
        ):
            for with_acc in (True, False):
                coefficients = {"G": gamma_g, "EAU_P": gamma_g, dominant: GAMMA_Q}
                if with_acc:
                    coefficients[accompanying] = GAMMA_Q * psi0_acc
                out.append(
                    Combination(
                        name=(
                            f"ELU_FOND_{dominant}_DOM"
                            f"{'_' + accompanying + '_ACC' if with_acc else ''}"
                            f"_G_{gamma_name}"
                        ),
                        family="ELU fondamentale",
                        coefficients=coefficients,
                    )
                )
    return out


def _accidentelle() -> list[Combination]:
    return [
        Combination(
            name="ELU_ACCIDENTELLE",
            family="ELU accidentelle",
            coefficients={"G": 1.0, "EAU_A": 1.0, "A": 1.0, "Q1": 0.5},
        )
    ]


def _els(
    family_key: str, family_label: str, psi_index: int | None
) -> list[Combination]:
    out = []
    for dominant in ("Q1", "Q3"):
        accompanying = "Q3" if dominant == "Q1" else "Q1"
        coeff_dom = 1.0 if psi_index is None else PSI[dominant][psi_index]
        psi_acc = PSI[accompanying][0]  # accompanying action always carries psi0
        for with_acc in (True, False):
            coefficients = {"G": 1.0, "EAU_P": 1.0, dominant: coeff_dom}
            if with_acc:
                coefficients[accompanying] = psi_acc
            out.append(
                Combination(
                    name=(
                        f"{family_key}_{dominant}_DOM"
                        f"{'_' + accompanying + '_ACC' if with_acc else ''}"
                    ),
                    family=family_label,
                    coefficients=coefficients,
                )
            )
    return out


def _quasi_permanente() -> list[Combination]:
    return [
        Combination(
            name="ELS_QUASI_PERMANENTE",
            family="ELS quasi permanente",
            coefficients={
                "G": 1.0,
                "EAU_P": 1.0,
                "Q1": PSI["Q1"][2],
                "Q3": PSI["Q3"][2],
            },
        )
    ]


def enumerate_combinations() -> list[Combination]:
    """The 18 combinations of D17: 8 ELU fondamentale (dominant x accompagnement x
    γG), 1 ELU accidentelle, 4 ELS caractéristique, 4 ELS fréquente, 1 ELS quasi
    permanente."""
    return [
        *_fondamentale(),
        *_accidentelle(),
        *_els("ELS_CARA", "ELS caractéristique", None),
        *_els("ELS_FREQ", "ELS fréquente", 1),
        *_quasi_permanente(),
    ]


def combine(coefficients: dict[str, float], values: dict[str, float]) -> float:
    """`sum(coefficients[case] * values[case])` over the cases the combination
    actually carries -- `values` must have every case `coefficients` names."""
    return sum(coeff * values[case] for case, coeff in coefficients.items())


__all__ = [
    "CASES",
    "GAMMA_G_DEFAVORABLE",
    "GAMMA_G_FAVORABLE",
    "GAMMA_Q",
    "PSI",
    "Combination",
    "combine",
    "enumerate_combinations",
]
