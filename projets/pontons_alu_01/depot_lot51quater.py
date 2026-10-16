"""Delivery of lot 51 quater for PONTONS-ALU-01 (consigne § Dépôt).

    <dépôt>/<variante>/      exports, efforts_elementaires.npz (forces CSV: B10 only)
    <dépôt>/<variante>/MED/  structure.med, charges.med, resultats.med (B10, B12)
    <dépôt>/comparaison_variantes.csv (and its detail)
    <dépôt>/vues/            PNG, variant and view in the file name
    <dépôt>/scripts/         vues_3d_pontons.py, afficher_pontons_salome.py,
                             lire_npz_lot51quater.py
    <dépôt>/empreintes.sha256

New file names only: the delivery refuses a target folder that already holds files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.exports_lot51 import sha256

LOT = "lot51quater"
DEFAULT_TARGET = Path("/media/sf_partage/echanges/lot51quater/pontons_alu_01")
SCRIPTS = Path(__file__).resolve().parent / "scripts"
DELIVERED_SCRIPTS = (
    SCRIPTS / "paraview" / "vues_3d_pontons.py",
    SCRIPTS / "paraview" / "afficher_pontons_salome.py",
    SCRIPTS / "lire_npz_lot51quater.py",
)
FORCES_CSV = "efforts_elementaires.csv"
FORCES_CSV_VARIANT = "B10"


def delivery_plan(ctx: ProjectContext, codes: list[str]) -> dict[str, Path]:
    """Published path -> source file."""
    root = ctx.results_dir / LOT
    plan: dict[str, Path] = {}
    for code in codes:
        folder = root / "exports" / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue
            if f.name == FORCES_CSV and code != FORCES_CSV_VARIANT:
                continue
            plan[f"{code}/{f.name}"] = f
        med = root / code / "MED"
        if med.is_dir():
            for f in sorted(med.glob("*.med")):
                plan[f"{code}/MED/{f.name}"] = f
    for name in ("comparaison_variantes.csv", "comparaison_variantes_detail.csv"):
        plan[name] = root / "exports" / name
    for f in sorted((root / "vues").glob("*.png")):
        plan[f"vues/{f.name}"] = f
    for f in DELIVERED_SCRIPTS:
        plan[f"scripts/{f.name}"] = f
    return plan


def step_depot(ctx: ProjectContext, codes: list[str], target: Path | None) -> None:
    dest = target or DEFAULT_TARGET
    if dest.exists() and any(dest.iterdir()):
        message = f"dépôt : {dest} n'est pas vide (noms de fichiers neufs exigés)"
        raise FileExistsError(message)
    plan = delivery_plan(ctx, codes)
    for name, source in plan.items():
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest / name)
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(plan)]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    size = sum((dest / n).stat().st_size for n in plan)
    print(f"dépôt : {len(plan)} fichiers, {size / 1e6:.0f} Mo, dans {dest}")


__all__ = ["delivery_plan", "step_depot"]
