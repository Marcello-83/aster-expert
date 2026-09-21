"""Build the three trial cases of lot 22 (meshes, command files, exports).

Fully synthetic, in Code_Aster's native ASCII mesh format (`LIRE_MAILLAGE`,
FORMAT="ASTER"): no Salome, no MED library, no file of any project. Output is
deterministic (a test replays it byte for byte). Files land in
`data/examples/lot22_essais/<essai>/`; an export sits next to each command
file, and the mesh is written once per case under the case's own stem
(run_aster stages only the `<stem>.*` siblings of an export).

- Essai A (`a1`, `a2`, `a3`): cantilever strip in DKT, material defined by
  `ELAS_COQUE` alone, L axis along the strip (`ANGL_REP=(0,0)`), then T axis
  along the strip through `VECTEUR` (`a2`) and through `ANGL_REP=(90,0)` (`a3`).
  Controls: `a4` (`ELAS` witness), `a5`-`a7` (`ELAS_COQUE` value sets, testing
  which stiffness the nodal reactions use).
- Essai B (`b1`, `b2`, `b4`): two DKT plates in one model under `PESANTEUR`;
  plate 1 `ELAS`+`RHO` (witness), plate 2 `ELAS_COQUE` without (`b1`) then with
  (`b2`) `RHO`; `b4`: no `RHO` on plate 2, `PESANTEUR` limited to plate 1.
  `b3` measures the `RHO` convention by tip deflection of a strip (no reaction).
- Essai C (`c`): DKT plate on nodal springs (`CREA_POI1`, `DIS_T`, `K_T_D_N`),
  one POI1 group per class of tributary-area stiffness.

Usage: python scripts/build_lot22_essais.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot22_essais"
_NAMES_PER_LINE = 8

# Essai A -- strip geometry, ELAS_COQUE values (per unit width), tip line load.
A_LENGTH, A_WIDTH, A_NX, A_NY = 2.0, 0.5, 20, 5
A_MEMB = {"MEMB_L": 1.0e7, "MEMB_LT": 3.0e6, "MEMB_T": 1.0e7, "MEMB_G_LT": 3.5e6}
A_FLEX = {"FLEX_L": 1000.0, "FLEX_LT": 0.0, "FLEX_T": 4000.0, "FLEX_G_LT": 500.0}
# Required by the level-B rule "must be all defined" (first attempt of lot 22);
# without effect in DKT (U4.43.01).
A_CISA = {"CISA_L": 1.0e10, "CISA_T": 1.0e10}
A_LINE_LOAD = -10.0  # N/m along the tip edge (FORCE_ARETE, FZ)

# Essai B -- steel plates, 1 m x 1 m, 4 x 4.
B_E, B_NU, B_RHO_VOL = 2.1e11, 0.3, 7850.0
B_THICK1, B_THICK2 = 0.01, 0.02
B_RHO_SURF = 100.0  # ELAS_COQUE RHO, "masse par unite de surface" (U4.43.01)
B_GRAVITY = 9.81

# Essai C -- 1 m x 1 m plate on springs, 4 x 4, surface stiffness and pressure.
C_KS, C_PRESSURE = 1.0e6, 1000.0  # N/m^3, Pa
C_N = 4


@dataclass
class Mesh:
    title: str
    nodes: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    quads: dict[int, tuple[int, int, int, int]] = field(default_factory=dict)
    segs: dict[int, tuple[int, int]] = field(default_factory=dict)
    groups_ma: dict[str, list[str]] = field(default_factory=dict)
    groups_no: dict[str, list[int]] = field(default_factory=dict)


def _fmt(x: float) -> str:
    return f"{round(x, 12) + 0.0:.12f}"


def grid(
    mesh: Mesh, *, x0: float, y0: float, lx: float, ly: float, nx: int, ny: int
) -> tuple[dict[tuple[int, int], int], list[int]]:
    """Add a planar `nx` x `ny` QUAD4 grid (normal +Z); return node ids and quad ids."""
    n_off, q_off = len(mesh.nodes), len(mesh.quads)
    ids: dict[tuple[int, int], int] = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            nid = n_off + i * (ny + 1) + j + 1
            ids[(i, j)] = nid
            mesh.nodes[nid] = (x0 + lx * i / nx, y0 + ly * j / ny, 0.0)
    quads = []
    for i in range(nx):
        for j in range(ny):
            qid = q_off + i * ny + j + 1
            mesh.quads[qid] = (
                ids[(i, j)],
                ids[(i + 1, j)],
                ids[(i + 1, j + 1)],
                ids[(i, j + 1)],
            )
            quads.append(qid)
    return ids, quads


def write_mesh(mesh: Mesh) -> str:
    lines = [f"% {mesh.title}", "TITRE", mesh.title, "FINSF", "", "COOR_3D"]
    lines += [
        f"N{n} {_fmt(x)} {_fmt(y)} {_fmt(z)}"
        for n, (x, y, z) in sorted(mesh.nodes.items())
    ]
    lines += ["FINSF", ""]
    if mesh.segs:
        lines.append("SEG2")
        lines += [f"SG{m} N{a} N{b}" for m, (a, b) in sorted(mesh.segs.items())]
        lines += ["FINSF", ""]
    lines.append("QUAD4")
    lines += [
        f"MA{m} " + " ".join(f"N{n}" for n in ns)
        for m, ns in sorted(mesh.quads.items())
    ]
    lines += ["FINSF", ""]
    # Fixed-width records: long name lists are wrapped (lot 21).
    for name, members in mesh.groups_ma.items():
        names = list(members)
        lines += ["GROUP_MA", name]
        lines += [
            "  " + " ".join(names[k : k + _NAMES_PER_LINE])
            for k in range(0, len(names), _NAMES_PER_LINE)
        ]
        lines += ["FINSF", ""]
    for name, node_ids in mesh.groups_no.items():
        node_names = [f"N{n}" for n in node_ids]
        lines += ["GROUP_NO", name]
        lines += [
            "  " + " ".join(node_names[k : k + _NAMES_PER_LINE])
            for k in range(0, len(node_names), _NAMES_PER_LINE)
        ]
        lines += ["FINSF", ""]
    lines += ["FIN", ""]
    return "\n".join(lines)


def export_text(stem: str) -> str:
    return "\n".join(
        [
            "P time_limit 300",
            "P memory_limit 2048",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P mpi_nbnoeud 1",
            f"F comm {stem}.comm D 1",
            f"F mail {stem}.mail D 20",
            "",
        ]
    )


def _num(x: float) -> str:
    return repr(float(x))


# --- Essai A ---------------------------------------------------------------


def a_mesh() -> Mesh:
    mesh = Mesh("Bande console synthetique, essai A (lot 22)")
    ids, quads = grid(mesh, x0=0.0, y0=0.0, lx=A_LENGTH, ly=A_WIDTH, nx=A_NX, ny=A_NY)
    mesh.groups_ma["PLAQUE"] = [f"MA{q}" for q in quads]
    for j in range(A_NY):
        mesh.segs[j + 1] = (ids[(A_NX, j)], ids[(A_NX, j + 1)])
    mesh.groups_ma["BOUT"] = [f"SG{m}" for m in sorted(mesh.segs)]
    mesh.groups_no["ENCASTR"] = [ids[(0, j)] for j in range(A_NY + 1)]
    mesh.groups_no["BOUT"] = [ids[(A_NX, j)] for j in range(A_NY + 1)]
    return mesh


def _coefs(values: dict[str, float]) -> str:
    return ", ".join(f"{k}={_num(v)}" for k, v in values.items())


A_MATERIAL = {**A_MEMB, **A_FLEX, **A_CISA}
# Isotropic-valued sets for E = 1.2e10 Pa, nu = 0, h = 0.01 m: C = E h, D = E h^3/12
# = 1000 N.m/m = MEMB * h^2 / 12 (the relation the REAC_NODA control below tests).
_ISO_MEMB = {"MEMB_L": 1.2e8, "MEMB_LT": 0.0, "MEMB_T": 1.2e8, "MEMB_G_LT": 6.0e7}
_ISO_FLEX = {"FLEX_L": 1000.0, "FLEX_LT": 0.0, "FLEX_T": 1000.0, "FLEX_G_LT": 500.0}
_ISO_MATERIAL = {**_ISO_MEMB, **_ISO_FLEX, **A_CISA}


def a_comm(
    name: str,
    comment: str,
    *,
    orientation: str = "ANGL_REP=(0.0, 0.0)",
    material: str | None = None,
    gravity_rho: float | None = None,
) -> str:
    """Strip cantilever. `material` is the DEFI_MATERIAU body; default: ELAS_COQUE.

    With `gravity_rho`, the tip load is replaced by PESANTEUR and RHO is added
    to the ELAS_COQUE set (essai B3).
    """
    values = dict(A_MATERIAL)
    if gravity_rho is not None:
        values["RHO"] = gravity_rho
    material = material or f"ELAS_COQUE=_F({_coefs(values)})"
    load = (
        f"PESANTEUR=_F(GRAVITE={_num(B_GRAVITY)}, DIRECTION=(0.0, 0.0, -1.0)),"
        if gravity_rho is not None
        else f'FORCE_ARETE=_F(GROUP_MA="BOUT", FZ={_num(A_LINE_LOAD)}),'
    )
    orient = f", {orientation}" if orientation else ""
    return f"""\
