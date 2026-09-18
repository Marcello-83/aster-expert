"""Tests for aster_expert.agent.hypotheses (lot 14, M1-M5).

No network, no corpus, no catalogue (CLAUDE.md, "aucun accès réseau dans les
tests unitaires"): every `DocumentarySource`/`CatalogueSource` here is
hand-built, exactly as a caller who already has a `SearchHit`/
`DocumentSection`/`CommandSchema` would build one.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DiscardedVariant,
    DocumentarySource,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
    PriorDecision,
)

_DOC_SOURCE = DocumentarySource(
    document_id="U2.02.01",
    section_path=("Conclusion_et_conseils_d_utilisation",),
    aster_version="17.4.0",
    source_path="source/manuals/man_u/u2/u2.02.01/Conclusion_et_conseils_d_utilisation.rst",
    source_commit="a" * 40,
    excerpt="On conseille d'utiliser pour ce type de structure des éléments DKT.",
)

_CATALOGUE_SOURCE = CatalogueSource(
    command="AFFE_MODELE",
    aster_version="17.4.0",
    keyword_path=("AFFE", "MODELISATION"),
)


def test_code_aster_entry_tranche_requires_a_source_and_justification() -> None:
    with pytest.raises(ValidationError, match="exige au moins une source"):
        CodeAsterHypothesisEntry(
            topic="Élément de coque retenu",
            option_retained="DKT",
            justification="structure mince, h/L < 1/20",
            status="tranche",
        )


def test_code_aster_entry_non_tranche_rejects_a_decision() -> None:
    with pytest.raises(ValidationError, match="ne porte ni option retenue"):
        CodeAsterHypothesisEntry(
            topic="Élément de coque retenu",
            sources=(_DOC_SOURCE,),
            option_retained="DKT",
            status="non_tranche",
        )


def test_code_aster_entry_non_tranche_may_carry_a_partial_source() -> None:
    """M5, correction 3: a section can be identified before its content is
    read (the real U2.02.01 comparison-table case) -- this must not be
    forced to drop the citation just because nothing is decided yet."""
    entry = CodeAsterHypothesisEntry(
        topic="Contenu détaillé du tableau comparatif DKT/DST/Q4G",
        sources=(DocumentarySource(**{**_DOC_SOURCE.model_dump(), "excerpt": None}),),
        notes="Section identifiée, contenu non extrait dans cette session.",
        status="non_tranche",
    )

    assert entry.sources[0].excerpt is None
    assert entry.status == "non_tranche"


def test_code_aster_entry_tranche_with_multiple_sources_is_valid() -> None:
    entry = CodeAsterHypothesisEntry(
        topic="Élément de coque retenu",
        options_considered=("DKT", "DST", "COQUE_3D"),
        option_retained="DKT",
        justification="structure mince, h/L < 1/20",
        sources=(_DOC_SOURCE, _CATALOGUE_SOURCE),
        discarded_variants=(
            DiscardedVariant(
                description="COQUE_3D", reason="coût de calcul injustifié"
            ),
        ),
        status="tranche",
    )

    assert entry.nature == "code_aster"
    assert len(entry.sources) == 2
    assert isinstance(entry.sources[0], DocumentarySource)
    assert isinstance(entry.sources[1], CatalogueSource)


def test_code_aster_entry_cannot_carry_a_practice_source() -> None:
    """M2: the field's type alone rules this out -- not a runtime guess."""
    with pytest.raises(ValidationError):
        CodeAsterHypothesisEntry(
            topic="x",
            option_retained="x",
            justification="x",
            sources=(PracticeSource(origin="norme", reference="Eurocode 7"),),  # type: ignore[arg-type]
            status="tranche",
        )


def test_code_aster_entry_herite_status_is_not_a_valid_literal() -> None:
    """M1: `herite` only makes sense for a practice fact (see module docstring)."""
    with pytest.raises(ValidationError):
        CodeAsterHypothesisEntry(
            topic="x",
            option_retained="x",
            justification="x",
            sources=(_DOC_SOURCE,),
            status="herite",  # type: ignore[arg-type]
        )


def test_practice_source_cannot_carry_a_document_id() -> None:
    """M2: extra="forbid" makes this a hard validation failure, not a silent drop."""
    with pytest.raises(ValidationError, match="extra"):
        PracticeSource.model_validate(
            {
                "origin": "norme",
                "reference": "Eurocode 7",
                "document_id": "U2.02.01",
            }
        )


