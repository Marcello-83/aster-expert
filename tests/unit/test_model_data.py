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
    ProfilePoint,
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


def test_the_versioned_file_has_no_missing_value_left_since_lot_27() -> None:
    """The 22 values `a_fournir` of lot 25 all found a source in the complementary
    data (`donnees_complementaires_combiwall_v1.md`); none remains, none was filled
    without one (each provided value is checked against its source text)."""
    items = load_model_data(_YAML).items()
    assert [n for n, v in items.items() if v.status == "a_fournir"] == []
    for name in (
        "geometrie.cote_tete_tubes",
        "tube.epaisseur_coque_retenue",
        "poutre_couronnement.position_axe_y",
        "charges.acceleration_pesanteur",
        "maillage.nombre_facettes_par_tube",
        "maillage.taille_verticale_visee",
    ):
        assert items[name].status == "fourni", name


def test_the_pressure_profiles_are_arrays_of_points_with_layers() -> None:
    items = load_model_data(_YAML).items()
    terres = items["eau_terres.profil_poussee_terres_permanent"].profile
    assert terres is not None
    g = [pt for pt in terres if pt.component == "G"]
    assert [(pt.z, pt.p, pt.layer) for pt in g][2:4] == [
        (-2.0, 24.0, "remblai"),
        (-2.0, 21.2, "sable"),
    ]  # a discontinuity: two points of the same Z, one per layer
    assert all(pt.layer for pt in terres)
    eau = items["eau_terres.profil_pression_eau_accidentel"].profile
    assert eau is not None
    assert [(pt.z, pt.p) for pt in eau] == [(3.0, 0.0), (-0.5, 35.0)]
    assert items["eau_terres.profil_poussee_terres_accidentel"].profile == terres


def test_a_profile_excludes_a_scalar_value() -> None:
    point = ProfilePoint(z=1.0, p=2.0)
    with pytest.raises(ValidationError, match="un seul"):
        DataValue(
            status="fourni", value=1, profile=(point,), unit="kPa", source=_DECISION
        )
    with pytest.raises(ValidationError, match="ni `profile`|ni `value`"):
        DataValue(
            status="a_fournir",
            profile=(point,),
            unit="kPa",
            required_by="5",
            comment="c",
        )


def test_the_consistency_check_reads_the_points_of_a_profile(tmp_path: Path) -> None:
    raw = yaml.safe_load(_YAML.read_text("utf-8"))
    raw["groups"]["eau_terres"]["profil_pression_eau_permanent"]["profile"][1]["p"] = (
        16.0
    )
    altered = tmp_path / "altered.yaml"
    altered.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    report = check_consistency(load_model_data(altered), sheet, _INPUTS)
    assert [r.name for r in report] == ["eau_terres.profil_pression_eau_permanent"]


def test_a_subsection_of_the_complementary_file_is_found_by_its_label() -> None:
    values = load_model_data(_YAML).items()
    assert values["tube.module_young"].source == ValueSource(
        kind="cas_test",
        document="donnees_complementaires_combiwall_v1.md",
        section="A.1",
    )
    altered = values["tube.module_young"].model_copy(update={"value": 200000})
    data = ModelData(
        project="p", case_reference="c", groups={"tube": {"module_young": altered}}
    )
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    (line,) = check_consistency(data, sheet, _INPUTS)
    assert "200000" in line.reason
    missing = altered.model_copy(
        update={
            "source": ValueSource(
                kind="cas_test",
                document="donnees_complementaires_combiwall_v1.md",
                section="A.9",
            )
        }
    )
    data = ModelData(project="p", case_reference="c", groups={"t": {"m": missing}})
    (line,) = check_consistency(data, sheet, _INPUTS)
    assert "introuvable" in line.reason


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


def test_the_fiche_and_the_data_file_report_no_blocker() -> None:
    """Lot 31 : le point 3 (décision 4, jonction tête de tube / poutre) était
    en révision depuis ce lot -- seul bloqueur restant, plus aucune donnée
    manquante (lot 27, les 22 valeurs ont toutes trouvé une source).

    Lot 32 : la révision est levée (règle de construction des conditions aux
    limites de l'étape 1, décision 4 inchangée) -- plus aucun bloqueur."""
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text("utf-8"))
    data = load_model_data(_YAML)
    assert sheet.generation_blockers() == ()
    assert sheet.generation_blockers(data) == ()
    assert sheet.is_ready_for_generation


# --- lot 35 : profil de butée limite (donnees_butee_combiwall_v1.md) --------------


def _butee() -> DataValue:
    return load_model_data(_YAML).items()["sol.profil_butee_limite"]


def test_lot35_the_bearing_profile_is_copied_with_its_source() -> None:
    item = _butee()

    assert item.status == "fourni"
    assert item.unit == "kPa"
    assert item.source is not None
    assert item.source.document == "donnees_butee_combiwall_v1.md"
    assert item.profile is not None
    assert [(p.z, p.p, p.layer) for p in item.profile] == [
        (-12.0, 47.1, "argile marneuse"),
        (-18.0, 202.3, "argile marneuse"),
        (-18.0, 327.6, "marne compacte"),
        (-26.0, 603.6, "marne compacte"),
    ]


def test_lot35_the_bearing_source_is_the_whole_verbatim_document() -> None:
    """Le fichier est recopié à l'identique de celui que MM a validé au lancement du
    lot (aucune section numérotée : `section: "document"`)."""
    text = (_INPUTS / "donnees_butee_combiwall_v1.md").read_text(encoding="utf-8")

    assert numbers_in("47,1") == [(47.1, 1)]
    for value in ("47,1", "202,3", "327,6", "603,6", "12,00", "26,00"):
        assert value in text
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text(encoding="utf-8"))
    assert check_consistency(load_model_data(_YAML), sheet, _INPUTS) == []


def test_lot35_a_bearing_value_absent_from_its_source_is_reported() -> None:
    item = _butee()
    assert item.profile is not None
    altered = item.model_copy(
        update={
            "profile": (
                *item.profile[:-1],
                item.profile[-1].model_copy(update={"p": 999.9}),
            )
        }
    )
    data = ModelData(
        project="p",
        case_reference="c",
        groups={"sol": {"profil_butee_limite": altered}},
    )
    sheet = HypothesesSheet.model_validate_json(_SHEET.read_text(encoding="utf-8"))

    (line,) = check_consistency(data, sheet, _INPUTS)

    assert "999.9" in line.reason
