"""Lecture des tables `IMPR_TABLE` d'un `.mess` Code_Aster (lot 35).

Deux familles de tables portent les grandeurs de la synthèse :

- `POST_RELEVE_T` (déplacements, réactions, ressorts) : la première colonne est
  l'`INTITULE` demandé, les lignes commencent par lui ;
- `CREA_TABLE` (efforts généralisés) : imprimée avec un `TITRE`, que le `.mess`
  écrit dans le marqueur de table (`##<titre>ASTER`) ; la première colonne est le
  nom du concept résultat.

Le fichier peut dépasser 100 Mo : la lecture est paresseuse (une table à la fois),
et `read_tables` ne garde que celles que l'appelant demande.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

Record = dict[str, "float | str"]

_MARKER = re.compile(r"^##(?P<title>\S*?)ASTER\b")
_NUMBER = re.compile(r"^[-+]?\d+\.\d+E[-+]\d+$")


class TableError(Exception):
    """Table absente ou illisible."""


def _convert(cell: str) -> float | str:
    return float(cell) if _NUMBER.match(cell) else cell


def iter_tables(
    path: Path, wanted: set[str] | None = None
) -> Iterator[tuple[str, list[str], list[list[str]]]]:
    """`(nom, en-têtes, lignes)` des tables imprimées, dans l'ordre du fichier.
    `nom` est le titre (`CREA_TABLE`) ou, à défaut, l'intitulé (première cellule de la
    première ligne, `POST_RELEVE_T`). Avec `wanted`, seules ces tables sont découpées
    en cellules : les autres, souvent très longues (un ligne par nœud du maillage),
    sont sautées ligne à ligne sans analyse."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            marker = _MARKER.match(line)
            if marker is None:
                continue
            title = marker.group("title")
            header = handle.readline().split()
            first = handle.readline()
            cells = first.split()
            name = title or (cells[0] if cells else "")
            if wanted is not None and name not in wanted:
                continue
            rows = [cells] if cells else []
            for row in handle:
                if not row.strip() or row.startswith("#"):
                    break
                rows.append(row.split())
            yield name, header, rows


def records(header: list[str], rows: list[list[str]]) -> list[Record]:
    """Une ligne = un dictionnaire colonne -> valeur. Une ligne dont le nombre de
    cellules diffère de celui des en-têtes (cellule vide) est alignée par la fin, sur
    ses cellules numériques -- jamais devinée autrement."""
    out: list[Record] = []
    for cells in rows:
        if len(cells) == len(header):
            out.append({h: _convert(c) for h, c in zip(header, cells, strict=True)})
            continue
        numeric: list[float] = []
        for cell in reversed(cells):
            if _NUMBER.match(cell):
                numeric.append(float(cell))
            else:
                break
        numeric.reverse()
        names = header[len(header) - len(numeric) :]
        record: Record = dict(zip(names, numeric, strict=True))
        record["_head"] = " ".join(cells[: len(cells) - len(numeric)])
        out.append(record)
    return out


def read_tables(path: Path, wanted: Iterable[str]) -> dict[str, list[Record]]:
    """Les tables dont le titre (`CREA_TABLE`) ou l'intitulé (`POST_RELEVE_T`, première
    cellule de la première ligne) est dans `wanted`. Une table demandée mais absente
    du fichier est une erreur (`TableError`), jamais une table vide."""
    remaining = set(wanted)
    found: dict[str, list[Record]] = {}
    for name, header, rows in iter_tables(path, set(remaining)):
        if name in remaining:
            found[name] = records(header, rows)
            remaining.discard(name)
        if not remaining:
            break
    if remaining:
        message = f"table(s) absente(s) du .mess : {', '.join(sorted(remaining))}"
        raise TableError(message)
    return found
