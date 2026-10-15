"""Variants of lot 51 (`variantes_lot51.yaml`, consigne § 2): each variant inherits its
base and declares its differences only. The variant of a run is chosen by the variable
PONTONS_VARIANTE (default: the reference, R)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal

import yaml

FILE = Path(__file__).resolve().parent / "variantes_lot51.yaml"
PILES = ("C1_YM", "C1_YP", "C2_YM", "C2_YP")
ENV = "PONTONS_VARIANTE"

Head = Literal["rotule", "encastrement"]


@dataclass(frozen=True)
class Variant:
    code: str
    description: str
    heads: dict[str, Head]
    ring: Literal["monolithique", "independant"]
    splice: Literal["articule", "continu"]
    pile_height: float
    bearings: Literal["neoprene", "mecanique"]
    kh_factor: float
    beam_side_mm: float
    beam_thickness_mm: float

    @property
    def mesh_overrides(self) -> dict[str, float]:
        return {"H_PILES": self.pile_height}

    @property
    def beam_label(self) -> str:
        side, thickness = self.beam_side_mm, self.beam_thickness_mm
        return f"{side:g} × {side:g} × {thickness:g}"


def _resolve(
    raw: dict[str, Any], code: str, seen: tuple[str, ...] = ()
) -> dict[str, Any]:
    if code in seen:
        message = f"variante {code} : héritage circulaire"
        raise ValueError(message)
    entry = dict(raw[code])
    base = entry.pop("base", None)
    if base is None:
        return entry
    merged = _resolve(raw, str(base), (*seen, code))
    merged.update(entry)
    return merged


@cache
def variants() -> dict[str, Variant]:
    data = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    raw = data["variantes"]
    out = {}
    for code in raw:
        v = _resolve(raw, code)
        heads = dict(v["tetes"])
        if sorted(heads) != sorted(PILES) or not set(heads.values()) <= {
            "rotule",
            "encastrement",
        }:
            message = f"variante {code} : têtes de piles {heads}"
            raise ValueError(message)
        out[code] = Variant(
            code=code,
            description=str(v["description"]),
            heads=heads,
            ring=v["anneau"],
            splice=v["eclissage"],
            pile_height=float(v["h_piles"]),
            bearings=v["appuis"],
            kh_factor=float(v["facteur_kh"]),
            beam_side_mm=float(v["poutre"]["cote"]),
            beam_thickness_mm=float(v["poutre"]["epaisseur"]),
        )
    if data["reference"] not in out:
        message = "variante de référence absente"
        raise ValueError(message)
    return out


def reference() -> str:
    return str(yaml.safe_load(FILE.read_text(encoding="utf-8"))["reference"])


def current() -> Variant:
    """The variant named by PONTONS_VARIANTE, or the reference."""
    code = os.environ.get(ENV, reference())
    found = variants().get(code)
    if found is None:
        message = f"{ENV} = {code!r} : variante inconnue ({', '.join(variants())})"
        raise ValueError(message)
    return found


__all__ = ["ENV", "PILES", "Variant", "current", "reference", "variants"]
