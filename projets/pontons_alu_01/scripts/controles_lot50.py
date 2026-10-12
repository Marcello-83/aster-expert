"""Contrôles analytiques du lot 50 (docs/essais_lot50.md § 2, critères écrits avant).

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/controles_lot50.py

Lit `resultats/controles/equilibre.json` et les livrables ; écrit
`references/controles_lot50/controles_analytiques.json`.
"""

from pathlib import Path

from aster_expert.projet.context import load_project
from pontons_alu_01.controles_analytiques import write

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    ctx = load_project("pontons_alu_01", ROOT)
    target = ctx.path("references/controles_lot50/controles_analytiques.json")
    result = write(ctx, target)
    for key in ("G1", "Q_mi_portee"):
        print(key, result[key]["verdict"], f"{result[key]['ecart_relatif']:.3e}")


if __name__ == "__main__":
    main()
