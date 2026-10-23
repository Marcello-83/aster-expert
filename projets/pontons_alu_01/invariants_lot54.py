# ruff: noqa: E501 -- en-tête du YAML écrit, lignes de commentaire entières
"""Invariants of `mesh check` for the final PRO geometry of PONTONS-ALU-01 (lot 54),
computed from the parameters of `maillage_ponton_52.py` and `variantes_lot54.yaml` only
(`geometrie_lot54`), before any run: those of lot 52 (`invariants_lot52.invariants`,
group MONTANTS_TRONCONS included) on the geometry of P67 and P68."""

from __future__ import annotations

from pathlib import Path

import yaml

from pontons_alu_01.geometrie_lot51ter import Geometry51ter
from pontons_alu_01.geometrie_lot54 import geometry
from pontons_alu_01.invariants_lot52 import invariants

VERSIONED = Path(__file__).resolve().parent / "maillage" / "invariants_ponton_54.yaml"
HEAD = (
    "# Invariants du maillage du ponton PRO définitif de PONTONS-ALU-01 (lot 54), variante de\n"
    "# référence : calculés par pontons_alu_01.invariants_lot54 à partir des seuls paramètres de\n"
    "# maillage_ponton_52.py et de variantes_lot54.yaml, avant toute exécution. Ne pas éditer\n"
    "# (régénérer : PYTHONPATH=projets .venv/bin/python -m pontons_alu_01.invariants_lot54).\n"
)


def text(g: Geometry51ter) -> str:
    return HEAD + yaml.safe_dump(invariants(g), sort_keys=False, allow_unicode=True)


def main() -> None:
    from pontons_alu_01.variantes_lot54 import reference, variants  # noqa: PLC0415

    g = geometry(variants()[reference()].mesh_overrides)
    VERSIONED.write_text(text(g), encoding="utf-8")
    print(VERSIONED)


if __name__ == "__main__":
    main()


__all__ = ["VERSIONED", "text"]
