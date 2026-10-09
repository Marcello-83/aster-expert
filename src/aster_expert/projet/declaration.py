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
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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
    ncpus: int | None = Field(default=None, gt=0)
    """Lot 47 quater: threads per MPI process; `None`, the machine's default."""
    mpi_nbcpu: int | None = Field(default=None, gt=0)
    """Lot 47 quater: MPI processes; `None`, the machine's default."""
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
    direction: Component | tuple[Component, ...]
    """One component, or several (lot 47: horizontal springs kx = ky act along DX
    and DY)."""
    forces: str
    """Extension `f(ctx, mess_text, case) -> {label: Σ k·u}` along `direction`;
    with several directions, `{label: {component: Σ k·u}}`."""
    stiffness_check: str | None = None
    """Extension `f(ctx, comm_text) -> dict`, reported as is."""

    @property
    def components(self) -> tuple[Component, ...]:
        """The directions as a tuple, one or several."""
        if isinstance(self.direction, tuple):
            return self.direction
        return (self.direction,)

    @model_validator(mode="after")
    def _extensions(self) -> SpringsSection:
        if isinstance(self.direction, tuple) and (
            not self.direction or len(set(self.direction)) != len(self.direction)
        ):
            message = f"ressorts : directions vides ou répétées {self.direction}"
            raise ValueError(message)
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
    self_equilibrated_scale: str | None = None
    """Lot 47 bis (CTL-005 and CTL-013, version 2): a self-equilibrated case (applied
    load zero by construction, e.g. a uniform temperature) declares the extension
    that gives the scale of its gaps, `f(ctx, mess_text, case, *, comm_text) ->
    {"value_n": S, "definition": text}`; without it the relative gap of a zero load
    is undefined (NaN). Refused on a case whose applied load is not zero."""

    @model_validator(mode="after")
    def _extension(self) -> LoadCase:
        if isinstance(self.expected_resultant, str):
            _check_extension(self.expected_resultant)
        if self.self_equilibrated_scale is not None:
            _check_extension(self.self_equilibrated_scale)
        return self


class SymmetryPlane(_Model):
    normal: Axis
    position: float = 0.0
    table: str = "SYMETRIE_{case}"
    cases: tuple[str, ...]
    coordinate_tolerance: float = 1.0e-6


class DisabledControl(_Model):
    """A default-harness control the project does not apply, with its written reason
    (lot 46, step 6). The results note shows it."""

    id: str
    reason: str

    @field_validator("reason")
    @classmethod
    def _written(cls, value: str) -> str:
        if len(value.split()) < 4:
            message = (
                "désactiver un contrôle par défaut exige un motif écrit (au moins une "
                "phrase)"
            )
            raise ValueError(message)
        return value


class ConvergenceSection(_Model):
    """Mesh convergence data of a project aiming at level E (control CTL-012)."""

    series: str
    """Extension `f(ctx) -> {'series': {quantity: [error per mesh, coarse to fine]},
    'final_threshold': x, 'source': text}`: results of the project's own runs."""


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
    convergence: ConvergenceSection | None = None
    """Lot 46: mesh convergence series, required of a project aiming at level E."""
    disabled: tuple[DisabledControl, ...] = ()
    """Lot 46: default-harness controls the project does not apply, each with a
    written reason (never silent)."""


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
    "contre_calcul",
    "visualisation",
]
"""Sections of a results package (lot 45): what a results note may display is
decided by the sections the package holds, never by the project's name. Lot 47:
`contre_calcul`, the comparison with an external calculation that is not validated
(never a level E). Lot 49: `visualisation`, the manifest of the deliverables (MED, VTU,
ParaView), their tables and pictures."""

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
    subdirectory: str | None = Field(default=None, pattern=r"^[a-z0-9_]+$")
    """Lot 49 bis: sub-directory of the section the files go to
    (`visualisation/flexion_composee/`), one level, never `..`."""


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
    unit: str | None = None
    """Lot 48 bis: unit of the column; without `format`, the number is shown with the
    decimals `config/arrondis.yaml` gives that unit (display only, the file is not
    changed)."""


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


