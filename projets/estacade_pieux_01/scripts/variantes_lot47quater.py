"""Lot 47 quater, step 1 -- the declared variants Q1 to Q4 (H1 plug, H2 deck at +1.50).

All on the DST basis (E13, variant (a)), production model with the positions of E18,
production slab mesh (0.05 m):

| Run | Cap beam | H1 mixed plug | H2 deck at +1.50 |
| --- | --- | --- | --- |
| q1 | 0.90 | yes | no |
| q2 | 0.90 | no | yes |
| q3 | 0.90 | yes | yes |
| q4 | 0.80 | yes | yes |

Sub-commands:

- `maillage` writes `maillage/params_h0p050_plan1p50.json` and
  `maillage/invariants_h0p050_plan1p50.yaml` (H2 mesh, from the data only, never read
  from a MED; a test replays them byte for byte);
- `generer q1=<med> ...` writes `resultats/lot47quater/<name>/<name>.{comm,export,mmed,
  connaissances.yaml,generation.json}`; the runs are made by `aster-expert run`;
- `controler q1=<run_dir> ...` checks Σ DZ of the tip reactions against the load of
  every position and the weight PP of the variant (steel, plug concrete, cap beam),
  writes `resultats/lot47quater/controles.json`;
- `comparer q1=<run_dir> ...` reads C1 to C13 (rules v2) and writes
  `resultats/lot47quater/lectures.json` and `verdict.json` (criterion of
  docs/essais_lot47quater.md § 3.4, written before the runs).

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/variantes_lot47quater.py maillage
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

import yaml

from aster_expert.projet.context import load_project
from estacade_pieux_01.charges_mobiles import all_cases, tr_axle_cases
from estacade_pieux_01.comparaison_v2 import ComparisonV2
from estacade_pieux_01.discretisation import JettyMesh
from estacade_pieux_01.donnees import ModelValues, model_values
from estacade_pieux_01.extensions import applied_loads, weights
from estacade_pieux_01.generation import CAP_HEIGHT_E19, Options, build_comm
from estacade_pieux_01.lecture import load_results, run_batches, run_med
from estacade_pieux_01.transcription import (
    DECK_LEVEL_H2,
    plug_concrete_weight,
    with_deck_level,
)

RUNS: dict[str, Options] = {
    "q1": Options(variant="dst", tr_axle=True, mixed_plug=True),
    "q2": Options(variant="dst", tr_axle=True, deck_level=DECK_LEVEL_H2),
    "q3": Options(
        variant="dst", tr_axle=True, mixed_plug=True, deck_level=DECK_LEVEL_H2
    ),
    "q4": Options(
        variant="dst_chevetre_0p80",
        tr_axle=True,
        mixed_plug=True,
        deck_level=DECK_LEVEL_H2,
    ),
}
BASE = {"q1": "S", "q2": "S", "q3": "S", "q4": "SH"}
"""Configuration of lot 47 ter with the same cap beam and slab (DST): the reference
of « en sortir » (§ 3.4)."""
THRESHOLD = 1.0e-6
MESH_LABEL_H2 = "h0p050_plan1p50"
TIME_LIMIT = 7200
MEMORY_LIMIT = 6144
"""Mio per MPI process: VmPeak of N1 4 325 Mo (lot 47 ter, one process)."""
HEADER = (
    "# Invariants du maillage de l'estacade, variante H2 du lot 47 quater (plan du\n"
    "# tablier à +1,50), taille 0,05 m : générés par\n"
    "# projets/estacade_pieux_01/scripts/variantes_lot47quater.py à partir des données,\n"
    "# avant toute exécution. Ne pas éditer.\n"
)


def values_of(name: str) -> ModelValues:
    ctx = load_project("estacade_pieux_01", ROOT)
    v = model_values(ctx)
    level = RUNS[name].deck_level
    return with_deck_level(v, level) if level is not None else v


def mesh_outputs() -> dict[Path, bytes]:
    ctx = load_project("estacade_pieux_01", ROOT)
    mesh = JettyMesh(with_deck_level(model_values(ctx), DECK_LEVEL_H2), 0.05)
    text = HEADER + yaml.safe_dump(
        mesh.invariants(), allow_unicode=True, sort_keys=False, width=100
    )
    folder = ctx.project_dir / "maillage"
    return {
        folder / f"invariants_{MESH_LABEL_H2}.yaml": text.encode(),
        folder / f"params_{MESH_LABEL_H2}.json": mesh.parameters_bytes(),
    }


def maillage() -> None:
    for path, data in mesh_outputs().items():
        path.write_bytes(data)
        print(path.relative_to(ROOT), len(data))


def _out(name: str) -> Path:
    ctx = load_project("estacade_pieux_01", ROOT)
    return ctx.results_dir / "lot47quater" / name


def export_text(name: str, ncpus: int, mpi: int) -> str:
    return (
        f"P time_limit {TIME_LIMIT}\nP memory_limit {MEMORY_LIMIT}\n"
        f"P ncpus {ncpus}\nP mpi_nbcpu {mpi}\nP mpi_nbnoeud 1\n"
        f"F comm {name}.comm D 1\nF mmed {name}.mmed D 20\n"
    )


def generer(meds: dict[str, Path], ncpus: int = 1, mpi: int = 1) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    knowledge = (ctx.project_dir / "connaissances_appliquees.yaml").read_text("utf-8")
    for name, med in meds.items():
        out = _out(name)
        out.mkdir(parents=True, exist_ok=True)
        text, report = build_comm(ctx, mesh_label=med.name, options=RUNS[name])
        (out / f"{name}.comm").write_text(text, encoding="utf-8")
        (out / f"{name}.generation.json").write_text(
            json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        shutil.copyfile(med, out / f"{name}.mmed")
        (out / f"{name}.connaissances.yaml").write_text(knowledge, encoding="utf-8")
        (out / f"{name}.export").write_text(
            export_text(name, ncpus, mpi), encoding="utf-8"
        )
        print(out / f"{name}.comm", report["comm_sha256"])
        print(
            f"  exécution : .venv/bin/aster-expert run {(out / f'{name}.comm').relative_to(ROOT)}"
        )


def expected_pp(name: str) -> float:
    """N, weight of the variant: slab, cap beams (E2 or E19), steel of the piles from
    the deck node to the tip, plug concrete (H1)."""
    v = values_of(name)
    w = weights(v)
    caps = w["chevetres_n"]
    if RUNS[name].variant == "dst_chevetre_0p80":
        caps *= CAP_HEIGHT_E19 / v.cap_height
    concrete = plug_concrete_weight(v) if RUNS[name].mixed_plug else 0.0
    return w["dalle_n"] + caps + w["pieux_n"] + concrete


def _tables(text: str, lots: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    from aster_expert.controles.tables import TableIndex  # noqa: PLC0415

    index = TableIndex(text)
    out: dict[str, dict[str, float]] = {}
    for lot in lots:
        for record in index.find(f"RPIEDS_{lot['resultat']}"):
            case = str(record["_head"]).split()[-1]
            out[case] = {c: float(record[c]) for c in ("DX", "DY", "DZ")}
    return out


def _mess(run: Path) -> Path:
    found = sorted(run.rglob("fort.6"))
    if not found:
        message = f"{run} : pas de fort.6"
        raise SystemExit(message)
    return found[0]


def controler(runs: dict[str, Path]) -> None:
    report: dict[str, Any] = {"seuil": THRESHOLD, "executions": {}}
    for name, run_dir in runs.items():
        v = values_of(name)
        expected = applied_loads(v)
        for axle_case in tr_axle_cases(v):
            expected[axle_case.name] = {"DX": 0.0, "DY": 0.0, "DZ": -axle_case.total}
        moving = {c.name for c in all_cases(v, 0.05)} | {
            c.name for c in tr_axle_cases(v)
        }
        pp = -expected_pp(name)
        text = _mess(run_dir).read_text("utf-8", errors="replace")
        gen = json.loads((_out(name) / f"{name}.generation.json").read_text("utf-8"))
        sums = _tables(text, gen["lots"])
        rows: dict[str, dict[str, Any]] = {}
        for case, r in sums.items():
            applied = pp if case == "PP" else expected[case]["DZ"]
            rows[case] = {
                "charge_dz_n": applied,
                "reaction_dz_n": r["DZ"],
                "ecart_relatif": (applied + r["DZ"]) / abs(applied)
                if applied
                else None,
            }
        wanted = moving | {"PP"}
        missing = sorted(wanted - set(rows))
        worst = max(
            (abs(float(rows[c]["ecart_relatif"])) for c in wanted & set(rows)),
            default=math.nan,
        )
        report["executions"][name] = {
            "execution": str(run_dir.resolve().relative_to(ROOT)),
            "positions_controlees": len(wanted & set(rows)) - 1,
            "pp_attendu_n": -pp,
            "pp_obtenu_n": rows["PP"]["reaction_dz_n"] if "PP" in rows else None,
            "ecart_pp": rows["PP"]["ecart_relatif"] if "PP" in rows else None,
            "manquants": missing,
            "ecart_relatif_max": worst,
            "verdict": "RÉUSSI" if not missing and worst <= THRESHOLD else "ÉCHEC",
        }
        e = report["executions"][name]
        print(
            name, e["verdict"], e["positions_controlees"], f"{worst:.2e}", e["ecart_pp"]
        )
    path = ROOT / "projets/estacade_pieux_01/resultats/lot47quater/controles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(path)


def configuration(name: str, run: Path) -> ComparisonV2:
    v = values_of(name)
    gen = json.loads((_out(name) / f"{name}.generation.json").read_text("utf-8"))
    results = load_results(run_med(run), run_batches(gen))
    tr = [n for n, p in gen["positions"].items() if p["modele"] == "TR"]
    positions = {n: p for n, p in gen["positions"].items() if p["modele"] != "TR"}
    return ComparisonV2(v, results, positions, tr)


CRITERION_LINES = (
    ("C3", "ELS_f (111)"),
    ("C3", "ELS_c (111)"),
    ("C3", "ELU (111)"),
    ("C5", "ELU (111)"),
)
"""Lines that H1, H2 or both must bring within 5 % (§ 3.4)."""
GUARD_LINES = (
    ("C2", "ELS_f (112)"),
    ("C2", "ELS_c (112)"),
    ("C2", "ELU (112)"),
    ("C4", "ELU (114)"),
    ("C6", "ELS_f (105), barre seule"),
    ("C6", "ELS_c (105), barre seule"),
    ("C6", "ELU (112), barre seule"),
    ("C7", "ELU (enveloppe 100-115), barre seule"),
    ("C8", "ELU (105, 112), barre seule, toutes lignes"),
)
"""Lines that must not leave their tolerance (§ 3.4)."""
TOLERANCE = {
    "C2": 0.03,
    "C3": 0.05,
    "C4": 0.05,
    "C5": 0.05,
    "C6": 0.05,
    "C7": 0.05,
    "C8": 0.05,
}


def _index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    import re  # noqa: PLC0415

    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        key = re.sub(r"[ ,;]+gouvernée par \d+", "", r["colonne"]).replace(
            ", information", ""
        )
        out.setdefault((r["point"], key), r)
    return out


def _within(row: dict[str, Any] | None, point: str) -> bool | None:
    if row is None or row.get("ecart_relatif") is None:
        return None
    return abs(float(row["ecart_relatif"])) <= TOLERANCE[point] + 1e-12


def verdict(lectures: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The criterion of § 3.4, applied to every run read, against its base (S or SH)."""
    previous = json.loads(
        (ROOT / "projets/estacade_pieux_01/resultats/lot47ter/lectures.json").read_text(
            "utf-8"
        )
    )
    out: dict[str, Any] = {}
    for name, rows in lectures.items():
        idx = _index(rows)
        base = _index(previous[BASE[name]])
        lines: list[dict[str, Any]] = []
        for role, keys in (("objectif", CRITERION_LINES), ("garde", GUARD_LINES)):
            for point, label in keys:
                row = idx.get((point, label))
                ref = base.get((point, label))
                lines.append(
                    {
                        "role": role,
                        "point": point,
                        "ligne": label,
                        "valeur": None if row is None else row["code_aster"],
                        "source": None if row is None else row["source"],
                        "ecart": None if row is None else row["ecart_relatif"],
                        "dans_tolerance": _within(row, point),
                        "base": BASE[name],
                        "ecart_base": None if ref is None else ref["ecart_relatif"],
                        "base_dans_tolerance": _within(ref, point),
                    }
                )
        objectives = [x for x in lines if x["role"] == "objectif"]
        guards = [x for x in lines if x["role"] == "garde"]
        reached = all(x["dans_tolerance"] for x in objectives)
        left = [
            f"{x['point']} {x['ligne']}"
            for x in guards
            if x["base_dans_tolerance"] and not x["dans_tolerance"]
        ]
        strict = [
            f"{x['point']} {x['ligne']}" for x in guards if not x["dans_tolerance"]
        ]
        out[name] = {
            "lignes": lines,
            "objectif_atteint": reached,
            "gardes_sorties_par_rapport_a_la_base": left,
            "gardes_hors_tolerance_lecture_stricte": strict,
            "explique": reached and not left,
            "explique_lecture_stricte": reached and not strict,
        }
    return out


