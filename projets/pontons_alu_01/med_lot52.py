"""MED files of lot 52 for PONTONS-ALU-01 (consigne § Vues et MED), variant B52.

Method of lot 51 quater (`med_lot51quater`): the unit fields Code_Aster wrote in MED
(post-processing run of the project chain on the `.comm` of this lot, unchanged, copied
under `resultats/lot52/B52/med_unitaires/`) are read by medcoupling in the Code_Aster
image, checked against the E25.16 tables of the lot run, combined here, and written by
`scripts/med_ecrire_lot52.py`.

New (defect reported at lot 51 quater): in `resultats.med`, a second mesh
`PONTON_B52_ELNO` where each SEG2 of the bars has its own two nodes; the displacements
(DEPL of the original node) and the forces (EFGE_ELNO of the element end) of each
combination, and the ULS envelopes, are fields ON_NODES of that mesh, so that the
deformed shape can be coloured by a force component. The fields of the original mesh
are kept.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.exports_lot51 import DEPL, EFGE
from pontons_alu_01.exports_lot51quater import Variant51quater
from pontons_alu_01.exports_lot52 import load
from pontons_alu_01.med_lot51quater import (
    ENVELOPE_COMPONENTS,
    READ_SCRIPT,
    build_spec,
    check_unit_fields,
    in_image,
)

LOT = "lot52"
WRITE_SCRIPT = Path(__file__).resolve().parent / "scripts" / "med_ecrire_lot52.py"
ELNO_GROUPS = (
    "POUTRES_PRINC",
    "MONTANTS",
    "MONTANTS_TRONCONS",
    "DIAGONALES",
    "PANNES_SEC",
    "PANNE_RIVE",
    "CHEVETRES",
    "LONGRINES",
    "PILES",
)


def variant_dir(ctx: ProjectContext, code: str) -> Path:
    return ctx.results_dir / LOT / code


def read_unit(ctx: ProjectContext, code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = variant_dir(ctx, code)
    work = base / "med_travail"
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "lu.json").is_file():
        for name in ("resultats.med", "charges.med"):
            shutil.copyfile(base / "med_unitaires" / name, work / name)
        shutil.copyfile(READ_SCRIPT, work / READ_SCRIPT.name)
        try:
            in_image(
                ctx,
                work,
                f"python3 {READ_SCRIPT.name} resultats.med charges.med lu.npz lu.json",
            )
        finally:
            for name in ("resultats.med", "charges.med"):
                (work / name).unlink(missing_ok=True)
    meta = json.loads((work / "lu.json").read_text("utf-8"))
    with np.load(work / "lu.npz") as data:
        arrays = {k: data[k] for k in data.files}
    return meta, arrays


def elno_support(
    v: Variant51quater,
    code: str,
    meta: dict[str, Any],
    spec: dict[str, Any],
    data: dict[str, NDArray[Any]],
) -> dict[str, Any]:
    """Coordinates, connectivity and groups of the ELNO mesh, and the combined fields
    on it; checked against the fields of the original mesh."""
    layout = [tuple(x) for x in meta["extremites"]]
    coords = v.vd.model.coords
    nodes = np.array([n for _, n in layout], dtype=np.int64)
    cells = [c for c, _ in layout]
    if cells[0::2] != cells[1::2]:
        message = (
            "extrémités EFGE_ELNO : deux extrémités consécutives par maille attendues"
        )
        raise ValueError(message)
    elno_coords = coords[nodes - 1]
    conn = np.arange(len(layout), dtype=np.int64).reshape(-1, 2)
    cell_of = {c - 1: k for k, c in enumerate(cells[0::2])}
    groups: dict[str, list[int]] = {}
    for name, grp in {**meta["groupes"], **spec["groupes_ajoutes"]}.items():
        if grp["level"] != -1:
            continue
        if name in ELNO_GROUPS or name.startswith(("TRAVEE_", "PALEE_")):
            ids = sorted(cell_of[i] for i in grp["ids"] if i in cell_of)
            if ids:
                groups[name] = ids
    elno_depl = data["comb_depl"][:, nodes - 1, :]
    elno_efge = data["comb_efge"]
    gap = float(
        max(
            np.max(np.abs(elno_depl - data["comb_depl"][:, nodes - 1, :])),
            np.max(np.abs(elno_coords - coords[nodes - 1])),
        )
    )
    spec.update(
        {
            "maillage_elno": f"PONTON_{code}_ELNO",
            "groupes_elno": groups,
            "composantes_depl": list(DEPL),
            "composantes_efge": list(EFGE),
        }
    )
    data.update(
        {
            "elno_coords": elno_coords,
            "elno_conn": conn,
            "elno_depl": elno_depl,
            "elno_efge": elno_efge,
            "elno_enveloppe": data["enveloppe"],
        }
    )
    return {
        "noeuds": len(layout),
        "mailles": len(conn),
        "groupes": len(groups),
        "ecart_construction": gap,
    }


def write_med(
    ctx: ProjectContext, code: str, spec: dict[str, Any], data: dict[str, NDArray[Any]]
) -> dict[str, Any]:
    base = variant_dir(ctx, code)
    work = base / "med_travail"
    out = base / "MED"
    out.mkdir(parents=True, exist_ok=True)
    (work / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), "utf-8")
    np.savez(work / "spec.npz", **data)  # type: ignore[arg-type]
    for name in ("resultats.med", "charges.med"):
        shutil.copyfile(base / "med_unitaires" / name, work / name)
    shutil.copyfile(WRITE_SCRIPT, work / WRITE_SCRIPT.name)
    try:
        in_image(
            ctx,
            work,
            f"python3 {WRITE_SCRIPT.name} resultats.med charges.med spec.json "
            "spec.npz sortie",
        )
    finally:
        for name in ("resultats.med", "charges.med"):
            (work / name).unlink(missing_ok=True)
    for name in ("structure.med", "charges.med", "resultats.med"):
        shutil.move(work / "sortie" / name, out / name)
    report: dict[str, Any] = json.loads(
        (work / "sortie" / "relecture.json").read_text("utf-8")
    )
    return report


def check_envelope(ctx: ProjectContext, code: str, env: NDArray[Any]) -> dict[str, Any]:
    path = ctx.results_dir / LOT / "exports" / "synthese.json"
    pp = json.loads(path.read_text("utf-8"))[code]["comparaison"]["PP_My"]
    return {
        "PP_My_comparaison_kNm": pp["value"],
        "PP_My_etat": pp["state"],
        "MFY_enveloppe_extremes_kNm": [
            float(env[:, 2].max()) * 1e-3,
            float(env[:, 3].min()) * 1e-3,
        ],
    }


def step_med(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    for code in codes:
        t0 = time.perf_counter()
        meta, arrays = read_unit(ctx, code)
        v = load(ctx, code, state)
        info: dict[str, Any] = {
            "controle_champs_unitaires": check_unit_fields(v, meta, arrays)
        }
        spec, data, checks = build_spec(code, v, meta, arrays)
        info.update(checks)
        info["support_elno"] = elno_support(v, code, meta, spec, data)
        info["controle_enveloppe"] = check_envelope(ctx, code, data["enveloppe"])
        report = write_med(ctx, code, spec, data)
        expected_groups = len(meta["groupes"]) + len(spec["groupes_ajoutes"])
        n_comb = len(spec["combinaisons"])
        info["relecture"] = report
        info["attendu"] = {
            "noeuds": meta["noeuds"],
            "niveaux": meta["niveaux"],
            "groupes": expected_groups,
            "champs_charges": meta["champs_charges"] + len(spec["evenements"]),
            "champs_resultats": 4 * n_comb + 2,
            "maillage_elno": {
                "noeuds": info["support_elno"]["noeuds"],
                "mailles": info["support_elno"]["mailles"],
                "groupes": info["support_elno"]["groupes"],
            },
        }
        ok = all(
            report[f]["noeuds"] == meta["noeuds"]
            and report[f]["niveaux"] == meta["niveaux"]
            and report[f]["groupes"] == expected_groups
            for f in ("structure.med", "charges.med", "resultats.med")
        )
        ok = ok and (
            len(report["charges.med"]["champs"]) == info["attendu"]["champs_charges"]
            and len(report["resultats.med"]["champs"])
            == info["attendu"]["champs_resultats"]
            and report["maillage_elno"] == info["attendu"]["maillage_elno"]
        )
        info["controle_med_reussi"] = bool(
            ok
            and info["controle_champs_unitaires"]["reussi"]
            and checks["combinaisons_contre_tables_ecart_relatif_max"] <= 1e-9
            and info["support_elno"]["ecart_construction"] == 0.0
            and all(
                r["ecart_relatif"] <= 1e-9
                for r in checks["resultantes_evenements"].values()
            )
            and max(
                report[f]["ecart_relecture_max"] for f in report if f.endswith(".med")
            )
            == 0.0
        )
        info["duree_s"] = time.perf_counter() - t0
        path = variant_dir(ctx, code) / "med_controles.json"
        path.write_text(
            json.dumps(info, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
        )
        (variant_dir(ctx, code) / "combinaisons_vues.json").write_text(
            json.dumps(checks["combinaisons"], indent=1, ensure_ascii=False) + "\n",
            "utf-8",
        )
        verdict = "RÉUSSI" if info["controle_med_reussi"] else "ÉCHEC"
        print(f"{code} : MED écrits, contrôle {verdict}")


__all__ = ["ELNO_GROUPS", "ENVELOPE_COMPONENTS", "step_med"]
