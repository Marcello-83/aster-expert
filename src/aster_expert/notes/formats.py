"""Text of numbers and dates in the notes (lot 45): French notation, no rounding of
a value that comes from a data file."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

EMPTY = "—"


def fr_number(value: float | int) -> str:
    """A number as written in the source (shortest exact `repr`), decimal comma.

    `parse_number` reads it back to the very same float: the check of the notes
    relies on it."""
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, int):
        return str(value)
    return repr(float(value)).replace(".", ",")


def parse_number(text: str) -> float | None:
    """The number written in `text` (decimal comma, no thousands separator), or
    `None` when it is not a plain number."""
    cleaned = text.strip().replace(",", ".").replace("−", "-")
    try:
        return float(cleaned)
    except ValueError:
        return None


def fr_significant(value: float | int, digits: int = 6) -> str:
    """A computed value shown with `digits` significant digits (`%g`), decimal comma.

    An integer stays whole. The precision shown is the tolerance of the
    comparison with the source (`displayed_tolerance`)."""
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}g}".replace(".", ",")


def displayed_tolerance(text: str) -> float:
    """Half a unit of the last significant digit displayed in `text`, relative to
    the value (the rounding a `%g` display can introduce)."""
    cleaned = text.strip().replace(",", ".").replace("−", "-").lower()
    mantissa = cleaned.split("e")[0].lstrip("+-")
    digits = [c for c in mantissa if c.isdigit()]
    significant = len("".join(digits).lstrip("0")) or 1
    tolerance: float = 0.5 * 10 ** (1 - significant)
    return tolerance


def fr_date(value: date | datetime) -> str:
    return (
        value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    )


def fr_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def cell(value: Any) -> str:
    """A generic scalar of a JSON or CSV file as a table cell."""
    if value is None:
        return EMPTY
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, int | float):
        return fr_significant(value)
    return str(value)


__all__ = [
    "EMPTY",
    "cell",
    "displayed_tolerance",
    "fr_date",
    "fr_datetime",
    "fr_number",
    "fr_significant",
    "parse_number",
]
