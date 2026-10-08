"""Combinations and envelopes of the deliverables, written into the MED (lot 49).

Standalone: runs with `medcoupling` and numpy inside the Code_Aster image
(`aster_expert.livrables.conteneur`), next to a copy of `calcul.py`
(`aster_expert.livrables.calcul`, plain numpy). Usage:

    python3 livrables_med.py <spec.json> <out.json>

The spec names three MED files written by Code_Aster in the post-processing run:

- `cases_med`: the elementary cases, one field per case and per declared field,
  named `CAS_<case>__<key>` (`IMPR_RESU/NOM_CHAM_MED`);
- `work_med`: every case of every solve (`NOM_RESU_MED` = token of the solve), the
  positions of the moving loads included;
- `loads_med`: the nodal forces of each elementary case (`FN_<case>`), and for a
  thermal case its `FORC_VARC` forces and temperature fields.

It writes, in the working directory:

- `resultats.med`: a copy of `cases_med` completed by the combinations
  (`COMB_<name>__<key>`, or `__MAX` and `__MIN` when the combination envelopes a moving
  load) and the envelopes (`ENV__<key>__MAX`, `__MIN`, with `__MAX_COMB`, `__MIN_COMB`,
  `__MAX_POS`, `__MIN_POS`: index of the governing combination and of its position,
  −1 when it has none). A new field is a deep copy of the case field written by
  Code_Aster (same supports, profiles and order of values) whose values are replaced:
  nothing is re-meshed or re-numbered;
- `donnees/<key>.npz`: the same arrays, the positions of the moving loads (`pos/`,
  for the queries only), with the row mapping (`row_kind`: 0 node, 1
  element-node, 2 Gauss point; `row_entity`: node or cell index in its level, from 0;
  `row_local`: node of the cell; `row_level`);
- `donnees/charges.npz`, `donnees/maillage.npz` (coordinates, connectivities by level,
  cell types, groups);
- `<out.json>`: what was written (field names, components, sizes).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import MEDLoader as ml  # noqa: N813
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calcul import combine, envelope, with_moving  # noqa: E402

_KIND = {ml.ON_NODES: 0, ml.ON_GAUSS_NE: 1, ml.ON_GAUSS_PT: 2, ml.ON_CELLS: 2}
"""Row kinds: 0 node, 1 element-node, 2 one value per element (a Gauss point or a
cell: the forces of a POI1 discrete element are written ON_CELLS)."""
_LEVELS = (0, -1, -2, -3)


def _raw(field: object) -> np.ndarray:
    """The raw array, always (rows, components): one component comes out 1-D."""
    array = field.getUndergroundDataArray()
    values = array.toNumPyArray().copy()
    return values.reshape(array.getNumberOfTuples(), array.getNumberOfComponents())


def _one(path: str, name: str, iteration: tuple[int, int] | None = None) -> object:
    if iteration is None:
        return ml.MEDFileField1TS.New(path, name)
    return ml.MEDFileField1TS.New(path, name, iteration[0], iteration[1])


def _mapping(one: object, mesh: object) -> dict[str, np.ndarray]:
    """Row of the raw array -> (kind, entity, local node, level)."""
    kinds, entities, locals_, levels = [], [], [], []
    supports = [int(t) for t in one.getTypesOfFieldAvailable()]
    raw_len = one.getUndergroundDataArray().getNumberOfTuples()
    for tof in supports:
        kind = _KIND.get(tof)
        if kind is None:
            message = f"support de champ non pris en charge : {tof}"
            raise ValueError(message)
        found = False
        for level in _LEVELS if kind else (0,):
            try:
                _values, ids = one.getFieldWithProfile(tof, level, mesh)
            except ml.InterpKernelException:
                continue
            found = True
            if kind == 0:
                n = _values.getNumberOfTuples()
                ent = (
                    np.arange(n, dtype=np.int64)
                    if ids is None
                    else ids.toNumPyArray().astype(np.int64)
                )
                kinds.append(np.zeros(n, dtype=np.int64))
                entities.append(ent)
                locals_.append(np.zeros(n, dtype=np.int64))
                levels.append(np.full(n, 1, dtype=np.int64))
                break
            umesh = mesh.getMeshAtLevel(level)
            cells = (
                np.arange(umesh.getNumberOfCells(), dtype=np.int64)
                if ids is None
                else ids.toNumPyArray().astype(np.int64)
            )
            for cell in cells:
                count = len(umesh.getNodeIdsOfCell(int(cell))) if kind == 1 else 1
                kinds.append(np.full(count, kind, dtype=np.int64))
                entities.append(np.full(count, cell, dtype=np.int64))
                locals_.append(np.arange(count, dtype=np.int64))
                levels.append(np.full(count, level, dtype=np.int64))
        if not found:
            message = f"support {tof} introuvable sur les niveaux du maillage"
            raise ValueError(message)
    out = {
        "row_kind": np.concatenate(kinds),
        "row_entity": np.concatenate(entities),
        "row_local": np.concatenate(locals_),
        "row_level": np.concatenate(levels),
    }
    if out["row_kind"].size != raw_len:
        message = (
            f"correspondance des lignes : {out['row_kind'].size} lignes pour un "
            f"tableau brut de {raw_len}"
        )
        raise ValueError(message)
    return out


def _write_like(template: object, name: str, values: np.ndarray, path: str) -> None:
    copy = template.deepCopy()
    copy.setName(name)
    array = copy.getUndergroundDataArray()
    if array.getNumberOfTuples() != values.shape[0]:
        message = f"{name} : {values.shape[0]} lignes pour {array.getNumberOfTuples()}"
        raise ValueError(message)
    flat = np.ascontiguousarray(values, dtype=np.float64)
    for column in range(flat.shape[1]):
        array[:, column] = ml.DataArrayDouble(flat[:, column].copy())
    copy.write(path, 0)


def _mesh_arrays(path: str) -> dict[str, np.ndarray]:
    mesh = ml.MEDFileMesh.New(path)
    out: dict[str, np.ndarray] = {"coords": mesh.getCoords().toNumPyArray().copy()}
    for level in mesh.getNonEmptyLevels():
        umesh = mesh.getMeshAtLevel(int(level))
        rows = [
            list(umesh.getNodeIdsOfCell(c)) for c in range(umesh.getNumberOfCells())
        ]
        width = max(len(r) for r in rows)
        conn = np.full((len(rows), width), -1, dtype=np.int64)
        for i, row in enumerate(rows):
            conn[i, : len(row)] = row
        out[f"conn_{int(level)}"] = conn
        out[f"type_{int(level)}"] = np.array(
            [int(umesh.getTypeOfCell(c)) for c in range(umesh.getNumberOfCells())],
            dtype=np.int64,
        )
    for lev in mesh.getNonEmptyLevelsExt():
        for name in mesh.getGroupsOnSpecifiedLev(lev):
            ids = mesh.getGroupArr(lev, name).toNumPyArray().astype(np.int64)
            key = f"gno_{name}" if lev == 1 else f"gma_{int(lev)}_{name}"
            out[key] = ids
    return out


def main(argv: list[str]) -> int:
    spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    out_json = Path(argv[2])
    work = Path(argv[1]).resolve().parent
    cases_med = str(work / spec["cases_med"])
    work_med = str(work / spec["work_med"])
    result_med = str(work / "resultats.med")
    shutil.copyfile(cases_med, result_med)
    data = work / "donnees"
    data.mkdir(exist_ok=True)
    report: dict[str, object] = {"champs": {}, "ecrits": []}
    mesh = ml.MEDFileMesh.New(cases_med)
    elementary = [c for c, info in spec["cases"].items() if info["elementary"]]
    combos = spec["combinations"]
    for fdef in spec["fields"]:
        key = fdef["key"]
        template = _one(cases_med, f"CAS_{elementary[0]}__{key}")
        components = list(template.getInfo())
        arrays: dict[str, np.ndarray] = {}
        needed = set(elementary)
        for comb in combos:
            needed |= set(comb["fixed"]) | set(comb.get("mobile_cases", ()))
        for case in sorted(needed):
            info = spec["cases"][case]
            if info["elementary"]:
                one = _one(cases_med, f"CAS_{case}__{key}")
            else:
                order = info["order"]
                one = _one(work_med, fdef["work"][info["token"]], (order, order))
            values = _raw(one)
            if values.shape != _raw(template).shape:
                message = f"{key} : disposition différente pour le cas {case}"
                raise ValueError(message)
            arrays[case] = values
        npz: dict[str, np.ndarray] = dict(_mapping(template, mesh))
        for case in elementary:
            npz[f"cas/{case}"] = arrays[case]
        # Positions of the moving loads: never written in the MED of results (lot 49,
        # consigne), kept here for `aster-expert resultats lire`.
        for case in sorted(set(arrays) - set(elementary)):
            npz[f"pos/{case}"] = arrays[case]
        items = []
        for index, comb in enumerate(combos):
            base = combine(arrays, comb["fixed"])
            enveloped = with_moving(
                base,
                arrays,
                float(comb.get("mobile_coefficient", 0.0)),
                comb.get("mobile_cases", ()),
            )
            items.append(enveloped)
            label = comb["name"].replace(" ", "_")
            if comb.get("mobile_cases"):
                names = [
                    (f"COMB_{label}__{key}__MAX", enveloped.maximum),
                    (f"COMB_{label}__{key}__MIN", enveloped.minimum),
                ]
                npz[f"comb/{index}/max"] = enveloped.maximum
                npz[f"comb/{index}/min"] = enveloped.minimum
                npz[f"comb/{index}/max_pos"] = enveloped.arg_max
                npz[f"comb/{index}/min_pos"] = enveloped.arg_min
            else:
                names = [(f"COMB_{label}__{key}", enveloped.maximum)]
                npz[f"comb/{index}/max"] = enveloped.maximum
                npz[f"comb/{index}/min"] = enveloped.minimum
            for name, values in names:
                _write_like(template, name, values, result_med)
                report["ecrits"].append(name)
        if spec.get("envelopes") and items:
            env = envelope(items)
            for suffix, values in (
                ("MAX", env.maximum),
                ("MIN", env.minimum),
                ("MAX_COMB", env.max_combination.astype(np.float64)),
                ("MIN_COMB", env.min_combination.astype(np.float64)),
                ("MAX_POS", env.max_position.astype(np.float64)),
                ("MIN_POS", env.min_position.astype(np.float64)),
            ):
                name = f"ENV__{key}__{suffix}"
                _write_like(template, name, values, result_med)
                report["ecrits"].append(name)
            npz["env/max"] = env.maximum
            npz["env/min"] = env.minimum
            npz["env/max_comb"] = env.max_combination
            npz["env/min_comb"] = env.min_combination
            npz["env/max_pos"] = env.max_position
            npz["env/min_pos"] = env.min_position
        np.savez(data / f"{key}.npz", **npz)
        report["champs"][key] = {
            "composantes": components,
            "lignes": int(npz["row_kind"].size),
            "supports": sorted({int(k) for k in npz["row_kind"]}),
        }
    loads: dict[str, np.ndarray] = {}
    load_info: dict[str, object] = {}
    loads_med = str(work / spec["loads_med"])
    if Path(loads_med).is_file():
        lmesh = ml.MEDFileMesh.New(loads_med)
        fields = ml.MEDFileFields.New(loads_med)
        for name in fields.getFieldsNames():
            one = fields.getFieldWithName(name)[0]
            loads[f"val/{name}"] = _raw(one)
            for k, v in _mapping(one, lmesh).items():
                loads[f"{k}/{name}"] = v
            load_info[name] = {
                "composantes": list(fields.getFieldWithName(name).getInfo())
            }
    np.savez(data / "charges.npz", **loads)
    report["charges"] = load_info
    np.savez(data / "maillage.npz", **_mesh_arrays(cases_med))
    out_json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