FieldFamily = Literal[
    "deplacements",
    "efforts_coques",
    "efforts_poutres",
    "contraintes_volumes",
    "reactions",
    "ressorts",
]
"""Families of result fields a deliverable declares (lot 49): each one is either
written or declared not relevant, with a written reason."""

DeliverableItem = Literal[
    "deplacements",
    "efforts_coques",
    "efforts_poutres",
    "contraintes_volumes",
    "reactions",
    "ressorts",
    "cas_elementaires",
    "combinaisons",
    "enveloppes",
    "charges",
]

_FIELD_OF_FAMILY: dict[str, frozenset[str]] = {
    "deplacements": frozenset({"DEPL"}),
    "efforts_coques": frozenset({"EFGE_NOEU", "EFGE_ELNO"}),
    "efforts_poutres": frozenset({"EFGE_ELNO", "EFGE_NOEU"}),
    "contraintes_volumes": frozenset({"SIGM_NOEU", "SIEF_NOEU", "SIGM_ELNO"}),
    "reactions": frozenset({"REAC_NODA"}),
    "ressorts": frozenset({"SIEF_ELGA"}),
}
"""Code_Aster fields admitted for each family (catalogue names of `NOM_CHAM`)."""


def _written_reason(value: str) -> str:
    if len(value.split()) < 4:
        message = "un motif écrit est exigé (au moins une phrase)"
        raise ValueError(message)
    return value


class DeliverableField(_Model):
    """One result field written to the deliverable files, on some groups."""

    family: FieldFamily
    field: str
    """Code_Aster field (`NOM_CHAM`): `DEPL`, `EFGE_NOEU`, `EFGE_ELNO`, `REAC_NODA`,
    `SIEF_ELGA` (forces of discrete elements), `SIGM_NOEU`..."""
    groups: tuple[str, ...] = ()
    """Cell groups (`GROUP_MA`) the field is restricted to; empty: the whole model."""
    node_groups: tuple[str, ...] = ()
    """Node groups (`GROUP_NO`), for nodal reactions only."""
    components: tuple[str, ...] = ()
    """`NOM_CMP`; empty: every component of the field."""
    convention: str = Field(min_length=10)
    """Frame and sign convention, as the reader must know them (the workbook's
    « Conventions » sheet shows it word for word)."""

    @model_validator(mode="after")
    def _consistent(self) -> DeliverableField:
        allowed = _FIELD_OF_FAMILY[self.family]
        if self.field not in allowed:
            message = (
                f"livrables : famille {self.family}, champ {self.field} non admis "
                f"({', '.join(sorted(allowed))})"
            )
            raise ValueError(message)
        if self.node_groups and self.field != "REAC_NODA":
            message = "livrables : `node_groups` est réservé à REAC_NODA"
            raise ValueError(message)
        if self.groups and self.node_groups:
            message = "livrables : `groups` ou `node_groups`, pas les deux"
            raise ValueError(message)
        return self


class NotRelevant(_Model):
    """A deliverable the project does not produce, with its written reason."""

    item: DeliverableItem
    reason: str

    @field_validator("reason")
    @classmethod
    def _written(cls, value: str) -> str:
        return _written_reason(value)


class IgnoredResult(_Model):
    """A result concept of the `.comm` that is not an elementary case (a combination
    already computed by Code_Aster, a sensitivity run...), with its reason."""

    result: str
    reason: str

    @field_validator("reason")
    @classmethod
    def _written(cls, value: str) -> str:
        return _written_reason(value)


class ExclusionDisk(_Model):
    """PAT-013: around each node of `node_group`, a closed disc of `radius` (in the
    plane XY) where a maximum of the plate is not read (singular support)."""

    node_group: str
    radius: float = Field(gt=0)
    groups: tuple[str, ...] = ()
    """Cell groups whose values the disc excludes; empty: every group."""
    source: str = Field(min_length=10)
    """Who decided it (a decision of MM, a pattern)."""


