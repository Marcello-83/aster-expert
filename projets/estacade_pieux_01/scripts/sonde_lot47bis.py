"""Lot 47 bis -- probe S2: share of the shear between a DKT slab and a coplanar
POU_D_T beam that shares its nodes, near a point support.

Writes `references/cas/sonde_lot47bis.{mail,comm,export,connaissances.yaml}` and
`references/sonde_lot47bis_attendus.json` (the statics of the T-section, computed
here by hand, before any run). Native ASTER mesh, no Salome: a slab strip
X in [-0.60, 0.60] x Y in [-3.00, 3.00] (QUAD4 of 0.05 m, the band of a cap beam of
the jetty), a POU_D_T beam of 1.20 x 0.90 m along Y on the line X = 0 sharing the
slab nodes, the same section, materials and orientations as the jetty (E2, E7,
E13); two point supports at (0, -2.00) and (0, +2.00) on the beam nodes (the pile
heads), isostatic: P1 DX DY DZ DRY, P2 DX DZ. Load: a uniform pressure q on the slab
(FORCE_COQUE FZ), symmetric about X = 0 and Y = 0.

The T-section is statically determinate: each support carries W / 2, the total
shear and moment of the section at any Y are known exactly. The listing prints the
beam alone (`EFGE_ELNO`: VZ, MFY) and the slab nodes of three lines (`EFGE_NOEU`:
QY, MYY, MXY); the share of the slab is the difference (criteria:
docs/essais_lot47bis.md § 6, written before the run).

Run: `.venv/bin/python projets/estacade_pieux_01/scripts/sonde_lot47bis.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CAS = PROJECT / "references" / "cas"
NAME = "sonde_lot47bis"

E_C, NU_C = 34.0e9, 0.2
THICK = 0.40
CAP_HY, CAP_HZ = 1.20, 0.90
Q = 10.0e3
H = 0.05
NX, NY = 24, 120
X0, Y0 = -0.60, -3.00
Y_SUPPORT = 2.00
LINES = {"L_M190": -1.90, "L_M200": -2.00, "L_P000": 0.00}


def _x(i: int) -> float:
    return round(X0 + H * i, 9)


def _y(j: int) -> float:
    return round(Y0 + H * j, 9)


def node(i: int, j: int) -> str:
    return f"N{i:02d}_{j:03d}"


def _j(y: float) -> int:
    return round((y - Y0) / H)


def mesh_text() -> str:
    lines = [
        "TITRE",
        "Sonde S2 du lot 47 bis (estacade_pieux_01)",
        "FINSF",
        "",
        "COOR_3D",
    ]
    for i in range(NX + 1):
        for j in range(NY + 1):
            lines.append(f"{node(i, j)} {_x(i):.6f} {_y(j):.6f} 0.000000")
    lines += ["FINSF", "", "QUAD4"]
    quads = []
    for i in range(NX):
        for j in range(NY):
            m = f"Q{i:02d}_{j:03d}"
            quads.append(m)
            lines.append(
                f"{m} {node(i, j)} {node(i + 1, j)} {node(i + 1, j + 1)} {node(i, j + 1)}"
            )
    ic = NX // 2
    lines += ["FINSF", "", "SEG2"]
    beams = []
    for j in range(NY):
        m = f"C{j:03d}"
        beams.append(m)
        lines.append(f"{m} {node(ic, j)} {node(ic, j + 1)}")
    lines += ["FINSF", ""]
    for g, ms in (("DALLE", quads), ("CHEV", beams)):
        lines += ["GROUP_MA", g]
        lines += ["  " + " ".join(ms[k : k + 8]) for k in range(0, len(ms), 8)]
        lines += ["FINSF", ""]
    groups = {
        "P1": [node(ic, _j(-Y_SUPPORT))],
        "P2": [node(ic, _j(Y_SUPPORT))],
        "APPUIS": [node(ic, _j(-Y_SUPPORT)), node(ic, _j(Y_SUPPORT))],
        "COIN": [node(0, 0)],
    }
    for name, y in LINES.items():
        groups[name] = [node(i, _j(y)) for i in range(NX + 1)]
    for g, ns in groups.items():
        lines += ["GROUP_NO", g]
        lines += ["  " + " ".join(ns[k : k + 8]) for k in range(0, len(ns), 8)]
        lines += ["FINSF", ""]
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def expected() -> dict[str, object]:
    """Statics of the T-section under q on the whole strip (width b, length L)."""
    b = NX * H
    length = NY * H
    w = Q * b * length
    console = length / 2.0 - Y_SUPPORT

    def shear_span(y: float) -> float:
        """|V| of the section at y, between the supports (y in (-2, 2))."""
        return abs(w / 2.0 - Q * b * (y + length / 2.0))

    def moment(y: float) -> float:
        """Moment of the section at y (sagging positive), y in [-2, 2]."""
        a = y + length / 2.0
        return w / 2.0 * (y + Y_SUPPORT) - Q * b * a * a / 2.0

    return {
        "q_Pa": Q,
        "largeur_bande_m": b,
        "longueur_m": length,
        "W_N": w,
        "reaction_par_appui_N": w / 2.0,
        "console_m": console,
        "V_total_Y_m1p90_N": shear_span(-1.90),
        "M_total_Y_m2p00_Nm": moment(-2.00),
        "M_total_Y_0_Nm": moment(0.0),
    }


def comm_text() -> str:
    return f"""# Sonde S2 du lot 47 bis (estacade_pieux_01) : section en T, dalle DKT et poutre
