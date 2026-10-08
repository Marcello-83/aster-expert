"""Keywords refused before any run, each tied to its diagnosis (lot 49).

A keyword value that Code_Aster accepts (the catalogue lets it through, level B) can
still give wrong results without an error. When such a defect is established by a
diagnosis of the knowledge base, the value is refused **before** the container starts,
with a readable message naming the diagnosis: never a silent rewrite of the user's file.

The rules live in `config/validation.yaml` (`execution.forbidden_keywords`), never in
the code: each one names a command, a keyword (any depth inside the command), the
refused values, the diagnosis and the reason. A rule is lifted by removing it from the
configuration once its diagnosis is resolved.

The `.comm` is read by the project's static parser (`aster_expert.parsing.comm_parser`,
the file is never executed). A value the parser cannot resolve (loop variable, call...)
is refused as well when the keyword is present: the rule cannot prove it is not one of
the refused values.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from aster_expert.execution.errors import ExecutionRunError
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.parsing.models import (
    FactorKeywordValue,
    KeywordNode,
    LiteralValue,
    SimpleKeywordValue,
    Statement,
)


class ForbiddenKeyword(BaseModel):
    """One rule: `command`/`keyword` must not take any of `values`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    keyword: str
    """Simple keyword name, searched at any depth of the command."""
    values: tuple[str, ...] = Field(min_length=1)
    diagnostic: str = Field(pattern=r"^(DIAG|ENV)-\d{3}$")
    reason: str = Field(min_length=10)


class ForbiddenUse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule: ForbiddenKeyword
    line: int
    value: str

    def message(self) -> str:
        r = self.rule
        return (
            f"ligne {self.line} : {r.command}/{r.keyword}={self.value} refusé avant "
            f"exécution ({r.diagnostic}) : {r.reason}"
        )


def _simple_nodes(
    keywords: dict[str, KeywordNode], name: str
) -> Iterator[SimpleKeywordValue]:
    for node in keywords.values():
        if isinstance(node, SimpleKeywordValue):
            if node.name == name:
                yield node
        elif isinstance(node, FactorKeywordValue):
            for occurrence in node.occurrences:
                yield from _simple_nodes(occurrence.keywords, name)


def _values(node: SimpleKeywordValue) -> list[str]:
    value = node.value
    if isinstance(value, LiteralValue):
        raw = value.value
        items = raw if isinstance(raw, list | tuple) else [raw]
        return [str(v) for v in items]
    return ["<valeur non résolue>"]


def _uses(statement: Statement, rule: ForbiddenKeyword) -> Iterator[ForbiddenUse]:
    if statement.command != rule.command:
        return
    for node in _simple_nodes(statement.keywords, rule.keyword):
        for value in _values(node):
            unresolved = value == "<valeur non résolue>"
            if unresolved or value.upper() in {v.upper() for v in rule.values}:
                yield ForbiddenUse(rule=rule, line=statement.line_start, value=value)


def find_forbidden(
    text: str, rules: Iterable[ForbiddenKeyword], *, name: str = "<comm>"
) -> list[ForbiddenUse]:
    """Every use of a refused value in the `.comm` text, in file order."""
    rules = tuple(rules)
    if not rules:
        return []
    analysis = parse_comm_source(text, file_path=name)
    found: list[ForbiddenUse] = []
    for statement in analysis.statements:
        for rule in rules:
            found.extend(_uses(statement, rule))
    return found


def refuse_forbidden(comm: Path, rules: Iterable[ForbiddenKeyword]) -> None:
    """Raise `ExecutionRunError` listing every refused use, if any."""
    found = find_forbidden(comm.read_text(encoding="utf-8"), rules, name=str(comm))
    if found:
        lines = "\n".join(f"  - {use.message()}" for use in found)
        message = (
            f"{comm.name} : mot-clé refusé avant toute exécution "
            f"(config/validation.yaml, execution.forbidden_keywords) :\n{lines}"
        )
        raise ExecutionRunError(message)


__all__ = ["ForbiddenKeyword", "ForbiddenUse", "find_forbidden", "refuse_forbidden"]
