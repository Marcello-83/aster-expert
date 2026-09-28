"""Lot 39, étapes 1 bis et 2 : essais `CALC_FERRAILLAGE` minimaux sur la section
réelle de la poutre de couronnement (2,50 m x 1,40 m, C35/45, B500B, D18),
avec la distance parement-axe des armatures de D19 (0,10 m sur toutes les
faces, diamètre équivalent 40 mm).

Même schéma que le lot 38 et que les cas tests officiels `ssll13*` : une poutre
`POU_D_E` d'un seul élément, efforts imposés (`CREA_CHAMP/CART_SIEF_R` ->
`CREA_RESU`), puis `CALC_FERRAILLAGE` et impression de `FERR_ELEM`.

Quatre essais, un répertoire chacun (un `<F>` dans l'un n'arrête pas les autres) :

- `d19/` : les quatre cas du lot 38, refaits avec 0,10 m (étape 1 bis) ;
- `limites/` : ce que la commande fait en 1D (étape 2) -- faces et signes,
  flexion déviée, effort tranchant et torsion, ELS caractéristique ;
- `fermin/` : `FERR_MIN='EC2'` (ferraillage minimal, étape 2.1) ;
- `fiss/` : `FERR_MIN_FISS='EC2'` à l'ELS quasi permanent (étape 2.1) ;
- `fermin_mpa/` : `fermin/` en MPa et mm, pour départager une incohérence
  d'unités constatée en Pa (étape 2.1).

Critères écrits avant l'exécution : `docs/essais_lot39.md`.

Usage : python scripts/build_lot39_essais.py
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "examples" / "lot39_essais"

HY, HZ = 2.50, 1.40
COVER = 0.10  # D19
PHI = 0.040  # D19
FCK, FYK = 35.0e6, 500.0e6
GAMMA_S, GAMMA_C, ALPHA_CC = 1.15, 1.5, 1.0
EYS = 210.0e9
ALPHA_E = 15.0
SIGS_ELS = 0.8 * FYK
SIGC_ELS = 0.6 * FCK
SIGC_ELS_QP = 0.45 * FCK
KT = 0.4
WMAX = 0.2e-3
COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")


class Case(NamedTuple):
    label: str
    efforts: dict[str, float]  # N, N.m -- absent components are zero


class Call(NamedTuple):
    type_comb: str
    labels: tuple[str, ...]
    extra: tuple[tuple[str, str], ...] = ()


M38 = 2.183517e6

D19_CASES = (
    Case("flexion_simple", {"MFZ": M38}),
    Case("composee_compression", {"N": -5.0e6, "MFZ": M38}),
    Case("composee_traction", {"N": 5.0e6, "MFZ": M38}),
    Case("els_qp", {"N": -1.0e6, "MFZ": 0.5e6}),
)
D19_CALLS = (
    Call("ELU", ("flexion_simple", "composee_compression", "composee_traction")),
    Call("ELS_QP", ("els_qp",)),
)

LIMITES_CASES = (
    Case("mfz_1", {"MFZ": 1.0e6}),
    Case("mfz_m1", {"MFZ": -1.0e6}),
    Case("mfy_1", {"MFY": 1.0e6}),
    Case("mfy_m1", {"MFY": -1.0e6}),
    Case("devie_1", {"MFY": 1.0e6, "MFZ": 1.0e6}),
    Case("mfz_3", {"MFZ": 3.0e6}),
    Case("mfy_3", {"MFY": 3.0e6}),
    Case("devie_3", {"MFY": 3.0e6, "MFZ": 3.0e6}),
    Case("vy_2", {"VY": 2.0e6}),
    Case("vy_4", {"VY": 4.0e6}),
    Case("vz_4", {"VZ": 4.0e6}),
    Case("mt_2", {"MT": 2.0e6}),
    Case("mt_4", {"MT": 4.0e6}),
    Case("vy_4_mt_4", {"VY": 4.0e6, "MT": 4.0e6}),
    Case("vy_4_vz_4", {"VY": 4.0e6, "VZ": 4.0e6}),
    Case("els_mfz_2", {"MFZ": 2.0e6}),
    Case("els_mfy_1", {"MFY": 1.0e6}),
    Case("els_n_m3_mfz_4", {"N": -3.0e6, "MFZ": 4.0e6}),
    Case("qp_mfz_1", {"MFZ": 1.0e6}),
)
_ELU_LIMITES = tuple(
    c.label for c in LIMITES_CASES if not c.label.startswith(("els_", "qp_"))
)
LIMITES_CALLS = (
    Call("ELU", _ELU_LIMITES),
    Call("ELS", ("els_mfz_2", "els_mfy_1", "els_n_m3_mfz_4")),
    Call("ELS_QP", ("qp_mfz_1",)),
)

FERMIN_CASES = (
    Case("mfz_1_sans_min", {"MFZ": 1.0e6}),
    Case("mfz_1_min", {"MFZ": 1.0e6}),
    Case("nul_min", {}),
    Case("vy_4_min", {"VY": 4.0e6}),
)
FERMIN_CALLS = (
    Call("ELU", ("mfz_1_sans_min",)),
    Call(
        "ELU",
        ("mfz_1_min", "nul_min", "vy_4_min"),
        (("FERR_MIN", '"EC2"'),),
    ),
)

FISS_CASES = (
    Case("qp_mfz_1_sans", {"MFZ": 1.0e6}),
    Case("qp_mfz_1_fiss", {"MFZ": 1.0e6}),
    Case("qp_nul_fiss", {}),
)
FISS_CALLS = (
    Call("ELS_QP", ("qp_mfz_1_sans",)),
    Call("ELS_QP", ("qp_mfz_1_fiss", "qp_nul_fiss"), (("FERR_MIN_FISS", '"EC2"'),)),
)


class Units(NamedTuple):
    """Unit system of an essai: `UNITE_CONTRAINTE` fixes the length unit too
    (`U4.81.42`, UNITE_CONTRAINTE : 'Pa' with m, 'MPa' with mm)."""

    name: str
    length: float  # factor from m
    stress: float  # factor from Pa


SI = Units("Pa", 1.0, 1.0)
MPA_MM = Units("MPa", 1000.0, 1.0e-6)


def _num(x: float) -> str:
    return repr(float(x))


def _affe(type_comb: str, extra: tuple[tuple[str, str], ...], units: Units = SI) -> str:
    cover, s = COVER * units.length, units.stress
    lines = [
        'TOUT="OUI"',
        'TYPE_STRUCTURE="1D"',
        f"C_SUP_Y={_num(cover)}",
        f"C_INF_Y={_num(cover)}",
        f"C_SUP_Z={_num(cover)}",
        f"C_INF_Z={_num(cover)}",
        f"FYK={_num(FYK * s)}",
        f"FCK={_num(FCK * s)}",
        f"EYS={_num(EYS * s)}",
        'TYPE_DIAGRAMME="B2"',
        f"ALPHA_CC={_num(ALPHA_CC)}",
    ]
    if type_comb == "ELU":
        lines += [f"GAMMA_S={_num(GAMMA_S)}", f"GAMMA_C={_num(GAMMA_C)}"]
    else:
        lines += [
            f"ALPHA_E={_num(ALPHA_E)}",
            f"SIGS_ELS={_num(SIGS_ELS * s)}",
            *(
                f"SIGC_{f}_ELS={_num(SIGC_ELS * s)}"
                for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
            ),
        ]
    if type_comb == "ELS_QP":
        lines += [f"SIGC_ELS_QP={_num(SIGC_ELS_QP * s)}", f"KT={_num(KT)}"]
        lines += [
            f"WMAX_{f}={_num(WMAX * units.length)}"
            for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
        ]
        lines += [
            f"PHI_{f}={_num(PHI * units.length)}"
            for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
        ]
    lines += [f"{k}={v}" for k, v in extra]
    return "\n".join(f"            {line}," for line in lines)


def build_comm(
    title: str,
    cases: tuple[Case, ...],
    calls: tuple[Call, ...],
    units: Units = SI,
) -> str:
    """Moments scale with the length unit (N.m -> N.mm), forces do not."""
    index = {c.label: i for i, c in enumerate(cases, start=1)}
    blocks = []
    for i, case in enumerate(cases, start=1):
        vale = ", ".join(
            _num(case.efforts.get(c, 0.0) * (units.length if c[0] == "M" else 1.0))
            for c in COMPONENTS
        )
        blocks.append(
            f"""# instant {i} : {case.label}
