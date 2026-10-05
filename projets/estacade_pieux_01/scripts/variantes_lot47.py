"""Lot 47 -- sensitivity variants declared by MM (E13), never the reference.

(a) `dst`: DST slab; (b) `pou_d_e_chevetres`: POU_D_E cap beams, to test the
hypothesis « the source model ignores the shear deformation of the bars », asked by
MM if C6 to C8 are out of tolerance (they are: docs/essais_lot47.md § 3).

`generer` writes `resultats/variantes/<variant>/var_<variant>.{comm,export,mmed,
connaissances.yaml,generation.json}` on the verified production mesh;
`comparer <variant>=<run_dir> ...` writes `resultats/variantes/<variant>/comparaison.json`
with the same reading as the reference (criteria of § 2, unchanged).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/variantes_lot47.py generer <med>
  .venv/bin/python projets/estacade_pieux_01/scripts/variantes_lot47.py comparer dst=<run> pou_d_e_chevetres=<run>
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from estacade_pieux_01.comparaison import Comparison
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.generation import Options, build_comm
from estacade_pieux_01.lecture import load_results, run_batches, run_med

VARIANTS = ("dst", "pou_d_e_chevetres")


def generer(med: Path, only: tuple[str, ...] = VARIANTS) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    knowledge = (ctx.project_dir / "connaissances_appliquees.yaml").read_text("utf-8")
    for variant in only:
        out = ctx.results_dir / "variantes" / variant
        out.mkdir(parents=True, exist_ok=True)
        stem = f"var_{variant}"
        text, report = build_comm(
            ctx,
            mesh_label=med.name,
            options=Options(
                variant=variant,
                resi_rela=1e-5 if variant == "pou_d_e_chevetres" else None,
            ),
        )
        (out / f"{stem}.comm").write_text(text, encoding="utf-8")
        (out / f"{stem}.generation.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.copyfile(med, out / f"{stem}.mmed")
        (out / f"{stem}.connaissances.yaml").write_text(knowledge, encoding="utf-8")
        (out / f"{stem}.export").write_text(
            "P time_limit 7200\nP memory_limit 10240\nP ncpus 1\nP mpi_nbcpu 1\n"
            f"P mpi_nbnoeud 1\nF comm {stem}.comm D 1\nF mmed {stem}.mmed D 20\n",
            encoding="utf-8",
        )
        print(out / f"{stem}.comm", report["comm_sha256"])


def comparer(runs: dict[str, Path]) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    for variant, run_dir in runs.items():
        out = ctx.results_dir / "variantes" / variant
        generation = json.loads(
            (out / f"var_{variant}.generation.json").read_text("utf-8")
        )
        results = load_results(run_med(run_dir), run_batches(generation))
        rows = Comparison(
            model_values(ctx), results, generation["positions"]
        ).all_points()
        payload = {
            "statut": "variante de sensibilité (E13), contre-calcul d'un modèle non validé",
            "variante": variant,
            "execution": str(run_dir),
            "lignes": rows,
        }
        (out / "comparaison.json").write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(variant, "écrit")


def main() -> None:
    command, *args = sys.argv[1:]
    if command == "generer":
        generer(Path(args[0]), tuple(args[1:]) or VARIANTS)
    elif command == "comparer":
        comparer({a.split("=", 1)[0]: Path(a.split("=", 1)[1]) for a in args})
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
