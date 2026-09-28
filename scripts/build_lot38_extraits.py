"""Extraits documentaires du lot 38 (`lot38_extraits.json`).

Chaque extrait est une plage de lignes d'un fichier .rst du dépôt de
documentation (`external/codeaster-doc`, commit du manifeste), copiée telle
quelle : aucun texte n'est saisi à la main. Le script est idempotent ; il
refuse de travailler si le dépôt n'est pas au commit attendu ou si un fichier
a des modifications locales.

    python scripts/build_lot38_extraits.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "external" / "codeaster-doc"
OUTPUT = ROOT / "data" / "examples" / "combiwall_inputs" / "lot38_extraits.json"
EXPECTED_COMMIT = "9c8c179f57ef7ca1d2891cac275ee4823a57967c"
ASTER_VERSION = "17.4.0"


class Spec(NamedTuple):
    ident: str
    document_id: str
    path: str  # relatif à external/codeaster-doc
    first: int
    last: int
    section: tuple[str, ...]


U = "source/manuals/man_u"
R = "source/manuals/man_r"
POU = f"{R}/r7/r7.04.05/Calcul_du_ferraillage_des_poutres_et_poteaux.rst"
PLA = f"{R}/r7/r7.04.05/Calcul_du_ferraillage_des_plaques.rst"
C42 = f"{U}/u4/u4.81.42/Op_randes.rst"

SPECS: tuple[Spec, ...] = (
    # --- lot 38, constat de symétrie POU_D_T (étape 1.3) -----------------------
    Spec(
        "u3_11_01_pou_dofs",
        "U3.11.01",
        f"{U}/u3/u3.11.01/Discr_tisation.rst",
        1,
        63,
        ("Discr_tisation",),
    ),
    Spec(
        "u4_44_01_ddl_tableau_5_2",
        "U4.44.01",
        f"{U}/u4/u4.44.01/Chargements_de_type_Dirichlet_.rst",
        3,
        80,
        ("Chargements de type Dirichlet", "Degrés de liberté"),
    ),
    Spec(
        "u4_44_01_ddl_impo_mot_cle",
        "U4.44.01",
        f"{U}/u4/u4.44.01/Chargements_de_type_Dirichlet_.rst",
        192,
        236,
        ("Chargements de type Dirichlet", "Mot-clé DDL_IMPO"),
    ),
    # --- CALC_FERRAILLAGE (U4.81.42) -------------------------------------------
    Spec("u4_81_42_but", "U4.81.42", f"{U}/u4/u4.81.42/But.rst", 1, 7, ("But",)),
    Spec(
        "u4_81_42_type_comb",
        "U4.81.42",
        C42,
        1,
        105,
        ("Op_randes", "RESULTAT, CARA_ELEM, TYPE_COMB, CODIFICATION"),
    ),
    Spec(
        "u4_81_42_unite", "U4.81.42", C42, 163, 179, ("Op_randes", "UNITE_CONTRAINTE")
    ),
    Spec(
        "u4_81_42_selection",
        "U4.81.42",
        C42,
        186,
        211,
        ("Op_randes", "AFFE", "Sélection des mailles"),
    ),
    Spec(
        "u4_81_42_ec2_type_structure",
        "U4.81.42",
        C42,
        803,
        827,
        ("Op_randes", "AFFE", "EC2", "TYPE_STRUCTURE"),
    ),
    Spec(
        "u4_81_42_ec2_enrobage",
        "U4.81.42",
        C42,
        928,
        1011,
        (
            "Op_randes",
            "AFFE",
            "EC2",
            "C_SUP, C_INF, C_SUP_Y, C_INF_Y, C_SUP_Z, C_INF_Z",
        ),
    ),
    Spec(
        "u4_81_42_ec2_materiaux",
        "U4.81.42",
        C42,
        1012,
        1107,
        ("Op_randes", "AFFE", "EC2", "ALPHA_E … ALPHA_CC"),
    ),
    Spec(
        "u4_81_42_ec2_els",
        "U4.81.42",
        C42,
        1108,
        1173,
        ("Op_randes", "AFFE", "EC2", "SIGS_ELS, SIGC_*_ELS"),
    ),
    Spec(
        "u4_81_42_ec2_wmax",
        "U4.81.42",
        C42,
        1174,
        1297,
        ("Op_randes", "AFFE", "EC2", "WMAX_*, SIGC_ELS_QP, KT, PHI_*"),
    ),
    Spec(
        "u4_81_42_ec2_classe",
        "U4.81.42",
        C42,
        1298,
        1318,
        ("Op_randes", "AFFE", "EC2", "UTIL_COMPR, CLASSE_ACIER"),
    ),
    Spec(
        "u4_81_42_composition",
        "U4.81.42",
        f"{U}/u4/u4.81.42/Composition_du_champ_produit.rst",
        1,
        82,
        ("Composition_du_champ_produit",),
    ),
    Spec(
        "u4_81_42_erreurs",
        "U4.81.42",
        f"{U}/u4/u4.81.42/Erreurs_et_alarmes.rst",
        1,
        73,
        ("Erreurs_et_alarmes",),
    ),
    # --- COMBINAISON_FERRAILLAGE (U4.81.44), POST_COMBINAISON (U4.81.45) --------
    Spec("u4_81_44_but", "U4.81.44", f"{U}/u4/u4.81.44/But.rst", 1, 11, ("But",)),
    Spec(
        "u4_81_44_operandes",
        "U4.81.44",
        f"{U}/u4/u4.81.44/Op_randes.rst",
        1,
        235,
        ("Op_randes",),
    ),
    Spec("u4_81_45_but", "U4.81.45", f"{U}/u4/u4.81.45/But.rst", 1, 8, ("But",)),
    Spec(
        "u4_81_45_syntaxe",
        "U4.81.45",
        f"{U}/u4/u4.81.45/Syntaxe.rst",
        1,
        56,
        ("Syntaxe",),
    ),
    Spec(
        "u4_81_45_operandes",
        "U4.81.45",
        f"{U}/u4/u4.81.45/Op_randes.rst",
        1,
        103,
        ("Op_randes",),
    ),
    # --- VERI_FERRAILLAGE (U4.81.46), panorama (U2.03.07) -----------------------
    Spec("u4_81_46_but", "U4.81.46", f"{U}/u4/u4.81.46/But.rst", 1, 9, ("But",)),
    Spec(
        "u4_81_46_operandes",
        "U4.81.46",
        f"{U}/u4/u4.81.46/Op_randes.rst",
        1,
        100,
        ("Op_randes",),
    ),
    Spec(
        "u2_03_07_ferraillage",
        "U2.03.07",
        f"{U}/u2/u2.03.07/Calcul_de_ferraillage.rst",
        1,
        16,
        ("Calcul_de_ferraillage",),
    ),
    # --- COMBINAISON_CHARGE (U4.90.31) -----------------------------------------
    Spec(
        "u4_90_31_principe",
        "U4.90.31",
        f"{U}/u4/u4.90.31/Principe.rst",
        1,
        29,
        ("Principe",),
    ),
    Spec(
        "u4_90_31_operandes",
        "U4.90.31",
        f"{U}/u4/u4.90.31/Op_randes.rst",
        1,
        235,
        ("Op_randes",),
    ),
    # --- R7.04.05 : méthode ----------------------------------------------------
    Spec(
        "r7_04_05_resume", "R7.04.05", f"{R}/r7/r7.04.05/index.rst", 1, 29, ("index",)
    ),
    Spec(
        "r7_04_05_1d_notations",
        "R7.04.05",
        POU,
        1,
        68,
        ("Calcul_du_ferraillage_des_poutres_et_poteaux", "Notations"),
    ),
    Spec(
        "r7_04_05_1d_elu",
        "R7.04.05",
        POU,
        69,
        150,
        ("Calcul_du_ferraillage_des_poutres_et_poteaux", "Dimensionnement à l’ELU"),
    ),
    Spec(
        "r7_04_05_1d_ec2_bael",
        "R7.04.05",
        POU,
        589,
        605,
        (
            "Calcul_du_ferraillage_des_poutres_et_poteaux",
            "Différence entre BAEL91 et EC2",
        ),
    ),
    Spec(
        "r7_04_05_1d_transversal",
        "R7.04.05",
        POU,
        729,
        738,
        (
            "Calcul_du_ferraillage_des_poutres_et_poteaux",
            "Calcul du ferraillage transversal",
            "hypothèses",
        ),
    ),
    Spec(
        "r7_04_05_1d_els",
        "R7.04.05",
        POU,
        906,
        950,
        (
            "Calcul_du_ferraillage_des_poutres_et_poteaux",
            "Dimensionnement à l’ELS Caractéristique",
        ),
    ),
    Spec(
        "r7_04_05_1d_els_qp",
        "R7.04.05",
        POU,
        1395,
        1632,
        (
            "Calcul_du_ferraillage_des_poutres_et_poteaux",
            "Dimensionnement à l'ELS Quasi Permanent",
        ),
    ),
    Spec(
        "r7_04_05_2d_capra_maury",
        "R7.04.05",
        PLA,
        1,
        45,
        ("Calcul_du_ferraillage_des_plaques", "Méthode de Capra et Maury"),
    ),
    Spec(
        "r7_04_05_veri",
        "R7.04.05",
        f"{R}/r7/r7.04.05/Verification_du_ferraillage.rst",
        1,
        30,
        ("Verification_du_ferraillage",),
    ),
    # --- conventions de repère et d'efforts ------------------------------------
    Spec(
        "u4_42_01_orientation_defaut",
        "U4.42.01",
        f"{U}/u4/u4.42.01/Mot_cle_ORIENTATION.rst",
        90,
        96,
        ("Mot_cle_ORIENTATION", "Règles d’utilisation"),
    ),
    Spec(
        "u2_01_05_efforts_poutre",
        "U2.01.05",
        f"{U}/u2/u2.01.05/Statique.rst",
        38,
        61,
        ("Statique", "Effort", "Cas des poutres"),
    ),
)


def _check_repository() -> None:
    head = subprocess.run(
        ["git", "-C", str(DOC), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if head != EXPECTED_COMMIT:
        message = f"dépôt de documentation au commit {head}, attendu {EXPECTED_COMMIT}"
        raise SystemExit(message)
    status = subprocess.run(
        ["git", "-C", str(DOC), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        message = f"dépôt de documentation modifié localement :\n{status}"
        raise SystemExit(message)


def build() -> list[dict[str, object]]:
    _check_repository()
    seen: set[str] = set()
    out: list[dict[str, object]] = []
    for spec in SPECS:
        if spec.ident in seen:
            message = f"identifiant en double : {spec.ident}"
            raise SystemExit(message)
        seen.add(spec.ident)
        lines = (DOC / spec.path).read_text(encoding="utf-8").split("\n")
        if not 1 <= spec.first <= spec.last <= len(lines):
            message = (
                f"{spec.ident} : plage {spec.first}-{spec.last} hors de {spec.path}"
            )
            raise SystemExit(message)
        out.append(
            {
                "id": spec.ident,
                "document_id": spec.document_id,
                "section_path": list(spec.section),
                "source_path": spec.path,
                "line_start": spec.first,
                "line_end": spec.last,
                "aster_version": ASTER_VERSION,
                "source_commit": EXPECTED_COMMIT,
                "text": "\n".join(lines[spec.first - 1 : spec.last]),
            }
        )
    return out


def main() -> int:
    payload = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    OUTPUT.write_text(payload, encoding="utf-8")
    sys.stdout.write(f"{len(SPECS)} extraits écrits dans {OUTPUT.relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
