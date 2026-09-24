"""Lot 34 : tableaux de résultats (Markdown) à partir des rapports JSON versionnés
de `data/examples/lot34_equilibre/rapports/` -- aucune valeur recopiée à la main.

Usage : python scripts/report_lot34.py [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "examples" / "lot34_equilibre" / "rapports"
COMPONENTS = ("DX", "DY", "DZ")


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((REPORTS / name).read_text(encoding="utf-8"))
    return data


def _e(value: float) -> str:
    return f"{value:+.3e}"


def probe_table(label: str, report: dict[str, Any]) -> str:
    """Charge assemblée par Code_Aster contre charge intégrée, composante Y et
    écart relatif maximal des trois composantes, par cas."""
    lines = [
        f"**{label}**",
        "",
        "| Cas | Assemblée Y (N) | Intégrée, profil spécifié Y (N) | Écart rel. max | "
        "Verdict | Écart rel. max, règle nodale | Verdict |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    for case, v in report["cases"].items():
        gap = max(abs(x) for x in v["relative_gap"].values())
        ev = v.get("as_evaluated")
        evaluated = (
            "— | —"
            if ev is None
            else (
                f"{max(abs(x) for x in ev['relative_gap'].values()):.2e} "
                f"| {ev['verdict']}"
            )
        )
        lines.append(
            f"| {case} | {v['assembled_n']['DY']:.9e} | {v['integrated_n']['DY']:.9e} "
            f"| {gap:.2e} | {v['verdict']} | {evaluated} |"
        )
    return "\n".join(lines)


def balance_table(label: str, report: dict[str, Any]) -> str:
    """Bilan d'équilibre par cas et composante."""
    lines = [
        f"**{label}**",
        "",
        "| Cas | Composante | Appliquée (N) | Réactions bloquées (N) | Ressorts (N) "
        "| Bilan (N) | Écart relatif |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for group in ("cases", "informative_cases"):
        for case, v in report.get(group, {}).items():
            tag = case if group == "cases" else f"{case} (informatif)"
            for c in COMPONENTS:
                t = v["components"][c]
                lines.append(
                    f"| {tag} | {c[1]} | {t['applied_as_evaluated_n']:.9e} "
                    f"| {t['reactions_blocked_n']:.9e} "
                    f"| {t['springs_on_structure_n']:.9e} "
                    f"| {_e(t['balance_n'])} | {t['relative_gap']:.2e} |"
                )
    return "\n".join(lines)


def combined_table_note(report: dict[str, Any]) -> str:
    """La table combinée du lot 33 (quatre groupes dans un seul `RESULTANTE`)
    contre la somme des réactions par groupe : elles diffèrent."""
    lines = [
        "| Cas | DY table combinée (N) | DY somme des 4 groupes (N) | "
        "DY ancrages seuls (N) |",
        "|---|---:|---:|---:|",
    ]
    for case, v in report["cases"].items():
        parts = v["reactions_by_group_n"]
        total = sum(
            parts[g]["DY"] for g in ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D")
        )
        lines.append(
            f"| {case} | {v['lot33_combined_table_n']['DY']:.9e} | {total:.9e} "
            f"| {parts['ANCRAGES']['DY']:.9e} |"
        )
    return "\n".join(lines)


def symmetry_table(report: dict[str, Any]) -> str:
    lines = [
        "| Cas | Paires | Sans image | Pire écart relatif |",
        "|---|---:|---:|---:|",
    ]
    for case, v in report["symmetry"].items():
        lines.append(
            f"| {case} | {v['n_pairs_checked']} | {v['n_unmatched']} "
            f"| {v['worst_relative_gap']:.2e} |"
        )
    return "\n".join(lines)


def gravity_table(balance: dict[str, Any], integrals: dict[str, Any]) -> str:
    g = integrals["cases"]["G"]
    z = balance["cases"]["G"]["components"]["DZ"]
    rows = [
        ("Poids tubes + palplanches + tirants (maillage)", -integrals["weight_mesh_n"]),
        ("  dont poids analytique", -integrals["weight_analytic_n"]),
        ("Composante verticale de la pression sur l'écran", g["screen_n"]["DZ"]),
        (
            "Composante verticale de la poutre (poids propre + charge)",
            g["beam_n"]["DZ"],
        ),
        ("Résultante verticale appliquée", z["applied_as_evaluated_n"]),
        (
            "Réactions verticales bloquées (ancrages + pied des tubes)",
            z["reactions_blocked_n"],
        ),
        ("Bilan vertical", z["balance_n"]),
    ]
    lines = ["| Terme | N |", "|---|---:|"]
    lines += [f"| {name} | {value:.9e} |" for name, value in rows]
    lines.append(f"| Écart relatif | {z['relative_gap']:.2e} |")
    return "\n".join(lines)


def full_report() -> str:
    balance = _load("equilibre_modele_complet.json")
    integrals = _load("integrale_modele_complet.json")
    parts = [
        "# Lot 34 -- tableaux de résultats (générés par scripts/report_lot34.py)",
        "",
        "## Quai réduit, étape 1 : charge assemblée contre charge intégrée",
        "",
        probe_table(
            "Référence indépendante du lot 33 (tri des paires), application unique, "
            "tables à 6 chiffres",
            _load("initiale_ecran.json"),
        ),
        "",
        probe_table(
            "Référence par couche, application unique de la fonction doublée, "
            "tables à 12 chiffres",
            _load("sonde_ecran_12chiffres.json"),
        ),
        "",
        probe_table(
            "Référence par couche, application par couche (correction), tables à 12 "
            "chiffres",
            _load("sonde_ecran_couches.json"),
        ),
        "",
        "## Quai réduit, étape 2 : bilan d'équilibre (modèle corrigé)",
        "",
        balance_table("Quai réduit", _load("equilibre_quai_reduit_v3.json")),
        "",
        "## Modèle complet, étape 4 : bilan d'équilibre",
        "",
        balance_table("Modèle complet", balance),
        "",
        "### Table combinée du lot 33 (à ne pas lire)",
        "",
        combined_table_note(balance),
        "",
        "### Symétrie (20 057 paires par cas, seuil 1e-6)",
        "",
        symmetry_table(balance),
        "",
        "### Pesanteur, cas G, direction verticale",
        "",
        gravity_table(balance, integrals),
        "",
    ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORTS / "tableaux_lot34.md")
    args = parser.parse_args(argv)
    text = full_report()
    args.output.write_text(text, encoding="utf-8")
    print(f"tableaux écrits dans {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
