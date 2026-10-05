"""Lot 47 -- writes the mesh invariants and parameters of the convergence series.

`maillage/invariants_<h>.yaml` and `maillage/params_<h>.json` for each size of
`CONVERGENCE_SIZES`, computed from the data only (never read from a MED): do not
edit, rerun `.venv/bin/python projets/estacade_pieux_01/scripts/invariants_lot47.py`.
A test replays the script and compares byte for byte.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aster_expert.projet.context import load_project
from estacade_pieux_01.discretisation import CONVERGENCE_SIZES, JettyMesh
from estacade_pieux_01.donnees import model_values

REPO = Path(__file__).resolve().parents[3]
HEADER = (
    "# Invariants du maillage de l'estacade (lot 47), taille {h} m : générés par\n"
    "# projets/estacade_pieux_01/scripts/invariants_lot47.py à partir des données,\n"
    "# avant toute exécution. Ne pas éditer.\n"
)


def outputs() -> dict[Path, bytes]:
    ctx = load_project("estacade_pieux_01", REPO)
    values = model_values(ctx)
    out: dict[Path, bytes] = {}
    for size in CONVERGENCE_SIZES:
        mesh = JettyMesh(values, size)
        label = mesh.label()
        text = HEADER.format(h=size) + yaml.safe_dump(
            mesh.invariants(), allow_unicode=True, sort_keys=False, width=100
        )
        out[ctx.project_dir / "maillage" / f"invariants_{label}.yaml"] = text.encode()
        out[ctx.project_dir / "maillage" / f"params_{label}.json"] = (
            mesh.parameters_bytes()
        )
    return out


def main() -> None:
    for path, data in outputs().items():
        path.write_bytes(data)
        print(path.relative_to(REPO), len(data))


if __name__ == "__main__":
    main()