# Essai (lot 22), variante {name} -- {comment}
# Bande console DKT, L = {A_LENGTH} m, b = {A_WIDTH} m.
# FLEX_LT = 0 : pas d'effet anticlastique, la bande se comporte comme des poutres
# en parallele. Reference : P*L^3/(3*FLEX*b) (charge en bout, P = q*b) ou
# p*L^4/(8*FLEX) (charge repartie p par unite de surface).

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA="PLAQUE", EPAIS=0.01{orient}))

MAT = DEFI_MATERIAU({material})

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="PLAQUE", MATER=MAT))

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=_F(GROUP_NO="ENCASTR", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    {load}
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE="REAC_NODA")

TAB_W = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="FLECHE_BOUT",
        GROUP_NO="BOUT",
        RESULTAT=RESU,
        NOM_CHAM="DEPL",
        NOM_CMP="DZ",
        OPERATION="EXTRACTION",
    )
)

TAB_R = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="REACTION_ENCASTREMENT",
        GROUP_NO="ENCASTR",
        RESULTAT=RESU,
        NOM_CHAM="REAC_NODA",
        RESULTANTE=("DX", "DY", "DZ"),
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE=TAB_W, UNITE=6, FORMAT_R="E20.12")

IMPR_TABLE(TABLE=TAB_R, UNITE=6, FORMAT_R="E20.12")

