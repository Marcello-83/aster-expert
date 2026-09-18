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
