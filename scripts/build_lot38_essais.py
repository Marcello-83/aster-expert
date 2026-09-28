"""Lot 38, étape 4 : essais `CALC_FERRAILLAGE` sur la section réelle de la poutre
de couronnement (2,50 m x 1,40 m, C35/45, B500B, enrobage 65 mm, décision D18).

Modèle : une poutre `POU_D_E` d'un seul élément avec des efforts imposés
(`CREA_CHAMP/CART_SIEF_R` -> `CREA_RESU`, même schéma que les cas tests officiels
`ssll13*`/`ssll18*`) -- l'élément accepté par `CALC_FERRAILLAGE` ne dépend pas de
la modélisation qui l'a produit (état des lieux, `docs/etat_des_lieux_lot38_
ferraillage.md`, §2). Quatre cas, N et M choisis pour illustrer les régimes de la
commande sur la section du projet, pas les valeurs réelles de la poutre (données
dans `docs/essais_lot38.md`) :

1. flexion simple (N = 0) ;
2. flexion composée avec compression ;
3. flexion composée avec traction ;
4. ELS quasi permanente (wk = 0,2 mm, décision D18).

Usage : python scripts/build_lot38_essais.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "examples" / "lot38_essais"

HY, HZ = 2.50, 1.40
COVER = 0.065
FCK, FYK = 35.0e6, 500.0e6
GAMMA_S, GAMMA_C, ALPHA_CC = 1.15, 1.5, 1.0
EYS = 210.0e9
ALPHA_E = 15.0
SIGS_ELS = 0.8 * FYK
SIGC_ELS = 0.6 * FCK
SIGC_ELS_QP = 0.45 * FCK
KT = 0.4
WMAX = 0.2e-3
PHI = 0.025

# (name, N [N], M [N.m])
CASES_ELU = [
    ("flexion_simple", 0.0, 2.183517e6),
    ("composee_compression", -5.0e6, 2.183517e6),
    ("composee_traction", 5.0e6, 2.183517e6),
]
CASE_ELS_QP = ("els_qp", -1.0e6, 0.5e6)


def _num(x: float) -> str:
    return repr(float(x))


def _affe_common() -> str:
    return f"""\
            TOUT="OUI",
            TYPE_STRUCTURE="1D",
            C_SUP_Y={_num(COVER)},
            C_INF_Y={_num(COVER)},
            C_SUP_Z={_num(COVER)},
            C_INF_Z={_num(COVER)},
            FYK={_num(FYK)},
            FCK={_num(FCK)},
            EYS={_num(EYS)},
            TYPE_DIAGRAMME="B2","""


def build_comm() -> str:
    n_elu = len(CASES_ELU)
    cheff_blocks = []
    affe_blocks = []
    for i, (name, n, m) in enumerate([*CASES_ELU, CASE_ELS_QP], start=1):
        cheff_blocks.append(f"""\
# cas {i} : {name} -- N = {n:g} N, MFZ = {m:g} N.m
CHEFF{i} = CREA_CHAMP(
    MAILLAGE=MA,
    OPERATION="AFFE",
    TYPE_CHAM="CART_SIEF_R",
    AFFE=_F(
        GROUP_MA="PoutreAB",
        NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
        VALE=({_num(n)}, 0.0, 0.0, 0.0, 0.0, {_num(m)}),
    ),
)
""")
        affe_blocks.append(
            f'        _F(NOM_CHAM="EFGE_ELNO", CHAM_GD=CHEFF{i}, INST={float(i)}, '
            "MODELE=MODEL, CARA_ELEM=CARA),"
        )
    affe_joined = "\n".join(affe_blocks)
    cheff_joined = "\n".join(cheff_blocks)
    elu_insts = ", ".join(f"{float(i)}" for i in range(1, n_elu + 1))
    qp_inst = float(n_elu + 1)
    return f"""\
