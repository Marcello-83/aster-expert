"""Build the FORCE_COQUE trial case of lot 21 (mesh, command file, export).

Fully synthetic: a half-cylinder shell (radius 0.71 m, height 1.00 m, axis Z,
angular span -90 deg .. +90 deg, diametral plane X = 0) meshed with planar
QUAD4 facets, written in Code_Aster's native ASCII mesh format (read by
`LIRE_MAILLAGE`, FORMAT="ASTER") -- no Salome, no MED library, no file of any
user project. Output is deterministic (the test replays it byte for byte).

The three files land in `data/examples/fcoque_essai/`:
- `demi_cylindre.mail`   mesh (nodes, QUAD4, groups);
- `demi_cylindre.comm`   command file (DKT, unit FORCE_COQUE along X);
- `demi_cylindre.export` run_aster export (the mesh must be staged with it).

Usage: python scripts/build_fcoque_essai.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

RADIUS = 0.71
HEIGHT = 1.00
THICKNESS = 0.010
N_THETA = 36  # facets over 180 degrees (5 degrees each)
N_Z = 10
STEM = "demi_cylindre"
_NAMES_PER_LINE = 8

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "fcoque_essai"


def _node_id(i: int, j: int) -> int:
    return i * (N_Z + 1) + j + 1


def _fmt(x: float) -> str:
    """Fixed-point text; an exact zero is written without sign."""
    return f"{round(x, 12) + 0.0:.12f}"


def facet_area() -> float:
    """Exact developed area of the faceted surface (planar chords)."""
    chord = 2.0 * RADIUS * math.sin(math.pi / (2.0 * N_THETA))
    return N_THETA * chord * HEIGHT


def build_mesh() -> str:
    lines = ["% Demi-cylindre synthetique, essai FORCE_COQUE (lot 21)", "TITRE"]
    lines += [
        f"Demi-cylindre R={RADIUS} H={HEIGHT}, {N_THETA}x{N_Z} QUAD4 plans",
        "FINSF",
        "",
        "COOR_3D",
    ]
    for i in range(N_THETA + 1):
        theta = -math.pi / 2.0 + math.pi * i / N_THETA
        for j in range(N_Z + 1):
            x = RADIUS * math.cos(theta)
            y = RADIUS * math.sin(theta)
            z = HEIGHT * j / N_Z
            lines.append(f"N{_node_id(i, j)} {_fmt(x)} {_fmt(y)} {_fmt(z)}")
    lines += ["FINSF", "", "QUAD4"]
    quad = 0
    for i in range(N_THETA):
        for j in range(N_Z):
            quad += 1
            ids = (
                _node_id(i, j),
                _node_id(i + 1, j),
                _node_id(i + 1, j + 1),
                _node_id(i, j + 1),
            )
            lines.append(f"MA{quad} " + " ".join(f"N{n}" for n in ids))
    # The ASTER format reads fixed-width records: long name lists are wrapped.
    lines += ["FINSF", "", "GROUP_MA"]
    names = [f"MA{k}" for k in range(1, quad + 1)]
    lines.append("COQUE")
    lines += [
        "  " + " ".join(names[k : k + _NAMES_PER_LINE])
        for k in range(0, quad, _NAMES_PER_LINE)
    ]
    lines += ["FINSF", ""]
    # Isostatic supports: A (theta=-90, z=0), B (theta=+90, z=0), C (theta=-90, z=H).
    node_a = _node_id(0, 0)
    node_b = _node_id(N_THETA, 0)
    node_c = _node_id(0, N_Z)
    for name, node in (("NA", node_a), ("NB", node_b), ("NC", node_c)):
        lines += ["GROUP_NO", f"{name} N{node}", "FINSF", ""]
    lines += [
        "GROUP_NO",
        f"APPUIS N{node_a} N{node_b} N{node_c}",
        "FINSF",
        "",
        "FIN",
        "",
    ]
    return "\n".join(lines)


def build_comm() -> str:
    return f"""\
# Essai FORCE_COQUE (lot 21) -- demi-cylindre synthetique, hors de tout projet.
# Question : l'intensite de FORCE_COQUE se rapporte-t-elle a la surface developpee
# des mailles ou a leur surface projetee sur le plan diametral ?
# Charge unitaire FX = 1 sur toute la surface ; resultante des reactions aux appuis.

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA="COQUE", EPAIS={THICKNESS}))

ACIER = DEFI_MATERIAU(ELAS=_F(E=2.1e11, NU=0.3))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", MATER=ACIER))

# Trois appuis ponctuels : 3 + 2 + 1 blocages, six mouvements de corps rigide.
CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        _F(GROUP_NO="NA", DX=0.0, DY=0.0, DZ=0.0),
        _F(GROUP_NO="NB", DX=0.0, DZ=0.0),
        _F(GROUP_NO="NC", DX=0.0),
    ),
    FORCE_COQUE=_F(GROUP_MA="COQUE", FX=1.0),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE="REAC_NODA")

TAB_X = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="RESULTANTE_REACTIONS",
        GROUP_NO="APPUIS",
        RESULTAT=RESU,
        NOM_CHAM="REAC_NODA",
        RESULTANTE=("DX", "DY", "DZ"),
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE=TAB_X, UNITE=6)

FIN()
"""


def build_export() -> str:
    return "\n".join(
        [
            "P time_limit 300",
            "P memory_limit 2048",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P mpi_nbnoeud 1",
            f"F comm {STEM}.comm D 1",
            f"F mail {STEM}.mail D 20",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{STEM}.mail").write_text(build_mesh(), encoding="utf-8")
    (out / f"{STEM}.comm").write_text(build_comm(), encoding="utf-8")
    (out / f"{STEM}.export").write_text(build_export(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
