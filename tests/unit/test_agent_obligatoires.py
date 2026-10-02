"""Paramètres obligatoires des commandes prévues par la fiche (lot 44, étape 2)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from aster_expert.agent.hypotheses import (
    HypothesesSheet,
    PlannedCommand,
    PracticeHypothesisEntry,
)
from aster_expert.agent.model_data import DataValue, ModelData
from aster_expert.agent.obligatoires import (
    ExecutionRules,
    _holds,
    add_missing_parameters,
    default_rules_path,
    load_execution_rules,
    mandatory_keywords,
    missing_parameters,
)
from aster_expert.catalogue.models import CommandSchema

_ROOT = Path(__file__).resolve().parents[2]
_T0 = datetime.fromisoformat("2026-10-02T10:00:00-04:00")


def _simple(
    path: list[str], status: str, cond: list[str], vt: object = "R"
) -> dict[str, object]:
    return {
        "path": path,
        "variant_id": ".".join(path),
        "kind": "simple",
        "status": status,
        "value_type": vt,
        "allowed_values": None,
        "default": None,
        "min_values": None,
        "max_values": None,
        "condition": cond,
    }


def _schema() -> CommandSchema:
    affe_cond = [" equal_to(\"CODIFICATION\", 'EC2')"]
    return CommandSchema.model_validate(
        {
            "command": "CMD",
            "aster_version": "17.4.0",
            "image_digest": "sha256:" + "0" * 64,
            "catalogue_source": "x",
            "catalogue_hash": "h" * 64,
            "kind": "operator",
            "result_type": None,
            "result_type_dynamic": False,
            "docu": None,
            "extracted_at": "2026-01-01T00:00:00Z",
            "keywords": [
                _simple(["RESULTAT"], "required", [], "evol_elas"),
                {
                    **_simple(["CODIFICATION"], "optional", [], "TXM"),
                    "default": "EC2",
                },
                _simple(["UNITE"], "required", [], "TXM"),
                {
                    "path": ["AFFE"],
                    "variant_id": "AFFE",
                    "kind": "factor",
                    "status": "required",
                    "min_occurrences": None,
                    "max_occurrences": None,
                    "condition": affe_cond,
                    "children": [
                        _simple(
                            ["AFFE", "C_INF"],
                            "required",
                            [*affe_cond, " equal_to(\"TYPE_STRUCTURE\", '2D')"],
                        ),
                        _simple(
                            ["AFFE", "C_INF_Y"],
                            "required",
                            [*affe_cond, " equal_to(\"TYPE_STRUCTURE\", '1D')"],
                        ),
                        _simple(["AFFE", "KT"], "optional", affe_cond),
                    ],
                },
            ],
        }
    )


_RULES = ExecutionRules(
    aster_version="17.4.0",
    source_commit="s",
    doc_commit="d",
    rules=(
        {
            "command": "CMD",
            "when": {"CODIFICATION": "EC2", "TYPE_COMB": "ELS_QP"},
            "keywords": ("AFFE.KT",),
            "sources": ("U4.x § Erreurs",),
        },  # type: ignore[arg-type]
    ),
    categories={"CMD": {"default": "mm:ferraillage", "UNITE": "agent:repere"}},
)


def test_catalogue_conditions_are_evaluated() -> None:
    options = {"CODIFICATION": "EC2", "TYPE_STRUCTURE": "2D"}
    assert _holds(" equal_to(\"TYPE_STRUCTURE\", '2D')", options)
    assert not _holds(" equal_to(\"TYPE_STRUCTURE\", '1D')", options)
    assert _holds('(exists("INST"))or(exists("CODIFICATION"))', options)
    assert not _holds('greater_than("RHO_ACIER", 0)', options)
    with pytest.raises(ValueError, match="non interprétée"):
        _holds("unknown_function('X')", options)


def test_mandatory_keywords_follow_options_and_rules() -> None:
    schema = _schema()
    els = mandatory_keywords(
        schema, {"TYPE_STRUCTURE": "2D", "TYPE_COMB": "ELS"}, _RULES
    )
    assert {m.keyword for m in els} == {"UNITE", "AFFE.C_INF"}  # RESULTAT : concept
    qp = mandatory_keywords(
        schema, {"TYPE_STRUCTURE": "1D", "TYPE_COMB": "ELS_QP"}, _RULES
    )
    assert {m.keyword: m.origin for m in qp} == {
        "UNITE": "catalogue",
        "AFFE.C_INF_Y": "catalogue",
        "AFFE.KT": "exécution",
    }


def _sheet(covered: dict[str, str]) -> HypothesesSheet:
    return HypothesesSheet(
        project_name="P",
        structure_description="d",
        created_at=_T0,
        planned_commands=(
            PlannedCommand(
                command="CMD",
                point_label="14",
                options={"TYPE_STRUCTURE": "2D", "TYPE_COMB": "ELS_QP"},
                covered_by=covered,
            ),
        ),
    )


def test_missing_parameters_become_questions_in_their_category() -> None:
    data = ModelData(
        project="P",
        case_reference="r",
        groups={
            "acier": {
                "enrobage": DataValue(
                    status="a_fournir", unit="m", required_by="14", comment="c"
                )
            }
        },
    )
    sheet = _sheet({"AFFE.C_INF": "data:acier.enrobage", "AFFE.KT": "data:x.absent"})
    missing = missing_parameters(sheet, data, {"CMD": _schema()}, _RULES)
    assert {(m.mandatory.keyword, m.category) for m in missing} == {
        ("UNITE", "agent:repere"),
        ("AFFE.KT", "mm:ferraillage"),  # cible absente : non couvert
    }
    augmented = add_missing_parameters(sheet, missing)
    added = [
        e
        for e in augmented.entries[len(sheet.entries) :]
        if isinstance(e, PracticeHypothesisEntry)
    ]
    assert len(added) == 2
    assert all(e.status == "non_tranche" for e in added)
    assert any("à MM (ferraillage)" in (e.notes or "") for e in added)
    assert any("choix de l'agent possible" in (e.notes or "") for e in added)
    # Idempotent : rien n'est ajouté deux fois.
    again = add_missing_parameters(augmented, missing)
    assert len(again.entries) == len(augmented.entries)


def test_planned_command_coverage_is_well_formed() -> None:
    with pytest.raises(ValidationError, match="mal formée"):
        PlannedCommand(command="C", point_label="1", covered_by={"K": "valeur"})


def test_empty_planned_commands_are_not_serialized() -> None:
    sheet = HypothesesSheet(project_name="P", structure_description="d", created_at=_T0)
    assert "planned_commands" not in sheet.model_dump(mode="json")
    assert "planned_commands" in _sheet({}).model_dump(mode="json")


def test_versioned_rules_cite_their_sources() -> None:
    rules = load_execution_rules(default_rules_path(_ROOT))
    assert rules.aster_version == "17.4.0"
    assert all(rule.sources for rule in rules.rules)
    keywords = {k for rule in rules.rules for k in rule.keywords}
    assert {"AFFE.ALPHA_E", "AFFE.KT", "AFFE.EYS", "AFFE.SIGC_ELS_QP"} <= keywords
