"""Errors of the `.comm` generator (lot 28)."""

from __future__ import annotations


class GenerationError(ValueError):
    """The fiche, the data or the mesh do not found a `.comm` generation."""
