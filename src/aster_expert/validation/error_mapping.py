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
from dataclasses import dataclass

_STACK_PREFIX = re.compile(r"^For keyword [^:]+: ")

_UNAUTHORIZED_KEYWORD = re.compile(r"^Unauthorized keyword: '(?P<kw>[^']*)'$")
# A missing mandatory keyword is *never* raised through CheckerError/`self.
# error(...)`: `Composite.checkMandatory` (`Cata/Language/SyntaxObjects.py`)
# raises a bare `KeyError("Keyword {0} is mandatory".format(key))` directly.
# `scripts/check_command_syntax.py` reports `str(exc)` for a bare exception
# (no `.msg` attribute) -- and `KeyError.__str__` returns `repr()` of its
# single argument, i.e. the *whole* message wrapped in one extra pair of
# single quotes: `"'Keyword CHAM_MATER is mandatory'"`, not `"Keyword
# CHAM_MATER is mandatory"`. The trailing/leading `'?` here matches that real
# shape (docs/development-plan.md, lot 10c, point R2 — found while every
# MISSING_MANDATORY_KEYWORD instance corpus-wide was silently falling
# through to the generic CHECKER_ERROR bucket instead) without discarding
# the unquoted form, in case some other, currently unobserved call site ever
# wraps this same text through a proper CheckerError instead.
_MANDATORY_KEYWORD = re.compile(r"^'?Keyword (?P<kw>\S+) is mandatory'?$")

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


@dataclass(frozen=True)
class ToolLimitation:
    """One verified, narrow signature of a `checkCommandSyntax` limitation.

    Not a project rule of grammar: every entry names one exact `(command,
    message)` shape, traced to a specific defect *in the catalogue's own*
    `sd_prod` function by reading its source directly, and confirmed against
    a real cas test where the offending statement carries only literal
    keywords — so the failure is not an artifact of this project's argument
    reconstruction (`aster_expert.validation.reconstruct`). The same failure
    would occur during real execution, on the same input: this is a genuine
    limitation of calling the checker outside execution, not a user fault
    (docs/development-plan.md, lot 10c, point P2).
    """

    command: str
    pattern: re.Pattern[str]
    reason: str


