"""Lot 36 : contrôles C2, C4, C5 et C6 de `docs/essais_lot36.md` sur le modèle complet.

- C2 : les tables du MED de la base égalent celles du `.mess` du lot 35 (même modèle) ;
- C4 : les 30 champs attendus du MED (base et V1) sont présents et finis ;
- C5 : la variation de (réaction d'ancrage DY + force des ressorts) du cas G entre V1
  et base égale l'opposée de la résultante de la pression initiale (largeur projetée
  analytique, `band_projected_width`) ;
- C6 : V1 ne modifie que le cas G.

Usage : python projets/quai_cw_test_01/scripts/analyze_lot36_controles.py <données> <run base> <run V1> \\
    <run lot 35> <sortie.json>
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.agent.model_data import load_model_data
from aster_expert.report.tables import read_tables
from quai_cw_test_01.generation.terre import REPOS_TABLE_KPA
from quai_cw_test_01.meshing.combiwall import band_projected_width, build_params
from quai_cw_test_01.report.build import CASES, _table_names
from quai_cw_test_01.report.med_source import (
    MedData,
    cross_check,
    field_names,
    load_med_data,
    med_tables,
)

DISPLACEMENT_PREFIXES = ("RESSORTS_", "DYT", "TETE_")


def _max_by(gaps: dict[str, float], keep: Any) -> float:
    return max((v for k, v in gaps.items() if keep(k)), default=0.0)


def _fields_ok(med: MedData) -> dict[str, Any]:
    missing, non_finite = [], []
    for name in field_names(CASES):
        keys = [k for k in med.arrays if k == name or k.startswith(name + "@")]
        keys = [
            k for k in keys if not k.endswith("#cells") and not k.endswith("#nodes")
        ]
        if not keys:
            missing.append(name)
        elif not all(np.isfinite(med.arrays[k]).all() for k in keys):
            non_finite.append(name)
    return {
        "n_attendus": len(field_names(CASES)),
        "manquants": missing,
        "non_finis": non_finite,
    }


def main(data_path: Path, base: Path, v1: Path, lot35: Path, out: Path) -> int:
    data = load_model_data(data_path)
    params = build_params(data)
    axes = [float(x) for x in params["tube"]["axes_x"]]
    central = int(params["tube"]["central"])
    profile_tubes = tuple(dict.fromkeys((central, 1)))
    names = _table_names(CASES, profile_tubes)
    med_base = load_med_data(base / "proc.0" / "fort.80", CASES)
    med_v1 = load_med_data(v1 / "proc.0" / "fort.80", CASES)
    t_base = med_tables(med_base, names, profile_tubes=profile_tubes)
    t_v1 = med_tables(med_v1, names, profile_tubes=profile_tubes)
    old = read_tables(lot35 / "proc.0" / "fort.6", names)
    result: dict[str, Any] = {"axes": axes}

    gaps_old = cross_check(t_base, old)
    result["C2"] = {
        "deplacements_max": _max_by(
            gaps_old, lambda k: k.startswith(DISPLACEMENT_PREFIXES)
        ),
        "autres_tables_max": _max_by(
            gaps_old, lambda k: not k.startswith(DISPLACEMENT_PREFIXES)
        ),
        "n_tables": len(gaps_old),
        "pire_table": max(gaps_old, key=gaps_old.get),  # type: ignore[arg-type]
    }
    result["C4"] = {"base": _fields_ok(med_base), "V1": _fields_ok(med_v1)}

    gaps_v1 = cross_check(t_v1, t_base)
    other = {k: v for k, v in gaps_v1.items() if not k.endswith("_G")}
    result["C6"] = {
        "autres_cas_max": max(other.values()),
        "n_tables_autres_cas": len(other),
        "cas_G_max": _max_by(gaps_v1, lambda k: k.endswith("_G")),
    }

    # C5 : bilan Y du cas G (ancrages + ressorts)
    springs = np.unique(med_base.conn[-2].ravel())
    from quai_cw_test_01.report.figures import _spring_key, build_context

    ctx = build_context(data_path)
    k = np.array(
        [ctx.spring_nodes[_spring_key(med_base.coords[n])].stiffness for n in springs]
    )

    def total(med: MedData, tables: dict[str, list[dict[str, Any]]]) -> float:
        anchor = float(tables["REAC_ANCR_G"][0]["DY"])
        dy = med.node_field("G", "DEPL")[springs, 1]
        return anchor + float((-k * dy).sum())

    expected = 0.0
    for band, points in REPOS_TABLE_KPA.items():
        (za, pa), (zb, pb) = sorted(points)
        expected += (
            (pa + pb)
            / 2.0
            * 1.0e3
            * (zb - za)
            * band_projected_width(params, params["bandes"][band])
        )
    delta = total(med_v1, t_v1) - total(med_base, t_base)
    result["C5"] = {
        "attendu_resultante_N": expected,
        "variation_ancrage_plus_ressorts_N": delta,
        "ecart_relatif": (delta + expected) / abs(expected),
    }
    out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a) for a in sys.argv[1:6])))
