"""`IMPR_TABLE` tables of a `.mess`, found by the title of their first row
(`POST_RELEVE_T/INTITULE`), for the level D controls (lot 41).

Same reading as the lot 33 to 37 analyses of the first project (moved here from
its scripts, byte for byte in behaviour): a table starts after a `##...ASTER`
marker line, its header is the next line, its rows run to the first blank or
`#` line; numbers are the trailing cells written `d.dddE±dd`.
"""

from __future__ import annotations

import re
from typing import Any

_NUM = re.compile(r"^[-+]?\d+\.\d+E[-+]\d+$")

Record = dict[str, "float | str"]


def parse_tables(text: str) -> list[dict[str, Any]]:
    """Every `IMPR_TABLE` table: header names and rows split in cells."""
    lines = text.splitlines()
    tables = []
    for i, line in enumerate(lines):
        if not line.startswith("##ASTER") or i + 1 >= len(lines):
            continue
        header = lines[i + 1].split()
        rows: list[list[str]] = []
        for row in lines[i + 2 :]:
            if not row.strip() or row.startswith("#"):
                break
            rows.append(row.split())
        tables.append({"header": header, "rows": rows})
    return tables


def table_records(table: dict[str, Any]) -> list[Record]:
    """Rows as records: the trailing numeric cells under the last header names,
    the leading text cells joined in `_head`."""
    header = table["header"]
    records: list[Record] = []
    for cells in table["rows"]:
        numeric: list[float] = []
        for cell in reversed(cells):
            if _NUM.match(cell):
                numeric.append(float(cell))
            else:
                break
        numeric.reverse()
        names = header[len(header) - len(numeric) :]
        record: Record = dict(zip(names, numeric, strict=True))
        record["_head"] = " ".join(cells[: len(cells) - len(numeric)])
        records.append(record)
    return records


def find_table(text: str, needle: str) -> list[Record]:
    """Records of the first table whose first row names `needle` in its first
    four cells (the `INTITULE`). A missing table is a `KeyError`."""
    for table in parse_tables(text):
        if table["rows"] and needle in table["rows"][0][:4]:
            return table_records(table)
    message = f"table introuvable : {needle}"
    raise KeyError(message)


class TableIndex:
    """The tables of one listing, parsed once (a `.mess` of the full model runs
    to 1.4 million lines, and each case reads a dozen tables)."""

    def __init__(self, text: str) -> None:
        self._tables = parse_tables(text)

    def find(self, needle: str) -> list[Record]:
        for table in self._tables:
            if table["rows"] and needle in table["rows"][0][:4]:
                return table_records(table)
        message = f"table introuvable : {needle}"
        raise KeyError(message)


__all__ = ["Record", "TableIndex", "find_table", "parse_tables", "table_records"]
