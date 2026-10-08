"""Lot 47 quater -- knowledge of the closing lot of the jetty.

1. PRE-039: the decision E20 of MM (DKT or DST for a slab coupled to beams sharing its
   nodes), copied from the fiche by `precedent_from_entry`, with the evidence MM names
   (CA-058 and the factorial plan of lot 47 ter). Never applied automatically: it is
   proposed in a new fiche and arbitrated by MM.

Idempotent: rerun `.venv/bin/python projets/estacade_pieux_01/scripts/
connaissances_lot47quater.py`; a test replays it and compares byte for byte.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.connaissances.base import write_entry
from aster_expert.connaissances.modeles import (
    ConstatEvidence,
    DocumentEvidence,
    Precedent,
)
from aster_expert.connaissances.precedents import precedent_from_entry

PROJECT = "estacade_pieux_01"
FICHE = f"projets/{PROJECT}/fiche/hypotheses_estacade_pieux_01.json"
TODAY = dt.date(2026, 10, 6)


LOT49_SCOPE = (
    " Portée (consigne du lot 49, MM) -- précédent pour les projets futurs ; la "
    "référence de l'estacade reste en DKT (E13), sans recalcul."
)


def pre_039() -> Precedent:
    sheet = HypothesesSheet.model_validate_json((ROOT / FICHE).read_text("utf-8"))
    entry = next(
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == "E20"
    )
    base = precedent_from_entry(
        entry,
        precedent_id="PRE-039",
        title="DKT ou DST pour une dalle couplée à des poutres qui partagent ses nœuds",
        summary=(
            "Décision de MM (E20, lot 47 quater) : dalle DST quand ses nœuds sont partagés "
            "par des poutres POU_D_T (chevêtres, nervures), DKT admis sans poutre couplée ; "
            "en DKT, la dalle capte l'effort tranchant près des appuis et la barre seule le "
            "sous-estime."
        ),
        origin_project=PROJECT,
        fiche=FICHE,
        recorded_on=TODAY,
    )
    return base.model_copy(
        update={
            "sources": (
                *base.sources,
                ConstatEvidence(constat_id="CA-058"),
                DocumentEvidence(
                    path="docs/essais_lot47ter.md",
                    section="6.3 Plan factoriel : verdict de l'hypothèse",
                    note=(
                        "C8 barre seule ELU : 198,1 kN en DKT, 660,8 kN en DST (source "
                        "653 kN) ; total barre + dalle 722,5 et 733,3 kN ; moments et "
                        "globales à moins de 2 % entre DKT et DST"
                    ),
                ),
            ),
            "commands": ("AFFE_MODELE",),
            "keywords": ("DKT", "DST", "POU_D_T"),
            # Lot 49 (consigne de MM, étape 0.4) : portée du précédent.
            "validity_domain": base.validity_domain + LOT49_SCOPE,
        }
    )


def main() -> None:
    write_entry(ROOT, pre_039())
    print("PRE-039")


if __name__ == "__main__":
    main()
