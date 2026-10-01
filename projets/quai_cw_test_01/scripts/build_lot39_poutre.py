"""Lot 39, étape 3.1 : `CALC_FERRAILLAGE` appliqué aux efforts combinés de la
poutre de couronnement, pour chaque famille de D17, avec les paramètres de D18 et
la position des armatures de D19 (schéma des cas tests officiels `ssll13*`).

Lot 41 : le cas est écrit par le tronc commun (`aster_expert.ferraillage.poutre`,
déclaration `rebar` de `projet.yaml`) ; ce script n'en est plus que l'appel sur
l'exécution du modèle complet réutilisée aux lots 38 et 39
(`data/processed/runs/20260925T125131-c67e28a1`). Le `.comm` écrit ne diffère de
celui du lot 39 que par la ligne « Produit par », qui nomme désormais le module du
tronc commun : relancer ce script réécrit donc `data/examples/lot39_poutre/`
autrement que l'exécution archivée du lot 39 (`20260928T100157-30609502`).

Usage : python projets/quai_cw_test_01/scripts/build_lot39_poutre.py [répertoire]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.ferraillage.poutre import prepare_member  # noqa: E402
from aster_expert.projet.context import load_project  # noqa: E402

MESS = (
    ROOT
    / "data"
    / "processed"
    / "runs"
    / "20260925T125131-c67e28a1"
    / "proc.0"
    / "fort.6"
)
OUT_DIR = ROOT / "data" / "examples" / "lot39_poutre"


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else OUT_DIR
    ctx = load_project("quai_cw_test_01", ROOT)
    assert ctx.declaration.rebar is not None
    member = ctx.declaration.rebar.members[0]
    comm = prepare_member(ctx, member, MESS, out)
    print(f"écrit {comm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
