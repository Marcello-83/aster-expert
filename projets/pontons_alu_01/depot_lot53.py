"""Delivery of lot 53 for PONTONS-ALU-01 (consigne § Dépôt).

    <dépôt>/B52/          deplacements_unitaires.csv, deplacements_evenements.csv,
                          deplacements_combinaisons.csv, deplacements_synthese.csv,
                          synthese_lot53.json (controls, MED fields)
    <dépôt>/B52/MED/      resultats_deplacements_lot53.med
    <dépôt>/vues/         PNG (views A, B, C; two PNG of the ParaVis script)
    <dépôt>/scripts/      afficher_pontons_salome_53.py, verifier_evenements_lot53.py
    <dépôt>/empreintes.sha256

New file names only: the delivery refuses a target folder that already holds files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.exports_lot51 import sha256

LOT = "lot53"
CODE = "B52"
DEFAULT_TARGET = Path("/media/sf_partage/echanges/lot53/pontons_alu_01")
SCRIPTS = Path(__file__).resolve().parent / "scripts"
DELIVERED_SCRIPTS = {
    "afficher_pontons_salome_53.py": SCRIPTS
    / "paraview"
    / "afficher_pontons_salome_53.py",
    "verifier_evenements_lot53.py": SCRIPTS / "verifier_evenements_lot53.py",
}


def delivery_plan(ctx: ProjectContext) -> dict[str, Path]:
    """Published path -> source file."""
    root = ctx.results_dir / LOT
    plan: dict[str, Path] = {}
    for f in sorted((root / "exports" / CODE).glob("*.csv")):
        plan[f"{CODE}/{f.name}"] = f
    plan[f"{CODE}/synthese_lot53.json"] = root / "exports" / "synthese.json"
    for f in sorted((root / CODE / "MED").glob("*.med")):
        plan[f"{CODE}/MED/{f.name}"] = f
    for f in sorted((root / "vues").glob("*.png")):
        plan[f"vues/{f.name}"] = f
    for name, f in DELIVERED_SCRIPTS.items():
        plan[f"scripts/{name}"] = f
    return plan


def step_depot(ctx: ProjectContext, target: Path | None) -> None:
    dest = target or DEFAULT_TARGET
    if dest.exists() and any(dest.iterdir()):
        message = f"dépôt : {dest} n'est pas vide (noms de fichiers neufs exigés)"
        raise FileExistsError(message)
    plan = delivery_plan(ctx)
    for name, source in plan.items():
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest / name)
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(plan)]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    size = sum((dest / n).stat().st_size for n in plan)
    print(f"dépôt : {len(plan)} fichiers, {size / 1e6:.1f} Mo, dans {dest}")


__all__ = ["delivery_plan", "step_depot"]
