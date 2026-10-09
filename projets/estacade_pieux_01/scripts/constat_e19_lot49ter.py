"""Lot 49 ter -- finding on E19: attribution of C6 updated in REF-015.

The §20.5.1 of the source writes « h = 0.80 m (augmenté à 0.90m) »: the forces of the
source model were very probably computed with a cap beam of 0.80 m. The attribution of
C6 moves from « hypothèse non établie » to « probable, appuyée par le texte de la
source » (consigne du lot 49 ter, étape 0). The reference E1 to E23 does not change,
nor the status, the values or the verdicts of REF-015: only the note of its three C6
lines. Idempotent: rerun `.venv/bin/python
projets/estacade_pieux_01/scripts/constat_e19_lot49ter.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.connaissances.base import load_knowledge, write_entry
from aster_expert.connaissances.modeles import ValidationReference

NOTE = (
    "verdict du rapport : hors tolérance ; attribution (lot 49 ter, constat sur E19) : "
    "C, chevêtre de 0,80 m dans le modèle source -- probable, appuyé par le texte de "
    "la source (§20.5.1 : « h = 0.80 m (augmenté à 0.90m) ») ; avec 0,80 m la barre "
    "seule tient la tolérance (lot 47 bis, § 9 ; lot 47 quater, § 5.4) ; et A, la "
    "source publie la barre (E17.2 compare le total). Référence E1 à E23 inchangée."
)


def main() -> None:
    base = load_knowledge(ROOT)
    entry = base.entries["REF-015"]
    assert isinstance(entry, ValidationReference)
    cases = []
    changed = 0
    for case in entry.cases:
        quantities = []
        for q in case.quantities:
            if q.name.startswith("C6 "):
                q = q.model_copy(update={"note": NOTE})
                changed += 1
            quantities.append(q)
        cases.append(case.model_copy(update={"quantities": tuple(quantities)}))
    updated = entry.model_copy(update={"cases": tuple(cases)})
    path = write_entry(ROOT, ValidationReference.model_validate(updated.model_dump()))
    print(path.relative_to(ROOT), changed, "ligne(s) C6")


if __name__ == "__main__":
    main()