FIN()
"""


_A_MEMB_ONLY = {**A_MEMB, **_ISO_FLEX, **A_CISA}
_A_FLEX_ONLY = {**_ISO_MEMB, **A_FLEX, **A_CISA}
# name, comment, keyword arguments of `a_comm`
A_VARIANTS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("a1", "L le long de la console (ANGL_REP = 0, 0)", {}),
    (
        "a2",
        "T le long de la console (VECTEUR = Y global)",
        {"orientation": "VECTEUR=(0.0, 1.0, 0.0)"},
    ),
    (
        "a3",
        "T le long de la console (ANGL_REP = 90, 0)",
        {"orientation": "ANGL_REP=(90.0, 0.0)"},
    ),
    (
        "a4",
        "temoin ELAS isotrope (E = 1.2e10, nu = 0 : D = 1000)",
        {"orientation": "", "material": "ELAS=_F(E=1.2e10, NU=0.0)"},
    ),
    (
        "a5",
        "ELAS_COQUE a valeurs isotropes (FLEX = MEMB*h^2/12)",
        {"material": f"ELAS_COQUE=_F({_coefs(_ISO_MATERIAL)})"},
    ),
    (
        "a6",
        "ELAS_COQUE : membrane de A, flexion isotrope (FLEX != MEMB*h^2/12)",
        {"material": f"ELAS_COQUE=_F({_coefs(_A_MEMB_ONLY)})"},
    ),
    (
        "a7",
        "ELAS_COQUE : membrane isotrope, FLEX_L != FLEX_T",
        {"material": f"ELAS_COQUE=_F({_coefs(_A_FLEX_ONLY)})"},
    ),
)


# --- Essai B ---------------------------------------------------------------


def b_mesh() -> Mesh:
    mesh = Mesh("Deux plaques DKT synthetiques, essai B (lot 22)")
    ids1, quads1 = grid(mesh, x0=0.0, y0=0.0, lx=1.0, ly=1.0, nx=4, ny=4)
    ids2, quads2 = grid(mesh, x0=2.0, y0=0.0, lx=1.0, ly=1.0, nx=4, ny=4)
    mesh.groups_ma["P1"] = [f"MA{q}" for q in quads1]
    mesh.groups_ma["P2"] = [f"MA{q}" for q in quads2]
    for tag, ids in (("1", ids1), ("2", ids2)):
        mesh.groups_no[f"A{tag}"] = [ids[(0, 0)]]
        mesh.groups_no[f"B{tag}"] = [ids[(4, 0)]]
        mesh.groups_no[f"APP{tag}"] = [
            ids[(0, 0)],
            ids[(4, 0)],
            ids[(4, 4)],
            ids[(0, 4)],
        ]
    return mesh


def b_coefficients(thickness: float) -> dict[str, float]:
    """Isotropic ELAS_COQUE values from the closed forms of U4.43.01 (per metre)."""
    c = B_E * thickness / (1.0 - B_NU**2)
    d = B_E * thickness**3 / (12.0 * (1.0 - B_NU**2))
    return {
        "MEMB_L": c,
        "MEMB_LT": B_NU * c,
        "MEMB_T": c,
        "MEMB_G_LT": (1.0 - B_NU) / 2.0 * c,
        "FLEX_L": d,
        "FLEX_LT": B_NU * d,
        "FLEX_T": d,
        "FLEX_G_LT": (1.0 - B_NU) / 2.0 * d,
        "CISA_L": 5.0 * B_E * thickness / (12.0 * (1.0 + B_NU)),
        "CISA_T": 5.0 * B_E * thickness / (12.0 * (1.0 + B_NU)),
    }


def b_comm(name: str, with_rho: bool, gravity_group: str | None = None) -> str:
    coefs = {**b_coefficients(B_THICK2)}
    if with_rho:
        coefs["RHO"] = B_RHO_SURF
    coef_text = ", ".join(f"{k}={_num(v)}" for k, v in coefs.items())
    rho_text = "avec RHO" if with_rho else "sans RHO"
    grav_group = f'GROUP_MA="{gravity_group}", ' if gravity_group else ""
    grav_text = (
        f"PESANTEUR limitee au groupe {gravity_group}"
        if gravity_group
        else "PESANTEUR sur tout le modele"
    )
    return f"""\
