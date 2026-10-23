"""Lot 54: the re-run of B52 of lot 52 (clone neuf, tables du lot 52 perdues) against the
files of lot 52 delivered on the share: nodes (coordinates and groups), elements
(connectivity, family), forces of every unit case (`efforts_elementaires.npz`, float32)
and reactions of every unit case (`reactions_elementaires.csv`, 17 digits).

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/verifier_reexecution_B52_lot54.py \
        [--partage /media/sf_partage/echanges/lot52/pontons_alu_01/B52]

Writes `resultats/lot54/exports/verification_reexecution_B52.json` and prints a summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.projet.context import load_project
from pontons_alu_01.exports_lot51quater import force_tensor
from pontons_alu_01.exports_lot51ter import reaction_rows
from pontons_alu_01.exports_lot54 import load_b52

ROOT = Path(__file__).resolve().parents[3]
SHARE = Path("/media/sf_partage/echanges/lot52/pontons_alu_01/B52")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partage", type=Path, default=SHARE)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    vd = load_b52(ctx)
    m = vd.model
    out: dict[str, Any] = {"source": str(args.partage)}
    old_nodes = rows(args.partage / "noeuds.csv")
    coords = np.asarray(m.coords, dtype=float)[:, :3]
    gap = max(
        float(
            np.max(np.abs(coords[int(r["noeud"]) - 1] - [float(r[c]) for c in "xyz"]))
        )
        for r in old_nodes
    )
    groups = sum(
        1 for r in old_nodes if r["groupes"] != "|".join(m.node_groups[int(r["noeud"])])
    )
    out["noeuds"] = {
        "nombre": len(old_nodes),
        "lot54": len(coords),
        "ecart_coord_m": gap,
        "groupes_differents": groups,
    }
    old_el = [r for r in rows(args.partage / "elements.csv") if r["element"].isdigit()]
    diff_el = sum(
        1
        for r in old_el
        if int(r["element"]) not in m.elements
        or tuple(m.elements[int(r["element"])].nodes)
        != (int(r["noeud1"]), int(r["noeud2"]))
        or m.elements[int(r["element"])].family != r["famille"]
    )
    out["elements"] = {
        "nombre": len(old_el),
        "lot54": len(m.elements),
        "differents": diff_el,
    }
    with np.load(args.partage / "efforts_elementaires.npz") as old:
        cases, elements, nodes, _, forces = force_tensor(vd)
        same_keys = (
            list(old["cas"]) == cases
            and np.array_equal(old["elements"], elements)
            and np.array_equal(old["noeuds"], nodes)
        )
        f32 = forces.astype(np.float32)
        rel = np.abs(f32.astype(np.float64) - old["efforts"].astype(np.float64))
        scale = np.maximum(
            np.abs(old["efforts"].astype(np.float64)).max(axis=(1, 2)), 1e-30
        )
        out["efforts_npz"] = {
            "memes_cles": bool(same_keys),
            "valeurs": int(old["efforts"].size),
            "egales_float32": int(np.sum(f32 == old["efforts"])),
            "ecart_max_rapporte_au_max_du_cas": float(
                (rel.max(axis=(1, 2)) / scale).max()
            ),
        }
    old_r = {
        (r["cas"], r["appui"], r["noeud"]): r
        for r in rows(args.partage / "reactions_elementaires.csv")
    }
    worst = 0.0
    n = 0
    for r in reaction_rows(vd):
        key = (str(r[0]), str(r[1]), str(r[2]))
        o = old_r.get(key)
        if o is None:
            continue
        for k, c in zip(range(6, 9), ("RX", "RY", "RZ"), strict=True):
            a, b = float(r[k]), float(o[c])
            worst = max(worst, abs(a - b) / max(abs(b), 1.0))
            n += 1
    out["reactions"] = {
        "valeurs": n,
        "lignes_lot52": len(old_r),
        "ecart_relatif_max": worst,
    }
    out["reussi"] = (
        gap <= 1e-9
        and groups == 0
        and diff_el == 0
        and out["efforts_npz"]["memes_cles"]
        and out["efforts_npz"]["ecart_max_rapporte_au_max_du_cas"] <= 1e-6
        and worst <= 1e-6
    )
    path = ctx.results_dir / "lot54" / "exports" / "verification_reexecution_B52.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if out["reussi"] else 1


if __name__ == "__main__":
    sys.exit(main())
