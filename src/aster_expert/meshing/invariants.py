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
    # Kind of each group: a cell group contributes the nodes of its cells, a node
    # group its own nodes (lot 27: an anchor node distinct from every screen node).
    kinds: tuple[Literal["cell", "node"], Literal["cell", "node"]] = ("cell", "cell")
    count: int
    # Points where the shared nodes must lie (each within `tolerance` of a shared node).
    at: tuple[Point, ...] = ()
    tolerance: float = 1e-9


class CoincidentNodesInvariant(_Model):
    tolerance: float


class GroupAreaInvariant(_Model):
    """Developed area of a cell group (sum of the areas of its 2D cells).

    `reference_area` is a value the mesh is compared with -- e.g. the ideal,
    unfaceted area: the invariant then also reports `area - reference_area`, which
    is the analytic effect of the discretisation (lot 27).
    """

    group: str
    area: float
    tolerance: float
    reference_area: float | None = None


class ProjectedWidthInvariant(_Model):
    """Width of a cell group projected on the plane Y = 0, at the level `z`.

    Computed from the areas of the cells: for each cell of the group whose vertical
    extent contains `z`, its area projected on the plane Y = 0 divided by its
    height. `z` must lie inside a row of cells, not on a node level (a node level
    belongs to two rows).
    """

    label: str
    group: str
    z: float
    width: float
    tolerance: float


class SubsetInvariant(_Model):
    """Every cell of `group` is a cell of `of`."""

    group: str
    of: str


class PlaneNodesInvariant(_Model):
    """The node group `group` is exactly the set of nodes with `axis` = `value`."""

    group: str
    axis: Literal["x", "y", "z"]
    value: float
    tolerance: float


class SymmetryInvariant(_Model):
    """For every node of coordinate x, a node exists at -x (same y and z)."""

    tolerance: float


class Invariants(_Model):
    schema_version: Literal[1]
    counts: CountsInvariant | None = None
    bbox: BBox | None = None
    bbox_tolerance: float = 1e-9
    groups: tuple[GroupInvariant, ...] = ()
    group_areas: tuple[GroupAreaInvariant, ...] = ()
    projected_widths: tuple[ProjectedWidthInvariant, ...] = ()
    subsets: tuple[SubsetInvariant, ...] = ()
    plane_nodes: tuple[PlaneNodesInvariant, ...] = ()
    symmetry: SymmetryInvariant | None = None
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


def _group_cells(dump: MedDump, name: str) -> list[tuple[str, int, int]]:
    """(type, level, cell id) of the cells of a group, merged over every level."""
    cells: list[tuple[str, int, int]] = []
    for group in dump.groups:
        if group.name != name or group.level == 1:
            continue
        level = dump.levels[str(group.level)]
        cells.extend((_short_type(level.types[i]), group.level, i) for i in group.ids)
    return cells


