"""Parameters, invariants and altered variants of the lot 26 qualification meshes.

Everything here is written **before** any Salome run: the expected values of the
invariants are computed analytically from the parameters (structured meshes of
planar quadrangles), never read back from a produced MED file.

Produces, under `data/examples/lot26_essais/`:

* `<geometry>/params.json` and `<geometry>/invariants.yaml`;
* `<geometry>/altere_*` : deliberately altered variants (a script or a
  parameter file) that `aster-expert mesh check` must reject.

Usage: python scripts/build_lot26_essais.py [--output-dir PATH]
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot26_essais"
SALOME_DIR = ROOT / "scripts" / "salome"

SIZE = 0.25  # m, target 1D length (every length below is a multiple of it)
PRECISION = 1e-7
TOL = 1e-9

Point = tuple[float, float, float]


def _pt(x: float, y: float, z: float) -> list[float]:
    return [x, y, z]


def _bbox(*v: float) -> list[float]:
    return list(v)


# --- geometry 1: plate with a stiffener --------------------------------------
G1_A, G1_B, G1_H = 1.0, 0.5, 0.5  # plate x, plate y, stiffener z


def g1_params() -> dict[str, Any]:
    return {
        "plaque": {"origine": _pt(0, 0, 0), "u": _pt(G1_A, 0, 0), "v": _pt(0, G1_B, 0)},
        "raidisseur": {
            "origine": _pt(0, 0, 0),
            "u": _pt(G1_A, 0, 0),
            "v": _pt(0, 0, G1_H),
        },
        "arete_commune": [_pt(0, 0, 0), _pt(G1_A, 0, 0)],
        "taille": SIZE,
        "precision": PRECISION,
    }


def g1_invariants() -> dict[str, Any]:
    nx, ny, nz = (round(v / SIZE) for v in (G1_A, G1_B, G1_H))
    return {
        "schema_version": 1,
        "counts": {
            "nodes": (nx + 1) * (ny + nz + 1),
            "cells": {"QUAD4": nx * (ny + nz), "SEG2": 3 * nx + 2 * ny + 2 * nz},
        },
        "groups": [
            {
                "name": "PLAQUE",
                "count": nx * ny,
                "cell_type": "QUAD4",
                "bbox": _bbox(0, G1_A, 0, G1_B, 0, 0),
                "tolerance": TOL,
            },
            {
                "name": "RAIDISSEUR",
                "count": nx * nz,
                "cell_type": "QUAD4",
                "bbox": _bbox(0, G1_A, 0, 0, 0, G1_H),
                "tolerance": TOL,
            },
            {
                "name": "ARETE",
                "count": nx,
                "cell_type": "SEG2",
                "bbox": _bbox(0, G1_A, 0, 0, 0, 0),
                "tolerance": TOL,
            },
        ],
        "nodes_at": [
            {"label": "coin", "point": _pt(0, 0, 0), "tolerance": TOL},
            {
                "label": "milieu de l'arête",
                "point": _pt(G1_A / 2, 0, 0),
                "tolerance": TOL,
            },
            {
                "label": "sommet du raidisseur",
                "point": _pt(G1_A, 0, G1_H),
                "tolerance": TOL,
            },
        ],
        "shared_nodes": [
            {
                "label": "interface plaque / raidisseur",
                "groups": ["PLAQUE", "RAIDISSEUR"],
                "count": nx + 1,
                "at": [_pt(0, 0, 0), _pt(G1_A / 2, 0, 0), _pt(G1_A, 0, 0)],
                "tolerance": TOL,
            },
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": TOL},
    }


# --- geometry 2: faceted tube and two tangent plates -------------------------
G2_RADIUS, G2_FACETS, G2_WIDTH = 0.71, 40, 0.5
G2_LEVELS = [-2.0, 0.0, 1.0, 2.0, 2.5]
G2_CENTER_DEG, G2_HALF_DEG = -90.0, 45.0


def g2_params(
    *, facets: int = G2_FACETS, levels: list[float] | None = None
) -> dict[str, Any]:
    return {
        "tube": {"rayon": G2_RADIUS, "facettes": facets},
        "plaques": {"largeur": G2_WIDTH},
        "cotes": list(G2_LEVELS if levels is None else levels),
        "empreinte": {"angle_centre_deg": G2_CENTER_DEG, "demi_angle_deg": G2_HALF_DEG},
        "taille": SIZE,
        "precision": PRECISION,
    }


def g2_invariants() -> dict[str, Any]:
    n_facets = G2_FACETS
    intervals = list(zip(G2_LEVELS[:-1], G2_LEVELS[1:], strict=True))
    segments = [round((b - a) / SIZE) for a, b in intervals]
    vertical = sum(segments)  # 1D segments on one vertical line
    columns_per_plate = round(G2_WIDTH / SIZE)
    levels = len(G2_LEVELS)
    nodes = n_facets * (vertical + 1) + 2 * columns_per_plate * (vertical + 1)
    tube_quads = n_facets * vertical
    plate_quads = columns_per_plate * vertical
    seg2 = (
        n_facets * levels  # tube horizontal edges, one segment per facet
        + n_facets * vertical  # tube generatrices
        + 2 * columns_per_plate * levels  # plate horizontal edges
        + 2 * vertical  # free vertical edge of each plate
    )
    facet_deg = 360.0 / n_facets
    imprint_facets = round(2 * G2_HALF_DEG / facet_deg)
    edge = G2_RADIUS * math.cos(math.radians(G2_HALF_DEG))
    z_min, z_max = G2_LEVELS[0], G2_LEVELS[-1]
    r, w = G2_RADIUS, G2_WIDTH
    invariants: dict[str, Any] = {
        "schema_version": 1,
        "counts": {
            "nodes": nodes,
            "cells": {"QUAD4": tube_quads + 2 * plate_quads, "SEG2": seg2},
        },
        "groups": [
            {
                "name": "TUBE",
                "count": tube_quads,
                "cell_type": "QUAD4",
                "bbox": _bbox(-r, r, -r, r, z_min, z_max),
                "tolerance": TOL,
            },
            {
                "name": "PLAQUE_D",
                "count": plate_quads,
                "cell_type": "QUAD4",
                "bbox": _bbox(r, r + w, 0, 0, z_min, z_max),
                "tolerance": TOL,
            },
            {
                "name": "PLAQUE_G",
                "count": plate_quads,
                "cell_type": "QUAD4",
                "bbox": _bbox(-r - w, -r, 0, 0, z_min, z_max),
                "tolerance": TOL,
            },
            {
                "name": "EMPREINTE",
                "count": imprint_facets * vertical,
                "cell_type": "QUAD4",
                "bbox": _bbox(-edge, edge, -r, -edge, z_min, z_max),
                "tolerance": TOL,
            },
            {
                "name": "SERRURE_D",
                "count": vertical,
                "cell_type": "SEG2",
                "bbox": _bbox(r, r, 0, 0, z_min, z_max),
                "tolerance": TOL,
            },
            {
                "name": "SERRURE_G",
                "count": vertical,
                "cell_type": "SEG2",
                "bbox": _bbox(-r, -r, 0, 0, z_min, z_max),
                "tolerance": TOL,
            },
        ],
        "nodes_at": [
            {
                "label": f"génératrice côté bassin, cote {z:g}",
                "point": _pt(0, -r, z),
                "tolerance": TOL,
            }
            for z in G2_LEVELS
        ]
        + [
            {
                "label": f"serrure droite, cote {z:g}",
                "point": _pt(r, 0, z),
                "tolerance": TOL,
            }
            for z in G2_LEVELS
        ],
        "shared_nodes": [
            {
                "label": f"serrure {side}",
                "groups": ["TUBE", f"PLAQUE_{side}"],
                "count": vertical + 1,
                "at": [_pt(sign * r, 0, z_min), _pt(sign * r, 0, z_max)],
                "tolerance": TOL,
            }
            for side, sign in (("D", 1), ("G", -1))
        ]
        + [
            {
                "label": "plaques entre elles",
                "groups": ["PLAQUE_D", "PLAQUE_G"],
                "count": 0,
                "tolerance": TOL,
            }
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": TOL},
    }
    return invariants


# --- geometry 3: beam and inclined bar on a shell ----------------------------
G3_A, G3_B = 1.0, 0.5
G3_BEAM_END = _pt(0, 0, 0.5)
G3_BAR_START = _pt(0.5, 0, 0)
G3_BAR_END = _pt(0.5, -0.3, -0.4)  # 3-4-5 triangle: length 0.5


def g3_params() -> dict[str, Any]:
    return {
        "coque": {"origine": _pt(0, 0, 0), "u": _pt(G3_A, 0, 0), "v": _pt(0, G3_B, 0)},
        "poutre": {"debut": _pt(0, 0, 0), "fin": G3_BEAM_END},
        "barre": {"debut": G3_BAR_START, "fin": G3_BAR_END},
        "taille": SIZE,
        "precision": PRECISION,
    }


def g3_invariants() -> dict[str, Any]:
    nx, ny = round(G3_A / SIZE), round(G3_B / SIZE)
    beam_segments = round(0.5 / SIZE)
    bar_segments = round(math.dist(G3_BAR_START, G3_BAR_END) / SIZE)
    shell_boundary = 2 * nx + 2 * ny
    return {
        "schema_version": 1,
        "counts": {
            "nodes": (nx + 1) * (ny + 1) + beam_segments + bar_segments,
            "cells": {
                "QUAD4": nx * ny,
                "SEG2": shell_boundary + beam_segments + bar_segments,
            },
        },
        "groups": [
            {
                "name": "COQUE",
                "count": nx * ny,
                "cell_type": "QUAD4",
                "bbox": _bbox(0, G3_A, 0, G3_B, 0, 0),
                "tolerance": TOL,
            },
            {
                "name": "POUTRE",
                "count": beam_segments,
                "cell_type": "SEG2",
                "bbox": _bbox(0, 0, 0, 0, 0, 0.5),
                "tolerance": TOL,
            },
            {
                "name": "BARRE",
                "count": bar_segments,
                "cell_type": "SEG2",
                "bbox": _bbox(0.5, 0.5, -0.3, 0, -0.4, 0),
                "tolerance": TOL,
            },
        ],
        "nodes_at": [
            {"label": "départ de la barre", "point": G3_BAR_START, "tolerance": TOL},
            {"label": "extrémité de la barre", "point": G3_BAR_END, "tolerance": TOL},
            {"label": "extrémité de la poutre", "point": G3_BEAM_END, "tolerance": TOL},
        ],
        "shared_nodes": [
            {
                "label": "départ de la barre sur la coque",
                "groups": ["BARRE", "COQUE"],
                "count": 1,
                "at": [G3_BAR_START],
                "tolerance": TOL,
            },
            {
                "label": "pied de la poutre sur la coque",
                "groups": ["POUTRE", "COQUE"],
                "count": 1,
                "at": [_pt(0, 0, 0)],
                "tolerance": TOL,
            },
            {
                "label": "poutre et barre entre elles",
                "groups": ["POUTRE", "BARRE"],
                "count": 0,
                "tolerance": TOL,
            },
        ],
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": TOL},
    }


# --- Code_Aster reading cases -------------------------------------------------
# Each case reads the MED of one geometry, models every group (DKT on the shell
# groups, BARRE on the segment groups, POU_D_E on beams) and asks POST_ELEM for
# the mass of each group with RHO = 1 and a unit thickness / section: the mass of
# a group is then its area (shell) or its length (segment), exact quantities
# computed here from the parameters.
SHELL, BAR, BEAM = "shell", "bar", "beam"


def _chord() -> float:
    return 2 * G2_RADIUS * math.sin(math.pi / G2_FACETS)


def aster_groups() -> dict[str, list[tuple[str, str, float]]]:
    """Per case, (group, kind, expected mass) in the order of the listing."""
    height = G2_LEVELS[-1] - G2_LEVELS[0]
    imprint = round(2 * G2_HALF_DEG / (360.0 / G2_FACETS))
    return {
        "g1": [
            ("PLAQUE", SHELL, G1_A * G1_B),
            ("RAIDISSEUR", SHELL, G1_A * G1_H),
            ("ARETE", BAR, G1_A),
        ],
        "g2": [
            ("TUBE", SHELL, G2_FACETS * _chord() * height),
            ("PLAQUE_D", SHELL, G2_WIDTH * height),
            ("PLAQUE_G", SHELL, G2_WIDTH * height),
            ("EMPREINTE", SHELL, imprint * _chord() * height),
            ("SERRURE_D", BAR, height),
            ("SERRURE_G", BAR, height),
        ],
        "g3": [
            ("COQUE", SHELL, G3_A * G3_B),
            ("POUTRE", BEAM, 0.5),
            ("BARRE", BAR, math.dist(G3_BAR_START, G3_BAR_END)),
        ],
    }


_Q = '"'
_MECA = '"MECANIQUE"'
_GEN = '"GENERALE"'


def aster_comm(case: str) -> str:
    groups = aster_groups()[case]
    names = lambda kind: [g for g, k, _ in groups if k == kind]  # noqa: E731

    def tup(items: list[str]) -> str:
        return "(" + ", ".join(f'"{i}"' for i in items) + ",)"

    affe = [
        f'_F(GROUP_MA={tup(names(SHELL))}, PHENOMENE="MECANIQUE", MODELISATION="DKT")'
    ]
    cara = [f"COQUE=_F(GROUP_MA={tup(names(SHELL))}, EPAIS=1.0)"]
    if names(BAR):
        affe.append(
            f"_F(GROUP_MA={tup(names(BAR))}, PHENOMENE={_MECA}, MODELISATION={_Q}BARRE{_Q})"
        )
        cara.append(
            f"BARRE=_F(GROUP_MA={tup(names(BAR))}, SECTION={_GEN}, CARA={_Q}A{_Q}, VALE=1.0)"
        )
    if names(BEAM):
        affe.append(
            f"_F(GROUP_MA={tup(names(BEAM))}, PHENOMENE={_MECA}, MODELISATION={_Q}POU_D_E{_Q})"
        )
        cara.append(
            f'POUTRE=_F(GROUP_MA={tup(names(BEAM))}, SECTION="GENERALE", '
            'CARA=("A", "IY", "IZ", "JX"), VALE=(1.0, 1.0, 1.0, 1.0))'
        )
    every = [g for g, _, _ in groups]
    mass = ",\n        ".join(f'_F(GROUP_MA="{g}")' for g in every)
    return f"""\
