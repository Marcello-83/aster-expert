"""Level B static validation orchestration (docs/development-plan.md, lot 10/10b/10c).

Ties the lot 9 parser, the lot 4/4b catalogue, and `checkCommandSyntax`
together without reimplementing any of their logic:

1. resolve which extracted catalogue (digest) to validate against;
2. parse the `.comm` file (lot 9, never executed);
3. plan which statements can even be attempted, and reconstruct their
   arguments for the ones that can (M2, `reconstruct.py`);
4. build the ordered, file-order dispatch payload sent to the container in
   one invocation (`_build_dispatch_payload`, lot 10c point P1): a
   `"check"`-mode item per non-excluded statement, confronted with
   `checkCommandSyntax`, *and* a `"type_probe"`-mode item per excluded
   statement that still produces a concept, to let a static-typed
   placeholder register regardless (M3, `checker_client.py` /
   `scripts/check_command_syntax.py`);
5. translate whatever it decided into `docs/metadata.md` section 4 entries
   (M4, `error_mapping.py`), routing the outcomes that are not really a
   syntax verdict (command absent from the live catalogue but explicitly
   imported, a non-`Command` catalogue object, an unresolved concept
   dependency, or — lot 10c point P2 — a verified `checkCommandSyntax`
   *tool limitation* rather than a real rejection) to `commands_not_checked`
   instead of `errors`, and attaching a `CheckedEntry.warnings` entry
   whenever a statement was checked only because a concept it references
   got a placeholder from a producer that is itself in error (lot 10c point
   P1 — distinct from a producer that is merely unverified, which warrants
   no warning: docs/development-plan.md, lot 10b points D/E, lot 10c).
"""

from __future__ import annotations

