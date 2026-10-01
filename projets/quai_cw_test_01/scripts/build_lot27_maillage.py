"""Parameters, invariants and reading case of the quay mesh (lot 27).

Everything here is produced **before** any Salome run, from the numerical data of the
model (`projets/quai_cw_test_01/donnees/combiwall_model_data.yaml`) and the analytic module
`quai_cw_test_01.meshing.combiwall`: the expected values are computed, never read back
from a MED file.

Produces:

* `data/examples/lot27_maillage/params.json` : the parameters of the Salome script
  `projets/quai_cw_test_01/maillage/combiwall_mesh.py`;
* `projets/quai_cw_test_01/maillage/combiwall_mesh_invariants.yaml` : the invariants of
  `aster-expert mesh check`;
* `data/examples/lot27_maillage/segments_attendus.json` : the number of segments
  imposed per type of edge (the mesh report compares it with the script's);
* `data/examples/lot27_maillage/aster/lot27_lecture.{comm,export}` and
  `aster_expected.json` : the trivial Code_Aster reading (masses of the groups with
  `RHO = 1`, `EPAIS = 1`, `A = 1`) and its expected values.

Usage: python projets/quai_cw_test_01/scripts/build_lot27_maillage.py
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
    expected_masses,
    expected_segments,
    layer_interface_levels,
)

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "data" / "examples"
PROJECT = ROOT / "projets" / "quai_cw_test_01"
DATA_PATH = PROJECT / "donnees" / "combiwall_model_data.yaml"
OUT = EXAMPLES / "lot27_maillage"
INVARIANTS_PATH = PROJECT / "maillage" / "combiwall_mesh_invariants.yaml"


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _yaml_flow(data: dict[str, Any]) -> str:
    header = (
        "# Invariants du maillage du quai QUAI-CW-TEST-01 (lot 27).\n"
        "#\n"
        "# Produit par projets/quai_cw_test_01/scripts/build_lot27_maillage.py, à partir de\n"
        "# projets/quai_cw_test_01/donnees/combiwall_model_data.yaml et du module analytique\n"
        "# aster_expert.meshing.combiwall : les comptages sont calculés AVANT toute\n"
        "# exécution de Salomé, jamais relus d'un MED. Ne pas éditer à la main.\n"
    )
    return header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def aster_comm(masses: dict[str, dict[str, Any]]) -> str:
    def tup(names: list[str]) -> str:
        return "(" + ", ".join(f'"{n}"' for n in names) + ",)"

    every = list(masses)
    # The model holds the union groups only: a cell must not be assigned twice.
    bars = ["TIRANTS"]
    beams = [g for g in every if masses[g]["kind"] == "beam"]
    shells = ["TUBES", "PALPS"]
    mass = ",\n        ".join(f'_F(GROUP_MA="{g}")' for g in every)
    return f"""\
# Lot 27 -- lecture par Code_Aster du MED du quai (critere dans docs/essais_lot27.md,
# ecrit avant l'execution). RHO = 1, EPAIS = 1, A = 1 : la masse d'un groupe est son
# aire developpee (coque, facettisation incluse) ou sa longueur (barre, poutre).
# Ce calcul n'est pas le .comm du quai (lot 28).

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20, INFO=2)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        _F(GROUP_MA={tup(shells)}, PHENOMENE="MECANIQUE", MODELISATION="DKT"),
        _F(GROUP_MA={tup(bars)}, PHENOMENE="MECANIQUE", MODELISATION="BARRE"),
        _F(GROUP_MA={tup(beams)}, PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"),
    ),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=_F(GROUP_MA={tup(shells)}, EPAIS=1.0),
    BARRE=_F(GROUP_MA={tup(bars)}, SECTION="GENERALE", CARA="A", VALE=1.0),
    POUTRE=_F(
        GROUP_MA={tup(beams)},
        SECTION="GENERALE",
        CARA=("A", "IY", "IZ", "JX"),
        VALE=(1.0, 1.0, 1.0, 1.0),
    ),
)

MAT = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3, RHO=1.0))

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=_F(GROUP_MA={tup(shells + bars + beams)}, MATER=MAT),
)

MASSE = POST_ELEM(
    MODELE=MO,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    MASS_INER=(
        {mass},
    ),
)

IMPR_TABLE(TABLE=MASSE, UNITE=6, FORMAT_R="E20.12")

FIN()
"""


def aster_export() -> str:
    return (
        "P time_limit 900\nP memory_limit 4096\nP ncpus 1\nP mpi_nbcpu 1\n"
        "P mpi_nbnoeud 1\nF comm lot27_lecture.comm D 1\n"
        "F mmed lot27_lecture.mmed D 20\n"
    )


def files() -> dict[Path, str]:
    data = load_model_data(DATA_PATH)
    params = build_params(data)
    masses = expected_masses(params)
    return {
        OUT / "params.json": _json(params),
        INVARIANTS_PATH: _yaml_flow(
            expected_invariants(params, layer_interface_levels(data))
        ),
        OUT / "segments_attendus.json": _json(expected_segments(params)),
        OUT / "aster" / "lot27_lecture.comm": aster_comm(masses),
        OUT / "aster" / "lot27_lecture.export": aster_export(),
        OUT / "aster_expected.json": _json(masses),
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    for path, content in files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
