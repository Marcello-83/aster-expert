"""Lot 36, étape 2 : la résultante de la pression initiale de V1 est-elle attendue ?

Bilan des forces selon Y du cas G : charges appliquées + réactions des ancrages +
force des ressorts = 0 (lots 34 et 35). V1 n'ajoute que la pression initiale : la
variation de (réaction d'ancrage DY + force des ressorts) entre V1 et la base doit
valoir l'opposée de la résultante attendue, calculée par une autre voie :
somme sur les bandes de ∫ p(z) · L_proj(bande) dz (pression linéaire sur la bande,
largeur projetée analytique `band_projected_width`, faces bassin -- tubes et
palplanches), dirigée vers la terre (+Y).

Usage : python scripts/analyze_lot36_resultante_v1.py <données> <.mess base> \\
    <.mess V1> <sortie.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.terre import REPOS_TABLE_KPA
from aster_expert.meshing.combiwall import band_projected_width, build_params
from aster_expert.report.build import build_synthesis


def _balance(mess: Path, data: Path) -> tuple[float, float]:
    synth = build_synthesis(mess, data, cases=("G",))
    case = synth.cases[0]
    return case.reactions[0].dy, case.springs.total_force_n


def main(data: Path, base: Path, v1: Path, out: Path) -> int:
    params = build_params(load_model_data(data))
    expected = 0.0
    detail = {}
    for band, points in REPOS_TABLE_KPA.items():
        (za, pa), (zb, pb) = sorted(points)
        width = band_projected_width(params, params["bandes"][band])
        force = (pa + pb) / 2.0 * 1.0e3 * (zb - za) * width
        detail[band] = {"largeur_projetee_m": width, "force_N": force}
        expected += force
    r0, s0 = _balance(base, data)
    r1, s1 = _balance(v1, data)
    delta = (r1 + s1) - (r0 + s0)
    res = {
        "attendu_resultante_V1_N": expected,
        "detail": detail,
        "base": {"ancrage_dy_N": r0, "ressorts_N": s0},
        "v1": {"ancrage_dy_N": r1, "ressorts_N": s1},
        "variation_ancrage_plus_ressorts_N": delta,
        "ecart_relatif_a_l_oppose": (delta + expected) / abs(expected),
    }
    out.write_text(
        json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a) for a in sys.argv[1:5])))
