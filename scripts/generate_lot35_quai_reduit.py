"""Lot 35 : génère le `.comm` du quai réduit (deux entraxes, trois tubes) avec la
chaîne de production du lot 35 -- charges par couche, repère des tubes,
maillage orienté, tables de synthèse -- pour développer et vérifier la synthèse
sur un modèle rapide avant l'unique exécution du modèle complet.

Réutilise le maillage vérifié du quai réduit (`data/examples/lot30_quai_reduit`)
sans y toucher ; écrit dans `data/examples/lot35_synthese/`, jamais dans
`data/examples/lot28_quai/` (réservé à `aster-expert generate`).

Usage : python scripts/generate_lot35_quai_reduit.py <maillage vérifié .med> [--nom NOM]
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml

from aster_expert.generation.errors import GenerationError
from aster_expert.generation.generate import generate_comm

ROOT = Path(__file__).resolve().parents[1]
FICHE = ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT_DIR = ROOT / "data" / "examples" / "lot35_synthese"


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
    parser.add_argument("--nom", default="quai_reduit_synthese")
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
        )
    except GenerationError as exc:
        print(f"generate ÉCHEC : {exc}")
        return 1
    output = OUT_DIR / f"{args.nom}.comm"
    output.write_text(text, encoding="utf-8")
    # Un cas avec maillage exige un `.export` (seul un `.export` fait copier les
    # fichiers voisins `<nom>.*`) : le maillage vérifié est recopié tel quel.
    shutil.copyfile(args.maillage, OUT_DIR / f"{args.nom}.mmed")
    (OUT_DIR / f"{args.nom}.export").write_text(
        "P time_limit 1800\nP memory_limit 8192\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm {args.nom}.comm D 1\n"
        f"F mmed {args.nom}.mmed D 20\n",
        encoding="utf-8",
    )
    print(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
    )
    print(f".comm écrit dans {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
