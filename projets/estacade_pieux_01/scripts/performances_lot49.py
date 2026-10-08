"""Lot 49, step 0 -- OpenMP threads, measured again with three repetitions per point.

Lot 47 quater measured one run per point (1, 4, 8, 12 threads) on the slab mesh of
0.25 m (case N3): 1.03, 0.85, 0.41 of the one-thread time. One run per point does not
make a rule. This script measures again, **three repetitions** per point, with 1, 4, 8,
12 and 14 threads (`P ncpus`, one MPI process), on two sizes:

- `n3`: the `.comm` of N3 (lot 47 ter, `data/processed/runs/20261006T125858-33203f20`,
  slab mesh of 0.25 m), unchanged but for `DEBUT`;
- `prod`: the production `.comm` of the structure (E13, slab mesh of 0.05 m, run
  `20261005T101455-e0d5c870`), **truncated after its first load lot** (`MB01`, 25 cases,
  one factorisation, its `CALC_CHAMP`, `IMPR_RESU` and tables), then `FIN()`. Same mesh,
  same model, same solver settings; one factorisation of the production matrix instead
  of thirteen (the thirteen are identical in size: CA-055). A full production run takes
  30 to 50 minutes with one thread and several times more with 12 threads; fifteen of
  them would have kept the machine for a day. Declared as such in the report.

The only change to `DEBUT` is `MESURE_TEMPS=_F(NIVE_DETAIL=2)` (U4.11.01, « Mot-clé
MESURE_TEMPS », « Opérande NIVE_DETAIL »): the listing then prints, after each command,
the elapsed time of « #1.3 Factorisation numerique (ou precond.) » apart from the rest of
« #1 Resolution des systemes lineaires » and « #2 Calculs elementaires et assemblages ».

The repetitions are interleaved (all points of repetition 1, then of repetition 2...),
so that a slow drift of the machine load does not fall on a single point. Every run
must give the same numbers as the first one-thread run of its size: all the values of
its `IMPR_TABLE` (format `E20.12`) are compared.

Sub-commands:

- `preparer` writes `resultats/lot49/perf/<taille>_t<NN>_r<k>/` (`.comm`, `.export`,
  `.mmed`, `.connaissances.yaml`);
- `lancer [<nom> ...]` runs them one after the other (all of them, in the interleaved
  order, without argument; a run already measured is skipped);
- `analyser` writes `resultats/lot49/perf/mesures.json` (durations, profile, factorisation
  share, speed-up on the median one-thread time, differences of the tables).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/performances_lot49.py preparer
"""

from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.execution.profil import read_profile

RUNS = ROOT / "data/processed/runs"
SOURCES: dict[str, tuple[Path, str, int]] = {
    # size: (reference run, stem, memory_limit in Mio)
    "n3": (RUNS / "20261006T125858-33203f20", "n3_sh_h0p250", 2048),
    "prod": (RUNS / "20261005T101455-e0d5c870", "estacade_pieux_01", 8192),
}
THREADS = (1, 4, 8, 12, 14)
REPETITIONS = 3
TIME_LIMIT = 7200
TRUNCATE_BEFORE = "MB02 = MACRO_ELAS_MULT("
"""`prod`: the `.comm` is cut before the second load lot."""
DEBUT_ORIGINAL = 'DEBUT(CODE="OUI")'
DEBUT_MEASURED = 'DEBUT(CODE="OUI", MESURE_TEMPS=_F(NIVE_DETAIL=2))'
GROUPS: dict[str, tuple[str, ...]] = {
    "MACRO_ELAS_MULT": ("MACRO_ELAS_MULT",),
    "CALC_CHAMP": ("CALC_CHAMP",),
    "IMPR_RESU": ("IMPR_RESU",),
    "DEFI_GROUP": ("DEFI_GROUP",),
}
_NUMBER = re.compile(r"^-?\d\.\d{12}E[+-]\d{2}$")
_TIMER = re.compile(
    r"^#(?P<id>[0-9.]+)\s+(?P<label>.+?)\s+CPU \(USER\+SYST/SYST/ELAPS\)\s*:"
    r"\s*(?P<cpu>[0-9.]+)\s+(?P<sys>[0-9.]+)\s+(?P<elapsed>[0-9.]+)\s*$"
)