# Essai B (lot 22), variante {name} -- plaque 2 en ELAS_COQUE {rho_text}.
# Plaque 1 : ELAS + RHO = {B_RHO_VOL} (temoin). Plaque 2 : ELAS_COQUE,
# EPAIS = {B_THICK2}
# (differente de la plaque 1 pour distinguer masse surfacique et masse volumique).
# {grav_text} ; resultante verticale des reactions par plaque.

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=(
        _F(GROUP_MA="P1", EPAIS={_num(B_THICK1)}),
        _F(GROUP_MA="P2", EPAIS={_num(B_THICK2)}),
    ),
)

MAT1 = DEFI_MATERIAU(ELAS=_F(E={_num(B_E)}, NU={_num(B_NU)}, RHO={_num(B_RHO_VOL)}))

MAT2 = DEFI_MATERIAU(ELAS_COQUE=_F({coef_text}))

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(_F(GROUP_MA="P1", MATER=MAT1), _F(GROUP_MA="P2", MATER=MAT2)),
)

# Par plaque : A DX, DY, DZ ; B DY, DZ ; les deux autres coins DZ.
CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        _F(GROUP_NO=("A1", "A2"), DX=0.0, DY=0.0, DZ=0.0),
        _F(GROUP_NO=("B1", "B2"), DY=0.0, DZ=0.0),
        _F(GROUP_NO=("APP1", "APP2"), DZ=0.0),
    ),
    PESANTEUR=_F({grav_group}GRAVITE={_num(B_GRAVITY)}, DIRECTION=(0.0, 0.0, -1.0)),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE="REAC_NODA")

