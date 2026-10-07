"""Tables of the results note read from the files of the package (lot 45).

`resolve_table` is the one place where a declared table (`NoteTable`) is turned into
rows of values; the note writes its cells from it, and the check of the notes calls it
again on the same files to compare each displayed number to its source. Nothing is
computed: a cell is a value of a CSV or JSON file, shown with 6 significant digits
unless the declaration gives a format.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aster_expert.arrondis import RoundingTable, format_value, load_table
from aster_expert.notes.formats import EMPTY, cell
from aster_expert.projet.declaration import NoteColumn, NoteTable
from aster_expert.projet.errors import ProjectError


@dataclass(frozen=True)
class Frame:
    """An element reached while following a path, with the elements enclosing it."""

    value: Any
    chain: tuple[tuple[Any, str], ...] = ()
    """(element, key) of each `*` already expanded, outermost first."""
    key: str = ""
    """Key of `value` in its own container (a dict key, or a list index)."""


@dataclass
class ResolvedTable:
    headers: list[str]
    values: list[list[Any]]
    """Raw values (numbers stay numbers), one list per displayed row."""
    cells: list[list[str]]
    source_rows: int
    shown_rows: int
    step: int
    truncated: bool = False
    columns: tuple[NoteColumn, ...] = field(default_factory=tuple)


def _step_into(value: Any, token: str, where: str) -> Any:
    if isinstance(value, dict):
        if token not in value:
            message = f"{where} : clé « {token} » absente (clés : {sorted(value)[:8]})"
            raise ProjectError(message)
        return value[token]
    if isinstance(value, list) and token.isdigit() and int(token) < len(value):
        return value[int(token)]
    message = f"{where} : « {token} » n'est pas atteignable"
    raise ProjectError(message)


def _frames(data: Any, path: str | None, where: str) -> list[Frame]:
    frames = [Frame(data)]
    if not path:
        return frames
    for token in path.split("."):
        nxt: list[Frame] = []
        for frame in frames:
            if token == "*":
                items = (
                    list(frame.value.items())
                    if isinstance(frame.value, dict)
                    else [(str(i), v) for i, v in enumerate(frame.value)]
                )
                for key, element in items:
                    nxt.append(Frame(element, (*frame.chain, (element, key)), key))
            else:
                nxt.append(
                    Frame(_step_into(frame.value, token, where), frame.chain, token)
                )
        frames = nxt
    return frames


def _row_items(
    frames: list[Frame], where: str
) -> list[tuple[Any, str, tuple[tuple[Any, str], ...]]]:
    rows = []
    for frame in frames:
        value = frame.value
        if isinstance(value, dict):
            rows += [(v, k, frame.chain) for k, v in value.items()]
        elif isinstance(value, list):
            rows += [(v, str(i), frame.chain) for i, v in enumerate(value)]
        else:
            message = f"{where} : le chemin des lignes ne désigne ni liste ni dict"
            raise ProjectError(message)
    return rows


def read_value(
    row: Any, key: str, chain: tuple[tuple[Any, str], ...], path: str, where: str
) -> Any:
    """The value of `path` for a row: `$key` is the key of the row, `^name` reads the
    enclosing element, `^$key` its key."""
    if path == "$key":
        return key
    up = len(path) - len(path.lstrip("^"))
    if up:
        if up > len(chain):
            message = f"{where} : « {path} » remonte plus haut que la ligne"
            raise ProjectError(message)
        element, parent_key = chain[-up]
        rest = path[up:]
        if rest == "$key":
            return parent_key
        current = element
    else:
        rest = path
        current = row
    for token in rest.split("."):
        current = _step_into(current, token, where)
    return current


def _rounding_table() -> RoundingTable:
    """The repository's own rounding table (`config/arrondis.yaml`)."""
    return load_table(Path(__file__).resolve().parents[3])


def _format(value: Any, column: NoteColumn) -> str:
    if (
        column.format is not None
        and isinstance(value, int | float)
        and not isinstance(value, bool)
    ):
        return column.format.format(value).replace(".", ",")
    if (
        column.unit is not None
        and isinstance(value, int | float)
        and not isinstance(value, bool)
    ):
        return format_value(value, column.unit, _rounding_table(), decimal_comma=True)
    return cell(value)


def resolve_table(package_dir: Path, table: NoteTable) -> ResolvedTable:
    """The rows of a declared table, from its file in the package."""
    path = package_dir / table.source
    where = f"tableau « {table.title} » ({table.source})"
    if not path.is_file():
        message = f"{where} : fichier absent du paquet"
        raise ProjectError(message)
    headers = [c.header for c in table.columns]
    raw_rows: list[tuple[Any, str, tuple[tuple[Any, str], ...]]]
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as stream:
            raw_rows = [
                (row, str(i), ()) for i, row in enumerate(csv.DictReader(stream))
            ]
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_rows = _row_items(_frames(data, table.rows, where), where)
    selected = raw_rows[:: table.step]
    truncated = len(selected) > table.max_rows
    selected = selected[: table.max_rows]
    values: list[list[Any]] = []
    cells: list[list[str]] = []
    for row, key, chain in selected:
        line: list[Any] = []
        for column in table.columns:
            if path.suffix.lower() == ".csv":
                text = row.get(column.path)
                if text is None:
                    message = f"{where} : colonne « {column.path} » absente"
                    raise ProjectError(message)
                try:
                    line.append(float(text))
                except ValueError:
                    line.append(text)
            else:
                line.append(read_value(row, key, chain, column.path, where))
        values.append(line)
        cells.append([_format(v, c) for v, c in zip(line, table.columns, strict=True)])
    return ResolvedTable(
        headers=headers,
        values=values,
        cells=cells,
        source_rows=len(raw_rows),
        shown_rows=len(selected),
        step=table.step,
        truncated=truncated,
        columns=table.columns,
    )


def table_note(resolved: ResolvedTable) -> str | None:
    """What the note says when the table does not show every row of its file."""
    if resolved.shown_rows >= resolved.source_rows:
        return None
    parts = [f"{resolved.shown_rows} lignes sur {resolved.source_rows}"]
    if resolved.step > 1:
        parts.append(f"une ligne sur {resolved.step}")
    if resolved.truncated:
        parts.append("tronqué au plafond du tableau")
    return " ; ".join(parts) + " (le fichier complet est dans le paquet de résultats)"


__all__ = [
    "EMPTY",
    "Frame",
    "ResolvedTable",
    "read_value",
    "resolve_table",
    "table_note",
]
