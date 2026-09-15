"""Unit tests for scripts/introspect_catalogue.py's pure logic.

This script runs under the Aster Python inside the container in production
(docs/architecture.md, ADR-002) and is not part of the `aster_expert`
package. Its core walking/serialization logic dispatches on
``type(obj).__name__`` rather than ``isinstance`` against the real
``code_aster.Cata.Language.SyntaxObjects`` classes specifically so it can be
exercised here, under the project's own Python (which never has
`code_aster` installed), against lightweight stand-ins.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "introspect_catalogue.py"
)


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "introspect_catalogue_script", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


script = _load_script()


# --- fake stand-ins for code_aster.Cata.Language.SyntaxObjects --------------
# Named to match by `type(obj).__name__`, never imported from `code_aster`.


class FakeDefinition(dict[str, Any]):
    """Mimics `CataDefinition`: a dict mixing meta fields and children."""

    def __init__(self, meta: dict[str, Any], entities: dict[str, Any]) -> None:
        super().__init__(meta)
        self.update(entities)
        self._entities = entities

    @property
    def entities(self) -> dict[str, Any]:
        return self._entities


class SimpleKeyword:
    def __init__(self, definition: FakeDefinition) -> None:
        self.definition = definition


class FactorKeyword:
    def __init__(self, definition: FakeDefinition) -> None:
        self.definition = definition


class Bloc:
    def __init__(self, definition: FakeDefinition, condition: str) -> None:
        self.definition = definition
        self._condition = condition

    def getCondition(self) -> str:  # noqa: N802 - matches the real API
        return self._condition


class FakeConceptClass:
    """Stands in for a `DataStructure`/`MeshEntity` subclass."""


class Operator:
    def __init__(self, name: str, definition: FakeDefinition) -> None:
        self.name = name
        self.definition = definition


class Macro(Operator):
    pass


def _is_concept_class(cls: type) -> bool:
    return isinstance(cls, type) and issubclass(cls, FakeConceptClass)


# --- serialize_bound ----------------------------------------------------------


def test_serialize_bound_maps_unbounded_sentinel() -> None:
    assert script.serialize_bound("**") is None


def test_serialize_bound_passes_through_int() -> None:
    assert script.serialize_bound(3) == 3


# --- serialize_status -----------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("o", "required"), ("f", "optional"), ("c", "hidden"), ("d", "default")],
)
def test_serialize_status_known_values(raw: str, expected: str) -> None:
    assert script.serialize_status(raw) == expected


def test_serialize_status_unrecognized_raises() -> None:
    with pytest.raises(ValueError, match="unrecognized statut"):
        script.serialize_status("x")


# --- serialize_default_value ---------------------------------------------------


def test_serialize_default_value_passthrough() -> None:
    assert script.serialize_default_value(None) is None
    assert script.serialize_default_value(3) == 3
    assert script.serialize_default_value(3.5) == 3.5
    assert script.serialize_default_value("ELAS") == "ELAS"


def test_serialize_default_value_complex() -> None:
    assert script.serialize_default_value(0j) == {"real": 0.0, "imag": 0.0}
    assert script.serialize_default_value(1 + 2j) == {"real": 1.0, "imag": 2.0}


def test_serialize_default_value_list_and_tuple() -> None:
    assert script.serialize_default_value((1, 2, 3)) == [1, 2, 3]
    assert script.serialize_default_value([1.0, 2j]) == [
        1.0,
        {"real": 0.0, "imag": 2.0},
    ]


def test_serialize_default_value_unrecognized_raises() -> None:
    with pytest.raises(TypeError, match="unrecognized value"):
        script.serialize_default_value(object())


# --- serialize_typ_atom / serialize_value_type ---------------------------------


def test_serialize_typ_atom_known_code() -> None:
    assert script.serialize_typ_atom("TXM", _is_concept_class) == "TXM"


def test_serialize_typ_atom_unknown_code_raises() -> None:
    with pytest.raises(ValueError, match="unrecognized type code"):
        script.serialize_typ_atom("Fichier", _is_concept_class)


def test_serialize_typ_atom_concept_class() -> None:
    class cham_no_sdaster(FakeConceptClass):  # noqa: N801 - mirrors catalogue naming
        pass

    assert (
        script.serialize_typ_atom(cham_no_sdaster, _is_concept_class)
        == "cham_no_sdaster"
    )


def test_serialize_typ_atom_unrecognized_raises() -> None:
    class NotAConcept:
        pass

    with pytest.raises(TypeError, match="unrecognized SIMP type atom"):
        script.serialize_typ_atom(NotAConcept, _is_concept_class)


def test_serialize_value_type_single_and_tuple() -> None:
    assert script.serialize_value_type("R", _is_concept_class) == "R"

    class evol_noli(FakeConceptClass):  # noqa: N801
        pass

    class evol_elas(FakeConceptClass):  # noqa: N801
        pass

    assert script.serialize_value_type((evol_noli, evol_elas), _is_concept_class) == [
        "evol_noli",
        "evol_elas",
    ]


# --- walk_entities --------------------------------------------------------------


def test_walk_entities_simple_keyword_no_condition() -> None:
    definition = FakeDefinition(
        {"nom": "AFFE_CHAR_MECA"},
        {
            "MODELE": SimpleKeyword(
                FakeDefinition({"statut": "o", "typ": "TXM", "max": 1, "min": 1}, {})
            )
        },
    )
    cmd = Operator("AFFE_CHAR_MECA", definition)
    encountered: set[str] = set()
    result = script.walk_entities(cmd, [], [], _is_concept_class, encountered)

    assert result == [
        {
            "path": ["MODELE"],
            "variant_id": script.compute_variant_id(["MODELE"], []),
            "kind": "simple",
            "status": "required",
            "value_type": "TXM",
            "allowed_values": None,
            "default": None,
            "min_values": 1,
            "max_values": 1,
            "condition": [],
        }
    ]
    assert encountered == {"SimpleKeyword"}


def test_walk_entities_propagates_nested_bloc_conditions() -> None:
    innermost = SimpleKeyword(
        FakeDefinition({"statut": "f", "typ": "R", "max": 1, "min": 1}, {})
    )
    inner_bloc = Bloc(FakeDefinition({}, {"SEUIL": innermost}), 'exists("PRECISION")')
    outer_bloc = Bloc(FakeDefinition({}, {"b_seuil": inner_bloc}), 'TYPE == "A"')
    definition = FakeDefinition({"nom": "X"}, {"b_type": outer_bloc})
    cmd = Operator("X", definition)

    encountered: set[str] = set()
    result = script.walk_entities(cmd, [], [], _is_concept_class, encountered)

    assert len(result) == 1
    assert result[0]["path"] == ["SEUIL"]
    assert result[0]["condition"] == ['TYPE == "A"', 'exists("PRECISION")']
    assert encountered == {"SimpleKeyword", "Bloc"}


def test_walk_entities_factor_keyword_with_children() -> None:
    child = SimpleKeyword(
        FakeDefinition(
            {"statut": "o", "typ": "TXM", "max": 1, "min": 1, "into": ["ELAS"]}, {}
        )
    )
    factor = FactorKeyword(
        FakeDefinition({"statut": "f", "max": "**", "min": 0}, {"RELATION": child})
    )
    definition = FakeDefinition({"nom": "X"}, {"COMPORTEMENT": factor})
    cmd = Operator("X", definition)

    encountered: set[str] = set()
    result = script.walk_entities(cmd, [], [], _is_concept_class, encountered)

    assert result == [
        {
            "path": ["COMPORTEMENT"],
            "variant_id": script.compute_variant_id(["COMPORTEMENT"], []),
            "kind": "factor",
            "status": "optional",
            "min_occurrences": 0,
            "max_occurrences": None,
            "condition": [],
            "children": [
                {
                    "path": ["COMPORTEMENT", "RELATION"],
                    "variant_id": script.compute_variant_id(
                        ["COMPORTEMENT", "RELATION"], []
                    ),
                    "kind": "simple",
                    "status": "required",
                    "value_type": "TXM",
                    "allowed_values": ["ELAS"],
                    "default": None,
                    "min_values": 1,
                    "max_values": 1,
                    "condition": [],
                }
            ],
        }
    ]
    assert encountered == {"SimpleKeyword", "FactorKeyword"}


def test_walk_entities_defaults_absent_min_per_syntax_checker() -> None:
    """Matches `SyntaxChecker` exactly, verified against its source (lot 4):

    `visitSimpleKeyword` reads `min` with no default (no lower bound
    enforced when absent), while `_visitComposite` (factor keyword
    occurrence counting) defaults `min` to 0. Caught via the mandated manual
    comparison against `external/codeaster-src` (DEFI_MATERIAU.ELAS, which
    sets neither `min` nor `max`) — an earlier version of this extractor
    defaulted both to 1, which does not match the checker's own behavior.
    """
    child = SimpleKeyword(FakeDefinition({"statut": "f", "typ": "R"}, {}))
    factor = FactorKeyword(FakeDefinition({"statut": "f"}, {"E": child}))
    definition = FakeDefinition({"nom": "X"}, {"ELAS": factor})
    cmd = Operator("X", definition)

    result = script.walk_entities(cmd, [], [], _is_concept_class, set())

    assert result[0]["min_occurrences"] == 0  # FactorKeyword: get("min", 0)
    assert result[0]["max_occurrences"] == 1  # get("max", 1)
    child_entry = result[0]["children"][0]
    assert child_entry["min_values"] is None  # SimpleKeyword: get("min"), no default
    assert child_entry["max_values"] == 1  # get("max", 1)


def test_walk_entities_unrecognized_entity_type_raises() -> None:
    class Weird:
        pass

    definition = FakeDefinition({"nom": "X"}, {"ODD": Weird()})
    cmd = Operator("X", definition)

    with pytest.raises(TypeError, match="unrecognized entity type"):
        script.walk_entities(cmd, [], [], _is_concept_class, set())


# --- build_command_schema -------------------------------------------------------


def _empty_command(name: str, cls: type = Operator, **meta: Any) -> Any:
    definition = FakeDefinition({"nom": name, **meta}, {})
    return cls(name, definition)


def test_build_command_schema_kind_and_result_type_fixed() -> None:
    class evol_noli(FakeConceptClass):  # noqa: N801
        pass

    cmd = _empty_command("STAT_NON_LINE", sd_prod=evol_noli)
    schema = script.build_command_schema(
        cmd,
        aster_version="17.4.0",
        image_digest="sha256:abc",
        catalogue_hash="sha256:def",
        catalogue_source="/opt/x/code_aster",
        extracted_at="2026-01-01T00:00:00+00:00",
        is_concept_class=_is_concept_class,
        encountered_classes=set(),
    )
    assert schema["kind"] == "operator"
    assert schema["result_type"] == "evol_noli"
    assert schema["result_type_dynamic"] is False
    assert schema["docu"] is None


def test_build_command_schema_dynamic_result_type() -> None:
    def sd_prod_func(**_kwargs: object) -> None:
        return None

    cmd = _empty_command("DEFI_MATERIAU", cls=Macro, sd_prod=sd_prod_func)
    schema = script.build_command_schema(
        cmd,
        aster_version="17.4.0",
        image_digest="sha256:abc",
        catalogue_hash="sha256:def",
        catalogue_source="/opt/x/code_aster",
        extracted_at="2026-01-01T00:00:00+00:00",
        is_concept_class=_is_concept_class,
        encountered_classes=set(),
    )
    assert schema["kind"] == "macro"
    assert schema["result_type"] is None
    assert schema["result_type_dynamic"] is True


def test_build_command_schema_no_result_type() -> None:
    cmd = _empty_command("SOME_PROC", sd_prod=None)
    schema = script.build_command_schema(
        cmd,
        aster_version="17.4.0",
        image_digest="sha256:abc",
        catalogue_hash="sha256:def",
        catalogue_source="/opt/x/code_aster",
        extracted_at="2026-01-01T00:00:00+00:00",
        is_concept_class=_is_concept_class,
        encountered_classes=set(),
    )
    assert schema["result_type"] is None
    assert schema["result_type_dynamic"] is False


def test_build_command_schema_unrecognized_command_class_raises() -> None:
    class Weird(Operator):
        pass

    cmd = _empty_command("X", cls=Weird)
    with pytest.raises(TypeError, match="unrecognized Command subclass"):
        script.build_command_schema(
            cmd,
            aster_version="17.4.0",
            image_digest="sha256:abc",
            catalogue_hash="sha256:def",
            catalogue_source="/opt/x/code_aster",
            extracted_at="2026-01-01T00:00:00+00:00",
            is_concept_class=_is_concept_class,
            encountered_classes=set(),
        )


def test_build_command_schema_unrecognized_docu_raises() -> None:
    cmd = _empty_command("X", docu=123)
    with pytest.raises(TypeError, match="unrecognized docu"):
        script.build_command_schema(
            cmd,
            aster_version="17.4.0",
            image_digest="sha256:abc",
            catalogue_hash="sha256:def",
            catalogue_source="/opt/x/code_aster",
            extracted_at="2026-01-01T00:00:00+00:00",
            is_concept_class=_is_concept_class,
            encountered_classes=set(),
        )


def test_build_command_schema_unrecognized_sd_prod_raises() -> None:
    cmd = _empty_command("X", sd_prod=object())
    with pytest.raises(TypeError, match="unrecognized sd_prod"):
        script.build_command_schema(
            cmd,
            aster_version="17.4.0",
            image_digest="sha256:abc",
            catalogue_hash="sha256:def",
            catalogue_source="/opt/x/code_aster",
            extracted_at="2026-01-01T00:00:00+00:00",
            is_concept_class=_is_concept_class,
            encountered_classes=set(),
        )


# --- docu_anomaly ----------------------------------------------------------------


def test_docu_anomaly_none_is_fine() -> None:
    assert script.docu_anomaly("X", None) is None


def test_docu_anomaly_valid_pattern_is_fine() -> None:
    assert script.docu_anomaly("STAT_NON_LINE", "U4.51.03") is None
    assert script.docu_anomaly("MODI_MODELE_XFEM", "U4.44.12-e") is None


def test_docu_anomaly_suspect_value_flagged() -> None:
    assert script.docu_anomaly("REST_HOMO_LOCAL", "UX.YZ.AB") == {
        "command": "REST_HOMO_LOCAL",
        "kind": "docu_suspect",
        "detail": "UX.YZ.AB",
    }
    assert script.docu_anomaly("TEST_COMPOR", "") == {
        "command": "TEST_COMPOR",
        "kind": "docu_suspect",
        "detail": "",
    }


# --- has_usable_docu (lot 4b, C4) ------------------------------------------------


def test_has_usable_docu_none_is_not_usable() -> None:
    assert script.has_usable_docu(None) is False


def test_has_usable_docu_valid_pattern() -> None:
    assert script.has_usable_docu("U4.51.03") is True
    assert script.has_usable_docu("U4.44.12-e") is True


def test_has_usable_docu_malformed_is_not_usable() -> None:
    assert script.has_usable_docu("UX.YZ.AB") is False
    assert script.has_usable_docu("") is False


# --- compute_variant_id (lot 4b, C1) ---------------------------------------------


def test_compute_variant_id_deterministic() -> None:
    first = script.compute_variant_id(["COMPORTEMENT", "RESI_INTE"], ["b_meca"])
    second = script.compute_variant_id(["COMPORTEMENT", "RESI_INTE"], ["b_meca"])
    assert first == second


def test_compute_variant_id_differs_by_bloc_route() -> None:
    same_path = ["COMPORTEMENT", "RESI_INTE"]
    a = script.compute_variant_id(same_path, ["b_elas"])
    b = script.compute_variant_id(same_path, ["b_vmis"])
    assert a != b


def test_compute_variant_id_differs_by_path() -> None:
    a = script.compute_variant_id(["MODELE"], [])
    b = script.compute_variant_id(["CHAM_MATER"], [])
    assert a != b


# --- extract_all -----------------------------------------------------------------


def test_extract_all_reports_per_command_failures_without_aborting() -> None:
    good = _empty_command("AFFE_CHAR_MECA", sd_prod=None)
    bad = _empty_command("BROKEN", sd_prod=object())

    schemas, summary = script.extract_all(
        {"AFFE_CHAR_MECA": good, "BROKEN": bad},
        aster_version="17.4.0",
        image_digest="sha256:abc",
        catalogue_hash="sha256:def",
        catalogue_source="/opt/x/code_aster",
        extracted_at="2026-01-01T00:00:00+00:00",
        is_concept_class=_is_concept_class,
    )

    assert set(schemas) == {"AFFE_CHAR_MECA"}
    assert summary["total_exposed"] == 2
    assert summary["total_extracted"] == 1
    assert summary["kind_counts"] == {"operator": 1}
    assert summary["commands_without_usable_docu"] == 1  # AFFE_CHAR_MECA, docu=None
    anomaly_commands = {a["command"]: a["kind"] for a in summary["anomalies"]}
    assert anomaly_commands["BROKEN"] == "extraction_error"


def test_extract_all_counts_missing_and_malformed_docu_together() -> None:
    """Regression test (lot 4b, C4).

    The lot 4 summary only listed the 2 malformed `docu` values as
    anomalies, silently treating the 260 commands with no `docu` at all as
    if they were fine. `commands_without_usable_docu` must count both.
    """
    no_docu = _empty_command("NO_DOCU", docu=None)
    bad_docu = _empty_command("BAD_DOCU", docu="UX.YZ.AB")
    good_docu = _empty_command("GOOD_DOCU", docu="U4.51.03")

    _schemas, summary = script.extract_all(
        {"NO_DOCU": no_docu, "BAD_DOCU": bad_docu, "GOOD_DOCU": good_docu},
        aster_version="17.4.0",
        image_digest="sha256:abc",
        catalogue_hash="sha256:def",
        catalogue_source="/opt/x/code_aster",
        extracted_at="2026-01-01T00:00:00+00:00",
        is_concept_class=_is_concept_class,
    )

    assert summary["commands_without_usable_docu"] == 2  # NO_DOCU and BAD_DOCU
    anomaly_commands = {a["command"] for a in summary["anomalies"]}
    assert anomaly_commands == {"BAD_DOCU"}  # only the malformed one is an anomaly


def test_walk_entities_same_path_different_bloc_gets_different_variant_id() -> None:
    """Mirrors the real duplication found on STAT_NON_LINE (lot 4b, C1):
    the same keyword name declared under two sibling `Bloc`."""
    resi_inte_elas = SimpleKeyword(FakeDefinition({"statut": "f", "typ": "R"}, {}))
    resi_inte_vmis = SimpleKeyword(FakeDefinition({"statut": "f", "typ": "R"}, {}))
    bloc_elas = Bloc(
        FakeDefinition({}, {"RESI_INTE": resi_inte_elas}),
        "equal_to(\"RELATION\", 'ELAS')",
    )
    bloc_vmis = Bloc(
        FakeDefinition({}, {"RESI_INTE": resi_inte_vmis}),
        "equal_to(\"RELATION\", 'VMIS_ISOT_LINE')",
    )
    comportement = FactorKeyword(
        FakeDefinition({"statut": "f"}, {"b_elas": bloc_elas, "b_vmis": bloc_vmis})
    )
    definition = FakeDefinition({"nom": "X"}, {"COMPORTEMENT": comportement})
    cmd = Operator("X", definition)

    result = script.walk_entities(cmd, [], [], _is_concept_class, set())

    resi_inte_entries = [
        e for e in result[0]["children"] if e["path"] == ["COMPORTEMENT", "RESI_INTE"]
    ]
    assert len(resi_inte_entries) == 2
    assert resi_inte_entries[0]["variant_id"] != resi_inte_entries[1]["variant_id"]
    assert {tuple(e["condition"]) for e in resi_inte_entries} == {
        ("equal_to(\"RELATION\", 'ELAS')",),
        ("equal_to(\"RELATION\", 'VMIS_ISOT_LINE')",),
    }


def test_main_fails_when_code_aster_not_importable(tmp_path: Path) -> None:
    # The project's own Python never has `code_aster` installed
    # (docs/architecture.md, ADR-002): this exercises the real failure path.
    exit_code = script.main(
        [
            "--image-digest",
            "sha256:abc",
            "--catalogue-hash",
            "sha256:def",
            "--aster-version",
            "17.4.0",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 1
