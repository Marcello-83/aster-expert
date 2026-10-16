"""Combinations of lot 51 quater for PONTONS-ALU-01: the rules of lot 51 ter
(`combinaisons_lot51ter`, set B′ revised, accidental ULS, P49, P56 rules, P57, P59, Q
and QD by modules) with the houle coefficients of P60 and the quasi-static impact of
P61.
The unit cases are those of lot 51 ter, unchanged; only the events change.

- P60 (« tablier noyé », P56 revised): HU = HU_TUBES × 4,92 + HU_PANNES × 1,91 (purlins
  50 × 50) or 2,11 (60 × 60) + HU_PLATELAGE × 0,90 ; HD = HD_TABLIER × 1,01 ; HU_F
  unchanged (2,36 ; 0,85 ; 0,35), uniform on the whole length, in phase.
- P61: six exclusive events HU_IMP_Mk (k = 0 to 5), each p_imp × (HU_TUBES_Mk +
  HU_PANNES_Mk + HU_PLATELAGE_Mk) on module Mk alone, action « HI ». HU_IMP_Mk and HU
  are alternatives in the houle slot (the impact precedes the immersion), with the
  factors of HU at the fundamental ULS and the characteristic SLS (lead and
  accompaniment); no impact at the accidental ULS, the frequent and the quasi-permanent
  SLS; P57 holds (never with AC or ACA) and B′ too (never with Q).
- Sensitivity without decision (consigne § Sensibilité, AVP forfait): HU_S5 =
  5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) on the whole length, in place of HU, no
  impact; used for `ancrage.csv` and `palee_equilibre.csv` only.

The envelopes, the governing combinations and the explicit enumeration are those of
`combinaisons_lot51ter` (decomposition by slot, validated in lot 51 ter): only the rule
builder knows the new action « HI ».
"""

from __future__ import annotations

from typing import Any

from pontons_alu_01.combinaisons_lot51ter import (
    ACTIONS,
    G_UNFAV,
    VARIABLES,
    Branch,
    Event,
    Option,
    Slot,
    events,
    magnitudes,
)

HOULE_ACTIONS = ("H", "HI", "HF")
"""Actions of the houle: characteristic HU, HD (H), impacts (HI), frequent HU_F (HF)."""
IMPACT = "HI"
IMPACT_STATES = ("ELU_fondamental", "ELS_caracteristique")
"""States where the impact enters (P61), with the factors of HU."""
S5_PRESSURE_KPA = 5.0
"""HU_S5: AVP forfait of 5 kPa on the three underside cases, sensitivity without
decision (consigne of lot 51 quater, § Sensibilité); never a design value."""
IMPACT_CASES = ("HU_TUBES", "HU_PANNES", "HU_PLATELAGE")


def magnitudes_p60(data: dict[str, Any], purlin_side_mm: float) -> dict[str, float]:
    """Magnitudes of lot 51 ter with the houle coefficients of P60 (kPa); the purlin
    coefficient depends on the purlin size of the variant (50 or 60 mm)."""
    out = magnitudes(data)
    key = {50.0: "hu_pannes_50", 60.0: "hu_pannes_60"}.get(float(purlin_side_mm))
    if key is None:
        message = (
            f"P60 : pas de coefficient HU_PANNES pour des pannes de {purlin_side_mm} mm"
        )
        raise ValueError(message)
    out["hu_tubes"] = float(data["houle_lot51quater.hu_tubes"])
    out["hu_pannes"] = float(data[f"houle_lot51quater.{key}"])
    out["hu_platelage"] = float(data["houle_lot51quater.hu_platelage"])
    out["hd_tablier"] = float(data["houle_lot51quater.hd_tablier"])
    out["p_impact"] = float(data["houle_lot51quater.p_impact"])
    return out


def events_p60_p61(
    m: dict[str, float],
    *,
    zones: list[str],
    cleats: list[int],
    modules: list[str],
) -> dict[str, Event]:
    """Events of lot 51 ter with the magnitudes `m` (P60), plus HU_IMP_Mk (P61)."""
    out = events(m, zones=zones, cleats=cleats, modules=modules)
    p = m["p_impact"]
    for mod in modules:
        name = f"HU_IMP_{mod}"
        out[name] = Event(name, IMPACT, {f"{c}_{mod}": p for c in IMPACT_CASES})
    return out


def events_s5(
    m: dict[str, float],
    *,
    zones: list[str],
    cleats: list[int],
    modules: list[str],
) -> dict[str, Event]:
    """Sensitivity HU_S5: the events of P60 with HU replaced by HU_S5 (5 kPa on the
    three underside cases), without impact."""
    base = dict(m)
    for k in ("hu_tubes", "hu_pannes", "hu_platelage"):
        base[k] = S5_PRESSURE_KPA
    out: dict[str, Event] = {}
    for name, e in events(base, zones=zones, cleats=cleats, modules=modules).items():
        if name == "HU":
            out["HU_S5"] = Event("HU_S5", e.action, e.coefficients, e.modules)
        else:
            out[name] = e
    return out


# --------------------------------------------------------------------------- rules


def _names(ev: dict[str, Event], action: str, state: str) -> list[str]:
    """Events of an action; the houle (H) takes the impacts (HI) in IMPACT_STATES."""
    wanted = {action}
    if action == "H" and state in IMPACT_STATES:
        wanted.add(IMPACT)
    return [e.name for e in ev.values() if e.action in wanted]


