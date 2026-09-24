"""Parameters, expected counts and expected invariants of the quay mesh (lot 27).

This module is **distinct from the Salome script** (`scripts/salome/combiwall_mesh.py`)
and runs before it: from the numerical data of the model (`ModelData`) it builds

- the parameters file the script reads (`build_params`): every value the script uses
  comes from there, none is written in the script;
- the invariants the produced MED must satisfy (`expected_invariants`), computed
  **analytically** from those parameters (closed-form counts of the structured
  meshes of the shells), never read back from a MED;
- the masses `POST_ELEM(MASS_INER)` must find with `RHO = 1`, `EPAIS = 1`, `A = 1`
  (`expected_masses`: areas and lengths of the groups, faceting included).

Discretisation rule (CLAUDE.md, "Scripts Salome", rule 2): no reliance on the
rounding of a local length. Each edge gets an integer number of segments, from the
target size and the real length of the edge (`segment_count`), or from the number a
decision fixes (5 per sheet-pile interval, 8 per beam bay, 1 per tie rod). The
script applies the same rule with its own code; the invariants check the outcome.

Frame (decision of point 9): X along the quay from `SYM_G` to `SYM_D`, Y towards the
land, Z up, origin on the axis of the central tube at level 0.00 CM; metres.
The basin side of a tube is its generatrix at Y = -R (angle 270 degrees).

`PIED_TUBES` (decision 12, point 11, lot 28): the node group of the foot ring of
every tube (Z = z_foot = -26.00), where the generator blocks the vertical
displacement. No other geometry reaches that level (the sheet piles stop at
z_sheet_foot = -18.00), so a `plane_nodes` invariant applies alongside the
group's own count/bbox.
"""

from __future__ import annotations

import math
from typing import Any

from aster_expert.agent.model_data import ModelData

TOL = 1e-9
"""Tolerance of the invariants (m): the nodes are computed, not measured."""

_LENGTH_UNITS = {"m", "m CM"}


class CombiwallMeshError(ValueError):
    """The data of the model cannot define the mesh."""


def segment_count(length: float, size: float) -> int:
    """Integer number of segments of an edge: nearest integer to length / size, >= 1.

    Half-way values round up. The count is imposed on the edge; the rounding of a
    local length by the mesher is never relied on.
    """
    if length <= 0 or size <= 0:
        message = f"longueur et taille doivent être positives : {length}, {size}"
        raise CombiwallMeshError(message)
    return max(1, math.floor(length / size + 0.5 + 1e-9))


# --- parameters -------------------------------------------------------------------


def _value(data: ModelData, name: str, *, unit: set[str] | None = None) -> Any:
    item = data.items().get(name)
    if item is None or item.status != "fourni":
        message = f"valeur absente ou à fournir : {name}"
        raise CombiwallMeshError(message)
    if unit is not None and item.unit not in unit:
        message = f"{name} : unité {item.unit!r} au lieu de {sorted(unit)}"
        raise CombiwallMeshError(message)
    return item.profile if item.profile is not None else item.value


