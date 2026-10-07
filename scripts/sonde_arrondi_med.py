"""Lot 48 bis, fait 6.1 : arrondir les coordonnées d'un MED réduit-il sa taille ?

Exécuté dans l'image Code_Aster (`medcoupling`) : lit un MED, en écrit une copie dont
les coordonnées sont arrondies à `decimales` décimales (par défaut 3, grille de 1 mm),
et écrit un JSON : tailles des deux fichiers, nombre de nœuds et de mailles, nombre de
coordonnées modifiées, plus grand déplacement.

    python3 sonde_arrondi_med.py <in.med> <out.med> <sonde.json> [decimales]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import MEDLoader


def main() -> None:
    source, target, report = sys.argv[1:4]
    decimals = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    name = MEDLoader.GetMeshNames(source)[0]
    mfm = MEDLoader.MEDFileMesh.New(source, name)
    coords = mfm.getCoords()
    before = coords.getValues()
    after = [round(v, decimals) for v in before]
    coords.setValues(after, coords.getNumberOfTuples(), coords.getNumberOfComponents())
    mfm.write(target, 2)
    cells = sum(
        mfm.getMeshAtLevel(level).getNumberOfCells()
        for level in mfm.getNonEmptyLevels()
    )
    summary = {
        "taille_origine": Path(source).stat().st_size,
        "taille_arrondi": Path(target).stat().st_size,
        "noeuds": coords.getNumberOfTuples(),
        "mailles": cells,
        "coordonnees_modifiees": sum(
            a != b for a, b in zip(before, after, strict=True)
        ),
        "deplacement_max": max(abs(a - b) for a, b in zip(before, after, strict=True)),
    }
    Path(report).write_text(json.dumps(summary, indent=2), encoding="utf-8")


main()
