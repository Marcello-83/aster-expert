"""Lot 49 : règles du tronc commun touchées par les livrables -- tolérance d'un nombre
en décimales fixes dans le contrôle des notes, règle de conservation appliquée au
niveau C du paquet."""

from __future__ import annotations

from aster_expert.notes.controle import _tolerates
from aster_expert.projet.paquet import _levels


def test_a_fixed_decimal_display_is_an_absolute_precision() -> None:
    assert _tolerates("0", -1.5e-6)  # N : 0 décimale, bruit de calcul
    assert _tolerates("12.3", 12.34)
    assert not _tolerates("12.3", 12.5)
    assert not _tolerates("0", 0.6)
    assert _tolerates("1.235e+05", 123456.0)
    assert not _tolerates("1.2e+05", 0.0)


def test_level_c_says_when_the_conservation_rule_holds() -> None:
    report = {"status": "completed_ok", "diag": "OK"}
    rule = "identique hors commentaires et en-tête (règle de conservation, lot 45)"
    levels = _levels({}, report, True, None, False, None, None, comm_rule=rule)
    c = next(step for step in levels["par_niveau"] if step["niveau"] == "C")
    assert c["atteint"] and rule in c["motif"]
    refused = _levels({}, report, False, None, False, None, None, comm_rule=rule)
    c = next(step for step in refused["par_niveau"] if step["niveau"] == "C")
    assert not c["atteint"] and "DIFFÉRENT" in c["motif"] and rule not in c["motif"]
