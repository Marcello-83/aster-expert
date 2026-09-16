"""Unit tests for scripts/check_command_syntax.py's pure logic.

This script runs under the Aster Python inside the container in production
(docs/architecture.md, ADR-002) and is not part of the `aster_expert`
package. Its dispatch loop takes `commands_module`, `command_base`, and
`check_command_syntax` as plain arguments specifically so it can be
exercised here, under the project's own Python (which never has
`code_aster` installed), against lightweight stand-ins -- same pattern as
tests/unit/test_introspect_catalogue_script.py.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "check_command_syntax.py"
)


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_command_syntax_script", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


script = _load_script()


class FakeCommand:
    """Stands in for `code_aster.Cata.Language.SyntaxObjects.Command`.

    `definition["sd_prod"]` mirrors the real attribute
    `_is_static_result_type` reads (`code_aster/Cata/Language/
    SyntaxObjects.py`): a `type` for a static command (registered
    immediately, before any check — lot 10c, point P1), any non-`type`
    callable for a dynamic one (registered only after a successful check,
    as in lot 10b). `dynamic=True` with no `produced_type` (the default)
    matches a command with no result at all (`sd_prod is None` in reality)
    treated as dynamic, since there is nothing to register early either way.
    """

    def __init__(
        self, name: str, *, produced_type: type | None = None, dynamic: bool = True
    ) -> None:
        self.name = name
        self._produced_type = produced_type
        sd_prod: Any = (
            (lambda **kw: produced_type)
            if dynamic or produced_type is None
            else produced_type
        )
        self.definition = {"sd_prod": sd_prod}

    def get_compat_syntax(self) -> Any:
        return lambda keywords: None

    def get_type_sd_prod(self, **keywords: Any) -> type | None:
        return self._produced_type


class FakeMaillage:
    pass


class FakePythonVariable:
    pass


def test_resolve_markers_replaces_concept_ref() -> None:
    placeholder = FakeMaillage()
    value = {"MAILLAGE": {"__concept_ref__": "MAIL"}, "FORMAT": "MED"}

    resolved = script.resolve_markers(value, {"MAIL": placeholder})

    assert resolved["MAILLAGE"] is placeholder
    assert resolved["FORMAT"] == "MED"


def test_resolve_markers_replaces_complex() -> None:
    value = {"CENTRE": {"__complex__": {"real": 1.0, "imag": -2.0}}}

    resolved = script.resolve_markers(value, {})

    assert resolved["CENTRE"] == complex(1.0, -2.0)


def test_resolve_markers_recurses_into_lists_and_nested_dicts() -> None:
    placeholder = FakeMaillage()
    value = {
        "EXCIT": [
            {"MODELE": {"__concept_ref__": "MO"}, "COEF": 1.0},
            {"MODELE": {"__concept_ref__": "MO"}, "COEF": 2.0},
        ]
    }

    resolved = script.resolve_markers(value, {"MO": placeholder})

    assert resolved["EXCIT"][0]["MODELE"] is placeholder
    assert resolved["EXCIT"][1]["COEF"] == 2.0


def test_resolve_markers_unresolved_concept_raises() -> None:
    try:
        script.resolve_markers({"__concept_ref__": "MISSING"}, {})
    except script.UnresolvedConceptError as exc:
        assert "MISSING" in str(exc)
    else:
        raise AssertionError("expected UnresolvedConceptError")


def test_run_requests_unknown_command() -> None:
    results = script.run_requests(
        [
            {
                "id": 0,
                "command": "STAT_NON_LINEX",
                "assigned_concept": None,
                "keywords": {},
            }
        ],
        commands_module=SimpleNamespace(),
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results == [
        {
            "id": 0,
            "ok": False,
            "orig": "UnknownCommand",
            "message": "command not found in live catalogue: 'STAT_NON_LINEX'",
            "stack": None,
        }
    ]


def test_run_requests_non_standard_catalogue_object() -> None:
    commands_module = SimpleNamespace(VARIABLE=object())
    results = script.run_requests(
        [{"id": 0, "command": "VARIABLE", "assigned_concept": None, "keywords": {}}],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "NonStandardCatalogueObject"
    assert "VARIABLE" in results[0]["message"]


def test_run_requests_success_without_produced_type() -> None:
    commands_module = SimpleNamespace(AFFE_MODELE=FakeCommand("AFFE_MODELE"))
    results = script.run_requests(
        [
            {
                "id": 5,
                "command": "AFFE_MODELE",
                "assigned_concept": None,
                "keywords": {"MAILLAGE": "m"},
            }
        ],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results == [{"id": 5, "ok": True, "produced_type": None}]


def test_run_requests_success_resolves_and_registers_produced_type() -> None:
    commands_module = SimpleNamespace(
        LIRE_MAILLAGE=FakeCommand("LIRE_MAILLAGE", produced_type=FakeMaillage),
        AFFE_MODELE=FakeCommand("AFFE_MODELE"),
    )
    requests = [
        {
            "id": 0,
            "command": "LIRE_MAILLAGE",
            "assigned_concept": "MAIL",
            "keywords": {},
        },
        {
            "id": 1,
            "command": "AFFE_MODELE",
            "assigned_concept": "MO",
            "keywords": {"MAILLAGE": {"__concept_ref__": "MAIL"}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0] == {"id": 0, "ok": True, "produced_type": "FakeMaillage"}
    assert results[1] == {"id": 1, "ok": True, "produced_type": None}


def test_run_requests_entier_and_reel_are_registered_as_python_variable() -> None:
    # `entier`/`reel` (docs/development-plan.md, lot 10b, point A) represent
    # an extracted value, not a structural object: a bare instance of either
    # fails checkCommandSyntax downstream on a raw-value keyword, so this
    # script registers a `PythonVariable` placeholder for them instead.
    class entier:  # noqa: N801 - must match the real DataStructure class name
        pass

    class reel:  # noqa: N801 - must match the real DataStructure class name
        pass

    commands_module = SimpleNamespace(
        DEFI_FICHIER=FakeCommand("DEFI_FICHIER", produced_type=entier),
        EXTR_TABLE=FakeCommand("EXTR_TABLE", produced_type=reel),
        IMPR_RESU=FakeCommand("IMPR_RESU"),
    )
    requests = [
        {
            "id": 0,
            "command": "DEFI_FICHIER",
            "assigned_concept": "UNITE",
            "keywords": {},
        },
        {"id": 1, "command": "EXTR_TABLE", "assigned_concept": "RVAL", "keywords": {}},
        {
            "id": 2,
            "command": "IMPR_RESU",
            "assigned_concept": None,
            "keywords": {"UNITE": {"__concept_ref__": "UNITE"}},
        },
    ]
    captured: dict[str, Any] = {}

    def fake_check(command: Any, keywords: Any) -> None:
        if command.name == "IMPR_RESU":
            captured["unite_value"] = keywords["UNITE"]

    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=fake_check,
    )
    assert results[0]["produced_type"] == "entier"
    assert results[1]["produced_type"] == "reel"
    assert all(r["ok"] for r in results)
    assert isinstance(captured["unite_value"], FakePythonVariable)


def test_run_requests_unresolved_concept_does_not_abort_batch() -> None:
    commands_module = SimpleNamespace(AFFE_MODELE=FakeCommand("AFFE_MODELE"))
    requests = [
        {
            "id": 0,
            "command": "AFFE_MODELE",
            "assigned_concept": None,
            "keywords": {"MAILLAGE": {"__concept_ref__": "NEVER_PRODUCED"}},
        },
        {"id": 1, "command": "AFFE_MODELE", "assigned_concept": None, "keywords": {}},
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "UnresolvedConcept"
    assert results[1]["ok"] is True


def test_run_requests_static_placeholder_registered_even_when_own_check_fails() -> None:
    # Two-branch placeholder rule, static side (docs/development-plan.md,
    # lot 10c, point P1): DEFI_LIST_REEL's own checkCommandSyntax fails here,
    # yet its placeholder is still available to a later consumer -- the
    # produced type is a catalogue fact, independent of this statement's own
    # verdict.
    def fake_check(command: Any, keywords: Any) -> None:
        if command.name == "DEFI_LIST_REEL":
            raise ValueError("bad literal keyword")

    commands_module = SimpleNamespace(
        DEFI_LIST_REEL=FakeCommand(
            "DEFI_LIST_REEL", produced_type=FakeMaillage, dynamic=False
        ),
        DEFI_LIST_INST=FakeCommand("DEFI_LIST_INST", dynamic=False),
    )
    requests = [
        {
            "id": 0,
            "command": "DEFI_LIST_REEL",
            "assigned_concept": "LISTR",
            "keywords": {"DEBUT": 0.0},
        },
        {
            "id": 1,
            "command": "DEFI_LIST_INST",
            "assigned_concept": "LIS",
            "keywords": {"DEFI_LIST": {"LIST_INST": {"__concept_ref__": "LISTR"}}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=fake_check,
    )
    assert results[0]["ok"] is False
    assert results[1]["ok"] is True


def test_run_requests_static_self_reference_never_resolves_to_its_own_placeholder() -> (
    None
):
    # Regression (docs/development-plan.md, lot 10c, point P1, discovered on
    # a real corpus file: astest/zzzz169c.comm has `line_1 = POST_RELEVE_T(
    # ACTION=_F(..., RESULTAT=line_1, ...))`, self-referencing a `line_1`
    # never otherwise produced by a tracked statement -- registering the
    # static placeholder *before* resolving this same request's own
    # keywords made RESULTAT wrongly resolve to this statement's own
    # about-to-be-produced placeholder instead of staying honestly
    # UnresolvedConcept. The fix: compute the placeholder early (a pure
    # catalogue fact, self-reference-proof) but only *commit* it into
    # concept_objects after resolving this same request's own keywords
    # (still before compat_syntax/checkCommandSyntax) -- see also the next
    # test, which guards against a naive "register only after resolution
    # succeeds" fix instead, which caused a sharp regression of its own.
    commands_module = SimpleNamespace(
        POST_RELEVE_T=FakeCommand(
            "POST_RELEVE_T", produced_type=FakeMaillage, dynamic=False
        ),
    )
    requests = [
        {
            "id": 0,
            "command": "POST_RELEVE_T",
            "assigned_concept": "line_1",
            "keywords": {"ACTION": {"RESULTAT": {"__concept_ref__": "line_1"}}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "UnresolvedConcept"
    assert "line_1" in results[0]["message"]


def test_run_requests_static_placeholder_survives_unrelated_unresolved_ref() -> None:
    # Regression of the self-reference fix itself (docs/development-plan.md,
    # lot 10c, point R5): a naive fix that only committed the static
    # placeholder *after* this same request's own resolve_markers succeeded
    # would also wrongly discard a statement's own valid, self-reference-free
    # static placeholder whenever ANY OTHER keyword of the same statement
    # referenced a still-unresolved concept -- confirmed by a sharp coverage
    # regression on a real user file (82.8% -> 26.3%). AFFE_CARA_ELEM (CARA)
    # here fails to resolve one of its own OTHER keywords (a genuinely
    # unresolved DISCRET.VALE reference), yet CARA must still be registered
    # for MECA_STATIQUE to use afterwards: it is a pure catalogue fact of
    # AFFE_CARA_ELEM the command, unrelated to any of its own keywords.
    commands_module = SimpleNamespace(
        AFFE_CARA_ELEM=FakeCommand(
            "AFFE_CARA_ELEM", produced_type=FakeMaillage, dynamic=False
        ),
        MECA_STATIQUE=FakeCommand("MECA_STATIQUE"),
    )
    requests = [
        {
            "id": 0,
            "command": "AFFE_CARA_ELEM",
            "assigned_concept": "CARA",
            "keywords": {"DISCRET": {"VALE": {"__concept_ref__": "NEVER_PRODUCED"}}},
        },
        {
            "id": 1,
            "command": "MECA_STATIQUE",
            "assigned_concept": None,
            "keywords": {"CARA_ELEM": {"__concept_ref__": "CARA"}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "UnresolvedConcept"
    assert results[1]["ok"] is True


def test_run_requests_type_probe_registers_static_placeholder_without_verdict() -> None:
    # An excluded statement (never sent as "check") still contributes a
    # static placeholder via a "type_probe" request -- and never appears in
    # the results list itself, since it was never confronted with the
    # checker (docs/development-plan.md, lot 10c, point P1).
    commands_module = SimpleNamespace(
        DEFI_LIST_REEL=FakeCommand(
            "DEFI_LIST_REEL", produced_type=FakeMaillage, dynamic=False
        ),
        DEFI_LIST_INST=FakeCommand("DEFI_LIST_INST", dynamic=False),
    )
    requests = [
        {
            "id": 0,
            "command": "DEFI_LIST_REEL",
            "assigned_concept": "LISTR",
            "mode": "type_probe",
        },
        {
            "id": 1,
            "command": "DEFI_LIST_INST",
            "assigned_concept": "LIS",
            "keywords": {"DEFI_LIST": {"LIST_INST": {"__concept_ref__": "LISTR"}}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert [r["id"] for r in results] == [1]
    assert results[0]["ok"] is True


def test_run_requests_type_probe_dynamic_command_registers_nothing() -> None:
    # A dynamic command's type genuinely depends on keywords a type_probe
    # never carries: nothing is registered, so a consumer still comes back
    # UnresolvedConcept, exactly as an excluded dynamic producer did before
    # lot 10c.
    commands_module = SimpleNamespace(
        CALC_CHAMP=FakeCommand("CALC_CHAMP", produced_type=FakeMaillage, dynamic=True),
        AFFE_MODELE=FakeCommand("AFFE_MODELE"),
    )
    requests = [
        {
            "id": 0,
            "command": "CALC_CHAMP",
            "assigned_concept": "RESU",
            "mode": "type_probe",
        },
        {
            "id": 1,
            "command": "AFFE_MODELE",
            "assigned_concept": None,
            "keywords": {"MAILLAGE": {"__concept_ref__": "RESU"}},
        },
    ]
    results = script.run_requests(
        requests,
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert [r["id"] for r in results] == [1]
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "UnresolvedConcept"


class _FakeCheckerError(Exception):
    def __init__(self, msg: str, stack: str) -> None:
        super().__init__(msg)
        self.msg = msg
        self._stack = stack


def test_run_requests_reports_checker_error_shape() -> None:
    def fake_check(command: Any, keywords: Any) -> None:
        raise _FakeCheckerError(
            "For keyword AFFE/PHENOMENE: Unexpected value", "AFFE/PHENOMENE"
        )

    commands_module = SimpleNamespace(AFFE_MODELE=FakeCommand("AFFE_MODELE"))
    results = script.run_requests(
        [{"id": 1, "command": "AFFE_MODELE", "assigned_concept": None, "keywords": {}}],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=fake_check,
    )
    assert results == [
        {
            "id": 1,
            "ok": False,
            "orig": "_FakeCheckerError",
            "message": "For keyword AFFE/PHENOMENE: Unexpected value",
            "stack": "AFFE/PHENOMENE",
        }
    ]


def test_run_requests_reports_bare_key_error_without_stack() -> None:
    def fake_check(command: Any, keywords: Any) -> None:
        raise KeyError("Keyword CHAM_MATER is mandatory")

    commands_module = SimpleNamespace(STAT_NON_LINE=FakeCommand("STAT_NON_LINE"))
    results = script.run_requests(
        [
            {
                "id": 2,
                "command": "STAT_NON_LINE",
                "assigned_concept": None,
                "keywords": {},
            }
        ],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=fake_check,
    )
    assert results == [
        {
            "id": 2,
            "ok": False,
            "orig": "KeyError",
            "message": "'Keyword CHAM_MATER is mandatory'",
            "stack": None,
        }
    ]


def test_run_requests_compat_syntax_rejection_is_reported() -> None:
    class BadCompat(FakeCommand):
        def get_compat_syntax(self) -> Any:
            def _raise(keywords: Any) -> None:
                raise ValueError("bad compat")

            return _raise

    commands_module = SimpleNamespace(AFFE_CHAR_MECA=BadCompat("AFFE_CHAR_MECA"))
    results = script.run_requests(
        [
            {
                "id": 3,
                "command": "AFFE_CHAR_MECA",
                "assigned_concept": None,
                "keywords": {},
            }
        ],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=lambda *a, **k: None,
    )
    assert results[0]["ok"] is False
    assert results[0]["orig"] == "ValueError"
    assert "compat_syntax" in results[0]["message"]


def test_run_requests_one_bad_request_does_not_abort_the_batch() -> None:
    def fake_check(command: Any, keywords: Any) -> None:
        if command.name == "B":
            raise ValueError("bad")

    commands_module = SimpleNamespace(A=FakeCommand("A"), B=FakeCommand("B"))
    results = script.run_requests(
        [
            {"id": 0, "command": "A", "assigned_concept": None, "keywords": {}},
            {"id": 1, "command": "B", "assigned_concept": None, "keywords": {}},
        ],
        commands_module=commands_module,
        command_base=FakeCommand,
        python_variable=FakePythonVariable,
        check_command_syntax=fake_check,
    )
    assert [r["id"] for r in results] == [0, 1]
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
