"""Structural parsing of a `.comm` file, without ever executing it.

A `.comm` file is syntactically plain Python (docs/architecture.md, section
5): `ast.parse` gives a full tree without running any of it. This module
walks that tree to recover the command structure described in
docs/metadata.md, section 3 — commands, concepts produced and referenced,
factor/simple keywords, literal groups, modelisations, phenomena,
behaviours, logical units — while resolving every keyword value it can via
`ast.literal_eval` and marking, explicitly, everything it cannot.

No regular-expression parsing, no `exec`, no `import` of the analyzed file
(docs/development-plan.md, lot 9). No construct is ever silently dropped: an
`ast` node type this module does not model produces an entry in
`parse_warnings` (CLAUDE.md, principle 9), and an argument that is not
statically resolvable makes its statement `dynamic` with an explicit
`unresolved` entry, never a guess (docs/development-plan.md, lot 9 note).

This module does not evaluate Aster `Bloc` conditions (the
`is_in`/`equal_to`/`value`/`not` mini-language lives in the catalogue's
Python source, not in `.comm` files, and selecting a variant from it is lot
10's job, not lot 9's — see docs/development-plan.md).
"""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeGuard

from aster_expert.parsing.errors import CommParseError
from aster_expert.parsing.models import (
    CommFileAnalysis,
    ConceptReferenceValue,
    DynamicReason,
    DynamicValue,
    ExternalFileRef,
    FactorKeywordValue,
    FactorOccurrence,
    KeywordNode,
    LiteralValue,
    ParseWarning,
    SimpleKeywordValue,
    SimpleValue,
    Statement,
)

_COMMAND_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass
class _RawStatement:
    node: ast.stmt
    call: ast.Call
    command: str
    assigned_concept: str | None
    control_flow: list[str]


# Control-flow containers a name definition can sit inside while still being
# bound at module scope (matches the containers `_collect_statements` itself
# recurses into) -- a `FunctionDef`/`ClassDef`/`AsyncFunctionDef` is never
# descended into further: its body is a separate Python scope.
_CONTROL_FLOW_BODIES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)


def _collect_shadowing_names(body: list[ast.stmt]) -> set[str]:
    """Names a call to which is never a Code_Aster command (lot 10b, point C).

    A real Code_Aster command is always imported from `code_aster.Commands`
    (or a sibling package), never defined by the `.comm` file itself. A call
    whose name matches a class, a function, or a plain module-level variable
    that *this file* defines shadows that identifier regardless of its case
    (the file's own definition always wins) and is therefore never a command
    -- this is exactly the lot 9 heuristic's false-positive source this
    amendment fixes: it previously matched any `NAME(...)` call against
    `_COMMAND_NAME_RE` with no regard for what `NAME` actually was bound to.

    Deliberately excludes `import`/`from ... import ...` bindings: unlike a
    locally-defined name, an imported one is exactly how a real command
    reaches the file in the first place (`from code_aster.Commands import
    STAT_NON_LINE`), so importing a name must never disqualify it.
    """
    names: set[str] = set()
    for node in body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(_names_in_target(target))
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            names.update(_names_in_target(node.target))
        elif isinstance(node, ast.For | ast.AsyncFor):
            names.update(_names_in_target(node.target))
            names |= _collect_shadowing_names(node.body)
            names |= _collect_shadowing_names(node.orelse)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                if item.optional_vars is not None:
                    names.update(_names_in_target(item.optional_vars))
            names |= _collect_shadowing_names(node.body)
        elif isinstance(node, ast.If | ast.While):
            names |= _collect_shadowing_names(node.body)
            names |= _collect_shadowing_names(node.orelse)
        elif isinstance(node, ast.Try):
            names |= _collect_shadowing_names(node.body)
            for handler in node.handlers:
                names |= _collect_shadowing_names(handler.body)
            names |= _collect_shadowing_names(node.orelse)
            names |= _collect_shadowing_names(node.finalbody)
    return names


def _names_in_target(target: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(target) if isinstance(n, ast.Name)}


def _collect_imported_names(body: list[ast.stmt]) -> set[str]:
    """Names explicitly bound by `import`/`from ... import ...` (lot 10b, point D).

    A wildcard `from ... import *` contributes nothing here: its members
    cannot be enumerated without executing the file, and CLAUDE.md forbids
    guessing them.
    """
    names: set[str] = set()
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name)
        elif isinstance(node, _CONTROL_FLOW_BODIES):
            for field in ("body", "orelse", "finalbody"):
                names |= _collect_imported_names(getattr(node, field, []) or [])
            for handler in getattr(node, "handlers", []) or []:
                names |= _collect_imported_names(handler.body)
    return names


