"""Project declaration: the interface between a project and the common trunk
(lot 41, étape 2.3).

A structure is a project, `projets/<name>/`, whose `projet.yaml` declares, and
only declares, what the common trunk needs to verify it: the fiche and the data
file, the mesh and its invariants, the `.comm` file or its generator, the support
and spring groups of the equilibrium, the load cases with their expected
resultants, the symmetry planes, the combinations and the members to reinforce.
The project's own code (generator, integrated loads, spring forces, prose of its
reports) lives in the project's Python package and is named here by
`"<module>:<callable>"`; the trunk never imports a project by name.

Everything is validated by pydantic (`extra="forbid"`); every refusal is turned
into a readable `ProjectError` by `load_declaration`, never a raw
`ValidationError`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aster_expert.projet.errors import ProjectError

DECLARATION_NAME = "projet.yaml"

Component = Literal["DX", "DY", "DZ", "DRX", "DRY", "DRZ"]
Axis = Literal["X", "Y", "Z"]

_EXTENSION = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _check_extension(value: str) -> str:
    if not _EXTENSION.match(value):
        message = (
            f"extension {value!r} : forme attendue « module:fonction » "
            "(ex. mon_ouvrage.extensions:generer)"
        )
        raise ValueError(message)
    return value


class DataRef(_Model):
    """A number read from the project's data file (`group.key`), which is the
    reference: a coefficient written both here and in the data would be a
    duplicate (lot 40 audit, E: `combinations.py`)."""

    data: str


Number = float | DataRef


class MeshSection(_Model):
    invariants: str
    """Invariants file checked by `mesh check` (path relative to the project)."""
    script: str | None = None
    """Salomé script run by `mesh run`."""
    parameters: str | None = None
    """Extension writing the parameters file of the script: `f(ctx) -> bytes`."""
    med: str | None = None
    """Verified MED to use; without it, the one recorded by `mesh check` for the
    script and parameters fingerprints (mesh cache)."""

    @model_validator(mode="after")
    def _parameters_need_a_script(self) -> MeshSection:
        if self.parameters is not None:
            _check_extension(self.parameters)
            if self.script is None:
                message = "maillage : `parameters` sans `script`"
                raise ValueError(message)
        return self


class ExportSection(_Model):
    time_limit: int = 1800
    memory_limit: int = 8192
    mesh_unit: int = 20
    mesh_format: Literal["mmed", "mail"] = "mmed"


class CommSection(_Model):
    output: str
    """Where the generated `.comm` is written (relative to the project)."""
    generator: str | None = None
    """Extension `f(ctx, fiche, data, med) -> (text, report_dict)`."""
    file: str | None = None
    """A `.comm` written by hand, used as is (no generator)."""
    required_data: tuple[str, ...] = ()
    """Data values the generator reads: each must be present and provided, or
    the generation is refused before the generator runs (lot 40 audit, § 5.3)."""
    export: ExportSection = Field(default_factory=ExportSection)

    @model_validator(mode="after")
    def _generator_or_file(self) -> CommSection:
        if (self.generator is None) == (self.file is None):
            message = "comm : exactement un de `generator` ou `file` est requis"
            raise ValueError(message)
        if self.generator is not None:
            _check_extension(self.generator)
        return self


class SupportGroup(_Model):
    group: str
    blocked: tuple[Component, ...]
    """Components actually blocked: only these enter the equilibrium sum."""
    table: str
    """Title of its reaction table in the `.mess`, with `{case}` (e.g.
    `REAC_SYMG_{case}`)."""
    in_mesh: bool = True
    """`False` for a group created by the `.comm` itself."""


class TotalReactions(_Model):
    label: str
    table: str


class SpringsSection(_Model):
    groups: tuple[str, ...]
    """Spring groups (created by the `.comm`, `CREA_POI1`)."""
    direction: Component
    forces: str
    """Extension `f(ctx, mess_text, case) -> {label: Σ k·u}` along `direction`."""
    stiffness_check: str | None = None
    """Extension `f(ctx, comm_text) -> dict`, reported as is."""

    @model_validator(mode="after")
    def _extensions(self) -> SpringsSection:
        _check_extension(self.forces)
        if self.stiffness_check is not None:
            _check_extension(self.stiffness_check)
        return self


class Resultant(_Model):
    DX: float
    DY: float
    DZ: float


class LoadCase(_Model):
    name: str
    expected_resultant: Resultant | str | None = None
    """The applied load expected for this case (N), or the extension that
    computes it: `f(ctx, case) -> {"as_evaluated": {...}, "specified": {...}}`.
    A case without an expected resultant is refused (étape 3)."""
    gravity: bool = False
    """The case carries the self-weight: its vertical balance is the gravity
    check."""
    informative: bool = False
    """Balance reported without verdict (point loads, lot 33)."""

    @model_validator(mode="after")
    def _extension(self) -> LoadCase:
        if isinstance(self.expected_resultant, str):
            _check_extension(self.expected_resultant)
        return self


class SymmetryPlane(_Model):
    normal: Axis
    position: float = 0.0
    table: str = "SYMETRIE_{case}"
    cases: tuple[str, ...]
    coordinate_tolerance: float = 1.0e-6


class ControlsSection(_Model):
    threshold: float = 1.0e-6
    vertical: Component = "DZ"
    """Component along which the self-weight acts (gravity check)."""
    output: str = "equilibre.json"
    total_reactions: TotalReactions | None = None
    supports: tuple[SupportGroup, ...]
    springs: SpringsSection | None = None
    cases: tuple[LoadCase, ...]
    symmetry_planes: tuple[SymmetryPlane, ...] = ()
    extra: str | None = None
    """Extension run after the controls, `f(ctx, run_dir, out_dir) -> list[Path]`
    (project-specific products, e.g. the integrated loads file)."""


class VariableAction(_Model):
    name: str
    psi0: Number
    psi1: Number
    psi2: Number


class ExplicitCombination(_Model):
    name: str
    family: str
    coefficients: dict[str, Number]


class ElementForces(_Model):
    table: str
    """Marker of the per-case element-force table (`##<table>ASTER`), with
    `{case}`."""
    components: tuple[str, ...]
    cases: tuple[str, ...]
    reference_case: str


class ManualCheck(_Model):
    combination: str
    node_nearest_x: float


class CombinationsSection(_Model):
    """EN 1990 families built from declared rules and data values: fundamental
    (6.10, unfavourable and favourable permanent block, each variable action
    dominant with and without the others), accidental combinations written out,
    characteristic, frequent and quasi-permanent."""

    permanent: tuple[str, ...]
    gamma_g_unfavourable: Number
    gamma_g_favourable: Number | None = None
    """Without it, no fundamental combination with the permanent block favourable
    (lot 43: a simply supported span where G is always unfavourable)."""
    gamma_q: Number
    variables: tuple[VariableAction, ...]
    frequent_accompanying: Literal["psi0", "psi2"] = "psi2"
    """ψ of the accompanying actions in the frequent combination (EN 1990 6.15b:
    ψ2)."""
    accidental: tuple[ExplicitCombination, ...] = ()
    forces: ElementForces | None = None
    manual_check: ManualCheck | None = None
    output: str = "combinaisons"
    report: str | None = None
    """Extension writing the project's report,
    `f(ctx, result, **context) -> {file name: text}`."""


class RebarFamily(_Model):
    family: str
    type_comb: Literal["ELU", "ELS", "ELS_QP"]
    gamma_c: float | None = None
    gamma_s: float | None = None


class RebarMember(_Model):
    """A 1D member designed by `CALC_FERRAILLAGE` on its combined forces (the
    `ssll13*` scheme of the official test cases: one SEG2 per section)."""

    group: str
    label: str
    hy: Number
    hz: Number
    cover: Number
    phi_mm: Number
    wk_mm: Number
    fck_mpa: Number
    fyk_mpa: Number
    eys_pa: Number
    alpha_cc: float = 1.0
    kt: float = 0.4
    alpha_e: float = 15.0
    sigma_s_ratio: float = 0.8
    sigma_c_ratio: float = 0.6
    sigma_c_qp_ratio: float = 0.45
    families: tuple[RebarFamily, ...]
    check_sections: dict[str, float] = Field(default_factory=dict)
    comm_header: tuple[str, ...] = ()
    """Comment lines at the top of the generated `.comm`."""
    mesh_title: str = "poutre"
    """Title of the synthetic mesh file (one SEG2 per section)."""
    output: str = "ferraillage"
    report: str | None = None
    """Extension `f(ctx, result, out_dir)` writing the Markdown and the figure."""


class RebarPlate(_Model):
    """A plate (DKT, `TYPE_STRUCTURE='2D'`) designed by `CALC_FERRAILLAGE` on the
    combined results of the project's own `.comm` (lot 43): the commands are
    written by `aster_expert.ferraillage.plaque.plate_rebar_block`, called by the
    project's generator, and read back by the `ferraillage` step, which also
    checks the densities at `check_node` with the independent module
    `aster_expert.rebar`. Units are named by
    each field; a value read from the data file must carry the unit named by its
    field (`_mm`, `_mpa`, `_m`), never converted."""

    group: str
    """Cell group of the plate (`GROUP_MA`)."""
    label: str
    thickness_m: Number
    """Plate thickness."""
    cover_mm: Number
    """Distance from each face to the axis of its bars, `C_INF` = `C_SUP`: one
    value per face for both directions in 2D (catalogue 17.4)."""
    fck_mpa: Number
    fyk_mpa: Number
    fctm_mpa: Number
    eys_mpa: Number
    alpha_cc: Number
    """Written explicitly: the catalogue default is 0.85."""
    sigma_s_ratio: Number
    """`SIGS_ELS` = ratio x fyk (characteristic ELS)."""
    sigma_c_els_mpa: Number
    """`SIGC_INF_ELS` = `SIGC_SUP_ELS` (mandatory in 2D at the ELS)."""
    sigma_c_els_qp_mpa: Number
    alpha_e: Number
    kt: Number
    wk_mm: Number
    phi_mm: Number
    families: tuple[RebarFamily, ...]
    """Combination family (as named by `aster_expert.combinaisons.enumeration`)
    -> `TYPE_COMB`, with the partial factors of the ULS families."""
    check_node: str
    """Node group (one node) of the independent check: the elements around it
    are compared with `aster_expert.rebar`."""
    output: str = "ferraillage"

    @model_validator(mode="after")
    def _uls_families_have_factors(self) -> RebarPlate:
        for f in self.families:
            if f.type_comb == "ELU" and (f.gamma_c is None or f.gamma_s is None):
                message = f"famille {f.family} (ELU) : gamma_c et gamma_s sont requis"
                raise ValueError(message)
        return self


class RebarSection(_Model):
    members: tuple[RebarMember, ...] = ()
    plates: tuple[RebarPlate, ...] = ()

    @model_validator(mode="after")
    def _not_empty(self) -> RebarSection:
        if not self.members and not self.plates:
            message = "ferraillage : ni `members` (1D) ni `plates` (2D)"
            raise ValueError(message)
        return self


class SynthesisSection(_Model):
    extension: str
    """Extension `f(ctx, run_dir, out_dir, level_d_path, views) -> list[Path]`."""


PackageSectionName = Literal[
    "maillage",
    "validation",
    "controles",
    "niveau_e",
    "cas",
    "combinaisons",
    "ferraillage",
]
"""Sections of a results package (lot 45): what a results note may display is
decided by the sections the package holds, never by the project's name."""

