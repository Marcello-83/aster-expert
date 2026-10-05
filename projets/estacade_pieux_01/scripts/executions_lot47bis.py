"""Lot 47 bis -- the two runs of docs/essais_lot47bis.md § 2 and § 3.

- `tr_essieu` (E18): the 57 positions of the sidewalk axle of the combination 100,
  on the verified production mesh, same model and solver as the production run;
- `chevetre_0p80` (E19): the whole production model (with the positions of E18) and
  a cap beam height of 0.80 m, sensitivity variant, never the reference.

`generer <med>` writes `resultats/lot47bis/<name>/<name>.{comm,export,mmed,
connaissances.yaml,generation.json}`; the runs are made by `aster-expert run` on the
`.export`.

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/executions_lot47bis.py generer <med>
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from estacade_pieux_01.generation import Options, build_comm

RUNS = {
    "tr_essieu": Options(mode="tr_essieu"),
    "chevetre_0p80": Options(variant="chevetre_0p80", tr_axle=True),
}


def generer(med: Path, only: tuple[str, ...] = tuple(RUNS)) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    knowledge = (ctx.project_dir / "connaissances_appliquees.yaml").read_text("utf-8")
    for name in only:
        out = ctx.results_dir / "lot47bis" / name
        out.mkdir(parents=True, exist_ok=True)
        text, report = build_comm(ctx, mesh_label=med.name, options=RUNS[name])
        (out / f"{name}.comm").write_text(text, encoding="utf-8")
        (out / f"{name}.generation.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.copyfile(med, out / f"{name}.mmed")
        (out / f"{name}.connaissances.yaml").write_text(knowledge, encoding="utf-8")
        (out / f"{name}.export").write_text(
            "P time_limit 7200\nP memory_limit 10240\nP ncpus 1\nP mpi_nbcpu 1\n"
            f"P mpi_nbnoeud 1\nF comm {name}.comm D 1\nF mmed {name}.mmed D 20\n",
            encoding="utf-8",
        )
        print(out / f"{name}.comm", report["comm_sha256"])


def main() -> None:
    command, *args = sys.argv[1:]
    if command == "generer":
        generer(Path(args[0]), tuple(args[1:]) or tuple(RUNS))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
