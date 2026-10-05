"""Lot 47 -- probe of the commands the knowledge base does not cover yet.

Writes `references/cas/sonde_lot47.{mail,comm,export,connaissances.yaml}` and
`references/sonde_lot47_attendus.json` (the expected values, computed here by
hand, before any run). Native ASTER mesh, no Salome: a 1.0 x 0.6 m DKT plate
(2 x 2 QUAD4), a POU_D_T cap beam along Y sharing the plate nodes at x = 0, a
POU_D_T pile hanging under the node (0, 0.3, 0) with a DIS_T spring at z = -0.5,
and an edge (SEG2) along y = 0.6. Isostatic supports: P0 (0, 0.3, 0) DX DY DZ,
Q (1, 0.3, 0) DY DZ, R (0, 0, 0) DZ.

What the probe establishes (criteria written in `docs/essais_lot47.md` before
the run):

- T1, uniform temperature on the plate (CREA_RESU/PREP_VARC of a NOEU_TEMP_R
  field TEMP_MIL/INF/SUP, as hsls01a) and on the cap beam (CHAM_GD with TEMP, as
  ssll12a), two AFFE_VARC occurrences: free expansion, DX(Q) = alpha dT 1.0 and
  DY(y = 0.6) - DY(y = 0) = alpha dT 0.6, membrane forces and beam N nil;
- T2, MACRO_ELAS_MULT (one factorisation, several CAS_CHARGE) with PESANTEUR on a
  model holding a DIS_T spring of zero mass (DIAG-004), FORCE_COQUE FZ and FX,
  FORCE_ARETE FZ on the SEG2 edge of a DKT plate: each resultant equals the
  declared load;
- the CERCLE section with (R, EP) of the equivalent tube reproduces the area of
  table B2 (pile weight);
- the reading of a `mult_elas` result by POST_RELEVE_T and CALC_CHAMP.

Run: `.venv/bin/python projets/estacade_pieux_01/scripts/sonde_lot47.py`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CAS = PROJECT / "references" / "cas"
NAME = "sonde_lot47"

ALPHA = 1.0e-5
DT = 27.5
E_C, NU_C, GAMMA_C = 34.0e9, 0.2, 25.0e3
E_S, NU_S, GAMMA_S = 210.0e9, 0.3, 78.5e3
G = 9.81
THICK = 0.40
CAP_HY, CAP_HZ = 1.20, 0.90
A_PILE_CM2, I_PILE_CM4 = 305.30, 155063.0
K_SPRING = 3500.0e3
P_G2, P_FR, Q_EDGE = 8080.0, 4070.0, 500.0

XS = (0.0, 0.5, 1.0)
YS = (0.0, 0.3, 0.6)
LX, LY = 1.0, 0.6


def equivalent_tube(area_cm2: float, inertia_cm4: float) -> tuple[float, float]:
    """(R, EP) in m of the uniform tube of area A and inertia I:
    I / A = (R^2 + r^2) / 4 and A / pi = R^2 - r^2."""
    s = 4.0 * inertia_cm4 / area_cm2
    d = area_cm2 / math.pi
    r_out = math.sqrt((s + d) / 2.0)
    r_in = math.sqrt((s - d) / 2.0)
    return r_out / 100.0, (r_out - r_in) / 100.0


def node_name(i: int, j: int) -> str:
    return f"N{i}{j}"


def mesh_text() -> str:
    lines = ["TITRE", "Sonde du lot 47 (estacade_pieux_01)", "FINSF", "", "COOR_3D"]
    for i, x in enumerate(XS):
        for j, y in enumerate(YS):
            lines.append(f"{node_name(i, j)} {x:.6f} {y:.6f} 0.000000")
    lines += ["NP1 0.000000 0.300000 -0.500000", "NP2 0.000000 0.300000 -1.000000"]
    lines += ["FINSF", "", "QUAD4"]
    quads = []
    for i in range(2):
        for j in range(2):
            m = f"Q{i}{j}"
            quads.append(m)
            lines.append(
                f"{m} {node_name(i, j)} {node_name(i + 1, j)} "
                f"{node_name(i + 1, j + 1)} {node_name(i, j + 1)}"
            )
    lines += ["FINSF", "", "SEG2"]
    lines += ["C1 N00 N01", "C2 N01 N02", "P1 N01 NP1", "P2 NP1 NP2"]
    lines += ["R1 N02 N12", "R2 N12 N22"]
    lines += ["FINSF", "", "POI1", "K1 NP1", "FINSF", ""]
    groups = {
        "DALLE": quads,
        "CHEV": ["C1", "C2"],
        "PIEU": ["P1", "P2"],
        "RIVE": ["R1", "R2"],
        "RESS": ["K1"],
    }
    for g, ms in groups.items():
        lines += ["GROUP_MA", g, "  " + " ".join(ms), "FINSF", ""]
    nodes = {"P0": "N01", "Q": "N21", "R": "N00", "Y0": "N00", "Y6": "N02"}
    nodes["APPUIS"] = "N01 N21 N00"
    nodes["PLAQUE"] = " ".join(node_name(i, j) for i in range(3) for j in range(3))
    for g, ns in nodes.items():
        lines += ["GROUP_NO", f"{g} {ns}", "FINSF", ""]
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def expected() -> dict[str, object]:
    radius, ep = equivalent_tube(A_PILE_CM2, I_PILE_CM4)
    area_pile = math.pi * (radius**2 - (radius - ep) ** 2)
    plate_w = GAMMA_C * LX * LY * THICK
    cap_w = GAMMA_C * CAP_HY * CAP_HZ * LY
    pile_w = GAMMA_S * area_pile * 1.0
    return {
        "tube_equivalent_m": {"R": radius, "EP": ep},
        "aire_pieu_m2": area_pile,
        "aire_pieu_b2_m2": A_PILE_CM2 * 1e-4,
        "T1": {
            "DX_Q_m": ALPHA * DT * LX,
            "DY_Y6_moins_Y0_m": ALPHA * DT * LY,
            "NXX_NYY_N_par_m": 0.0,
            "N_chevetre_N": 0.0,
        },
        "T2": {
            "PP_DZ_N": -(plate_w + cap_w + pile_w),
            "PP_detail_N": {"plaque": plate_w, "chevetre": cap_w, "pieu": pile_w},
            "G2_DZ_N": -P_G2 * LX * LY,
            "FR_DX_N": P_FR * LX * LY,
            "GC_DZ_N": -Q_EDGE * LX,
        },
    }


def comm_text() -> str:
    radius, ep = equivalent_tube(A_PILE_CM2, I_PILE_CM4)
    return f"""# Sonde du lot 47 (estacade_pieux_01) : température coque + poutre, MACRO_ELAS_MULT,
