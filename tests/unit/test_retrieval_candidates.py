"""Questions candidates du banc tirées du journal des requêtes (lot 42, étape 6)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from aster_expert.mcp.logging import QueryLogEntry
from aster_expert.retrieval.candidates import (
    candidate_questions,
    known_questions,
    read_journal,
    write_candidates,
)

T0 = dt.datetime(2026, 9, 20, 10, 0, tzinfo=dt.UTC)


def _entry(
    minutes: float, tool: str, query: str, returned: list[str], **kw: Any
) -> QueryLogEntry:
    return QueryLogEntry.model_validate(
        {
            "timestamp": T0 + dt.timedelta(minutes=minutes),
            "tool": tool,
            "query": query,
            "profile": kw.get("profile", "methode"),
            "returned": [{"identifier": r, "score": 1.0} for r in returned],
            "duration_s": 0.1,
            "origin": kw.get("origin", "session"),
        }
    )


def test_a_search_whose_hit_is_read_is_not_a_candidate() -> None:
    entries = [
        _entry(0, "search_codeaster_docs", "ressort de sol réparti", ["U4.42.01#A"]),
        _entry(1, "get_document_section", "U4.42.01#B", ["U4.42.01#B"]),
        _entry(
            2, "search_codeaster_docs", "ressort de sol autre forme", ["U2.01.01#A"]
        ),
    ]
    # La première a été lue ; la dernière n'est suivie de rien : aucune candidate.
    assert candidate_questions(entries) == []


def test_reformulation_reading_elsewhere_and_empty_answers_are_candidates() -> None:
    entries = [
        _entry(
            0,
            "search_codeaster_docs",
            "raideur surfacique ressort coque",
            ["U4.42.01#A"],
        ),
        _entry(
            1, "search_codeaster_docs", "ressort réparti sur une coque", ["U2.06.01#A"]
        ),
        _entry(2, "get_document_section", "U3.12.01#X", ["U3.12.01#X"]),
        _entry(30, "search_codeaster_docs", "symétrie plan bloqué", []),
    ]
    found = {c.question: c for c in candidate_questions(entries)}
    assert found["raideur surfacique ressort coque"].motive == "reformulée"
    assert found["ressort réparti sur une coque"].motive == "lu ailleurs"
    assert found["ressort réparti sur une coque"].followed_by == "U3.12.01#X"
    assert found["symétrie plan bloqué"].motive == "sans résultat"
    assert all(c.status == "à valider par MM" for c in found.values())


def test_a_change_of_topic_is_not_a_reformulation() -> None:
    entries = [
        _entry(0, "search_codeaster_docs", "loi de Mohr-Coulomb", ["R7.01.28#A"]),
        _entry(
            1,
            "search_codeaster_docs",
            "section circulaire d'une poutre",
            ["U4.42.01#A"],
        ),
    ]
    assert [c.question for c in candidate_questions(entries)] == []


def test_known_bare_and_duplicate_queries_are_left_out(tmp_path: Path) -> None:
    bench = tmp_path / "questions.jsonl"
    bench.write_text(
        json.dumps({"question": "Ressort de sol réparti ?"}) + "\n", "utf-8"
    )
    entries = [
        _entry(0, "search_codeaster_docs", "ressort de sol réparti", []),
        _entry(1, "search_codeaster_docs", "STAT_NON_LINE", []),
        _entry(2, "search_codeaster_docs", "pivot nul factorisation", []),
        _entry(3, "search_codeaster_docs", "pivot nul factorisation", []),
    ]
    found = candidate_questions(entries, known=known_questions(bench))
    assert [c.question for c in found] == ["pivot nul factorisation"]
    path = write_candidates(tmp_path / "out.jsonl", found)
    assert json.loads(path.read_text("utf-8").splitlines()[0])["id"] == "cand-001"


def test_the_journal_is_read_tolerantly_without_mcp_check(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    lines = [
        _entry(0, "search_codeaster_docs", "a b", []).model_dump_json(),
        _entry(
            1, "search_codeaster_docs", "c d", [], origin="mcp-check"
        ).model_dump_json(),
        "\x00\x00 ligne abîmée",
    ]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    entries, bad = read_journal(log)
    assert [e.query for e in entries] == ["a b"] and bad == 1
