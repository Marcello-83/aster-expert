"""Minimal, parametrised reproducer for the null-pivot diagnosis of lot 29.

Fully synthetic, independent of the quay model: a short facetted tube (radius
and facet count taken from the quay's own data, `data/examples/
combiwall_model_data.yaml`, `tube.rayon`/`maillage.nombre_facettes_par_tube`),
its head ring tied by `LIAISON_SOLIDE` to a beam node (`POU_D_E`), and N
`DIS_T` discrete springs (`K_T_D_N`) planted on the tube's own shell nodes
below the ring -- the same three ingredients lot 28's real quay model
combines (point 1 tube, point 2/3 poutre + LIAISON_SOLIDE, point 4 ressorts),
stripped of everything else (palplanche, tirants, pressure profiles, the
other eight tubes).

Four parameters, one factor varied at a time (lot 29, Etape 1):
- `n_springs`: number of DIS_T springs (0 by default).
- `stiffness_n_per_m`: nodal stiffness of each spring, N/m.
- `symmetry`: cut the tube to a half-circle (-90..+90 deg) by an X=0 plane,
  the tube-1/tube-9 configuration of the quay.
- `redundant_bc`: only meaningful with `symmetry=True` -- reproduces the
  known-bad pre-fix behaviour (`aster_expert.generation.comm.
  symmetry_and_support_block`'s own docstring) by imposing DRY=DRZ=0 a
  SECOND time on the ring's own share of the symmetry plane, on top of the
  rotation `LIAISON_SOLIDE` already derives there.

Mesh written in Code_Aster's native ASCII format (`LIRE_MAILLAGE`,
FORMAT="ASTER") -- no Salome, no MED library (`scripts/build_fcoque_essai.py`,
lot 21, is the model for this convention). Node/element counts grow with
`n_springs` (one extra 0.25 m layer per `nodes_per_layer` springs needed):
the tube is only as tall as it needs to be to host its own springs, never
padded.

Usage: python scripts/build_lot29_repro.py <label> [options]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

# Quay data (data/examples/combiwall_model_data.yaml): tube.rayon,
# maillage.nombre_facettes_par_tube, maillage.taille_verticale_visee,
# tube.epaisseur_coque_retenue, tube.module_young, tube.coefficient_poisson,
# tube.masse_volumique.
RADIUS = 0.71
FACETS = 40
MESH_SIZE = 0.25
MIN_LAYERS = 8  # 8 x 0.25 m = 2.00 m, the lot 29 instructions' own example.
THICKNESS = 0.014
TUBE_E = 210.0e9
TUBE_NU = 0.30
TUBE_RHO = 7850.0

# Poutre de couronnement (data/examples/combiwall_model_data.yaml,
# poutre_couronnement).
BEAM_LENGTH = 1.0
BEAM_HY = 2.50
BEAM_HZ = 1.40
BETON_E = 34.0e9
BETON_NU = 0.20
BETON_RHO = 2500.0

# aster_expert.generation.comm.DRZ_STIFFNESS_COEF / SOLVER_RESI_RELA: both
# already established by the real model's own diagnosis (lot 28, items 4/6
# and the FACTOR_57 finding) -- held fixed here, never a factor of this lot's
# matrix.
COEF_RIGI_DRZ = 1.0e-3
SOLVER_RESI_RELA = 1.0e-4

_NAMES_PER_LINE = 8

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot29_repro"


def nodes_per_layer(*, facets: int, symmetry: bool) -> int:
    return facets // 2 + 1 if symmetry else facets


def total_layers(*, n_springs: int, facets: int, symmetry: bool) -> int:
    """Layer 0 is PIED, the last layer is TETE; springs occupy the
    intermediate layers (1 .. total_layers - 1). Never shorter than
    `MIN_LAYERS` (the 2.00 m default of the lot 29 instructions)."""
    npl = nodes_per_layer(facets=facets, symmetry=symmetry)
    layers_for_springs = math.ceil(n_springs / npl) if n_springs > 0 else 0
    return max(MIN_LAYERS, layers_for_springs + 1)


def _fmt(x: float) -> str:
    return f"{round(x, 12) + 0.0:.12f}"


def _node_name(layer: int, i: int, *, npl: int) -> str:
    return f"N{layer * npl + i + 1}"


def _wrapped(prefix_lines: list[str], names: list[str]) -> list[str]:
    return prefix_lines + [
        "  " + " ".join(names[k : k + _NAMES_PER_LINE])
        for k in range(0, len(names), _NAMES_PER_LINE)
    ]


def build_mesh(
    *,
    n_springs: int,
    symmetry: bool,
    facets: int = FACETS,
    radius: float = RADIUS,
    mesh_size: float = MESH_SIZE,
) -> tuple[str, dict[str, Any]]:
    if facets % 4 != 0:
        message = f"facets doit être un multiple de 4 : {facets}"
        raise ValueError(message)
    npl = nodes_per_layer(facets=facets, symmetry=symmetry)
    n_layers = total_layers(n_springs=n_springs, facets=facets, symmetry=symmetry)
    tete_layer = n_layers
    ring_z = tete_layer * mesh_size

    if symmetry:
        half = facets // 2
        thetas = [-math.pi / 2.0 + math.pi * i / half for i in range(half + 1)]
    else:
        thetas = [2.0 * math.pi * i / facets for i in range(facets)]

    lines = [
        "% Reproducteur lot 29 (tube facette + LIAISON_SOLIDE + ressorts)",
        "TITRE",
        f"Reproducteur lot 29 : R={radius} facettes={facets} "
        f"symmetry={symmetry} n_springs={n_springs}",
        "FINSF",
        "",
        "COOR_3D",
    ]
    for layer in range(n_layers + 1):
        z = layer * mesh_size
        for i, theta in enumerate(thetas):
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            lines.append(
                f"{_node_name(layer, i, npl=npl)} {_fmt(x)} {_fmt(y)} {_fmt(z)}"
            )
    n_tube_nodes = (n_layers + 1) * npl
    beam_n1 = f"N{n_tube_nodes + 1}"
    beam_n2 = f"N{n_tube_nodes + 2}"
    lines.append(f"{beam_n1} {_fmt(0.0)} {_fmt(0.0)} {_fmt(ring_z)}")
    lines.append(f"{beam_n2} {_fmt(BEAM_LENGTH)} {_fmt(0.0)} {_fmt(ring_z)}")
    lines += ["FINSF", "", "QUAD4"]

    quad_names: list[str] = []
    i_range = (facets // 2) if symmetry else facets
    for layer in range(n_layers):
        for i in range(i_range):
            i_next = i + 1 if symmetry else (i + 1) % facets
            a = _node_name(layer, i, npl=npl)
            b = _node_name(layer, i_next, npl=npl)
            c = _node_name(layer + 1, i_next, npl=npl)
            d = _node_name(layer + 1, i, npl=npl)
            name = f"MA{len(quad_names) + 1}"
            quad_names.append(name)
            lines.append(f"{name} {a} {b} {c} {d}")
    lines += ["FINSF", "", "SEG2", f"MB1 {beam_n1} {beam_n2}", "FINSF", ""]

    spring_names: list[str] = []
    if n_springs > 0:
        for layer in range(1, n_layers):
            for i in range(npl):
                if len(spring_names) >= n_springs:
                    break
                spring_names.append(_node_name(layer, i, npl=npl))
            if len(spring_names) >= n_springs:
                break
        if len(spring_names) != n_springs:
            message = (
                f"pas assez de nœuds intermédiaires pour {n_springs} ressorts "
                f"({len(spring_names)} disponibles)"
            )
            raise ValueError(message)

    lines += ["GROUP_MA"]
    lines = _wrapped([*lines, "COQUE"], quad_names)
    lines += ["FINSF", "", "GROUP_MA", "POUTRE", "  MB1", "FINSF", ""]
    meta_n_springs = n_springs

    pied_names = [_node_name(0, i, npl=npl) for i in range(npl)]
    tete_names = [_node_name(tete_layer, i, npl=npl) for i in range(npl)]
    lines = _wrapped([*lines, "GROUP_NO", "PIED"], pied_names) + ["FINSF", ""]
    lines = _wrapped([*lines, "GROUP_NO", "TETE"], tete_names) + ["FINSF", ""]
    lines += ["GROUP_NO", f"POUTRE_N {beam_n1}", "FINSF", ""]
    lines += ["GROUP_NO", f"POUTRE_LIBRE {beam_n2}", "FINSF", ""]
    if n_springs > 0:
        # Point 4 du quai : le groupe de nœuds sert de base à CREA_POI1
        # (`aster_expert.generation.comm.mesh_prep_block`) -- jamais une
        # maille POI1 écrite à la main dans le maillage natif : une première
        # tentative ainsi faite a produit, à l'exécution, `<F> <MODELISA8_14>`
        # ("la maille POI1 ... est incluse dans une autre"), le mécanisme
        # réel (CREA_POI1) déjà utilisé par le générateur de production
        # n'est jamais réimplémenté ici.
        lines = _wrapped([*lines, "GROUP_NO", "RESSORTS"], spring_names) + [
            "FINSF",
            "",
        ]

    meta: dict[str, Any] = {
        "npl": npl,
        "n_layers": n_layers,
        "tete_layer": tete_layer,
        "ring_z": ring_z,
        "n_tube_nodes": n_tube_nodes,
        "n_quads": len(quad_names),
        "beam_n1": beam_n1,
        "beam_n2": beam_n2,
    }

    if symmetry:
        plan_i = (0, facets // 2)
        plan_x0 = [
            _node_name(layer, i, npl=npl)
            for layer in range(1, n_layers + 1)
            for i in plan_i
        ]
        plan_x0_ring = [_node_name(tete_layer, i, npl=npl) for i in plan_i]
        plan_x0_rest = [n for n in plan_x0 if n not in plan_x0_ring]
        lines = _wrapped([*lines, "GROUP_NO", "PLAN_X0"], plan_x0) + ["FINSF", ""]
        lines = _wrapped([*lines, "GROUP_NO", "PLAN_X0_RING"], plan_x0_ring) + [
            "FINSF",
            "",
        ]
        lines = _wrapped([*lines, "GROUP_NO", "PLAN_X0_REST"], plan_x0_rest) + [
            "FINSF",
            "",
        ]
        meta["plan_x0"] = len(plan_x0)
        meta["plan_x0_ring"] = len(plan_x0_ring)
        meta["plan_x0_rest"] = len(plan_x0_rest)

    meta["n_springs"] = meta_n_springs

    lines += ["FIN", ""]
    return "\n".join(lines), meta


def build_comm(
    *, n_springs: int, stiffness_n_per_m: float, symmetry: bool, redundant_bc: bool
) -> str:
    if redundant_bc and not symmetry:
        message = "redundant_bc n'a de sens qu'avec symmetry=True"
        raise ValueError(message)

    modele_affe = [
        '_F(GROUP_MA=("COQUE",), PHENOMENE="MECANIQUE", MODELISATION="DKT"),',
        '_F(GROUP_MA=("POUTRE",), PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"),',
    ]
    if n_springs > 0:
        modele_affe.append(
            '_F(GROUP_MA=("RESSORTS",), PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),'
        )
    modele_body = "\n        ".join(modele_affe)

    discret_block = ""
    if n_springs > 0:
        discret_block = f"""
    DISCRET=_F(
        GROUP_MA=("RESSORTS",), CARA="K_T_D_N",
        VALE=(0.0, {_fmt(stiffness_n_per_m)}, 0.0),
    ),"""

    bloc_occurrences = [
        '_F(GROUP_NO=("PIED",), DX=0.0, DY=0.0, DZ=0.0),',
    ]
    if symmetry:
        bloc_occurrences.append('_F(GROUP_NO=("PLAN_X0",), DX=0.0),')
        if redundant_bc:
            bloc_occurrences.append('_F(GROUP_NO=("PLAN_X0",), DRY=0.0, DRZ=0.0),')
        else:
            bloc_occurrences.append('_F(GROUP_NO=("PLAN_X0_REST",), DRY=0.0, DRZ=0.0),')
    bloc_body = "\n        ".join(bloc_occurrences)

    crea_poi1_block = ""
    if n_springs > 0:
        crea_poi1_block = """