def test_practice_source_decision_ingenieur_requires_a_date() -> None:
    with pytest.raises(ValidationError, match="exige une date"):
        PracticeSource(
            origin="decision_ingenieur", reference="Choix du bureau d'études"
        )


def test_practice_source_norme_does_not_require_a_date() -> None:
    source = PracticeSource(origin="norme", reference="NF EN 1997-1 (Eurocode 7)")

    assert source.date is None


def test_practice_entry_non_tranche_rejects_any_source() -> None:
    """Unlike a code_aster entry, a practice source only ever means "decided"."""
    with pytest.raises(ValidationError, match="ne porte aucune source"):
        PracticeHypothesisEntry(
            topic="Représentation du tirant d'ancrage",
            sources=(PracticeSource(origin="norme", reference="Eurocode 7"),),
            status="non_tranche",
        )


def test_practice_entry_herite_requires_a_precedent_projet_source() -> None:
    with pytest.raises(ValidationError, match="precedent_projet"):
        PracticeHypothesisEntry(
            topic="Poussée des terres au repos",
            option_retained="K0 = 0.5",
            justification="valeur reprise du projet antérieur",
            sources=(PracticeSource(origin="norme", reference="Eurocode 7"),),
            status="herite",
        )


def test_practice_entry_herite_with_precedent_projet_is_valid() -> None:
    entry = PracticeHypothesisEntry(
        topic="Poussée des terres au repos",
        option_retained="K0 = 0.5",
        justification="valeur reprise du projet antérieur XYZ",
        sources=(
            PracticeSource(
                origin="precedent_projet", reference="Projet XYZ, note de calcul n°12"
            ),
        ),
        status="herite",
    )

    assert entry.nature == "pratique"
    assert entry.status == "herite"


def test_practice_entry_non_tranche_blocks_generation() -> None:
    sheet = HypothesesSheet(
        project_name="Paroi moulée -- essai",
        structure_description="Écran de soutènement ancré",
        created_at=datetime(2026, 9, 18),
        entries=(
            PracticeHypothesisEntry(
                topic="Représentation du tirant d'ancrage",
                status="non_tranche",
            ),
        ),
    )

    assert sheet.is_ready_for_generation is False
    assert len(sheet.unresolved_entries()) == 1
    assert sheet.unresolved_entries()[0].topic == "Représentation du tirant d'ancrage"


def test_sheet_with_all_entries_resolved_is_ready_for_generation() -> None:
    sheet = HypothesesSheet(
        project_name="Paroi moulée -- essai",
        structure_description="Écran de soutènement ancré",
        created_at=datetime(2026, 9, 18),
        entries=(
            CodeAsterHypothesisEntry(
                topic="Élément de coque retenu",
                option_retained="DKT",
                justification="structure mince",
                sources=(_DOC_SOURCE,),
                status="tranche",
            ),
        ),
        group_naming=(
            MeshGroupNaming(
                group_name="PAROI_AV",
                kind="maille",
                description="Paroi moulée, face amont",
                status="tranche",
            ),
        ),
    )

    assert sheet.is_ready_for_generation is True


def test_sheet_rejects_duplicate_group_names() -> None:
    with pytest.raises(ValidationError, match="en double"):
        HypothesesSheet(
            project_name="Paroi moulée -- essai",
            structure_description="Écran de soutènement ancré",
            created_at=datetime(2026, 9, 18),
            group_naming=(
                MeshGroupNaming(
                    group_name="PAROI_AV",
                    kind="maille",
                    description="Paroi moulée, face amont",
                ),
                MeshGroupNaming(
                    group_name="PAROI_AV",
                    kind="noeud",
                    description="Nœuds de la paroi amont",
                ),
            ),
        )


def test_sheet_blocks_on_unresolved_group_naming_even_with_all_entries_resolved() -> (
    None
):
    sheet = HypothesesSheet(
        project_name="Paroi moulée -- essai",
        structure_description="Écran de soutènement ancré",
        created_at=datetime(2026, 9, 18),
        group_naming=(
            MeshGroupNaming(
                group_name="PAROI_AV",
                kind="maille",
                description="Paroi moulée, face amont",
                status="non_tranche",
            ),
        ),
    )

    assert sheet.is_ready_for_generation is False
    assert len(sheet.unresolved_group_names()) == 1


