"""Read back extracted command schemas (`aster-expert catalogue show`)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import (
    CommandSchema,
    FactorKeywordSchema,
    KeywordSchema,
)


def resolve_active_digest(versions_yaml_path: Path) -> str:
    """Return the digest of the last environment detected (lot 2).

    Never falls back to a tag: `config/versions.yaml`'s `detected` section
    is only ever written with a resolved digest (docs/architecture.md,
    ADR-002).
    """
    if not versions_yaml_path.is_file():
        message = f"config/versions.yaml not found: {versions_yaml_path}"
        raise CatalogueExtractionError(message)
    data = yaml.safe_load(versions_yaml_path.read_text(encoding="utf-8")) or {}
    digest = (
        (data.get("detected") or {}).get("container", {}).get("image_digest")
        if isinstance(data.get("detected"), dict)
        else None
    )
    if not digest:
        message = (
            "no detected image digest in config/versions.yaml; "
            "run `aster-expert env detect` (or `catalogue extract`) first"
        )
        raise CatalogueExtractionError(message)
    return str(digest)


def load_command_schema(
    catalogue_root: Path, digest: str, command: str
) -> CommandSchema:
    path = catalogue_root / digest / f"{command}.json"
    if not path.is_file():
        message = (
            f"no extracted schema for '{command}' at digest {digest}; "
            "run `aster-expert catalogue extract` first"
        )
        raise CatalogueExtractionError(message)
    return CommandSchema.model_validate(json.loads(path.read_text(encoding="utf-8")))


def find_keyword(schema: CommandSchema, path: list[str]) -> KeywordSchema:
    """Locate a keyword by its dotted path (e.g. ``COMPORTEMENT.RELATION``)."""
    if not path:
        message = "empty keyword path"
        raise CatalogueExtractionError(message)

    entries: list[KeywordSchema] = list(schema.keywords)
    current: KeywordSchema | None = None
    for depth in range(len(path)):
        wanted = path[: depth + 1]
        current = next((e for e in entries if list(e.path) == wanted), None)
        if current is None:
            message = f"keyword path not found in {schema.command!r}: {'.'.join(path)}"
            raise CatalogueExtractionError(message)
        entries = current.children if isinstance(current, FactorKeywordSchema) else []
    if current is None:  # pragma: no cover - unreachable: path is non-empty
        message = "internal error: keyword path resolved to nothing"
        raise CatalogueExtractionError(message)
    return current