def build_params(data: ModelData) -> dict[str, Any]:
    """Parameters file of the Salome script, from the numerical data of the model.

    Values are copied in metres (the data file already holds them in m or m CM) and
    checked against each other: the imposed levels must contain the levels the
    decisions need, the tie rod must be the segment the data describe, the tubes
    must fill the slice.
    """

    def length(name: str) -> float:
        return float(_value(data, name, unit=_LENGTH_UNITS))

    radius = length("tube.rayon")
    if abs(radius - length("repere.x_serrure_par_rapport_axe_tube")) > TOL:
        message = "le rayon du tube et le décalage des serrures diffèrent"
        raise CombiwallMeshError(message)
    x_left = length("repere.x_face_coupe_gauche")
    x_right = length("repere.x_face_coupe_droite")
    pitch = length("geometrie.entraxe_tubes")
    bays = int(_value(data, "geometrie.nombre_entraxes_tranche"))
    n_tubes = bays + 1
    if int(_value(data, "geometrie.nombre_tubes_entiers")) + int(
        _value(data, "geometrie.nombre_demi_tubes")
    ) != n_tubes or int(_value(data, "geometrie.nombre_palplanches_intercalaires")) != (
        bays
    ):
        message = "les comptes de tubes et de palplanches ne concordent pas"
        raise CombiwallMeshError(message)
    if abs(x_left + bays * pitch - x_right) > TOL:
        message = "les faces de coupe ne sont pas à huit entraxes l'une de l'autre"
        raise CombiwallMeshError(message)
    axes = [x_left + pitch * k for k in range(n_tubes)]
    central = (n_tubes + 1) // 2
    if abs(axes[central - 1]) > TOL:
        message = "le tube central n'est pas à X = 0"
        raise CombiwallMeshError(message)

    facets = int(_value(data, "maillage.nombre_facettes_par_tube"))
    if facets % 4 != 0:
        message = "le nombre de facettes doit être un multiple de 4 (coupe à ±90°)"
        raise CombiwallMeshError(message)
    levels = [float(v) for v in _value(data, "maillage.cotes_imposees")]
    if levels != sorted(levels) or len(set(levels)) != len(levels):
        message = "les cotes imposées doivent être strictement croissantes"
        raise CombiwallMeshError(message)
    foot_tube = length("geometrie.cote_pied_tubes")
    head_tube = length("geometrie.cote_tete_tubes")
    foot_sheet = length("geometrie.cote_pied_palplanches")
    head_sheet = length("geometrie.cote_tete_palplanches")
    if levels[0] != foot_tube or levels[-1] != head_tube:
        message = "les cotes imposées ne vont pas du pied à la tête des tubes"
        raise CombiwallMeshError(message)
    imposed_by_decisions = {
        "pied des palplanches": foot_sheet,
        "tête des palplanches": head_sheet,
        "dragage (ressorts)": length("geometrie.cote_dragage"),
        "interface argile/marne": length("sol.cote_interface_argile_marne"),
        "bas de l'empreinte": length("charges.accostage_cote_bas_empreinte"),
        "haut de l'empreinte": length("charges.accostage_cote_haut_empreinte"),
        "tête des tirants": length("tirants.cote_tete"),
    }
    for label, z in imposed_by_decisions.items():
        if z not in levels:
            message = f"la cote {z:g} ({label}) n'est pas une cote imposée"
            raise CombiwallMeshError(message)

    start = [0.0, length("tirants.position_tete_sur_tube"), length("tirants.cote_tete")]
    if abs(start[1] - radius) > TOL:
        message = "l'accrochage des tirants n'est pas sur la génératrice côté terre"
        raise CombiwallMeshError(message)
    anchor_y = length("tirants.ancrage_y")
    anchor_z = length("tirants.ancrage_z")
    run, drop = anchor_y - start[1], start[2] - anchor_z
    rod = math.hypot(run, drop)
    slope = math.degrees(math.atan2(drop, run))
    stated_length = length("tirants.longueur_modelisee")
    stated_slope = float(_value(data, "tirants.inclinaison"))
    # The anchor coordinates are stated to the centimetre: the length and the slope
    # they give differ slightly from the stated 26.00 m and 20 degrees. The
    # coordinates are used as stated; the gap is bounded here and reported.
    if (
        abs(rod - stated_length) > 1e-3 * stated_length
        or abs(slope - stated_slope) > 0.05
    ):
        message = (
            f"tirant : longueur {rod:.5f} m et pente {slope:.4f}° incompatibles "
            f"avec {stated_length} m et {stated_slope}°"
        )
        raise CombiwallMeshError(message)

    # Facet ranges [j0, j1) of each tube (facet j spans 360 j / N to 360 (j + 1) / N
    # degrees): whole tubes, and the two half tubes cut through their axis by the
    # planes of symmetry (the half on the inner side of the slice).
    quarter = facets // 4
    sectors = [[0, facets] for _ in range(n_tubes)]
    sectors[0] = [-quarter, quarter]
    sectors[-1] = [quarter, 3 * quarter]

    return {
        "schema": "combiwall_mesh_params_v1",
        "taille_verticale": length("maillage.taille_verticale_visee"),
        "tube": {
            "rayon": radius,
            "facettes": facets,
            "cotes": levels,
            "axes_x": axes,
            "central": central,
            "secteurs": sectors,
        },
        "palplanche": {
            "cotes": [z for z in levels if foot_sheet <= z <= head_sheet],
            "segments_largeur": int(
                _value(data, "maillage.nombre_elements_largeur_palplanche")
            ),
            # serrure lines: generatrices at Y = 0, on the +X side of a tube (angle 0)
            # and on the -X side of the next one (angle 180)
            "angles_serrure_deg": [0.0, 180.0],
        },
        "poutre": {
            "y": length("poutre_couronnement.position_axe_y"),
            "z": length("poutre_couronnement.cote_centre_gravite"),
            "segments_par_entraxe": int(
                _value(data, "maillage.nombre_elements_par_entraxe_poutre")
            ),
        },
        "tirants": {
            "debut_y": start[1],
            "debut_z": start[2],
            "angle_debut_deg": 90.0,  # generatrix at Y = +R: land side
            "fin_y": anchor_y,
            "fin_z": anchor_z,
            "segments": int(_value(data, "maillage.nombre_elements_par_tirant")),
            "longueur_donnee": stated_length,
            "longueur_des_coordonnees": rod,
            "pente_des_coordonnees_deg": slope,
        },
        "empreinte": {
            "tube": central,
            "cote_bas": length("charges.accostage_cote_bas_empreinte"),
            "cote_haut": length("charges.accostage_cote_haut_empreinte"),
            "angle_centre_deg": 270.0,
            "demi_angle_deg": float(
                _value(data, "charges.accostage_demi_angle_empreinte")
            ),
        },
        "ecran_poussee": {"angle_centre_deg": 90.0, "demi_angle_deg": 90.0},
        "bandes": {
            "RESS_AV_ARGI": {
                "cote_bas": length("sol.cote_interface_argile_marne"),
                "cote_haut": length("sol.cote_haut_ressorts"),
                "avec_palplanches": True,
            },
            "RESS_AV_MARNE": {
                "cote_bas": foot_tube,
                "cote_haut": length("sol.cote_interface_argile_marne"),
                "avec_palplanches": False,
            },
        },
        "symetrie": {"x_gauche": x_left, "x_droite": x_right},
        "precision": TOL,
    }


# --- layout, analytic ---------------------------------------------------------------


