"""Errors raised while extracting or reading the Code_Aster catalogue."""

from __future__ import annotations


class CatalogueExtractionError(Exception):
    """Raised when catalogue introspection cannot be completed or trusted.

    Never raised on a guess: every case results from an explicit,
    verifiable failure (missing prerequisite, failed container run, a
    per-command extraction error reported by the introspection script).
    """
