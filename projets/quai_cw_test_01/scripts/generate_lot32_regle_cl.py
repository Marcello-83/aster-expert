"""Génère le `.comm` du quai réduit avec la règle de construction des
conditions aux limites du lot 32, étape 1 : dans un ensemble de nœuds liés
par `LIAISON_SOLIDE`, un degré de liberté que la relation détermine n'est
imposé directement que sur un seul nœud (le nœud de poutre) -- déjà la
méthode de jonction retenue (décision 4, point 3), inchangée par ce lot ; la
règle est déjà celle du générateur de production
(`quai_cw_test_01.generation.comm.symmetry_and_support_block`,
`check_symmetry_ddl_impo_no_ring_redundancy`).

Comme `projets/quai_cw_test_01/scripts/generate_lot31_candidat.py`, ce script réutilise le maillage
du quai réduit déjà vérifié (`data/examples/lot30_quai_reduit`) sans y
toucher, et écrit dans `data/examples/lot32_cl/`, jamais dans
`data/examples/lot28_quai/` (réservé à `aster-expert generate`).

Le point 3 de la fiche est en révision depuis le lot 31 (cause établie,
décision non modifiée) : `aster-expert generate` la refuserait en l'état.
Comme `tests/unit/test_generation_generate.py`, la révision est levée en
mémoire seulement, pour les seuls besoins de cette génération d'essai --
jamais écrite dans la fiche versionnée. La fermeture réelle de cette
révision (si l'étape 1 réussit) est un acte distinct, à l'étape 3.

Usage : python projets/quai_cw_test_01/scripts/generate_lot32_regle_cl.py <maillage vérifié .mmed>
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aster_expert.agent.arbitration import lift_revision
from aster_expert.agent.hypotheses import PracticeHypothesisEntry
from aster_expert.constats.base import load_resolved_sheet
from quai_cw_test_01.generation.errors import GenerationError
from quai_cw_test_01.generation.generate import generate_comm

ROOT = Path(__file__).resolve().parents[3]
_REFERENCE_FICHE = (
    ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)
DONNEES = ROOT / "data" / "examples" / "lot30_quai_reduit" / "model_data_reduit.yaml"
OUT_DIR = ROOT / "data" / "examples" / "lot32_cl"


def _resolved_fiche_path() -> Path:
    sheet = load_resolved_sheet(_REFERENCE_FICHE)
    entries = list(sheet.entries)
    for i, e in enumerate(entries):
        if (
            isinstance(e, PracticeHypothesisEntry)
            and e.point_label == "3"
            and e.under_revision
        ):
            entries[i] = lift_revision(
                e,
                reason="Levée locale, pour les seuls besoins de cette génération "
                "d'essai (lot 32, étape 1 -- la décision 4 elle-même n'est ni "
                "prise ni modifiée) -- jamais écrite dans la fiche versionnée.",
                lifted_by="projets/quai_cw_test_01/scripts/generate_lot32_regle_cl.py",
                lifted_at=datetime.now(UTC),
            )
    resolved = sheet.model_copy(update={"entries": tuple(entries)})
    directory = Path(tempfile.mkdtemp(prefix="aster-expert-resolved-fiche-lot32-"))
    path = directory / "fiche_resolue.json"
    path.write_text(resolved.model_dump_json(), encoding="utf-8")
    return path


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
        "--stem",
        default="quai_reduit_regle_cl",
        help="nom de base des fichiers produits",
    )
    args = parser.parse_args(argv)

    fiche = _resolved_fiche_path()
    output = OUT_DIR / f"{args.stem}.comm"

    aster_version = _resolve_aster_version_tag(ROOT / "config" / "versions.yaml")
    try:
        text, report = generate_comm(
            fiche_path=fiche,
            data_path=DONNEES,
            med_path=args.maillage,
            project_root=ROOT,
            work_dir_root="data/processed/mesh_runs",
            aster_version=aster_version,
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
