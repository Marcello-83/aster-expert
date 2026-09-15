"""M4: translate a `checkCommandSyntax` exception into a report entry.

Purely a classification of a message `checkCommandSyntax` already decided to
raise (docs/development-plan.md, lot 10: "aucune règle de cardinalité
maison"). Every pattern below was verified empirically against the real
checker (see the lot 10 batch report for the exact commands and keywords
used); an unrecognized message shape is never dropped, only bucketed under
the generic `CHECKER_ERROR` code with the original text preserved verbatim.
"""

from __future__ import annotations

import re

_STACK_PREFIX = re.compile(r"^For keyword [^:]+: ")

_UNAUTHORIZED_KEYWORD = re.compile(r"^Unauthorized keyword: '(?P<kw>[^']*)'$")
_MANDATORY_KEYWORD = re.compile(r"^Keyword (?P<kw>\S+) is mandatory$")

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_UNAUTHORIZED_KEYWORD, "UNKNOWN_KEYWORD"),
    (_MANDATORY_KEYWORD, "MISSING_MANDATORY_KEYWORD"),
    (re.compile(r"^Unexpected type: .*$"), "INVALID_TYPE"),
    (re.compile(r"^Unexpected value: .*$"), "INVALID_VALUE"),
    (
        re.compile(r"^At (most|least) \d+ values? (is|are) expected$"),
        "INVALID_VALUE_CARDINALITY",
    ),
    (
        re.compile(r"^Too (much|few) factor keyword.*$"),
        "INVALID_OCCURRENCE_CARDINALITY",
    ),
    (re.compile(r"^reuse is not allowed!$"), "REUSE_NOT_ALLOWED"),
    (re.compile(r"^Cannot type result of the command.*$"), "RESULT_TYPE_ERROR"),
    (re.compile(r"^'dict' object is expected$"), "INVALID_STRUCTURE"),
    (re.compile(r"^Type 'dict' or 'tuple' is expected$"), "INVALID_STRUCTURE"),
    (
        re.compile(r"^(At least one|Exactly one|At most one) argument of .*$"),
        "RULE_VIOLATION",
    ),
    (re.compile(r"^.* must be all (defined|undefined)$"), "RULE_VIOLATION"),
)


def strip_stack_prefix(message: str) -> str:
    """Remove `CheckerError.msg`'s own "For keyword X/Y: " prefix, if any.

    The prefix duplicates the `stack` field already reported separately by
    scripts/check_command_syntax.py (`CheckerError._stack`) — stripped here
    so the classification patterns below match the same way regardless of
    whether the original exception carried a stack.
    """
    return _STACK_PREFIX.sub("", message, count=1)


def classify(message: str) -> str:
    """Map an (already stack-stripped) message to a report `code`."""
    stripped = message.strip()
    for pattern, code in _PATTERNS:
        if pattern.match(stripped):
            return code
    return "CHECKER_ERROR"


def extract_keyword(message: str) -> str | None:
    """Pull the keyword name out of an unauthorized/mandatory-keyword message."""
    stripped = message.strip()
    match = _UNAUTHORIZED_KEYWORD.match(stripped) or _MANDATORY_KEYWORD.match(stripped)
    return match.group("kw") if match else None
