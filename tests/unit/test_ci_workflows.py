"""Workflows GitHub Actions (lot 46, étape 2) : cohérence avec le dépôt.

Ils ne s'exécutent que sur GitHub : ces tests vérifient ce qui se vérifie ici
(YAML valide, déclencheurs, version de uv, absence de tests lents au premier)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOWS = _REPO / ".github" / "workflows"


def _load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((_WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # YAML 1.1 lit `on` comme le booléen True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def _steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for job in workflow["jobs"].values() for s in job["steps"]]


def _commands(workflow: dict[str, Any]) -> str:
    return "\n".join(s.get("run", "") for s in _steps(workflow))


def test_ci_se_declenche_sur_pull_request_et_branches_de_lot() -> None:
    triggers = _load("ci.yml")["on"]
    assert "pull_request" in triggers
    assert "lot-*" in triggers["push"]["branches"]
    assert "workflow_dispatch" not in triggers


def test_ci_lance_les_controles_demandes() -> None:
    commandes = _commands(_load("ci.yml"))
    for attendu in (
        "uv sync --locked --all-extras",
        "ruff format --check",
        "ruff check",
        "mypy src",
        ".venv/bin/mypy\n",
        ".venv/bin/pytest\n",
        "aster_expert.publication --arbre",
        "pip-audit",
    ):
        assert attendu in commandes + "\n", attendu
    assert "-m lent" not in commandes


def test_audit_des_dependances_ne_bloque_pas() -> None:
    audit = [s for s in _steps(_load("ci.yml")) if "pip-audit" in s.get("run", "")]
    assert audit
    assert all(s.get("continue-on-error") is True for s in audit)


def test_ci_lent_est_a_la_demande_seulement() -> None:
    workflow = _load("ci-lent.yml")
    assert set(workflow["on"]) == {"workflow_dispatch"}
    commandes = _commands(workflow)
    assert "pytest -m lent_aster" in commandes
    assert "lent_salome" not in commandes
    assert "config/versions.yaml" in commandes  # image tirée par digest


def test_version_de_uv_identique_a_celle_du_script_cloud() -> None:
    script = (_REPO / "scripts" / "cloud_setup.sh").read_text(encoding="utf-8")
    attendue = re.search(r'^UV_VERSION="([^"]+)"', script, re.MULTILINE)
    assert attendue
    for nom in ("ci.yml", "ci-lent.yml"):
        setup = [
            s
            for s in _steps(_load(nom))
            if str(s.get("uses", "")).startswith("astral-sh/setup-uv")
        ]
        assert [s["with"]["version"] for s in setup] == [attendue.group(1)]
