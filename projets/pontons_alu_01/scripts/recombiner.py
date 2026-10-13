"""Recombinaison des cas élémentaires de PONTONS-ALU-01 (lot 50 ter).

Livré avec les fichiers de l'export ; bibliothèque standard de Python seulement :

    python3 recombiner.py [répertoire des CSV]

Lit `efforts_elementaires.csv` et `combinaisons.csv` (format commun : `;`, point décimal,
une ligne `#` en tête) et recombine, pour chaque combinaison, Σ facteur × cas élémentaire
à chaque extrémité d'élément. Contrôle unique du lot 50 ter (docs/essais_lot50ter.md
§ 1, critère écrit avant l'export) : trois valeurs du lot 50 bis, jeu B, ELU fondamental
et accidentel, à 10⁻⁶ près en relatif. Code de sortie 0 si les trois passent, 1 sinon.

La fonction `recombine` sert aussi à toute autre recombinaison (autre jeu, autre état
limite, autre famille).
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
TOLERANCE = 1e-6
# Valeurs non arrondies du lot 50 bis (pontons_alu_01.lot50bis.family_summary sur
# resultats/livrables/, jeu B), 17 chiffres significatifs ; valeur publiée entre
# parenthèses dans le libellé.
REFERENCES = (
    ("|MFY| max des poutres principales, ELU B (53,2175 kN·m)", 53217.46915097667),
    ("N min des pannes secondaires, ELU B (−85,6 kN)", -85649.60688741648),
    ("N min du profilé support SUP_1, ELU B (−58,0 kN)", -58007.69303457486),
)
PUBLISHED = (53217.5, -85600.0, -58000.0)
PUBLISHED_STEP = (0.1, 100.0, 100.0)
"""Valeurs publiées par la consigne et leur pas d'arrondi (N, N·m)."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


def recombine(
    efforts: list[dict[str, str]],
    combinations: Iterable[dict[str, str]],
    keep: Callable[[dict[str, str]], bool],
) -> Iterable[tuple[str, tuple[str, str], dict[str, float]]]:
    """(combinaison, (élément, extrémité), torseur) pour les lignes retenues par
    `keep`, chaque combinaison étant Σ facteur × cas élémentaire."""
    by_end: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in efforts:
        if keep(row):
            end = (row["element"], row["extremite"])
            by_end.setdefault(end, {})[row["cas"]] = [float(row[c]) for c in COMPONENTS]
    for combo in combinations:
        factors = {
            k: float(v)
            for k, v in combo.items()
            if k not in ("combinaison", "etat_limite", "jeu") and float(v) != 0.0
        }
        for end, cases in by_end.items():
            total = [0.0] * len(COMPONENTS)
            for case, factor in factors.items():
                for i, v in enumerate(cases[case]):
                    total[i] += factor * v
            yield combo["combinaison"], end, dict(zip(COMPONENTS, total, strict=True))


def extreme(
    efforts: list[dict[str, str]],
    combinations: list[dict[str, str]],
    keep: Callable[[dict[str, str]], bool],
    value: Callable[[dict[str, float]], float],
    kind: str,
) -> tuple[float, str, tuple[str, str]]:
    best: tuple[float, str, tuple[str, str]] | None = None
    for name, end, torsor in recombine(efforts, combinations, keep):
        v = value(torsor)
        if best is None or (v > best[0] if kind == "max" else v < best[0]):
            best = (v, name, end)
    assert best is not None
    return best


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    efforts = read_csv(folder / "efforts_elementaires.csv")
    combos = [
        c
        for c in read_csv(folder / "combinaisons.csv")
        if c["jeu"] == "B" and c["etat_limite"] in ("ELU_fondamental", "ELU_accidentel")
    ]
    found = (
        extreme(
            efforts,
            combos,
            lambda r: r["famille"] == "POUTRES_PRINC",
            lambda t: abs(t["MFY"]),
            "max",
        ),
        extreme(
            efforts,
            combos,
            lambda r: r["famille"] == "PANNES_SEC",
            lambda t: t["N"],
            "min",
        ),
        extreme(
            efforts, combos, lambda r: r["groupe"] == "SUP_1", lambda t: t["N"], "min"
        ),
    )
    ok = True
    print(f"{len(combos)} combinaisons ELU du jeu B, {len(efforts)} lignes d'efforts")
    for (label, ref), published, step, (v, name, end) in zip(
        REFERENCES, PUBLISHED, PUBLISHED_STEP, found, strict=True
    ):
        relative = abs(v - ref) / abs(ref)
        rounded = round(v / step) * step
        passed = relative <= TOLERANCE and abs(rounded - published) < step / 2
        ok &= passed
        print(
            f"{'OK ' if passed else 'ÉCHEC'} {label} : recombiné {v!r} N(·m), "
            f"lot 50 bis {ref!r}, écart relatif {relative:.3e} ; arrondi {rounded:g} "
            f"(publié {published:g}) ; {name}, élément {end[0]} extrémité {end[1]}"
        )
    print("contrôle de recombinaison :", "réussi" if ok else "ÉCHEC")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
