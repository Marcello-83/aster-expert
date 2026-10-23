"""Combinations of lot 54 for PONTONS-ALU-01: the rules of lot 51 ter
(`combinaisons_lot51ter`: set B′ revised, accidental ULS, P49, P57, P59, Q and QD by
modules) with the houle of P69 and the rule P70.

- P69 (P56 and P60 revised, P61 cancelled): HU = 5,0 × (HU_TUBES + HU_PANNES +
  HU_PLATELAGE); HD = 5,0 × HD_TABLIER; HU_F = 2,728 HU_TUBES + 2,516 HU_PANNES +
  2,425 HU_PLATELAGE at the frequent SLS; no impact event (HU_IMP_Mk removed). The
  unit cases of 1 kPa by surface and module are those of P56. Values: data group
  `houle_lot54`.
- P70: a local mooring (AML_TQk_…) or a broken mooring line (AMF_TQk_…) and a berthing
  (AC_… or ACA_…) never come together when both are on the same side and the berthing
  zone centre is less than 1,60 m from the cleat in X. AM1 and AM2 stay combinable with
  AC and ACA. In each branch holding both a mooring and a berthing slot, the two slots
  are maximised jointly over the allowed pairs (`combinaisons_lot51ter.Exclusion`,
  `joint_best`); the other slots stay independent.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pontons_alu_01.combinaisons_lot51ter import (
    Branch,
    Event,
    Exclusion,
    events,
    magnitudes,
)
from pontons_alu_01.combinaisons_lot51ter import (
    branches as branches_51ter,
)
from pontons_alu_01.geometrie_lot51ter import Geometry51ter

HOULE_ACTIONS = ("H", "HF")
POST_HALF_WIDTH = 1.60
"""m, half width of a berth (3,20 m, P70): a berthing zone centre closer than this to a
cleat on the same side is the same berth."""
MOORING_PREFIXES = ("AML", "AMF")
BERTHING_PREFIXES = ("AC", "ACA")


def magnitudes_p69(data: dict[str, Any]) -> dict[str, float]:
    """Magnitudes of lot 51 ter with the houle of P69 (kPa, group houle_lot54)."""
    out = magnitudes(data)
    for key in (
        "hu_tubes",
        "hu_pannes",
        "hu_platelage",
        "hd_tablier",
        "huf_tubes",
        "huf_pannes",
        "huf_platelage",
    ):
        out[key] = float(data[f"houle_lot54.{key}"])
    return out


def events_p69(
    m: dict[str, float],
    *,
    zones: list[str],
    cleats: list[int],
    modules: list[str],
) -> dict[str, Event]:
    """Events of lot 51 ter with the magnitudes `m` of P69, no impact."""
    return events(m, zones=zones, cleats=cleats, modules=modules)


# --------------------------------------------------------------------------- P70


@dataclass(frozen=True)
class Incompatibility:
    mooring: str
    berthing: str
    side: str
    cleat: int
    x_cleat: float
    zone: str
    x_zone: float

    @property
    def distance(self) -> float:
        return abs(self.x_zone - self.x_cleat)


def zone_centres(g: Geometry51ter) -> dict[str, float]:
    """X of the centre of each berthing zone (one value for both sides)."""
    out: dict[str, float] = {}
    for z in g.zones:
        name = z.name.removeprefix("ACC_")[:-3]
        centre = (z.x0 + z.x1) / 2.0
        if name in out and abs(out[name] - centre) > 1e-9:
            message = f"zone {name} : centres différents selon la rive"
            raise ValueError(message)
        out[name] = centre
    return out


def expected_centres(g: Geometry51ter) -> dict[str, float]:
    """The centres of P70 written from the spans: start Xd + 0,5, middle (Xd + Xf)/2,
    end Xf − 0,5, PTk middle, PF 38,85 + Lpf − 0,5."""
    out: dict[str, float] = {}
    for s in g.spans:
        if s.nature == "grande":
            out[f"{s.name}D"] = s.x0 + 0.5
            out[f"{s.name}M"] = (s.x0 + s.x1) / 2.0
            out[f"{s.name}F"] = s.x1 - 0.5
        elif s.nature == "petite":
            k = int(s.name[2:])
            station = g.parameters["STATIONS"][k - 1]
            out[s.name] = station + g.parameters["ENTRAXE_CHEVETRES"] / 2.0
        else:
            out[s.name] = s.x1 - 0.5
    return out


def incompatibilities(ev: dict[str, Event], g: Geometry51ter) -> list[Incompatibility]:
    """Every forbidden pair (mooring event, berthing event) of P70."""
    centres = zone_centres(g)
    cleat_x = {n: x for n, x, _ in g.cleats}
    out: list[Incompatibility] = []
    for m in ev.values():
        prefix, _, rest = m.name.partition("_")
        if prefix not in MOORING_PREFIXES:
            continue
        tq, side, _ = rest.split("_")
        cleat = int(tq.removeprefix("TQ"))
        for b in ev.values():
            bprefix, _, brest = b.name.partition("_")
            if bprefix not in BERTHING_PREFIXES:
                continue
            zone, bside, _ = brest.split("_")
            if bside != side:
                continue
            if abs(centres[zone] - cleat_x[cleat]) < POST_HALF_WIDTH:
                out.append(
                    Incompatibility(
                        m.name, b.name, side, cleat, cleat_x[cleat], zone, centres[zone]
                    )
                )
    return out


def forbidden_pairs(items: list[Incompatibility]) -> set[frozenset[str]]:
    return {frozenset((i.mooring, i.berthing)) for i in items}


def with_exclusions(bs: list[Branch], forbidden: set[frozenset[str]]) -> list[Branch]:
    """The branches with an Exclusion on every pair of slots holding a forbidden pair
    of options (P70)."""
    out = []
    for b in bs:
        found = []
        for i, si in enumerate(b.slots):
            for j in range(i + 1, len(b.slots)):
                sj = b.slots[j]
                pairs = frozenset(
                    (a, c)
                    for a, (na, _) in enumerate(si.options)
                    for c, (nc, _) in enumerate(sj.options)
                    if na is not None
                    and nc is not None
                    and frozenset((na, nc)) in forbidden
                )
                if pairs:
                    found.append(Exclusion(i, j, pairs))
        out.append(replace(b, exclusions=tuple(found)))
    return out


def branches_p70(ev: dict[str, Event], g: Geometry51ter) -> list[Branch]:
    """Branches of lot 51 ter on the events of P69, with the exclusions of P70."""
    return with_exclusions(
        branches_51ter(ev), forbidden_pairs(incompatibilities(ev, g))
    )


def joint_branch(b: Branch) -> bool:
    """Whether a branch holds both a mooring and a berthing slot (P70 applies)."""
    return bool(b.exclusions)


def check_rules(bs: list[Branch], ev: dict[str, Event]) -> list[str]:
    """Breaches of B′ (houle and Q), P57 (houle and berthing), two berthing events,
    and of the structure of P70 (an AML/AMF slot and an AC/ACA slot in one branch
    without exclusion)."""
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

        houle, berthing = set(HOULE_ACTIONS), {"AC", "ACA"}
        if apart(houle, {"Q"}):
            problems.append(f"{b.state}/{b.name} : houle et Q (B′)")
        if apart(houle, berthing):
            problems.append(f"{b.state}/{b.name} : houle et accostage (P57)")
        if apart(berthing, berthing):
            problems.append(f"{b.state}/{b.name} : deux événements d'accostage")
        if apart({"AM", "AMF"}, berthing) and not b.exclusions:
            problems.append(f"{b.state}/{b.name} : amarrage et accostage sans P70")
    return problems


__all__ = [
    "HOULE_ACTIONS",
    "POST_HALF_WIDTH",
    "Incompatibility",
    "branches_p70",
    "check_rules",
    "events_p69",
    "expected_centres",
    "forbidden_pairs",
    "incompatibilities",
    "joint_branch",
    "magnitudes_p69",
    "with_exclusions",
    "zone_centres",
]
