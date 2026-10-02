"""Lot 44 : décision de MM sur le module de l'acier de la dalle (Es = 200 GPa).

Consigne du lot 44 (`docs/lots/lot44_consigne.md`, « Décisions de MM, validées par le
lancement du lot ») : « Module de l'acier : Es = 200 GPa (EN 1992-1-1, 3.2.7(4)), au
lieu des 210 GPa communiqués au lot 43 » ; « αe = 15 est maintenu : c'est un
coefficient d'équivalence de long terme, choisi délibérément, indépendant de Es » ;
« Le précédent de la dalle qui porte Es est corrigé, avec la mention de la
décision ».

- Entrée : la fiche arbitrée du lot 43 (`arbitrer_fiche_lot43.final_sheet`, conservée
  dans `fiche/historique/`).
- La décision passe par `record_practice_decision` sur l'entrée des paramètres ELS du
  point 14 : la décision du lot 43 (EYS = 210 000 MPa) va dans `decision_history`.
- Sorties : la fiche courante `fiche/hypotheses_dalle_arbitree.json`, son document
  `fiche/fiche_arbitree.md`, et le précédent PRE-031 réécrit à partir de l'entrée
  (`superseded_decisions` = 1, mention de la décision dans le titre et le résumé).

La valeur `acier.module_young` des données passe à 200 000 MPa (source : décision du
point 14), confrontée au texte de la décision par `check_consistency`.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/decisions_lot44.py`
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arbitrer_fiche_lot43 as lot43

from aster_expert.agent.arbitration import apply_decision, record_practice_decision
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.connaissances.base import write_entry
from aster_expert.connaissances.modeles import Precedent
from aster_expert.connaissances.precedents import precedent_from_entry
from aster_expert.constats.base import base_dir, load_base, resolve_sheet

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
FICHE = PROJECT / "fiche" / "hypotheses_dalle_arbitree.json"
DOCUMENT = PROJECT / "fiche" / "fiche_arbitree.md"
ELS_TOPIC = (
    "Paramètres ELS obligatoires de CALC_FERRAILLAGE en 2D (ALPHA_E, SIGC_*_ELS, "
    "SIGC_ELS_QP, KT, EYS)"
)
DECIDED_AT = datetime.fromisoformat("2026-10-02T09:03:49-04:00")
"""Heure de l'enregistrement par la session (MM n'en a écrit aucune ; règle du quai,
lot 24)."""
PRECEDENT_ID = "PRE-031"


def es_decision(entry: PracticeHypothesisEntry) -> PracticeHypothesisEntry:
    return record_practice_decision(
        entry=entry,
        option_retained=(
            "ALPHA_E = 15. SIGC_INF_ELS = SIGC_SUP_ELS = 0,6 fck = 18 MPa, avec un second "
            "calcul à valeur non contraignante pour montrer que la limite n'est pas active "
            "(rapportée si elle l'est). SIGC_ELS_QP = 0,45 fck = 13,5 MPa. KT = 0,4 "
            "(chargement de longue durée). EYS = 200 000 MPa (Es = 200 GPa, EN 1992-1-1, "
            "3.2.7(4) ; décision de MM au lot 44, au lieu des 210 GPa du lot 43)."
        ),
        justification=(
            "Réponses de MM aux questions de la session (complément d'arbitrage, "
            "donnees/sources/arbitrage_dalle_appuyee_01_complement_els.md) : ces "
            "paramètres sont obligatoires en 2D selon U4.81.42 et l'arbitrage v1 dit « pas "
            "de limite sur σc en XC1 ». Lot 44, décision de MM : « La valeur de 210 GPa "
            "est celle des aciers de construction (EN 1993). La réglementation du béton "
            "armé retient 200 GPa pour les armatures. »"
        ),
        validity_domain=(
            "La limite σc = 18 MPa est un artifice de saisie exigé par la commande, sans "
            "exigence de l'EC2 en XC1 : son inactivité est vérifiée par la sensibilité. "
            "αe = 15 est maintenu : c'est un coefficient d'équivalence de long terme, "
            "choisi délibérément, indépendant de Es (lot 44)."
        ),
        sources=(
            lot43._mm_complement(),
            PracticeSource(
                origin="arbitrage_mm",
                reference=(
                    "consigne du lot 44 (docs/lots/lot44_consigne.md), module de l'acier "
                    "Es = 200 GPa ; référence normative fournie par MM, non indexée"
                ),
                date=date(2026, 10, 2),
            ),
        ),
        discarded_variants=(
            DiscardedVariant(
                description="ALPHA_E = Es/Ecm (≈ 6,1).", reason="MM retient 15."
            ),
            DiscardedVariant(
                description="SIGC_*_ELS non contraignant sans sensibilité.",
                reason="MM retient 0,6 fck et demande la sensibilité.",
            ),
            DiscardedVariant(
                description="KT = 0,6 (courte durée).", reason="Longue durée."
            ),
            DiscardedVariant(
                description="EYS = 210 000 MPa (décision du lot 43).",
                reason=(
                    "valeur des aciers de construction (EN 1993) ; le béton armé retient "
                    "200 GPa pour les armatures (lot 44)."
                ),
            ),
        ),
        decided_by="MM",
        decided_at=DECIDED_AT,
    )


def current_sheet() -> HypothesesSheet:
    sheet = lot43.final_sheet()
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == "14"
        and e.topic == ELS_TOPIC
    )
    return apply_decision(sheet, es_decision(entry))


def precedent(sheet: HypothesesSheet) -> Precedent:
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.topic == ELS_TOPIC
    )
    return precedent_from_entry(
        entry,
        precedent_id=PRECEDENT_ID,
        title=f"Point 14 : {ELS_TOPIC} (Es corrigé au lot 44)",
        summary=(
            f"Décision de MM au point 14 de la fiche de la dalle (2026-10-02) : "
            f"{ELS_TOPIC} ; Es corrigé au lot 44 par décision de MM (200 GPa au lieu "
            "de 210 GPa, αe = 15 maintenu)."
        ),
        origin_project="dalle_appuyee_01",
        fiche="projets/dalle_appuyee_01/fiche/hypotheses_dalle_arbitree.json",
        recorded_on=dt.date(2026, 10, 2),
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
