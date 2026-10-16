"""Lot 51 quater of PONTONS-ALU-01: houle « tablier noyé » (P60), quasi-static impact
(P61), from the unit cases of lot 51 ter (no Code_Aster run for the results).

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot51quater.py <étape> \
        [--variantes A10,B10,...] [--paralleles 4] [--depot <dossier>]

Étapes : `exports` (recombinaison, CSV, `.npz`, comparaison et contrôles d'identité,
`exports_lot51quater`), `med` (structure, charges et résultats combinés de B10 et B12,
`med_lot51quater`), `vues` (PNG de B10 et B12, `vues_3d_pontons.py` et la coupe), `depot`
(copie sur le partage, empreintes), `tout`. Tout est écrit sous
`resultats/lot51quater/` ; les exécutions lues sont celles de `resultats/lot51ter/etat.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01.variantes_lot51ter import variants

ROOT = Path(__file__).resolve().parents[3]
MED_VARIANTS = ("B10", "B12")


def lot51ter_state(ctx: ProjectContext) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (ctx.results_dir / "lot51ter" / "etat.json").read_text("utf-8")
    )
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("etape", choices=("exports", "med", "vues", "depot", "tout"))
    parser.add_argument("--variantes", default="")
    parser.add_argument("--paralleles", type=int, default=4)
    parser.add_argument("--depot", type=Path, default=None)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    codes = [c for c in args.variantes.split(",") if c] or list(variants())
    state = lot51ter_state(ctx)
    if args.etape in ("exports", "tout"):
        from pontons_alu_01.exports_lot51quater import step_exports  # noqa: PLC0415

        step_exports(ctx, codes, state, workers=args.paralleles)
    if args.etape in ("med", "tout"):
        from pontons_alu_01.med_lot51quater import step_med  # noqa: PLC0415

        step_med(ctx, [c for c in codes if c in MED_VARIANTS], state)
    if args.etape in ("vues", "tout"):
        from pontons_alu_01.vues_lot51quater import step_vues  # noqa: PLC0415

        step_vues(ctx, [c for c in codes if c in MED_VARIANTS], state)
    if args.etape in ("depot", "tout"):
        from pontons_alu_01.depot_lot51quater import step_depot  # noqa: PLC0415

        step_depot(ctx, codes, args.depot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
