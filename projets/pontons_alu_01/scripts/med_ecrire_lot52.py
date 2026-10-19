"""Lot 52, run by the Python of the Code_Aster image (medcoupling): write structure.med,
charges.med and resultats.med of one variant, then read them again.

    python3 med_ecrire_lot52.py resultats.med charges.med spec.json spec.npz sortie/

As med_ecrire_lot51quater.py, plus, in resultats.med, a second mesh (spec
« maillage_elno ») where each SEG2 of the bars has its own two nodes: on it, the
displacements (DEPL of the original node) and the forces (EFGE_ELNO of the element end)
of each combination are two fields ON_NODES of the same support, so that MEDReader can
warp by DEPL and colour by a force component (defect of lot 51 quater).

Templates: the unit fields that Code_Aster wrote (CAS_<cas>__DEPL, CAS_<cas>__EFGE_ELNO of
resultats.med, FN_<cas> of charges.med). A new field is a deep copy of a template whose
values are replaced by the array of spec.npz (same layout: nodes, or the ends of the
SEG2 cells of the EFGE_ELNO profile); nothing is interpolated. The mesh is renamed and
the groups of spec.json are added. sortie/relecture.json: what each written file holds
when read again (nodes, cells per level, groups, fields) and the largest gap between
each field read again and its array of spec.npz. Written in MED 3.3, the version
of the files Code_Aster writes (the MEDReader of Salomé-Méca 2024.1 refuses MED 4.2).
"""

import json
import sys
from pathlib import Path
from typing import Any

import medcoupling as mc  # type: ignore[import-not-found]
import numpy as np


def template(path: Path, name: str) -> Any:
    ts = mc.MEDFileFieldMultiTS(str(path), name, False)
    it = ts.getIterations()[0]
    return mc.MEDFileField1TS(str(path), name, it[0], it[1])


def filled(tpl: Any, name: str, mesh_name: str, values: Any) -> Any:
    f = tpl.deepCopy()
    under = f.getUndergroundDataArray()
    arr = under.toNumPyArray()
    if arr.shape != values.shape:
        raise SystemExit(f"{name} : forme {values.shape} au lieu de {arr.shape}")
    arr[...] = values
    f.setName(name)
    f.setMeshName(mesh_name)
    f.setTime(0, 0, 0.0)
    return f


def with_components(f: Any, components: list[str]) -> Any:
    arr = f.getUndergroundDataArray()
    for i, c in enumerate(components):
        arr.setInfoOnComponent(i, c)
    return f


def summary(path: Path, spec_arrays: dict[str, Any]) -> dict[str, Any]:
    mm = mc.MEDFileMesh.New(str(path))
    out: dict[str, Any] = {
        "version_med": mc.MEDFileVersionOfFileStr(str(path)),
        "maillage": mm.getName(),
        "noeuds": mm.getNumberOfNodes(),
        "niveaux": {str(lv): mm.getSizeAtLevel(lv) for lv in mm.getNonEmptyLevels()},
        "groupes": len(mm.getGroupsNames()),
        "champs": [],
        "ecart_relecture_max": 0.0,
    }
    for name in mc.GetAllFieldNames(str(path)):
        out["champs"].append(name)
        if name in spec_arrays:
            f = template(path, name)
            got = f.getUndergroundDataArray().toNumPyArray()
            gap = float(np.max(np.abs(got - spec_arrays[name])))
            out["ecart_relecture_max"] = max(out["ecart_relecture_max"], gap)
    return out


def elno_mesh(spec: dict[str, Any], data: Any) -> tuple[Any, Any]:
    """The mesh with one pair of nodes per SEG2 of the bars, and its groups."""
    coords = np.ascontiguousarray(data["elno_coords"], dtype=np.float64)
    conn = data["elno_conn"]
    m = mc.MEDCouplingUMesh(spec["maillage_elno"], 1)
    arr = mc.DataArrayDouble(coords.ravel().tolist(), len(coords), 3)
    arr.setInfoOnComponents(["X", "Y", "Z"])
    m.setCoords(arr)
    m.allocateCells(len(conn))
    for a, b in conn:
        m.insertNextCell(mc.NORM_SEG2, [int(a), int(b)])
    m.finishInsertingCells()
    mm = mc.MEDFileUMesh()
    mm.setName(spec["maillage_elno"])
    mm.setMeshAtLevel(0, m)
    for name, ids in spec["groupes_elno"].items():
        g = mc.DataArrayInt([int(i) for i in ids])
        g.setName(name)
        mm.addGroup(0, g)
    return mm, m


