"""Paramètres et invariants du « quai réduit » (lot 30, étape 2).

Même mécanisme que `scripts/build_lot27_maillage.py`, à partir de
`data/examples/lot30_quai_reduit/model_data_reduit.yaml` (deux entraxes au
lieu de huit) : les comptages sont calculés analytiquement, avant toute
exécution de Salomé, jamais relus d'un MED.

Produit :

* `data/examples/lot30_quai_reduit/params.json` : paramètres du script Salomé
  `scripts/salome/combiwall_mesh.py` ;
* `data/examples/lot30_quai_reduit/invariants.yaml` : invariants de
  `aster-expert mesh check` ;
* `data/examples/lot30_quai_reduit/segments_attendus.json` : nombre de
  segments imposé par type d'arête.

Usage : python scripts/build_lot30_quai_reduit.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from aster_expert.agent.model_data import load_model_data
from aster_expert.meshing.combiwall import (
    build_params,
    expected_invariants,
    expected_segments,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "examples"
DATA_PATH = EXAMPLES / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT = EXAMPLES / "lot30_quai_reduit"
INVARIANTS_PATH = OUT / "invariants.yaml"


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _yaml_flow(data: dict[str, Any]) -> str:
    header = (
        "# Invariants du maillage du quai réduit (lot 30, étape 2).\n"
        "#\n"
        "# Produit par scripts/build_lot30_quai_reduit.py, à partir de\n"
        "# data/examples/lot30_quai_reduit/model_data_reduit.yaml et du module\n"
        "# analytique aster_expert.meshing.combiwall : les comptages sont calculés\n"
        "# AVANT toute exécution de Salomé, jamais relus d'un MED. Ne pas éditer à\n"
        "# la main.\n"
    )
    return header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def files() -> dict[Path, str]:
    data = load_model_data(DATA_PATH)
    params = build_params(data)
    return {
        OUT / "params.json": _json(params),
        INVARIANTS_PATH: _yaml_flow(expected_invariants(params)),
        OUT / "segments_attendus.json": _json(expected_segments(params)),
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    for path, content in files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
