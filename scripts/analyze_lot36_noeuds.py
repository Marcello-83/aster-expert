"""Lot 36, étape 1 : vérification à la main des nœuds à ressort les plus sollicités.

Recalcule, pour un cas et un nœud, l'aire tributaire A (analytique), la raideur k
écrite dans le `.comm` (VALE de la classe du nœud), le déplacement DY (`.mess`),
la pression k·DY/A, le module k/A à comparer à k_h de la couche, la butée limite
côté bassin (contrôle du lot 35) et la butée limite côté terre (Rankine).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.springs import build_spring_classes
from aster_expert.generation.terre import butee_terre_pa
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.combiwall import build_params, spring_node_areas
from aster_expert.report import quantities as q
from aster_expert.report.build import _butee_pa
from aster_expert.report.tables import read_tables

ROOT = Path(__file__).resolve().parents[1]


def _vale_of_group(comm_text: str, group: str) -> float:
    pattern = re.compile(
        r'GROUP_MA=\("' + re.escape(group) + r'",\), CARA="K_T_D_N", '
        r"VALE=\(0\.0, ([0-9.eE+-]+), 0\.0\)"
    )
    found = pattern.findall(comm_text)
    if len(found) != 1:
        message = f"{group} : {len(found)} occurrence(s) de K_T_D_N dans le .comm"
        raise ValueError(message)
    return float(found[0])


def main(mess: Path, comm: Path, case: str, out: Path) -> None:
    data = load_model_data(ROOT / "data/examples/combiwall_model_data.yaml")
    mv = ModelValues(data)
    params = build_params(data)
    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    bas = _butee_pa(data)
    terre = butee_terre_pa()
    classes = build_spring_classes(params, k_h)
    tributary = spring_node_areas(params)
    comm_text = comm.read_text(encoding="utf-8")
    rows = read_tables(mess, [f"RESSORTS_{case}"])[f"RESSORTS_{case}"]
    axes = [float(x) for x in params["tube"]["axes_x"]]
    radius = float(params["tube"]["rayon"])

    def by_key(pt):
        return tuple(round(c, 6) + 0.0 for c in pt)

    tributary_by_key = {
        band: {by_key(pt): a for pt, a in pts.items()}
        for band, pts in tributary.items()
    }
    node_class: dict = {}
    for c in classes:
        for pt in c.nodes:
            node_class.setdefault(by_key(pt), []).append(c)

    def describe(row):
        x, y, z = (float(row[k]) for k in ("COOR_X", "COOR_Y", "COOR_Z"))
        key = by_key((x, y, z))
        if (
            key not in node_class
        ):  # tables à 12 chiffres : repli sur le voisin le plus proche
            key = min(
                node_class,
                key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2 + (p[2] - z) ** 2,
            )
        cls = node_class[key]
        # classe effective : COMMUN si le nœud est partagé, sinon la classe de bande
        eff = next((c for c in cls if c.band == "COMMUN"), cls[0])
        k_comm = _vale_of_group(comm_text, eff.group_name)
        # aire tributaire projetée : lue de l'analytique (`spring_node_areas`), pas
        # déduite de la raideur ; la comparaison k/A = k_h est ainsi un vrai contrôle
        areas = {
            c.band: tributary_by_key[c.band][key] for c in cls if c.band != "COMMUN"
        }
        area = sum(areas.values())
        dy = float(row["DY"])
        cap_b = sum(a * q._capacity(key[2], bas, b) for b, a in areas.items())
        cap_t = sum(a * q._capacity(key[2], terre, b) for b, a in areas.items())
        return {
            "noeud": str(row.get("NOEUD", "")),
            "x": key[0],
            "y": key[1],
            "z": key[2],
            "porteur": q.holder_of(key[0], key[1], axes, radius),
            "bandes": sorted(areas),
            "groupe_comm": eff.group_name,
            "aire_A_m2": area,
            "raideur_k_comm_N_par_m": k_comm,
            "raideur_k_analytique_N_par_m": sum(
                k_h[b] * 1e6 * a for b, a in areas.items()
            ),
            "k_h_couche_MN_m3": {b: k_h[b] for b in areas},
            "k_sur_A_MN_m3": k_comm / area / 1e6,
            "DY_m": dy,
            "pression_kDY_sur_A_kPa": k_comm * dy / area / 1e3,
            "butee_bassin_kPa": cap_b / area / 1e3,
            "taux_butee_bassin": (k_comm * abs(dy) / cap_b) if dy < 0 else None,
            "butee_terre_kPa": cap_t / area / 1e3,
            "taux_butee_terre": (k_comm * dy / cap_t) if dy > 0 else None,
        }

    comp = min(rows, key=lambda r: float(r["DY"]))
    # taux maximal : recalculé nœud par nœud (compression)
    worst = None
    for r in rows:
        if float(r["DY"]) < 0:
            d = describe(r)
            if worst is None or d["taux_butee_bassin"] > worst["taux_butee_bassin"]:
                worst = d
    tens = None
    for r in rows:
        if float(r["DY"]) > 0:
            d = describe(r)
            if tens is None or d["taux_butee_terre"] > tens["taux_butee_terre"]:
                tens = d
    maxdy = max(rows, key=lambda r: float(r["DY"]))
    res = {
        "cas": case,
        "compression_taux_bassin_maximal": worst,
        "traction_taux_terre_maximal": tens,
        "traction_DY_maximal": describe(maxdy),
        "compression_DY_minimal": describe(comp),
    }
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
