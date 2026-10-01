"""Lot 29, extension beyond the four prescribed factors: two INDEPENDENT
tube+ring+beam+`LIAISON_SOLIDE` units (geometrically disjoint, no shared
node) in the same model, sharing only the global DOF numbering and a single
pool of `DIS_T` springs -- the real quay model has NINE such units, not one.

Not part of the lot 29 matrix's four factors (n_springs, stiffness,
symmetry, redundant_bc): H1-H3 on a *single* unit (`build_lot29_repro.py`)
cleanly rejected spring count and stiffness scale, and only reproduced a
null pivot through the already-fixed symmetry/`LIAISON_SOLIDE` redundancy
(`redundant_bc=True`) -- never through springs alone, however many. This
script tests the next most parsimonious remaining candidate before falling
back to H4 (solver/renumbering): does the mere PRESENCE of a second,
independent `LIAISON_SOLIDE` occurrence in the same model change the
outcome, everything else held fixed at the largest configuration that
already passed on one unit (N=10000 springs total, real stiffness, no
symmetry, non-redundant BC)?

Usage: python projets/quai_cw_test_01/scripts/build_lot29_repro_two_units.py <label> [--n-springs N]
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_lot29_repro import (  # noqa: E402
    BEAM_HY,
    BEAM_HZ,
    BEAM_LENGTH,
    BETON_E,
    BETON_NU,
    BETON_RHO,
    COEF_RIGI_DRZ,
    DEFAULT_OUTPUT_DIR,
    FACETS,
    MESH_SIZE,
    RADIUS,
    SOLVER_RESI_RELA,
    THICKNESS,
    TUBE_E,
    TUBE_NU,
    TUBE_RHO,
    _fmt,
    _wrapped,
    nodes_per_layer,
    total_layers,
)

UNIT_X_OFFSET = 5.0  # m: unit B's axis, far enough from unit A to never share a node.


def _unit_mesh(
    *, unit: str, x_offset: float, n_springs: int
) -> tuple[list[str], dict[str, Any]]:
    """One tube+ring+beam unit's mesh lines, every name prefixed by `unit`
    (`A`/`B`) so the two units never share a node or element name."""
    npl = nodes_per_layer(facets=FACETS, symmetry=False)
    n_layers = total_layers(n_springs=n_springs, facets=FACETS, symmetry=False)
    tete_layer = n_layers
    ring_z = tete_layer * MESH_SIZE
    thetas = [2.0 * math.pi * i / FACETS for i in range(FACETS)]

    def name(layer: int, i: int) -> str:
        return f"N{unit}{layer * npl + i + 1}"

    lines: list[str] = ["COOR_3D"]
    for layer in range(n_layers + 1):
        z = layer * MESH_SIZE
        for i, theta in enumerate(thetas):
            x = x_offset + RADIUS * math.cos(theta)
            y = RADIUS * math.sin(theta)
            lines.append(f"{name(layer, i)} {_fmt(x)} {_fmt(y)} {_fmt(z)}")
    beam_n1 = f"N{unit}B1"
    beam_n2 = f"N{unit}B2"
    lines.append(f"{beam_n1} {_fmt(x_offset)} {_fmt(0.0)} {_fmt(ring_z)}")
    lines.append(f"{beam_n2} {_fmt(x_offset + BEAM_LENGTH)} {_fmt(0.0)} {_fmt(ring_z)}")
    lines += ["FINSF", "", "QUAD4"]

    quad_names: list[str] = []
    for layer in range(n_layers):
        for i in range(FACETS):
            i_next = (i + 1) % FACETS
            a, b = name(layer, i), name(layer, i_next)
            c, d = name(layer + 1, i_next), name(layer + 1, i)
            qname = f"M{unit}{len(quad_names) + 1}"
            quad_names.append(qname)
            lines.append(f"{qname} {a} {b} {c} {d}")
    lines += ["FINSF", "", "SEG2", f"MB{unit} {beam_n1} {beam_n2}", "FINSF", ""]

    spring_names: list[str] = []
    if n_springs > 0:
        for layer in range(1, n_layers):
            for i in range(npl):
                if len(spring_names) >= n_springs:
                    break
                spring_names.append(name(layer, i))
            if len(spring_names) >= n_springs:
                break

    lines = _wrapped([*lines, "GROUP_MA", f"COQUE_{unit}"], quad_names) + ["FINSF", ""]
    lines += ["GROUP_MA", f"POUTRE_{unit}", f"  MB{unit}", "FINSF", ""]
    pied_names = [name(0, i) for i in range(npl)]
    tete_names = [name(tete_layer, i) for i in range(npl)]
    lines = _wrapped([*lines, "GROUP_NO", f"PIED_{unit}"], pied_names) + ["FINSF", ""]
    lines = _wrapped([*lines, "GROUP_NO", f"TETE_{unit}"], tete_names) + ["FINSF", ""]
    lines += ["GROUP_NO", f"POUTRE_N_{unit} {beam_n1}", "FINSF", ""]
    lines += ["GROUP_NO", f"POUTRE_LIBRE_{unit} {beam_n2}", "FINSF", ""]
    if n_springs > 0:
        lines = _wrapped([*lines, "GROUP_NO", f"RESSORTS_{unit}"], spring_names) + [
            "FINSF",
            "",
        ]

    meta = {
        "n_layers": n_layers,
        "n_quads": len(quad_names),
        "n_springs": len(spring_names),
    }
    return lines, meta


def build_mesh(*, n_springs_total: int) -> tuple[str, dict[str, Any]]:
    n_a = n_springs_total // 2
    n_b = n_springs_total - n_a
    lines_a, meta_a = _unit_mesh(unit="A", x_offset=0.0, n_springs=n_a)
    lines_b, meta_b = _unit_mesh(unit="B", x_offset=UNIT_X_OFFSET, n_springs=n_b)
    header = [
        "% Reproducteur lot 29 -- deux unites tube+anneau+poutre+LIAISON_SOLIDE",
        "TITRE",
        f"Deux unites independantes, n_springs_total={n_springs_total}",
        "FINSF",
        "",
    ]
    text = "\n".join([*header, *lines_a, *lines_b, "FIN", ""])
    return text, {"unit_a": meta_a, "unit_b": meta_b}


def build_comm(*, n_springs_total: int, stiffness_n_per_m: float) -> str:
    n_a = n_springs_total // 2
    n_b = n_springs_total - n_a
    crea_poi1 = []
    discret = []
    modele_affe = [
        '_F(GROUP_MA=("COQUE_A", "COQUE_B"), PHENOMENE="MECANIQUE", '
        'MODELISATION="DKT"),',
        '_F(GROUP_MA=("POUTRE_A", "POUTRE_B"), PHENOMENE="MECANIQUE", '
        'MODELISATION="POU_D_E"),',
    ]
    for unit, n in (("A", n_a), ("B", n_b)):
        if n > 0:
            crea_poi1.append(
                f'_F(NOM_GROUP_MA="RESSORTS_{unit}", GROUP_NO=("RESSORTS_{unit}",)),'
            )
            discret.append(
                f'_F(GROUP_MA=("RESSORTS_{unit}",), CARA="K_T_D_N", '
                f"VALE=(0.0, {_fmt(stiffness_n_per_m)}, 0.0)),"
            )
            modele_affe.append(
                f'_F(GROUP_MA=("RESSORTS_{unit}",), PHENOMENE="MECANIQUE", '
                'MODELISATION="DIS_T"),'
            )
    crea_poi1_block = ""
    if crea_poi1:
        crea_poi1_block = f"""
