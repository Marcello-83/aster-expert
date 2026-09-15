"""Unit tests for scripts/check_command_syntax.py's pure logic.

This script runs under the Aster Python inside the container in production
(docs/architecture.md, ADR-002) and is not part of the `aster_expert`
package. Its dispatch loop takes `commands_module`, `ds_namespace`, and
`check_command_syntax` as plain arguments specifically so it can be
exercised here, under the project's own Python (which never has
`code_aster` installed), against lightweight stand-ins — same pattern as
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


class FakeMaillage:
    def __init__(self) -> None:
        self.kind = "maillage_sdaster"


def test_resolve_markers_replaces_concept_type() -> None:
    ds = SimpleNamespace(maillage_sdaster=FakeMaillage)
    value = {"MAILLAGE": {"__concept_type__": "maillage_sdaster"}, "FORMAT": "MED"}

    resolved = script.resolve_markers(value, ds)

    assert isinstance(resolved["MAILLAGE"], FakeMaillage)
    assert resolved["FORMAT"] == "MED"


def test_resolve_markers_replaces_complex() -> None:
    value = {"CENTRE": {"__complex__": {"real": 1.0, "imag": -2.0}}}

    resolved = script.resolve_markers(value, SimpleNamespace())

    assert resolved["CENTRE"] == complex(1.0, -2.0)


def test_resolve_markers_recurses_into_lists_and_nested_dicts() -> None:
    ds = SimpleNamespace(modele_sdaster=FakeMaillage)
    value = {
        "EXCIT": [
            {"MODELE": {"__concept_type__": "modele_sdaster"}, "COEF": 1.0},
            {"MODELE": {"__concept_type__": "modele_sdaster"}, "COEF": 2.0},
        ]
    }

    resolved = script.resolve_markers(value, ds)

    assert isinstance(resolved["EXCIT"][0]["MODELE"], FakeMaillage)
    assert resolved["EXCIT"][1]["COEF"] == 2.0


def test_resolve_markers_unknown_concept_type_raises_key_error() -> None:
    try:
        script.resolve_markers(
            {"__concept_type__": "does_not_exist"}, SimpleNamespace()
        )
    except KeyError as exc:
        assert "does_not_exist" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_run_requests_unknown_command() -> None:
    results = script.run_requests(
        [{"id": 0, "command": "STAT_NON_LINEX", "keywords": {}}],
        commands_module=SimpleNamespace(),
        ds_namespace=SimpleNamespace(),
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


def test_run_requests_success() -> None:
    commands_module = SimpleNamespace(AFFE_MODELE=object())
    results = script.run_requests(
        [{"id": 5, "command": "AFFE_MODELE", "keywords": {"MAILLAGE": "m"}}],
        commands_module=commands_module,
        ds_namespace=SimpleNamespace(),
        check_command_syntax=lambda *a, **k: None,
    )
    assert results == [{"id": 5, "ok": True}]


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

    commands_module = SimpleNamespace(AFFE_MODELE=object())
    results = script.run_requests(
        [{"id": 1, "command": "AFFE_MODELE", "keywords": {}}],
        commands_module=commands_module,
        ds_namespace=SimpleNamespace(),
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

    commands_module = SimpleNamespace(STAT_NON_LINE=object())
    results = script.run_requests(
        [{"id": 2, "command": "STAT_NON_LINE", "keywords": {}}],
        commands_module=commands_module,
        ds_namespace=SimpleNamespace(),
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


def test_run_requests_one_bad_request_does_not_abort_the_batch() -> None:
    def fake_check(command: Any, keywords: Any) -> None:
        if command == "boom":
            raise ValueError("bad")

    commands_module = SimpleNamespace(A="a", B="boom")
    results = script.run_requests(
        [
            {"id": 0, "command": "A", "keywords": {}},
            {"id": 1, "command": "B", "keywords": {}},
        ],
        commands_module=commands_module,
        ds_namespace=SimpleNamespace(),
        check_command_syntax=fake_check,
    )
    assert [r["id"] for r in results] == [0, 1]
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
