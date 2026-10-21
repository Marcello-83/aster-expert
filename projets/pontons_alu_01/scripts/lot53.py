"""Lot 53 of PONTONS-ALU-01: displacements under berthing and mooring, post-processing
of variant B52 of lot 52 (no new Code_Aster run).

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot53.py <étape> \
        [--depot <dossier>]

Étapes : `exports` (relecture des tables de l'exécution B52 du lot 52, points de sortie,
cas unitaires, événements, enveloppes, synthèse, contrôles ; `deplacements_lot53`),
`verifier` (lecteur indépendant des CSV : linéarité de trois événements), `med` (copie de
`resultats.med` du lot 52 et champs DEPL ajoutés, `med_lot53`), `vues` (PNG A, B, C,
`vues_lot53`), `references` (listing versionné : synthèse, extrêmes par événement,
contrôles, sous `references/post_traitement_lot53/`), `depot` (copie sur le partage,
empreintes), `tout`. Tout est écrit sous `resultats/lot53/`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.errors import ProjectError

ROOT = Path(__file__).resolve().parents[3]
STEM = "pontons_alu_01"
LOT = "lot53"
SOURCE_LOT = "lot52"
CHECK_SCRIPT = Path(__file__).resolve().parent / "verifier_evenements_lot53.py"
REFERENCES = (
    Path(__file__).resolve().parents[1] / "references" / "post_traitement_lot53"
)
VERSIONED = (
    ("exports/B52/deplacements_synthese.csv", "deplacements_synthese.csv"),
    ("exports/B52/deplacements_evenements.csv", "deplacements_evenements.csv"),
    ("exports/synthese.json", "synthese_lot53.json"),
    ("exports/verification_evenements.txt", "verification_evenements.txt"),
)


def source_state(ctx: ProjectContext) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (ctx.results_dir / SOURCE_LOT / "etat.json").read_text("utf-8")
    )
    return loaded


def summary_path(ctx: ProjectContext) -> Path:
    return ctx.results_dir / LOT / "exports" / "synthese.json"


def update_summary(ctx: ProjectContext, key: str, value: Any) -> None:
    path = summary_path(ctx)
    data = json.loads(path.read_text("utf-8"))
    data[key] = value
    path.write_text(
        json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )


def step_verifier(ctx: ProjectContext) -> dict[str, Any]:
    """Criterion 4: the independent reader (csv module only)."""
    out = ctx.results_dir / LOT / "exports" / "B52"
    events = ctx.results_dir / SOURCE_LOT / "exports" / "B52" / "evenements.csv"
    result = subprocess.run(  # noqa: S603 -- argv fixe
        [
            sys.executable,
            "-I",
            str(CHECK_SCRIPT),
            str(out / "deplacements_unitaires.csv"),
            str(events),
            str(out / "deplacements_evenements.csv"),
            "--graine",
            "53",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    (out.parent / "verification_evenements.txt").write_text(
        result.stdout + result.stderr, "utf-8"
    )
    report = {
        "code": result.returncode,
        "sortie": result.stdout.strip().splitlines()[-6:],
    }
    update_summary(ctx, "controle_linearite_lecteur_independant", report)
    return report


def step_references(ctx: ProjectContext) -> None:
    """The listing of the values reported in `docs/essais_lot53.md` (versioned)."""
    REFERENCES.mkdir(parents=True, exist_ok=True)
    for src, name in VERSIONED:
        shutil.copyfile(ctx.results_dir / LOT / src, REFERENCES / name)
    print(f"références : {len(VERSIONED)} fichiers dans {REFERENCES}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "etape",
        choices=(
            "exports",
            "verifier",
            "med",
            "vues",
            "references",
            "depot",
            "tout",
        ),
    )
    parser.add_argument("--depot", type=Path, default=None)
    args = parser.parse_args()
    ctx = load_project(STEM, ROOT)
    try:
        if args.etape in ("exports", "tout"):
            from pontons_alu_01.deplacements_lot53 import step_exports  # noqa: PLC0415

            summary = step_exports(ctx, source_state(ctx))
            for key in (
                "controle_empreintes",
                "controle_relecture",
                "controle_TP_P5",
                "controle_liaisons",
                "controle_enumeration",
                "controle_champs_points",
            ):
                print(f"{key} : {'RÉUSSI' if summary[key]['reussi'] else 'ÉCHEC'}")
            print(f"temps : {summary['temps_s']}")
        if args.etape in ("verifier", "tout"):
            report = step_verifier(ctx)
            print(f"lecteur indépendant : code {report['code']}")
        if args.etape in ("med", "tout"):
            from pontons_alu_01.med_lot53 import step_med  # noqa: PLC0415

            step_med(ctx)
        if args.etape in ("vues", "tout"):
            from pontons_alu_01.vues_lot53 import step_vues  # noqa: PLC0415

            step_vues(ctx)
        if args.etape in ("references", "tout"):
            step_references(ctx)
        if args.etape in ("depot", "tout"):
            from pontons_alu_01.depot_lot53 import step_depot  # noqa: PLC0415

            step_depot(ctx, args.depot)
    except ProjectError:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
