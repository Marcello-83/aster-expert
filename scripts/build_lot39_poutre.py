"""Lot 39, étape 3.1 : `CALC_FERRAILLAGE` appliqué aux efforts combinés de la
poutre de couronnement, pour chaque famille de D17, avec les paramètres de D18 et
la position des armatures de D19.

Source des efforts : les cas élémentaires `EFPOUT_<cas>` (`EFGE_ELNO`) de
l'exécution du modèle complet réutilisée au lot 38
(`data/processed/runs/20260925T125131-c67e28a1`, `.comm` identique au
`data/examples/lot37_efforts/complet.comm` versionné), combinés par
`aster_expert.report.combinations` -- les mêmes efforts combinés qu'au lot 38,
mais **par extrémité d'élément** (128 couples élément/nœud) et non moyennés par
nœud : l'effort tranchant saute au droit des tubes, une moyenne le fausserait.

`CALC_FERRAILLAGE` exige un résultat Code_Aster : il est produit ici dans le
schéma des cas tests officiels `ssll13*` (une maille `SEG2` par section, efforts
imposés par `CREA_CHAMP/CART_SIEF_R`, `CREA_RESU`). Les mailles synthétiques sont
parallèles à X sans `ORIENTATION` : même repère local que `POUTRE_COUR`
(x_l = X, y_l = Y vers la terre, z_l = Z ascendant ; HY = 2,50 m selon y_l,
HZ = 1,40 m selon z_l). AYS/AYI : faces côté terre/côté bassin ; AZS/AZI : faces
supérieure/inférieure (`U4.81.42`, composition du champ ; signes établis par
l'essai `limites` du lot 39).

Familles (D17) et paramètres :

- ELU fondamentale (8 combinaisons) : γc = 1,5, γs = 1,15 ;
- ELU accidentelle (1) : γc = 1,2, γs = 1,0 -- valeurs recommandées de
  l'EN 1992-1-1, tableau 2.1N, non décidées par MM (signalé dans le rapport) ;
- ELS caractéristique (4) : σc ≤ 0,6 fck (XS3, 7.2(2)), σs ≤ 0,8 fyk (7.2(5)) ;
- ELS quasi permanente (1) : wk = 0,2 mm (D18), φ = 40 mm (D19), kt = 0,4,
  σc,QP = 0,45 fck ;
- ELS fréquente (4) : aucun critère de ferraillage dans D18 : non calculée.

αcc = 1,0 (valeur recommandée de l'EN 1992-1-1, 3.1.6(1) ; défaut du catalogue
0,85). `FERR_MIN` n'est pas activé : en `UNITE_CONTRAINTE='Pa'` il applique des
minima faux (essais `fermin`/`fermin_mpa` du lot 39) ; les minima sont appliqués
hors de Code_Aster (`aster_expert.rebar.minimum`).

Usage : python scripts/build_lot39_poutre.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_lot38_export import MESS, _parse_beam_tables  # noqa: E402

from aster_expert.report.combinations import (  # noqa: E402
    CASES,
    Combination,
    combine,
    enumerate_combinations,
)

OUT_DIR = ROOT / "data" / "examples" / "lot39_poutre"
COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
HY, HZ = 2.50, 1.40
COVER = 0.10  # D19
PHI = 0.040  # D19
FCK, FYK, EYS = 35.0e6, 500.0e6, 210.0e9
ALPHA_CC = 1.0
FAMILIES = (
    ("ELU fondamentale", "ELU", 1.5, 1.15),
    ("ELU accidentelle", "ELU", 1.2, 1.0),
    ("ELS caractéristique", "ELS", None, None),
    ("ELS quasi permanente", "ELS_QP", None, None),
)


def sections() -> tuple[list[dict[str, float]], dict[str, list[dict[str, float]]]]:
    """The 128 (element, node) rows, in the order of the tables, and the rows of each
    elementary case (same order, checked)."""
    raw = _parse_beam_tables(MESS.read_text(encoding="utf-8").splitlines())
    reference = raw["G"]
    for case in CASES:
        rows = raw[case]
        assert len(rows) == len(reference), case
        for a, b in zip(rows, reference, strict=True):
            assert (a["MAILLE"], a["NOEUD"]) == (b["MAILLE"], b["NOEUD"]), case
    return reference, raw


def combinations() -> list[Combination]:
    families = {f[0] for f in FAMILIES}
    return [c for c in enumerate_combinations() if c.family in families]


def combined(
    raw: dict[str, list[dict[str, float]]], combination: Combination, index: int
) -> dict[str, float]:
    return {
        comp: combine(
            combination.coefficients,
            {case: raw[case][index][comp] for case in combination.coefficients},
        )
        for comp in COMPONENTS
    }


def _num(x: float) -> str:
    return repr(float(x))


def _affe(type_comb: str, gamma_c: float | None, gamma_s: float | None) -> str:
    lines = [
        'TOUT="OUI"',
        'TYPE_STRUCTURE="1D"',
        *(f"{k}={_num(COVER)}" for k in ("C_SUP_Y", "C_INF_Y", "C_SUP_Z", "C_INF_Z")),
        f"FYK={_num(FYK)}",
        f"FCK={_num(FCK)}",
        f"EYS={_num(EYS)}",
        'TYPE_DIAGRAMME="B2"',
        f"ALPHA_CC={_num(ALPHA_CC)}",
    ]
    if type_comb == "ELU":
        assert gamma_c is not None and gamma_s is not None
        lines += [f"GAMMA_S={_num(gamma_s)}", f"GAMMA_C={_num(gamma_c)}"]
    else:
        lines += [
            "ALPHA_E=15.0",
            f"SIGS_ELS={_num(0.8 * FYK)}",
            *(
                f"SIGC_{f}_ELS={_num(0.6 * FCK)}"
                for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
            ),
        ]
    if type_comb == "ELS_QP":
        lines += [f"SIGC_ELS_QP={_num(0.45 * FCK)}", "KT=0.4"]
        lines += [f"WMAX_{f}=0.0002" for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")]
        lines += [f"PHI_{f}={_num(PHI)}" for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")]
    return "\n".join(f"            {line}," for line in lines)


def build_comm(
    rows: list[dict[str, float]],
    raw: dict[str, list[dict[str, float]]],
    combos: list[Combination],
) -> str:
    fields = []
    for i, combination in enumerate(combos, start=1):
        occurrences = []
        for k in range(len(rows)):
            values = combined(raw, combination, k)
            vale = ", ".join(_num(values[c]) for c in COMPONENTS)
            occurrences.append(
                f'        _F(GROUP_MA="S{k + 1:03d}", NOM_CMP=("N", "VY", "VZ", "MT", "MFY", "MFZ"), VALE=({vale})),'
            )
        joined = "\n".join(occurrences)
        fields.append(
            f"""# instant {i} : {combination.name} ({combination.family})