TAB1 = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="RESULTANTE_PLAQUE_1",
        GROUP_NO="APP1",
        RESULTAT=RESU,
        NOM_CHAM="REAC_NODA",
        RESULTANTE=("DX", "DY", "DZ"),
        OPERATION="EXTRACTION",
    )
)

TAB2 = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="RESULTANTE_PLAQUE_2",
        GROUP_NO="APP2",
        RESULTAT=RESU,
        NOM_CHAM="REAC_NODA",
        RESULTANTE=("DX", "DY", "DZ"),
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE=TAB1, UNITE=6, FORMAT_R="E20.12")

IMPR_TABLE(TABLE=TAB2, UNITE=6, FORMAT_R="E20.12")

FIN()
"""


# --- Essai C ---------------------------------------------------------------


def tributary_area(i: int, j: int) -> float:
    h = 1.0 / C_N
    fi = 0.5 if i in (0, C_N) else 1.0
    fj = 0.5 if j in (0, C_N) else 1.0
    return fi * fj * h * h


def c_classes() -> dict[str, tuple[float, list[tuple[int, int]]]]:
    """Stiffness classes: name -> (nodal stiffness, grid indices)."""
    classes: dict[str, tuple[float, list[tuple[int, int]]]] = {}
    for i in range(C_N + 1):
        for j in range(C_N + 1):
            corner_i, corner_j = i in (0, C_N), j in (0, C_N)
            name = (
                "COIN"
                if corner_i and corner_j
                else "BORD"
                if corner_i or corner_j
                else "INT"
            )
            stiffness = C_KS * tributary_area(i, j)
            classes.setdefault(name, (stiffness, []))[1].append((i, j))
    return classes


def c_mesh() -> Mesh:
    mesh = Mesh("Plaque DKT sur ressorts nodaux, essai C (lot 22)")
    ids, quads = grid(mesh, x0=0.0, y0=0.0, lx=1.0, ly=1.0, nx=C_N, ny=C_N)
    mesh.groups_ma["PLAQUE"] = [f"MA{q}" for q in quads]
    for name, (_, members) in c_classes().items():
        mesh.groups_no[name] = [ids[m] for m in members]
    mesh.groups_no["TOUS"] = [
        ids[(i, j)] for i in range(C_N + 1) for j in range(C_N + 1)
    ]
    mesh.groups_no["A"] = [ids[(0, 0)]]
    mesh.groups_no["B"] = [ids[(C_N, 0)]]
    return mesh


def c_comm() -> str:
    classes = c_classes()
    poi1 = ",\n        ".join(
        f'_F(NOM_GROUP_MA="P_{name}", GROUP_NO="{name}")' for name in classes
    )
    spring_groups = ", ".join(f'"P_{name}"' for name in classes)
    discrets = "\n        ".join(
        f'_F(GROUP_MA="P_{name}", CARA="K_T_D_N", VALE=(0.0, 0.0, {_num(k)})),'
        for name, (k, _) in classes.items()
    )
    return f"""\
