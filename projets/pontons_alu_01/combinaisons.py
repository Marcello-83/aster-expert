"""Combinations of PONTONS-ALU-01 (lot 50, annex « Données » § D5).

Two sets from one run:

- **A, « modèle AVP »**: the nine combinations of the Sofistik file S2, reproduced as
  they are, defects included (houle permanent at 1,0, TA at 0,6 in the accidental
  one...). H is 20·Hu or 10·Hd, TA is TA+ or TA−, exclusive; G is 1,2 / 0,9 in the
  fundamental ones; Q, AM, AC, ACA (factor 0 when favourable) are at 0 or at their
  factor, every choice enumerated so that the envelope takes the worst.
- **B, « PRO »**: generated from the EN 1990 formulas and the table of § D5: each
  variable action dominant in turn, G favourable or unfavourable as a block, every
  accompanying action present or absent (γ favourable = 0), exclusive variants
  (Hu/Hd, T+/T−, AM−/AM+, AC−/AC+, ACA−/ACA+, Q/Q½), ACA in the accidental ones only
  and AC never there.

Identical coefficient sets are kept once (the first name is kept)."""

from __future__ import annotations

import itertools
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Combination:
    name: str
    family: str
    coefficients: dict[str, float]
    definition: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "fixed": dict(self.coefficients),
            "definition": self.definition,
        }


@dataclass(frozen=True)
class Action:
    """A variable action of set B: its exclusive variants (case -> scale applied to
    the elementary case), ψ and γ unfavourable (§ D5)."""

    name: str
    variants: dict[str, float]
    psi0: float
    psi1: float
    psi2: float
    gamma: float


H_SCALE_B = 5.0
"""kPa: houle of set B, 5 kPa up or down (P9), on cases of 1 kPa."""
ACTIONS_B = (
    Action("H", {"HU": H_SCALE_B, "HD": H_SCALE_B}, 0.77, 0.77, 0.2, 1.5),
    Action("T", {"TP": 1.0, "TM": 1.0}, 0.6, 0.6, 0.5, 1.5),
    Action("AM", {"AMM": 1.0, "AMP": 1.0}, 0.77, 0.77, 0.2, 1.30),
    Action("AC", {"ACM": 1.0, "ACP": 1.0}, 1.0, 0.0, 0.0, 1.0),
    Action("Q", {"Q": 1.0, "QD": 1.0}, 0.77, 0.77, 0.2, 1.3),
)
ACCIDENTAL_B = {"AAM": 1.0, "AAP": 1.0}
G_UNFAV, G_FAV = 1.2, 0.9
PERMANENT = ("G1", "G2")

FAMILIES = {
    "A": ("A_ELU", "A_ELUA", "A_ELS_C"),
    "B": ("B_ELU", "B_ELUA", "B_ELS_C", "B_ELS_F", "B_ELS_QP"),
}
STATE_OF_FAMILY = {
    "A_ELU": "ELU_fondamental",
    "A_ELUA": "ELU_accidentel",
    "A_ELS_C": "ELS_caracteristique",
    "B_ELU": "ELU_fondamental",
    "B_ELUA": "ELU_accidentel",
    "B_ELS_C": "ELS_caracteristique",
    "B_ELS_F": "ELS_frequent",
    "B_ELS_QP": "ELS_quasi_permanent",
}


@dataclass
class _Builder:
    out: list[Combination] = field(default_factory=list)
    seen: set[tuple[tuple[str, float], ...]] = field(default_factory=set)

    def add(self, name: str, family: str, coefs: dict[str, float]) -> None:
        clean = {c: round(v, 12) for c, v in coefs.items() if v != 0.0}
        key = (family, *sorted(clean.items()))
        if key in self.seen:
            return
        self.seen.add(key)  # type: ignore[arg-type]
        definition = " + ".join(f"{v:g}·{c}" for c, v in clean.items())
        self.out.append(Combination(name, family, clean, f"{name} = {definition}"))


def _add(coefs: dict[str, float], case: str, value: float) -> None:
    coefs[case] = coefs.get(case, 0.0) + value


# --- set A ---------------------------------------------------------------------------

S2 = (
    # number, family, G (unfav, fav), Q factor, other case, other factor
    (10, "A_ELU", (1.2, 0.9), 1.3, "ACM", 1.0),
    (20, "A_ELU", (1.2, 0.9), 1.3, "AMM", 1.0),
    (30, "A_ELU", (1.2, 0.9), 1.0, "AMM", 1.0),
    (40, "A_ELU", (1.2, 0.9), 1.0, "ACM", 1.3),
    (50, "A_ELUA", (1.0,), 0.26, "AAM", 1.0),
    (60, "A_ELS_C", (1.0,), 1.0, "ACM", 0.77),
    (70, "A_ELS_C", (1.0,), 1.0, "AMM", 1.0),
    (80, "A_ELS_C", (1.0,), 0.77, "AMM", 1.0),
    (90, "A_ELS_C", (1.0,), 0.77, "ACM", 1.0),
)
H_A = {"HU": 20.0, "HD": 10.0}
TA_A = ("TAP", "TAM")
TA_FACTOR_A = 0.6


