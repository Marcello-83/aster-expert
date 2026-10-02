"""Schemas of the five YAML knowledge layers (lot 42, étape 1).

Every entry (`KnowledgeEntry`) carries a stable identifier, its project of
origin, a date, the validation level it reached, its sources (at least one: no
entry without proof), the Code_Aster commands and keywords it concerns, and its
status:

- `observé`: seen in a project, with its proof;
- `établi`: the proof can be replayed -- a versioned trial case (path and
  SHA-256) or a versioned test;
- `promu`: proved in at least two projects (lot 44: a reuse counts only with
  a successful execution or a passing test, `is_proof`), or validated at
  level E. Only `aster_expert.connaissances.promotion` sets it, and the model
  refuses it without those conditions.

The level an entry claims never exceeds what its sources reach: a document, a
decision or a failed run is A, code or a test B, a successful run its own level
(C or D). The level of a cited finding (`constat`) is checked by the base,
which knows the findings (`aster_expert.connaissances.base`).
"""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["observé", "établi", "promu"]
Level = Literal["A", "B", "C", "D", "E"]
LayerName = Literal[
    "constats_code_aster",
    "diagnostics",
    "patrons",
    "controles",
    "references_validation",
    "precedents",
]

LAYERS: tuple[LayerName, ...] = (
    "constats_code_aster",
    "diagnostics",
    "patrons",
    "controles",
    "references_validation",
    "precedents",
)
YAML_LAYERS: tuple[LayerName, ...] = LAYERS[1:]
STATUSES: tuple[Status, ...] = ("observé", "établi", "promu")
LEVEL_ORDER = "ABCDE"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{8}$")
_CONSTAT_ID = re.compile(r"^CA-\d{3}$")


def max_level(levels: list[Level]) -> Level:
    return max(levels, key=LEVEL_ORDER.index) if levels else "A"


def _relative_path(value: str, name: str) -> str:
    parts = value.split("/")
    if not value or value.startswith("/") or ".." in parts or "" in parts:
        message = f"`{name}` : chemin relatif à la racine du dépôt attendu, sans `..`"
        raise ValueError(message)
    return value


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------
# Sources (preuves)
# --------------------------------------------------------------------------


class ExecutionEvidence(_Model):
    """A Code_Aster run. `run` names an archived run (`data/processed/runs/`,
    not versioned: present in the VM only); `case_path`/`case_sha256` a
    versioned case, the only form that makes the proof replayable."""

    kind: Literal["execution"] = "execution"
    run: str | None = None
    case_path: str | None = None
    case_sha256: str | None = None
    outcome: Literal["échec", "réussite"]
    level: Literal["C", "D", "E"] | None = None
    """Level reached by a successful run (C: run to `FIN`; D: results checked;
    E: results compared to a validated reference)."""
    note: str

    @model_validator(mode="after")
    def _coherent(self) -> ExecutionEvidence:
        if self.run is None and self.case_path is None:
            message = "une source d'exécution nomme une exécution archivée ou un cas"
            raise ValueError(message)
        if self.run is not None and not _RUN_ID.match(self.run):
            message = (
                f"identifiant d'exécution {self.run!r} : forme AAAAMMJJThhmmss-xxxxxxxx"
            )
            raise ValueError(message)
        if self.case_path is not None:
            _relative_path(self.case_path, "case_path")
            if self.case_sha256 is None or not _SHA256.match(self.case_sha256):
                message = (
                    "un cas versionné porte son empreinte SHA-256 (64 hexadécimaux)"
                )
                raise ValueError(message)
        elif self.case_sha256 is not None:
            message = "une empreinte sans chemin de cas"
            raise ValueError(message)
        if self.outcome == "échec" and self.level is not None:
            message = "une exécution en échec n'atteint aucun niveau C ou D"
            raise ValueError(message)
        if self.outcome == "réussite" and self.level is None:
            message = "une exécution réussie déclare le niveau atteint (C, D ou E)"
            raise ValueError(message)
        if not self.note.strip():
            message = "une source d'exécution dit ce qu'elle montre (`note`)"
            raise ValueError(message)
        return self

    @property
    def replayable(self) -> bool:
        return self.case_path is not None

    def evidence_level(self) -> Level:
        return self.level if self.level is not None else "A"


