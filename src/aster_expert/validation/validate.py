"""Level B static validation orchestration (docs/development-plan.md, lot 10).

Ties the lot 9 parser, the lot 4/4b catalogue, and `checkCommandSyntax`
together without reimplementing any of their logic:

1. resolve which extracted catalogue (digest) to validate against;
2. parse the `.comm` file (lot 9, never executed);
3. build the concept -> Aster type table (M1, `concept_types.py`);
4. plan which statements can be checked at all, and reconstruct their
   arguments for the ones that can (M2, `reconstruct.py`);
5. call `checkCommandSyntax` on all of them in one container invocation
   (M3, `checker_client.py`);
6. translate whatever it decided into `docs/metadata.md` section 4 entries
   (M4, `error_mapping.py`).
"""

from __future__ import annotations

import difflib
from datetime import UTC, datetime
from pathlib import Path

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import (
    CommandSchema,
    FactorKeywordSchema,
    KeywordSchema,
)
from aster_expert.catalogue.query import (
    find_keyword_variants,
    load_command_schema,
    resolve_active_digest,
)
from aster_expert.parsing.comm_parser import parse_comm_file
from aster_expert.parsing.errors import CommParseError
from aster_expert.validation.checker_client import run_checks
from aster_expert.validation.concept_types import build_concept_type_table
from aster_expert.validation.error_mapping import (
    classify,
    extract_keyword,
    strip_stack_prefix,
)
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.models import (
    CheckedEntry,
    NotCheckedEntry,
    ValidationFinding,
    ValidationReport,
)
from aster_expert.validation.reconstruct import CheckRequest, Excluded, plan_statements


def _peek_schema(catalogue_root: Path, digest: str) -> CommandSchema:
    """Load any one command schema for a digest, to read its shared fields.

    `aster_version` and `catalogue_hash` are identical across every command
    of one extraction (docs/metadata.md, section 2) — any single file gives
    both without a dedicated summary file.
    """
    digest_dir = catalogue_root / digest
    first = next(iter(sorted(digest_dir.glob("*.json"))), None)
    if first is None:
        message = f"no extracted command schema under {digest_dir}"
        raise ValidationRunError(message)
    return CommandSchema.model_validate_json(first.read_text(encoding="utf-8"))


def resolve_digest_for_version(
    catalogue_root: Path, version: str | None, versions_path: Path
) -> tuple[str, str]:
    """Resolve (digest, aster_version).

    Without `--version`, uses the last environment detected
    (`config/versions.yaml`, `detected` section — same source
    `catalogue show` uses). With `--version`, only ever matches an already
    *extracted* catalogue (never a freshly resolved image): scans
    `catalogue_root` for a digest whose extraction recorded that exact
    version string, and fails explicitly rather than guess if none, or more
    than one, matches.
    """
    if version is None:
        if not catalogue_root.is_dir():
            message = f"no extracted catalogue at {catalogue_root}"
            raise ValidationRunError(message)
        try:
            digest = resolve_active_digest(versions_path)
        except CatalogueExtractionError as exc:
            raise ValidationRunError(str(exc)) from exc
        return digest, _peek_schema(catalogue_root, digest).aster_version

    if not catalogue_root.is_dir():
        message = f"no extracted catalogue at {catalogue_root}"
        raise ValidationRunError(message)

    candidates: list[str] = []
    for digest_dir in sorted(catalogue_root.iterdir()):
        if not digest_dir.is_dir():
            continue
        try:
            schema = _peek_schema(catalogue_root, digest_dir.name)
        except ValidationRunError:
            continue
        if schema.aster_version == version:
            candidates.append(digest_dir.name)

    if not candidates:
        message = (
            f"no extracted catalogue found for version {version!r} under "
            f"{catalogue_root}; run `aster-expert catalogue extract` with "
            "that version's environment first"
        )
        raise ValidationRunError(message)
    if len(candidates) > 1:
        message = (
            f"more than one extracted catalogue matches version {version!r}: "
            f"{candidates}; refusing to guess which one to validate against"
        )
        raise ValidationRunError(message)
    return candidates[0], version