CHEFF{i} = CREA_CHAMP(
    MAILLAGE=MA,
    OPERATION="AFFE",
    TYPE_CHAM="CART_SIEF_R",
    AFFE=_F(
        GROUP_MA="PoutreAB",
        NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"),
        VALE=({vale}),
    ),
)
"""
        )
    affe = "\n".join(
        f'        _F(NOM_CHAM="EFGE_ELNO", CHAM_GD=CHEFF{i}, INST={float(i)}, '
        "MODELE=MODEL, CARA_ELEM=CARA),"
        for i in range(1, len(cases) + 1)
    )
    ferr = []
    for call in calls:
        insts = ", ".join(repr(float(index[label])) for label in call.labels)
        ferr.append(
            f"""RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="{call.type_comb}",
    UNITE_CONTRAINTE="{units.name}",
    INST=({insts},),
    AFFE=(
        _F(
{_affe(call.type_comb, call.extra, units)}
        ),
    ),
)
"""
        )
    return f"""# Lot 39 : {title}
# Section de la poutre de couronnement 2,50 m x 1,40 m, C35/45, B500B (D18),
# distance parement-axe des armatures 0,10 m sur toutes les faces (D19).
# Produit par scripts/build_lot39_essais.py ; critères : docs/essais_lot39.md.

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
        VALE=({_num(HY * units.length)}, {_num(HZ * units.length)}),
    ),
)