class TestEvidence(_Model):
    """A versioned test that guards the fact (`path` relative to the repository,
    `function` the test function defined in it)."""

    __test__: ClassVar[bool] = False  # not a pytest test class

    kind: Literal["test"] = "test"
    path: str
    function: str
    note: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> TestEvidence:
        _relative_path(self.path, "path")
        if not re.match(r"^test_\w+$", self.function):
            message = f"fonction de test {self.function!r} : forme test_…"
            raise ValueError(message)
        return self

    def evidence_level(self) -> Level:
        return "B"


class CodeEvidence(_Model):
    """Versioned code implementing the entry (`symbol` defined in `path`)."""

    kind: Literal["code"] = "code"
    path: str
    symbol: str
    note: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> CodeEvidence:
        _relative_path(self.path, "path")
        return self

    def evidence_level(self) -> Level:
        return "B"


class DocumentEvidence(_Model):
    """A versioned report or document of the repository (`section` optional)."""

    kind: Literal["document"] = "document"
    path: str
    section: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _coherent(self) -> DocumentEvidence:
        _relative_path(self.path, "path")
        return self

    def evidence_level(self) -> Level:
        return "A"


class ConstatEvidence(_Model):
    """A finding of the base (`connaissances/constats_code_aster/`)."""

    kind: Literal["constat"] = "constat"
    constat_id: str

    @model_validator(mode="after")
    def _coherent(self) -> ConstatEvidence:
        if not _CONSTAT_ID.match(self.constat_id):
            message = f"identifiant de constat {self.constat_id!r} : forme CA-nnn"
            raise ValueError(message)
        return self


class DecisionEvidence(_Model):
    """An arbitrated `pratique` entry of a project's fiche."""

    kind: Literal["decision"] = "decision"
    fiche: str
    point_label: str
    decided_by: str
    decided_at: dt.datetime

    @model_validator(mode="after")
    def _coherent(self) -> DecisionEvidence:
        _relative_path(self.fiche, "fiche")
        return self

    def evidence_level(self) -> Level:
        return "A"


Evidence = Annotated[
    ExecutionEvidence
    | TestEvidence
    | CodeEvidence
    | DocumentEvidence
    | ConstatEvidence
    | DecisionEvidence,
    Field(discriminator="kind"),
]


def evidence_level(source: Evidence, constat_levels: dict[str, Level]) -> Level:
    if isinstance(source, ConstatEvidence):
        return constat_levels.get(source.constat_id, "A")
    return source.evidence_level()


def is_proof(source: Evidence) -> bool:
    """Whether a reuse's evidence *proves* the entry in that project (lot 44).

    Only a successful execution whose result verifies the entry, or a versioned
    test that applies it and passes, is a proof. A citation in a fiche, a decision
    (`DecisionEvidence`), a document, a piece of code or a finding is not: at lot
    43 the citation of CA-025 and CA-041 by the slab's fiche made them formally
    eligible without the slab ever exercising them.
    """
    if isinstance(source, ExecutionEvidence):
        return source.outcome == "réussite"
    return isinstance(source, TestEvidence)


def is_replayable(source: Evidence) -> bool:
    if isinstance(source, ExecutionEvidence):
        return source.replayable
    return isinstance(source, TestEvidence)


# --------------------------------------------------------------------------
# Common entry
# --------------------------------------------------------------------------


class Reuse(_Model):
    """A reuse of the entry in another project, with its evidence. It counts
    for promotion only when `proven` (lot 44, `is_proof`)."""

    project: str
    date: dt.date
    evidence: Evidence
    note: str

    @property
    def proven(self) -> bool:
        return is_proof(self.evidence)


class StatusEvent(_Model):
    status: Status
    date: dt.date
    by: str
    reason: str

    @model_validator(mode="after")
    def _coherent(self) -> StatusEvent:
        if not self.by.strip() or not self.reason.strip():
            message = "un changement de statut porte son auteur et son motif"
            raise ValueError(message)
        return self


