"""Lot 44, étape 8.3 : effet de la reformulation et de l'aiguillage sur cand-019 et
cand-021, les deux requêtes du journal du lot 42 restées sans résultat.

Pour chaque question : la requête d'origine (liste de mots-clés, recopiée du journal
`data/evaluations/questions_candidates_lot42.jsonl`), sa reformulation en langage
naturel (règle du skill `code-aster-expert`, lot 44), même profil, même moteur
(`aster_expert.mcp.tools.search_codeaster_docs`, k = 10) ; on relève le rang du
document attendu. Pour cand-021 (un nom de cas test), on mesure aussi l'aiguillage
vers `search_test_cases`.

Constat du lot 44 : au lot 42, les deux requêtes avaient été lancées avec le filtre
`family="testcase"` (journal), alors que les cas tests ne sont pas indexés dans la
documentation : c'est ce filtre, non la forme en liste de mots-clés, qui les rendait
vides (une famille absente est refusée depuis par l'outil). Sans ce filtre, la mesure
compare les deux formulations.

Le journal des requêtes n'est pas touché (journal temporaire). Sortie :
`data/evaluations/lot44/reformulation.json`. Déterministe (index BM25 figé).

Usage : `.venv/bin/python scripts/mesure_reformulation_lot44.py`
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aster_expert.mcp import tools

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "evaluations" / "lot44" / "reformulation.json"
CANDIDATES = ROOT / "data" / "evaluations" / "questions_candidates_lot42.jsonl"
BENCH = ROOT / "data" / "evaluations" / "questions.jsonl"
PROFILES = ROOT / "data" / "evaluations" / "query_profiles.jsonl"
BENCH_ORIGIN = (
    "journal des requêtes (lot 42), tri validé par MM, document établi au lot 44"
)

CASES = (
    {
        "id": "cand-019",
        "journal_lot42": (
            "family='testcase', k=8 : 0 résultat "
            "(query_log.jsonl, 2026-09-21T09:26:24Z)"
        ),
        "profile": "syntaxe",
        "expected": "U4.43.01",
        "original": (
            "ELAS_COQUE MEMB_L FLEX_L coefficients rigidité membrane flexion repère "
            "local orthotrope"
        ),
        "reformulated": (
            "Comment définir le matériau ELAS_COQUE d'une coque orthotrope en donnant "
            "ses rigidités de membrane et de flexion"
        ),
    },
    {
        "id": "cand-021",
        "journal_lot42": (
            "family='testcase', k=5 : 0 résultat "
            "(query_log.jsonl, 2026-09-21T09:27:05Z)"
        ),
        "profile": "syntaxe",
        "expected": "V3.03.502",
        "original": "ssls502a DEFI_MATERIAU ELAS_COQUE",
        "reformulated": (
            "Quel cas test officiel valide une plaque définie avec le matériau "
            "ELAS_COQUE de DEFI_MATERIAU"
        ),
    },
)


def _rank(documents: list[str], expected: str) -> int | None:
    return documents.index(expected) + 1 if expected in documents else None


def measure() -> list[dict[str, object]]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "log.jsonl"
        for case in CASES:
            row: dict[str, object] = {
                "id": case["id"],
                "expected": case["expected"],
                # Cause de l'échec du lot 42 : les cas tests ne sont pas indexés dans
                # la documentation, le filtre family='testcase' ne pouvait rien rendre.
                "journal_lot42": case["journal_lot42"],
            }
            for key in ("original", "reformulated"):
                result = tools.search_codeaster_docs(
                    project_root=ROOT,
                    query=case[key],
                    profile=case["profile"],
                    k=10,
                    log_path=log,
                )
                docs = list(dict.fromkeys(h.document_id for h in result.results))
                row[key] = {
                    "query": case[key],
                    "documents": docs,
                    "rank_expected": _rank(docs, case["expected"]),
                }
            if case["id"] == "cand-021":
                routed = tools.search_test_cases(
                    project_root=ROOT,
                    command="DEFI_MATERIAU",
                    keyword="ELAS_COQUE",
                    limit=200,
                    log_path=log,
                )
                paths = [m.path for m in routed.results]
                row["aiguillage_search_test_cases"] = {
                    "appel": (
                        "search_test_cases(command='DEFI_MATERIAU', "
                        "keyword='ELAS_COQUE')"
                    ),
                    "fichiers": len(paths),
                    "ssls502a_trouve": "ssls502a.comm" in paths,
                }
            out.append(row)
    return out


def measure_bench() -> dict[str, object]:
    """Requête d'origine du journal (sans filtre) contre formulation du banc, pour
    les questions versées au lot 44 qui ont un document attendu : hit@10."""
    candidates = {
        json.loads(line)["id"]: json.loads(line)
        for line in CANDIDATES.read_text("utf-8").splitlines()
        if line.strip()
    }
    bench = [
        json.loads(line)
        for line in BENCH.read_text("utf-8").splitlines()
        if line.strip()
    ]
    profiles = {
        json.loads(line)["id"]: json.loads(line)["query_profile"]
        for line in PROFILES.read_text("utf-8").splitlines()
        if line.strip()
    }
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "log.jsonl"
        for q in bench:
            if q["origin"] != BENCH_ORIGIN or not q["required_documents"]:
                continue
            original = candidates[q["source_question"]]["question"]
            hits = {}
            for key, text in (("original", original), ("reformulated", q["question"])):
                result = tools.search_codeaster_docs(
                    project_root=ROOT,
                    query=text,
                    profile=profiles[q["id"]],
                    k=10,
                    log_path=log,
                )
                docs = {h.document_id for h in result.results}
                hits[key] = bool(docs & set(q["required_documents"]))
            rows.append({"id": q["id"], "source": q["source_question"], **hits})
    return {
        "questions": len(rows),
        "hit10_original": sum(r["original"] for r in rows),
        "hit10_reformulated": sum(r["reformulated"] for r in rows),
        "detail": rows,
    }


def main() -> int:
    rows = measure()
    bench = measure_bench()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"cas": rows, "banc_lot44": bench}, ensure_ascii=False, indent=2)
        + "\n",
        "utf-8",
    )
    print(
        f"banc lot 44 ({bench['questions']} questions documentées) : hit@10 requête "
        f"d'origine {bench['hit10_original']}, reformulée {bench['hit10_reformulated']}"
    )
    for row in rows:
        o = row["original"]
        r = row["reformulated"]
        print(
            f"{row['id']} attendu {row['expected']} : rang d'origine "
            f"{o['rank_expected']} ({len(o['documents'])} doc.), reformulée "  # type: ignore[index]
            f"{r['rank_expected']} ({len(r['documents'])} doc.)"  # type: ignore[index]
        )
        if "aiguillage_search_test_cases" in row:
            print(f"  aiguillage : {row['aiguillage_search_test_cases']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
