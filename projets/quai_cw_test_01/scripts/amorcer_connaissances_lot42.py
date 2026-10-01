"""Lot 42, étape 5 : amorçage de la base de connaissances avec le quai.

Écrit dans `connaissances/` les entrées construites par
`quai_cw_test_01.capitalisation` (diagnostics, patrons, contrôles, références de
validation, précédents), puis le registre de retour d'expérience
`connaissances/rex/quai_cw_test_01.yaml` : chaque exécution échouée attribuée au
projet (archives `data/processed/runs/`, VM seulement) est classée d'après sa
signature principale. Idempotent : relancé, il réécrit les mêmes octets ; les
revues déjà inscrites (`reviews`) et les lots déclarés sont conservés.

Usage : `.venv/bin/python projets/quai_cw_test_01/scripts/amorcer_connaissances_lot42.py`
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.connaissances.base import (  # noqa: E402
    RUNS_RELATIVE,
    load_knowledge,
    verify_against_repository,
    write_entry,
)
from aster_expert.connaissances.rex import (  # noqa: E402
    Baseline,
    DeclaredFigure,
    LegacyRuns,
    LotRecord,
    RexRegistry,
    project_runs,
    registry_path,
    write_registry,
)
from quai_cw_test_01.capitalisation import (  # noqa: E402
    PROJECT,
    build_entries,
    classify,
)

LEGACY = LegacyRuns(
    before=dt.datetime(2026, 9, 29, 0, 0, 0),
    durations="docs/audit/annexes_lot40/executions_archivees.json",
    reason=(
        "Avant le lot 41, le quai était le seul ouvrage du dépôt et les exécutions "
        "n'avaient pas de compte rendu nommant leur .comm : toutes les exécutions "
        "archivées avant le 2026-09-29 sont celles du quai (audit du lot 40, § 3.4)."
    ),
)
BASELINE = Baseline(
    source="docs/audit/audit_lot40.md, § 3.4 ; consigne du lot 42, étape 5.7",
    lots=40,
    executions=190,
    failures=73,
    compute_hours=1.54,
    supervisor_interventions=DeclaredFigure(
        value=25,
        nature="estimation",
        note=(
            "Estimation de Claude (consigne du lot 42) : environ 25 lots sur les lots 19 "
            "à 41 ont exigé une intervention de fond de MM (correction de diagnostic, de "
            "critère ou de décision : lots 21, 23, 28 à 34, 36, 37, 39, entre autres). "
            "Ce n'est pas une mesure ; les interventions sont comptées à partir du lot 43."
        ),
    ),
)
LOTS = (
    LotRecord(
        lot="42",
        supervisor_interventions=DeclaredFigure(
            value=None,
            nature="non renseigné",
            note="à renseigner par MM dans le compte rendu (consigne du lot 42, étape 4)",
        ),
        avoided_errors=DeclaredFigure(
            value=None,
            nature="non renseigné",
            note="lot de construction de la base : aucune consultation n'a pu éviter d'erreur",
        ),
    ),
)


def main() -> int:
    entries = build_entries(ROOT)
    for entry in entries:
        write_entry(ROOT, entry)
    base = load_knowledge(ROOT)
    check = verify_against_repository(base)
    for problem in check.problems:
        print(f"ÉCART {problem}")
    if check.problems:
        return 1
    print(
        f"{len(entries)} entrées écrites ; {check.checked} preuves confrontées au dépôt."
    )

    path = registry_path(ROOT, PROJECT)
    previous = None
    if path.is_file():
        from aster_expert.connaissances.rex import load_registry  # noqa: PLC0415

        previous = load_registry(ROOT, PROJECT)
    registry = RexRegistry(
        project=PROJECT,
        case_roots=("projets/quai_cw_test_01", "data/examples"),
        legacy_runs=LEGACY,
        baseline=BASELINE,
        lots=previous.lots if previous and previous.lots else LOTS,
        reviews=previous.reviews if previous else (),
        classifications=previous.classifications if previous else (),
    )
    if not (ROOT / RUNS_RELATIVE).is_dir():
        print("Archives d'exécution absentes : classement non recalculé.")
        write_registry(ROOT, registry)
        return 0
    runs = project_runs(ROOT, registry, base)
    classifications = tuple(
        classify(r.signature, r.run) for r in runs if r.failed and r.signature
    )
    registry = registry.model_copy(update={"classifications": classifications})
    write_registry(ROOT, RexRegistry.model_validate(registry.model_dump()))
    print(
        f"{len(runs)} exécutions attribuées au projet, {len(classifications)} échecs "
        f"classés : {path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
