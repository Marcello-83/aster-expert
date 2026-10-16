"""Recombinaison des cas élémentaires de PONTONS-ALU-01 (lot 51 ter, ponton intégral).

Livré avec les fichiers de l'export de chaque variante ; bibliothèque standard de Python
seulement :

    python3 recombiner.py [répertoire des CSV] [--compter]
    python3 recombiner.py [répertoire] --element 412 --extremite 2 --composante MFY

Les combinaisons ne sont pas listées une à une (2 351 600 par variante en règles) :
`combinaisons.csv` donne les règles, branche par branche (une option par emplacement, le
produit des emplacements fait la branche), et `evenements.csv` les coefficients de chaque
événement sur les cas élémentaires (valeurs caractéristiques). Colonne `portee` :
« fixe » pour un coefficient toujours appliqué ; « module Mk » pour les événements Q et
QD en dispositions défavorables : chaque module est chargé ou non. Pour une grandeur, la
disposition la plus défavorable ne s'énumère pas : au maximum, l'événement prend la
somme des contributions positives des modules, au minimum celle des contributions
négatives (lignes d'influence, exact en linéaire). Ce script énumère les combinaisons
des règles (`--compter` : effectifs, en règles et avec les 2ⁿ − 1 dispositions
comptées une à une) et recombine Σ facteur × cas élémentaire en une extrémité d'élément
de `efforts_elementaires.csv` : maximum et minimum de la composante demandée sur toutes
les combinaisons de chaque état limite, avec la combinaison qui les donne.

Contrôle du lot 51 ter (docs/essais_lot51ter.md) : ces extrêmes, obtenus combinaison par
combinaison, égalent ceux du calcul par décomposition de l'outil.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
Events = dict[str, tuple[dict[str, float], list[tuple[str, dict[str, float]]]]]
Rules = list[tuple[str, str, list[list[tuple[str | None, float]]]]]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def read_events(folder: Path) -> Events:
    """événement -> (coefficients fixes, [(module, coefficients)])."""
    out: Events = {}
    for row in read_csv(folder / "evenements.csv"):
        fixed, modules = out.setdefault(row["evenement"], ({}, []))
        value = float(row["coefficient"])
        if row["portee"] == "fixe":
            fixed[row["cas"]] = value
            continue
        module = row["portee"].removeprefix("module ")
        if not modules or modules[-1][0] != module:
            modules.append((module, {}))
        modules[-1][1][row["cas"]] = value
    return out


def read_rules(folder: Path) -> Rules:
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


def count(rules: Rules, events: Events | None = None) -> dict[str, int]:
    """Effectifs par état limite ; avec `events`, chaque disposition comptée."""
    out: dict[str, int] = {}
    for state, _, slots in rules:
        n = 1
        for s in slots:
            if events is None:
                n *= len(s)
            else:
                n *= sum(
                    1
                    if name is None or not events[name][1]
                    else 2 ** len(events[name][1]) - 1
                    for name, _ in s
                )
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


def _option(
    name: str | None, factor: float, events: Events, values: dict[str, float]
) -> tuple[float, float, str, str]:
    """(valeur au maximum, valeur au minimum, libellé au maximum, au minimum)."""
    if name is None:
        return 0.0, 0.0, "", ""
    fixed, modules = events[name]
    base = factor * sum(c * values[k] for k, c in fixed.items())
    if not modules:
        label = f"{name}×{factor:g}"
        return base, base, label, label
    parts = [
        (m, factor * sum(c * values[k] for k, c in mc.items())) for m, mc in modules
    ]
    up = [m for m, v in parts if v > 0.0]
    down = [m for m, v in parts if v < 0.0]
    hi = base + sum(v for _, v in parts if v > 0.0)
    lo = base + sum(v for _, v in parts if v < 0.0)
    return (
        hi,
        lo,
        f"{name}[{'+'.join(up) or 'aucun module'}]×{factor:g}",
        f"{name}[{'+'.join(down) or 'aucun module'}]×{factor:g}",
    )


def extremes(
    rules: Rules, events: Events, values: dict[str, float]
) -> dict[str, tuple[float, str, float, str]]:
    """Par état limite : (max, combinaison, min, combinaison) de Σ facteur × valeur,
    combinaison par combinaison."""
    out: dict[str, tuple[float, str, float, str]] = {}
    for state, _, slots in rules:
        prepared = [[_option(n, f, events, values) for n, f in s] for s in slots]
        hi, hi_c, lo, lo_c = out.get(state, (-float("inf"), "", float("inf"), ""))
        for choice in itertools.product(*prepared):
            up = sum(o[0] for o in choice)
            down = sum(o[1] for o in choice)
            if up > hi:
                hi = up
                hi_c = " + ".join(o[2] for o in choice if o[2])
            if down < lo:
                lo = down
                lo_c = " + ".join(o[3] for o in choice if o[3])
        out[state] = (hi, hi_c, lo, lo_c)
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
    events = read_events(args.dossier)
    if args.compter or args.element is None:
        tally = count(rules)
        expanded = count(rules, events)
        for state, n in tally.items():
            print(
                f"{state} : {n} combinaisons ({expanded[state]} dispositions comptées)"
            )
        print(f"total : {sum(tally.values())} ({sum(expanded.values())})")
        if args.element is None:
            return 0
    torsors = element_end(args.dossier, args.element, args.extremite)
    values = {case: t[args.composante] for case, t in torsors.items()}
    for state, (hi, hi_name, lo, lo_name) in extremes(rules, events, values).items():
        print(f"{state} : max {hi!r} ({hi_name}) ; min {lo!r} ({lo_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