# FORCE_ARETE sur arête de DKT, section CERCLE, ressort DIS_T sans masse sous PESANTEUR.
# Généré par projets/estacade_pieux_01/scripts/sonde_lot47.py : ne pas éditer.

DEBUT(CODE="OUI")

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MODELE = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        _F(GROUP_MA=("DALLE", "RIVE"), PHENOMENE="MECANIQUE", MODELISATION="DKT"),
        _F(GROUP_MA=("CHEV", "PIEU"), PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),
        _F(GROUP_MA=("RESS",), PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),
    ),
)

BETON = DEFI_MATERIAU(ELAS=_F(E={E_C!r}, NU={NU_C!r}, RHO={GAMMA_C / G!r}, ALPHA={ALPHA!r}))
ACIER = DEFI_MATERIAU(ELAS=_F(E={E_S!r}, NU={NU_S!r}, RHO={GAMMA_S / G!r}, ALPHA={ALPHA!r}))

CARA = AFFE_CARA_ELEM(
    MODELE=MODELE,
    COQUE=_F(GROUP_MA="DALLE", EPAIS={THICK!r}, ANGL_REP=(0.0, 0.0)),
    POUTRE=(
        _F(GROUP_MA="CHEV", SECTION="RECTANGLE", CARA=("HY", "HZ"), VALE=({CAP_HY!r}, {CAP_HZ!r})),
        _F(GROUP_MA="PIEU", SECTION="CERCLE", CARA=("R", "EP"), VALE=({radius!r}, {ep!r})),
    ),
    ORIENTATION=(
        _F(GROUP_MA="CHEV", CARA="VECT_Y", VALE=(-1.0, 0.0, 0.0)),
        _F(GROUP_MA="PIEU", CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),
    ),
    DISCRET=(
        _F(GROUP_MA="RESS", CARA="K_T_D_N", REPERE="GLOBAL", VALE=({K_SPRING!r}, {K_SPRING!r}, 0.0)),
        _F(GROUP_MA="RESS", CARA="M_T_D_N", VALE=(0.0,)),
    ),
)

CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(_F(GROUP_MA=("DALLE", "CHEV"), MATER=BETON), _F(GROUP_MA="PIEU", MATER=ACIER)),
)

CL = AFFE_CHAR_MECA(
    MODELE=MODELE,
    DDL_IMPO=(
        _F(GROUP_NO="P0", DX=0.0, DY=0.0, DZ=0.0),
        _F(GROUP_NO="Q", DY=0.0, DZ=0.0),
        _F(GROUP_NO="R", DZ=0.0),
    ),
)

# T1 : température uniforme sur la plaque (PREP_VARC, comme hsls01a) et sur le
# chevêtre (CHAM_GD TEMP, comme ssll12a) ; le pieu n'en reçoit pas.
T_COQ = CREA_CHAMP(
    OPERATION="AFFE",
    TYPE_CHAM="NOEU_TEMP_R",
    MAILLAGE=MAIL,
    AFFE=_F(GROUP_MA="DALLE", NOM_CMP=("TEMP_MIL", "TEMP_INF", "TEMP_SUP"), VALE=({DT!r}, {DT!r}, {DT!r})),
)
T_COQ_R = CREA_RESU(
    OPERATION="AFFE", TYPE_RESU="EVOL_THER", AFFE=_F(NOM_CHAM="TEMP", CHAM_GD=T_COQ, INST=0.0)
)
T_COQ_P = CREA_RESU(
    OPERATION="PREP_VARC",
    TYPE_RESU="EVOL_THER",
    PREP_VARC=_F(MODELE=MODELE, CARA_ELEM=CARA, EVOL_THER=T_COQ_R, GROUP_MA="DALLE"),
)
T_POU = CREA_CHAMP(
    OPERATION="AFFE",
    TYPE_CHAM="NOEU_TEMP_R",
    MAILLAGE=MAIL,
    AFFE=_F(GROUP_MA="CHEV", NOM_CMP="TEMP", VALE={DT!r}),
)
CHMAT_T = AFFE_MATERIAU(
    MAILLAGE=MAIL,
    AFFE=(_F(GROUP_MA=("DALLE", "CHEV"), MATER=BETON), _F(GROUP_MA="PIEU", MATER=ACIER)),
    AFFE_VARC=(
        _F(GROUP_MA="DALLE", NOM_VARC="TEMP", EVOL=T_COQ_P, NOM_CHAM="TEMP", VALE_REF=0.0),
        _F(GROUP_MA="CHEV", NOM_VARC="TEMP", CHAM_GD=T_POU, VALE_REF=0.0),
    ),
)
RESU_T = MECA_STATIQUE(MODELE=MODELE, CHAM_MATER=CHMAT_T, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CL))
RESU_T = CALC_CHAMP(
    reuse=RESU_T, RESULTAT=RESU_T, CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"), FORCE=("REAC_NODA",)
)
T_T1D = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="T1_DEPL",
        RESULTAT=RESU_T,
        NOM_CHAM="DEPL",
        TOUT_ORDRE="OUI",
        GROUP_NO=("PLAQUE",),
        NOM_CMP=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_T1D, UNITE=6, FORMAT_R="E20.12")
