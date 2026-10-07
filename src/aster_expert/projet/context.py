"""A loaded project: its declaration, its files, its extensions (lot 41).

`load_project` finds `projets/<name>/projet.yaml` (or a declaration given by
path), validates it and returns a `ProjectContext`; `check_project` confronts
the declaration with the files it names -- fiche, data, mesh invariants,
extensions -- and returns every problem found, as sentences. No project step
runs on a declaration that `check_project` refuses.

A project's code is a Python package, `projets/<name>/`, imported from the
`projets` directory: an extension (`"<module>:<callable>"`) must belong to that
package, so that a declaration can never make the trunk run code from elsewhere.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aster_expert.agent.hypotheses import HypothesesSheet
from aster_expert.agent.model_data import ModelData, load_model_data
from aster_expert.projet.declaration import (
    DECLARATION_NAME,
    DataRef,
    Number,
    ProjectDeclaration,
    load_declaration,
)
from aster_expert.projet.errors import ProjectError

PROJECTS_DIR = "projets"


def available_projects(repo_root: Path) -> list[str]:
    root = repo_root / PROJECTS_DIR
    if not root.is_dir():
        return []
    return sorted(p.parent.name for p in root.glob(f"*/{DECLARATION_NAME}"))


def resolve_project_dir(name_or_path: str, repo_root: Path) -> Path:
    """`<name>`, `projets/<name>` or a path to `projet.yaml`."""
    candidate = Path(name_or_path)
    if candidate.is_file() and candidate.name == DECLARATION_NAME:
        return candidate.resolve().parent
    if candidate.is_dir() and (candidate / DECLARATION_NAME).is_file():
        return candidate.resolve()
    by_name = repo_root / PROJECTS_DIR / name_or_path
    if (by_name / DECLARATION_NAME).is_file():
        return by_name.resolve()
    known = available_projects(repo_root)
    message = (
        f"projet introuvable : {name_or_path} (aucun {DECLARATION_NAME}) ; "
        f"projets déclarés : {', '.join(known) if known else 'aucun'}"
    )
    raise ProjectError(message)


@dataclass
class ProjectContext:
    repo_root: Path
    project_dir: Path
    declaration: ProjectDeclaration
    fiche_override: Path | None = None
    data_override: Path | None = None
    cache: dict[str, Any] = field(default_factory=dict)

    def path(self, relative: str) -> Path:
        return self.project_dir / relative

    @property
    def fiche_path(self) -> Path:
        return self.fiche_override or self.path(self.declaration.fiche)

    @property
    def data_path(self) -> Path:
        return self.data_override or self.path(self.declaration.data)

    @property
    def results_dir(self) -> Path:
        return self.path(self.declaration.results)

    def data(self) -> ModelData:
        if "data" not in self.cache:
            try:
                self.cache["data"] = load_model_data(self.data_path)
            except (OSError, ValueError) as exc:
                message = f"fichier de données illisible : {self.data_path} : {exc}"
                raise ProjectError(message) from exc
        data: ModelData = self.cache["data"]
        return data

    def sheet(self) -> HypothesesSheet:
        """The fiche, with every constat reference resolved against the shared
        base (`aster_expert.constats`)."""
        if "sheet" not in self.cache:
            from aster_expert.constats.base import load_resolved_sheet  # noqa: PLC0415

            try:
                self.cache["sheet"] = load_resolved_sheet(
                    self.fiche_path, repo_root=self.repo_root
                )
            except (OSError, ValueError) as exc:
                message = f"fiche illisible : {self.fiche_path} : {exc}"
                raise ProjectError(message) from exc
        sheet: HypothesesSheet = self.cache["sheet"]
        return sheet

    def waived_revisions(self, step: str) -> tuple[tuple[str, str], ...]:
        """`(point, topic)` of the revisions that do not block `step` (lot 48 bis)."""
        return tuple(
            (scope.point_label, scope.topic)
            for scope in self.declaration.blocker_scopes
            if step not in scope.steps
        )

    def blockers_for(self, step: str) -> tuple[str, ...]:
        """Generation blockers of the fiche and data that concern `step`."""
        return self.sheet().generation_blockers(
            self.data(), waived_revisions=self.waived_revisions(step)
        )

    def waiver_notes(self, step: str) -> list[str]:
        """The revisions `step` waived and why, for the step's report."""
        waived = set(self.waived_revisions(step))
        under_revision = {
            (e.point_label or "?", e.topic)
            for e in self.sheet().entries_under_revision()
        }
        return [
            f"Révision du point {scope.point_label} ({scope.topic}) non bloquante "
            f"pour `{step}` : {scope.reason} (bloque : {', '.join(scope.steps)})."
            for scope in self.declaration.blocker_scopes
            if (scope.point_label, scope.topic) in waived & under_revision
        ]

    def extension(self, reference: str) -> Callable[..., Any]:
        """Import `module:callable` from the project's own package."""
        module_name, _, attribute = reference.partition(":")
        package = self.declaration.name
        if module_name != package and not module_name.startswith(package + "."):
            message = (
                f"extension {reference} : elle doit appartenir au paquet du projet "
                f"({package}), jamais à un autre module"
            )
            raise ProjectError(message)
        projects_root = str(self.project_dir.parent)
        if projects_root not in sys.path:
            sys.path.insert(0, projects_root)
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            message = f"extension {reference} : module introuvable ({exc})"
            raise ProjectError(message) from exc
        function = getattr(module, attribute, None)
        if function is None or not callable(function):
            message = f"extension {reference} : pas de fonction {attribute}"
            raise ProjectError(message)
        return function  # type: ignore[no-any-return]

    def number(self, value: Number, *, unit: str | None = None) -> float:
        """A declared number, or a value of the data file (never converted: the
        unit written in the data must be the one expected)."""
        if not isinstance(value, DataRef):
            return float(value)
        item = self.data().items().get(value.data)
        if item is None:
            message = f"donnée manquante : {value.data} (absente de {self.data_path})"
            raise ProjectError(message)
        if item.status != "fourni" or isinstance(item.value, str | bool):
            message = f"donnée non numérique ou à fournir : {value.data}"
            raise ProjectError(message)
        if unit is not None and item.unit != unit:
            message = (
                f"donnée {value.data} : unité {item.unit!r}, {unit!r} attendue "
                "(aucune conversion n'est faite)"
            )
            raise ProjectError(message)
        assert item.value is not None
        return float(item.value)  # type: ignore[arg-type]


def load_project(
    name_or_path: str,
    repo_root: Path,
    *,
    fiche: Path | None = None,
    data: Path | None = None,
) -> ProjectContext:
    project_dir = resolve_project_dir(name_or_path, repo_root)
    declaration = load_declaration(project_dir / DECLARATION_NAME)
    if declaration.name != project_dir.name:
        message = (
            f"déclaration {project_dir / DECLARATION_NAME} : name={declaration.name!r} "
            f"diffère du répertoire du projet ({project_dir.name!r})"
        )
        raise ProjectError(message)
    return ProjectContext(
        repo_root=repo_root,
        project_dir=project_dir,
        declaration=declaration,
        fiche_override=fiche,
        data_override=data,
    )


__all__ = [
    "PROJECTS_DIR",
    "ProjectContext",
    "available_projects",
    "load_project",
    "resolve_project_dir",
]
