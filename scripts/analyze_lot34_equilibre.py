"""Lot 34, étapes 2 et 3 : bilan d'équilibre terme à terme d'une exécution de
production (quai réduit ou modèle complet), composante par composante (X, Y, Z).

Entrées : le `.mess` de l'exécution, le `.comm` généré, les données, et le
rapport de la sonde de charge assemblée (`analyze_lot34_charge_assemblee.py`,
même maillage) qui donne la charge appliquée -- « telle qu'évaluée » par Code_
Aster (règle nodale, `aster_expert.meshing.equilibrium`) et « spécifiée »
(intégrale du profil).

Bilan, pour chaque cas et chaque composante c :

    appliquée_c + Σ réactions_c (composantes bloquées) + Σ ressorts_c = 0

- réactions : `REAC_NODA`/`RESULTANTE` par groupe d'appui (`TAB_REAC_<groupe>_<cas>`),
  seules les composantes réellement bloquées entrent dans la somme (SYM_G/SYM_D :
  DX ; PIED_TUBES : DZ ; ANCRAGES : DX, DY, DZ) ; les autres sont relevées à part
  (elles doivent être nulles) ;
- ressorts : -Σ k_i DY_i par bande (argile, marne) ; les ressorts n'ont de
  raideur que selon Y (`K_T_D_N = (0, k, 0)`).

Usage : python scripts/analyze_lot34_equilibre.py <mess> <comm> <données> \\
    <rapport sonde .json> [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import analyze_lot33_equilibre as l33  # noqa: E402

from aster_expert.generation.comm import reaction_table_title  # noqa: E402

THRESHOLD = 1.0e-6
CASES = ("G", "Q1", "EAU_P", "EAU_A")
BLOCKED = {
    "SYM_G": ("DX",),
    "SYM_D": ("DX",),
    "PIED_TUBES": ("DZ",),
    "ANCRAGES": ("DX", "DY", "DZ"),
}
COMPONENTS = ("DX", "DY", "DZ")


def group_reactions(mess: str, case: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for group in (*BLOCKED, "TOUS"):
        records = l33.find_table(mess, reaction_table_title(group, case))
        assert len(records) == 1, (group, records)
        out[group] = {c: float(records[0][c]) for c in COMPONENTS}
    return out


def spring_by_band(mess: str, case: str, classes: list[Any]) -> dict[str, float]:
    """Σ k_i DY_i par bande. Chaque ligne de `TAB_RESS_<cas>` (`DEPL`/`DY`,
    `COOR_X/Y/Z`) est appariée au nœud de ressort le plus proche (à 1 mm) ; un
    nœud à la limite de deux bandes porte les ressorts des deux, chacun compté
    dans sa bande. Un nœud non retrouvé est une erreur, jamais ignoré."""
    records = l33.find_table(mess, f"RESSORTS_{case}")
    tol = 1.0e-3
    stiffness: dict[tuple[float, float, float], dict[str, float]] = {}
    for c in classes:
        for x, y, z in c.nodes:
            key = (round(x, 6), round(y, 6), round(z, 6))
            per_band = stiffness.setdefault(key, {})
            per_band[c.band] = per_band.get(c.band, 0.0) + c.stiffness_n_per_m
    grid: dict[tuple[int, int, int], list[tuple[float, float, float]]] = {}
    for key in stiffness:
        grid.setdefault(tuple(int(v // tol) for v in key), []).append(key)  # type: ignore[arg-type]
    totals = dict.fromkeys(sorted({c.band for c in classes}), 0.0)
    counted: set[tuple[float, float, float]] = set()
    for r in records:
        point = (r["COOR_X"], r["COOR_Y"], r["COOR_Z"])
        cell = tuple(int(v // tol) for v in point)
        best, best_d = None, math.inf
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for cand in grid.get(
                        (cell[0] + dx, cell[1] + dy, cell[2] + dz), ()
                    ):
                        d = math.dist(point, cand)
                        if d < best_d:
                            best, best_d = cand, d
        if best is None or best_d > tol:
            message = f"nœud de ressort non retrouvé : {point}"
            raise ValueError(message)
        if best in counted:
            message = f"nœud de ressort compté deux fois : {best}"
            raise ValueError(message)
        counted.add(best)
        for band, k in stiffness[best].items():
            totals[band] += k * r["DY"]
    if len(counted) != len(stiffness):
        message = (
            f"{len(stiffness) - len(counted)} nœud(s) de ressort absents de TAB_RESS"
        )
        raise ValueError(message)
    return totals


def balance_terms(
    applied_eval: dict[str, float],
    applied_spec: dict[str, float],
    reactions: dict[str, dict[str, float]],
    springs: dict[str, float],
) -> dict[str, dict[str, float]]:
    """Bilan `appliquée + réactions bloquées + ressorts` par composante, rapporté
    à la plus grande composante de la charge appliquée. Les réactions relevées sur
    les composantes libres (forces de liaison de `LIAISON_SOLIDE`) sont consignées
    à part, jamais sommées."""
    spring_on_structure = {"DX": 0.0, "DY": -sum(springs.values()), "DZ": 0.0}
    blocked_sum = {
        c: sum(reactions[g][c] for g, blocked in BLOCKED.items() if c in blocked)
        for c in COMPONENTS
    }
    scale = max(abs(applied_eval[k]) for k in COMPONENTS)
    terms: dict[str, dict[str, float]] = {}
    for c in COMPONENTS:
        balance = applied_eval[c] + blocked_sum[c] + spring_on_structure[c]
        balance_spec = applied_spec[c] + blocked_sum[c] + spring_on_structure[c]
        free_sum = sum(
            reactions[g][c] for g, blocked in BLOCKED.items() if c not in blocked
        )
        terms[c] = {
            "applied_as_evaluated_n": applied_eval[c],
            "applied_specified_n": applied_spec[c],
            "reactions_blocked_n": blocked_sum[c],
            "springs_on_structure_n": spring_on_structure[c],
            "balance_n": balance,
            "relative_gap": balance / scale if scale else math.nan,
            "relative_gap_vs_specified": balance_spec / scale if scale else math.nan,
            "reactions_free_components_n": free_sum,
            "reactions_free_components_relative": free_sum / scale
            if scale
            else math.nan,
        }
    return terms


def written_spring_stiffness(comm_text: str) -> dict[str, float]:
    """`K_T_D_N` (N/m, deuxième composante) écrit dans le `.comm`, par groupe."""
    found = re.findall(
        r'_F\(GROUP_MA=\("([^"]+)",\), CARA="K_T_D_N", '
        r"VALE=\(0\.0, ([-\d.eE+]+), 0\.0\)",
        comm_text,
    )
    return {name: float(k) for name, k in found}


def spring_stiffness_check(comm_text: str, all_classes: list[Any]) -> dict[str, Any]:
    """Étape 2.2 : chaque nœud à ressort porte exactement une raideur, et la somme
    lue (bandes) égale la somme écrite dans le `.comm` (dernière occurrence de
    `DISCRET` gagnante sur un nœud partagé, règle de surcharge)."""
    from aster_expert.generation.springs import COMBINED_BAND  # noqa: PLC0415

    written = written_spring_stiffness(comm_text)
    missing = [c.group_name for c in all_classes if c.group_name not in written]
    if missing:
        message = f"classes sans K_T_D_N dans le .comm : {missing}"
        raise ValueError(message)
    effective: dict[Any, float] = {}
    for c in all_classes:
        for node in c.nodes:
            effective[node] = written[c.group_name]
    read: dict[Any, float] = {}
    for c in all_classes:
        if c.band == COMBINED_BAND:
            continue
        for node in c.nodes:
            read[node] = read.get(node, 0.0) + c.stiffness_n_per_m
    sum_written = sum(effective.values())
    sum_read = sum(read.values())
    return {
        "n_nodes": len(effective),
        "sum_k_written_effective_n_per_m": sum_written,
        "sum_k_read_n_per_m": sum_read,
        "relative_gap": (sum_written - sum_read) / sum_read,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("comm", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("sonde", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    from aster_expert.agent.model_data import load_model_data  # noqa: PLC0415
    from aster_expert.generation.springs import (  # noqa: PLC0415
        COMBINED_BAND,
        build_spring_classes,
    )
    from aster_expert.meshing.combiwall import build_params  # noqa: PLC0415

    mess = args.mess.read_text(encoding="utf-8")
    data = load_model_data(args.donnees)
    params = build_params(data)
    k_h = {
        "RESS_AV_ARGI": float(data.items()["sol.k_h_argile_marneuse_raide"].value),
        "RESS_AV_MARNE": float(data.items()["sol.k_h_marne_compacte"].value),
    }
    classes = [c for c in build_spring_classes(params, k_h) if c.band != COMBINED_BAND]
    sonde = json.loads(args.sonde.read_text(encoding="utf-8"))

    comm_text = args.comm.read_text(encoding="utf-8")
    all_classes = build_spring_classes(params, k_h)
    result: dict[str, Any] = {
        "threshold": THRESHOLD,
        "spring_stiffness": spring_stiffness_check(comm_text, all_classes),
        "cases": {},
        "informative_cases": {},
        "symmetry": {},
    }
    for case in CASES:
        reactions = group_reactions(mess, case)
        springs = spring_by_band(mess, case, classes)
        terms = balance_terms(
            sonde["cases"][case]["as_evaluated"]["integrated_n"],
            sonde["cases"][case]["integrated_n"],
            reactions,
            springs,
        )
        # Lot 35 : la table combinée `REACTIONS_<cas>` du lot 33 n'est plus écrite
        # dans le `.comm` (retirée du générateur : sa valeur n'égale pas la somme des
        # tables par groupe) ; elle n'est plus lue ici.
        result["cases"][case] = {
            "components": terms,
            "reactions_by_group_n": reactions,
            "springs_k_dy_by_band_n": springs,
            "reaction_sum_all_nodes_n": reactions["TOUS"],
            "verdict": "RÉUSSI"
            if all(abs(t["relative_gap"]) <= THRESHOLD for t in terms.values())
            else "ÉCHEC",
        }

    # Q3 (amarrage) et A (accostage) : charges ponctuelles écrites dans le `.comm`,
    # bilan informatif (aucun verdict, comme au lot 33).
    from aster_expert.meshing.combiwall import expected_masses  # noqa: PLC0415

    bollard = re.search(
        r"GROUP_NO=\(\"BOLLARD\",\), FY=([-\d.eE+]+), FZ=([-\d.eE+]+)", comm_text
    )
    defense = re.search(r"GROUP_MA=\(\"DEFENSE\",\), FY=([-\d.eE+]+)\)", comm_text)
    written = {}
    if bollard:
        written["Q3"] = {"DX": 0.0, "DY": float(bollard[1]), "DZ": float(bollard[2])}
    if defense:
        area = expected_masses(params)["DEFENSE"]["mass"]
        written["A"] = {"DX": 0.0, "DY": float(defense[1]) * area, "DZ": 0.0}
    for case, applied in written.items():
        terms = balance_terms(
            applied,
            applied,
            group_reactions(mess, case),
            spring_by_band(mess, case, classes),
        )
        result["informative_cases"][case] = {"components": terms}

    for case in (*CASES, *written):
        try:
            result["symmetry"][case] = l33.symmetry_check(mess, case)
        except KeyError:
            continue

    output = args.output or (args.mess.parent / "equilibre_lot34.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
