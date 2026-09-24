"""Génère le `.comm` d'un candidat de jonction tête de tube / poutre de
couronnement (lot 31, étape 2) sur le quai réduit du lot 30, sans toucher au
`.comm` de production ni à celui du lot 30.

Réutilise le maillage réduit déjà vérifié (`data/examples/lot30_quai_reduit`,
mêmes paramètres, mêmes décisions) : ce script appelle directement
`aster_expert.generation.generate.generate_comm` avec l'option de diagnostic
`JunctionCandidate`, jamais la CLI `aster-expert generate` (qui écrit
toujours dans `data/examples/lot28_quai/`).

Usage : python scripts/generate_lot31_candidat.py <méthode> <maillage vérifié .mmed>
  méthode : liaison_solide | liaison_ddl_translations | noeud_unique
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import JunctionCandidate, generate_comm

ROOT = Path(__file__).resolve().parents[1]
FICHE = ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT_DIR = ROOT / "data" / "examples" / "lot31_jonction"


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
    parser.add_argument(
        "methode",
        choices=("liaison_solide", "liaison_ddl_translations", "noeud_unique"),
    )
    parser.add_argument("maillage", type=Path, help="MED vérifié (mesh check OK)")
    parser.add_argument(
        "--stem", help="nom de base des fichiers produits (défaut: méthode)"
    )
    args = parser.parse_args(argv)

    stem = args.stem or f"quai_reduit_{args.methode}"
    output = OUT_DIR / f"{stem}.comm"

    aster_version = _resolve_aster_version_tag(ROOT / "config" / "versions.yaml")
    try:
        text, report = generate_comm(
            fiche_path=FICHE,
            data_path=DONNEES,
            med_path=args.maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=aster_version,
            junction=JunctionCandidate(method=args.methode),
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    print(f".comm écrit dans {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
