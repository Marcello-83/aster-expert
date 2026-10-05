"""Extensions of the project declared in `projet.yaml` (to write)."""

from __future__ import annotations

from typing import Any


def generate(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
    """`.comm` generator of the project: not written yet."""
    message = "générateur du projet à écrire (projets/estacade_pieux_01/extensions.py)"
    raise NotImplementedError(message)
