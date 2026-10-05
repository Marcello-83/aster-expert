"""Declaration of the knowledge a run applies (lot 46, step 5).

Before lot 46 no execution recorded which entries of the base it applied: CA-045,
PAT-008, PAT-009, CTL-008 and CTL-010 served in the slab and became ineligible at
lot 44 because nothing could show it. Every run of a *project* now declares them.

Form retained: a **companion file** next to the `.comm`, `<stem>.connaissances.yaml`,
copied by `execute_comm_file` into `compte_rendu.json` (`knowledge`). Not a header
block of the `.comm`, because the `.comm` of a project is generated and compared byte
for byte (regeneration check, level conservation rule of lot 45): a declaration inside
it would change the file Code_Aster runs for a statement that is not part of the
calculation; and a companion is read, validated and refused *before* the container is
launched, whatever the generator wrote. A run of a project without it is refused; a
run outside any project (`data/examples/...`, official test cases) may declare, never
has to.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

COMPANION_SUFFIX = ".connaissances.yaml"


class DeclarationError(ValueError):
    """The declaration is missing, unreadable or names an unknown entry."""


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AppliedEntry(_Model):
    id: str
    """Identifier in the base (`CA-nnn`, `DIAG-nnn`, `PAT-nnn`, `CTL-nnn`, `REF-nnn`,
    `PRE-nnn`)."""
    how: str
    """What the run applies of it, in a sentence (never empty)."""
    corrected_defect: str | None = None
    """For a control that failed on a real defect later corrected: the defect. Not a
    proof by itself (see `connaissances.epreuve`)."""

    @field_validator("how")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            message = "une entrée appliquée dit ce qui en est appliqué (`how`)"
            raise ValueError(message)
        return value


class KnowledgeDeclaration(_Model):
    """The companion file."""

    schema_version: Literal[1]
    project: str
    applied: tuple[AppliedEntry, ...] = ()
    none_reason: str | None = None
    """An empty list is a statement: why this run applies nothing from the base."""

    @field_validator("applied")
    @classmethod
    def _unique(cls, value: tuple[AppliedEntry, ...]) -> tuple[AppliedEntry, ...]:
        ids = [e.id for e in value]
        if len(ids) != len(set(ids)):
            message = "une entrée déclarée deux fois"
            raise ValueError(message)
        return value


class AppliedKnowledge(_Model):
    """What `compte_rendu.json` holds of the declaration."""

    file: str
    """Companion file, relative to the repository when it lies inside."""
    sha256: str
    project: str
    applied: tuple[AppliedEntry, ...] = Field(default=())
    none_reason: str | None = None


def companion_path(comm: Path) -> Path:
    return comm.with_name(comm.stem + COMPANION_SUFFIX)


def project_of(comm: Path, repo_root: Path) -> str | None:
    """The project a `.comm` belongs to: it lies under `projets/<nom>/` and that
    folder holds a `projet.yaml`."""
    try:
        relative = comm.resolve().relative_to((repo_root / "projets").resolve())
    except ValueError:
        return None
    if not relative.parts:
        return None
    name = relative.parts[0]
    return name if (repo_root / "projets" / name / "projet.yaml").is_file() else None


def parse_declaration(path: Path) -> KnowledgeDeclaration:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return KnowledgeDeclaration.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        message = f"{path.name} : déclaration illisible ({exc})"
        raise DeclarationError(message) from exc


def load_for_run(
    comm: Path, repo_root: Path, known_ids: set[str]
) -> AppliedKnowledge | None:
    """The declaration of a run, validated, or None for a run outside any project
    that declares nothing. Raises `DeclarationError` (the run must not start)."""
    project = project_of(comm, repo_root)
    path = companion_path(comm)
    if not path.is_file():
        if project is None:
            return None
        message = (
            f"exécution du projet {project} sans déclaration des connaissances "
            f"appliquées : écrire {path.name} à côté du .comm (schéma "
            "aster_expert.connaissances.declaration, skill code-aster-expert § 6 "
            "quinquies). Une exécution de projet ne part pas sans elle (lot 46)."
        )
        raise DeclarationError(message)
    declaration = parse_declaration(path)
    if project is not None and declaration.project != project:
        message = (
            f"{path.name} : déclaration du projet {declaration.project}, exécution "
            f"du projet {project}"
        )
        raise DeclarationError(message)
    if not declaration.applied and not (declaration.none_reason or "").strip():
        message = (
            f"{path.name} : aucune entrée déclarée et aucun motif (`none_reason`) : "
            "dire pourquoi l'exécution n'applique rien de la base"
        )
        raise DeclarationError(message)
    unknown = sorted(e.id for e in declaration.applied if e.id not in known_ids)
    if unknown:
        message = (
            f"{path.name} : entrée(s) absente(s) de la base : {', '.join(unknown)}"
        )
        raise DeclarationError(message)
    try:
        shown = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        shown = str(path)
    return AppliedKnowledge(
        file=shown,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        project=declaration.project,
        applied=declaration.applied,
        none_reason=declaration.none_reason,
    )


__all__ = [
    "COMPANION_SUFFIX",
    "AppliedEntry",
    "AppliedKnowledge",
    "DeclarationError",
    "KnowledgeDeclaration",
    "companion_path",
    "load_for_run",
    "parse_declaration",
    "project_of",
]