class ReadingPoint(_Model):
    """A place whose values the workbook lists case by case (pile heads, centre of a
    slab): the nodes of `node_group`; for an element field, the element ends of
    `cell_group` at those nodes."""

    label: str
    node_group: str
    cell_group: str | None = None


class DeliverablesSection(_Model):
    """`deliverables` (lot 49): what a computation hands over to the engineer -- a MED
    of results, a MED of the applied loads, ParaView scripts and pictures, a
    workbook -- declared once, for any project.

    Named in English like every other key of `projet.yaml` (`mesh`, `comm`,
    `controls`, `results_package`). Every family of fields, the elementary cases,
    the combinations, the envelopes and the loads are either produced or listed in
    `not_relevant` with a written reason: nothing is left out in silence.
    """

    units: Literal["m, N, Pa"] = "m, N, Pa"
    """Units of the model; the only system the trunk knows how to label today."""
    fields: tuple[DeliverableField, ...] = Field(min_length=1)
    combinations: str | None = None
    """`declarees` (the `combinations` section of `projet.yaml`) or an extension
    `f(ctx) -> list[dict]` returning combinations with their moving loads
    (`aster_expert.livrables.combinaisons.GenericCombination`)."""
    envelopes: bool = True
    """Max and min of every component over the combinations, with the governing
    combination and moving load position."""
    moving_cases: tuple[str, ...] = ()
    """Patterns (`TSA_*`) of the cases that are positions of a moving load: they are
    enveloped in the combinations, never written one by one, and no MED of loads is
    written for them."""
    static_results: dict[str, str] = Field(default_factory=dict)
    """Result concept of a `MECA_STATIQUE` -> name of its case, when the name is not
    the concept itself nor the concept without `RESU_`."""
    ignored_results: tuple[IgnoredResult, ...] = ()
    not_relevant: tuple[NotRelevant, ...] = ()
    exclusion_disks: tuple[ExclusionDisk, ...] = ()
    points: tuple[ReadingPoint, ...] = ()
    max_med_bytes: int = Field(default=2 * 1024**3, gt=0)
    """Above this size a MED is not copied to the exchange folder (2 Go, lot 49)."""

    @model_validator(mode="after")
    def _complete(self) -> DeliverablesSection:
        declared = {f.family for f in self.fields}
        excused = {n.item for n in self.not_relevant}
        both = declared & excused
        if both:
            message = f"livrables : produit et déclaré non pertinent : {sorted(both)}"
            raise ValueError(message)
        families = set(_FIELD_OF_FAMILY)
        silent = sorted(families - declared - excused)
        if silent:
            message = (
                "livrables : famille ni produite ni déclarée non pertinente (avec "
                f"motif) : {', '.join(silent)}"
            )
            raise ValueError(message)
        if self.combinations is None and "combinaisons" not in excused:
            message = (
                "livrables : `combinations` absent sans motif (not_relevant: "
                "combinaisons)"
            )
            raise ValueError(message)
        if not self.envelopes and "enveloppes" not in excused:
            message = "livrables : enveloppes désactivées sans motif"
            raise ValueError(message)
        if self.combinations not in (None, "declarees"):
            _check_extension(self.combinations)
        return self


# --- Lot 49 bis : synthèse ingénieur -----------------------------------------------

LimitState = Literal[
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
]
"""Limit states of the engineering summary (EN 1990, 6.4.3 and 6.5.3), in this
order."""

LIMIT_STATES: tuple[LimitState, ...] = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
)

MemberKind = Literal["poutre", "coque", "discret", "appui"]

_FIELDS_OF_KIND: dict[str, frozenset[str]] = {
    "poutre": frozenset({"EFGE_ELNO", "EFGE_NOEU"}),
    "coque": frozenset({"EFGE_NOEU", "EFGE_ELNO"}),
    "discret": frozenset({"SIEF_ELGA"}),
    "appui": frozenset({"REAC_NODA"}),
}