# Lot 38, étape 4 : essais CALC_FERRAILLAGE sur la section réelle de la poutre de
# couronnement (2,50 m x 1,40 m, C35/45, B500B, enrobage 65 mm, décision D18).
# Modèle synthétique (efforts imposés) : voir scripts/build_lot38_essais.py et
# docs/essais_lot38.md (critère écrit avant l'exécution).

DEBUT(CODE="OUI")

MA = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MODEL = AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=_F(GROUP_MA="PoutreAB", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MODEL,
    POUTRE=_F(
        CARA=("HY", "HZ"),
        GROUP_MA=("PoutreAB",),
        SECTION="RECTANGLE",
        VALE=({_num(HY)}, {_num(HZ)}),
    ),
)

{cheff_joined}
RESU = CREA_RESU(
    OPERATION="AFFE",
    TYPE_RESU="EVOL_ELAS",
    AFFE=(
{affe_joined}
    ),
)

RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="ELU",
    UNITE_CONTRAINTE="Pa",
    INST=({elu_insts}),
    AFFE=(
        _F(
{_affe_common()}
            GAMMA_S={_num(GAMMA_S)},
            GAMMA_C={_num(GAMMA_C)},
            ALPHA_CC={_num(ALPHA_CC)},
        ),
    ),
)

RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="ELS_QP",
    UNITE_CONTRAINTE="Pa",
    INST=({qp_inst},),
    AFFE=(
        _F(
{_affe_common()}
            ALPHA_E={_num(ALPHA_E)},
            SIGC_INF_Y_ELS={_num(SIGC_ELS)},
            SIGC_SUP_Y_ELS={_num(SIGC_ELS)},
            SIGC_INF_Z_ELS={_num(SIGC_ELS)},
            SIGC_SUP_Z_ELS={_num(SIGC_ELS)},
            SIGS_ELS={_num(SIGS_ELS)},
            SIGC_ELS_QP={_num(SIGC_ELS_QP)},
            KT={_num(KT)},
            WMAX_INF_Y={_num(WMAX)},
            WMAX_SUP_Y={_num(WMAX)},
            WMAX_INF_Z={_num(WMAX)},
            WMAX_SUP_Z={_num(WMAX)},
            PHI_INF_Y={_num(PHI)},
            PHI_SUP_Y={_num(PHI)},
            PHI_INF_Z={_num(PHI)},
            PHI_SUP_Z={_num(PHI)},
        ),
    ),
)

COMP = ("AYS", "AYI", "AZS", "AZI", "AST", "ATOT", "DNSVOL", "CONSTRUC")

T_FERR = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU,
        NOM_CHAM="FERR_ELEM",
        TOUT_ORDRE="OUI",
        NOM_CMP=COMP,
        GROUP_MA="PoutreAB",
    )
)
IMPR_TABLE(TABLE=T_FERR, UNITE=6, FORMAT_R="E20.12", TITRE="FERR_LOT38")

FIN()
"""


def export_text() -> str:
    return (
        "P time_limit 300\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        "P mpi_nbnoeud 1\nF comm essais.comm D 1\nF mail essais.mail D 20\n"
    )


def mesh_text() -> str:
    """Single SEG2 element (group `PoutreAB`, maille `M1`), native ASTER format --
    same writer shape as `scripts/build_lot22_essais.write_mesh` (proven by many
    executions), minus the QUAD4 block this mesh has no use for."""
    lines = [
        "% essais_lot38",
        "TITRE",
        "essais_lot38",
        "FINSF",
        "",
        "COOR_3D",
        "N1 0.000000000000 0.000000000000 0.000000000000",
        "N2 1.000000000000 0.000000000000 0.000000000000",
        "FINSF",
        "",
        "SEG2",
        "M1 N1 N2",
        "FINSF",
        "",
        "GROUP_MA",
        "PoutreAB",
        "  M1",
        "FINSF",
        "",
        "FIN",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "essais.comm").write_text(build_comm(), encoding="utf-8")
    (OUT_DIR / "essais.export").write_text(export_text(), encoding="utf-8")
    (OUT_DIR / "essais.mail").write_text(mesh_text(), encoding="utf-8")
    print(f"écrit dans {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
