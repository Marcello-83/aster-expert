"""Schema for a structure's fiche d'hypothèses (lot 14).

`docs/development-plan.md` (clôture lot 8c) already flagged the limit a real
usage attempt ran into: the Code_Aster corpus documents *operators*, not
*engineering practice*. Confirmed again, more sharply, at the opening of
this lot: the corpus founds an element choice, a slenderness criterion, a
connection mechanism, the available constitutive laws and their domain, the
loading/boundary keywords -- it never founds how to represent a geotechnical
tie-back anchor, the choice between contact/springs/joints for a soil-wall
interface, an earth-pressure calculation, an excavation phasing, or where a
soil model's boundaries sit. A fiche d'hypothèses that blends both kinds of
answer, indistinguishably, would let a downstream generator manufacture a
justification for an engineering choice the corpus never made (CLAUDE.md,
principle 11: "aucun document, résultat ou extrait synthétique ne doit être
présenté comme réel").

This module defines the data structure only (M1-M4) -- no `.comm`
generation, no mesh template, no automatic fiche authoring (explicitly out
of scope for this lot). It never imports from `aster_expert.retrieval`,
`.indexing` or `.catalogue`: a caller who already has a `SearchHit`, a
`DocumentSection` or a `CommandSchema` builds a `DocumentarySource`/
`CatalogueSource` from its own citation fields (`docs/metadata.md` §6,
`.claude/skills/code-aster-expert/references/citation.md`) -- this module
does not re-fetch or re-validate that citation itself.

**M2, the safety property, enforced by structure, not by prose.**
`HypothesisEntry` is a discriminated union of two *disjoint* concrete
classes, `CodeAsterHypothesisEntry` and `PracticeHypothesisEntry`, chosen by
the `nature` field itself, not derived after the fact from whichever source
happens to be attached. `PracticeHypothesisEntry.sources` is typed
`tuple[PracticeSource, ...]` -- a `CodeAsterSource` is not merely discouraged
there, it is not a member of that field's type at all, and every model here
carries `extra="forbid"` (a deliberate departure from this project's usual
bare `frozen=True`, justified by this one safety property): passing a
`document_id` to a `PracticeSource` does not get silently dropped, it raises
`pydantic.ValidationError`. An entry's `nature` is fixed at the moment it is
written -- a `pratique` question, whether or not it has been settled yet,
can never later acquire a documentary source, because the field that would
carry one is never present on that branch of the union.

**M5, corrected against a real specimen.** A first draft of this schema
(before M5) modelled a single, mandatory, fully-populated `source` per
entry. Transcribing the real reference fiche (lot 14, M5) broke that draft
in three ways, each fixed here:

1. A single engineering point is routinely founded by *several* citations
   together (a catalogue schema fact plus one or more documentary
   confirmations) -- `sources` is now a tuple, not an optional singleton.
2. The corpus is reached through two structurally different tool outputs
   that citation.md already treats as distinct
   (`search_codeaster_docs`/`get_document_section` vs `get_command_schema`)
   -- `CodeAsterSource` is now a discriminated union of `DocumentarySource`
   and `CatalogueSource`, never one class straining to cover both shapes.
3. The specimen cites a document/section, or a catalogue command/keyword,
   without always capturing every field a live tool call would carry
   (`source_commit`, `excerpt`, `source_path`, `catalogue_source`/
   `catalogue_hash`/`image_digest` are frequently absent from the fiche's
   own prose; some citations give a document id and section but no path
   -- R7.01.28, R7.01.14, R7.01.18, R7.01.25 -- and one, R7.01.23, gives
   only a document id, no section at all; and in one case -- U2.02.01's
   comparison table -- the section is correctly identified while its
   content was explicitly never read). Requiring those fields would have
   forced fabricating them to transcribe a real fiche, exactly what this
   project forbids (CLAUDE.md, principle 11) -- an early draft of the
   transcription script did exactly that, synthesizing a plausible-looking
   `source_path` for every citation and even inventing a section for
   R7.01.23; caught by comparing the draft output against the specimen's
   own text before this fiche was committed, not by any test. They are all
   optional/defaultable here; a document known but not yet located down to
   a path, or identified but not yet read, is a real, representable state
   ("the place is known, the content is not confirmed read"), not a schema
   defect to paper over.

A fourth gap surfaced too: `option_retained`/`justification` describe a
*decision*, but the specimen also carries evidence that is not a decision at
all -- which search profiles and queries were tried and came back empty
(feeding `status="non_tranche"`), and deductions that connect catalogue
facts to the project's situation without a document stating the conclusion
directly (CLAUDE.md principle 6's "distinguer faits, déductions,
recommandations", at the prose level in
`.claude/skills/code-aster-expert/references/answer-format.md`, needed a
place to land inside this *structured* schema too). `notes` on every entry
carries exactly this, unconstrained by `status`.

**N1 (lot 14b), the gap M5 left open on purpose.** M5's own "Limites
connues" named it: nothing stopped a `tranche` entry from citing a document
by id/section alone, never actually read -- exactly what the reference
specimen itself did for R7.01.25 (cited for "documente les éléments de
joint", excerpt never captured). `_require_a_verbatim_excerpt_when_documentary`
makes that structural rather than a matter of skill discipline: a `tranche`
entry that cites any `DocumentarySource` must have a real, non-empty
`excerpt` on at least one of them. The reference specimen's R7.01.25
citation was itself corrected against this rule -- by reading the document
for real (`get_document_section`), not by inventing a passage to satisfy
the validator.

**P1/P2 (lot 15), the gap lot 14b left open by construction.** Lot 14b gave
an LLM drafting session exactly two write paths, neither able to produce a
decided `pratique` entry (`aster_expert.agent.drafting`). That barrier also
meant no path existed for a *human* decision either: `PracticeSource` has
existed since M1, yet nothing before this lot ever built a
`PracticeHypothesisEntry(status="tranche", ...)`, so the reference
specimen's eight `pratique`/`non_tranche` entries were structurally unable
to leave that state. `PracticeHypothesisEntry` now requires, when
`status="tranche"`: at least one `discarded_variants` entry (an arbitration
with no alternative actually weighed is not one) and both `decided_by` and
`decided_at` (P2 -- "qui a tranché et quand"). A re-arbitrated entry keeps
its previous decision in `decision_history` (`PriorDecision`, append-only,
frozen like every model here) rather than overwriting it: the fiche feeds a
note de calcul, and which option was retained *before* the current one is
part of that record. Both requirements are enforced by this model's own
validator, not by whichever function happens to build the entry -- see
`aster_expert.agent.arbitration.record_practice_decision`, the one function
meant to call this, but the guarantee holds against any construction path,
including a hand-built one.

**R1 (lot 17), the gap lot 16 hit trying to arbitrate for real.** Lot 15's
own "Limites connues" already predicted this: nothing on `_HypothesisEntryBase`
carried a decision's *known limits* -- so when a real arbitration file
(the engineer's arbitration file of lot 16) gave every decision a distinct "Limites
connues" member alongside "Retenu"/"Écarté", `record_practice_decision`
could not record a single one of its nine decisions without either
inventing a `justification` the engineer never wrote or dropping the
limits entirely (`docs/development-plan.md`, clôture lot 16, Q1). `notes`
was not the answer: it is already claimed, verbatim, by
`render_decision_sheet`'s "Cherché et non trouvé" (M5 correction 4) -- a
search trace, not a decision's own bound.

`validity_domain: str | None` fixes this, and is deliberately asymmetric
between the two natures. On `PracticeHypothesisEntry`, a `status="tranche"`
entry requires it non-empty, exactly like `option_retained`/`justification`
(and, symmetrically, a `non_tranche` entry forbids it, like every other
decision field -- there is no limit to state for a decision not yet made):
the domain of validity of a decision is to engineering what the A-E level
is to this project's tooling (CLAUDE.md, "niveaux de validation") -- a
statement of exactly how far the answer can be trusted. A decision reused
outside the domain it was scoped to is the failure mode this whole fiche
exists to prevent (CLAUDE.md, principe 11). On `CodeAsterHypothesisEntry`
it stays optional regardless of `status`, for the same reason `sources` do
(M5, correction 3): the corpus states a documented domain of validity for
some facts (a slenderness bound, a law's isotropy hypothesis) and not for
others, and that is a real, representable difference, never a schema gap
to paper over by forcing a value. Never conflated with `notes` (a search
trace) nor, for a `pratique` entry, with `option_retained` (what was
decided) -- three distinct things a single free-text field would blur back
together. `PriorDecision` carries it too, required exactly like
`option_retained`/`justification`: a superseded decision's own limits are
as much part of the historical record as what was retained (P2's own
reasoning, unchanged).

This lot only carries the field through the schema (`PracticeHypothesisEntry`,
`CodeAsterHypothesisEntry` via the shared base, `PriorDecision`) and the
one function that writes it (`aster_expert.agent.arbitration.
record_practice_decision`). Carrying it further -- into a generated
`.comm` header or a note de calcul -- is explicitly out of scope here
(no generator exists yet, lot 14's own boundary, unchanged): the field is
shaped so that future lot can read it, nothing more is built for it now.

**E1 (lot 22), the origin the lot 21 trial could not record.** A fact
established by running Code_Aster (the `FORCE_COQUE` intensity refers to the
developed area of the elements) fitted neither `DocumentarySource` (it needs
an excerpt of a document nobody wrote) nor `CatalogueSource` (it needs a
catalogue node). `ExecutionSource` is the third member of `CodeAsterSource`:
it binds the fact to the version and image digest, to the repository commit
and the exact bytes (`case_sha256`) of a versioned trial case, to the
quantity measured, the value obtained, the reference it was compared to and
the relative deviation, and to the level actually reached (`C` or `D`, never
higher: `E` needs a validated reference this project has not built). It is
admitted only on `code_aster` entries -- `PracticeHypothesisEntry.sources`
is typed `PracticeSource`, which refuses it as it refuses any documentary
source (M2). Whether the case path exists in the repository is a filesystem
question a pydantic model must not answer on load; it is checked by
`aster_expert.agent.drafting.record_execution_finding` when a finding is
written, and by a test over the versioned fiche.

**V1 (lot 22), the blocker lot 21 missed.** `generation_blockers()` was empty
at lot 21 while decision 2 was being revised: an entry decided yesterday and
under revision today looked exactly like a settled one. `RevisionEvent` /
`PracticeHypothesisEntry.revision_history` make "under revision" an explicit,
reasoned, dated state -- a mandatory `reason`, an author, a date, appended
to an append-only history (never edited), lifted by another event carrying
its own reason (`aster_expert.agent.arbitration.declare_under_revision`,
`lift_revision`, or automatically by a new `record_practice_decision`). An
entry under revision is a generation blocker.
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection
from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

PracticeOrigin = Literal[
    "norme", "precedent_projet", "decision_ingenieur", "arbitrage_mm"
]
"""`arbitrage_mm` (lot 43): a decision written in an arbitration document of MM,
the engineer who supervises every project, reported in a fiche with that
document as `reference`. Dated, like `decision_ingenieur`."""


class DocumentarySource(BaseModel):
    """A citation of one documentary fragment (M1; M5, correction 2).

    Mirrors the citation contract already established for
    `search_codeaster_docs`/`get_document_section`
    (`docs/metadata.md` §6, `.claude/skills/code-aster-expert/references/
    citation.md`) -- names and meanings are never reinvented here.
    `source_commit`, `excerpt` and `source_path` are optional, and
    `section_path` defaults to empty (M5, correction 3): a real fiche can
    correctly name a document while explicitly not having read its content
    yet (the U2.02.01 comparison-table case, lot 14's own worked example of
    the lot 8c/K1 problem this project already fixed), and the reference
    specimen itself cites several documents (e.g. R7.01.28, R7.01.14,
    R7.01.18, R7.01.25) by document id and section alone, without a
    `source_path`, and one (R7.01.23) by document id alone, with no section
    at all. Transcribing that specimen faithfully means these fields must
    be representable as genuinely unknown -- never filled with a
    plausible-looking but invented path or section (CLAUDE.md, principle
    11), which is exactly the mistake an early draft of the transcription
    script made and this optionality exists to make impossible to repeat by
    accident. `profile` records which `search_codeaster_docs` retrieval
    profile (ADR-007) produced this citation, when it came from a search
    rather than a direct `get_document_section` call.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    aster_version: str
    section_path: tuple[str, ...] = ()
    source_path: str | None = None
    source_commit: str | None = None
    fragment_id: str | None = None
    profile: str | None = None
    excerpt: str | None = None


