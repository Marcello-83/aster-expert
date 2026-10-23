"""Delivery of lot 54 for PONTONS-ALU-01 (consigne § Dépôt).

    <dépôt>/B54/, <dépôt>/A54/   exports (CSV, efforts_elementaires.npz, recombiner.py,
                                 incompatibilites.csv ; B54 : déplacements)
    <dépôt>/comparaison_B52_B54.csv, comparaison_variantes.csv
    <dépôt>/vues/                PNG of the notes (B54)
    <dépôt>/scripts/             lire_npz.py, vues_lot54.py
    <dépôt>/empreintes.sha256

The CSV of more than 100 MB are not delivered, as in lot 52 (`depot_lot52`). New file
names only: the delivery refuses a target folder that already holds files.
"""

from __future__ import annotations

from pathlib import Path

from aster_expert.projet.context import ProjectContext
from pontons_alu_01 import depot_lot52

LOT = "lot54"
DEFAULT_TARGET = Path("/media/sf_partage/echanges/lot54/pontons_alu_01")
HERE = Path(__file__).resolve().parent
DELIVERED_SCRIPTS = {
    "lire_npz.py": HERE / "scripts" / "lire_npz_lot51quater.py",
    "vues_lot54.py": HERE / "vues_lot54.py",
}
COMPARISONS = ("comparaison_B52_B54.csv", "comparaison_variantes.csv")


def step_depot(ctx: ProjectContext, codes: list[str], target: Path | None) -> None:
    """The delivery of lot 52 (`depot_lot52.step_depot`) on the folders of lot 54."""
    depot_lot52.step_depot(
        ctx,
        codes,
        target or DEFAULT_TARGET,
        lot=LOT,
        scripts=DELIVERED_SCRIPTS,
        comparisons=COMPARISONS,
    )


__all__ = ["step_depot"]