def _collect_keyword_names(entries: list[KeywordSchema]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        names.add(entry.path[-1])
        if isinstance(entry, FactorKeywordSchema):
            names.update(_collect_keyword_names(entry.children))
    return names


def _suggest(candidate: str, pool: set[str]) -> str | None:
    matches = difflib.get_close_matches(candidate, sorted(pool), n=1, cutoff=0.6)
    return matches[0] if matches else None


def _build_finding(
    statement_index: int,
    command: str,
    line: int,
    outcome: dict[str, object],
    *,
    catalogue_root: Path,
    digest: str,
    schema_cache: dict[str, CommandSchema | None],
) -> ValidationFinding:
    orig = str(outcome.get("orig", ""))
    raw_message = str(outcome.get("message", ""))
    stack = outcome.get("stack")

    if orig == "UnknownCommand":
        names = {p.stem for p in (catalogue_root / digest).glob("*.json")}
        return ValidationFinding(
            code="UNKNOWN_COMMAND",
            command=command,
            statement_index=statement_index,
            line=line,
            path=[],
            variant_id=None,
            message=raw_message,
            suggestion=_suggest(command, names),
            source="catalogue",
        )

    message = strip_stack_prefix(raw_message)
    code = classify(message)
    if isinstance(stack, str) and stack:
        path = stack.split("/")
    else:
        keyword = extract_keyword(message)
        path = [keyword] if keyword else []

    if command not in schema_cache:
        try:
            schema_cache[command] = load_command_schema(catalogue_root, digest, command)
        except CatalogueExtractionError:
            schema_cache[command] = None
    schema = schema_cache[command]

    suggestion = None
    if code == "UNKNOWN_KEYWORD" and schema is not None:
        bad_keyword = extract_keyword(message)
        if bad_keyword:
            suggestion = _suggest(
                bad_keyword, _collect_keyword_names(list(schema.keywords))
            )

    variant_id = None
    if path and schema is not None:
        try:
            variants = find_keyword_variants(schema, path)
        except CatalogueExtractionError:
            variants = []
        if len(variants) == 1:
            variant_id = variants[0].variant_id

    return ValidationFinding(
        code=code,
        command=command,
        statement_index=statement_index,
        line=line,
        path=path,
        variant_id=variant_id,
        message=message,
        suggestion=suggestion,
        source="checkCommandSyntax",
    )


def validate_comm_file(
    comm_path: Path,
    *,
    project_root: Path,
    workroot: Path,
    docker_bin: Path,
    version: str | None = None,
    image_repository: str = "simvia/code_aster",
    network: str = "none",
    memory: str | None = None,
    cpus: str | None = None,
    timeout: int = 300,
) -> ValidationReport:
    catalogue_root = project_root / "data" / "processed" / "catalogue"
    versions_path = project_root / "config" / "versions.yaml"

    digest, aster_version = resolve_digest_for_version(
        catalogue_root, version, versions_path
    )

    try:
        analysis = parse_comm_file(comm_path)
    except CommParseError as exc:
        raise ValidationRunError(str(exc)) from exc

    concept_types, concept_warnings = build_concept_type_table(
        analysis, catalogue_root=catalogue_root, digest=digest
    )
    requests, excluded, matched_warning_ids = plan_statements(analysis, concept_types)

    image_ref = f"{image_repository}@{digest}"
    outcomes = run_checks(
        [
            {"id": r.statement_index, "command": r.command, "keywords": r.keywords}
            for r in requests
        ],
        image_ref=image_ref,
        workroot=workroot,
        docker_bin=docker_bin,
        network=network,
        memory=memory,
        cpus=cpus,
        timeout=timeout,
    )

    statements_by_index = {s.index: s for s in analysis.statements}
    schema_cache: dict[str, CommandSchema | None] = {}

    errors: list[ValidationFinding] = []
    checked: list[CheckedEntry] = []
    for request in requests:
        statement = statements_by_index[request.statement_index]
        outcome = outcomes.get(request.statement_index)
        if outcome is None:
            message = (
                "checker script returned no result for statement "
                f"{request.statement_index}"
            )
            raise ValidationRunError(message)
        ok = bool(outcome["ok"])
        checked.append(
            CheckedEntry(
                statement_index=statement.index,
                command=statement.command,
                line=statement.line_start,
                ok=ok,
            )
        )
        if not ok:
            errors.append(
                _build_finding(
                    statement.index,
                    statement.command,
                    statement.line_start,
                    outcome,
                    catalogue_root=catalogue_root,
                    digest=digest,
                    schema_cache=schema_cache,
                )
            )

    not_checked = [
        NotCheckedEntry(
            statement_index=e.statement_index,
            command=e.command,
            line=statements_by_index[e.statement_index].line_start,
            reasons=e.reasons,
        )
        for e in excluded
    ]

    warnings = list(concept_warnings)
    unmatched = [
        w for i, w in enumerate(analysis.parse_warnings) if i not in matched_warning_ids
    ]
    if unmatched:
        warnings.append(
            f"{len(unmatched)} lot 9 parse_warning(s) concern a construct outside any "
            "captured statement (e.g. an assignment whose target could not be "
            "represented) and are not reflected in commands_not_checked"
        )

    schema0 = _peek_schema(catalogue_root, digest)

    return ValidationReport(
        file_path=str(comm_path),
        aster_version=aster_version,
        image_digest=digest,
        validation_level="B",
        catalogue_hash=schema0.catalogue_hash,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        commands_checked=checked,
        commands_not_checked=not_checked,
        checked_at=datetime.now(UTC),
    )


__all__ = [
    "CheckRequest",
    "Excluded",
    "resolve_digest_for_version",
    "validate_comm_file",
]