def test_sheet_blocks_on_empty_group_naming_even_with_all_entries_resolved() -> None:
    """R3 (lot 17): a `group_naming` section never even started is not the
    same state as one whose every entry is `tranche` -- `unresolved_group_
    names()` cannot see the difference (a tuple with zero elements has none
    to list either way), so `generation_blockers` must name it explicitly."""
    sheet = HypothesesSheet(
        project_name="Paroi moulée -- essai",
        structure_description="Écran de soutènement ancré",
        created_at=datetime(2026, 9, 18),
        entries=(
            CodeAsterHypothesisEntry(
                topic="Élément de coque retenu",
                option_retained="DKT",
                justification="structure mince",
                sources=(_DOC_SOURCE,),
                status="tranche",
            ),
        ),
        group_naming=(),
    )

    assert sheet.unresolved_group_names() == ()
    assert sheet.is_ready_for_generation is False
    blockers = sheet.generation_blockers()
    assert len(blockers) == 1
    assert "aucune convention de nommage de groupe" in blockers[0]


def test_generation_blockers_is_empty_when_the_sheet_is_ready() -> None:
    sheet = HypothesesSheet(
        project_name="Paroi moulée -- essai",
        structure_description="Écran de soutènement ancré",
        created_at=datetime(2026, 9, 18),
        entries=(
            CodeAsterHypothesisEntry(
                topic="Élément de coque retenu",
                option_retained="DKT",
                justification="structure mince",
                sources=(_DOC_SOURCE,),
                status="tranche",
            ),
        ),
        group_naming=(
            MeshGroupNaming(
                group_name="PAROI_AV",
                kind="maille",
                description="Paroi moulée, face amont",
                status="tranche",
            ),
        ),
    )

    assert sheet.generation_blockers() == ()
    assert sheet.is_ready_for_generation is True


def test_practice_source_date_is_a_real_date_type() -> None:
    source = PracticeSource(
        origin="decision_ingenieur",
        reference="Choix du bureau d'études : contact frottant",
        date=date(2026, 9, 18),
    )

    assert source.date == date(2026, 9, 18)


def test_notes_field_is_allowed_regardless_of_status() -> None:
    """M5, correction 4: search-evidence/deduction text is not a decision
    record and must never be blocked by the non_tranche guard."""
    entry = PracticeHypothesisEntry(
        topic="Représentation du tirant d'ancrage",
        notes=(
            "Aucun document méthodologique dédié trouvé. Cherché sous "
            "methode puis syntaxe (\"tirant d'ancrage géotechnique "
            'scellement bulbe").'
        ),
        status="non_tranche",
    )

    assert entry.notes is not None


def test_code_aster_entry_tranche_rejects_a_documentary_source_without_excerpt() -> (
    None
):
    """N1 (lot 14b): a document cited by id/section alone, never read, does
    not found a 'tranche' entry -- the R7.01.25 gap M5 left open."""
    with pytest.raises(ValidationError, match="extrait verbatim"):
        CodeAsterHypothesisEntry(
            topic="Éléments de joint pour une interface sol-écran",
            option_retained="JOINT_MECA_FROT",
            justification="R7.01.25 documenterait les éléments de joint",
            sources=(
                DocumentarySource(**{**_DOC_SOURCE.model_dump(), "excerpt": None}),
            ),
            status="tranche",
        )


def test_code_aster_entry_tranche_accepts_a_pure_catalogue_source() -> None:
    """N1: a CatalogueSource has no excerpt field at all -- the catalogue
    node get_command_schema returns is already the verbatim fact, nothing
    to quote a second time, so a purely-catalogue entry is exempt."""
    entry = CodeAsterHypothesisEntry(
        topic="Familles d'éléments 1D disponibles pour un tirant",
        option_retained="BARRE, CABLE, DIS_T, DIS_TR",
        justification="Catalogue introspecté, AFFE_MODELE/AFFE/MODELISATION.",
        sources=(_CATALOGUE_SOURCE,),
        status="tranche",
    )

    assert entry.status == "tranche"


