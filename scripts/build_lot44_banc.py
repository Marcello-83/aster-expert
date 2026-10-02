"""Lot 44, étape 8 : versement au banc des 22 questions candidates retenues par MM.

Source du tri : `/media/sf_partage/echanges/tri_questions_candidates_lot42.md` (22
retenues, 17 écartées). La colonne « Document attendu » du tri n'était qu'une
hypothèse : le document attendu de chaque question a été établi par la session du lot
44 en lisant la documentation (outils MCP `search_codeaster_docs`,
`get_document_section`), et la trace de lecture est dans `verified_by`. Une question
à laquelle aucun document ne répond entre comme « non documentée »
(`answerability="absent"`, `required_documents` vide, `note` qui dit ce qui a été
cherché) -- jamais un document forcé.

La question est écrite en langage naturel (formulation du tri), non en liste de
mots-clés : c'est la règle de reformulation du lot 44 (skill `code-aster-expert`).

Données : `data/evaluations/lot44/questions_retenues_lot44.yaml`. Écrit (idempotent,
ordre fixe) : les questions `eval-066` à `eval-087` à la fin de
`data/evaluations/questions.jsonl` et leurs profils dans
`data/evaluations/query_profiles.jsonl`. Relancer ne duplique rien.

Usage : `.venv/bin/python scripts/build_lot44_banc.py`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data" / "evaluations" / "questions.jsonl"
PROFILES = ROOT / "data" / "evaluations" / "query_profiles.jsonl"

VERSION = {
    "solver": "17.4.0",
    "documentation_revision": "9c8c179f57ef7ca1d2891cac275ee4823a57967c",
    "compatibility_status": (
        "correspondance solveur/documentation vérifiée par tag (git ls-remote --tags, "
        "config/versions.yaml) ; aucune confirmation croisée par changelog au-delà de "
        "cette convention de nommage commune"
    ),
}
ORIGIN = "journal des requêtes (lot 42), tri validé par MM, document établi au lot 44"

DATA = ROOT / "data" / "evaluations" / "lot44" / "questions_retenues_lot44.yaml"


def rows() -> list[dict[str, Any]]:
    """The 22 questions, as versioned in `DATA` (order fixed)."""
    raw = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    return list(raw["questions"])


def question(row: dict[str, Any]) -> dict[str, object]:
    return {
        "id": row["id"],
        "question": row["question"],
        "domain": row["domain"],
        "origin": ORIGIN,
        "source_question": row["source_question"],
        "version": VERSION,
        "required_documents": row["required_documents"],
        "supporting_documents": row["supporting_documents"],
        "expected_commands": row["expected_commands"],
        "verified_by": row["verified_by"],
        "note": row["note"],
        "answerability": row["answerability"],
        "gold_confidence": row["gold_confidence"],
    }


def _append(path: Path, records: list[dict[str, object]]) -> int:
    existing = {
        json.loads(line)["id"]
        for line in path.read_text("utf-8").splitlines()
        if line.strip()
    }
    new = [r for r in records if r["id"] not in existing]
    if new:
        with path.open("a", encoding="utf-8") as handle:
            for r in new:
                handle.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(new)


def main() -> int:
    data = rows()
    n_q = _append(QUESTIONS, [question(r) for r in data])
    n_p = _append(
        PROFILES,
        [
            {"id": r["id"], "question": r["question"], "query_profile": r["profile"]}
            for r in data
        ],
    )
    print(f"questions ajoutées : {n_q} ; profils ajoutés : {n_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
