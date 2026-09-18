"""Tests for aster_expert.agent.drafting (lot 14b, N2-N4).

N3 is the central deliverable of this lot: these tests must fail if the
drafting write path can ever produce a `pratique` entry at `status=
"tranche"`, a `code_aster` entry at `status="tranche"` without a real
excerpt, or a decision (`option_retained`/`justification`) without a
source. No network, no corpus, no catalogue (CLAUDE.md): every source here
is hand-built.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from aster_expert.agent.drafting import (
    SearchAttempt,
    Trame,
    default_trame_path,
    load_trame,
    record_code_aster_finding,
    record_unfounded_point,
)
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
    PracticeHypothesisEntry,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_READ_SOURCE = DocumentarySource(
    document_id="R7.01.25",
    aster_version="17.4.0",
    section_path=("index",),
    source_path="source/manuals/man_r/r7/r7.01.25/index.rst",
    profile="methode",
    excerpt=(
        "Ce document décrit des lois surfaciques permettant de modéliser "
        "la rupture et le frottement."
    ),
)

_UNREAD_SOURCE = DocumentarySource(
    document_id="R7.01.18",
    aster_version="17.4.0",
    section_path=("Introduction",),
    profile="theorie",
    excerpt=None,
)

_CATALOGUE_SOURCE = CatalogueSource(
    command="STAT_NON_LINE",
    aster_version="17.4.0",
    keyword_path=("COMPORTEMENT", "RELATION"),
)


def test_default_trame_loads_seven_ordered_rubrics() -> None:
    trame = load_trame(default_trame_path(_PROJECT_ROOT))

    assert isinstance(trame, Trame)
    assert [t.label for t in trame.topics] == ["1", "2", "3", "4", "5", "6", "7"]
    assert all(t.heading and t.prompt for t in trame.topics)


def test_record_code_aster_finding_builds_a_tranche_entry() -> None:
    entry = record_code_aster_finding(
        point_label="3",
        topic="Éléments de joint disponibles au catalogue",
        sources=(_CATALOGUE_SOURCE, _READ_SOURCE),
        option_retained="JOINT_MECA_FROT/RUPT/ENDO sur modélisations XXX_JOINT",
        justification=(
            "get_command_schema liste ces lois ; R7.01.25 confirme leur objet."
        ),
    )

    assert isinstance(entry, CodeAsterHypothesisEntry)
    assert entry.nature == "code_aster"
    assert entry.status == "tranche"


def test_record_code_aster_finding_rejects_a_source_never_read() -> None:
    """N1/N3: the write path delegates the excerpt discipline to the
    schema -- it does not reimplement it, and does not weaken it."""
    with pytest.raises(ValidationError, match="extrait verbatim"):
        record_code_aster_finding(
            topic="Loi de Hoek-Brown pour les roches",
            sources=(_UNREAD_SOURCE,),
            option_retained="HOEK_BROWN",
            justification="R7.01.18 documenterait cette loi",
        )


def test_record_code_aster_finding_rejects_no_source() -> None:
    with pytest.raises(ValidationError, match="exige au moins une source"):
        record_code_aster_finding(
            topic="x",
            sources=(),
            option_retained="x",
            justification="x",
        )


def test_record_code_aster_finding_has_no_status_parameter() -> None:
    """N3: nothing a caller passes can make this build a non_tranche entry
    -- the parameter to do so does not exist on this function at all."""
    assert "status" not in inspect.signature(record_code_aster_finding).parameters


def test_record_unfounded_point_builds_a_non_tranche_practice_entry() -> None:
    entry = record_unfounded_point(
        point_label="3",
        topic="Choix entre contact, ressorts et joint pour une interface sol-radier",
        searches=(
            SearchAttempt(
                profile="methode",
                query="interface sol radier fondation superficielle",
                outcome="aucun résultat comparant les trois mécanismes pour ce cas",
            ),
        ),
    )

    assert isinstance(entry, PracticeHypothesisEntry)
    assert entry.nature == "pratique"
    assert entry.status == "non_tranche"
    assert entry.sources == ()
    assert "interface sol radier" in (entry.notes or "")


def test_record_unfounded_point_rejects_an_empty_trace() -> None:
    """N2: jamais une entrée vide sans explication."""
    with pytest.raises(ValueError, match="jamais une entrée vide"):
        record_unfounded_point(topic="x", searches=())


def test_record_unfounded_point_has_no_decision_parameters() -> None:
    """N3, the central structural guarantee: whatever a drafting session
    calls this with, it cannot come back as a decided entry -- because the
    parameters a decision needs are not part of this function's signature,
    not merely discouraged or defaulted away."""
    params = inspect.signature(record_unfounded_point).parameters

    assert "option_retained" not in params
    assert "justification" not in params
    assert "sources" not in params
    assert "status" not in params


def test_record_unfounded_point_can_carry_a_deduction_without_becoming_a_decision() -> (
    None
):
    entry = record_unfounded_point(
        topic="Phasage construction/excavation",
        searches=(
            SearchAttempt(
                profile="methode",
                query="phasage excavation radier",
                outcome="aucun document dédié à ce phasage",
            ),
        ),
        deduction=(
            "Le rattachement au découpage en pas de temps de STAT_NON_LINE "
            "est une déduction d'ingénierie, non une lecture documentaire "
            "directe."
        ),
    )

    assert entry.option_retained is None
    assert entry.justification is None
    assert "Déduction" in (entry.notes or "")
