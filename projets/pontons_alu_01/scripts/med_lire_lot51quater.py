"""Lot 51 quater, run by the Python of the Code_Aster image (medcoupling): read the MED
files that Code_Aster wrote for one variant (unit results and loads of the post-processing
run of the project chain) and dump what the project's Python needs.

    python3 med_lire_lot51quater.py resultats.med charges.med sortie.npz sortie.json

sortie.npz: DEPL (case, node, 6), EFGE_ELNO (case, end, 6) in the order of the MED
array, FN (case, node, 6) for the cases with a nodal force field; sortie.json: mesh name,
counts, groups, the cases, and for each end of the EFGE_ELNO layout the cell (level -1,
from 1) and the node (from 1).
"""

import json
import sys
from pathlib import Path
from typing import Any

import medcoupling as mc  # type: ignore[import-not-found]
import numpy as np


def main() -> None:
    resu, charges, out_npz, out_json = sys.argv[1:5]
    mm = mc.MEDFileMesh.New(resu)
    mesh_name = mm.getName()
    levels = {str(lv): mm.getSizeAtLevel(lv) for lv in mm.getNonEmptyLevels()}
    groups: dict[str, Any] = {}
    for name in mm.getGroupsNames():
        lvs = list(mm.getGrpNonEmptyLevelsExt(name))
        lv = lvs[0]
        if lv == 1:
            ids = mm.getNodeGroupArr(name).toNumPyArray().tolist()
        else:
            ids = mm.getGroupArr(lv, name).toNumPyArray().tolist()
        groups[name] = {"level": int(lv), "ids": [int(i) for i in ids]}
    fields = mc.GetAllFieldNames(resu)
    cases = sorted({f.split("__")[0][4:] for f in fields if f.startswith("CAS_")})
    seg = mm.getMeshAtLevel(-1)
    conn = seg.getNodalConnectivity().toNumPyArray()
    index = seg.getNodalConnectivityIndex().toNumPyArray()
    depl: list[Any] = []
    efge: list[Any] = []
    layout: list[tuple[int, int]] | None = None
    for case in cases:
        name = f"CAS_{case}__DEPL"
        it = mc.MEDFileFieldMultiTS(resu, name, False).getIterations()[0]
        f = mc.MEDFileField1TS(resu, name, it[0], it[1])
        arr = f.getFieldOnMeshAtLevel(mc.ON_NODES, 0, mm).getArray().toNumPyArray()
        depl.append(arr.copy())
        name = f"CAS_{case}__EFGE_ELNO"
        f = mc.MEDFileField1TS(resu, name, it[0], it[1])
        values, pfl = f.getFieldWithProfile(mc.ON_GAUSS_NE, -1, mm)
        under = f.getUndergroundDataArray().toNumPyArray()
        v = values.toNumPyArray().copy()
        if v.shape != under.shape or not np.array_equal(v, under):
            raise SystemExit(f"{name} : tableau sous-jacent différent du champ")
        efge.append(v)
        cells = pfl.toNumPyArray().tolist()
        current = []
        for c in cells:
            nodes = conn[index[c] + 1 : index[c + 1]].tolist()
            current += [(int(c) + 1, int(n) + 1) for n in nodes]
        if layout is None:
            layout = current
        elif layout != current:
            raise SystemExit(f"{name} : disposition des extrémités différente")
    fn_cases: list[str] = []
    fn: list[Any] = []
    for name in mc.GetAllFieldNames(charges):
        if not name.startswith("FN_"):
            continue
        ts = mc.MEDFileFieldMultiTS(charges, name, False)
        it = ts.getIterations()[0]
        f = mc.MEDFileField1TS(charges, name, it[0], it[1])
        cm = mc.MEDFileMesh.New(charges)
        arr = f.getFieldOnMeshAtLevel(mc.ON_NODES, 0, cm).getArray().toNumPyArray()
        fn.append(arr.copy())
        fn_cases.append(name[3:])
    np.savez(
        out_npz,
        depl=np.array(depl),
        efge=np.array(efge),
        fn=np.array(fn),
    )
    with Path(out_json).open("w", encoding="utf-8") as stream:
        json.dump(
            {
                "maillage": mesh_name,
                "noeuds": mm.getNumberOfNodes(),
                "niveaux": levels,
                "groupes": groups,
                "cas": cases,
                "cas_charges": fn_cases,
                "champs_resultats": len(fields),
                "champs_charges": len(mc.GetAllFieldNames(charges)),
                "extremites": layout,
            },
            stream,
        )


main()
