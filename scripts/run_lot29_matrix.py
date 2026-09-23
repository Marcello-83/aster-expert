"""Runs the lot 29 reproducer matrix (one factor at a time, `docs/essais_lot29.md`).

Each case is built (`build_lot29_repro.build_case`) and executed with
`aster-expert run` (level C, real Docker/Code_Aster execution -- this project
never simulates or predicts an execution result). The outcome (`status`,
`diag`, duration) and a short excerpt of the first `<F>` block in the `.mess`
(if any) are collected into `results.json`, never overwritten silently: an
existing entry for the same label is only replaced by an actual new run.

Usage: python scripts/run_lot29_matrix.py [--only LABEL ...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_lot29_repro import DEFAULT_OUTPUT_DIR, build_case  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = DEFAULT_OUTPUT_DIR / "results.json"


@dataclass(frozen=True)
class Case:
    label: str
    n_springs: int
    stiffness_n_per_m: float
    symmetry: bool
    redundant_bc: bool
    note: str


# The lot 29 matrix, one factor changed at a time from the A0 baseline.
# N_MID/N_HIGH are decided during Etape 1 (H3) and frozen here once known --
# see docs/essais_lot29.md for the reasoning.
N_MID = 1000
N_HIGH = 10000
K_REAL = 1.0e6
K_LOW = K_REAL * 1.0e-4
K_HIGH = K_REAL * 1.0e4

CASES: list[Case] = [
    Case("A0_n0", 0, K_REAL, False, False, "baseline, calibration"),
    Case("A1_n10", 10, K_REAL, False, False, "H3: N petit"),
    Case("A2_n1000", N_MID, K_REAL, False, False, "H3: N moyen"),
    Case("A3_n10000", N_HIGH, K_REAL, False, False, "H3: N grand"),
    Case("B1_klow", N_HIGH, K_LOW, False, False, "H2: raideur / 1e4"),
    Case("B2_khigh", N_HIGH, K_HIGH, False, False, "H2: raideur x 1e4"),
    Case("C0_sym_n0", 0, K_REAL, True, False, "H1(3): symetrie seule"),
    Case("C1_sym_n", N_HIGH, K_REAL, True, False, "H1(3): symetrie + ressorts"),
    Case("D0_sym_redundant", 0, K_REAL, True, True, "H1(4): BC redondante (bug connu)"),
]


def _mess_excerpt(mess_path: str | None, *, max_lines: int = 40) -> str | None:
    if not mess_path:
        return None
    path = Path(mess_path)
    if not path.is_file():
        return None
    text = path.read_text("utf-8", errors="replace")
    match = re.search(r"║ <F> <\S+>.*?╚.*?╝", text, flags=re.S)
    if not match:
        return None
    lines = match.group(0).splitlines()
    return "\n".join(lines[:max_lines])


def run_case(case: Case) -> dict:
    meta = build_case(
        case.label,
        n_springs=case.n_springs,
        stiffness_n_per_m=case.stiffness_n_per_m,
        symmetry=case.symmetry,
        redundant_bc=case.redundant_bc,
        output_dir=DEFAULT_OUTPUT_DIR,
    )
    comm_path = DEFAULT_OUTPUT_DIR / case.label / "repro.comm"
    start = time.time()
    proc = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "aster-expert"), "run", str(comm_path)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    wall_s = time.time() - start
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {"status": "parse_error", "diag": None, "mess_path": None}

    excerpt = _mess_excerpt(report.get("mess_path"))
    return {
        "label": case.label,
        "note": case.note,
        "n_springs": case.n_springs,
        "stiffness_n_per_m": case.stiffness_n_per_m,
        "symmetry": case.symmetry,
        "redundant_bc": case.redundant_bc,
        "status": report.get("status"),
        "diag": report.get("diag"),
        "duration_s": report.get("duration_s"),
        "wall_s": wall_s,
        "work_dir": report.get("work_dir"),
        "mess_excerpt": excerpt,
        "mesh_counts": {
            "n_layers": meta["mesh"]["n_layers"],
            "n_quads": meta["mesh"]["n_quads"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args(argv)

    existing: dict[str, dict] = {}
    if RESULTS_PATH.is_file():
        existing = {r["label"]: r for r in json.loads(RESULTS_PATH.read_text("utf-8"))}

    cases = [c for c in CASES if args.only is None or c.label in args.only]
    for case in cases:
        print(f"--- {case.label} ({case.note}) ---", file=sys.stderr)
        result = run_case(case)
        existing[case.label] = result
        print(json.dumps(result, indent=2, ensure_ascii=False))
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(
            json.dumps(list(existing.values()), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
