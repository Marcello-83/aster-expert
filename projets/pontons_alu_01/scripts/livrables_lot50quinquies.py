"""Lot 50 quinquies : dépôt de `charges.med` et du script Salomé-Méca de PONTONS-ALU-01
sur le partage, après la sous-étape générique `charges` :

    .venv/bin/aster-expert projet pontons_alu_01 livrables --sous-etape charges
    PYTHONPATH=projets .venv/bin/python \
        projets/pontons_alu_01/scripts/livrables_lot50quinquies.py [--depot <répertoire>]

Le MED déposé est celui de Code_Aster, octet pour octet (empreinte comparée à
`resultats/livrables/med/charges.med`) ; le script déposé ne diffère de celui qui a
rendu les images que par la ligne `FICHIER_MED`.
"""

import argparse
import sys
from pathlib import Path

from aster_expert.livrables.chaine import deliverables_dir
from aster_expert.livrables.charges_salome import (
    MED_NAME,
    deposit,
    run_in_salome,
    sha256_of,
)
from aster_expert.projet.context import load_project

ROOT = Path(__file__).resolve().parents[3]
DEPOT = Path("/media/sf_partage/echanges/lot50quinquies/pontons_alu_01")
VERSION = "Salomé-Méca V2024.1.0, ParaView 5.11"
MENU = "menu Tools > Python Shell (2e menu Tools, celui de ParaView), bouton Run Script"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--depot", type=Path, default=DEPOT)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    root = deliverables_dir(ctx)
    original = root / "med" / MED_NAME
    names = deposit(ctx, args.depot, menu=MENU, version=VERSION)
    if sha256_of(args.depot / MED_NAME) != sha256_of(original):
        print("ÉCART : le MED déposé n'est pas celui de Code_Aster")
        return 1
    # Les deux essais sont refaits sur le script réellement déposé.
    script = args.depot / "charges_salome.py"
    work = root / "charges_salome" / "essai_depot"
    direct = run_in_salome(ctx, script, work / "direct")
    execd = run_in_salome(ctx, script, work / "exec", mode="exec")
    print(f"{len(names)} fichiers déposés dans {args.depot}")
    print(f"script déposé : {len(direct)} images (pvbatch), {len(execd)} par exec()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
