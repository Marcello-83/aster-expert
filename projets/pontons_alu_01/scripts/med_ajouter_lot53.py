"""Lot 53, run by the Python of the Code_Aster image (medcoupling): copy resultats.med of
lot 52 under a new name and add the displacement fields of lot 53, then read it again.

    python3 med_ajouter_lot53.py resultats.med spec.json spec.npz sortie.med relecture.json

For each key of spec « champs »: `<key>__DEPL` on the original mesh (deep copy of the
DEPL template « gabarit_depl » of lot 52, values replaced by the array of spec.npz, same
layout: every node) and `E_<key>__DEPL` ON_NODES on the common support « maillage_elno »
(two nodes per SEG2 of the bars, read from the file). The fields of lot 52 are kept
untouched. relecture.json: MED version, meshes, fields; the largest gap between each field
of lot 52 in the copy and in the source file, and between each new field read again and
its array. Written in MED 3.3 (version of the source file).
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import medcoupling as mc  # type: ignore[import-not-found]
import numpy as np


def template(path: Path, name: str) -> Any:
    ts = mc.MEDFileFieldMultiTS(str(path), name, False)
    it = ts.getIterations()[0]
    return mc.MEDFileField1TS(str(path), name, it[0], it[1])


def values(path: Path, name: str) -> Any:
    return template(path, name).getUndergroundDataArray().toNumPyArray()


def main() -> None:
    base, spec_json, spec_npz, out = (Path(a) for a in sys.argv[1:5])
    report_path = Path(sys.argv[5])
    spec = json.loads(spec_json.read_text(encoding="utf-8"))
    data = np.load(spec_npz)
    shutil.copyfile(base, out)
    mesh_name = spec["maillage"]
    tpl = template(base, spec["gabarit_depl"])
    written = {}
    for key in spec["champs"]:
        f = tpl.deepCopy()
        arr = f.getUndergroundDataArray().toNumPyArray()
        if arr.shape != data[key].shape:
            raise SystemExit(f"{key} : forme {data[key].shape} au lieu de {arr.shape}")
        arr[...] = data[key]
        f.setName(f"{key}__DEPL")
        f.setMeshName(mesh_name)
        f.setTime(0, 0, 0.0)
        f.write33(str(out), 0)
        written[f"{key}__DEPL"] = data[key]
    emm = mc.MEDFileMesh.New(str(out), spec["maillage_elno"])
    emesh = emm.getMeshAtLevel(0)
    for key in spec["champs"]:
        name = f"E_{key}__DEPL"
        field = mc.MEDCouplingFieldDouble(mc.ON_NODES, mc.ONE_TIME)
        field.setName(name)
        field.setMesh(emesh)
        v = np.ascontiguousarray(data[f"E_{key}"], dtype=np.float64)
        arr = mc.DataArrayDouble(v.ravel().tolist(), v.shape[0], v.shape[1])
        arr.setInfoOnComponents(spec["composantes_depl"])
        field.setArray(arr)
        field.setTime(0.0, 0, 0)
        field.checkConsistencyLight()
        ff = mc.MEDFileField1TS()
        ff.setFieldNoProfileSBT(field)
        ff.write33(str(out), 0)
        written[name] = v

    old = list(mc.GetAllFieldNames(str(base)))
    now = list(mc.GetAllFieldNames(str(out)))
    gap_old = 0.0
    for name in old:
        gap_old = max(
            gap_old, float(np.max(np.abs(values(out, name) - values(base, name))))
        )
    gap_new = 0.0
    for name, arr in written.items():
        gap_new = max(gap_new, float(np.max(np.abs(values(out, name) - arr))))
    report = {
        "version_med": mc.MEDFileVersionOfFileStr(str(out)),
        "maillages": list(mc.GetMeshNames(str(out))),
        "champs_source": len(old),
        "champs": now,
        "champs_conserves": all(n in now for n in old),
        "ecart_champs_source": gap_old,
        "ecart_champs_nouveaux": gap_new,
        "noeuds": mc.MEDFileMesh.New(str(out), mesh_name).getNumberOfNodes(),
        "noeuds_elno": emm.getNumberOfNodes(),
    }
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")


main()
