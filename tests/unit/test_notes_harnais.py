"""La note de résultats montre le harnais de niveau D et les contrôles désactivés
(lot 46, étape 6)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from docx import Document

from aster_expert.notes.controle import check_results_note, full_text
from aster_expert.notes.resultats import build_results_note
from aster_expert.projet.context import load_project

_REPO = Path(__file__).resolve().parents[2]
_MOTIF = "Résultante non déclarée pour ce cas : contrôle sans objet pour cette dalle."


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    root = tmp_path / "depot"
    shutil.copytree(
        _REPO / "projets" / "dalle_appuyee_01", root / "projets" / "dalle_appuyee_01"
    )
    shutil.copytree(_REPO / "connaissances", root / "connaissances")
    shutil.copytree(
        _REPO / "docs", root / "docs", ignore=shutil.ignore_patterns("audit")
    )
    shutil.copytree(_REPO / "config", root / "config")
    return root


def _write_harness(root: Path, *, disabled: dict[str, str]) -> None:
    path = (
        root
        / "projets"
        / "dalle_appuyee_01"
        / "resultats"
        / "paquet"
        / "controles"
        / "controles_d.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    controls = {
        "CTL-005": {"verdict": "RÉUSSI", "worst_relative_gap": 8.33339678744475e-12},
        "CTL-006": {"verdict": "RÉUSSI", "worst_relative_gap": 5.217306701649408e-13},
        "CTL-012": {"verdict": "RÉUSSI", "worst_finest_error": 0.0005171300778781434},
        "CTL-013": {"verdict": "RÉUSSI", "worst_relative_gap": 0.0},
    }
    for control_id, reason in disabled.items():
        controls[control_id] = {"verdict": "DÉSACTIVÉ", "reason": reason}
    data["harness"] = {"controls": controls, "disabled": disabled}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")


def test_la_note_affiche_le_harnais_et_le_motif_d_un_controle_desactive(
    depot: Path, tmp_path: Path
) -> None:
    _write_harness(depot, disabled={"CTL-013": _MOTIF})
    ctx = load_project("dalle_appuyee_01", depot)
    target = tmp_path / "note.docx"
    build_results_note(ctx, target)
    text = full_text(Document(str(target)))
    assert "Contrôles de niveau D appliqués par défaut" in text
    assert "CTL-013 désactivé par le projet" in text
    assert _MOTIF in text
    assert check_results_note(ctx, target).ok


def test_le_controle_refuse_une_note_qui_tait_un_controle_desactive(
    depot: Path, tmp_path: Path
) -> None:
    ctx = load_project("dalle_appuyee_01", depot)
    target = tmp_path / "note.docx"
    build_results_note(ctx, target)  # paquet sans harnais : la note n'en parle pas
    _write_harness(depot, disabled={"CTL-013": _MOTIF})  # le paquet change ensuite
    check = check_results_note(load_project("dalle_appuyee_01", depot), target)
    assert any("CTL-013 désactivé" in p for p in check.problems)
