"""Lit un MED de résultats avec `medcoupling` (autonome : ni Salomé, ni le projet).

S'exécute dans l'image Docker de `cave` (`aster_expert.report.med_read`), dont le
Python porte `medcoupling`, `MEDLoader` et `numpy`. Usage :

    python3 med_results_dump.py <fichier.med> <sortie.json> inventory
    python3 med_results_dump.py <fichier.med> <sortie.json> extract <champ> [<champ>...]

`inventory` : nombre de nœuds, niveaux de maillage, champs (nom MED complet,
composantes, supports, pas de temps), écrit dans `<sortie.json>`.

`extract` : écrit `<sortie.json>` (métadonnées : groupes, composantes, tableaux
présents) et `<sortie>.npz` (tableaux) :

- `coords` : (n_nœuds, 3) ; `conn_<niv>` : (n_mailles, n_max) nœuds de chaque maille du
  niveau `niv` (0 = coques, -1 = segments, -2 = ponctuels), complété par -1 ;
- champ aux nœuds `<champ>` : (n_nœuds, n_composantes), ou une ligne par nœud du
  profil (`<champ>#nodes` : indices des nœuds) pour un champ restreint à des mailles ;
- champ par élément aux nœuds (ELNO) `<champ>@<niv>` : une ligne par (maille, nœud
  local) dans l'ordre des mailles de `<champ>@<niv>#cells` (numéros de maille du
  niveau `niv`) ; l'ordre des nœuds d'une maille est celui de `conn_<niv>`.

Les numéros de nœud et de maille sont des indices MED à partir de 0 (le nœud `N<k>`
de Code_Aster est l'indice `k - 1`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import MEDLoader
import numpy as np

_LEVELS = (0, -1, -2)


def _fields(path: str) -> tuple[object, object]:
    return MEDLoader.MEDFileFields.New(path), MEDLoader.MEDFileMesh.New(path)


def inventory(path: str) -> dict[str, object]:
    fields, mesh = _fields(path)
    out = []
    for name in fields.getFieldsNames():
        multi = fields.getFieldWithName(name)
        first = multi[0]
        out.append(
            {
                "name": name,
                "components": list(multi.getInfo()),
                "supports": [int(t) for t in first.getTypesOfFieldAvailable()],
                "iterations": [list(map(int, it)) for it in multi.getIterations()],
            }
        )
    return {
        "mesh": mesh.getName(),
        "n_nodes": int(mesh.getCoords().getNumberOfTuples()),
        "levels": [int(lv) for lv in mesh.getNonEmptyLevels()],
        "fields": out,
    }


def _connectivity(mesh: object, level: int) -> np.ndarray:
    umesh = mesh.getMeshAtLevel(level)
    rows = [list(umesh.getNodeIdsOfCell(c)) for c in range(umesh.getNumberOfCells())]
    width = max(len(r) for r in rows)
    out = np.full((len(rows), width), -1, dtype=np.int64)
    for i, row in enumerate(rows):
        out[i, : len(row)] = row
    return out


def extract(path: str, names: list[str], npz_path: str) -> dict[str, object]:
    fields, mesh = _fields(path)
    arrays: dict[str, np.ndarray] = {"coords": mesh.getCoords().toNumPyArray()}
    meta: dict[str, object] = {"mesh": mesh.getName(), "fields": {}}
    for level in mesh.getNonEmptyLevels():
        if int(level) in _LEVELS:
            arrays[f"conn_{int(level)}"] = _connectivity(mesh, int(level))
    groups: dict[str, object] = {"node": {}, "cell": {}}
    for lev in mesh.getNonEmptyLevelsExt():
        for name in mesh.getGroupsOnSpecifiedLev(lev):
            ids = [int(i) for i in mesh.getGroupArr(lev, name).getValues()]
            if lev == 1:
                groups["node"][name] = ids
            else:
                groups["cell"].setdefault(str(lev), {})[name] = ids
    meta["groups"] = groups
    for name in names:
        multi = fields.getFieldWithName(name)
        first = multi[0]
        info = {"components": list(multi.getInfo()), "arrays": []}
        supports = [int(t) for t in first.getTypesOfFieldAvailable()]
        if MEDLoader.ON_NODES in supports:
            values, nodes = first.getFieldWithProfile(MEDLoader.ON_NODES, 0, mesh)
            arrays[name] = values.toNumPyArray()
            if nodes is not None:  # champ restreint à un profil de nœuds
                arrays[f"{name}#nodes"] = nodes.toNumPyArray().astype(np.int64)
            info["arrays"].append(name)
        if MEDLoader.ON_GAUSS_NE in supports:
            for level in _LEVELS[:2]:
                try:
                    values, cells = first.getFieldWithProfile(
                        MEDLoader.ON_GAUSS_NE, level, mesh
                    )
                except MEDLoader.InterpKernelException:
                    continue
                key = f"{name}@{level}"
                arrays[key] = values.toNumPyArray()
                ids = cells.toNumPyArray() if cells is not None else np.arange(0)
                arrays[f"{key}#cells"] = ids.astype(np.int64)
                info["arrays"].append(key)
        meta["fields"][name] = info
    np.savez_compressed(npz_path, **arrays)
    meta["npz"] = npz_path
    return meta


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        sys.stderr.write(__doc__ or "")
        return 2
    path, sortie, mode = argv[1], argv[2], argv[3]
    if mode == "inventory":
        result = inventory(path)
    elif mode == "extract":
        result = extract(path, argv[4:], sortie[: -len(".json")] + ".npz")
    else:
        sys.stderr.write(f"mode inconnu : {mode}\n")
        return 2
    with Path(sortie).open("w", encoding="utf-8") as handle:
        json.dump(result, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