PACKAGE_MAX_BYTES = 20 * 1024 * 1024
"""Ceiling of a results package (lot 45, 20 Mo per project)."""


class PackageItem(_Model):
    """Files copied into the results package: a path or a glob, relative to
    the project directory (its results or its versioned references)."""

    section: PackageSectionName
    source: str
    label: str | None = None
    """Short label (a caption), never a sentence of hypothesis."""
    required: bool = True
    """A required item that matches nothing refuses the export."""


class PackageCriterion(_Model):
    """Document in which the criteria of a level were written before the
    execution; the export records the commit that introduced it."""

    level: Literal["D", "E"]
    document: str
    """Path relative to the repository."""


class PackageLevelE(_Model):
    """Comparison to a validated reference (level E), run by the project."""

    results: str
    """JSON relative to the project, holding `verdicts: {id: {verdict: ...}}`."""
    criteria_ids: tuple[str, ...] = Field(min_length=1)
    """The verdicts that make level E (the file may hold others: level D,
    reinforcement, informative ones), each of which must read `RÉUSSI`."""
    comm: str | None = None
    """`.comm` of the reference execution (relative to the project): compared,
    line by line, to the `.comm` of the packaged execution."""


class NoteColumn(_Model):
    """One column of a table of the results note: a header and where to read the
    value in a row (a column name of a CSV, or a dotted path of a JSON row)."""

    header: str
    path: str
    format: str | None = None
    """Python format of a number, e.g. `{:.4e}`; by default 6 significant digits."""


