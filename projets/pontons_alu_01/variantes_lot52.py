"""Variants of lot 52 (`variantes_lot52.yaml`, consigne § Variantes): the PRO geometry
of the whole pontoon (decisions P62 to P66). Same structure as lot 51 ter
(`variantes_lot51ter`), plus the section of the posts and diagonals (P63) and the
distance e_diag of the diagonal–post node from the main beam axis (P64). The variant of
a run is chosen by PONTONS_VARIANTE (default: the reference, B52)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from pontons_alu_01.variantes_lot51 import ENV, _resolve
from pontons_alu_01.variantes_lot51ter import PIERS, Variant51ter

FILE = Path(__file__).resolve().parent / "variantes_lot52.yaml"


@dataclass(frozen=True)
class Variant52(Variant51ter):
    post_side_mm: float
    post_thickness_mm: float
    e_diag: float

    @property
    def mesh_overrides(self) -> dict[str, Any]:
        """The parameters of `maillage_ponton_52.py` this variant sets."""
        return {
            **super().mesh_overrides,
            "COTE_MONTANTS": self.post_side_mm * 1e-3,
            "E_DIAG": self.e_diag,
        }

    @property
    def post_label(self) -> str:
        s, t = self.post_side_mm, self.post_thickness_mm
        return f"{s:g} × {s:g} × {t:g}"


def _data() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    return loaded


def variant_fields(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The fields of `Variant52` of every variant of a variants file (lot 54 adds its
    own)."""
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
        out[code] = {
            "code": code,
            "description": str(v["description"]),
            "geometry": str(v["geometrie"]),
            "stations": stations,
            "cap_spacing": float(data["entraxe_chevetres"]),
            "pile_heights": heights,
            "cantilever": float(geo["l_pf"]),
            "beam_side_mm": float(v["poutre"]["cote"]),
            "beam_thickness_mm": float(v["poutre"]["epaisseur"]),
            "purlin_side_mm": float(v["panne"]["cote"]),
            "purlin_thickness_mm": float(v["panne"]["epaisseur"]),
            "post_side_mm": float(v["montant"]["cote"]),
            "post_thickness_mm": float(v["montant"]["epaisseur"]),
            "e_diag": float(data["e_diag"]),
        }
    if data["reference"] not in out:
        message = "variante de référence absente"
        raise ValueError(message)
    return out


@cache
def variants() -> dict[str, Variant52]:
    return {code: Variant52(**f) for code, f in variant_fields(_data()).items()}


def reference() -> str:
    return str(_data()["reference"])


def current() -> Variant52:
    """The variant named by PONTONS_VARIANTE, or the reference."""
    code = os.environ.get(ENV, reference())
    found = variants().get(code)
    if found is None:
        message = f"{ENV} = {code!r} : variante inconnue ({', '.join(variants())})"
        raise ValueError(message)
    return found


__all__ = [
    "ENV",
    "PIERS",
    "Variant52",
    "current",
    "reference",
    "variant_fields",
    "variants",
]
