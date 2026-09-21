"""Build the trial cases of lot 23 (post-processing under ELAS_COQUE).

Fully synthetic, native ASCII mesh format, deterministic (a test replays it
byte for byte). Reuses the mesh writer and the ELAS_COQUE value set of lot 22
(`scripts/build_lot22_essais.py`). Files land in `data/examples/lot23_essais/`.

- D1 (`d1`): cantilever strip of essai A (DKT, ELAS_COQUE, bending values
  distinct from MEMB * EPAIS^2 / 12), tip line load. Generalised forces (nodes,
  Gauss points), FORC_NODA, REAC_NODA against M(x) = P (L - x) / b and Q = P / b.
- D2 (`d2a`, `d2b`): D1 with EPAIS x2 and x0.5, ELAS_COQUE coefficients untouched.
- D3 (`d3`): D1 with CISA_L and CISA_T x1000.
- D4 (`d4`): two DKT plates under PESANTEUR (essai B geometry), ELAS_COQUE plate
  with RHO = 0, ELAS plate with its normal RHO.
- D5 (`d5a`, `d5b`): strip whose half x < 1 is ELAS_COQUE and half x > 1 is ELAS
  (same D = 1000 N.m/m), load at x = 0, support at x = 2 either by nodal discrete
  springs (`d5a`) or by imposed degrees of freedom (`d5b`).

Usage: python scripts/build_lot23_essais.py [--output-dir PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_lot22_essais as l22  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "data" / "examples" / "lot23_essais"

EPAIS = 0.01
# Spring stiffnesses of D5a (per support node): translation N/m, rotation N.m/rad.
D5_K_TRANSLATION = 1.0e6
D5_K_ROTATION = 1.0e5
# ELAS witness with the same bending stiffness as the strip: D = E h^3 / 12 = 1000.
D5_ELAS = "ELAS=_F(E=1.2e10, NU=0.0)"

_FIELDS = (
    # (table name, field, components)
    ("EFGE_ELNO", "EFGE_ELNO", ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")),
    ("EFGE_NOEU", "EFGE_NOEU", ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")),
    ("SIEF_ELGA", "SIEF_ELGA", ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")),
)


def _tables() -> str:
    out = []
    for name, field, cmps in _FIELDS:
        cmp_text = ", ".join(f'"{c}"' for c in cmps)
        if field == "SIEF_ELGA":
            # CREA_TABLE needs COOR_ELGA, which MEBODKT cannot compute (first attempt
            # of lot 23) : the Gauss-point values are printed by element instead.
            out.append(
                f"""\
IMPR_RESU(
    FORMAT="RESULTAT",
    UNITE=6,
    RESU=_F(RESULTAT=RESU, NOM_CHAM="{field}", NUME_ORDRE=1, NOM_CMP=({cmp_text})),
)
"""
            )
            continue
        out.append(
            f"""\
T_{name} = CREA_TABLE(
    RESU=_F(RESULTAT=RESU, NOM_CHAM="{field}", NUME_ORDRE=1, NOM_CMP=({cmp_text}), TOUT="OUI")
)

IMPR_TABLE(TABLE=T_{name}, UNITE=6, FORMAT_R="E20.12")
"""
        )
    return "\n".join(out)


def _resultant(title: str, field: str, group: str, table: str) -> str:
    return f"""\
{table} = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="{title}",
        GROUP_NO="{group}",
        RESULTAT=RESU,
        NOM_CHAM="{field}",
        RESULTANTE=("DX", "DY", "DZ"),
        MOMENT=("DRX", "DRY", "DRZ"),
        POINT=(0.0, 0.0, 0.0),
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE={table}, UNITE=6, FORMAT_R="E20.12")
"""


def strip_mesh() -> l22.Mesh:
    """Essai A strip plus a node group at mid-length (x = 1) and a group of the whole."""
    mesh = l22.a_mesh()
    per_row = l22.A_NY + 1
    mid = l22.A_NX // 2
    # Node ids follow `grid`: n = i * (ny + 1) + j + 1.
    mesh.groups_no["MILIEU"] = [mid * per_row + j + 1 for j in range(per_row)]
    mesh.groups_no["TOUS"] = sorted(mesh.nodes)
    return mesh


def d_comm(name: str, comment: str, *, epais: float, cisa_factor: float) -> str:
    values = dict(l22.A_MATERIAL)
    values["CISA_L"] *= cisa_factor
    values["CISA_T"] *= cisa_factor
    coef_text = l22._coefs(values)
    return f"""\
