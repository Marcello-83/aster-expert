"""Birth of a project in one command: `aster-expert projet creer <nom>` (lot 44).

At lot 43 the second project had to be set up by hand: its execution roots in
`config/validation.yaml` (the run was refused without them) and its registry
`connaissances/rex/<nom>.yaml` (`rex` refused without it). `create_project`
writes, at once:

- the tree `projets/<nom>/` (Python package, `fiche/`, `donnees/sources/`,
  `maillage/`, `scripts/`, `tests/`, `references/cas/`), with a `LISEZMOI.md`;
- a minimal `projet.yaml` that the schema accepts (`load_declaration`): fiche and
  data skeletons that exist, a mesh invariants file and a generator still to
  write -- `aster-expert projet <nom> verifier` lists exactly what is missing;
- the two execution roots of the project (`resultats`, `references/cas`) in
  `config/validation.yaml`, inserted as text so that comments are kept;
- the `rex` registry (`project`, `case_roots`).

Never overwrites anything: an existing project directory or registry is refused.
The project code itself (generator, mesh script, invariants) is the project
session's work, as before.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from aster_expert.agent.hypotheses import HypothesesSheet
from aster_expert.connaissances.archive import build_manifest
from aster_expert.connaissances.rex import RexRegistry, registry_path, write_registry
from aster_expert.projet.context import PROJECTS_DIR
from aster_expert.projet.declaration import DECLARATION_NAME, load_declaration
from aster_expert.projet.errors import ProjectError

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
VALIDATION_CONFIG = Path("config") / "validation.yaml"
_SUBDIRS = (
    "fiche",
    "donnees/sources",
    "maillage",
    "scripts",
    "tests",
    "references/cas",
)


@dataclass(frozen=True)
class CreatedProject:
    name: str
    project_dir: Path
    files: tuple[Path, ...]
    roots_added: tuple[str, ...]
    registry: Path


def structure_identifier(name: str) -> str:
    """`mon_ouvrage_01` -> `MON-OUVRAGE-01`."""
    return name.upper().replace("_", "-")


def execution_roots(name: str) -> tuple[str, str]:
    return (
        f"{PROJECTS_DIR}/{name}/resultats",
        f"{PROJECTS_DIR}/{name}/references/cas",
    )


def _declaration(name: str, description: str) -> str:
    structure = structure_identifier(name)
    return f"""\
# Déclaration du projet {structure} (créée par `aster-expert projet creer`).
#
# Interface avec le tronc commun (schéma aster_expert.projet.declaration). Squelette
# minimal : la fiche et les données existent (vides) ; les invariants du maillage et
# le générateur restent à écrire par la session du projet. `aster-expert projet
# {name} verifier` liste ce qui manque. Chemins relatifs au répertoire du projet.
schema_version: 1
name: {name}
structure: {structure}
description: >-
  {description}
fiche: fiche/hypotheses_{name}.json
data: donnees/{name}_model_data.yaml
data_sources: donnees/sources
results: resultats
knowledge_applied: connaissances_appliquees.yaml

mesh:
  invariants: maillage/invariants.yaml

comm:
  generator: {name}.extensions:generate
  output: resultats/{name}.comm

# Lot 49 : contrat de livrables, obligatoire (`verifier` refuse un projet sans lui) :
# champs livrés par famille d'éléments, combinaisons, enveloppes, et chaque livrable
# non pertinent avec son motif (aster_expert.projet.declaration.DeliverablesSection).
# deliverables:
#   fields:
#     - {{family: deplacements, field: DEPL, components: [DX, DY, DZ],
#        convention: "..."}}
#   not_relevant:
#     - {{item: ressorts, reason: "..."}}
#   combinations: declarees
"""


_EXTENSIONS = '''\
"""Extensions of the project declared in `projet.yaml` (to write)."""

from __future__ import annotations

from typing import Any


def generate(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
    """`.comm` generator of the project: not written yet."""
    message = "générateur du projet à écrire (projets/{name}/extensions.py)"
    raise NotImplementedError(message)
'''


def _readme(name: str, description: str) -> str:
    return f"""\
# Projet {structure_identifier(name)}

{description}

Créé par `aster-expert projet creer {name}` : arborescence, `projet.yaml` minimal,
racines d'exécution (`config/validation.yaml`) et registre `rex`
(`connaissances/rex/{name}.yaml`). Tout le reste est à écrire.

