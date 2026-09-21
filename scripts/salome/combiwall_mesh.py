# ruff: noqa: E501, C401, PTH123
"""Lot 27 -- mesh of the combi-wall quay QUAI-CW-TEST-01 (slice of 8 bays).

Run by `aster-expert mesh run --params <params.json> combiwall_mesh.py` inside
Salome (Python 3.9). Arguments: parameters file, output MED name. The parameters
file is produced by the repository (`scripts/build_lot27_maillage.py`, from
`data/examples/combiwall_model_data.yaml`); nothing numerical is written here.

Rules of CLAUDE.md, "Scripts Salome":

- one single partition of the whole geometry (`# ASSEMBLY begin/end`);
- groups created on the geometry (`CreateGroup`, `GetInPlace`, `UnionIDs`) then
  transferred to the mesh (`GroupOnGeom`), never picked by hand;
- no coordinate in the script: every value comes from the parameters file;
- every GEOM / SMESH call with more than three parameters passes them by name;
- no reliance on the rounding of a local length: each edge receives an integer
  number of segments (`segment_count`, from the target size and the real length of
  the edge, or from the number a decision fixes), imposed by a sub-mesh hypothesis;
- the fingerprint of the parameters and the segments imposed are written next to the
  MED (`<stem>.meta.json`).

Frame (point 9): X along the quay, Y towards the land, Z up. Facet j of a tube
spans the angles 360 j / N to 360 (j + 1) / N degrees; angle 0 is the +X generatrix
(a lock line, Y = 0), 90 the land side (Y > 0), 270 the basin side.

Names and signatures of GEOM / SMESH: `data/examples/lot27_maillage/
signatures_geom_smesh.txt` (probe `lot27_sonde_signatures.py`), never from memory.
"""

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import salome
import SMESH
from salome.geom import geomBuilder
from salome.smesh import smeshBuilder

salome.salome_init()
geompy = geomBuilder.New()
smesh = smeshBuilder.New()

BASE = Path(sys.argv[0]).resolve().parent
PARAMS_PATH = BASE / sys.argv[1]
MED_PATH = BASE / sys.argv[2]

RAW = PARAMS_PATH.read_bytes()
PARAMS = json.loads(RAW)
START = time.time()


def log(message):
    """Print and append to `<MED stem>.progress.txt` (survives a killed run)."""
    line = "LOT27 [%6.1f s] %s" % (time.time() - START, message)
    print(line)
    with open(str(MED_PATH.with_suffix(".progress.txt")), "a") as handle:
        handle.write(line + "\n")


TUBE = PARAMS["tube"]
SHEET = PARAMS["palplanche"]
BEAM = PARAMS["poutre"]
ROD = PARAMS["tirants"]
IMPRINT = PARAMS["empreinte"]
PUSH = PARAMS["ecran_poussee"]
BANDS = PARAMS["bandes"]
SYMMETRY = PARAMS["symetrie"]

RADIUS = TUBE["rayon"]
FACETS = TUBE["facettes"]
LEVELS = TUBE["cotes"]
AXES = TUBE["axes_x"]
SECTORS = TUBE["secteurs"]
NUMBERS = range(1, len(AXES) + 1)
INTERVALS = list(zip(LEVELS[:-1], LEVELS[1:]))  # noqa: B905 (Python 3.9)
SIZE = PARAMS["taille_verticale"]
CHORD = 2.0 * RADIUS * math.sin(math.pi / FACETS)


def segment_count(length, size):
    """Integer number of segments of an edge: nearest integer to length / size, >= 1."""
    return max(1, int(math.floor(length / size + 0.5 + 1e-9)))


def clean(value):
    """Remove the rounding noise of cos/sin (an exact 0 stays an exact 0)."""
    return round(value, 12) + 0.0


def facet_of_angle(angle_deg):
    """Vertex index of an angle: it must be a multiple of the facet angle."""
    index = angle_deg * FACETS / 360.0
    if abs(index - round(index)) > 1e-9:
        raise RuntimeError("angle %r is not on a facet boundary" % angle_deg)
    return int(round(index))


def is_full(number):
    return SECTORS[number - 1][1] - SECTORS[number - 1][0] == FACETS


