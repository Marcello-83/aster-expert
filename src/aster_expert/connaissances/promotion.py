"""Explicit promotion of an entry to `promu` (lot 42, étape 2).

`promote(repo_root, entry_id, by=..., reason=...)` checks the conditions and
fails otherwise, never silently:

- the entry exists and is `établi` (an `observé` entry is first made
  replayable);
- it was **proved** in at least two projects -- its origin and the projects of
  its `reuses` whose evidence is a successful execution or a passing test
  (`modeles.is_proof`); for a finding, its épreuves of
  `connaissances/epreuves_constats.yaml` -- or it reached level E.

Lot 44: a citation in a fiche, a decision, a document or a piece of code is not a
proof. Until lot 43 a finding counted every project whose fiche cites it: CA-025
and CA-041 were eligible through the slab without the slab exercising them.
`eligibility` replays the rule over every entry of the base.

A YAML entry is rewritten with `status: promu` and a status event; every
promotion, of a finding included, is appended to `connaissances/promotions.yaml`.
Nothing calls this function except the command `aster-expert connaissances
promouvoir`.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from aster_expert.connaissances.base import (
    PROMOTIONS_FILE,
    ConstatView,
    knowledge_dir,
    load_knowledge,
    write_entry,
)
from aster_expert.connaissances.modeles import StatusEvent


class PromotionRefusedError(ValueError):
    """The conditions of promotion are not met."""


def promotion_conditions(repo_root: Path, entry_id: str) -> tuple[bool, str, list[str]]:
    """(allowed, reason, projects) without writing anything."""
    base = load_knowledge(repo_root)
    entry = base.get(entry_id)
    if entry is None:
        return False, f"{entry_id} absent de la base", []
    if entry.status == "promu":
        return False, f"{entry_id} est déjà promu", []
    if entry.status != "établi":
        return (
            False,
            f"{entry_id} est {entry.status} : seule une entrée établie (preuve "
            "rejouable) peut être promue",
            [],
        )
    projects = sorted(
        entry.projects if isinstance(entry, ConstatView) else entry.projects()
    )
    cited = sorted(
        entry.cited_by if isinstance(entry, ConstatView) else entry.cited_projects()
    )
    if len(projects) >= 2:
        return True, f"éprouvée dans {len(projects)} projets", projects
    if entry.validation_level == "E":
        return True, "validée au niveau E", projects
    unproved = (
        f" ; cité sans épreuve par {', '.join(cited)}, ce qui ne compte pas"
        if cited
        else ""
    )
    return (
        False,
        f"{entry_id} : un seul projet ({', '.join(projects)}) et niveau "
        f"{entry.validation_level} : la promotion exige deux projets qui l'ont "
        f"éprouvée ou le niveau E{unproved}",
        projects,
    )


class Eligibility(BaseModel):
    """One line of the eligibility replay (lot 44)."""

    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    validation_level: str
    proved_in: tuple[str, ...]
    cited_by: tuple[str, ...]
    eligible: bool
    reason: str


def eligibility(repo_root: Path) -> list[Eligibility]:
    """The corrected rule replayed over every entry of the base."""
    base = load_knowledge(repo_root)
    out = []
    for entry in sorted(base.all_entries(), key=lambda e: e.id):
        allowed, reason, projects = promotion_conditions(repo_root, entry.id)
        cited = (
            entry.cited_by if isinstance(entry, ConstatView) else entry.cited_projects()
        )
        out.append(
            Eligibility(
                id=entry.id,
                status=entry.status,
                validation_level=entry.validation_level,
                proved_in=tuple(projects),
                cited_by=tuple(sorted(cited)),
                eligible=allowed,
                reason=reason,
            )
        )
    return out


def promote(
    repo_root: Path,
    entry_id: str,
    *,
    by: str,
    reason: str,
    today: dt.date | None = None,
) -> str:
    if not by.strip() or not reason.strip():
        message = "une promotion porte son auteur et son motif"
        raise PromotionRefusedError(message)
    allowed, why, projects = promotion_conditions(repo_root, entry_id)
    if not allowed:
        raise PromotionRefusedError(why)
    day = today or dt.date.today()
    base = load_knowledge(repo_root)
    entry = base.entries.get(entry_id)
    if entry is not None:
        event = StatusEvent(status="promu", date=day, by=by, reason=reason)
        promoted = type(entry).model_validate(
            {
                **entry.model_dump(),
                "status": "promu",
                "status_history": [*entry.status_history, event],
            }
        )
        write_entry(repo_root, promoted)
    path = knowledge_dir(repo_root) / PROMOTIONS_FILE
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    events = list((raw or {}).get("promotions") or [])
    events.append(
        {
            "id": entry_id,
            "date": day.isoformat(),
            "by": by,
            "reason": reason,
            "projects": projects,
        }
    )
    path.write_text(
        yaml.safe_dump({"promotions": events}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    load_knowledge(repo_root)
    return f"{entry_id} promu ({why})."


__all__ = [
    "Eligibility",
    "PromotionRefusedError",
    "eligibility",
    "promote",
    "promotion_conditions",
]
