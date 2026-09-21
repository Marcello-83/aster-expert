"""Apply the lot 27 criterion (`docs/essais_lot27.md`) to the Code_Aster listing.

Reads `data/examples/lot27_maillage/mess/mess_lecture.txt` (copy of the `fort.6` of the
run) and checks, against `aster_expected.json` and the invariants: nodes and cells as
read by Code_Aster, cardinality of every cell group, the `POST_ELEM(MASS_INER)` mass of
every group (relative tolerance 1e-6), and the absence of alarm. Writes `analyse.json`.

Usage: python scripts/analyze_lot27_maillage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_lot26_essais import parse_listing  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "examples" / "lot27_maillage"
INVARIANTS = ROOT / "data" / "examples" / "combiwall_mesh_invariants.yaml"
REL_TOL = 1e-6


def main() -> int:
    listing = parse_listing((DIR / "mess" / "mess_lecture.txt").read_text("utf-8"))
    expected = json.loads((DIR / "aster_expected.json").read_text("utf-8"))
    inv = yaml.safe_load(INVARIANTS.read_text("utf-8"))
    counts = {g["name"]: g["count"] for g in inv["groups"] if g["name"] in expected}
    errors = {g: listing["masses"][g] / e["mass"] - 1.0 for g, e in expected.items()}
    result = {
        **listing,
        "expected_nodes": inv["counts"]["nodes"],
        "expected_cells": inv["counts"]["cells"],
        "expected_group_counts": counts,
        "expected_masses": {g: e["mass"] for g, e in expected.items()},
        "mass_relative_errors": errors,
        "max_abs_mass_error": max(abs(v) for v in errors.values()),
        "verdict": {
            "nodes": listing["nodes"] == inv["counts"]["nodes"],
            "cells": listing["cells"] == inv["counts"]["cells"],
            "group_cardinalities": all(
                listing["groups"].get(g) == n for g, n in counts.items()
            ),
            "masses_within_1e-6": all(abs(v) <= REL_TOL for v in errors.values()),
            "no_alarm": not listing["alarms"],
        },
    }
    (DIR / "analyse.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(result["verdict"]),
        result["max_abs_mass_error"],
        listing["nodes"],
        listing["cells"],
        len(listing["masses"]),
        listing["alarms"][:3],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