class NoteTable(_Model):
    """A table of the results note (lot 45), read from a file of the package:
    nothing is computed, each cell is a value of the file."""

    section: PackageSectionName
    """Where the note shows it (`cas`: results by case...)."""
    title: str
    source: str
    """CSV or JSON file of the package, relative to the package directory."""
    rows: str | None = None
    """JSON: dotted path of the list (or dict) of rows; `*` iterates the elements or
    the values of a list or dict (`cases.*.ties`); a column path starting with `^`
    reads the enclosing element (`^case`), `^^` the one above; `$key` is the key of the
    row in its dict, `^$key` the key of the enclosing element."""
    key_header: str | None = None
    """JSON dict of rows: header of the extra first column holding each key."""
    columns: tuple[NoteColumn, ...] = Field(min_length=1)
    step: int = Field(default=1, ge=1)
    """One row out of `step` (the first one included); the note says so."""
    max_rows: int = Field(default=60, ge=1, le=500)


class NoteFigures(_Model):
    """Existing figures of the package shown in the results note (lot 45)."""

    section: PackageSectionName
    pattern: str
    """Glob relative to the package directory (`cas/deformee_*.png`)."""
    title: str
    caption: str = "{stem}"
    """`{stem}`: file name without suffix."""
    max_figures: int = Field(default=12, ge=1, le=60)
    width_cm: float = Field(default=16.0, gt=0, le=17.0)