# POU_D_T coplanaires à nœuds partagés, deux appuis ponctuels, pression uniforme.
# Généré par projets/estacade_pieux_01/scripts/sonde_lot47bis.py : ne pas éditer.

DEBUT(CODE="OUI")

MAIL = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

# CA-028, CA-045 : normales de la dalle +Z, MXX et MYY > 0 tendent la face supérieure.
MAIL = MODI_MAILLAGE(
    reuse=MAIL,
    MAILLAGE=MAIL,
    ORIE_NORM_COQUE=_F(GROUP_MA=("DALLE",), VECT_NORM=(0.0, 0.0, 1.0), GROUP_NO="COIN"),
)

MODELE = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=(
        _F(GROUP_MA=("DALLE",), PHENOMENE="MECANIQUE", MODELISATION="DKT"),
        _F(GROUP_MA=("CHEV",), PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),
    ),
)

BETON = DEFI_MATERIAU(ELAS=_F(E={E_C!r}, NU={NU_C!r}))

CARA = AFFE_CARA_ELEM(
    MODELE=MODELE,
    COQUE=_F(GROUP_MA="DALLE", EPAIS={THICK!r}, ANGL_REP=(0.0, 0.0)),
    POUTRE=_F(GROUP_MA="CHEV", SECTION="RECTANGLE", CARA=("HY", "HZ"), VALE=({CAP_HY!r}, {CAP_HZ!r})),
    ORIENTATION=_F(GROUP_MA="CHEV", CARA="VECT_Y", VALE=(-1.0, 0.0, 0.0)),
)

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(GROUP_MA=("DALLE", "CHEV"), MATER=BETON))

# Appuis ponctuels isostatiques sur les nœuds de la poutre (têtes de pieux).
CL = AFFE_CHAR_MECA(
    MODELE=MODELE,
    DDL_IMPO=(
        _F(GROUP_NO="P1", DX=0.0, DY=0.0, DZ=0.0, DRY=0.0),
        _F(GROUP_NO="P2", DX=0.0, DZ=0.0),
    ),
)
CH_Q = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="DALLE", FZ={-Q!r}))

RESU = MECA_STATIQUE(
    MODELE=MODELE, CHAM_MATER=CHMAT, CARA_ELEM=CARA, EXCIT=(_F(CHARGE=CL), _F(CHARGE=CH_Q))
)
RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, GROUP_MA="DALLE", CONTRAINTE=("EFGE_NOEU",))
RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, GROUP_MA="CHEV", CONTRAINTE=("EFGE_ELNO",))
RESU = CALC_CHAMP(reuse=RESU, RESULTAT=RESU, FORCE=("REAC_NODA",))

T_REAC = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="S2_REAC",
        RESULTAT=RESU,
        NOM_CHAM="REAC_NODA",
        TOUT_ORDRE="OUI",
        GROUP_NO=("APPUIS",),
        RESULTANTE=("DX", "DY", "DZ"),
    )
)
IMPR_TABLE(TABLE=T_REAC, UNITE=6, FORMAT_R="E20.12")
T_POU = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU,
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
        GROUP_MA=("CHEV",),
    )
)
IMPR_TABLE(TABLE=T_POU, UNITE=6, FORMAT_R="E20.12", TITRE="S2_EFGE_POUTRE")
{"".join(_line_table(name) for name in LINES)}
FIN()
"""


def _line_table(name: str) -> str:
    return f"""T_{name} = POST_RELEVE_T(
    ACTION=_F(
        OPERATION="EXTRACTION",
        INTITULE="S2_{name}",
        RESULTAT=RESU,
        NOM_CHAM="EFGE_NOEU",
        TOUT_ORDRE="OUI",
        GROUP_NO=("{name}",),
        NOM_CMP=("QX", "QY", "MXX", "MYY", "MXY"),
    )
)
IMPR_TABLE(TABLE=T_{name}, UNITE=6, FORMAT_R="E20.12")
"""


EXPORT = f"""P time_limit 600
P memory_limit 2048
P ncpus 1
P mpi_nbcpu 1
P mpi_nbnoeud 1
F comm {NAME}.comm D 1
F mail {NAME}.mail D 20
"""
KNOWLEDGE = """# Connaissances appliquées par la sonde S2 du lot 47 bis (lot 46, fichier compagnon).
schema_version: 1
project: estacade_pieux_01
applied:
  - id: CA-028
    how: "normales de la dalle orientées +Z par ORIE_NORM_COQUE avant la charge"
  - id: CA-045
    how: "MYY > 0 tend la face du côté de la normale (face supérieure)"
  - id: CA-037
    how: "poutre de Timoshenko POU_D_T, section RECTANGLE (E13)"
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
