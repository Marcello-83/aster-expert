"""Contrôle post-lot 54: displacements of every unit case of B54, non-regression, recombination.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/controle_lot54_deplacements.py \
        --execution <dossier d'exécution> --maillage <maillage.med> --comm <.comm> \
        [--lot54 /media/sf_partage/echanges/lot54/pontons_alu_01/B54] --sortie <dossier>

Re-reads the tables of a B54 run (same `.comm` as lot 54) with the readers of lot 54, then:
- rewrites `efforts_elementaires.npz`, `deplacements_unitaires.csv` and `appuis_axes.csv` and
  compares them with the files of lot 54 (relative 1e-9);
- writes `deplacements_unitaires_complet.csv`: same points and columns, every unit case that
  appears in `evenements.csv` (plus the cases of lot 54);
- recombines, from the complete file alone (module `csv`), the extremes of
  `deplacements_combinaisons.csv` from the labels of their governing combinations.
No change of model, case, event or combination.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aster_expert.projet.context import load_project
from pontons_alu_01 import deplacements_lot53 as d53
from pontons_alu_01.controle_lot54 import (
    LOT54,
    build_state,
    compare_csv,
    compare_npz,
    read_complete,
    recombination,
    rows_of,
)
from pontons_alu_01.exports_lot51 import write as write_csv
from pontons_alu_01.exports_lot54 import export, load, source_line

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--maillage", type=Path, required=True)
    parser.add_argument("--comm", type=Path, required=True)
    parser.add_argument("--lot54", type=Path, default=LOT54)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    state = build_state(args.execution, args.maillage, args.comm)
    out = args.sortie
    out.mkdir(parents=True, exist_ok=True)
    vd = load(ctx, "B54", state)
    export(vd, state, out, source=source_line(vd, state), forces_csv=False)
    r = d53.compute(ctx, state, vd)
    cases_lot54 = d53.exported_cases(r.vd)
    event_cases = {row["cas"] for row in rows_of(out / "evenements.csv")}
    cases_full = [c for c in r.vd.cases if c in set(cases_lot54) | event_cases]
    missing = sorted(event_cases - set(cases_full))
    src = source_line(vd, state)
    d53.write_exports(
        out,
        src,
        r.pts,
        r.qs,
        r.unit,
        cases_lot54,
        r.ev_ext,
        r.combos,
        d53.synthesis_rows(r.vd, r.pts, r.qs, r.combos),
        relabel={},
    )
    note = (
        f"{src} Déplacements des points de sortie sous TOUS les cas unitaires de evenements.csv : "
        "permanents (G1, G2, DEJ), exploitation (Q_Mk, QD_Mk), houle (HU_TUBES, HU_PANNES, "
        "HU_PLATELAGE, HD_TABLIER), accostage (ACN, ACX, ACZ : 1 kN/m sur 1 m), amarrage (AMY, AMX : "
        "1 kN) et thermiques (TP, TM). Unités : mm (DX, DY, DZ), mrad (DRX, DRY, DRZ). "
        f"{d53.POINT_NOTE}"
    )
    write_csv(
        out / "deplacements_unitaires_complet.csv",
        note,
        [
            *d53.POINT_HEADER,
            "cas",
            "DX_mm",
            "DY_mm",
            "DZ_mm",
            "DRX_mrad",
            "DRY_mrad",
            "DRZ_mrad",
        ],
        d53.unit_rows(r.pts, r.unit, cases_full),
    )
    lot = args.lot54
    non_reg = {
        "efforts_elementaires.npz": compare_npz(
            out / "efforts_elementaires.npz", lot / "efforts_elementaires.npz"
        ),
        "deplacements_unitaires.csv": compare_csv(
            out / "deplacements_unitaires.csv", lot / "deplacements_unitaires.csv"
        ),
        "appuis_axes.csv": compare_csv(
            out / "appuis_axes.csv", lot / "appuis_axes.csv"
        ),
    }
    # the complete file must contain the lot 54 file unchanged
    complete = read_complete(out / "deplacements_unitaires_complet.csv")
    old = read_complete(lot / "deplacements_unitaires.csv")
    gap = max(
        (
            abs(a - b)
            for k, v in old.items()
            for a, b in zip(v, complete[k], strict=True)
        ),
        default=0.0,
    )
    non_reg["complet_contient_lot54"] = {
        "ecart_max_absolu": gap,
        "identique": gap == 0.0,
    }
    targets = [
        ("PF_bout_YM", "DY", "ELS_caracteristique"),
        ("PF_bout_YM", "DY", "ELU_accidentel"),
        ("P5C2_YM_axe", "DX", "ELS_caracteristique"),
        ("P5C2_YM_axe", "DY", "ELS_caracteristique"),
        ("P3_semelle_centre", "DZ", "ELS_caracteristique"),
    ]
    targets = [
        t
        for t in targets
        if any(
            r_["point"] == t[0] for r_ in rows_of(lot / "deplacements_combinaisons.csv")
        )
    ]
    recomb = recombination(
        out / "deplacements_unitaires_complet.csv",
        lot / "deplacements_combinaisons.csv",
        lot / "evenements.csv",
        targets,
    )
    worst = max((abs(x["ecart_mm"]) for x in recomb), default=0.0)
    report = {
        "cas_complets": len(cases_full),
        "cas_de_evenements_absents_du_modele": missing,
        "non_regression": non_reg,
        "recombinaison": recomb,
        "recombinaison_ecart_max_mm": worst,
    }
    (out / "controle_deplacements.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    for k, v in non_reg.items():
        print(k, v)
    print("cas complets :", len(cases_full), "| absents :", missing)
    print("recombinaison : écart max (mm)", worst)
    ok = all(v["identique"] for v in non_reg.values()) and worst <= 0.01 and not missing
    print("RÉUSSI" if ok else "ÉCHEC")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
