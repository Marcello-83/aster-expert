"""Rows of a family of members and of its design sections (lot 49 bis).

A family (`engineering_summary.families` of `projet.yaml`) is a set of rows of one
deliverable field (`aster_expert.livrables.donnees`): the element ends of its beams
(`ELNO`), the nodes of its shells (`NOEU`), its springs, its supports. A design section
is a subset of those rows, chosen by the explicit rule the project declares
(`SectionRule`: node group, cell groups, coordinate box, distance to the nodes of a
group, nearest mesh station). Nothing here knows a structure: every name and every
coordinate comes from the declaration.

The rows of a shell that cannot carry a design value are flagged, never dropped in
silence: inside an exclusion disc (PAT-013, declared in `deliverables`), or at a node
shared with a beam (CA-058: the shell and the beam share the force there, and the
shell's value alone has no physical meaning).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.livrables.donnees import (
    Deliverables,
    FieldInfo,
    FloatArray,
    IntArray,
    Mesh,
)
from aster_expert.projet.declaration import (
    DeliverablesSection,
    DesignSection,
    MemberFamily,
    SectionRule,
)
from aster_expert.projet.errors import ProjectError

LEVEL = 1.0e-3
"""Tolerance on coordinates (1 mm, the grid of `config/arrondis.yaml`)."""
AXES = {"X": 0, "Y": 1, "Z": 2}
M_RES = "M_RES"
V_RES = "V_RES"
"""Resultant moment √(MFY² + MFZ²) and shear √(VY² + VZ²) of a circular beam."""


def group_names(mesh: Mesh, patterns: tuple[str, ...] | list[str]) -> list[str]:
    """Cell or node groups of the mesh matching `patterns` (`RESS_K*`), in order."""
    known: list[str] = []
    for key in mesh.arrays:
        if key.startswith("gma_"):
            known.append(key.split("_", 2)[2])
        elif key.startswith("gno_"):
            known.append(key[len("gno_") :])
    out: list[str] = []
    for pattern in patterns:
        found = [g for g in known if fnmatch.fnmatchcase(g, pattern)]
        if not found:
            message = f"groupe {pattern} absent du maillage des livrables"
            raise ProjectError(message)
        out += [g for g in found if g not in out]
    return out


def _rows_of_groups(
    mesh: Mesh,
    kind: IntArray,
    level: IntArray,
    entity: IntArray,
    node: IntArray,
    groups: list[str],
) -> Any:
    keep = np.zeros(len(kind), dtype=bool)
    for group in groups:
        cells = mesh.cell_group(group)
        if cells is not None and (kind > 0).any():
            lv, ids = cells
            keep |= (kind > 0) & (level == lv) & np.isin(entity, ids)
            # A node-carried element (a spring POI1) also belongs by its node.
            keep |= (kind == 0) & np.isin(node, mesh.node_group(group))
        else:
            keep |= np.isin(node, mesh.node_group(group))
    return keep


@dataclass
class FamilyRows:
    """The rows of one family, with their place and the arrays of every case."""

    family: MemberFamily
    info: FieldInfo
    index: IntArray
    """Rows of the field arrays."""
    node: IntArray
    xyz: FloatArray
    kind: IntArray
    element: IntArray
    local: IntArray
    level: IntArray
    member: list[str]
    columns: tuple[str, ...]
    """Components of the field, then the derived resultants."""
    cases: dict[str, FloatArray] = field(default_factory=dict)
    """Elementary case or moving position -> (rows, components of the field)."""

    @property
    def raw(self) -> tuple[str, ...]:
        return self.info.components

    def extend(self, values: FloatArray) -> FloatArray:
        """The field components and, for a circular beam, the resultants."""
        if not self.family.circular:
            return values
        comps = self.raw
        mfy, mfz = values[:, comps.index("MFY")], values[:, comps.index("MFZ")]
        vy, vz = values[:, comps.index("VY")], values[:, comps.index("VZ")]
        return np.column_stack([values, np.hypot(mfy, mfz), np.hypot(vy, vz)])

    def column(self, name: str) -> int:
        return self.columns.index(name)

    def place(self, row: int) -> dict[str, Any]:
        """Member, element, end, node and coordinates of a row (1-based MED numbers)."""
        x, y, z = (float(v) for v in self.xyz[row])
        return {
            "groupe": self.member[row] or None,
            "maille_med": int(self.element[row]) + 1 if self.kind[row] > 0 else None,
            "extremite": int(self.local[row]) + 1 if self.kind[row] == 1 else None,
            "noeud_med": int(self.node[row]) + 1,
            "coordonnees_m": [x, y, z],
        }


def load_family(d: Deliverables, info: FieldInfo, family: MemberFamily) -> FamilyRows:
    """The rows of `family` in the field `info`, with the arrays of the elementary
    cases and of the moving positions restricted to them."""
    mesh = d.mesh
    path: Path = d.data / f"{info.key}.npz"
    with np.load(path) as npz:
        kind = np.array(npz["row_kind"])
        entity = np.array(npz["row_entity"])
        local = np.array(npz["row_local"])
        level = np.array(npz["row_level"])
        nodes = np.where(kind == 0, entity, -1)
        for lv in np.unique(level[kind > 0]):
            rows = (kind > 0) & (level == lv)
            nodes[rows] = mesh.arrays[f"conn_{int(lv)}"][entity[rows], local[rows]]
        groups = group_names(mesh, family.groups)
        keep = _rows_of_groups(mesh, kind, level, entity, nodes, groups)
        index = np.where(keep)[0]
        if index.size == 0:
            message = f"famille {family.name} : aucune ligne du champ {info.key}"
            raise ProjectError(message)
        cases = {
            k.split("/", 1)[1]: np.asarray(npz[k], dtype=np.float64)[index]
            for k in npz.files
            if k.startswith(("cas/", "pos/"))
        }
    member = [""] * index.size
    if family.members:
        for name in group_names(mesh, (family.members,)):
            inside = _rows_of_groups(
                mesh, kind[index], level[index], entity[index], nodes[index], [name]
            )
            for row in np.where(inside)[0]:
                if not member[int(row)]:
                    member[int(row)] = name
    extra = (M_RES, V_RES) if family.circular else ()
    return FamilyRows(
        family=family,
        info=info,
        index=index,
        node=nodes[index],
        xyz=mesh.coords[nodes[index]],
        kind=kind[index],
        element=entity[index],
        local=local[index],
        level=level[index],
        member=member,
        columns=(*info.components, *extra),
        cases=cases,
    )


@dataclass
class SectionRows:
    """A design section: its rows in its family, and the rows that cannot carry a
    design value with their reason."""

    section: DesignSection
    mask: Any
    singular: Any
    reasons: dict[int, str]
    notes: list[str]


def _coordinate(fr: FamilyRows, axis: str, *, absolute: bool = False) -> FloatArray:
    values = fr.xyz[:, AXES[axis]]
    return np.abs(values) if absolute else values


def rule_mask(fr: FamilyRows, mesh: Mesh, rule: SectionRule) -> tuple[Any, list[str]]:
    """Rows of `fr` that satisfy every criterion of `rule`, and what was read."""
    mask = np.ones(len(fr.index), dtype=bool)
    notes: list[str] = []
    if rule.node_group is not None:
        mask &= np.isin(fr.node, mesh.node_group(rule.node_group))
    if rule.groups:
        groups = group_names(mesh, rule.groups)
        mask &= _rows_of_groups(mesh, fr.kind, fr.level, fr.element, fr.node, groups)
    if rule.box is not None:
        for axis in ("X", "Y", "Z"):
            bounds = getattr(rule.box, axis.lower())
            if bounds is None:
                continue
            values = _coordinate(fr, axis, absolute=axis in rule.box.absolute)
            low, high = min(bounds), max(bounds)
            mask &= (values >= low - LEVEL) & (values <= high + LEVEL)
    if rule.near is not None:
        centres = np.unique(
            np.round(
                mesh.coords[
                    mesh.node_group(rule.near.node_group), AXES[rule.near.axis]
                ],
                6,
            )
        )
        values = _coordinate(fr, rule.near.axis)
        distance = np.min(np.abs(values[:, None] - centres[None, :]), axis=1)
        if rule.near.mode == "at":
            mask &= np.abs(distance - rule.near.distance) <= LEVEL
        elif rule.near.mode == "within":
            mask &= distance <= rule.near.distance + LEVEL
        else:
            mask &= distance > rule.near.distance + LEVEL
    if rule.station is not None:
        values = _coordinate(fr, rule.station.axis, absolute=rule.station.absolute)
        candidates = np.unique(np.round(values[mask], 6))
        if candidates.size == 0:
            return mask, notes
        chosen = float(candidates[np.argmin(np.abs(candidates - rule.station.value))])
        mask &= np.abs(values - chosen) <= LEVEL
        sign = "|" if rule.station.absolute else ""
        notes.append(
            f"station lue : {sign}{rule.station.axis}{sign} = {chosen:.3f} m "
            f"(déclarée {rule.station.value:.3f} m, nœud du maillage le plus proche)"
        )
    return mask, notes


def singular_rows(
    fr: FamilyRows,
    mesh: Mesh,
    deliverables: DeliverablesSection | None,
    shared_with: tuple[str, ...],
) -> tuple[Any, dict[int, str]]:
    """Rows of a shell inside an exclusion disc (PAT-013) or at a node shared with
    the beams of `shared_with` (CA-058), with the reason of each."""
    flagged = np.zeros(len(fr.index), dtype=bool)
    reasons: dict[int, str] = {}
    if fr.family.kind != "coque":
        return flagged, reasons
    xy = fr.xyz[:, :2]
    for disk in deliverables.exclusion_disks if deliverables else ():
        if disk.groups and not set(disk.groups) & set(fr.family.groups):
            continue
        inside = np.zeros(len(fr.index), dtype=bool)
        for centre in mesh.coords[mesh.node_group(disk.node_group), :2]:
            inside |= np.hypot(*(xy - centre).T) <= disk.radius + 1.0e-9
        for row in np.where(inside & ~flagged)[0]:
            reasons[int(row)] = (
                f"dans un disque d'exclusion de rayon {disk.radius:g} m autour de "
                f"{disk.node_group} (PAT-013) : appui ponctuel singulier"
            )
        flagged |= inside
    if shared_with:
        nodes = np.unique(
            np.concatenate([mesh.node_group(g) for g in group_names(mesh, shared_with)])
        )
        shared = np.isin(fr.node, nodes)
        for row in np.where(shared & ~flagged)[0]:
            reasons[int(row)] = (
                "nœud partagé avec une poutre ("
                + ", ".join(shared_with)
                + ") : l'effort s'y partage entre la coque et la poutre (CA-058)"
            )
        flagged |= shared
    return flagged, reasons


def section_rows(
    fr: FamilyRows,
    mesh: Mesh,
    section: DesignSection,
    deliverables: DeliverablesSection | None,
) -> SectionRows:
    mask, notes = rule_mask(fr, mesh, section.rule)
    if not mask.any():
        message = f"section {section.name} : aucune ligne ne suit la règle de lecture"
        raise ProjectError(message)
    flagged, reasons = singular_rows(fr, mesh, deliverables, section.shared_with)
    return SectionRows(section, mask, flagged, reasons, notes)


__all__ = [
    "AXES",
    "LEVEL",
    "M_RES",
    "V_RES",
    "FamilyRows",
    "SectionRows",
    "group_names",
    "load_family",
    "rule_mask",
    "section_rows",
    "singular_rows",
]
