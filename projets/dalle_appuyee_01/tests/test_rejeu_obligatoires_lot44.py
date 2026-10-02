"""Rejeu de la détection des paramètres obligatoires sur la phase 1 du lot 43."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _ROOT / "projets" / "dalle_appuyee_01" / "scripts"
_CATALOGUE = (
    _ROOT
    / "data"
    / "processed"
    / "catalogue"
    / "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
    / "CALC_FERRAILLAGE.json"
)

pytestmark = pytest.mark.skipif(
    not _CATALOGUE.is_file(), reason="catalogue extrait absent (data/processed)"
)


@pytest.fixture(scope="module")
def rejeu() -> ModuleType:
    sys.path.insert(0, str(_SCRIPTS))
    name = "rejeu_obligatoires_lot44"
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_four_els_parameters_of_lot_43_are_found(rejeu: ModuleType) -> None:
    found = rejeu.summary()["parametres_els_lot43"]
    assert all(found[name] for name in ("σc", "αe", "KT", "Es"))
    assert found["Es"] == ["AFFE.EYS"]


def test_versioned_summary_is_reproduced(rejeu: ModuleType) -> None:
    text = json.dumps(rejeu.summary(), ensure_ascii=False, indent=2) + "\n"
    assert rejeu.SUMMARY.read_text(encoding="utf-8") == text


def test_cli_lists_and_adds_the_missing_parameters(
    rejeu: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner  # noqa: PLC0415

    from aster_expert.cli import app  # noqa: PLC0415

    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(_ROOT))
    fiche = tmp_path / "fiche.json"
    fiche.write_text(json.dumps(rejeu.planned_sheet().model_dump(mode="json")))
    out = tmp_path / "complete.json"
    result = CliRunner().invoke(
        app,
        [
            "fiche",
            "obligatoires",
            str(fiche),
            "--donnees",
            str(rejeu.DATA),
            "--sortie",
            str(out),
        ],
    )
    assert result.exit_code == 1, result.output
    assert "MANQUE CALC_FERRAILLAGE/AFFE.KT" in result.output
    assert "11 question(s) ajoutée(s)" in result.output
    assert out.is_file()
