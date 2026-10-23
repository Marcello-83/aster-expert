"""Contrôle post-lot 54 (B54): readers and checks shared by the scripts of the control
(`scripts/controle_lot54_deplacements.py`, `scripts/champ_combine_lot54.py`).

No new rule: the combination labels and the event coefficients are those of lot 54
(`deplacements_combinaisons.csv`, `evenements.csv`), read back as they were delivered.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any

import numpy as np

LOT54 = Path("/media/sf_partage/echanges/lot54/pontons_alu_01/B54")


def build_state(execution: Path, mesh: Path, comm: Path) -> dict[str, Any]:
    """The `etat.json` entry of B54 that `exports_lot54.load` needs."""
    return {
        "B54": {
            "execution": {"execution_dir": str(execution)},
            "maillage": {
                "med": str(mesh),
                "med_sha256": hashlib.sha256(mesh.read_bytes()).hexdigest(),
            },
            "comm": str(comm),
        }
    }


def rows_of(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def compare_csv(a: Path, b: Path) -> dict[str, Any]:
    ra, rb = rows_of(a), rows_of(b)
    if len(ra) != len(rb) or (ra and ra[0].keys() != rb[0].keys()):
        return {"identique": False, "motif": "lignes ou colonnes différentes"}
    worst = 0.0
    text_gap = 0
    for x, y in zip(ra, rb, strict=True):
        for k, vx in x.items():
            vy = y[k]
            try:
                fx, fy = float(vx), float(vy)
            except ValueError:
                text_gap += vx != vy
                continue
            scale = max(abs(fx), abs(fy), 1e-300)
            worst = max(worst, abs(fx - fy) / scale if scale > 1e-12 else abs(fx - fy))
    return {
        "lignes": len(ra),
        "ecart_relatif_max": worst,
        "ecarts_texte": int(text_gap),
        "identique": worst <= 1e-9 and text_gap == 0,
    }


def compare_npz(a: Path, b: Path) -> dict[str, Any]:
    with np.load(a) as x, np.load(b) as y:
        if set(x.files) != set(y.files):
            return {"identique": False, "motif": "tableaux différents"}
        worst = 0.0
        for k in x.files:
            if x[k].shape != y[k].shape:
                return {"identique": False, "motif": f"forme de {k}"}
            if x[k].dtype.kind in "fc":
                scale = max(float(np.abs(y[k]).max()), 1e-300)
                worst = max(worst, float(np.abs(x[k] - y[k]).max()) / scale)
            elif not np.array_equal(x[k], y[k]):
                return {"identique": False, "motif": f"valeurs de {k}"}
    return {"ecart_relatif_max_a_la_valeur_max": worst, "identique": worst <= 1e-9}


def event_table(path: Path) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}
    for r in rows_of(path):
        table.setdefault(r["evenement"], {})[r["cas"]] = float(r["coefficient"])
    return table


def modules_of(table: dict[str, dict[str, float]], family: str) -> dict[str, str]:
    """`Q` or `QD` -> {"M0": "Q_M0", ...}."""
    return {case.rsplit("_", 1)[1]: case for case in table.get(family, {})}


def label_coefficients(
    label: str, table: dict[str, dict[str, float]]
) -> tuple[str, dict[str, float]]:
    """`ETAT: ev×k + Q[M0+M1]×k + ...` -> (state, {unit case: coefficient})."""
    state, _, body = label.partition(": ")
    coefs: dict[str, float] = {}
    for term in body.split(" + "):
        name, _, factor = term.rpartition("×")
        k = float(factor)
        m = re.fullmatch(r"(QD|Q)\[(.+)\]", name)
        if m:
            family, mods = m.groups()
            for mod in mods.split("+"):
                case = modules_of(table, family)[mod]
                coefs[case] = coefs.get(case, 0.0) + k * table[family][case]
        else:
            for case, c in table[name].items():
                coefs[case] = coefs.get(case, 0.0) + k * c
    return state, coefs


def read_complete(path: Path) -> dict[tuple[str, str], tuple[float, ...]]:
    """(point, case) -> components, in mm and mrad."""
    out: dict[tuple[str, str], tuple[float, ...]] = {}
    for r in rows_of(path):
        out[(r["point"], r["cas"])] = tuple(
            float(r[c])
            for c in ("DX_mm", "DY_mm", "DZ_mm", "DRX_mrad", "DRY_mrad", "DRZ_mrad")
        )
    return out


def recombination(
    complete: Path, combos: Path, events: Path, targets: list[tuple[str, str, str]]
) -> list[dict[str, Any]]:
    unit = read_complete(complete)
    table = event_table(events)
    comp = {"DX": 0, "DY": 1, "DZ": 2}
    rows = rows_of(combos)
    report: list[dict[str, Any]] = []
    for point, direction, limit in targets:
        row = next(
            r
            for r in rows
            if r["point"] == point
            and r["direction"] == direction
            and r["etat_limite"] == limit
        )
        for column in ("total", "total_hors_T"):
            for side in ("max", "min"):
                label = row[f"{column}_combinaison_{side}"]
                if not label:
                    continue
                _, coefs = label_coefficients(label, table)
                value = sum(
                    c * unit[(point, case)][comp[direction]]
                    for case, c in coefs.items()
                )
                expected = float(row[f"{column}_{side}"])
                report.append(
                    {
                        "point": point,
                        "direction": direction,
                        "etat_limite": limit,
                        "grandeur": f"{column}_{side}",
                        "recombine_mm": value,
                        "csv_mm": expected,
                        "ecart_mm": value - expected,
                    }
                )
    return report


__all__ = [
    "LOT54",
    "build_state",
    "compare_csv",
    "compare_npz",
    "event_table",
    "label_coefficients",
    "read_complete",
    "recombination",
    "rows_of",
]