LocalFibre = Literal["+z_l", "-z_l", "+y_l", "-y_l", "+n", "-n"]
"""Side of the « top » fibre of a section, in the local frame of the element (beam:
`y_l`, `z_l`; shell: `n`, its normal)."""


class LimitStateFamilies(_Model):
    """A limit state and the combination families (`family` of the combinations of
    the deliverables) that make it."""

    state: LimitState
    families: tuple[str, ...] = Field(min_length=1)


class AbsentLimitState(_Model):
    state: LimitState
    reason: str

    @field_validator("reason")
    @classmethod
    def _written(cls, value: str) -> str:
        return _written_reason(value)


class CrackingState(_Model):
    """The limit state whose combinations serve the control of cracking (label
    `ELSfiss` of the bending export); EN 1992-1-1, 7.3.1 recommends the
    quasi-permanent one."""

    state: LimitState = "ELS_quasi_permanent"
    source: str = Field(min_length=10)


class MemberFamily(_Model):
    """A family of structural members, named as the engineer names that element of
    the structure -- an element of the structure, not a type of field."""

    name: str = Field(min_length=2)
    kind: MemberKind
    field: str
    """Key of a deliverable field (`EFGE_ELNO`, `EFGE_NOEU`, `SIEF_ELGA`,
    `REAC_NODA`)."""
    groups: tuple[str, ...] = Field(min_length=1)
    """Cell groups of the family (node groups for `appui`)."""
    members: str | None = None
    """Pattern (`PIEU_F*`) of the cell groups of each member: detail sheet, diagrams
    and place of each value."""
    quantities: tuple[str, ...] = Field(min_length=1)
    """Components of the design quantities, in the order shown."""
    circular: bool = False
    """Beam of circular section: the moment and the shear are also read as
    resultants √(MFY² + MFZ²) and √(VY² + VZ²)."""
    moments: tuple[str, ...] = ()
    """Beam: bending components whose max and min are design values."""
    shears: tuple[str, ...] = ()
    """Beam: shear components whose largest modulus is a design value."""
    axis: Axis | None = None
    """Beam: global axis along which the members are drawn (diagrams)."""
    caveat: str | None = None
    """What the values of the family are not (« barre seule, CA-058 »)."""

    @model_validator(mode="after")
    def _consistent(self) -> MemberFamily:
        # A field delivered twice is keyed `EFGE_ELNO_2`... (lot 49).
        field = re.sub(r"_\d+$", "", self.field)
        if field not in _FIELDS_OF_KIND[self.kind]:
            message = (
                f"synthèse : famille {self.name}, type {self.kind}, champ "
                f"{self.field} non admis"
            )
            raise ValueError(message)
        bending = {"MFY", "MFZ"} & set(self.quantities)
        if self.kind == "poutre" and bending and not (self.moments or self.circular):
            message = f"synthèse : poutres {self.name} sans `moments` ni `circular`"
            raise ValueError(message)
        unknown = set(self.moments) | set(self.shears)
        unknown -= set(self.quantities)
        if unknown:
            message = f"synthèse : {self.name} : {sorted(unknown)} hors `quantities`"
            raise ValueError(message)
        return self


class CoordinateBox(_Model):
    """Rows whose node lies in the box (bounds included, 1 mm of tolerance); an axis
    of `absolute` is read in absolute value."""

    x: tuple[float, float] | None = None
    y: tuple[float, float] | None = None
    z: tuple[float, float] | None = None
    absolute: tuple[Axis, ...] = ()


class NearGroup(_Model):
    """Rows at a distance `distance` along `axis` (`at`), within it, or beyond it, of
    the coordinates of the nodes of `node_group` (the faces of a support)."""

    node_group: str
    axis: Axis
    distance: float = Field(ge=0)
    mode: Literal["at", "within", "beyond"] = "at"