| Répertoire | Contenu |
| --- | --- |
| `fiche/` | fiche d'hypothèses (skill `hypotheses-drafting`) et document d'arbitrage |
| `donnees/` | données du modèle et leurs sources recopiées à l'identique |
| `maillage/` | script Salomé et invariants (calculés analytiquement avant exécution) |
| `extensions.py` | générateur du `.comm` et extensions déclarées |
| `scripts/`, `tests/` | scripts de lot et tests propres au projet |
| `references/cas/` | cas versionnés rejouables (constats, références de validation) |
| `resultats/` | sorties de `aster-expert projet {name} <étape>` (non versionné) |
"""


def add_execution_roots(
    repo_root: Path, roots: tuple[str, ...], name: str
) -> tuple[str, ...]:
    """Insert `roots` at the end of `execution.allowed_roots`, keeping the file's
    comments. Idempotent: a root already listed is not added twice."""
    path = repo_root / VALIDATION_CONFIG
    text = path.read_text(encoding="utf-8")
    config = yaml.safe_load(text) or {}
    present = set(config.get("execution", {}).get("allowed_roots", []) or [])
    to_add = tuple(r for r in roots if r not in present)
    if not to_add:
        return ()
    lines = text.splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "allowed_roots:"), None
    )
    if start is None:
        message = f"{VALIDATION_CONFIG} : section execution.allowed_roots introuvable"
        raise ProjectError(message)
    indent = len(lines[start]) - len(lines[start].lstrip()) + 2
    end = start + 1
    while end < len(lines):
        stripped = lines[end].strip()
        current = len(lines[end]) - len(lines[end].lstrip())
        if stripped and current < indent:
            break
        end += 1
    pad = " " * indent
    block = [f"{pad}# Projet {name} (aster-expert projet creer, lot 44).\n"]
    block += [f"{pad}- {r}\n" for r in to_add]
    lines[end:end] = block
    path.write_text("".join(lines), encoding="utf-8")
    check = yaml.safe_load(path.read_text(encoding="utf-8"))
    listed = check["execution"]["allowed_roots"]
    if any(r not in listed for r in to_add):  # pragma: no cover - garde-fou
        message = f"{VALIDATION_CONFIG} : insertion des racines non relue"
        raise ProjectError(message)
    return to_add


def create_project(
    repo_root: Path,
    name: str,
    *,
    description: str = "Ouvrage à décrire.",
    now: datetime | None = None,
) -> CreatedProject:
    """Create the project `name` (see the module docstring)."""
    if not _NAME.match(name):
        message = (
            f"nom de projet {name!r} refusé : minuscules, chiffres et `_`, "
            "commençant par une lettre (c'est aussi le nom du paquet Python)"
        )
        raise ProjectError(message)
    project_dir = repo_root / PROJECTS_DIR / name
    if project_dir.exists():
        message = f"le projet existe déjà : {project_dir}"
        raise ProjectError(message)
    if registry_path(repo_root, name).exists():
        message = f"registre rex déjà présent : {registry_path(repo_root, name)}"
        raise ProjectError(message)
    created_at = now or datetime.now().astimezone()
    files: list[Path] = []

    def write(relative: str, text: str) -> None:
        path = project_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        files.append(path)

    for sub in _SUBDIRS:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
    write("__init__.py", f'"""Projet {structure_identifier(name)}."""\n')
    write("tests/__init__.py", "")
    write("references/cas/.gitkeep", "")
    write("maillage/.gitkeep", "")
    write("scripts/.gitkeep", "")
    write("donnees/sources/.gitkeep", "")
    write("extensions.py", _EXTENSIONS.replace("{name}", name))
    write("LISEZMOI.md", _readme(name, description))
    sheet = HypothesesSheet(
        project_name=structure_identifier(name),
        structure_description=description,
        created_at=created_at,
    )
    write(
        f"fiche/hypotheses_{name}.json",
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
    )
    write(
        f"donnees/{name}_model_data.yaml",
        "# Données chiffrées du modèle (schéma aster_expert.agent.model_data).\n"
        f"project: {structure_identifier(name)}\n"
        f'case_reference: "à renseigner"\n'
        "groups: {}\n",
    )
    write(
        "connaissances_appliquees.yaml",
        "# Connaissances de la base appliquées par les exécutions du projet (lot 46).\n"
        "# À remplir AVANT la première exécution : une exécution de projet sans\n"
        "# entrée déclarée (ni `none_reason` motivé) est refusée. Schéma :\n"
        "# aster_expert.connaissances.declaration.\n"
        "schema_version: 1\n"
        f"project: {name}\n"
        "applied: []\n",
    )
    write(DECLARATION_NAME, _declaration(name, description))
    load_declaration(project_dir / DECLARATION_NAME)
    roots = add_execution_roots(repo_root, execution_roots(name), name)
    registry = write_registry(
        repo_root,
        RexRegistry(
            project=name,
            case_roots=(f"{PROJECTS_DIR}/{name}",),
            declaration_required_since=created_at.replace(tzinfo=None),
            # Un projet neuf n'a aucune exécution : son archive complète est vide.
            archive=build_manifest([], today=created_at.date()),
        ),
    )
    return CreatedProject(
        name=name,
        project_dir=project_dir,
        files=tuple(files),
        roots_added=roots,
        registry=registry,
    )


__all__ = [
    "CreatedProject",
    "add_execution_roots",
    "create_project",
    "execution_roots",
    "structure_identifier",
]
