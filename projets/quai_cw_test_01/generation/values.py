"""Typed access to `ModelData` values, with the SI conversion the generator
owns (CLAUDE.md, "les conversions d'unités vers le SI sont faites par le
générateur et commentées") -- every number the `.comm` writes traces back to
one of these accessors, never a literal typed by hand.

Units accepted here are exactly the units the data file's own comments name
(`projets/quai_cw_test_01/donnees/combiwall_model_data.yaml`): m, m CM (a level,
already in metres), mm, MPa, MN/m, MN.m2/m, kg/m3, deg, kN, kN.m, kPa, m/s2, "-".
"""

from __future__ import annotations

import math
from typing import Any

from aster_expert.agent.model_data import ModelData
from quai_cw_test_01.generation.errors import GenerationError

_TO_SI = {
    "m": 1.0,
    "m CM": 1.0,
    "mm": 1.0e-3,
    "MPa": 1.0e6,
    "MN/m": 1.0e6,
    "MN.m2/m": 1.0e6,
    "MN/m3": 1.0e6,
    "cm2": 1.0e-4,
    "kg/m3": 1.0,
    "kg/m2": 1.0,
    "deg": math.pi / 180.0,
    "kN": 1.0e3,
    "kN.m": 1.0e3,
    "kPa": 1.0e3,
    "m/s2": 1.0,
    "-": 1.0,
    "N/m2": 1.0,
}


class ModelValues:
    """Wraps a `ModelData`, converting every scalar read to SI (m, N, Pa, kg,
    rad) on the way out. A name absent, `a_fournir`, or of a unit not listed
    in `_TO_SI` is refused explicitly -- never silently passed through."""

    def __init__(self, data: ModelData) -> None:
        self._data = data
        self._items = data.items()

    def _item(self, name: str) -> Any:
        item = self._items.get(name)
        if item is None:
            message = f"valeur absente du fichier de données : {name}"
            raise GenerationError(message)
        if item.status != "fourni":
            message = f"valeur à fournir, non générable : {name}"
            raise GenerationError(message)
        return item

    def raw(self, name: str) -> Any:
        """The value exactly as the data file states it, no conversion."""
        return self._item(name).value

    def unit(self, name: str) -> str:
        return str(self._item(name).unit)

    def si(self, name: str) -> float:
        """A scalar value converted to SI."""
        item = self._item(name)
        if item.value is None:
            message = f"valeur {name} : pas de scalaire (profil ?)"
            raise GenerationError(message)
        factor = _TO_SI.get(item.unit)
        if factor is None:
            message = f"unité non convertible en SI : {name} [{item.unit}]"
            raise GenerationError(message)
        if isinstance(item.value, str):
            message = f"valeur {name} : texte, pas un scalaire SI"
            raise GenerationError(message)
        if isinstance(item.value, tuple):
            message = f"valeur {name} : vecteur, utiliser si_vector()"
            raise GenerationError(message)
        return float(item.value) * factor

    def si_vector(self, name: str) -> tuple[float, ...]:
        item = self._item(name)
        factor = _TO_SI.get(item.unit, 1.0) if item.unit != "-" else 1.0
        assert isinstance(item.value, tuple)
        return tuple(float(v) * factor for v in item.value)

    def text(self, name: str) -> str:
        item = self._item(name)
        assert isinstance(item.value, str)
        return item.value

    def profile_si(
        self, name: str
    ) -> list[tuple[float, float, str | None, str | None]]:
        """A profile's points `(z, p, layer, component)`, `z` and `p` in SI
        (Pa for a pressure, m for a level -- the data's own `m CM`/`kPa`)."""
        item = self._item(name)
        if item.profile is None:
            message = f"valeur {name} : pas de profil"
            raise GenerationError(message)
        p_factor = _TO_SI.get(item.unit)
        if p_factor is None:
            message = f"unité de profil non convertible en SI : {name} [{item.unit}]"
            raise GenerationError(message)
        return [(pt.z, pt.p * p_factor, pt.layer, pt.component) for pt in item.profile]


__all__ = ["ModelValues"]