import difflib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    resolve_digest_for_aster_version,
)
from aster_expert.parsing.comm_parser import parse_comm_file
from aster_expert.parsing.errors import CommParseError
from aster_expert.parsing.models import CommFileAnalysis, Statement
from aster_expert.validation.checker_client import run_checks
from aster_expert.validation.error_mapping import (
    classify,
    extract_keyword,
    match_execution_confirmed_override,
    match_tool_limitation,
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

# `outcome["orig"]` values that are never a syntax verdict -- routed to
# `commands_not_checked`, never `errors` (docs/development-plan.md, lot 10b).
_NOT_A_VERDICT = frozenset({"NonStandardCatalogueObject", "UnresolvedConcept"})


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

    try:
        digest = resolve_digest_for_aster_version(catalogue_root, version)
    except CatalogueExtractionError as exc:
        raise ValidationRunError(str(exc)) from exc
    return digest, version


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


# Commands individually confirmed, by source-level investigation, to be
# genuinely absent from a target version's catalogue -- never a typo, so a
# close-match `suggestion` here would actively mislead (docs/development-
# plan.md, lot 10c, point P4/R4). `_suggest` alone cannot tell "removed
# command" apart from "misspelled command": it is a text-distance heuristic
# with no access to the catalogue's own history, so this table only grows on
# proof, one verified name at a time, never a broad rule.
_CONFIRMED_ABSENT_COMMANDS: dict[str, str] = {
    "POST_GOUJ": (
        "command absent from the target version's catalogue -- confirmed "
        "absent from the entire code_aster 17.4.0 source tree and from the "
        "running container's own installed package (not merely unindexed: "
        "docs/development-plan.md, lot 10c, point P4), so not a typo. Git "
        "history of the upstream repository shows its catalogue definition "
        "(catapy/commande/post_gouj2e.capy, a pre-Python legacy catalogue "
        "format) deleted roughly a decade ago. The two official cas tests "
        "still calling it (astest/zzzz120a.comm, astest/zzzz120b.comm) "
        "reference a command the product no longer has: a real defect in "
        "those two corpus files, not a false positive of this tool."
    ),
}


def _producers_of(analysis: CommFileAnalysis, concept: str) -> list[int]:
    """Every statement index assigning `concept` (docs/development-plan.md, lot 10b).

    Used only to enrich an `UnresolvedConcept` outcome's reason text with
    *why* the producer was unavailable — never to resolve a type itself.
    """
    return [s.index for s in analysis.statements if s.assigned_concept == concept]


def _most_recent_producer_index(
    analysis: CommFileAnalysis, concept: str, *, before_index: int
) -> int | None:
    """The producer whose placeholder is actually live for a consumer.

    The largest statement index below `before_index` assigning `concept` —
    matching `concept_objects`' own semantics in
    `scripts/check_command_syntax.py` ("the placeholder most recently
    produced… in processing order"). `None` if no such statement exists
    (the concept is referenced before any assignment in this file — the
    existing `UnresolvedConcept` routing already covers that case; this
    helper is only ever used to enrich a *successful* lookup with the
    producer's own error/ok status, docs/development-plan.md lot 10c, point
    P1).
    """
    candidates = [
        s.index
        for s in analysis.statements
        if s.assigned_concept == concept and s.index < before_index
    ]
    return max(candidates) if candidates else None


def _referenced_concepts(value: Any) -> set[str]:
    """Every `__concept_ref__` name anywhere in a reconstructed keyword tree.

    Walks the same JSON-safe shape `aster_expert.validation.reconstruct`
    builds (dicts/lists of literals and markers) — including a `reuse=`
    marker, already folded into `keywords["reuse"]` by `reconstruct.
    plan_statement`. Used only to find which producers a *checked* statement
    directly depends on, to warn when one of them is itself in error
    (docs/development-plan.md, lot 10c, point P1) — never to resolve a type.
    """
    found: set[str] = set()
    if isinstance(value, dict):
        if "__concept_ref__" in value and len(value) == 1:
            found.add(value["__concept_ref__"])
        else:
            for v in value.values():
                found |= _referenced_concepts(v)
    elif isinstance(value, list):
        for v in value:
            found |= _referenced_concepts(v)
    return found


def _concept_at_path(keywords: Any, path: list[str]) -> str | None:
    """The concept name bound at a dotted keyword path, if any.

    Walks `keywords` (the same JSON-safe tree `reconstruct.py` builds)
    following `path` (as `CheckerError._stack`, "/"-split — a factor
    keyword's single occurrence is a plain dict, per `reconstruct.
    _reconstruct_keywords`, so no occurrence index appears in the path).
    `None` for anything but a bare `__concept_ref__` marker at that exact
    path -- used only to verify a producer command for
    `error_mapping.ExecutionConfirmedOverride` (docs/development-plan.md,
    lot 10c, point P3), never to resolve a type.
    """
    node: Any = keywords
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    if isinstance(node, dict) and "__concept_ref__" in node and len(node) == 1:
        concept: str = node["__concept_ref__"]
        return concept
    return None


def _error_dependency_warnings(
    request: CheckRequest,
    *,
    analysis: CommFileAnalysis,
    error_indices: set[int],
    statements_by_index: dict[int, Statement],
) -> list[str]:
    """Warn when a checked statement directly depends on an erroring one.

    Fires only for a concept whose most recent producer is itself in
    `errors` — never for one that is merely `commands_not_checked` (an
    excluded producer's static placeholder, if any, is just as reliable a
    catalogue fact as any other — docs/metadata.md §4, two-branch rule):
    this is exactly what keeps "non vérifié" distinct from "en erreur" in
    the report (docs/development-plan.md, lot 10c, point P1).
    """
    warnings: list[str] = []
    for concept in sorted(_referenced_concepts(request.keywords)):
        producer_index = _most_recent_producer_index(
            analysis, concept, before_index=request.statement_index
        )
        if producer_index is not None and producer_index in error_indices:
            producer = statements_by_index[producer_index]
            warnings.append(
                f"depends on concept {concept!r} produced by statement "
                f"{producer_index} ({producer.command}, line "
                f"{producer.line_start}), which is in error — never merely "
                "unverified"
            )
    return warnings


def _unresolved_concept_reason(
    message: str,
    *,
    analysis: CommFileAnalysis,
    excluded_by_index: dict[int, Excluded],
    error_indices: set[int],
) -> str:
    """Enrich an `UnresolvedConcept` message with its producer's own status."""
    # `message` is script-authored: "concept 'NAME' has no resolved placeholder..."
    name = message.split("'")[1] if message.count("'") >= 2 else None
    if name is None:
        return message
    producers = _producers_of(analysis, name)
    if not producers:
        return f"{message} (no statement in this file assigns it — unexpected)"
    details = []
    for idx in producers:
        if idx in excluded_by_index:
            details.append(
                f"statement {idx} ({excluded_by_index[idx].command}) was not "
                f"checked: {'; '.join(excluded_by_index[idx].reasons)}"
            )
        elif idx in error_indices:
            details.append(
                f"statement {idx} was checked but rejected by checkCommandSyntax"
            )
        else:
            details.append(f"statement {idx} was not reached before this one")
    return f"{message} — " + " / ".join(details)


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
        confirmed_reason = _CONFIRMED_ABSENT_COMMANDS.get(command)
        names = {p.stem for p in (catalogue_root / digest).glob("*.json")}
        return ValidationFinding(
            code="UNKNOWN_COMMAND",
            command=command,
            statement_index=statement_index,
            line=line,
            path=[],
            variant_id=None,
            message=confirmed_reason or raw_message,
            suggestion=None if confirmed_reason else _suggest(command, names),
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


def _build_dispatch_payload(
    analysis: CommFileAnalysis,
    requests: list[CheckRequest],
    excluded: list[Excluded],
) -> list[dict[str, Any]]:
    """Ordered, file-order payload sent to the container (lot 10c, point P1).

    A `CheckRequest` becomes a `"check"`-mode item, confronted with
    `checkCommandSyntax` as before. An `Excluded` statement that produces a
    concept becomes a `"type_probe"`-mode item (command name only, no
    keywords): never confronted with the checker — this statement's own
    `commands_not_checked` entry and its reasons are unaffected, decided
    solely by `reconstruct.plan_statements` above — but a chance for its
    concept's placeholder to register immediately if that command's
    `sd_prod` is static (`scripts/check_command_syntax.py`). An `Excluded`
    statement with no `assigned_concept` contributes nothing: there is no
    placeholder to register and no verdict to report either. Every
    `analysis.statements` entry is, by construction of `plan_statements`, in
    exactly one of `requests`/`excluded` — this function covers all of them.
    """
    requests_by_index = {r.statement_index: r for r in requests}
    excluded_by_index = {e.statement_index: e for e in excluded}
    payload: list[dict[str, Any]] = []
    for statement in analysis.statements:
        request = requests_by_index.get(statement.index)
        if request is not None:
            payload.append(
                {
                    "id": request.statement_index,
                    "command": request.command,
                    "assigned_concept": request.assigned_concept,
                    "keywords": request.keywords,
                    "mode": "check",
                }
            )
            continue
        excl = excluded_by_index.get(statement.index)
        if excl is not None and statement.assigned_concept is not None:
            payload.append(
                {
                    "id": statement.index,
                    "command": excl.command,
                    "assigned_concept": statement.assigned_concept,
                    "mode": "type_probe",
                }
            )
    return payload


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

    requests, excluded, matched_warning_ids = plan_statements(analysis)
    excluded_by_index = {e.statement_index: e for e in excluded}

    image_ref = f"{image_repository}@{digest}"
    outcomes: dict[int, dict[str, Any]] = run_checks(
        _build_dispatch_payload(analysis, requests, excluded),
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
    not_checked: list[NotCheckedEntry] = [
        NotCheckedEntry(
            statement_index=e.statement_index,
            command=e.command,
            line=statements_by_index[e.statement_index].line_start,
            reasons=e.reasons,
        )
        for e in excluded
    ]
    error_indices: set[int] = set()

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
        orig = str(outcome.get("orig", "")) if not ok else ""

        if (
            not ok
            and orig == "UnknownCommand"
            and statement.command in (analysis.imported_names)
        ):
            not_checked.append(
                NotCheckedEntry(
                    statement_index=statement.index,
                    command=statement.command,
                    line=statement.line_start,
                    reasons=[
                        f"'{statement.command}' is explicitly imported in this "
                        "file but absent from the extracted catalogue: it is "
                        "not part of code_aster.Cata.Commands (lives outside "
                        "it, e.g. in code_aster.MacroCommands — "
                        "docs/development-plan.md, lot 4/10b) and was never "
                        "introspected, so it cannot be confronted with a "
                        "schema"
                    ],
                )
            )
            continue

        if not ok and orig in _NOT_A_VERDICT:
            message = str(outcome.get("message", ""))
            if orig == "UnresolvedConcept":
                message = _unresolved_concept_reason(
                    message,
                    analysis=analysis,
                    excluded_by_index=excluded_by_index,
                    error_indices=error_indices,
                )
            not_checked.append(
                NotCheckedEntry(
                    statement_index=statement.index,
                    command=statement.command,
                    line=statement.line_start,
                    reasons=[message],
                )
            )
            continue

        if not ok:
            stripped_message = strip_stack_prefix(str(outcome.get("message", "")))
            tool_limitation_reason = match_tool_limitation(
                statement.command, stripped_message
            )
            if tool_limitation_reason is not None:
                # A verified checkCommandSyntax limitation, not a real
                # rejection (docs/development-plan.md, lot 10c, point P2):
                # routed to commands_not_checked, never errors — this
                # statement was never really "checked" in the sense that
                # matters for error_indices/P1's dependency warnings either.
                not_checked.append(
                    NotCheckedEntry(
                        statement_index=statement.index,
                        command=statement.command,
                        line=statement.line_start,
                        reasons=[tool_limitation_reason],
                    )
                )
                continue

            override = match_execution_confirmed_override(
                statement.command, outcome.get("stack"), stripped_message
            )
            if override is not None:
                producer_concept = _concept_at_path(
                    request.keywords, override.stack.split("/")
                )
                producer_index = (
                    _most_recent_producer_index(
                        analysis, producer_concept, before_index=statement.index
                    )
                    if producer_concept is not None
                    else None
                )
                producer_command = (
                    statements_by_index[producer_index].command
                    if producer_index is not None
                    else None
                )
                if producer_command == override.required_producer_command:
                    # Execution-confirmed false positive of this project's
                    # own static check, never of checkCommandSyntax itself
                    # (docs/development-plan.md, lot 10c, point P3): reported
                    # as checked+valid, with a warning naming the evidence —
                    # never silently dropped, never counted as an error.
                    checked.append(
                        CheckedEntry(
                            statement_index=statement.index,
                            command=statement.command,
                            line=statement.line_start,
                            ok=True,
                            warnings=[
                                override.reason,
                                *_error_dependency_warnings(
                                    request,
                                    analysis=analysis,
                                    error_indices=error_indices,
                                    statements_by_index=statements_by_index,
                                ),
                            ],
                        )
                    )
                    continue

        checked.append(
            CheckedEntry(
                statement_index=statement.index,
                command=statement.command,
                line=statement.line_start,
                ok=ok,
                warnings=_error_dependency_warnings(
                    request,
                    analysis=analysis,
                    error_indices=error_indices,
                    statements_by_index=statements_by_index,
                ),
            )
        )
        if not ok:
            error_indices.add(statement.index)
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

    not_checked.sort(key=lambda e: e.statement_index)

    warnings: list[str] = []
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
