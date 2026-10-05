"""Machine-readable project state, `docs/etat.yaml` (lot 46).

The file is the single source of the project's own traceability: lots (object,
state, merge commit), capabilities (level and proof), projects (level reached)
and links to the metrics. The README section "État du projet" is generated from
it (`render_readme_section`); `check_readme` and `check_references` are what the
tests and `aster-expert etat verifier` run.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

STATE_FILE = Path("docs") / "etat.yaml"
README = Path("README.md")
BEGIN = (
    "<!-- etat:debut (généré depuis docs/etat.yaml par `aster-expert etat readme`) -->"
)
END = "<!-- etat:fin -->"

LotState = Literal["fait", "partiel", "non_fait", "en_cours"]
CapabilityState = Literal["operationnelle", "partielle", "a_confirmer"]
Level = Literal["A", "B", "C", "D", "E"]


class StateError(Exception):
    """The state file or the README is missing or inconsistent."""


class Lot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    objet: str
    etat: LotState
    commit: str | None
    date: str | None = None
    commits_suivants: tuple[str, ...] = ()
    note: str | None = None


class Capacite(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nom: str
    niveau: Level | None
    etat: CapabilityState
    fichiers: tuple[str, ...]
    commandes: tuple[str, ...]
    limites: str


class Projet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nom: str
    ouvrage: str
    niveau_atteint: Level
    preuve: str
    limites: str


class Metrique(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    libelle: str
    fichier: str


class Etat(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    mis_a_jour_au_lot: str
    date: str
    lots: tuple[Lot, ...]
    capacites: tuple[Capacite, ...]
    projets: tuple[Projet, ...]
    metriques: tuple[Metrique, ...] = Field(default=())


def load_state(project_root: Path) -> Etat:
    path = project_root / STATE_FILE
    if not path.is_file():
        message = f"état du projet introuvable : {path}"
        raise StateError(message)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Etat.model_validate(_dates_as_text(raw))


def _dates_as_text(value: object) -> object:
    """PyYAML reads a bare date as `datetime.date`: the schema wants text."""
    if isinstance(value, dict):
        return {k: _dates_as_text(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dates_as_text(v) for v in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


_CAP_LABEL = {
    "operationnelle": "opérationnelle",
    "partielle": "partielle",
    "a_confirmer": "à confirmer",
}


def render_readme_section(state: Etat) -> str:
    """The README block between the markers, markers included, ending with a newline."""
    lots_faits = [lot for lot in state.lots if lot.etat == "fait"]
    autres = [lot for lot in state.lots if lot.etat != "fait"]
    lines = [
        BEGIN,
        "## État du projet",
        "",
        f"Mis à jour au lot {state.mis_a_jour_au_lot} ({state.date}), depuis "
        f"`{STATE_FILE.as_posix()}` : ne pas éditer cette section à la main.",
        "",
        f"Lots : {len(lots_faits)} faits sur {len(state.lots)}"
        + (
            " ; autres : "
            + ", ".join(f"{lot.id} ({lot.etat.replace('_', ' ')})" for lot in autres)
            if autres
            else ""
        )
        + ". Dernier lot : "
        f"{state.lots[-1].id}, {state.lots[-1].objet}.",
        "",
        "Capacités :",
        "",
    ]
    for cap in state.capacites:
        niveau = f"niveau {cap.niveau}" if cap.niveau else "sans niveau de validation"
        lines.append(f"- {cap.nom} : {niveau}, {_CAP_LABEL[cap.etat]}. {cap.limites}")
    lines += ["", "Projets :", ""]
    for projet in state.projets:
        lines.append(
            f"- `{projet.nom}` ({projet.ouvrage}) : niveau {projet.niveau_atteint} "
            f"atteint, preuve `{projet.preuve}`."
        )
    lines += ["", "Métriques :", ""]
    lines += [f"- {m.libelle} : `{m.fichier}`" for m in state.metriques]
    lines += ["", END, ""]
    return "\n".join(lines)


def _split_readme(text: str) -> tuple[str, str, str]:
    start = text.find(BEGIN)
    end = text.find(END)
    if start < 0 or end < start:
        message = (
            f"README.md : marqueurs de la section d'état absents ({BEGIN} ... {END})"
        )
        raise StateError(message)
    after = end + len(END)
    if text[after : after + 1] == "\n":
        after += 1
    return text[:start], text[start:after], text[after:]


def update_readme(project_root: Path) -> bool:
    """Rewrite the README section. True when the file changed."""
    path = project_root / README
    text = path.read_text(encoding="utf-8")
    before, _old, after = _split_readme(text)
    new = before + render_readme_section(load_state(project_root)) + after
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def check_readme(project_root: Path) -> list[str]:
    """Reasons the README section differs from the state file (empty when equal)."""
    text = (project_root / README).read_text(encoding="utf-8")
    _before, current, _after = _split_readme(text)
    if current != render_readme_section(load_state(project_root)):
        return [
            "la section « État du projet » du README diverge de docs/etat.yaml : "
            "lancer `aster-expert etat readme`"
        ]
    return []


def _is_shallow(project_root: Path) -> bool:
    out = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip() != "false"


def check_references(project_root: Path, *, check_commits: bool = True) -> list[str]:
    """Missing proof files and unknown commits (commits skipped if shallow)."""
    state = load_state(project_root)
    problems: list[str] = []
    paths = [f for c in state.capacites for f in c.fichiers]
    paths += [p.preuve for p in state.projets] + [m.fichier for m in state.metriques]
    problems += [
        f"fichier cité absent : {p}" for p in paths if not (project_root / p).exists()
    ]
    ids = [lot.id for lot in state.lots]
    problems += [
        f"lot en double : {i}" for i in sorted({i for i in ids if ids.count(i) > 1})
    ]
    if check_commits and not _is_shallow(project_root):
        for lot in state.lots:
            for commit in (
                *([lot.commit] if lot.commit else []),
                *lot.commits_suivants,
            ):
                known = subprocess.run(
                    ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                    cwd=project_root,
                    capture_output=True,
                    check=False,
                )
                if known.returncode != 0:
                    problems.append(
                        f"lot {lot.id} : commit {commit} inconnu de l'historique"
                    )
    return problems


__all__ = [
    "Etat",
    "StateError",
    "check_readme",
    "check_references",
    "load_state",
    "render_readme_section",
    "update_readme",
]