class CatalogueSource(BaseModel):
    """A citation of one catalogue schema fact (M1; M5, correction 2).

    Mirrors `get_command_schema`'s own citation contract
    (`docs/metadata.md` §2, `.claude/skills/code-aster-expert/references/
    citation.md`): `command` and `aster_version` are always known when this
    tool is used, so they stay required; `catalogue_source`/
    `catalogue_hash`/`image_digest` are optional (M5, correction 3) because
    a fiche's prose routinely cites "get_command_schema, COMMANDE, mot-clé
    X, v. 17.4.0" without repeating the catalogue's own provenance hashes.
    `keyword_path` is the dotted path given to `get_command_schema`'s
    `keyword` argument (e.g. `("COMPORTEMENT", "RELATION")`); `variant_id`
    is filled in only when the specific variant was resolved
    (`docs/metadata.md` §2: `path` alone never identifies a node uniquely).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    aster_version: str
    keyword_path: tuple[str, ...] = ()
    variant_id: str | None = None
    catalogue_source: str | None = None
    catalogue_hash: str | None = None
    image_digest: str | None = None


ExecutionLevel = Literal["C", "D"]

_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class ExecutionSource(BaseModel):
    """A fact established by executing a versioned trial case (E1, lot 22).

    Admitted on `code_aster` entries only (see the module docstring).
    `validation_level` is the level the trial actually reached, `C` (run to
    `FIN`) or `D` (results checked physically or against a closed form); the
    trial's own report says what was checked, this field never claims more.
    `relative_deviation` is `(value_obtained - reference_value) /
    reference_value` as a fraction (not a percentage), recomputed and
    compared on validation so that a transcription slip is refused, and
    undefined for a zero reference (refused: state an absolute comparison in
    `reference` instead of a meaningless ratio).

    `repo_commit` is the repository `HEAD` when the case ran; the case files
    are usually not in that commit yet (the batch commit follows the run), so
    `working_tree_modified` says whether the tree was dirty and `case_sha256`
    pins the exact bytes of the case file. `case_path` is relative to the
    repository root and stays inside it. `mess_path`, when a copy of the
    listing was versioned, is relative too.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    aster_version: str
    image_digest: str
    repo_commit: str
    working_tree_modified: bool
    case_path: str
    case_sha256: str
    mess_path: str | None = None
    quantity: str
    value_obtained: float
    reference: str
    reference_value: float
    relative_deviation: float
    validation_level: ExecutionLevel

    @model_validator(mode="after")
    def _check_fields(self) -> ExecutionSource:
        for name in ("aster_version", "quantity", "reference"):
            if not getattr(self, name).strip():
                message = f"une source d'exécution exige `{name}` non vide"
                raise ValueError(message)
        if not _SHA256_DIGEST.match(self.image_digest):
            message = "image_digest doit être de la forme sha256:<64 hexadécimaux>"
            raise ValueError(message)
        if not _GIT_COMMIT.match(self.repo_commit):
            message = "repo_commit doit être un hash Git complet (40 hexadécimaux)"
            raise ValueError(message)
        if not _SHA256_HEX.match(self.case_sha256):
            message = "case_sha256 doit être 64 hexadécimaux"
            raise ValueError(message)
        for name in ("case_path", "mess_path"):
            value = getattr(self, name)
            if value is None:
                continue
            parts = value.split("/")
            if not value or value.startswith("/") or ".." in parts or "" in parts:
                message = (
                    f"`{name}` doit être un chemin relatif à la racine du dépôt, "
                    f"sans `..` : {value!r}"
                )
                raise ValueError(message)
        if self.reference_value == 0.0:
            message = "écart relatif indéfini pour une référence nulle"
            raise ValueError(message)
        expected = (self.value_obtained - self.reference_value) / self.reference_value
        if not math.isclose(
            expected, self.relative_deviation, rel_tol=1e-6, abs_tol=1e-9
        ):
            message = (
                f"relative_deviation={self.relative_deviation} incohérent avec "
                f"(valeur obtenue - référence)/référence = {expected}"
            )
            raise ValueError(message)
        return self