def test_code_aster_entry_tranche_accepts_one_excerpt_among_several_sources() -> None:
    """N1: the rule is per-entry (at least one real excerpt), not per
    citation -- a second, unread documentary source stays representable
    alongside a confirmed one (the real specimen mixes both)."""
    unread = DocumentarySource(**{**_DOC_SOURCE.model_dump(), "excerpt": None})
    entry = CodeAsterHypothesisEntry(
        topic="Lois de comportement de sol disponibles",
        option_retained="MOHR_COULOMB, HUJEUX",
        justification=(
            "get_command_schema liste ces lois ; R7.01.28 confirme MOHR_COULOMB."
        ),
        sources=(_DOC_SOURCE, unread),
        status="tranche",
    )

    assert entry.status == "tranche"


_PRACTICE_SOURCE = PracticeSource(
    origin="decision_ingenieur",
    reference="Choix du bureau d'études : contact frottant",
    date=date(2026, 9, 18),
)

_PRACTICE_DISCARDED = (
    DiscardedVariant(
        description="Éléments de joint", reason="non documenté pour ce cas"
    ),
)


_VALIDITY_DOMAIN = (
    "Valable pour un contact permanent, non cyclique -- non validé pour un "
    "chargement sismique."
)


def test_practice_entry_tranche_requires_decided_by_and_decided_at() -> None:
    """P1/P2 (lot 15): a human arbitration is not represented without
    knowing who decided and when -- the model rejects it regardless of
    which function tried to build it."""
    with pytest.raises(ValidationError, match="qui a tranché"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            validity_domain=_VALIDITY_DOMAIN,
            sources=(_PRACTICE_SOURCE,),
            discarded_variants=_PRACTICE_DISCARDED,
            status="tranche",
        )


