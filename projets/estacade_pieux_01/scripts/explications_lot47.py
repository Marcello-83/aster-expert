"""Lot 47 -- examination of the gaps (after the run, never a verdict).

Post-execution readings, declared as such in docs/essais_lot47.md § 3.4: they change
no verdict of § 2 and tune nothing toward the source; they test candidate
explanations of the gaps.

1. Shear of the cap beam under TS against the mesh size (convergence series): does the
   share of load carried by the beam depend on the slab mesh near the pile head?
2. Slab maxima excluding the neighbourhood of the pile heads (radius 0.60 m): the
   values that the singular points do not govern (C9, C11, C12, C13).
3. Mean Nxx over each cross-section of the slab (FR, TE-), against the local maximum.
4. Contribution of each action, at the governing point of C3 and C5.
5. Scale of the self-equilibrated thermal cases: Σ |k·u| of the springs.

Usage: `.venv/bin/python projets/estacade_pieux_01/scripts/explications_lot47.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from aster_expert.projet.pipeline import load_state
from estacade_pieux_01.combinaisons import find
from estacade_pieux_01.comparaison import Comparison, _norm
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.extensions import spring_stiffness_at
from estacade_pieux_01.lecture import bcomp, comp, load_results, run_batches, run_med

CONVERGENCE_RUNS = {
    "h0p100": "data/processed/runs/20261005T100812-bdc02930",
    "h0p050": "data/processed/runs/20261005T100829-3782599a",
    "h0p025": "data/processed/runs/20261005T100910-b21d2121",
}
RADIUS = 0.60


def cap_shear_vs_mesh(ctx: Any) -> dict[str, Any]:
    v = model_values(ctx)
    out: dict[str, Any] = {}
    for label, run in CONVERGENCE_RUNS.items():
        gen = json.loads(
            (
                ctx.results_dir
                / "convergence"
                / label
                / f"conv_{label}.generation.json"
            ).read_text("utf-8")
        )
        r = load_results(run_med(ROOT / run), run_batches(gen))
        rows = r.beam_rows("CHEV_2")
        vz = r.beams["TSA_M20"][rows, bcomp("VZ")]
        mfy = r.beams["TSA_M20"][rows, bcomp("MFY")]
        heads = [p for p in v.piles() if p.file == 2]
        reaction = 0.0
        pile_rows = r.beam_rows("PIEUX")
        for p in heads:
            top = [
                i
                for i in pile_rows
                if np.allclose(r.coords[r.beam_nodes[i]], (p.x, p.y, v.z_mid))
            ]
            reaction += float(-r.beams["TSA_M20"][top[0], bcomp("N")])
        out[label] = {
            "chevetre_2_max_abs_VZ_kN": float(np.max(np.abs(vz))) / 1e3,
            "chevetre_2_max_abs_MFY_kNm": float(np.max(np.abs(mfy))) / 1e3,
            "N_tetes_file_2_kN": reaction / 1e3,
        }
    return out


def slab_away_from_heads(cmp: Comparison) -> dict[str, Any]:
    v = cmp.v
    near = np.zeros(len(cmp.x), dtype=bool)
    for p in v.piles():
        near |= np.hypot(cmp.x - p.x, cmp.y - p.y) <= RADIUS + 1e-9
    away = ~near
    out: dict[str, Any] = {"rayon_m": RADIUS, "noeuds_exclus": int(near.sum())}
    chapeau = cmp._chapeau_mask() & away
    for column in ("ELS_f", "ELS_c", "ELU"):
        env = cmp.comb.column(
            111, column, cmp.slab_ex("MXX", chapeau), lambda a: a[:, 0]
        )
        out[f"C9_{column}_kNm_m"] = float(np.max(env.maximum)) / 1e3
    lane = np.abs(cmp.y) <= v.lane[1] + 1e-9
    for label, mask, number in (
        ("courant", lane & away, 111),
        ("rive", ~lane & away, 100),
    ):
        env = cmp.comb.column(
            number, "ELU", cmp.slab_ex("QX", mask), lambda a: np.abs(a[:, 0])
        )
        out[f"C12_{label}_kN_m"] = float(np.max(env.maximum)) / 1e3
    ts_all = cmp.comb.ts["axe"] + cmp.comb.ts["bord"]
    for model, names, base in (
        ("LM1", ts_all, ["UDL", "TR"]),
        ("LM2", cmp.comb.lm2, []),
    ):
        env = cmp.comb.elementary(
            names, base, cmp.slab_ex("MXX", away), lambda a: -a[:, 0]
        )
        envq = cmp.comb.elementary(
            names, base, cmp.slab_ex("QX", away), lambda a: np.abs(a[:, 0])
        )
        out[f"C13_{model}_Mxx_inf"] = float(np.max(env.maximum)) / 1e3
        out[f"C13_{model}_Mxx_sup"] = float(np.min(env.minimum)) / 1e3
        out[f"C13_{model}_V"] = float(np.max(envq.maximum)) / 1e3
    for label, case in (("FR", "FR"), ("TE-", "TEM")):
        out[f"C11_{label}_max_abs_kN_m"] = (
            float(np.max(np.abs(cmp.r.slab[case][away, comp("NXX")]))) / 1e3
        )
    return out


def section_mean_nxx(cmp: Comparison) -> dict[str, Any]:
    out: dict[str, Any] = {}
    xs = np.unique(np.round(cmp.x, 6))
    for label, case in (("FR", "FR"), ("TE-", "TEM")):
        nxx = cmp.r.slab[case][:, comp("NXX")]
        means = []
        for x in xs:
            sel = np.abs(cmp.x - x) < 1e-6
            order = np.argsort(cmp.y[sel])
            y, n = cmp.y[sel][order], nxx[sel][order]
            means.append(float(np.trapezoid(n, y) / (y[-1] - y[0])))
        arr = np.array(means)
        i = int(np.argmax(np.abs(arr)))
        out[label] = {
            "max_abs_moyenne_section_kN_m": abs(arr[i]) / 1e3,
            "X": float(xs[i]),
        }
    return out


def pile_contributions(cmp: Comparison, rows_c: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    r = cmp.r
    for point in ("C3", "C5"):
        row = next(
            x for x in rows_c if x["point"] == point and x["colonne"].startswith("ELU")
        )
        where = row["lieu"]
        target = np.array([where["X"], where["Y"], where["Z"]])
        cand = [i for i in cmp.pile_rows if np.allclose(cmp.beam_xyz[i], target)]
        parts: dict[str, Any] = {}
        c = find(111, "ELU+")
        cases = {
            "G (PP+G2)": ["PP", "G2"],
            "UDL+TR": ["UDL", "TR"],
            "TS": [where["TS"]],
            "FR": ["FR"],
            "TE+": ["TEP"],
        }
        for label, names in cases.items():
            m = np.sum(
                [r.beams[n][cand][:, [bcomp("MFY"), bcomp("MFZ")]] for n in names],
                axis=0,
            )
            parts[label] = {
                "MFY_kNm": float(m[0, 0]) / 1e3,
                "MFZ_kNm": float(m[0, 1]) / 1e3,
                "module_kNm": float(_norm(m)[0]) / 1e3,
            }
        out[point] = {
            "lieu": where,
            "coefficients_ELU+": c.coefficients,
            "gamma_G": c.gamma_g,
            "par_action": parts,
        }
    heads = {}
    for p in cmp.v.piles():
        idx = int(
            np.argmin(
                np.linalg.norm(r.coords - np.array([p.x, p.y, cmp.v.z_mid]), axis=1)
            )
        )
        heads[p.name] = float(r.depl["TEP"][idx, 0]) * 1e3
    out["DX_tetes_TE+_mm"] = heads
    return out


def thermal_scale(cmp: Comparison) -> dict[str, Any]:
    v = cmp.v
    out = {}
    for case in ("TEP", "TEM"):
        total = 0.0
        for s in v.springs:
            for p in v.piles():
                if p.family != s.family:
                    continue
                idx = int(
                    np.argmin(
                        np.linalg.norm(cmp.r.coords - np.array([p.x, p.y, s.z]), axis=1)
                    )
                )
                k = spring_stiffness_at(v, p.x, s.z)
                total += k * float(np.hypot(*cmp.r.depl[case][idx, :2]))
        out[case] = {"somme_abs_k_u_N": total}
    return out


def main() -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    state = load_state(ctx)
    assert state.execution_dir is not None
    generation = json.loads((ctx.results_dir / "generation.json").read_text("utf-8"))
    results = load_results(run_med(Path(state.execution_dir)), run_batches(generation))
    cmp = Comparison(model_values(ctx), results, generation["positions"])
    rows = json.loads(
        (ctx.results_dir / "comparaison" / "comparaison.json").read_text("utf-8")
    )["lignes"]
    payload = {
        "statut": "lectures postérieures à l'exécution, sans verdict (docs/essais_lot47.md § 3.4)",
        "chevetre_selon_maillage_TS_file_2": cap_shear_vs_mesh(ctx),
        "dalle_hors_tetes_de_pieux": slab_away_from_heads(cmp),
        "nxx_moyen_par_section": section_mean_nxx(cmp),
        "pieux_par_action": pile_contributions(cmp, rows),
        "echelle_cas_thermiques": thermal_scale(cmp),
    }
    out = ctx.results_dir / "comparaison" / "explications.json"
    out.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
