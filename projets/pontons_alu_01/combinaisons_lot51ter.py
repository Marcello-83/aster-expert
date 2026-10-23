"""Combinations of lot 51 ter for PONTONS-ALU-01: set B′ revised (P27, P31 to P35),
the accidental ULS, DEJ tied to G (P49) and, new in this lot, the houle by surfaces
and limit states (P56), houle and berthing never together (P57), the mooring factors
P59 and the unfavourable patterns of Q and QD by modules.

As in lot 51 (`combinaisons_lot51`), the combinations are written as rules: a branch is
a product of slots, a slot a list of options (an event and its factor, or the absence),
a combination one option per slot of one branch.

Events (characteristic values; kN on the unit cases of 1 kN, kN/m on 1 kN/m, kPa on
1 kPa):

- permanent: G (G1 + G2), G_DEJ_090 (0,9 G + DEJ), G_DEJ_100 (G + DEJ), as in lot
  51 bis;
- houle (P56): HU (HU_TUBES × 14,49 + HU_PANNES × 12,99 + HU_PLATELAGE × 12,48), HD
  (HD_TABLIER × 12,03), HU_F (frequent: 2,36, 0,85, 0,35), uniform on the whole length,
  in phase;
- Q and QD with **unfavourable patterns** by modules (M0 to M5): each module loaded or
  not. The pattern is never enumerated: for a quantity and a sense, the event takes the
  sum of the module contributions of that sign (influence lines, exact in linear
  analysis); the modules retained are written in the governing combination;
- temperature TP, TM; berthing AC and ACA (21 zones × 2 sides × 4 tangential
  variants, one event per combination at most); mooring AM local (one cleat of 20, ⊥ or
  ±∥), AM1 (the 20 cleats), AM2 (the 10 cleats of one side), AMF (accidental, one
  cleat).

Rules (γ, ψ0, ψ1, ψ2): houle H 1,5 ; 0,77 ; HU_F in place of ψ1·HU ; 0 (P56); T 1,5 ;
0,6 ; 0,6 ; 0,5; AM 1,5 ; 0,77 ; 0,77 ; 0,2 (P59); AC 1,5 ; 1,0 ; 0,5 ; 0 (P31); Q
1,3 ; 0,77 ; 0,77 ; 0,2. B′: never Q with the houle. P57: never the houle with a
berthing event (AC or ACA). Fundamental ULS G + γ·Q_lead + Σ γ·ψ0·Q_i;
characteristic SLS G + Q_lead + Σ ψ0·Q_i; frequent SLS G + ψ1·Q_lead + Σ ψ2·Q_i
(houle: HU_F × 1,0 as lead, nothing as accompaniment); quasi-permanent SLS G + Σ ψ2·Q_i
(no houle); accidental ULS G + A_d + ψ1·Q_lead + Σ ψ2·Q_i, lead possibly absent, A_d =
ACA (no other berthing event, no houle) or AMF (no other mooring event); houle as lead
of the accidental ULS: HU or HD × 0,77 (P56, « comme au lot 51 bis »).
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from pontons_alu_01.geometrie_lot51 import SIDES

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

G_UNFAV, G_FAV = 1.2, 0.9
STATES = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
)
VARIABLES = ("H", "T", "AM", "AC", "Q")


@dataclass(frozen=True)
class ActionRule:
    name: str
    gamma: float
    psi0: float
    psi1: float
    psi2: float
    source: str


ACTIONS = {
    "H": ActionRule(
        "H",
        1.5,
        0.77,
        0.77,
        0.0,
        "P56 (ψ1 : HU_F × 1,0 à l'ELS fréquent, × 0,77 en tête de l'ELU accidentel ;"
        " ψ2 = 0)",
    ),
    "T": ActionRule("T", 1.5, 0.6, 0.6, 0.5, "lot 50, D5 (inchangé)"),
    "AM": ActionRule("AM", 1.5, 0.77, 0.77, 0.2, "P59 (P33)"),
    "AC": ActionRule("AC", 1.5, 1.0, 0.5, 0.0, "P31"),
    "Q": ActionRule("Q", 1.3, 0.77, 0.77, 0.2, "lot 50, D5 (inchangé)"),
}


@dataclass(frozen=True)
class Event:
    """An event: fixed coefficients on the unit cases and, for a pattern event, the
    coefficients of each module (each module loaded or not, unfavourable choice)."""

    name: str
    action: str
    coefficients: dict[str, float]
    modules: tuple[tuple[str, dict[str, float]], ...] = ()

    @property
    def patterns(self) -> int:
        """Number of loadings the event stands for (2ⁿ − 1 for n modules)."""
        return 2 ** len(self.modules) - 1 if self.modules else 1


Option = tuple[str | None, float]


@dataclass(frozen=True)
class Slot:
    label: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class Exclusion:
    """Two slots of a branch that are maximised jointly (lot 54, P70): `pairs` are the
    (option of `first`, option of `second`) indices that may not come together."""

    first: int
    second: int
    pairs: frozenset[tuple[int, int]]

    def allowed(self, i: int, j: int) -> bool:
        return (i, j) not in self.pairs


@dataclass(frozen=True)
class Branch:
    state: str
    name: str
    slots: tuple[Slot, ...]
    exclusions: tuple[Exclusion, ...] = ()
    """Pairs of slots with forbidden option pairs (lot 54, P70); none before."""

    def _joint(self) -> set[int]:
        slots = [k for x in self.exclusions for k in (x.first, x.second)]
        if len(slots) != len(set(slots)):
            message = f"{self.state}/{self.name} : un emplacement dans deux exclusions"
            raise ValueError(message)
        return set(slots)

    def _count(self, weight: Callable[[Option], int]) -> int:
        joint = self._joint()
        free = math.prod(
            sum(weight(o) for o in s.options)
            for k, s in enumerate(self.slots)
            if k not in joint
        )
        for x in self.exclusions:
            a, b = self.slots[x.first].options, self.slots[x.second].options
            free *= sum(
                weight(a[i]) * weight(b[j])
                for i in range(len(a))
                for j in range(len(b))
                if x.allowed(i, j)
            )
        return free

    @property
    def count(self) -> int:
        return self._count(lambda _: 1)

    def expanded_count(self, ev: dict[str, Event]) -> int:
        """Count with every pattern of the pattern events enumerated."""
        return self._count(lambda o: 1 if o[0] is None else ev[o[0]].patterns)

    def allows(self, picks: tuple[int, ...]) -> bool:
        """Whether a choice (one option index per slot) avoids every forbidden pair."""
        return all(x.allowed(picks[x.first], picks[x.second]) for x in self.exclusions)


# --------------------------------------------------------------------------- events


def magnitudes(data: dict[str, Any]) -> dict[str, float]:
    """Characteristic magnitudes of the data file: maritime actions (kN) and houle
    coefficients (kPa)."""
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
    out = {k: float(data[f"actions_maritimes.{k}"]) for k in keys}
    for k in (
        "hu_tubes",
        "hu_pannes",
        "hu_platelage",
        "hd_tablier",
        "huf_tubes",
        "huf_pannes",
        "huf_platelage",
    ):
        out[k] = float(data[f"houle_lot51ter.{k}"])
    return out


def events(
    m: dict[str, float],
    *,
    zones: list[str],
    cleats: list[int],
    modules: list[str],
) -> dict[str, Event]:
    out: dict[str, Event] = {}

    def add(
        name: str,
        action: str,
        coefs: dict[str, float],
        mods: tuple[tuple[str, dict[str, float]], ...] = (),
    ) -> None:
        out[name] = Event(name, action, coefs, mods)

    add("G", "G", {"G1": 1.0, "G2": 1.0})
    add("G_DEJ_090", "G", {"G1": G_FAV, "G2": G_FAV, "DEJ": 1.0})
    add("G_DEJ_100", "G", {"G1": 1.0, "G2": 1.0, "DEJ": 1.0})
    add(
        "HU",
        "H",
        {
            "HU_TUBES": m["hu_tubes"],
            "HU_PANNES": m["hu_pannes"],
            "HU_PLATELAGE": m["hu_platelage"],
        },
    )
    add("HD", "H", {"HD_TABLIER": m["hd_tablier"]})
    add(
        "HU_F",
        "HF",
        {
            "HU_TUBES": m["huf_tubes"],
            "HU_PANNES": m["huf_pannes"],
            "HU_PLATELAGE": m["huf_platelage"],
        },
    )
    for base in ("Q", "QD"):
        add(base, "Q", {}, tuple((mod, {f"{base}_{mod}": 1.0}) for mod in modules))
    add("TP", "T", {"TP": 1.0})
    add("TM", "T", {"TM": 1.0})
    tangential = (
        ("+X", "ACX", 1.0),
        ("-X", "ACX", -1.0),
        ("+Z", "ACZ", 1.0),
        ("-Z", "ACZ", -1.0),
    )
    for z in zones:
        for s, _ in SIDES:
            for tag, case, sign in tangential:
                for prefix, normal, tang in (
                    ("AC", "ac_normal", "ac_tangentiel"),
                    ("ACA", "aca_normal", "aca_tangentiel"),
                ):
                    add(
                        f"{prefix}_{z}_{s}_{tag}",
                        prefix,
                        {
                            f"ACN_{z}_{s}": m[normal],
                            f"{case}_{z}_{s}": sign * m[tang],
                        },
                    )
    for c in cleats:
        for s, _ in SIDES:
            for action, value in (("AM", m["am_local"]), ("AMF", m["amf"])):
                prefix = "AML" if action == "AM" else "AMF"
                add(f"{prefix}_TQ{c}_{s}_PERP", action, {f"AMY_TQ{c}_{s}": value})
                add(f"{prefix}_TQ{c}_{s}_+X", action, {f"AMX_TQ{c}_{s}": value})
                add(f"{prefix}_TQ{c}_{s}_-X", action, {f"AMX_TQ{c}_{s}": -value})
    for tag, sign in (("+X", 1.0), ("-X", -1.0)):
        coefs = {}
        for c in cleats:
            for s, _ in SIDES:
                coefs[f"AMY_TQ{c}_{s}"] = m["am1_perpendiculaire"]
                coefs[f"AMX_TQ{c}_{s}"] = sign * m["am1_parallele"]
        add(f"AM1_{tag}", "AM", coefs)
    for s, _ in SIDES:
        add(
            f"AM2_{s}",
            "AM",
            {f"AMY_TQ{c}_{s}": m["am2_perpendiculaire"] for c in cleats},
        )
    return out


# --------------------------------------------------------------------------- rules


def _names(ev: dict[str, Event], action: str) -> list[str]:
    return [e.name for e in ev.values() if e.action == action]


def _slot(label: str, names: list[str], factor: float, *, absent: bool) -> Slot:
    opts: list[Option] = [(None, 0.0)] if absent else []
    opts += [(n, factor) for n in names]
    return Slot(label, tuple(opts))


def _accompanying(
    ev: dict[str, Event],
    lead: str | None,
    factor: dict[str, float],
    excluded: tuple[str, ...],
    *,
    no_houle: bool,
) -> list[tuple[str, list[Slot]]]:
    """Accompanying slots, as one or two disjoint sets: T and AM each in its slot; H
    and Q share one slot (B′); AC in its slot; P57: never H with AC (when both may
    come, one set has an AC event and no H, the other no AC event)."""
    pool = [
        a for a in VARIABLES if a != lead and a not in excluded and factor[a] != 0.0
    ]
    base = [
        _slot(a, _names(ev, a), factor[a], absent=True)
        for a in ("T", "AM")
        if a in pool
    ]
    h_ok = "H" in pool and lead != "Q" and not no_houle
    q_ok = "Q" in pool and lead != "H"
    ac_ok = "AC" in pool and lead != "H"

    def hq(with_h: bool) -> list[Slot]:
        opts: list[Option] = [(None, 0.0)]
        if with_h:
            opts += [(n, factor["H"]) for n in _names(ev, "H")]
        if q_ok:
            opts += [(n, factor["Q"]) for n in _names(ev, "Q")]
        return [Slot("H/Q" if with_h else "Q", tuple(opts))] if len(opts) > 1 else []

    if ac_ok and h_ok:
        return [
            (
                "avec AC",
                [
                    *base,
                    _slot("AC", _names(ev, "AC"), factor["AC"], absent=False),
                    *hq(False),
                ],
            ),
            ("sans AC", [*base, *hq(True)]),
        ]
    slots = list(base)
    if ac_ok:
        slots.append(_slot("AC", _names(ev, "AC"), factor["AC"], absent=True))
    slots += hq(h_ok)
    return [("", slots)]


def _lead_slot(ev: dict[str, Event], lead: str, factor: float, state: str) -> Slot:
    if lead == "H" and state == "ELS_frequent":
        return Slot("H (HU_F, P56)", tuple((n, 1.0) for n in _names(ev, "HF")))
    return _slot(lead, _names(ev, lead), factor, absent=False)


def branches(ev: dict[str, Event]) -> list[Branch]:
    a = ACTIONS
    gamma = {k: r.gamma for k, r in a.items()}
    g_psi0 = {k: r.gamma * r.psi0 for k, r in a.items()}
    psi0 = {k: r.psi0 for k, r in a.items()}
    psi1 = {k: r.psi1 for k, r in a.items()}
    psi2 = {k: r.psi2 for k, r in a.items()}
    perm_elu = Slot("G (P49 : DEJ lié)", (("G", G_UNFAV), ("G_DEJ_090", 1.0)))
    perm = Slot("G (P49 : DEJ lié)", (("G", 1.0), ("G_DEJ_100", 1.0)))
    out: list[Branch] = []

    def add(state: str, name: str, head: list[Slot], rest: list[Slot]) -> None:
        out.append(Branch(state, name, (*head, *rest)))

    for state, permanent, lead_f, acc_f in (
        ("ELU_fondamental", perm_elu, gamma, g_psi0),
        ("ELS_caracteristique", perm, dict.fromkeys(VARIABLES, 1.0), psi0),
        ("ELS_frequent", perm, psi1, psi2),
    ):
        for lead in VARIABLES:
            head = [permanent, _lead_slot(ev, lead, lead_f[lead], state)]
            for tag, rest in _accompanying(ev, lead, acc_f, (), no_houle=lead == "AC"):
                add(
                    state,
                    f"dominante {lead}" + (f" ({tag})" if tag else ""),
                    head,
                    rest,
                )
    for _, rest in _accompanying(ev, None, psi2, (), no_houle=False):
        add("ELS_quasi_permanent", "sans dominante", [perm], rest)
    for accidental, excluded in (("ACA", "AC"), ("AMF", "AM")):
        leads: list[str | None] = [None, *(x for x in VARIABLES if x != excluded)]
        for acc_lead in leads:
            if accidental == "ACA" and acc_lead == "H":
                continue  # P57 : pas de houle avec l'accostage accidentel
            head = [perm, _slot(accidental, _names(ev, accidental), 1.0, absent=False)]
            if acc_lead is not None:
                head.append(
                    _slot(acc_lead, _names(ev, acc_lead), psi1[acc_lead], absent=False)
                )
            no_houle = accidental == "ACA" or acc_lead == "AC"
            for tag, rest in _accompanying(
                ev, acc_lead, psi2, (excluded,), no_houle=no_houle
            ):
                add(
                    "ELU_accidentel",
                    f"{accidental}, dominante {acc_lead or 'aucune'}"
                    + (f" ({tag})" if tag else ""),
                    head,
                    rest,
                )
    return out


def counts(bs: list[Branch]) -> dict[str, int]:
    out = dict.fromkeys(STATES, 0)
    for b in bs:
        out[b.state] += b.count
    return out


def expanded_counts(bs: list[Branch], ev: dict[str, Event]) -> dict[str, int]:
    out = dict.fromkeys(STATES, 0)
    for b in bs:
        out[b.state] += b.expanded_count(ev)
    return out


def check_exclusions(bs: list[Branch], ev: dict[str, Event]) -> list[str]:
    """Breaches found in the rules: Q with the houle (B′), the houle with a berthing
    event (P57), two berthing events (exclusivity). A slot holds one option, so two
    actions meet in a combination only if they sit in two different slots."""
    problems = []
    for b in bs:
        actions = [
            {ev[n].action for n, _ in s.options if n is not None} for s in b.slots
        ]

        def apart(x: set[str], y: set[str], actions: list[set[str]] = actions) -> bool:
            return any(
                acts_i & x and acts_j & y
                for i, acts_i in enumerate(actions)
                for j, acts_j in enumerate(actions)
                if i != j
            )

        houle, berthing = {"H", "HF"}, {"AC", "ACA"}
        if apart(houle, {"Q"}):
            problems.append(f"{b.state}/{b.name} : houle et Q (B′)")
        if apart(houle, berthing):
            problems.append(f"{b.state}/{b.name} : houle et accostage (P57)")
        if apart(berthing, berthing):
            problems.append(f"{b.state}/{b.name} : deux événements d'accostage")
    return problems


def combination(
    b: Branch,
    ev: dict[str, Event],
    choice: tuple[Option, ...],
    masks: tuple[int, ...] | None = None,
) -> tuple[str, dict[str, float]]:
    """Name and coefficients of one combination; `masks[k]` gives the modules loaded
    by the pattern event of slot k (bit i: module i), all of them if None."""
    coefs: dict[str, float] = {}
    parts = []
    for k, (name, factor) in enumerate(choice):
        if name is None:
            continue
        e = ev[name]
        label = name
        if e.modules:
            mask = (2 ** len(e.modules) - 1) if masks is None else masks[k]
            kept = [mod for i, mod in enumerate(e.modules) if mask >> i & 1]
            label = f"{name}[{'+'.join(m for m, _ in kept) or 'aucun module'}]"
            for _, mc in kept:
                for case, c in mc.items():
                    coefs[case] = coefs.get(case, 0.0) + factor * c
        parts.append(f"{label}×{factor:g}")
        for case, c in e.coefficients.items():
            coefs[case] = coefs.get(case, 0.0) + factor * c
    return f"{b.state}: " + " + ".join(parts), coefs


def enumerate_branch(
    b: Branch, ev: dict[str, Event]
) -> Iterator[tuple[str, dict[str, float]]]:
    """Every combination of a branch with every pattern of its pattern events
    (non-empty patterns), for tests and checks."""
    per_slot: list[list[tuple[Option, int]]] = []
    for s in b.slots:
        items: list[tuple[Option, int]] = []
        for n, fac in s.options:
            if n is not None and ev[n].modules:
                items += [((n, fac), m) for m in range(1, 2 ** len(ev[n].modules))]
            else:
                items.append(((n, fac), 0))
        per_slot.append(items)
    index = [
        [i for i, (n, _) in enumerate(s.options) for _ in range(_weight(ev, n))]
        for s in b.slots
    ]
    for picks, where in zip(
        itertools.product(*per_slot), itertools.product(*index), strict=True
    ):
        if not b.allows(where):
            continue  # paire interdite (lot 54, P70)
        choice = tuple(o for o, _ in picks)
        masks = tuple(m for _, m in picks)
        yield combination(b, ev, choice, masks)


def _weight(ev: dict[str, Event], name: str | None) -> int:
    """Number of items of an option in `enumerate_branch` (its non-empty patterns)."""
    return 1 if name is None or not ev[name].modules else 2 ** len(ev[name].modules) - 1


# --------------------------------------------------------------------------- envelopes


@dataclass
class Extreme:
    value: FloatArray
    choice: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = field(
        default_factory=list
    )
    """Per quantity: (branch index, option index per slot, module mask per slot)."""


def _option_values(
    ev: dict[str, Event],
    f: dict[str, FloatArray],
    name: str,
    factor: float,
    sign: float,
    shape: tuple[int, ...],
) -> tuple[FloatArray, IntArray]:
    """sign × factor × value of an option, and the mask of the modules a pattern
    event keeps (those whose contribution has the sense sought)."""
    e = ev[name]
    total = np.zeros(shape)
    for case, c in e.coefficients.items():
        total = total + c * f[case]
    total = sign * factor * total
    mask = np.zeros(shape, dtype=np.int64)
    for i, (_, mc) in enumerate(e.modules):
        part = np.zeros(shape)
        for case, c in mc.items():
            part = part + c * f[case]
        part = sign * factor * part
        keep = part > 0.0
        total = total + np.where(keep, part, 0.0)
        mask = mask | (keep.astype(np.int64) << i)
    return total, mask


def joint_best(
    cand_a: FloatArray, cand_b: FloatArray, x: Exclusion
) -> tuple[FloatArray, IntArray, IntArray]:
    """max over the allowed pairs (i, j) of cand_a[i] + cand_b[j], with i and j (lot 54,
    P70: the mooring and berthing slots of a branch maximised jointly). The options of
    the first slot are grouped by their set of forbidden options of the second; for
    each group, the best allowed option of the second is the first of its k best
    options (k = largest forbidden set + 1) outside the set."""
    forbidden: dict[int, set[int]] = {}
    for i, j in x.pairs:
        forbidden.setdefault(i, set()).add(j)
    groups: dict[frozenset[int], int] = {frozenset(): 0}
    group_of = np.zeros(cand_a.shape[0], dtype=np.int64)
    for i in range(cand_a.shape[0]):
        group_of[i] = groups.setdefault(frozenset(forbidden.get(i, ())), len(groups))
    n_b = cand_b.shape[0]
    k = min(n_b, 1 + max(len(s) for s in groups))
    if k < n_b:
        top = np.argpartition(-cand_b, k - 1, axis=0)[:k]
    else:
        top = np.broadcast_to(
            np.arange(n_b).reshape(n_b, *([1] * (cand_b.ndim - 1))), cand_b.shape
        ).copy()
    top_v = np.take_along_axis(cand_b, top, axis=0)
    order = np.argsort(-top_v, axis=0, kind="stable")
    top = np.take_along_axis(top, order, axis=0)
    top_v = np.take_along_axis(top_v, order, axis=0)
    best_v = np.empty((len(groups), *cand_b.shape[1:]))
    best_j = np.empty((len(groups), *cand_b.shape[1:]), dtype=np.int64)
    for s, g in groups.items():
        if not s:
            pos = np.zeros(cand_b.shape[1:], dtype=np.int64)
        else:
            if len(s) >= n_b:
                message = "exclusion : aucune option permise pour un groupe"
                raise ValueError(message)
            pos = np.argmax(~np.isin(top, list(s)), axis=0)
        best_v[g] = np.take_along_axis(top_v, pos[None], axis=0)[0]
        best_j[g] = np.take_along_axis(top, pos[None], axis=0)[0]
    joint = cand_a + best_v[group_of]
    ja = np.argmax(joint, axis=0)
    value = np.take_along_axis(joint, ja[None], axis=0)[0]
    jb = np.take_along_axis(best_j, group_of[ja][None], axis=0)[0]
    return value, ja, jb


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
    quantity given per unit case: Σ over the slots of the best option (a pattern event
    keeps the modules of the sense sought), the best branch kept. `without`: actions
    left out of the sum (« variables seules »: G)."""
    shape = next(iter(f.values())).shape
    cache: dict[tuple[str, float], tuple[FloatArray, IntArray]] = {}
    best: FloatArray | None = None
    best_branch = np.zeros(shape, dtype=np.int64)
    width = max(len(b.slots) for b in bs)
    best_choice = np.zeros((width, *shape), dtype=np.int64)
    best_mask = np.zeros((width, *shape), dtype=np.int64)
    for i, b in enumerate(bs):
        if b.state != state:
            continue
        total = np.zeros(shape)
        picks = np.zeros((width, *shape), dtype=np.int64)
        masks = np.zeros((width, *shape), dtype=np.int64)
        stacks: dict[int, tuple[FloatArray, IntArray]] = {}
        for k, s in enumerate(b.slots):
            vals = []
            mks = []
            for n, fac in s.options:
                if n is None or ev[n].action in without:
                    vals.append(np.zeros(shape))
                    mks.append(np.zeros(shape, dtype=np.int64))
                    continue
                key = (n, fac)
                if key not in cache:
                    cache[key] = _option_values(ev, f, n, fac, sign, shape)
                vals.append(cache[key][0])
                mks.append(cache[key][1])
            stacks[k] = (np.stack(vals), np.stack(mks))
        joint = b._joint()
        for k, (cand, mk) in stacks.items():
            if k in joint:
                continue
            j = np.argmax(cand, axis=0)
            total = total + np.take_along_axis(cand, j[None], axis=0)[0]
            picks[k] = j
            masks[k] = np.take_along_axis(mk, j[None], axis=0)[0]
        for x in b.exclusions:
            value, ja, jb = joint_best(stacks[x.first][0], stacks[x.second][0], x)
            total = total + value
            picks[x.first], picks[x.second] = ja, jb
            masks[x.first] = np.take_along_axis(stacks[x.first][1], ja[None], axis=0)[0]
            masks[x.second] = np.take_along_axis(stacks[x.second][1], jb[None], axis=0)[
                0
            ]
        if best is None:
            better = np.ones(shape, dtype=bool)
            best = total
        else:
            better = total > best
            best = np.where(better, total, best)
        best_branch = np.where(better, i, best_branch)
        best_choice = np.where(better[None], picks, best_choice)
        best_mask = np.where(better[None], masks, best_mask)
    assert best is not None
    flat_b = best_branch.reshape(-1)
    flat_c = best_choice.reshape(width, -1)
    flat_m = best_mask.reshape(width, -1)
    choices = []
    for q in range(flat_b.size):
        n_slots = len(bs[int(flat_b[q])].slots)
        choices.append(
            (
                int(flat_b[q]),
                tuple(int(x) for x in flat_c[:n_slots, q]),
                tuple(int(x) for x in flat_m[:n_slots, q]),
            )
        )
    return Extreme(sign * best, choices)


