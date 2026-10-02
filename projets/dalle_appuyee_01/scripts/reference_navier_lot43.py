"""Lot 43 : référence de Kirchhoff (série de Navier) au centre de la dalle, pour
les cas G et Q, calculée à partir des données arbitrées AVANT toute exécution.

Le nombre de termes n'est pas choisi à la main : l'ordre de troncature (m, n
impairs <= N) est doublé jusqu'à ce que la flèche et les deux moments varient de
moins de 1e-10 en relatif ; l'historique est écrit, c'est la justification du
nombre de termes. Contrôle indépendant de la flèche : série de Lévy.

Écrit `references/navier_lot43.json` (versionné). Usage :
`.venv/bin/python projets/dalle_appuyee_01/scripts/reference_navier_lot43.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from dalle_appuyee_01.generation import slab_values
from dalle_appuyee_01.navier import (
    flexural_rigidity,
    levy_centre_deflection,
    navier_centre,
)

OUT = ROOT / "projets" / "dalle_appuyee_01" / "references" / "navier_lot43.json"
TOL = 1.0e-10


def reference() -> dict[str, object]:
    ctx = load_project("dalle_appuyee_01", ROOT)
    v = slab_values(ctx)
    rigidity = flexural_rigidity(v.young, v.poisson, v.thickness)
    loads = {"G": v.unit_weight * v.thickness, "Q": v.live_load}
    cases: dict[str, object] = {}
    for case, q in loads.items():
        res = navier_centre(
            a=v.length, b=v.width, rigidity=rigidity, poisson=v.poisson, q=q, tol=TOL
        )
        levy = levy_centre_deflection(a=v.length, b=v.width, rigidity=rigidity, q=q)
        cases[case] = {
            "q_pa": q,
            "w_m": res.w,
            "mx_nm_par_m": res.mx,
            "my_nm_par_m": res.my,
            "ordre_troncature": res.order,
            "termes_m_n": ((res.order + 1) // 2) ** 2,
            "historique": [
                {"ordre": o, "w_m": w, "mx": mx, "my": my}
                for o, w, mx, my in res.history
            ],
            "w_levy_m": levy,
            "ecart_navier_levy": abs(res.w - levy) / abs(levy),
        }
    return {
        "a_m (X)": v.length,
        "b_m (Y)": v.width,
        "h_m": v.thickness,
        "E_pa": v.young,
        "nu": v.poisson,
        "D_nm": rigidity,
        "tolerance_relative_troncature": TOL,
        "convention": "w > 0 dans le sens de la charge ; Mx, My > 0 tendent la face inférieure (Kirchhoff)",
        "cas": cases,
    }


def main() -> int:
    ref = reference()
    OUT.write_text(
        json.dumps(ref, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for case, c in ref["cas"].items():  # type: ignore[attr-defined]
        print(
            f"{case} : q = {c['q_pa']:g} Pa, w = {c['w_m']:.9e} m, Mx = {c['mx_nm_par_m']:.9e}, "
            f"My = {c['my_nm_par_m']:.9e} N.m/m, ordre {c['ordre_troncature']} "
            f"({c['termes_m_n']} termes), Navier/Lévy {c['ecart_navier_levy']:.1e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