class _Layout:
    """Counts and coordinates derived from the parameters (no mesh involved)."""

    def __init__(self, params: dict[str, Any]) -> None:
        tube = params["tube"]
        self.params = params
        self.radius: float = tube["rayon"]
        self.facets: int = tube["facettes"]
        self.size: float = params["taille_verticale"]
        self.levels: list[float] = tube["cotes"]
        self.axes: list[float] = tube["axes_x"]
        self.central: int = tube["central"]
        self.n_tubes = len(self.axes)
        self.chord = 2.0 * self.radius * math.sin(math.pi / self.facets)
        if segment_count(self.chord, self.size) != 1:
            message = "facette plus longue que la taille visée : non prévu (1 segment)"
            raise CombiwallMeshError(message)
        self.sheet_levels: list[float] = params["palplanche"]["cotes"]
        self.sheet_columns: int = params["palplanche"]["segments_largeur"]
        self.rows = self._rows(self.levels)
        self.sheet_rows = self._rows(self.sheet_levels)
        self.vertical = sum(self.rows)
        self.sheet_vertical = sum(self.sheet_rows)
        # (j0, j1) facet index range of each tube, j1 excluded
        self.sectors: list[tuple[int, int]] = [
            (int(s[0]), int(s[1])) for s in tube["secteurs"]
        ]

    def _rows(self, levels: list[float]) -> list[int]:
        return [
            segment_count(b - a, self.size)
            for a, b in zip(levels[:-1], levels[1:], strict=True)
        ]

    def rows_between(self, low: float, high: float, *, sheet: bool = False) -> int:
        levels = self.sheet_levels if sheet else self.levels
        rows = self.sheet_rows if sheet else self.rows
        return sum(
            n
            for (a, b), n in zip(
                zip(levels[:-1], levels[1:], strict=True), rows, strict=True
            )
            if a >= low - TOL and b <= high + TOL
        )

    def is_full(self, number: int) -> bool:
        j0, j1 = self.sectors[number - 1]
        return j1 - j0 == self.facets

    def facet_count(self, number: int) -> int:
        j0, j1 = self.sectors[number - 1]
        return j1 - j0

    def in_window(self, j: int, center: float, half: float) -> bool:
        """Facet j (angles 360 j / N to 360 (j+1) / N) lies within the window."""
        low, high = center - half, center + half
        for angle in (360.0 * j / self.facets, 360.0 * (j + 1) / self.facets):
            if (angle - low) % 360.0 > (high - low) + 1e-6:
                return False
        return True

    def window_facets(self, number: int, center: float, half: float) -> list[int]:
        j0, j1 = self.sectors[number - 1]
        return [j for j in range(j0, j1) if self.in_window(j, center, half)]

    def vertex(self, number: int, j: int) -> tuple[float, float]:
        angle = 2.0 * math.pi * j / self.facets
        return (
            self.axes[number - 1] + self.radius * math.cos(angle),
            self.radius * math.sin(angle),
        )

    def ring_nodes(self, number: int) -> int:
        n = self.facet_count(number)
        return n if self.is_full(number) else n + 1

    def tube_nodes(self, number: int) -> int:
        return self.ring_nodes(number) * (self.vertical + 1)

    def tube_quads(self, number: int) -> int:
        return self.facet_count(number) * self.vertical

    def tube_seg2(self, number: int) -> int:
        n = self.facet_count(number)
        lines = n if self.is_full(number) else n + 1
        return n * len(self.levels) + lines * self.vertical

    def sheet_x(self, k: int) -> tuple[float, float]:
        """X of the two serrure lines of sheet pile k (1-based)."""
        return self.axes[k - 1] + self.radius, self.axes[k] - self.radius

    def sheet_nodes(self) -> int:  # interior columns only: the serrures are tube nodes
        return (self.sheet_columns - 1) * (self.sheet_vertical + 1)

    def sheet_quads(self) -> int:
        return self.sheet_columns * self.sheet_vertical

    def sheet_seg2(self) -> int:
        return self.sheet_columns * len(self.sheet_levels)

    @property
    def bay_segments(self) -> int:
        return int(self.params["poutre"]["segments_par_entraxe"])

    @property
    def tie_segments(self) -> int:
        return int(self.params["tirants"]["segments"])


def expected_segments(params: dict[str, Any]) -> dict[str, Any]:
    """Segments imposed on each type of edge (the mesh report lists them)."""
    lay = _Layout(params)
    return {
        "taille_visee": lay.size,
        "aretes_verticales_tube_et_palplanche": {
            f"{a:g} -> {b:g}": {"longueur": b - a, "segments": n}
            for (a, b), n in zip(
                zip(lay.levels[:-1], lay.levels[1:], strict=True),
                lay.rows,
                strict=True,
            )
        },
        "aretes_horizontales_facette": {"longueur": lay.chord, "segments": 1},
        "aretes_horizontales_palplanche": {
            "longueur": lay.axes[1] - lay.axes[0] - 2 * lay.radius,
            "segments": lay.sheet_columns,
        },
        "aretes_poutre": {
            "longueur": lay.axes[1] - lay.axes[0],
            "segments": lay.bay_segments,
        },
        "aretes_tirant": {
            "longueur": params["tirants"]["longueur_des_coordonnees"],
            "segments": lay.tie_segments,
        },
    }


# --- expected invariants -----------------------------------------------------------


def _bbox(*v: float) -> list[float]:
    return [float(x) for x in v]


def _union(boxes: list[list[float]]) -> list[float]:
    return _bbox(
        min(b[0] for b in boxes),
        max(b[1] for b in boxes),
        min(b[2] for b in boxes),
        max(b[3] for b in boxes),
        min(b[4] for b in boxes),
        max(b[5] for b in boxes),
    )


def _tube_box(
    lay: _Layout, number: int, js: range, z0: float, z1: float
) -> list[float]:
    xs, ys = zip(*(lay.vertex(number, j) for j in js), strict=True)
    return _bbox(min(xs), max(xs), min(ys), max(ys), z0, z1)


def _pt(x: float, y: float, z: float) -> list[float]:
    return [float(x), float(y), float(z)]


def _names(prefix: str, count: int) -> list[str]:
    return [f"{prefix}{k:02d}" for k in range(1, count + 1)]


