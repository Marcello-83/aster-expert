"""Load combinations built from a project declaration (lot 41, étape 2.4).

The families are those of EN 1990 (6.10 fundamental, 6.11 accidental, 6.14 to
6.16 characteristic, frequent, quasi-permanent); the coefficients are never
written in the code: γ and ψ are read from the project's data file through the
declaration (`combinations` section) -- the data file is the reference (lot 40
audit: the coefficients of the first project were written twice, in the code
and in the data).

Rules, for variable actions `Q_1 ... Q_n` declared in this order:

- fundamental: for each dominant `Q_i`, for γG unfavourable then favourable
  (applied to the whole permanent block), with then without the other actions
  (each at γQ ψ0);
- accidental: written out in the declaration;
- characteristic: permanent block at 1, dominant at 1, the others at ψ0 (with,
  then without);
- frequent: dominant at ψ1, the others at ψ2 by default (EN 1990 6.15b), or at
  ψ0 when the project's decision says so (`frequent_accompanying`);
- quasi-permanent: permanent block at 1, every variable action at ψ2.

A combination carries only the cases it names (no zero coefficient added); the
order of its coefficients is the order above, which fixes the order of the
floating-point sum in `combine`.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from aster_expert.projet.declaration import CombinationsSection, Number

FUNDAMENTAL = "ELU fondamentale"
ACCIDENTAL = "ELU accidentelle"
CHARACTERISTIC = "ELS caractéristique"
FREQUENT = "ELS fréquente"
QUASI_PERMANENT = "ELS quasi permanente"


class Combination(BaseModel):
    """One combination: its name, family and coefficient of each elementary case
    (absent cases carry no key, not a zero -- `coefficients.get(case, 0.0)`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    family: str
    coefficients: dict[str, float]


def _suffix(others: list[str]) -> str:
    return "_" + "_".join(others) + "_ACC" if others else ""


def enumerate_combinations(
    section: CombinationsSection, number: Callable[[Number], float]
) -> list[Combination]:
    """The combinations of the declaration, `number` resolving a declared value
    (a literal or a value of the data file)."""
    gamma_unfav = number(section.gamma_g_unfavourable)
    gamma_fav = number(section.gamma_g_favourable)
    gamma_q = number(section.gamma_q)
    psi = {
        v.name: (number(v.psi0), number(v.psi1), number(v.psi2))
        for v in section.variables
    }
    names = [v.name for v in section.variables]
    out: list[Combination] = []
    for dominant in names:
        others = [n for n in names if n != dominant]
        for gamma_name, gamma_g in (("defav", gamma_unfav), ("favo", gamma_fav)):
            for with_acc in (True, False) if others else (False,):
                coefficients = dict.fromkeys(section.permanent, gamma_g)
                coefficients[dominant] = gamma_q
                if with_acc:
                    for other in others:
                        coefficients[other] = gamma_q * psi[other][0]
                out.append(
                    Combination(
                        name=(
                            f"ELU_FOND_{dominant}_DOM"
                            f"{_suffix(others) if with_acc else ''}_G_{gamma_name}"
                        ),
                        family=FUNDAMENTAL,
                        coefficients=coefficients,
                    )
                )
    out += [
        Combination(
            name=a.name,
            family=a.family,
            coefficients={case: number(v) for case, v in a.coefficients.items()},
        )
        for a in section.accidental
    ]
    accompanying_frequent = 0 if section.frequent_accompanying == "psi0" else 2
    for key, label, dominant_index, others_index in (
        ("ELS_CARA", CHARACTERISTIC, None, 0),
        ("ELS_FREQ", FREQUENT, 1, accompanying_frequent),
    ):
        for dominant in names:
            others = [n for n in names if n != dominant]
            coeff_dom = 1.0 if dominant_index is None else psi[dominant][dominant_index]
            for with_acc in (True, False) if others else (False,):
                coefficients = dict.fromkeys(section.permanent, 1.0)
                coefficients[dominant] = coeff_dom
                if with_acc:
                    for other in others:
                        coefficients[other] = psi[other][others_index]
                out.append(
                    Combination(
                        name=(
                            f"{key}_{dominant}_DOM{_suffix(others) if with_acc else ''}"
                        ),
                        family=label,
                        coefficients=coefficients,
                    )
                )
    quasi = dict.fromkeys(section.permanent, 1.0)
    for name in names:
        quasi[name] = psi[name][2]
    out.append(
        Combination(
            name="ELS_QUASI_PERMANENTE", family=QUASI_PERMANENT, coefficients=quasi
        )
    )
    return out


def combine(coefficients: dict[str, float], values: dict[str, float]) -> float:
    """`sum(coefficients[case] * values[case])` over the cases the combination
    carries, in its order -- `values` must have every case `coefficients` names."""
    return sum(coeff * values[case] for case, coeff in coefficients.items())


def grouped_by_coefficient(
    coefficients: dict[str, float], values: dict[str, float]
) -> float:
    """The same sum computed independently: cases sharing a coefficient summed
    first, then multiplied once (`1.35 * (G1 + G2) + 1.5 * Q`). Used as the hand
    check of `combine`."""
    groups: dict[float, float] = {}
    for case, coeff in coefficients.items():
        if coeff in groups:
            groups[coeff] = groups[coeff] + values[case]
        else:
            groups[coeff] = values[case]
    return sum(coeff * total for coeff, total in groups.items())


__all__ = [
    "ACCIDENTAL",
    "CHARACTERISTIC",
    "FREQUENT",
    "FUNDAMENTAL",
    "QUASI_PERMANENT",
    "Combination",
    "combine",
    "enumerate_combinations",
    "grouped_by_coefficient",
]
