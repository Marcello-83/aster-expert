"""Structured model data of the combi-wall case (lot 25): schema, consistency
check against the sources, and generation blockers.

No network, no Docker. The repository file is checked against the versioned fiche
and the versioned test-case files.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.model_data import (
    DataValue,
    ModelData,
    ValueSource,
    check_consistency,
    load_model_data,
    numbers_in,
)

_ROOT = Path(__file__).resolve().parents[2]
_YAML = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"
_SHEET = _ROOT / "data" / "examples" / "hypotheses_combiwall_reference_arbitree.json"
_INPUTS = _ROOT / "data" / "examples" / "combiwall_inputs"

_DECISION = ValueSource(kind="decision", point_label="8")


def _sheet(option: str) -> HypothesesSheet:
    entry = PracticeHypothesisEntry(
        point_label="8",
        topic="t",
        status="tranche",
        option_retained=option,
        justification="j",
        validity_domain="v",
        sources=(
            PracticeSource(
                origin="decision_ingenieur", reference="MM", date=datetime(2026, 1, 1)
            ),
        ),
        discarded_variants=(DiscardedVariant(description="d", reason="r"),),
        decided_by="MM",
        decided_at=datetime(2026, 1, 1),
    )
    return HypothesesSheet(
        project_name="p",
        structure_description="s",
        created_at=datetime(2026, 1, 1),
        entries=(entry,),
    )


def _data(**values: DataValue) -> ModelData:
    return ModelData(project="p", case_reference="c", groups={"g": values})


def _provided(value: float | str | tuple[float, ...]) -> DataValue:
    return DataValue(status="fourni", value=value, unit="u", source=_DECISION)


def test_numbers_in_reads_french_notation() -> None:
    text = "Effort de 1 000 kN, k = 35 MN/m³, de −12,00 à +4,00 ; ±0,71 m ; sept tubes"
    found = dict(numbers_in(text))
    assert found[1000.0] == 0
    assert found[35.0] == 0
    assert found[-12.0] == 2
    assert found[4.0] == 2
    assert found[0.71] == 2
    assert found[7.0] == 0
    # narrow no-break space and no-break space as thousands separators
    assert (2908.0, 0) in numbers_in("2 908 MN/m") + numbers_in("2 908")


def test_numbers_in_does_not_glue_separate_quantities() -> None:
    values = [v for v, _ in numbers_in("35 MN, 80 MN/m³ et 22,00 + 8,00/2 = 26,00")]
    assert 35.0 in values
    assert 80.0 in values
    assert 26.0 in values
    assert 35080.0 not in values


def test_consistency_accepts_a_value_within_the_displayed_rounding() -> None:
    sheet = _sheet("Raideur ≈ 35,7 MN/m ; effort de 1 000 kN ; 2 908 MN/m")
    data = _data(a=_provided(35.7), b=_provided(1000), c=_provided(2908))
    assert check_consistency(data, sheet, _INPUTS) == []
    assert check_consistency(_data(a=_provided(35.74)), sheet, _INPUTS) == []


def test_consistency_reports_a_wrong_value_without_correcting_it() -> None:
    sheet = _sheet("Raideur ≈ 35,7 MN/m")
    data = _data(a=_provided(35.9), b=_provided("S355"))
    report = check_consistency(data, sheet, _INPUTS)
    assert [r.name for r in report] == ["g.a", "g.b"]
    assert "35.9" in report[0].reason
    assert data.items()["g.a"].value == 35.9  # untouched


def test_consistency_reports_a_missing_source() -> None:
    data = _data(a=DataValue(status="fourni", value=1, unit="u", source=_DECISION))
    sheet = _sheet("x")
    other = ModelData(
        project="p",
        case_reference="c",
        groups={
            "g": {
                "a": DataValue(
                    status="fourni",
                    value=1,
                    unit="u",
                    source=ValueSource(kind="decision", point_label="42"),
                ),
                "b": DataValue(
                    status="fourni",
                    value=1,
                    unit="u",
                    source=ValueSource(
                        kind="cas_test", document="absent.md", section="§1"
                    ),
                ),
                "c": DataValue(
                    status="fourni",
                    value=1,
                    unit="u",
                    source=ValueSource(
                        kind="cas_test",
                        document="cas_test_quai_combiwall_v2.md",
                        section="§99",
                    ),
                ),
            }
        },
    )
    assert check_consistency(data, sheet, _INPUTS)[0].reason.startswith("absent")
    reasons = [r.reason for r in check_consistency(other, sheet, _INPUTS)]
    assert "aucune décision tranchée au point 42" in reasons[0]
    assert "introuvable" in reasons[1]
    assert "section §99 introuvable" in reasons[2]


def test_consistency_checks_test_case_sections() -> None:
    source = ValueSource(
        kind="cas_test", document="cas_test_quai_combiwall_v2.md", section="§2"
    )
    ok = DataValue(status="fourni", value=1420, unit="mm", source=source)
    wrong = DataValue(status="fourni", value=1520, unit="mm", source=source)
    assert check_consistency(_data(a=ok), _sheet("x"), _INPUTS) == []
    assert len(check_consistency(_data(a=wrong), _sheet("x"), _INPUTS)) == 1


def test_schema_refuses_incoherent_values() -> None:
    with pytest.raises(ValidationError, match="requis"):
        DataValue(status="fourni", unit="m", source=_DECISION)
    with pytest.raises(ValidationError, match="requis"):
        DataValue(status="fourni", value=1, unit="m")
    with pytest.raises(ValidationError, match="reste absente"):
        DataValue(status="a_fournir", value=1, unit="m", required_by="1", comment="c")
    with pytest.raises(ValidationError, match="required_by"):
        DataValue(status="a_fournir", unit="m")
    with pytest.raises(ValidationError, match="n'a pas de sens"):
        DataValue(status="fourni", value=1, unit="m", source=_DECISION, required_by="1")
    with pytest.raises(ValidationError):
        DataValue(status="fourni", value=1, unit="m", source=_DECISION, extra=1)  # type: ignore[call-arg]


def test_source_schema_matches_its_kind() -> None:
    with pytest.raises(ValidationError, match="document"):
        ValueSource(kind="cas_test", section="§1")
    with pytest.raises(ValidationError, match="point_label"):
        ValueSource(kind="decision")
    with pytest.raises(ValidationError, match="topic_prefix"):
        ValueSource(kind="constat", point_label="1")
    with pytest.raises(ValidationError, match="topic_prefix"):
        ValueSource(kind="decision", point_label="1", topic_prefix="x")


def test_a_missing_value_is_a_generation_blocker() -> None:
    missing = DataValue(status="a_fournir", unit="Pa", required_by="5", comment="c")
    data = _data(a=_provided(1), profil=missing)
    sheet = _sheet("x")
    assert data.missing_values() == ("valeur à fournir (point 5) : g.profil [Pa] -- c",)
    assert not any("valeur à fournir" in b for b in sheet.generation_blockers())
    assert any("g.profil" in b for b in sheet.generation_blockers(data))


# --- the versioned data file ---------------------------------------------------


def test_the_versioned_file_is_valid_and_consistent_with_its_sources() -> None:
    data = load_model_data(_YAML)
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    assert data.project == "QUAI-CW-TEST-01"
    assert check_consistency(data, sheet, _INPUTS) == []


def test_the_versioned_file_marks_the_absent_values_as_such() -> None:
    items = load_model_data(_YAML).items()
    missing = {name for name, v in items.items() if v.status == "a_fournir"}
    # the profiles of earth and water pressure (point 5) are absent from every source
    assert {
        "eau_terres.profil_poussee_terres_permanent",
        "eau_terres.profil_pression_eau_permanent",
        "eau_terres.profil_poussee_terres_accidentel",
        "eau_terres.profil_pression_eau_accidentel",
    } <= missing
    assert "charges.acceleration_pesanteur" in missing
    assert "maillage.nombre_facettes_par_tube" in missing
    assert len(missing) == 22
    assert all(items[name].value is None for name in missing)


def test_the_versioned_file_keeps_the_units_of_its_sources() -> None:
    items = load_model_data(_YAML).items()
    assert items["charges.amarrage_effort"].unit == "kN"
    assert items["palplanche.MEMB_L"].unit == "MN/m"
    assert items["palplanche.FLEX_L"].unit == "MN.m2/m"
    assert items["tube.diametre_exterieur"].unit == "mm"


def test_the_consistency_check_catches_an_altered_file(tmp_path: Path) -> None:
    raw = yaml.safe_load(_YAML.read_text("utf-8"))
    raw["groups"]["tube"]["rayon"]["value"] = 0.72
    raw["groups"]["charges"]["amarrage_effort"]["value"] = 1200
    altered = tmp_path / "altered.yaml"
    altered.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    report = check_consistency(load_model_data(altered), sheet, _INPUTS)
    assert sorted(r.name for r in report) == ["charges.amarrage_effort", "tube.rayon"]


def test_the_fiche_still_reports_no_blocker_of_its_own_and_the_file_adds_its_own() -> (
    None
):
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    data = load_model_data(_YAML)
    assert sheet.generation_blockers() == ()
    blockers = sheet.generation_blockers(data)
    assert len(blockers) == 22
    assert all(b.startswith("valeur à fournir (point ") for b in blockers)
    assert sheet.is_ready_for_generation  # the fiche alone: ready, the data file blocks