CH{i:02d} = CREA_CHAMP(
    MAILLAGE=MA,
    OPERATION="AFFE",
    TYPE_CHAM="CART_SIEF_R",
    AFFE=(
{joined}
    ),
)
"""
        )
    affe = "\n".join(
        f'        _F(NOM_CHAM="EFGE_ELNO", CHAM_GD=CH{i:02d}, INST={float(i)}, '
        "MODELE=MODEL, CARA_ELEM=CARA),"
        for i in range(1, len(combos) + 1)
    )
    calls = []
    for family, type_comb, gamma_c, gamma_s in FAMILIES:
        insts = ", ".join(
            repr(float(i)) for i, c in enumerate(combos, start=1) if c.family == family
        )
        calls.append(
            f"""# {family}
RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="{type_comb}",
    UNITE_CONTRAINTE="Pa",
    INST=({insts},),
    AFFE=(
        _F(
{_affe(type_comb, gamma_c, gamma_s)}
        ),
    ),
)
"""
        )
    return f"""# Lot 39, étape 3.1 : ferraillage de la poutre de couronnement sous les
# combinaisons de D17 (CALC_FERRAILLAGE, TYPE_STRUCTURE='1D').
# Une maille SEG2 par extrémité d'élément de POUTRE_COUR (128 sections,
# sections.csv) ; efforts combinés (efforts.csv) imposés par CART_SIEF_R.
# Produit par scripts/build_lot39_poutre.py -- ne pas éditer.