CodeAsterSource = DocumentarySource | CatalogueSource | ExecutionSource
"""No discriminator field: the variants share no common literal tag and
are told apart by their own distinct, non-overlapping required fields
instead (`document_id` vs `command` vs `case_path`) -- pydantic's default "smart" union
mode resolves this without one, and adding a synthetic tag neither
citation.md nor any tool output actually carries would be inventing a field
this schema does not need (M5 discipline: no field beyond what the real
citations require)."""


class PracticeSource(BaseModel):
    """A citation grounded in engineering practice, never in the corpus (M1).

    `origin` distinguishes the three kinds M1 names: `norme` (a normative
    reference -- a standard, a code of practice), `precedent_projet` (a
    prior project's own decision, reused), `decision_ingenieur` (an
    explicit, dated decision by the engineer working this fiche) and, since
    lot 43, `arbitrage_mm` (a decision of MM's arbitration document, named in
    `reference`). `date` is required exactly for these two dated kinds
    ("avec sa date" in M1 reads
    naturally against that one kind: an engineer's decision is a dated
    act; a standard's or a prior project's own reference is already dated
    or identified by `reference` itself, e.g. an edition year or a project
    code).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: PracticeOrigin
    reference: str
    date: date_type | None = None

    @model_validator(mode="after")
    def _decision_requires_a_date(self) -> PracticeSource:
        if self.origin in ("decision_ingenieur", "arbitrage_mm") and self.date is None:
            message = "une décision explicite de l'ingénieur exige une date"
            raise ValueError(message)
        return self


class DiscardedVariant(BaseModel):
    """One option considered and set aside, with the reason (M3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str
    reason: str


class PriorDecision(BaseModel):
    """One superseded arbitration of a `pratique` entry (P2, lot 15).

    Populated only by `aster_expert.agent.arbitration.record_practice_decision`,
    always by moving a `PracticeHypothesisEntry`'s *current* decision fields
    here, verbatim, before replacing them -- never edited in place once
    written (frozen, like every model in this module): re-arbitrating a
    point changes what `PracticeHypothesisEntry` currently asserts, never
    what it asserted before. `validity_domain` (R1, lot 17) is required
    here exactly as it is on the live decision: the limits a superseded
    option was decided under are as much part of the historical record as
    the option itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    option_retained: str
    justification: str
    validity_domain: str
    sources: tuple[PracticeSource, ...]
    discarded_variants: tuple[DiscardedVariant, ...] = ()
    decided_by: str
    decided_at: datetime


class RevisionEvent(BaseModel):
    """One step of a `pratique` entry's revision log (V1, lot 22).

    `declared` opens a revision, `lifted` closes it; each carries a mandatory
    non-blank `reason` (why the decision is in question, or why it stands or
    was replaced), the author and the date. Append-only and frozen, like
    `PriorDecision`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["declared", "lifted"]
    reason: str
    by: str
    at: datetime

    @model_validator(mode="after")
    def _reason_and_author_required(self) -> RevisionEvent:
        if not self.reason.strip() or not self.by.strip():
            message = "un événement de révision exige un motif et un auteur non vides"
            raise ValueError(message)
        return self


def _forbid_decision_fields_when_unresolved(
    *, option_retained: str | None, justification: str | None
) -> None:
    """Shared by both entry classes: `non_tranche` never looks decided.

    Applies regardless of nature or of whether partial `sources` are
    tolerated for that nature (see each class below) -- an option and a
    justification are always specifically a *decision's* record, so their
    presence always means a decision was made, whatever `status` claims.
    """
    if option_retained is not None or justification is not None:
        message = "une entrée non tranchée ne porte ni option retenue ni justification"
        raise ValueError(message)


def _require_decision_fields(
    *,
    status: str,
    sources: tuple[object, ...],
    option_retained: str | None,
    justification: str | None,
) -> None:
    """Shared by both entry classes: a claimed decision must be backed."""
    if not sources:
        message = f"une entrée '{status}' exige au moins une source"
        raise ValueError(message)
    if not option_retained:
        message = f"une entrée '{status}' exige une option retenue"
        raise ValueError(message)
    if not justification:
        message = f"une entrée '{status}' exige une justification"
        raise ValueError(message)


def _require_a_verbatim_excerpt_when_documentary(
    sources: tuple[CodeAsterSource, ...],
) -> None:
    """N1 (lot 14b), closing the gap `docs/development-plan.md` (clôture lot
    14, "Limites connues") named explicitly: "aucune règle n'impose qu'une
    entrée tranche fondée ... par une DocumentarySource porte un excerpt non
    nul". A `document_id`/`section_path` alone is a *reference*, not a
    *proof* -- exactly the defect the lot 6 commande-document table carried
    before its own citation was made to hold the excerpt, not just point at
    it (CLAUDE.md principle 11: no citation stands for content nobody
    actually read).

    Deliberately scoped to `DocumentarySource` only: a `CatalogueSource` has
    no `excerpt` field at all (`citation.md`) because the catalogue node
    `get_command_schema` returns *is* the verbatim fact, not a paraphrase of
    one -- there is nothing to quote a second time. An entry founded solely
    by `CatalogueSource`s is therefore exempt; an entry that also cites a
    document must have actually read at least one of those documents (M5's
    own R7.01.25 gap: cited by id and section, never read -- fixed in the
    reference specimen alongside this validator, not by inventing a passage
    for it, but by calling `get_document_section` for real).
    """
    documentary = [s for s in sources if isinstance(s, DocumentarySource)]
    if documentary and not any((s.excerpt or "").strip() for s in documentary):
        message = (
            "une entrée 'tranche' citant un document exige l'extrait verbatim "
            "qui la fonde (au moins un `excerpt` non vide parmi ses "
            "DocumentarySource) -- une référence sans passage lu n'est pas "
            "vérifiable"
        )
        raise ValueError(message)


class _HypothesisEntryBase(BaseModel):
    """Fields shared by both natures (M3), factored out once M5's real
    transcription needed to add `point_label`/`notes` to both alike rather
    than duplicate them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    point_label: str | None = None
    topic: str
    options_considered: tuple[str, ...] = ()
    option_retained: str | None = None
    justification: str | None = None
    discarded_variants: tuple[DiscardedVariant, ...] = ()
    notes: str | None = None
    validity_domain: str | None = None
    """Known limits of this entry (R1, lot 17) -- distinct from `notes` (a
    search trace) and, for a `pratique` entry, from `option_retained` (what
    was decided). See the module docstring's R1 paragraph for the per-nature
    requirement this base class itself does not enforce."""


class CodeAsterHypothesisEntry(_HypothesisEntryBase):
    """One hypothesis founded on the Code_Aster corpus/catalogue (M1, M3).

    `status` excludes `herite` on purpose: "hérité d'un ouvrage antérieur"
    is inherently a practice fact (a value carried over from a prior
    project), never a documentary one -- re-confirming a corpus fact is
    always either `tranche` (checked, now) or `non_tranche` (not checked
    yet), never "inherited".

    Unlike `PracticeHypothesisEntry`, `sources` is *not* forbidden when
    `non_tranche` (M5, correction 3): a document or section can be
    correctly identified before its content is actually read (the U2.02.01
    comparison-table case) -- that is "found the place, content not yet
    confirmed", not a decision, and must stay representable as such rather
    than being forced to drop the citation altogether.

    `tranche` additionally requires a verbatim excerpt (N1, lot 14b): see
    `_require_a_verbatim_excerpt_when_documentary`.

    `validity_domain` (R1, lot 17) is optional regardless of `status`: the
    corpus states an explicit domain of validity for some facts (a
    slenderness bound, a law's isotropy hypothesis) and not for others, and
    that difference must stay representable rather than being forced.
    """

    nature: Literal["code_aster"] = "code_aster"
    sources: tuple[CodeAsterSource, ...] = ()
    status: Literal["tranche", "non_tranche"]

    @model_validator(mode="after")
    def _status_matches_content(self) -> CodeAsterHypothesisEntry:
        if self.status == "non_tranche":
            _forbid_decision_fields_when_unresolved(
                option_retained=self.option_retained, justification=self.justification
            )
        else:
            _require_decision_fields(
                status=self.status,
                sources=self.sources,
                option_retained=self.option_retained,
                justification=self.justification,
            )
            _require_a_verbatim_excerpt_when_documentary(self.sources)
        return self


class PracticeHypothesisEntry(_HypothesisEntryBase):
    """One hypothesis founded on practice, never on the corpus (M1, M2, M3).

    `sources: tuple[PracticeSource, ...]` -- never `CodeAsterSource`/
    `DocumentarySource`/`CatalogueSource`, see the module docstring (M2):
    this is the field whose *type* makes the safety property structural
    rather than advisory. Unlike the code_aster entry above, `sources` is
    strictly forbidden while `non_tranche`: a practice source only ever
    represents an actual decision (a norme applied, a precedent reused, an
    engineer's dated call) -- there is no partial or "found but unread"
    state for practice the way there is for a document.

    `decided_by`/`decided_at`/`decision_history` (P1/P2, lot 15) exist only
    to record a *human* arbitration of this entry -- see the module
    docstring's P1/P2 paragraph and
    `aster_expert.agent.arbitration.record_practice_decision`. `status=
    "tranche"` requires both `decided_by` and `decided_at` populated, and
    at least one `discarded_variants`; `status="non_tranche"` forbids all
    three fields, symmetrically with `sources`, for the same reason: an
    unresolved point has neither a decision nor an author of one to record.
    `herite` is deliberately left out of this requirement -- it names a
    value inherited from a prior project's own decision, not an
    arbitration made on this fiche, and no function in this project builds
    it (M1, lot 14: hand-built only, unchanged by this lot).

    `validity_domain` (R1, lot 17) follows the same shape as `decided_by`/
    `decided_at`: required non-empty when `status="tranche"` (a decision
    without its known limits stated is refused, not merely encouraged to
    have them), forbidden when `non_tranche` (nothing has been decided, so
    there is no domain to bound yet), and -- like `discarded_variants`/
    `decided_by`/`decided_at` before it -- left unconstrained for `herite`,
    the same deliberate limit named above.
    """

    nature: Literal["pratique"] = "pratique"
    sources: tuple[PracticeSource, ...] = ()
    status: Literal["tranche", "non_tranche", "herite"]
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_history: tuple[PriorDecision, ...] = ()
    revision_history: tuple[RevisionEvent, ...] = ()

    @property
    def under_revision(self) -> bool:
        """True when the last revision event opened a revision (V1, lot 22)."""
        return bool(self.revision_history) and self.revision_history[-1].kind == (
            "declared"
        )

    @property
    def revision_reason(self) -> str | None:
        return self.revision_history[-1].reason if self.under_revision else None

    @model_validator(mode="after")
    def _revision_log_is_coherent(self) -> PracticeHypothesisEntry:
        expected = "declared"
        for event in self.revision_history:
            if event.kind != expected:
                message = (
                    "l'historique de révision doit alterner 'declared' puis "
                    f"'lifted' en commençant par 'declared' (reçu {event.kind!r})"
                )
                raise ValueError(message)
            expected = "lifted" if expected == "declared" else "declared"
        if self.under_revision and self.status == "non_tranche":
            message = (
                "une entrée non tranchée ne peut être « en révision » : "
                "rien n'a été décidé, il n'y a rien à réviser"
            )
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _status_matches_content(self) -> PracticeHypothesisEntry:
        if self.status == "non_tranche":
            if self.sources:
                message = "une entrée pratique non tranchée ne porte aucune source"
                raise ValueError(message)
            _forbid_decision_fields_when_unresolved(
                option_retained=self.option_retained, justification=self.justification
            )
            if (
                self.decided_by is not None
                or self.decided_at is not None
                or self.decision_history
            ):
                message = (
                    "une entrée pratique non tranchée ne porte ni arbitre ni date "
                    "d'arbitrage ni historique -- rien n'a encore été tranché"
                )
                raise ValueError(message)
            if self.validity_domain is not None:
                message = (
                    "une entrée pratique non tranchée ne porte aucun domaine de "
                    "validité -- ce champ documente les limites d'une décision "
                    "(R1, lot 17), et aucune n'a encore été prise"
                )
                raise ValueError(message)
        else:
            _require_decision_fields(
                status=self.status,
                sources=self.sources,
                option_retained=self.option_retained,
                justification=self.justification,
            )
            if self.status == "herite" and not any(
                s.origin == "precedent_projet" for s in self.sources
            ):
                message = (
                    "une entrée 'hérité d'un ouvrage antérieur' exige au moins une "
                    "source 'precedent_projet' -- jamais une norme seule ni une "
                    "décision prise ici"
                )
                raise ValueError(message)
            if self.status == "tranche":
                if not self.discarded_variants:
                    message = (
                        "une entrée pratique tranchée exige les variantes écartées "
                        "avec leur raison (P1, lot 15) -- une décision sans "
                        "alternative examinée n'est pas un arbitrage"
                    )
                    raise ValueError(message)
                if not self.decided_by or self.decided_at is None:
                    message = (
                        "une entrée pratique tranchée exige qui a tranché "
                        "(decided_by) et quand (decided_at) -- P2, lot 15"
                    )
                    raise ValueError(message)
                if not (self.justification or "").strip():
                    message = (
                        "une entrée pratique tranchée exige une justification non "
                        "vide -- une justification blanche est refusée (lot 19)"
                    )
                    raise ValueError(message)
                if not (self.validity_domain or "").strip():
                    message = (
                        "une entrée pratique tranchée exige un domaine de validité "
                        "non vide (R1, lot 17) -- une décision sans limite énoncée "
                        "est refusée, exactement comme une décision sans "
                        "justification"
                    )
                    raise ValueError(message)
        return self


class FindingReference(BaseModel):
    """A `code_aster` finding kept in the shared base of findings, cited by this
    fiche instead of being copied into it (lot 41, étape 4).

    A finding about Code_Aster (a keyword's behaviour, a trap established by a
    trial run) is not a fact of one structure: it belongs to the shared base
    `connaissances/constats_code_aster/` (`aster_expert.constats`), one file per
    finding, and every fiche that relies on it names it by `constat_id`.
    `point_label` stays here, on the reference: it places the finding among
    *this* fiche's points, which the shared base knows nothing about.
    `aster_expert.constats.base.resolve_sheet` replaces each reference by the
    full `CodeAsterHypothesisEntry` of the base (with this `point_label`); an
    unresolved reference is a generation blocker.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    nature: Literal["constat"] = "constat"
    constat_id: str
    point_label: str | None = None


HypothesisEntry = Annotated[
    CodeAsterHypothesisEntry | PracticeHypothesisEntry | FindingReference,
    Field(discriminator="nature"),
]


class MeshGroupNaming(BaseModel):
    """One `GROUP_MA`/`GROUP_NO` name shared, verbatim, by the mesh and the
    `.comm` this fiche will eventually let both be generated from (M4).

    Never sourced from the corpus or from practice (`CodeAsterSource`/
    `PracticeSource` do not apply): a group name is an arbitrary choice of
    this project's engineer, not a fact to cite. Any length or
    character-set constraint the target version's mesh reader might impose
    on `group_name` is not checked here -- not verified against a real
    catalogue or mesh format as of this lot, to be added on evidence rather
    than guessed (CLAUDE.md, "ne jamais deviner"). Not exercised by the M5
    real-case confrontation: the reference specimen predates this section
    and never discusses mesh group names -- validated by unit test only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_name: str
    kind: Literal["maille", "noeud"]
    description: str
    status: Literal["tranche", "non_tranche"] = "non_tranche"
    point_label: str | None = None
    """`point_label` of the fiche point that grounds this group (lot 20),
    checked by `HypothesesSheet.group_naming_gaps`."""


class MissingValues(Protocol):
    """What `generation_blockers` asks of a data file (lot 25)."""

    def missing_values(self) -> tuple[str, ...]: ...


class HypothesesSheet(BaseModel):
    """One structure's fiche d'hypothèses (lot 14).

    `unresolved_entries`/`unresolved_group_names`/`is_ready_for_generation`
    make M2's "bloquera la génération en aval" a property this sheet can
    actually be asked about, not only a sentence in this docstring -- no
    generator is built in this lot (explicitly out of scope), but whatever
    lot builds one has, from day one, a single authoritative check to call
    rather than reinventing its own notion of "ready". `generation_blockers`
    (R3, lot 17) gives the explicit reason behind that boolean, including
    the one case `unresolved_group_names` cannot see on its own: a
    `group_naming` section that was never started at all.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_name: str
    structure_description: str
    aster_version: str | None = None
    created_at: datetime
    entries: tuple[HypothesisEntry, ...] = ()
    group_naming: tuple[MeshGroupNaming, ...] = ()

    @model_validator(mode="after")
    def _group_names_are_unique(self) -> HypothesesSheet:
        names = [g.group_name for g in self.group_naming]
        if len(names) != len(set(names)):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            message = (
                f"noms de groupe en double : {duplicates} -- la coïncidence "
                "maillage/.comm que cette section garantit par construction "
                "exige des noms uniques (M4)"
            )
            raise ValueError(message)
        return self

    def unresolved_entries(
        self,
    ) -> tuple[CodeAsterHypothesisEntry | PracticeHypothesisEntry, ...]:
        return tuple(
            e
            for e in self.entries
            if not isinstance(e, FindingReference) and e.status == "non_tranche"
        )

    def finding_references(self) -> tuple[FindingReference, ...]:
        """References to the shared base still unresolved in this sheet (lot 41)."""
        return tuple(e for e in self.entries if isinstance(e, FindingReference))

    def entries_under_revision(self) -> tuple[PracticeHypothesisEntry, ...]:
        return tuple(
            e
            for e in self.entries
            if isinstance(e, PracticeHypothesisEntry) and e.under_revision
        )

    def unresolved_group_names(self) -> tuple[MeshGroupNaming, ...]:
        return tuple(g for g in self.group_naming if g.status == "non_tranche")

    def generation_blockers(
        self, model_data: MissingValues | None = None
    ) -> tuple[str, ...]:
        """Human-readable reasons `is_ready_for_generation` is `False` (R3,
        lot 17).

        `model_data` (lot 25) is the structured data file of the model
        (`aster_expert.agent.model_data.ModelData`): each value it still marks
        « à fournir » is one more blocker. Without it, only the fiche is
        examined, as before.

        An empty `group_naming` is not the same state as a `group_naming`
        whose every entry is `tranche`: `unresolved_group_names()` lists
        `non_tranche` elements, and a tuple with zero elements has none to
        list by construction -- indistinguishable, on that check alone,
        from a naming section that was actually completed (lot 16, clôture,
        Q4's own "limite consignée"). `group_name` is the interface
        contract between the mesh and the generated `.comm` (M4): a fiche
        whose naming rubric was never even started cannot generate anything
        coherent, and this method says so explicitly rather than leaving
        `is_ready_for_generation` silently `True`-by-omission.
        """
        blockers: list[str] = []
        if not self.group_naming:
            blockers.append(
                "aucune convention de nommage de groupe (group_naming) n'a "
                "été rédigée pour cette fiche -- section vide, distincte "
                "d'une section entièrement tranchée (R3, lot 17)"
            )
        blockers.extend(
            f"entrée {e.nature} non tranchée (point {e.point_label or '?'}) : {e.topic}"
            for e in self.unresolved_entries()
        )
        blockers.extend(
            f"entrée pratique en révision (point {e.point_label or '?'}) : "
            f"{e.topic} -- motif : {e.revision_reason}"
            for e in self.entries_under_revision()
        )
        blockers.extend(
            f"nom de groupe non tranché : {g.group_name} ({g.kind})"
            for g in self.unresolved_group_names()
        )
        blockers.extend(
            f"constat référencé non résolu contre la base partagée : "
            f"{r.constat_id} (point {r.point_label or '?'})"
            for r in self.finding_references()
        )
        if model_data is not None:
            blockers.extend(model_data.missing_values())
        return tuple(blockers)

    def group_naming_gaps(
        self, catalogue_identifiers: Collection[str] = ()
    ) -> tuple[str, ...]:
        """Report mismatches between `group_naming` and the fiche's points.

        Reported, never corrected. Lot 20 replaced lot 19's "every group is
        cited by a decision" check, which produced false gaps because
        decisions are written in prose. Now: (1) every identifier written
        between backticks in a decided `pratique` entry's `option_retained`
        must be a `group_naming` name; (2) every group carries a
        `point_label`, that point exists among the `pratique` entries, and
        every `pratique` entry bearing it is `tranche`. Nothing is checked
        while `group_naming` is empty (R3 already reports that state).

        `catalogue_identifiers` (lot 25) is the vocabulary of the target
        version's catalogue (`aster_expert.catalogue.query.catalogue_vocabulary`:
        command names, keywords, allowed values such as field names). A
        backticked identifier that belongs to it is Code_Aster's, not a group
        (lot 24: `EPAIS`, `EFGE_NOEU`). This module does not import the
        catalogue: the caller supplies the vocabulary; without it, every
        backticked identifier is still read as a group.
        """
        if not self.group_naming:
            return ()
        names = {g.group_name for g in self.group_naming}
        known = frozenset(catalogue_identifiers)
        practice = tuple(
            e for e in self.entries if isinstance(e, PracticeHypothesisEntry)
        )
        gaps: list[str] = []
        for e in practice:
            if e.status != "tranche":
                continue
            cited = re.findall(r"`([A-Z][A-Z0-9_]*)`", e.option_retained or "")
            gaps.extend(
                f"groupe cité par la décision du point {e.point_label} "
                f"absent de la convention : {c}"
                for c in dict.fromkeys(cited)
                if c not in names and c not in known
            )
        for g in self.group_naming:
            if g.point_label is None:
                gaps.append(f"groupe sans point_label : {g.group_name}")
                continue
            at_point = [e for e in practice if e.point_label == g.point_label]
            if not at_point:
                gaps.append(
                    f"groupe {g.group_name} : le point {g.point_label} "
                    "n'existe pas parmi les entrées pratique"
                )
            elif any(e.status != "tranche" for e in at_point):
                gaps.append(
                    f"groupe {g.group_name} : le point {g.point_label} porte "
                    "une entrée pratique non tranchée"
                )
        return tuple(gaps)

    @property
    def is_ready_for_generation(self) -> bool:
        return not self.generation_blockers()


__all__: list[str] = [
    "CatalogueSource",
    "CodeAsterHypothesisEntry",
    "CodeAsterSource",
    "DiscardedVariant",
    "DocumentarySource",
    "ExecutionLevel",
    "FindingReference",
    "ExecutionSource",
    "HypothesesSheet",
    "HypothesisEntry",
    "MeshGroupNaming",
    "MissingValues",
    "PracticeHypothesisEntry",
    "PracticeOrigin",
    "PracticeSource",
    "PriorDecision",
    "RevisionEvent",
]
