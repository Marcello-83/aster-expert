"""Extract and compare the results of the lot 25 trials (D7) from their `.mess` copies.

Reads `data/examples/lot25_essais/mess/mess_<case>.txt` (copies of the `fort.6`
of each run), parses the `IMPR_TABLE` tables with the helpers of the lot 23
analysis and writes `analyse.json`, applying the criterion of
`docs/essais_lot25.md` (written before the runs):

1. exact: nodal bending moment |M(z)| = q (H - z) (MXX in D7a, MYY in D7b), every
   other bending component, and MXY, <= 1e-6 q H;
2. discretisation-sensitive: tip deflection error decreases from 8 x 8 to 16 x 16;
3. axis identification: at 16 x 16, |error vs announced reference| < 0.01 x
   |error vs other reference|;
4. exact: D7c tip deflection equals D7a's to 1e-6 (relative).

Usage: python scripts/analyze_lot25_essais.py [--mess-dir PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_lot23_essais as a23  # noqa: E402
import build_lot25_essais as l25  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MESS_DIR = ROOT / "data" / "examples" / "lot25_essais" / "mess"
DEFAULT_OUTPUT = ROOT / "data" / "examples" / "lot25_essais" / "analyse.json"

H, Q = l25.HEIGHT, l25.Q_LINE
EXACT_TOLERANCE = 1e-6
W_L = Q * H**3 / (3 * l25.MATERIAL["FLEX_L"])
W_T = Q * H**3 / (3 * l25.MATERIAL["FLEX_T"])
_TOL = 1e-9
# Bending moment along local x_l (MXX) or local y_l (MYY), by case.
_MOMENT = {"d7a": "MXX", "d7a16": "MXX", "d7b": "MYY", "d7b16": "MYY", "d7c": "MXX"}
_EXPECTED = {"d7a": W_L, "d7a16": W_L, "d7b": W_T, "d7b16": W_T, "d7c": W_L}
_OTHER = {"d7a": W_T, "d7a16": W_T, "d7b": W_L, "d7b16": W_L, "d7c": W_T}


def case(text: str, name: str) -> dict[str, object]:
    depl = a23.find_table(text, "DEPL")
    efge = a23.find_table(text, "EFGE_NOEU")
    tip = [r["DY"] for r in depl if abs(r["COOR_Z"] - H) < _TOL]
    mean_tip = sum(tip) / len(tip)
    moment = _MOMENT[name]
    other_bending = "MYY" if moment == "MXX" else "MXX"
    moment_error = max(abs(abs(r[moment]) - Q * (H - r["COOR_Z"])) for r in efge)
    expected, other = _EXPECTED[name], _OTHER[name]
    return {
        "tip_deflection": {
            **a23._stats(tip),
            "mean": mean_tip,
            "sign": "+Y" if mean_tip > 0 else "-Y",
            "expected_reference": expected,
            "other_reference": other,
            "rel_error_vs_expected": (abs(mean_tip) - expected) / expected,
            "rel_error_vs_other": (abs(mean_tip) - other) / other,
        },
        "moment_component": moment,
        "moment_at_base_mean_abs": (
            sum(abs(r[moment]) for r in efge if r["COOR_Z"] < _TOL)
            / len([r for r in efge if r["COOR_Z"] < _TOL])
        ),
        "moment_max_abs_error_over_qH": moment_error / (Q * H),
        "other_bending_max_abs_over_qH": max(abs(r[other_bending]) for r in efge)
        / (Q * H),
        "MXY_max_abs_over_qH": max(abs(r["MXY"]) for r in efge) / (Q * H),
        "moment_signs": sorted({("+" if r[moment] > 0 else "-") for r in efge}),
        "n_efge_points": len(efge),
        "DY_spread_on_tip": max(tip) - min(tip),
    }


def verdict(results: dict[str, dict[str, object]]) -> dict[str, object]:
    def tip(name: str) -> dict[str, float]:
        return results[name]["tip_deflection"]  # type: ignore[return-value]

    out: dict[str, object] = {}
    exact_ok = all(
        results[n]["moment_max_abs_error_over_qH"] <= EXACT_TOLERANCE  # type: ignore[operator]
        and results[n]["other_bending_max_abs_over_qH"] <= EXACT_TOLERANCE  # type: ignore[operator]
        and results[n]["MXY_max_abs_over_qH"] <= EXACT_TOLERANCE  # type: ignore[operator]
        for n in results
        if n != "d7c"
    )
    out["1_moment_exact"] = exact_ok
    for a, fine in (("d7a", "d7a16"), ("d7b", "d7b16")):
        coarse_err = abs(tip(a)["rel_error_vs_expected"])
        fine_err = abs(tip(fine)["rel_error_vs_expected"])
        out[f"2_error_decreases_{a}"] = {
            "err_8": coarse_err,
            "err_16": fine_err,
            "ok": fine_err < coarse_err,
        }
        out[f"3_axis_identified_{a}"] = {
            "err_expected": fine_err,
            "err_other": abs(tip(fine)["rel_error_vs_other"]),
            "ok": fine_err < 0.01 * abs(tip(fine)["rel_error_vs_other"]),
        }
    rel = abs(tip("d7c")["mean"] - tip("d7a")["mean"]) / abs(tip("d7a")["mean"])
    out["4_angl_rep_equals_vecteur"] = {"rel_diff": rel, "ok": rel <= EXACT_TOLERANCE}
    return out


def analyse(mess_dir: Path) -> dict[str, object]:
    texts = {
        n: (mess_dir / f"mess_{n}.txt").read_text(encoding="utf-8")
        for n in ("d7a", "d7a16", "d7b", "d7b16", "d7c")
    }
    results = {n: case(t, n) for n, t in texts.items()}
    return {
        "alarms": {
            n: "aucune alarme" in t and "<A>" not in t for n, t in texts.items()
        },
        **results,
        "verdict": verdict(results),
        "constants": {
            "H": H,
            "q": Q,
            "w_L_ref": W_L,
            "w_T_ref": W_T,
            "flex_ratio": l25.MATERIAL["FLEX_L"] / l25.MATERIAL["FLEX_T"],
            "criterion": "docs/essais_lot25.md",
        },
    }


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
