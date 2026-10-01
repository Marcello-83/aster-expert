"""Lot 41 bis, étape 4 : rend rejouables les constats CA-029, CA-034, CA-035, CA-036.

Les six cas archivés au lot 35 (`data/examples/lot35_constats/`) lisent un maillage
(`LIRE_MAILLAGE`, unité 20) qui n'était pas versionné à côté d'eux : le rejeu du lot
41 les a déclarés « non rejouables en l'état ». Les six exécutions d'origine
(`data/processed/runs/20260924T…`, non versionnées) lisaient toutes le même fichier,
le maillage du quai réduit déjà versionné au lot 30
(`data/examples/lot30_quai_reduit/quai_reduit.mmed`, SHA-256 `507a0942…`).

Pour chaque cas `<nom>.comm`, ce script écrit à côté de lui `<nom>.mmed` (copie à
l'octet de ce maillage) et `<nom>.export` (mêmes paramètres que l'`.export` des
exécutions d'origine, noms de fichiers du cas). Les cas eux-mêmes ne sont pas
touchés : leur empreinte reste celle des constats. Idempotent.

Usage : python projets/quai_cw_test_01/scripts/versionner_maillages_lot41bis.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES_DIR = ROOT / "data" / "examples" / "lot35_constats"
MESH = ROOT / "data" / "examples" / "lot30_quai_reduit" / "quai_reduit.mmed"
MESH_SHA256 = "507a0942d5c1e0bd07325e443e511f061432e625b0262a53d96b12355812b5b6"
# Cas -> empreinte attendue (celle des constats) ; exécution d'origine en commentaire.
CASES = {
    "f1_avant.sonde": "8a7dbf6d8a465c3d",  # 20260924T152937-a4da70cf, CA-029
    "f1_apres.sonde": "0c2754ddbcbccfb0",  # 20260924T155826-b6368ff9, CA-029
    "f2_avant.ressorts": "646598c7855046e5",  # 20260924T153701-fcac67f2, CA-034
    "f2_apres.ressorts": "97ce90bec429e780",  # 20260924T154200-f7ec9180, CA-034
    "f3_nodal.sonde": "5e9a74d6c1108554",  # 20260924T151447-7d8347d4, CA-035
    "f4_reactions.controles": "9ada8a2dbb739df7",  # 20260924T153254-726c58d9, CA-036
}
# Paramètres des `.export` des six exécutions d'origine (identiques entre elles).
EXPORT = """P time_limit 1800
P memory_limit 8192
P ncpus 1
P mpi_nbcpu 1
P mpi_nbnoeud 1
F comm {name}.comm D 1
F mmed {name}.mmed D 20
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if _sha(MESH) != MESH_SHA256:
        print(f"{MESH} : empreinte inattendue", file=sys.stderr)
        return 1
    for name, prefix in CASES.items():
        comm = CASES_DIR / f"{name}.comm"
        if not _sha(comm).startswith(prefix):
            print(f"{comm} : empreinte différente de celle du constat", file=sys.stderr)
            return 1
        mesh = CASES_DIR / f"{name}.mmed"
        if not mesh.is_file() or _sha(mesh) != MESH_SHA256:
            shutil.copyfile(MESH, mesh)
        (CASES_DIR / f"{name}.export").write_text(
            EXPORT.format(name=name), encoding="utf-8"
        )
        print(f"{name} : .mmed et .export écrits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
