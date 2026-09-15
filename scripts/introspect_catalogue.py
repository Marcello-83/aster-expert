"""Extract command schemas from the Code_Aster catalogue.

Run inside the Code_Aster container by its own Python interpreter (see
docs/architecture.md, ADR-002). Standard library only (scripts/README.md).
Writes one JSON file per command to ``--output-dir`` (conforming to
docs/metadata.md, section 2) and prints a summary as JSON on stdout.

Never guesses: a command whose definition contains a node type, a `typ`
atom, a `statut`, or an `sd_prod` shape this module does not recognize is
reported as an extraction error for that command (not silently skipped, not
guessed), and the process exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KNOWN_TYPE_CODES = frozenset({"C", "I", "R", "TXM"})
STATUS_MAP = {"o": "required", "f": "optional", "c": "hidden", "d": "default"}
KNOWN_COMMAND_KINDS = frozenset({"operator", "macro", "procedure", "formule"})

# Verified against docs (U4/U7/UX-style manual identifiers, e.g. "U4.51.03",
# "U4.44.12-e"). Commands whose catalogue `docu` does not match this are
# flagged as a (soft) anomaly, never corrected or dropped.
DOCU_PATTERN = re.compile(r"^[A-Z]\d\.\d{2}\.\d{2}(-\w+)?$")


def serialize_bound(value: object) -> object:
    """Map the catalogue's "**" (unbounded) sentinel to `null`."""
    if value == "**":
        return None
    return value


def serialize_status(raw: object) -> str:
    try:
        return STATUS_MAP[raw]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        message = f"unrecognized statut: {raw!r}"
        raise ValueError(message) from exc


def serialize_default_value(value: object) -> object:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, list | tuple):
        return [serialize_default_value(v) for v in value]
    message = f"unrecognized value: {value!r}"
    raise TypeError(message)


def serialize_typ_atom(atom: object, is_concept_class: Callable[[type], bool]) -> str:
    if isinstance(atom, str):
        if atom not in KNOWN_TYPE_CODES:
            message = f"unrecognized type code: {atom!r}"
            raise ValueError(message)
        return atom
    if isinstance(atom, type) and is_concept_class(atom):
        return atom.__name__
    message = f"unrecognized SIMP type atom: {atom!r}"
    raise TypeError(message)


def serialize_value_type(
    typ: object, is_concept_class: Callable[[type], bool]
) -> str | list[str]:
    if isinstance(typ, list | tuple):
        return [serialize_typ_atom(t, is_concept_class) for t in typ]
    return serialize_typ_atom(typ, is_concept_class)


