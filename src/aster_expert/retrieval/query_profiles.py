"""Query-profile annotations for the evaluation set (lot 7c, G1/G3).

The profile a query is served with (`syntaxe`, `theorie`, `methode`,
`aster_expert.retrieval.source_priority`) is never detected from the query
text in this project (lot 7b instruction E2, reaffirmed at lot 7c G1): a
caller always states it explicitly. `data/evaluations/query_profiles.jsonl`
is the profile every one of the lot 5/5b bench questions *would* be served
with by such a caller, established once from the question's own wording
alone, without consulting which documents it expects
(`/media/sf_partage/echanges/lot7c_query_profiles.jsonl`, copied here
verbatim). This module only loads and validates that file -- it is input
data, never a source of rules (CLAUDE.md, `/media/sf_partage` n'est jamais
une source de règles), and it is never edited here to match a measured
result (lot 7c instruction G3: "si tu penses qu'une annotation est fausse,
signale-la ... mais ne la change pas toi-même -- ce serait régler
l'annotation sur le résultat").
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

QueryProfile = Literal["syntaxe", "theorie", "methode"]

DEFAULT_QUERY_PROFILE: QueryProfile = "syntaxe"


class QueryProfileAnnotation(BaseModel):
    """One line of `data/evaluations/query_profiles.jsonl`."""

    model_config = ConfigDict(frozen=True)

    id: str
    question: str
    query_profile: QueryProfile


def load_query_profiles(path: Path) -> dict[str, QueryProfile]:
    """Question id -> its annotated profile.

    Never invents an entry for a question id absent from `path` (lot 7c: the
    input file does not cover `eval-065`, added to the bench after the
    annotation was produced -- a caller decides its own fallback for a
    missing id, this loader never guesses one on its behalf).
    """
    profiles: dict[str, QueryProfile] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = QueryProfileAnnotation.model_validate_json(line)
        profiles[entry.id] = entry.query_profile
    return profiles


def default_query_profiles_path(project_root: Path) -> Path:
    return project_root / "data" / "evaluations" / "query_profiles.jsonl"
