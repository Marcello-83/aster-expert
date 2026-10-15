"""Combinations of lot 51 bis for PONTONS-ALU-01: the rules of lot 51
(`combinaisons_lot51`: set B′ revised and accidental ULS, branches × slots, cases
totalled over the spans) with the buoyancy DEJ of decision P49 tied to the permanent
action:

- with G × 1,2 (fundamental ULS, unfavourable weight): DEJ × 0;
- with G × 0,9 (fundamental ULS, favourable weight): DEJ × 1,0;
- at the SLS and the accidental ULS (G × 1,0): with and without DEJ (DEJ × 1,0 or 0).

DEJ is tied to the factor of G, so it cannot be a slot of its own: the permanent slot
offers events whose coefficients carry it (`G_DEJ_090` = 0,9 × G1 + 0,9 × G2 + 1,0 ×
DEJ, `G_DEJ_100` = G1 + G2 + DEJ, each at factor 1,0), read back by `recombiner.py`
like any other event. Their action is « G », so that « variables seules » (deflections)
leaves them out with the weight.
"""

from __future__ import annotations

from dataclasses import replace

from pontons_alu_01.combinaisons_lot51 import (
    G_FAV,
    G_UNFAV,
    Branch,
    Event,
    Slot,
)
from pontons_alu_01.combinaisons_lot51 import branches as branches_lot51
from pontons_alu_01.combinaisons_lot51 import events as events_lot51

DEJ_EVENTS = ("G_DEJ_090", "G_DEJ_100")


def events(m: dict[str, float]) -> dict[str, Event]:
    """Events of lot 51 (cases totalled over the spans) and the two permanent events
    carrying DEJ."""
    out = events_lot51(m, split=False)
    out["G_DEJ_090"] = Event("G_DEJ_090", "G", {"G1": G_FAV, "G2": G_FAV, "DEJ": 1.0})
    out["G_DEJ_100"] = Event("G_DEJ_100", "G", {"G1": 1.0, "G2": 1.0, "DEJ": 1.0})
    return out


def branches(ev: dict[str, Event]) -> list[Branch]:
    """The branches of lot 51 with the permanent slot of P49."""
    out = []
    for b in branches_lot51(ev):
        if b.state == "ELU_fondamental":
            options = (("G", G_UNFAV), ("G_DEJ_090", 1.0))
        else:
            options = (("G", 1.0), ("G_DEJ_100", 1.0))
        slots = tuple(
            Slot("G (P49 : DEJ lié)", options) if s.label == "G" else s for s in b.slots
        )
        if slots == b.slots:
            message = f"branche {b.name} : emplacement G absent"
            raise ValueError(message)
        out.append(replace(b, slots=slots))
    return out


__all__ = ["DEJ_EVENTS", "branches", "events"]
