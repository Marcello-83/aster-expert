"""Lot 47 -- mesh convergence series of the slab under a wheel load (point U3).

`generer` : for each size of `CONVERGENCE_SIZES`, writes under
`resultats/convergence/<h>/` the `.comm` of the mode `convergence` (TS axé centred at
X = 8,10 and X = 5,60), its `.export`, the verified MED of that size (path given on
the command line, as produced by `aster-expert mesh run` and accepted by `mesh check`)
and the knowledge companion file.

`analyser` : reads the MED of each run with `medcoupling` in the container
(`scripts/lire_resultats_lot47.py`, mode `convergence`) and writes
`references/convergence_lot47.json` with the verdict of the criterion of
`docs/essais_lot47.md` § 2.7 (written before the runs).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/convergence_lot47.py generer h0p100=<med> h0p050=<med> h0p025=<med>
  .venv/bin/python projets/estacade_pieux_01/scripts/convergence_lot47.py analyser h0p100=<run_dir> h0p050=<run_dir> h0p025=<run_dir>
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.projet.context import load_project
from estacade_pieux_01.discretisation import CONVERGENCE_SIZES, JettyMesh
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.generation import Options, build_comm

KNOWLEDGE = """# Connaissances appliquées par la suite de convergence du lot 47.
schema_version: 1
project: estacade_pieux_01
applied:
  - id: PAT-003
    how: "empreintes de roue par bandes CREA_GROUP_MA/BANDE CRIT_NOEUD=TOUS intersectées"
  - id: CA-029
    how: "pression de roue constante sur des mailles entières, jamais une fonction évaluée aux nœuds"
  - id: PAT-001
    how: "ressorts par classe de raideur, une maille POI1 par nœud"
  - id: DIAG-004
    how: "masse nulle M_T_D_N des ressorts DIS_T"
  - id: CA-055
    how: "MACRO_ELAS_MULT, une factorisation pour les deux positions"
  - id: DIAG-011
    how: "EFGE_NOEU restreint à la dalle"
"""


def _pairs(args: list[str]) -> dict[str, Path]:
    out = {}
    for arg in args:
        label, _, path = arg.partition("=")
        out[label] = Path(path)
    return out


def generer(meds: dict[str, Path]) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    values = model_values(ctx)
    for size in CONVERGENCE_SIZES:
        mesh = JettyMesh(values, size)
        label = mesh.label()
        out = ctx.results_dir / "convergence" / label
        out.mkdir(parents=True, exist_ok=True)
        stem = f"conv_{label}"
        text, report = build_comm(
            ctx,
            mesh_label=f"{label}.med",
            options=Options(mode="convergence", cell=size),
        )
        (out / f"{stem}.comm").write_text(text, encoding="utf-8")
        (out / f"{stem}.generation.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.copyfile(meds[label], out / f"{stem}.mmed")
        (out / f"{stem}.connaissances.yaml").write_text(KNOWLEDGE, encoding="utf-8")
        (out / f"{stem}.export").write_text(
            "P time_limit 3600\nP memory_limit 10240\nP ncpus 1\nP mpi_nbcpu 1\n"
            f"P mpi_nbnoeud 1\nF comm {stem}.comm D 1\nF mmed {stem}.mmed D 20\n"
            f"F rmed {stem}.rmed R 80\n",
            encoding="utf-8",
        )
        print(out / f"{stem}.comm", report["comm_sha256"])


def analyser(runs: dict[str, Path]) -> None:
    from estacade_pieux_01.lecture import read_convergence  # noqa: PLC0415

    ctx = load_project("estacade_pieux_01", ROOT)
    result = read_convergence(ctx, runs)
    out = ctx.project_dir / "references" / "convergence_lot47.json"
    out.write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["verdicts"], indent=1, ensure_ascii=False))


def main() -> None:
    command, *args = sys.argv[1:]
    if command == "generer":
        generer(_pairs(args))
    elif command == "analyser":
        analyser(_pairs(args))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