def expected_invariants(params: dict[str, Any]) -> dict[str, Any]:
    """Invariants of the quay MED, computed from the parameters (schema of
    `aster_expert.meshing.invariants.Invariants`)."""
    lay = _Layout(params)
    n_tubes, n_sheets = lay.n_tubes, lay.n_tubes - 1
    z_foot, z_head = lay.levels[0], lay.levels[-1]
    z_sheet_foot = lay.sheet_levels[0]
    radius = lay.radius
    beam_y, beam_z = params["poutre"]["y"], params["poutre"]["z"]
    tie = params["tirants"]
    x_left, x_right = params["symetrie"]["x_gauche"], params["symetrie"]["x_droite"]

    # counts
    nodes = (
        sum(lay.tube_nodes(k) for k in range(1, n_tubes + 1))
        + n_sheets * lay.sheet_nodes()
        + (n_sheets * lay.bay_segments + 1)  # beam
        + n_tubes * lay.tie_segments  # tie rods: the start node is a tube node
    )
    quads = sum(lay.tube_quads(k) for k in range(1, n_tubes + 1)) + n_sheets * (
        lay.sheet_quads()
    )
    seg2 = (
        sum(lay.tube_seg2(k) for k in range(1, n_tubes + 1))
        + n_sheets * lay.sheet_seg2()
        + n_sheets * lay.bay_segments
        + n_tubes * lay.tie_segments
    )

    groups: list[dict[str, Any]] = []

    def cell_group(name: str, count: int, cell_type: str, bbox: list[float]) -> None:
        groups.append(
            {
                "name": name,
                "count": count,
                "cell_type": cell_type,
                "bbox": bbox,
                "tolerance": TOL,
            }
        )

    def node_group(name: str, count: int, bbox: list[float]) -> None:
        groups.append(
            {
                "name": name,
                "kind": "node",
                "count": count,
                "bbox": bbox,
                "tolerance": TOL,
            }
        )

    tube_boxes: list[list[float]] = []
    for k in range(1, n_tubes + 1):
        j0, j1 = lay.sectors[k - 1]
        box = _tube_box(lay, k, range(j0, j1 + 1), z_foot, z_head)
        tube_boxes.append(box)
        cell_group(f"TUBE_{k:02d}", lay.tube_quads(k), "QUAD4", box)
    cell_group(
        "TUBES",
        sum(lay.tube_quads(k) for k in range(1, n_tubes + 1)),
        "QUAD4",
        _union(tube_boxes),
    )
    sheet_boxes: list[list[float]] = []
    for k in range(1, n_sheets + 1):
        x0, x1 = lay.sheet_x(k)
        box = _bbox(x0, x1, 0.0, 0.0, z_sheet_foot, z_head)
        sheet_boxes.append(box)
        cell_group(f"PALP_{k:02d}", lay.sheet_quads(), "QUAD4", box)
    cell_group("PALPS", n_sheets * lay.sheet_quads(), "QUAD4", _union(sheet_boxes))
    tubes_total = sum(lay.tube_quads(k) for k in range(1, n_tubes + 1))
    cell_group(
        "ECRAN",
        tubes_total + n_sheets * lay.sheet_quads(),
        "QUAD4",
        _union(tube_boxes + sheet_boxes),
    )

    # ECRAN_POUSSEE: the facets of the tubes on the land side (Y >= 0), and the sheets
    push = params["ecran_poussee"]
    push_tubes = [
        lay.window_facets(k, push["angle_centre_deg"], push["demi_angle_deg"])
        for k in range(1, n_tubes + 1)
    ]
    push_boxes = [
        _tube_box(lay, k, range(min(js), max(js) + 2), z_foot, z_head)
        for k, js in enumerate(push_tubes, start=1)
    ]
    cell_group(
        "ECRAN_POUSSEE",
        sum(len(js) for js in push_tubes) * lay.vertical + n_sheets * lay.sheet_quads(),
        "QUAD4",
        _union(push_boxes + sheet_boxes),
    )
    cell_group(
        "POUTRE_COUR",
        n_sheets * lay.bay_segments,
        "SEG2",
        _bbox(x_left, x_right, beam_y, beam_y, beam_z, beam_z),
    )
    tie_boxes: list[list[float]] = []
    for k in range(1, n_tubes + 1):
        x = lay.axes[k - 1]
        box = _bbox(x, x, tie["debut_y"], tie["fin_y"], tie["fin_z"], tie["debut_z"])
        tie_boxes.append(box)
        cell_group(f"TIRANT_{k:02d}", lay.tie_segments, "SEG2", box)
    cell_group("TIRANTS", n_tubes * lay.tie_segments, "SEG2", _union(tie_boxes))

    # spring bands: every cell of the screen (or of the tubes only) between two levels
    for name, band in params["bandes"].items():
        low, high = band["cote_bas"], band["cote_haut"]
        count = sum(
            lay.facet_count(k) for k in range(1, n_tubes + 1)
        ) * lay.rows_between(low, high)
        boxes = list(tube_boxes)
        if band["avec_palplanches"]:
            count += (
                n_sheets * lay.sheet_columns * lay.rows_between(low, high, sheet=True)
            )
            boxes += sheet_boxes
        box = _union(boxes)
        box[4], box[5] = low, high
        cell_group(name, count, "QUAD4", box)

    # DEFENSE: the imprint on the basin side of the central tube
    imp = params["empreinte"]
    imp_facets = lay.window_facets(
        imp["tube"], imp["angle_centre_deg"], imp["demi_angle_deg"]
    )
    cell_group(
        "DEFENSE",
        len(imp_facets) * lay.rows_between(imp["cote_bas"], imp["cote_haut"]),
        "QUAD4",
        _tube_box(
            lay,
            imp["tube"],
            range(min(imp_facets), max(imp_facets) + 2),
            imp["cote_bas"],
            imp["cote_haut"],
        ),
    )

    # node groups
    for k in range(1, n_tubes + 1):
        j0, j1 = lay.sectors[k - 1]
        ring = _tube_box(lay, k, range(j0, j1 + 1), z_head, z_head)
        node_group(f"TETE_TUBE_{k:02d}", lay.ring_nodes(k), ring)
    for k in range(1, n_tubes + 1):
        x = lay.axes[k - 1]
        node_group(
            f"ANC_{k:02d}",
            1,
            _bbox(x, x, tie["fin_y"], tie["fin_y"], tie["fin_z"], tie["fin_z"]),
        )
    node_group(
        "ANCRAGES",
        n_tubes,
        _bbox(x_left, x_right, tie["fin_y"], tie["fin_y"], tie["fin_z"], tie["fin_z"]),
    )
    x_c = lay.axes[lay.central - 1]
    node_group("BOLLARD", 1, _bbox(x_c, x_c, beam_y, beam_y, beam_z, beam_z))
    y_low = -radius
    y_high = max(tie["fin_y"], beam_y, radius)
    sym_count = 2 * (lay.vertical + 1) + 2  # two cut generatrices, tie anchor, beam end
    for name, x in (("SYM_G", x_left), ("SYM_D", x_right)):
        node_group(name, sym_count, _bbox(x, x, y_low, y_high, z_foot, beam_z))

    # PIED_TUBES (decision 12, point 11): the foot ring of every tube (Z = z_foot);
    # no other geometry reaches that level, so a plane_nodes invariant applies too.
    foot_boxes = [
        _tube_box(
            lay,
            k,
            range(lay.sectors[k - 1][0], lay.sectors[k - 1][1] + 1),
            z_foot,
            z_foot,
        )
        for k in range(1, n_tubes + 1)
    ]
    node_group(
        "PIED_TUBES",
        sum(lay.ring_nodes(k) for k in range(1, n_tubes + 1)),
        _union(foot_boxes),
    )

    # nodes at the imposed levels, on every tube and every sheet pile
    nodes_at: list[dict[str, Any]] = []
    for k in range(1, n_tubes + 1):
        x = lay.axes[k - 1]
        for z in lay.levels:
            for side, y in (("bassin", -radius), ("terre", radius)):
                nodes_at.append(
                    {
                        "label": f"tube {k}, génératrice côté {side}, cote {z:g}",
                        "point": _pt(x, y, z),
                        "tolerance": TOL,
                    }
                )
    for k in range(1, n_sheets + 1):
        x0, x1 = lay.sheet_x(k)
        x_mid = x0 + 2 * (x1 - x0) / lay.sheet_columns
        for z in lay.sheet_levels:
            nodes_at.append(
                {
                    "label": f"palplanche {k}, colonne 2, cote {z:g}",
                    "point": _pt(x_mid, 0.0, z),
                    "tolerance": TOL,
                }
            )
    for k in range(1, n_tubes + 1):
        nodes_at.append(
            {
                "label": f"poutre au droit du tube {k}",
                "point": _pt(lay.axes[k - 1], beam_y, beam_z),
                "tolerance": TOL,
            }
        )

    shared: list[dict[str, Any]] = []
    for k in range(1, n_sheets + 1):
        x0, x1 = lay.sheet_x(k)
        for tube, x in ((k, x0), (k + 1, x1)):
            shared.append(
                {
                    "label": f"serrure de la palplanche {k} sur le tube {tube}",
                    "groups": [f"PALP_{k:02d}", f"TUBE_{tube:02d}"],
                    "count": lay.sheet_vertical + 1,
                    "at": [_pt(x, 0.0, z) for z in lay.sheet_levels],
                    "tolerance": TOL,
                }
            )
    for k in range(1, n_tubes + 1):
        shared.append(
            {
                "label": f"nœud de départ du tirant {k} sur le tube {k}",
                "groups": [f"TIRANT_{k:02d}", f"TUBE_{k:02d}"],
                "count": 1,
                "at": [_pt(lay.axes[k - 1], tie["debut_y"], tie["debut_z"])],
                "tolerance": TOL,
            }
        )
        shared.append(
            {
                "label": f"extrémité arrière du tirant {k} distincte de l'écran",
                "groups": [f"ANC_{k:02d}", "ECRAN"],
                "kinds": ["node", "cell"],
                "count": 0,
                "tolerance": TOL,
            }
        )
        shared.append(
            {
                "label": f"extrémité arrière du tirant {k} sur son tirant",
                "groups": [f"ANC_{k:02d}", f"TIRANT_{k:02d}"],
                "kinds": ["node", "cell"],
                "count": 1,
                "tolerance": TOL,
            }
        )
    shared.append(
        {
            "label": "BOLLARD sur la poutre",
            "groups": ["BOLLARD", "POUTRE_COUR"],
            "kinds": ["node", "cell"],
            "count": 1,
            "at": [_pt(x_c, beam_y, beam_z)],
            "tolerance": TOL,
        }
    )
    shared.append(
        {
            "label": "BOLLARD hors de l'écran",
            "groups": ["BOLLARD", "ECRAN"],
            "kinds": ["node", "cell"],
            "count": 0,
            "tolerance": TOL,
        }
    )
    shared.append(
        {
            "label": "poutre non reliée à l'écran (liaison rigide au lot 28)",
            "groups": ["POUTRE_COUR", "ECRAN"],
            "count": 0,
            "tolerance": TOL,
        }
    )
    shared.append(
        {
            "label": "tubes voisins sans nœud commun",
            "groups": ["TUBE_01", "TUBE_02"],
            "count": 0,
            "tolerance": TOL,
        }
    )
    shared.append(
        {
            "label": "palplanches voisines sans nœud commun",
            "groups": ["PALP_01", "PALP_02"],
            "count": 0,
            "tolerance": TOL,
        }
    )

    subsets = (
        [
            {"group": "TUBES", "of": "ECRAN"},
            {"group": "PALPS", "of": "ECRAN"},
            {"group": "ECRAN_POUSSEE", "of": "ECRAN"},
            {"group": "RESS_AV_ARGI", "of": "ECRAN"},
            {"group": "RESS_AV_MARNE", "of": "TUBES"},
            {"group": "DEFENSE", "of": f"TUBE_{imp['tube']:02d}"},
            {"group": "DEFENSE", "of": "TUBES"},
        ]
        + [{"group": f"TUBE_{k:02d}", "of": "TUBES"} for k in range(1, n_tubes + 1)]
        + [{"group": f"PALP_{k:02d}", "of": "PALPS"} for k in range(1, n_sheets + 1)]
        + [{"group": f"TIRANT_{k:02d}", "of": "TIRANTS"} for k in range(1, n_tubes + 1)]
    )

    # geometric checks from the areas of the cells
    ideal = 2.0 * (math.pi / 4.0) * radius * (imp["cote_haut"] - imp["cote_bas"])
    developed = len(imp_facets) * lay.chord * (imp["cote_haut"] - imp["cote_bas"])
    mid_rows = _mid_row_levels(lay)
    tube_width = sum(
        2 * radius if lay.is_full(k) else radius for k in range(1, n_tubes + 1)
    )
    sheet_width = sum(
        lay.sheet_x(k)[1] - lay.sheet_x(k)[0] for k in range(1, n_sheets + 1)
    )
    widths = [
        {
            "label": (
                f"bande de {z_sheet_foot:g} à {z_head:+g} : "
                "tubes côté terre et palplanches"
            ),
            "group": "ECRAN_POUSSEE",
            "z": mid_rows["haut"],
            "width": tube_width + sheet_width,
            "tolerance": TOL,
        },
        {
            "label": f"bande de {z_foot:g} à {z_sheet_foot:g} : tubes seuls",
            "group": "ECRAN_POUSSEE",
            "z": mid_rows["bas"],
            "width": tube_width,
            "tolerance": TOL,
        },
    ]

    return {
        "schema_version": 1,
        "counts": {"nodes": nodes, "cells": {"QUAD4": quads, "SEG2": seg2}},
        "bbox": _bbox(x_left, x_right, -radius, tie["fin_y"], z_foot, beam_z),
        "bbox_tolerance": TOL,
        "groups": groups,
        "group_areas": [
            {
                "group": "DEFENSE",
                "area": developed,
                "tolerance": TOL,
                "reference_area": ideal,
            }
        ],
        "projected_widths": widths,
        "subsets": subsets,
        "plane_nodes": [
            {"group": "SYM_G", "axis": "x", "value": x_left, "tolerance": TOL},
            {"group": "SYM_D", "axis": "x", "value": x_right, "tolerance": TOL},
            {"group": "PIED_TUBES", "axis": "z", "value": z_foot, "tolerance": TOL},
        ],
        "symmetry": {"tolerance": TOL},
        "nodes_at": nodes_at,
        "shared_nodes": shared,
        "no_orphan_nodes": True,
        "no_coincident_nodes": {"tolerance": TOL},
    }


