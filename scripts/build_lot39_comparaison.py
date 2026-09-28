"""Lot 39, étape 5 : lignes de comparaison au logiciel de section de MM
(`data/examples/lot38_essais/ligne_comparaison_mm.csv`, mis à jour).

Une ligne par **plan de flexion** : un logiciel de section en flexion composée
traite un moment à la fois. Pour chaque ligne, dans le vocabulaire d'un tel
logiciel :

- `h_m` : dimension de la section **dans le plan de flexion** (2,50 m pour MFZ,
  flexion horizontale ; 1,40 m pour MFY, flexion verticale) ;
- `b_m` : dimension perpendiculaire ;
- `ds_m`, `di_m` : distance du parement à l'axe des armatures de la fibre
  supérieure et de la fibre inférieure **du logiciel** (0,10 m, D19) ;
- `etat_limite` : ELU fondamentale, ELS caractéristique ou ELS quasi permanente ;
- sens du moment : la ligne dit quelle face réelle de la poutre est tendue et
  laquelle est comprimée, et demande de saisir `M_a_saisir_MNm` (positif) avec la
  **fibre inférieure du logiciel = face tendue**.

Le premier essai de MM (h = 1,00 m, b = 2,50 m, type ELS pour un moment ELU de
flexion horizontale) est la confusion que ce format doit rendre impossible.

Les colonnes `As_*_MM_m2` et `ecart_*` sont laissées vides : **MM les remplit ;
la session ne les remplit pas.**

Usage : python scripts/build_lot39_comparaison.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aster_expert.rebar.biaxial import design_biaxial  # noqa: E402
from aster_expert.rebar.model import Concrete, Rectangle, Steel  # noqa: E402
from aster_expert.rebar.ultimate import design_ultimate  # noqa: E402

OUT = ROOT / "data" / "examples" / "lot38_essais" / "ligne_comparaison_mm.csv"
POUTRE = ROOT / "data" / "examples" / "lot39_poutre"
MESS_D19 = (
    ROOT / "data" / "examples" / "lot39_essais" / "rapports" / "mess_d19_extrait.txt"
)
COVER = 0.10
FACE_NAMES = {
    "AYS": "face côté terre (+y)",
    "AYI": "face côté bassin (-y)",
    "AZS": "face supérieure (+z)",
    "AZI": "face inférieure (-z)",
}
SECTIONS = {
    "bollard X = 0": 0.0,
    "mi-travée entre tubes X = +1,30": 1.3,
    "plan de symétrie SYM_G X = -10,40": -10.4,
}
HEADER = [
    "ligne",
    "origine",
    "etat_limite",
    "combinaison",
    "section",
    "plan_de_flexion",
    "moment_code_aster",
    "h_m",
    "b_m",
    "ds_m",
    "di_m",
    "N_MN_compression_positive",
    "M_a_saisir_MNm",
    "fibre_inferieure_logiciel_face_tendue",
    "fibre_superieure_logiciel_face_comprimee",
    "materiaux",
    "parametres_etat_limite",
    "As_tendue_code_aster_m2",
    "As_comprimee_code_aster_m2",
    "As_tendue_direction_seule_m2",
    "remarque",
    "As_tendue_MM_m2",
    "As_comprimee_MM_m2",
    "ecart_tendue",
]
MATERIALS = "béton C35/45 (fck 35 MPa), acier B500B (fyk 500 MPa, classe B), αcc = 1,0"
ELU_FOND = (
    "γc = 1,5 ; γs = 1,15 ; diagramme béton rectangulaire simplifié ; palier horizontal"
)
ELS_QP = "wk = 0,2 mm ; φ = 40 mm ; kt = 0,4 ; σc,QP = 0,45 fck ; αe = 15"


def _plane(moment: str, value: float) -> tuple[str, float, float, str, str]:
    """(plan, h, b, tension face, compression face) for MFZ or MFY of sign `value`."""
    if moment == "MFZ":
        tension, compression = ("AYS", "AYI") if value > 0 else ("AYI", "AYS")
        return (
            "flexion horizontale (MFZ, axe vertical)",
            2.50,
            1.40,
            tension,
            compression,
        )
    tension, compression = ("AZS", "AZI") if value > 0 else ("AZI", "AZS")
    return "flexion verticale (MFY, axe horizontal)", 1.40, 2.50, tension, compression


def _row(
    number: int,
    origin: str,
    limit_state: str,
    combination: str,
    section: str,
    moment: str,
    value: float,
    n_tension: float,
    params: str,
    as_code_aster: dict[str, float],
    as_single: float | None,
    remark: str,
) -> list[object]:
    plane, h, b, tension, compression = _plane(moment, value)
    return [
        number,
        origin,
        limit_state,
        combination,
        section,
        plane,
        f"{moment} = {value:+.6f} MN·m",
        h,
        b,
        COVER,
        COVER,
        f"{-n_tension + 0.0:.6f}",
        f"{abs(value):.6f}",
        f"{FACE_NAMES[tension]} ({tension})",
        f"{FACE_NAMES[compression]} ({compression})",
        MATERIALS,
        params,
        f"{as_code_aster[tension]:.6e}",
        f"{as_code_aster[compression]:.6e}",
        "" if as_single is None else f"{as_single:.6e}",
        remark,
        "",
        "",
        "",
    ]


def _d19_rows(start: int) -> list[list[object]]:
    table = [
        ln.split()
        for ln in MESS_D19.read_text(encoding="utf-8").splitlines()
        if ln.startswith("RESU ")
    ]
    ca = {
        round(float(c[2])): dict(
            zip(("AYS", "AYI", "AZS", "AZI"), map(float, c[6:10]), strict=True)
        )
        for c in table
    }
    cases = (
        (1, "flexion simple", "ELU fondamentale", 0.0, 2.183517, ELU_FOND),
        (
            2,
            "flexion composée, compression 5 MN",
            "ELU fondamentale",
            -5.0,
            2.183517,
            ELU_FOND,
        ),
        (
            3,
            "flexion composée, traction 5 MN",
            "ELU fondamentale",
            5.0,
            2.183517,
            ELU_FOND,
        ),
        (4, "ELS QP, compression 1 MN", "ELS quasi permanente", -1.0, 0.5, ELS_QP),
    )
    rows = []
    for k, (inst, label, state, n, m, params) in enumerate(cases):
        remark = "essai du lot 38 refait avec D19 (0,10 m) au lot 39"
        if inst == 2:
            remark += " ; point intérieur : le béton seul équilibre (N, M), As = 0"
        if inst == 4:
            remark += " ; béton seul sans traction sous la limite : As = 0"
        rows.append(
            _row(
                start + k,
                "essai lot 38 (section réelle, efforts imposés)",
                state,
                label,
                "section 2,50 x 1,40 m",
                "MFZ",
                m,
                n,
                params,
                ca[inst],
                None,
                remark,
            )
        )
    return rows


def _section_rows(start: int) -> list[list[object]]:
    sections = {}
    with (POUTRE / "sections.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            sections[r["section"]] = float(r["x_m"])
    with (POUTRE / "efforts.csv").open(encoding="utf-8") as fh:
        efforts = list(csv.DictReader(fh))
    with (POUTRE / "ferraillage.csv").open(encoding="utf-8") as fh:
        areas = {(r["instant"], r["section"]): r for r in csv.DictReader(fh)}
    concrete = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
    steel = Steel(fyk=500.0, gamma_s=1.15)
    rows: list[list[object]] = []
    number = start
    for label, x in SECTIONS.items():
        candidates = [
            e
            for e in efforts
            if e["famille"] == "ELU fondamentale"
            and abs(sections[e["section"]] - x) < 1e-9
        ]
        governing = max(
            candidates, key=lambda e: float(areas[(e["instant"], e["section"])]["ATOT"])
        )
        ca_row = areas[(governing["instant"], governing["section"])]
        ca = {f: float(ca_row[f]) for f in ("AYS", "AYI", "AZS", "AZI")}
        n, mfy, mfz = (float(governing[c]) / 1e6 for c in ("N", "MFY", "MFZ"))
        bi = design_biaxial(2.50, 1.40, COVER, concrete, steel, n, mfy, mfz)
        for moment, value, width, depth in (
            ("MFZ", mfz, 1.40, 2.50),
            ("MFY", mfy, 2.50, 1.40),
        ):
            single = design_ultimate(
                Rectangle(width=width, depth=depth, cover_pos=COVER, cover_neg=COVER),
                concrete,
                steel,
                n,
                value,
            )
            as_single = single.as_pos if value > 0 else single.as_neg
            remark = (
                f"section {governing['section']} de lot39_poutre ; combinaison ELU "
                "fondamentale de plus grand ATOT à cette abscisse ; flexion déviée : "
                "Code_Aster calcule chaque direction seule (colonne "
                "As_tendue_direction_seule, à comparer au logiciel) puis augmente les "
                f"quatre aires de 10 % par itération de Bresler ({bi.iterations} "
                "itérations ici, R7.04.05)"
            )
            rows.append(
                _row(
                    number,
                    "étape 3 du lot 39 (poutre sous les combinaisons de D17)",
                    "ELU fondamentale",
                    governing["combinaison"],
                    label,
                    moment,
                    value,
                    n,
                    ELU_FOND,
                    ca,
                    as_single,
                    remark,
                )
            )
            number += 1
    return rows


def main() -> int:
    rows = _d19_rows(1)
    rows += _section_rows(len(rows) + 1)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"écrit {OUT.relative_to(ROOT)} : {len(rows)} lignes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
