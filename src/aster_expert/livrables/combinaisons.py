"""Combinations of the deliverables (lot 49), with their moving loads.

A combination of the deliverables is `Σ coefficient × case` over its fixed cases, plus,
when it holds a moving load, `coefficient × one position` enveloped over the positions
of that load: its value at each point is the max (and the min) over the positions, and
the position that gives it is kept (PAT-012 : « enveloppées et combinées sur le poste à
partir du MED »).

The combinations come either from the `combinations` section of `projet.yaml`
(`declarees`, EN 1990 families built by `aster_expert.combinaisons.enumeration`) or
from an extension of the project returning a list of dicts of this module's schema.
Nothing is computed here but the description: the arithmetic is in
`aster_expert.livrables.champs`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aster_expert.combinaisons.enumeration import enumerate_combinations
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError


class GenericCombination(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    family: str
    fixed: dict[str, float]
    """Elementary case -> coefficient."""
    mobile_coefficient: float = 0.0
    mobile_cases: tuple[str, ...] = ()
    """Positions of the moving load enveloped in this combination."""
    mobile_label: str | None = None
    """What the moving load is (« TS bord de voie »)."""
    definition: str = ""
    """The combination in words, as the source gives it (shown in the workbook)."""

    @model_validator(mode="after")
    def _mobile(self) -> GenericCombination:
        if bool(self.mobile_cases) != (self.mobile_coefficient != 0.0):
            message = (
                f"combinaison {self.name} : positions mobiles et coefficient vont "
                "ensemble"
            )
            raise ValueError(message)
        return self

    def cases(self) -> set[str]:
        return set(self.fixed) | set(self.mobile_cases)


class CombinationSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    combinations: tuple[GenericCombination, ...] = Field(min_length=1)
    source: str

    def mobile_cases(self) -> set[str]:
        return {c for comb in self.combinations for c in comb.mobile_cases}


def combinations_of(ctx: ProjectContext) -> CombinationSet | None:
    """The combinations the deliverables declare; `None` when they are declared not
    relevant."""
    section = ctx.declaration.deliverables
    if section is None or section.combinations is None:
        return None
    if section.combinations == "declarees":
        declared = ctx.declaration.combinations
        if declared is None:
            message = (
                "livrables : combinations: declarees, mais projet.yaml n'a pas de "
                "section `combinations`"
            )
            raise ProjectError(message)
        combos = [
            GenericCombination(
                name=c.name,
                family=c.family,
                fixed=dict(c.coefficients),
                definition=" + ".join(f"{v:g}·{k}" for k, v in c.coefficients.items()),
            )
            for c in enumerate_combinations(declared, ctx.number)
        ]
        return CombinationSet(
            combinations=tuple(combos),
            source="section combinations de projet.yaml (EN 1990, aster_expert."
            "combinaisons.enumeration)",
        )
    raw: list[dict[str, Any]] = ctx.extension(section.combinations)(ctx)
    return CombinationSet(
        combinations=tuple(GenericCombination.model_validate(r) for r in raw),
        source=f"extension {section.combinations}",
    )


__all__ = ["CombinationSet", "GenericCombination", "combinations_of"]