def test_practice_entry_tranche_requires_discarded_variants() -> None:
    """P1: an arbitration without at least one alternative actually
    weighed is refused, not merely encouraged."""
    with pytest.raises(ValidationError, match="variantes écartées"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            validity_domain=_VALIDITY_DOMAIN,
            sources=(_PRACTICE_SOURCE,),
            status="tranche",
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_practice_entry_tranche_requires_a_validity_domain() -> None:
    """R1 (lot 17): a decision without its known limits stated is refused,
    exactly like one missing a justification -- the gap lot 16 hit trying
    to record a real arbitration."""
    with pytest.raises(ValidationError, match="domaine de validité"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            sources=(_PRACTICE_SOURCE,),
            discarded_variants=_PRACTICE_DISCARDED,
            status="tranche",
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_practice_entry_tranche_rejects_a_blank_validity_domain() -> None:
    """R1: whitespace-only does not count as stated, same discipline as
    `option_retained`/`justification`."""
    with pytest.raises(ValidationError, match="domaine de validité"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            validity_domain="   ",
            sources=(_PRACTICE_SOURCE,),
            discarded_variants=_PRACTICE_DISCARDED,
            status="tranche",
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_practice_entry_non_tranche_rejects_a_validity_domain() -> None:
    """R1: symmetric with `sources`/`option_retained` -- nothing has been
    decided, so there is no domain to bound yet."""
    with pytest.raises(ValidationError, match="ne porte aucun domaine de validité"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            validity_domain=_VALIDITY_DOMAIN,
            status="non_tranche",
        )


def test_practice_entry_tranche_rejects_no_source() -> None:
    """P1: 'une décision sans source est refusée', unchanged from M3/M5's
    shared decision-fields check -- exercised here on the arbitrated path."""
    with pytest.raises(ValidationError, match="exige au moins une source"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            discarded_variants=_PRACTICE_DISCARDED,
            status="tranche",
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_practice_entry_cannot_carry_a_documentary_source() -> None:
    """P1: 'une source de nature documentaire Code_Aster reste
    structurellement impossible, comme au lot 14' -- the field's type
    alone rules this out, exactly as for CodeAsterHypothesisEntry (M2)."""
    with pytest.raises(ValidationError):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            sources=(_DOC_SOURCE,),  # type: ignore[arg-type]
            discarded_variants=_PRACTICE_DISCARDED,
            status="tranche",
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )


def test_practice_entry_tranche_with_full_arbitration_is_valid() -> None:
    entry = PracticeHypothesisEntry(
        topic="Interface sol-écran",
        option_retained="Contact frottant",
        justification="Décision du bureau d'études, cohérente avec les précédents",
        validity_domain=_VALIDITY_DOMAIN,
        sources=(_PRACTICE_SOURCE,),
        discarded_variants=_PRACTICE_DISCARDED,
        status="tranche",
        decided_by="J. Dupont",
        decided_at=datetime(2026, 9, 18, 10, 0),
    )

    assert entry.status == "tranche"
    assert entry.decided_by == "J. Dupont"
    assert entry.validity_domain == _VALIDITY_DOMAIN
    assert entry.decision_history == ()


def test_code_aster_entry_validity_domain_is_optional_regardless_of_status() -> None:
    """R1: unlike a practice entry, a code_aster entry's validity_domain is
    never required, whatever `status` is -- the corpus states one for some
    facts and not for others, and that must stay representable."""
    non_tranche = CodeAsterHypothesisEntry(
        topic="x",
        sources=(DocumentarySource(**{**_DOC_SOURCE.model_dump(), "excerpt": None}),),
        status="non_tranche",
    )
    tranche = CodeAsterHypothesisEntry(
        topic="Critère d'élancement",
        option_retained="DKT",
        justification="structure mince, h/L < 1/10",
        validity_domain="Valable pour h/L < 1/10 (coques minces) -- U2.02.01.",
        sources=(_DOC_SOURCE,),
        status="tranche",
    )

    assert non_tranche.validity_domain is None
    assert (
        tranche.validity_domain
        == "Valable pour h/L < 1/10 (coques minces) -- U2.02.01."
    )


def test_practice_entry_non_tranche_rejects_decided_by() -> None:
    """Symmetric with the `sources` guard: an unresolved point has no
    arbitration to record yet."""
    with pytest.raises(ValidationError, match="ni arbitre ni date"):
        PracticeHypothesisEntry(
            topic="Interface sol-écran",
            status="non_tranche",
            decided_by="J. Dupont",
        )


def test_practice_entry_can_carry_a_decision_history() -> None:
    """P2: a re-arbitrated entry keeps its previous decision rather than
    discarding it."""
    entry = PracticeHypothesisEntry(
        topic="Interface sol-écran",
        option_retained="Ressorts discrets",
        justification="Nouvelle décision après revue",
        validity_domain=_VALIDITY_DOMAIN,
        sources=(_PRACTICE_SOURCE,),
        discarded_variants=_PRACTICE_DISCARDED,
        status="tranche",
        decided_by="M. Martin",
        decided_at=datetime(2026, 10, 1, 9, 0),
        decision_history=(
            PriorDecision(
                option_retained="Contact frottant",
                justification="Décision du bureau d'études",
                validity_domain=_VALIDITY_DOMAIN,
                sources=(_PRACTICE_SOURCE,),
                discarded_variants=_PRACTICE_DISCARDED,
                decided_by="J. Dupont",
                decided_at=datetime(2026, 9, 18, 10, 0),
            ),
        ),
    )

    assert len(entry.decision_history) == 1
    assert entry.decision_history[0].option_retained == "Contact frottant"
    assert entry.option_retained == "Ressorts discrets"


def test_prior_decision_requires_decided_by_and_decided_at() -> None:
    with pytest.raises(ValidationError):
        PriorDecision(
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            validity_domain=_VALIDITY_DOMAIN,
            sources=(_PRACTICE_SOURCE,),
            decided_by="J. Dupont",
        )  # type: ignore[call-arg]


def test_prior_decision_requires_a_validity_domain() -> None:
    """R1 (lot 17): a superseded decision's own limits are as much part of
    the historical record as the option it retained."""
    with pytest.raises(ValidationError):
        PriorDecision(
            option_retained="Contact frottant",
            justification="Décision du bureau d'études",
            sources=(_PRACTICE_SOURCE,),
            decided_by="J. Dupont",
            decided_at=datetime(2026, 9, 18, 10, 0),
        )  # type: ignore[call-arg]


def test_catalogue_source_and_documentary_source_are_told_apart_in_a_tuple() -> None:
    """M5, correction 2: a plain union, no synthetic discriminator, still
    resolves each member to the right concrete class."""
    entry = CodeAsterHypothesisEntry(
        topic="Raccord coque-poutre",
        option_retained="LIAISON_ELEM(OPTION='COQ_POU')",
        justification="R3.03.03 nomme explicitement cette commande pour ce raccord",
        sources=(_CATALOGUE_SOURCE, _DOC_SOURCE),
        status="tranche",
    )

    assert isinstance(entry.sources[0], CatalogueSource)
    assert isinstance(entry.sources[1], DocumentarySource)