def nodal(name: str, mesh: Any, values: Any, components: list[str]) -> Any:
    f = mc.MEDCouplingFieldDouble(mc.ON_NODES, mc.ONE_TIME)
    f.setName(name)
    f.setMesh(mesh)
    v = np.ascontiguousarray(values, dtype=np.float64)
    arr = mc.DataArrayDouble(v.ravel().tolist(), v.shape[0], v.shape[1])
    arr.setInfoOnComponents(components)
    f.setArray(arr)
    f.setTime(0.0, 0, 0)
    f.checkConsistencyLight()
    ff = mc.MEDFileField1TS()
    ff.setFieldNoProfileSBT(f)
    return ff


def main() -> None:
    resu, charges, spec_json, spec_npz = (Path(a) for a in sys.argv[1:5])
    out = Path(sys.argv[5])
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_json.read_text(encoding="utf-8"))
    data = np.load(spec_npz)
    old, new = spec["maillage_source"], spec["maillage"]

    mm = mc.MEDFileMesh.New(str(resu))
    mm.setName(new)
    for name, grp in spec["groupes_ajoutes"].items():
        ids = mc.DataArrayInt(grp["ids"])
        ids.setName(name)
        if grp["level"] == 1:
            mm.addNodeGroup(ids)
        else:
            mm.addGroup(grp["level"], ids)
    mm.write33(str(out / "structure.med"), 2)

    written: dict[str, Any] = {}
    # charges.med : champs unitaires du MED de Code_Aster (maillage renommé) + événements.
    path = out / "charges.med"
    mm.write33(str(path), 2)
    for name in mc.GetAllFieldNames(str(charges)):
        f = template(charges, name)
        f.setMeshName(new)
        f.write33(str(path), 0)
    tpl = template(charges, spec["gabarit_forces"])
    for k, name in enumerate(spec["evenements"]):
        values = data["evenements"][k]
        filled(tpl, name, new, values).write33(str(path), 0)
        written[name] = values

    # resultats.med : combinaisons (DEPL, EFGE_ELNO) et enveloppes ELU.
    path = out / "resultats.med"
    mm.write33(str(path), 2)
    tpl_u = template(resu, spec["gabarit_depl"])
    tpl_e = template(resu, spec["gabarit_efge"])
    for k, name in enumerate(spec["combinaisons"]):
        u = data["comb_depl"][k]
        e = data["comb_efge"][k]
        filled(tpl_u, f"{name}__DEPL", new, u).write33(str(path), 0)
        filled(tpl_e, f"{name}__EFGE_ELNO", new, e).write33(str(path), 0)
        written[f"{name}__DEPL"] = u
        written[f"{name}__EFGE_ELNO"] = e
    env = data["enveloppe"]
    f = filled(tpl_e, spec["enveloppe"], new, env)
    with_components(f, spec["composantes_enveloppe"]).write33(str(path), 0)
    written[spec["enveloppe"]] = env
    # Support commun : maillage ELNO (deux nœuds propres par SEG2 des barres).
    emm, emesh = elno_mesh(spec, data)
    emm.write33(str(path), 0)
    for k, name in enumerate(spec["combinaisons"]):
        u = data["elno_depl"][k]
        e = data["elno_efge"][k]
        nodal(f"E_{name}__DEPL", emesh, u, spec["composantes_depl"]).write33(
            str(path), 0
        )
        nodal(f"E_{name}__EFGE", emesh, e, spec["composantes_efge"]).write33(
            str(path), 0
        )
        written[f"E_{name}__DEPL"] = u
        written[f"E_{name}__EFGE"] = e
    nodal(
        "E_" + spec["enveloppe"],
        emesh,
        data["elno_enveloppe"],
        spec["composantes_enveloppe"],
    ).write33(str(path), 0)
    written["E_" + spec["enveloppe"]] = data["elno_enveloppe"]

    report: dict[str, Any] = {}
    for name in ("structure.med", "charges.med", "resultats.med"):
        report[name] = summary(out / name, written)
    report["maillage_source"] = old
    report["maillages_resultats"] = list(mc.GetMeshNames(str(out / "resultats.med")))
    emm2 = mc.MEDFileMesh.New(str(out / "resultats.med"), spec["maillage_elno"])
    report["maillage_elno"] = {
        "noeuds": emm2.getNumberOfNodes(),
        "mailles": emm2.getSizeAtLevel(0),
        "groupes": len(emm2.getGroupsNames()),
    }
    (out / "relecture.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


main()
