"""Lot 53, PONTONS-ALU-01: independent check of `deplacements_evenements.csv` (standard
library only, run with `python -I`).

    python -I verifier_evenements_lot53.py deplacements_unitaires.csv evenements.csv \
        deplacements_evenements.csv [--graine 53]

Three events are drawn (seed) among those that `deplacements_evenements.csv` names. For
each, the value at every point and direction is recomputed as Σ coefficient
(`evenements.csv`, characteristic) × value of the unit case (`deplacements_unitaires.csv`).
Checked: (a) every row where the event is named as the extreme holds that value; (b) on
every row of its family and of « toutes », min ≤ value ≤ max. Tolerance: 1e-9 × max |u|
of the event. Exit code 0 if all hold, 1 otherwise.
"""

import csv
import random
import sys
from collections.abc import Iterator
from pathlib import Path

COMPONENTS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")
COLUMNS = ("DX_mm", "DY_mm", "DZ_mm", "DRX_mrad", "DRY_mrad", "DRZ_mrad")


def rows(path: str) -> Iterator[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        next(stream)
        yield from csv.DictReader(stream, delimiter=";")


def main() -> int:
    unit_path, events_path, extremes_path = sys.argv[1:4]
    seed = (
        int(sys.argv[sys.argv.index("--graine") + 1]) if "--graine" in sys.argv else 53
    )
    unit: dict[tuple[str, str], list[float]] = {}
    for r in rows(unit_path):
        unit[(r["cas"], r["point"])] = [float(r[c]) for c in COLUMNS]
    points = sorted({p for _, p in unit})
    coefs: dict[str, dict[str, float]] = {}
    action: dict[str, str] = {}
    for r in rows(events_path):
        if r["portee"] != "fixe":
            continue
        coefs.setdefault(r["evenement"], {})[r["cas"]] = float(r["coefficient"])
        action[r["evenement"]] = r["action"]
    extremes = list(rows(extremes_path))
    named = sorted(
        {r["evenement_max"] for r in extremes} | {r["evenement_min"] for r in extremes}
    )
    drawn = random.Random(seed).sample(named, 3)
    failures = 0
    for ev in drawn:
        value: dict[str, list[float]] = {}
        for p in points:
            total = [0.0] * 6
            for case, c in coefs[ev].items():
                u = unit[(case, p)]
                total = [t + c * x for t, x in zip(total, u, strict=True)]
            value[p] = total
        big = max(abs(x) for v in value.values() for x in v[:3])
        tol = 1e-9 * big
        named_rows, bounded, worst = 0, 0, 0.0
        for r in extremes:
            v = value[r["point"]][COMPONENTS.index(r["direction"])]
            for side in ("max", "min"):
                if r[f"evenement_{side}"] == ev:
                    named_rows += 1
                    gap = abs(float(r[side]) - v)
                    worst = max(worst, gap)
                    if gap > tol:
                        failures += 1
            if r["famille"] in (action[ev], "toutes"):
                bounded += 1
                if not float(r["min"]) - tol <= v <= float(r["max"]) + tol:
                    failures += 1
        print(
            f"{ev} : {named_rows} extrêmes nommés, écart max {worst:.3e} mm "
            f"(tolérance {tol:.3e}) ; {bounded} lignes encadrées"
        )
    print(f"événements tirés : {', '.join(drawn)}")
    print("RÉUSSI" if failures == 0 else f"ÉCHEC : {failures} écart(s)")
    return 0 if failures == 0 else 1


sys.exit(main())
