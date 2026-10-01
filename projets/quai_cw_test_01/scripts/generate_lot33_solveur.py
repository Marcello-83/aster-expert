"""Lot 33, étape 1 : isole l'effet de deux paramètres hérités des tentatives
du lot 28, jamais démontrés nécessaires isolément (`SOLVEUR/RESI_RELA` et
`AFFE_CARA_ELEM/COQUE/COEF_RIGI_DRZ`, `quai_cw_test_01.generation.comm`).

Deux `.comm` du quai réduit, chacun avec **un seul** des deux paramètres
remis à sa valeur par défaut du catalogue (l'autre restant à sa valeur de
production) -- démonstration isolée, jamais les deux retraits à la fois :

- `quai_reduit_resi_rela_defaut.comm` : `SOLVEUR/RESI_RELA` au défaut
  catalogue (`comm.SOLVER_RESI_RELA_CATALOGUE_DEFAULT`), `COEF_RIGI_DRZ` à
  la valeur de production ;
- `quai_reduit_coef_rigi_drz_defaut.comm` : `COEF_RIGI_DRZ` au défaut
  catalogue (`comm.DRZ_STIFFNESS_COEF_CATALOGUE_DEFAULT`), `RESI_RELA` à la
  valeur de production.

Réutilise le maillage du quai réduit déjà vérifié (lot 30/32, cache de
maillage `data/processed/mesh_runs/verified_meshes.json`) sans y toucher, et
écrit dans `data/examples/lot33_solveur/`, jamais dans
`data/examples/lot28_quai/` (réservé à `aster-expert generate`).

Le point 3 de la fiche est en révision-close (lot 32) : aucune levée de
révision en mémoire n'est nécessaire ici, contrairement à
`projets/quai_cw_test_01/scripts/generate_lot32_regle_cl.py`.

Usage : python projets/quai_cw_test_01/scripts/generate_lot33_solveur.py <maillage vérifié .med>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from quai_cw_test_01.generation import comm
from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.generate import SolverDiagnostics, generate_comm

ROOT = Path(__file__).resolve().parents[3]
FICHE = (
    ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT_DIR = ROOT / "data" / "examples" / "lot33_solveur"

VARIANTS: dict[str, SolverDiagnostics] = {
    # Isolation : seul RESI_RELA passe au défaut catalogue, COEF_RIGI_DRZ
    # reste explicitement à la valeur qu'avait la production avant ce lot
    # (jamais `None`, pour ne jamais dépendre du défaut futur de
    # SolverDiagnostics lui-même -- ce script doit rester reproductible).
    "quai_reduit_resi_rela_defaut": SolverDiagnostics(
        resi_rela=comm.SOLVER_RESI_RELA_CATALOGUE_DEFAULT,
        coef_rigi_drz=comm.DRZ_STIFFNESS_COEF,
    ),
    "quai_reduit_coef_rigi_drz_defaut": SolverDiagnostics(
        resi_rela=comm.SOLVER_RESI_RELA,
        coef_rigi_drz=comm.DRZ_STIFFNESS_COEF_CATALOGUE_DEFAULT,
    ),
}


def _resolve_aster_version_tag(versions_path: Path) -> str:
    data = yaml.safe_load(versions_path.read_text(encoding="utf-8")) or {}
    detected = data.get("detected")
    tag = (
        (detected or {}).get("container", {}).get("image_tag")
        if isinstance(detected, dict)
        else None
    )
    if not tag:
        message = f"aucune version détectée dans {versions_path}"
        raise SystemExit(message)
    return str(tag)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maillage", type=Path, help="MED vérifié (mesh check OK)")
    args = parser.parse_args(argv)

    aster_version = _resolve_aster_version_tag(ROOT / "config" / "versions.yaml")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stem, solver in VARIANTS.items():
        try:
            text, report = generate_comm(
                fiche_path=FICHE,
                data_path=DONNEES,
                med_path=args.maillage,
                project_root=ROOT,
                work_dir_root="data/processed/mesh_runs",
                aster_version=aster_version,
                solver=solver,
            )
        except GenerationError as exc:
            print(f"generate ÉCHEC ({stem}) : {exc}")
            return 1
        output = OUT_DIR / f"{stem}.comm"
        output.write_text(text, encoding="utf-8")
        print(
            f"{stem} : resi_rela={solver.resi_rela}, "
            f"coef_rigi_drz={solver.coef_rigi_drz}"
        )
        print(
            json.dumps(
                json.loads(report.model_dump_json()), indent=2, ensure_ascii=False
            )
        )
        print(f".comm écrit dans {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
