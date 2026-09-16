"""Data models for config/sources.yaml and data/raw/manifest.json.

See docs/corpus.md sections 1 and 5.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

UpdatePolicy = Literal["fetch_only", "fetch_and_checkout", "pinned"]


class SourceFamily(BaseModel):
    """One documentary/code family carried by a source (docs/corpus.md §3)."""

    model_config = ConfigDict(frozen=True)

    enabled: bool
    paths: tuple[str, ...] = ()


class SourceConfig(BaseModel):
    """One declared external repository (config/sources.yaml `sources[]`)."""

    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    ref: str
    commit: str | None = None
    local_path: str
    license: str
    families: dict[str, SourceFamily]
    update_policy: UpdatePolicy | None = None

    def enabled_family_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(name for name, family in self.families.items() if family.enabled)
        )


class SourcesDefaults(BaseModel):
    model_config = ConfigDict(frozen=True)

    clone_root: str
    update_policy: UpdatePolicy
    allow_dirty: bool
    partial_clone: bool
    depth: int | None = None


class SecondarySource(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    indexed: bool
    note: str


class SourcesFile(BaseModel):
    """The parsed content of config/sources.yaml."""

    model_config = ConfigDict(frozen=True)

    schema_version: int
    defaults: SourcesDefaults
    sources: tuple[SourceConfig, ...]
    secondary_sources: tuple[SecondarySource, ...] = ()


# Status of a single source's synchronization attempt. A `blocked_*` status
# is a normal, reported outcome, never an exception: this project never
# corrects a diverging or dirty working copy with authority (CLAUDE.md,
# "Gestion des dépôts externes").
SyncStatus = Literal[
    "cloned",
    "adopted",
    "blocked_dirty",
    "blocked_diverged",
    "blocked_error",
]


class ManifestSourceEntry(BaseModel):
    """One entry of data/raw/manifest.json `sources[]` (docs/corpus.md §5).

    `status`/`detail` are an amendment (lot 3) to the schema sketched in
    docs/corpus.md: the documented fields alone cannot distinguish a source
    that was actually synchronized from one whose sync was refused (dirty
    working copy, or a working copy diverged from the declaration) without
    losing information silently, which CLAUDE.md forbids.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    url: str
    ref: str
    commit: str | None
    local_path: str
    synchronized_at: datetime
    dirty: bool
    families: tuple[str, ...]
    status: SyncStatus
    detail: str | None = None


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    sources: tuple[ManifestSourceEntry, ...]


# Lot 6 : inventaire du corpus documentaire (docs/corpus.md §6).
#
# Kinds of documented, never silently corrected, corpus defects (CLAUDE.md,
# "Ne jamais neutraliser une alarme sans en expliquer la cause";
# docs/corpus.md §6):
#   - missing_label              : no ".. _id:" directive found in index.rst.
#   - missing_title               : no "**<label>** <title>" line found for
#                                   the document's own label (8/2047
#                                   documents at lot 6 — an older preamble
#                                   convention, "**Manuel ...**" /
#                                   "**Fascicule ...**", precedes the real
#                                   title line on most of them; one carries
#                                   no such line at all).
#   - label_directory_mismatch   : the label does not match its own
#                                   directory name (a real defect found on
#                                   3/2047 documents at lot 6, see the batch
#                                   report — never corrected here).
#   - duplicate_document_id      : two documents normalize to the same id.
#   - unresolved_toctree_entry   : a toctree entry has no matching file.
#   - unknown_family_prefix      : the id's leading token matches none of
#                                   the families declared in docs/corpus.md
#                                   §3.
#   - empty_component_file       : a file composing the document carries no
#                                   substantive content (docutils probe,
#                                   lot 6, I3/I6).
#   - empty_document             : the document, across every file that
#                                   composes it, carries no substantive
#                                   content beyond its label and title.
#   - orphan_file                 : a file composing the document that is
#                                   neither a toctree entry nor mentioned
#                                   by name (with or without its extension)
#                                   in any other `.rst` file of the same
#                                   document — narrow on purpose: a two-
#                                   level toctree (an intermediate
#                                   "sommaire" page) already counts as a
#                                   mention, so it is never a false
#                                   positive on that real, if rare, corpus
#                                   shape (`R5.03.17`, lot 6 compte rendu).
DocumentAnomalyKind = Literal[
    "missing_label",
    "missing_title",
    "label_directory_mismatch",
    "duplicate_document_id",
    "unresolved_toctree_entry",
    "unknown_family_prefix",
    "empty_component_file",
    "empty_document",
    "orphan_file",
]


