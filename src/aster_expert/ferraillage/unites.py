"""Rule on the stress unit of `CALC_FERRAILLAGE` when `FERR_MIN` is asked (lot 45).

Constat CA-041 (executed, lot 39, case `data/examples/lot39_essais/fermin*`):
`FERR_MIN='EC2'` gives the minimum of EN 1992-1-1 9.2.1.1 only with
`UNITE_CONTRAINTE='MPa'` (lengths in mm); with `'Pa'` (lengths in m) the same command
gives 0,0013 b d and a transverse minimum 1 000 times too low, without any alarm.
The generators of the common core never ask `FERR_MIN` (minima are computed outside
Code_Aster, `aster_expert.rebar`); this check keeps that true of what they write, and
refuses any `FERR_MIN` that would come with another unit. `FERR_MIN_FISS` is not
covered: CA-041 establishes no unit dependency for it.
"""

from __future__ import annotations

import ast

from aster_expert.projet.errors import ProjectError

FERR_MIN_UNIT = "MPa"
"""The only stress unit for which `FERR_MIN` is established (CA-041)."""


def ferr_min_unit_violations(text: str) -> list[str]:
    """The `CALC_FERRAILLAGE` calls of a `.comm` that ask `FERR_MIN` without
    `UNITE_CONTRAINTE='MPa'`, one message per call (with its line)."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        message = f"ferraillage : texte illisible, FERR_MIN non contrôlé : {exc}"
        raise ProjectError(message) from exc
    out = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "CALC_FERRAILLAGE"
        ):
            continue
        asked = any(
            isinstance(inner, ast.keyword) and inner.arg == "FERR_MIN"
            for inner in ast.walk(node)
        )
        if not asked:
            continue
        unit = next(
            (
                k.value.value
                for k in node.keywords
                if k.arg == "UNITE_CONTRAINTE" and isinstance(k.value, ast.Constant)
            ),
            None,
        )
        if unit != FERR_MIN_UNIT:
            out.append(
                f"ligne {node.lineno} : CALC_FERRAILLAGE demande FERR_MIN avec "
                f"UNITE_CONTRAINTE={unit!r} ; FERR_MIN n'est juste qu'en "
                f"{FERR_MIN_UNIT!r} (longueurs en mm, constat CA-041)"
            )
    return out


def check_ferr_min_unit(text: str) -> None:
    """Refuse a text where `FERR_MIN` is asked in a unit other than MPa."""
    problems = ferr_min_unit_violations(text)
    if problems:
        message = "ferraillage : " + " ; ".join(problems)
        raise ProjectError(message)


__all__ = ["FERR_MIN_UNIT", "check_ferr_min_unit", "ferr_min_unit_violations"]