# Lot 26 -- lecture par Code_Aster du MED de la geometrie {case} (critere dans
# docs/essais_lot26.md, ecrit avant l'execution). RHO = 1, EPAIS = 1, A = 1 :
# la masse d'un groupe est son aire (coque) ou sa longueur (barre, poutre).

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20, INFO=2)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        {(chr(10) + "        ").join(a + "," for a in affe)}
    ),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    {(chr(10) + "    ").join(c + "," for c in cara)}
)

MAT = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3, RHO=1.0))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA={tup(every)}, MATER=MAT))

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


def aster_export(case: str) -> str:
    return (
        "P time_limit 300\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm lot26_{case}.comm D 1\n"
        f"F mmed lot26_{case}.mmed D 20\n"
    )


ASTER_DIRS = {"g1": "plaque_raidisseur", "g2": "tube_plaques", "g3": "poutre_barre"}


# --- altered scripts ---------------------------------------------------------
_ASSEMBLY = re.compile(r"# ASSEMBLY begin:.*?# ASSEMBLY end\n", re.DOTALL)


def altered_script(name: str, replacement: str) -> str:
    """Copy of a Salome script whose assembly block is replaced (exactly once)."""
    text = (SALOME_DIR / f"{name}.py").read_text(encoding="utf-8")
    if len(_ASSEMBLY.findall(text)) != 1:
        message = f"{name}: expected exactly one ASSEMBLY block"
        raise SystemExit(message)
    banner = (
        "# ALTERED VARIANT (lot 26): the assembly below deliberately replaces the\n"
        "# single partition; `aster-expert mesh check` must reject the result.\n"
    )
    return _ASSEMBLY.sub(lambda _m: banner + replacement + "\n", text)


