"""MCP tool implementations (lot 8) — a wrapper, never a new capability.

Every function below composes modules that already exist and are already
tested (`aster_expert.retrieval`, `.catalogue`, `.parsing`, `.validation`),
in exactly the same way `aster_expert.cli` does — no ranking, chunking,
catalogue-extraction, or validation logic is added or altered here
(CLAUDE.md, lot 8 scope). `aster_expert.mcp.server` is the only caller; it
carries no logic of its own beyond reading environment variables and
registering these functions as MCP tools, so every behavior described here
is reachable, and testable, without an MCP transport at all.

Every function journals its own call (`aster_expert.mcp.logging`) before
returning, timed with `time.monotonic()` around the actual work only —
loading the environment or resolving paths is not counted. A caller that
supplies something this layer cannot serve (an unknown profile, mode or
granularity, a missing index, a missing work root, a path that fails to
parse or validate) gets an `McpToolError` carrying the real, specific
reason: the underlying package's own error message is never swallowed
(CLAUDE.md, "ne jamais neutraliser une alarme sans en expliquer la cause").
A malformed *response* — this project's own bug, not a caller mistake — is
deliberately left to raise whatever pydantic or the underlying module
itself raises: the MCP SDK turns that into a loud `UnexpectedToolError`
rather than a partial result (docs/development-plan.md, lot 8, H5).
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.query import (
    find_keyword_variants,
    load_command_schema,
    resolve_active_digest,
    resolve_digest_for_aster_version,
)
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.indexing.bm25_index import default_index_dir, load_bm25_index
from aster_expert.mcp.errors import McpToolError
from aster_expert.mcp.logging import (
    ReturnedItem,
    append_query_log,
    default_query_log_path,
)
from aster_expert.mcp.models import (
    CommAnalysisResult,
    CommandSchemaResult,
    SearchDocsResult,
)
from aster_expert.parsing.comm_parser import parse_comm_file
from aster_expert.parsing.errors import CommParseError
from aster_expert.parsing.fragment_models import FragmentGranularity
from aster_expert.retrieval.query_profiles import DEFAULT_QUERY_PROFILE
from aster_expert.retrieval.source_priority import (
    SourcePriorityMode,
    hard_filter_search,
    load_source_priority,
    soft_reweight_search,
)
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.models import ValidationReport
from aster_expert.validation.validate import validate_comm_file

_GRANULARITIES: tuple[FragmentGranularity, ...] = ("by_file", "by_subsection")
_PRIORITY_MODES: tuple[SourcePriorityMode, ...] = ("hard", "soft")


def search_codeaster_docs(
    *,
    project_root: Path,
    query: str,
    profile: str = DEFAULT_QUERY_PROFILE,
    k: int = 10,
    granularity: str = "by_file",
    priority_mode: str = "soft",
    version: str | None = None,
    family: str | None = None,
    document_id: str | None = None,
    command: str | None = None,
    section_contains: str | None = None,
    log_path: Path | None = None,
) -> SearchDocsResult:
    """Rank indexed documentary fragments against `query` (lot 7/7b/7c, wrapped).

    `profile` is always taken as given, never inferred from `query` itself
    (ADR-007, docs/architecture.md): the tool description in
    `aster_expert.mcp.server` is where a caller is told how to choose one.
    """
    if granularity not in _GRANULARITIES:
        message = f"Granularité inconnue : {granularity!r} ; attendu {_GRANULARITIES}"
        raise McpToolError(message)
    if priority_mode not in _PRIORITY_MODES:
        message = (
            f"Mode de priorité inconnu : {priority_mode!r} ; attendu {_PRIORITY_MODES}"
        )
        raise McpToolError(message)

    retrieval_config_path = project_root / "config" / "retrieval.yaml"
    source_priority = load_source_priority(retrieval_config_path)
    if profile not in source_priority:
        message = (
            f"Profil inconnu : {profile!r} ; profils déclarés dans "
            f"config/retrieval.yaml : {sorted(source_priority)}"
        )
        raise McpToolError(message)
    priority_families = source_priority[profile]

    index_dir = default_index_dir(project_root, granularity)
    if not index_dir.is_dir():
        message = (
            f"Index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord"
        )
        raise McpToolError(message)

    started = time.monotonic()
    retriever, corpus = load_bm25_index(index_dir)
    priority_search = (
        hard_filter_search if priority_mode == "hard" else soft_reweight_search
    )
    hits = priority_search(
        retriever,
        corpus,
        query,
        k=k,
        priority_families=priority_families,
        version=version,
        family=family,
        document_id=document_id,
        command=command,
        section_contains=section_contains,
    )
    duration = time.monotonic() - started

    result = SearchDocsResult(
        query=query,
        profile=profile,
        priority_families=priority_families,
        priority_mode=priority_mode,
        results=hits,
    )

    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="search_codeaster_docs",
        query=query,
        profile=profile,
        filters={
            "granularity": granularity,
            "priority_mode": priority_mode,
            "k": str(k),
            "version": version,
            "family": family,
            "document_id": document_id,
            "command": command,
            "section_contains": section_contains,
        },
        returned=[
            ReturnedItem(identifier=hit.fragment_id, score=hit.score) for hit in hits
        ],
        duration_s=duration,
    )
    return result


def get_command_schema(
    *,
    project_root: Path,
    command: str,
    keyword: str | None = None,
    version: str | None = None,
    log_path: Path | None = None,
) -> CommandSchemaResult:
    """Exact command schema from the extracted catalogue (lot 4/4b, wrapped)."""
    versions_path = project_root / "config" / "versions.yaml"
    catalogue_root = project_root / "data" / "processed" / "catalogue"

    started = time.monotonic()
    try:
        digest = (
            resolve_digest_for_aster_version(catalogue_root, version)
            if version is not None
            else resolve_active_digest(versions_path)
        )
        schema = load_command_schema(catalogue_root, digest, command)
        variants = (
            find_keyword_variants(schema, keyword.split(".")) if keyword else None
        )
    except CatalogueExtractionError as exc:
        raise McpToolError(str(exc)) from exc
    duration = time.monotonic() - started

    result = CommandSchemaResult(command_schema=schema, keyword_variants=variants)

    returned = (
        [
            ReturnedItem(identifier=f"{command}.{'.'.join(v.path)}#{v.variant_id}")
            for v in variants
        ]
        if variants is not None
        else [ReturnedItem(identifier=command)]
    )
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="get_command_schema",
        query=f"{command}.{keyword}" if keyword else command,
        filters={"version": version, "keyword": keyword},
        returned=returned,
        duration_s=duration,
    )
    return result


def analyze_comm(
    *,
    project_root: Path,
    comm_path: str,
    log_path: Path | None = None,
) -> CommAnalysisResult:
    """Structural analysis of a `.comm` file, never executed (lot 9, wrapped)."""
    path = Path(comm_path)

    started = time.monotonic()
    try:
        analysis = parse_comm_file(path)
    except CommParseError as exc:
        raise McpToolError(str(exc)) from exc
    duration = time.monotonic() - started

    # Only the file's name and content fingerprint are journaled, never its
    # text or any value derived from its content (lot 8, H3).
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="analyze_comm",
        duration_s=duration,
        file_name=path.name,
        file_fingerprint=analysis.file_hash,
    )
    return CommAnalysisResult(analysis=analysis)


def validate_comm(
    *,
    project_root: Path,
    comm_path: str,
    version: str | None = None,
    workroot: Path | None,
    docker_bin_env: str | None = None,
    image_repository: str = "simvia/code_aster",
    network: str = "none",
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 1800,
    log_path: Path | None = None,
) -> ValidationReport:
    """Level B validation against the target catalogue (lot 10/10b/10c, wrapped).

    `ValidationReport.validation_level` is always `"B"` already
    (`aster_expert.validation.models`): this wrapper returns the report as
    it is produced, never re-wrapped, so H2's "the level travels with the
    response" holds without a second, redundant field.
    """
    path = Path(comm_path)
    if not path.is_file():
        message = f"Fichier introuvable : {path}"
        raise McpToolError(message)
    if workroot is None:
        message = (
            "ASTER_CONTAINER_WORKROOT n'est pas renseigné : aucune validation "
            "n'est autorisée sans répertoire de travail dédié (voir .env.example)."
        )
        raise McpToolError(message)

    fingerprint = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"

    try:
        docker_bin = find_docker_binary(docker_bin_env)
    except EnvironmentDetectionError as exc:
        raise McpToolError(str(exc)) from exc

    started = time.monotonic()
    try:
        report = validate_comm_file(
            path,
            project_root=project_root,
            workroot=workroot,
            docker_bin=docker_bin,
            version=version,
            image_repository=image_repository,
            network=network,
            memory=memory,
            cpus=cpus,
            timeout=timeout,
        )
    except (EnvironmentDetectionError, ValidationRunError) as exc:
        raise McpToolError(str(exc)) from exc
    duration = time.monotonic() - started

    # Only the file's name and content fingerprint are journaled, never its
    # text (lot 8, H3).
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="validate_comm",
        filters={"version": version},
        duration_s=duration,
        file_name=path.name,
        file_fingerprint=fingerprint,
    )
    return report


__all__: list[str] = [
    "analyze_comm",
    "get_command_schema",
    "search_codeaster_docs",
    "validate_comm",
]
