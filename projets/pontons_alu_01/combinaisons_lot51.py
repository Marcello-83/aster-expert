"""Combinations of lot 51 for PONTONS-ALU-01: set B′ revised (P27, P31 to P35) and the
accidental ULS, written as rules rather than as a list.

With exclusive events (consigne § 4: one berthing event among 40, one mooring event
among 28, per combination), the combinations number in the hundreds of thousands
(millions with the span patterns of variant E): they are described by **branches**,
a branch being a product of **slots**, each slot a list of options (an event and its
factor, or the absence). A combination is one option per slot of one branch; its
coefficients are Σ factor × the coefficients of the event on the unit cases.

Rules (lot 50, D5, for what the consigne leaves unchanged; P27, P31 to P35 for the
rest):

- permanent: G1 and G2 as one block, 1,2 or 0,9 at the fundamental ULS, 1,0 elsewhere;
  variant E: G1 as a block, each span's G2 at 1,2 or 0,9 independently;
- variable actions (γ, ψ0, ψ1, ψ2): houle H (HU or HD × 5 kPa; 1,5 ; 0,77 ; 0,77 ;
  0,2), temperature T (TP or TM; 1,5 ; 0,6 ; 0,6 ; 0,5), mooring AM (28 events; 1,5,
  P33 ; ψ kept from the project 0,77 ; 0,77 ; 0,2), berthing AC (40 events; 1,5 ;
  1,0 ; 0,5 ; 0, P31), crowd Q (Q or Q½; 1,3 ; 0,77 ; 0,77 ; 0,2); variant E: H and
  Q on any non-empty set of spans;
- B′: never Q (or Q½) together with the houle;
- fundamental ULS (6.10): G + γ·Q_lead + Σ γ·ψ0·Q_i; characteristic SLS: G + Q_lead +
  Σ ψ0·Q_i; frequent SLS: G + ψ1·Q_lead + Σ ψ2·Q_i; quasi-permanent SLS: G + Σ ψ2·Q_i;
- accidental ULS (6.11, rule of the project): G + A_d + ψ1·Q_lead + Σ ψ2·Q_i, the
  lead possibly absent; A_d = ACA (40 events, no other berthing event) or AMF (24
  events, no other mooring event).

An option whose factor is zero is the absence (ψ2 = 0 of the berthing): the set of
combinations is then free of duplicates, which `test_combinaisons_lot51` checks by
enumeration against the lot 50 rule (identical coefficient sets kept once).
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from pontons_alu_01.geometrie_lot51 import SIDES, SPANS

FloatArray = NDArray[np.float64]

H_SCALE = 5.0
"""kPa: houle of set B (P9), on the cases of 1 kPa."""
G_UNFAV, G_FAV = 1.2, 0.9


@dataclass(frozen=True)
class ActionRule:
    name: str
    gamma: float
    psi0: float
    psi1: float
    psi2: float
    source: str


ACTIONS = {
    "H": ActionRule("H", 1.5, 0.77, 0.77, 0.2, "lot 50, D5 (inchangé)"),
    "T": ActionRule("T", 1.5, 0.6, 0.6, 0.5, "lot 50, D5 (inchangé)"),
    "AM": ActionRule("AM", 1.5, 0.77, 0.77, 0.2, "P33 (γ) ; ψ du projet, lot 50 D5"),
    "AC": ActionRule("AC", 1.5, 1.0, 0.5, 0.0, "P31"),
    "Q": ActionRule("Q", 1.3, 0.77, 0.77, 0.2, "lot 50, D5 (inchangé)"),
}
VARIABLES = ("H", "T", "AM", "AC", "Q")
STATES = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
)


@dataclass(frozen=True)
class Event:
    """An event of an action: its coefficients on the unit cases (characteristic
    values: kN on the unit cases of 1 kN, kPa on those of 1 kPa)."""

    name: str
    action: str
    coefficients: dict[str, float]


Option = tuple[str | None, float]
"""(event, factor); `None` is the absence."""


@dataclass(frozen=True)
class Slot:
    label: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class Branch:
    state: str
    name: str
    slots: tuple[Slot, ...]

    @property
    def count(self) -> int:
        return math.prod(len(s.options) for s in self.slots)


# --------------------------------------------------------------------------- events


def _patterns() -> list[tuple[str, ...]]:
    return [
        tuple(s for s, keep in zip(SPANS, bits, strict=True) if keep)
        for bits in itertools.product((1, 0), repeat=len(SPANS))
        if any(bits)
    ]


def events(m: dict[str, float], *, split: bool) -> dict[str, Event]:
    """Every event, from the magnitudes `m` of the data file (kN) and the cleats and
    zones of the model. `split`: variant E, span patterns of H and Q, G2 per span."""
    out: dict[str, Event] = {}

    def add(name: str, action: str, coefs: dict[str, float]) -> None:
        out[name] = Event(name, action, coefs)

    if split:
        add("G1", "G", {"G1": 1.0})
        for t in SPANS:
            add(f"G2_{t}", "G", {f"G2_{t}": 1.0})
        for d in ("HU", "HD"):
            for pat in _patterns():
                add(f"{d}_{'+'.join(pat)}", "H", {f"{d}_{t}": H_SCALE for t in pat})
        for pat in _patterns():
            add(f"Q_{'+'.join(pat)}", "Q", {f"Q_{t}": 1.0 for t in pat})
    else:
        add("G", "G", {"G1": 1.0, "G2": 1.0})
        for d in ("HU", "HD"):
            add(d, "H", {d: H_SCALE})
        add("Q", "Q", {"Q": 1.0})
    add("QD", "Q", {"QD": 1.0})
    add("TP", "T", {"TP": 1.0})
    add("TM", "T", {"TM": 1.0})
    zones = ("QU", "MI1", "CH1", "PT", "PA2")
    tangential = (
        ("+X", "ACX", 1.0),
        ("-X", "ACX", -1.0),
        ("+Z", "ACZ", 1.0),
        ("-Z", "ACZ", -1.0),
    )
    for z in zones:
        for s, _ in SIDES:
            for tag, case, sign in tangential:
                add(
                    f"AC_{z}_{s}_{tag}",
                    "AC",
                    {
                        f"ACN_{z}_{s}": m["ac_normal"],
                        f"{case}_{z}_{s}": sign * m["ac_tangentiel"],
                    },
                )
                add(
                    f"ACA_{z}_{s}_{tag}",
                    "ACA",
                    {
                        f"ACN_{z}_{s}": m["aca_normal"],
                        f"{case}_{z}_{s}": sign * m["aca_tangentiel"],
                    },
                )
    cleats = [f"TQ{k}" for k in range(1, 5)]
    for c in cleats:
        for s, _ in SIDES:
            for action, value in (("AM", m["am_local"]), ("AMF", m["amf"])):
                prefix = "AML" if action == "AM" else "AMF"
                add(f"{prefix}_{c}_{s}_PERP", action, {f"AMY_{c}_{s}": value})
                add(f"{prefix}_{c}_{s}_+X", action, {f"AMX_{c}_{s}": value})
                add(f"{prefix}_{c}_{s}_-X", action, {f"AMX_{c}_{s}": -value})
    for tag, sign in (("+X", 1.0), ("-X", -1.0)):
        coefs = {}
        for c in cleats:
            for s, _ in SIDES:
                coefs[f"AMY_{c}_{s}"] = m["am1_perpendiculaire"]
                coefs[f"AMX_{c}_{s}"] = sign * m["am1_parallele"]
        add(f"AM1_{tag}", "AM", coefs)
    for s, _ in SIDES:
        add(
            f"AM2_{s}", "AM", {f"AMY_{c}_{s}": m["am2_perpendiculaire"] for c in cleats}
        )
    return out


def magnitudes(data: dict[str, Any]) -> dict[str, float]:
    """The characteristic magnitudes (kN) of the data file, group actions_maritimes."""
    keys = (
        "ac_normal",
        "ac_tangentiel",
        "aca_normal",
        "aca_tangentiel",
        "am_local",
        "am1_perpendiculaire",
        "am1_parallele",
        "am2_perpendiculaire",
        "amf",
    )
    return {k: float(data[f"actions_maritimes.{k}"]) for k in keys}


# --------------------------------------------------------------------------- rules


def _variants(ev: dict[str, Event], action: str) -> list[str]:
    return [e.name for e in ev.values() if e.action == action]


def _slot(label: str, names: list[str], factor: float, *, absent: bool) -> Slot:
    """Options of one action at one factor; a zero factor is the absence."""
    opts: list[Option] = [(None, 0.0)] if absent or factor == 0.0 else []
    if factor != 0.0:
        opts += [(n, factor) for n in names]
    return Slot(label, tuple(opts))


def _permanent(ev: dict[str, Event], factors: tuple[float, ...]) -> list[Slot]:
    perm = _variants(ev, "G")
    if "G" in perm:
        return [Slot("G", tuple(("G", f) for f in factors))]
    return [Slot(n, tuple((n, f) for f in factors)) for n in perm]


def _others(
    ev: dict[str, Event],
    lead: str | None,
    factor: dict[str, float],
    excluded: tuple[str, ...] = (),
) -> list[Slot]:
    """Accompanying slots: every variable but the lead and the excluded ones, at
    `factor[action]`, absence allowed; H and Q share one slot (B′) unless one of them
    leads, the other being then absent."""
    slots: list[Slot] = []
    pool = [a for a in VARIABLES if a != lead and a not in excluded]
    for a in pool:
        if a in ("H", "Q"):
            continue
        slots.append(_slot(a, _variants(ev, a), factor[a], absent=True))
    if lead not in ("H", "Q"):
        opts: list[Option] = [(None, 0.0)]
        for a in ("H", "Q"):
            if a in pool and factor[a] != 0.0:
                opts += [(n, factor[a]) for n in _variants(ev, a)]
        slots.append(Slot("H/Q", tuple(opts)))
    return slots


def branches(ev: dict[str, Event]) -> list[Branch]:
    gamma = {a: r.gamma for a, r in ACTIONS.items()}
    g_psi0 = {a: r.gamma * r.psi0 for a, r in ACTIONS.items()}
    psi0 = {a: r.psi0 for a, r in ACTIONS.items()}
    psi1 = {a: r.psi1 for a, r in ACTIONS.items()}
    psi2 = {a: r.psi2 for a, r in ACTIONS.items()}
    out: list[Branch] = []
    for lead in VARIABLES:
        out.append(
            Branch(
                "ELU_fondamental",
                f"dominante {lead}",
                (
                    *_permanent(ev, (G_UNFAV, G_FAV)),
                    _slot(lead, _variants(ev, lead), gamma[lead], absent=False),
                    *_others(ev, lead, g_psi0),
                ),
            )
        )
    for state, lead_f, acc_f in (
        ("ELS_caracteristique", dict.fromkeys(VARIABLES, 1.0), psi0),
        ("ELS_frequent", psi1, psi2),
    ):
        for lead in VARIABLES:
            if lead_f[lead] == 0.0:
                continue
            out.append(
                Branch(
                    state,
                    f"dominante {lead}",
                    (
                        *_permanent(ev, (1.0,)),
                        _slot(lead, _variants(ev, lead), lead_f[lead], absent=False),
                        *_others(ev, lead, acc_f),
                    ),
                )
            )
    out.append(
        Branch(
            "ELS_quasi_permanent",
            "sans dominante",
            (*_permanent(ev, (1.0,)), *_others(ev, None, psi2)),
        )
    )
    for accidental, excluded in (("ACA", "AC"), ("AMF", "AM")):
        leads: list[str | None] = [None, *(a for a in VARIABLES if a != excluded)]
        for acc_lead in leads:
            slots = [
                *_permanent(ev, (1.0,)),
                _slot(accidental, _variants(ev, accidental), 1.0, absent=False),
            ]
            if acc_lead is not None:
                slots.append(
                    _slot(
                        acc_lead, _variants(ev, acc_lead), psi1[acc_lead], absent=False
                    )
                )
            slots += _others(ev, acc_lead, psi2, (excluded,))
            out.append(
                Branch(
                    "ELU_accidentel",
                    f"{accidental}, dominante {acc_lead or 'aucune'}",
                    tuple(slots),
                )
            )
    return out


def counts(bs: list[Branch]) -> dict[str, int]:
    out = dict.fromkeys(STATES, 0)
    for b in bs:
        out[b.state] += b.count
    return out


def combination(
    b: Branch, ev: dict[str, Event], choice: tuple[Option, ...]
) -> tuple[str, dict[str, float]]:
    coefs: dict[str, float] = {}
    parts = []
    for name, factor in choice:
        if name is None:
            continue
        parts.append(f"{name}×{factor:g}")
        for case, c in ev[name].coefficients.items():
            coefs[case] = coefs.get(case, 0.0) + factor * c
    return f"{b.state}: " + " + ".join(parts), coefs


def enumerate_branch(
    b: Branch, ev: dict[str, Event]
) -> Iterator[tuple[str, dict[str, float]]]:
    for choice in itertools.product(*(s.options for s in b.slots)):
        yield combination(b, ev, choice)


# --------------------------------------------------------------------------- envelopes


@dataclass
class Extreme:
    value: FloatArray
    """Per quantity."""
    choice: list[tuple[int, tuple[int, ...]]]
    """Per quantity: (branch index, option index per slot)."""


def _event_values(
    ev: dict[str, Event], f: dict[str, FloatArray], names: set[str]
) -> dict[str, FloatArray]:
    shape = next(iter(f.values())).shape
    out = {}
    for n in names:
        total = np.zeros(shape)
        for case, c in ev[n].coefficients.items():
            total = total + c * f[case]
        out[n] = total
    return out


def envelope(
    bs: list[Branch],
    ev: dict[str, Event],
    f: dict[str, FloatArray],
    state: str,
    *,
    sign: float = 1.0,
    without: tuple[str, ...] = (),
) -> Extreme:
    """max (sign = 1) or min (sign = −1) over the combinations of `state` of a linear
    quantity given per unit case (`f[case]`, arrays of one shape): Σ over the slots
    of the best option, the best branch kept. `without`: actions left out of the sum
    (« variables seules » : the permanent action G)."""
    names = {
        n for b in bs if b.state == state for s in b.slots for n, _ in s.options if n
    }
    values = _event_values(ev, f, names)
    shape = next(iter(f.values())).shape
    best: FloatArray | None = None
    best_choice: NDArray[np.int64] | None = None
    best_branch: NDArray[np.int64] | None = None
    branch_list = [(i, b) for i, b in enumerate(bs) if b.state == state]
    for i, b in branch_list:
        total = np.zeros(shape)
        picks = []
        for s in b.slots:
            cand = np.stack(
                [
                    np.zeros(shape)
                    if n is None or ev[n].action in without
                    else sign * fac * values[n]
                    for n, fac in s.options
                ]
            )
            k = np.argmax(cand, axis=0)
            total = total + np.take_along_axis(cand, k[None], axis=0)[0]
            picks.append(k)
        if best is None:
            best = total
            best_choice = np.stack(picks)
            best_branch = np.full(shape, i)
        else:
            better = total > best
            best = np.where(better, total, best)
            assert best_branch is not None and best_choice is not None
            best_branch = np.where(better, i, best_branch)
            stacked = np.stack(picks)
            if stacked.shape[0] != best_choice.shape[0]:
                width = max(stacked.shape[0], best_choice.shape[0])
                stacked = _pad(stacked, width)
                best_choice = _pad(best_choice, width)
            best_choice = np.where(better[None], stacked, best_choice)
    assert best is not None and best_branch is not None and best_choice is not None
    flat_branch = best_branch.reshape(-1)
    flat_choice = best_choice.reshape(best_choice.shape[0], -1)
    choices = [
        (
            int(flat_branch[q]),
            tuple(int(k) for k in flat_choice[: len(bs[flat_branch[q]].slots), q]),
        )
        for q in range(flat_branch.size)
    ]
    return Extreme(sign * best, choices)


def _pad(a: NDArray[np.int64], width: int) -> NDArray[np.int64]:
    if a.shape[0] == width:
        return a
    pad = np.zeros((width - a.shape[0], *a.shape[1:]), dtype=a.dtype)
    return np.concatenate([a, pad])


def governing(
    bs: list[Branch], ev: dict[str, Event], extreme: Extreme, q: int
) -> tuple[str, dict[str, float]]:
    """Name and coefficients of the combination that governs quantity `q`."""
    i, picks = extreme.choice[q]
    b = bs[i]
    choice = tuple(s.options[k] for s, k in zip(b.slots, picks, strict=True))
    return combination(b, ev, choice)


DIRECTIONS = 2048
"""Directions of the plane for the maximum of a resultant √(a² + b²): the maximum over
the combinations of the projection on each direction, then over the directions (error
≤ 1 − cos(π/2048) ≈ 1,2·10⁻⁶ by default)."""


def resultant_max(
    bs: list[Branch],
    ev: dict[str, Event],
    a: dict[str, FloatArray],
    b: dict[str, FloatArray],
    state: str,
    *,
    without: tuple[str, ...] = (),
) -> FloatArray:
    """max over the combinations of √(a² + b²), per quantity (1-D arrays)."""
    theta = np.linspace(0.0, 2.0 * math.pi, DIRECTIONS, endpoint=False)
    out: FloatArray | None = None
    for chunk in np.array_split(theta, 16):
        c, s = np.cos(chunk)[:, None], np.sin(chunk)[:, None]
        proj = {case: c * a[case][None, :] + s * b[case][None, :] for case in a}
        m = envelope(bs, ev, proj, state, without=without).value.max(axis=0)
        out = m if out is None else np.maximum(out, m)
    assert out is not None
    return out


# --------------------------------------------------------------------------- files


def event_rows(ev: dict[str, Event]) -> list[list[Any]]:
    return [
        [e.action, e.name, case, float(c)]
        for e in ev.values()
        for case, c in e.coefficients.items()
    ]


def rule_rows(bs: list[Branch]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for b in bs:
        for k, s in enumerate(b.slots, start=1):
            rows.append(
                [
                    b.state,
                    b.name,
                    k,
                    s.label,
                    len(s.options),
                    b.count,
                    "|".join(
                        "∅" if n is None else f"{n}×{repr(float(fac))}"
                        for n, fac in s.options
                    ),
                ]
            )
    return rows


__all__ = [
    "ACTIONS",
    "STATES",
    "Branch",
    "Event",
    "Extreme",
    "Slot",
    "branches",
    "combination",
    "counts",
    "enumerate_branch",
    "envelope",
    "event_rows",
    "events",
    "governing",
    "magnitudes",
    "resultant_max",
    "rule_rows",
]