{"".join(blocks)}
RESU = CREA_RESU(
    OPERATION="AFFE",
    TYPE_RESU="EVOL_ELAS",
    AFFE=(
{affe}
    ),
)

{"".join(ferr)}
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
IMPR_TABLE(TABLE=T_FERR, UNITE=6, FORMAT_R="E20.12", TITRE="FERR_LOT39")

FIN()
"""


def export_text(name: str) -> str:
    return (
        "P time_limit 300\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm {name}.comm D 1\nF mail {name}.mail D 20\n"
    )


def mesh_text(title: str, units: Units = SI) -> str:
    """Single SEG2 element (group `PoutreAB`), native ASTER format -- same writer as
    `scripts/build_lot38_essais.mesh_text`, length 1 m in the essai's unit."""
    return "\n".join(
        [
            f"% {title}",
            "TITRE",
            title,
            "FINSF",
            "",
            "COOR_3D",
            "N1 0.000000000000 0.000000000000 0.000000000000",
            f"N2 {units.length:.12f} 0.000000000000 0.000000000000",
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
    )


ESSAIS = {
    "d19": ("étape 1 bis, cas du lot 38 avec D19", D19_CASES, D19_CALLS),
    "limites": (
        "étape 2, comportement de la commande en 1D",
        LIMITES_CASES,
        LIMITES_CALLS,
    ),
    "fermin": ("étape 2.1, FERR_MIN='EC2'", FERMIN_CASES, FERMIN_CALLS),
    "fiss": ("étape 2.1, FERR_MIN_FISS='EC2' à l'ELS QP", FISS_CASES, FISS_CALLS),
    "fermin_mpa": (
        "étape 2.1, FERR_MIN='EC2' en MPa et mm (discrimination d'unités)",
        FERMIN_CASES,
        FERMIN_CALLS,
    ),
}
UNITS = {"fermin_mpa": MPA_MM}


def main() -> int:
    for name, (title, cases, calls) in ESSAIS.items():
        units = UNITS.get(name, SI)
        folder = OUT_DIR / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.comm").write_text(
            build_comm(title, cases, calls, units), "utf-8"
        )
        (folder / f"{name}.export").write_text(export_text(name), "utf-8")
        (folder / f"{name}.mail").write_text(mesh_text(f"lot39_{name}", units), "utf-8")
        print(f"écrit {folder.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
