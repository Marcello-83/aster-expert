"""Extract and compare the results of the lot 23 trials from their `.mess` copies.

Reads `data/examples/lot23_essais/mess/mess_<case>.txt` (copies of the `fort.6`
of each run), parses the tables printed by `IMPR_TABLE` and the Gauss-point
listing printed by `IMPR_RESU`, and writes `analyse.json` next to them. No
Code_Aster module is imported and no `.mess` parser of the project is extended:
the tables are the plain text `IMPR_TABLE` writes (CLAUDE.md, "ne pas
réimplémenter").

References (per unit width, cantilever L = 2 m, b = 0.5 m, tip load P = 5 N):
M(x) = P (L - x) / b, Q = P / b, tip deflection P L^3 / (3 D b) with D = 1000.

Usage: python scripts/analyze_lot23_essais.py [--mess-dir PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_lot22_essais as l22  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MESS_DIR = ROOT / "data" / "examples" / "lot23_essais" / "mess"
DEFAULT_OUTPUT = ROOT / "data" / "examples" / "lot23_essais" / "analyse.json"

P = abs(l22.A_LINE_LOAD) * l22.A_WIDTH
L, B = l22.A_LENGTH, l22.A_WIDTH
D_FLEX = l22.A_FLEX["FLEX_L"]
# Stiffness the stress reconstruction of ELAS_COQUE appears to use (deduction,
# tested by D2): MEMB_L * EPAIS^2 / 12.
MEMB_L = l22.A_MEMB["MEMB_L"]

_NUM = re.compile(r"^[-+]?\d+\.\d+E[-+]\d+$")


def moment_ref(x: float) -> float:
    return P * (L - x) / B


def parse_tables(text: str) -> list[dict[str, list[float] | list[str]]]:
    """Every `IMPR_TABLE` table: header names and numeric rows aligned on the last columns."""
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
    return tables  # type: ignore[return-value]


def table_records(table: dict) -> list[dict[str, float | str]]:
    """Rows as dicts : trailing numeric cells are matched to the trailing header names."""
    header = table["header"]
    records = []
    for cells in table["rows"]:
        numeric = []
        for cell in reversed(cells):
            if _NUM.match(cell):
                numeric.append(float(cell))
            else:
                break
        numeric.reverse()
        names = header[len(header) - len(numeric) :]
        records.append(
            {
                **dict(zip(names, numeric, strict=True)),
                "_head": " ".join(cells[: len(cells) - len(numeric)]),
            }
        )
    return records


def find_table(text: str, needle: str) -> list[dict]:
    """Records of the first table whose first data row carries `needle` in its leading cells."""
    for table in parse_tables(text):
        if table["rows"] and needle in table["rows"][0][:4]:
            return table_records(table)
    raise KeyError(needle)


def sief_elga(text: str) -> dict[int, list[dict[str, float]]]:
    """Gauss-point stress listing of `IMPR_RESU` : cell id -> rows (point, sub-point, SIXX...)."""
    out: dict[int, list[dict[str, float]]] = {}
    started = False
    names: list[str] = []
    for line in text.splitlines():
        if "SIEF_ELGA" in line and "CHAMP PAR ELEMENT" in line:
            started = True
            continue
        if not started:
            continue
        if line.startswith("|      MAILLE"):
            names = [c.strip() for c in line.strip("|").split("|")]
            continue
        if line.startswith("|") and names:
            cells = [c.strip() for c in line.strip("|").split("|")]
            row = {n: float(v) for n, v in zip(names[1:], cells[1:], strict=False)}
            out.setdefault(int(cells[0]), []).append(row)
        elif names and out and not line.startswith("|"):
            break
    return out


def _stats(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}


def strip_case(text: str, epais: float) -> dict[str, object]:
    """Comparisons of one D1/D2/D3 case (cantilever strip, ELAS_COQUE)."""
    depl = find_table(text, "DEPL")
    tip = [r["DZ"] for r in depl if abs(r["COOR_X"] - L) < 1e-9]
    mid = [r["DZ"] for r in depl if abs(r["COOR_X"] - L / 2) < 1e-9]
    out: dict[str, object] = {
        "epais": epais,
        "deflection_tip": _stats(tip),
        "deflection_mid": _stats(mid),
        "deflection_tip_ref": P * L**3 / (3 * D_FLEX * B),
    }
    for name in ("EFGE_ELNO", "EFGE_NOEU"):
        rec = find_table(text, name)
        by_x: dict[str, dict[str, list[float]]] = {}
        for label, x in (("x0", 0.0), ("x_mid", L / 2)):
            pts = [r for r in rec if abs(r["COOR_X"] - x) < 1e-9]
            by_x[label] = {
                c: [r[c] for r in pts] for c in ("MXX", "QX", "NXX", "MYY", "MXY", "QY")
            }
        worst = max(abs(r["MXX"] - moment_ref(r["COOR_X"])) for r in rec)
        parasitic = max(
            max(abs(r[c]) for r in rec)
            for c in ("NXX", "NYY", "NXY", "MYY", "MXY", "QY")
        )
        out[name] = {
            "MXX_x0": _stats(by_x["x0"]["MXX"]),
            "MXX_x0_ref": moment_ref(0.0),
            "QX_x0": _stats(by_x["x0"]["QX"]),
            "MXX_mid": _stats(by_x["x_mid"]["MXX"]),
            "MXX_mid_ref": moment_ref(L / 2),
            "QX_mid": _stats(by_x["x_mid"]["QX"]),
            "Q_ref_abs": P / B,
            "max_abs_MXX_error_all_points": worst,
            "max_abs_other_components": parasitic,
            "n_points": len(rec),
        }
    # Gauss points : cell-mean stress on the upper skin -> equivalent moment.
    stress = sief_elga(text)
    centres = _cell_centres(find_table(text, "EFGE_ELNO"))
    ratios = []
    for cell, rows in stress.items():
        sup = [r["SIXX"] for r in rows if r["SOUS_POINT"] == 3.0]
        if not sup:
            continue
        m_eq = (sum(sup) / len(sup)) * epais**2 / 6.0
        ratios.append(m_eq / moment_ref(centres[cell]))
    out["SIEF_ELGA"] = {
        "sixx_upper_skin_first_cell": next(
            r["SIXX"]
            for r in stress[min(stress)]
            if r["SOUS_POINT"] == 3.0 and r["POINT"] == 1.0
        ),
        "M_equivalent_over_M_ref": _stats(ratios),
        "n_cells": len(ratios),
        "sixx_upper_skin_cell_mean_first_cell": _first_cell_mean(stress),
    }
    for label, name in (
        ("REAC_NODA_clamp", "REAC_NODA_ENCASTREMENT"),
        ("FORC_NODA_clamp", "FORC_NODA_ENCASTREMENT"),
        ("FORC_NODA_all_nodes", "FORC_NODA_TOUS"),
    ):
        out[label] = _resultant(text, name)
    return out


def _first_cell_mean(stress: dict[int, list[dict[str, float]]]) -> float:
    rows = stress[min(stress)]
    sup = [r["SIXX"] for r in rows if r["SOUS_POINT"] == 3.0]
    return sum(sup) / len(sup)


def _cell_centres(elno: list[dict]) -> dict[int, float]:
    cells: dict[int, list[float]] = {}
    for r in elno:
        cells.setdefault(int(str(r["_head"]).split()[3]), []).append(r["COOR_X"])
    return {c: sum(v) / len(v) for c, v in cells.items()}


def _resultant(text: str, title: str) -> dict[str, float]:
    for table in parse_tables(text):
        for row in table["rows"]:
            if row[0].startswith(title[:16]) and len(row) > 4:
                rec = table_records({"header": table["header"], "rows": [row]})[0]
                return {k: v for k, v in rec.items() if k != "_head" and k != "INST"}
    raise KeyError(title)


def plate_case(text: str) -> dict[str, dict[str, float]]:
    out = {}
    for label in ("RESULTANTE_PLAQU",):
        found = []
        for table in parse_tables(text):
            for row in table["rows"]:
                if row[0].startswith(label):
                    found.append(
                        table_records({"header": table["header"], "rows": [row]})[0]
                    )
        out["plate_1"] = {k: v for k, v in found[0].items() if k in ("DZ",)}
        out["plate_2"] = {k: v for k, v in found[1].items() if k in ("DZ",)}
    return out


def mixed_case(text: str, kind: str) -> dict[str, object]:
    depl = find_table(text, "FLECHE_BOUT")
    out: dict[str, object] = {"tip_deflection": _stats([r["DZ"] for r in depl])}
    if kind == "springs":
        out["springs_resultant"] = _resultant(text, "FORC_NODA_RESSOR")
    else:
        out["reac_noda_x2"] = _resultant(text, "REAC_NODA_X2")
        out["reac_noda_all"] = _resultant(text, "REAC_NODA_TOUS")
        out["reac_noda_x0_loaded_end"] = _resultant(text, "REAC_NODA_X0")
    return out


def analyse(mess_dir: Path) -> dict[str, object]:
    def read(name: str) -> str:
        return (mess_dir / f"mess_{name}.txt").read_text(encoding="utf-8")

    texts = {n: read(n) for n in ("d1", "d2a", "d2b", "d3", "d4", "d5a", "d5b")}
    result: dict[str, object] = {
        "alarms": {
            n: "aucune alarme" in t and "<A>" not in t for n, t in texts.items()
        },
        "d1": strip_case(texts["d1"], 0.01),
        "d2a": strip_case(texts["d2a"], 0.02),
        "d2b": strip_case(texts["d2b"], 0.005),
        "d3": strip_case(texts["d3"], 0.01),
        "d4": plate_case(texts["d4"]),
        "d5a": mixed_case(texts["d5a"], "springs"),
        "d5b": mixed_case(texts["d5b"], "clamp"),
        "constants": {
            "P": P,
            "L": L,
            "b": B,
            "FLEX_L": D_FLEX,
            "MEMB_L": MEMB_L,
            "stiffness_ratio_memb_h2_over_12_over_flex": MEMB_L
            * 0.01**2
            / 12.0
            / D_FLEX,
        },
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mess-dir", type=Path, default=DEFAULT_MESS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    args.output.write_text(
        json.dumps(analyse(args.mess_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
