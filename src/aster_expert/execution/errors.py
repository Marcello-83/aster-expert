"""Errors raised while locating or invoking the containerized Code_Aster runtime."""

from __future__ import annotations


class EnvironmentDetectionError(Exception):
    """Raised when the Code_Aster container environment cannot be resolved.

    Never raised on a guess: every case results from an explicit, verifiable
    failure (missing binary, forbidden tag, unreadable image, failed probe).
    """


class ExecutionRunError(Exception):
    """Raised when a `.comm` cannot even be attempted (level C).

    Never raised for an execution that ran but ended badly (a real
    `checkCommandSyntax`-level or Aster-level failure produces a normal
    `ExecutionReport` with `status="failed"` — that is a fact to report, not
    an error to raise). This is reserved for what stops the attempt before
    or during the container invocation itself: a file outside the allowed
    roots (docs/development-plan.md, lot 11, O2), a missing dedicated work
    directory, or a malformed result from the in-container script.
    """
