"""Lot 39, étape 6 : essai minimal de `CALC_FERRAILLAGE` en `TYPE_STRUCTURE='2D'`
sur une plaque DKT d'un seul élément, efforts généralisés imposés, comparé au
module `aster_expert.rebar` (établir le fonctionnement de la commande, pas
dimensionner).

Plaque carrée 1 m x 1 m dans le plan XY, `QUAD4`, épaisseur 0,50 m, distance
parement-axe des armatures 0,05 m sur les deux faces, C35/45, B500B, ELU
fondamental (γc = 1,5, γs = 1,15, αcc = 1,0). Repère local par défaut (x_l =
projection de X). Efforts par mètre (N/m, N.m/m), `UNITE_CONTRAINTE='Pa'` ;
aucune option sensible aux unités (`FERR_MIN*`) n'est activée.

Critères écrits avant l'exécution : `docs/essais_lot39.md`, étape 6.

Usage : python scripts/build_lot39_plaque.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "examples" / "lot39_essais" / "plaque"
EPAIS, COVER = 0.50, 0.05
CMP = ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")
CASES = (
    ("mxx_p", {"MXX": 0.2e6}),
    ("mxx_m", {"MXX": -0.2e6}),
    ("nxx_t_mxx", {"NXX": 1.0e6, "MXX": 0.2e6}),
    ("nxx_c_mxx", {"NXX": -2.0e6, "MXX": 0.2e6}),
    ("mxx_mxy", {"MXX": 0.2e6, "MXY": 0.1e6}),
    ("mxy", {"MXY": 0.1e6}),
    ("nxx_t", {"NXX": 1.0e6}),
)


def _num(x: float) -> str:
    return repr(float(x))


def build_comm() -> str:
    fields = []
    for i, (label, efforts) in enumerate(CASES, start=1):
        vale = ", ".join(_num(efforts.get(c, 0.0)) for c in CMP)
        fields.append(
            f"""# instant {i} : {label}
CHEFF{i} = CREA_CHAMP(
    MAILLAGE=MA,
    OPERATION="AFFE",
    TYPE_CHAM="CART_SIEF_R",
    AFFE=_F(
        GROUP_MA="PLAQUE",
        NOM_CMP=("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY"),
        VALE=({vale}),
    ),
)
"""
        )
    affe = "\n".join(
        f'        _F(NOM_CHAM="EFGE_ELNO", CHAM_GD=CHEFF{i}, INST={float(i)}, '
        "MODELE=MODEL, CARA_ELEM=CARA),"
        for i in range(1, len(CASES) + 1)
    )
    insts = ", ".join(repr(float(i)) for i in range(1, len(CASES) + 1))
    return f"""# Lot 39, étape 6 : CALC_FERRAILLAGE en 2D sur une plaque DKT d'un élément.
# Produit par scripts/build_lot39_plaque.py ; critères : docs/essais_lot39.md.

DEBUT(CODE="OUI")

MA = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MODEL = AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=_F(GROUP_MA="PLAQUE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)

CARA = AFFE_CARA_ELEM(MODELE=MODEL, COQUE=_F(GROUP_MA="PLAQUE", EPAIS={_num(EPAIS)}))

{"".join(fields)}
RESU = CREA_RESU(
    OPERATION="AFFE",
    TYPE_RESU="EVOL_ELAS",
    AFFE=(
{affe}
    ),
)

RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="ELU",
    UNITE_CONTRAINTE="Pa",
    INST=({insts}),
    AFFE=(
        _F(
            TOUT="OUI",
            TYPE_STRUCTURE="2D",
            C_INF={_num(COVER)},
            C_SUP={_num(COVER)},
            FYK=500000000.0,
            FCK=35000000.0,
            EYS=210000000000.0,
            TYPE_DIAGRAMME="B2",
            ALPHA_CC=1.0,
            GAMMA_S=1.15,
            GAMMA_C=1.5,
        ),
    ),
)

T_FERR = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU,
        NOM_CHAM="FERR_ELEM",
        TOUT_ORDRE="OUI",
        NOM_CMP=("DNSXI", "DNSXS", "DNSYI", "DNSYS", "DNSXT", "DNSYT"),
        GROUP_MA="PLAQUE",
    )
)
IMPR_TABLE(TABLE=T_FERR, UNITE=6, FORMAT_R="E20.12", TITRE="FERR_LOT39_2D")

FIN()
"""


def mesh_text() -> str:
    return "\n".join(
        [
            "% lot39_plaque",
            "TITRE",
            "lot39_plaque",
            "FINSF",
            "",
            "COOR_3D",
            "N1 0.000000000000 0.000000000000 0.000000000000",
            "N2 1.000000000000 0.000000000000 0.000000000000",
            "N3 1.000000000000 1.000000000000 0.000000000000",
            "N4 0.000000000000 1.000000000000 0.000000000000",
            "FINSF",
            "",
            "QUAD4",
            "M1 N1 N2 N3 N4",
            "FINSF",
            "",
            "GROUP_MA",
            "PLAQUE",
            "  M1",
            "FINSF",
            "",
            "FIN",
            "",
        ]
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plaque.comm").write_text(build_comm(), "utf-8")
    (OUT / "plaque.mail").write_text(mesh_text(), "utf-8")
    (OUT / "plaque.export").write_text(
        "P time_limit 300\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        "P mpi_nbnoeud 1\nF comm plaque.comm D 1\nF mail plaque.mail D 20\n",
        "utf-8",
    )
    print(f"écrit {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
