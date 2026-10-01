"""Lot 39, étapes 3.2, 3.3 et 4 : lecture de `CALC_FERRAILLAGE` sur la poutre de
couronnement, enveloppes As(X), contre-vérification de sections par le module
indépendant, tableau de synthèse avec les minima et l'effort tranchant / torsion
calculés hors de Code_Aster.

Lot 41 : le calcul est fait par le tronc commun (`aster_expert.ferraillage.poutre`)
et la prose du tableau et de la figure par l'extension du projet
(`quai_cw_test_01.rapports.rebar_report`) ; ce script n'en est plus que l'appel.
Le `.comm` exécuté doit être celui du répertoire de sortie, octet pour octet.

Aucun verdict de conformité : des aires calculées sous les hypothèses de la
fiche.

Usage : python projets/quai_cw_test_01/scripts/analyze_lot39_poutre.py \\
    <répertoire d'exécution> [répertoire de sortie]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.ferraillage.poutre import analyze_member  # noqa: E402
from aster_expert.projet.context import load_project  # noqa: E402

DIR = ROOT / "data" / "examples" / "lot39_poutre"


def main(argv: list[str]) -> int:
    run = Path(argv[1]).resolve()
    out = Path(argv[2]) if len(argv) > 2 else DIR
    ctx = load_project("quai_cw_test_01", ROOT)
    assert ctx.declaration.rebar is not None
    result = analyze_member(ctx, ctx.declaration.rebar.members[0], run, out)
    print(json.dumps(result.summary, ensure_ascii=False, indent=1))
    return 0 if not result.summary["controle_main"]["echecs"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
