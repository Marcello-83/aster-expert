"""Recombinaison des cas élémentaires de PONTONS-ALU-01 (lot 51).

Livré avec les fichiers de l'export de chaque variante ; bibliothèque standard de Python
seulement :

    python3 recombiner.py [répertoire des CSV] [--compter]
    python3 recombiner.py [répertoire] --element 412 --extremite 2 --composante MFY

Les combinaisons ne sont pas listées une à une (276 235 par variante, 5 416 185 pour la
variante E) : `combinaisons.csv` donne les règles, branche par branche (une option par
emplacement, le produit des emplacements fait la branche), et `evenements.csv` les
coefficients de chaque événement sur les cas élémentaires (valeurs caractéristiques, kN ou
kPa sur les cas unitaires de 1 kN, 1 kN/m sur 1 m ou 1 kPa). Ce script énumère les
combinaisons à partir de ces deux fichiers (`combinaisons`), compte chaque état limite
(`--compter`) et recombine Σ facteur × cas élémentaire en une extrémité d'élément de
`efforts_elementaires.csv` : maximum et minimum de la composante demandée sur toutes les
combinaisons de chaque état limite, avec la combinaison qui les donne.

Contrôle du lot 51 (docs/essais_lot51.md § 1, critère 5) : ces extrêmes, obtenus
combinaison par combinaison, égalent ceux du calcul par décomposition de l'outil.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from collections.abc import Iterator
from pathlib import Path

COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def read_events(folder: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in read_csv(folder / "evenements.csv"):
        out.setdefault(row["evenement"], {})[row["cas"]] = float(row["coefficient"])
    return out


def read_rules(
    folder: Path,
) -> list[tuple[str, str, list[list[tuple[str | None, float]]]]]:
    """(état limite, branche, emplacements) ; un emplacement est une liste d'options
    (événement ou None pour l'absence, facteur)."""
    branches: dict[tuple[str, str], list[list[tuple[str | None, float]]]] = {}
    for row in read_csv(folder / "combinaisons.csv"):
        options: list[tuple[str | None, float]] = []
        for item in row["options"].split("|"):
            if item == "∅":
                options.append((None, 0.0))
            else:
                name, factor = item.rsplit("×", 1)
                options.append((name, float(factor)))
        branches.setdefault((row["etat_limite"], row["branche"]), []).append(options)
    return [(state, name, slots) for (state, name), slots in branches.items()]


def combinations(
    rules: list[tuple[str, str, list[list[tuple[str | None, float]]]]],
    events: dict[str, dict[str, float]],
    state: str | None = None,
) -> Iterator[tuple[str, str, dict[str, float]]]:
    """(état limite, nom, coefficients sur les cas élémentaires) de chaque combinaison."""
    for st, _, slots in rules:
        if state is not None and st != state:
            continue
        for choice in itertools.product(*slots):
            coefs: dict[str, float] = {}
            parts = []
            for name, factor in choice:
                if name is None:
                    continue
                parts.append(f"{name}×{factor:g}")
                for case, c in events[name].items():
                    coefs[case] = coefs.get(case, 0.0) + factor * c
            yield st, " + ".join(parts), coefs


def count(
    rules: list[tuple[str, str, list[list[tuple[str | None, float]]]]],
) -> dict[str, int]:
    out: dict[str, int] = {}
    for state, _, slots in rules:
        n = 1
        for s in slots:
            n *= len(s)
        out[state] = out.get(state, 0) + n
    return out


def element_end(folder: Path, element: str, end: str) -> dict[str, dict[str, float]]:
    """Torseur de chaque cas élémentaire à une extrémité d'élément."""
    out: dict[str, dict[str, float]] = {}
    with (folder / "efforts_elementaires.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        lines = (line for line in stream if not line.startswith("#"))
        for row in csv.DictReader(lines, delimiter=";"):
            if row["element"] == element and row["extremite"] == end:
                out[row["cas"]] = {c: float(row[c]) for c in COMPONENTS}
    if not out:
        message = (
            f"élément {element}, extrémité {end} absent de efforts_elementaires.csv"
        )
        raise KeyError(message)
    return out


def extremes(
    rules: list[tuple[str, str, list[list[tuple[str | None, float]]]]],
    events: dict[str, dict[str, float]],
    values: dict[str, float],
) -> dict[str, tuple[float, str, float, str]]:
    """Par état limite : (max, combinaison, min, combinaison) de Σ facteur × valeur."""
    out: dict[str, tuple[float, str, float, str]] = {}
    for state, name, coefs in combinations(rules, events):
        v = sum(c * values[case] for case, c in coefs.items())
        best = out.get(state)
        if best is None:
            out[state] = (v, name, v, name)
            continue
        hi, hi_name, lo, lo_name = best
        if v > hi:
            hi, hi_name = v, name
        if v < lo:
            lo, lo_name = v, name
        out[state] = (hi, hi_name, lo, lo_name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dossier", nargs="?", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument("--compter", action="store_true")
    parser.add_argument("--element")
    parser.add_argument("--extremite", default="1")
    parser.add_argument("--composante", default="MFY", choices=COMPONENTS)
    args = parser.parse_args()
    rules = read_rules(args.dossier)
    if args.compter or args.element is None:
        tally = count(rules)
        for state, n in tally.items():
            print(f"{state} : {n} combinaisons")
        print(f"total : {sum(tally.values())}")
        if args.element is None:
            return 0
    events = read_events(args.dossier)
    torsors = element_end(args.dossier, args.element, args.extremite)
    values = {case: t[args.composante] for case, t in torsors.items()}
    for state, (hi, hi_name, lo, lo_name) in extremes(rules, events, values).items():
        print(f"{state} : max {hi!r} ({hi_name}) ; min {lo!r} ({lo_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
