"""Search the shared base of findings (lot 41, étape 4.3): by catalogue command,
by keyword (or keyword value, e.g. `DKT`), by free text -- all given criteria
together. A text search needs every word (accents and case ignored) and ranks
by the number of occurrences; without text, the findings established by
execution come first (level D, then C, B, A)."""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict

from aster_expert.constats.models import Constat

_WORD = re.compile(r"[\w<>]+")
_LEVEL_RANK = {"D": 0, "C": 1, "B": 2, "A": 3}


def _fold(text: str) -> str:
    """Accents, case and the ligatures œ/æ ignored (« noeuds » finds « nœuds »)."""
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
    return bare.replace("œ", "oe").replace("æ", "ae")


class ConstatHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    constat: Constat
    score: int
    """Occurrences of the searched words (0 without text)."""


def search_constats(
    base: dict[str, Constat],
    *,
    text: str | None = None,
    command: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
) -> list[ConstatHit]:
    if not (text or command or keyword):
        message = "préciser au moins un critère : commande, mot-clé ou texte"
        raise ValueError(message)
    if limit < 1:
        message = "limit doit être au moins 1"
        raise ValueError(message)
    words = [_fold(w) for w in _WORD.findall(text or "") if len(w) > 1]
    hits = []
    for constat in base.values():
        if command and command.upper() not in constat.commands:
            continue
        if keyword and keyword.upper() not in (*constat.keywords, *constat.commands):
            continue
        score = 0
        if words:
            haystack = _fold(constat.searchable_text())
            counts = [haystack.count(w) for w in words]
            if not all(counts):
                continue
            score = sum(counts)
        hits.append(ConstatHit(constat=constat, score=score))
    hits.sort(
        key=lambda h: (
            -h.score,
            _LEVEL_RANK[h.constat.validation_level],
            h.constat.constat_id,
        )
    )
    return hits[:limit]


__all__ = ["ConstatHit", "search_constats"]