class Station(_Model):
    """Rows at the mesh coordinate nearest to `value` along `axis` (in absolute value
    with `absolute`): the coordinate actually read is reported."""

    axis: Axis
    value: float
    absolute: bool = False


class SectionRule(_Model):
    """How a design section is read: the rows of the family that satisfy every given
    criterion."""

    description: str = Field(min_length=10)
    node_group: str | None = None
    groups: tuple[str, ...] = ()
    """Cell groups the rows must belong to (within the family)."""
    box: CoordinateBox | None = None
    near: NearGroup | None = None
    station: Station | None = None


class TextOrData(_Model):
    """A text value of an export header, written here or read in the data file."""

    value: str | None = None
    data: str | None = None
    source: str = Field(min_length=3)

    @model_validator(mode="after")
    def _one(self) -> TextOrData:
        if (self.value is None) == (self.data is None):
            message = "en-tête : `value` ou `data`, l'un des deux"
            raise ValueError(message)
        return self


class LengthOrData(_Model):
    """A length of an export header (m or mm in the data file; exported in its own
    unit, converted in the export only)."""

    value: float | None = None
    unit: Literal["m", "mm"] | None = None
    data: str | None = None
    source: str = Field(min_length=3)

    @model_validator(mode="after")
    def _one(self) -> LengthOrData:
        if self.data is None and (self.value is None or self.unit is None):
            message = "en-tête : `value` et `unit`, ou `data`"
            raise ValueError(message)
        if self.data is not None and self.value is not None:
            message = "en-tête : `value` ou `data`, pas les deux"
            raise ValueError(message)
        return self


class BendingPlane(_Model):
    """One plane of bending exported for the bending software (one file)."""

    moment: str
    """`MFY`, `MFZ` (beam), `MXX`, `MYY` (shell), or `resultante` (circular beam)."""
    top_fibre: LocalFibre | None = None
    """Side of the top fibre; not for a resultant (a circular section has none)."""
    label: str = Field(min_length=3)
    rotated: bool = False
    """Section turned by a quarter of a turn for this plane (horizontal bending of a
    beam): h and b of the header are exchanged, ds and di too."""

    @model_validator(mode="after")
    def _fibre(self) -> BendingPlane:
        if (self.moment == "resultante") != (self.top_fibre is None):
            message = (
                "export : `top_fibre` est exigée sauf pour la résultante d'une section "
                "circulaire"
            )
            raise ValueError(message)
        return self


class BendingExport(_Model):
    """Header of the files `flexion_composee/<section>.csv`, in the order of input of
    MM's bending software (lot 49 bis)."""

    section_type: str = Field(min_length=3)
    h: LengthOrData
    b: LengthOrData
    ds: LengthOrData
    di: LengthOrData
    concrete: TextOrData
    steel: TextOrData
    exposure: TextOrData
    cnom: LengthOrData
    equivalence: str | None = None
    """Rule (and source) of an equivalent section: a circular section entered as a
    square of the same modulus."""
    per_metre: bool = False
    """Shell: forces per metre width, b = 1.00 m."""
    planes: tuple[BendingPlane, ...] = Field(min_length=1)


class DesignSection(_Model):
    """A named design section of a family, read by an explicit rule."""

    name: str = Field(pattern=r"^[a-z0-9_]+$")
    """File name of its export (`flexion_composee/<name>.csv`)."""
    label: str
    family: str
    rule: SectionRule
    justification: str = Field(min_length=10)
    """One line: why this section is a design section."""
    exclude_singular: bool = True
    """Shell: values inside the exclusion discs (PAT-013) and on the lines of nodes
    shared with `shared_with` (CA-058) are left out of the design value -- or, when
    False, a governing value read there is marked « non significative »."""
    shared_with: tuple[str, ...] = ()
    """Shell: cell groups of the beams whose nodes the shell shares."""
    caveat: str | None = None
    bending_export: BendingExport | None = None
    not_exported: str | None = None
    """Why a section has no bending export (written reason)."""

    @model_validator(mode="after")
    def _export(self) -> DesignSection:
        if self.bending_export is None and self.not_exported is None:
            message = (
                f"section {self.name} : ni `bending_export` ni motif `not_exported`"
            )
            raise ValueError(message)
        if self.not_exported is not None:
            _written_reason(self.not_exported)
        return self


