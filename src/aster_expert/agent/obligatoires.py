"""Mandatory keywords of the commands a fiche plans (lot 44, step 2).

At lot 43, U4.81.42 made σc, αe, KT and Es mandatory for the 2D serviceability
reinforcement of `CALC_FERRAILLAGE`, and the fiche never asked for them: a second
intervention of MM was needed. This module reads, for each `PlannedCommand` of a
fiche, the keywords that the combination of options makes mandatory, and adds a
question to the fiche for each one that nothing answers yet.

Two sources, never merged silently:

- the **catalogue** of the target version: every simple keyword whose status is
  `required` and whose `condition`s hold for the given options (unset options take
  their catalogue default), concept-valued keywords (`RESULTAT`, `CARA_ELEM`)
  excepted -- those are objects of the `.comm`, not values to decide;
- the **execution rules** (`data/config/obligations_execution.yaml`): keywords
  the catalogue declares `optional` with no default, which the command refuses at
  run time (`<F>`) when they are missing. Each rule carries its sources (U4 of the
  same version, then the implementation). For `CALC_FERRAILLAGE` in 17.4 the four
  ELS parameters of lot 43 are all of this kind: the catalogue alone would never
  have found them (constat CA-053).

A keyword is covered when the planned command maps it (`covered_by`) to a value of
the data file -- provided or still « à fournir », the latter being a blocker
already -- or to a question of the fiche. Each uncovered keyword becomes a
`non_tranche` entry (`record_unfounded_point`) in the category the rules give it:
`mm` (it commits the structure) or `agent:<domain>` (a choice the agent may make,
lot 44 partition rule). Nothing is ever decided here.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from aster_expert.agent.drafting import SearchAttempt, record_unfounded_point
from aster_expert.agent.hypotheses import (
    AGENT_CHOICE_DOMAINS,
    HypothesesSheet,
    PlannedCommand,
    PracticeHypothesisEntry,
)
from aster_expert.agent.model_data import ModelData
from aster_expert.catalogue.models import (
    CommandSchema,
    FactorKeywordSchema,
    KeywordSchema,
    SimpleKeywordSchema,
)
from aster_expert.parsing.models import (
    CommFileAnalysis,
    KeywordNode,
    LiteralValue,
    SimpleKeywordValue,
)

_VALUE_TYPES = frozenset({"R", "I", "TXM", "C"})


class ExecutionRule(BaseModel):
    """Keywords mandatory at run time under the options of `when`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    when: dict[str, str]
    keywords: tuple[str, ...]
    sources: tuple[str, ...] = Field(min_length=1)


class ExecutionRules(BaseModel):
    """The versioned table `data/config/obligations_execution.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    aster_version: str
    source_commit: str
    doc_commit: str
    rules: tuple[ExecutionRule, ...]
    categories: dict[str, dict[str, str]] = Field(default_factory=dict)

    def category(self, command: str, keyword: str) -> str:
        table = self.categories.get(command, {})
        name = keyword.rsplit(".", 1)[-1]
        return table.get(name, table.get("default", "mm:non classé"))


def default_rules_path(project_root: Path) -> Path:
    return project_root / "data" / "config" / "obligations_execution.yaml"


def load_execution_rules(path: Path) -> ExecutionRules:
    return ExecutionRules.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


class MandatoryKeyword(BaseModel):
    """One keyword the combination of options makes mandatory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    keyword: str
    origin: str
    """`catalogue` or `exécution` (an `ExecutionRule`)."""
    sources: tuple[str, ...]


