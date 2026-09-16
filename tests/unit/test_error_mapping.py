"""Unit tests for M4 (lot 10): translate a checkCommandSyntax message.

Every message string below was observed verbatim against the real checker
inside the Aster container (image digest
sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5,
17.4.0) during the lot 10 batch experiment — see the lot 10 batch report for
the exact `checkCommandSyntax` calls that produced each one.
"""

from __future__ import annotations

from aster_expert.validation.error_mapping import (
    classify,
    extract_keyword,
    strip_stack_prefix,
)


def test_strip_stack_prefix_removes_for_keyword_prefix() -> None:
    raw = (
        "For keyword AFFE/PHENOMENE: Unexpected value: 'MECHANIQUEBAD', "
        "must be in ('MECANIQUE', 'THERMIQUE', 'ACOUSTIQUE')"
    )
    assert strip_stack_prefix(raw) == (
        "Unexpected value: 'MECHANIQUEBAD', "
        "must be in ('MECANIQUE', 'THERMIQUE', 'ACOUSTIQUE')"
    )


def test_strip_stack_prefix_is_noop_without_prefix() -> None:
    raw = "At least one argument of ('CREA_GROUP_MA', 'CREA_GROUP_NO') must be defined"
    assert strip_stack_prefix(raw) == raw


def test_unauthorized_keyword() -> None:
    message = strip_stack_prefix(
        "For keyword VERI_JACOBIENXX: Unauthorized keyword: 'VERI_JACOBIENXX'"
    )
    assert classify(message) == "UNKNOWN_KEYWORD"
    assert extract_keyword(message) == "VERI_JACOBIENXX"


def test_mandatory_keyword() -> None:
    # docs/development-plan.md, lot 10c, point R2: `Composite.checkMandatory`
    # (`Cata/Language/SyntaxObjects.py`) raises a bare `KeyError("Keyword {0}
    # is mandatory")`, never a CheckerError -- `str(KeyError(...))` wraps the
    # message in one extra pair of quotes (`KeyError.__str__` is `repr()` of
    # its single argument). This is the real, verbatim shape
    # scripts/check_command_syntax.py reports; the unquoted form below is
    # kept only as defensive coverage, never observed in practice.
    message = "'Keyword CHAM_MATER is mandatory'"
    assert classify(message) == "MISSING_MANDATORY_KEYWORD"
    assert extract_keyword(message) == "CHAM_MATER"


def test_mandatory_keyword_unquoted_form_still_matches() -> None:
    # Defensive coverage only (see test_mandatory_keyword above): no call
    # site in the 17.4.0 source produces this unquoted shape, but the
    # pattern must not regress it either.
    message = "Keyword CHAM_MATER is mandatory"
    assert classify(message) == "MISSING_MANDATORY_KEYWORD"
    assert extract_keyword(message) == "CHAM_MATER"


def test_invalid_type() -> None:
    message = (
        "Unexpected type: "
        "<class 'code_aster.Cata.Language.DataStructure.cham_no_sdaster'>, "
        "expecting: "
        "[<class 'code_aster.Cata.Language.DataStructure.maillage_sdaster'>]"
    )
    assert classify(message) == "INVALID_TYPE"


def test_invalid_value() -> None:
    message = strip_stack_prefix(
        "For keyword AFFE/PHENOMENE: Unexpected value: 'MECHANIQUEBAD', "
        "must be in ('MECANIQUE', 'THERMIQUE', 'ACOUSTIQUE')"
    )
    assert classify(message) == "INVALID_VALUE"


def test_too_many_values() -> None:
    message = strip_stack_prefix(
        "For keyword ORIE_NORM_COQUE/VECT_NORM: At most 3 values are expected"
    )
    assert classify(message) == "INVALID_VALUE_CARDINALITY"


def test_too_many_occurrences() -> None:
    message = strip_stack_prefix(
        "For keyword INCREMENT: Too much factor keyword, "
        "at most 1 occurrence(s) expected"
    )
    assert classify(message) == "INVALID_OCCURRENCE_CARDINALITY"


def test_reuse_not_allowed() -> None:
    message = strip_stack_prefix("For keyword reuse: reuse is not allowed!")
    assert classify(message) == "REUSE_NOT_ALLOWED"


def test_rule_violation_at_least_one() -> None:
    message = (
        "At least one argument of "
        "('CREA_GROUP_MA', 'CREA_GROUP_NO', 'DETR_GROUP_NO', 'DETR_GROUP_MA') "
        "must be defined"
    )
    assert classify(message) == "RULE_VIOLATION"


def test_unrecognized_message_falls_back_to_checker_error() -> None:
    assert classify("some future message shape nobody has seen yet") == "CHECKER_ERROR"


def test_extract_keyword_returns_none_for_unrelated_message() -> None:
    assert extract_keyword("Unexpected type: foo, expecting: bar") is None
