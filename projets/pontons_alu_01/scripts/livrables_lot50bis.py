"""Livrables du lot 50 bis (CSV seulement) : synthèse par famille avec le taux élastique
simplifié (P28) des jeux B et B′ (P27), pieds des profilés supports, rotules côté quai
(P25), balayage de l'inertie, inertie et module nécessaires, comparaison au lot 50.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/livrables_lot50bis.py \
        [--lot50 <résultats du lot 50>/livrables]

Lit `resultats/livrables/` (k = 1) et `resultats/balayage/k3|k5/livrables/` ; écrit
`resultats/livrables/paquet/lot50bis/`. La comparaison au lot 50 n'est écrite que si le
répertoire des livrables du lot 50 est donné (ils ne sont pas versionnés).
"""

import argparse
import json
from pathlib import Path

from aster_expert.projet.context import load_project
from pontons_alu_01.lot50bis import (
    WARNING,
    family_summary,
    hinge_reactions,
    lot50_comparison,
    needed_inertia,
    sections,
    support_feet,
    sweep_point,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[3]
UNITS = "Unités : kN, kN·m, mm, mm³, mm⁴ ; repère local de projet.yaml (MFY = My)."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lot50", type=Path, default=None)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    reference = ctx.results_dir / "livrables"
    out = reference / "paquet" / "lot50bis"
    out.mkdir(parents=True, exist_ok=True)
    files = {}

    summary = family_summary(ctx, reference)
    write_csv(out / "synthese_familles.csv", summary, f"{WARNING} {UNITS}")
    files["synthese_familles.csv"] = len(summary)
    feet = support_feet(ctx, reference)
    write_csv(
        out / "profiles_supports_pieds.csv",
        feet,
        "Efforts des profilés supports au pied (Z = +1,09), transmis au chevêtre par "
        "l'articulation (P18) ; repère local x_l = +Z (N > 0 traction), y_l = +X (VY), "
        "z_l = +Y (VZ). kN.",
    )
    files["profiles_supports_pieds.csv"] = len(feet)
    hinges = hinge_reactions(ctx, reference)
    write_csv(
        out / "rotules_quai.csv",
        hinges,
        "Réactions des rotules côté quai (P25 : Y > 0 fixe, Y < 0 guidée, DY libre), "
        "repère global, effort de l'appui sur la structure. kN.",
    )
    files["rotules_quai.csv"] = len(hinges)

    table = [sweep_point(ctx, reference, 1.0)]
    for k in (3, 5):
        root = ctx.results_dir / "balayage" / f"k{k}" / "livrables"
        table.append(sweep_point(ctx, root, float(k)))
    write_csv(
        out / "balayage_inertie.csv",
        table,
        "Balayage de l'inertie des poutres principales (IY = k × IY du MP1200, A et IZ "
        "inchangés). Flèche relative : UZ moins la corde des appuis X = 0 et X = L de la "
        "même poutre (tassement de la semelle retiré) ; UZ absolu : poutres "
        "principales. ELS caractéristique ; « variables » : G1 et G2 retirés. My et Wel "
        f"nécessaire : ELU fondamental et accidentel. {WARNING} {UNITS}",
    )
    files["balayage_inertie.csv"] = len(table)
    needed = needed_inertia(ctx, table)
    write_csv(
        out / "inertie_necessaire.csv",
        needed,
        "Inertie nécessaire d'une poutre principale pour une flèche relative sous "
        "actions variables (ELS caractéristique) de L/200, L/250, L/300 : ajustement "
        "f(k) = a + b/k sur k = 1, 3, 5 (docs/essais_lot50bis.md § 3).",
    )
    files["inertie_necessaire.csv"] = len(needed)
    if args.lot50 is not None:
        cmp = lot50_comparison(ctx, args.lot50, reference)
        write_csv(
            out / "comparaison_lot50.csv",
            cmp,
            "Effet de P24 et P25 : lot 50 (B = 1,50, rotules fixes, largeur chargée "
            "1,50 m) contre lot 50 bis (B = 1,86, rotule Y < 0 guidée, 2,00 m). kN, kN·m.",
        )
        files["comparaison_lot50.csv"] = len(cmp)
    secs = {
        k: {
            "section": s.name,
            "A_mm2": s.area * 1e6,
            "Wel_y_mm3": s.w_y * 1e9,
            "Wel_z_mm3": s.w_z * 1e9,
            "Av_mm2": s.a_v * 1e6,
            "f0_MPa": s.f0 * 1e-6,
            "f0_haz_MPa": s.f0_haz * 1e-6,
            "gamma_M1": s.gamma_m1,
            "source": s.source,
        }
        for k, s in sections(ctx).items()
    }
    (out / "lot50bis.json").write_text(
        json.dumps(
            {"avertissement": WARNING, "sections": secs, "fichiers": files},
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for name, n in files.items():
        print(name, n, "lignes")


if __name__ == "__main__":
    main()
