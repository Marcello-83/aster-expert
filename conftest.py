"""Fixtures communes à `tests/` et à `projets/*/tests/` (lot 46)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert import chemins


@pytest.fixture
def lecture_sous_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fait de `tmp_path` une racine de lecture pour les commandes `aster-expert`.

    Les tests qui passent à une commande un fichier écrit sous `tmp_path` le
    demandent ; la politique réelle est éprouvée par `tests/unit/test_chemins.py`."""
    politique = chemins.PathPolicy(
        "lecture", (tmp_path.resolve(), Path(__file__).resolve().parent), ""
    )
    monkeypatch.setattr(chemins, "load_read_policy", lambda _root: politique)
    return tmp_path