@dataclass
class _ResolveContext:
    known_concepts: set[str]
    loop_names: set[str]
    warnings: list[ParseWarning]


@dataclass
class _Aggregates:
    mesh_groups: set[str] = field(default_factory=set)
    node_groups: set[str] = field(default_factory=set)
    modelisations: set[str] = field(default_factory=set)
    phenomena: set[str] = field(default_factory=set)
    behaviours: set[str] = field(default_factory=set)
    logical_units: set[int] = field(default_factory=set)
    referenced_concepts: set[str] = field(default_factory=set)
    unresolved: list[str] = field(default_factory=list)
    dynamic: bool = False


def parse_comm_file(path: Path) -> CommFileAnalysis:
    """Parse a `.comm` file from disk. The file is read, never executed."""
    if not path.is_file():
        message = f"file not found: {path}"
        raise CommParseError(message)
    raw_bytes = path.read_bytes()
    file_hash = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    try:
        source = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        message = f"{path}: not valid UTF-8: {exc}"
        raise CommParseError(message) from exc
    return parse_comm_source(source, file_path=str(path), file_hash=file_hash)


def parse_comm_source(
    source: str, *, file_path: str, file_hash: str | None = None
) -> CommFileAnalysis:
    """Parse `.comm` source text already read into memory.

    `file_hash` defaults to the sha256 of the UTF-8-encoded source; pass the
    hash of the original bytes explicitly when it is known (`parse_comm_file`
    does), so it matches the file on disk exactly even if re-encoding would
    not round-trip byte-for-byte.
    """
    try:
        module = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        message = f"{file_path}: not parseable as Python source: {exc}"
        raise CommParseError(message) from exc

    shadowing_names = _collect_shadowing_names(module.body)
    imported_names = sorted(_collect_imported_names(module.body))

    raw_statements: list[_RawStatement] = []
    loop_names: set[str] = set()
    warnings: list[ParseWarning] = []
    _collect_statements(
        module.body, [], raw_statements, loop_names, warnings, shadowing_names
    )

    known_concepts = {r.assigned_concept for r in raw_statements if r.assigned_concept}
    known_concepts |= _collect_reuse_targets(raw_statements)

    ctx = _ResolveContext(
        known_concepts=known_concepts, loop_names=loop_names, warnings=warnings
    )

    statements: list[Statement] = []
    external_files: list[ExternalFileRef] = []
    test_statements: list[int] = []
    for index, raw in enumerate(raw_statements):
        statement = _build_statement(index, raw, source, ctx)
        statements.append(statement)
        ref = _external_file_ref(index, statement.command, statement.keywords)
        if ref is not None:
            external_files.append(ref)
        if statement.command == "TEST_RESU":
            test_statements.append(index)

    if file_hash is None:
        file_hash = f"sha256:{hashlib.sha256(source.encode('utf-8')).hexdigest()}"

    return CommFileAnalysis(
        file_path=file_path,
        file_hash=file_hash,
        assumed_version=None,
        version_source="undetermined",
        statements=statements,
        test_statements=test_statements,
        external_files=external_files,
        imported_names=imported_names,
        parse_warnings=warnings,
        parsed_at=datetime.now(UTC),
    )


# --------------------------------------------------------------------------
# Pass 1: recursive statement collection. No value resolution happens here.
# --------------------------------------------------------------------------