# Essai D (lot 23), variante {name} -- {comment}
# Bande console DKT, L = {l22.A_LENGTH} m, b = {l22.A_WIDTH} m, ELAS_COQUE de l'essai A,
# charge de bout q = {abs(l22.A_LINE_LOAD)} N/m, P = q b = {abs(l22.A_LINE_LOAD) * l22.A_WIDTH} N.
# Par unite de largeur : M(x) = P (L - x) / b, Q = P / b.

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA="PLAQUE", EPAIS={l22._num(epais)}, ANGL_REP=(0.0, 0.0)))

MAT = DEFI_MATERIAU(ELAS_COQUE=_F({coef_text}))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA="PLAQUE", MATER=MAT))

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=_F(GROUP_NO="ENCASTR", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    FORCE_ARETE=_F(GROUP_MA="BOUT", FZ={l22._num(l22.A_LINE_LOAD)}),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

RESU = CALC_CHAMP(
    reuse=RESU,
    RESULTAT=RESU,
    CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"),
    FORCE=("FORC_NODA", "REAC_NODA"),
)

T_DEPL = CREA_TABLE(
    RESU=_F(RESULTAT=RESU, NOM_CHAM="DEPL", NUME_ORDRE=1, NOM_CMP=("DZ", "DRY"), GROUP_NO=("MILIEU", "BOUT"))
)

IMPR_TABLE(TABLE=T_DEPL, UNITE=6, FORMAT_R="E20.12")

{_tables()}
{_resultant("REAC_NODA_ENCASTREMENT", "REAC_NODA", "ENCASTR", "T_REAC")}
{_resultant("FORC_NODA_ENCASTREMENT", "FORC_NODA", "ENCASTR", "T_FORC")}
{_resultant("FORC_NODA_TOUS", "FORC_NODA", "TOUS", "T_FTOUS")}
FIN()
"""


# --- D4 -------------------------------------------------------------------


def d4_comm() -> str:
    """Essai B geometry, ELAS_COQUE plate with RHO = 0 (ELAS plate keeps RHO)."""
    coefs = l22.b_coefficients(l22.B_THICK2)
    coefs["RHO"] = 0.0
    coef_text = l22._coefs(coefs)
    return f"""\
# Essai D4 (lot 23) -- plaque 2 en ELAS_COQUE avec RHO = 0, plaque 1 en ELAS + RHO = {l22.B_RHO_VOL}.
# PESANTEUR sur tout le modele ; resultante verticale des reactions par plaque
# (les valeurs de ELAS_COQUE sont isotropes : REAC_NODA y est exact, essai A5/A7 du lot 22).

DEBUT()

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=(
        _F(GROUP_MA="P1", EPAIS={l22._num(l22.B_THICK1)}),
        _F(GROUP_MA="P2", EPAIS={l22._num(l22.B_THICK2)}),
    ),
)

MAT1 = DEFI_MATERIAU(ELAS=_F(E={l22._num(l22.B_E)}, NU={l22._num(l22.B_NU)}, RHO={l22._num(l22.B_RHO_VOL)}))

MAT2 = DEFI_MATERIAU(ELAS_COQUE=_F({coef_text}))

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(_F(GROUP_MA="P1", MATER=MAT1), _F(GROUP_MA="P2", MATER=MAT2)),
)

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    DDL_IMPO=(
        _F(GROUP_NO=("A1", "A2"), DX=0.0, DY=0.0, DZ=0.0),
        _F(GROUP_NO=("B1", "B2"), DY=0.0, DZ=0.0),
        _F(GROUP_NO=("APP1", "APP2"), DZ=0.0),
    ),
    PESANTEUR=_F(GRAVITE={l22._num(l22.B_GRAVITY)}, DIRECTION=(0.0, 0.0, -1.0)),
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