G1_COMPOUND = "PARTITION = geompy.MakeCompound([plaque, raidisseur])"
G3_COMPOUND = (
    "PARTITION = geompy.MakeCompound(\n"
    "    [\n"
    "        geompy.MakePartition(\n"
    '            [coque, poutre], [], [], [], geompy.ShapeType["FACE"], 0, [], 1\n'
    "        ),\n"
    "        barre,\n"
    "    ]\n"
    ")"
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def files() -> dict[str, str]:
    out: dict[str, str] = {
        "plaque_raidisseur/params.json": _json(g1_params()),
        "plaque_raidisseur/invariants.yaml": _yaml(g1_invariants()),
        "plaque_raidisseur/altere_sans_partition.py": altered_script(
            "lot26_plaque_raidisseur", G1_COMPOUND
        ),
        "tube_plaques/params.json": _json(g2_params()),
        "tube_plaques/invariants.yaml": _yaml(g2_invariants()),
        "tube_plaques/altere_36_facettes.json": _json(g2_params(facets=36)),
        "tube_plaques/altere_sans_cote_1.json": _json(
            g2_params(levels=[c for c in G2_LEVELS if c != 1.0])
        ),
        "poutre_barre/params.json": _json(g3_params()),
        "poutre_barre/invariants.yaml": _yaml(g3_invariants()),
        "poutre_barre/altere_barre_non_reliee.py": altered_script(
            "lot26_poutre_barre", G3_COMPOUND
        ),
    }
    for case, directory in ASTER_DIRS.items():
        out[f"{directory}/aster/lot26_{case}.comm"] = aster_comm(case)
        out[f"{directory}/aster/lot26_{case}.export"] = aster_export(case)
    out["aster_expected.json"] = _json(
        {
            case: {g: {"kind": k, "mass": m} for g, k, m in groups}
            for case, groups in aster_groups().items()
        }
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for name, content in files().items():
        path = args.output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
