"""Run `checkCommandSyntax` against a batch of reconstructed command calls.

Run inside the Code_Aster container by its own Python interpreter (see
docs/architecture.md, ADR-002). Standard library only. Reads a JSON request
file (`--requests`) shaped as `{"requests": [{"id": int, "command": str,
"keywords": <json>}, ...]}` and prints one JSON object per line on stdout:
`{"id": ..., "ok": true}` or `{"id": ..., "ok": false, "orig": "KeyError",
"message": "...", "stack": "AFFE/PHENOMENE"}` or, if the command itself does
not exist in the live catalogue, `{"id": ..., "ok": false, "orig":
"UnknownCommand", "message": "..."}`.

This script decides nothing about validity beyond what `checkCommandSyntax`
(the official checker used by the supervisor itself, docs/development-plan.md
lot 10) already decides: no cardinality rule, no `Bloc` condition, no type
grammar is reimplemented here (aster_expert.validation does the same, one
level up — see its module docstring). This script's own responsibility is
narrow: deserialize the JSON-safe keyword tree built by
`aster_expert.validation.reconstruct` back into the Python objects
`checkCommandSyntax` expects (concept placeholders, complex numbers), call
it, and serialize whatever it decides.

Two JSON markers are recognized, anywhere in the keyword tree, and nowhere
else (a plain literal dict from a `.comm` file never uses a dunder key by
Aster's own naming convention — full-uppercase French acronyms):

- ``{"__concept_type__": "<name>"}``: a concept reference whose Aster type
  was established by `aster_expert.validation.concept_types` (M1) from the
  producing command's catalogue `result_type`. Replaced by a bare instance of
  ``code_aster.Cata.Language.DataStructure.<name>`` — a *light* class (no
  `__init__` override, see that module's own docstring): its only role in
  static checking is `type(obj) is` / `obj.getType()`, verified empirically
  (see the lot 10 batch report) against a wrong-typed instance (rejected)
  and a `PythonVariable()` (accepted for any type — the checker's own
  escape hatch for a value it cannot yet resolve, not used here precisely
  because we *can* resolve the type from the catalogue and want the real
  type check to run).
- ``{"__complex__": {"real": ..., "imag": ...}}``: a literal Python
  `complex`, not JSON-native.

A per-request failure (an unrecognized `__concept_type__` name, a command
absent from the live catalogue) is reported for that request alone, in the
same shape as a `checkCommandSyntax` rejection — it never aborts the batch.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def resolve_markers(value: Any, ds_namespace: Any) -> Any:
    """Recursively replace JSON markers with the Python objects they encode.

    `ds_namespace` provides `__concept_type__` names as attributes (the real
    `code_aster.Cata.Language.DataStructure` module in production; a
    lightweight stand-in in tests, matching the pattern already used for
    scripts/introspect_catalogue.py).
    """
    if isinstance(value, dict):
        if "__concept_type__" in value and len(value) == 1:
            type_name = value["__concept_type__"]
            try:
                cls = getattr(ds_namespace, type_name)
            except AttributeError as exc:
                message = f"unknown concept type in DataStructure: {type_name!r}"
                raise KeyError(message) from exc
            return cls()
        if "__complex__" in value and len(value) == 1:
            parts = value["__complex__"]
            return complex(parts["real"], parts["imag"])
        return {k: resolve_markers(v, ds_namespace) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_markers(v, ds_namespace) for v in value]
    return value


def run_requests(
    requests: list[dict[str, Any]],
    *,
    commands_module: Any,
    ds_namespace: Any,
    check_command_syntax: Any,
) -> list[dict[str, Any]]:
    """Pure dispatch loop, injectable for testing without `code_aster`."""
    results: list[dict[str, Any]] = []
    for request in requests:
        request_id = request["id"]
        command_name = request["command"]
        command_obj = getattr(commands_module, command_name, None)
        if command_obj is None:
            results.append(
                {
                    "id": request_id,
                    "ok": False,
                    "orig": "UnknownCommand",
                    "message": f"command not found in live catalogue: {command_name!r}",
                    "stack": None,
                }
            )
            continue
        try:
            keywords = resolve_markers(request["keywords"], ds_namespace)
            if not isinstance(keywords, dict):
                message = "reconstructed keywords did not deserialize to a dict"
                raise TypeError(message)
            check_command_syntax(command_obj, keywords)
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            results.append(
                {
                    "id": request_id,
                    "ok": False,
                    "orig": type(exc).__name__,
                    "message": str(getattr(exc, "msg", None) or exc),
                    "stack": getattr(exc, "_stack", None) or None,
                }
            )
            continue
        results.append({"id": request_id, "ok": True})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, type=str)
    args = parser.parse_args(argv)

    try:
        import code_aster.Cata.Commands as commands_module  # noqa: N813
        from code_aster.Cata.Language import DataStructure as ds_namespace  # noqa: N813
        from code_aster.Cata.SyntaxChecker import checkCommandSyntax
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        print(f"check_command_syntax: cannot import catalogue: {exc}", file=sys.stderr)
        return 1

    with open(args.requests, encoding="utf-8") as fh:  # noqa: PTH123 - stdlib-only script
        payload = json.load(fh)

    results = run_requests(
        payload["requests"],
        commands_module=commands_module,
        ds_namespace=ds_namespace,
        check_command_syntax=checkCommandSyntax,
    )
    print(json.dumps({"results": results}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
