"""Lot 43 : invariants de maillage de la suite de convergence (section B de
l'arbitrage), calculés à partir des seuls paramètres, avant toute exécution.

Écrit `maillage/invariants_h<taille>.yaml` pour chaque taille de
`maillage.tailles_convergence` des données. Fichiers générés : ne jamais les éditer.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/invariants_lot43.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.model_data import load_model_data
from dalle_appuyee_01.discretisation import SlabMesh

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
DATA = PROJECT / "donnees" / "dalle_model_data.yaml"


def size_label(size: float) -> str:
    return f"h{size:.3f}".replace(".", "p")


def meshes() -> list[SlabMesh]:
    items = load_model_data(DATA).items()
    sizes = items["maillage.tailles_convergence"].value
    assert isinstance(sizes, tuple)
    length = float(items["geometrie.longueur"].value)  # type: ignore[arg-type]
    width = float(items["geometrie.largeur"].value)  # type: ignore[arg-type]
    return [SlabMesh(length=length, width=width, size=float(s)) for s in sizes]


def invariants_path(mesh: SlabMesh) -> Path:
    return PROJECT / "maillage" / f"invariants_{size_label(mesh.size)}.yaml"


def main() -> int:
    for mesh in meshes():
        path = invariants_path(mesh)
        header = (
            "# Généré par scripts/invariants_lot43.py à partir des paramètres "
            f"(taille {mesh.size} m, {mesh.nx} x {mesh.ny} QUAD4) : ne pas éditer.\n"
        )
        path.write_text(
            header
            + yaml.safe_dump(mesh.invariants(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(
            f"{path.relative_to(ROOT)} : {mesh.nodes} nœuds, {mesh.quads} QUAD4, {mesh.segments} SEG2"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