def _mid_row_levels(lay: _Layout) -> dict[str, float]:
    """A level inside a row of cells of each band (never on a node level)."""

    def mid(low: float, high: float, rows: int) -> float:
        return low + (rows // 2 + 0.5) * (high - low) / rows

    sheet_intervals = list(
        zip(lay.sheet_levels[:-1], lay.sheet_levels[1:], strict=True)
    )
    a, b = sheet_intervals[len(sheet_intervals) // 2]
    upper = mid(a, b, lay.sheet_rows[len(sheet_intervals) // 2])
    a0, b0 = lay.levels[0], lay.levels[1]
    return {"haut": upper, "bas": mid(a0, b0, lay.rows[0])}


def band_projected_width(params: dict[str, Any], band: dict[str, Any]) -> float:
    """Projected width (m) of a spring band's cross-section: the tubes' own
    width (a half-tube on an edge tube contributes its radius, a full tube
    its diameter) plus, when the band carries them (`avec_palplanches`), the
    sheet-pile panels between -- the same closed-form width
    `expected_invariants` computes for its own `projected_widths` control on
    `ECRAN_POUSSEE`, generalised here to any band and any number of tubes
    (lot 30, étape 2: `aster_expert.generation.generate` no longer hardcodes
    the full quay's own 20.80/11.36 m for `aster_expert.generation.springs
    .check_spring_sum` -- a value tied to eight bays, wrong for any other
    slice length)."""
    lay = _Layout(params)
    tube_width = sum(
        2.0 * lay.radius if lay.is_full(k) else lay.radius
        for k in range(1, lay.n_tubes + 1)
    )
    if not band["avec_palplanches"]:
        return tube_width
    sheet_width = sum(
        lay.sheet_x(k)[1] - lay.sheet_x(k)[0] for k in range(1, lay.n_tubes)
    )
    return tube_width + sheet_width


# --- expected masses (Code_Aster reading) -------------------------------------------


def expected_masses(params: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Area (shell groups) or length (bar and beam groups) of every cell group.

    `POST_ELEM(MASS_INER)` with `RHO = 1`, `EPAIS = 1`, `A = 1` returns them as masses.
    The faceting is included: the shells are the flat facets, not the cylinder.
    """
    lay = _Layout(params)
    n_tubes, n_sheets = lay.n_tubes, lay.n_tubes - 1
    height = lay.levels[-1] - lay.levels[0]
    sheet_height = lay.sheet_levels[-1] - lay.sheet_levels[0]
    out: dict[str, dict[str, Any]] = {}

    def add(name: str, kind: str, mass: float) -> None:
        out[name] = {"kind": kind, "mass": mass}

    for k in range(1, n_tubes + 1):
        add(f"TUBE_{k:02d}", "shell", lay.facet_count(k) * lay.chord * height)
    add(
        "TUBES",
        "shell",
        sum(out[f"TUBE_{k:02d}"]["mass"] for k in range(1, n_tubes + 1)),
    )
    for k in range(1, n_sheets + 1):
        x0, x1 = lay.sheet_x(k)
        add(f"PALP_{k:02d}", "shell", (x1 - x0) * sheet_height)
    add(
        "PALPS",
        "shell",
        sum(out[f"PALP_{k:02d}"]["mass"] for k in range(1, n_sheets + 1)),
    )
    add("ECRAN", "shell", out["TUBES"]["mass"] + out["PALPS"]["mass"])
    push = params["ecran_poussee"]
    push_facets = sum(
        len(lay.window_facets(k, push["angle_centre_deg"], push["demi_angle_deg"]))
        for k in range(1, n_tubes + 1)
    )
    add(
        "ECRAN_POUSSEE",
        "shell",
        push_facets * lay.chord * height + out["PALPS"]["mass"],
    )
    for name, band in params["bandes"].items():
        low, high = band["cote_bas"], band["cote_haut"]
        area = (
            sum(lay.facet_count(k) for k in range(1, n_tubes + 1))
            * lay.chord
            * (high - low)
        )
        if band["avec_palplanches"]:
            area += sum(
                lay.sheet_x(k)[1] - lay.sheet_x(k)[0] for k in range(1, n_sheets + 1)
            ) * (high - low)
        add(name, "shell", area)
    imp = params["empreinte"]
    facets = lay.window_facets(
        imp["tube"], imp["angle_centre_deg"], imp["demi_angle_deg"]
    )
    add(
        "DEFENSE",
        "shell",
        len(facets) * lay.chord * (imp["cote_haut"] - imp["cote_bas"]),
    )
    add("POUTRE_COUR", "beam", lay.axes[-1] - lay.axes[0])
    rod = params["tirants"]["longueur_des_coordonnees"]
    for k in range(1, n_tubes + 1):
        add(f"TIRANT_{k:02d}", "bar", rod)
    add("TIRANTS", "bar", n_tubes * rod)
    return out


Point3D = tuple[float, float, float]


def spring_node_areas(params: dict[str, Any]) -> dict[str, dict[Point3D, float]]:
    """Nodal tributary area (m^2, decision 5 / point 4, lot 28) of every node on the
    **bassin side only** (Y <= 0) of each spring band -- analytic, no MED involved.

    "Projetée sur le plan Y = 0" (the decision's own wording) means the area of
    each quad counted here is its projection on the XZ plane (dropping Y), not its
    true developed area -- exactly what a subgrade-reaction spring reacts against
    (a load per unit *plan* area, not per unit facet area): for a quad spanning two
    tube vertices j, j+1 (or two sheet-pile columns) and two Z levels a, b, that
    projected area is the simple rectangle `abs(x(j+1) - x(j)) * (b - a)` (both
    vertical edges of the projection share their own x, so the shoelace area is
    exact, not approximate). Only the tube facets whose two bounding generatrices
    lie at Y <= 0 -- a window centred on the bassin generatrix (270 degrees) of
    half-angle 90 degrees, `lay.window_facets`, the same mechanism
    `ECRAN_POUSSEE`/`DEFENSE` already use, correctly intersected with each tube's
    own existing sector (the two half-tubes, 1 and 9, do not carry the facets a
    blind `[facets // 2, facets)` range would assume) -- and, when the band
    carries them (`avec_palplanches`), every sheet-pile column contribute.

    Each quad contributes exactly 1/4 of its projected area to each of its 4
    corner nodes -- the standard structured-grid tributary rule, applied by
    accumulation rather than by hand-classifying which nodes are "boundary": an
    edge node simply has fewer quads (from the selected set) touching it, so it
    accumulates less, with no separate case to get wrong. A lock-line node
    (angle 0 or 180 degrees) is shared between a tube's own bassin-side quads
    and its neighbouring sheet-pile's quads: both accumulate onto the same
    coordinate key, so it is counted once, not twice, exactly as decided.

    This is a closed-form identity, not a discretisation choice: summing every
    returned area reproduces exactly the band's own projected width (as
    `expected_invariants` computes it for the terre side; the bassin side gives
    the same value by symmetry) times its height, independently of
    `taille_verticale` -- checked by `test_meshing_combiwall.py`.
    """

    def key(x: float, y: float, z: float) -> Point3D:
        return (round(x, 9) + 0.0, round(y, 9) + 0.0, round(z, 9) + 0.0)

    def add(
        areas: dict[Point3D, float], x: float, y: float, z: float, value: float
    ) -> None:
        k = key(x, y, z)
        areas[k] = areas.get(k, 0.0) + value

    def rows_of(size: float, a: float, b: float) -> list[tuple[float, float]]:
        n = segment_count(b - a, size)
        zs = [a + (b - a) * r / n for r in range(n + 1)]
        return list(zip(zs[:-1], zs[1:], strict=True))

    lay = _Layout(params)
    out: dict[str, dict[Point3D, float]] = {}

    for name, band in params["bandes"].items():
        low, high = band["cote_bas"], band["cote_haut"]
        levels = [z for z in lay.levels if low - TOL <= z <= high + TOL]
        areas: dict[Point3D, float] = {}

        for tube in range(1, lay.n_tubes + 1):
            facets = lay.window_facets(tube, 270.0, 90.0)
            for level_a, level_b in zip(levels[:-1], levels[1:], strict=True):
                for a, b in rows_of(lay.size, level_a, level_b):
                    for j in facets:
                        xj, yj = lay.vertex(tube, j)
                        xj1, yj1 = lay.vertex(tube, j + 1)
                        quarter = abs(xj1 - xj) * (b - a) / 4.0
                        for x, y, z in (
                            (xj, yj, a),
                            (xj1, yj1, a),
                            (xj, yj, b),
                            (xj1, yj1, b),
                        ):
                            add(areas, x, y, z, quarter)
        if band["avec_palplanches"]:
            cols = lay.sheet_columns
            for sheet in range(1, lay.n_tubes):
                x0, x1 = lay.sheet_x(sheet)
                for level_a, level_b in zip(levels[:-1], levels[1:], strict=True):
                    for a, b in rows_of(lay.size, level_a, level_b):
                        for c in range(cols):
                            xc = x0 + (x1 - x0) * c / cols
                            xc1 = x0 + (x1 - x0) * (c + 1) / cols
                            quarter = (xc1 - xc) * (b - a) / 4.0
                            for x, z in ((xc, a), (xc1, a), (xc, b), (xc1, b)):
                                add(areas, x, 0.0, z, quarter)
        out[name] = areas
    return out


def tube_head_ring_points(params: dict[str, Any], number: int) -> tuple[Point3D, ...]:
    """Analytic (x, y, z) of every node of tube `number`'s own head ring
    (`TETE_TUBE_<number>`), at `z = tube.cotes[-1]` -- lot 31, étape 2:
    junction candidates need each ring node's own coordinates (never just the
    group's bounding box `expected_invariants` computes). Same enumeration as
    that function's own `TETE_TUBE_<k>` node count (`lay.ring_nodes`):
    `lay.vertex` is periodic in the facet index with period `lay.facets`, so
    `range(j0, j0 + ring_nodes)` gives exactly `ring_nodes` distinct points
    whether the ring is a full loop (no facet repeated) or a partial one (no
    wrap-around)."""
    lay = _Layout(params)
    j0, _j1 = lay.sectors[number - 1]
    z_head = lay.levels[-1]
    return tuple(
        (*lay.vertex(number, j0 + i), z_head) for i in range(lay.ring_nodes(number))
    )


PressurePoint = tuple[float, float]


def expected_pressure_resultant_y(
    params: dict[str, Any], profile_points: list[PressurePoint]
) -> float:
    """Exact Y-component resultant (N, if `profile_points` is in Pa/m) of a
    Z-dependent pressure applied to `ECRAN_POUSSEE` by `FORCE_COQUE`/`PRES`
    (point 5), analytic and computed **before** execution -- lot 28, Étape 4,
    "résultante appliquée" control.

    `profile_points` are exactly the `(z, p)` pairs a `DEFI_FONCTION` block
    receives (ascending Z, already through `doubled_profile`): the same
    linear interpolation, constant beyond the extremes (`PROL_DROITE`/
    `PROL_GAUCHE` = "CONSTANT").

    This does **not** integrate the true, continuous pressure field: it
    integrates the piecewise-linear function *as `DEFI_FONCTION` evaluates
    it*, at the mesh's own row boundaries (`_Layout.rows`, from
    `taille_verticale`) -- a bilinear DKT/QUAD4 shell element reconstructs a
    row's own pressure exactly this way, from the two nodal values at its
    own Z levels, regardless of any kink the profile has *inside* that row.
    Reproducing the same discrete sum, rather than the continuous integral,
    is what makes the comparison exact (1e-6) rather than merely
    discretisation-sensitive.

    `FORCE_COQUE` convention (U4.44.01, point 5): force = -pressure x normal.
    A tube facet's outward normal is exactly `(cos(theta_mid), sin(theta_mid),
    0)` (a regular polygon's chord normal bisects its two vertices' angles);
    a palplanche panel is flat in the Y = 0 plane, normal `(0, 1, 0)`
    (`ORIE_NORM_COQUE` propagates the same "outward, towards terre"
    orientation `MAIL`'s own reference point fixes on a tube facet, point 5).
    """
    lay = _Layout(params)
    push = params["ecran_poussee"]

    def p_at(z: float) -> float:
        if z <= profile_points[0][0]:
            return profile_points[0][1]
        if z >= profile_points[-1][0]:
            return profile_points[-1][1]
        for (z0, p0), (z1, p1) in zip(
            profile_points[:-1], profile_points[1:], strict=True
        ):
            if z0 <= z <= z1:
                return p0 + (p1 - p0) * (z - z0) / (z1 - z0)
        message = f"z={z} hors du domaine couvert par le profil"
        raise CombiwallMeshError(message)

    def rows_of(a: float, b: float) -> list[tuple[float, float]]:
        n = segment_count(b - a, lay.size)
        zs = [a + (b - a) * r / n for r in range(n + 1)]
        return list(zip(zs[:-1], zs[1:], strict=True))

    all_rows: list[tuple[float, float]] = []
    for a, b in zip(lay.levels[:-1], lay.levels[1:], strict=True):
        all_rows.extend(rows_of(a, b))
    pressure_integral = sum((p_at(a) + p_at(b)) / 2.0 * (b - a) for a, b in all_rows)

    tube_y_width = 0.0
    for k in range(1, lay.n_tubes + 1):
        for j in lay.window_facets(k, push["angle_centre_deg"], push["demi_angle_deg"]):
            theta_mid = math.pi * (2 * j + 1) / lay.facets
            tube_y_width += math.sin(theta_mid) * lay.chord

    # Palplanche panels: flat, in the Y = 0 plane, continuing the same
    # outward-to-terre orientation from the tube facets they share a
    # lock-line node with -- normal_y = +1.
    sheet_width = sum(
        lay.sheet_x(sheet)[1] - lay.sheet_x(sheet)[0] for sheet in range(1, lay.n_tubes)
    )

    return -(tube_y_width + sheet_width) * pressure_integral


def group_names(params: dict[str, Any]) -> dict[str, list[str]]:
    """The names of the convention (v3 of MM), by kind of group."""
    n = len(params["tube"]["axes_x"])
    cells = (
        _names("TUBE_", n)
        + ["TUBES"]
        + _names("PALP_", n - 1)
        + ["PALPS", "ECRAN", "ECRAN_POUSSEE", "POUTRE_COUR"]
        + _names("TIRANT_", n)
        + ["TIRANTS", *params["bandes"], "DEFENSE"]
    )
    nodes = (
        _names("TETE_TUBE_", n)
        + _names("ANC_", n)
        + ["ANCRAGES", "BOLLARD", "SYM_G", "SYM_D", "PIED_TUBES"]
    )
    return {"maille": cells, "noeud": nodes}
