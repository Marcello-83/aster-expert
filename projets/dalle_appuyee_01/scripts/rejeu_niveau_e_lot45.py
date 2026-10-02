"""Lot 45 : rejeu des critères E0, E1 et E2 du lot 43 sur le `.comm` actuel de la dalle.

Décision de MM (partie A du lot 45) : « EYS a changé, donc rejoue E0, E1 et E2 sur le
.comm actuel, si le maillage est versionné. Exception autorisée à l'interdit
d'exécution. » La règle de conservation d'un niveau (paquet de résultats) veut qu'un
niveau ne reste acquis que pour un `.comm` identique, hors commentaires et en-tête, à
celui qui l'a obtenu : celui du lot 43 portait EYS = 210 GPa, celui de l'exécution du
lot 44 EYS = 200 GPa.

Les critères sont ceux du lot 43 (`docs/essais_lot43.md`, commit 4093f12, écrits avant
l'exécution) : ni leur texte ni leurs seuils ne sont réécrits, `evaluate` est celui du
script du lot 43. Les trois maillages sont ceux **versionnés** à côté des cas
(`references/cas/dalle_h*.mmed`) ; aucun maillage n'est regénéré (pas de Salomé), mais
chacun passe `mesh check` contre les invariants versionnés avant d'être utilisé.

Sorties : `references/rejeu_niveau_e_lot45.json` (valeurs lues, verdicts, empreintes des
`.comm` et des maillages) et `references/rejeu_lot45/dalle_h*.comm` (les `.comm`
exécutés). Le répertoire de travail est `resultats/convergence_lot45/` (non versionné).

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/rejeu_niveau_e_lot45.py`
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import niveau_e_lot43 as lot43
from invariants_lot43 import invariants_path, meshes, size_label

from aster_expert.meshing.check import check_med
from aster_expert.meshing.config import load_mesh_config
from aster_expert.projet.pipeline import Runtime

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
CASES_DIR = PROJECT / "references" / "cas"
OUT = PROJECT / "resultats" / "convergence_lot45"
RESULT = PROJECT / "references" / "rejeu_niveau_e_lot45.json"
COMMS = PROJECT / "references" / "rejeu_lot45"
CRITERIA_DOCUMENT = "docs/essais_lot43.md"
CRITERIA_COMMIT = "4093f126b4829bec8fc07a97c67beba010c80fce"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    rt = Runtime(ROOT)
    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, version = rt.aster()
    reference = json.loads(lot43.REFERENCE.read_text(encoding="utf-8"))["cas"]
    lot43.OUT = OUT  # work directory of the replay, never the one of lot 43
    series: list[dict[str, Any]] = []
    for mesh in meshes():
        label = size_label(mesh.size)
        versioned = CASES_DIR / f"dalle_{label}.mmed"
        if not versioned.is_file():
            print(f"maillage versionné absent : {versioned} : rejeu impossible")
            return 1
        work = OUT / label
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        report = check_med(
            versioned,
            invariants_path(mesh),
            project_root=ROOT,
            config=config,
            docker_bin=rt.docker_bin(),
            image_ref=f"{rt.image_repository}@{digest}",
        )
        held = sum(r.ok for r in report.results)
        if not report.ok:
            print(f"mesh check {label} : {held}/{len(report.results)} : arrêt")
            return 1
        text, run_info = lot43.run_case(mesh, versioned, rt)
        comm = work / f"dalle_{label}.comm"
        COMMS.mkdir(exist_ok=True)
        shutil.copyfile(comm, COMMS / comm.name)
        cases = {case: lot43.read_case(text, case) for case in lot43.CASES}
        for case, values in cases.items():
            ref = reference[case]
            values["w"] = -values["DZ"]
            values["mx"] = -values["MXX"]
            values["my"] = -values["MYY"]
            values["erreurs"] = {
                q: (values[q] - ref[f"{q}_m" if q == "w" else f"{q}_nm_par_m"])
                / ref[f"{q}_m" if q == "w" else f"{q}_nm_par_m"]
                for q in lot43.QUANTITIES
            }
        series.append(
            {
                "taille_m": mesh.size,
                "mailles": f"{mesh.nx} x {mesh.ny}",
                "maillage": {
                    "versionne": str(versioned.relative_to(ROOT)),
                    "sha256": _sha(versioned),
                    "mesh_check": f"{held}/{len(report.results)}",
                },
                "comm": {
                    "chemin": str((COMMS / comm.name).relative_to(ROOT)),
                    "sha256": _sha(comm),
                },
                "execution": run_info,
                "cas": cases,
                "ferraillage": lot43.rebar_at_centre(text),
            }
        )
        print(
            f"{label} : {run_info['statut']} {run_info['duree_s']} s, "
            f"mesh check {held}/{len(report.results)}"
        )
    verdicts = lot43.evaluate(series)
    RESULT.write_text(
        json.dumps(
            {
                "rejeu_de": "references/niveau_e_lot43.json",
                "motif": (
                    "EYS passé de 210 GPa (lot 43) à 200 GPa (décision de MM, lot 44) : "
                    "le .comm n'est plus celui qui avait obtenu le niveau E"
                ),
                "criteres": {
                    "document": CRITERIA_DOCUMENT,
                    "commit": CRITERIA_COMMIT,
                    "note": "critères du lot 43, ni texte ni seuils réécrits",
                },
                "code_aster": {"version": version, "image_digest": digest},
                "series": series,
                "verdicts": verdicts,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for key, value in verdicts.items():
        print(key, value["verdict"], value.get("detail", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
