"""Lot 45 : correction de la mention de D21 dans la fiche courante de la dalle.

Consigne du lot 45 (`docs/lots/lot45_consigne.md`, « Décisions de MM, validées par le
lancement du lot ») : « Le lot 43 a retenu kc = 0,4 et Act = b·h/2. C'est
l'application de D21 à une pièce fléchie, et non une exception à D21 comme
l'affirmait l'arbitrage de Claude. Corrige en conséquence la mention dans le précédent
de la dalle concerné. »

- Entrée : la fiche courante du lot 44 (`decisions_lot44.current_sheet`).
- La correction passe par `record_practice_decision` sur l'entrée du ferraillage du
  point 14 (P6) : la décision du lot 43 va dans `decision_history`. L'option retenue
  (kc = 0,4, k = 1,0, Act = b·h/2) ne change pas ; la justification et les variantes
  écartées sont corrigées, D21 (PRE-020) est ajoutée aux sources.
- Sorties : la fiche courante, son document, et le précédent PRE-030 réécrit à partir de
  l'entrée (note de correspondance dans le résumé).

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/decisions_lot45.py`
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arbitrer_fiche_lot43 as lot43
import decisions_lot44 as lot44

from aster_expert.agent.arbitration import apply_decision, record_practice_decision
from aster_expert.agent.hypotheses import (
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.connaissances.base import write_entry
from aster_expert.connaissances.modeles import Precedent
from aster_expert.connaissances.precedents import precedent_from_entry
from aster_expert.constats.base import base_dir, load_base, resolve_sheet

FICHE = lot44.FICHE
DOCUMENT = lot44.DOCUMENT
P6_TOPIC = (
    "Ferraillage : acier, distance parement–axe, ELS en XC1 (contraintes, fissuration), "
    "ferraillage minimal"
)
DECIDED_AT = datetime.fromisoformat("2026-10-02T14:04:31+00:00")
"""Heure de l'enregistrement par la session (MM n'en a écrit aucune ; règle du quai,
lot 24), la même que celle des décisions du quai du lot 45."""
PRECEDENT_ID = "PRE-030"


def p6_decision(entry: PracticeHypothesisEntry) -> PracticeHypothesisEntry:
    assert entry.option_retained is not None
    assert "Act = b·h/2" in entry.option_retained
    return record_practice_decision(
        entry=entry,
        option_retained=entry.option_retained,
        justification=(
            "Décision P6 de MM. Distance à l'axe selon PRE-018 (enrobage mesuré au nu de "
            "l'armature). Maîtrise de la fissuration : application de D21 (PRE-020, "
            "décision de MM sur la poutre de couronnement du quai, EN 1992-1-1, 7.3.2) à "
            "une pièce fléchie : Act est la zone tendue complète de la section avant "
            "fissuration, soit b·h/2 en flexion ; kc = 0,4 dépend de la sollicitation ; "
            "k = 1,0 dépend de h (h ≤ 300 mm). Correction du lot 45 : l'arbitrage v1 et "
            "la fiche du lot 43 présentaient kc = 0,4 et Act = b·h/2 comme une exception "
            "à D21 (« PRE-021 », identifiant qui n'a jamais existé : D21 est PRE-020) ; "
            "c'est l'application de D21."
        ),
        validity_domain=entry.validity_domain or "",
        sources=(
            *entry.sources,
            PracticeSource(
                origin="arbitrage_mm",
                reference=(
                    "consigne du lot 45 (docs/lots/lot45_consigne.md), conséquence "
                    "pour la dalle : kc = 0,4 et Act = b·h/2 appliquent D21 (PRE-020)"
                ),
                date=date(2026, 10, 2),
            ),
        ),
        discarded_variants=tuple(
            v
            for v in entry.discarded_variants
            if not v.description.startswith("Act = zone tendue complète")
        ),
        decided_by="MM",
        decided_at=DECIDED_AT,
    )


def current_sheet() -> HypothesesSheet:
    sheet = lot44.current_sheet()
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == "14"
        and e.topic == P6_TOPIC
    )
    return apply_decision(sheet, p6_decision(entry))


def precedent(sheet: HypothesesSheet) -> Precedent:
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.topic == P6_TOPIC
    )
    return precedent_from_entry(
        entry,
        precedent_id=PRECEDENT_ID,
        title=f"Point 14 : {P6_TOPIC}",
        summary=(
            f"Décision de MM au point 14 de la fiche de la dalle (2026-10-02) : "
            f"{P6_TOPIC} ; kc = 0,4 et Act = b·h/2 appliquent D21 (PRE-020) à une pièce "
            "fléchie, ils n'en sont pas une exception (correction du lot 45 ; "
            "« PRE-021 » n'a jamais existé)."
        ),
        origin_project="dalle_appuyee_01",
        fiche="projets/dalle_appuyee_01/fiche/hypotheses_dalle_arbitree.json",
        recorded_on=date(2026, 10, 2),
    )


def main() -> int:
    sheet = current_sheet()
    FICHE.write_text(
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    DOCUMENT.write_text(lot43.render(sheet), encoding="utf-8")
    write_entry(ROOT, precedent(sheet))
    resolved = resolve_sheet(sheet, load_base(base_dir(ROOT)))
    data = load_model_data(lot43.DATA)
    discrepancies = check_consistency(data, resolved, lot43.SOURCES)
    print(f"fiche courante : {FICHE.relative_to(ROOT)}")
    print(f"bloqueurs : {len(resolved.generation_blockers(data))}")
    print(f"écarts données/sources : {[str(d) for d in discrepancies]}")
    return 1 if discrepancies else 0


if __name__ == "__main__":
    raise SystemExit(main())
