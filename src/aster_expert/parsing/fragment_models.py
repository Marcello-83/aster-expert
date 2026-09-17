"""Data model for a documentary fragment (lot 7, docs/metadata.md §1).

`DocumentFragment` matches the schema sketched in docs/metadata.md §1, with
one amendment made explicit here rather than left implicit: `granularity`
(docs/development-plan.md, lot 7, D2) — this lot builds two chunkings of the
same corpus side by side (one fragment per section file, and a finer one
splitting long files into subsections) and measures both on the evaluation
bench before choosing. A fragment without this field could not be told apart
from its sibling built at the other granularity from the same source file,
which `CLAUDE.md` ("Toute donnée indexée conserve sa source") forbids.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

FragmentGranularity = Literal["by_file", "by_subsection"]


class DocumentFragment(BaseModel):
    """One documentary fragment, ready for lexical indexing (lot 7).

    `fragment_id` is deterministic (document id + section path), never a
    counter or a timestamp (docs/metadata.md §1). `content` is the exact
    raw source slice (`str.splitlines()` re-joined, never re-rendered by
    docutils): a LaTeX formula inside `.. math::`/`:math:` appears exactly
    as written in the source, per the lot 7 instruction. `content_hash` is
    computed over that same exact slice, so idempotence (docs/corpus.md §7,
    two runs on the same revision produce identical fragments, hashes
    included) is a direct consequence of never re-deriving `content`.
    """

    model_config = ConfigDict(frozen=True)

    fragment_id: str
    granularity: FragmentGranularity
    source_name: str
    source_commit: str
    document_id: str
    document_title: str | None
    family: str
    aster_version: str
    doc_revision: str | None = None
    section_path: tuple[str, ...]
    content: str
    content_hash: str
    source_path: str
    source_url: str | None = None
    line_start: int
    line_end: int
    related_commands: tuple[str, ...] = ()
    related_keywords: tuple[str, ...] = ()
    related_documents: tuple[str, ...] = ()
    language: str = "fr"
    extracted_at: datetime
