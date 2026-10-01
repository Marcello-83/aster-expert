"""Candidate questions for the retrieval bench, from the query journal (lot 42,
étape 6).

A documentary search (`search_codeaster_docs`) did not give a useful answer
when none of the documents it returned was read afterwards
(`get_document_section`) and it was followed, within `window`:

- by a reading of another document (`lu ailleurs`: the answer was found
  elsewhere, the document read is a hint of the expected one);
- or by another search with a different query sharing at least one word of
  four letters or more (`reformulée` -- a query on an unrelated subject is a
  change of topic, not a reformulation);
- or it returned nothing (`sans résultat`).

Each such query becomes a candidate question, marked `à valider par MM`: the
heuristic tells where the retrieval failed, never what the right answer is.
Duplicates, queries already in the bench and `mcp-check` calls are left out;
the journal is read tolerantly (a damaged line is counted, not fatal).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from aster_expert.mcp.logging import CHECK_ORIGIN, QueryLogEntry

SEARCH_TOOL = "search_codeaster_docs"
READ_TOOL = "get_document_section"
Motive = Literal["lu ailleurs", "reformulée", "sans résultat"]


class CandidateQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    profile: str | None
    motive: Motive
    followed_by: str | None
    """The other query, or the document read instead."""
    returned_documents: tuple[str, ...]
    asked_at: dt.datetime
    status: Literal["à valider par MM"] = "à valider par MM"
    origin: str = "journal des requêtes (query_log.jsonl), lot 42"


def _document(identifier: str) -> str:
    return identifier.split("#", 1)[0]


def _norm(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.casefold()) if len(w) >= 4}


def read_journal(path: Path) -> tuple[list[QueryLogEntry], int]:
    """Usage entries in time order and the number of unreadable lines."""
    if not path.is_file():
        return [], 0
    entries, bad = [], 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = QueryLogEntry.model_validate_json(line)
        except ValueError:
            bad += 1
            continue
        if entry.origin != CHECK_ORIGIN:
            entries.append(entry)
    entries.sort(key=lambda e: e.timestamp)
    return entries, bad


def known_questions(path: Path) -> set[str]:
    """Normalised questions and source questions already in the bench."""
    out: set[str] = set()
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            for key in ("question", "source_question"):
                if item.get(key):
                    out.add(_norm(str(item[key])))
    return out


def candidate_questions(
    entries: Iterable[QueryLogEntry],
    *,
    known: set[str] | None = None,
    window: dt.timedelta = dt.timedelta(minutes=15),
) -> list[CandidateQuestion]:
    ordered = sorted(entries, key=lambda e: e.timestamp)
    known = known or set()
    seen: set[str] = set()
    out: list[CandidateQuestion] = []
    for i, entry in enumerate(ordered):
        if entry.tool != SEARCH_TOOL or not entry.query:
            continue
        key = _norm(entry.query)
        # A bare catalogue identifier is a syntax lookup, not a question.
        if key in seen or key in known or re.fullmatch(r"[a-z0-9_]+", key):
            continue
        returned = {_document(r.identifier) for r in entry.returned}
        read_hit = False
        elsewhere: str | None = None
        reformulated: str | None = None
        for later in ordered[i + 1 :]:
            if later.timestamp - entry.timestamp > window:
                break
            if later.tool == READ_TOOL and later.query:
                doc = _document(later.query)
                if doc in returned:
                    read_hit = True
                    break
                elsewhere = elsewhere or later.query
            elif later.tool == SEARCH_TOOL:
                if (
                    later.query
                    and _norm(later.query) != key
                    and _words(later.query) & _words(entry.query)
                ):
                    reformulated = later.query
                break
        if read_hit:
            continue
        motive: Motive | None = None
        follow: str | None = None
        if not entry.returned:
            motive = "sans résultat"
        elif elsewhere is not None:
            motive, follow = "lu ailleurs", elsewhere
        elif reformulated is not None:
            motive, follow = "reformulée", reformulated
        if motive is None:
            continue
        seen.add(key)
        out.append(
            CandidateQuestion(
                id=f"cand-{len(out) + 1:03d}",
                question=entry.query,
                profile=entry.profile,
                motive=motive,
                followed_by=follow,
                returned_documents=tuple(
                    dict.fromkeys(_document(r.identifier) for r in entry.returned)
                ),
                asked_at=entry.timestamp,
            )
        )
    return out


def write_candidates(path: Path, candidates: list[CandidateQuestion]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(json.loads(c.model_dump_json()), ensure_ascii=False) + "\n"
            for c in candidates
        ),
        encoding="utf-8",
    )
    return path


__all__ = [
    "CandidateQuestion",
    "candidate_questions",
    "known_questions",
    "read_journal",
    "write_candidates",
]
