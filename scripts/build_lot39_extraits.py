"""Extraits documentaires du lot 39 (`lot39_extraits.json`).

Même règle que `scripts/build_lot38_extraits.py` (dont les contrôles de dépôt sont
réutilisés) : chaque extrait est une plage de lignes d'un fichier .rst de
`external/codeaster-doc`, au commit du manifeste, copiée telle quelle.

    python scripts/build_lot39_extraits.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_lot38_extraits import (  # noqa: E402
    ASTER_VERSION,
    C42,
    DOC,
    EXPECTED_COMMIT,
    PLA,
    POU,
    Spec,
    U,
    _check_repository,
)

OUTPUT = ROOT / "data" / "examples" / "combiwall_inputs" / "lot39_extraits.json"
BEAM = "Calcul_du_ferraillage_des_poutres_et_poteaux"

SPECS: tuple[Spec, ...] = (
    Spec(
        "r7_04_05_1d_elu_balayage",
        "R7.04.05",
        POU,
        339,
        339,
        (
            BEAM,
            "Dimensionnement à l’ELU",
            "Principe d’équilibre et calcul des sections d’acier",
        ),
    ),
    Spec(
        "r7_04_05_1d_flexion_deviee",
        "R7.04.05",
        POU,
        606,
        700,
        (
            BEAM,
            "Dimensionnement à l’ELU",
            "Calcul du ferraillage longitudinal en flexion déviée",
        ),
    ),
    Spec(
        "r7_04_05_1d_transversal_elu",
        "R7.04.05",
        POU,
        702,
        904,
        (BEAM, "Dimensionnement à l’ELU", "Calcul du ferraillage transversal"),
    ),
    Spec(
        "r7_04_05_1d_els_balayage",
        "R7.04.05",
        POU,
        1065,
        1065,
        (BEAM, "Dimensionnement à l’ELS Caractéristique", "COND_ITER"),
    ),
    Spec(
        "r7_04_05_1d_minimum",
        "R7.04.05",
        POU,
        1839,
        1875,
        (BEAM, "Prise en compte du ferraillage minimum"),
    ),
    Spec(
        "u4_81_42_ec2_ferr_min",
        "U4.81.42",
        C42,
        876,
        927,
        ("Op_randes", "AFFE", "EC2", "FERR_MIN, RHO_LONGI_MIN, RHO_TRNSV_MIN"),
    ),
    Spec(
        "u4_81_42_ec2_epure_cisa",
        "U4.81.42",
        C42,
        855,
        875,
        ("Op_randes", "AFFE", "EC2", "EPURE_CISA"),
    ),
    Spec(
        "u4_81_42_ferr_min_fiss",
        "U4.81.42",
        C42,
        338,
        354,
        ("Op_randes", "AFFE", "FERR_MIN_FISS"),
    ),
    Spec(
        "u4_81_42_composition_1d_2d",
        "U4.81.42",
        f"{U}/u4/u4.81.42/Composition_du_champ_produit.rst",
        1,
        82,
        ("Composition_du_champ_produit",),
    ),
    Spec(
        "r7_04_05_2d_capra_maury",
        "R7.04.05",
        PLA,
        1,
        45,
        ("Calcul_du_ferraillage_des_plaques", "Méthode de Capra et Maury"),
    ),
)


def build() -> list[dict[str, object]]:
    _check_repository()
    out: list[dict[str, object]] = []
    for spec in SPECS:
        lines = (DOC / spec.path).read_text(encoding="utf-8").split("\n")
        assert 1 <= spec.first <= spec.last <= len(lines), spec.ident
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
    assert len({s.ident for s in SPECS}) == len(SPECS)
    return out


def main() -> int:
    OUTPUT.write_text(
        json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{len(SPECS)} extraits écrits dans {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
