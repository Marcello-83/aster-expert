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

`search_codeaster_docs`, `get_document_section` and `get_command_schema`
read the BM25 index and the command catalogue through `aster_expert.mcp.
cache` rather than the raw `load_bm25_index`/`load_command_schema` (lot 8b,
J1: the first measured `search_codeaster_docs` call reloaded the index from
disk every time, 5.2 s) — still no ranking or catalogue logic added, only
the disk read itself is memoized for the server process's lifetime.
`get_document_section` (lot 8c, K1) reuses that same cached corpus rather
than re-reading the fragments JSONL a second time: the corpus entry's
`content` field already is the fragment's exact raw text
(`aster_expert.indexing.bm25_index.build_bm25_index`), so there is no
second source of that text to keep in sync.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from pathlib import Path

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.query import (
    find_keyword_variants,
    resolve_active_digest,
    resolve_digest_for_aster_version,
)
from aster_expert.execution.docker_client import find_docker_binary
from aster_expert.execution.errors import EnvironmentDetectionError
from aster_expert.indexing.bm25_index import (
    default_index_dir,
    find_fragments,
    to_document_section,
)
from aster_expert.mcp.cache import cached_bm25_index, cached_command_schema
from aster_expert.mcp.errors import McpToolError
from aster_expert.mcp.logging import (
    ReturnedItem,
    append_query_log,
    default_query_log_path,
)
from aster_expert.mcp.models import (
    CommAnalysisResult,
    CommandSchemaResult,
    ConstatHitResult,
    DocumentSectionResult,
    SearchConstatsResult,
    SearchDocsResult,
)
from aster_expert.mcp.testcases import (
    SearchTestcasesResult,
    TestcaseFileResult,
    read_testcase,
    resolve_corpus,
    search_testcases,
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
    retriever, corpus = cached_bm25_index(index_dir)
    if family is not None:
        # An unknown family would otherwise return an empty result with no
        # explanation (lot 21: `family="testcase"`, absent from the index).
        families = sorted({str(fragment.get("family")) for fragment in corpus})
        if family not in families:
            message = (
                f"Famille inconnue : {family!r} ; familles présentes dans "
                f"l'index ({granularity}) : {families}. Les cas tests ne sont pas "
                "indexés ici : les chercher par search_test_cases."
            )
            raise McpToolError(message)
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


def get_document_section(
    *,
    project_root: Path,
    fragment_id: str | None = None,
    document_id: str | None = None,
    section_path: Sequence[str] | None = None,
    granularity: str = "by_file",
    line_start: int | None = None,
    line_end: int | None = None,
    log_path: Path | None = None,
) -> DocumentSectionResult:
    """Text of one fragment, by default whole (lot 8c, K1; ranged, lot 14, L1).

    Chains directly off `search_codeaster_docs`: every `SearchHit` already
    carries the exact `fragment_id`, `document_id`, `section_path` and
    `granularity` this tool needs (K2) -- no identifier has to be
    reconstructed by hand. `SearchHit.excerpt` is capped at 280 characters
    (`aster_expert.indexing.bm25_index._EXCERPT_CHARS`), fine for a ranked
    list of many candidates but never enough to found an answer on a
    section's actual body (a comparison table, a validity domain, a list of
    conditions): this tool is the only one that returns a section whole, and
    reports its size rather than ever cutting it silently.

    `line_start`/`line_end` (both required together, absolute source-file
    lines, matching `DocumentSection.line_start`/`.line_end`) narrow the
    request to a sub-range -- needed once a fragment is itself too large
    for one response (`aster_expert.indexing.bm25_index.
    _DEFAULT_MAX_SECTION_CHARS`, lot 14): `DocumentSection.outline` and
    `.guidance` then explain exactly which ranges exist and how to request
    them, rather than a silent cut.
    """
    if granularity not in _GRANULARITIES:
        message = f"Granularité inconnue : {granularity!r} ; attendu {_GRANULARITIES}"
        raise McpToolError(message)

    has_fragment_id = fragment_id is not None
    has_document_id = document_id is not None
    has_section_path = section_path is not None
    if has_fragment_id and (has_document_id or has_section_path):
        message = (
            "Donner soit fragment_id, soit document_id et section_path "
            "ensemble, jamais les deux façons à la fois."
        )
        raise McpToolError(message)
    if not has_fragment_id and (has_document_id != has_section_path):
        message = "document_id et section_path doivent être donnés ensemble."
        raise McpToolError(message)
    if not has_fragment_id and not has_document_id:
        message = "fragment_id, ou document_id et section_path, sont requis."
        raise McpToolError(message)

    index_dir = default_index_dir(project_root, granularity)
    if not index_dir.is_dir():
        message = (
            f"Index introuvable ({index_dir}) ; lancez "
            f"'aster-expert index build --granularity {granularity}' d'abord"
        )
        raise McpToolError(message)

    section_path_tuple = tuple(section_path) if section_path is not None else None

    started = time.monotonic()
    _, corpus = cached_bm25_index(index_dir)
    matches = find_fragments(
        corpus,
        fragment_id=fragment_id,
        document_id=document_id,
        section_path=section_path_tuple,
    )
    target = (
        fragment_id
        if has_fragment_id
        else f"{document_id}#{'/'.join(section_path_tuple or ())}"
    )
    if not matches:
        message = (
            f"Aucun fragment ne correspond à {target!r} dans l'index "
            f"{granularity!r} ({index_dir})."
        )
        raise McpToolError(message)
    if len(matches) > 1:
        message = (
            f"Plusieurs fragments correspondent à {target!r} dans l'index "
            f"{granularity!r} : identifiant ambigu, jamais résolu en "
            "silence -- utilisez fragment_id."
        )
        raise McpToolError(message)
    try:
        section = to_document_section(
            matches[0], line_start=line_start, line_end=line_end
        )
    except ValueError as exc:
        raise McpToolError(str(exc)) from exc
    duration = time.monotonic() - started

    result = DocumentSectionResult(section=section)

    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="get_document_section",
        query=target,
        filters={"granularity": granularity},
        returned=[ReturnedItem(identifier=section.fragment_id)],
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
        schema = cached_command_schema(catalogue_root, digest, command)
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

    if not workroot.is_dir():
        message = (
            f"Le répertoire de travail ASTER_CONTAINER_WORKROOT n'existe pas : "
            f"{workroot}. Le créer (ou corriger la variable dans .mcp.json) ; "
            "un répertoire sous /tmp disparaît au redémarrage de la machine."
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


def search_test_cases(
    *,
    project_root: Path,
    command: str,
    keyword: str | None = None,
    limit: int = 50,
    log_path: Path | None = None,
) -> SearchTestcasesResult:
    """Test-case command files using `command` (and `keyword`), level A (lot 22).

    Structural match through the project's parser, at the corpus commit the
    synchronisation manifest recorded; read-only.
    """
    started = time.monotonic()
    root, source = resolve_corpus(project_root)
    result = search_testcases(
        root, source, command=command, keyword=keyword, limit=limit
    )
    duration = time.monotonic() - started
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="search_test_cases",
        query=f"{command}.{keyword}" if keyword else command,
        filters={
            "keyword": keyword,
            "limit": str(limit),
            "source_commit": source.source_commit,
        },
        returned=[ReturnedItem(identifier=hit.path) for hit in result.results],
        duration_s=duration,
    )
    return result


def read_test_case(
    *,
    project_root: Path,
    path: str,
    line_start: int | None = None,
    line_end: int | None = None,
    log_path: Path | None = None,
) -> TestcaseFileResult:
    """One test-case command file, whole under a threshold, else by range (lot 22).

    A path outside the corpus root, or not a command file, is refused.
    """
    started = time.monotonic()
    root, source = resolve_corpus(project_root)
    result = read_testcase(
        root, source, path=path, line_start=line_start, line_end=line_end
    )
    duration = time.monotonic() - started
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="read_test_case",
        query=path,
        filters={
            "line_start": None if line_start is None else str(line_start),
            "line_end": None if line_end is None else str(line_end),
            "source_commit": source.source_commit,
        },
        returned=[ReturnedItem(identifier=result.path)],
        duration_s=duration,
    )
    return result