DEBUT(CODE="OUI")

MA = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MODEL = AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=_F(GROUP_MA="POUTRE", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MODEL,
    POUTRE=_F(
        CARA=("HY", "HZ"),
        GROUP_MA=("POUTRE",),
        SECTION="RECTANGLE",
        VALE=({_num(HY)}, {_num(HZ)}),
    ),
)

{"".join(fields)}
RESU = CREA_RESU(
    OPERATION="AFFE",
    TYPE_RESU="EVOL_ELAS",
    AFFE=(
{affe}
    ),
)

{"".join(calls)}
T_FERR = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU,
        NOM_CHAM="FERR_ELEM",
        TOUT_ORDRE="OUI",
        NOM_CMP=("AYS", "AYI", "AZS", "AZI", "AST", "ATOT"),
        TOUT="OUI",
    )
)
IMPR_TABLE(TABLE=T_FERR, UNITE=6, FORMAT_R="E20.12", TITRE="FERR_POUTRE")

FIN()
"""


def mesh_text(count: int) -> str:
    """One SEG2 per section, own nodes, along X (1 m apart, 0,5 m long): the
    geometry carries no information, only the local frame (x_l = X) matters."""
    lines = ["% lot39_poutre", "TITRE", "lot39_poutre", "FINSF", "", "COOR_3D"]
    for k in range(1, count + 1):
        lines.append(f"A{k:03d} {float(k):.12f} 0.000000000000 0.000000000000")
        lines.append(f"B{k:03d} {k + 0.5:.12f} 0.000000000000 0.000000000000")
    lines += ["FINSF", "", "SEG2"]
    lines += [f"M{k:03d} A{k:03d} B{k:03d}" for k in range(1, count + 1)]
    lines += ["FINSF", "", "GROUP_MA", "POUTRE"]
    lines += [f"  M{k:03d}" for k in range(1, count + 1)]
    lines += ["FINSF", ""]
    for k in range(1, count + 1):
        lines += ["GROUP_MA", f"S{k:03d}", f"  M{k:03d}", "FINSF", ""]
    lines += ["FIN", ""]
    return "\n".join(lines)


def export_text() -> str:
    return (
        "P time_limit 600\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        "P mpi_nbnoeud 1\nF comm poutre.comm D 1\nF mail poutre.mail D 20\n"
    )


def main() -> int:
    rows, raw = sections()
    combos = combinations()
    assert len(combos) == 14, len(combos)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "poutre.comm").write_text(build_comm(rows, raw, combos), "utf-8")
    (OUT_DIR / "poutre.mail").write_text(mesh_text(len(rows)), "utf-8")
    (OUT_DIR / "poutre.export").write_text(export_text(), "utf-8")
    with (OUT_DIR / "sections.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["section", "maille", "noeud", "x_m"])
        for k, row in enumerate(rows, start=1):
            writer.writerow(
                [f"S{k:03d}", int(row["MAILLE"]), int(row["NOEUD"]), row["COOR_X"]]
            )
    with (OUT_DIR / "efforts.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["instant", "combinaison", "famille", "section", *COMPONENTS])
        for i, combination in enumerate(combos, start=1):
            for k in range(len(rows)):
                values = combined(raw, combination, k)
                writer.writerow(
                    [
                        i,
                        combination.name,
                        combination.family,
                        f"S{k + 1:03d}",
                        *(f"{values[c]:.12e}" for c in COMPONENTS),
                    ]
                )
    print(f"écrit {OUT_DIR.relative_to(ROOT)} : {len(rows)} sections, 14 instants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
