"""Lot 47 ter -- the four runs of docs/essais_lot47ter.md (criteria committed before).

- `n1_sh` : variant SH (DST slab, cap beam of 0.80 m), whole production model with the
  positions of E18, production mesh (0.05 m);
- `n2_s_tre` : the 57 positions of the sidewalk axle of E18 on the variant S (DST,
  0.90 m), production mesh;
- `n3_sh_h0p250`, `n4_sh_h0p500` : variant SH on the coarse slab meshes, prints by
  fractions of cells.

Sub-commands:

- `generer <name>=<med> ...` writes `resultats/lot47ter/<name>/<name>.{comm,export,
  mmed,connaissances.yaml,generation.json}`; the runs are made by `aster-expert run`;
- `controler <name>=<run_dir> ...` checks Σ DZ of the tip reactions against the load of
  every position and of PP (§ 2.3, § 3.3) and writes `resultats/lot47ter/controles.json`;
- `comparer <run_N1> <run_N2> <run_N3> <run_N4>` reads C1 to C13 (rules v2) for the four
  configurations R, S, H, SH and on the three meshes of SH, and writes
  `resultats/lot47ter/plan_factoriel.json` and `maillages.json`.

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/executions_lot47ter.py generer n1_sh=<med> ...
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

from aster_expert.projet.context import load_project
from estacade_pieux_01.charges_mobiles import all_cases, tr_axle_cases
from estacade_pieux_01.comparaison_v2 import ComparisonV2, merge
from estacade_pieux_01.donnees import model_values
from estacade_pieux_01.extensions import applied_loads, weights
from estacade_pieux_01.generation import CAP_HEIGHT_E19, Options, build_comm
from estacade_pieux_01.lecture import load_results, run_batches, run_med

RUNS = {
    "n1_sh": Options(variant="dst_chevetre_0p80", tr_axle=True),
    "n2_s_tre": Options(mode="tr_essieu", variant="dst"),
    "n3_sh_h0p250": Options(variant="dst_chevetre_0p80", tr_axle=True, mesh_size=0.25),
    "n4_sh_h0p500": Options(variant="dst_chevetre_0p80", tr_axle=True, mesh_size=0.5),
}
THRESHOLD = 1.0e-6
EXISTING = {
    "R": ("data/processed/runs/20261005T101455-e0d5c870", "resultats/generation.json"),
    "R_tre": (
        "data/processed/runs/20261005T150307-187df570",
        "resultats/lot47bis/tr_essieu/tr_essieu.generation.json",
    ),
    "S": (
        "data/processed/runs/20261005T104915-1d558927",
        "resultats/variantes/dst/var_dst.generation.json",
    ),
    "H": (
        "data/processed/runs/20261005T150840-65219726",
        "resultats/lot47bis/chevetre_0p80/chevetre_0p80.generation.json",
    ),
}
KNOWLEDGE_EXTRA = """  - id: ENV-002
    how: "serveur MCP : schéma de la base rechargé quand ses sources changent (lot 47 ter)"
"""


def _out(name: str) -> Path:
    ctx = load_project("estacade_pieux_01", ROOT)
    return ctx.results_dir / "lot47ter" / name


def generer(meds: dict[str, Path]) -> None:
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
            "P time_limit 7200\nP memory_limit 10240\nP ncpus 1\nP mpi_nbcpu 1\n"
            f"P mpi_nbnoeud 1\nF comm {name}.comm D 1\nF mmed {name}.mmed D 20\n",
            encoding="utf-8",
        )
        print(out / f"{name}.comm", report["comm_sha256"])
        # DIAG-025: the limits of the .export are not read by `aster-expert run`.
        print(
            "  exécution : .venv/bin/aster-expert run --timeout 7200 --memory-mb 10240 "
            f"{(out / f'{name}.comm').relative_to(ROOT)}"
        )


def _tables(text: str, lots: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Σ DX, DY, DZ of the tip reactions per case, from the RPIEDS_<batch> tables."""
    from aster_expert.controles.tables import TableIndex  # noqa: PLC0415

    index = TableIndex(text)
    out: dict[str, dict[str, float]] = {}
    for lot in lots:
        for record in index.find(f"RPIEDS_{lot['resultat']}"):
            name = str(record["_head"]).split()[-1]
            out[name] = {c: float(record[c]) for c in ("DX", "DY", "DZ")}
    return out


