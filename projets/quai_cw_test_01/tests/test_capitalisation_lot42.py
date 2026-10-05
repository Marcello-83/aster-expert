"""Amorçage de la base de connaissances avec le quai (lot 42, étape 5).

Les entrées versionnées sous `connaissances/` sont celles que construit
`quai_cw_test_01.capitalisation` : le test les reconstruit et les compare octet
pour octet (aucune entrée éditée à la main sans passer par le module). Le
classement des 73 échecs est vérifié contre le registre ; il exige les archives
d'exécution (VM) et est ignoré, avec son motif, sans elles.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from aster_expert.connaissances.archive import archive_problem
from aster_expert.connaissances.base import (
    dump_entry,
    entry_path,
    load_knowledge,
    read_entry,
)
from aster_expert.connaissances.rex import load_registry, project_runs
from quai_cw_test_01.capitalisation import PROJECT, build_entries, classify

ROOT = Path(__file__).resolve().parents[3]


def test_every_seeded_entry_is_rebuilt_byte_for_byte() -> None:
    entries = build_entries(ROOT)
    assert len(entries) == 79  # lot 45 : + Es (PRE-032)
    for entry in entries:
        path = entry_path(ROOT, entry)
        # Lot 43 : un projet suivant n'ajoute que des réutilisations (`reuses`) ;
        # tout le reste de l'amorçage est reconstruit à l'octet.
        versioned = read_entry(path, entry.layer)
        assert versioned.reuses == () or all(
            r.project != PROJECT for r in versioned.reuses
        ), path
        # Lot 44 : une promotion (statut et historique, par la commande) n'est pas
        # de l'amorçage non plus.
        if versioned.status == "promu":
            assert versioned.status_history[-1].status == "promu", path
            versioned = versioned.model_copy(
                update={
                    "status": entry.status,
                    "status_history": versioned.status_history[:-1],
                }
            )
        assert dump_entry(versioned.model_copy(update={"reuses": ()})) == dump_entry(
            entry
        ), path


def test_no_seeded_entry_is_promoted_and_precedents_cover_every_decision() -> None:
    base = load_knowledge(ROOT)
    # Lot 44 : les seules promotions sont celles de la règle corrigée.
    promoted = {e.id for e in base.all_entries() if e.status == "promu"}
    assert promoted == {"CTL-005", "CTL-006", "CTL-012", "PAT-011", "REF-014"}
    fiche = yaml.safe_load(
        (
            ROOT
            / "projets"
            / PROJECT
            / "fiche"
            / "hypotheses_combiwall_reference_arbitree.json"
        ).read_text(encoding="utf-8")
    )
    decided = [
        e
        for e in fiche["entries"]
        if e.get("nature") == "pratique" and e.get("status") == "tranche"
    ]
    seeded = [
        e
        for k, e in base.entries.items()
        if k.startswith("PRE-") and e.origin_project == PROJECT
    ]
    assert len(seeded) == len(decided)


def test_the_baseline_metrics_are_declared_as_such() -> None:
    registry = load_registry(ROOT, PROJECT)
    assert registry.baseline is not None
    assert (registry.baseline.executions, registry.baseline.failures) == (190, 73)
    assert registry.baseline.supervisor_interventions.nature == "estimation"


# Lot 46 : l'archive doit être celle du manifeste du registre (ni absente, ni partielle
# comme dans le Cloud, ni étrangère).
_ARCHIVE_PROBLEM = archive_problem(ROOT)


@pytest.mark.skipif(
    _ARCHIVE_PROBLEM is not None,
    reason=f"archive d'exécution non conforme au manifeste : {_ARCHIVE_PROBLEM}",
)
def test_the_73_archived_failures_are_classified_as_recorded() -> None:
    registry = load_registry(ROOT, PROJECT)
    base = load_knowledge(ROOT)
    runs = project_runs(ROOT, registry, base)
    legacy = [r for r in runs if r.started < registry.legacy_runs.before]  # type: ignore[union-attr]
    assert len(legacy) == 190
    failed = [r for r in runs if r.failed]
    assert len(failed) == 73
    recorded = {c.run: c for c in registry.classifications}
    for r in failed:
        assert r.signature is not None
        assert classify(r.signature, r.run) == recorded[r.run]
    decisions = Counter(c.decision for c in registry.classifications)
    assert decisions == {"rattaché": 69, "écarté": 4}
