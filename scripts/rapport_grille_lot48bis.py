"""Lot 48 bis, étape 6 : l'invariant de grille sur les maillages versionnés (rapport).

Pour chaque maillage de la liste : lecture par `medcoupling` (conteneur),
`check_grid` avec la règle de `config/arrondis.yaml` ; aucun maillage n'est modifié.
Pour trois d'entre eux, la sonde `sonde_arrondi_med.py` écrit une copie arrondie (hors
dépôt) et compare les tailles : le fait 6.1 (arrondir ne réduit ni la taille ni le
nombre de lignes).

    .venv/bin/python scripts/rapport_grille_lot48bis.py
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from aster_expert.arrondis import load_table
from aster_expert.execution.container_env import build_environment_setup_script
from aster_expert.execution.docker_client import (
    find_docker_binary,
    run_in_container,
)
from aster_expert.meshing.check import dump_med
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.grille import check_grid
from aster_expert.validation.validate import resolve_digest_for_version

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "examples" / "lot48bis_grille"
MESHES = [
    "data/examples/lot26_essais/plaque_raidisseur/med/lot26_g1.med",
    "data/examples/lot26_essais/poutre_barre/med/lot26_g3.med",
    "data/examples/lot26_essais/tube_plaques/med/lot26_g2.med",
    "data/examples/lot27_maillage/med/combiwall_mesh.med",
    "data/examples/lot28_quai/quai_combiwall.mmed",
    "data/examples/lot30_quai_reduit/quai_reduit.mmed",
    "data/examples/lot37_efforts/reduit_fin.mmed",
    "projets/dalle_appuyee_01/references/cas/dalle_h0p500.mmed",
    "projets/dalle_appuyee_01/references/cas/dalle_h0p250.mmed",
    "projets/dalle_appuyee_01/references/cas/dalle_h0p125.mmed",
    "projets/estacade_pieux_01/references/cas/estacade_pieux_01.mmed",
]
SONDES = {MESHES[7], MESHES[9], MESHES[3]}


def main() -> None:
    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        ROOT / "data" / "processed" / "catalogue",
        None,
        ROOT / "config" / "versions.yaml",
    )
    docker = find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
    image = f"simvia/code_aster@{digest}"
    rule = load_table(ROOT).maillage
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for relative in MESHES:
        med = ROOT / relative
        dump, work = dump_med(
            med, project_root=ROOT, config=config, docker_bin=docker, image_ref=image
        )
        report = check_grid(dump.coords, rule)
        row = {
            "maillage": relative,
            "taille_octets": med.stat().st_size,
            "grille": json.loads(report.model_dump_json()),
        }
        if relative in SONDES:
            row["sonde_arrondi"] = sonde(med, docker, image, work)
        rows.append(row)
        print(relative, report.line(), flush=True)
    (OUT / "rapport_grille.json").write_text(
        json.dumps(
            {
                "regle": json.loads(rule.model_dump_json()),
                "grille_m": rule.grid,
                "maillages": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def sonde(med: Path, docker: Path, image: str, work: Path) -> dict[str, object]:
    folder = work / f"sonde-{uuid.uuid4().hex[:6]}"
    folder.mkdir()
    shutil.copy2(med, folder / "in.med")
    shutil.copy2(ROOT / "scripts" / "sonde_arrondi_med.py", folder)
    command = (
        build_environment_setup_script()
        + "\npython3 /work/sonde_arrondi_med.py"
        + " /work/in.med /work/out.med /work/s.json\n"
    )
    result = run_in_container(
        docker_bin=docker,
        image_ref=image,
        workdir=folder,
        command=command,
        network="none",
        memory="4096m",
        cpus="2",
        timeout=900,
        container_name=f"aster-expert-sonde-{uuid.uuid4().hex}",
    )
    if result.returncode != 0:
        raise SystemExit(result.stderr[-800:])
    data: dict[str, object] = json.loads((folder / "s.json").read_text("utf-8"))
    shutil.rmtree(folder)
    return data


if __name__ == "__main__":
    main()