def compute_variant_id(path: list[str], bloc_route: list[str]) -> str:
    """Stable, deterministic id disambiguating same-`path` nodes (lot 4b, C1).

    `path` alone does not identify a node: a keyword name reused under
    several sibling `Bloc` (e.g. `COMPORTEMENT.RESI_INTE` declared once per
    behaviour-selecting block) yields the same `path` for each variant —
    verified on STAT_NON_LINE alone: 37 duplicated paths, 72 extra entries.
    `bloc_route` is the ordered list of the raw catalogue dict keys of every
    `Bloc` traversed to reach this node (never the `condition` text itself,
    which is a separate, human-readable fact and does not by construction
    rule out two different blocs sharing the same condition string). Since
    dict keys are unique within a single `CataDefinition`, the concatenation
    of `bloc_route` and `path` is unique by construction — this hashes it
    only for a short, stable, opaque identifier.
    """
    payload = json.dumps({"path": path, "bloc_route": bloc_route}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def walk_entities(
    node: Any,
    path: list[str],
    condition_stack: list[str],
    is_concept_class: Callable[[type], bool],
    encountered_classes: set[str],
    bloc_route: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Walk the immediate and nested entities of a Command/FactorKeyword/Bloc.

    Dispatches on ``type(child).__name__`` rather than ``isinstance``: this
    module is unit-tested by the project's own Python, which never imports
    `code_aster` (docs/architecture.md, ADR-002), so tests exercise this
    logic against lightweight stand-ins that only need a matching class
    name, not the real ``code_aster.Cata`` inheritance chain.

    Uses ``.definition.entities`` (immediate children only, `Bloc` kept as
    its own node), never ``.definition.keywords`` (which flattens `Bloc`
    children into the parent and loses the condition).
    """
    bloc_route = bloc_route if bloc_route is not None else []
    result: list[dict[str, Any]] = []
    for key, child in node.definition.entities.items():
        type_name = type(child).__name__
        cur_path = [*path, key]
        if type_name == "Bloc":
            encountered_classes.add("Bloc")
            condition = child.getCondition()
            if not isinstance(condition, str):
                message = f"unrecognized Bloc condition at {cur_path}: {condition!r}"
                raise TypeError(message)
            result.extend(
                walk_entities(
                    child,
                    path,
                    [*condition_stack, condition],
                    is_concept_class,
                    encountered_classes,
                    [*bloc_route, key],
                )
            )
        elif type_name == "FactorKeyword":
            encountered_classes.add("FactorKeyword")
            children = walk_entities(
                child,
                cur_path,
                condition_stack,
                is_concept_class,
                encountered_classes,
                bloc_route,
            )
            result.append(
                {
                    "path": cur_path,
                    "variant_id": compute_variant_id(cur_path, bloc_route),
                    "kind": "factor",
                    "status": serialize_status(child.definition.get("statut", "f")),
                    "min_occurrences": serialize_bound(child.definition.get("min", 0)),
                    "max_occurrences": serialize_bound(child.definition.get("max", 1)),
                    "condition": list(condition_stack),
                    "children": children,
                }
            )
        elif type_name == "SimpleKeyword":
            encountered_classes.add("SimpleKeyword")
            into = child.definition.get("into")
            result.append(
                {
                    "path": cur_path,
                    "variant_id": compute_variant_id(cur_path, bloc_route),
                    "kind": "simple",
                    "status": serialize_status(child.definition.get("statut", "f")),
                    "value_type": serialize_value_type(
                        child.definition.get("typ"), is_concept_class
                    ),
                    "allowed_values": (
                        [serialize_default_value(v) for v in into]
                        if into is not None
                        else None
                    ),
                    "default": serialize_default_value(child.definition.get("defaut")),
                    # No default of 0/1 here: SyntaxChecker.visitSimpleKeyword
                    # reads `min` with no default (`step.definition.get("min")`,
                    # i.e. no lower bound enforced when absent) — unlike
                    # FactorKeyword occurrence counting, which defaults to 0.
                    "min_values": serialize_bound(child.definition.get("min")),
                    "max_values": serialize_bound(child.definition.get("max", 1)),
                    "condition": list(condition_stack),
                }
            )
        else:
            message = f"unrecognized entity type at {cur_path}: {type_name!r}"
            raise TypeError(message)
    return result


def build_command_schema(
    cmd: Any,
    *,
    aster_version: str,
    image_digest: str,
    catalogue_hash: str,
    catalogue_source: str,
    extracted_at: str,
    is_concept_class: Callable[[type], bool],
    encountered_classes: set[str],
) -> dict[str, Any]:
    kind = type(cmd).__name__.lower()
    if kind not in KNOWN_COMMAND_KINDS:
        message = f"unrecognized Command subclass: {type(cmd).__name__!r}"
        raise TypeError(message)
    encountered_classes.add(type(cmd).__name__)

    sd_prod = cmd.definition.get("sd_prod")
    if sd_prod is None:
        result_type, dynamic = None, False
    elif isinstance(sd_prod, type):
        result_type, dynamic = sd_prod.__name__, False
    elif callable(sd_prod):
        result_type, dynamic = None, True
    else:
        message = f"unrecognized sd_prod: {sd_prod!r}"
        raise TypeError(message)

    docu = cmd.definition.get("docu")
    if docu is not None and not isinstance(docu, str):
        message = f"unrecognized docu: {docu!r}"
        raise TypeError(message)

    return {
        "command": cmd.name,
        "aster_version": aster_version,
        "image_digest": image_digest,
        "catalogue_source": catalogue_source,
        "catalogue_hash": catalogue_hash,
        "kind": kind,
        "result_type": result_type,
        "result_type_dynamic": dynamic,
        "docu": docu,
        "keywords": walk_entities(cmd, [], [], is_concept_class, encountered_classes),
        "extracted_at": extracted_at,
    }


def has_usable_docu(docu: str | None) -> bool:
    """Whether `docu` is shaped like a real manual reference, not just non-null.

    Absence (`None`) and a malformed value are both "not usable" for
    citation purposes: distinguishing them is the job of `docu_anomaly`
    below, not of this predicate.
    """
    return docu is not None and bool(DOCU_PATTERN.match(docu))


def docu_anomaly(command: str, docu: str | None) -> dict[str, str] | None:
    """Flag a `docu` value not shaped like a manual reference (soft anomaly).

    A heuristic, not a fact: reported as `docu_suspect`, the value is never
    dropped or corrected in the schema itself. Returns nothing for `None`:
    that case is common (260/268 commands on the 17.4.0 catalogue) and
    counted in aggregate as `commands_without_usable_docu` in the summary,
    not reported as one `docu_suspect` anomaly per command (lot 4b, C4 — the
    lot 4 summary under-reported this: only the 2 malformed non-null values
    were flagged, silently treating "absent" as "fine").
    """
    if docu is None:
        return None
    if not DOCU_PATTERN.match(docu):
        return {"command": command, "kind": "docu_suspect", "detail": docu}
    return None


def extract_all(
    commands: Mapping[str, Any],
    *,
    aster_version: str,
    image_digest: str,
    catalogue_hash: str,
    catalogue_source: str,
    extracted_at: str,
    is_concept_class: Callable[[type], bool],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Extract every command's schema; never raises on a per-command failure.

    Returns (schemas keyed by command name, summary dict). A command that
    fails to extract is excluded from the first return value and recorded
    as an `extraction_error` anomaly in the summary.
    """
    schemas: dict[str, dict[str, Any]] = {}
    kind_counts: dict[str, int] = {}
    encountered_classes: set[str] = set()
    anomalies: list[dict[str, str]] = []

    for name in sorted(commands):
        cmd = commands[name]
        try:
            schema = build_command_schema(
                cmd,
                aster_version=aster_version,
                image_digest=image_digest,
                catalogue_hash=catalogue_hash,
                catalogue_source=catalogue_source,
                extracted_at=extracted_at,
                is_concept_class=is_concept_class,
                encountered_classes=encountered_classes,
            )
        except (TypeError, ValueError) as exc:
            anomalies.append(
                {"command": name, "kind": "extraction_error", "detail": str(exc)}
            )
            continue
        schemas[name] = schema
        kind_counts[schema["kind"]] = kind_counts.get(schema["kind"], 0) + 1
        anomaly = docu_anomaly(name, schema["docu"])
        if anomaly is not None:
            anomalies.append(anomaly)

    commands_without_usable_docu = sum(
        1 for schema in schemas.values() if not has_usable_docu(schema["docu"])
    )

    summary = {
        "total_exposed": len(commands),
        "total_extracted": len(schemas),
        "kind_counts": kind_counts,
        "encountered_classes": sorted(encountered_classes),
        "commands_without_usable_docu": commands_without_usable_docu,
        "anomalies": anomalies,
    }
    return schemas, summary


def _find_commands(cata_commands_module: Any, command_base: type) -> dict[str, Any]:
    commands: dict[str, Any] = {}
    for attr_name in dir(cata_commands_module):
        if attr_name.startswith("_"):
            continue
        obj = getattr(cata_commands_module, attr_name)
        if isinstance(obj, command_base):
            commands[attr_name] = obj
    return commands


def _write_schemas(
    schemas: Iterable[tuple[str, dict[str, Any]]], output_dir: Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas:
        (output_dir / f"{name}.json").write_text(
            json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--catalogue-hash", required=True)
    parser.add_argument("--aster-version", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        import code_aster
        import code_aster.Cata.Commands
        from code_aster.Cata.Language import DataStructure as DS  # noqa: N817
        from code_aster.Cata.Language.DataStructure import DataStructure, UnitBaseType
        from code_aster.Cata.Language.SyntaxObjects import Command
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        print(f"introspect_catalogue: cannot import catalogue: {exc}", file=sys.stderr)
        return 1

    def is_concept_class(cls: type) -> bool:
        return (
            issubclass(cls, DataStructure)
            or issubclass(cls, UnitBaseType)
            or issubclass(cls, DS.MeshEntity)
            or issubclass(cls, DS.GEOM)
        )

    commands = _find_commands(code_aster.Cata.Commands, Command)
    if not commands:
        print(
            "introspect_catalogue: no Command instances in Cata.Commands",
            file=sys.stderr,
        )
        return 1

    catalogue_source = str(Path(code_aster.__file__).resolve().parent)
    extracted_at = datetime.now(UTC).isoformat()

    schemas, summary = extract_all(
        commands,
        aster_version=args.aster_version,
        image_digest=args.image_digest,
        catalogue_hash=args.catalogue_hash,
        catalogue_source=catalogue_source,
        extracted_at=extracted_at,
        is_concept_class=is_concept_class,
    )

    _write_schemas(schemas.items(), args.output_dir)

    print(json.dumps(summary))

    has_hard_errors = any(a["kind"] == "extraction_error" for a in summary["anomalies"])
    return 1 if has_hard_errors else 0


if __name__ == "__main__":
    sys.exit(main())
