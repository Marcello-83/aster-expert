"""Default level-D harness of every project (lot 46, step 6).

Level D was specific to each project. The pipeline now applies, with no declaration
from the project, the promoted controls of the base (`default_harness: true`: CTL-005
equilibrium, CTL-006 symmetry, CTL-012 mesh convergence) and the generic control
CTL-013 (resultant of each load case against the declared load) that the base did not
hold. The four generic controls asked for are therefore:

- global equilibrium: CTL-005, already in the base (not rewritten);
- resultant of each load case against the declared load: CTL-013 (new, here);
- symmetry, if the project declares it: CTL-006, already in the base;
- mesh convergence, if level E is aimed at: CTL-012, already in the base, made generic
  here (it was project code): the project only supplies the error series.

A control is applied unless the project **disables it with a written reason** in
`projet.yaml` (`controls.disabled`); the results note shows the disabled controls and
their reasons. A control that does not apply (no symmetry plane declared, level E not
aimed at) says so; it never passes silently. The harness reads results only: it is
replayed from an equilibrium file (`equilibre.json`) without any execution.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

APPLIED = "RÉUSSI"
FAILED = "ÉCHEC"
NOT_APPLICABLE = "NON APPLICABLE"
DISABLED = "DÉSACTIVÉ"
VERDICTS_THAT_COUNT = (APPLIED, FAILED)

GENERIC_CONTROLS = ("CTL-013",)
"""Generic controls the base does not flag as default (a default control must be
promoted): applied by every project."""
PROMOTED_DEFAULTS = ("CTL-005", "CTL-006", "CTL-012")
"""The promoted controls of the default harness. A test checks that this tuple is the
set of the base's `default_harness` controls."""
DEFAULT_CONTROLS = (*PROMOTED_DEFAULTS, *GENERIC_CONTROLS)


def aims_at_level_e(ctx: ProjectContext) -> bool:
    """Level E is aimed at when the results package declares an E criterion."""
    package = ctx.declaration.results_package
    return package is not None and any(c.level == "E" for c in package.criteria)


