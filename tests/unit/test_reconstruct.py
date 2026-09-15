"""Unit tests for the M2 argument reconstruction / eligibility gate (lot 10/10b)."""

from __future__ import annotations

from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.validation.reconstruct import plan_statements

# lot 9 only classifies a keyword value as a concept reference (as opposed to
# a dynamic, unresolved name) when the referenced name is itself assigned by
# some statement *within the same parsed source* -- so every scenario below
# that reads MAIL must also produce it.
READ_MAIL = 'MAIL = LIRE_MAILLAGE(FORMAT="MED")\n'


def test_fully_literal_statement_is_a_check_request() -> None:
    source = (
        READ_MAIL
        + 'MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", MODELISATION="3D"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, matched = plan_statements(analysis)

    assert excluded == []
    assert matched == set()
    request = next(r for r in requests if r.command == "AFFE_MODELE")
    assert request.assigned_concept == "MO"
    assert request.keywords == {
        "MAILLAGE": {"__concept_ref__": "MAIL"},
        "AFFE": {"TOUT": "OUI", "MODELISATION": "3D"},
    }


def test_multiple_factor_occurrences_become_a_list() -> None:
    source = READ_MAIL + (
        "MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=("
        '_F(GROUP_MA="A", MODELISATION="3D"), '
        '_F(GROUP_MA="B", MODELISATION="3D")))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis)

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

    requests, excluded, _ = plan_statements(analysis)

    affe_modele = next(e for e in excluded if e.command == "AFFE_MODELE")
    assert not any(r.command == "AFFE_MODELE" for r in requests)
    assert "control flow" in affe_modele.reasons[0]


def test_unresolved_keyword_excludes() -> None:
    source = READ_MAIL + "MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=une_variable)\n"
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis)

    affe_modele = next(e for e in excluded if e.command == "AFFE_MODELE")
    assert not any(r.command == "AFFE_MODELE" for r in requests)
    assert any("unresolved keyword: AFFE" in r for r in affe_modele.reasons)


def test_concept_reference_becomes_a_concept_ref_marker_even_if_never_resolvable() -> (
    None
):
    # Unlike lot 10, M2 no longer decides whether a referenced concept's type
    # is knowable -- it always emits the marker and lets
    # scripts/check_command_syntax.py resolve it live, in order, against the
    # concepts it has actually managed to type so far (lot 10b, point A).
    source = (
        'UNKNOWN_CONCEPT = LIRE_MAILLAGE(FORMAT="MED")\n'
        'MO = AFFE_MODELE(MAILLAGE=UNKNOWN_CONCEPT, AFFE=_F(TOUT="OUI"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis)

    assert excluded == []
    affe_modele = next(r for r in requests if r.command == "AFFE_MODELE")
    assert affe_modele.keywords["MAILLAGE"] == {"__concept_ref__": "UNKNOWN_CONCEPT"}


def test_reuse_becomes_a_concept_ref_marker() -> None:
    source = (
        "MAIL = MODI_MAILLAGE(reuse=MAIL, MAILLAGE=MAIL, "
        'ORIE_PEAU=_F(GROUP_MA_PEAU="h"))\n'
    )
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis)

    assert excluded == []
    assert requests[0].keywords["reuse"] == {"__concept_ref__": "MAIL"}
    assert requests[0].assigned_concept == "MAIL"


def test_formule_keeps_only_catalogue_keywords() -> None:
    # FORMULE accepts free keywords (named constants used by the expression)
    # that are not part of its catalog schema (lot 10b, point E) -- these
    # must never reach checkCommandSyntax.
    source = 'F = FORMULE(NOM_PARA="X", VALE="A*X+B", A=2.0, B=1.0)\n'
    analysis = parse_comm_source(source, file_path="t.comm")

    requests, excluded, _ = plan_statements(analysis)

    assert excluded == []
    assert requests[0].keywords == {"NOM_PARA": "X", "VALE": "A*X+B"}


def test_overlapping_parse_warning_excludes_and_is_reported_as_matched() -> None:
    # A statement whose "reuse=" value is not a plain name produces a lot 9
    # parse_warning but leaves `dynamic=False` and `reuse=None` (lot 9 does
    # not track this specific gap on the statement itself) -- this is
    # exactly the case the ABSOLUTE RULE's parse_warning bullet exists for.
    source = "MAIL = DEFI_GROUP(reuse=some_call(), MAILLAGE=MAIL)\n"
    analysis = parse_comm_source(source, file_path="t.comm")
    assert analysis.parse_warnings, "expected lot 9 to warn about reuse=some_call()"

    requests, excluded, matched = plan_statements(analysis)

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

    requests, excluded, matched = plan_statements(analysis)

    assert any(r.command == "AFFE_MODELE" for r in requests)
    assert excluded == []
    assert matched == set()
