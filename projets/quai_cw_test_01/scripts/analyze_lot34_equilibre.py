"""Lot 34, étapes 2 et 3 : bilan d'équilibre terme à terme d'une exécution de
production (quai réduit ou modèle complet), composante par composante (X, Y, Z).

Entrées : le `.mess` de l'exécution, le `.comm` généré, les données, et le
rapport de la sonde de charge assemblée (`analyze_lot34_charge_assemblee.py`,
même maillage) qui donne la charge appliquée -- « telle qu'évaluée » par Code_
Aster (règle nodale, `quai_cw_test_01.meshing.equilibrium`) et « spécifiée »
(intégrale du profil).

Bilan, pour chaque cas et chaque composante c :

    appliquée_c + Σ réactions_c (composantes bloquées) + Σ ressorts_c = 0

- réactions : `REAC_NODA`/`RESULTANTE` par groupe d'appui (`TAB_REAC_<groupe>_<cas>`),
  seules les composantes réellement bloquées entrent dans la somme (SYM_G/SYM_D :
  DX ; PIED_TUBES : DZ ; ANCRAGES : DX, DY, DZ) ; les autres sont relevées à part
  (elles doivent être nulles) ;
- ressorts : -Σ k_i DY_i par bande (argile, marne) ; les ressorts n'ont de
  raideur que selon Y (`K_T_D_N = (0, k, 0)`).

Usage : python projets/quai_cw_test_01/scripts/analyze_lot34_equilibre.py <mess> <comm> <données> \\
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))

import analyze_lot33_equilibre as l33  # noqa: E402

from quai_cw_test_01.controles import (  # noqa: E402
    spring_by_band,
    spring_stiffness_check,
)
from quai_cw_test_01.generation.comm import reaction_table_title  # noqa: E402

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("comm", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("sonde", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    from aster_expert.agent.model_data import load_model_data  # noqa: PLC0415
    from quai_cw_test_01.generation.springs import (  # noqa: PLC0415
        COMBINED_BAND,
        build_spring_classes,
    )
    from quai_cw_test_01.meshing.combiwall import build_params  # noqa: PLC0415

    mess = args.mess.read_text(encoding="utf-8")
    data = load_model_data(args.donnees)
    params = build_params(data)
    k_h = {
        "RESS_AV_ARGI": float(data.items()["sol.k_h_argile_marneuse_raide"].value),  # type: ignore[arg-type]
        "RESS_AV_MARNE": float(data.items()["sol.k_h_marne_compacte"].value),  # type: ignore[arg-type]
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
    from quai_cw_test_01.meshing.combiwall import expected_masses  # noqa: PLC0415

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