def in_window(j, center_deg, half_deg):
    """True when facet j lies inside [center - half, center + half] (degrees)."""
    low, high = center_deg - half_deg, center_deg + half_deg
    for angle in (360.0 * j / FACETS, 360.0 * (j + 1) / FACETS):
        if (angle - low) % 360.0 > (high - low) + 1e-6:
            return False
    return True


# ---------------------------------------------------------------------------------
# Point 1 / decisions 2 and 11 -- tubes (DKT shells, 40 facets) and sheet piles.
# Every facet is built one elevation interval at a time, the elevations being the
# imposed levels: they are therefore lines of the partition. The two half tubes
# are the facets of the sectors cut through the axis by the planes X = +-10.40.
# ---------------------------------------------------------------------------------
VERTICES = {}


def vertex_key(number, j, level_index):
    return (number, j % FACETS if is_full(number) else j, level_index)


def vertex(number, j, level_index):
    key = vertex_key(number, j, level_index)
    if key not in VERTICES:
        angle = 2.0 * math.pi * key[1] / FACETS
        VERTICES[key] = geompy.MakeVertex(
            clean(AXES[number - 1] + RADIUS * math.cos(angle)),
            clean(RADIUS * math.sin(angle)),
            LEVELS[level_index],
        )
    return VERTICES[key]


def face(vertices):
    wire = geompy.MakePolyline(thePoints=vertices, theIsClosed=True)
    return geompy.MakeFaceWires(theWires=[wire], isPlanarWanted=1)


def edge(first, second):
    return geompy.MakeEdge(thePnt1=first, thePnt2=second)


TUBE_FACES = {}  # (tube, facet j, interval i) -> face
VERTICAL_EDGES = {}  # (tube, vertex j, interval i) -> edge
HORIZONTAL_EDGES = {}  # (tube, facet j, level index) -> edge
for number in NUMBERS:
    j0, j1 = SECTORS[number - 1]
    for j in range(j0, j1):
        for i in range(len(INTERVALS)):
            TUBE_FACES[(number, j, i)] = face(
                [
                    vertex(number, j, i),
                    vertex(number, j + 1, i),
                    vertex(number, j + 1, i + 1),
                    vertex(number, j, i + 1),
                ]
            )
        for level_index in range(len(LEVELS)):
            HORIZONTAL_EDGES[(number, j, level_index)] = edge(
                vertex(number, j, level_index), vertex(number, j + 1, level_index)
            )
    last = j1 if not is_full(number) else j1 - 1
    for j in range(j0, last + 1):
        for i in range(len(INTERVALS)):
            VERTICAL_EDGES[(number, j, i)] = edge(
                vertex(number, j, i), vertex(number, j, i + 1)
            )
log(
    "tubes: %d faces, %d horizontal and %d vertical edges"
    % (len(TUBE_FACES), len(HORIZONTAL_EDGES), len(VERTICAL_EDGES))
)

# Sheet piles: flat, in the plane Y = 0, between the lock lines of two tubes. They
# reuse the vertices of the tubes on the lock generatrices, so that the nodes are
# shared over the whole height.
LOCK_LEFT = facet_of_angle(SHEET["angles_serrure_deg"][0])
LOCK_RIGHT = facet_of_angle(SHEET["angles_serrure_deg"][1])
SHEET_LEVELS = [LEVELS.index(z) for z in SHEET["cotes"]]
SHEET_FACES = {}  # (sheet k, index into SHEET_LEVELS) -> face
SHEET_HORIZONTAL_EDGES = []
for k in range(1, len(AXES)):
    for position, level_index in enumerate(SHEET_LEVELS):
        SHEET_HORIZONTAL_EDGES.append(
            edge(
                vertex(k, LOCK_LEFT, level_index),
                vertex(k + 1, LOCK_RIGHT, level_index),
            )
        )
        if position + 1 < len(SHEET_LEVELS):
            upper = SHEET_LEVELS[position + 1]
            SHEET_FACES[(k, position)] = face(
                [
                    vertex(k, LOCK_LEFT, level_index),
                    vertex(k + 1, LOCK_RIGHT, level_index),
                    vertex(k + 1, LOCK_RIGHT, upper),
                    vertex(k, LOCK_LEFT, upper),
                ]
            )
log("sheet piles: %d faces" % len(SHEET_FACES))

