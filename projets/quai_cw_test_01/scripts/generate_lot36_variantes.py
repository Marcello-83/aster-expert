"""Lot 36, étape 2 : génère le `.comm` de base ou de la variante de diagnostic V1
(pression initiale au repos côté bassin, cas G) pour le quai réduit ou le modèle
complet, avec le générateur de production (`quai_cw_test_01.generation.generate`).

La variante V1 est une option de **diagnostic** (`InitialPressureDiagnostic`) : elle ne
sert jamais à produire le modèle de calcul. La base est le `.comm` de production
(octet pour octet celui de `data/examples/lot28_quai/` pour le modèle complet).

Usage : python projets/quai_cw_test_01/scripts/generate_lot36_variantes.py {reduit,complet} {base,v1}
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml

from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.generate import InitialPressureDiagnostic, generate_comm

ROOT = Path(__file__).resolve().parents[3]
FICHE = (
    ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)
OUT_DIR = ROOT / "data" / "examples" / "lot36_butee"
MODELES = {
    "reduit": (
        ROOT / "data/examples/lot30_quai_reduit/model_data_reduit.yaml",
        ROOT / "data/processed/mesh_runs/20260923T135537-6993814e/combiwall_mesh.med",
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
    parser.add_argument("variante", choices=("base", "v1"))
    args = parser.parse_args(argv)
    donnees, maillage = MODELES[args.modele]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        text, report = generate_comm(
            fiche_path=FICHE,
            data_path=donnees,
            med_path=maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=_aster_version_tag(),
            initial_pressure=InitialPressureDiagnostic(
                pression_repos_bassin=args.variante == "v1"
            ),
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1
    nom = f"{args.modele}_{args.variante}"
    (OUT_DIR / f"{nom}.comm").write_text(text, encoding="utf-8")
    shutil.copyfile(maillage, OUT_DIR / f"{nom}.mmed")
    (OUT_DIR / f"{nom}.export").write_text(
        "P time_limit 1800\nP memory_limit 8192\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm {nom}.comm D 1\nF mmed {nom}.mmed D 20\n",
        encoding="utf-8",
    )
    print(f"{nom}.comm : sha256 {report.comm_sha256}, {len(text.splitlines())} lignes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