def _cell_area(dump: MedDump, level: int, cell_id: int) -> float:
    """Area of a planar polygonal cell (Newell), 0 for cells of dimension 1."""
    nodes = dump.levels[str(level)].connectivity[cell_id]
    if len(nodes) < 3:
        return 0.0
    pts = [dump.coords[n] for n in nodes]
    nx = ny = nz = 0.0
    for a, b in zip(pts, pts[1:] + pts[:1], strict=True):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def _projected_area_on_y(dump: MedDump, level: int, cell_id: int) -> float:
    """Area of a cell projected on the plane Y = 0 (shoelace on x, z)."""
    nodes = dump.levels[str(level)].connectivity[cell_id]
    if len(nodes) < 3:
        return 0.0
    pts = [dump.coords[n] for n in nodes]
    twice = sum(
        a[0] * b[2] - b[0] * a[2] for a, b in zip(pts, pts[1:] + pts[:1], strict=True)
    )
    return abs(twice) / 2.0


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

    if invariants.bbox is not None:
        box = _bbox(dump, set(range(len(dump.coords))))
        ok = box is not None and all(
            abs(a - b) <= invariants.bbox_tolerance
            for a, b in zip(box, invariants.bbox, strict=True)
        )
        add(
            "boîte",
            f"boîte englobante du modèle (tol. {invariants.bbox_tolerance:g})",
            _fmt_point(invariants.bbox),
            _fmt_point(box) if box else "vide",
            ok,
        )

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

    for area in invariants.group_areas:
        cells_of = _group_cells(dump, area.group)
        label = f"aire développée de {area.group} (tol. {area.tolerance:g})"
        if not cells_of:
            add("aire", label, area.area, "groupe absent ou sans maille", False)
            continue
        total = sum(_cell_area(dump, lv, i) for _, lv, i in cells_of)
        add(
            "aire",
            label,
            f"{area.area:.9g}",
            f"{total:.9g}",
            abs(total - area.area) <= area.tolerance,
        )
        if area.reference_area is not None:
            expected_gap = area.area - area.reference_area
            gap = total - area.reference_area
            add(
                "aire",
                f"écart de {area.group} à la référence {area.reference_area:.9g} "
                f"(effet de facettisation, tol. {area.tolerance:g})",
                f"{expected_gap:.9g}",
                f"{gap:.9g}",
                abs(gap - expected_gap) <= area.tolerance,
            )

    for width in invariants.projected_widths:
        cells_of = _group_cells(dump, width.group)
        label = (
            f"largeur projetée sur Y = 0 de {width.group} à z = {width.z:g} "
            f"({width.label})"
        )
        total = 0.0
        for _, lv, i in cells_of:
            zs = [dump.coords[n][2] for n in dump.levels[str(lv)].connectivity[i]]
            low, high = min(zs), max(zs)
            if high - low > 0 and low <= width.z <= high:
                total += _projected_area_on_y(dump, lv, i) / (high - low)
        add(
            "largeur projetée",
            f"{label} (tol. {width.tolerance:g})",
            f"{width.width:.9g}",
            f"{total:.9g}",
            bool(cells_of) and abs(total - width.width) <= width.tolerance,
        )

    for sub in invariants.subsets:
        inner = {(lv, i) for _, lv, i in _group_cells(dump, sub.group)}
        outer = {(lv, i) for _, lv, i in _group_cells(dump, sub.of)}
        outside = inner - outer
        add(
            "inclusion",
            f"mailles de {sub.group} dans {sub.of}",
            f"{len(inner)} mailles incluses",
            f"{len(inner) - len(outside)} sur {len(inner)}",
            bool(inner) and not outside,
        )

    for plane in invariants.plane_nodes:
        axis = "xyz".index(plane.axis)
        in_plane = {
            n
            for n, p in enumerate(dump.coords)
            if abs(p[axis] - plane.value) <= plane.tolerance
        }
        present, _, members = _group_members(dump, plane.group, "node")
        label = (
            f"groupe {plane.group} = nœuds en {plane.axis.upper()} = {plane.value:g} "
            f"(tol. {plane.tolerance:g})"
        )
        add(
            "plan",
            label,
            f"{len(in_plane)} nœuds du plan",
            f"{len(members)} nœuds du groupe, {len(members & in_plane)} dans le plan"
            if present
            else "groupe absent",
            present and members == in_plane,
        )

    if invariants.symmetry is not None:
        tol = invariants.symmetry.tolerance
        keyed: dict[tuple[int, int, int], list[Point]] = {}
        for p in dump.coords:
            keyed.setdefault(
                (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol)), []
            ).append(p)
        unmatched = 0
        example: Point | None = None
        for p in dump.coords:
            mirror = (round(-p[0] / tol), round(p[1] / tol), round(p[2] / tol))
            found = any(
                math.dist((-p[0], p[1], p[2]), q) <= tol
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
                for dz in (-1, 0, 1)
                for q in keyed.get((mirror[0] + dx, mirror[1] + dy, mirror[2] + dz), ())
            )
            if not found:
                unmatched += 1
                example = example or p
        add(
            "symétrie",
            f"nœud en -x pour chaque nœud en x (tol. {tol:g})",
            "0 nœud sans symétrique",
            f"{unmatched} nœud(s) sans symétrique"
            + (f", ex. {_fmt_point(example)}" if example else ""),
            unmatched == 0,
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
        present_a, _, nodes_a = _group_members(dump, first, shared.kinds[0])
        present_b, _, nodes_b = _group_members(dump, second, shared.kinds[1])
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
