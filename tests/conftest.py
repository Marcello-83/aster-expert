"""Fixtures partagées (lot 41) : un projet factice minimal, écrit dans un dépôt
temporaire, pour éprouver le tronc commun sans le quai (déclaration, refus,
enchaînement des étapes, contrôles D, combinaisons).

Le projet est un paquet Python (`projets/<nom>/__init__.py`) dont le nom est
unique à chaque test : le tronc commun importe ses extensions, et deux projets de
même nom partageraient le cache d'import."""

from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]

_EXTENSIONS = '''
"""Extensions du projet factice des tests du tronc commun."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate(ctx, *, fiche_path, data_path, med_path, aster_version):
    from aster_expert.projet.declaration import DataRef

    longueur = ctx.number(DataRef(data="geometrie.longueur"), unit="m")
    text = f"# généré pour {aster_version}\\nDEBUT()\\n# L = {longueur!r}\\nFIN()\\n"
    return text, {"comm_sha256": "0" * 64, "longueur": longueur}


def resultant(ctx, case, *, comm_path, mesh_path, out_dir):
    values = {"DX": 0.0, "DY": 0.0, "DZ": -100.0}
    return {"as_evaluated": values, "specified": values}


def springs(ctx, mess_text, case, *, comm_text):
    return {"BANDE": 0.0}


def stiffness(ctx, comm_text):
    return {"n_nodes": 0}


def mesh_parameters(ctx):
    return b"{}\\n"


def combinations_report(ctx, result, **context):
    return {"rapport.md": f"{len(result.combinations)} combinaisons\\n"}


def synthesis(ctx, *, result, out_dir, data_path, comm_path=None,
              level_d_path=None, med_path=None, label="", views=True):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "synthese.md").write_text("# Synthèse factice\\n", encoding="utf-8")
    return [f"Synthèse : {out_dir / 'synthese.md'}"]
'''


@dataclass
class FakeProject:
    repo_root: Path
    name: str
    directory: Path

    @property
    def declaration_path(self) -> Path:
        return self.directory / "projet.yaml"

    def declaration(self) -> dict[str, Any]:
        loaded: dict[str, Any] = yaml.safe_load(
            self.declaration_path.read_text(encoding="utf-8")
        )
        return loaded

    def write_declaration(self, data: dict[str, Any]) -> None:
        self.declaration_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )


def _fiche(structure: str) -> dict[str, Any]:
    return {
        "project_name": structure,
        "structure_description": "Barre factice des tests du tronc commun.",
        "created_at": "2026-09-29T00:00:00",
        "entries": [],
        "group_naming": [
            {
                "group_name": "APPUI",
                "kind": "noeud",
                "description": "Nœud d'appui",
                "status": "tranche",
                "point_label": "1",
            }
        ],
    }


def _data(structure: str) -> dict[str, Any]:
    source = {"kind": "cas_test", "document": "description.md", "section": "§1"}
    return {
        "project": structure,
        "case_reference": "Projet factice des tests",
        "groups": {
            "geometrie": {
                "longueur": {
                    "status": "fourni",
                    "value": 2.0,
                    "unit": "m",
                    "source": source,
                },
            },
            "combinaisons": {
                "gamma_q": {
                    "status": "fourni",
                    "value": 1.5,
                    "unit": "-",
                    "source": source,
                },
            },
        },
    }


def _declaration(name: str, structure: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": name,
        "structure": structure,
        "description": "Projet factice des tests du tronc commun.",
        "fiche": "fiche.json",
        "data": "donnees.yaml",
        "data_sources": "sources",
        "results": "resultats",
        "mesh": {"invariants": "invariants.yaml", "med": "maillage.med"},
        "comm": {
            "generator": f"{name}.extensions:generate",
            "output": "resultats/barre.comm",
            "required_data": ["geometrie.longueur"],
        },
        "controls": {
            "total_reactions": {"label": "TOUS", "table": "REAC_TOUS_{case}"},
            "supports": [
                {"group": "APPUI", "blocked": ["DZ"], "table": "REAC_APPUI_{case}"}
            ],
            "springs": {
                "groups": ["BANDE"],
                "direction": "DY",
                "forces": f"{name}.extensions:springs",
                "stiffness_check": f"{name}.extensions:stiffness",
            },
            "cases": [
                {
                    "name": "G",
                    "gravity": True,
                    "expected_resultant": f"{name}.extensions:resultant",
                },
                {
                    "name": "Q",
                    "expected_resultant": {"DX": 0.0, "DY": 0.0, "DZ": -50.0},
                },
            ],
            "symmetry_planes": [
                {"normal": "X", "position": 1.0, "cases": ["G", "Q"]},
            ],
        },
        "combinations": {
            "permanent": ["G"],
            "gamma_g_unfavourable": 1.35,
            "gamma_g_favourable": 1.0,
            "gamma_q": {"data": "combinaisons.gamma_q"},
            "variables": [{"name": "Q", "psi0": 0.7, "psi1": 0.5, "psi2": 0.3}],
            "report": f"{name}.extensions:combinations_report",
        },
        "synthesis": {"extension": f"{name}.extensions:synthesis"},
    }


@pytest.fixture
def fake_project(tmp_path: Path) -> Iterator[Callable[..., FakeProject]]:
    """Factory : `fake_project(**changes)` écrit un projet factice complet (fiche,
    données, invariants, extensions) dans un dépôt temporaire ; `changes`
    remplace des clés de premier niveau de la déclaration."""
    created: list[str] = []

    def make(**changes: Any) -> FakeProject:
        name = f"essai_{uuid.uuid4().hex[:8]}"
        structure = "ESSAI-MIN"
        repo = tmp_path / "depot"
        directory = repo / "projets" / name
        (directory / "sources").mkdir(parents=True)
        (repo / "connaissances" / "constats_code_aster").mkdir(
            parents=True, exist_ok=True
        )
        (directory / "__init__.py").write_text('"""Projet factice."""\n', "utf-8")
        (directory / "extensions.py").write_text(_EXTENSIONS, encoding="utf-8")
        (directory / "fiche.json").write_text(json.dumps(_fiche(structure)), "utf-8")
        (directory / "donnees.yaml").write_text(
            yaml.safe_dump(_data(structure), allow_unicode=True), encoding="utf-8"
        )
        (directory / "invariants.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "groups": [
                        {"name": "APPUI", "kind": "node", "count": 1},
                        {"name": "BARRE", "kind": "cell", "count": 1},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (directory / "maillage.med").write_bytes(b"MED factice")
        (repo / "config").mkdir(exist_ok=True)
        config = repo / "config" / "validation.yaml"
        if not config.is_file():
            config.write_text(
                (_ROOT / "config" / "validation.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        declaration = _declaration(name, structure)
        declaration.update(changes)
        project = FakeProject(repo_root=repo, name=name, directory=directory)
        project.write_declaration(declaration)
        created.append(name)
        return project

    yield make
    for name in created:
        for module in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
            del sys.modules[module]
