"""Lot 47 -- comparison of the production run with the values of the source model.

Reads the MED of the run of the project chain (`etat.json`: last execution) with
`medcoupling` in the container, then computes C1 to C13 as written in
docs/essais_lot47.md § 2.3 to 2.5 (criteria committed before the run), and writes:

- `resultats/comparaison/comparaison.json` (every row: Code_Aster, source, gap,
  tolerance, verdict, location);
- `resultats/comparaison/comparaison.md` (the table of the report).

Explanations of the gaps are not written here: they go in the report, after
examination (docs/essais_lot47.md § 3), never into the numbers.

Usage: `.venv/bin/python projets/estacade_pieux_01/scripts/comparer_lot47.py [<run_dir>]`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from aster_expert.projet.pipeline import load_state
from estacade_pieux_01.comparaison import Comparison
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.lecture import load_results, run_batches, run_med


def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4g}"
    return str(x)


def render(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Point | Colonne | Code_Aster | Source | Écart | Tolérance | Verdict | Lieu |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        tol = "—" if r["tolerance"] is None else f"{100 * r['tolerance']:.0f} %"
        gap = r["ecart_relatif"]
        gap_s = "—" if gap != gap else f"{100 * gap:+.1f} %"
        where = ", ".join(f"{k} {_fmt(v)}" for k, v in r["lieu"].items())
        lines.append(
            f"| {r['point']} | {r['colonne']} | {r['code_aster']:.4g} | {r['source']} "
            f"| {gap_s} | {tol} | {r['verdict']} | {where} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
    else:
        state = load_state(ctx)
        if state.execution_dir is None:
            raise SystemExit("aucune exécution du projet (etat.json)")
        run_dir = Path(state.execution_dir)
    generation = json.loads((ctx.results_dir / "generation.json").read_text("utf-8"))
    med = run_med(run_dir)
    results = load_results(med, run_batches(generation))
    comparison = Comparison(model_values(ctx), results, generation["positions"])
    rows = comparison.all_points()
    out = ctx.results_dir / "comparaison"
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "statut": "contre-calcul d'un modèle non validé (jamais un niveau E)",
        "critere": "docs/essais_lot47.md § 2.3 à 2.5",
        "execution": str(run_dir),
        "comm_sha256": generation["comm_sha256"],
        "lignes": rows,
    }
    (out / "comparaison.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out / "comparaison.md").write_text(render(rows), encoding="utf-8")
    print(render(rows))


if __name__ == "__main__":
    main()
