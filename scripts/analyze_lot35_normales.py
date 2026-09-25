"""Lot 35, étape 1 (point 4) : vérifie explicitement l'orientation des normales de
chaque maille de chaque groupe de couche de `ECRAN_POUSSEE`, sur le maillage tel que
Code_Aster le tient après `MODI_MAILLAGE/ORIE_NORM_COQUE` (écrit en MED par le `.comm`
exécuté, unité 81 -- `aster_expert.generation.comm.oriented_mesh_block`).

Remplace la vérification désactivée (`VERI_NORM="NON"`) des charges par couche :
`aster_expert.meshing.normals.check_layer_normals`. Le MED est lu par `medcoupling`
dans le conteneur (`aster_expert.meshing.check.dump_med`), jamais par Salomé.

Usage : python scripts/analyze_lot35_normales.py <fort.81> <données> [--sortie PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from aster_expert.agent.model_data import load_model_data
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.generation import comm
from aster_expert.generation.profiles import layer_profiles
from aster_expert.generation.values import ModelValues
from aster_expert.meshing.check import dump_med
from aster_expert.meshing.combiwall import build_params
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.invariants import MedDump, _group_cells
from aster_expert.meshing.normals import check_layer_normals
from aster_expert.validation.validate import resolve_digest_for_version

ROOT = Path(__file__).resolve().parents[1]


def _flip_first_cell(dump: MedDump, group: str) -> MedDump:
    """Copie du dump où la première maille de `group` a son ordre de nœuds inversé
    (donc sa normale)."""
    _, level, cell_id = _group_cells(dump, group)[0]
    key = str(level)
    connectivity = list(dump.levels[key].connectivity)
    connectivity[cell_id] = tuple(reversed(connectivity[cell_id]))
    levels = {
        **dump.levels,
        key: dump.levels[key].model_copy(update={"connectivity": tuple(connectivity)}),
    }
    return dump.model_copy(update={"levels": levels})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("med", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("--sortie", type=Path, default=None)
    parser.add_argument(
        "--altere",
        action="store_true",
        help="essai d'altération : inverse l'ordre des nœuds d'une maille du premier "
        "groupe de couche avant le contrôle, qui doit alors échouer",
    )
    args = parser.parse_args(argv)

    data = load_model_data(args.donnees)
    params = build_params(data)
    earth = ModelValues(data).profile_si("eau_terres.profil_poussee_terres_permanent")
    layers = layer_profiles(earth, "G")
    layer_groups = [comm.layer_group_name(layer) for layer in layers]
    tube_axes = {
        f"TUBE_{k:02d}": x for k, x in enumerate(params["tube"]["axes_x"], start=1)
    }

    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        ROOT / "data" / "processed" / "catalogue",
        None,
        ROOT / "config" / "versions.yaml",
    )
    repository = os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")
    dump, work_dir = dump_med(
        args.med,
        project_root=ROOT,
        config=config,
        docker_bin=find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None),
        image_ref=f"{repository}@{digest}",
    )
    if args.altere:
        dump = _flip_first_cell(dump, layer_groups[0])
    results = check_layer_normals(
        dump, layer_groups=layer_groups, tube_axes=tube_axes, sheet_group="PALPS"
    )
    ok = all(r.ok for r in results)
    for r in results:
        print(
            f"[{'OK' if r.ok else 'ÉCART':6}] {r.label} | attendu : {r.expected} "
            f"| obtenu : {r.obtained}"
        )
    print(f"\n{'Toutes les normales sont conformes.' if ok else 'ÉCART.'}")
    if args.sortie is not None:
        args.sortie.write_text(
            json.dumps(
                {
                    "med": str(args.med),
                    "lecture": str(work_dir),
                    "ok": ok,
                    "resultats": [json.loads(r.model_dump_json()) for r in results],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