# --- D5 -------------------------------------------------------------------


def d5_mesh() -> l22.Mesh:
    """Strip of essai A split at x = 1 : COQ (x < 1), ELA (x > 1); edges x = 0 and x = 2."""
    mesh = l22.Mesh("Bande mixte ELAS_COQUE / ELAS, essai D5 (lot 23)")
    ids, quads = l22.grid(
        mesh,
        x0=0.0,
        y0=0.0,
        lx=l22.A_LENGTH,
        ly=l22.A_WIDTH,
        nx=l22.A_NX,
        ny=l22.A_NY,
    )
    half = l22.A_NX // 2 * l22.A_NY  # quads are numbered i-major, ny per column
    mesh.groups_ma["COQ"] = [f"MA{q}" for q in quads[:half]]
    mesh.groups_ma["ELA"] = [f"MA{q}" for q in quads[half:]]
    for j in range(l22.A_NY):
        mesh.segs[j + 1] = (ids[(0, j)], ids[(0, j + 1)])
    mesh.groups_ma["BOUT0"] = [f"SG{m}" for m in sorted(mesh.segs)]
    mesh.groups_no["X0"] = [ids[(0, j)] for j in range(l22.A_NY + 1)]
    mesh.groups_no["X2"] = [ids[(l22.A_NX, j)] for j in range(l22.A_NY + 1)]
    mesh.groups_no["TOUS"] = sorted(mesh.nodes)
    return mesh