# Verified against real astest/*.comm cas tests (docs/development-plan.md,
# lot 10c, point P2 — commands and line numbers in each `reason` below).
# `Cannot type result of the command X\nException raised: ...)` is the
# generic wrapper `SyntaxCheckerVisitor.visitCommand`
# (`Cata/Language/SyntaxChecker.py`) puts around *any* exception from its own
# internal `step.get_type_sd_prod(**userDict)` call — every message here
# matches that same wrapper, never a project-authored message.
_TOOL_LIMITATIONS: tuple[ToolLimitation, ...] = (
    ToolLimitation(
        command="MACRO_ELAS_MULT",
        pattern=re.compile(
            r"^Cannot type result of the command MACRO_ELAS_MULT\n"
            r"Exception raised: KeyError\('NOM_CAS'\)\)$"
        ),
        reason=(
            "checkCommandSyntax limitation, not a user fault: "
            "MACRO_ELAS_MULT's own sd_prod "
            "(code_aster/Cata/Commands/macro_elas_mult.py) reads "
            "CAS_CHARGE[i]['NOM_CAS'] unconditionally, but NOM_CAS is "
            "declared optional with no default (docs/metadata.md, §2) so "
            "addDefaultKeywords never inserts it — a plain KeyError bubbles "
            "out of get_type_sd_prod, which checkCommandSyntax itself calls "
            "internally (Cata/Language/SyntaxChecker.py, visitCommand) and "
            "wraps as CheckerError. Confirmed against a real cas test with "
            "an entirely literal, catalogue-conformant CAS_CHARGE that "
            "simply omits NOM_CAS (astest/hslv304b.comm, MACRO_ELAS_MULT at "
            "line 57): the official checker cannot type this file, not "
            "because of anything wrong in it."
        ),
    ),
    ToolLimitation(
        command="AFFE_CARA_ELEM",
        pattern=re.compile(
            r"^Cannot type result of the command AFFE_CARA_ELEM\n"
            r"Exception raised: KeyError\('EPAIS'\)\)$"
        ),
        reason=(
            "checkCommandSyntax limitation, not a user fault: same family "
            "as MACRO_ELAS_MULT above. AFFE_CARA_ELEM's own sd_prod "
            "(code_aster/Cata/Commands/affe_cara_elem.py,"
            " affe_cara_elem_prod) reads mclf['EPAIS'] unconditionally for a "
            "COQUE occurrence, but EPAIS is declared optional with no "
            "default (docs/metadata.md, §2) and the catalogue's own "
            "alternative, EPAIS_FO (a formula), is a legitimate substitute "
            "the function never checks for. Confirmed against a real cas "
            "test whose COQUE occurrence uses EPAIS_FO (a FORMULE concept "
            "reference) and never provides EPAIS at all "
            "(astest/zzzz331a.comm, AFFE_CARA_ELEM at lines 50/58): a "
            "legitimate, catalogue-conformant file the official checker "
            "itself cannot type."
        ),
    ),
    ToolLimitation(
        command="DEFI_GROUP",
        pattern=re.compile(
            r"^Cannot type result of the command DEFI_GROUP\n"
            r"Exception raised: CataError\('type de concept resultat non "
            r"prevu'\)\)$"
        ),
        reason=(
            "checkCommandSyntax limitation, not a user fault: DEFI_GROUP's "
            "own sd_prod (code_aster/Cata/Commands/defi_group.py, "
            "defi_group_prod) dispatches on `AsType(MAILLAGE) == "
            "maillage_sdaster` — an *exact* class equality, not a subclass "
            "check — so a MAILLAGE of type super_mesh (a maillage_sdaster "
            "subclass, code_aster/Cata/Language/DataStructure.py, produced "
            "by DEFI_MAILLAGE/ASSE_MAILLAGE) never matches and falls "
            "through to `raise CataError(...)`. A real gap in the "
            "catalogue's own type dispatch (read directly in "
            "defi_group_prod, not inferred): the same failure occurs during "
            "real execution, on the same input. Confirmed on a real cas "
            "test (astest/sdlx102a.comm, DEFI_GROUP at lines 58/63/66, all "
            "consuming a super_mesh MAILLAGE from DEFI_MAILLAGE with "
            "otherwise entirely literal keywords)."
        ),
    ),
)


def match_tool_limitation(command: str, message: str) -> str | None:
    """Return the dedicated not-checked reason for a verified tool limitation.

    `None` for anything else — an unmatched `CHECKER_ERROR` is still a real,
    unclassified rejection, reported as an error like any other
    (docs/development-plan.md, lot 10c: never a broad heuristic, only exact,
    individually verified signatures — see `_TOOL_LIMITATIONS`).
    """
    stripped = message.strip()
    return next(
        (
            limitation.reason
            for limitation in _TOOL_LIMITATIONS
            if limitation.command == command and limitation.pattern.match(stripped)
        ),
        None,
    )


@dataclass(frozen=True)
class ExecutionConfirmedOverride:
    """A static `INVALID_TYPE` rejection proven, by real execution, to be a
    false positive of this project's own level-B check — never of
    `checkCommandSyntax` itself, whose verdict is a fact this project never
    overrides silently (docs/metadata.md §4: `code` "n'est jamais une
    décision de validité propre au projet"). `command`/`stack` narrow the
    match to the exact failing keyword; `required_producer_command` is
    checked separately, host-side (`aster_expert.validation.validate`),
    against the concept actually bound at that keyword — this table alone
    is not sufficient to decide a match.
    """

    command: str
    stack: str
    pattern: re.Pattern[str]
    required_producer_command: str
    reason: str


