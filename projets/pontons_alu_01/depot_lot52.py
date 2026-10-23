"""Delivery of lot 52 for PONTONS-ALU-01 (consigne § Dépôt).

    <dépôt>/<variante>/      exports, efforts_elementaires.npz, geometrie_noeuds.csv
    <dépôt>/B52/MED/         structure.med, charges.med, resultats.med
    <dépôt>/comparaison_variantes.csv (its detail, and B52 against B12 of lot 51 quater)
    <dépôt>/vues/            PNG of B52, view in the file name
    <dépôt>/scripts/         vues_3d_pontons_52.py, afficher_pontons_salome_52.py,
                             lire_npz.py
    <dépôt>/empreintes.sha256

The CSV of more than 100 MB (efforts_elementaires.csv, deplacements_elementaires.csv)
are not delivered (consigne § Exports). New file names only: the delivery refuses a
target folder that already holds files.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.exports_lot51 import sha256

LOT = "lot52"
DEFAULT_TARGET = Path("/media/sf_partage/echanges/lot52/pontons_alu_01")
SCRIPTS = Path(__file__).resolve().parent / "scripts"
DELIVERED_SCRIPTS = {
    "vues_3d_pontons_52.py": SCRIPTS / "paraview" / "vues_3d_pontons_52.py",
    "afficher_pontons_salome_52.py": SCRIPTS
    / "paraview"
    / "afficher_pontons_salome_52.py",
    "lire_npz.py": SCRIPTS / "lire_npz_lot51quater.py",
}
SIZE_LIMIT = 100_000_000
"""Bytes: larger CSV are not delivered."""
COMPARISONS = (
    "comparaison_variantes.csv",
    "comparaison_variantes_detail.csv",
    "comparaison_B52_B12_lot51quater.csv",
)


def delivery_plan(
    ctx: ProjectContext,
    codes: list[str],
    *,
    lot: str = LOT,
    scripts: dict[str, Path] | None = None,
    comparisons: tuple[str, ...] = COMPARISONS,
) -> tuple[dict[str, Path], list[str]]:
    """Published path -> source file, and the files left out (size); lot 54 passes
    its folder, scripts and comparisons."""
    root = ctx.results_dir / lot
    plan: dict[str, Path] = {}
    left: list[str] = []
    for code in codes:
        folder = root / "exports" / code
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue
            if f.suffix == ".csv" and f.stat().st_size > SIZE_LIMIT:
                left.append(f"{code}/{f.name} ({f.stat().st_size / 1e6:.0f} Mo)")
                continue
            plan[f"{code}/{f.name}"] = f
        med = root / code / "MED"
        if med.is_dir():
            for f in sorted(med.glob("*.med")):
                plan[f"{code}/MED/{f.name}"] = f
    for name in comparisons:
        if (root / "exports" / name).is_file():
            plan[name] = root / "exports" / name
    for f in sorted((root / "vues").glob("*.png")):
        plan[f"vues/{f.name}"] = f
    for name, f in (DELIVERED_SCRIPTS if scripts is None else scripts).items():
        plan[f"scripts/{name}"] = f
    return plan, left


def step_depot(
    ctx: ProjectContext,
    codes: list[str],
    target: Path | None,
    **plan_options: Any,
) -> None:
    dest = target or DEFAULT_TARGET
    if dest.exists() and any(dest.iterdir()):
        message = f"dépôt : {dest} n'est pas vide (noms de fichiers neufs exigés)"
        raise FileExistsError(message)
    plan, left = delivery_plan(ctx, codes, **plan_options)
    for name, source in plan.items():
        (dest / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest / name)
    lines = [f"{sha256(dest / n)}  {n}" for n in sorted(plan)]
    (dest / "empreintes.sha256").write_text("\n".join(lines) + "\n", "utf-8")
    size = sum((dest / n).stat().st_size for n in plan)
    print(f"dépôt : {len(plan)} fichiers, {size / 1e6:.0f} Mo, dans {dest}")
    for item in left:
        print(f"non déposé (> 100 Mo) : {item}")


__all__ = ["delivery_plan", "step_depot"]
