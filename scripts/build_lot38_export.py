"""Lot 38, étapes 2 et 5 : combinaisons de D17 appliquées à la poutre de
couronnement, export tabulaire (CSV/Markdown) et contrôle manuel d'une combinaison.

Source des efforts élémentaires : le `.mess` (`fort.6`) d'une exécution déjà
réalisée du modèle complet (`data/processed/runs/20260925T125131-c67e28a1`),
dont le `.comm` exécuté est identique (sha256) à celui versionné
(`data/examples/lot37_efforts/complet.comm`, inchangé par le lot 38) :
`DIAGNOSTIC JOB : OK`, aucune alarme. Aucune nouvelle exécution n'est nécessaire
pour cet export -- la combinaison elle-même est un calcul linéaire fait dans
l'outil (voir `aster_expert.report.combinations`).

`EFGE_ELNO` n'est pas moyenné par Code_Aster (lot 35) : un nœud intérieur porte
deux valeurs (une par élément adjacent). Ce script moyenne les deux pour
l'export -- une simplification pour la lisibilité, signalée dans le
Markdown produit, jamais pour un contrôle d'équilibre.

Usage : python scripts/build_lot38_export.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aster_expert.report.combinations import (  # noqa: E402
    CASES,
    Combination,
    combine,
    enumerate_combinations,
)

MESS = (
    ROOT
    / "data"
    / "processed"
    / "runs"
    / "20260925T125131-c67e28a1"
    / "proc.0"
    / "fort.6"
)
EXPORTED_COMM = ROOT / "data" / "examples" / "lot37_efforts" / "complet.comm"
OUT_DIR = ROOT / "data" / "examples" / "lot38_combinaisons"
COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
_MARKER = re.compile(r"^##EFPOUT_(\w+)ASTER\s")


def _parse_beam_tables(text_lines: list[str]) -> dict[str, dict[str, list[dict]]]:
    """`{case: {node: [{"x":.., **components}]}}` -- one row per (node, element);
    rows of the same node are kept separate here, averaged by the caller."""
    out: dict[str, list[dict]] = {}
    i = 0
    n = len(text_lines)
    while i < n:
        m = _MARKER.match(text_lines[i])
        if m is None:
            i += 1
            continue
        case = m.group(1)
        header = text_lines[i + 1].split()
        rows = []
        j = i + 2
        while j < n and text_lines[j].strip() and not text_lines[j].startswith("#"):
            cells = text_lines[j].split()
            width = len(COMPONENTS) + 6  # MAILLE, NOEUD, SOUS_POINT, COOR_X/Y/Z
            numeric = [float(c) for c in cells[-width:]]
            names = header[-width:]
            rows.append(dict(zip(names, numeric, strict=True)))
            j += 1
        out[case] = rows
        i = j
    return out


def _average_by_node(rows: list[dict]) -> dict[int, dict[str, float]]:
    by_node: dict[int, list[dict]] = {}
    for row in rows:
        by_node.setdefault(int(row["NOEUD"]), []).append(row)
    result: dict[int, dict[str, float]] = {}
    for node, group in by_node.items():
        result[node] = {
            "x": group[0]["COOR_X"],
            **{c: sum(g[c] for g in group) / len(group) for c in COMPONENTS},
        }
    return result


def _load_cases() -> tuple[dict[str, dict[int, dict[str, float]]], str]:
    lines = MESS.read_text(encoding="utf-8", errors="strict").splitlines()
    raw = _parse_beam_tables(lines)
    missing = set(CASES) - set(raw)
    if missing:
        message = f"cas manquants dans {MESS} : {sorted(missing)}"
        raise SystemExit(message)
    diag_lines = [line for line in lines if "DIAGNOSTIC JOB" in line]
    return {case: _average_by_node(raw[case]) for case in CASES}, diag_lines[-1].strip()


def _combined(
    cases: dict[str, dict[int, dict[str, float]]],
) -> dict[str, dict[int, dict[str, float]]]:
    """`{combination_name: {node: {"x":.., **components}}}`."""
    nodes = sorted(next(iter(cases.values())))
    out: dict[str, dict[int, dict[str, float]]] = {}
    for combination in enumerate_combinations():
        per_node: dict[int, dict[str, float]] = {}
        for node in nodes:
            x = cases["G"][node]["x"]
            values = {
                comp: combine(
                    combination.coefficients,
                    {
                        case: cases[case][node][comp]
                        for case in combination.coefficients
                    },
                )
                for comp in COMPONENTS
            }
            per_node[node] = {"x": x, **values}
        out[combination.name] = per_node
    return out


def _extrema(
    per_node: dict[int, dict[str, float]],
) -> dict[str, dict[str, object]]:
    """Pour chaque composante, le nœud extrémal et les composantes concomitantes."""
    out: dict[str, dict[str, object]] = {}
    for comp in COMPONENTS:
        node = max(per_node, key=lambda n: abs(per_node[n][comp]))
        out[comp] = {"node": node, **per_node[node]}
    return out


def _manual_check(
    cases: dict[str, dict[int, dict[str, float]]],
    combinations: list[Combination],
    bollard_node: int,
) -> dict[str, object]:
    """ELU fondamentale, Q3 dominante, sans Q1, γG défavorable, au nœud du bollard :
    recalcul à la main à partir des tables élémentaires, comparé à `combine()`."""
    target = next(c for c in combinations if c.name == "ELU_FOND_Q3_DOM_G_defav")
    hand = {}
    for comp in COMPONENTS:
        g = cases["G"][bollard_node][comp]
        eau_p = cases["EAU_P"][bollard_node][comp]
        q3 = cases["Q3"][bollard_node][comp]
        hand[comp] = 1.35 * (g + eau_p) + 1.5 * q3
    code = {
        comp: combine(
            target.coefficients,
            {case: cases[case][bollard_node][comp] for case in target.coefficients},
        )
        for comp in COMPONENTS
    }
    gaps = {c: abs(hand[c] - code[c]) for c in COMPONENTS}
    return {
        "combination": target.name,
        "coefficients": target.coefficients,
        "node": bollard_node,
        "hand": hand,
        "code": code,
        "max_absolute_gap": max(gaps.values()),
    }


def main() -> int:
    cases, diagnostic = _load_cases()
    combinations = enumerate_combinations()
    combined = _combined(cases)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Nœud du bollard : X = 0 (axe de TUBE_05, décision du point 9), Y = 0,34 (axe
    # de la poutre), Z = 3,30.
    bollard = min(
        cases["G"],
        key=lambda n: abs(cases["G"][n]["x"]),
    )
    check = _manual_check(cases, combinations, bollard)

    with (OUT_DIR / "combinaisons.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["combinaison", "famille", "noeud", "x_m", *COMPONENTS])
        for combination in combinations:
            for node, values in sorted(combined[combination.name].items()):
                writer.writerow(
                    [
                        combination.name,
                        combination.family,
                        node,
                        f"{values['x']:.6f}",
                        *(f"{values[c]:.6e}" for c in COMPONENTS),
                    ]
                )

    with (OUT_DIR / "extrema.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "combinaison",
                "famille",
                "composante_extremale",
                "noeud",
                "x_m",
                *COMPONENTS,
            ]
        )
        for combination in combinations:
            extrema = _extrema(combined[combination.name])
            for comp, row in extrema.items():
                writer.writerow(
                    [
                        combination.name,
                        combination.family,
                        comp,
                        row["node"],
                        f"{row['x']:.6f}",
                        *(f"{row[c]:.6e}" for c in COMPONENTS),
                    ]
                )

    lines = [
        "# Poutre de couronnement -- combinaisons de D17 (lot 38)",
        "",
        f"Source : `{MESS.relative_to(ROOT)}` -- {diagnostic}. `.comm` exécuté "
        f"identique (sha256) à `{EXPORTED_COMM.relative_to(ROOT)}`, inchangé par le "
        "lot 38 : aucune nouvelle exécution.",
        "",
        "## Repère et conventions de signe",
        "",
        "Repère global (décision du point 9) : X le long du quai (SYM_G -> SYM_D), "
        "Y vers la terre, Z ascendant, origine dans l'axe de TUBE_05 à la cote "
        "0,00 CM. `N, VY, VZ, MT, MFY, MFZ` sont les composantes de `EFGE_ELNO` "
        "dans le repère « utilisateur » de la poutre (`POU_D_T`, axe porteur x_l "
        "= +X, U2.01.05 « Cas des poutres ») : N effort normal (traction "
        "positive), VY/VZ efforts tranchants, MT moment de torsion, MFY/MFZ "
        "moments de flexion. `EFGE_ELNO` n'étant pas moyenné par Code_Aster, les "
        "deux valeurs d'un nœud intérieur (une par élément adjacent) sont "
        "moyennées ici pour la lisibilité -- une simplification, jamais un "
        "contrôle d'équilibre.",
        "",
        "## Géométrie de section et données D18",
        "",
        "Section rectangulaire : HY = 2,50 m (largeur), HZ = 1,40 m (hauteur), "
        "axe à Y = 0,34 m, Z = 3,30 m. Béton C35/45, acier B500B, classe "
        "d'exposition XS3, durée d'utilisation 100 ans, enrobage nominal 65 mm, "
        "wk = 0,2 mm sous combinaison quasi permanente (décision D18, point 14).",
        "",
        "## Combinaisons (18, décision D17, point 13)",
        "",
        "| Nom | Famille | Coefficients |",
        "| --- | --- | --- |",
    ]
    for combination in combinations:
        coeffs = ", ".join(
            f"{case}={value:g}" for case, value in combination.coefficients.items()
        )
        lines.append(f"| `{combination.name}` | {combination.family} | {coeffs} |")
    lines += [
        "",
        "## Contrôle manuel",
        "",
        f"Combinaison `{check['combination']}` (ELU fondamentale, Q3 dominante, "
        f"sans Q1, γG défavorable), nœud {check['node']} (bollard, X ≈ 0) : "
        "1,35·(G+EAU_P) + 1,5·Q3, recalculé à la main à partir des tables "
        f"élémentaires du `.mess`, contre `combine()` -- écart absolu maximal "
        f"{check['max_absolute_gap']:.3e} (unités N, N.m).",
        "",
        "| Composante | À la main | `combine()` | Écart |",
        "| --- | --- | --- | --- |",
    ]
    for comp in COMPONENTS:
        lines.append(
            f"| {comp} | {check['hand'][comp]:.6e} | {check['code'][comp]:.6e} | "
            f"{abs(check['hand'][comp] - check['code'][comp]):.3e} |"
        )
    lines += [
        "",
        "## Extrema",
        "",
        "Voir `extrema.csv` : pour chaque combinaison, le nœud où chaque "
        "composante est maximale en valeur absolue, avec les composantes "
        "concomitantes.",
        "",
    ]
    (OUT_DIR / "poutre_couronnement.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "controle_manuel.json").write_text(
        json.dumps(check, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{len(combinations)} combinaisons, écart manuel maximal "
        f"{check['max_absolute_gap']:.3e}, écrits dans {OUT_DIR.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