def controler(runs: dict[str, Path]) -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    v = model_values(ctx)
    expected = applied_loads(v)
    for axle_case in tr_axle_cases(v):
        expected[axle_case.name] = {"DX": 0.0, "DY": 0.0, "DZ": -axle_case.total}
    w = weights(v)
    pp_e19 = -(
        w["dalle_n"] + w["chevetres_n"] * CAP_HEIGHT_E19 / v.cap_height + w["pieux_n"]
    )
    moving = {c.name for c in all_cases(v, 0.05)} | {c.name for c in tr_axle_cases(v)}
    report: dict[str, Any] = {"seuil": THRESHOLD, "executions": {}}
    for name, run_dir in runs.items():
        text = (run_dir / "proc.0" / "fort.6").read_text("utf-8", errors="replace")
        gen = json.loads((_out(name) / f"{name}.generation.json").read_text("utf-8"))
        sums = _tables(text, gen["lots"])
        rows: dict[str, dict[str, Any]] = {}
        for case, r in sums.items():
            applied = pp_e19 if case == "PP" else expected[case]["DZ"]
            rows[case] = {
                "charge_dz_n": applied,
                "reaction_dz_n": r["DZ"],
                "ecart_relatif": (applied + r["DZ"]) / abs(applied)
                if applied
                else None,
                "ecart_absolu_n": applied + r["DZ"],
            }
        wanted = (
            {c.name for c in tr_axle_cases(v)}
            if name == "n2_s_tre"
            else moving | {"PP"}
        )
        missing = sorted(wanted - set(rows))
        worst = max(
            (abs(float(rows[c]["ecart_relatif"])) for c in wanted & set(rows)),
            default=math.nan,
        )
        report["executions"][name] = {
            "execution": str(run_dir.resolve().relative_to(ROOT)),
            "positions_controlees": len(wanted & set(rows))
            - (1 if "PP" in wanted else 0),
            "pp_attendu_n": -pp_e19 if "PP" in wanted else None,
            "pp_obtenu_n": rows["PP"]["reaction_dz_n"] if "PP" in rows else None,
            "ecart_pp": rows["PP"]["ecart_relatif"] if "PP" in rows else None,
            "manquants": missing,
            "ecart_relatif_max": worst,
            "verdict": "RÉUSSI" if not missing and worst <= THRESHOLD else "ÉCHEC",
            "cas": rows,
        }
        e = report["executions"][name]
        print(
            name, e["verdict"], e["positions_controlees"], f"{worst:.2e}", e["ecart_pp"]
        )
    path = _out("controles.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(path)


def _load(run: str | Path, generation: str | Path) -> Any:
    ctx = load_project("estacade_pieux_01", ROOT)
    gen_path = Path(generation)
    if not gen_path.is_absolute():
        gen_path = ctx.project_dir / gen_path
    gen = json.loads(gen_path.read_text("utf-8"))
    run_path = Path(run) if Path(run).is_absolute() else ROOT / run
    return load_results(run_med(run_path), run_batches(gen)), gen


def configuration(name: str, runs: dict[str, Path]) -> ComparisonV2:
    """The comparison v2 of one configuration of the factorial plan, or of SH on a
    coarse mesh (`SH_h0p250`, `SH_h0p500`)."""
    ctx = load_project("estacade_pieux_01", ROOT)
    v = model_values(ctx)
    if name in ("R", "S"):
        base, gen = _load(*EXISTING[name])
        if name == "R":
            extra, gen_tr = _load(*EXISTING["R_tre"])
        else:
            extra, gen_tr = _load(
                runs["n2_s_tre"], _out("n2_s_tre") / "n2_s_tre.generation.json"
            )
        results = merge(base, extra)
        positions = dict(gen["positions"])
        tr = [c for lot in gen_tr["lots"] for c in lot["cas"]]
        return ComparisonV2(v, results, positions, tr)
    if name == "H":
        results, gen = _load(*EXISTING["H"])
    else:
        key = {"SH": "n1_sh", "SH_h0p250": "n3_sh_h0p250", "SH_h0p500": "n4_sh_h0p500"}[
            name
        ]
        results, gen = _load(runs[key], _out(key) / f"{key}.generation.json")
    tr = [n for n, p in gen["positions"].items() if p["modele"] == "TR"]
    positions = {n: p for n, p in gen["positions"].items() if p["modele"] != "TR"}
    return ComparisonV2(v, results, positions, tr)


ALL_CONFIGS = ("R", "S", "H", "SH", "SH_h0p250", "SH_h0p500")
NEEDS = {
    "S": "n2_s_tre",
    "SH": "n1_sh",
    "SH_h0p250": "n3_sh_h0p250",
    "SH_h0p500": "n4_sh_h0p500",
}


def comparer(runs: dict[str, Path]) -> None:
    """Read every configuration whose runs are given (R and H need none) and add it
    to `lectures.json`."""
    path = _out("lectures.json")
    out: dict[str, Any] = json.loads(path.read_text("utf-8")) if path.is_file() else {}
    for name in ALL_CONFIGS:
        if name in NEEDS and NEEDS[name] not in runs:
            continue
        if name not in NEEDS and name in out:
            continue
        cmp = configuration(name, runs)
        out[name] = cmp.all_points()
        print(name, len(out[name]), "lignes")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(path)


CONFIGS = ("R", "S", "H", "SH")
MESHES = {"0,05": "SH", "0,25": "SH_h0p250", "0,50": "SH_h0p500"}
HYPOTHESIS_LINES = (
    ("C2", "ELS_f (112)"),
    ("C2", "ELS_c (112)"),
    ("C2", "ELU (112)"),
    ("C3", "ELS_f (111)"),
    ("C3", "ELS_c (111)"),
    ("C3", "ELU (111)"),
    ("C4", "ELU (114)"),
    ("C5", "ELU (111)"),
    ("C6", "ELS_f (105), barre seule"),
    ("C6", "ELS_c (105), barre seule"),
    ("C6", "ELU (112), barre seule"),
    ("C7", "ELU (enveloppe 100-115), barre seule"),
    ("C8", "ELU (105, 112), barre seule, toutes lignes"),
)
"""The 13 lines of the criterion of docs/essais_lot47ter.md § 2.4."""
TOLERANCE_E12 = {
    "C2": 0.03,
    "C3": 0.05,
    "C4": 0.05,
    "C5": 0.05,
    "C6": 0.05,
    "C7": 0.05,
    "C8": 0.05,
    "C9": 0.10,
    "C12": 0.10,
    "C13": 0.10,
}
LOCAL_LINES = (
    ("C9", "ELS_f (111)"),
    ("C9", "ELS_c (111)"),
    ("C9", "ELU (111)"),
    ("C12", "ELU rive (100)"),
    ("C13", "LM1 Mxx inf."),
    ("C13", "LM1 Mxx sup."),
    ("C13", "LM1 V (|Qxx|)"),
    ("C13", "LM2 Mxx inf."),
    ("C13", "LM2 Mxx sup."),
    ("C13", "LM2 V (|Qxx|)"),
)
"""The lines of the step 2 (§ 3.4)."""


def label_key(label: str) -> str:
    """A column label without what depends on the run (governing combination) and
    without the « information » mark: the same key in every configuration."""
    import re  # noqa: PLC0415

    key = re.sub(r" ; gouvernée par \d+", "", label)
    key = re.sub(r", gouvernée par \d+", "", key)
    return key.replace(", information", "")


def _index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        out.setdefault((r["point"], label_key(r["colonne"])), r)
    return out


def _gap(value: float, source: float | None) -> float | None:
    if source is None or source == 0:
        return None
    return (value - source) / abs(source)


def analyser() -> None:
    lectures = json.loads(_out("lectures.json").read_text("utf-8"))
    idx = {name: _index(rows) for name, rows in lectures.items()}
    # Table 4 x (C1 to C13): every line of the reference, judged or for information.
    table = []
    for r in lectures["R"]:
        key = (r["point"], label_key(r["colonne"]))
        line: dict[str, Any] = {
            "point": key[0],
            "colonne": key[1],
            "source": r["source"],
            "tolerance": r["tolerance"],
            "juge": r["verdict"] != "—",
        }
        for c in CONFIGS:
            row = idx[c].get(key)
            value = None if row is None else row["code_aster"]
            line[c] = value
            line[f"ecart_{c}"] = (
                None
                if value is None
                else _gap(abs(value) if key[0] == "C7" else value, r["source"])
            )
            line[f"lieu_{c}"] = None if row is None else row["lieu"]
        vals = [line[c] for c in CONFIGS]
        if all(isinstance(x, (int, float)) for x in vals):
            r_, s_, h_, sh_ = vals
            base = abs(r_) if r_ else float("nan")
            line["effet_dst"] = ((s_ - r_) + (sh_ - h_)) / 2 / base
            line["effet_chevetre_0p80"] = ((h_ - r_) + (sh_ - s_)) / 2 / base
            line["interaction"] = ((sh_ - h_) - (s_ - r_)) / 2 / base
        table.append(line)

    # Criterion of § 2.4.
    def judged(config: str) -> list[dict[str, Any]]:
        out = []
        for point, col in HYPOTHESIS_LINES:
            row = idx[config][(point, col)]
            value = abs(row["code_aster"]) if point == "C7" else row["code_aster"]
            src = abs(row["source"]) if point == "C7" else row["source"]
            gap = _gap(value, src)
            assert gap is not None
            out.append(
                {
                    "point": point,
                    "colonne": col,
                    "code_aster": value,
                    "source": src,
                    "ecart_relatif": gap,
                    "tolerance": TOLERANCE_E12[point],
                    "dans_la_tolerance": abs(gap) <= TOLERANCE_E12[point],
                    "lieu": row["lieu"],
                }
            )
        return out

    crit = {c: judged(c) for c in CONFIGS}
    n_in = {c: sum(x["dans_la_tolerance"] for x in crit[c]) for c in CONFIGS}
    if n_in["SH"] == len(HYPOTHESIS_LINES):
        verdict = "confirmée"
    elif n_in["SH"] > n_in["R"]:
        verdict = "partielle"
    else:
        verdict = "réfutée"
    plan = {
        "statut": "contre-calcul d'un modèle non validé ; variantes déclarées, "
        "jamais la référence",
        "critere": "docs/essais_lot47ter.md § 2.4 (écrit avant l'exécution de N1)",
        "configurations": {
            "R": "DKT, chevêtre 0,90 m (référence)",
            "S": "DST, chevêtre 0,90 m",
            "H": "DKT, chevêtre 0,80 m (E19)",
            "SH": "DST, chevêtre 0,80 m",
        },
        "lignes_du_critere": crit,
        "lignes_dans_la_tolerance": n_in,
        "verdict_hypothese": verdict,
        "lignes_qui_resistent": [
            f"{x['point']} {x['colonne']} ({x['ecart_relatif']:+.1%})"
            for x in crit["SH"]
            if not x["dans_la_tolerance"]
        ],
        "tableau": table,
    }
    _out("plan_factoriel.json").write_text(
        json.dumps(plan, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    # Step 2: mesh dependence (§ 3.4).
    meshes = []
    for point, col in LOCAL_LINES:
        values = {h: idx[name][(point, col)] for h, name in MESHES.items()}
        src = values["0,05"]["source"]
        v05 = values["0,05"]["code_aster"]
        variation = max(
            abs(values[h]["code_aster"] - v05) / abs(v05) for h in ("0,25", "0,50")
        )
        joins = [
            h
            for h, r in values.items()
            if abs(_gap(r["code_aster"], src) or 0.0) <= TOLERANCE_E12[point]
        ]
        meshes.append(
            {
                "point": point,
                "colonne": col,
                "source": src,
                "valeurs": {h: r["code_aster"] for h, r in values.items()},
                "ecarts": {h: _gap(r["code_aster"], src) for h, r in values.items()},
                "lieux": {h: r["lieu"] for h, r in values.items()},
                "variation_max_relative": variation,
                "rejoint_la_source_a": joins,
                "comparabilite": "comparable"
                if variation <= 0.10
                else "non comparable sans le maillage source",
            }
        )
    _out("maillages.json").write_text(
        json.dumps(
            {
                "statut": "contre-calcul d'un modèle non validé ; configuration SH",
                "critere": "docs/essais_lot47ter.md § 3.4 (écrit avant les exécutions)",
                "lignes": meshes,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        "utf-8",
    )
    print("hypothèse :", verdict, n_in)
    for x in plan["lignes_qui_resistent"]:
        print("  résiste :", x)
    for m in meshes:
        print(
            m["point"],
            m["colonne"],
            {h: round(v, 1) for h, v in m["valeurs"].items()},
            f"{m['variation_max_relative']:.0%}",
            m["comparabilite"],
            m["rejoint_la_source_a"],
        )


def _pairs(args: list[str]) -> dict[str, Path]:
    return {a.split("=", 1)[0]: Path(a.split("=", 1)[1]) for a in args}


def main() -> None:
    command, *args = sys.argv[1:]
    if command == "generer":
        generer(_pairs(args))
    elif command == "controler":
        controler(_pairs(args))
    elif command == "comparer":
        comparer(_pairs(args))
    elif command == "analyser":
        analyser()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