# docs/development-plan.md, lot 10c, point P3. EXTR_COUPE's catalogue
# declares a single static `sd_prod=cham_gd_sdaster`
# (code_aster/Cata/Commands/extr_coupe.py) -- but its executor
# (code_aster/MacroCommands/extr_coupe_ops.py, `line_coupe`/
# `convert_med_to_aster`) can instead call `LIRE_RESU(TYPE_RESU=resu.
# getType(), ...)`, i.e. rebuild the cut result typed *like the original
# RESULTAT it was extracted from* (an `evol_*` subtype of `resultat_sdaster`,
# code_aster/Cata/Language/DataStructure.py) -- not literally
# `cham_gd_sdaster`. The catalogue's static declaration is an
# oversimplification of a genuinely path-dependent executor, not
# discoverable by reading the catalogue alone. Verified by real execution
# (docs/development-plan.md, lot 10c, point P3): `cave run` /
# `run_aster astest/zzzz169a.export` inside the container reaches `FIN`
# with `DIAGNOSTIC JOB : OK` and every `TEST_RESU`/`TEST_TABLE` passing,
# including the exact CREA_CHAMP(OPERATION="EXTR", RESULTAT=<EXTR_COUPE
# result>)/POST_RELEVE_T(ACTION=_F(RESULTAT=<EXTR_COUPE result>, ...))
# statements this project's static check rejects. This project's own check
# is therefore stricter than the real supervisor here, not the file.
_EXECUTION_CONFIRMED_OVERRIDES: tuple[ExecutionConfirmedOverride, ...] = (
    ExecutionConfirmedOverride(
        command="CREA_CHAMP",
        stack="RESULTAT",
        pattern=re.compile(
            r"^Unexpected type: <class 'code_aster\.Cata\.Language\."
            r"DataStructure\.cham_gd_sdaster'>, expecting: \[<class "
            r"'code_aster\.Cata\.Language\.DataStructure\.resultat_sdaster'"
            r"\>\]$"
        ),
        required_producer_command="EXTR_COUPE",
        reason=(
            "checkCommandSyntax rejects this RESULTAT as cham_gd_sdaster, "
            "expecting resultat_sdaster -- a real mismatch between "
            "EXTR_COUPE's static catalogue declaration (sd_prod="
            "cham_gd_sdaster) and its executor's actual, path-dependent "
            "behaviour (code_aster/MacroCommands/extr_coupe_ops.py can "
            "retype the cut result like the original RESULTAT via "
            "LIRE_RESU(TYPE_RESU=resu.getType(), ...), a resultat_sdaster "
            "subtype). Confirmed by real execution: astest/zzzz169a.comm, "
            "with this exact CREA_CHAMP(OPERATION='EXTR', RESULTAT=<an "
            "EXTR_COUPE result>) pattern, reaches FIN "
            "(docs/development-plan.md, lot 10c, point P3). This project's "
            "static check is stricter than the real supervisor here, not "
            "the file: reported as a warning, never an error."
        ),
    ),
    ExecutionConfirmedOverride(
        command="POST_RELEVE_T",
        stack="ACTION/RESULTAT",
        pattern=re.compile(
            r"^Unexpected type: <class 'code_aster\.Cata\.Language\."
            r"DataStructure\.cham_gd_sdaster'>, expecting: \[<class "
            r"'code_aster\.Cata\.Language\.DataStructure\.resultat_sdaster'"
            r"\>\]$"
        ),
        required_producer_command="EXTR_COUPE",
        reason=(
            "checkCommandSyntax rejects this ACTION/RESULTAT as "
            "cham_gd_sdaster, expecting resultat_sdaster -- same "
            "EXTR_COUPE catalogue/executor mismatch as CREA_CHAMP above. "
            "Confirmed by real execution: astest/zzzz169a.comm, with this "
            "exact POST_RELEVE_T(ACTION=_F(RESULTAT=<an EXTR_COUPE "
            "result>, ...)) pattern, reaches FIN (docs/development-plan.md, "
            "lot 10c, point P3). Reported as a warning, never an error."
        ),
    ),
)


def match_execution_confirmed_override(
    command: str, stack: str | None, message: str
) -> ExecutionConfirmedOverride | None:
    """Return the matching override, if any -- `None` for anything else.

    Only the message/command/stack shape is checked here; the caller
    (`aster_expert.validation.validate`) still verifies the required
    producer command against the actual concept bound at that keyword
    before treating this as confirmed (never a guess from text alone).
    """
    stripped = message.strip()
    return next(
        (
            override
            for override in _EXECUTION_CONFIRMED_OVERRIDES
            if override.command == command
            and override.stack == (stack or "")
            and override.pattern.match(stripped)
        ),
        None,
    )
