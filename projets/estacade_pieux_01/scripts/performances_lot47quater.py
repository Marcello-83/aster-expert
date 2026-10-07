"""Lot 47 quater, step 0 -- speed-up of a mid-size run (slab mesh of 0.25 m, case N3).

The `.comm` of N3 (lot 47 ter, `data/processed/runs/20261006T125858-33203f20`, 246.5 s
with one thread) is run again, unchanged, with other resources in its `.export`:

- `t01`, `t04`, `t08`, `t12`: 1, 4, 8, 12 OpenMP threads (`P ncpus`), one MPI process;
- `m02`, `m04`: 2 and 4 MPI processes (`P mpi_nbcpu`), one thread each;
- `m04t3`: 4 MPI processes × 3 threads (12 cores, U2.08.06: mix MPI and OpenMP);
- `m04pt`: as `m04`, with `PARALLELISME_TEMPS='OUI'` on the `CALC_CHAMP` of `EFGE_NOEU`
  and `REAC_NODA` (U4.81.04, « Performance des calculs »): the only variant whose
  `.comm` differs;
- `c1`, `c2`: two independent runs of the same `.export`, started together.

`memory_limit` is 2 048 Mio per process (VmPeak of N3: 934 Mo). Every variant must give
the same numbers as N3: all the values of its `IMPR_TABLE` (format `E20.12`) are
compared with those of N3 (largest relative difference, by table value).

Sub-commands:

- `preparer` writes `resultats/lot47quater/perf/<name>/` (`.comm`, `.export`, `.mmed`,
  `.connaissances.yaml`);
- `lancer <name> ...` runs them one after the other with `aster-expert run` and writes
  `resultats/lot47quater/perf/<name>/execution.json` (run directory, wall time);
- `lancer-ensemble <name> <name>` starts two runs at the same time;
- `analyser` writes `resultats/lot47quater/perf/mesures.json` (profile by group of
  commands, speed-up, differences to N3).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/performances_lot47quater.py preparer
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.execution.profil import read_profile
from aster_expert.projet.context import load_project

REFERENCE_RUN = ROOT / "data/processed/runs/20261006T125858-33203f20"
STEM = "n3_sh_h0p250"
# name: (ncpus, mpi_nbcpu, PARALLELISME_TEMPS)
VARIANTS: dict[str, tuple[int, int, bool]] = {
    "t01": (1, 1, False),
    "t04": (4, 1, False),
    "t08": (8, 1, False),
    "t12": (12, 1, False),
    "m02": (1, 2, False),
    "m04": (1, 4, False),
    "m04t3": (3, 4, False),
    "m04pt": (1, 4, True),
    "c1": (1, 1, False),
    "c2": (1, 1, False),
    "t01b": (1, 1, False),
    "m04t3b": (3, 4, False),
}
"""`t01b` (lot 47 quater, second day): `t01` again, as the base of the runs made the day
after (`m02` again, `m04pt`, `c1`, `c2`), the machine load having changed (desktop
session using about 1.25 core). `m04t3b`: replay of the hang of `m04t3` with a short
time limit (`TIME_LIMIT_OF`)."""
TIME_LIMIT_OF = {"m04t3b": 300}
MEMORY_LIMIT = 2048
TIME_LIMIT = 7200
GROUPS: dict[str, tuple[str, ...]] = {
    "lecture du maillage": ("LIRE_MAILLAGE",),
    "assemblage et factorisation (MACRO_ELAS_MULT)": ("MACRO_ELAS_MULT",),
    "CALC_CHAMP": ("CALC_CHAMP",),
    "IMPR_RESU": ("IMPR_RESU",),
}
_NUMBER = re.compile(r"^-?\d\.\d{12}E[+-]\d{2}$")
_PT_TARGETS = ('CONTRAINTE=("EFGE_NOEU",))', 'FORCE=("REAC_NODA",))')


def _perf_dir() -> Path:
    ctx = load_project("estacade_pieux_01", ROOT)
    return ctx.results_dir / "lot47quater" / "perf"


def _with_time_parallelism(text: str) -> str:
    """Add PARALLELISME_TEMPS='OUI' to the CALC_CHAMP of EFGE_NOEU and REAC_NODA."""
    count = 0
    for target in _PT_TARGETS:
        count += text.count(target)
        text = text.replace(target, target[:-1] + ', PARALLELISME_TEMPS="OUI")')
    if count == 0:
        message = "aucun CALC_CHAMP EFGE_NOEU/REAC_NODA trouvé"
        raise SystemExit(message)
    return text


def preparer() -> None:
    for name, (ncpus, mpi, pt) in VARIANTS.items():
        out = _perf_dir() / name
        out.mkdir(parents=True, exist_ok=True)
        text = (REFERENCE_RUN / f"{STEM}.comm").read_text(encoding="utf-8")
        (out / f"{name}.comm").write_text(
            _with_time_parallelism(text) if pt else text, encoding="utf-8"
        )
        shutil.copyfile(REFERENCE_RUN / f"{STEM}.mmed", out / f"{name}.mmed")
        shutil.copyfile(
            REFERENCE_RUN / f"{STEM}.connaissances.yaml",
            out / f"{name}.connaissances.yaml",
        )
        limit = TIME_LIMIT_OF.get(name, TIME_LIMIT)
        (out / f"{name}.export").write_text(
            f"P time_limit {limit}\nP memory_limit {MEMORY_LIMIT}\n"
            f"P ncpus {ncpus}\nP mpi_nbcpu {mpi}\nP mpi_nbnoeud 1\n"
            f"F comm {name}.comm D 1\nF mmed {name}.mmed D 20\n",
            encoding="utf-8",
        )
        print(f"{name} : ncpus {ncpus}, mpi_nbcpu {mpi}, PARALLELISME_TEMPS {pt}")


def _start(name: str) -> tuple[subprocess.Popen[str], float]:
    comm = _perf_dir() / name / f"{name}.comm"
    argv = [str(ROOT / ".venv/bin/aster-expert"), "run", str(comm)]
    print("lancement :", " ".join(argv), flush=True)
    process = subprocess.Popen(  # noqa: S603 - fixed argv
        argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    return process, time.monotonic()


def _finish(name: str, process: subprocess.Popen[str], started: float) -> None:
    output, _ = process.communicate()
    wall = time.monotonic() - started
    match = re.search(r"data/processed/runs/(\d{8}T\d{6}-[0-9a-f]{8})", output)
    record = {
        "variant": name,
        "resources": VARIANTS[name],
        "return_code": process.returncode,
        "wall_s": wall,
        "run": match.group(1) if match else None,
        "output": output[-4000:],
    }
    (_perf_dir() / name / "execution.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{name} : code {process.returncode}, {wall:.1f} s, {record['run']}")


def lancer(names: list[str]) -> None:
    for name in names:
        process, started = _start(name)
        _finish(name, process, started)


def lancer_ensemble(names: list[str]) -> None:
    started = [(_start(name), name) for name in names]
    for (process, t0), name in started:
        _finish(name, process, t0)


def _mess(run: Path) -> Path:
    candidates = sorted(run.rglob("fort.6"))
    if not candidates:
        message = f"{run} : pas de fort.6"
        raise SystemExit(message)
    return candidates[0]


def _table_numbers(mess: Path) -> list[float]:
    values: list[float] = []
    # Every number written with 12 decimals (FORMAT_R="E20.12"): only the IMPR_TABLE of
    # the run print that format.
    for line in mess.read_text(encoding="utf-8", errors="replace").splitlines():
        values += [float(w) for w in line.split() if _NUMBER.match(w)]
    return values


def _difference(values: list[float], reference: list[float]) -> dict[str, Any]:
    if len(values) != len(reference):
        return {"comparable": False, "n": len(values), "n_reference": len(reference)}
    scale = max(abs(v) for v in reference) or 1.0
    worst = max(
        (
            abs(a - b) / max(abs(b), 1e-12 * scale)
            for a, b in zip(values, reference, strict=True)
        ),
        default=0.0,
    )
    absolute = max(
        (abs(a - b) for a, b in zip(values, reference, strict=True)), default=0.0
    )
    return {
        "comparable": True,
        "n": len(values),
        "ecart_relatif_max": worst,
        "ecart_absolu_max": absolute,
        "ecart_absolu_max_rapporte_a_la_plus_grande_valeur": absolute / scale,
    }


def _profile(run: Path) -> dict[str, Any]:
    profile = read_profile(_mess(run))
    assert profile.total is not None
    groups = profile.grouped(GROUPS)
    return {
        "total_elapsed_s": profile.total.elapsed,
        "total_user_sys_s": profile.total.user_sys,
        "groupes_s": groups,
        "groupes_part": {k: v / profile.total.elapsed for k, v in groups.items()},
    }


def analyser() -> None:
    reference_numbers = _table_numbers(_mess(REFERENCE_RUN))
    result: dict[str, Any] = {
        "reference": {
            "run": REFERENCE_RUN.name,
            "profil": _profile(REFERENCE_RUN),
            "duree_compte_rendu_s": json.loads(
                (REFERENCE_RUN / "compte_rendu.json").read_text("utf-8")
            )["report"]["duration_s"],
            "valeurs_comparees": len(reference_numbers),
        },
        "variantes": {},
    }
    base = None
    for name in VARIANTS:
        path = _perf_dir() / name / "execution.json"
        if not path.is_file():
            continue
        record = json.loads(path.read_text("utf-8"))
        entry: dict[str, Any] = {
            "ncpus": record["resources"][0],
            "mpi_nbcpu": record["resources"][1],
            "parallelisme_temps": record["resources"][2],
            "run": record["run"],
            "code_retour": record["return_code"],
            "duree_murale_s": record["wall_s"],
        }
        if record["run"]:
            run = ROOT / "data/processed/runs" / record["run"]
            report = json.loads((run / "compte_rendu.json").read_text("utf-8"))
            entry["statut"] = report["report"]["status"]
            entry["duree_compte_rendu_s"] = report["report"]["duration_s"]
            entry["ressources"] = report.get("resources")
            try:
                entry["profil"] = _profile(run)
                entry["ecart_aux_tables_de_n3"] = _difference(
                    _table_numbers(_mess(run)), reference_numbers
                )
            except (SystemExit, ValueError) as exc:
                entry["profil"] = None
                entry["erreur_lecture"] = str(exc)
        if name == "t01":
            base = entry.get("duree_compte_rendu_s")
        if name == "t01b":
            entry["base_du_second_jour"] = True
        result["variantes"][name] = entry
    if base:
        for entry in result["variantes"].values():
            if entry.get("duree_compte_rendu_s"):
                entry["acceleration_sur_t01"] = base / entry["duree_compte_rendu_s"]
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
    elif command == "lancer-ensemble":
        lancer_ensemble(rest)
    elif command == "analyser":
        analyser()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
