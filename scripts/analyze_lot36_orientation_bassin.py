"""Lot 36, étape 2 (préalable à V1) : orientation des mailles de tube côté bassin.

Les faces bassin des bandes de ressorts (`RESS_AV_*` moins `ECRAN_POUSSEE`) ne sont
pas touchées par `ORIE_NORM_COQUE` : leur orientation est celle du MED d'entrée.
Ce script la constate sur le maillage orienté (`fort.81`, relu par `medcoupling` dans
le conteneur) : cosinus de la normale avec la direction radiale sortante du tube.

Usage : python scripts/analyze_lot36_orientation_bassin.py <fort.81> <données> \\
    <sortie.json>
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from aster_expert.agent.model_data import load_model_data
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.meshing.check import dump_med
from aster_expert.meshing.combiwall import build_params
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.invariants import _group_cells
from aster_expert.meshing.normals import _centroid, cell_normal
from aster_expert.validation.validate import resolve_digest_for_version

ROOT = Path(__file__).resolve().parents[1]


def main(med: Path, data_path: Path, out: Path) -> int:
    params = build_params(load_model_data(data_path))
    axes = {f"TUBE_{k:02d}": x for k, x in enumerate(params["tube"]["axes_x"], start=1)}
    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        ROOT / "data" / "processed" / "catalogue",
        None,
        ROOT / "config" / "versions.yaml",
    )
    repository = os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")
    dump, _ = dump_med(
        med,
        project_root=ROOT,
        config=config,
        docker_bin=find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None),
        image_ref=f"{repository}@{digest}",
    )
    ecran = {(lv, i) for _, lv, i in _group_cells(dump, "ECRAN_POUSSEE")}
    tubes = {t: {(lv, i) for _, lv, i in _group_cells(dump, t)} for t in axes}
    report: dict[str, object] = {"med": str(med)}
    for band in ("RESS_AV_ARGI", "RESS_AV_MARNE"):
        cells = [(lv, i) for _, lv, i in _group_cells(dump, band)]
        bassin = [c for c in cells if c not in ecran]
        stats = {
            "mailles_bande": len(cells),
            "mailles_bassin": len(bassin),
            "hors_tube": 0,
            "cos_min": math.inf,
            "cos_max": -math.inf,
            "vers_exterieur": 0,
            "vers_interieur": 0,
            "y_centre_max": -math.inf,
            "non_horizontales": 0,
        }
        for lv, i in bassin:
            tube = next((t for t, m in tubes.items() if (lv, i) in m), None)
            if tube is None:
                stats["hors_tube"] += 1
                continue
            cx, cy, _ = _centroid(dump, lv, i)
            stats["y_centre_max"] = max(stats["y_centre_max"], cy)
            n = cell_normal(dump, lv, i)
            if abs(n[2]) > 1e-9:
                stats["non_horizontales"] += 1
            r = (cx - axes[tube], cy)
            rn = math.hypot(*r)
            cos = (n[0] * r[0] + n[1] * r[1]) / rn
            stats["cos_min"] = min(stats["cos_min"], cos)
            stats["cos_max"] = max(stats["cos_max"], cos)
            stats["vers_exterieur" if cos > 0 else "vers_interieur"] += 1
        report[band] = stats
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