class KnowledgeEntry(_Model):
    """Fields shared by the five YAML layers."""

    layer: ClassVar[LayerName]
    id_pattern: ClassVar[re.Pattern[str]]

    id: str
    title: str
    summary: str
    """The fact, the recipe or the decision in one sentence."""
    origin_project: str
    date: dt.date
    validation_level: Level
    status: Status
    sources: tuple[Evidence, ...]
    commands: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    reuses: tuple[Reuse, ...] = ()
    status_history: tuple[StatusEvent, ...] = ()

    @model_validator(mode="after")
    def _common_rules(self) -> KnowledgeEntry:
        if not self.id_pattern.match(self.id):
            message = (
                f"{self.id} : identifiant hors de la forme de la couche {self.layer} "
                f"({self.id_pattern.pattern})"
            )
            raise ValueError(message)
        summary = self.summary.strip()
        if not summary.endswith(".") or len(summary) > 500:
            message = (
                f"{self.id} : le résumé est une phrase terminée par un point, de 500 "
                "caractères au plus"
            )
            raise ValueError(message)
        if not self.sources:
            message = f"{self.id} : aucune entrée de connaissance sans preuve (sources)"
            raise ValueError(message)
        for name in ("commands", "keywords"):
            for token in getattr(self, name):
                if token != token.upper() or not token.strip():
                    message = (
                        f"{self.id} : `{name}` porte des identifiants Code_Aster en "
                        f"casse officielle (majuscules), reçu {token!r}"
                    )
                    raise ValueError(message)
        replayable = any(is_replayable(s) for s in self.sources)
        level_e = self.status == "promu" and self.validation_level == "E"
        if self.status in ("établi", "promu") and not (replayable or level_e):
            message = (
                f"{self.id} : statut {self.status} sans preuve rejouable (cas "
                "versionné avec son empreinte, ou test versionné)"
            )
            raise ValueError(message)
        if self.status == "promu":
            if len(self.projects()) < 2 and self.validation_level != "E":
                message = (
                    f"{self.id} : statut promu sans réutilisation éprouvée dans un "
                    "second projet ni validation de niveau E"
                )
                raise ValueError(message)
            if not self.status_history or self.status_history[-1].status != "promu":
                message = (
                    f"{self.id} : une promotion se fait par la commande "
                    "`connaissances promouvoir`, qui l'inscrit dans l'historique"
                )
                raise ValueError(message)
        if self.status_history and self.status_history[-1].status != self.status:
            message = (
                f"{self.id} : statut {self.status}, dernier événement de l'historique "
                f"{self.status_history[-1].status}"
            )
            raise ValueError(message)
        for reuse in self.reuses:
            if reuse.project == self.origin_project:
                message = (
                    f"{self.id} : une réutilisation se fait dans un autre projet que "
                    "le projet d'origine"
                )
                raise ValueError(message)
        return self

    def projects(self) -> set[str]:
        """Origin and projects that *proved* the entry (lot 44): the projects
        that count for promotion."""
        return {self.origin_project, *(r.project for r in self.reuses if r.proven)}

    def cited_projects(self) -> set[str]:
        """Projects whose reuse is recorded without a proof (citation, decision,
        code, document): reported, never counted."""
        return {r.project for r in self.reuses if not r.proven} - self.projects()

    def evidence_level(self, constat_levels: dict[str, Level]) -> Level:
        levels = [evidence_level(s, constat_levels) for s in self.sources]
        levels += [evidence_level(r.evidence, constat_levels) for r in self.reuses]
        return max_level(levels)

    def specific_text(self) -> list[str]:
        """The prose of the layer's own fields, searched by the text search."""
        return []

    def searchable_text(self) -> str:
        return "\n".join(
            [
                self.id,
                self.title,
                self.summary,
                *self.specific_text(),
                " ".join(self.commands),
                " ".join(self.keywords),
            ]
        )


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------

