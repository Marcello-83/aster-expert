"""Inventory of the load cases a production `.comm` solves (lot 49).

The deliverables are built from the project's own `.comm`, read by the static parser
(`aster_expert.parsing.comm_parser`, never executed): every `MACRO_ELAS_MULT` (one case
per occurrence of `CAS_CHARGE`, stored at `NUME_ORDRE` = its rank, CA-055) and every
`MECA_STATIQUE` (one case) gives the cases, with the model, the material field, the
element characteristics and the load concepts each case is solved with.

Each `AFFE_CHAR_MECA` (or `AFFE_CHAR_MECA_F`) is classified by its keywords:
kinematic (`DDL_IMPO`, `LIAISON_*`...) or a load (`PESANTEUR`, `FORCE_*`, `PRES_REP`).
The nodal forces of a case are assembled from its loads only: a kinematic one
has no second member of its own (a non-zero imposed value is reported, not drawn). A
charge that mixes both cannot be split and is refused for the deliverable of loads.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.parsing.models import (
    CommFileAnalysis,
    ConceptListValue,
    ConceptReferenceValue,
    DynamicValue,
    FactorKeywordValue,
    KeywordNode,
    LiteralValue,
    SimpleKeywordValue,
    Statement,
)

SOLVERS = ("MECA_STATIQUE", "MACRO_ELAS_MULT")
CHARGE_COMMANDS = ("AFFE_CHAR_MECA", "AFFE_CHAR_MECA_F")
KINEMATIC_KEYWORDS = frozenset(
    {
        "DDL_IMPO",
        "FACE_IMPO",
        "ARETE_IMPO",
        "DDL_POUTRE",
        "LIAISON_DDL",
        "LIAISON_OBLIQUE",
        "LIAISON_GROUP",
        "LIAISON_MAIL",
        "LIAISON_PROJ",
        "LIAISON_SOLIDE",
        "LIAISON_ELEM",
        "LIAISON_UNIF",
        "LIAISON_CHAMNO",
        "LIAISON_RBE3",
        "LIAISON_INTERF",
        "LIAISON_COQUE",
        "LIAISON_CYCL",
        "RELA_CINE_BP",
    }
)
"""Keywords of `AFFE_CHAR_MECA` that impose a kinematic condition (U4.44.01)."""
_NEUTRAL = frozenset({"MODELE", "INFO", "VERI_NORM", "DOUBLE_LAGRANGE", "SYME"})
NEUTRAL_KEYWORDS = _NEUTRAL
"""Keywords of a charge that load nothing (lot 50 quater: public name)."""


class InventoryError(ValueError):
    """The `.comm` cannot be read into cases (refused, never guessed)."""


@dataclass(frozen=True)
class SolveCase:
    name: str
    order: int
    """`NUME_ORDRE` of the case in its result (1 for a `MECA_STATIQUE`)."""
    charges: tuple[str, ...]
    """Every charge concept the case is solved with (global charges included)."""
    stores_sief: bool
    """`SIEF_ELGA` stored by the solver (its `OPTION`, default `SIEF_ELGA`)."""


@dataclass(frozen=True)
class Solve:
    result: str
    command: str
    line_start: int
    modele: str
    cham_mater: str
    cara_elem: str | None
    cases: tuple[SolveCase, ...]


@dataclass(frozen=True)
class VarcSource:
    """A command variable of a material field (`AFFE_MATERIAU/AFFE_VARC`)."""

    nom_varc: str
    concept: str
    kind: str
    """`CHAM_GD` or `EVOL`."""
    groups: tuple[str, ...]


@dataclass
class Inventory:
    solves: tuple[Solve, ...]
    charges: dict[str, frozenset[str]]
    """Charge concept -> its top-level keywords."""
    computed: dict[str, set[str]]
    """Result -> options already computed by `CALC_CHAMP` on it."""
    destroyed_at: dict[str, int]
    """Result -> first line of the `DETRUIRE` that destroys it."""
    fin_line: int
    units: set[int]
    varc: dict[str, tuple[VarcSource, ...]] = field(default_factory=dict)
    nonzero_imposed: dict[str, str] = field(default_factory=dict)
    """Kinematic charge with a non-zero imposed value -> its text (reported)."""

    def kinematic(self, charge: str) -> bool:
        return bool(self.charges.get(charge, frozenset()) & KINEMATIC_KEYWORDS)

    def mixed(self, charge: str) -> bool:
        keys = self.charges.get(charge, frozenset()) - _NEUTRAL
        return bool(keys & KINEMATIC_KEYWORDS) and bool(keys - KINEMATIC_KEYWORDS)

    def loads_of(self, case: SolveCase) -> tuple[str, ...]:
        """The charges of `case` that carry loads (kinematic ones removed)."""
        return tuple(c for c in case.charges if not self.kinematic(c))

    def cases(self) -> list[tuple[Solve, SolveCase]]:
        return [(s, c) for s in self.solves for c in s.cases]


def concepts(node: KeywordNode | None) -> list[str]:
    """Concept names of a keyword value (a name, a tuple of names)."""
    if node is None or not isinstance(node, SimpleKeywordValue):
        return []
    value = node.value
    if isinstance(value, ConceptReferenceValue):
        return [value.concept]
    if isinstance(value, ConceptListValue):
        return [i.concept for i in value.items if isinstance(i, ConceptReferenceValue)]
    if isinstance(value, DynamicValue):
        try:
            tree = ast.parse(value.source, mode="eval")
        except SyntaxError:
            return []
        return [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]
    return []


def literal(node: KeywordNode | None) -> object:
    if isinstance(node, SimpleKeywordValue) and isinstance(node.value, LiteralValue):
        return node.value.value
    return None


def _one(statement: Statement, name: str, *, required: bool = True) -> str | None:
    found = concepts(statement.keywords.get(name))
    if not found:
        if required:
            message = (
                f"ligne {statement.line_start} : {statement.command} sans {name} "
                "lisible"
            )
            raise InventoryError(message)
        return None
    return found[0]


def _occurrences(statement: Statement, name: str) -> list[dict[str, KeywordNode]]:
    node = statement.keywords.get(name)
    if isinstance(node, FactorKeywordValue):
        return [o.keywords for o in node.occurrences]
    return []


def _case_name(result: str, static_results: Mapping[str, str]) -> str:
    if result in static_results:
        return static_results[result]
    if result.startswith("RESU_") and len(result) > len("RESU_"):
        return result[len("RESU_") :]
    return result


def _nonzero(statement: Statement) -> str | None:
    for occ in _occurrences(statement, "DDL_IMPO"):
        for key, node in occ.items():
            if key in ("GROUP_NO", "GROUP_MA", "NOEUD", "TOUT"):
                continue
            value = literal(node)
            if isinstance(value, int | float) and value != 0:
                return f"DDL_IMPO {key}={value}"
    return None


def build_inventory(
    analysis: CommFileAnalysis,
    *,
    static_results: Mapping[str, str] | None = None,
    ignored: Iterable[str] = (),
) -> Inventory:
    """Cases, charges and positions of `analysis` (see module docstring)."""
    static_results = static_results or {}
    ignored = set(ignored)
    charges: dict[str, frozenset[str]] = {}
    nonzero: dict[str, str] = {}
    computed: dict[str, set[str]] = {}
    destroyed: dict[str, int] = {}
    varc: dict[str, tuple[VarcSource, ...]] = {}
    solves: list[Solve] = []
    units: set[int] = set()
    fin = None
    for st in analysis.statements:
        units.update(st.logical_units)
        if st.command in CHARGE_COMMANDS and st.assigned_concept:
            charges[st.assigned_concept] = frozenset(st.keywords)
            text = _nonzero(st)
            if text:
                nonzero[st.assigned_concept] = text
        elif st.command == "AFFE_MATERIAU" and st.assigned_concept:
            sources = []
            for occ in _occurrences(st, "AFFE_VARC"):
                for kind in ("CHAM_GD", "EVOL"):
                    found = concepts(occ.get(kind))
                    if found:
                        sources.append(
                            VarcSource(
                                nom_varc=str(literal(occ.get("NOM_VARC")) or "?"),
                                concept=found[0],
                                kind=kind,
                                groups=tuple(
                                    str(g)
                                    for g in _as_list(literal(occ.get("GROUP_MA")))
                                ),
                            )
                        )
            if sources:
                varc[st.assigned_concept] = tuple(sources)
        elif st.command == "CALC_CHAMP" and st.reuse:
            options = computed.setdefault(st.reuse, set())
            for key in ("CONTRAINTE", "FORCE", "DEFORMATION", "CRITERES"):
                options.update(str(v) for v in _as_list(literal(st.keywords.get(key))))
        elif st.command == "DETRUIRE":
            for name in concepts(st.keywords.get("NOM")):
                destroyed.setdefault(name, st.line_start)
        elif st.command == "FIN":
            fin = st.line_start
        elif st.command in SOLVERS and st.assigned_concept:
            result = st.assigned_concept
            if result in ignored:
                continue
            modele = _one(st, "MODELE")
            cham_mater = _one(st, "CHAM_MATER")
            cara = _one(st, "CARA_ELEM", required=False)
            assert modele is not None and cham_mater is not None
            cases: list[SolveCase] = []
            if st.command == "MACRO_ELAS_MULT":
                global_charges = concepts(st.keywords.get("CHAR_MECA_GLOBAL"))
                for rank, occ in enumerate(_occurrences(st, "CAS_CHARGE"), 1):
                    case_name = literal(occ.get("NOM_CAS"))
                    if not isinstance(case_name, str):
                        message = (
                            f"ligne {st.line_start} : cas {rank} de {result} sans "
                            "NOM_CAS littéral"
                        )
                        raise InventoryError(message)
                    option = literal(occ.get("OPTION")) or "SIEF_ELGA"
                    cases.append(
                        SolveCase(
                            name=case_name,
                            order=rank,
                            charges=(
                                *global_charges,
                                *concepts(occ.get("CHAR_MECA")),
                            ),
                            stores_sief=option == "SIEF_ELGA",
                        )
                    )
            else:
                excit = [
                    c
                    for occ in _occurrences(st, "EXCIT")
                    for c in concepts(occ.get("CHARGE"))
                ]
                option = literal(st.keywords.get("OPTION")) or "SIEF_ELGA"
                cases.append(
                    SolveCase(
                        name=_case_name(result, static_results),
                        order=1,
                        charges=tuple(excit),
                        stores_sief=option == "SIEF_ELGA",
                    )
                )
            solves.append(
                Solve(
                    result=result,
                    command=st.command,
                    line_start=st.line_start,
                    modele=modele,
                    cham_mater=cham_mater,
                    cara_elem=cara,
                    cases=tuple(cases),
                )
            )
    if fin is None:
        message = "le .comm ne se termine pas par FIN()"
        raise InventoryError(message)
    names = [c.name for s in solves for c in s.cases]
    duplicated = sorted({n for n in names if names.count(n) > 1})
    if duplicated:
        message = f"cas de même nom dans plusieurs résolutions : {duplicated}"
        raise InventoryError(message)
    unknown = sorted(set(static_results) - {s.result for s in solves})
    if unknown:
        message = f"static_results : résultat(s) absent(s) du .comm : {unknown}"
        raise InventoryError(message)
    return Inventory(
        solves=tuple(solves),
        charges=charges,
        computed=computed,
        destroyed_at=destroyed,
        fin_line=fin,
        units=units,
        varc=varc,
        nonzero_imposed=nonzero,
    )


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def inventory_of_text(
    text: str,
    *,
    static_results: Mapping[str, str] | None = None,
    ignored: Iterable[str] = (),
) -> Inventory:
    return build_inventory(
        parse_comm_source(text, file_path="<production>"),
        static_results=static_results,
        ignored=ignored,
    )


__all__ = [
    "KINEMATIC_KEYWORDS",
    "NEUTRAL_KEYWORDS",
    "Inventory",
    "InventoryError",
    "Solve",
    "SolveCase",
    "VarcSource",
    "build_inventory",
    "concepts",
    "inventory_of_text",
    "literal",
]