def _perf_dir() -> Path:
    """Fixed path: the campaign runs for hours and must not reload `projet.yaml` (an
    edit of the declaration during the campaign stopped it once)."""
    return ROOT / "projets/estacade_pieux_01/resultats/lot49/perf"


def _name(size: str, threads: int, repetition: int) -> str:
    return f"{size}_t{threads:02d}_r{repetition}"


def _order() -> list[tuple[str, str, int, int]]:
    """Interleaved order: repetition, then size, then threads."""
    return [
        (_name(size, threads, rep), size, threads, rep)
        for rep in range(1, REPETITIONS + 1)
        for size in SOURCES
        for threads in THREADS
    ]


def _comm_text(size: str) -> str:
    run, stem, _ = SOURCES[size]
    text = (run / f"{stem}.comm").read_text(encoding="utf-8")
    if text.count(DEBUT_ORIGINAL) != 1:
        message = f"{size} : DEBUT attendu une fois tel quel ({DEBUT_ORIGINAL})"
        raise SystemExit(message)
    text = text.replace(DEBUT_ORIGINAL, DEBUT_MEASURED)
    if size == "prod":
        cut = text.index(TRUNCATE_BEFORE)
        text = (
            text[:cut]
            + "# Lot 49 (mesures) : .comm de production coupé après le premier lot.\n"
            + "FIN()\n"
        )
    return text


def preparer() -> None:
    for name, size, threads, _rep in _order():
        run, stem, memory = SOURCES[size]
        out = _perf_dir() / name
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{name}.comm").write_text(_comm_text(size), encoding="utf-8")
        shutil.copyfile(run / f"{stem}.mmed", out / f"{name}.mmed")
        shutil.copyfile(
            run / f"{stem}.connaissances.yaml", out / f"{name}.connaissances.yaml"
        )
        (out / f"{name}.export").write_text(
            f"P time_limit {TIME_LIMIT}\nP memory_limit {memory}\n"
            f"P ncpus {threads}\nP mpi_nbcpu 1\nP mpi_nbnoeud 1\n"
            f"F comm {name}.comm D 1\nF mmed {name}.mmed D 20\n",
            encoding="utf-8",
        )
    print(f"{len(_order())} exécutions préparées dans {_perf_dir()}")


def _run_one(name: str) -> None:
    record_path = _perf_dir() / name / "execution.json"
    if record_path.is_file():
        print(f"{name} : déjà mesurée, ignorée", flush=True)
        return
    comm = _perf_dir() / name / f"{name}.comm"
    argv = [str(ROOT / ".venv/bin/aster-expert"), "run", str(comm)]
    print("lancement :", " ".join(argv), flush=True)
    started = time.monotonic()
    begun = time.strftime("%Y-%m-%dT%H:%M:%S")
    completed = subprocess.run(  # noqa: S603 - fixed argv
        argv, cwd=ROOT, capture_output=True, text=True, check=False
    )
    wall = time.monotonic() - started
    output = completed.stdout + completed.stderr
    match = re.search(r"data/processed/runs/(\d{8}T\d{6}-[0-9a-f]{8})", output)
    record = {
        "name": name,
        "started_at": begun,
        "return_code": completed.returncode,
        "wall_s": wall,
        "run": match.group(1) if match else None,
        "output": output[-4000:],
    }
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{name} : code {completed.returncode}, {wall:.1f} s, {record['run']}")


def lancer(names: list[str]) -> None:
    for name in names or [n for n, *_ in _order()]:
        _run_one(name)


def _mess(run: Path) -> Path:
    candidates = sorted(run.rglob("fort.6"))
    if not candidates:
        message = f"{run} : pas de fort.6"
        raise SystemExit(message)
    return candidates[0]


def _table_numbers(mess: Path) -> list[float]:
    values: list[float] = []
    for line in mess.read_text(encoding="utf-8", errors="replace").splitlines():
        values += [float(w) for w in line.split() if _NUMBER.match(w)]
    return values


