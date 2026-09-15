"""Errors raised while locating or invoking the containerized Code_Aster runtime."""

from __future__ import annotations


class EnvironmentDetectionError(Exception):
    """Raised when the Code_Aster container environment cannot be resolved.

    Never raised on a guess: every case results from an explicit, verifiable
    failure (missing binary, forbidden tag, unreadable image, failed probe).
    """