SignatureKind = Literal[
    "<F>",
    "<E>",
    "<S>",
    "<EXCEPTION>",
    "<A>",
    "arrêt anormal",
    "erreur Python",
    "environnement",
]


class Signature(_Model):
    """How an error shows: message kind, identifiers (`FACTOR_11`), and an
    optional regular expression looked for in the message or the listing."""

    kind: SignatureKind
    identifiers: tuple[str, ...] = ()
    pattern: str | None = None
    """Regular expression (case ignored) the message text, or the listing for an
    abnormal stop or a Python error, must contain."""

    @model_validator(mode="after")
    def _coherent(self) -> Signature:
        if not self.identifiers and not self.pattern:
            message = "une signature porte des identifiants ou un motif"
            raise ValueError(message)
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                message = f"motif de signature invalide : {exc}"
                raise ValueError(message) from exc
        for ident in self.identifiers:
            if not re.match(r"^[A-Z][A-Z0-9_]*$", ident):
                message = f"identifiant de message {ident!r} : forme MODULE_nn"
                raise ValueError(message)
        return self

    def label(self) -> str:
        idents = " ".join(f"<{i}>" for i in self.identifiers)
        return " ".join(p for p in (self.kind, idents) if p)


class Diagnostic(KnowledgeEntry):
    """An error or alarm signature, its established cause and its correction."""

    layer: ClassVar[LayerName] = "diagnostics"
    id_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^(DIAG|ENV)-\d{3}$")

    category: Literal[
        "modélisation", "préparation", "limite de Code_Aster", "environnement"
    ]
    signature: Signature
    cause: str
    cause_established: bool
    """False when the correction is known but the internal mechanism is not
    (said in `cause`)."""
    correction: str
    prevention: str | None = None

    @model_validator(mode="after")
    def _diagnostic_rules(self) -> Diagnostic:
        is_env = self.id.startswith("ENV-")
        if is_env != (self.category == "environnement"):
            message = f"{self.id} : ENV-nnn exactement pour la catégorie environnement"
            raise ValueError(message)
        if is_env != (self.signature.kind == "environnement"):
            message = f"{self.id} : signature « environnement » exactement pour ENV-nnn"
            raise ValueError(message)
        return self

    def specific_text(self) -> list[str]:
        return [
            self.signature.label(),
            self.signature.pattern or "",
            self.cause,
            self.correction,
            self.prevention or "",
        ]


# --------------------------------------------------------------------------
# Patrons
# --------------------------------------------------------------------------


class Pattern(KnowledgeEntry):
    """A reusable modelling recipe: problem, solution, fragment, conditions of
    use, the controls that check it and the findings it rests on."""

    layer: ClassVar[LayerName] = "patrons"
    id_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^PAT-\d{3}$")

    problem: str
    solution: str
    fragment: str
    fragment_language: Literal["comm", "salome", "python"]
    conditions: str
    controls: tuple[str, ...] = ()
    """Identifiers of the controls (`CTL-nnn`) that check the pattern."""
    constats: tuple[str, ...] = ()
    """Findings (`CA-nnn`) it rests on."""
    implementation: tuple[CodeEvidence, ...] = ()

    @model_validator(mode="after")
    def _pattern_rules(self) -> Pattern:
        for c in self.controls:
            if not re.match(r"^CTL-\d{3}$", c):
                message = f"{self.id} : contrôle {c!r} hors de la forme CTL-nnn"
                raise ValueError(message)
        for c in self.constats:
            if not _CONSTAT_ID.match(c):
                message = f"{self.id} : constat {c!r} hors de la forme CA-nnn"
                raise ValueError(message)
        if "..." in self.fragment or "…" in self.fragment:
            message = f"{self.id} : pas de points de suspension dans un fragment"
            raise ValueError(message)
        return self

    def specific_text(self) -> list[str]:
        return [self.problem, self.solution, self.fragment, self.conditions]


# --------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------