class ResultsPackageSection(_Model):
    """`aster-expert projet exporter-resultats <nom>` (lot 45): a versionable
    package of results -- tables, existing figures, fingerprints, level reached
    -- never a MED file."""

    output: str = "paquet"
    """Directory, relative to the project's results directory."""
    max_bytes: int = PACKAGE_MAX_BYTES
    items: tuple[PackageItem, ...]
    criteria: tuple[PackageCriterion, ...] = ()
    level_e: PackageLevelE | None = None
    note_tables: tuple[NoteTable, ...] = ()
    note_figures: tuple[NoteFigures, ...] = ()

    @model_validator(mode="after")
    def _within_ceiling(self) -> ResultsPackageSection:
        if not 0 < self.max_bytes <= PACKAGE_MAX_BYTES:
            message = (
                f"paquet de résultats : max_bytes={self.max_bytes}, plafond "
                f"{PACKAGE_MAX_BYTES} octets (20 Mo)"
            )
            raise ValueError(message)
        if Path(self.output).is_absolute() or ".." in Path(self.output).parts:
            message = "paquet de résultats : `output` doit rester sous les résultats"
            raise ValueError(message)
        return self


class ProjectDeclaration(_Model):
    schema_version: Literal[1]
    name: str
    """Directory name under `projets/`, and name of the project's package."""
    structure: str
    """Identifier of the structure: must equal the data file's `project`."""
    variants: tuple[str, ...] = ()
    """Other data identifiers of the same structure, admitted in place of
    `structure` (reduced models of diagnosis, finer meshes)."""
    fiche_project_name: str | None = None
    """The fiche's `project_name`, when it is not `structure` itself (a fiche
    written before its data file may carry a longer name)."""
    description: str
    fiche: str
    data: str
    data_sources: str | None = None
    mesh: MeshSection
    comm: CommSection
    controls: ControlsSection | None = None
    combinations: CombinationsSection | None = None
    rebar: RebarSection | None = None
    synthesis: SynthesisSection | None = None
    results_package: ResultsPackageSection | None = None
    results: str = "resultats"
    """Directory, relative to the project, where the steps write their outputs."""


def _format_validation_error(exc: ValidationError) -> tuple[str, ...]:
    out = []
    for err in exc.errors():
        where = ".".join(str(p) for p in err["loc"]) or "(racine)"
        kind = err["type"]
        if kind == "missing":
            out.append(f"champ manquant : {where}")
        elif kind == "extra_forbidden":
            out.append(f"champ inconnu : {where}")
        else:
            out.append(f"{where} : {err['msg']}")
    return tuple(out)


def load_declaration(path: Path) -> ProjectDeclaration:
    """Read and validate `projet.yaml`; any defect is a readable `ProjectError`."""
    if not path.is_file():
        message = f"déclaration de projet introuvable : {path}"
        raise ProjectError(message)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        message = f"déclaration illisible (YAML) : {path} : {exc}"
        raise ProjectError(message) from exc
    if not isinstance(raw, dict):
        message = f"déclaration vide ou qui n'est pas une table YAML : {path}"
        raise ProjectError(message)
    try:
        return ProjectDeclaration.model_validate(raw)
    except ValidationError as exc:
        message = f"déclaration incomplète ou incohérente : {path}"
        raise ProjectError(message, _format_validation_error(exc)) from exc


__all__ = [
    "DECLARATION_NAME",
    "CombinationsSection",
    "CommSection",
    "ControlsSection",
    "DataRef",
    "ElementForces",
    "ExplicitCombination",
    "LoadCase",
    "PACKAGE_MAX_BYTES",
    "ManualCheck",
    "MeshSection",
    "Number",
    "PackageCriterion",
    "PackageItem",
    "PackageLevelE",
    "NoteColumn",
    "NoteFigures",
    "NoteTable",
    "PackageSectionName",
    "ProjectDeclaration",
    "RebarFamily",
    "RebarMember",
    "RebarPlate",
    "RebarSection",
    "Resultant",
    "ResultsPackageSection",
    "SpringsSection",
    "SupportGroup",
    "SymmetryPlane",
    "SynthesisSection",
    "TotalReactions",
    "VariableAction",
    "load_declaration",
]
