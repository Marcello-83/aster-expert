"""Paramètres et invariants du quai réduit à maillage raffiné ×2 (lot 37, C10).

Même mécanisme que `projets/quai_cw_test_01/scripts/build_lot30_quai_reduit.py`, à partir de
`data/examples/lot37_efforts/quai_reduit_fin/model_data.yaml` (taille verticale visée
0,125 m au lieu de 0,25 m) : les comptages sont calculés analytiquement, avant toute
exécution de Salomé, jamais relus d'un MED.

Produit, dans `data/examples/lot37_efforts/quai_reduit_fin/` : `params.json`
(paramètres du script Salomé `projets/quai_cw_test_01/maillage/combiwall_mesh.py`), `invariants.yaml`
(invariants de `aster-expert mesh check`) et `segments_attendus.json`.

Usage : python projets/quai_cw_test_01/scripts/build_lot37_maillage_fin.py
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from aster_expert.agent.model_data import load_model_data
from quai_cw_test_01.meshing.combiwall import (
    build_params,
    expected_invariants,
    expected_segments,
    layer_interface_levels,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "examples" / "lot37_efforts" / "quai_reduit_fin"
DATA_PATH = OUT / "model_data.yaml"


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _yaml_flow(data: dict[str, Any]) -> str:
    header = (
        "# Invariants du maillage du quai réduit raffiné ×2 (lot 37, C10).\n"
        "#\n"
        "# Produit par projets/quai_cw_test_01/scripts/build_lot37_maillage_fin.py, à partir de\n"
        "# data/examples/lot37_efforts/quai_reduit_fin/model_data.yaml et du module\n"
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
        OUT / "invariants.yaml": _yaml_flow(
            expected_invariants(params, layer_interface_levels(data))
        ),
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
