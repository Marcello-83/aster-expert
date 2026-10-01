"""Lot 37, étape 4 : génère le `.comm` de production (demi-section des tirants de
bord, poutre de couronnement en `POU_D_T`) du modèle complet ou du quai réduit
(maillage courant ou raffiné ×2, critère C10), avec le générateur de production
(`quai_cw_test_01.generation.generate`), sans aucune option de diagnostic.

Usage : python projets/quai_cw_test_01/scripts/generate_lot37.py {complet,reduit,reduit_fin} [--maillage MED]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml

from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.generate import generate_comm

ROOT = Path(__file__).resolve().parents[3]
FICHE = (
    ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)
OUT_DIR = ROOT / "data" / "examples" / "lot37_efforts"
MODELES = {
    "reduit": (
        ROOT / "data/examples/lot30_quai_reduit/model_data_reduit.yaml",
        ROOT / "data/processed/mesh_runs/20260923T135537-6993814e/combiwall_mesh.med",
    ),
    "reduit_fin": (
        ROOT / "data/examples/lot37_efforts/quai_reduit_fin/model_data.yaml",
        None,
    ),
    "complet": (
        ROOT / "projets/quai_cw_test_01/donnees/combiwall_model_data.yaml",
        ROOT / "data/processed/mesh_runs/20260922T071600-8d931d77/combiwall_mesh.med",
    ),
}


def _aster_version_tag() -> str:
    data = yaml.safe_load((ROOT / "config/versions.yaml").read_text(encoding="utf-8"))
    return str(data["detected"]["container"]["image_tag"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modele", choices=sorted(MODELES))
    parser.add_argument("--maillage", type=Path, default=None)
    args = parser.parse_args(argv)
    donnees, maillage = MODELES[args.modele]
    maillage = args.maillage or maillage
    if maillage is None:
        print("generate ÉCHEC : --maillage est obligatoire pour ce modèle")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        text, report = generate_comm(
            fiche_path=FICHE,
            data_path=donnees,
            med_path=maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=_aster_version_tag(),
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1
    (OUT_DIR / f"{args.modele}.comm").write_text(text, encoding="utf-8")
    shutil.copyfile(maillage, OUT_DIR / f"{args.modele}.mmed")
    (OUT_DIR / f"{args.modele}.export").write_text(
        "P time_limit 1800\nP memory_limit 8192\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm {args.modele}.comm D 1\n"
        f"F mmed {args.modele}.mmed D 20\n",
        encoding="utf-8",
    )
    print(
        f"{args.modele}.comm : sha256 {report.comm_sha256}, "
        f"{len(text.splitlines())} lignes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