def _collect_statements(
    body: list[ast.stmt],
    control_flow: list[str],
    raw: list[_RawStatement],
    loop_names: set[str],
    warnings: list[ParseWarning],
    shadowing_names: set[str],
) -> None:
    for node in body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            _handle_assign(
                node,
                node.targets,
                node.value,
                control_flow,
                raw,
                warnings,
                shadowing_names,
            )
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and isinstance(node.value, ast.Call)
        ):
            _handle_assign(
                node,
                [node.target],
                node.value,
                control_flow,
                raw,
                warnings,
                shadowing_names,
            )
        elif isinstance(node, ast.Expr):
            _handle_expr(node, control_flow, raw, shadowing_names)
        elif isinstance(node, ast.If):
            cf = [*control_flow, "If"]
            _collect_statements(
                node.body, cf, raw, loop_names, warnings, shadowing_names
            )
            _collect_statements(
                node.orelse, cf, raw, loop_names, warnings, shadowing_names
            )
        elif isinstance(node, ast.For | ast.AsyncFor):
            _collect_loop_targets(node.target, loop_names)
            cf = [*control_flow, "For"]
            _collect_statements(
                node.body, cf, raw, loop_names, warnings, shadowing_names
            )
            _collect_statements(
                node.orelse, cf, raw, loop_names, warnings, shadowing_names
            )
        elif isinstance(node, ast.While):
            cf = [*control_flow, "While"]
            _collect_statements(
                node.body, cf, raw, loop_names, warnings, shadowing_names
            )
            _collect_statements(
                node.orelse, cf, raw, loop_names, warnings, shadowing_names
            )
        elif isinstance(node, ast.Try):
            cf = [*control_flow, "Try"]
            _collect_statements(
                node.body, cf, raw, loop_names, warnings, shadowing_names
            )
            for handler in node.handlers:
                _collect_statements(
                    handler.body, cf, raw, loop_names, warnings, shadowing_names
                )
            _collect_statements(
                node.orelse, cf, raw, loop_names, warnings, shadowing_names
            )
            _collect_statements(
                node.finalbody, cf, raw, loop_names, warnings, shadowing_names
            )
        elif isinstance(node, ast.With | ast.AsyncWith):
            cf = [*control_flow, "With"]
            _collect_statements(
                node.body, cf, raw, loop_names, warnings, shadowing_names
            )
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            warnings.append(
                ParseWarning(
                    line=node.lineno,
                    node_type="FunctionDef",
                    message=(
                        f"function '{node.name}' defined at module level: any "
                        "command call inside its body is not analyzed (the file "
                        "is never executed to find out whether, or how many "
                        "times, the function runs)."
                    ),
                )
            )
        elif isinstance(node, ast.ClassDef):
            warnings.append(
                ParseWarning(
                    line=node.lineno,
                    node_type="ClassDef",
                    message=(
                        f"class '{node.name}' defined at module level: its body "
                        "is not analyzed."
                    ),
                )
            )
        # Anything else (Import, ImportFrom, a plain Assign to a non-Call
        # value, AugAssign, Pass, Break, Continue, Raise, Assert, Delete,
        # Global, Nonlocal, Return) is ordinary Python bookkeeping, not part
        # of the command structure, and is not reported.


def _handle_assign(
    node: ast.stmt,
    targets: list[ast.expr],
    value: ast.Call,
    control_flow: list[str],
    raw: list[_RawStatement],
    warnings: list[ParseWarning],
    shadowing_names: set[str],
) -> None:
    command = _command_name(value, shadowing_names)
    if command is None:
        return
    if len(targets) == 1 and isinstance(targets[0], ast.Name):
        raw.append(
            _RawStatement(
                node=node,
                call=value,
                command=command,
                assigned_concept=targets[0].id,
                control_flow=list(control_flow),
            )
        )
        return
    warnings.append(
        ParseWarning(
            line=node.lineno,
            node_type=type(node).__name__,
            message=(
                f"call to '{command}' assigned with an unsupported target "
                f"shape ({len(targets)} target(s), not a single plain name): "
                "not represented as a statement."
            ),
        )
    )


def _handle_expr(
    node: ast.Expr,
    control_flow: list[str],
    raw: list[_RawStatement],
    shadowing_names: set[str],
) -> None:
    if not isinstance(node.value, ast.Call):
        return
    command = _command_name(node.value, shadowing_names)
    if command is None:
        return
    raw.append(
        _RawStatement(
            node=node,
            call=node.value,
            command=command,
            assigned_concept=None,
            control_flow=list(control_flow),
        )
    )


def _command_name(call: ast.Call, shadowing_names: set[str]) -> str | None:
    if (
        isinstance(call.func, ast.Name)
        and _COMMAND_NAME_RE.match(call.func.id)
        and call.func.id not in shadowing_names
    ):
        return call.func.id
    return None


def _collect_loop_targets(target: ast.expr, loop_names: set[str]) -> None:
    for node in ast.walk(target):
        if isinstance(node, ast.Name):
            loop_names.add(node.id)


def _collect_reuse_targets(raw_statements: list[_RawStatement]) -> set[str]:
    names: set[str] = set()
    for raw in raw_statements:
        for kw in raw.call.keywords:
            if kw.arg == "reuse" and isinstance(kw.value, ast.Name):
                names.add(kw.value.id)
    return names


# --------------------------------------------------------------------------
# Pass 2: keyword value resolution.
# --------------------------------------------------------------------------


def _is_factor_call(node: ast.expr) -> TypeGuard[ast.Call]:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_F"
    )


