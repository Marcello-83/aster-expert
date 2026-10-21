"""MED of lot 53 for PONTONS-ALU-01 (consigne § MED et vues), variant B52.

`resultats.med` of lot 52 is copied under a new name,
`resultats_deplacements_lot53.med`, and receives the displacement fields chosen by
`deplacements_lot53.field_choices` (six characteristic events, four governing
combinations): `<key>__DEPL` on the original mesh and `E_<key>__DEPL` on the common
support `PONTON_B52_ELNO` of lot 52 (two nodes per
SEG2: the DEPL of the original node), so that the deformed shape of a field can be
coloured by any of its components, as the forces of lot 52. Written by
`scripts/med_ajouter_lot53.py` in the Code_Aster image (medcoupling).
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.exports_lot51 import DEPL
from pontons_alu_01.med_lot51quater import in_image

LOT = "lot53"
SOURCE_LOT = "lot52"
CODE = "B52"
MED_NAME = "resultats_deplacements_lot53.med"
WRITE_SCRIPT = Path(__file__).resolve().parent / "scripts" / "med_ajouter_lot53.py"
TEMPLATE = "PP_MY_EXTREME__DEPL"
SOURCE_FIELDS = 18
"""Fields of resultats.med of lot 52 (4 combinations × 4, envelope × 2)."""


def step_med(ctx: ProjectContext) -> dict[str, Any]:
    t0 = time.perf_counter()
    summary_path = ctx.results_dir / LOT / "exports" / "synthese.json"
    summary = json.loads(summary_path.read_text("utf-8"))
    src = ctx.results_dir / SOURCE_LOT / CODE
    work = ctx.results_dir / LOT / CODE / "med_travail"
    out = ctx.results_dir / LOT / CODE / "MED"
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((src / "med_travail" / "lu.json").read_text("utf-8"))
    spec_52 = json.loads((src / "med_travail" / "spec.json").read_text("utf-8"))
    nodes = np.array([n for _, n in meta["extremites"]], dtype=np.int64)
    keys = [c["key"] for c in summary["champs_med"]]
    with np.load(work / "champs.npz") as stored:
        fields = {k: stored[k] for k in keys}
    data: dict[str, Any] = dict(fields)
    for k in keys:
        data[f"E_{k}"] = fields[k][nodes - 1]
    gap_elno = max(
        float(np.max(np.abs(data[f"E_{k}"] - fields[k][nodes - 1]))) for k in keys
    )
    spec = {
        "maillage": spec_52["maillage"],
        "maillage_elno": spec_52["maillage_elno"],
        "gabarit_depl": TEMPLATE,
        "champs": keys,
        "composantes_depl": list(DEPL),
    }
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    np.savez(work / "spec.npz", **data)
    shutil.copyfile(src / "MED" / "resultats.med", work / "resultats.med")
    shutil.copyfile(WRITE_SCRIPT, work / WRITE_SCRIPT.name)
    try:
        in_image(
            ctx,
            work,
            f"python3 {WRITE_SCRIPT.name} resultats.med spec.json spec.npz "
            f"{MED_NAME} relecture.json",
        )
    finally:
        (work / "resultats.med").unlink(missing_ok=True)
    shutil.move(work / MED_NAME, out / MED_NAME)
    report: dict[str, Any] = json.loads((work / "relecture.json").read_text("utf-8"))
    expected = SOURCE_FIELDS + 2 * len(keys)
    names = report["champs"]
    info = {
        "fichier": MED_NAME,
        "relecture": report,
        "champs_attendus": expected,
        "ecart_construction_elno": gap_elno,
        "correspondance": {
            c["key"]: {
                "maillage_origine": f"{c['key']}__DEPL",
                "support_commun": f"E_{c['key']}__DEPL",
                "titre": c["title"],
                "source": c["source"],
                "choisi_par": c["governing"],
            }
            for c in summary["champs_med"]
        },
        "duree_s": time.perf_counter() - t0,
    }
    info["reussi"] = bool(
        report["champs_source"] == SOURCE_FIELDS
        and report["champs_conserves"]
        and len(names) == expected
        and report["ecart_champs_source"] == 0.0
        and report["ecart_champs_nouveaux"] == 0.0
        and gap_elno == 0.0
        and report["noeuds_elno"] == len(nodes)
    )
    summary["controle_med"] = info
    summary_path.write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )
    print(
        f"{CODE} : {MED_NAME}, {len(names)} champs, contrôle "
        f"{'RÉUSSI' if info['reussi'] else 'ÉCHEC'}"
    )
    return info


__all__ = ["MED_NAME", "step_med"]