MAIL = CREA_MAILLAGE(
    MAILLAGE=MAIL,
    CREA_POI1=_F(NOM_GROUP_MA="RESSORTS", GROUP_NO=("RESSORTS",)),
)
"""

    return f"""\
# Reproducteur minimal, lot 29 -- diagnostic du pivot nul de LIAISON_SOLIDE +
# ressorts DIS_T (lot 28, `.mess` <F> <FACTOR_11>). Hors de tout projet, hors
# fiche : ne pas transposer.
# Parametres : n_springs={n_springs}, stiffness_n_per_m={_fmt(stiffness_n_per_m)},
# symmetry={symmetry}, redundant_bc={redundant_bc}.

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"), DEBUG=_F(SDVERI="OUI"))

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
{crea_poi1_block}
MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        {modele_body}
    ),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=_F(
        GROUP_MA=("COQUE",), EPAIS={_fmt(THICKNESS)},
        COEF_RIGI_DRZ={_fmt(COEF_RIGI_DRZ)},
    ),
    POUTRE=_F(
        GROUP_MA=("POUTRE",), SECTION="RECTANGLE", CARA=("HY", "HZ"),
        VALE=({_fmt(BEAM_HY)}, {_fmt(BEAM_HZ)}),
    ),{discret_block}
)