def _resolve_value(node: ast.expr, ctx: _ResolveContext) -> SimpleValue:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        pass
    else:
        return LiteralValue(value=value, value_type=type(value).__name__)

    source = ast.unparse(node)
    if isinstance(node, ast.Name):
        if node.id in ctx.known_concepts:
            return ConceptReferenceValue(concept=node.id, source=source)
        reason: DynamicReason = (
            "boucle" if node.id in ctx.loop_names else "reference_variable"
        )
        return DynamicValue(reason=reason, node_type="Name", source=source)

    reason, construct = _classify_dynamic(node)
    return DynamicValue(reason=reason, node_type=construct, source=source)


def _classify_dynamic(node: ast.expr) -> tuple[DynamicReason, str]:
    construct = type(node).__name__
    if isinstance(node, ast.Call):
        return "appel_fonction", construct
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Mult):
        return "concatenation", construct
    if isinstance(node, ast.ListComp | ast.DictComp | ast.SetComp | ast.GeneratorExp):
        return "comprehension", construct
    if isinstance(node, ast.Dict):
        return "dictionnaire_assemble", construct
    return "autre", construct


def _resolve_keyword_entry(
    name: str, node: ast.expr, ctx: _ResolveContext
) -> KeywordNode:
    if _is_factor_call(node):
        return FactorKeywordValue(
            name=name, occurrences=[_resolve_factor_call(node, ctx)]
        )

    if isinstance(node, ast.List | ast.Tuple) and node.elts:
        factor_elts = [e for e in node.elts if _is_factor_call(e)]
        if len(factor_elts) == len(node.elts):
            occurrences = [_resolve_factor_call(e, ctx) for e in factor_elts]
            return FactorKeywordValue(name=name, occurrences=occurrences)
        if factor_elts:
            ctx.warnings.append(
                ParseWarning(
                    line=node.lineno,
                    node_type=type(node).__name__,
                    message=(
                        f"keyword '{name}' mixes _F(...) and non-_F(...) "
                        "elements in the same list/tuple: treated as unresolved."
                    ),
                )
            )
            value: SimpleValue = DynamicValue(
                reason="autre", node_type="MixedFactorList", source=ast.unparse(node)
            )
            return SimpleKeywordValue(name=name, value=value)

    return SimpleKeywordValue(name=name, value=_resolve_value(node, ctx))


def _resolve_factor_call(call: ast.Call, ctx: _ResolveContext) -> FactorOccurrence:
    keywords: dict[str, KeywordNode] = {}
    unpack_count = 0
    for kw in call.keywords:
        if kw.arg is None:
            ctx.warnings.append(
                ParseWarning(
                    line=call.lineno,
                    node_type="keyword-unpacking",
                    message=(
                        "dict unpacking (**) used inside _F(...): its keys "
                        "cannot be enumerated statically."
                    ),
                )
            )
            keywords[f"**kwargs[{unpack_count}]"] = SimpleKeywordValue(
                name="**kwargs",
                value=DynamicValue(
                    reason="dictionnaire_assemble",
                    node_type="keyword-unpacking",
                    source=ast.unparse(kw.value),
                ),
            )
            unpack_count += 1
            continue
        keywords[kw.arg] = _resolve_keyword_entry(kw.arg, kw.value, ctx)
    if call.args:
        ctx.warnings.append(
            ParseWarning(
                line=call.lineno,
                node_type="positional-args",
                message=(
                    "positional arguments inside _F(...) are not valid "
                    "Code_Aster syntax and are ignored."
                ),
            )
        )
    return FactorOccurrence(keywords=keywords)


def _resolve_command(
    call: ast.Call, command: str, ctx: _ResolveContext
) -> tuple[dict[str, KeywordNode], str | None]:
    keywords: dict[str, KeywordNode] = {}
    reuse: str | None = None
    unpack_count = 0
    for kw in call.keywords:
        if kw.arg is None:
            ctx.warnings.append(
                ParseWarning(
                    line=call.lineno,
                    node_type="keyword-unpacking",
                    message=(
                        f"dict unpacking (**) used to build the keywords of "
                        f"'{command}': its keys cannot be enumerated statically."
                    ),
                )
            )
            keywords[f"**kwargs[{unpack_count}]"] = SimpleKeywordValue(
                name="**kwargs",
                value=DynamicValue(
                    reason="dictionnaire_assemble",
                    node_type="keyword-unpacking",
                    source=ast.unparse(kw.value),
                ),
            )
            unpack_count += 1
            continue
        if kw.arg == "reuse":
            if isinstance(kw.value, ast.Name):
                reuse = kw.value.id
            else:
                ctx.warnings.append(
                    ParseWarning(
                        line=call.lineno,
                        node_type="reuse",
                        message=(
                            f"'reuse=' of '{command}' is not a plain name: "
                            f"{ast.unparse(kw.value)!r}."
                        ),
                    )
                )
            continue
        keywords[kw.arg] = _resolve_keyword_entry(kw.arg, kw.value, ctx)
    if call.args:
        ctx.warnings.append(
            ParseWarning(
                line=call.lineno,
                node_type="positional-args",
                message=(
                    f"positional arguments in call to '{command}': "
                    "Code_Aster commands are keyword-only, ignored."
                ),
            )
        )
    return keywords, reuse


