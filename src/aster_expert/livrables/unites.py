"""Units of the deliverable fields (lot 49): SI unit of each component, and the unit it
is displayed in.

The models of the projects are written in m, N, Pa (`DeliverablesSection.units`). The
unit of a component follows from the family of elements it belongs to, never from its
name alone: `N` is a force (N) on a beam, `NXX` a force per unit length (N/m) on a
shell. Values are never converted in a file that feeds a computation; the display
unit only serves the workbook and the CSV files meant for reading, whose number of
decimals comes from `config/arrondis.yaml`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayUnit:
    unit: str
    """Unit of the displayed value."""
    factor: float
    """Displayed value = SI value × factor."""


DISPLAY: dict[str, DisplayUnit] = {
    "m": DisplayUnit("mm", 1000.0),
    "rad": DisplayUnit("mrad", 1000.0),
    "N": DisplayUnit("kN", 1.0e-3),
    "N·m": DisplayUnit("kN·m", 1.0e-3),
    "N/m": DisplayUnit("kN/m", 1.0e-3),
    "N·m/m": DisplayUnit("kN·m/m", 1.0e-3),
    "Pa": DisplayUnit("MPa", 1.0e-6),
    "°C": DisplayUnit("°C", 1.0),
}
"""SI unit -> display unit (kN, kN·m, mm, MPa: the units of the notes and of the lot 47
exports)."""

_TRANSLATIONS = ("DX", "DY", "DZ")
_ROTATIONS = ("DRX", "DRY", "DRZ")


def si_unit(family: str, field: str, component: str) -> str:
    """SI unit of `component` of `field` for a family of elements (or `charges`).

    Raises `KeyError` for a component the trunk does not know how to label: a
    deliverable never shows a value without its unit.
    """
    if component in ("TEMP", "TEMP_MIL", "TEMP_INF", "TEMP_SUP"):
        return "°C"
    if field == "DEPL":
        if component in _TRANSLATIONS:
            return "m"
        if component in _ROTATIONS:
            return "rad"
    if field == "REAC_NODA" or family == "charges":
        if component in _TRANSLATIONS:
            return "N"
        if component in _ROTATIONS:
            return "N·m"
    if family == "efforts_coques":
        if component in ("NXX", "NYY", "NXY", "QX", "QY"):
            return "N/m"
        if component in ("MXX", "MYY", "MXY"):
            return "N·m/m"
    if family in ("efforts_poutres", "ressorts"):
        if component in ("N", "VY", "VZ"):
            return "N"
        if component in ("MT", "MFY", "MFZ"):
            return "N·m"
    if family == "contraintes_volumes" and component.startswith("SI"):
        return "Pa"
    message = (
        f"unité inconnue : famille {family}, champ {field}, composante {component}"
    )
    raise KeyError(message)


def display(si: str) -> DisplayUnit:
    """The display unit of an SI unit."""
    return DISPLAY[si]


__all__ = ["DISPLAY", "DisplayUnit", "display", "si_unit"]
