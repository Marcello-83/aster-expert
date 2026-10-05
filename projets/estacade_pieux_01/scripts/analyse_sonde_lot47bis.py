"""Lot 47 bis -- analysis of the probe S2 (docs/essais_lot47bis.md § 6).

Reads the listing of the run of `references/cas/sonde_lot47bis.comm`, writes:

- `references/cas/sonde_lot47bis_listing_extrait.txt`: the printed tables, copied
  as they are (the versioned listing the findings cite);
- `references/sonde_lot47bis_resultats.json`: the total of the T-section (bar +
  slab, trapezoids over the slab nodes of each line) against the statics of
  `references/sonde_lot47bis_attendus.json`, the share of the bar alone, and the
  verdict of the criterion of § 6.2.

Usage: `.venv/bin/python projets/estacade_pieux_01/scripts/analyse_sonde_lot47bis.py <run_dir>`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
CAS = PROJECT / "references" / "cas"
LINES = {"L_M190": -1.90, "L_M200": -2.00, "L_P000": 0.00}


def _block(lines: list[str], start: int) -> tuple[list[str], list[list[str]]]:
    header = lines[start + 1].split()
    rows = []
    for line in lines[start + 2 :]:
        if not line.strip():
            break
        rows.append(line.split())
    return header, rows


def tables(text: str) -> dict[str, tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    out: dict[str, tuple[list[str], list[list[str]]]] = {}
    for i, line in enumerate(lines):
        if not line.startswith("##"):
            continue
        header, rows = _block(lines, i)
        if line.startswith("##S2_EFGE_POUTREASTER"):
            out["S2_EFGE_POUTRE"] = (header, rows)
        elif rows and rows[0][0].startswith("S2_"):
            out[rows[0][0]] = (header, rows)
    return out


def extract(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    for i, line in enumerate(lines):
        if line.startswith("##") and i + 2 < len(lines):
            first = lines[i + 2].split()
            if line.startswith("##S2_") or (first and first[0].startswith("S2_")):
                kept.append(line)
                for row in lines[i + 1 :]:
                    if not row.strip():
                        break
                    kept.append(row)
                kept.append("")
    return "\n".join(kept) + "\n"


def column(header: list[str], rows: list[list[str]], name: str) -> np.ndarray[Any, Any]:
    # La table de CREA_TABLE n'a pas de colonne INTITULE : les lignes sont alignées
    # sur l'en-tête ; celle de POST_RELEVE_T commence par l'intitulé.
    k = header.index(name)
    return np.array([float(r[k]) for r in rows])


def main() -> None:
    run = Path(sys.argv[1])
    text = (run / "proc.0" / "fort.6").read_text(encoding="utf-8", errors="replace")
    (CAS / "sonde_lot47bis_listing_extrait.txt").write_text(extract(text), "utf-8")
    t = tables(text)
    expected = json.loads(
        (PROJECT / "references" / "sonde_lot47bis_attendus.json").read_text("utf-8")
    )
    h, rows = t["S2_REAC"]
    reaction = float(column(h, rows, "DZ")[0])
    hb, rb = t["S2_EFGE_POUTRE"]
    yb = column(hb, rb, "COOR_Y")
    vz = column(hb, rb, "VZ")
    mfy = column(hb, rb, "MFY")
    # s : signe tel que s·MFY > 0 en travée (milieu, Y = 0), comme à l'estacade.
    s = 1.0 if float(np.mean(mfy[np.abs(yb) < 1e-9])) > 0 else -1.0
    out: dict[str, Any] = {
        "execution": str(run),
        "reaction_DZ_N": reaction,
        "reaction_attendue_N": expected["W_N"],
        "ecart_reaction": (reaction - expected["W_N"]) / expected["W_N"],
        "signe_s": s,
        "lignes": {},
    }
    targets = {
        "L_M190": ("V", expected["V_total_Y_m1p90_N"]),
        "L_M200": ("M", expected["M_total_Y_m2p00_Nm"]),
        "L_P000": ("M", expected["M_total_Y_0_Nm"]),
    }
    verdicts = [abs(out["ecart_reaction"]) <= 1e-6]
    for name, y in LINES.items():
        hl, rl = t[f"S2_{name}"]
        x = column(hl, rl, "COOR_X")
        order = np.argsort(x)
        x = x[order]
        qy = column(hl, rl, "QY")[order]
        myy = column(hl, rl, "MYY")[order]
        mxy = column(hl, rl, "MXY")[order]
        at = np.abs(yb - y) < 1e-9
        kind, ref = targets[name]
        if kind == "V":
            bar = float(np.mean(vz[at]))
            slab = float(np.trapezoid(qy, x))
            total = bar + slab
            gap = (abs(total) - abs(ref)) / abs(ref)
        else:
            bar = s * float(np.mean(mfy[at]))
            slab = -float(np.trapezoid(myy, x))
            total = bar + slab
            gap = (total - ref) / abs(ref)
        verdicts.append(abs(gap) <= 0.02)
        out["lignes"][name] = {
            "Y": y,
            "grandeur": "effort tranchant |VZ + ∫QY dX| (N)"
            if kind == "V"
            else "moment s·MFY − ∫MYY dX (N·m)",
            "barre_seule": bar,
            "barre_extremites": [
                float(v) for v in (vz[at] if kind == "V" else s * mfy[at])
            ],
            "dalle": slab,
            "total": total,
            "statique": ref,
            "ecart_relatif_total": gap,
            "part_de_la_barre": bar / total if total else float("nan"),
            "terme_de_bord_MXY": float(mxy[-1] - mxy[0]),
        }
    out["verdict"] = "RÉUSSI" if all(verdicts) else "ÉCHEC"
    path = PROJECT / "references" / "sonde_lot47bis_resultats.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