__all__: list[str] = [
    "analyze_comm",
    "get_command_schema",
    "get_document_section",
    "read_test_case",
    "search_codeaster_docs",
    "search_test_cases",
    "validate_comm",
]


def search_constats(
    *,
    project_root: Path,
    text: str | None = None,
    command: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
    log_path: Path | None = None,
) -> SearchConstatsResult:
    """Findings of the shared base concerning a command, a keyword or a text
    (lot 41), level A: a reading of `connaissances/constats_code_aster/`, each hit
    with the level the finding itself reached."""
    from aster_expert.constats.base import (  # noqa: PLC0415
        BASE_RELATIVE,
        base_dir,
        constat_path,
        load_base,
    )
    from aster_expert.constats.search import search_constats as _search  # noqa: PLC0415

    started = time.monotonic()
    base = load_base(base_dir(project_root))
    hits = _search(base, text=text, command=command, keyword=keyword, limit=limit)
    results = [
        ConstatHitResult(
            constat_id=h.constat.constat_id,
            summary=h.constat.summary,
            topic=h.constat.entry.topic,
            option_retained=h.constat.entry.option_retained,
            constat_validation_level=h.constat.validation_level,
            aster_version=h.constat.aster_version,
            commands=h.constat.commands,
            keywords=h.constat.keywords,
            trial_cases=tuple(c.case_path for c in h.constat.trial_cases),
            origin_project=h.constat.origin.project,
            file=constat_path(BASE_RELATIVE, h.constat.constat_id).as_posix(),
            score=h.score,
        )
        for h in hits
    ]
    duration = time.monotonic() - started
    append_query_log(
        log_path if log_path is not None else default_query_log_path(project_root),
        tool="search_constats",
        query=text,
        filters={"command": command, "keyword": keyword, "limit": str(limit)},
        returned=[
            ReturnedItem(identifier=r.constat_id, score=float(r.score)) for r in results
        ],
        duration_s=duration,
    )
    return SearchConstatsResult(
        text=text,
        command=command,
        keyword=keyword,
        total_in_base=len(base),
        results=results,
        guidance=(
            "Un constat est un fait établi sur Code_Aster (catalogue, documentation "
            "ou exécution d'un cas d'essai versionné), valable pour la version "
            "indiquée. Lire le fichier du constat pour ses sources avant de "
            "s'appuyer dessus ; un constat de niveau A ou B n'a pas été éprouvé par "
            "exécution."
        ),
    )
