# ruff: noqa: E501 -- en-tête du YAML écrit, lignes de commentaire entières
"""Invariants of `mesh check` for the PRO geometry of PONTONS-ALU-01 (lot 52), computed
from the parameters of `maillage_ponton_52.py` only (`geometrie_lot52`), before any run:
those of lot 51 ter (`invariants_lot51ter.invariants`: counts, families, bars, footings,
berthing zones, ring corners, link, pin and cleat groups, nodes at their points) plus the
group MONTANTS_TRONCONS (pieces of post between a main beam and the diagonal node,
P64), a subset of MONTANTS. The links LM_ (post / main beam, 0,01 m) and the new LR_
(purlin / post or diagonal, 0,085 m) are checked as every link group: one node at its
point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pontons_alu_01.geometrie_lot51ter import Geometry51ter
from pontons_alu_01.geometrie_lot52 import TRONCONS, geometry, post_pieces
from pontons_alu_01.invariants_lot51 import TOL, _bbox
from pontons_alu_01.invariants_lot51ter import invariants as invariants_51ter

VERSIONED = Path(__file__).resolve().parent / "maillage" / "invariants_ponton_52.yaml"
HEAD = (
    "# Invariants du maillage du ponton PRO de PONTONS-ALU-01 (lot 52), variante de référence :\n"
    "# calculés par pontons_alu_01.invariants_lot52 à partir des seuls paramètres de\n"
    "# maillage_ponton_52.py et de variantes_lot52.yaml, avant toute exécution. Ne pas éditer\n"
    "# (régénérer : PYTHONPATH=projets .venv/bin/python -m pontons_alu_01.invariants_lot52).\n"
)


def invariants(g: Geometry51ter) -> dict[str, Any]:
    out = invariants_51ter(g)
    pieces = post_pieces(g)
    out["groups"].append(
        {
            "name": TRONCONS,
            "kind": "cell",
            "count": sum(n for *_, n in pieces),
            "cell_type": "SEG2",
            "bbox": _bbox([q for _, a, b, _ in pieces for q in (a, b)]),
            "tolerance": TOL,
        }
    )
    out["subsets"].append({"group": TRONCONS, "of": "MONTANTS"})
    return out


def text(g: Geometry51ter) -> str:
    return HEAD + yaml.safe_dump(invariants(g), sort_keys=False, allow_unicode=True)


def main() -> None:
    from pontons_alu_01.variantes_lot52 import reference, variants  # noqa: PLC0415

    g = geometry(variants()[reference()].mesh_overrides)
    VERSIONED.write_text(text(g), encoding="utf-8")
    print(VERSIONED)


if __name__ == "__main__":
    main()


__all__ = ["VERSIONED", "invariants", "text"]
