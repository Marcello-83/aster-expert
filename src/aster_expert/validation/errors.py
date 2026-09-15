"""Errors raised while running the level B validation pipeline itself.

Distinct from a validation *finding* (a `ValidationFinding` in the report,
docs/metadata.md section 4): this exception means the pipeline could not run
at all (no catalogue extracted for the requested version, no work root, a
failed container invocation) — never raised on a guess about the `.comm`
file's own correctness.
"""

from __future__ import annotations


class ValidationRunError(Exception):
    """Raised when level B validation cannot be completed or trusted."""