def _slot(label: str, names: list[str], factor: float, *, absent: bool) -> Slot:
    opts: list[Option] = [(None, 0.0)] if absent else []
    opts += [(n, factor) for n in names]
    return Slot(label, tuple(opts))


def _accompanying(
    ev: dict[str, Event],
    lead: str | None,
    factor: dict[str, float],
    excluded: tuple[str, ...],
    state: str,
    *,
    no_houle: bool,
) -> list[tuple[str, list[Slot]]]:
    """`combinaisons_lot51ter._accompanying`, the houle slot taking the impacts in
    IMPACT_STATES."""
    pool = [
        a for a in VARIABLES if a != lead and a not in excluded and factor[a] != 0.0
    ]
    base = [
        _slot(a, _names(ev, a, state), factor[a], absent=True)
        for a in ("T", "AM")
        if a in pool
    ]
    h_ok = "H" in pool and lead != "Q" and not no_houle
    q_ok = "Q" in pool and lead != "H"
    ac_ok = "AC" in pool and lead != "H"

    def hq(with_h: bool) -> list[Slot]:
        opts: list[Option] = [(None, 0.0)]
        if with_h:
            opts += [(n, factor["H"]) for n in _names(ev, "H", state)]
        if q_ok:
            opts += [(n, factor["Q"]) for n in _names(ev, "Q", state)]
        return [Slot("H/Q" if with_h else "Q", tuple(opts))] if len(opts) > 1 else []

    if ac_ok and h_ok:
        return [
            (
                "avec AC",
                [
                    *base,
                    _slot("AC", _names(ev, "AC", state), factor["AC"], absent=False),
                    *hq(False),
                ],
            ),
            ("sans AC", [*base, *hq(True)]),
        ]
    slots = list(base)
    if ac_ok:
        slots.append(_slot("AC", _names(ev, "AC", state), factor["AC"], absent=True))
    slots += hq(h_ok)
    return [("", slots)]


def _lead_slot(ev: dict[str, Event], lead: str, factor: float, state: str) -> Slot:
    if lead == "H" and state == "ELS_frequent":
        return Slot("H (HU_F, P56)", tuple((n, 1.0) for n in _names(ev, "HF", state)))
    return _slot(lead, _names(ev, lead, state), factor, absent=False)


def branches(ev: dict[str, Event]) -> list[Branch]:
    """`combinaisons_lot51ter.branches` with the impacts of P61 in the houle slot of
    the fundamental ULS and the characteristic SLS. Without any « HI » event, the
    branches are those of lot 51 ter (checked by a test)."""
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
            for tag, rest in _accompanying(
                ev, lead, acc_f, (), state, no_houle=lead == "AC"
            ):
                add(
                    state,
                    f"dominante {lead}" + (f" ({tag})" if tag else ""),
                    head,
                    rest,
                )
    for _, rest in _accompanying(
        ev, None, psi2, (), "ELS_quasi_permanent", no_houle=False
    ):
        add("ELS_quasi_permanent", "sans dominante", [perm], rest)
    state = "ELU_accidentel"
    for accidental, excluded in (("ACA", "AC"), ("AMF", "AM")):
        leads: list[str | None] = [None, *(x for x in VARIABLES if x != excluded)]
        for acc_lead in leads:
            if accidental == "ACA" and acc_lead == "H":
                continue  # P57 : pas de houle avec l'accostage accidentel
            head = [
                perm,
                _slot(accidental, _names(ev, accidental, state), 1.0, absent=False),
            ]
            if acc_lead is not None:
                head.append(
                    _slot(
                        acc_lead,
                        _names(ev, acc_lead, state),
                        psi1[acc_lead],
                        absent=False,
                    )
                )
            no_houle = accidental == "ACA" or acc_lead == "AC"
            for tag, rest in _accompanying(
                ev, acc_lead, psi2, (excluded,), state, no_houle=no_houle
            ):
                add(
                    state,
                    f"{accidental}, dominante {acc_lead or 'aucune'}"
                    + (f" ({tag})" if tag else ""),
                    head,
                    rest,
                )
    return out


def check_exclusions(bs: list[Branch], ev: dict[str, Event]) -> list[str]:
    """`combinaisons_lot51ter.check_exclusions` with the impacts counted as houle, and
    P61: no impact outside IMPACT_STATES, never two houle events together."""
    problems = []
    houle, berthing = set(HOULE_ACTIONS), {"AC", "ACA"}
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

        if apart(houle, {"Q"}):
            problems.append(f"{b.state}/{b.name} : houle et Q (B′)")
        if apart(houle, berthing):
            problems.append(f"{b.state}/{b.name} : houle et accostage (P57)")
        if apart(berthing, berthing):
            problems.append(f"{b.state}/{b.name} : deux événements d'accostage")
        if apart(houle, houle):
            problems.append(f"{b.state}/{b.name} : deux événements de houle (P61)")
        if b.state not in IMPACT_STATES and any(IMPACT in acts for acts in actions):
            problems.append(f"{b.state}/{b.name} : impact hors ELU f. et ELS c (P61)")
    return problems


__all__ = [
    "HOULE_ACTIONS",
    "IMPACT",
    "IMPACT_STATES",
    "S5_PRESSURE_KPA",
    "branches",
    "check_exclusions",
    "events_p60_p61",
    "events_s5",
    "magnitudes_p60",
]