class CaughtError(_Model):
    """The real error a control caught. `attrapée`: the control itself refused
    it; `a posteriori`: written after the error, it refuses the faulty file
    (shown by its test); `aucune consignée`: no real error is recorded."""

    mode: Literal["attrapée", "a posteriori", "aucune consignée"]
    description: str
    evidence: Evidence | None = None

    @model_validator(mode="after")
    def _coherent(self) -> CaughtError:
        if (self.mode == "aucune consignée") != (self.evidence is None):
            message = (
                "une erreur attrapée porte sa preuve ; « aucune consignée » n'en a pas"
            )
            raise ValueError(message)
        return self


class Control(KnowledgeEntry):
    """A reusable verification control."""

    layer: ClassVar[LayerName] = "controles"
    id_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^CTL-\d{3}$")

    detects: str
    parameters: str
    implementation: CodeEvidence
    scope: Literal["tronc commun", "projet"]
    """Where the code lives: the common trunk (`src/`) or a project."""
    caught_error: CaughtError
    default_harness: bool = False
    """In the default harness of every project: only a promoted control."""

    @model_validator(mode="after")
    def _control_rules(self) -> Control:
        if self.default_harness and self.status != "promu":
            message = (
                f"{self.id} : seul un contrôle promu entre dans le harnais par défaut"
            )
            raise ValueError(message)
        in_src = self.implementation.path.startswith("src/")
        if in_src != (self.scope == "tronc commun"):
            message = (
                f"{self.id} : portée {self.scope} et code dans "
                f"{self.implementation.path}"
            )
            raise ValueError(message)
        return self

    def specific_text(self) -> list[str]:
        return [self.detects, self.parameters, self.caught_error.description]


# --------------------------------------------------------------------------
# Références de validation
# --------------------------------------------------------------------------


class ReferenceQuantity(_Model):
    """One compared quantity. `exact`: a quantity the element's theory
    reproduces exactly, held to `tolerance` relative; `raffinement`: a quantity
    sensitive to discretisation, whose error must decrease when the mesh is
    refined (CLAUDE.md, « Critère de réussite des essais »)."""

    name: str
    value_obtained: float
    reference_value: float
    criterion: Literal["exact", "raffinement"]
    tolerance: float | None = None
    refined_case_path: str | None = None
    refined_value: float | None = None
    result: Literal["réussi", "échec"]
    note: str | None = None

    @property
    def deviation(self) -> float:
        return (self.value_obtained - self.reference_value) / self.reference_value

    @property
    def refined_deviation(self) -> float | None:
        if self.refined_value is None:
            return None
        return (self.refined_value - self.reference_value) / self.reference_value

    def computed_result(self) -> Literal["réussi", "échec"]:
        if self.criterion == "exact":
            assert self.tolerance is not None
            return "réussi" if abs(self.deviation) <= self.tolerance else "échec"
        refined = self.refined_deviation
        assert refined is not None
        return "réussi" if abs(refined) < abs(self.deviation) else "échec"

    @model_validator(mode="after")
    def _coherent(self) -> ReferenceQuantity:
        if self.reference_value == 0.0 or not math.isfinite(self.reference_value):
            message = (
                f"{self.name} : référence nulle ou non finie (écart relatif indéfini)"
            )
            raise ValueError(message)
        if self.criterion == "exact":
            if self.tolerance is None or self.tolerance <= 0.0:
                message = f"{self.name} : critère exact sans tolérance positive"
                raise ValueError(message)
            if self.refined_value is not None or self.refined_case_path is not None:
                message = f"{self.name} : critère exact sans valeur raffinée"
                raise ValueError(message)
        else:
            if self.refined_value is None or self.refined_case_path is None:
                message = f"{self.name} : critère de raffinement sans cas raffiné"
                raise ValueError(message)
            _relative_path(self.refined_case_path, "refined_case_path")
        if self.result != self.computed_result():
            message = (
                f"{self.name} : résultat déclaré {self.result}, critère appliqué "
                f"{self.computed_result()}"
            )
            raise ValueError(message)
        return self