def comparer(runs: dict[str, Path]) -> None:
    folder = ROOT / "projets/estacade_pieux_01/resultats/lot47quater"
    path = folder / "lectures.json"
    out: dict[str, Any] = json.loads(path.read_text("utf-8")) if path.is_file() else {}
    for name, run in runs.items():
        out[name] = configuration(name, run).all_points()
        print(name, len(out[name]), "lignes")
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    result = verdict(out)
    (folder / "verdict.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    for name, r in result.items():
        print(
            name,
            "expliqué" if r["explique"] else "non expliqué",
            r["gardes_sorties_par_rapport_a_la_base"],
        )


def _pairs(args: list[str]) -> dict[str, Path]:
    out = {}
    for item in args:
        name, _, path = item.partition("=")
        if name not in RUNS or not path:
            raise SystemExit(f"attendu q1=<chemin>, lu {item!r}")
        out[name] = Path(path)
    return out


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    command, *rest = argv
    if command == "maillage":
        maillage()
    elif command == "generer":
        options = [a for a in rest if a.startswith("--")]
        pairs = _pairs([a for a in rest if not a.startswith("--")])
        ncpus = next(
            (int(a.split("=")[1]) for a in options if a.startswith("--ncpus=")), 1
        )
        mpi = next((int(a.split("=")[1]) for a in options if a.startswith("--mpi=")), 1)
        generer(pairs, ncpus, mpi)
    elif command == "controler":
        controler(_pairs(rest))
    elif command == "comparer":
        comparer(_pairs(rest))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