def _difference(values: list[float], reference: list[float]) -> dict[str, Any]:
    if len(values) != len(reference):
        return {"comparable": False, "n": len(values), "n_reference": len(reference)}
    scale = max((abs(v) for v in reference), default=1.0) or 1.0
    absolute = max(
        (abs(a - b) for a, b in zip(values, reference, strict=True)), default=0.0
    )
    return {
        "comparable": True,
        "n": len(values),
        "identiques": values == reference,
        "ecart_absolu_max_rapporte_a_la_plus_grande_valeur": absolute / scale,
    }


def _solver_timers(mess: Path) -> dict[str, float]:
    """Elapsed time summed over the run, by timer of `MESURE_TEMPS` (#1, #1.3, #2...)."""
    sums: dict[str, float] = {}
    labels: dict[str, str] = {}
    for line in mess.read_text(encoding="utf-8", errors="replace").splitlines():
        found = _TIMER.match(line.strip())
        if found:
            key = found["id"].rstrip(".")
            sums[key] = sums.get(key, 0.0) + float(found["elapsed"])
            labels[key] = " ".join(found["label"].split())
    return {f"#{k} {labels[k]}": v for k, v in sorted(sums.items())}


def analyser() -> None:
    result: dict[str, Any] = {"tailles": {}, "executions": {}}
    references: dict[str, list[float]] = {}
    for name, size, threads, rep in _order():
        path = _perf_dir() / name / "execution.json"
        if not path.is_file():
            continue
        record = json.loads(path.read_text("utf-8"))
        entry: dict[str, Any] = {
            "taille": size,
            "fils": threads,
            "repetition": rep,
            "run": record["run"],
            "debut": record["started_at"],
            "code_retour": record["return_code"],
        }
        if record["run"]:
            run = RUNS / record["run"]
            report = json.loads((run / "compte_rendu.json").read_text("utf-8"))
            entry["statut"] = report["report"]["status"]
            entry["duree_s"] = report["report"]["duration_s"]
            mess = _mess(run)
            profile = read_profile(mess)
            assert profile.total is not None
            entry["total_job_s"] = profile.total.elapsed
            entry["groupes_s"] = profile.grouped(GROUPS)
            timers = _solver_timers(mess)
            entry["minuteurs_s"] = timers
            facto = next((v for k, v in timers.items() if k.startswith("#1.3 ")), None)
            entry["factorisation_numerique_s"] = facto
            entry["part_factorisation"] = (
                facto / profile.total.elapsed if facto is not None else None
            )
            numbers = _table_numbers(mess)
            if size not in references and threads == 1 and rep == 1:
                references[size] = numbers
            if size in references:
                entry["tables"] = _difference(numbers, references[size])
        result["executions"][name] = entry
    for size in SOURCES:
        points: dict[str, Any] = {}
        base = None
        for threads in THREADS:
            runs = [
                e
                for e in result["executions"].values()
                if e["taille"] == size and e["fils"] == threads and "duree_s" in e
            ]
            if not runs:
                continue
            durations = [e["duree_s"] for e in runs]
            factos = [
                e["factorisation_numerique_s"]
                for e in runs
                if e["factorisation_numerique_s"] is not None
            ]
            shares = [
                e["part_factorisation"]
                for e in runs
                if e["part_factorisation"] is not None
            ]
            point = {
                "n": len(runs),
                "durees_s": durations,
                "mediane_s": statistics.median(durations),
                "min_s": min(durations),
                "max_s": max(durations),
                "factorisation_mediane_s": statistics.median(factos)
                if factos
                else None,
                "part_factorisation_mediane": (
                    statistics.median(shares) if shares else None
                ),
            }
            if threads == 1:
                base = point["mediane_s"]
            points[str(threads)] = point
        if base:
            for point in points.values():
                point["temps_relatif_t01_sur_tN"] = base / point["mediane_s"]
        result["tailles"][size] = points
    out = _perf_dir() / "mesures.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(out)


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    command, *rest = argv
    if command == "preparer":
        preparer()
    elif command == "lancer":
        lancer(rest)
    elif command == "analyser":
        analyser()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
