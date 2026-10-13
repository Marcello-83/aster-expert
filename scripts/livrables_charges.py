"""MED de vérification des cas de charge, écrit dans le conteneur (lot 50 quater).

Lancé par `aster_expert.livrables.charges_verif` avec `medcoupling` (le Python du projet
n'a aucun module MED, ADR-002). Entrées, dans le répertoire du script :

- `source.med` : le MED de charges du post-traitement (maillage et groupes) ;
- `entree.npz` : `ordre` (noms des cas), `cellules` (numéros des mailles linéiques dans
  leur niveau), `nodal/<cas>` (nœuds × 6), `repartie/<cas>` (mailles × 6) et
  `temperature/<cas>` (mailles) ; seuls les cas qui ont ce champ le portent ;
- `spec.json` : niveau des mailles linéiques et noms des composantes.

Sortie : `charges.med` (le maillage de `source.med` et trois champs à un pas par cas,
numéro d'ordre = rang du cas dans `ordre`, à partir de 1) et `sortie.json`. Le fichier
écrit est relu et comparé à l'entrée, valeur pour valeur : un écart arrête le script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import MEDLoader as ml  # noqa: N813
import numpy as np


def _champ(umesh, support, name, components, values, rank):  # noqa: ANN001, ANN202
    array = ml.DataArrayDouble(np.ascontiguousarray(values, dtype=np.float64))
    array.setInfoOnComponents(list(components))
    field = ml.MEDCouplingFieldDouble(support)
    field.setMesh(umesh)
    field.setName(name)
    field.setArray(array)
    field.setTime(float(rank), rank, rank)
    one = ml.MEDFileField1TS()
    one.setFieldNoProfileSBT(field)
    return one


def _ecrire(path, mesh, level, name, support, components, steps):  # noqa: ANN001, ANN202
    umesh = mesh.getMeshAtLevel(0 if support == ml.ON_NODES else level)
    multi = ml.MEDFileFieldMultiTS()
    for rank, values in steps:
        multi.pushBackTimeStep(_champ(umesh, support, name, components, values, rank))
    fields = ml.MEDFileFields()
    fields.pushField(multi)
    fields.write(path, 0)


def main(argv: list[str]) -> int:
    work = Path(argv[1]).resolve().parent
    spec = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    entree = np.load(work / "entree.npz")
    ordre = [str(n) for n in entree["ordre"]]
    rang = {nom: i for i, nom in enumerate(ordre, 1)}
    cellules = entree["cellules"].astype(np.int64)
    level = int(spec["niveau_mailles_lineiques"])
    out = str(work / "charges.med")
    mesh = ml.MEDFileMesh.New(str(work / "source.med"))
    mesh.write(out, 2)
    nombre_mailles = mesh.getMeshAtLevel(level).getNumberOfCells()
    champs = {
        "CHARGE_NODALE": ("nodal", ml.ON_NODES, spec["composantes_nodales"]),
        "CHARGE_REPARTIE": ("repartie", ml.ON_CELLS, spec["composantes_reparties"]),
        "ECART_TEMPERATURE": ("temperature", ml.ON_CELLS, ["DT"]),
    }
    rapport: dict[str, object] = {"champs": {}}
    for nom_champ, (cle, support, composantes) in champs.items():
        pas = []
        for nom in ordre:
            if f"{cle}/{nom}" not in entree.files:
                continue
            valeurs = entree[f"{cle}/{nom}"]
            if support == ml.ON_CELLS:
                # Une valeur par maille linéique du niveau, dans l'ordre du niveau.
                complet = np.zeros((nombre_mailles, len(composantes)), dtype=np.float64)
                complet[cellules] = valeurs.reshape(len(cellules), len(composantes))
                valeurs = complet
            pas.append((rang[nom], valeurs))
        if not pas:
            continue
        _ecrire(out, mesh, level, nom_champ, support, composantes, pas)
        rapport["champs"][nom_champ] = {
            "support": "noeuds" if support == ml.ON_NODES else "mailles",
            "composantes": list(composantes),
            "pas": {nom: rang[nom] for nom in ordre if f"{cle}/{nom}" in entree.files},
        }
    # Relecture : chaque pas du fichier écrit égale l'entrée.
    ecarts = 0
    comparees = 0
    for nom_champ, (cle, support, composantes) in champs.items():
        for nom in rapport["champs"].get(nom_champ, {}).get("pas", {}):
            one = ml.MEDFileField1TS.New(out, nom_champ, rang[nom], rang[nom])
            lu = (
                one.getUndergroundDataArray()
                .toNumPyArray()
                .reshape(-1, len(composantes))
            )
            attendu = entree[f"{cle}/{nom}"].reshape(-1, len(composantes))
            if support == ml.ON_CELLS:
                lu = lu[cellules]
            comparees += lu.size
            if not np.array_equal(lu, attendu):
                ecarts += 1
    rapport["relecture"] = {"valeurs_comparees": int(comparees), "pas_en_ecart": ecarts}
    Path(argv[2]).write_text(json.dumps(rapport, indent=1), encoding="utf-8")
    if ecarts:
        message = f"relecture du MED : {ecarts} pas différents de l'entrée"
        raise SystemExit(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