T_T1E = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU_T,
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP=("NXX", "NYY", "NXY", "MXX", "MYY"),
        GROUP_MA="DALLE",
    )
)
IMPR_TABLE(TABLE=T_T1E, UNITE=6, FORMAT_R="E20.12", TITRE="T1_EFGE_DALLE")
T_T1C = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU_T,
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
        GROUP_MA=("CHEV", "PIEU"),
    )
)
IMPR_TABLE(TABLE=T_T1C, UNITE=6, FORMAT_R="E20.12", TITRE="T1_EFGE_POUTRES")
T_T1R = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="T1_REAC",
        RESULTAT=RESU_T,
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO=("APPUIS",),
        RESULTANTE=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_T1R, UNITE=6, FORMAT_R="E20.12")

# T2 : MACRO_ELAS_MULT, une factorisation pour quatre cas.
CH_PP = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE={G!r}, DIRECTION=(0.0, 0.0, -1.0)))
CH_G2 = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="DALLE", FZ={-P_G2!r}))
CH_FR = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="DALLE", FX={P_FR!r}))
CH_GC = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_ARETE=_F(GROUP_MA="RIVE", FZ={-Q_EDGE!r}))
MULT = MACRO_ELAS_MULT(
    MODELE=MODELE,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    CHAR_MECA_GLOBAL=CL,
    CAS_CHARGE=(
        _F(NOM_CAS="PP", CHAR_MECA=CH_PP),
        _F(NOM_CAS="G2", CHAR_MECA=CH_G2),
        _F(NOM_CAS="FR", CHAR_MECA=CH_FR),
        _F(NOM_CAS="GC", CHAR_MECA=CH_GC),
    ),
)
MULT = CALC_CHAMP(
    reuse=MULT, RESULTAT=MULT, CONTRAINTE=("EFGE_ELNO", "EFGE_NOEU"), FORCE=("REAC_NODA",)
)
T_T2R = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="T2_REAC",
        RESULTAT=MULT,
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO=("APPUIS",),
        RESULTANTE=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_T2R, UNITE=6, FORMAT_R="E20.12")
T_T2P = CREA_TABLE(
    RESU=_F(
        RESULTAT=MULT,
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
        GROUP_MA=("PIEU",),
    )
)
IMPR_TABLE(TABLE=T_T2P, UNITE=6, FORMAT_R="E20.12", TITRE="T2_EFGE_PIEU")

IMPR_RESU(
    FORMAT="MED",
    UNITE=80,
    RESU=(
        _F(RESULTAT=MULT, NOM_RESU_MED="MULT", NOM_CHAM=("DEPL", "EFGE_NOEU"), CARA_ELEM=CARA),
        _F(RESULTAT=RESU_T, NOM_RESU_MED="TEMP", NOM_CHAM=("DEPL",), CARA_ELEM=CARA),
    ),
)

FIN()
"""


EXPORT = f"""P time_limit 600
P memory_limit 2048
P ncpus 1
P mpi_nbcpu 1
P mpi_nbnoeud 1
F comm {NAME}.comm D 1
F mail {NAME}.mail D 20
F rmed {NAME}.rmed R 80
"""

KNOWLEDGE = """# Connaissances appliquées par la sonde du lot 47 (lot 46, fichier compagnon).
schema_version: 1
project: estacade_pieux_01
applied:
  - id: DIAG-004
    how: "masse M_T_D_N nulle affectée au ressort DIS_T, le modèle portant PESANTEUR"
  - id: PAT-001
    how: "ressort nodal par CREA_POI1 implicite (maille POI1 du maillage), K_T_D_N par classe"
  - id: CA-048
    how: "charge surfacique de plaque par FORCE_COQUE en FZ global, poids par PESANTEUR et RHO"
  - id: CA-037
    how: "poutre de Timoshenko POU_D_T (E13)"
"""


def main() -> None:
    CAS.mkdir(parents=True, exist_ok=True)
    (CAS / f"{NAME}.mail").write_text(mesh_text(), encoding="utf-8")
    (CAS / f"{NAME}.comm").write_text(comm_text(), encoding="utf-8")
    (CAS / f"{NAME}.export").write_text(EXPORT, encoding="utf-8")
    (CAS / f"{NAME}.connaissances.yaml").write_text(KNOWLEDGE, encoding="utf-8")
    out = PROJECT / "references" / f"{NAME}_attendus.json"
    out.write_text(
        json.dumps(expected(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(expected(), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
