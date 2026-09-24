"""Lot 34, étape 2 : contrôle des ressorts nœud par nœud. Compare la force que
Code_Aster calcule pour chaque ressort (`FORC_NODA` restreint aux `POI1`,
`TAB_FRESS_<cas>`) à `k * DY` (`TAB_RESS_<cas>`, raideur lue des classes du
générateur), et signale chaque nœud où elles diffèrent.

Sert à établir, sur le quai réduit, qu'un nœud partagé par deux bandes ne portait
que la raideur de la marne (`CREA_POI1` ne crée qu'une maille ponctuelle par nœud :
la dernière occurrence de `DISCRET` écrasait l'autre), et à vérifier la correction.

Usage : python scripts/analyze_lot34_ressorts.py <mess> <données> <cas> [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import analyze_lot33_equilibre as l33  # noqa: E402

TOLERANCE_M = 1.0e-3
"""Appariement des lignes du `.mess` aux nœuds de ressort (les coordonnées sont
imprimées à 12 chiffres, mais un nœud est cherché à 1 mm)."""

Point = tuple[float, float, float]


def compare_spring_forces(
    displacements: list[dict[str, Any]],
    forces: list[dict[str, Any]],
    stiffness: dict[Point, float],
    *,
    relative_tolerance: float = 1.0e-6,
) -> dict[str, Any]:
    """`FORC_NODA` (DY) de chaque nœud contre `k * DY` ; `stiffness` donne la raideur
    (N/m) lue des classes de chaque nœud (somme des bandes). Un nœud non retrouvé
    est une erreur."""
    grid: dict[tuple[int, int, int], list[Point]] = {}
    for key in stiffness:
        cell = (
            int(key[0] // TOLERANCE_M),
            int(key[1] // TOLERANCE_M),
            int(key[2] // TOLERANCE_M),
        )
        grid.setdefault(cell, []).append(key)

    def find(point: Point) -> Point:
        cx, cy, cz = (int(v // TOLERANCE_M) for v in point)
        best, best_d = None, math.inf
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for cand in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        d = math.dist(point, cand)
                        if d < best_d:
                            best, best_d = cand, d
        if best is None or best_d > TOLERANCE_M:
            message = f"nœud de ressort non retrouvé : {point}"
            raise ValueError(message)
        return best

    dy_by_node = {
        find((r["COOR_X"], r["COOR_Y"], r["COOR_Z"])): r["DY"] for r in displacements
    }
    sum_force = 0.0
    sum_k_dy = 0.0
    mismatches: list[dict[str, Any]] = []
    for r in forces:
        node = find((r["COOR_X"], r["COOR_Y"], r["COOR_Z"]))
        force = r["DY"]
        k_dy = stiffness[node] * dy_by_node[node]
        sum_force += force
        sum_k_dy += k_dy
        if abs(force - k_dy) > relative_tolerance * max(abs(k_dy), 1.0):
            dy = dy_by_node[node]
            mismatches.append(
                {
                    "node": node,
                    "force_aster_n": force,
                    "k_dy_read_n": k_dy,
                    "k_read_n_per_m": stiffness[node],
                    "k_effective_n_per_m": force / dy if dy else math.nan,
                }
            )
    return {
        "n_nodes": len(forces),
        "sum_force_aster_n": sum_force,
        "sum_k_dy_read_n": sum_k_dy,
        "sum_gap_n": sum_force - sum_k_dy,
        "n_mismatches": len(mismatches),
        "mismatches": mismatches,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("cas")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    from aster_expert.agent.model_data import load_model_data  # noqa: PLC0415
    from aster_expert.generation.springs import (  # noqa: PLC0415
        COMBINED_BAND,
        build_spring_classes,
    )
    from aster_expert.meshing.combiwall import build_params  # noqa: PLC0415

    mess = args.mess.read_text(encoding="utf-8")
    data = load_model_data(args.donnees)
    k_h = {
        "RESS_AV_ARGI": float(data.items()["sol.k_h_argile_marneuse_raide"].value),
        "RESS_AV_MARNE": float(data.items()["sol.k_h_marne_compacte"].value),
    }
    stiffness: dict[Point, float] = {}
    for c in build_spring_classes(build_params(data), k_h):
        if c.band == COMBINED_BAND:
            continue
        for x, y, z in c.nodes:
            key = (round(x, 6), round(y, 6), round(z, 6))
            stiffness[key] = stiffness.get(key, 0.0) + c.stiffness_n_per_m
    result = compare_spring_forces(
        l33.find_table(mess, f"RESSORTS_{args.cas}"),
        l33.find_table(mess, f"FRESS_{args.cas}"),
        stiffness,
    )
    output = args.output or (args.mess.parent / f"ressorts_{args.cas}.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {k: v for k, v in result.items() if k != "mismatches"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
