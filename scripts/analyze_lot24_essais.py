"""Extract and compare the results of the lot 24 trials (D6) from their `.mess` copies.

Reads `data/examples/lot24_essais/mess/mess_<case>.txt` (copies of the `fort.6`
of each run), parses the `IMPR_TABLE` tables with the helpers of the lot 23
analysis (no project `.mess` parser is extended) and writes `analyse.json`.

References (square plate a = 1 m, decision 2 v5 coefficients, L = mesh Y, T = mesh X):

- d6a: elongation q a / MEMB_T, NYY = q, no other component;
- d6b: w(a/2) = 5 p a^4 / (384 FLEX_T), M(x) = p x (a - x) / 2, |QY| = p / 2 (a - 2 x);
- d6c: u_x = gamma y with gamma = tau / MEMB_G_LT, u_y = 0, |NXY| = tau.

Usage: python scripts/analyze_lot24_essais.py [--mess-dir PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_lot23_essais as a23  # noqa: E402
import build_lot24_essais as l24  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MESS_DIR = ROOT / "data" / "examples" / "lot24_essais" / "mess"
DEFAULT_OUTPUT = ROOT / "data" / "examples" / "lot24_essais" / "analyse.json"

A = l24.SIDE
COMPONENTS = ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")
_TOL = 1e-9


def _stats(values: list[float]) -> dict[str, float]:
    return a23._stats(values)


def _rel(value: float, reference: float) -> float:
    return (value - reference) / reference


def _at(records: list[dict], axis: str, value: float) -> list[dict]:
    return [r for r in records if abs(r[axis] - value) < _TOL]


def _max_abs(records: list[dict], names: tuple[str, ...]) -> float:
    return max(abs(r[name]) for r in records for name in names)


def _reactions(text: str) -> dict[str, dict[str, float]]:
    return {
        group: a23._resultant(text, f"REAC_NODA_{group}")
        for group in ("NX0", "NXA", "TOUS")
    }


def _efge(text: str, name: str, others: tuple[str, ...], ref: dict[str, float]) -> dict:
    records = a23.find_table(text, name)
    out: dict[str, object] = {
        "n_points": len(records),
        "max_abs_other_components": _max_abs(records, others),
    }
    for component, expected in ref.items():
        values = [r[component] for r in records]
        out[component] = {**_stats(values), "ref": expected}
    return out


def d6a(text: str) -> dict[str, object]:
    depl = a23.find_table(text, "DEPL")
    end = [r["DX"] for r in _at(depl, "COOR_X", A)]
    ref = l24.Q_TRACTION * A / l24.MATERIAL["MEMB_T"]
    others = tuple(c for c in COMPONENTS if c != "NYY")
    out: dict[str, object] = {
        "elongation": {
            **_stats(end),
            "ref": ref,
            "rel_error_mean": _rel(sum(end) / len(end), ref),
        },
        "DX_clamped_edge_max_abs": max(abs(r["DX"]) for r in _at(depl, "COOR_X", 0.0)),
        "DY_max_abs": max(abs(r["DY"]) for r in depl),
        "DZ_max_abs": max(abs(r["DZ"]) for r in depl),
        "reactions": _reactions(text),
        "reaction_ref": {"RESULT_X_NX0": -l24.Q_TRACTION * A},
    }
    for name in ("EFGE_ELNO", "EFGE_NOEU"):
        out[name] = _efge(text, name, others, {"NYY": l24.Q_TRACTION})
    return out


def d6b(text: str) -> dict[str, object]:
    depl = a23.find_table(text, "DEPL")
    mid = [r["DZ"] for r in _at(depl, "COOR_X", A / 2)]
    ref_w = 5 * l24.P_PRESSURE * A**4 / (384 * l24.MATERIAL["FLEX_T"])
    out: dict[str, object] = {
        "deflection_mid": {**_stats(mid), "ref": ref_w},
        "DZ_max_abs": max(abs(r["DZ"]) for r in depl),
        "DZ_supports_max_abs": max(
            abs(r["DZ"])
            for r in depl
            if r["COOR_X"] < _TOL or abs(r["COOR_X"] - A) < _TOL
        ),
        "DZ_spread_along_y": max(mid) - min(mid),
        "reactions": _reactions(text),
        "reaction_ref": {
            "RESULT_Z_per_support": l24.P_PRESSURE * A * A / 2,
            "RESULT_Z_total": l24.P_PRESSURE * A * A,
        },
    }
    for name in ("EFGE_ELNO", "EFGE_NOEU"):
        records = a23.find_table(text, name)
        m_ref = lambda x: l24.P_PRESSURE * x * (A - x) / 2  # noqa: E731
        q_ref = lambda x: l24.P_PRESSURE / 2 * (A - 2 * x)  # noqa: E731
        node_lines = sorted({round(r["COOR_X"], 9) for r in records})
        out[name] = {
            "n_points": len(records),
            "MYY_mid": {
                **_stats([r["MYY"] for r in _at(records, "COOR_X", A / 2)]),
                "ref": m_ref(A / 2),
            },
            "MYY_max_abs_error_all_points": max(
                abs(abs(r["MYY"]) - m_ref(r["COOR_X"])) for r in records
            ),
            "MYY_max_abs_error_all_points_over_ref_max": max(
                abs(abs(r["MYY"]) - m_ref(r["COOR_X"])) for r in records
            )
            / m_ref(A / 2),
            "QY_x0": {
                **_stats([r["QY"] for r in _at(records, "COOR_X", 0.0)]),
                "ref_abs": q_ref(0.0),
            },
            "QY_xa": {
                **_stats([r["QY"] for r in _at(records, "COOR_X", A)]),
                "ref_abs": q_ref(A),
            },
            "QY_by_x": {
                f"{x:.3f}": _stats([r["QY"] for r in _at(records, "COOR_X", x)])
                for x in node_lines
            },
            "MYY_by_x": {
                f"{x:.3f}": _stats([r["MYY"] for r in _at(records, "COOR_X", x)])
                for x in node_lines
            },
            "max_abs_other_components": _max_abs(
                records, ("NXX", "NYY", "NXY", "MXX", "MXY", "QX")
            ),
        }
    return out


def d6c(text: str) -> dict[str, object]:
    depl = a23.find_table(text, "DEPL")
    gamma = l24.TAU_SHEAR / l24.MATERIAL["MEMB_G_LT"]
    top = [r["DX"] for r in _at(depl, "COOR_Y", A)]
    others = tuple(c for c in COMPONENTS if c != "NXY")
    out: dict[str, object] = {
        "gamma_ref": gamma,
        "DX_top": {
            **_stats(top),
            "ref": gamma * A,
            "rel_error_mean": _rel(sum(top) / len(top), gamma * A),
        },
        "DX_max_abs_error_vs_gamma_y": max(
            abs(r["DX"] - gamma * r["COOR_Y"]) for r in depl
        ),
        "DY_max_abs": max(abs(r["DY"]) for r in depl),
        "DZ_max_abs": max(abs(r["DZ"]) for r in depl),
        "reactions": _reactions(text),
        "reaction_ref": {"RESULT_X_and_Y": 0.0},
    }
    for name in ("EFGE_ELNO", "EFGE_NOEU"):
        out[name] = _efge(text, name, others, {"NXY": l24.TAU_SHEAR})
    return out


def analyse(mess_dir: Path) -> dict[str, object]:
    texts = {
        n: (mess_dir / f"mess_{n}.txt").read_text(encoding="utf-8")
        for n in ("d6a", "d6b", "d6b16", "d6c")
    }
    return {
        "alarms": {
            n: "aucune alarme" in t and "<A>" not in t for n, t in texts.items()
        },
        "d6a": d6a(texts["d6a"]),
        "d6b": d6b(texts["d6b"]),
        "d6b16": d6b(texts["d6b16"]),
        "d6c": d6c(texts["d6c"]),
        "constants": {
            "a": A,
            "EPAIS": l24.EPAIS,
            "q": l24.Q_TRACTION,
            "p": l24.P_PRESSURE,
            "tau": l24.TAU_SHEAR,
            **l24.MATERIAL,
            "flex_T_over_memb_T_epais2_over_12": l24.MATERIAL["FLEX_T"]
            / (l24.MATERIAL["MEMB_T"] * l24.EPAIS**2 / 12.0),
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