class SpanSet(_Model):
    """Spans of a relative deflection: the nodes of each line (same coordinate along
    `line_axis`) between two consecutive `supports` along `axis` (deflection
    relative to the chord of the supports), or between a support and a free end
    (`cantilevers`: relative to the support)."""

    axis: Axis
    line_axis: Axis
    supports: tuple[float, ...] = ()
    cantilevers: tuple[tuple[float, float], ...] = ()
    """(support, free end) pairs."""


class ServiceCriterion(_Model):
    """A serviceability criterion declared by MM, with its source."""

    name: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str
    kind: Literal["displacement", "relative_deflection"]
    field: str = "DEPL"
    components: tuple[Literal["DX", "DY", "DZ"], ...] = Field(min_length=1)
    """Several components: their resultant."""
    groups: tuple[str, ...] = ()
    node_group: str | None = None
    limit_state: LimitState
    exclude_cases: tuple[str, ...] = ()
    """Cases removed from the combinations (« hors G et hors TE »)."""
    span_m: float = Field(gt=0)
    ratio: float = Field(gt=0)
    """Limit = span_m / ratio."""
    spans: SpanSet | None = None
    verdict: bool = True
    """False: reported for information, without verdict."""
    verdict_groups: tuple[str, ...] = ()
    """Patterns of the member groups the verdict applies to; the other places are
    reported with `note_others`."""
    note_others: str | None = None
    source: str = Field(min_length=10)

    @model_validator(mode="after")
    def _shape(self) -> ServiceCriterion:
        if (self.kind == "relative_deflection") != (self.spans is not None):
            message = f"critère {self.name} : `spans` va avec relative_deflection"
            raise ValueError(message)
        if not self.groups and self.node_group is None:
            message = f"critère {self.name} : `groups` ou `node_group`"
            raise ValueError(message)
        return self


class SlabCut(_Model):
    """A cut of a shell family drawn by the diagrams: the rows on `axis = value`
    (nearest mesh coordinate), along `along`."""

    name: str = Field(pattern=r"^[a-z0-9_]+$")
    family: str
    axis: Axis
    value: float
    along: Axis
    components: tuple[str, ...] = Field(min_length=1)
    shared_with: tuple[str, ...] = ()