# ---------------------------------------------------------------------------------
# Point 3 -- crown beam on its axis (Y, Z of the parameters), one edge per bay,
# a vertex (hence a node) on the axis of every tube.
# ---------------------------------------------------------------------------------
BEAM_VERTICES = [geompy.MakeVertex(x, BEAM["y"], BEAM["z"]) for x in AXES]
BEAM_EDGES = [edge(a, b) for a, b in zip(BEAM_VERTICES[:-1], BEAM_VERTICES[1:])]  # noqa: B905

# ---------------------------------------------------------------------------------
# Point 2 -- nine tie rods, one bar element each: from the tube node on the land-side
# generatrix at the head level to the anchor (Y, Z of the parameters), in the plane
# of the tube axis (the two rods of the planes of symmetry lie in those planes).
# ---------------------------------------------------------------------------------
ROD_HEAD_J = facet_of_angle(ROD["angle_debut_deg"])
ROD_HEAD_LEVEL = LEVELS.index(ROD["debut_z"])
ROD_ENDS = [geompy.MakeVertex(x, ROD["fin_y"], ROD["fin_z"]) for x in AXES]
ROD_EDGES = [
    edge(vertex(number, ROD_HEAD_J, ROD_HEAD_LEVEL), ROD_ENDS[number - 1])
    for number in NUMBERS
]

# ASSEMBLY begin: one single partition of the whole geometry.
PARTITION = geompy.MakePartition(
    ListShapes=list(TUBE_FACES.values())
    + list(SHEET_FACES.values())
    + BEAM_EDGES
    + ROD_EDGES,
    ListTools=[],
    ListKeepInside=[],
    ListRemoveInside=[],
    Limit=geompy.ShapeType["FACE"],
    RemoveWebs=0,
    ListMaterials=[],
    KeepNonlimitShapes=1,
)
# ASSEMBLY end
log("partition done")

IDS_CACHE = {}


def geometry_ids(shapes, kind):
    """Identifiers, in `PARTITION`, of the sub-shapes of type `kind` lying in `shapes`."""
    found = geompy.GetInPlace(
        theShapeWhere=PARTITION, theShapeWhat=geompy.MakeCompound(theShapes=shapes)
    )
    return set(
        geompy.GetSubShapeID(PARTITION, sub)
        for sub in geompy.SubShapeAll(found, geompy.ShapeType[kind])
    )


def geometry_group(name, ids, kind):
    group = geompy.CreateGroup(
        theMainShape=PARTITION, theShapeType=geompy.ShapeType[kind], theName=name
    )
    geompy.UnionIDs(theGroup=group, theSubShapes=sorted(ids))
    return group


# ---------------------------------------------------------------------------------
# Discretisation: an integer number of segments on every edge, imposed by a
# sub-mesh hypothesis on a group of edges of the partition, one group per class.
# ---------------------------------------------------------------------------------
mesh = smesh.Mesh(PARTITION, "maillage")
mesh.Quadrangle()

SEGMENTS = {}  # report: class -> {"segments": n, "edges": count, "length": L}
EDGE_CLASSES = []
for i, (low, high) in enumerate(INTERVALS):
    EDGE_CLASSES.append(
        (
            "vertical %g -> %g" % (low, high),
            high - low,
            segment_count(high - low, SIZE),
            [e for key, e in VERTICAL_EDGES.items() if key[2] == i],
        )
    )
EDGE_CLASSES.append(
    (
        "horizontal facet of a tube",
        CHORD,
        segment_count(CHORD, SIZE),
        list(HORIZONTAL_EDGES.values()),
    )
)
EDGE_CLASSES.append(
    (
        "horizontal sheet pile",
        AXES[1] - AXES[0] - 2.0 * RADIUS,
        SHEET["segments_largeur"],
        SHEET_HORIZONTAL_EDGES,
    )
)
EDGE_CLASSES.append(
    ("beam bay", AXES[1] - AXES[0], BEAM["segments_par_entraxe"], BEAM_EDGES)
)
EDGE_CLASSES.append(
    ("tie rod", ROD["longueur_des_coordonnees"], ROD["segments"], ROD_EDGES)
)
CLASSIFIED = 0
for label, length, count, shapes in EDGE_CLASSES:
    ids = geometry_ids(shapes, "EDGE")
    group = geometry_group("SEG " + label, ids, "EDGE")
    mesh.Segment(geom=group).NumberOfSegments(count)
    SEGMENTS[label] = {"segments": count, "edges": len(ids), "length": length}
    CLASSIFIED += len(ids)
