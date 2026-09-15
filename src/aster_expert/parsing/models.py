"""Structural analysis of a `.comm` file, conforming to docs/metadata.md, section 3.

Every model here is produced by static `ast` inspection of a `.comm` file. No
model in this module is ever built by executing the file (docs/architecture.md,
section 5; CLAUDE.md, principle 9).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DynamicReason = Literal[
    "boucle",
    "dictionnaire_assemble",
    "appel_fonction",
    "concatenation",
    "comprehension",
    "reference_variable",
    "autre",
]


class LiteralValue(BaseModel):
    """A keyword value statically reconstructed via `ast.literal_eval`."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["literal"] = "literal"
    resolved: Literal[True] = True
    value: Any
    value_type: str


class ConceptReferenceValue(BaseModel):
    """A keyword value that is a bare reference to a concept produced

    elsewhere in the file (e.g. `MODELE=MO`). Statically identified, but not
    a Python literal: `checkCommandSyntax` (lot 10) needs an actual
    `DataStructure` object for this, not a name (docs/development-plan.md,
    lot 9 and lot 10 notes).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["concept"] = "concept"
    resolved: Literal[False] = False
    concept: str
    source: str


class DynamicValue(BaseModel):
    """A keyword value that could not be statically resolved.

    `reason` is a coarse typology used for reporting (see the lot 9 batch
    report): `boucle` (the name was assigned inside a `for`/`while` loop
    body), `dictionnaire_assemble` (a non-literal `dict`, or `**kwargs`
    unpacking), `appel_fonction` (a call), `concatenation` (`+`/`*` on
    non-literal operands), `comprehension`, `reference_variable` (a plain
    Python name that is neither a loop variable nor a known concept), or
    `autre` for anything else (f-strings, ternaries, attribute access,
    subscripts, comparisons, mixed `_F(...)` lists, ...).
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["dynamic"] = "dynamic"
    resolved: Literal[False] = False
    reason: DynamicReason
    node_type: str
    source: str


SimpleValue = Annotated[
    LiteralValue | ConceptReferenceValue | DynamicValue, Field(discriminator="kind")
]


class SimpleKeywordValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    node: Literal["simple"] = "simple"
    name: str
    value: SimpleValue


class FactorOccurrence(BaseModel):
    model_config = ConfigDict(frozen=True)

    keywords: dict[str, KeywordNode]


class FactorKeywordValue(BaseModel):
    """A factor keyword: one `_F(...)` call, or a list/tuple of `_F(...)`

    calls for multiple occurrences (docs/metadata.md, section 3).
    """

    model_config = ConfigDict(frozen=True)

    node: Literal["factor"] = "factor"
    name: str
    occurrences: list[FactorOccurrence]


KeywordNode = Annotated[
    SimpleKeywordValue | FactorKeywordValue, Field(discriminator="node")
]

FactorKeywordValue.model_rebuild()
FactorOccurrence.model_rebuild()


class ParseWarning(BaseModel):
    """An explicit record of a construct the parser encountered but does not

    model (CLAUDE.md, principle: never a silent omission). Never a reason to
    drop the rest of the file.
    """

    model_config = ConfigDict(frozen=True)

    line: int | None
    node_type: str
    message: str


class ExternalFileRef(BaseModel):
    """A logical unit (`UNITE=`) and/or file path (`FICHIER=`) referenced by

    a statement (`DEFI_FICHIER`, `INCLUDE`, `LIRE_MAILLAGE`, ...).
    """

    model_config = ConfigDict(frozen=True)

    statement_index: int
    command: str
    unite: int | None
    fichier: str | None


class Statement(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int
    command: str
    line_start: int
    line_end: int
    assigned_concept: str | None
    reuse: str | None
    referenced_concepts: list[str]
    keywords: dict[str, KeywordNode]
    mesh_groups: list[str]
    node_groups: list[str]
    modelisations: list[str]
    phenomena: list[str]
    behaviours: list[str]
    logical_units: list[int]
    control_flow: list[str]
    raw_text: str
    dynamic: bool
    unresolved: list[str]


VersionSource = Literal["config", "argument", "export_file", "undetermined"]


class CommFileAnalysis(BaseModel):
    """Conforms to docs/metadata.md, section 3.

    `assumed_version`/`version_source` are never set by the parser itself: it
    resolves no Code_Aster version (docs/development-plan.md, lot 9 is
    parsing only; version resolution belongs to lot 2/lot 10). A downstream
    consumer that does know the target version may overwrite these two
    fields; `parse_comm_file` always leaves them at `None`/`"undetermined"`.

    `imported_names` (amendment, lot 10b) lists every name explicitly bound
    by an `import`/`from ... import ...` statement anywhere in the file
    (deduplicated, sorted) — never a wildcard import's members, which cannot
    be enumerated without executing the file. A downstream consumer uses
    this to tell a command name that is merely a typo from one that is real
    but outside the extracted catalogue's scope (docs/development-plan.md,
    lot 4/10b — e.g. `DEFI_CONT`, defined in `code_aster.MacroCommands`, not
    `code_aster.Cata.Commands`).
    """

    model_config = ConfigDict(frozen=True)

    file_path: str
    file_hash: str
    assumed_version: str | None
    version_source: VersionSource
    statements: list[Statement]
    test_statements: list[int]
    external_files: list[ExternalFileRef]
    imported_names: list[str]
    parse_warnings: list[ParseWarning]
    parsed_at: datetime
