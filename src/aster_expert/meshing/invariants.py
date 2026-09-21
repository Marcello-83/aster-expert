"""Invariants a MED mesh must satisfy, and their evaluation on a MED dump (lot 26).

The evaluation is pure: it works on the JSON dump produced by
`scripts/dump_med.py` (read with `medcoupling` inside the Code_Aster image,
never with Salome), so it is tested without Docker on synthetic dumps.
Every invariant is evaluated and reported; the check fails as soon as one is
not held (first failing invariant named in the report).
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from aster_expert.meshing.errors import MeshCheckError

Point = tuple[float, float, float]
BBox = tuple[float, float, float, float, float, float]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CountsInvariant(_Model):
    nodes: int | None = None
    # Cells per MED geometric type, e.g. {"QUAD4": 16, "SEG2": 20}. The whole
    # mapping is the invariant: a type absent from it must be absent from the mesh.
    cells: dict[str, int] | None = None


class GroupInvariant(_Model):
    name: str
    kind: Literal["cell", "node"] = "cell"
    count: int | None = None
    cell_type: str | None = None
    bbox: BBox | None = None
    tolerance: float = 1e-9


class NodeAtInvariant(_Model):
    label: str
    point: Point
    tolerance: float = 1e-9


class SharedNodesInvariant(_Model):
    label: str
    groups: tuple[str, str]
    count: int
    # Points where the shared nodes must lie (each within `tolerance` of a shared node).
    at: tuple[Point, ...] = ()
    tolerance: float = 1e-9


class CoincidentNodesInvariant(_Model):
    tolerance: float


class Invariants(_Model):
    schema_version: Literal[1]
    counts: CountsInvariant | None = None
    groups: tuple[GroupInvariant, ...] = ()
    nodes_at: tuple[NodeAtInvariant, ...] = ()
    shared_nodes: tuple[SharedNodesInvariant, ...] = ()
    no_orphan_nodes: bool = False
    no_coincident_nodes: CoincidentNodesInvariant | None = None


class MedLevel(_Model):
    types: tuple[str, ...]
    connectivity: tuple[tuple[int, ...], ...]


class MedGroup(_Model):
    name: str
    level: int
    ids: tuple[int, ...]


class MedDump(_Model):
    mesh_name: str
    space_dimension: int
    coords: tuple[Point, ...]
    levels: dict[str, MedLevel]
    groups: tuple[MedGroup, ...]


class InvariantResult(_Model):
    kind: str
    label: str
    expected: str
    obtained: str
    ok: bool


def load_invariants(path: Path) -> Invariants:
    if not path.is_file():
        message = f"invariants file not found: {path}"
        raise MeshCheckError(message)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Invariants.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        message = f"invalid invariants file {path}: {exc}"
        raise MeshCheckError(message) from exc


def _short_type(name: str) -> str:
    return name.removeprefix("NORM_")


def _fmt_point(point: Point | BBox) -> str:
    return "(" + ", ".join(f"{v:.9g}" for v in point) + ")"


def _all_cells(dump: MedDump) -> list[tuple[str, tuple[int, ...]]]:
    return [
        (_short_type(t), nodes)
        for level in dump.levels.values()
        for t, nodes in zip(level.types, level.connectivity, strict=True)
    ]


def _group_members(
    dump: MedDump, name: str, kind: str
) -> tuple[bool, list[str], set[int]]:
    """(present, cell types, node ids) of a group, merged over every level."""
    present = False
    types: list[str] = []
    nodes: set[int] = set()
    for group in dump.groups:
        if group.name != name:
            continue
        if kind == "node":
            if group.level == 1:
                present = True
                nodes.update(group.ids)
            continue
        if group.level == 1:
            continue
        present = True
        level = dump.levels[str(group.level)]
        for cell_id in group.ids:
            types.append(_short_type(level.types[cell_id]))
            nodes.update(level.connectivity[cell_id])
    return present, types, nodes


def _bbox(dump: MedDump, nodes: set[int]) -> BBox | None:
    if not nodes:
        return None
    pts = [dump.coords[n] for n in nodes]
    return (
        min(p[0] for p in pts),
        max(p[0] for p in pts),
        min(p[1] for p in pts),
        max(p[1] for p in pts),
        min(p[2] for p in pts),
        max(p[2] for p in pts),
    )


def find_coincident_pairs(
    coords: tuple[Point, ...], tolerance: float
) -> list[tuple[int, int]]:
    """Pairs of distinct nodes closer than `tolerance` (grid hashing, no O(n^2))."""
    grid: dict[tuple[int, int, int], list[int]] = {}
    for index, p in enumerate(coords):
        key = (int(p[0] // tolerance), int(p[1] // tolerance), int(p[2] // tolerance))
        grid.setdefault(key, []).append(index)
    pairs: list[tuple[int, int]] = []
    for index, p in enumerate(coords):
        cx, cy, cz = (
            int(p[0] // tolerance),
            int(p[1] // tolerance),
            int(p[2] // tolerance),
        )
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for other in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        if other > index and math.dist(p, coords[other]) <= tolerance:
                            pairs.append((index, other))
    return pairs


def evaluate(dump: MedDump, invariants: Invariants) -> list[InvariantResult]:
    results: list[InvariantResult] = []

    def add(
        kind: str, label: str, expected: object, obtained: object, ok: bool
    ) -> None:
        results.append(
            InvariantResult(
                kind=kind,
                label=label,
                expected=str(expected),
                obtained=str(obtained),
                ok=ok,
            )
        )

    cells = _all_cells(dump)
    if invariants.counts is not None:
        if invariants.counts.nodes is not None:
            got = len(dump.coords)
            add(
                "comptage",
                "nombre de nœuds",
                invariants.counts.nodes,
                got,
                got == invariants.counts.nodes,
            )
        if invariants.counts.cells is not None:
            by_type = dict(sorted(Counter(t for t, _ in cells).items()))
            expected = dict(sorted(invariants.counts.cells.items()))
            add("comptage", "mailles par type", expected, by_type, by_type == expected)

    for spec in invariants.groups:
        present, types, nodes = _group_members(dump, spec.name, spec.kind)
        prefix = f"groupe {spec.name}"
        add(
            "groupe",
            f"{prefix} : présence",
            "présent",
            "présent" if present else "absent",
            present,
        )
        if not present:
            continue
        cardinality = len(nodes) if spec.kind == "node" else len(types)
        if spec.count is not None:
            add(
                "groupe",
                f"{prefix} : cardinalité",
                spec.count,
                cardinality,
                cardinality == spec.count,
            )
        if spec.cell_type is not None:
            observed = dict(Counter(types))
            add(
                "groupe",
                f"{prefix} : type des mailles",
                spec.cell_type,
                observed if observed else "aucune maille",
                bool(observed) and set(observed) == {spec.cell_type},
            )
        if spec.bbox is not None:
            box = _bbox(dump, nodes)
            ok = box is not None and all(
                abs(a - b) <= spec.tolerance
                for a, b in zip(box, spec.bbox, strict=True)
            )
            add(
                "groupe",
                f"{prefix} : boîte englobante (tol. {spec.tolerance:g})",
                _fmt_point(spec.bbox),
                _fmt_point(box) if box else "vide",
                ok,
            )

    for at in invariants.nodes_at:
        nearest = min((math.dist(at.point, p) for p in dump.coords), default=math.inf)
        add(
            "nœud imposé",
            f"nœud en {at.label} {_fmt_point(at.point)} (tol. {at.tolerance:g})",
            "au moins un nœud",
            f"distance au nœud le plus proche {nearest:.3g}",
            nearest <= at.tolerance,
        )

    for shared in invariants.shared_nodes:
        first, second = shared.groups
        present_a, _, nodes_a = _group_members(dump, first, "cell")
        present_b, _, nodes_b = _group_members(dump, second, "cell")
        label = f"nœuds partagés {first} / {second} ({shared.label})"
        if not (present_a and present_b):
            missing = [n for n, p in ((first, present_a), (second, present_b)) if not p]
            add(
                "interface",
                label,
                shared.count,
                f"groupe absent : {', '.join(missing)}",
                False,
            )
            continue
        common = nodes_a & nodes_b
        add("interface", label, shared.count, len(common), len(common) == shared.count)
        for point in shared.at:
            nearest = min(
                (math.dist(point, dump.coords[n]) for n in common), default=math.inf
            )
            add(
                "interface",
                f"{label} : nœud partagé en {_fmt_point(point)} "
                f"(tol. {shared.tolerance:g})",
                "un nœud partagé",
                f"distance {nearest:.3g}" if common else "aucun nœud partagé",
                nearest <= shared.tolerance,
            )

    if invariants.no_orphan_nodes:
        used = {n for _, nodes in cells for n in nodes}
        orphans = sorted(set(range(len(dump.coords))) - used)
        add(
            "nœuds orphelins",
            "nœuds sans maille",
            0,
            0 if not orphans else f"{len(orphans)} (ex. {orphans[:5]})",
            not orphans,
        )

    if invariants.no_coincident_nodes is not None:
        tol = invariants.no_coincident_nodes.tolerance
        pairs = find_coincident_pairs(dump.coords, tol)
        add(
            "nœuds confondus",
            f"paires de nœuds à moins de {tol:g}",
            0,
            len(pairs) if not pairs else f"{len(pairs)} (ex. {pairs[:3]})",
            not pairs,
        )
    return results


def format_report(title: str, results: list[InvariantResult]) -> str:
    failed = [r for r in results if not r.ok]
    lines = [
        f"Rapport mesh check : {title}",
        f"Invariants : {len(results)}, tenus : {len(results) - len(failed)}, "
        f"en écart : {len(failed)}",
        "",
    ]
    for result in results:
        status = "OK    " if result.ok else "ÉCART "
        lines.append(
            f"[{status}] {result.kind} | {result.label} | attendu : {result.expected} "
            f"| obtenu : {result.obtained}"
        )
    lines.append("")
    if failed:
        first = failed[0]
        lines.append(f"PREMIER INVARIANT NON TENU : {first.kind} | {first.label}")
    else:
        lines.append("Tous les invariants sont tenus.")
    return "\n".join(lines) + "\n"
