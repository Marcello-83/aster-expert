"""Lot 49, step 6 -- replay of the export of lot 47 with `aster-expert resultats lire`.

The eight files handed to the supervisor at lot 47 (`/media/sf_partage/echanges/lot47`)
were written by throw-away scripts. Each line of the five CSV files is asked again of
the query engine of the deliverables (`aster_expert.livrables.lecture.query`, the code
of `aster-expert resultats lire`), and each number compared at the number of decimals
of the original file (« à l'identique aux arrondis près »). Columns that are not a value
of the results but a derived quantity (moduli √(MFY² + MFZ²), integrals of the slab over
a band, sums of a reading) are listed as such, not compared. The `.comm` is compared by
its SHA-256, the two Markdown documents are not data exports.

Usage:
  .venv/bin/python projets/estacade_pieux_01/scripts/rejeu_export_lot47.py [<dossier>]
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.livrables.lecture import Answer, Query, query
from aster_expert.projet.context import ProjectContext, load_project

EXPORT = Path("/media/sf_partage/echanges/lot47")
CASE = {"TE+": "TEP", "TE-": "TEM"}
_COMB = re.compile(r"^(\d{3} (?:ELU[+-]|ELS_[fc]))(?=\s|$)")


def _decimals(text: str) -> int:
    return len(text.split(".")[1]) if "." in text else 0


def _same(value_si: float, factor: float, text: str) -> bool:
    """`value_si × factor` rounded to the decimals of `text` equals `text`."""
    if text in ("", "—"):
        return False
    expected = float(text)
    shown = round(value_si * factor, _decimals(text))
    return bool(abs(shown - expected) <= 0.5 * 10 ** (-_decimals(text)) + 1e-12)


def _case(row: dict[str, str], name_key: str = "cas_ou_combinaison") -> str:
    """The name `resultats lire` understands for a line of the export."""
    name = row[name_key]
    ts = row.get("TS", "—")
    if name.startswith("G = PP+G2"):
        return "expr:PP+G2"
    if name.startswith("TS seul"):
        return ts
    match = _COMB.match(name)
    if match:
        return f"{match.group(1)}@{ts}" if ts not in ("", "—") else match.group(1)
    return CASE.get(name, name)


class Cache:
    def __init__(self, ctx: ProjectContext) -> None:
        self.ctx = ctx
        self.data: dict[tuple[Any, ...], Answer] = {}

    def __call__(self, **kwargs: Any) -> Answer:
        key = tuple(
            sorted(
                (k, tuple(v) if isinstance(v, list | tuple) else v)
                for k, v in kwargs.items()
            )
        )
        if key not in self.data:
            self.data[key] = query(self.ctx, Query(**kwargs))
        return self.data[key]


def _index(answer: Answer) -> dict[tuple[int, Any, str], float]:
    """(MED node, MED cell or "", component) -> SI value."""
    return {
        (int(r["noeud_med"]), r.get("maille_med", ""), r["composante"]): float(
            r["valeur_si"]
        )
        for r in answer.rows
    }


def _compare(stats: dict[str, Any], label: str, ok: bool, detail: str) -> None:
    stats["valeurs"] += 1
    if not ok:
        stats["differentes"] += 1
        if len(stats["exemples"]) < 10:
            stats["exemples"].append(f"{label} : {detail}")


def _new_stats(
    columns: Sequence[str], derived: Sequence[str], note: str = ""
) -> dict[str, Any]:
    return {
        "colonnes_comparees": list(columns),
        "colonnes_derivees_non_comparees": list(derived),
        "valeurs": 0,
        "differentes": 0,
        "lignes": 0,
        "exemples": [],
        "note": note,
    }


BEAM = {
    "N_kN": ("N", 1e-3),
    "VY_kN": ("VY", 1e-3),
    "VZ_kN": ("VZ", 1e-3),
    "MT_kNm": ("MT", 1e-3),
    "MFY_kNm": ("MFY", 1e-3),
    "MFZ_kNm": ("MFZ", 1e-3),
    "MY_MFY_kNm": ("MFY", 1e-3),
    "MZ_MFZ_kNm": ("MFZ", 1e-3),
}


def tetes(ask: Cache, rows: list[dict[str, str]]) -> dict[str, Any]:
    cols = [c for c in BEAM if c in rows[0]]
    stats = _new_stats(
        cols,
        [
            "M_resultant_kNm",
            "V_resultant_kN",
            "info_TS_qui_maximise_M_resultant_pour_ce_pieu",
        ],
    )
    for row in rows:
        stats["lignes"] += 1
        found = _index(
            ask(
                groupes=("PIEUX",),
                noeuds="TETES",
                champ="EFGE_ELNO",
                cas=(_case(row),),
                mode="tout",
            )
        )
        for col in cols:
            comp, factor = BEAM[col]
            value = found.get(
                (int(row["noeud_med"]), int(row["maille_SEG2_med"]), comp)
            )
            ok = value is not None and _same(value, factor, row[col])
            _compare(
                stats,
                f"{row['pieu']} {row['cas_ou_combinaison']} {col}",
                ok,
                f"{value} vs {row[col]}",
            )
    return stats


def profils(ask: Cache, rows: list[dict[str, str]]) -> dict[str, Any]:
    cols = [c for c in BEAM if c in rows[0]]
    stats = _new_stats(
        [*cols, "F_ressort_X_kN", "F_ressort_Y_kN"],
        ["M_resultant_kNm", "V_resultant_kN", "k_kN_par_m"],
    )
    for row in rows:
        stats["lignes"] += 1
        group = f"PIEU_{row['pieu']}"
        case = _case(row)
        found = _index(
            ask(groupes=(group,), champ="EFGE_ELNO", cas=(case,), mode="tout")
        )
        for col in cols:
            comp, factor = BEAM[col]
            value = found.get(
                (int(row["noeud_med"]), int(row["maille_SEG2_med"]), comp)
            )
            ok = value is not None and _same(value, factor, row[col])
            _compare(
                stats,
                f"{row['pieu']} n{row['noeud_med']} {case} {col}",
                ok,
                f"{value} vs {row[col]}",
            )
        if row.get("F_ressort_X_kN"):
            springs = ask(groupes=(group,), champ="SIEF_ELGA", cas=(case,), mode="tout")
            at = {
                r["composante"]: float(r["valeur_si"])
                for r in springs.rows
                if int(r["noeud_med"]) == int(row["noeud_med"])
            }
            for col, comp in (("F_ressort_X_kN", "N"), ("F_ressort_Y_kN", "VY")):
                value = -at[comp] if comp in at else None  # force sur le pieu : −k·u
                ok = value is not None and _same(value, 1e-3, row[col])
                _compare(
                    stats,
                    f"{row['pieu']} n{row['noeud_med']} {case} {col}",
                    ok,
                    f"{value} vs {row[col]}",
                )
    return stats


def chevetres(ask: Cache, rows: list[dict[str, str]]) -> dict[str, Any]:
    cols = [
        c
        for c in ("N_kN", "VY_kN", "VZ_kN", "MT_kNm", "MFY_kNm", "MFZ_kNm")
        if c in rows[0]
    ]
    derived = [
        c
        for c in rows[0]
        if c not in cols
        and c
        not in (
            "chevetre_file",
            "X_m",
            "Y_m",
            "Z_m",
            "noeud_med",
            "extremite_lue",
            "maille_SEG2_med",
            "cas_ou_combinaison",
            "TS",
            "repere_chevetre",
            "repere_dalle",
        )
    ]
    stats = _new_stats(
        cols,
        derived,
        "les colonnes de la dalle (intégrales sur la bande de 1,20 m) et le moment de travée signé sont des grandeurs dérivées",
    )
    for row in rows:
        stats["lignes"] += 1
        case = _case(row)
        found = _index(
            ask(groupes=("CHEVETRES",), champ="EFGE_ELNO", cas=(case,), mode="tout")
        )
        for col in cols:
            comp, factor = BEAM[col]
            value = found.get(
                (int(row["noeud_med"]), int(row["maille_SEG2_med"]), comp)
            )
            ok = value is not None and _same(value, factor, row[col])
            _compare(
                stats,
                f"file {row['chevetre_file']} n{row['noeud_med']} {case} {col}",
                ok,
                f"{value} vs {row[col]}",
            )
    return stats


def coupes(ask: Cache, rows: list[dict[str, str]]) -> dict[str, Any]:
    stats = _new_stats(["max_sur_TS", "TS_du_max", "min_sur_TS", "TS_du_min"], [])
    for row in rows:
        stats["lignes"] += 1
        y = 0.0 if "Y = 0" in row["coupe"] else -2.0
        comb = _COMB.match(row["combinaison"])
        assert comb is not None
        answer = ask(
            champ="EFGE_NOEU",
            composantes=(row["composante"],),
            cas=(comb.group(1),),
            mode="coupe",
            coupe=f"Y={y}",
        )
        by = {
            (
                int(r["noeud_med"]),
                r["cas_ou_combinaison"].rsplit("(", 1)[1].rstrip(")"),
            ): r
            for r in answer.rows
        }
        for which, col, pos in (
            ("max", "max_sur_TS", "TS_du_max"),
            ("min", "min_sur_TS", "TS_du_min"),
        ):
            r = by.get((int(row["noeud_med"]), which))
            ok = r is not None and _same(float(r["valeur_si"]), 1e-3, row[col])
            _compare(
                stats,
                f"{row['coupe']} n{row['noeud_med']} {row['composante']} {col}",
                ok,
                f"{r and r['valeur_si']} vs {row[col]}",
            )
            ok = r is not None and r["position_mobile"] == row[pos]
            _compare(
                stats,
                f"{row['coupe']} n{row['noeud_med']} {pos}",
                ok,
                f"{r and r['position_mobile']} vs {row[pos]}",
            )
    return stats


def resultantes(
    ask: Cache, ctx: ProjectContext, rows: list[dict[str, str]]
) -> dict[str, Any]:
    stats = _new_stats(
        [
            "FX_kN",
            "FY_kN",
            "FZ_kN (lignes « réactions » par file)",
            "charge appliquée (cas élémentaires)",
        ],
        ["réactions, total", "bilan charge + réactions"],
        "réactions d'une file : Σ −k·u des ressorts des deux pieux (SIEF_ELGA) et réaction DZ des pointes (REAC_NODA) ; la charge appliquée d'une position mobile n'est pas livrée (pas de MED de charges pour les positions)",
    )
    loads = json.loads(
        (ctx.results_dir / "livrables" / "paquet" / "controle_charges.json").read_text(
            "utf-8"
        )
    )["cas"]
    for row in rows:
        case = CASE.get(row["cas"], row["cas"])
        if row["ligne"] == "charge appliquée":
            if case not in loads:
                continue
            stats["lignes"] += 1
            sums = loads[case]["somme_n"]
            for col, comp in (("FX_kN", "FX"), ("FY_kN", "FY"), ("FZ_kN", "FZ")):
                _compare(
                    stats,
                    f"{case} charge {col}",
                    _same(sums[comp], 1e-3, row[col]),
                    f"{sums[comp]} vs {row[col]}",
                )
        elif row["ligne"] == "réactions":
            stats["lignes"] += 1
            groups = (f"PIEU_F{row['file']}_YM", f"PIEU_F{row['file']}_YP")
            springs = {
                r["composante"]: float(r["valeur_si"])
                for r in ask(
                    groupes=groups,
                    champ="SIEF_ELGA",
                    composantes=("N", "VY"),
                    cas=(case,),
                    mode="somme",
                ).rows
            }
            reac = {
                r["composante"]: float(r["valeur_si"])
                for r in ask(
                    groupes=groups,
                    champ="REAC_NODA",
                    composantes=("DZ",),
                    cas=(case,),
                    mode="somme",
                ).rows
            }
            for col, value in (
                ("FX_kN", -springs.get("N", float("nan"))),
                ("FY_kN", -springs.get("VY", float("nan"))),
                ("FZ_kN", reac.get("DZ", float("nan"))),
            ):
                _compare(
                    stats,
                    f"{case} file {row['file']} {col}",
                    _same(value, 1e-3, row[col]),
                    f"{value} vs {row[col]}",
                )
    return stats


def main(argv: list[str]) -> None:
    folder = Path(argv[0]) if argv else EXPORT
    ctx = load_project("estacade_pieux_01", ROOT)
    ask = Cache(ctx)

    def read(name: str) -> list[dict[str, str]]:
        with (folder / name).open(encoding="utf-8") as handle:
            return list(csv.DictReader(handle, delimiter=";"))

    report: dict[str, Any] = {"dossier": str(folder), "fichiers": {}}
    report["fichiers"]["tetes_de_pieux.csv"] = tetes(ask, read("tetes_de_pieux.csv"))
    report["fichiers"]["profils_pieux.csv"] = profils(ask, read("profils_pieux.csv"))
    report["fichiers"]["chevetres.csv"] = chevetres(ask, read("chevetres.csv"))
    report["fichiers"]["dalle_coupes.csv"] = coupes(ask, read("dalle_coupes.csv"))
    report["fichiers"]["resultantes_cas_elementaires.csv"] = resultantes(
        ask, ctx, read("resultantes_cas_elementaires.csv")
    )
    comm = hashlib.sha256((folder / "comm_production.comm").read_bytes()).hexdigest()
    manifest = json.loads(
        (ctx.results_dir / "livrables" / "manifeste.json").read_text("utf-8")
    )
    report["fichiers"]["comm_production.comm"] = {
        "sha256": comm,
        "identique_au_comm_de_production_des_livrables": comm
        == manifest["comm_production_sha256"],
    }
    for doc in ("ecarts_C1_C13.md", "modele_resume.md"):
        report["fichiers"][doc] = {
            "note": "document de relecture (texte), pas un export de valeurs : non reproductible par une requête ; ses valeurs viennent du paquet (contre_calcul) et des CSV ci-dessus"
        }
    summary: defaultdict[str, int] = defaultdict(int)
    for entry in report["fichiers"].values():
        summary["valeurs"] += entry.get("valeurs", 0)
        summary["differentes"] += entry.get("differentes", 0)
    report["bilan"] = dict(summary)
    out = ctx.results_dir / "livrables" / "rejeu_export_lot47.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(
        json.dumps(
            {
                k: {
                    kk: vv
                    for kk, vv in v.items()
                    if kk
                    in (
                        "lignes",
                        "valeurs",
                        "differentes",
                        "identique_au_comm_de_production_des_livrables",
                    )
                }
                for k, v in report["fichiers"].items()
            },
            indent=1,
            ensure_ascii=False,
        )
    )
    print(json.dumps(report["bilan"]))


if __name__ == "__main__":
    main(sys.argv[1:])
