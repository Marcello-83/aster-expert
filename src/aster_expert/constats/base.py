"""The shared base of Code_Aster findings (lot 41, étape 4).

`connaissances/constats_code_aster/<CA-nnn>.json`, one `Constat` per file,
versioned. A fiche cites a finding by `FindingReference`; `resolve_sheet`
substitutes the full entry (with the fiche's own `point_label`), and
`externalize_sheet` does the converse for a fiche whose `code_aster` entries
are already all in the base -- strictly: an entry that matches no finding of
the base, or differs from it by one character, is refused, never silently
turned into a reference to something else.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from pathlib import Path

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    FindingReference,
    HypothesesSheet,
    HypothesisEntry,
)
from aster_expert.constats.models import (
    Constat,
    FindingOrigin,
    derived_level,
    derived_trial_cases,
    entry_text,
)

BASE_RELATIVE = Path("connaissances") / "constats_code_aster"

_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9_]*[A-Z0-9](?![A-Za-z0-9_])")


class ConstatBaseError(ValueError):
    """The base is unreadable, or a reference does not resolve."""


def base_dir(repo_root: Path) -> Path:
    return repo_root / BASE_RELATIVE


def constat_path(directory: Path, constat_id: str) -> Path:
    return directory / f"{constat_id}.json"


def load_base(directory: Path) -> dict[str, Constat]:
    """Every finding of the base, by identifier. A file whose name is not its
    identifier is refused."""
    if not directory.is_dir():
        message = f"base de constats introuvable : {directory}"
        raise ConstatBaseError(message)
    out: dict[str, Constat] = {}
    for path in sorted(directory.glob("CA-*.json")):
        try:
            constat = Constat.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            message = f"constat illisible : {path} : {exc}"
            raise ConstatBaseError(message) from exc
        if path.stem != constat.constat_id:
            message = f"{path} : le fichier porte l'identifiant {constat.constat_id}"
            raise ConstatBaseError(message)
        out[constat.constat_id] = constat
    return out


def write_constat(constat: Constat, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = constat_path(directory, constat.constat_id)
    path.write_text(
        json.dumps(json.loads(constat.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return path


def resolve_sheet(sheet: HypothesesSheet, base: dict[str, Constat]) -> HypothesesSheet:
    """Replace each `FindingReference` by the base's entry, with the reference's
    `point_label`. An unknown identifier is an error."""
    if not sheet.finding_references():
        return sheet
    entries: list[HypothesisEntry] = []
    for e in sheet.entries:
        if isinstance(e, FindingReference):
            constat = base.get(e.constat_id)
            if constat is None:
                message = (
                    f"constat {e.constat_id} (point {e.point_label}) absent de la base"
                )
                raise ConstatBaseError(message)
            entries.append(
                constat.entry.model_copy(update={"point_label": e.point_label})
            )
        else:
            entries.append(e)
    return sheet.model_copy(update={"entries": tuple(entries)})


def find_base_dir(start: Path) -> Path:
    """The base of the repository that contains `start` (first parent holding
    `connaissances/constats_code_aster`)."""
    for parent in (start.resolve(), *start.resolve().parents):
        candidate = parent / BASE_RELATIVE
        if candidate.is_dir():
            return candidate
    message = f"aucune base de constats au-dessus de {start}"
    raise ConstatBaseError(message)


def load_resolved_sheet(
    path: Path, *, repo_root: Path | None = None
) -> HypothesesSheet:
    """Read a fiche and resolve its references. Without `repo_root`, the base is
    the one of the repository holding the fiche."""
    sheet = HypothesesSheet.model_validate_json(path.read_text(encoding="utf-8"))
    if not sheet.finding_references():
        return sheet
    directory = base_dir(repo_root) if repo_root is not None else find_base_dir(path)
    return resolve_sheet(sheet, load_base(directory))


def _without_point(entry: CodeAsterHypothesisEntry) -> CodeAsterHypothesisEntry:
    return entry.model_copy(update={"point_label": None})


def externalize_sheet(
    sheet: HypothesesSheet, base: dict[str, Constat]
) -> HypothesesSheet:
    """Every `code_aster` entry replaced by a reference to the finding of the
    base that is identical to it (point label aside). Refused if an entry has no
    identical finding, or several."""
    by_content: dict[str, list[str]] = {}
    for constat in base.values():
        key = constat.entry.model_dump_json()
        by_content.setdefault(key, []).append(constat.constat_id)
    entries: list[HypothesisEntry] = []
    for e in sheet.entries:
        if not isinstance(e, CodeAsterHypothesisEntry):
            entries.append(e)
            continue
        matches = by_content.get(_without_point(e).model_dump_json(), [])
        if len(matches) != 1:
            message = (
                f"constat du point {e.point_label} « {e.topic[:80]} » : "
                f"{len(matches)} constat(s) identique(s) dans la base (1 attendu) -- "
                "la base est la référence : mettre à jour le constat, jamais la fiche"
            )
            raise ConstatBaseError(message)
        entries.append(
            FindingReference(constat_id=matches[0], point_label=e.point_label)
        )
    return sheet.model_copy(update={"entries": tuple(entries)})


def identifiers(
    entry: CodeAsterHypothesisEntry,
    *,
    commands: Collection[str],
    keywords: Collection[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(commands, keywords) the finding concerns: the command and keyword path of
    its catalogue sources, plus every catalogue identifier its text names.
    `commands`/`keywords` are the target catalogue's own vocabulary
    (`aster_expert.catalogue.query.catalogue_identifiers`), never a hand list."""
    found_commands: set[str] = set()
    found_keywords: set[str] = set()
    for s in entry.sources:
        if isinstance(s, CatalogueSource):
            found_commands.add(s.command)
            found_keywords.update(s.keyword_path)
    for token in _IDENTIFIER.findall(entry_text(entry)):
        if token in commands:
            found_commands.add(token)
        elif token in keywords:
            found_keywords.add(token)
    found_keywords -= found_commands
    return tuple(sorted(found_commands)), tuple(sorted(found_keywords))


def build_constat(
    entry: CodeAsterHypothesisEntry,
    *,
    constat_id: str,
    summary: str,
    origin: FindingOrigin,
    commands: Collection[str],
    keywords: Collection[str],
) -> Constat:
    """A finding of the base from a fiche's entry: every derived field computed
    here, then checked again by `Constat` itself."""
    bare = _without_point(entry)
    versions = sorted({s.aster_version for s in bare.sources})
    if len(versions) != 1:
        message = f"{constat_id} : versions des sources {versions} (une seule attendue)"
        raise ConstatBaseError(message)
    found_commands, found_keywords = identifiers(
        bare, commands=commands, keywords=keywords
    )
    return Constat(
        constat_id=constat_id,
        summary=summary,
        aster_version=versions[0],
        validation_level=derived_level(bare),
        commands=found_commands,
        keywords=found_keywords,
        trial_cases=derived_trial_cases(bare),
        origin=origin,
        entry=bare,
    )


__all__ = [
    "BASE_RELATIVE",
    "ConstatBaseError",
    "base_dir",
    "build_constat",
    "constat_path",
    "externalize_sheet",
    "find_base_dir",
    "identifiers",
    "load_base",
    "load_resolved_sheet",
    "resolve_sheet",
    "write_constat",
]
