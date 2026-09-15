"""Run `checkCommandSyntax` against an ordered batch of reconstructed calls.

Run inside the Code_Aster container by its own Python interpreter (see
docs/architecture.md, ADR-002). Standard library only. Reads a JSON request
file (`--requests`) shaped as `{"requests": [{"id": int, "command": str,
"assigned_concept": str|null, "keywords": <json>}, ...]}` and prints one JSON
object per line on stdout, one of:

- `{"id": ..., "ok": true, "produced_type": <str|null>}`
- `{"id": ..., "ok": false, "orig": "<ExceptionClassName>", "message": "...",
  "stack": "AFFE/PHENOMENE"}` -- a real rejection by the official checker (or
  by the official `compat_syntax` adaptation that runs before it).
- `{"id": ..., "ok": false, "orig": "UnknownCommand", "message": "...",
  "stack": null}` -- the command name does not exist in the live catalogue.
- `{"id": ..., "ok": false, "orig": "NonStandardCatalogueObject", "message":
  "...", "stack": null}` -- the name resolves to something in
  `code_aster.Cata.Commands` that is not a `Command` instance (e.g.
  `VARIABLE`, `code_aster.Cata.Commands.variable.VariableSupport`:
  docs/development-plan.md, lot 10b, point E) -- never fed to
  `checkCommandSyntax`, which assumes a `Command`.
- `{"id": ..., "ok": false, "orig": "UnresolvedConcept", "message": "...",
  "stack": null}` -- a `__concept_ref__` marker names a concept this batch
  has not (yet, or ever) resolved a placeholder object for.

This script decides nothing about validity beyond what the official
machinery already decides:

- **Type resolution (docs/development-plan.md, lot 10b, point A).** For a
  request whose `assigned_concept` is not null and which passes
  `checkCommandSyntax`, the produced Aster type is read from
  `Command.get_type_sd_prod(**keywords)` -- the exact method
  `Command.call_default` itself calls after `checkCommandSyntax` succeeds
  (`code_aster/Cata/Language/SyntaxObjects.py`). It is *never* computed from
  `sd_prod` directly: `get_type_sd_prod` is what adds default keywords and
  fills the arguments `sd_prod` needs but the user did not provide with
  `None` (`add_none_sdprod`) before calling it, and it dispatches correctly
  between an `Operator` (calls `sd_prod(**ctxt)`) and a `Macro` (calls
  `sd_prod(self, **ctxt)`, the catalog object as `self`) through
  `Command.build_sd_prod`, overridden by `Macro` -- reproducing that
  dispatch by hand would be exactly the reimplementation lot 10b forbids.
  Verified empirically in session (see the lot 10b batch report): calling
  `get_type_sd_prod` standalone, *without* a prior successful
  `checkCommandSyntax`, can silently return a bogus type (`CALC_CHAMP` with
  no `RESULTAT` resolves to Python's own `NoneType` rather than raising) --
  which is why this script never calls it except after `checkCommandSyntax`
  has already succeeded on the very same `keywords`. In that order it cannot
  fail: `SyntaxCheckerVisitor.visitCommand` (`Cata/Language/SyntaxChecker.py`)
  already calls `step.get_type_sd_prod(**userDict)` itself, as part of the
  check, and turns any exception from it into a `CheckerError`
  (`RESULT_TYPE_ERROR` once classified downstream) -- so a `checkCommandSyntax`
  that returns normally has already proven this second call will succeed too.
  A `reuse=` statement needs no special case here: for a reentrant command
  the produced object *is* the reused one (verified empirically: `CALC_CHAMP`
  reused on a `RESULTAT` placeholder resolves to that placeholder's own type
  via `AsType(RESULTAT)`), so the uniform call already returns the right
  answer without this script ever inspecting `reuse` itself.
- **Compatibility adaptation (docs/development-plan.md, lot 10b, point B).**
  Before `checkCommandSyntax`, this script replays the *official*
  pre-check adaptation the supervisor itself runs
  (`ExecuteCommand.compat_syntax_`, `code_aster/Supervis/ExecuteCommand.py`):
  `command.get_compat_syntax()(keywords)`, i.e. the `compat_syntax` function
  attached directly in the command's catalog entry
  (`Cata/Language/SyntaxObjects.py`, `Command.get_compat_syntax`). Verified
  empirically against `MODI_MAILLAGE` (`ORIE_PEAU_3D` -> `ORIE_PEAU`
  renaming) and `MECA_STATIQUE`/`THER_LINEAIRE`/`THER_NON_LINE`/
  `SECH_NON_LINE` (`reuse=` -> `RESULTAT=` injection when the user omits
  `RESULTAT`): both are plain dict mutations with no dependency on a real
  (non-placeholder) object, safe to run against the placeholders this
  project builds. No hand-written translation table is used anywhere in this
  project for this: every catalog command that needs one already carries its
  own `compat_syntax` function, called here by name. The *post*-check
  adaptation (`ExecuteCommand.adapt_syntax`) is a separate hook, defined per
  command in the `code_aster.CodeCommands`/`MacroCommands` *executor*
  modules (not the `Cata` catalog), which import `libaster`/`aster_core` --
  unavailable in this container (docs/architecture.md, ADR-002; confirmed by
  lot 10's own finding that `checkCommandSyntax` itself needs neither). It is
  about execution-time keyword shaping, not syntax or typing, and is out of
  reach and out of scope for level B validation; this is a documented limit,
  not a silent omission.
- **`FORMULE` free keywords (docs/development-plan.md, lot 10b, point E)**
  are stripped *before* this script ever sees them, by
  `aster_expert.validation.reconstruct` (M2) -- not here: the official
  mechanism that does this in production
  (`FormulaDefinition.change_syntax`, `code_aster/CodeCommands/formule.py`)
  lives in the same executor layer as `adapt_syntax` above and needs
  `libaster` too, so it cannot be replayed here either. See that module's
  docstring for the narrow, explicit, verified substitute.

No cardinality rule, no `Bloc` condition, no type grammar is reimplemented
here or anywhere in `aster_expert.validation`.

Markers recognized anywhere in a request's `keywords` tree, and nowhere else
(a plain literal dict from a `.comm` file never uses a dunder key by
Aster's own naming convention -- full-uppercase French acronyms):

- ``{"__concept_ref__": "<name>"}``: a reference to a concept produced by an
  *earlier* request in this same batch (lower `id`, but concretely: earlier
  in the `requests` list -- this script trusts the caller's ordering, see
  `aster_expert.validation.validate`). Resolved by looking up the live
  in-memory table this script builds as it processes requests in order; every
  concept reference in a lot 9 analysis is, by construction, a name assigned
  by some statement in the same file (`aster_expert.parsing.comm_parser`
  only ever produces a `ConceptReferenceValue` for such a name) -- so a
  lookup miss here always means that producing statement was excluded,
  failed, or has not been reached yet in this batch, never a name this
  project invented.
- ``{"__complex__": {"real": ..., "imag": ...}}``: a literal Python
  `complex`, not JSON-native.

A per-request failure (an unresolved concept, a command absent from the live
catalogue, a non-`Command` catalogue object, a `compat_syntax` or
`checkCommandSyntax` rejection) is reported for that request alone and never
aborts the batch -- including for a request whose own `assigned_concept`
therefore never gets a placeholder registered, which is exactly what makes
any *later* request referencing it correctly come back `UnresolvedConcept`
in turn.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


class UnresolvedConceptError(Exception):
    """A `__concept_ref__` marker names a concept with no live placeholder yet."""


# `entier` (`code_aster/Cata/Commands/defi_fichier.py`, `code_aster/Cata/
# Commands/extr_table.py`) and `reel` (`extr_table.py` only) are the only two
# `DataStructure` subclasses, in the whole 17.4.0 catalogue, a command's
# `sd_prod` can return that represent an extracted *value* (an auto-allocated
# logical unit number, a scalar pulled out of a table) rather than a
# structural Aster object. Verified empirically (see the lot 10b batch
# report): a bare instance of either class fails `checkCommandSyntax` on the
# consuming keyword downstream (`Unexpected value`) whenever that keyword's
# `typ` is a `ValueCheckMixing` subclass expecting a real Python value (e.g.
# `UnitType()` for a `UNITE=` keyword, `LISTE_R` on `CREA_TABLE`) --
# `ValueCheckMixing.checkValue` (`Cata/Language/DataStructure.py`) only
# special-cases `None` and `PythonVariable`, never a bare `DataStructure`
# instance. `PythonVariable` is the checker's own, official escape hatch for
# exactly this ("a value not yet resolvable" -- confirmed by that same
# special-casing), so it is used here instead of `result_cls()` for these two
# names specifically -- never a broader rule for every "simple" concept type,
# which would be a guess this project does not make.
_RAW_VALUE_CONCEPT_TYPES = frozenset({"entier", "reel"})


def resolve_markers(value: Any, concept_objects: dict[str, Any]) -> Any:
    """Recursively replace JSON markers with the Python objects they encode.

    `concept_objects` maps a concept name to the placeholder object most
    recently produced for it by this same batch, in processing order.
    """
    if isinstance(value, dict):
        if "__concept_ref__" in value and len(value) == 1:
            name = value["__concept_ref__"]
            if name not in concept_objects:
                message = f"concept {name!r} has no resolved placeholder in this batch"
                raise UnresolvedConceptError(message)
            return concept_objects[name]
        if "__complex__" in value and len(value) == 1:
            parts = value["__complex__"]
            return complex(parts["real"], parts["imag"])
        return {k: resolve_markers(v, concept_objects) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_markers(v, concept_objects) for v in value]
    return value


def run_requests(
    requests: list[dict[str, Any]],
    *,
    commands_module: Any,
    command_base: type,
    check_command_syntax: Any,
    python_variable: type,
) -> list[dict[str, Any]]:
    """Sequential dispatch loop, injectable for testing without `code_aster`.

    Processes `requests` in the given list order and maintains
    `concept_objects` live across the whole batch (see module docstring):
    this is why the caller must send requests in file order, not grouped or
    reordered by any other key.
    """
    results: list[dict[str, Any]] = []
    concept_objects: dict[str, Any] = {}

    for request in requests:
        request_id = request["id"]
        command_name = request["command"]
        assigned_concept = request.get("assigned_concept")

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
        if not isinstance(command_obj, command_base):
            results.append(
                {
                    "id": request_id,
                    "ok": False,
                    "orig": "NonStandardCatalogueObject",
                    "message": (
                        f"catalogue object for {command_name!r} is not a Command "
                        f"instance (type: {type(command_obj).__name__}): not "
                        "compatible with checkCommandSyntax"
                    ),
                    "stack": None,
                }
            )
            continue

        try:
            keywords = resolve_markers(request["keywords"], concept_objects)
            if not isinstance(keywords, dict):
                message = "reconstructed keywords did not deserialize to a dict"
                raise TypeError(message)
        except UnresolvedConceptError as exc:
            results.append(
                {
                    "id": request_id,
                    "ok": False,
                    "orig": "UnresolvedConcept",
                    "message": str(exc),
                    "stack": None,
                }
            )
            continue

        try:
            compat = command_obj.get_compat_syntax()
            compat(keywords)
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            results.append(
                {
                    "id": request_id,
                    "ok": False,
                    "orig": type(exc).__name__,
                    "message": f"compat_syntax: {getattr(exc, 'msg', None) or exc}",
                    "stack": getattr(exc, "_stack", None) or None,
                }
            )
            continue

        try:
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

        produced_type: str | None = None
        if assigned_concept:
            result_cls = command_obj.get_type_sd_prod(**keywords)
            if result_cls is not None:
                if result_cls.__name__ in _RAW_VALUE_CONCEPT_TYPES:
                    concept_objects[assigned_concept] = python_variable()
                else:
                    concept_objects[assigned_concept] = result_cls()
                produced_type = result_cls.__name__
        results.append({"id": request_id, "ok": True, "produced_type": produced_type})

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, type=str)
    args = parser.parse_args(argv)

    try:
        import code_aster.Cata.Commands as commands_module  # noqa: N813
        from code_aster.Cata.Language.DataStructure import PythonVariable
        from code_aster.Cata.Language.SyntaxObjects import Command
        from code_aster.Cata.SyntaxChecker import checkCommandSyntax
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        print(f"check_command_syntax: cannot import catalogue: {exc}", file=sys.stderr)
        return 1

    with open(args.requests, encoding="utf-8") as fh:  # noqa: PTH123 - stdlib-only script
        payload = json.load(fh)

    results = run_requests(
        payload["requests"],
        commands_module=commands_module,
        python_variable=PythonVariable,
        command_base=Command,
        check_command_syntax=checkCommandSyntax,
    )
    print(json.dumps({"results": results}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
