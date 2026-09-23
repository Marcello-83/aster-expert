"""Génère le `.comm` du quai réduit (lot 30, étape 2) sans toucher au `.comm`
de production du lot 28.

`aster-expert generate` (CLI) écrit toujours dans
`data/examples/lot28_quai/quai_combiwall.comm` : l'appeler ici écraserait le
fichier de production. Ce script appelle directement
`aster_expert.generation.generate.generate_comm` et écrit le résultat dans
`data/examples/lot30_quai_reduit/quai_reduit.comm`, avec les mêmes fiche et
décisions que la production (aucune décision n'est prise ou modifiée), pour
la seule donnée changeante : le fichier de données du quai réduit.

Usage : python scripts/generate_lot30_quai_reduit.py <maillage vérifié .mmed>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import DiagnosticOmissions, generate_comm

ROOT = Path(__file__).resolve().parents[1]
FICHE = ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"


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
        "--output",
        type=Path,
        default=ROOT / "data" / "examples" / "lot30_quai_reduit" / "quai_reduit.comm",
        help="chemin du .comm produit",
    )
    parser.add_argument(
        "--sans-ressorts",
        action="store_true",
        help="étape 3, retrait 1 : aucune classe de ressort (diagnostic seulement)",
    )
    parser.add_argument(
        "--sans-tirants",
        action="store_true",
        help="étape 3, retrait 2 : aucun tirant (diagnostic seulement)",
    )
    parser.add_argument(
        "--sans-palplanches",
        action="store_true",
        help="étape 3, retrait 3 : aucune palplanche (diagnostic seulement)",
    )
    parser.add_argument(
        "--sans-poutre",
        action="store_true",
        help=(
            "étape 3, retrait 4 : aucune poutre / LIAISON_SOLIDE (diagnostic seulement)"
        ),
    )
    args = parser.parse_args(argv)

    aster_version = _resolve_aster_version_tag(ROOT / "config" / "versions.yaml")
    try:
        text, report = generate_comm(
            fiche_path=FICHE,
            data_path=DONNEES,
            med_path=args.maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=aster_version,
            diagnostic=DiagnosticOmissions(
                sans_ressorts=args.sans_ressorts,
                sans_tirants=args.sans_tirants,
                sans_palplanches=args.sans_palplanches,
                sans_poutre=args.sans_poutre,
            ),
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    print(f".comm écrit dans {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
