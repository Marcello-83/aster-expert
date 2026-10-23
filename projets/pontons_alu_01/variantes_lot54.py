"""Variants of lot 54 (`variantes_lot54.yaml`, consigne § Variantes): the final PRO
geometry of the whole pontoon (decisions P67 to P76). Same fields as lot 52
(`variantes_lot52.variant_fields`), plus the inner posts of a long span (P67: regular
truss, five equal panels of 1,25 m) and the cap beams (P68: width 0,60 along X, ends at
Y = ±1,20). The variant of a run is chosen by PONTONS_VARIANTE (default: the reference,
B54)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from pontons_alu_01.variantes_lot51 import ENV
from pontons_alu_01.variantes_lot51ter import PIERS
from pontons_alu_01.variantes_lot52 import Variant52, variant_fields

FILE = Path(__file__).resolve().parent / "variantes_lot54.yaml"


@dataclass(frozen=True)
class Variant54(Variant52):
    inner_posts: tuple[float, ...]
    cap_width: float
    cap_ends: tuple[float, float]

    @property
    def mesh_overrides(self) -> dict[str, Any]:
        """The parameters of `maillage_ponton_52.py` this variant sets."""
        return {
            **super().mesh_overrides,
            "X_MONTANTS": list(self.inner_posts),
            "B_CHEVETRE": self.cap_width,
            "Y_CHEVETRE": list(self.cap_ends),
        }


def _data() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    return loaded


@cache
def variants() -> dict[str, Variant54]:
    data = _data()
    posts = tuple(float(x) for x in data["x_montants"])
    if list(posts) != sorted(posts):
        message = "x_montants : abscisses croissantes attendues"
        raise ValueError(message)
    lo, hi = (float(y) for y in data["chevetres"]["y"])
    return {
        code: Variant54(
            **f,
            inner_posts=posts,
            cap_width=float(data["chevetres"]["b"]),
            cap_ends=(lo, hi),
        )
        for code, f in variant_fields(data).items()
    }


def reference() -> str:
    return str(_data()["reference"])


def current() -> Variant54:
    """The variant named by PONTONS_VARIANTE, or the reference."""
    code = os.environ.get(ENV, reference())
    found = variants().get(code)
    if found is None:
        message = f"{ENV} = {code!r} : variante inconnue ({', '.join(variants())})"
        raise ValueError(message)
    return found


__all__ = ["ENV", "PIERS", "Variant54", "current", "reference", "variants"]