class EngineeringSummarySection(_Model):
    """`engineering_summary` (lot 49 bis): the reading an engineer makes of the
    deliverables -- families of members, design sections with concomitant torsors,
    limit states, serviceability criteria, export for the bending software.

    Named `engineering_summary` and not `synthesis`: that key is the project's own
    synthesis step (lots 35 to 37), and the keys of `projet.yaml` are English. Every
    section of a structure is declared here, never in `src/`."""

    limit_states: tuple[LimitStateFamilies, ...] = Field(min_length=1)
    absent_limit_states: tuple[AbsentLimitState, ...] = ()
    cracking: CrackingState
    families: tuple[MemberFamily, ...] = Field(min_length=1)
    sections: tuple[DesignSection, ...] = Field(min_length=1)
    service_criteria: tuple[ServiceCriterion, ...] = ()
    no_service_criteria: str | None = None
    """Why the project declares no serviceability criterion."""
    cuts: tuple[SlabCut, ...] = ()

    @model_validator(mode="after")
    def _complete(self) -> EngineeringSummarySection:
        states = [s.state for s in self.limit_states]
        absent = [s.state for s in self.absent_limit_states]
        if len(set(states)) != len(states) or set(states) & set(absent):
            message = "synthèse : un état limite est déclaré deux fois"
            raise ValueError(message)
        silent = sorted(set(LIMIT_STATES) - set(states) - set(absent))
        if silent:
            message = (
                "synthèse : état limite ni déclaré ni absent (avec motif) : "
                + ", ".join(silent)
            )
            raise ValueError(message)
        if self.cracking.state not in states:
            message = (
                f"synthèse : l'état de fissuration {self.cracking.state} est absent"
            )
            raise ValueError(message)
        names = {f.name for f in self.families}
        for section in self.sections:
            if section.family not in names:
                message = f"section {section.name} : famille {section.family} inconnue"
                raise ValueError(message)
        for cut in self.cuts:
            if cut.family not in names:
                message = f"coupe {cut.name} : famille {cut.family} inconnue"
                raise ValueError(message)
        for criterion in self.service_criteria:
            if criterion.limit_state not in states:
                message = (
                    f"critère {criterion.name} : état limite {criterion.limit_state} "
                    "absent"
                )
                raise ValueError(message)
        if not self.service_criteria and self.no_service_criteria is None:
            message = "synthèse : ni critère de service ni motif `no_service_criteria`"
            raise ValueError(message)
        if self.no_service_criteria is not None:
            _written_reason(self.no_service_criteria)
        sections = [s.name for s in self.sections]
        if len(set(sections)) != len(sections):
            message = "synthèse : deux sections de même nom"
            raise ValueError(message)
        return self


StepName = Literal[
    "verifier",
    "maillage",
    "generer",
    "valider",
    "executer",
    "controles",
    "synthese",
    "combinaisons",
    "ferraillage",
    "livrables",
]


class BlockerScope(_Model):
    """The steps that depend on a practice entry under revision (lot 48 bis, R8).

    A revision of the fiche blocks every step unless the project says which steps
    depend on the revised point: any other step runs, and says it waived the
    revision. An entry without a scope blocks every step, as before."""

    point_label: str
    topic: str
    """Exact topic of the entry (a point can hold several entries)."""
    steps: tuple[StepName, ...] = Field(min_length=1)
    """The only steps this revision blocks."""
    reason: str = Field(min_length=1)
    """Why the other steps do not depend on it (shown by the steps that waive it)."""


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
    deliverables: DeliverablesSection | None = None
    """Lot 49: the deliverables of the computation (MED, ParaView, workbook).
    Required of a project created from lot 49 on (`aster-expert projet creer`)."""
    engineering_summary: EngineeringSummarySection | None = None
    """Lot 49 bis: families of members, design sections, limit states,
    serviceability criteria (`aster_expert.livrables.ingenieur`)."""
    results: str = "resultats"
    """Directory, relative to the project, where the steps write their outputs."""
    blocker_scopes: tuple[BlockerScope, ...] = ()
    planned_commands_exemption: str | None = None
    """Lot 48 bis (audit R6): `projet verifier` requires `planned_commands` in the fiche
    (`aster-expert fiche prevoir`). A project whose fiche cannot receive them yet says
    why here; the exemption is shown by `verifier`, never silent."""
    confidential_data: bool = False
    """Lot 48 bis (audit R4): the project is built from real data whose site, client or
    firm names must never be versioned. The list of confidential terms then becomes
    mandatory for the publication check (`aster_expert.publication.missing_terms`)."""
    knowledge_applied: str | None = None
    """Lot 46: declaration of the knowledge the project's runs apply (relative to the
    project directory). Copied next to each `.comm` as `<stem>.connaissances.yaml`
    before the run; a project's run without a declaration is refused."""


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
    "DeliverableField",
    "DeliverablesSection",
    "ExclusionDisk",
    "BendingExport",
    "BendingPlane",
    "DesignSection",
    "EngineeringSummarySection",
    "LIMIT_STATES",
    "LimitState",
    "MemberFamily",
    "ServiceCriterion",
    "ReadingPoint",
    "FieldFamily",
    "IgnoredResult",
    "NotRelevant",
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
