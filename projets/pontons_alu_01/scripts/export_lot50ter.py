"""Export du lot 50 ter (CSV pour l'EC9, les vues et les plans), lu dans les résultats du
lot 50 bis, sans exécution Code_Aster :

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/export_lot50ter.py \
        [--sortie <répertoire>]

Écrit dans `resultats/export_lot50ter/` (par défaut) les neuf CSV, `recombiner.py` et
`empreintes.sha256`, puis lance `recombiner.py` (contrôle unique, docs/essais_lot50ter.md
§ 1) et le contrôle d'équilibre relu dans les fichiers exportés (§ 2). Le dépôt sur le
partage se fait par copie du répertoire.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from aster_expert.livrables.donnees import Deliverables
from aster_expert.projet.context import load_project
from pontons_alu_01.extensions import resultant
from pontons_alu_01.geometrie import geometry
from pontons_alu_01.lot50ter import (
    CASE_LABELS,
    CASES,
    build_model,
    combination_rows,
    displacement_rows,
    element_rows,
    force_rows,
    load_rows,
    member_rows,
    nodes_rows,
    reaction_rows,
    result_field,
    section_rows,
    sha256,
    write,
)

ROOT = Path(__file__).resolve().parents[3]
RUN = "20261012T144404-2cf50a46"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sortie", type=Path, default=None)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    livrables = ctx.results_dir / "livrables"
    out = args.sortie or ctx.results_dir / "export_lot50ter"
    out.mkdir(parents=True, exist_ok=True)
    comm = ctx.results_dir / "pontons_alu_01.comm"
    etat = json.loads((livrables / "etat.json").read_text("utf-8"))
    comm_sha = sha256(comm)
    if comm_sha != etat["production_comm_sha256"] or not etat[
        "production_run"
    ].endswith(RUN):
        message = "le .comm ou l'exécution ne sont pas ceux du lot 50 bis"
        raise SystemExit(message)
    med = livrables / "med" / "resultats.med"
    source = (
        f"PONTONS-ALU-01, lot 50 bis (P24, P25, MP1200, k = 1) : exécution {RUN}, .comm "
        f"sha256 {comm_sha}, MED des résultats resultats/livrables/med/resultats.med "
        f"sha256 {sha256(med)}, maillage sha256 {sha256(ctx.results_dir / 'pontons_alu_01.mmed')}."
    )
    d = Deliverables(livrables)
    model = build_model(d, comm)
    files: dict[str, int] = {}
    axes = (
        "Repère global : X le long du tablier (X = 0 rotules côté quai, X = 6,25 m axe "
        "des poteaux), Y transversal, Z vertical vers le haut (m NGF)."
    )

    files["noeuds.csv"] = write(
        out / "noeuds.csv",
        f"{source} Unités : m. {axes} noeud = numéro MED (à partir de 1) ; groupes : "
        "groupes de nœuds et de mailles du maillage qui contiennent le nœud.",
        ["noeud", "x", "y", "z", "groupes"],
        nodes_rows(model),
    )
    files["elements.csv"] = write(
        out / "elements.csv",
        f"{source} Unités : m. {axes} element = numéro MED de la maille SEG2 (à partir "
        "de 1 ; = « maille » des CSV du lot 50 bis + 1). Repère local (U4.42.01, "
        "ORIENTATION) : x_l du nœud 1 au nœud 2 ; VECT_Z (0, 0, 1) pour les barres "
        "horizontales et le chevêtre (z_l = projection de +Z, y_l = z_l ∧ x_l) ; VECT_Y "
        "(1, 0, 0) pour les profilés supports et les poteaux (y_l = projection de +X, "
        "z_l = x_l ∧ y_l). Liaisons : LIAISON_SOLIDE (groupes LR_nn) et LIAISON_DDL "
        "(articulations ROT_Sk-ROT_Ck), sans section.",
        [
            "element",
            "type",
            "noeud1",
            "noeud2",
            "famille",
            "groupe",
            "membre",
            "section",
            "yl_x",
            "yl_y",
            "yl_z",
            "zl_x",
            "zl_y",
            "zl_z",
            "excentricite_ou_liaison",
        ],
        element_rows(model),
    )
    files["membres.csv"] = write(
        out / "membres.csv",
        f"{source} Unités : m. {axes} Membre : barre physique entre deux nœuds de "
        "raccord (nœud commun à une autre barre, nœud d'une liaison, appui) ; début = "
        "extrémité de plus petite coordonnée selon l'axe de la famille (X : poutres, "
        "diagonales, pannes ; Y : montants, chevêtre ; Z : supports, poteaux). Raccords : "
        "« membre : nature » séparés par « | » ; nœuds intermédiaires connectés : aucun "
        "par construction (un raccord coupe le membre), colonne gardée vide.",
        [
            "membre",
            "libelle",
            "famille",
            "groupe",
            "section",
            "x_debut",
            "y_debut",
            "z_debut",
            "x_fin",
            "y_fin",
            "z_fin",
            "longueur",
            "noeud_debut",
            "noeud_fin",
            "elements",
            "raccords_debut",
            "raccords_fin",
            "raccords_intermediaires",
        ],
        member_rows(model),
    )
    efge = result_field(d, ctx, "EFGE_ELNO")
    files["efforts_elementaires.csv"] = write(
        out / "efforts_elementaires.csv",
        f"{source} Unités : N, N·m, m. EFGE_ELNO (POU_D_T) aux deux extrémités de chaque "
        "élément, repère local de elements.csv ; convention Code_Aster brute : N > 0 en "
        "traction ; efforts intérieurs, même convention aux deux extrémités (diagramme "
        "continu d'un élément au suivant, sauts aux seuls raccords). abscisse_m : depuis "
        "le début du membre (0 à un nœud de début). Cas : "
        + ", ".join(f"{c} = {CASE_LABELS[c]}" for c in CASES)
        + " (houle Hu, Hd pour 1 kPa ; TA± du jeu A gardés). Familles : poutres "
        "principales, montants, diagonales, pannes, profilés supports, chevêtre (poteaux "
        "hors liste de la consigne : dans elements.csv et membres.csv seulement).",
        [
            "cas",
            "element",
            "membre",
            "groupe",
            "famille",
            "extremite",
            "noeud",
            "abscisse_m",
            "N",
            "VY",
            "VZ",
            "MT",
            "MFY",
            "MFZ",
        ],
        force_rows(model, efge),
    )
    depl = result_field(d, ctx, "DEPL")
    files["deplacements_elementaires.csv"] = write(
        out / "deplacements_elementaires.csv",
        f"{source} Unités : m, rad. DEPL par nœud et par cas élémentaire, repère global. "
        "Cas : " + ", ".join(f"{c} = {CASE_LABELS[c]}" for c in CASES) + ".",
        ["cas", "noeud", "DX", "DY", "DZ", "DRX", "DRY", "DRZ"],
        displacement_rows(depl),
    )
    reac = result_field(d, ctx, "REAC_NODA")
    springs = result_field(d, ctx, "SIEF_ELGA")
    g = geometry()
    centre = np.array([g.parameters["L"], 0.0, g.footing_z])
    reactions = reaction_rows(model, reac, springs, springs.node_of_row(d.mesh), centre)
    files["reactions_elementaires.csv"] = write(
        out / "reactions_elementaires.csv",
        f"{source} Unités : N, N·m, m. Effort de l'appui sur la structure, repère global. "
        "Rotules côté quai : REAC_NODA (P25 : Y > 0 DX DY DZ bloqués ; Y < 0 guidée, DY "
        "libre, RY nulle), moments sans objet. Ressorts de la semelle (RIGI_PARASOL, "
        "DIS_T) cumulés : −Σ k·u (SIEF_ELGA N, VY, VZ selon X, Y, Z), moment par rapport "
        "au point (x, y, z) de la ligne (axe des poteaux, plan moyen de la semelle).",
        [
            "cas",
            "appui",
            "noeud",
            "x",
            "y",
            "z",
            "RX",
            "RY",
            "RZ",
            "MX",
            "MY",
            "MZ",
            "remarque",
        ],
        reactions,
    )
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        "PONTONS-ALU-01, jeux B (PRO, EN 1990) et B′ (P27 : B sans Q ou Q½ concomitant "
        "à la houle ; proposition à trancher par MM), pontons_alu_01.combinaisons. Une "
        "ligne par combinaison et par jeu (B′ ⊂ B, mêmes noms). Facteurs sans dimension "
        "appliqués aux cas élémentaires de efforts/deplacements/reactions_elementaires.csv, "
        "échelle de la houle comprise (HU, HD : cas de 1 kPa, houle de 5 kPa, facteur = "
        "γ·ψ × 5). Cas : " + ", ".join(f"{c} = {CASE_LABELS[c]}" for c in CASES) + ".",
        ["combinaison", "etat_limite", "jeu", *CASES],
        combination_rows(),
    )
    files["charges.csv"] = write(
        out / "charges.csv",
        f"{source} Unités : N/m (répartie), N (ponctuelle), m/s2 (pesanteur), K (écart de "
        "température), m. Charges du .comm (pas de la consigne), repère global ; "
        "direction : vecteur unitaire, valeur signée selon ce vecteur. Répartie : début et "
        "fin du groupe chargé (coordonnées, et abscisse s le long de la barre dans "
        "« source »). Ressorts et appuis : voir elements.csv et reactions_elementaires.csv.",
        [
            "cas",
            "type",
            "groupe_ou_elements",
            "dir_x",
            "dir_y",
            "dir_z",
            "valeur",
            "unite",
            "x_debut",
            "y_debut",
            "z_debut",
            "x_fin",
            "y_fin",
            "z_fin",
            "source",
        ],
        load_rows(model),
    )
    files["sections.csv"] = write(
        out / "sections.csv",
        f"{source} Unités : m, m2, m4 ; AY, AZ : coefficients de cisaillement de "
        "Code_Aster (A/Av, sans dimension). AFFE_CARA_ELEM/POUTRE : mots-clés affectés, "
        "puis caractéristiques que Code_Aster en déduit (formules et tableaux de U4.42.01, "
        "R3.08.03, recalculés ici : Code_Aster ne les imprime qu'avec INFO = 2). IY, IZ "
        "dans le repère local de elements.csv (MP1200 : IY = inertie forte, y_l horizontal).",
        ["section", "groupes", "type", "cara", "valeur", "unite", "origine"],
        section_rows(model),
    )

    shutil.copyfile(
        Path(__file__).resolve().parent / "recombiner.py", out / "recombiner.py"
    )
    names = [*files, "recombiner.py"]
    (out / "empreintes.sha256").write_text(
        "".join(f"{sha256(out / n)}  {n}\n" for n in names), encoding="utf-8"
    )
    for name, count in files.items():
        print(f"{name} : {count} lignes de données")

    # Équilibre de chaque cas relu dans les fichiers (docs/essais_lot50ter.md § 2).
    worst = 0.0
    for case in CASES:
        lines = [r for r in reactions if r[0] == case]
        total = np.sum([np.array(r[6:9], dtype=float) for r in lines], axis=0)
        applied = resultant(ctx, case)["as_evaluated"]
        load = np.array([applied[c] for c in ("DX", "DY", "DZ")])
        # Échelle : la charge, ou la plus grande réaction pour un cas autoéquilibré.
        scale = max(
            float(np.abs(load).max()),
            *(abs(float(v)) for r in lines for v in r[6:9]),
            1.0,
        )
        residual = float(np.abs(total + load).max()) / scale
        worst = max(worst, residual)
        print(f"équilibre {case} : résidu relatif {residual:.3e}")
    print(f"équilibre : résidu relatif maximal {worst:.3e}")

    result = subprocess.run(
        [sys.executable, "-I", str(out / "recombiner.py"), str(out)],
        check=False,
        capture_output=True,
        text=True,
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode or (1 if worst > 1e-6 else 0)


if __name__ == "__main__":
    sys.exit(main())
