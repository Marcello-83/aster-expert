"""Dump a MED file to JSON with `medcoupling` (stand-alone: no Salome, no project).

Runs inside the Code_Aster Docker image (`aster-expert mesh check`), whose
Python has `medcoupling` and `MEDLoader`. Usage:

    python3 dump_med.py <file.med> <dump.json>

The dump is a plain description of the mesh (coordinates, connectivity per
level, groups as cell or node ids); every comparison with the invariants is done
outside, in the project, on this dump.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import medcoupling
import MEDLoader


def dump(path: str) -> dict[str, object]:
    names = MEDLoader.GetMeshNames(path)
    if len(names) != 1:
        message = f"expected exactly one mesh in {path}, found {list(names)}"
        raise SystemExit(message)
    mesh_name = names[0]
    mfm = MEDLoader.MEDFileMesh.New(path, mesh_name)
    coords = mfm.getCoords()
    ncomp = coords.getNumberOfComponents()
    flat = coords.getValues()
    points = [
        [*flat[i * ncomp : (i + 1) * ncomp], *([0.0] * (3 - ncomp))]
        for i in range(coords.getNumberOfTuples())
    ]
    levels: dict[str, object] = {}
    for level in mfm.getNonEmptyLevels():
        umesh = mfm.getMeshAtLevel(level)
        types = []
        connectivity = []
        for cell in range(umesh.getNumberOfCells()):
            types.append(
                medcoupling.MEDCouplingUMesh.GetReprOfGeometricType(
                    umesh.getTypeOfCell(cell)
                )
            )
            connectivity.append(list(umesh.getNodeIdsOfCell(cell)))
        levels[str(level)] = {"types": types, "connectivity": connectivity}
    groups = []
    for level in mfm.getNonEmptyLevelsExt():
        for name in mfm.getGroupsOnSpecifiedLev(level):
            groups.append(
                {
                    "name": name,
                    "level": level,
                    "ids": list(mfm.getGroupArr(level, name).getValues()),
                }
            )
    return {
        "mesh_name": mesh_name,
        "space_dimension": ncomp,
        "coords": points,
        "levels": levels,
        "groups": groups,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.stderr.write("usage: dump_med.py <file.med> <dump.json>\n")
        return 2
    with Path(argv[2]).open("w", encoding="utf-8") as handle:
        json.dump(dump(argv[1]), handle)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
