"""Serviceability criteria of the engineering summary (lot 49 bis).

Each criterion (`engineering_summary.service_criteria`, declared by MM with its
source) is read on the delivered displacements, combination by combination and
position by position, by superposition of the elementary cases (the arithmetic of
`aster_expert.livrables.torseurs`), with the cases the criterion leaves out
(`exclude_cases`: « hors G et hors TE »):

- `displacement`: modulus of the given components at each node (√(DX² + DY²) at a
  pile head);
- `relative_deflection`: the deflection relative to the supports, on each line of
  nodes (same coordinate along `line_axis`): between two consecutive supports,
  u(s) − [u(a)·(b − s) + u(b)·(s − a)] / (b − a), the chord of the supports taken off;
  on a cantilever, u(s) − u(support).

The limit is `span_m / ratio`; the verdict is given on the unrounded value. A
criterion declared for information (`verdict: false`), or a place outside
`verdict_groups`, is reported without verdict.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Any

import numpy as np

from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.donnees import Deliverables, FloatArray, IntArray, Mesh
from aster_expert.livrables.sections import AXES, LEVEL, group_names
from aster_expert.livrables.torseurs import STATE_LABELS
from aster_expert.projet.declaration import EngineeringSummarySection, ServiceCriterion
from aster_expert.projet.errors import ProjectError


@dataclass
class NodeArrays:
    nodes: IntArray
    cases: dict[str, FloatArray]
    """Case or position -> (nodes, components of the criterion)."""


def _nodes(mesh: Mesh, criterion: ServiceCriterion) -> IntArray:
    sets = [mesh.node_group(g) for g in group_names(mesh, criterion.groups)]
    if criterion.node_group is not None:
        sets.append(mesh.node_group(criterion.node_group))
    found: IntArray = np.unique(np.concatenate(sets))
    if criterion.groups and criterion.node_group is not None:
        found = np.intersect1d(found, mesh.node_group(criterion.node_group))
    return found


def node_arrays(d: Deliverables, criterion: ServiceCriterion) -> NodeArrays:
    nodes = _nodes(d.mesh, criterion)
    with np.load(d.data / f"{criterion.field}.npz") as npz:
        kind = np.array(npz["row_kind"])
        entity = np.array(npz["row_entity"])
        if not (kind == 0).all():
            message = f"critère {criterion.name} : champ {criterion.field} non nodal"
            raise ProjectError(message)
        where = {int(n): i for i, n in enumerate(entity)}
        missing = [int(n) for n in nodes if int(n) not in where]
        if missing:
            message = (
                f"critère {criterion.name} : {len(missing)} nœud(s) sans valeur de "
                f"{criterion.field}"
            )
            raise ProjectError(message)
        rows = np.array([where[int(n)] for n in nodes])
        components = d.container["champs"][criterion.field]["composantes"]
        cols = [components.index(c) for c in criterion.components]
        cases = {
            k.split("/", 1)[1]: np.asarray(npz[k], dtype=np.float64)[rows][:, cols]
            for k in npz.files
            if k.startswith(("cas/", "pos/"))
        }
    return NodeArrays(nodes, cases)


def _combined(
    arrays: NodeArrays,
    combinations: list[tuple[int, GenericCombination]],
    exclude: tuple[str, ...],
) -> Any:
    n, c = len(arrays.nodes), next(iter(arrays.cases.values())).shape[1]
    for ci, comb in combinations:
        base = np.zeros((n, c))
        for case, coefficient in comb.fixed.items():
            if case in exclude or coefficient == 0.0:
                continue
            base = base + coefficient * arrays.cases[case]
        if not comb.mobile_cases:
            yield ci, -1, base
            continue
        for pi, position in enumerate(comb.mobile_cases):
            yield ci, pi, base + comb.mobile_coefficient * arrays.cases[position]


@dataclass(frozen=True)
class Chords:
    """For each measured node: its index, the indices and weights of its two
    supports (the same support twice for a cantilever)."""

    node: IntArray
    a: IntArray
    b: IntArray
    wa: FloatArray
    wb: FloatArray
    span: list[str]


def chords(mesh: Mesh, nodes: IntArray, criterion: ServiceCriterion) -> Chords:
    spans = criterion.spans
    assert spans is not None
    xyz = mesh.coords[nodes]
    along = xyz[:, AXES[spans.axis]]
    line = np.round(xyz[:, AXES[spans.line_axis]] / LEVEL).astype(np.int64)
    out_n: list[int] = []
    out_a: list[int] = []
    out_b: list[int] = []
    out_wa: list[float] = []
    out_wb: list[float] = []
    out_span: list[str] = []
    supports = sorted(spans.supports)
    for key in np.unique(line):
        on = np.where(line == key)[0]

        def at(s: float, on: Any = on) -> int | None:
            hit = on[np.abs(along[on] - s) <= LEVEL]
            return int(hit[0]) if hit.size else None

        for s0, s1 in zip(supports[:-1], supports[1:], strict=True):
            a, b = at(s0), at(s1)
            if a is None or b is None:
                continue
            inner = on[(along[on] > s0 + LEVEL) & (along[on] < s1 - LEVEL)]
            for k in inner:
                s = float(along[k])
                out_n.append(int(k))
                out_a.append(a)
                out_b.append(b)
                out_wa.append((s1 - s) / (s1 - s0))
                out_wb.append((s - s0) / (s1 - s0))
                out_span.append(f"{spans.axis} {s0:g} → {s1:g}")
        for support, end in spans.cantilevers:
            a = at(support)
            if a is None:
                continue
            low, high = min(support, end), max(support, end)
            inner = on[(along[on] >= low - LEVEL) & (along[on] <= high + LEVEL)]
            for k in inner:
                if int(k) == a:
                    continue
                out_n.append(int(k))
                out_a.append(a)
                out_b.append(a)
                out_wa.append(1.0)
                out_wb.append(0.0)
                out_span.append(f"console {spans.axis} {support:g} → {end:g}")
    if not out_n:
        message = f"critère {criterion.name} : aucune portée trouvée sur le maillage"
        raise ProjectError(message)
    return Chords(
        np.array(out_n),
        np.array(out_a),
        np.array(out_b),
        np.array(out_wa),
        np.array(out_wb),
        out_span,
    )


def _members(mesh: Mesh, nodes: IntArray, patterns: tuple[str, ...]) -> list[str]:
    names = [""] * len(nodes)
    if not patterns:
        return names
    known = [k.split("_", 2)[2] for k in mesh.arrays if k.startswith("gma_")]
    for group in known:
        if not any(fnmatch.fnmatchcase(group, p) for p in patterns):
            continue
        inside = np.isin(nodes, mesh.node_group(group))
        for i in np.where(inside)[0]:
            names[int(i)] = names[int(i)] or group
    return names


def evaluate_criterion(
    d: Deliverables,
    combinations: list[GenericCombination],
    summary: EngineeringSummarySection,
    criterion: ServiceCriterion,
) -> dict[str, Any]:
    from aster_expert.livrables.torseurs import combinations_of_state  # noqa: PLC0415

    combos = combinations_of_state(combinations, summary, criterion.limit_state)
    arrays = node_arrays(d, criterion)
    mesh = d.mesh
    if criterion.kind == "relative_deflection":
        ch = chords(mesh, arrays.nodes, criterion)
        measured = ch.node
    else:
        ch = None
        measured = np.arange(len(arrays.nodes))
    best = np.full(len(measured), -np.inf)
    best_ci = np.full(len(measured), -1)
    best_pi = np.full(len(measured), -1)
    best_signed = np.zeros(len(measured))
    count = 0
    for ci, pi, values in _combined(arrays, combos, criterion.exclude_cases):
        count += 1
        if ch is None:
            signed = np.linalg.norm(values, axis=1)
        else:
            u = values[:, 0] if values.shape[1] == 1 else np.linalg.norm(values, axis=1)
            signed = u[ch.node] - ch.wa * u[ch.a] - ch.wb * u[ch.b]
        metric = np.abs(signed)
        higher = metric > best
        best = np.where(higher, metric, best)
        best_signed = np.where(higher, signed, best_signed)
        best_ci[higher] = ci
        best_pi[higher] = pi
    limit = criterion.span_m / criterion.ratio
    members = _members(mesh, arrays.nodes[measured], criterion.verdict_groups)
    in_scope = np.array(
        [bool(m) for m in members]
        if criterion.verdict_groups
        else [True] * len(members)
    )

    def describe(k: int) -> dict[str, Any]:
        comb = combinations[int(best_ci[k])]
        pi = int(best_pi[k])
        node = int(arrays.nodes[measured[k]])
        return {
            "valeur_m": float(best[k]),
            "valeur_signee_m": float(best_signed[k]),
            "noeud_med": node + 1,
            "coordonnees_m": [float(v) for v in mesh.coords[node]],
            "groupe": members[k] or None,
            "portee": ch.span[k] if ch is not None else None,
            "combinaison": comb.name,
            "position_mobile": comb.mobile_cases[pi] if pi >= 0 else None,
        }

    out: dict[str, Any] = {
        "critere": criterion.name,
        "libelle": criterion.label,
        "nature": criterion.kind,
        "composantes": list(criterion.components),
        "etat_limite": criterion.limit_state,
        "etat_limite_libelle": STATE_LABELS[criterion.limit_state],
        "cas_exclus": list(criterion.exclude_cases),
        "portee_m": criterion.span_m,
        "rapport": criterion.ratio,
        "limite_m": limit,
        "evaluations": count,
        "points_mesures": int(len(measured)),
        "source": criterion.source,
    }
    scope = np.where(in_scope)[0]
    if scope.size:
        k = int(scope[int(np.argmax(best[scope]))])
        out["gouvernant"] = describe(k)
        out["taux"] = float(best[k]) / limit
        out["verdict"] = (
            ("RÉUSSI" if best[k] <= limit else "ÉCHEC")
            if criterion.verdict
            else "INFORMATION"
        )
    others = np.where(~in_scope)[0]
    if others.size:
        k = int(others[int(np.argmax(best[others]))])
        out["hors_verdict"] = {
            **describe(k),
            "taux": float(best[k]) / limit,
            "note": criterion.note_others,
        }
    return out


def evaluate_all(
    d: Deliverables,
    combinations: list[GenericCombination],
    summary: EngineeringSummarySection,
) -> list[dict[str, Any]]:
    return [
        evaluate_criterion(d, combinations, summary, c)
        for c in summary.service_criteria
    ]


__all__ = ["chords", "evaluate_all", "evaluate_criterion", "node_arrays"]
