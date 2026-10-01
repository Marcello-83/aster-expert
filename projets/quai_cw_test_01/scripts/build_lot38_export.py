"""Lot 38, étapes 2 et 5 : combinaisons de D17 appliquées à la poutre de
couronnement, export tabulaire (CSV/Markdown) et contrôle manuel d'une combinaison.

Source des efforts élémentaires : le `.mess` (`fort.6`) de l'exécution du modèle
complet réutilisée au lot 38 (`data/processed/runs/20260925T125131-c67e28a1`, `.comm`
exécuté identique au `data/examples/lot37_efforts/complet.comm` versionné).

Lot 41 : le calcul est fait par le tronc commun (`aster_expert.combinaisons`, règles
de la déclaration `combinations` de `projet.yaml`, γ et ψ lus du fichier de données)
et la prose du rapport par l'extension du projet (`quai_cw_test_01.rapports`) ; ce
script n'en est plus que l'appel sur les entrées historiques du lot 38. Il redonne
octet pour octet `data/examples/lot38_combinaisons/` (critère du lot 41).

Usage : python projets/quai_cw_test_01/scripts/build_lot38_export.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.combinaisons.efforts import (  # noqa: E402
    combined_forces,
    write_combined_forces,
)
from aster_expert.projet.context import load_project  # noqa: E402

RUN = ROOT / "data" / "processed" / "runs" / "20260925T125131-c67e28a1"
MESS = RUN / "proc.0" / "fort.6"
EXPORTED_COMM = ROOT / "data" / "examples" / "lot37_efforts" / "complet.comm"
OUT_DIR = ROOT / "data" / "examples" / "lot38_combinaisons"


def main() -> int:
    ctx = load_project("quai_cw_test_01", ROOT)
    result = combined_forces(ctx, MESS)
    write_combined_forces(
        ctx,
        result,
        OUT_DIR,
        comm_path=EXPORTED_COMM,
        run_comm_path=RUN / "complet.comm",
    )
    check = result.manual_check
    assert check is not None
    print(
        f"{len(result.combinations)} combinaisons, écart manuel maximal "
        f"{check['max_absolute_gap']:.3e}, écrits dans {OUT_DIR.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