def _equilibrium(
    ctx: ProjectContext, result: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    verdicts = [c["verdict"] for c in summary["equilibrium"].values()] + [
        g["verdict"] for g in summary["gravity"].values()
    ]
    if not verdicts:
        return {"verdict": NOT_APPLICABLE, "reason": "aucun cas de charge contrôlé"}
    worst = max(
        (c["worst_relative_gap"] for c in summary["equilibrium"].values()), default=0.0
    )
    return {
        "verdict": APPLIED if all(v == APPLIED for v in verdicts) else FAILED,
        "worst_relative_gap": worst,
        "cases": sorted(summary["equilibrium"]),
    }


def _symmetry(
    ctx: ProjectContext, result: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    controls = ctx.declaration.controls
    if controls is None or not controls.symmetry_planes:
        return {
            "verdict": NOT_APPLICABLE,
            "reason": "aucun plan de symétrie déclaré par le projet",
        }
    symmetry = summary["symmetry"]
    return {
        "verdict": APPLIED
        if symmetry and all(s["verdict"] == APPLIED for s in symmetry.values())
        else FAILED,
        "worst_relative_gap": max(
            (s["worst_relative_gap"] for s in symmetry.values()), default=math.nan
        ),
        "planes": sorted(symmetry),
    }


def _resultant(
    ctx: ProjectContext, result: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    """CTL-013: for each load case, the resultant Code_Aster evaluates equals the
    declared one, component by component, within the project's threshold, referred to
    the largest component of the load (same scale as the equilibrium). Version 2
    (lot 47 bis): a self-equilibrated case is referred to its declared scale."""
    controls = ctx.declaration.controls
    assert controls is not None
    cases: dict[str, float] = {}
    for name, entry in result["cases"].items():
        terms = entry["components"]
        scale = max(abs(t["applied_as_evaluated_n"]) for t in terms.values())
        declared = [t["scale_n"] for t in terms.values() if "scale_n" in t]
        if declared:
            scale = max(declared)
        gap = max(
            abs(t["applied_as_evaluated_n"] - t["applied_specified_n"])
            for t in terms.values()
        )
        cases[name] = gap / scale if scale else math.nan
    if not cases:
        return {"verdict": NOT_APPLICABLE, "reason": "aucun cas de charge contrôlé"}
    passed = all(g <= controls.threshold for g in cases.values())
    return {
        "verdict": APPLIED if passed else FAILED,
        "threshold": controls.threshold,
        "relative_gap_by_case": cases,
        "worst_relative_gap": max(cases.values()),
    }


def convergence_verdict(
    series: dict[str, list[float]], final_threshold: float | None
) -> dict[str, Any]:
    """CTL-012: the error of each quantity decreases strictly along the refinement
    and the finest one is under the threshold written before the execution."""
    if not series or any(len(errors) < 2 for errors in series.values()):
        return {"verdict": FAILED, "reason": "au moins deux maillages par grandeur"}
    decreasing = {
        name: all(b < a for a, b in zip(errors, errors[1:], strict=False))
        for name, errors in series.items()
    }
    finest = {name: errors[-1] for name, errors in series.items()}
    under = (
        {name: value <= final_threshold for name, value in finest.items()}
        if final_threshold is not None
        else {}
    )
    ok = all(decreasing.values()) and all(under.values())
    return {
        "verdict": APPLIED if ok else FAILED,
        "decreasing": decreasing,
        "finest_error": finest,
        "final_threshold": final_threshold,
        "worst_finest_error": max(finest.values()),
    }


def _convergence(
    ctx: ProjectContext, result: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    if not aims_at_level_e(ctx):
        return {"verdict": NOT_APPLICABLE, "reason": "niveau E non visé par le projet"}
    controls = ctx.declaration.controls
    assert controls is not None
    if controls.convergence is None:
        return {
            "verdict": FAILED,
            "reason": (
                "niveau E visé sans série de convergence déclarée "
                "(`controls.convergence` de projet.yaml) : la déclarer, ou "
                "désactiver CTL-012 avec un motif écrit"
            ),
        }
    supplied = ctx.extension(controls.convergence.series)(ctx)
    try:
        series = {str(k): [float(x) for x in v] for k, v in supplied["series"].items()}
        threshold = supplied.get("final_threshold")
    except (KeyError, TypeError, ValueError) as exc:
        message = (
            f"{controls.convergence.series} doit rendre "
            "{'series': {grandeur: [erreur par maillage]}, 'final_threshold': x}"
        )
        raise ProjectError(message) from exc
    out = convergence_verdict(series, None if threshold is None else float(threshold))
    out["source"] = supplied.get("source")
    return out


_IMPLEMENTATIONS: dict[
    str, Callable[[ProjectContext, dict[str, Any], dict[str, Any]], dict[str, Any]]
] = {
    "CTL-005": _equilibrium,
    "CTL-006": _symmetry,
    "CTL-012": _convergence,
    "CTL-013": _resultant,
}


def disabled_controls(ctx: ProjectContext) -> dict[str, str]:
    """Controls the project disables, with their written reasons."""
    controls = ctx.declaration.controls
    if controls is None:
        return {}
    unknown = [d.id for d in controls.disabled if d.id not in DEFAULT_CONTROLS]
    if unknown:
        message = (
            f"controls.disabled : {', '.join(unknown)} n'est pas un contrôle du "
            f"harnais par défaut ({', '.join(DEFAULT_CONTROLS)})"
        )
        raise ProjectError(message)
    return {d.id: d.reason for d in controls.disabled}


def run_harness(
    ctx: ProjectContext, result: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    """Apply the default harness to an equilibrium result and its trunk summary."""
    disabled = disabled_controls(ctx)
    applied: dict[str, Any] = {}
    for control_id in DEFAULT_CONTROLS:
        if control_id in disabled:
            applied[control_id] = {
                "verdict": DISABLED,
                "reason": disabled[control_id],
            }
            continue
        applied[control_id] = _IMPLEMENTATIONS[control_id](ctx, result, summary)
    return {"controls": applied, "disabled": disabled}


__all__ = [
    "APPLIED",
    "DEFAULT_CONTROLS",
    "DISABLED",
    "FAILED",
    "GENERIC_CONTROLS",
    "NOT_APPLICABLE",
    "PROMOTED_DEFAULTS",
    "VERDICTS_THAT_COUNT",
    "aims_at_level_e",
    "convergence_verdict",
    "disabled_controls",
    "run_harness",
]
