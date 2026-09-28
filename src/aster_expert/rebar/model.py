"""Data models of the independent EN 1992-1-1 section design (lot 38).

Units are consistent and fixed for the whole package: lengths in m, stresses in MPa,
forces in MN, moments in MN.m, areas in m2. A caller working in N and Pa converts at
its boundary.

Sign conventions of the package (not those of Code_Aster, which the trial scripts map
explicitly):

- axial force `n_tension`: positive in tension;
- bending moment `m`: positive when the **positive face** of the section is in
  tension, whatever the axis. The two faces carry their own cover.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# Ductility class of the reinforcing steel: characteristic strain at maximum load.
_EPS_UK = {"A": 0.025, "B": 0.05, "C": 0.075}


class Concrete(BaseModel):
    """Concrete of the section (EN 1992-1-1, 3.1.7 and Table 3.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fck: float = Field(gt=0.0)
    """Characteristic cylinder strength, MPa."""
    gamma_c: float = Field(gt=0.0)
    alpha_cc: float = Field(default=1.0, gt=0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fcd(self) -> float:
        """Design strength, MPa."""
        return self.alpha_cc * self.fck / self.gamma_c

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eps_c2(self) -> float:
        """Strain at maximum stress (parabola-rectangle)."""
        if self.fck <= 50.0:
            return 2.0e-3
        return (2.0 + 0.085 * float((self.fck - 50.0) ** 0.53)) * 1e-3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eps_cu2(self) -> float:
        """Ultimate strain (parabola-rectangle)."""
        if self.fck <= 50.0:
            return 3.5e-3
        return (2.6 + 35.0 * ((90.0 - self.fck) / 100.0) ** 4) * 1e-3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exponent(self) -> float:
        """Exponent `n` of the parabolic branch."""
        if self.fck <= 50.0:
            return 2.0
        return 1.4 + 23.4 * ((90.0 - self.fck) / 100.0) ** 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def lam(self) -> float:
        """Depth factor `lambda` of the simplified rectangular block."""
        return 0.8 if self.fck <= 50.0 else 0.8 - (self.fck - 50.0) / 400.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eta(self) -> float:
        """Strength factor `eta` of the simplified rectangular block."""
        return 1.0 if self.fck <= 50.0 else 1.0 - (self.fck - 50.0) / 200.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fctm(self) -> float:
        """Mean tensile strength, MPa (EN 1992-1-1, Table 3.1)."""
        if self.fck <= 50.0:
            return 0.30 * float(self.fck ** (2.0 / 3.0))
        return 2.12 * math.log(1.0 + (self.fck + 8.0) / 10.0)


class Steel(BaseModel):
    """Reinforcing steel, horizontal-plateau diagram (`TYPE_DIAGRAMME = 'B2'`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fyk: float = Field(gt=0.0)
    """Characteristic yield strength, MPa."""
    es: float = Field(default=210000.0, gt=0.0)
    """Young modulus, MPa."""
    gamma_s: float = Field(gt=0.0)
    ductility_class: Literal["A", "B", "C"] = "B"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fyd(self) -> float:
        return self.fyk / self.gamma_s

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eps_ud(self) -> float:
        """Design ultimate strain, `0.9 * eps_uk`."""
        return 0.9 * _EPS_UK[self.ductility_class]

    def stress(self, strain: float) -> float:
        """Stress (MPa) for a strain, compression positive, plateau not limited."""
        return max(-self.fyd, min(self.fyd, self.es * strain))


class Rectangle(BaseModel):
    """Rectangular section bent in the plane of its depth `h`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    width: float = Field(gt=0.0)
    """`b`, m, perpendicular to the bending plane."""
    depth: float = Field(gt=0.0)
    """`h`, m, in the bending plane."""
    cover_pos: float = Field(gt=0.0)
    """Distance from the positive face to the axis of its reinforcement layer, m."""
    cover_neg: float = Field(gt=0.0)
    """Same for the negative face, m."""

    @model_validator(mode="after")
    def _layers_inside(self) -> Rectangle:
        if self.cover_pos + self.cover_neg >= self.depth:
            message = "les deux lits d'armatures se croisent : enrobages >= profondeur"
            raise ValueError(message)
        return self

    @property
    def area(self) -> float:
        return self.width * self.depth


class Design(BaseModel):
    """Reinforcement found for one `(n_tension, m)` couple."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_pos: float
    """Area on the positive face, m2 (zero when none is needed)."""
    as_neg: float
    as_neg_needed_in_compression: bool = False
    """True when the solution puts steel in compression (compression reinforcement)."""
    feasible: bool = True
    pivot: Literal["A", "B", "C", "none"] = "none"
    neutral_axis_depth: float | None = None
    """m, from the compressed extreme fibre (`None` for a fully tensioned section)."""
    note: str = ""

    @property
    def total(self) -> float:
        return self.as_pos + self.as_neg