def _walk_keywords(
    keywords: dict[str, KeywordNode], prefix: str = ""
) -> Iterator[tuple[str, SimpleKeywordValue]]:
    for name, node in keywords.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(node, SimpleKeywordValue):
            yield path, node
        else:
            for i, occurrence in enumerate(node.occurrences):
                yield from _walk_keywords(occurrence.keywords, f"{path}[{i}]")


def _flatten_literal_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple | set):
        return [v for v in value if isinstance(v, str)]
    return []


def _flatten_literal_ints(value: Any) -> list[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return [value]
    if isinstance(value, list | tuple | set):
        return [v for v in value if isinstance(v, int) and not isinstance(v, bool)]
    return []


def _aggregate(keywords: dict[str, KeywordNode]) -> _Aggregates:
    agg = _Aggregates()
    for path, kw in _walk_keywords(keywords):
        value = kw.value
        if isinstance(value, LiteralValue):
            if kw.name.startswith("GROUP_MA"):
                agg.mesh_groups.update(_flatten_literal_strings(value.value))
            elif kw.name.startswith("GROUP_NO"):
                agg.node_groups.update(_flatten_literal_strings(value.value))
            elif kw.name == "MODELISATION":
                agg.modelisations.update(_flatten_literal_strings(value.value))
            elif kw.name == "PHENOMENE":
                agg.phenomena.update(_flatten_literal_strings(value.value))
            elif kw.name in ("RELATION", "RELATION_KIT"):
                agg.behaviours.update(_flatten_literal_strings(value.value))
            elif kw.name == "UNITE":
                agg.logical_units.update(_flatten_literal_ints(value.value))
        elif isinstance(value, ConceptReferenceValue):
            agg.referenced_concepts.add(value.concept)
        else:
            agg.unresolved.append(path)
            agg.dynamic = True
    return agg


def _external_file_ref(
    index: int, command: str, keywords: dict[str, KeywordNode]
) -> ExternalFileRef | None:
    unite_node = keywords.get("UNITE")
    fichier_node = keywords.get("FICHIER")
    unite: int | None = None
    fichier: str | None = None
    if isinstance(unite_node, SimpleKeywordValue) and isinstance(
        unite_node.value, LiteralValue
    ):
        v = unite_node.value.value
        if isinstance(v, int) and not isinstance(v, bool):
            unite = v
    if isinstance(fichier_node, SimpleKeywordValue) and isinstance(
        fichier_node.value, LiteralValue
    ):
        v = fichier_node.value.value
        if isinstance(v, str):
            fichier = v
    if unite is None and fichier is None:
        return None
    return ExternalFileRef(
        statement_index=index, command=command, unite=unite, fichier=fichier
    )


def _build_statement(
    index: int, raw: _RawStatement, source: str, ctx: _ResolveContext
) -> Statement:
    keywords, reuse = _resolve_command(raw.call, raw.command, ctx)
    agg = _aggregate(keywords)

    unresolved = list(agg.unresolved)
    dynamic = agg.dynamic
    if raw.control_flow:
        dynamic = True
        unresolved.append(
            f"@statement: nested inside {'.'.join(raw.control_flow)} "
            f"(line {raw.node.lineno}), presence/repetition not statically "
            "determined"
        )

    raw_text = ast.get_source_segment(source, raw.node) or ""
    end_lineno = raw.node.end_lineno or raw.node.lineno

    return Statement(
        index=index,
        command=raw.command,
        line_start=raw.node.lineno,
        line_end=end_lineno,
        assigned_concept=raw.assigned_concept,
        reuse=reuse,
        referenced_concepts=sorted(agg.referenced_concepts),
        keywords=keywords,
        mesh_groups=sorted(agg.mesh_groups),
        node_groups=sorted(agg.node_groups),
        modelisations=sorted(agg.modelisations),
        phenomena=sorted(agg.phenomena),
        behaviours=sorted(agg.behaviours),
        logical_units=sorted(agg.logical_units),
        control_flow=raw.control_flow,
        raw_text=raw_text,
        dynamic=dynamic,
        unresolved=unresolved,
    )
