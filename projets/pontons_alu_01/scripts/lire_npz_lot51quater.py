"""Lecture indépendante de `efforts_elementaires.npz` (lot 51 quater, PONTONS-ALU-01).

numpy et la bibliothèque standard seulement ; aucun module du projet :

    python3 lire_npz_lot51quater.py efforts_elementaires.npz efforts_elementaires.csv \
        [--tirages 20] [--graine 51]

Tire au sort des efforts (cas, extrémité d'élément, composante) dans le `.npz` et les
compare aux mêmes valeurs de `efforts_elementaires.csv` (17 chiffres significatifs). Le
`.npz` est en float32 : l'écart admis est l'arrondi float32, |Δ| ≤ 2⁻²⁴ × |v| (+ 10⁻³⁰).
Code de sortie 1 au premier écart, 0 sinon.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import numpy as np

TOLERANCE = 2.0**-24


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("npz", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--tirages", type=int, default=20)
    parser.add_argument("--graine", type=int, default=51)
    args = parser.parse_args()
    with np.load(args.npz) as data:
        cases = [str(c) for c in data["cas"]]
        elements = data["elements"]
        nodes = data["noeuds"]
        components = [str(c) for c in data["composantes"]]
        forces = data["efforts"]
    print(
        f"{args.npz.name} : efforts {forces.shape} {forces.dtype}, {len(cases)} cas, "
        f"{len(elements)} extrémités, composantes {components}"
    )
    rng = random.Random(args.graine)
    draws = [
        (
            rng.randrange(len(cases)),
            rng.randrange(len(elements)),
            rng.randrange(len(components)),
        )
        for _ in range(args.tirages)
    ]
    wanted = {(cases[i], int(elements[j]), int(nodes[j])): (i, j) for i, j, _ in draws}
    found: dict[tuple[str, int, int], dict[str, str]] = {}
    with args.csv.open(encoding="utf-8", newline="") as stream:
        lines = (line for line in stream if not line.startswith("#"))
        for record in csv.DictReader(lines, delimiter=";"):
            key = (record["cas"], int(record["element"]), int(record["noeud"]))
            if key in wanted:
                found[key] = record
    failures = 0
    for i, j, k in draws:
        key = (cases[i], int(elements[j]), int(nodes[j]))
        row = found.get(key)
        if row is None:
            print(f"ABSENT du CSV : cas {key[0]}, élément {key[1]}, nœud {key[2]}")
            failures += 1
            continue
        reference = float(row[components[k]])
        value = float(forces[i, j, k])
        gap = abs(value - reference)
        ok = gap <= TOLERANCE * abs(reference) + 1e-30
        failures += not ok
        print(
            f"{'OK' if ok else 'ÉCART'} cas {key[0]}, élément {key[1]}, nœud {key[2]}, "
            f"{components[k]} : npz {value!r}, csv {reference!r}, |Δ| = {gap:.3e}"
        )
    print(f"{len(draws) - failures}/{len(draws)} tirages conformes")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