# Essai C (lot 22) -- plaque DKT 1 m x 1 m, {C_N} x {C_N}, sur ressorts nodaux normaux.
# CREA_MAILLAGE/CREA_POI1 : une maille POI1 par noeud, un groupe par classe de
# raideur (interieur, bord, coin) ; DIS_T ; DISCRET/K_T_D_N. Raideur nodale =
# {C_KS:g} N/m^3 x aire tributaire. Pression uniforme {C_PRESSURE:g} Pa :
# deplacement attendu uniforme p/ks, somme des reactions des ressorts = p x aire.

DEBUT()

MAIL0 = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MAIL = CREA_MAILLAGE(
    MAILLAGE=MAIL0,
    CREA_POI1=(
        {poi1},
    ),
)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        _F(GROUP_MA="PLAQUE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
        _F(GROUP_MA=({spring_groups}), PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),
    ),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=_F(GROUP_MA="PLAQUE", EPAIS=0.01),
    DISCRET=(
        {discrets}
    ),
)

ACIER = DEFI_MATERIAU(ELAS=_F(E=2.1e11, NU=0.3))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="PLAQUE", MATER=ACIER))

# Blocage des mouvements dans le plan (DX, DY, DRZ) : A DX, DY ; B DY.
CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(_F(GROUP_NO="A", DX=0.0, DY=0.0), _F(GROUP_NO="B", DY=0.0)),
    PRES_REP=_F(GROUP_MA="PLAQUE", PRES={_num(C_PRESSURE)}),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

# Forces nodales calculees sur les seuls elements ressorts.
RESS = CALC_CHAMP(RESULTAT=RESU, GROUP_MA=({spring_groups}), FORCE="FORC_NODA")

TAB_W = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="DEPLACEMENT_DZ",
        GROUP_NO="TOUS",
        RESULTAT=RESU,
        NOM_CHAM="DEPL",
        NOM_CMP="DZ",
        OPERATION="EXTRACTION",
    )
)

TAB_R = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="RESULTANTE_RESSORTS",
        GROUP_NO="TOUS",
        RESULTAT=RESS,
        NOM_CHAM="FORC_NODA",
        RESULTANTE=("DX", "DY", "DZ"),
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE=TAB_W, UNITE=6, FORMAT_R="E20.12")

IMPR_TABLE(TABLE=TAB_R, UNITE=6, FORMAT_R="E20.12")

FIN()
"""


def cases() -> dict[str, tuple[Mesh, str]]:
    """Case stem -> (mesh, command file), path relative to the output dir."""
    out: dict[str, tuple[Mesh, str]] = {}
    for name, comment, kwargs in A_VARIANTS:
        out[f"essai_a/{name}"] = (a_mesh(), a_comm(name, comment, **kwargs))  # type: ignore[arg-type]
    out["essai_b/b3"] = (
        a_mesh(),
        a_comm(
            "b3",
            "console ELAS_COQUE avec RHO sous PESANTEUR (mesure par deplacement)",
            gravity_rho=1.0,
        ),
    )
    out["essai_b/b1"] = (b_mesh(), b_comm("b1", with_rho=False))
    out["essai_b/b2"] = (b_mesh(), b_comm("b2", with_rho=True))
    out["essai_b/b4"] = (
        b_mesh(),
        b_comm("b4", with_rho=False, gravity_group="P1"),
    )
    out["essai_c/c"] = (c_mesh(), c_comm())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for rel, (mesh, comm) in cases().items():
        stem = Path(rel)
        target = args.output_dir / stem
        target.parent.mkdir(parents=True, exist_ok=True)
        target.with_suffix(".mail").write_text(write_mesh(mesh), encoding="utf-8")
        target.with_suffix(".comm").write_text(comm, encoding="utf-8")
        target.with_suffix(".export").write_text(
            export_text(stem.name), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
