"""Lot 36 : met en forme en Markdown les chiffres de l'étape 1 (vérification à la main)
et de l'étape 2 (part de chaque cause), lus des JSON produits par
`analyze_lot36_noeuds.py` et `analyze_lot36_butee.py`. Aucun nombre n'est recalculé ici.

Usage : python scripts/render_lot36_butee_md.py <noeuds.json> <butee.json> <sortie.md>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _n(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def step1(nodes: dict[str, Any]) -> list[str]:
    lines = [
        "## Étape 1 — vérification à la main (cas G, base)",
        "",
        "Aire tributaire A : lue de l'analytique (`spring_node_areas`), jamais déduite de la "
        "raideur ; raideur k : lue du `.comm` (`VALE` de la classe du nœud) ; DY : MED/`.mess`.",
        "",
        "| | Nœud le plus sollicité en compression | Nœud en traction le plus sollicité |",
        "|---|---|---|",
    ]
    c, t = (
        nodes["compression_taux_bassin_maximal"],
        nodes["traction_taux_terre_maximal"],
    )
    rows = [
        (
            "Nœud, porteur",
            f"N{c['noeud']}, {c['porteur']}",
            f"N{t['noeud']}, {t['porteur']}",
        ),
        ("Cote z (m CM)", _n(c["z"], 2), _n(t["z"], 2)),
        ("Groupe de raideur du `.comm`", c["groupe_comm"], t["groupe_comm"]),
        ("Aire tributaire A (m²)", _n(c["aire_A_m2"], 6), _n(t["aire_A_m2"], 6)),
        (
            "Raideur k (N/m)",
            _n(c["raideur_k_comm_N_par_m"], 2),
            _n(t["raideur_k_comm_N_par_m"], 2),
        ),
        ("k / A (MN/m³)", _n(c["k_sur_A_MN_m3"], 6), _n(t["k_sur_A_MN_m3"], 6)),
        (
            "k_h de la couche (MN/m³)",
            _n(next(iter(c["k_h_couche_MN_m3"].values())), 3),
            _n(next(iter(t["k_h_couche_MN_m3"].values())), 3),
        ),
        ("DY (mm)", _n(c["DY_m"] * 1e3, 4), _n(t["DY_m"] * 1e3, 4)),
        (
            "Pression k·DY/A (kPa)",
            _n(c["pression_kDY_sur_A_kPa"], 2),
            _n(t["pression_kDY_sur_A_kPa"], 2),
        ),
        (
            "σ'p bassin en z (kPa)",
            _n(c["butee_bassin_kPa"], 2),
            _n(t["butee_bassin_kPa"], 2),
        ),
        (
            "Taux vs butée bassin",
            _n(c["taux_butee_bassin"] * 100, 1) + " %"
            if c["taux_butee_bassin"]
            else "—",
            "—",
        ),
        (
            "Butée côté terre en z (kPa)",
            _n(c["butee_terre_kPa"], 2),
            _n(t["butee_terre_kPa"], 2),
        ),
        ("Taux vs butée terre", "—", _n(t["taux_butee_terre"] * 100, 2) + " %"),
    ]
    lines += [f"| {a} | {b} | {d} |" for a, b, d in rows]
    lines += [
        "",
        "Vérification à la main du nœud en compression : k/A vaut le k_h de la couche "
        f"({_n(c['k_sur_A_MN_m3'], 6)} MN/m³) ; A = ¼ × (largeur projetée des deux facettes "
        "voisines) × hauteur de maille, soit ¼ × (R(1−cos 9°) + R(cos 9° − cos 18°)) × 0,25 m "
        "avec R = 0,71 m, ce qui donne 0,0348 × 0,25 / 4 = 0,002172 m² : aucune erreur "
        "d'aire tributaire ni d'unité (MN/m³ × 1e6 = N/m³).",
        "",
    ]
    return lines


def _row(label: str, base: Any, v1: Any) -> str:
    return f"| {label} | {base} | {v1} |"


def step2(d: dict[str, Any]) -> list[str]:
    b, v = d["base"], d["V1"]
    bc, vc, bt, vt = b["compression"], v["compression"], b["traction"], v["traction"]
    lines = [
        "## Étape 2 — part de chaque cause (cas G, modèle complet, 10 433 nœuds à ressort)",
        "",
        "| Grandeur | Base | V1 (pression initiale côté bassin) |",
        "|---|---:|---:|",
        _row("Nœuds en compression", _int(bc["n"]), _int(vc["n"])),
        _row(
            "Taux maximal de butée bassin",
            _n(bc["taux_max"] * 100, 1) + " %",
            _n(vc["taux_max"] * 100, 1) + " %",
        ),
        _row(
            "Nœud du taux maximal",
            f"N{bc['noeud_taux_max']['noeud']}, z = {_n(bc['noeud_taux_max']['z'], 2)}",
            f"N{vc['noeud_taux_max']['noeud']}, z = {_n(vc['noeud_taux_max']['z'], 2)}",
        ),
        _row(
            "Nœuds au-delà de 100 %",
            _int(bc["n_au_dela_100"]),
            _int(vc["n_au_dela_100"]),
        ),
        _row(
            "Force de compression totale des ressorts (MN)",
            _n(bc["force_totale_compression_N"] / 1e6, 2),
            _n(vc["force_totale_compression_N"] / 1e6, 2),
        ),
        _row(
            "Dont force en excès de la butée (MN)",
            _n(bc["force_en_exces_N"] / 1e6, 2),
            _n(vc["force_en_exces_N"] / 1e6, 2),
        ),
        _row("Nœuds en traction", _int(bt["n"]), _int(vt["n"])),
        _row(
            "Pression de traction maximale (kPa)",
            _n(bt["pression_max_kPa"], 1),
            _n(vt["pression_max_kPa"], 1),
        ),
        _row(
            "Force de traction totale (MN)",
            _n(bt["force_totale_traction_N"] / 1e6, 2),
            _n(vt["force_totale_traction_N"] / 1e6, 2),
        ),
        _row(
            "Taux maximal vs butée limite **côté terre**",
            _n(bt["taux_max_vs_butee_terre"] * 100, 2) + " %",
            _n(vt["taux_max_vs_butee_terre"] * 100, 2) + " %",
        ),
        _row(
            "Nœuds en traction **au-delà** de la butée côté terre",
            _int(bt["n_au_dela_butee_terre"]),
            _int(vt["n_au_dela_butee_terre"]),
        ),
        _row(
            "Cote de pivot, génératrice bassin de TUBE_05 (m CM)",
            _n(b["cote_pivot_tube_central_bassin"], 2),
            _n(v["cote_pivot_tube_central_bassin"], 2),
        ),
        "",
        "### Contrôle corrigé du signe : nœuds en traction contre la butée limite côté terre "
        "(Kp·σ'v + 2c'·√Kp)",
        "",
        "| Couche | Modèle | Nœuds en traction | Pression max (kPa) | Butée terre au nœud du taux max (kPa) | Taux max | Au-delà |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for label, run in (("base", bt), ("V1", vt)):
        for layer, x in run["par_couche"].items():
            lines.append(
                f"| {layer} | {label} | {_int(x['n'])} | {_n(x['pression_max_kPa'], 1)} | "
                f"{_n(x['butee_terre_au_noeud_du_taux_max_kPa'], 1)} | {_n(x['taux_max'] * 100, 2)} % | "
                f"{_int(x['n_au_dela_butee_terre'])} |"
            )
    lines += [
        "",
        "σ'v côté terre : stratigraphie du cas de test (§5), nappe à +2,00 (§6), terre-plein à "
        "+4,00 ; γ au-dessus de la nappe, γ' au-dessous. Ce calcul retrouve à 0,1 kPa près le "
        "profil de poussée active de l'annexe A.4 (test unitaire).",
        "",
        "### V2 — sans exécution supplémentaire",
        "",
        "| Lecture | Taux maximal | Nœuds au-delà de 100 % |",
        "|---|---:|---:|",
        f"| Base (référence) | {_n(bc['taux_max'] * 100, 1)} % | {_int(bc['n_au_dela_100'])} |",
        f"| V2, lecture littérale : (réaction de la base − pression initiale de V1)⁺ / σ'p bassin | "
        f"{_n(bc['taux_V2_max'] * 100, 1)} % | {_int(bc['n_V2_au_dela_100'])} |",
        f"| Lecture voisine : pression initiale de V1 **ajoutée** à la réaction de V1, / σ'p bassin | "
        f"{_n(vc['taux_V1_reaction_plus_repos_max'] * 100, 1)} % | "
        f"{_int(vc['n_V1_reaction_plus_repos_au_dela_100'])} |",
        "",
        "L'énoncé ne dit pas laquelle des deux lectures est celle de la figure F.1.1 : les deux "
        "sont rapportées, aucune n'est retenue. Le taux maximal est identique dans les trois "
        "cas parce que le nœud du maximum est à z = −12,00, où la pression initiale est nulle.",
        "",
        "### Où se trouvent les dépassements (nœuds au-delà de 100 % / nœuds en compression)",
        "",
        "| Tranche de cote (m CM) | Base | V1 |",
        "|---|---:|---:|",
    ]
    bins_b, bins_v = bc["par_tranche_de_cote_1m"], vc["par_tranche_de_cote_1m"]
    for key in bins_b:
        if bins_b[key]["n_au_dela_100"] or bins_v[key]["n_au_dela_100"]:
            lines.append(
                f"| {key} | {bins_b[key]['n_au_dela_100']} / {bins_b[key]['n_compression']} | "
                f"{bins_v[key]['n_au_dela_100']} / {bins_v[key]['n_compression']} |"
            )
    e = d["ecarts_base_V1"]
    lines += [
        "",
        "### Ce que chaque cause attribue (chiffres seulement, aucune conclusion de conception)",
        "",
        f"1. **Ressorts linéaires non plafonnés** : {_n(bc['force_en_exces_N'] / 1e6, 2)} MN sur "
        f"{_n(bc['force_totale_compression_N'] / 1e6, 2)} MN de compression "
        f"({_n(100 * bc['force_en_exces_N'] / bc['force_totale_compression_N'], 1)} %) dépassent la "
        "force de butée de leur nœud, dans le modèle de base ; les dépassements sont sur les "
        "tranches −12 à −17 m.",
        f"2. **Pression initiale au repos côté bassin (V1)** : les nœuds au-delà de 100 % passent de "
        f"{_int(bc['n_au_dela_100'])} à {_int(vc['n_au_dela_100'])} ({e['n_au_dela_100']:+d}), le taux "
        f"maximal de {_n(bc['taux_max'] * 100, 1)} % à {_n(vc['taux_max'] * 100, 1)} % ; la force de "
        f"compression baisse de {_n((bc['force_totale_compression_N'] - vc['force_totale_compression_N']) / 1e6, 2)} MN.",
        f"3. **Absence de ressorts côté terre** : {_int(bt['n'])} nœuds en traction "
        f"({_n(100 * bt['n'] / b['n_noeuds'], 1)} % des nœuds à ressort), pression maximale "
        f"{_n(bt['pression_max_kPa'], 1)} kPa, soit {_n(bt['taux_max_vs_butee_terre'] * 100, 2)} % de la "
        f"butée limite côté terre ; {_int(bt['n_au_dela_butee_terre'])} nœud au-delà. Sous V1 : "
        f"{_int(vt['n'])} nœuds, {_n(vt['taux_max_vs_butee_terre'] * 100, 2)} %, "
        f"{_int(vt['n_au_dela_butee_terre'])} au-delà.",
        "",
    ]
    return lines


def main(nodes_path: Path, butee_path: Path, out: Path) -> int:
    nodes = json.loads(nodes_path.read_text(encoding="utf-8"))
    butee = json.loads(butee_path.read_text(encoding="utf-8"))
    text = "\n".join(
        ["# Lot 36 — diagnostic de la butée sous G", "", *step1(nodes), *step2(butee)]
    )
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a) for a in sys.argv[1:4])))
