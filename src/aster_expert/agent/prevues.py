"""Planned commands of a fiche, derived from the project's `.comm` (lot 48 bis).

Audit R6: no fiche declared `planned_commands`, so `fiche obligatoires` had nothing to
read (lot 43 : four ELS parameters of `CALC_FERRAILLAGE` found only at run time).
`aster-expert fiche prevoir <projet>` derives the list from the `.comm` the project
generates, attaches each command to the point of the constat that names it (else to
the first practice point), and writes it into the fiche. Nothing is covered by the
derivation (`covered_by` stays empty): covering a keyword is a decision.
"""

from __future__ import annotations

import json
from pathlib import Path

from aster_expert.agent.hypotheses import HypothesesSheet, PlannedCommand
from aster_expert.agent.obligatoires import (
    default_rules_path,
    load_execution_rules,
    planned_from_comm,
)
from aster_expert.catalogue.errors import CatalogueExtractionError
from aster_expert.catalogue.models import CommandSchema
from aster_expert.catalogue.query import load_command_schema
from aster_expert.constats.base import base_dir, load_base
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.validation.errors import ValidationRunError
from aster_expert.validation.validate import resolve_digest_for_version


def derive_planned_commands(
    fiche_path: Path, comm_path: Path, repo_root: Path
) -> tuple[tuple[PlannedCommand, ...], tuple[str, ...]]:
    """(planned commands, commands without catalogue schema) of `comm_path`."""
    raw = json.loads(fiche_path.read_text(encoding="utf-8"))
    base = load_base(base_dir(repo_root))
    command_point: dict[str, str] = {}
    first_practice: str | None = None
    for entry in raw["entries"]:
        if entry.get("nature") == "constat" and entry["constat_id"] in base:
            for command in base[entry["constat_id"]].commands:
                command_point.setdefault(command, entry["point_label"])
        elif entry.get("nature") == "pratique" and first_practice is None:
            first_practice = entry["point_label"]
    if first_practice is None:
        message = f"{fiche_path} : aucun point de pratique où rattacher une commande"
        raise ValueError(message)
    fallback = first_practice

    catalogue_root = repo_root / "data" / "processed" / "catalogue"
    digest, _ = resolve_digest_for_version(
        catalogue_root, None, repo_root / "config" / "versions.yaml"
    )

    def schema_of(command: str) -> CommandSchema | None:
        try:
            return load_command_schema(catalogue_root, digest, command)
        except (CatalogueExtractionError, ValidationRunError, OSError, ValueError):
            return None

    analysis = parse_comm_source(
        comm_path.read_text(encoding="utf-8"), file_path=str(comm_path)
    )
    rules = load_execution_rules(default_rules_path(repo_root))
    return planned_from_comm(
        analysis,
        schema_of,
        lambda command: command_point.get(command, fallback),
        rules,
    )


def write_planned_commands(
    fiche_path: Path, planned: tuple[PlannedCommand, ...]
) -> None:
    """Write `planned_commands` into the fiche, validated, other keys untouched."""
    raw = json.loads(fiche_path.read_text(encoding="utf-8"))
    raw["planned_commands"] = [p.model_dump(mode="json") for p in planned]
    HypothesesSheet.model_validate(raw)
    fiche_path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def carry_planned_commands(sheet: HypothesesSheet, fiche_path: Path) -> HypothesesSheet:
    """`sheet` with the `planned_commands` the fiche file already holds.

    A script that rebuilds a fiche from its decisions must not drop the commands
    `fiche prevoir` wrote there (lot 48 bis); the scripts call this before writing."""
    if not fiche_path.is_file():
        return sheet
    raw = json.loads(fiche_path.read_text(encoding="utf-8"))
    planned = tuple(
        PlannedCommand.model_validate(p) for p in raw.get("planned_commands", ())
    )
    return sheet.model_copy(update={"planned_commands": planned})


__all__ = [
    "carry_planned_commands",
    "derive_planned_commands",
    "write_planned_commands",
]