class ReferenceCase(_Model):
    case_path: str
    case_sha256: str
    quantities: tuple[ReferenceQuantity, ...]

    @model_validator(mode="after")
    def _coherent(self) -> ReferenceCase:
        _relative_path(self.case_path, "case_path")
        if not _SHA256.match(self.case_sha256):
            message = f"{self.case_path} : empreinte SHA-256 attendue"
            raise ValueError(message)
        if not self.quantities:
            message = f"{self.case_path} : au moins une grandeur comparée"
            raise ValueError(message)
        return self


class ValidationReference(KnowledgeEntry):
    """A case with a known solution, executable, with criterion and result."""

    layer: ClassVar[LayerName] = "references_validation"
    id_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^REF-\d{3}$")

    problem: str
    reference_solution: str
    cases: tuple[ReferenceCase, ...]
    result: Literal["réussi", "échec"]

    @model_validator(mode="after")
    def _reference_rules(self) -> ValidationReference:
        computed = (
            "réussi"
            if all(q.result == "réussi" for c in self.cases for q in c.quantities)
            else "échec"
        )
        if self.result != computed:
            message = (
                f"{self.id} : résultat déclaré {self.result}, grandeurs : {computed}"
            )
            raise ValueError(message)
        declared = {
            (s.case_path, s.case_sha256)
            for s in self.sources
            if isinstance(s, ExecutionEvidence) and s.case_path is not None
        }
        for case in self.cases:
            if (case.case_path, case.case_sha256) not in declared:
                message = (
                    f"{self.id} : le cas {case.case_path} n'est pas une source "
                    "d'exécution de l'entrée"
                )
                raise ValueError(message)
        return self

    def specific_text(self) -> list[str]:
        return [
            self.problem,
            self.reference_solution,
            *(q.name for c in self.cases for q in c.quantities),
        ]


# --------------------------------------------------------------------------
# Précédents
# --------------------------------------------------------------------------


class Precedent(KnowledgeEntry):
    """A practice decision of MM, reusable as a precedent: never applied
    automatically, only proposed in a new fiche (`aster_expert.connaissances.
    precedents.propose_precedent`) and submitted to arbitration."""

    layer: ClassVar[LayerName] = "precedents"
    id_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^PRE-\d{3}$")

    fiche: str
    point_label: str
    topic: str
    option_retained: str
    justification: str
    validity_domain: str
    discarded_variants: tuple[str, ...]
    decided_by: str
    decided_at: dt.datetime
    superseded_decisions: int
    application: Literal["proposition seulement"] = "proposition seulement"

    @model_validator(mode="after")
    def _precedent_rules(self) -> Precedent:
        if not any(isinstance(s, DecisionEvidence) for s in self.sources):
            message = f"{self.id} : un précédent cite la décision qui le fonde"
            raise ValueError(message)
        if not self.validity_domain.strip():
            message = f"{self.id} : un précédent porte son domaine de validité"
            raise ValueError(message)
        return self

    def specific_text(self) -> list[str]:
        return [
            self.topic,
            self.option_retained,
            self.justification,
            self.validity_domain,
            *self.discarded_variants,
        ]


ENTRY_TYPES: dict[LayerName, type[KnowledgeEntry]] = {
    "diagnostics": Diagnostic,
    "patrons": Pattern,
    "controles": Control,
    "references_validation": ValidationReference,
    "precedents": Precedent,
}


__all__ = [
    "ENTRY_TYPES",
    "LAYERS",
    "LEVEL_ORDER",
    "STATUSES",
    "YAML_LAYERS",
    "CaughtError",
    "CodeEvidence",
    "ConstatEvidence",
    "Control",
    "DecisionEvidence",
    "Diagnostic",
    "DocumentEvidence",
    "Evidence",
    "ExecutionEvidence",
    "KnowledgeEntry",
    "LayerName",
    "Level",
    "Pattern",
    "Precedent",
    "ReferenceCase",
    "ReferenceQuantity",
    "Reuse",
    "Signature",
    "Status",
    "StatusEvent",
    "TestEvidence",
    "ValidationReference",
    "evidence_level",
    "is_proof",
    "is_replayable",
    "max_level",
]
