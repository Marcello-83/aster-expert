"""Lot 36, étape 2 : part de chaque cause du dépassement de butée, sous G.

Lit les MED de résultats de la base et de V1 (`aster_expert.report.med_source`,
`medcoupling` dans le conteneur) et, pour chaque nœud à ressort du cas G :

- compression (DY < 0) : taux = k·|DY| / force de butée du nœud (Σ_bandes aire × σ'p
  bassin) ; nombre de nœuds au-delà de 100 % ;
- traction (DY > 0) : pression k·DY / A comparée à la butée limite **côté terre**
  (Rankine, `aster_expert.generation.terre`) ; nombre de nœuds au-delà, tableau par
  couche ;
- V2 (aucune exécution) : sur les nœuds en compression de la base, la pression de
  réaction moins la pression initiale de V1 (nulle si négative), rapportée à la butée
  bassin ; lecture voisine, nommée à part : pression initiale **ajoutée** à la
  réaction de V1.

Constats chiffrés seulement : aucun verdict, aucune conclusion de conception.

Usage : python scripts/analyze_lot36_butee.py <données> <MED base> <MED V1> \\
    <sortie.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.terre import REPOS_TABLE_KPA
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.combiwall import build_params, spring_node_areas
from aster_expert.report import quantities as q
from aster_expert.report.figures import _spring_key, build_context, pivot_level
from aster_expert.report.med_source import MedData, load_med_data

CASE = "G"
LAYERS = {
    "RESS_AV_ARGI": "argile marneuse (−12,00 à −18,00)",
    "RESS_AV_MARNE": "marne compacte (−18,00 à −26,00)",
}


def _repos_pa() -> dict[str, list[tuple[float, float]]]:
    return {
        band: sorted(((z, p * 1e3) for z, p in pts), key=lambda t: -t[0])
        for band, pts in REPOS_TABLE_KPA.items()
    }


def _arrays(med: MedData, data_path: Path) -> dict[str, np.ndarray]:
    ctx = build_context(data_path)
    data = load_model_data(data_path)
    mv = ModelValues(data)
    params = build_params(data)
    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    repos = q.spring_nodes(spring_node_areas(params), k_h, _repos_pa())
    springs = np.unique(med.conn[-2].ravel())
    xyz = med.coords[springs]
    dy = med.node_field(CASE, "DEPL")[springs, 1]
    keys = [_spring_key(p) for p in xyz]
    nodes = [ctx.spring_nodes[k] for k in keys]
    return {
        "node": springs + 1,
        "x": xyz[:, 0],
        "y": xyz[:, 1],
        "z": xyz[:, 2],
        "dy": dy,
        "k": np.array([n.stiffness for n in nodes]),
        "area": np.array([n.area for n in nodes]),
        "cap_bassin": np.array([n.capacity_n for n in nodes]),
        "cap_terre": np.array([ctx.spring_nodes_terre[k].capacity_n for k in keys]),
        "f0": np.array([repos[k].capacity_n for k in keys]),
        "band_argi": np.array(["RESS_AV_ARGI" in n.band_stiffness for n in nodes]),
        "band_marne": np.array(["RESS_AV_MARNE" in n.band_stiffness for n in nodes]),
    }


def _holder(a: dict[str, np.ndarray], i: int, axes: list[float], radius: float) -> str:
    return q.holder_of(float(a["x"][i]), float(a["y"][i]), axes, radius)


def _node_line(
    a: dict[str, np.ndarray], i: int, axes: list[float], radius: float
) -> dict[str, Any]:
    return {
        "noeud": int(a["node"][i]),
        "porteur": _holder(a, i, axes, radius),
        "x": float(a["x"][i]),
        "y": float(a["y"][i]),
        "z": float(a["z"][i]),
        "DY_mm": float(a["dy"][i] * 1e3),
        "aire_m2": float(a["area"][i]),
        "raideur_N_par_m": float(a["k"][i]),
        "pression_reaction_kPa": float(a["k"][i] * a["dy"][i] / a["area"][i] / 1e3),
        "butee_bassin_kPa": float(a["cap_bassin"][i] / a["area"][i] / 1e3),
        "butee_terre_kPa": float(a["cap_terre"][i] / a["area"][i] / 1e3),
    }


def summarize(
    a: dict[str, np.ndarray], axes: list[float], radius: float
) -> dict[str, Any]:
    dy, k, cap_b, cap_t, f0 = a["dy"], a["k"], a["cap_bassin"], a["cap_terre"], a["f0"]
    comp = dy < 0.0
    tens = dy > 0.0
    ratio = np.where(comp, k * np.abs(dy) / cap_b, 0.0)
    ratio_terre = np.where(tens, k * dy / cap_t, 0.0)
    v2 = np.where(comp, np.maximum(k * np.abs(dy) - f0, 0.0) / cap_b, 0.0)
    out: dict[str, Any] = {
        "n_noeuds": int(len(dy)),
        "compression": {
            "n": int(comp.sum()),
            "taux_max": float(ratio.max()),
            "noeud_taux_max": _node_line(a, int(ratio.argmax()), axes, radius),
            "n_au_dela_100": int((ratio > 1.0).sum()),
            "force_en_exces_N": float(
                np.maximum(k * np.abs(dy) - cap_b, 0.0)[comp].sum()
            ),
            "force_totale_compression_N": float((k * np.abs(dy))[comp].sum()),
            "taux_V2_max": float(v2.max()),
            "n_V2_au_dela_100": int((v2 > 1.0).sum()),
            "taux_V1_reaction_plus_repos_max": float(
                np.where(comp, (f0 + k * np.abs(dy)) / cap_b, 0.0).max()
            ),
            "n_V1_reaction_plus_repos_au_dela_100": int(
                (np.where(comp, (f0 + k * np.abs(dy)) / cap_b, 0.0) > 1.0).sum()
            ),
        },
        "traction": {
            "n": int(tens.sum()),
            "taux_max_vs_butee_terre": float(ratio_terre.max()),
            "noeud_taux_max": _node_line(a, int(ratio_terre.argmax()), axes, radius),
            "n_au_dela_butee_terre": int((ratio_terre > 1.0).sum()),
            "force_totale_traction_N": float((k * dy)[tens].sum()),
            "pression_max_kPa": float((k * dy / a["area"])[tens].max() / 1e3),
            "par_couche": {},
        },
    }
    bins: dict[str, dict[str, int]] = {}
    for top in range(-12, -26, -1):
        inside = (a["z"] <= top + 1e-9) & (a["z"] > top - 1.0 - 1e-9) & comp
        bins[f"{top:d} à {top - 1:d}"] = {
            "n_compression": int(inside.sum()),
            "n_au_dela_100": int((inside & (ratio > 1.0)).sum()),
        }
    out["compression"]["par_tranche_de_cote_1m"] = bins
    axis = axes[len(axes) // 2]
    line = (np.abs(a["x"] - axis) < 1e-6) & (a["y"] < 0)
    out["cote_pivot_tube_central_bassin"] = pivot_level(a["z"][line], dy[line])
    for band, label in LAYERS.items():
        mask = tens & a["band_argi" if band == "RESS_AV_ARGI" else "band_marne"]
        if not mask.any():
            out["traction"]["par_couche"][label] = {"n": 0}
            continue
        idx = np.flatnonzero(mask)
        p = k[idx] * dy[idx] / a["area"][idx] / 1e3
        lim = cap_t[idx] / a["area"][idx] / 1e3
        worst = idx[int(np.argmax(ratio_terre[idx]))]
        out["traction"]["par_couche"][label] = {
            "n": int(mask.sum()),
            "pression_max_kPa": float(p.max()),
            "butee_terre_au_noeud_du_taux_max_kPa": float(
                cap_t[worst] / a["area"][worst] / 1e3
            ),
            "taux_max": float(ratio_terre[worst]),
            "n_au_dela_butee_terre": int((ratio_terre[idx] > 1.0).sum()),
            "z_min": float(a["z"][idx].min()),
            "z_max": float(a["z"][idx].max()),
            "butee_terre_min_kPa": float(lim.min()),
        }
    top = np.argsort(-ratio_terre)[:5]
    out["traction"]["cinq_taux_les_plus_eleves"] = [
        {
            **_node_line(a, int(i), axes, radius),
            "taux_vs_butee_terre": float(ratio_terre[i]),
        }
        for i in top
        if ratio_terre[i] > 0.0
    ]
    return out


def main(data_path: Path, med_base: Path, med_v1: Path, out: Path) -> int:
    ctx = build_context(data_path)
    result: dict[str, Any] = {"cas": CASE, "donnees": str(data_path)}
    for label, med_path in (("base", med_base), ("V1", med_v1)):
        med = load_med_data(med_path, (CASE,))
        result[label] = summarize(_arrays(med, data_path), ctx.axes, ctx.radius)
        result[label]["med"] = str(med_path)
    base, v1 = result["base"], result["V1"]
    result["ecarts_base_V1"] = {
        "taux_max_compression": v1["compression"]["taux_max"]
        - base["compression"]["taux_max"],
        "n_au_dela_100": v1["compression"]["n_au_dela_100"]
        - base["compression"]["n_au_dela_100"],
        "n_traction": v1["traction"]["n"] - base["traction"]["n"],
        "n_traction_au_dela_butee_terre": v1["traction"]["n_au_dela_butee_terre"]
        - base["traction"]["n_au_dela_butee_terre"],
    }
    out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a) for a in sys.argv[1:5])))
