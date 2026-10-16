"""Variants of lot 51 ter (`variantes_lot51ter.yaml`, consigne § Variantes): the whole
pontoon (abutment, five piers, five long spans, end cantilever), geometry of panne A or
B (free height of the piles of each pier, cantilever length) and sections of the main
beams and purlins; each variant inherits its base and declares its differences only.
The variant of a run is chosen by PONTONS_VARIANTE (default: the reference, B10)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from pontons_alu_01.variantes_lot51 import ENV, _resolve

FILE = Path(__file__).resolve().parent / "variantes_lot51ter.yaml"
PIERS = 5


@dataclass(frozen=True)
class Variant51ter:
    code: str
    description: str
    geometry: str
    stations: tuple[float, ...]
    cap_spacing: float
    pile_heights: tuple[float, ...]
    cantilever: float
    beam_side_mm: float
    beam_thickness_mm: float
    purlin_side_mm: float
    purlin_thickness_mm: float

    @property
    def mesh_overrides(self) -> dict[str, Any]:
        """The parameters of `maillage_ponton_51ter.py` this variant sets."""
        return {
            "STATIONS": list(self.stations),
            "ENTRAXE_CHEVETRES": self.cap_spacing,
            "H_PILES": list(self.pile_heights),
            "L_PF": self.cantilever,
            "COTE_PANNES": self.purlin_side_mm * 1e-3,
        }

    @property
    def beam_label(self) -> str:
        s, t = self.beam_side_mm, self.beam_thickness_mm
        return f"{s:g} × {s:g} × {t:g}"

    @property
    def purlin_label(self) -> str:
        s, t = self.purlin_side_mm, self.purlin_thickness_mm
        return f"{s:g} × {s:g} × {t:g}"


def _data() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    return loaded


@cache
def variants() -> dict[str, Variant51ter]:
    data = _data()
    stations = tuple(float(x) for x in data["stations"])
    if len(stations) != PIERS or list(stations) != sorted(stations):
        message = f"stations : {PIERS} abscisses croissantes attendues"
        raise ValueError(message)
    raw = data["variantes"]
    out = {}
    for code in raw:
        v = _resolve(raw, code)
        geo = data["geometries"][v["geometrie"]]
        heights = tuple(float(h) for h in geo["h_piles"])
        if len(heights) != PIERS:
            message = (
                f"géométrie {v['geometrie']} : {PIERS} hauteurs de piles attendues"
            )
            raise ValueError(message)
        out[code] = Variant51ter(
            code=code,
            description=str(v["description"]),
            geometry=str(v["geometrie"]),
            stations=stations,
            cap_spacing=float(data["entraxe_chevetres"]),
            pile_heights=heights,
            cantilever=float(geo["l_pf"]),
            beam_side_mm=float(v["poutre"]["cote"]),
            beam_thickness_mm=float(v["poutre"]["epaisseur"]),
            purlin_side_mm=float(v["panne"]["cote"]),
            purlin_thickness_mm=float(v["panne"]["epaisseur"]),
        )
    if data["reference"] not in out:
        message = "variante de référence absente"
        raise ValueError(message)
    return out


def reference() -> str:
    return str(_data()["reference"])


def current() -> Variant51ter:
    """The variant named by PONTONS_VARIANTE, or the reference."""
    code = os.environ.get(ENV, reference())
    found = variants().get(code)
    if found is None:
        message = f"{ENV} = {code!r} : variante inconnue ({', '.join(variants())})"
        raise ValueError(message)
    return found


__all__ = ["ENV", "PIERS", "Variant51ter", "current", "reference", "variants"]
