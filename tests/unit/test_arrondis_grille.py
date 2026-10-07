"""Table d'arrondi unique et invariant de grille (lot 48 bis, remarque de MM)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.arrondis import (
    ArrondisError,
    GridRule,
    comm_value,
    format_value,
    load_table,
    off_grid_noise,
    round_value,
)
from aster_expert.meshing.grille import check_grid
from aster_expert.notes.tables import _format
from aster_expert.projet.declaration import NoteColumn

ROOT = Path(__file__).resolve().parents[2]
TABLE = load_table(ROOT)
RULE = TABLE.maillage


def test_the_table_gives_the_decimals_of_the_units() -> None:
    assert [TABLE.decimals(u) for u in ("m", "kN", "kN·m", "MPa")] == [3, 1, 1, 2]
    with pytest.raises(ArrondisError, match="absente"):
        TABLE.decimals("furlong")


def test_noise_is_rounded_away_and_never_prints_minus_zero() -> None:
    assert format_value(2.4999999999, "m", TABLE) == "2.500"
    assert format_value(0.30000000004, "m", TABLE) == "0.300"
    assert format_value(-1e-17, "kN", TABLE) == "0.0"
    assert round_value(-1e-17, "m", TABLE) == 0.0
    assert format_value(1234.5678, "kN", TABLE, decimal_comma=True) == "1234,6"


def test_a_derived_exact_value_keeps_its_precision_in_the_comm() -> None:
    radius = 0.30000000004
    text, comment = comm_value(radius, "m", TABLE, derived_exact=True)
    assert float(text) == radius and comment == "0.300 m"
    text, comment = comm_value(radius, "m", TABLE, derived_exact=False)
    assert float(text) == 0.3 and comment is None


def test_the_grid_invariant_sees_only_near_but_not_on_the_grid() -> None:
    assert off_grid_noise(2.5, RULE) is None  # sur la grille
    assert off_grid_noise(2.4999999999, RULE) == pytest.approx(1e-10, abs=1e-12)
    assert off_grid_noise(0.30000000004, RULE) is not None
    assert off_grid_noise(0.3004, RULE) is None  # loin de la grille : légitime


def test_the_report_counts_nodes_and_examples() -> None:
    coords = [(0.0, 0.0, 0.0), (2.4999999999, 0.5, 0.30000000004), (0.1234, 1.0, 2.0)]
    report = check_grid(coords, RULE)
    assert report.noisy == 2 and report.nodes_concerned == 1 and report.nodes == 3
    assert [e.axis for e in report.examples] == ["x", "z"]
    assert report.ok  # non bloquant dans la table du dépôt
    assert "écart rapporté" in report.line()
    blocking = GridRule(grille_decimales=3, epsilon=1e-6, bloquant=True)
    assert not check_grid(coords, blocking).ok


def test_the_repository_table_is_not_blocking_while_meshes_carry_deviations() -> None:
    assert RULE.bloquant is False and RULE.grid == pytest.approx(1e-3)


def test_a_note_column_with_a_unit_uses_the_table() -> None:
    column = NoteColumn(header="N", path="n", unit="kN")
    assert _format(1234.5678, column) == "1234,6"
    explicit = NoteColumn(header="N", path="n", unit="kN", format="{:.2f}")
    assert _format(1.234, explicit) == "1,23"
    assert _format("texte", column) == "texte"