ALL_EDGES = len(geompy.SubShapeAll(PARTITION, geompy.ShapeType["EDGE"]))
if CLASSIFIED != ALL_EDGES:
    raise RuntimeError(
        "%d edges classified, %d in the partition" % (CLASSIFIED, ALL_EDGES)
    )
log("segments imposed on %d edges: %s" % (CLASSIFIED, json.dumps(SEGMENTS)))

if not mesh.Compute():
    raise RuntimeError("Compute() failed")
log("mesh computed: %d nodes" % mesh.NbNodes())

# ---------------------------------------------------------------------------------
# Groups (convention validated by MM, v3): created on the geometry, transferred to
# the mesh. Cell groups first.
# ---------------------------------------------------------------------------------
CELL_IDS = {}
MESH_GROUPS = []


def cell_group(name, ids, kind):
    CELL_IDS[name] = set(ids)
    mesh.GroupOnGeom(
        grp=geometry_group(name, ids, kind),
        name=name,
        typ=SMESH.FACE if kind == "FACE" else SMESH.EDGE,
    )
    MESH_GROUPS.append(name)


def node_group(name, ids, kind):
    mesh.GroupOnGeom(grp=geometry_group(name, ids, kind), name=name, typ=SMESH.NODE)
    MESH_GROUPS.append(name)


# TUBE_xx, TUBES, PALP_xx, PALPS, ECRAN
for number in NUMBERS:
    cell_group(
        "TUBE_%02d" % number,
        geometry_ids([f for key, f in TUBE_FACES.items() if key[0] == number], "FACE"),
        "FACE",
    )
cell_group("TUBES", set().union(*[CELL_IDS["TUBE_%02d" % n] for n in NUMBERS]), "FACE")
for k in range(1, len(AXES)):
    cell_group(
        "PALP_%02d" % k,
        geometry_ids([f for key, f in SHEET_FACES.items() if key[0] == k], "FACE"),
        "FACE",
    )
cell_group(
    "PALPS",
    set().union(*[CELL_IDS["PALP_%02d" % k] for k in range(1, len(AXES))]),
    "FACE",
)
cell_group("ECRAN", CELL_IDS["TUBES"] | CELL_IDS["PALPS"], "FACE")

# Point 5 -- ECRAN_POUSSEE (decision 11): the facets of the tubes on the land side
# (Y >= 0) and the sheet piles; below the sheet piles only the tubes receive it.
cell_group(
    "ECRAN_POUSSEE",
    geometry_ids(
        [
            f
            for (number, j, _), f in TUBE_FACES.items()
            if in_window(j, PUSH["angle_centre_deg"], PUSH["demi_angle_deg"])
        ],
        "FACE",
    )
    | CELL_IDS["PALPS"],
    "FACE",
)
# POUTRE_COUR, TIRANT_xx, TIRANTS (points 3 and 2)
cell_group("POUTRE_COUR", geometry_ids(BEAM_EDGES, "EDGE"), "EDGE")
for number in NUMBERS:
    cell_group(
        "TIRANT_%02d" % number, geometry_ids([ROD_EDGES[number - 1]], "EDGE"), "EDGE"
    )
cell_group(
    "TIRANTS", set().union(*[CELL_IDS["TIRANT_%02d" % n] for n in NUMBERS]), "EDGE"
)

# Point 4 -- spring bands: every cell of the screen (or of the tubes alone) between
# two levels.
for name, band in BANDS.items():
    inside = [
        i
        for i, (low, high) in enumerate(INTERVALS)
        if low >= band["cote_bas"] - 1e-9 and high <= band["cote_haut"] + 1e-9
    ]
    shapes = [f for (n, j, i), f in TUBE_FACES.items() if i in inside]
    if band["avec_palplanches"]:
        sheet_positions = [
            p
            for p in range(len(SHEET_LEVELS) - 1)
            if SHEET["cotes"][p] >= band["cote_bas"] - 1e-9
            and SHEET["cotes"][p + 1] <= band["cote_haut"] + 1e-9
        ]
        shapes += [f for (k, p), f in SHEET_FACES.items() if p in sheet_positions]
    cell_group(name, geometry_ids(shapes, "FACE"), "FACE")