class DocumentAnomaly(BaseModel):
    """One inventory anomaly (docs/corpus.md §6): listed, never fixed here."""

    model_config = ConfigDict(frozen=True)

    kind: DocumentAnomalyKind
    document_id: str | None
    relative_path: str
    detail: str


class DocumentEntry(BaseModel):
    """One inventory entry, one per DOCUMENT (a directory), docs/corpus.md §6.

    A document is a directory owning its own `index.rst` (never nested
    inside another document's directory — verified at lot 6: 0 occurrences
    on the synchronized `codeaster-doc` corpus). `document_id` is always the
    normalized (uppercased) form; `raw_label` is preserved exactly as
    written in the source and never replaced by the normalized form (lot 6
    instruction: casing is not uniform — 1943 upper, 104 lower on the
    17.4.0 corpus, 0 mixed).
    """

    model_config = ConfigDict(frozen=True)

    document_id: str
    raw_label: str
    directory_name: str
    family: str
    subfamily: str
    title: str | None
    relative_path: str
    files: tuple[str, ...]
    size_bytes: int
    fingerprint: str
    source_name: str
    source_commit: str


# Lot 6, I5 : table commande -> document, construite depuis un fait observé
# dans le titre du document (jamais une ressemblance devinée).


class CommandDocumentEdge(BaseModel):
    """One command <-> U4/U7 document link, both directions many-to-many:
    a document can name several commands together (`AFFE_CHAR_MECA`,
    `AFFE_CHAR_MECA_C`, `AFFE_CHAR_MECA_F` in one document), and a command
    can be documented by several documents (`IMPR_RESU`, one per output
    format)."""

    model_config = ConfigDict(frozen=True)

    command: str
    document_id: str


class CommandMappingResult(BaseModel):
    """Result of `aster-expert sources command-map` (lot 6, I5)."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    source_name: str
    source_commit: str
    total_catalogue_commands: int
    matched_catalogue_commands: int
    edges: tuple[CommandDocumentEdge, ...]
    commands_without_document: tuple[str, ...]
    documents_without_command: tuple[str, ...]
    documents_naming_known_macro_command: tuple[tuple[str, str], ...]


class InventoryResult(BaseModel):
    """The full result of building data/raw/inventory.jsonl (docs/corpus.md §6)."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    source_name: str
    source_commit: str
    documents: tuple[DocumentEntry, ...]
    anomalies: tuple[DocumentAnomaly, ...]


# Lot 6, I3 : sonde d'analyse .rst par docutils — valide (ou infirme) que
# parser les sources .rst perd peu de contenu par rapport à un rendu Sphinx
# construit (docs/development-plan.md, lot 6).


class ProbeFrequency(BaseModel):
    """One unrecognized directive/role name (or unresolved include target),
    with its raw occurrence count across the probed sample."""

    model_config = ConfigDict(frozen=True)

    name: str
    count: int


class CrossReferenceEdge(BaseModel):
    """One resolvable `:ref:`/`:external:ref:` link between two documents
    (lot 6, I4). `count` is the number of occurrences of this exact edge
    across every file of `source_document_id`."""

    model_config = ConfigDict(frozen=True)

    source_document_id: str
    target_document_id: str
    count: int


class UnresolvedReference(BaseModel):
    """One `:ref:`/`:external:ref:` target that is not a known document id
    (lot 6, I4) — never merged with a resolvable edge, never dropped."""

    model_config = ConfigDict(frozen=True)

    source_document_id: str
    raw_target: str
    count: int


class CrossReferenceGraphResult(BaseModel):
    """Result of `aster-expert sources xref` (docs/development-plan.md, lot 6, I4)."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    source_name: str
    source_commit: str
    total_references: int
    resolvable_references: int
    unresolvable_references: int
    edges: tuple[CrossReferenceEdge, ...]
    unresolved: tuple[UnresolvedReference, ...]


class RstProbeReport(BaseModel):
    """Result of `aster-expert sources probe` (docs/development-plan.md, lot 6, I3)."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    source_name: str
    source_commit: str
    sample_per_family: dict[str, tuple[str, ...]]
    sampled_documents: int
    sampled_files: int
    raw_chars: int
    recoverable_chars: int
    recovery_ratio: float
    parse_errors: tuple[str, ...]
    unknown_directives: tuple[ProbeFrequency, ...]
    unknown_roles: tuple[ProbeFrequency, ...]
    unresolved_includes: tuple[ProbeFrequency, ...]
    conf_py_extensions: tuple[str, ...]
