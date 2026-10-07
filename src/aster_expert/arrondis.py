"""Rounding of the text outputs by unit (lot 48 bis, MM's remark).

Coordinates such as `2.4999999999` or `0.30000000004` add nothing and hinder
reading and the search of nodes. One table, `config/arrondis.yaml`, gives the
number of decimals per unit; it serves display only. Numerical checks,
combinations and reinforcement always work on the unrounded values; a value
derived from an exact calculation (the radius and the thickness of an equivalent
tube that reproduce A and I) keeps its precision in a `.comm` and carries the
rounded value in a comment (`comm_value`).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

RULES_FILE = Path("config") / "arrondis.yaml"


class ArrondisError(ValueError):
    """The table is unreadable, or a unit is not in it."""


class GridRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    grille_decimales: int = Field(ge=0, le=9)
    epsilon: float = Field(gt=0)
    bloquant: bool

    @property
    def grid(self) -> float:
        return 10.0**-self.grille_decimales


class RoundingTable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int
    decimales: dict[str, int]
    maillage: GridRule

    def decimals(self, unit: str) -> int:
        try:
            return self.decimales[unit]
        except KeyError:
            message = (
                f"unité « {unit} » absente de {RULES_FILE.as_posix()} "
                f"({', '.join(sorted(self.decimales))})"
            )
            raise ArrondisError(message) from None


@lru_cache(maxsize=8)
def _load(path: str) -> RoundingTable:
    file = Path(path)
    if not file.is_file():
        message = f"table d'arrondi introuvable : {file}"
        raise ArrondisError(message)
    return RoundingTable.model_validate(yaml.safe_load(file.read_text("utf-8")))


def load_table(project_root: Path) -> RoundingTable:
    return _load(str(project_root / RULES_FILE))


def round_value(value: float, unit: str, table: RoundingTable) -> float:
    """`value` rounded to the decimals of `unit` (a display value, never an input)."""
    rounded = round(value, table.decimals(unit))
    return 0.0 if rounded == 0 else rounded  # no « -0.0 »


def format_value(
    value: float, unit: str, table: RoundingTable, *, decimal_comma: bool = False
) -> str:
    """`value` as text with the decimals of `unit` (`1.0e-17` of noise prints `0`)."""
    decimals = table.decimals(unit)
    text = f"{round_value(value, unit, table):.{decimals}f}"
    return text.replace(".", ",") if decimal_comma else text


def comm_value(
    value: float, unit: str, table: RoundingTable, *, derived_exact: bool
) -> tuple[str, str | None]:
    """The text of a number written in a `.comm`, and its comment.

    A value derived from an exact calculation keeps its full precision (`repr`) and the
    comment gives the rounded value; any other value is written rounded, without
    comment. The `.comm` never carries a number the calculation did not use.
    """
    if derived_exact:
        shown = format_value(value, unit, table)
        return repr(float(value)), f"{shown} {unit}"
    return repr(round_value(value, unit, table)), None


def off_grid_noise(value: float, rule: GridRule) -> float | None:
    """The distance of `value` to the grid when it is within `epsilon` of a multiple
    without being on it (`2.4999999999` on a 1 mm grid), else None."""
    on_grid = round(value, rule.grille_decimales)
    if value == on_grid:
        return None
    distance = abs(value - on_grid)
    return distance if distance <= rule.epsilon else None


__all__ = [
    "ArrondisError",
    "GridRule",
    "RoundingTable",
    "comm_value",
    "format_value",
    "load_table",
    "off_grid_noise",
    "round_value",
]