# Point 8 -- DEFENSE: mooring-fender imprint, basin side of the central tube, between
# the two imprint levels, within the half-angle on each side of the basin generatrix.
inside = [
    i
    for i, (low, high) in enumerate(INTERVALS)
    if low >= IMPRINT["cote_bas"] - 1e-9 and high <= IMPRINT["cote_haut"] + 1e-9
]
cell_group(
    "DEFENSE",
    geometry_ids(
        [
            f
            for (n, j, i), f in TUBE_FACES.items()
            if n == IMPRINT["tube"]
            and i in inside
            and in_window(j, IMPRINT["angle_centre_deg"], IMPRINT["demi_angle_deg"])
        ],
        "FACE",
    ),
    "FACE",
)

# Node groups: TETE_TUBE_xx (ring of nodes at the head level, on vertices),
# ANC_xx / ANCRAGES (anchor ends), BOLLARD (beam node above the central tube).
for number in NUMBERS:
    node_group(
        "TETE_TUBE_%02d" % number,
        geometry_ids(
            [
                v
                for (n, j, level_index), v in VERTICES.items()
                if n == number and level_index == len(LEVELS) - 1
            ],
            "VERTEX",
        ),
        "VERTEX",
    )
ANCHOR_IDS = {}
for number in NUMBERS:
    ANCHOR_IDS[number] = geometry_ids([ROD_ENDS[number - 1]], "VERTEX")
    node_group("ANC_%02d" % number, ANCHOR_IDS[number], "VERTEX")
node_group("ANCRAGES", set().union(*ANCHOR_IDS.values()), "VERTEX")
node_group(
    "BOLLARD", geometry_ids([BEAM_VERTICES[TUBE["central"] - 1]], "VERTEX"), "VERTEX"
)

# Point 7 -- SYM_G, SYM_D: every node of the plane X = x of a face of the cut. The
# tube cut through its axis contributes its two cut generatrices (interior nodes on
# the edges, end nodes on the vertices), the tie rod its anchor, the beam its end.
# A group holds one type of shape: an EDGE group and a VERTEX group, united.
for name, x in (("SYM_G", SYMMETRY["x_gauche"]), ("SYM_D", SYMMETRY["x_droite"])):
    number = [n for n in NUMBERS if abs(AXES[n - 1] - x) < 1e-9][0]
    j0, j1 = SECTORS[number - 1]
    cut_edges = [
        e for (n, j, i), e in VERTICAL_EDGES.items() if n == number and j in (j0, j1)
    ]
    cut_vertices = [
        v
        for (n, j, level_index), v in VERTICES.items()
        if n == number and j in (j0, j1)
    ] + [ROD_ENDS[number - 1], BEAM_VERTICES[number - 1]]
    on_edges = mesh.GroupOnGeom(
        grp=geometry_group(
            name + " edges",
            geometry_ids(cut_edges + [ROD_EDGES[number - 1]], "EDGE"),
            "EDGE",
        ),
        name=name + "_EDGES",
        typ=SMESH.NODE,
    )
    on_vertices = mesh.GroupOnGeom(
        grp=geometry_group(
            name + " vertices", geometry_ids(cut_vertices, "VERTEX"), "VERTEX"
        ),
        name=name + "_VERTICES",
        typ=SMESH.NODE,
    )
    mesh.UnionListOfGroups(groups=[on_edges, on_vertices], name=name)
    mesh.RemoveGroup(group=on_edges)
    mesh.RemoveGroup(group=on_vertices)
    MESH_GROUPS.append(name)

log("groups: %d" % len(MESH_GROUPS))
mesh.ExportMED(str(MED_PATH), auto_groups=False, overwrite=True)

meta = {
    "params_sha256": hashlib.sha256(RAW).hexdigest(),
    "segments": SEGMENTS,
    "groups": MESH_GROUPS,
    "nodes": mesh.NbNodes(),
    "faces": mesh.NbFaces(),
    "edges": mesh.NbEdges(),
}
MED_PATH.with_suffix(".meta.json").write_text(json.dumps(meta))
print("LOT27_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
