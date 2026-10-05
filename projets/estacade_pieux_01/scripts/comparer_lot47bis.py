"""Lot 47 bis -- comparison v2 (E17, E18) and check of the supervisor's diagnostics.

Reads the MED of the production run of lot 47 and, when given, the MED of the run of
the sidewalk axle of E18 (same mesh), then writes
`resultats/lot47bis/comparaison_v2.json` with:

- `lignes`: C1 to C13 read as written in docs/essais_lot47bis.md § 1 (criteria
  committed before this reading), with the rule, the location, the governing family
  and moving case;
- `controle_total`: the check of the total bar + slab of § 1.5 (free body under PP);
- `diagnostic_a`, `diagnostic_b`: the numbers the supervisor quoted, recomputed.

A variant run (E19) is read the same way with `--variante <run_dir> <generation.json>`
(its own MED holds every case, the axle of E18 included).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/comparer_lot47bis.py \
      <production_run> [<tr_essieu_run>] [--variante <run> <generation.json> <out.json>]
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
from estacade_pieux_01.combinaisons import find
from estacade_pieux_01.comparaison import _norm
from estacade_pieux_01.comparaison_v2 import CRITERIA, ComparisonV2, merge
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.lecture import load_results, run_batches, run_med

V1 = ROOT / "projets" / "estacade_pieux_01" / "references" / "comparaison_lot47.json"


def diagnostic_a(cmp: ComparisonV2) -> dict[str, Any]:
    """(a) Location and family of the v1 readings of C3 and C5; moment at the head
    node of F7_YP under 111 ELU+; moment and shear along the head elements."""
    c1 = cmp.c1
    out: dict[str, Any] = {}
    v1 = json.loads(V1.read_text("utf-8"))["lignes"]
    top, bottom = cmp.v.plug
    zones = {
        "C3": c1._pile_zone(bottom, top),
        "C5": c1._pile_zone(-1e9, bottom - 2e-6),
    }
    for point, rows in zones.items():
        row = next(
            r for r in v1 if r["point"] == point and r["colonne"].startswith("ELU")
        )
        ex = c1.beam_ex(rows, ("MFY", "MFZ"))
        fam: dict[str, dict[str, Any]] = {}
        for family in ("ELU+", "ELU-"):
            env = c1.comb.combine(find(111, family), ex, _norm)
            i = int(np.argmax(env.maximum))
            fam[family] = {
                "max_kNm": float(env.maximum[i]) / 1e3,
                "lieu_Z": float(c1.beam_xyz[rows[i], 2]),
                "cas_mobile": env.arg_max[i],
            }
        governing = (
            "ELU+" if fam["ELU+"]["max_kNm"] >= fam["ELU-"]["max_kNm"] else "ELU-"
        )
        out[f"{point}_v1"] = {
            "valeur_v1_kNm": row["code_aster"],
            "lieu_v1": row["lieu"],
            "par_famille": fam,
            "famille_qui_gouverne": governing,
        }
    pile = next(p for p in cmp.v.piles() if p.name == "F7_YP")
    rows = np.array(
        [
            r
            for r in c1.pile_rows
            if abs(c1.beam_xyz[r, 0] - pile.x) < 1e-6
            and abs(c1.beam_xyz[r, 1] - pile.y) < 1e-6
        ]
    )
    z = c1.beam_xyz[rows, 2]
    c = find(111, "ELU+")
    ex = c1.beam_ex(rows, ("MFY", "MFZ", "VY", "VZ"))
    fixed = c.gamma_g * (ex("PP") + ex("G2"))
    for action, coef in c.coefficients.items():
        if action == "LM1":
            fixed = fixed + coef * (ex("UDL") + ex("TR"))
        else:
            fixed = fixed + coef * ex({"FR": "FR", "TE+": "TEP", "TE-": "TEM"}[action])
    names = c1.comb.ts["bord"]
    stack = np.stack([fixed + c.coefficients["LM1"] * ex(n) for n in names])
    head = int(np.nonzero(np.abs(z - cmp.v.z_mid) < 1e-6)[0][0])
    moments = np.hypot(stack[:, :, 0], stack[:, :, 1])
    k = int(np.argmax(moments[:, head]))
    profile = []
    order = np.argsort(-z)
    for j in order[:8]:
        profile.append(
            {
                "Z": float(z[j]),
                "M_kNm": float(moments[k, j]) / 1e3,
                "V_kN": float(np.hypot(stack[k, j, 2], stack[k, j, 3])) / 1e3,
            }
        )
    out["F7_YP_111_ELU+"] = {
        "M_tete_kNm": float(moments[k, head]) / 1e3,
        "cas_mobile": names[k],
        "ecart_a_449": (float(moments[k, head]) / 1e3 - 449) / 449,
        "ecart_a_463": (float(moments[k, head]) / 1e3 - 463) / 463,
        "profil_haut_du_pieu": profile,
    }
    return out


def diagnostic_b(cmp: ComparisonV2) -> dict[str, Any]:
    """(b) At Y = ±1.90 under 112 ELU+: VZ of the cap beam, ∫QY of the band, total;
    on the support (Y = ±2.00): bar and slab parts of the total moment."""
    c1 = cmp.c1
    rows = c1.cap_rows
    y = c1.beam_xyz[rows, 1]
    c = find(112, "ELU+")
    out: dict[str, Any] = {}
    exv_bar = cmp.cap_ex("V", total=False)
    exv_tot = cmp.cap_ex("V", total=True)
    exm_bar = cmp.cap_ex("M", total=False)
    exm_tot = cmp.cap_ex("M", total=True)
    for label, target, exb, ext, sign in (
        ("effort_tranchant_Y_1p90", 1.90, exv_bar, exv_tot, None),
        ("moment_sur_appui_Y_2p00", 2.00, exm_bar, exm_tot, -1.0),
    ):
        sel = np.nonzero(np.abs(np.abs(y) - target) < 1e-6)[0]

        def take(ex: Any, sel: Any = sel) -> Any:
            return lambda name, sel=sel: ex(name)[sel]

        if sign is None:
            env = cmp.comb.combine(c, take(ext), lambda a: np.abs(a[:, 0]))
            i = int(np.argmax(env.maximum))
        else:
            env = cmp.comb.combine(c, take(ext), lambda a: a[:, 0])
            i = int(np.argmin(env.minimum))
        case = env.arg_max[i] if sign is None else env.arg_min[i]

        def value(ex: Any, case: str = case, i: int = i, sel: Any = sel) -> float:
            fixed = c.gamma_g * (ex("PP") + ex("G2"))
            for action, coef in c.coefficients.items():
                if action == "LM1":
                    fixed = fixed + coef * (ex("UDL") + ex("TR") + ex(case))
                else:
                    fixed = fixed + coef * ex(
                        {"FR": "FR", "TE+": "TEP", "TE-": "TEM"}[action]
                    )
            return float(fixed[sel][i, 0]) / 1e3

        bar = value(exb)
        total = value(ext)
        out[label] = {
            "lieu": cmp._where_beam(int(rows[sel[i]])),
            "cas_mobile": case,
            "barre_kN_ou_kNm": bar,
            "dalle_kN_ou_kNm": total - bar,
            "total": total,
            "part_dalle": (total - bar) / total if total else float("nan"),
        }
    return out


def read(
    production: Path, tr_run: Path | None, ctx: Any
) -> tuple[ComparisonV2, dict[str, Any]]:
    generation = json.loads((ctx.results_dir / "generation.json").read_text("utf-8"))
    results = load_results(run_med(production), run_batches(generation))
    positions = dict(generation["positions"])
    tr_axle: list[str] = []
    if tr_run is not None:
        gen_tr = json.loads(
            (
                ctx.results_dir / "lot47bis" / "tr_essieu" / "tr_essieu.generation.json"
            ).read_text("utf-8")
        )
        extra = load_results(run_med(tr_run), run_batches(gen_tr))
        results = merge(results, extra)
        tr_axle = [lot_case for lot in gen_tr["lots"] for lot_case in lot["cas"]]
    cmp = ComparisonV2(model_values(ctx), results, positions, tr_axle)
    return cmp, {"execution_production": str(production), "execution_tr": str(tr_run)}


def main() -> None:
    args = sys.argv[1:]
    ctx = load_project("estacade_pieux_01", ROOT)
    out_dir = ctx.results_dir / "lot47bis"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args[0] == "--variante":
        run, gen_path, out = Path(args[1]), Path(args[2]), Path(args[3])
        generation = json.loads(gen_path.read_text("utf-8"))
        results = load_results(run_med(run), run_batches(generation))
        tr_axle = [n for n, p in generation["positions"].items() if p["modele"] == "TR"]
        positions = {
            n: p for n, p in generation["positions"].items() if p["modele"] != "TR"
        }
        cmp = ComparisonV2(model_values(ctx), results, positions, tr_axle)
        payload = {
            "statut": "variante de sensibilité E19, sans verdict ; contre-calcul d'un "
            "modèle non validé",
            "critere": CRITERIA,
            "execution": str(run),
            "comm_sha256": generation["comm_sha256"],
            "lignes": [r for r in cmp.caps() if r["point"] in ("C6", "C7", "C8")],
        }
        out.write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n", "utf-8"
        )
        print(out)
        return
    production = Path(args[0])
    tr_run = Path(args[1]) if len(args) > 1 else None
    cmp, runs = read(production, tr_run, ctx)
    payload = {
        "statut": "contre-calcul d'un modèle non validé (jamais un niveau E) ; "
        "critères v2 écrits après la première exécution",
        "critere": CRITERIA,
        **runs,
        "lignes": cmp.all_points(),
        "controle_total": cmp.total_check(),
        "diagnostic_a": diagnostic_a(cmp),
        "diagnostic_b": diagnostic_b(cmp),
        "disques": {"rayon_m": 0.60, "noeuds_exclus": int((~cmp.away).sum())},
    }
    path = out_dir / "comparaison_v2.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(path)


if __name__ == "__main__":
    main()