class MissingParameter(BaseModel):
    """A mandatory keyword of a planned command that nothing answers yet."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mandatory: MandatoryKeyword
    point_label: str
    options: dict[str, str]
    category: str

    def label(self) -> str:
        options = ", ".join(f"{k}={v}" for k, v in sorted(self.options.items()))
        return (
            f"{self.mandatory.command}/{self.mandatory.keyword} ({options}) : "
            f"obligatoire ({self.mandatory.origin}), catégorie {self.category}"
        )


def _defaults(schema: CommandSchema) -> dict[str, str]:
    out: dict[str, str] = {}

    def walk(entries: list[KeywordSchema]) -> None:
        for e in entries:
            if isinstance(e, SimpleKeywordSchema):
                if e.default is not None and not e.condition:
                    out.setdefault(e.path[-1], str(e.default))
            else:
                walk(e.children)

    walk(list(schema.keywords))
    return out


def _holds(condition: str, options: Mapping[str, str]) -> bool:
    """Evaluate one catalogue condition (`equal_to`, `exists`, `greater_than`,
    `less_than`, `is_in`, combined by `and`/`or`/`not`) on the options. Parsed by
    `ast`, never `eval`: an unknown construct is an error, not a guess."""
    tree = ast.parse(condition.strip(), mode="eval")

    def value(node: ast.expr) -> object:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Tuple | ast.List):
            return tuple(value(e) for e in node.elts)
        message = f"condition du catalogue non interprétée : {condition!r}"
        raise UninterpretedConditionError(message)

    def number(text: str | None) -> float | None:
        try:
            return None if text is None else float(text)
        except ValueError:
            return None

    def ev(node: ast.expr) -> bool:
        if isinstance(node, ast.BoolOp):
            results = [ev(v) for v in node.values]
            return all(results) if isinstance(node.op, ast.And) else any(results)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not ev(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = [value(a) for a in node.args]
            name = str(args[0])
            current = options.get(name)
            if node.func.id == "exists":
                return current is not None
            if node.func.id == "absent":
                return current is None
            if node.func.id == "equal_to":
                return current is not None and current == str(args[1])
            if node.func.id == "is_in":
                allowed = args[1] if isinstance(args[1], tuple) else (args[1],)
                return current in {str(a) for a in allowed}
            if node.func.id in ("greater_than", "less_than"):
                x = number(current)
                if x is None:
                    return False
                bound = float(str(args[1]))
                return x > bound if node.func.id == "greater_than" else x < bound
        message = f"condition du catalogue non interprétée : {condition!r}"
        raise UninterpretedConditionError(message)

    return ev(tree.body)


class UninterpretedConditionError(ValueError):
    """A catalogue condition the evaluator does not know (`is_type(...)`, ...)."""


def mandatory_keywords(
    schema: CommandSchema,
    options: Mapping[str, str],
    rules: ExecutionRules,
    uninterpreted: list[str] | None = None,
) -> tuple[MandatoryKeyword, ...]:
    """Mandatory keywords of `schema.command` under `options`, catalogue first.

    A keyword whose condition cannot be interpreted (lot 48 bis: `is_type("RESULTAT")`
    on `CALC_CHAMP`, which aborted the whole check) is neither reported nor assumed
    absent: it is appended to `uninterpreted` (`COMMANDE/MOT-CLÉ : condition`) so the
    caller says it. Without that list the refusal stays an error, as before."""
    effective = {**_defaults(schema), **options}
    found: dict[str, MandatoryKeyword] = {}
    citation = (
        f"catalogue {schema.aster_version} ({schema.command}, "
        f"{schema.catalogue_hash[:12]})"
    )

    def walk(entries: list[KeywordSchema]) -> None:
        for e in entries:
            try:
                holds = all(_holds(c, effective) for c in e.condition)
            except UninterpretedConditionError:
                if uninterpreted is None:
                    raise
                uninterpreted.append(
                    f"{schema.command}/{'.'.join(e.path)} : {'; '.join(e.condition)}"
                )
                continue
            if not holds:
                continue
            if isinstance(e, FactorKeywordSchema):
                if e.status == "required":
                    walk(e.children)
                continue
            types = (
                {e.value_type} if isinstance(e.value_type, str) else set(e.value_type)
            )
            if e.status != "required" or not types <= _VALUE_TYPES:
                continue
            path = ".".join(e.path)
            found.setdefault(
                path,
                MandatoryKeyword(
                    command=schema.command,
                    keyword=path,
                    origin="catalogue",
                    sources=(citation,),
                ),
            )

    walk(list(schema.keywords))
    for rule in rules.rules:
        if rule.command != schema.command:
            continue
        if any(effective.get(k) != v for k, v in rule.when.items()):
            continue
        for keyword in rule.keywords:
            if keyword not in found:
                found[keyword] = MandatoryKeyword(
                    command=schema.command,
                    keyword=keyword,
                    origin="exécution",
                    sources=rule.sources,
                )
    given = set(options)
    return tuple(m for m in found.values() if m.keyword.rsplit(".", 1)[-1] not in given)


def _covered(target: str, sheet: HypothesesSheet, data: ModelData | None) -> bool:
    kind, _, ref = target.partition(":")
    if kind == "data":
        return data is not None and ref in data.items()
    return any(
        isinstance(e, PracticeHypothesisEntry) and e.point_label == ref
        for e in sheet.entries
    )


def missing_parameters(
    sheet: HypothesesSheet,
    data: ModelData | None,
    schemas: Mapping[str, CommandSchema],
    rules: ExecutionRules,
    uninterpreted: list[str] | None = None,
) -> tuple[MissingParameter, ...]:
    """Mandatory keywords of every planned command that nothing covers.

    A `covered_by` target that does not exist (data key absent from the file,
    point absent from the fiche) does not cover anything: the keyword is reported.
    """
    missing: list[MissingParameter] = []
    for planned in sheet.planned_commands:
        schema = schemas[planned.command]
        for mandatory in mandatory_keywords(
            schema, planned.options, rules, uninterpreted
        ):
            target = planned.covered_by.get(mandatory.keyword)
            if target is not None and _covered(target, sheet, data):
                continue
            missing.append(
                MissingParameter(
                    mandatory=mandatory,
                    point_label=planned.point_label,
                    options=planned.options,
                    category=rules.category(planned.command, mandatory.keyword),
                )
            )
    return tuple(missing)


_CONSTANT = re.compile(r"""['"]([^'"]+)['"]""")
_CONDITION_NAME = re.compile(
    r'(?:equal_to|exists|absent|is_in|greater_than|less_than)\(\s*"([A-Za-z0-9_]+)"'
)


def _condition_values(schema: CommandSchema) -> dict[str, frozenset[str]]:
    """Options the catalogue conditions of `schema` test, with the string constants
    those conditions name (a superset of the values each option can take)."""
    values: dict[str, set[str]] = {}

    def walk(entries: list[KeywordSchema]) -> None:
        for e in entries:
            for condition in e.condition:
                constants = set(_CONSTANT.findall(condition))
                for name in _CONDITION_NAME.findall(condition):
                    values.setdefault(name, set()).update(constants)
            if isinstance(e, FactorKeywordSchema):
                walk(e.children)

    walk(list(schema.keywords))
    return {name: frozenset(v) for name, v in values.items()}


def _literal_options(
    keywords: Mapping[str, KeywordNode], allowed: Mapping[str, frozenset[str]]
) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, node in keywords.items():
        if isinstance(node, SimpleKeywordValue):
            value = node.value
            if (
                isinstance(value, LiteralValue)
                and isinstance(value.value, str)
                and value.value in allowed.get(name, frozenset())
            ):
                found.setdefault(name, value.value)
        else:
            for occurrence in node.occurrences:
                for key, val in _literal_options(occurrence.keywords, allowed).items():
                    found.setdefault(key, val)
    return found


def planned_from_comm(
    analysis: CommFileAnalysis,
    schema_of: Callable[[str], CommandSchema | None],
    point_of: Callable[[str], str],
    rules: ExecutionRules,
) -> tuple[tuple[PlannedCommand, ...], tuple[str, ...]]:
    """The `planned_commands` a `.comm` implies (lot 48 bis, audit R6).

    One entry per distinct command and per distinct combination of the options the
    catalogue conditions of that command test, or the execution rules (`rules`) key
    on, as written literally in the `.comm` (`TYPE_COMB="ELS"`). `schema_of` returns
    None for a command without a catalogue schema (`DEBUT`, `FIN` and the like:
    skipped, and named in the second result).
    `point_of` gives the fiche point a command's questions are attached to. Nothing
    is covered here: `covered_by` stays empty, a coverage is a decision.
    """
    planned: dict[tuple[str, tuple[tuple[str, str], ...]], PlannedCommand] = {}
    skipped: list[str] = []
    for statement in analysis.statements:
        schema = schema_of(statement.command)
        if schema is None:
            if statement.command not in skipped:
                skipped.append(statement.command)
            continue
        allowed = {
            name: set(constants)
            for name, constants in _condition_values(schema).items()
        }
        for rule in rules.rules:
            if rule.command == statement.command:
                for name, value in rule.when.items():
                    allowed.setdefault(name, set()).add(value)
        options = _literal_options(
            statement.keywords, {n: frozenset(v) for n, v in allowed.items()}
        )
        key = (statement.command, tuple(sorted(options.items())))
        if key not in planned:
            planned[key] = PlannedCommand(
                command=statement.command,
                point_label=point_of(statement.command),
                options=options,
            )
    ordered = sorted(planned.values(), key=lambda p: (p.command, sorted(p.options)))
    return tuple(ordered), tuple(skipped)


def _category_text(category: str) -> str:
    kind, _, detail = category.partition(":")
    if kind == "agent":
        label = AGENT_CHOICE_DOMAINS.get(detail, detail)
        return (
            f"choix de l'agent possible (domaine « {label} », à trancher par "
            "record_agent_choice avec ses vérificateurs)"
        )
    return f"à MM ({detail})"


def question_for(parameter: MissingParameter) -> PracticeHypothesisEntry:
    """The `non_tranche` question added to the fiche for one missing keyword."""
    m = parameter.mandatory
    keyword = m.keyword.rsplit(".", 1)[-1]
    options = ", ".join(f"{k}={v}" for k, v in sorted(parameter.options.items()))
    return record_unfounded_point(
        point_label=parameter.point_label,
        topic=f"Paramètre obligatoire {m.command}/{keyword} ({options})",
        searches=(
            SearchAttempt(
                profile="syntaxe",
                query=f"{m.command} {m.keyword} obligatoire ({options})",
                outcome=(f"obligatoire ({m.origin}) : " + " ; ".join(m.sources)),
            ),
        ),
        deduction=(
            f"Aucune donnée ni question de la fiche ne fixe {keyword}. "
            f"Catégorie : {_category_text(parameter.category)}."
        ),
    )


def add_missing_parameters(
    sheet: HypothesesSheet, missing: tuple[MissingParameter, ...]
) -> HypothesesSheet:
    """`sheet` with one question per missing keyword (an existing question of the
    same point and topic is not duplicated)."""
    existing = {(e.point_label, getattr(e, "topic", None)) for e in sheet.entries}
    added = []
    for parameter in missing:
        question = question_for(parameter)
        key = (question.point_label, question.topic)
        if key not in existing:
            existing.add(key)
            added.append(question)
    return sheet.model_copy(update={"entries": sheet.entries + tuple(added)})


__all__: list[str] = [
    "ExecutionRule",
    "ExecutionRules",
    "MandatoryKeyword",
    "MissingParameter",
    "add_missing_parameters",
    "default_rules_path",
    "load_execution_rules",
    "mandatory_keywords",
    "missing_parameters",
    "question_for",
]
