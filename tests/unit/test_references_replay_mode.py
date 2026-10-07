"""Lot 48 bis (audit R3, A15) : mode de rejeu des références et cas de référence.

Une référence « établie » déclare un mode de rejeu ; chaque mode déclaré a son test
(ici) ; un cas de référence d'un projet porte sa déclaration de connaissances (sans
quoi son rejeu est refusé, REF-014 au lot 46)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aster_expert.connaissances.base import (
    dump_entry,
    knowledge_dir,
    load_knowledge,
)
from aster_expert.connaissances.declaration import COMPANION_SUFFIX
from aster_expert.connaissances.modeles import REPLAY_MODES, ValidationReference
from aster_expert.connaissances.references import replay_references
from aster_expert.execution.models import ExecutionReport

ROOT = Path(__file__).resolve().parents[2]


def _references() -> list[ValidationReference]:
    base = load_knowledge(ROOT)
    return [e for e in base.entries.values() if isinstance(e, ValidationReference)]


def _report(work_dir: Path, mess: Path, comm: Path) -> ExecutionReport:
    return ExecutionReport(
        comm_path=str(comm),
        aster_version="17.4.0",
        image_digest="sha256:" + "0" * 64,
        status="completed_ok",
        diag="OK",
        return_code=0,
        work_dir=str(work_dir),
        mess_path=str(mess),
        result_files=(),
        duration_s=1.0,
        extracted_by="run_aster.status",
        executed_at=dt.datetime(2026, 10, 7, tzinfo=dt.UTC),
        messages=(),
        messages_source="run_aster.error_messages",
    )


def test_every_established_reference_declares_a_tested_mode() -> None:
    for ref in _references():
        if ref.status in ("établi", "promu"):
            assert ref.replay_mode in REPLAY_MODES, ref.id
    # Chaque mode du registre a son test ci-dessous.
    assert set(REPLAY_MODES) == {"listing"}


def test_ref_015_is_observed_with_its_reason() -> None:
    ref = next(r for r in _references() if r.id == "REF-015")
    assert ref.status == "observé" and ref.replay_mode is None
    assert ref.status_history[-1].status == "observé"
    assert "0/30" in ref.status_history[-1].reason


def test_an_established_reference_without_mode_is_refused() -> None:
    ref = next(r for r in _references() if r.id == "REF-001")
    data = ref.model_dump(mode="json")
    data.pop("replay_mode")
    with pytest.raises(ValidationError, match="mode de rejeu"):
        ValidationReference.model_validate(data)


def test_entry_files_are_canonical() -> None:
    for ref in _references():
        path = knowledge_dir(ROOT) / "references_validation" / f"{ref.id}.yaml"
        assert path.read_text(encoding="utf-8") == dump_entry(ref), ref.id


def test_mode_listing_finds_printed_values_and_flags_missing_ones(
    tmp_path: Path,
) -> None:
    ref = next(r for r in _references() if r.id == "REF-001")
    values = [q.value_obtained for c in ref.cases for q in c.quantities]

    def run_with(lines: list[str]) -> tuple[str, ...]:
        mess = tmp_path / "fake.mess"
        mess.write_text("\n".join(lines), encoding="utf-8")
        result = replay_references(
            ROOT,
            only=("REF-001",),
            output_dir=tmp_path / "out",
            runner=(
                lambda comm: _report(tmp_path, mess, comm),
                "17.4.0",
                "d",
            ),
        )
        return tuple(r.verdict for r in result.references)

    assert run_with([f"{v:.12E}" for v in values]) == ("tient",)
    assert run_with(["rien d'imprimé"]) == ("à réexaminer",)


def test_a_full_replay_skips_references_without_mode(tmp_path: Path) -> None:
    mess = tmp_path / "fake.mess"
    mess.write_text("", encoding="utf-8")
    result = replay_references(
        ROOT,
        only=(),
        output_dir=tmp_path / "out",
        runner=(lambda comm: _report(tmp_path, mess, comm), "17.4.0", "d"),
    )
    assert result.skipped == ("REF-015",)
    assert "REF-015" not in {r.reference_id for r in result.references}
    assert any("REF-015 : non rejouée" in line for line in result.lines())


def test_every_reference_case_of_a_project_declares_its_knowledge() -> None:
    """REF-014 : deux cas sur trois sans déclaration (lot 46) étaient non rejouables."""
    cases = sorted(ROOT.glob("projets/*/references/cas/*.comm"))
    assert cases
    for comm in cases:
        companion = comm.with_name(comm.stem + COMPANION_SUFFIX)
        assert companion.is_file(), f"{comm.name} sans {companion.name}"
        declared = yaml.safe_load(companion.read_text(encoding="utf-8"))
        assert declared["applied"], companion.name
