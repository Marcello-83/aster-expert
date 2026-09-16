"""Errors raised while synchronizing the external Git sources.

Distinct from a per-source *block* (recorded in the manifest as `status`
`blocked_dirty`/`blocked_diverged`/`blocked_error` — an expected, reported
outcome for one source, never fatal to the others): this exception means
`config/sources.yaml` itself, or the surrounding filesystem state, could not
be read or is malformed — the run cannot proceed at all.
"""

from __future__ import annotations


class SourcesConfigError(Exception):
    """Raised when config/sources.yaml is missing, malformed, or inconsistent."""
