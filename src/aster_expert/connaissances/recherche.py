"""Search the six knowledge layers (lot 42, étape 3.1).

Same semantics as the search of findings (lot 41): every given criterion
together; a text search needs every word (accents and case ignored) and ranks by
the number of occurrences. Without text, entries are ranked by status (`promu`,
`établi`, `observé`), then by level (E down to A), then by identifier.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.base import AnyEntry, KnowledgeBase
from aster_expert.connaissances.modeles import LAYERS, STATUSES, LayerName, Status
from aster_expert.constats.search import _fold

_WORD = re.compile(r"[\w<>]+")
_STATUS_RANK = {"promu": 0, "établi": 1, "observé": 2}
_LEVEL_RANK = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4}


class KnowledgeHit(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    entry_id: str
    layer: LayerName
    score: int


def search_knowledge(
    base: KnowledgeBase,
    *,
    text: str | None = None,
    command: str | None = None,
    keyword: str | None = None,
    layers: tuple[str, ...] = (),
    status: str | None = None,
    limit: int = 20,
) -> list[KnowledgeHit]:
    if not (text or command or keyword or layers or status):
        message = (
            "préciser au moins un critère : texte, commande, mot-clé, couche ou statut"
        )
        raise ValueError(message)
    if limit < 1:
        message = "limit doit être au moins 1"
        raise ValueError(message)
    unknown = [layer for layer in layers if layer not in LAYERS]
    if unknown:
        message = f"couche(s) inconnue(s) {unknown} ; couches : {', '.join(LAYERS)}"
        raise ValueError(message)
    if status is not None and status not in STATUSES:
        message = f"statut inconnu {status!r} ; statuts : {', '.join(STATUSES)}"
        raise ValueError(message)
    words = [_fold(w) for w in _WORD.findall(text or "") if len(w) > 1]
    hits: list[KnowledgeHit] = []
    for entry in base.all_entries():
        layer = base.layer_of(entry.id)
        if layers and layer not in layers:
            continue
        if status is not None and entry.status != status:
            continue
        if command and command.upper() not in entry.commands:
            continue
        if keyword and keyword.upper() not in (*entry.keywords, *entry.commands):
            continue
        score = 0
        if words:
            haystack = _fold(entry.searchable_text())
            counts = [haystack.count(w) for w in words]
            if not all(counts):
                continue
            score = sum(counts)
        hits.append(KnowledgeHit(entry_id=entry.id, layer=layer, score=score))
    hits.sort(key=lambda h: _rank(h, base))
    return hits[:limit]


def _rank(hit: KnowledgeHit, base: KnowledgeBase) -> tuple[int, int, int, str]:
    entry: AnyEntry | None = base.get(hit.entry_id)
    assert entry is not None
    status: Status = entry.status
    return (
        -hit.score,
        _STATUS_RANK[status],
        _LEVEL_RANK[entry.validation_level],
        hit.entry_id,
    )


__all__ = ["KnowledgeHit", "search_knowledge"]
