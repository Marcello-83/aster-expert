"""Lot 50 quater : contrôle des charges de PONTONS-ALU-01 contre `charges.csv` (lot 50 ter)
et dépôt sur le partage, après la sous-étape générique `charges` :

    .venv/bin/aster-expert projet pontons_alu_01 livrables --sous-etape charges
    PYTHONPATH=projets .venv/bin/python \
        projets/pontons_alu_01/scripts/livrables_lot50quater.py [--depot <répertoire>]

Pour chacun des douze cas mécaniques à intégrale calculable, la somme des forces
nodales du MED (`charges/manifeste.json`, valeurs non arrondies) est comparée à
l'intégrale des charges de `export_lot50ter/charges.csv` (valeur × longueur de
l'étendue chargée × direction ; ponctuelles : valeur × direction), au seuil de 1e-6 en
relatif. La pesanteur (G1) n'a pas d'intégrale dans ce fichier : elle est comparée au
poids calculé à la main du projet (CTL-013, `controls.cases`). Le tableau est écrit dans
`charges/controle_charges_csv.csv`, puis le dossier est déposé (`charges_verif.deposit`).
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

from aster_expert.livrables.chaine import deliverables_dir
from aster_expert.livrables.charges_verif import deposit
from aster_expert.projet.context import load_project

ROOT = Path(__file__).resolve().parents[3]
DEPOT = Path("/media/sf_partage/echanges/lot50quater/pontons_alu_01")
SEUIL = 1.0e-6


def integrals(path: Path) -> dict[str, list[float]]:
    """Résultante (N) de chaque cas, d'après les lignes réparties et ponctuelles."""
    totals: dict[str, list[float]] = {}
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line[:1] != "#"
    ]
    for row in csv.DictReader(lines, delimiter=";"):
        if row["type"] not in ("répartie", "ponctuelle"):
            continue
        direction = [float(row[f"dir_{a}"]) for a in "xyz"]
        value = float(row["valeur"])
        if row["type"] == "répartie":
            start = [float(row[f"{a}_debut"]) for a in "xyz"]
            end = [float(row[f"{a}_fin"]) for a in "xyz"]
            value *= math.dist(start, end)
        total = totals.setdefault(row["cas"], [0.0, 0.0, 0.0])
        for k in range(3):
            total[k] += value * direction[k]
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--depot", type=Path, default=DEPOT)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    out = deliverables_dir(ctx) / "charges"
    manifest = json.loads((out / "manifeste.json").read_text(encoding="utf-8"))
    expected = integrals(
        ROOT / "projets/pontons_alu_01/resultats/export_lot50ter/charges.csv"
    )
    rows = []
    failed = []
    for case in manifest["resultantes"]:
        name = case["cas"]
        if name not in expected:
            continue
        want = expected[name]
        measured = case["mesure_n"]
        scale = max(abs(v) for v in want) or 1.0
        gap = max(abs(m - w) for m, w in zip(measured, want, strict=True)) / scale
        verdict = "RÉUSSI" if gap <= SEUIL else "ÉCHEC"
        if verdict == "ÉCHEC":
            failed.append(name)
        rows.append([name, *measured, *want, gap, verdict])
    with (out / "controle_charges_csv.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        f.write(
            "# Somme des forces nodales du MED (N) contre l'intégrale des charges de "
            "export_lot50ter/charges.csv (N), repère global ; seuil 1e-6 en relatif.\n"
        )
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(
            [
                "cas",
                "MED_FX_N",
                "MED_FY_N",
                "MED_FZ_N",
                "csv_FX_N",
                "csv_FY_N",
                "csv_FZ_N",
                "ecart_relatif",
                "verdict",
            ]
        )
        for row in rows:
            writer.writerow(
                [row[0], *(f"{v:.6f}" for v in row[1:7]), f"{row[7]:.2e}", row[8]]
            )
    print("cas | ΣF MED (kN) | ΣF charges.csv (kN) | écart relatif | verdict")
    for row in rows:
        med = ", ".join(f"{v * 1e-3:.3f}" for v in row[1:4])
        csv_ = ", ".join(f"{v * 1e-3:.3f}" for v in row[4:7])
        print(f"{row[0]} | {med} | {csv_} | {row[7]:.2e} | {row[8]}")
    print(f"{len(rows)} cas comparés ; échecs : {failed or 'aucun'}")
    if failed:
        return 1
    names = deposit(ctx, args.depot)
    print(f"{len(names)} fichiers déposés dans {args.depot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
