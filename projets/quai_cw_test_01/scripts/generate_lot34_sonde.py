"""Lot 34, étape 1 : génère le `.comm` de la sonde de charge assemblée
(`quai_cw_test_01.generation.generate.EquilibriumProbe`) du quai réduit -- tous les
degrés de liberté de tous les nœuds bloqués, `REAC_NODA` sommé sur tous les
nœuds, un cas de charge à la fois. Réutilise le maillage vérifié du quai réduit
sans y toucher et écrit dans `data/examples/lot34_equilibre/`.

Usage : python projets/quai_cw_test_01/scripts/generate_lot34_sonde.py <maillage vérifié .med> \
    [--pression ecran|tubes|palplanches|aucune]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.generate import EquilibriumProbe, generate_comm

ROOT = Path(__file__).resolve().parents[3]
FICHE = (
    ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT_DIR = ROOT / "data" / "examples" / "lot34_equilibre"


def _resolve_aster_version_tag(versions_path: Path) -> str:
    data = yaml.safe_load(versions_path.read_text(encoding="utf-8")) or {}
    detected = data.get("detected")
    tag = (
        (detected or {}).get("container", {}).get("image_tag")
        if isinstance(detected, dict)
        else None
    )
    if not tag:
        message = f"aucune version détectée dans {versions_path}"
        raise SystemExit(message)
    return str(tag)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maillage", type=Path, help="MED vérifié (mesh check OK)")
    parser.add_argument(
        "--pression",
        choices=("ecran", "tubes", "palplanches", "aucune"),
        default="ecran",
    )
    parser.add_argument("--nodal", action="store_true")
    parser.add_argument(
        "--production",
        action="store_true",
        help="modèle de production (aucune sonde) : contrôles d'équilibre seuls",
    )
    parser.add_argument(
        "--forces-ressorts",
        action="store_true",
        help="production + FORC_NODA restreint aux POI1 (diagnostic des ressorts)",
    )
    args = parser.parse_args(argv)

    aster_version = _resolve_aster_version_tag(ROOT / "config" / "versions.yaml")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        text, report = generate_comm(
            fiche_path=FICHE,
            data_path=DONNEES,
            med_path=args.maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=aster_version,
            probe=EquilibriumProbe(forces_ressorts=True)
            if args.forces_ressorts
            else None
            if args.production
            else EquilibriumProbe(
                blocage_total=True,
                pression_sur=args.pression,
                extraction_nodale=args.nodal,
            ),
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1
    stem = (
        "quai_reduit_forces_ressorts"
        if args.forces_ressorts
        else "quai_reduit_controles"
        if args.production
        else "sonde_blocage_total"
        if args.pression == "ecran"
        else f"sonde_pression_{args.pression}"
    )
    if args.nodal:
        stem += "_nodal"
    output = OUT_DIR / f"{stem}.comm"
    output.write_text(text, encoding="utf-8")
    print(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    print(f".comm écrit dans {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
