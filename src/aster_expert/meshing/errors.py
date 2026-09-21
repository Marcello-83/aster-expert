"""Errors of the mesh chain."""

from __future__ import annotations


class MeshError(Exception):
    """Base class of the mesh chain errors."""


class MeshConfigError(MeshError):
    """`mesh:` section of `config/validation.yaml` missing or malformed."""


class MeshRunError(MeshError):
    """A Salome script could not be run, or its result is not acceptable."""


class MeshCheckError(MeshError):
    """The MED file could not be read or the invariants file is not valid."""
