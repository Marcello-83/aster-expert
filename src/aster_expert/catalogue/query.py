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


def resolve_digest_for_aster_version(catalogue_root: Path, version: str) -> str:
    """The single extracted catalogue digest whose `aster_version` is `version`.

    Never guesses: fails loudly if zero, or more than one, extracted digest
    under `catalogue_root` matches (docs/architecture.md principle 1,
    "ne jamais mélanger silencieusement plusieurs versions"). Shared by
    `aster_expert.validation.validate.resolve_digest_for_version` (its
    explicit-`--version` branch) and `aster_expert.indexing.enrichment`
    (lot 7b, E1) — the same "which extracted catalogue matches this exact
    version string" question, asked by both callers, answered once here.
    """
    if not catalogue_root.is_dir():
        message = f"no extracted catalogue at {catalogue_root}"
        raise CatalogueExtractionError(message)

    candidates: list[str] = []
    for digest_dir in sorted(catalogue_root.iterdir()):
        if not digest_dir.is_dir():
            continue
        first = next(iter(sorted(digest_dir.glob("*.json"))), None)
        if first is None:
            continue
        schema = CommandSchema.model_validate_json(first.read_text(encoding="utf-8"))
        if schema.aster_version == version:
            candidates.append(digest_dir.name)

    if not candidates:
        message = (
            f"no extracted catalogue found for version {version!r} under "
            f"{catalogue_root}; run `aster-expert catalogue extract` with "
            "that version's environment first"
        )
        raise CatalogueExtractionError(message)
    if len(candidates) > 1:
        message = (
            f"more than one extracted catalogue matches version {version!r}: "
            f"{candidates}; refusing to guess which one to use"
        )
        raise CatalogueExtractionError(message)
    return candidates[0]


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


def find_keyword_variants(
    schema: CommandSchema, path: list[str]
) -> list[KeywordSchema]:
    """Locate every variant of a keyword by its dotted path.

    `path` does not identify a single node: the same keyword name can be
    declared once per sibling `Bloc` (e.g. a behaviour-specific
    `COMPORTEMENT.RESI_INTE`), so several entries can share the same `path`,
    each with its own `condition` and `variant_id` (lot 4b, C1 — an earlier
    version of this function silently returned the first match via `next()`,
    hiding the other variants). A full recursive scan is used rather than a
    level-by-level descent: duplication can occur at any depth, not only at
    the leaf, so descending by the first match at each level could itself
    silently drop variants of an intermediate ancestor.
    """
    if not path:
        message = "empty keyword path"
        raise CatalogueExtractionError(message)

    results: list[KeywordSchema] = []

    def walk(entries: list[KeywordSchema]) -> None:
        for entry in entries:
            if list(entry.path) == path:
                results.append(entry)
            if isinstance(entry, FactorKeywordSchema):
                walk(entry.children)

    walk(list(schema.keywords))

    if not results:
        message = f"keyword path not found in {schema.command!r}: {'.'.join(path)}"
        raise CatalogueExtractionError(message)
    return results
