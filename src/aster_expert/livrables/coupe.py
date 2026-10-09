"""Equilibrium of a cut of a T section (lot 49 ter, proof of D1; CTL-005 extended).

A beam sharing its nodes with a plate (`tee_section`) is cut at `along = value`. The
free body is everything on the side −x_l of the cut (beams, plate, piles, springs).
Its equilibrium in moment about the line of the cut (at `reference_level`, along the
`across` axis) gives the total bending moment of the whole cross-section of the
structure, with no assumption on how the bar and the plate share it:

    M_cut·e_c + Σ (r × F + M)·e_c = 0 over the external forces of the body,

where the moment of the cut on the body is, per R3.08.01 (traction σxx e_x on the face
of normal +x_l: moment MFY e_y + MFZ e_z) and CA-045 (plate: ∫ ζ σ_aa dζ = M_aa, moment
(n × e_a)·M_aa per unit length), M_cut·e_c = MFY (e_y·e_c) + MFZ (e_z·e_c) summed over
the bars, plus (n × e_a)·e_c × ∫ M_aa dc over the whole plate line. The external
forces are the nodal forces of the case (MED of loads, `charges.npz`), the reactions
(`REAC_NODA`) and the forces of the springs on the structure (−`SIEF_ELGA`), read in
the deliverables. Nodes on the cut have no lever arm for a force normal to the plate.
The nodal moments of the load vector are the consistent representation of distributed
loads: zero over each element, they are not counted (the share of the element crossing
the cut cannot be split at its node) and are reported apart. The bars are read at the
cut node as the mean of the two element ends (their jump is the nodal interaction with
the plate, CA-058), as the check of the total of lot 47 bis.

Reported: the total moment of the section in the convention of the bar
(M_T = M_cut·e_c / (e_y·e_c)), the moment the equilibrium requires
(−M_ext·e_c / (e_y·e_c)), their relative gap, and the share of the T sections (bands
of ±half-width) in the total.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from aster_expert.livrables.donnees import Deliverables, FieldInfo
from aster_expert.livrables.sections import AXES, load_family
from aster_expert.projet.declaration import (
    EngineeringSummarySection,
    EquilibriumCut,
    MemberFamily,
)
from aster_expert.projet.errors import ProjectError

TOL = 1.0e-6


def _unit(v: tuple[float, float, float]) -> np.ndarray[Any, Any]:
    a = np.asarray(v, dtype=float)
    out: np.ndarray[Any, Any] = a / np.linalg.norm(a)
    return out


def cut_equilibrium(
    d: Deliverables,
    infos: list[FieldInfo],
    summary: EngineeringSummarySection,
    family: MemberFamily,
    cut: EquilibriumCut,
) -> dict[str, Any]:
    tee = family.tee_section
    if tee is None:
        message = f"coupe : la famille {family.name} n'a pas de section en T"
        raise ProjectError(message)
    by_key = {i.key: i for i in infos}
    plate_family = next(f for f in summary.families if f.name == tee.plate_family)
    a, c = AXES[tee.along], AXES[tee.across]
    e_a = np.eye(3)[a]
    e_c = np.eye(3)[c]
    x_l, y_l = _unit(cut.beam_local_x), _unit(cut.beam_local_y)
    z_l = np.cross(x_l, y_l)
    normal = _unit(cut.plate_normal)
    side = float(np.dot(x_l, e_a))
    if abs(side) < 0.5:
        message = "coupe : l'axe local x de la poutre n'est pas selon l'axe de coupe"
        raise ProjectError(message)
    mesh = d.mesh
    coords = mesh.coords
    case_key = f"cas/{cut.case}"
    # Barres : extrémités au droit de la coupe, élément du côté du corps libre.
    beam = load_family(d, by_key[family.field], family)
    if case_key not in {f"cas/{k}" for k in beam.cases}:
        message = f"coupe : cas {cut.case} absent des livrables"
        raise ProjectError(message)
    values = beam.cases[cut.case]
    comps = beam.raw
    ends: dict[tuple[int, int], dict[int, int]] = {}
    for r in range(len(beam.index)):
        ends.setdefault((int(beam.level[r]), int(beam.element[r])), {})[
            int(beam.local[r])
        ] = r
    # Une coupe par un nœud : moyenne des deux extrémités d'élément qui y aboutissent
    # (le saut entre elles est l'effort d'interaction nodal barre–dalle, CA-058 ; la
    # valeur nodale de la dalle est aussi une moyenne des deux côtés) -- même lecture
    # que le contrôle du total du lot 47 bis (docs/essais_lot47bis.md § 1.5).
    by_node: dict[int, list[int]] = {}
    for pair in ends.values():
        for r in pair.values():
            if abs(beam.xyz[r, a] - cut.value) <= TOL:
                by_node.setdefault(int(beam.node[r]), []).append(r)
    m_bars = 0.0
    bar_count = 0
    bar_xyz: list[np.ndarray[Any, Any]] = []
    for rows in by_node.values():
        mfy = float(np.mean([values[r, comps.index("MFY")] for r in rows]))
        mfz = float(np.mean([values[r, comps.index("MFZ")] for r in rows]))
        m_bars += mfy * float(np.dot(y_l, e_c)) + mfz * float(np.dot(z_l, e_c))
        bar_count += len(rows)
        bar_xyz.append(beam.xyz[rows[0]])
    # Plaque : toute la ligne de la coupe.
    plate_info = by_key[plate_family.field]
    line_nodes = np.nonzero(np.abs(coords[:, a] - cut.value) <= TOL)[0]
    plate = load_family(d, plate_info, plate_family, keep_nodes=line_nodes)
    order = np.argsort(plate.xyz[:, c])
    across = plate.xyz[order, c]
    moment_part = next(p for p in tee.parts if p.beam == "MFY")
    m_aa = plate.cases[cut.case][order, plate.raw.index(moment_part.plate)]
    integral = float(np.trapezoid(m_aa, across))
    plate_factor = float(np.dot(np.cross(normal, e_a), e_c))
    band_integral = 0.0
    for xb in bar_xyz:
        on = np.abs(across - xb[c]) <= tee.half_width + 1.0e-9
        band_integral += float(np.trapezoid(m_aa[on], across[on]))
    m_cut = m_bars + plate_factor * integral
    # Forces extérieures du corps libre (côté −x_l de la coupe).
    origin = np.zeros(3)
    origin[a] = cut.value
    vertical = 3 - a - c
    origin[vertical] = cut.reference_level
    body = (coords[:, a] - cut.value) * side < -TOL
    on_cut = np.abs(coords[:, a] - cut.value) <= TOL
    m_ext = 0.0
    nodal_on_cut = 0.0
    nodal_body = 0.0
    found_load = False
    for name, vals, kind, entity, components in d.loads():
        if name != f"FN_{cut.case}":
            continue
        found_load = True
        rows = kind == 0
        nodes = entity[rows]
        v = vals.reshape(len(kind), -1)[rows]
        f = np.zeros((len(nodes), 3))
        mom = np.zeros((len(nodes), 3))
        for k, comp in enumerate(("DX", "DY", "DZ")):
            if comp in components:
                f[:, k] = v[:, components.index(comp)]
        for k, comp in enumerate(("DRX", "DRY", "DRZ")):
            if comp in components:
                mom[:, k] = v[:, components.index(comp)]
        lever = coords[nodes] - origin
        torque = np.cross(lever, f)
        inside = body[nodes]
        m_ext += float(np.sum(torque[inside] @ e_c))
        nodal_body += float(np.sum(mom[inside] @ e_c))
        nodal_on_cut += float(np.sum(mom[on_cut[nodes]] @ e_c))
    if not found_load:
        message = f"coupe : pas de champ de charges FN_{cut.case}"
        raise ProjectError(message)
    for info in infos:
        if info.family not in ("reactions", "ressorts"):
            continue
        fa = d.field(info)
        nodes = fa.node_of_row(mesh)
        arr = fa.arrays[case_key]
        f = np.zeros((len(nodes), 3))
        names = ("DX", "DY", "DZ") if info.family == "reactions" else ("N", "VY", "VZ")
        sign = 1.0 if info.family == "reactions" else -1.0
        for k, comp in enumerate(names):
            if comp in info.components:
                f[:, k] = sign * arr[:, info.components.index(comp)]
        if info.family == "reactions":
            _, first = np.unique(nodes, return_index=True)
            keep = np.zeros(len(nodes), dtype=bool)
            keep[first] = True
        else:
            keep = np.ones(len(nodes), dtype=bool)
        lever = coords[nodes] - origin
        torque = np.cross(lever, f)
        m_ext += float(np.sum(torque[keep & body[nodes]] @ e_c))
    bar_factor = float(np.dot(y_l, e_c))
    total_bar_convention = m_cut / bar_factor if bar_factor else float("nan")
    required = -m_ext / bar_factor if bar_factor else float("nan")
    scale = max(abs(total_bar_convention), abs(required)) or 1.0
    gap = abs(total_bar_convention - required) / scale
    band_total = (
        (m_bars + plate_factor * band_integral) / bar_factor if bar_factor else 0.0
    )
    return {
        "coupe": f"{tee.along} = {cut.value:+.3f}",
        "cas": cut.case,
        "extremites_de_barre": bar_count,
        "noeuds_de_barre": len(by_node),
        "lecture_barre": "moyenne des deux extrémités d'élément au nœud de la coupe",
        "noeuds_de_plaque": int(len(across)),
        "somme_barres_Nm": m_bars / bar_factor if bar_factor else float("nan"),
        "integrale_plaque_Nm": integral,
        "moment_total_section_Nm": total_bar_convention,
        "moment_equilibre_Nm": required,
        "ecart_relatif": gap,
        "moments_nodaux_sur_la_coupe_Nm": nodal_on_cut,
        "moments_nodaux_du_corps_Nm": nodal_body,
        "note_moments_nodaux": "moments du vecteur des charges consistant d'une charge "
        "répartie : nuls par élément, non comptés dans le bilan (seul reste celui de "
        "l'élément coupé, dont la part au nœud de la coupe n'est pas séparable)",
        "sections_en_T_Nm": band_total,
        "part_des_sections_en_T": band_total / total_bar_convention
        if total_bar_convention
        else float("nan"),
        "convention": "convention de la barre (M_T = MFY + ∫MYY dX pour une poutre "
        "x_l = +Y, y_l = −X : moment > 0 tend la fibre supérieure)",
    }


__all__ = ["cut_equilibrium"]