def d5_comm(name: str, *, springs: bool) -> str:
    coef_text = l22._coefs(l22.A_MATERIAL)
    load_note = f"P = {abs(l22.A_LINE_LOAD) * l22.A_WIDTH} N en x = 0 (bout ELAS_COQUE), appui en x = 2"
    if springs:
        mesh_step = """\
MAIL0 = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MAIL = CREA_MAILLAGE(MAILLAGE=MAIL0, CREA_POI1=_F(NOM_GROUP_MA="RESSORTS", GROUP_NO="X2"))
"""
        model = """\
MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        _F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
        _F(GROUP_MA="RESSORTS", PHENOMENE="MECANIQUE", MODELISATION="DIS_TR"),
    ),
)
"""
        cara = f"""\
CARA = AFFE_CARA_ELEM(
    MODELE=MO,
    COQUE=_F(GROUP_MA=("COQ", "ELA"), EPAIS={l22._num(EPAIS)}, ANGL_REP=(0.0, 0.0)),
    DISCRET=_F(
        GROUP_MA="RESSORTS",
        CARA="K_TR_D_N",
        VALE=({l22._num(D5_K_TRANSLATION)}, {l22._num(D5_K_TRANSLATION)}, {l22._num(D5_K_TRANSLATION)}, {l22._num(D5_K_ROTATION)}, {l22._num(D5_K_ROTATION)}, {l22._num(D5_K_ROTATION)}),
    ),
)
"""
        bc = ""
        post = """\
RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, GROUP_MA="RESSORTS", FORCE="FORC_NODA")

"""
        # The forces of the springs are read on POI1 elements only.
        tables = _resultant("FORC_NODA_RESSORTS", "FORC_NODA", "X2", "T_RESS")
        tables += "\n" + _resultant(
            "FORC_NODA_TOUS_RESSORTS", "FORC_NODA", "TOUS", "T_RESS_TOUS"
        )
        comment = "appui par ressorts DIS_TR nodaux en x = 2 : FORC_NODA restreint aux ressorts"
    else:
        mesh_step = 'MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)\n'
        model = """\
MO = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)
"""
        cara = f"""\
CARA = AFFE_CARA_ELEM(MODELE=MO, COQUE=_F(GROUP_MA=("COQ", "ELA"), EPAIS={l22._num(EPAIS)}, ANGL_REP=(0.0, 0.0)))
"""
        bc = 'DDL_IMPO=_F(GROUP_NO="X2", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),\n    '
        post = 'RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE=("FORC_NODA", "REAC_NODA"))\n\n'
        tables = _resultant("REAC_NODA_X2", "REAC_NODA", "X2", "T_REAC")
        tables += "\n" + _resultant(
            "REAC_NODA_TOUS", "REAC_NODA", "TOUS", "T_REAC_TOUS"
        )
        # Loaded end, carried by ELAS_COQUE elements only : the reaction must be nil.
        tables += "\n" + _resultant("REAC_NODA_X0", "REAC_NODA", "X0", "T_REAC_X0")
        comment = (
            "appui encastre en x = 2 : REAC_NODA sur des noeuds sans element ELAS_COQUE"
        )
    return f"""\
# Essai D5 (lot 23), variante {name} -- {comment}.
# Bande DKT L = {l22.A_LENGTH} m, b = {l22.A_WIDTH} m ; x < 1 : ELAS_COQUE (essai A), x > 1 : ELAS
# (E = 1.2e10, nu = 0, h = {EPAIS} : D = 1000 N.m/m, meme raideur de flexion). {load_note}.
# Moments pris autour de (0,0,0), point d'application de la charge : equilibre
# global attendu MY = 0, |MX| = P x 0.25 (charge centree sur la largeur), |RZ| = P.

DEBUT()

{mesh_step}
{model}
{cara}
MAT = DEFI_MATERIAU(ELAS_COQUE=_F({coef_text}))

MATE = DEFI_MATERIAU({D5_ELAS})

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(_F(GROUP_MA="COQ", MATER=MAT), _F(GROUP_MA="ELA", MATER=MATE)),
)

CHAR = AFFE_CHAR_MECA(
    MODELE=MO,
    {bc}FORCE_ARETE=_F(GROUP_MA="BOUT0", FZ={l22._num(l22.A_LINE_LOAD)}),
)

RESU = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CHAR))

{post}T_DEPL = POST_RELEVE_T(
    ACTION=_F(
        INTITULE="FLECHE_BOUT",
        GROUP_NO="X0",
        RESULTAT=RESU,
        NOM_CHAM="DEPL",
        NOM_CMP="DZ",
        OPERATION="EXTRACTION",
    )
)

IMPR_TABLE(TABLE=T_DEPL, UNITE=6, FORMAT_R="E20.12")

{tables}
FIN()
"""


def cases() -> dict[str, tuple[l22.Mesh, str]]:
    out: dict[str, tuple[l22.Mesh, str]] = {}
    out["essai_d1/d1"] = (
        strip_mesh(),
        d_comm("d1", "reference, EPAIS = 0.01", epais=EPAIS, cisa_factor=1.0),
    )
    out["essai_d2/d2a"] = (
        strip_mesh(),
        d_comm("d2a", "EPAIS x2", epais=2 * EPAIS, cisa_factor=1.0),
    )
    out["essai_d2/d2b"] = (
        strip_mesh(),
        d_comm("d2b", "EPAIS x0.5", epais=0.5 * EPAIS, cisa_factor=1.0),
    )
    out["essai_d3/d3"] = (
        strip_mesh(),
        d_comm("d3", "CISA_L et CISA_T x1000", epais=EPAIS, cisa_factor=1000.0),
    )
    out["essai_d4/d4"] = (l22.b_mesh(), d4_comm())
    out["essai_d5/d5a"] = (d5_mesh(), d5_comm("d5a", springs=True))
    out["essai_d5/d5b"] = (d5_mesh(), d5_comm("d5b", springs=False))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for rel, (mesh, comm) in cases().items():
        stem = Path(rel)
        target = args.output_dir / stem
        target.parent.mkdir(parents=True, exist_ok=True)
        target.with_suffix(".mail").write_text(l22.write_mesh(mesh), encoding="utf-8")
        target.with_suffix(".comm").write_text(comm, encoding="utf-8")
        target.with_suffix(".export").write_text(
            l22.export_text(stem.name), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