def set_a() -> list[Combination]:
    b = _Builder()
    for number, family, gammas, q, other, k in S2:
        for g, (h, hk), ta, q_on, o_on in itertools.product(
            gammas, H_A.items(), TA_A, (True, False), (True, False)
        ):
            coefs: dict[str, float] = {}
            for c in PERMANENT:
                _add(coefs, c, g)
            _add(coefs, h, hk)
            _add(coefs, ta, TA_FACTOR_A)
            if q_on:
                _add(coefs, "Q", q)
            if o_on:
                _add(coefs, other, k)
            tag = (
                f"G{g:g}_{h}_{ta}"
                + ("_Q" if q_on else "")
                + (f"_{other}" if o_on else "")
            )
            b.add(f"A{number}_{tag}", family, coefs)
    return b.out


# --- set B ---------------------------------------------------------------------------


def _choices(action: Action) -> list[tuple[str, float] | None]:
    """Absent, or one of the exclusive variants."""
    return [None, *action.variants.items()]


def _accompanying(
    others: tuple[Action, ...],
) -> Iterator[tuple[tuple[Action, tuple[str, float]], ...]]:
    for picks in itertools.product(*(_choices(a) for a in others)):
        yield tuple(
            (a, p) for a, p in zip(others, picks, strict=False) if p is not None
        )


def _tag(parts: list[str]) -> str:
    return "_".join(parts)


def set_b() -> list[Combination]:
    b = _Builder()
    # ELU fondamental (6.10) : G en bloc, dominante γ·Q_k1, accompagnement γ·ψ0·Q_ki.
    for g, lead in itertools.product((G_UNFAV, G_FAV), ACTIONS_B):
        others = tuple(a for a in ACTIONS_B if a is not lead)
        for lead_case, lead_scale in lead.variants.items():
            for acc in _accompanying(others):
                coefs: dict[str, float] = {}
                for c in PERMANENT:
                    _add(coefs, c, g)
                _add(coefs, lead_case, lead.gamma * lead_scale)
                for a, (case, scale) in acc:
                    _add(coefs, case, a.gamma * a.psi0 * scale)
                tag = _tag([f"G{g:g}", lead_case] + [c for _, (c, _) in acc])
                b.add(f"B_ELU_{tag}", "B_ELU", coefs)
    # ELU accidentel : G + ACA + ψ1·Q_k1 + Σ ψ2·Q_ki, AC exclu.
    variables = tuple(a for a in ACTIONS_B if a.name != "AC")
    for aca in ACCIDENTAL_B:
        leads: tuple[Action | None, ...] = (None, *variables)
        for acc_lead in leads:
            others = tuple(a for a in variables if a is not acc_lead)
            lead_choices: list[tuple[str, float] | None] = (
                [None] if acc_lead is None else list(acc_lead.variants.items())
            )
            for lead_pick in lead_choices:
                for acc in _accompanying(others):
                    coefs = dict.fromkeys(PERMANENT, 1.0)
                    _add(coefs, aca, 1.0)
                    parts = [aca]
                    if acc_lead is not None and lead_pick is not None:
                        _add(coefs, lead_pick[0], acc_lead.psi1 * lead_pick[1])
                        parts.append(lead_pick[0])
                    for a, (case, scale) in acc:
                        _add(coefs, case, a.psi2 * scale)
                        parts.append(case)
                    b.add(f"B_ELUA_{_tag(parts)}", "B_ELUA", coefs)
    # ELS caractéristique, fréquent, quasi permanent.
    rules: tuple[tuple[str, Callable[[Action], float], Callable[[Action], float]], ...]
    rules = (
        ("B_ELS_C", lambda _a: 1.0, lambda a: a.psi0),
        ("B_ELS_F", lambda a: a.psi1, lambda a: a.psi2),
    )
    for family, lead_psi, acc_psi in rules:
        for lead in ACTIONS_B:
            others = tuple(a for a in ACTIONS_B if a is not lead)
            for lead_case, lead_scale in lead.variants.items():
                for acc in _accompanying(others):
                    coefs = dict.fromkeys(PERMANENT, 1.0)
                    _add(coefs, lead_case, lead_psi(lead) * lead_scale)
                    for a, (case, scale) in acc:
                        _add(coefs, case, acc_psi(a) * scale)
                    tag = _tag([lead_case] + [c for _, (c, _) in acc])
                    b.add(f"{family}_{tag}", family, coefs)
    for acc in _accompanying(ACTIONS_B):
        coefs = dict.fromkeys(PERMANENT, 1.0)
        for a, (case, scale) in acc:
            _add(coefs, case, a.psi2 * scale)
        tag = _tag(["G"] + [c for _, (c, _) in acc])
        b.add(f"B_ELS_QP_{tag}", "B_ELS_QP", coefs)
    return b.out


def combinations(which: str = "AB") -> list[Combination]:
    out: list[Combination] = []
    if "A" in which:
        out += set_a()
    if "B" in which:
        out += set_b()
    return out


def counts(which: str = "AB") -> dict[str, int]:
    tally: dict[str, int] = {}
    for c in combinations(which):
        tally[c.family] = tally.get(c.family, 0) + 1
    return tally


__all__ = [
    "ACTIONS_B",
    "FAMILIES",
    "STATE_OF_FAMILY",
    "Combination",
    "combinations",
    "counts",
    "set_a",
    "set_b",
]
