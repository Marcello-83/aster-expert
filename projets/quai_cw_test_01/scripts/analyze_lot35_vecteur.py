"""Lot 35 : le repère utilisateur des tubes (`AFFE_CARA_ELEM/COQUE/VECTEUR`) ne change
aucun déplacement. Compare, cas par cas et nœud par nœud, les déplacements de tous les
nœuds (tables `SYMETRIE_<cas>`, DX, DY, DZ, 12 chiffres) de deux exécutions du même
quai réduit, l'une avec `VECTEUR = (0, 0, 1)` sur les tubes, l'autre sans.

Critère (docs/essais_lot35.md) : écart nul sur tous les déplacements (la raideur d'un
matériau isotrope ne dépend pas du repère local d'une coque).

Usage : python projets/quai_cw_test_01/scripts/analyze_lot35_vecteur.py <mess avec> <mess sans> [--sortie PATH]
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import json
from pathlib import Path

from aster_expert.report.tables import read_tables

CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("avec", type=Path)
    parser.add_argument("sans", type=Path)
    parser.add_argument("--sortie", type=Path, default=None)
    args = parser.parse_args(argv)

    names = [f"SYMETRIE_{c}" for c in CASES]
    with_vector = read_tables(args.avec, names)
    without = read_tables(args.sans, names)
    result: dict[str, dict[str, float | int]] = {}
    for case, name in zip(CASES, names, strict=True):
        a, b = with_vector[name], without[name]
        if len(a) != len(b):
            message = f"{name} : {len(a)} lignes contre {len(b)}"
            raise SystemExit(message)
        largest = max(abs(float(r[c])) for r in a for c in ("DX", "DY", "DZ"))
        gap = max(
            abs(float(x[c]) - float(y[c]))
            for x, y in zip(a, b, strict=True)
            for c in ("DX", "DY", "DZ")
        )
        result[case] = {
            "n_nodes": len(a),
            "max_abs_displacement_m": largest,
            "max_gap_m": gap,
            "relative_gap": gap / largest,
        }
        print(f"{case:6} {len(a)} nœuds, |u|max {largest:.6e} m, écart max {gap:.3e} m")
    if args.sortie is not None:
        args.sortie.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return 0 if all(v["max_gap_m"] == 0.0 for v in result.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
