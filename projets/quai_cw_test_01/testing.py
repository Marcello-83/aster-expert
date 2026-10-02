"""Test support: the fiche of the quai, ready for generation (lot 45).

The versioned fiche declares the decision on Es « en révision » (generation blocker)
until the quai is recomputed with Es = 200 GPa. The generator tests exercise the
mechanics of the generator, not that decision: they read a copy of the fiche in
`resultats/` (not versioned) where only this revision is lifted. The versioned fiche is
never written.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from aster_expert.agent.arbitration import lift_revision
from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry

FICHE = (
    Path(__file__).resolve().parent
    / "fiche"
    / ("hypotheses_combiwall_reference_arbitree.json")
)


@cache
def fiche_generable() -> Path:
    """Path of a copy of the fiche with every revision lifted (test use only)."""
    sheet = HypothesesSheet.model_validate_json(FICHE.read_text(encoding="utf-8"))
    entries = []
    for entry in sheet.entries:
        if isinstance(entry, PracticeHypothesisEntry) and entry.under_revision:
            assert entry.revision_history[-1].at is not None
            entry = lift_revision(
                entry,
                reason="copie de test : décision Es en attente, levée en mémoire",
                lifted_by="tests",
                lifted_at=entry.revision_history[-1].at,
            )
        entries.append(entry)
    copy = sheet.model_copy(update={"entries": tuple(entries)})
    # Under the project (not /tmp): the constats base is found above the fiche.
    directory = FICHE.parent.parent / "resultats" / "tests_fiche_generable"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / FICHE.name
    path.write_text(
        json.dumps(copy.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
