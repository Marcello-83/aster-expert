"""Variants of lot 51 bis (`variantes_lot51bis.yaml`, consigne § 1): ring height, free
height of the piles and main beam section; each variant inherits its base and declares
its differences only. The variant of a run is chosen by PONTONS_VARIANTE (default: the
reference, H80C)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from pontons_alu_01.variantes_lot51 import ENV, _resolve

FILE = Path(__file__).resolve().parent / "variantes_lot51bis.yaml"


@dataclass(frozen=True)
class Variant51bis:
    code: str
    description: str
    ring_height: float
    pile_height: float
    beam_side_mm: float
    beam_thickness_mm: float

    @property
    def mesh_overrides(self) -> dict[str, float]:
        return {"H_ANNEAU": self.ring_height, "H_PILES": self.pile_height}

    @property
    def beam_label(self) -> str:
        side, thickness = self.beam_side_mm, self.beam_thickness_mm
        return f"{side:g} × {side:g} × {thickness:g}"


def _data() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    return loaded


@cache
def variants() -> dict[str, Variant51bis]:
    data = _data()
    raw = data["variantes"]
    out = {}
    for code in raw:
        v = _resolve(raw, code)
        out[code] = Variant51bis(
            code=code,
            description=str(v["description"]),
            ring_height=float(v["h_anneau"]),
            pile_height=float(v["h_piles"]),
            beam_side_mm=float(v["poutre"]["cote"]),
            beam_thickness_mm=float(v["poutre"]["epaisseur"]),
        )
    if data["reference"] not in out:
        message = "variante de référence absente"
        raise ValueError(message)
    return out


def reference() -> str:
    return str(_data()["reference"])


def current() -> Variant51bis:
    """The variant named by PONTONS_VARIANTE, or the reference."""
    code = os.environ.get(ENV, reference())
    found = variants().get(code)
    if found is None:
        message = f"{ENV} = {code!r} : variante inconnue ({', '.join(variants())})"
        raise ValueError(message)
    return found


__all__ = ["ENV", "Variant51bis", "current", "reference", "variants"]
