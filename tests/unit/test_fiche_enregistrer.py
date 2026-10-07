"""`aster-expert fiche enregistrer` (lot 48 bis, audit R6) : rejeu de l'enregistrement
de E13 à E16 de l'estacade, identique à celui du script `fiche_lot47.py`."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from aster_expert.agent.enregistrement import (
    RecordingError,
    check_quotes,
    parse_arbitration,
    record_decisions,
)
from aster_expert.agent.hypotheses import HypothesesSheet, PracticeHypothesisEntry
from aster_expert.cli import app

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projets" / "estacade_pieux_01"
SOURCES = PROJECT / "donnees" / "sources"
ENREGISTREMENT = SOURCES / "enregistrement_E13_E16_lot48bis.md"
LABELS = ("E13", "E14", "E15", "E16")


def _sheet() -> HypothesesSheet:
    return HypothesesSheet.model_validate_json(
        (PROJECT / "fiche" / "hypotheses_estacade_pieux_01.json").read_text("utf-8")
    )


def _reopened(sheet: HypothesesSheet) -> HypothesesSheet:
    """The fiche as it stood before the decisions E13 to E16: open questions."""
    entries = tuple(
        PracticeHypothesisEntry(
            point_label=e.point_label,
            topic=e.topic,
            status="non_tranche",
            notes=e.notes,
        )
        if isinstance(e, PracticeHypothesisEntry) and e.point_label in LABELS
        else e
        for e in sheet.entries
    )
    return sheet.model_copy(update={"entries": entries})


def test_replaying_e13_to_e16_gives_the_recorded_fiche() -> None:
    real = _sheet()
    arbitration = parse_arbitration(ENREGISTREMENT.read_text(encoding="utf-8"))
    check_quotes(
        arbitration,
        (PROJECT / arbitration.source).read_text(encoding="utf-8"),
    )
    replayed, done = record_decisions(_reopened(real), arbitration)
    assert [d.split(" :")[0] for d in done] == list(LABELS)
    assert all(d.endswith("tranché") for d in done)
    assert replayed.model_dump_json() == real.model_dump_json()


def test_a_decision_already_taken_is_re_arbitrated_with_its_history() -> None:
    real = _sheet()
    arbitration = parse_arbitration(ENREGISTREMENT.read_text(encoding="utf-8"))
    again, done = record_decisions(real, arbitration)
    assert all(d.endswith("ré-arbitré") for d in done)
    e13 = next(
        e
        for e in again.entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == "E13"
    )
    assert len(e13.decision_history) == 1


def test_a_point_absent_from_the_fiche_is_inserted() -> None:
    real = _sheet()
    text = ENREGISTREMENT.read_text(encoding="utf-8").replace(
        "### E14 — Étendue du bouchon des pieux", "### E99 — Point nouveau"
    )
    arbitration = parse_arbitration(text)
    without = real.model_copy(
        update={
            "entries": tuple(
                e for e in real.entries if getattr(e, "point_label", None) != "E14"
            )
        }
    )
    inserted, done = record_decisions(without, arbitration)
    assert any(line == "E99 : inséré" for line in done)
    assert len(inserted.entries) == len(without.entries) + 1


def test_a_retyped_text_is_refused() -> None:
    arbitration = parse_arbitration(
        ENREGISTREMENT.read_text(encoding="utf-8").replace(
            "Le bouchon va de +0.70 à -0.80", "Le bouchon va de +0.70 à -0.90"
        )
    )
    with pytest.raises(RecordingError, match="E14.*à l'identique"):
        check_quotes(
            arbitration,
            (SOURCES / "arbitrage_estacade_pieux_01_lot47.md").read_text("utf-8"),
        )


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("Enregistré le : ", "Autre : ", "Enregistré le"),
        ("2026-10-05T05:48:41-04:00", "2026-10-05T05:48:41", "fuseau"),
        ("- Écartée : Nœud du tablier", "- Rien : Nœud du tablier", "puce inconnue"),
        ("- Note : ", "- Remarque : ", "puce inconnue"),
    ],
)
def test_a_malformed_file_is_refused(old: str, new: str, message: str) -> None:
    with pytest.raises(RecordingError, match=message):
        parse_arbitration(ENREGISTREMENT.read_text(encoding="utf-8").replace(old, new))


def test_the_command_simulates_without_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASTER_EXPERT_ROOT", str(ROOT))
    fiche = PROJECT / "fiche" / "hypotheses_estacade_pieux_01.json"
    before = fiche.read_bytes()
    result = CliRunner().invoke(
        app,
        ["fiche", "enregistrer", "estacade_pieux_01", str(ENREGISTREMENT), "--simuler"],
    )
    assert result.exit_code == 0, result.output
    assert "E13 : ré-arbitré" in result.output and "Simulation" in result.output
    assert fiche.read_bytes() == before
