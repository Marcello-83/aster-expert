"""Apply the lot 26 criterion (`docs/essais_lot26.md`) to the Code_Aster listings.

Reads `data/examples/lot26_essais/mess/mess_<case>.txt` (copies of the `fort.6` of
each run) and checks, against the analytic expectations of
`scripts/build_lot26_essais.py`:

* the mesh as read by Code_Aster (`LIRE_MAILLAGE INFO=2`): number of nodes,
  cells per type, cardinality of every cell group, against `invariants.yaml`;
* the `POST_ELEM(MASS_INER)` mass of every group (its area or length, RHO = 1),
  relative tolerance 1e-6;
* no alarm in the listing.

Writes `analyse.json`. Usage: python scripts/analyze_lot26_essais.py [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_lot26_essais as l26  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "examples" / "lot26_essais"
DEFAULT_OUTPUT = DIR / "analyse.json"
REL_TOL = 1e-6


def parse_listing(text: str) -> dict[str, Any]:
    nodes = int(re.search(r"^NOMBRE DE NOEUDS\s+(\d+)", text, re.M).group(1))  # type: ignore[union-attr]
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("NOMBRE DE MAILLES"))
    cells: dict[str, int] = {}
    i = start + 1
    while lines[i].strip():
        name, count = lines[i].split()
        cells[name] = int(count)
        i += 1
    start = next(
        i for i, ln in enumerate(lines) if ln.startswith("NOMBRE DE GROUPES DE MAILLES")
    )
    groups: dict[str, int] = {}
    i = start + 1
    while i < len(lines) and lines[i].strip():
        name, count = lines[i].split()
        groups[name] = int(count)
        i += 1
    masses: dict[str, float] = {}
    header = next(i for i, ln in enumerate(lines) if ln.startswith("LIEU  "))
    for row in lines[header + 1 :]:
        fields = row.split()
        if len(fields) < 3 or fields[1] != "GROUP_MA":
            break
        masses[fields[0]] = float(fields[2])
    alarms = [ln.strip() for ln in lines if ln.lstrip().startswith("<A>")]
    return {
        "nodes": nodes,
        "cells": cells,
        "groups": groups,
        "masses": masses,
        "alarms": alarms,
    }


def analyze_case(case: str, directory: str) -> dict[str, Any]:
    listing = parse_listing((DIR / "mess" / f"mess_{case}.txt").read_text("utf-8"))
    invariants = yaml.safe_load(
        (DIR / directory / "invariants.yaml").read_text("utf-8")
    )
    expected_masses = {g: m for g, _, m in l26.aster_groups()[case]}
    group_counts = {
        g["name"]: g["count"]
        for g in invariants["groups"]
        if g["name"] in expected_masses
    }
    mass_errors = {
        g: listing["masses"][g] / expected - 1.0
        for g, expected in expected_masses.items()
    }
    return {
        **listing,
        "expected_nodes": invariants["counts"]["nodes"],
        "expected_cells": invariants["counts"]["cells"],
        "expected_group_counts": group_counts,
        "expected_masses": expected_masses,
        "mass_relative_errors": mass_errors,
        "verdict": {
            "nodes": listing["nodes"] == invariants["counts"]["nodes"],
            "cells": listing["cells"] == invariants["counts"]["cells"],
            "group_cardinalities": all(
                listing["groups"].get(g) == n for g, n in group_counts.items()
            ),
            "masses_within_1e-6": all(abs(e) <= REL_TOL for e in mass_errors.values()),
            "no_alarm": not listing["alarms"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = {
        case: analyze_case(case, directory)
        for case, directory in l26.ASTER_DIRS.items()
    }
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
