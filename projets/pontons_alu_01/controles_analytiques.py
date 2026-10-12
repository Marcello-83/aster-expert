"""Analytical checks of PONTONS-ALU-01 (lot 50), criteria written before reading the
results in docs/essais_lot50.md § 2.

- § 2.1: total vertical reaction under G1 (quay hinges + soil springs, from the level
  D harness, `equilibre.json`) against the weight computed by hand, 0,5 %.
- § 2.2: moment of the whole deck section at X = L/2 under Q, from the beam forces of
  the deliverables (EFGE_ELNO of case Q), against q·b·L²/8, 10 %.

The section moment about the global axis Y through (L/2, ·, z_PP) is
Σ (MT x_l + MFY y_l + MFZ z_l)·e_Y + Σ N (x_l·e_X)(z − z_PP) over the cut members,
each torsor interpolated linearly at the cut between the ends of the element that
crosses it (R3.08.01 : MFY = ∫ z σ_xx dS, the force of the +x_l side on the −x_l side).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.livrables.donnees import Deliverables, FieldArrays
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.geometrie import geometry, influence_widths

HAND_WEIGHT_N = 44988.4
"""docs/essais_lot50.md § 2.1, written before the run."""
CUT_MEMBERS_PREFIXES = ("PP_", "PANNE_", "DIAG_", "MONT_")


def _beam_field(d: Deliverables, ctx: ProjectContext) -> FieldArrays:
    section = ctx.declaration.deliverables
    assert section is not None
    infos = d.field_infos(section.fields)
    info = next(i for i in infos if i.field == "EFGE_ELNO")
    return d.field(info)


def section_moment(ctx: ProjectContext, case: str, x_cut: float) -> dict[str, Any]:
    """Moment about global Y of the deck section X = x_cut, member by member."""
    d = Deliverables(ctx.results_dir / "livrables")
    fa = _beam_field(d, ctx)
    comps = list(fa.info.components)
    values = fa.arrays[f"cas/{case}"]
    coords = d.mesh.coords
    z0 = geometry().deck_z
    rows = []
    total = 0.0
    for prefix in CUT_MEMBERS_PREFIXES:
        names = sorted(
            k.split("_", 2)[2]
            for k in d.mesh.arrays
            if k.startswith("gma_") and k.split("_", 2)[2].startswith(prefix)
        )
        for name in names:
            cells = d.mesh.cell_group(name)
            assert cells is not None
            level, ids = cells
            conn = d.mesh.arrays[f"conn_{level}"]
            for cell in ids:
                a, b = conn[cell][0], conn[cell][1]
                xa, xb = coords[a][0], coords[b][0]
                lo, hi = min(xa, xb), max(xa, xb)
                if not (lo <= x_cut < hi) or abs(xb - xa) < 1e-9:
                    continue
                sel = (fa.kind == 1) & (fa.level == level) & (fa.entity == cell)
                ends = {int(fa.local[i]): values[i] for i in np.flatnonzero(sel)}
                t = (x_cut - xa) / (xb - xa)
                torsor = (1 - t) * ends[0] + t * ends[1]
                tor = dict(zip(comps, torsor.tolist(), strict=True))
                xl = coords[b] - coords[a]
                xl = xl / np.linalg.norm(xl)
                zl = np.array([0.0, 0.0, 1.0])
                yl = np.cross(zl, xl)
                moment = tor["MT"] * xl + tor["MFY"] * yl + tor["MFZ"] * zl
                z = float(coords[a][2] + t * (coords[b][2] - coords[a][2]))
                lever = tor["N"] * xl[0] * (z - z0)
                contribution = float(moment[1] + lever)
                total += contribution
                rows.append(
                    {
                        "barre": name,
                        "element": int(cell),
                        "z_m": z,
                        "N_n": tor["N"],
                        "MT_nm": tor["MT"],
                        "MFY_nm": tor["MFY"],
                        "MFZ_nm": tor["MFZ"],
                        "moment_Y_nm": float(moment[1]),
                        "bras_de_levier_nm": float(lever),
                        "contribution_nm": contribution,
                    }
                )
    return {"x_coupe_m": x_cut, "barres": rows, "moment_total_nm": total}


def run(ctx: ProjectContext) -> dict[str, Any]:
    """Lot 50: G1 against the hand weight of the lot 50 geometry, and Q."""
    eq = json.loads((ctx.results_dir / "controles" / "equilibre.json").read_text())
    out: dict[str, Any] = {"criteres": "docs/essais_lot50.md § 2 (écrits avant)"}
    g1 = _case(eq, "G1")
    reaction = g1["reactions_dz"]
    out["G1"] = {
        "poids_a_la_main_n": HAND_WEIGHT_N,
        "reaction_totale_n": reaction,
        "detail": g1,
        "ecart_relatif": abs(reaction - HAND_WEIGHT_N) / HAND_WEIGHT_N,
        "tolerance": 0.005,
    }
    out["G1"]["verdict"] = "RÉUSSI" if out["G1"]["ecart_relatif"] <= 0.005 else "ÉCHEC"
    out["Q_mi_portee"] = q_midspan(ctx, eq)
    return out


def q_midspan(ctx: ProjectContext, eq: dict[str, Any]) -> dict[str, Any]:
    """§ 2.2 of lot 50, § 2 of lot 50 bis: moment of the deck section at L/2 under Q
    against q·b·L²/8, b the loaded width (Σ of the influence widths), 10 %."""
    g = geometry()
    span = g.parameters["L"]
    out: dict[str, Any] = {}
    q = 5000.0
    b = sum(influence_widths(g).values())
    reference = q * b * span**2 / 8.0
    cut = section_moment(ctx, "Q", span / 2.0)
    m = cut["moment_total_nm"]
    rq = _case(eq, "Q")["reactions_quai_dz"]
    statics = rq * span / 2.0 - q * b * (span / 2.0) ** 2 / 2.0
    out["Q_mi_portee"] = {
        "qbL2_sur_8_nm": reference,
        "b_m": b,
        "coupe": cut,
        "moment_section_nm": m,
        "ecart_relatif": abs(abs(m) - reference) / reference,
        "tolerance": 0.10,
        "verification_statique": {
            "reaction_quai_dz_n": rq,
            "moment_libre_rq_l2_moins_qbl2_8_nm": statics,
            "ecart_a_la_somme_des_barres_nm": abs(abs(m) - abs(statics)),
        },
    }
    out["Q_mi_portee"]["verdict"] = (
        "RÉUSSI" if out["Q_mi_portee"]["ecart_relatif"] <= 0.10 else "ÉCHEC"
    )
    return dict(out["Q_mi_portee"])


def run_lot50bis(ctx: ProjectContext) -> dict[str, Any]:
    """Lot 50 bis: the Q check only (consigne), b = 2,00 m (P24)."""
    eq = json.loads((ctx.results_dir / "controles" / "equilibre.json").read_text())
    return {
        "criteres": "docs/essais_lot50bis.md § 2 (écrits avant)",
        "Q_mi_portee": q_midspan(ctx, eq),
    }


def _case(eq: dict[str, Any], case: str) -> dict[str, Any]:
    """Vertical reactions on the structure of a case in `equilibre.json` (level D
    harness): blocked components of the quay hinges and soil springs."""
    dz = eq["cases"][case]["components"]["DZ"]
    quay = float(dz["reactions_blocked_n"])
    springs = float(dz["springs_on_structure_n"])
    return {
        "reactions_quai_dz": quay,
        "ressorts_dz": springs,
        "reactions_dz": quay + springs,
    }


def write(ctx: ProjectContext, target: Path) -> dict[str, Any]:
    result = run(ctx)
    target.write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


__all__ = [
    "HAND_WEIGHT_N",
    "q_midspan",
    "run",
    "run_lot50bis",
    "section_moment",
    "write",
]
