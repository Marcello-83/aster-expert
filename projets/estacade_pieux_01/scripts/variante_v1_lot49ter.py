"""Lot 49 ter -- effect of the declared variant V1 (D6) on the pile head, the cap beam
and the head displacement.

docs/essais_lot49ter.md, § 2.9. V1: the pile segment inside the cap beam made rigid
(`LIAISON_SOLIDE` on PIEU_T1, +0.70 to +1.30, one body per pile). Read in the
deliverables of the reference (`resultats/livrables/`) and of V1
(`resultats/livrables_derives/V1/`) with the same trunk functions and the same
combinations; nothing typed by hand. The decision of the criterion (5 % on M_dim of
the plug, E27) is taken by the engineering summary (`design_moment.variants`); this
script reports the other effects:

- pile head (C3): resultant moment at +1.30 in the reference; in V1 the elements of
  the rigid part have no generalised force (U4.44.01, LIAISON_SOLIDE), so the moment
  is read at the top of the deformable part (+0.70) in both models;
- cap beam (T section, E25): span moment, moment at the face and shear at the face;
- head displacement √(DX² + DY²) at TETES, characteristic SLS.

Writes `references/variante_v1_lot49ter.json`.
Run: `.venv/bin/python projets/estacade_pieux_01/scripts/variante_v1_lot49ter.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.livrables.appuis import subset
from aster_expert.livrables.derives import open_derived
from aster_expert.livrables.donnees import Deliverables
from aster_expert.livrables.ingenieur import family_rows
from aster_expert.livrables.sections import M_RES, section_rows
from aster_expert.livrables.torseurs import combinations_of_state, evaluate
from aster_expert.projet.context import load_project
from aster_expert.projet.declaration import LimitState

PROJECT = ROOT / "projets" / "estacade_pieux_01"
STATES: tuple[LimitState, ...] = (
    "ELU_fondamental",
    "ELS_caracteristique",
    "ELS_frequent",
)


def _envelope(fr: Any, rows: Any, column: str, combos: Any, sign: float) -> float:
    sub = subset(fr, rows)
    c = sub.column(column)
    best = -np.inf
    for _ci, _pi, values in evaluate(sub, combos):
        best = max(best, float(np.max(sign * values[:, c])))
    return best


def _model(ctx: Any, d: Deliverables, infos: Any) -> dict[str, Any]:
    summary = ctx.declaration.engineering_summary
    piles = next(f for f in summary.families if f.name == "pieux")
    caps = next(f for f in summary.families if f.name == "chevêtres")
    pr = family_rows(d, infos, summary, piles)
    cr = family_rows(d, infos, summary, caps)
    z = pr.xyz[:, 2]
    head = np.nonzero(np.abs(z - 1.30) < 1e-6)[0]
    # Haut de la partie déformable : extrémité à +0,70 de l'élément +0,50 → +0,70.
    top = []
    for r in np.nonzero(np.abs(z - 0.70) < 1e-6)[0]:
        if pr.kind[r] != 1:
            continue
        other = [
            q
            for q in np.nonzero(
                (pr.element == pr.element[r]) & (pr.level == pr.level[r])
            )[0]
            if q != r
        ]
        if other and pr.xyz[other[0], 2] < 0.70:
            top.append(int(r))
    sections = {s.name: s for s in summary.sections}
    span = section_rows(cr, d.mesh, sections["chevetre_travee"], None)
    face = section_rows(cr, d.mesh, sections["chevetre_nu_appui"], None)
    out: dict[str, Any] = {}
    for state in STATES:
        combos = combinations_of_state(d.combinations, summary, state)
        out[state] = {
            "tete_+1,30_M_kNm": _envelope(pr, head, M_RES, combos, 1.0) * 1e-3,
            "haut_partie_deformable_+0,70_M_kNm": _envelope(pr, top, M_RES, combos, 1.0)
            * 1e-3,
            "chevetre_travee_M_kNm": _envelope(
                cr, np.nonzero(span.mask)[0], "MFY", combos, -1.0
            )
            * 1e-3,
            "chevetre_nu_M_kNm": _envelope(
                cr, np.nonzero(face.mask)[0], "MFY", combos, 1.0
            )
            * 1e-3,
            "chevetre_nu_V_kN": max(
                _envelope(cr, np.nonzero(face.mask)[0], "VZ", combos, 1.0),
                _envelope(cr, np.nonzero(face.mask)[0], "VZ", combos, -1.0),
            )
            * 1e-3,
        }
    # Déplacement horizontal en tête, ELS caractéristique.
    depl = next(i for i in infos if i.key == "DEPL")
    fa = d.field(depl)
    nodes = fa.node_of_row(d.mesh)
    rows = np.nonzero(np.isin(nodes, d.mesh.node_group("TETES")))[0]
    combos = combinations_of_state(d.combinations, summary, "ELS_caracteristique")
    best = 0.0
    for _ci, comb in combos:
        base = sum(
            (k * fa.arrays[f"cas/{n}"][rows] for n, k in comb.fixed.items() if k),
            np.zeros((len(rows), len(depl.components))),
        )
        for p in comb.mobile_cases or (None,):
            v = (
                base
                if p is None
                else base + comb.mobile_coefficient * fa.arrays[f"pos/{p}"][rows]
            )
            dx = v[:, depl.components.index("DX")]
            dy = v[:, depl.components.index("DY")]
            best = max(best, float(np.max(np.hypot(dx, dy))))
    out["deplacement_tete_ELS_c_mm"] = best * 1e3
    return out


def main() -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    ref_d = Deliverables(PROJECT / "resultats" / "livrables", keep_fields=True)
    section = ctx.declaration.deliverables
    assert section is not None
    ref = _model(ctx, ref_d, ref_d.field_infos(section.fields))
    v1_d, v1_infos, _rec = open_derived(ctx, "V1")
    v1_d.__dict__["combinations"] = ref_d.combinations
    v1 = _model(ctx, v1_d, v1_infos)

    def change(a: float, b: float) -> float:
        return (b - a) / abs(a) if a else float("nan")

    effects: dict[str, Any] = {}
    for state in STATES:
        effects[state] = {
            key: {"reference": ref[state][key], "V1": v1[state][key],
                  "variation": change(ref[state][key], v1[state][key])}
            for key in ref[state]
        }  # fmt: skip
    effects["deplacement_tete_ELS_c_mm"] = {
        "reference": ref["deplacement_tete_ELS_c_mm"],
        "V1": v1["deplacement_tete_ELS_c_mm"],
        "variation": change(
            ref["deplacement_tete_ELS_c_mm"], v1["deplacement_tete_ELS_c_mm"]
        ),
    }
    out = {
        "lot": "49 ter",
        "variante": "V1 : tronçon de pieu +0,70 → +1,30 indéformable (LIAISON_SOLIDE, "
        "U4.44.01), aucun nœud à +0,60",
        "note": "en V1, les éléments de la partie rigide n'ont pas d'effort généralisé "
        "(U4.44.01) : le moment de tête est lu au haut de la partie déformable "
        "(+0,70) dans les deux modèles ; la valeur au nœud +1,30 de V1 est nulle par "
        "construction",
        "effets": effects,
    }
    path = PROJECT / "references" / "variante_v1_lot49ter.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
