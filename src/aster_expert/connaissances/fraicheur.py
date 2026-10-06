"""Freshness of the knowledge schema held by a long-lived process (lot 47 ter, ENV-002).

The MCP server reads the knowledge base again at every call, but it imports the
schema (`aster_expert.connaissances.modeles`, `aster_expert.constats.models`, …) once,
at start. When a session changes the schema and the base together (lot 47 bis:
`version` and `version_history` added to CTL-005 and CTL-013), the files on disk follow
the new schema while the process still validates them with the old one: every entry is
refused (`extra="forbid"`), the whole base is declared inconsistent and every search
fails until the server is restarted.

`refresh_if_stale` compares the fingerprint of the source files of the read path with
the one taken when this module was imported and, if they differ, reloads those
modules in dependency order, then takes the new fingerprint. A failure of the base
after a refresh is a real inconsistency of the base, not a stale schema.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from pathlib import Path

READ_PATH_MODULES = (
    "aster_expert.constats.models",
    "aster_expert.constats.base",
    "aster_expert.constats.search",
    "aster_expert.connaissances.modeles",
    "aster_expert.connaissances.archive",
    "aster_expert.connaissances.base",
    "aster_expert.connaissances.recherche",
)
"""Modules of the reading of the base by `search_connaissances` and
`search_constats`, in dependency order (a module after those it imports)."""


def _source(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        message = f"module introuvable : {name}"
        raise ImportError(message)
    return Path(spec.origin)


def code_fingerprint(modules: tuple[str, ...] = READ_PATH_MODULES) -> str:
    """SHA-256 of the names and contents of the source files of `modules`."""
    digest = hashlib.sha256()
    for name in modules:
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(_source(name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


_loaded = code_fingerprint()


def loaded_fingerprint() -> str:
    """Fingerprint of the schema this process validates with."""
    return _loaded


def is_stale() -> bool:
    """True when the source files changed since they were loaded."""
    return code_fingerprint() != _loaded


def refresh_if_stale() -> bool:
    """Reload the read path when its sources changed; True if it did."""
    global _loaded  # noqa: PLW0603 -- the fingerprint of this process
    current = code_fingerprint()
    if current == _loaded:
        return False
    for name in READ_PATH_MODULES:
        module = sys.modules.get(name)
        if module is None:
            importlib.import_module(name)
        else:
            importlib.reload(module)
    _loaded = current
    return True


__all__ = [
    "READ_PATH_MODULES",
    "code_fingerprint",
    "is_stale",
    "loaded_fingerprint",
    "refresh_if_stale",
]
