"""Lot 47 quater -- the two transcription gaps found by the supervisor in the source.

Declared variants, never the reference (E1 to E19 unchanged):

- **H1, concrete plug in the pile section.** The legend of figure 66 of the source
  separates « Pieu (att. élevée-béton) », « Pieu (im-béton) », « Pieu (immergé) » and
  « Pieu (sol) »: the Robot model gave the upper segments a steel + plug concrete
  section, which E3 (question Q3) left out. Plug: C35/45 concrete of diameter 0.622 m
  (§ 20.4.1 of the source), from the head down to -0.80 (lot 47 quater instruction of
  MM; E14 reads « de +0.70 à -0.80 » for the reading zone of C3/C4, kept unchanged).
  Section homogenised in steel, n = Es / Ecm with Ecm = 34 GPa (uncracked concrete),
  for A and I; weight of the concrete added (25 kN/m3) through the density of a steel
  material of its own.
- **H2, deck plane at +1.50 instead of +1.30.** Figure 66 carries « +1,50 » at the
  deck and the springs of file 1 start at +1.00 with steps of 0.50 m: the deck, the cap
  beams and the pile heads are at +1.50; the springs stay at their levels (B3); the
  upper B2 segment is prolonged up to the deck node (E3).

The numbers of H1 come from the instruction of the lot (MM), which cites the source;
nothing here is read from a MED or tuned toward the source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from estacade_pieux_01.donnees import LEVEL_PRECISION, DataError, ModelValues, Section

PLUG_DIAMETER = 0.622
"""m, inner diameter of the plug (§ 20.4.1 of the source, lot 47 quater instruction)."""
PLUG_E = 34.0e9
"""Pa, Ecm of the uncracked C35/45 concrete of the plug (lot 47 quater instruction)."""
PLUG_GAMMA = 25.0e3
"""N/m3, unit weight of the plug concrete (lot 47 quater instruction)."""
DECK_LEVEL_H2 = 1.50
"""m NGF, deck plane of H2 (figure 66 of the source, lot 47 quater instruction)."""


def with_deck_level(v: ModelValues, z: float) -> ModelValues:
    """The model values with the deck plane at `z` (H2): the upper segment of B2 starts
    at `z` (E3), springs and lower segments unchanged."""
    first = v.sections[0]
    if z <= first.z_bottom + LEVEL_PRECISION:
        message = f"plan du tablier {z} sous le bas du tronçon {first.name}"
        raise DataError(message)
    above = [s for s in v.springs if s.z > z - LEVEL_PRECISION]
    if above:
        message = f"ressort au-dessus du plan du tablier {z} : {above[0].group}"
        raise DataError(message)
    sections = (replace(first, z_top=z), *v.sections[1:])
    return replace(v, z_mid=z, sections=sections)


@dataclass(frozen=True)
class MixedSection:
    """A B2 segment with the plug, homogenised in steel (H1)."""

    section: Section
    concrete_area: float
    concrete_inertia: float
    ratio: float
    """n = Es / Ecm."""
    area: float
    inertia: float
    density: float
    """kg/m3 of the steel material of the segment: (γs·As + γc·Ac) / (g·A)."""

    @property
    def name(self) -> str:
        return self.section.name

    def equivalent_tube(self) -> tuple[float, float]:
        """(R, EP) of the tube with exactly this area and inertia (CA-057)."""
        return Section(
            name=self.name,
            z_top=self.section.z_top,
            z_bottom=self.section.z_bottom,
            area=self.area,
            inertia=self.inertia,
        ).equivalent_tube()

    def steel_weight_per_length(self, v: ModelValues) -> float:
        return v.gamma_steel * self.section.area

    def concrete_weight_per_length(self) -> float:
        return PLUG_GAMMA * self.concrete_area


def mixed_sections(v: ModelValues) -> tuple[MixedSection, ...]:
    """The segments from the head down to the bottom of the plug (H1)."""
    bottom = v.plug[1]
    if not any(abs(s.z_bottom - bottom) < LEVEL_PRECISION for s in v.sections):
        message = f"le bas du bouchon ({bottom}) n'est pas une limite de tronçon de B2"
        raise DataError(message)
    concrete_area = math.pi * PLUG_DIAMETER**2 / 4.0
    concrete_inertia = math.pi * PLUG_DIAMETER**4 / 64.0
    ratio = v.e_steel / PLUG_E
    out = []
    for s in v.sections:
        if s.z_bottom < bottom - LEVEL_PRECISION:
            continue
        area = s.area + concrete_area / ratio
        inertia = s.inertia + concrete_inertia / ratio
        density = (v.gamma_steel * s.area + PLUG_GAMMA * concrete_area) / (
            v.gravity * area
        )
        out.append(
            MixedSection(
                section=s,
                concrete_area=concrete_area,
                concrete_inertia=concrete_inertia,
                ratio=ratio,
                area=area,
                inertia=inertia,
                density=density,
            )
        )
    return tuple(out)


def plug_concrete_weight(v: ModelValues) -> float:
    """N, weight of the plug concrete of all the piles (H1)."""
    per_pile = sum(
        m.concrete_weight_per_length() * (m.section.z_top - m.section.z_bottom)
        for m in mixed_sections(v)
    )
    return per_pile * len(v.piles())


__all__ = [
    "DECK_LEVEL_H2",
    "PLUG_DIAMETER",
    "PLUG_E",
    "PLUG_GAMMA",
    "MixedSection",
    "mixed_sections",
    "plug_concrete_weight",
    "with_deck_level",
]
