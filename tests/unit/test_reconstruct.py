"""Unit tests for the M2 argument reconstruction / eligibility gate (lot 10)."""

from __future__ import annotations

from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.validation.concept_types import ConceptType
from aster_expert.validation.reconstruct import plan_statements

KNOWN = {
    "MAIL": ConceptType(aster_type="maillage_sdaster", reason=""),
    "MO": ConceptType(aster_type="modele_sdaster", reason=""),
}

# lot 9 only classifies a keyword value as a concept reference (as opposed to
# a dynamic, unresolved name) when the referenced name is itself assigned by
# some statement *within the same parsed source* -- so every scenario below
# that reads MAIL must also produce it, regardless of what the hand-rolled
# `KNOWN` table above says its type is.
READ_MAIL = 'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'


def test_fully_literal_statement_is_a_check_request() -> None:
    source = (
        READ_MAIL
        + 'MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", MODELISATION="3D"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, matched = plan_statements(analysis, KNOWN)

    assert excluded == []
    assert matched == set()
    request = next(r for r in requests if r.command == "AFFE_MODELE")
    assert request.keywords == {
        "MAILLAGE": {"__concept_type__": "maillage_sdaster"},
        "AFFE": {"TOUT": "OUI", "MODELISATION": "3D"},
    }


def test_multiple_factor_occurrences_become_a_list() -> None:
    source = READ_MAIL + (
        "MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=("
        '_F(GROUP_MA="A", MODELISATION="3D"), '
        '_F(GROUP_MA="B", MODELISATION="3D")))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    assert excluded == []
    request = next(r for r in requests if r.command == "AFFE_MODELE")
    assert request.keywords["AFFE"] == [
        {"GROUP_MA": "A", "MODELISATION": "3D"},
        {"GROUP_MA": "B", "MODELISATION": "3D"},
    ]


def test_control_flow_excludes_without_reconstruction() -> None:
    source = (
        READ_MAIL + 'if 1:\n    MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    affe_modele = next(e for e in excluded if e.command == "AFFE_MODELE")
    assert not any(r.command == "AFFE_MODELE" for r in requests)
    assert "control flow" in affe_modele.reasons[0]


def test_unresolved_keyword_excludes() -> None:
    source = READ_MAIL + "MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=une_variable)\n"
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    affe_modele = next(e for e in excluded if e.command == "AFFE_MODELE")
    assert not any(r.command == "AFFE_MODELE" for r in requests)
    assert any("unresolved keyword: AFFE" in r for r in affe_modele.reasons)


def test_concept_of_unknown_type_excludes() -> None:
    # UNKNOWN_CONCEPT is a real concept for lot 9 (produced by LIRE_MAILLAGE
    # right here) but absent from the hand-rolled `KNOWN` table passed to
    # plan_statements, i.e. of unknown type for M2's purposes.
    source = (
        'UNKNOWN_CONCEPT = LIRE_MAILLAGE(FORMAT="MED")\n'
        'MO = AFFE_MODELE(MAILLAGE=UNKNOWN_CONCEPT, AFFE=_F(TOUT="OUI"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    affe_modele = next(e for e in excluded if e.command == "AFFE_MODELE")
    assert not any(r.command == "AFFE_MODELE" for r in requests)
    assert any(
        "UNKNOWN_CONCEPT" in r and "unknown type" in r for r in affe_modele.reasons
    )


def test_reuse_of_unknown_type_excludes() -> None:
    source = (
        "MAIL = MODI_MAILLAGE(reuse=UNKNOWN_CONCEPT, MAILLAGE=MAIL, "
        'ORIE_PEAU=_F(GROUP_MA_PEAU="h"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    assert requests == []
    assert any("reuse=" in r and "UNKNOWN_CONCEPT" in r for r in excluded[0].reasons)


def test_reuse_of_known_type_is_included_in_keywords() -> None:
    source = (
        "MAIL = MODI_MAILLAGE(reuse=MAIL, MAILLAGE=MAIL, "
        'ORIE_PEAU=_F(GROUP_MA_PEAU="h"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis, KNOWN)

    assert excluded == []
    assert requests[0].keywords["reuse"] == {"__concept_type__": "maillage_sdaster"}


def test_overlapping_parse_warning_excludes_and_is_reported_as_matched() -> None:
    # A statement whose "reuse=" value is not a plain name produces a lot 9
    # parse_warning but leaves `dynamic=False` and `reuse=None` (lot 9 does
    # not track this specific gap on the statement itself) -- this is
    # exactly the case the ABSOLUTE RULE's parse_warning bullet exists for.
    source = "MAIL = DEFI_GROUP(reuse=some_call(), MAILLAGE=MAIL)\n"
    analysis = parse_comm_source(source, file_path="t.comm")
    assert analysis.parse_warnings, "expected lot 9 to warn about reuse=some_call()"

    requests, excluded, matched = plan_statements(analysis, KNOWN)

    assert requests == []
    assert len(excluded) == 1
    assert matched == {0}
    assert any("parse_warning" in r for r in excluded[0].reasons)


def test_parse_warning_outside_any_statement_is_not_matched() -> None:
    source = (
        "def helper():\n    pass\n\n"
        + READ_MAIL
        + ('MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI"))\n')
    )
    analysis = parse_comm_source(source, file_path="t.comm")
    assert any(w.node_type == "FunctionDef" for w in analysis.parse_warnings)

    requests, excluded, matched = plan_statements(analysis, KNOWN)

    assert any(r.command == "AFFE_MODELE" for r in requests)
    assert excluded == []
    assert matched == set()
