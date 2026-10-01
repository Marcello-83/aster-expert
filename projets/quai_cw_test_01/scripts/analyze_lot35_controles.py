"""Lot 35 : contrôles de lecture croisée de la synthèse, écrits dans
`docs/essais_lot35.md` (critères fixés **avant** l'exécution du modèle complet).

Chaque contrôle confronte deux lectures indépendantes d'une même grandeur du calcul
exécuté, avec le seuil du rapport ; aucun seuil n'est modifié après lecture.

- C5 tirants / ancrages : Σ N cos θ = réaction d'ancrage selon Y (tous les cas) et
  Σ N sin θ = réaction selon Z (hors pesanteur), écart relatif <= 1e-6 ;
- C6 ressorts : la force par bande de la synthèse égale `-Σ k·DY` du script d'équilibre
  du lot 34 (`analyze_lot34_equilibre.spring_by_band`), écart relatif <= 1e-9 ;
- C7 tête : le maximum en valeur absolue de DY de la synthèse égale celui de
  `POST_RELEVE_T/EXTREMA` (tables `ORDRE_GRANDEUR_<cas>`, six chiffres), écart relatif
  <= 1e-4 ;
- C9 nœud de butée extrême : son taux recalculé par les classes de ressorts du
  générateur (`build_spring_classes`), raideur et aire différentes de la synthèse (aires
  par bande), écart relatif <= 1e-9 ;
- C10 palplanches : aucune table du `.comm` ne lit un champ de contraintes
  (`SIEF_*`, `SIGM_*`) ; la table d'efforts des palplanches lit `EFGE_NOEU`.

Usage : python projets/quai_cw_test_01/scripts/analyze_lot35_controles.py <mess> <comm> <données> \\
    <synthese.json> --sortie <controles.json>
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aster_expert.agent.model_data import load_model_data  # noqa: E402
from aster_expert.report.tables import read_tables  # noqa: E402
from quai_cw_test_01.controles import spring_by_band  # noqa: E402
from quai_cw_test_01.generation.springs import (  # noqa: E402
    COMBINED_BAND,
    build_spring_classes,
)
from quai_cw_test_01.meshing.combiwall import build_params  # noqa: E402

CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")
THRESHOLDS = {"C5": 1e-6, "C6": 1e-9, "C7": 1e-4, "C9": 1e-9}


def _verdict(value: float, threshold: float) -> str:
    return "RÉUSSI" if math.isfinite(value) and abs(value) <= threshold else "ÉCHEC"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("comm", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("synthese", type=Path)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args(argv)

    synthesis = json.loads(args.synthese.read_text(encoding="utf-8"))
    data = load_model_data(args.donnees)
    params = build_params(data)
    k_h = {
        "RESS_AV_ARGI": float(data.items()["sol.k_h_argile_marneuse_raide"].value),  # type: ignore[arg-type]
        "RESS_AV_MARNE": float(data.items()["sol.k_h_marne_compacte"].value),  # type: ignore[arg-type]
    }
    all_classes = build_spring_classes(params, k_h)
    band_classes = [c for c in all_classes if c.band != COMBINED_BAND]
    mess_text = args.mess.read_text(encoding="utf-8", errors="replace")

    criteria: list[dict[str, Any]] = []

    def add(cid: str, case: str, what: str, value: float) -> None:
        threshold = THRESHOLDS[cid]
        criteria.append(
            {
                "id": cid,
                "case": case,
                "description": what,
                "threshold": threshold,
                "value": value,
                "verdict": _verdict(value, threshold),
            }
        )

    by_case = {c["case"]: c for c in synthesis["cases"]}
    for case in CASES:
        block = by_case[case]
        tie = block["tie_anchor"]
        add("C5", case, "Σ N cos θ contre réaction d'ancrage selon Y", tie["gap_dy"])
        if not tie["gravity"]:
            add(
                "C5",
                case,
                "Σ N sin θ contre réaction d'ancrage selon Z",
                tie["gap_dz"],
            )
        expected = spring_by_band(mess_text, case, band_classes)
        for band, force in block["springs"]["layer_forces_n"].items():
            reference = -expected[band]  # le script du lot 34 rend +Σ k·DY
            gap = (force - reference) / abs(reference) if reference else math.inf
            add(
                "C6",
                case,
                f"force des ressorts de {band} (synthèse / script lot 34)",
                gap,
            )

    # `IMPR_TABLE` tronque l'intitulé à 16 caractères : ORDRE_GRANDEUR_Q3 s'imprime
    # ORDRE_GRANDEUR_Q (lot 34 : deux intitulés de même début sont indiscernables).
    def ordre_title(case: str) -> str:
        return f"ORDRE_GRANDEUR_{case}"[:16]

    ordre = read_tables(args.mess, [ordre_title(c) for c in ("G", "Q3")])
    for case in ("G", "Q3"):
        rows = ordre[ordre_title(case)]
        maxi_abs = next(r for r in rows if r.get("EXTREMA") == "MAXI_ABS")
        reference = abs(float(maxi_abs["VALE"]))
        got = abs(by_case[case]["head"]["max_abs"]["value"])
        add(
            "C7",
            case,
            "max |DY| en tête (synthèse / EXTREMA)",
            (got - reference) / reference,
        )

    # C9 : le taux du nœud de butée extrême de chaque cas, recalculé par une autre
    # voie que la synthèse : raideur de chaque bande lue des classes de ressorts du
    # générateur (`build_spring_classes`), aire tributaire de la bande = k_bande / k_h,
    # butée interpolée ici (et non par `quai_cw_test_01.report.quantities`).
    item = data.items()["sol.profil_butee_limite"]
    assert item.profile is not None
    layer_of = {"RESS_AV_ARGI": "argile marneuse", "RESS_AV_MARNE": "marne compacte"}
    profile = {
        band: sorted(
            [(p.z, p.p * 1e3) for p in item.profile if p.layer == layer],
            key=lambda pt: pt[0],
        )
        for band, layer in layer_of.items()
    }

    def sigma(band: str, z: float) -> float:
        (z0, p0), (z1, p1) = profile[band][0], profile[band][-1]
        return p0 + (p1 - p0) * (z - z0) / (z1 - z0)

    per_node: dict[tuple[float, float, float], list[tuple[str, float]]] = {}
    for c in band_classes:
        for node in c.nodes:
            key = (round(node[0], 6), round(node[1], 6), round(node[2], 6))
            per_node.setdefault(key, []).append((c.band, c.stiffness_n_per_m))
    for case in CASES:
        bearing = by_case[case]["springs"]["bearing"]
        at = bearing["at_max"]
        if at is None:
            continue
        key = (round(at["x"], 6), round(at["y"], 6), round(at["z"], 6))
        parts = per_node[key]
        k_total = sum(k for _, k in parts)
        capacity = sum(k / (k_h[b] * 1e6) * sigma(b, at["z"]) for b, k in parts)
        ratio = k_total * abs(at["value"]) / capacity
        add(
            "C9",
            case,
            "taux de butée maximal recalculé par les classes de ressorts",
            (ratio - bearing["max_ratio"]) / bearing["max_ratio"],
        )

    comm_text = args.comm.read_text(encoding="utf-8")
    stress_reads = re.findall(
        r'NOM_CHAM="(SIEF_[A-Z]+|SIGM_[A-Z]+)"', comm_text
    ) + re.findall(r'CONTRAINTE=\([^)]*"(?:SIEF|SIGM)_[A-Z]+"', comm_text)
    palp = re.search(
        r"TAB_EFPALP_G = CREA_TABLE\(.*?NOM_CHAM=\"([A-Z_]+)\"", comm_text, re.S
    )
    c10_ok = (not stress_reads) and palp is not None and palp[1] == "EFGE_NOEU"
    criteria.append(
        {
            "id": "C10",
            "case": "-",
            "description": "aucune lecture de contrainte ; palplanches en EFGE_NOEU",
            "threshold": "aucune lecture SIEF_*/SIGM_*",
            "value": {
                "lectures_de_contraintes": stress_reads,
                "champ_palplanches": palp[1] if palp else None,
            },
            "verdict": "RÉUSSI" if c10_ok else "ÉCHEC",
        }
    )

    result = {
        "criteria": criteria,
        "verdict": "RÉUSSI"
        if all(c["verdict"] == "RÉUSSI" for c in criteria)
        else "ÉCHEC",
    }
    args.sortie.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    worst: dict[str, float] = {}
    for crit in criteria:
        if isinstance(crit["value"], float):
            worst[crit["id"]] = max(worst.get(crit["id"], 0.0), abs(crit["value"]))
    for cid, value in sorted(worst.items()):
        print(f"{cid} : pire écart {value:.3e} (seuil {THRESHOLDS[cid]:.0e})")
    print("verdict global :", result["verdict"])
    return 0 if result["verdict"] == "RÉUSSI" else 1


if __name__ == "__main__":
    raise SystemExit(main())