MAT_TUBE = DEFI_MATERIAU(
    ELAS=_F(E={_fmt(TUBE_E)}, NU={_fmt(TUBE_NU)}, RHO={_fmt(TUBE_RHO)})
)
MAT_BETON = DEFI_MATERIAU(
    ELAS=_F(E={_fmt(BETON_E)}, NU={_fmt(BETON_NU)}, RHO={_fmt(BETON_RHO)})
)

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(
        _F(GROUP_MA=("COQUE",), MATER=MAT_TUBE),
        _F(GROUP_MA=("POUTRE",), MATER=MAT_BETON),
    ),
)

# Point 3 du quai : liaison de corps solide, anneau de tete + noeud de poutre
# (cas test sdlx03b.comm).
CH_SOLIDE = AFFE_CHAR_MECA(
    MODELE=MO,
    LIAISON_SOLIDE=_F(GROUP_NO=("TETE", "POUTRE_N")),
)

CH_BLOC = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        {bloc_body}
    ),
)

CH_CHARGE = AFFE_CHAR_MECA(
    MODELE=MO, FORCE_NODALE=_F(GROUP_NO=("POUTRE_LIBRE",), FZ=-1000.0)
)

RESU = MECA_STATIQUE(
    MODELE=MO,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    EXCIT=(_F(CHARGE=CH_SOLIDE), _F(CHARGE=CH_BLOC), _F(CHARGE=CH_CHARGE)),
    SOLVEUR=_F(METHODE="MUMPS", RESI_RELA={_fmt(SOLVER_RESI_RELA)}),
)

RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE=("REAC_NODA",))

FIN()
"""


def build_export(stem: str) -> str:
    return "\n".join(
        [
            "P time_limit 600",
            "P memory_limit 4096",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P mpi_nbnoeud 1",
            f"F comm {stem}.comm D 1",
            f"F mail {stem}.mail D 20",
            "",
        ]
    )


def build_case(
    label: str,
    *,
    n_springs: int,
    stiffness_n_per_m: float,
    symmetry: bool,
    redundant_bc: bool,
    output_dir: Path,
) -> dict[str, Any]:
    mesh_text, mesh_meta = build_mesh(n_springs=n_springs, symmetry=symmetry)
    comm_text = build_comm(
        n_springs=n_springs,
        stiffness_n_per_m=stiffness_n_per_m,
        symmetry=symmetry,
        redundant_bc=redundant_bc,
    )
    case_dir = output_dir / label
    case_dir.mkdir(parents=True, exist_ok=True)
    stem = "repro"
    (case_dir / f"{stem}.mail").write_text(mesh_text, encoding="utf-8")
    (case_dir / f"{stem}.comm").write_text(comm_text, encoding="utf-8")
    (case_dir / f"{stem}.export").write_text(build_export(stem), encoding="utf-8")
    meta = {
        "label": label,
        "n_springs": n_springs,
        "stiffness_n_per_m": stiffness_n_per_m,
        "symmetry": symmetry,
        "redundant_bc": redundant_bc,
        "mesh": mesh_meta,
        "mesh_sha256": hashlib.sha256(mesh_text.encode("utf-8")).hexdigest(),
        "comm_sha256": hashlib.sha256(comm_text.encode("utf-8")).hexdigest(),
    }
    (case_dir / f"{stem}.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("--n-springs", type=int, default=0)
    parser.add_argument("--stiffness", type=float, default=1.0e6)
    parser.add_argument("--symmetry", action="store_true")
    parser.add_argument("--redundant-bc", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    meta = build_case(
        args.label,
        n_springs=args.n_springs,
        stiffness_n_per_m=args.stiffness,
        symmetry=args.symmetry,
        redundant_bc=args.redundant_bc,
        output_dir=args.output_dir,
    )
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