def governing(
    bs: list[Branch], ev: dict[str, Event], extreme: Extreme, q: int
) -> tuple[str, dict[str, float]]:
    i, picks, masks = extreme.choice[q]
    b = bs[i]
    choice = tuple(s.options[k] for s, k in zip(b.slots, picks, strict=True))
    return combination(b, ev, choice, masks)


DIRECTIONS = 2048
"""Directions of the plane for the maximum of a resultant √(a² + b²) (error ≤
1 − cos(π/2048) ≈ 1,2·10⁻⁶ by default), as in lot 51."""


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
    for chunk in np.array_split(theta, 32):
        c, s = np.cos(chunk)[:, None], np.sin(chunk)[:, None]
        proj = {case: c * a[case][None, :] + s * b[case][None, :] for case in a}
        m = envelope(bs, ev, proj, state, without=without).value.max(axis=0)
        out = m if out is None else np.maximum(out, m)
    assert out is not None
    return out


def brute_force(
    b: Branch, ev: dict[str, Event], values: dict[str, float], sign: float
) -> float:
    """max (sign = 1) or min of a scalar over every combination of a branch, every
    pattern enumerated explicitly (outer sums, numpy): the check of `envelope`."""
    per_slot: list[list[list[float]]] = []
    for s in b.slots:
        slot: list[list[float]] = []
        for n, fac in s.options:
            if n is None:
                slot.append([0.0])
                continue
            e = ev[n]
            fixed = sum(c * values[k] for k, c in e.coefficients.items())
            if not e.modules:
                slot.append([fac * fixed])
                continue
            parts = [sum(c * values[k] for k, c in mc.items()) for _, mc in e.modules]
            slot.append(
                [
                    fac * (fixed + sum(p for i, p in enumerate(parts) if mask >> i & 1))
                    for mask in range(1, 2 ** len(parts))
                ]
            )
        per_slot.append(slot)
    # Lot 54 (P70) : deux emplacements liés deviennent un seul, paire par paire permise.
    joint = b._joint()
    lists = [
        [x for opt in slot for x in opt]
        for k, slot in enumerate(per_slot)
        if k not in joint
    ]
    for x in b.exclusions:
        a, c = per_slot[x.first], per_slot[x.second]
        lists.append(
            [
                p + q
                for i, xs in enumerate(a)
                for j, ys in enumerate(c)
                if x.allowed(i, j)
                for p in xs
                for q in ys
            ]
        )
    total = np.zeros(1)
    for opts in lists:
        total = (total[:, None] + np.array(opts)[None, :]).reshape(-1)
        total = np.unique(total)  # les doublons de valeur ne changent pas l'extrême
    return float(total.max() if sign > 0 else total.min())


# --------------------------------------------------------------------------- files


def event_rows(ev: dict[str, Event]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for e in ev.values():
        for case, c in e.coefficients.items():
            rows.append([e.action, e.name, "fixe", case, float(c)])
        for mod, mc in e.modules:
            for case, c in mc.items():
                rows.append([e.action, e.name, f"module {mod}", case, float(c)])
    return rows


def rule_rows(bs: list[Branch], ev: dict[str, Event]) -> list[list[Any]]:
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
                    b.expanded_count(ev),
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
    "Exclusion",
    "Extreme",
    "Slot",
    "branches",
    "brute_force",
    "check_exclusions",
    "combination",
    "counts",
    "enumerate_branch",
    "envelope",
    "event_rows",
    "events",
    "expanded_counts",
    "governing",
    "joint_best",
    "magnitudes",
    "resultant_max",
    "rule_rows",
]
