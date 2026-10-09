"""Rows of a family of members and of its design sections (lot 49 bis).

A family (`engineering_summary.families` of `projet.yaml`) is a set of rows of one
deliverable field (`aster_expert.livrables.donnees`): the element ends of its beams
(`ELNO`), the nodes of its shells (`NOEU`), its springs, its supports. A design section
is a subset of those rows, chosen by the explicit rule the project declares
(`SectionRule`: node group, cell groups, coordinate box, distance to the nodes of a
group, nearest mesh station). Nothing here knows a structure: every name and every
coordinate comes from the declaration.

The rows of a shell that cannot carry a design value are flagged, never dropped in
silence: inside an exclusion disc (PAT-013, declared in `deliverables`), inside the
band of half-width b/2 along a beam sharing its nodes (E26, lot 49 ter: the plate is
read at the face of the beam), or at a node shared with a beam (CA-058: the shell and
the beam share the force there, and the shell's value alone has no physical meaning).

Lot 49 ter adds three things, declared by the project:

- the T section of a beam sharing its nodes with a plate (E25, rule E17.2,
  `tee_section`): at each row of the beam, the plate nodes of the same coordinate along
  the beam, within ±half-width across it, integrated by trapezoids and added to the
  bar, case by case (exact: the combinations are linear); the bar alone is kept in the
  columns `<component>_barre`;
- a cut of the beams at a level (`SectionRule.level`, E24): where no node lies there,
  a synthetic row interpolated linearly between the two ends of the element that
  crosses it, case by case;
- the resultant shear √(QX² + QY²) of a shell (`V_RES`), per unit width.
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
    Level,
    MemberFamily,
    SectionRule,
)
from aster_expert.projet.errors import ProjectError

LEVEL = 1.0e-3
"""Tolerance on coordinates (1 mm, the grid of `config/arrondis.yaml`)."""
AXES = {"X": 0, "Y": 1, "Z": 2}
M_RES = "M_RES"
V_RES = "V_RES"
"""Resultant moment √(MFY² + MFZ²) and shear √(VY² + VZ²) of a circular beam; shear
√(QX² + QY²) of a shell (lot 49 ter)."""
BAR_SUFFIX = "_barre"
"""Columns of the bar alone in a T section (E25: traceability only)."""
SYNTHETIC = 2
"""`kind` of a row interpolated at a level (lot 49 ter)."""


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
    added: tuple[str, ...] = ()
    """Raw columns appended to the field (the bar alone of a T section)."""
    synthetic: dict[int, dict[str, Any]] = field(default_factory=dict)
    """Row -> how it was interpolated (rows of `kind` SYNTHETIC)."""
    tee: dict[str, Any] | None = None
    """How the T section was composed (E25), for the report."""

    @property
    def raw(self) -> tuple[str, ...]:
        return (*self.info.components, *self.added)

    @property
    def resultants(self) -> tuple[str, ...]:
        if self.family.circular:
            return (M_RES, V_RES)
        if self.family.kind == "coque" and {"QX", "QY"} <= set(self.info.components):
            return (V_RES,)
        return ()

    def extend(self, values: FloatArray) -> FloatArray:
        """The raw columns and the resultants (circular beam: M and V; shell: V)."""
        comps = self.raw
        if self.family.circular:
            mfy, mfz = values[:, comps.index("MFY")], values[:, comps.index("MFZ")]
            vy, vz = values[:, comps.index("VY")], values[:, comps.index("VZ")]
            return np.column_stack([values, np.hypot(mfy, mfz), np.hypot(vy, vz)])
        if self.resultants:
            qx, qy = values[:, comps.index("QX")], values[:, comps.index("QY")]
            return np.column_stack([values, np.hypot(qx, qy)])
        return values

    def column(self, name: str) -> int:
        return self.columns.index(name)

    def place(self, row: int) -> dict[str, Any]:
        """Member, element, end, node and coordinates of a row (1-based MED numbers);
        an interpolated row names its element, its two ends and their weights."""
        x, y, z = (float(v) for v in self.xyz[row])
        if row in self.synthetic:
            info = self.synthetic[row]
            return {
                "groupe": self.member[row] or None,
                "maille_med": int(self.element[row]) + 1,
                "extremite": None,
                "noeud_med": None,
                "coordonnees_m": [x, y, z],
                "interpolation": {
                    "noeuds_med": info["noeuds_med"],
                    "extremites": info["extremites"],
                    "poids": info["poids"],
                    "coordonnees_extremites_m": info["coordonnees_m"],
                },
            }
        return {
            "groupe": self.member[row] or None,
            "maille_med": int(self.element[row]) + 1 if self.kind[row] > 0 else None,
            "extremite": int(self.local[row]) + 1 if self.kind[row] == 1 else None,
            "noeud_med": int(self.node[row]) + 1,
            "coordonnees_m": [x, y, z],
        }


def load_family(
    d: Deliverables,
    info: FieldInfo,
    family: MemberFamily,
    *,
    keep_nodes: IntArray | None = None,
) -> FamilyRows:
    """The rows of `family` in the field `info`, with the arrays of the elementary
    cases and of the moving positions restricted to them (and to the rows at
    `keep_nodes` when given: the band of plate of a T section)."""
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
        if keep_nodes is not None:
            keep &= np.isin(nodes, keep_nodes)
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
    extra: tuple[str, ...] = (M_RES, V_RES) if family.circular else ()
    if family.kind == "coque" and {"QX", "QY"} <= set(info.components):
        extra = (V_RES,)
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
            if f"{axis.lower()}_min" in rule.box.exclusive:
                mask &= values > low + LEVEL
            else:
                mask &= values >= low - LEVEL
            if f"{axis.lower()}_max" in rule.box.exclusive:
                mask &= values < high - LEVEL
            else:
                mask &= values <= high + LEVEL
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
        at = np.zeros(len(fr.index), dtype=bool)
        sign = "|" if rule.station.absolute else ""
        for target in rule.station.targets:
            chosen = float(candidates[np.argmin(np.abs(candidates - target))])
            at |= np.abs(values - chosen) <= LEVEL
            notes.append(
                f"station lue : {sign}{rule.station.axis}{sign} = {chosen:.3f} m "
                f"(déclarée {target:.3f} m, nœud du maillage le plus proche)"
            )
        mask &= at
    if rule.level is not None:
        key = (rule.level.axis, float(rule.level.value))
        at = np.zeros(len(fr.index), dtype=bool)
        for row, info in fr.synthetic.items():
            at[row] = info["niveau"] == key
        exact = (fr.kind != SYNTHETIC) & (
            np.abs(fr.xyz[:, AXES[rule.level.axis]] - rule.level.value) <= LEVEL
        )
        mask &= at | exact
        notes.append(
            f"coupe à {rule.level.axis} = {rule.level.value:.3f} m : "
            f"{int(at.sum())} ligne(s) interpolée(s) entre les extrémités de "
            f"l'élément qui la traverse, {int(exact.sum())} extrémité(s) d'élément "
            "à cette cote"
        )
    return mask, notes


@dataclass(frozen=True)
class Band:
    """E26: plate rows closer than `half_width` (strictly) to a node of a beam family
    sharing its nodes with the plate."""

    family: str
    nodes_xy: FloatArray
    half_width: float
    source: str


def band_of(mesh: Mesh, family: MemberFamily) -> Band | None:
    if family.exclusion_band is None:
        return None
    nodes: list[IntArray] = []
    for group in group_names(mesh, family.groups):
        cells = mesh.cell_group(group)
        if cells is None:
            nodes.append(mesh.node_group(group))
            continue
        level, ids = cells
        nodes.append(np.unique(mesh.arrays[f"conn_{level}"][ids]))
    unique = np.unique(np.concatenate(nodes))
    return Band(
        family.name,
        mesh.coords[unique, :2],
        family.exclusion_band.half_width,
        family.exclusion_band.source,
    )


def band_distance(xy: FloatArray, band: Band) -> FloatArray:
    """Distance in the plane XY of each point to the nearest node of the beams."""
    best = np.full(len(xy), np.inf)
    for start in range(0, len(band.nodes_xy), 256):
        chunk = band.nodes_xy[start : start + 256]
        d = np.hypot(
            xy[:, None, 0] - chunk[None, :, 0], xy[:, None, 1] - chunk[None, :, 1]
        )
        best = np.minimum(best, d.min(axis=1))
    return best


def singular_rows(
    fr: FamilyRows,
    mesh: Mesh,
    deliverables: DeliverablesSection | None,
    shared_with: tuple[str, ...],
    bands: tuple[Band, ...] = (),
) -> tuple[Any, dict[int, str]]:
    """Rows of a shell inside an exclusion disc (PAT-013), inside the band of a beam
    sharing its nodes (E26) or at a node shared with the beams of `shared_with`
    (CA-058), with the reason of each."""
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
    for band in bands:
        inside = band_distance(xy, band) < band.half_width - LEVEL
        for row in np.where(inside & ~flagged)[0]:
            reasons[int(row)] = (
                f"dans la bande de ±{band.half_width:g} m le long des {band.family} "
                f"(E26 : lecture au nu ; valeur d'axe, comparaison seulement) -- "
                f"{band.source}"
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
    bands: tuple[Band, ...] = (),
) -> SectionRows:
    mask, notes = rule_mask(fr, mesh, section.rule)
    if not mask.any():
        message = f"section {section.name} : aucune ligne ne suit la règle de lecture"
        raise ProjectError(message)
    flagged, reasons = singular_rows(fr, mesh, deliverables, section.shared_with, bands)
    return SectionRows(section, mask, flagged, reasons, notes)


# --- Lot 49 ter : coupe interpolée, section en T -------------------------------------


def add_level_rows(fr: FamilyRows, level: Level) -> int:
    """Append to `fr` one row per beam element crossing `axis = value` strictly,
    interpolated linearly between its two ends, case by case. Returns the count."""
    axis = AXES[level.axis]
    value = float(level.value)
    key = (level.axis, value)
    if any(info["niveau"] == key for info in fr.synthetic.values()):
        return 0
    ends: dict[tuple[int, int], dict[int, int]] = {}
    for row in np.where(fr.kind == 1)[0]:
        ends.setdefault((int(fr.level[row]), int(fr.element[row])), {})[
            int(fr.local[row])
        ] = int(row)
    new: list[tuple[int, int, float, float]] = []
    for pair in ends.values():
        if 0 not in pair or 1 not in pair:
            continue
        r0, r1 = pair[0], pair[1]
        z0, z1 = float(fr.xyz[r0, axis]), float(fr.xyz[r1, axis])
        low, high = min(z0, z1), max(z0, z1)
        if not (low + LEVEL < value < high - LEVEL):
            continue
        w1 = (value - z0) / (z1 - z0)
        new.append((r0, r1, 1.0 - w1, w1))
    if not new:
        return 0
    start = len(fr.index)
    r0s = np.array([n[0] for n in new])
    r1s = np.array([n[1] for n in new])
    wa = np.array([n[2] for n in new])[:, None]
    wb = np.array([n[3] for n in new])[:, None]
    xyz = wa * fr.xyz[r0s] + wb * fr.xyz[r1s]
    xyz[:, axis] = value
    fr.index = np.concatenate([fr.index, np.full(len(new), -1)])
    fr.node = np.concatenate([fr.node, np.full(len(new), -1)])
    fr.xyz = np.vstack([fr.xyz, xyz])
    fr.kind = np.concatenate([fr.kind, np.full(len(new), SYNTHETIC)])
    fr.element = np.concatenate([fr.element, fr.element[r0s]])
    fr.local = np.concatenate([fr.local, np.full(len(new), -1)])
    fr.level = np.concatenate([fr.level, fr.level[r0s]])
    fr.member = [*fr.member, *[fr.member[int(r)] for r in r0s]]
    for case, values in fr.cases.items():
        fr.cases[case] = np.vstack([values, wa * values[r0s] + wb * values[r1s]])
    for k, (r0, r1, a, b) in enumerate(new):
        fr.synthetic[start + k] = {
            "niveau": key,
            "lignes": [r0, r1],
            "noeuds_med": [int(fr.node[r0]) + 1, int(fr.node[r1]) + 1],
            "extremites": [int(fr.local[r0]) + 1, int(fr.local[r1]) + 1],
            "poids": [a, b],
            "coordonnees_m": [
                [float(v) for v in fr.xyz[r0]],
                [float(v) for v in fr.xyz[r1]],
            ],
        }
    return len(new)


def band_nodes(mesh: Mesh, beam: FamilyRows, plate_groups: list[str], tee: Any) -> Any:
    """Plate nodes of the T section of `beam` (same `along`, |across| ≤ half-width)."""
    along, across = AXES[tee.along], AXES[tee.across]
    plate = np.unique(
        np.concatenate(
            [
                np.unique(mesh.arrays[f"conn_{lv}"][ids])
                for lv, ids in (
                    c for c in (mesh.cell_group(g) for g in plate_groups) if c
                )
            ]
        )
    )
    coords = mesh.coords[plate]
    beam_xyz = mesh.coords[np.unique(beam.node[beam.node >= 0])]
    keep = np.zeros(len(plate), dtype=bool)
    for xb in beam_xyz:
        keep |= (np.abs(coords[:, along] - xb[along]) < 1.0e-6) & (
            np.abs(coords[:, across] - xb[across]) <= tee.half_width + 1.0e-9
        )
    return plate[keep]


def compose_tee(beam: FamilyRows, plate: FamilyRows, tee: Any) -> None:
    """E25: the beam's columns of `tee.parts` become bar + ∫ plate over the band, case
    by case; the bar alone is kept in `<component>_barre` (raw columns appended)."""
    along, across = AXES[tee.along], AXES[tee.across]
    rows: list[int] = []
    idx: list[int] = []
    weights: list[float] = []
    widths: set[int] = set()
    for r in range(len(beam.index)):
        xb = beam.xyz[r]
        sel = np.nonzero(
            (np.abs(plate.xyz[:, along] - xb[along]) < 1.0e-6)
            & (np.abs(plate.xyz[:, across] - xb[across]) <= tee.half_width + 1.0e-9)
        )[0]
        if sel.size < 2:
            message = (
                f"section en T de {beam.family.name} : bande de {tee.plate_family} "
                f"vide en {xb.tolist()}"
            )
            raise ProjectError(message)
        order = sel[np.argsort(plate.xyz[sel, across])]
        xs = plate.xyz[order, across]
        w = np.zeros(len(xs))
        dx = np.diff(xs)
        w[:-1] += dx / 2.0
        w[1:] += dx / 2.0
        rows += [r] * len(order)
        idx += order.tolist()
        weights += w.tolist()
        widths.add(len(order))
    r_arr = np.array(rows)
    i_arr = np.array(idx)
    w_arr = np.array(weights)
    plate_comps = plate.raw
    beam_comps = list(beam.info.components)
    bars = tuple(f"{p.beam}{BAR_SUFFIX}" for p in tee.parts)
    n = len(beam.index)
    for case, values in beam.cases.items():
        if case not in plate.cases:
            message = f"section en T : cas {case} absent de {tee.plate_family}"
            raise ProjectError(message)
        pv = plate.cases[case]
        out = np.column_stack(
            [values, *[values[:, beam_comps.index(p.beam)] for p in tee.parts]]
        )
        for part in tee.parts:
            integral = np.bincount(
                r_arr,
                weights=pv[i_arr, plate_comps.index(part.plate)] * w_arr,
                minlength=n,
            )
            out[:, beam_comps.index(part.beam)] += part.factor * integral
        beam.cases[case] = out
    beam.added = (*beam.added, *bars)
    beam.columns = (*beam.raw, *beam.resultants)
    beam.tee = {
        "famille_plaque": tee.plate_family,
        "demi_largeur_m": tee.half_width,
        "axe_de_la_poutre": tee.along,
        "integration_selon": tee.across,
        "noeuds_par_bande": sorted(widths),
        "composantes": [
            f"{p.beam} + {p.factor:g} × ∫{p.plate} d{tee.across}" for p in tee.parts
        ],
        "barre_seule": list(bars),
        "source": tee.source,
    }


__all__ = [
    "AXES",
    "BAR_SUFFIX",
    "LEVEL",
    "M_RES",
    "SYNTHETIC",
    "V_RES",
    "Band",
    "FamilyRows",
    "SectionRows",
    "add_level_rows",
    "band_distance",
    "band_nodes",
    "band_of",
    "compose_tee",
    "group_names",
    "load_family",
    "rule_mask",
    "section_rows",
    "singular_rows",
]
