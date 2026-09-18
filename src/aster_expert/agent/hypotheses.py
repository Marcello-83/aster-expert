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
entry. Transcribing the real combi-wall fiche (lot 14, M5) broke that draft
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
by id/section alone, never actually read -- exactly what the combi-wall
specimen itself did for R7.01.25 (cited for "documente les éléments de
joint", excerpt never captured). `_require_a_verbatim_excerpt_when_documentary`
makes that structural rather than a matter of skill discipline: a `tranche`
entry that cites any `DocumentarySource` must have a real, non-empty
`excerpt` on at least one of them. The combi-wall specimen's R7.01.25
citation was itself corrected against this rule -- by reading the document
for real (`get_document_section`), not by inventing a passage to satisfy
the validator.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PracticeOrigin = Literal["norme", "precedent_projet", "decision_ingenieur"]


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
    the lot 8c/K1 problem this project already fixed), and the combi-wall
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


CodeAsterSource = DocumentarySource | CatalogueSource
"""No discriminator field: the two variants share no common literal tag and
are told apart by their own distinct, non-overlapping required fields
instead (`document_id` vs `command`) -- pydantic's default "smart" union
mode resolves this without one, and adding a synthetic tag neither
citation.md nor any tool output actually carries would be inventing a field
this schema does not need (M5 discipline: no field beyond what the real
citations require)."""


class PracticeSource(BaseModel):
    """A citation grounded in engineering practice, never in the corpus (M1).

    `origin` distinguishes the three kinds M1 names: `norme` (a normative
    reference -- a standard, a code of practice), `precedent_projet` (a
    prior project's own decision, reused), `decision_ingenieur` (an
    explicit, dated decision by the engineer working this fiche). `date` is
    required exactly for `decision_ingenieur` ("avec sa date" in M1 reads
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
        if self.origin == "decision_ingenieur" and self.date is None:
            message = "une décision explicite de l'ingénieur exige une date"
            raise ValueError(message)
        return self


class DiscardedVariant(BaseModel):
    """One option considered and set aside, with the reason (M3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str
    reason: str


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
    combi-wall specimen alongside this validator, not by inventing a passage
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
    """

    nature: Literal["pratique"] = "pratique"
    sources: tuple[PracticeSource, ...] = ()
    status: Literal["tranche", "non_tranche", "herite"]

    @model_validator(mode="after")
    def _status_matches_content(self) -> PracticeHypothesisEntry:
        if self.status == "non_tranche":
            if self.sources:
                message = "une entrée pratique non tranchée ne porte aucune source"
                raise ValueError(message)
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
            if self.status == "herite" and not any(
                s.origin == "precedent_projet" for s in self.sources
            ):
                message = (
                    "une entrée 'hérité d'un ouvrage antérieur' exige au moins une "
                    "source 'precedent_projet' -- jamais une norme seule ni une "
                    "décision prise ici"
                )
                raise ValueError(message)
        return self


HypothesisEntry = Annotated[
    CodeAsterHypothesisEntry | PracticeHypothesisEntry, Field(discriminator="nature")
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
    real-case confrontation: the combi-wall specimen predates this section
    and never discusses mesh group names -- validated by unit test only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_name: str
    kind: Literal["maille", "noeud"]
    description: str
    status: Literal["tranche", "non_tranche"] = "non_tranche"


class HypothesesSheet(BaseModel):
    """One structure's fiche d'hypothèses (lot 14).

    `unresolved_entries`/`unresolved_group_names`/`is_ready_for_generation`
    make M2's "bloquera la génération en aval" a property this sheet can
    actually be asked about, not only a sentence in this docstring -- no
    generator is built in this lot (explicitly out of scope), but whatever
    lot builds one has, from day one, a single authoritative check to call
    rather than reinventing its own notion of "ready".
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

    def unresolved_entries(self) -> tuple[HypothesisEntry, ...]:
        return tuple(e for e in self.entries if e.status == "non_tranche")

    def unresolved_group_names(self) -> tuple[MeshGroupNaming, ...]:
        return tuple(g for g in self.group_naming if g.status == "non_tranche")

    @property
    def is_ready_for_generation(self) -> bool:
        return not self.unresolved_entries() and not self.unresolved_group_names()


__all__: list[str] = [
    "CatalogueSource",
    "CodeAsterHypothesisEntry",
    "CodeAsterSource",
    "DiscardedVariant",
    "DocumentarySource",
    "HypothesesSheet",
    "HypothesisEntry",
    "MeshGroupNaming",
    "PracticeHypothesisEntry",
    "PracticeOrigin",
    "PracticeSource",
]