MAIL = CREA_MAILLAGE(
    MAILLAGE=MAIL,
    CREA_POI1=(
        {"\n        ".join(crea_poi1)}
    ),
)
"""
    discret_block = ""
    if discret:
        discret_block = f"""
    DISCRET=(
        {"\n        ".join(discret)}
    ),"""

    n_springs_note = f"n_springs_total={n_springs_total}"
    stiffness_note = f"stiffness_n_per_m={_fmt(stiffness_n_per_m)}"
    return f"""\
# Reproducteur lot 29 -- extension a deux unites (hors des quatre facteurs
# prescrits, voir le docstring de ce script). Hors de tout projet.
# Parametres : {n_springs_note}, {stiffness_note}.

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"), DEBUG=_F(SDVERI="OUI"))

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
{crea_poi1_block}
MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        {"\n        ".join(modele_affe)}
    ),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=_F(
        GROUP_MA=("COQUE_A", "COQUE_B"), EPAIS={_fmt(THICKNESS)},
        COEF_RIGI_DRZ={_fmt(COEF_RIGI_DRZ)},
    ),
    POUTRE=_F(
        GROUP_MA=("POUTRE_A", "POUTRE_B"), SECTION="RECTANGLE", CARA=("HY", "HZ"),
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
        _F(GROUP_MA=("COQUE_A", "COQUE_B"), MATER=MAT_TUBE),
        _F(GROUP_MA=("POUTRE_A", "POUTRE_B"), MATER=MAT_BETON),
    ),
)

# Deux occurrences independantes de LIAISON_SOLIDE, comme les neuf du quai
# (quai_cw_test_01.generation.comm.liaison_solide_block), jamais une seule.
CH_SOLIDE = AFFE_CHAR_MECA(
    MODELE=MO,
    LIAISON_SOLIDE=(
        _F(GROUP_NO=("TETE_A", "POUTRE_N_A")),
        _F(GROUP_NO=("TETE_B", "POUTRE_N_B")),
    ),
)

CH_BLOC = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        _F(GROUP_NO=("PIED_A", "PIED_B"), DX=0.0, DY=0.0, DZ=0.0),
    ),
)

CH_CHARGE = AFFE_CHAR_MECA(
    MODELE=MO,
    FORCE_NODALE=(
        _F(GROUP_NO=("POUTRE_LIBRE_A",), FZ=-1000.0),
        _F(GROUP_NO=("POUTRE_LIBRE_B",), FZ=-1000.0),
    ),
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
    label: str, *, n_springs_total: int, stiffness_n_per_m: float, output_dir: Path
) -> dict[str, Any]:
    mesh_text, mesh_meta = build_mesh(n_springs_total=n_springs_total)
    comm_text = build_comm(
        n_springs_total=n_springs_total, stiffness_n_per_m=stiffness_n_per_m
    )
    case_dir = output_dir / label
    case_dir.mkdir(parents=True, exist_ok=True)
    stem = "repro"
    (case_dir / f"{stem}.mail").write_text(mesh_text, encoding="utf-8")
    (case_dir / f"{stem}.comm").write_text(comm_text, encoding="utf-8")
    (case_dir / f"{stem}.export").write_text(build_export(stem), encoding="utf-8")
    meta = {
        "label": label,
        "n_springs_total": n_springs_total,
        "stiffness_n_per_m": stiffness_n_per_m,
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
    parser.add_argument("--n-springs", type=int, default=10000)
    parser.add_argument("--stiffness", type=float, default=1.0e6)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    meta = build_case(
        args.label,
        n_springs_total=args.n_springs,
        stiffness_n_per_m=args.stiffness,
        output_dir=args.output_dir,
    )
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
