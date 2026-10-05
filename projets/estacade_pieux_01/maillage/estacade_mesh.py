# ruff: noqa: E501, C401, PTH123
"""Lot 47 -- mesh of the jetty ESTACADE-PIEUX-01 (slab, cap beams, piles).

Run by `aster-expert mesh run --params <params.json> estacade_mesh.py` inside
Salome (Python 3.9). Arguments: parameters file, output MED name. The parameters
come from `estacade_pieux_01.discretisation.JettyMesh.parameters`; nothing
numerical is written here.

Rules of CLAUDE.md, "Scripts Salome" (pattern PAT-008):

- one single partition of the whole geometry (`# ASSEMBLY begin/end`): the slab
  face cut by the lines X = X_i, Y = +-2.00 and Y = +-1.50, plus the pile edges,
  so that the pile heads, the cap beam nodes and the slab nodes are shared;
- groups created on the geometry (`CreateGroup`, `GetInPlace`, `UnionIDs`) then
  transferred to the mesh (`GroupOnGeom`), never picked by hand;
- every GEOM / SMESH call with more than three parameters passes them by name
  (`MakePartition`: `KeepNonlimitShapes` is the 8th argument, given by name, so
  that the pile edges, which are not faces, are kept);
- each edge receives the integer number of segments of the parameters file,
  imposed by a sub-mesh hypothesis on a group of edges of the same count;
- the fingerprint of the parameters and the segments imposed are written next to
  the MED (`<stem>.meta.json`); progress in `<stem>.progress.txt`.

Frame (point U1): X along the deck from the abutment, Y across from the axis, Z up
equal to the NGF level; the slab lies in the plane Z = z_dalle (mid-plane).
"""

import hashlib
import json
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
PROGRESS = MED_PATH.with_suffix(".progress.txt")
START = time.time()


def progress(text):
    with open(PROGRESS, "a", encoding="utf-8") as stream:
        stream.write("%8.1f s  %s\n" % (time.time() - START, text))


RAW = PARAMS_PATH.read_bytes()
PARAMS = json.loads(RAW)
Z = PARAMS["z_dalle"]
XC = PARAMS["x_coupes"]
YC = PARAMS["y_coupes"]
SEG_X = PARAMS["segments_x"]
SEG_Y = PARAMS["segments_y"]
LEVELS = PARAMS["cotes_pieu"]
progress("paramètres lus")


def vertex(x, y, z):
    return geompy.MakeVertex(x, y, z)


def edge(p, q):
    return geompy.MakeEdge(p, q)


def rectangle(x0, x1, y0, y1):
    wire = geompy.MakePolyline(
        thePoints=[
            vertex(x0, y0, Z),
            vertex(x1, y0, Z),
            vertex(x1, y1, Z),
            vertex(x0, y1, Z),
        ],
        theIsClosed=True,
    )
    return geompy.MakeFaceWires(theWires=[wire], isPlanarWanted=1)


SLAB = rectangle(XC[0], XC[-1], YC[0], YC[-1])
TOOLS = [edge(vertex(x, YC[0], Z), vertex(x, YC[-1], Z)) for x in XC[1:-1]]
TOOLS += [edge(vertex(XC[0], y, Z), vertex(XC[-1], y, Z)) for y in YC[1:-1]]

PILE_EDGES = {}
for pile in PARAMS["pieux"]:
    points = [vertex(pile["x"], pile["y"], z) for z in LEVELS]
    PILE_EDGES[pile["nom"]] = [
        (LEVELS[k], LEVELS[k + 1], edge(points[k], points[k + 1]))
        for k in range(len(LEVELS) - 1)
    ]
ALL_PILE_EDGES = [e for edges in PILE_EDGES.values() for (_, _, e) in edges]
progress("géométrie construite : %d arêtes de pieux" % len(ALL_PILE_EDGES))

# ASSEMBLY begin: one single partition of the whole geometry.
PARTITION = geompy.MakePartition(
    ListShapes=[SLAB] + ALL_PILE_EDGES,
    ListTools=TOOLS,
    ListKeepInside=[],
    ListRemoveInside=[],
    Limit=geompy.ShapeType["FACE"],
    RemoveWebs=0,
    ListMaterials=[],
    KeepNonlimitShapes=1,
)
# ASSEMBLY end
progress("partition faite")


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


mesh = smesh.Mesh(PARTITION, "estacade")
mesh.Quadrangle()

# Segments: every slab edge piece by its own interval, grouped by count.
BY_COUNT = {}
for k in range(len(XC) - 1):
    for y in YC:
        BY_COUNT.setdefault(SEG_X[k], []).append(
            edge(vertex(XC[k], y, Z), vertex(XC[k + 1], y, Z))
        )
for k in range(len(YC) - 1):
    for x in XC:
        BY_COUNT.setdefault(SEG_Y[k], []).append(
            edge(vertex(x, YC[k], Z), vertex(x, YC[k + 1], Z))
        )
SEGMENTS = {}
CLASSIFIED = set()
for count, shapes in sorted(BY_COUNT.items()):
    ids = geometry_ids(shapes, "EDGE")
    if ids & CLASSIFIED:
        raise RuntimeError("edges classified twice (count %d)" % count)
    CLASSIFIED |= ids
    mesh.Segment(geom=geometry_group("SEG %d" % count, ids, "EDGE")).NumberOfSegments(
        count
    )
    SEGMENTS["dalle %d" % count] = {"segments": count, "edges": len(ids)}
PILE_IDS = geometry_ids(ALL_PILE_EDGES, "EDGE")
if PILE_IDS & CLASSIFIED:
    raise RuntimeError("pile edges among the slab edges")
CLASSIFIED |= PILE_IDS
mesh.Segment(geom=geometry_group("SEG PIEUX", PILE_IDS, "EDGE")).NumberOfSegments(1)
SEGMENTS["pieux"] = {"segments": 1, "edges": len(PILE_IDS)}
ALL_EDGES = len(geompy.SubShapeAll(PARTITION, geompy.ShapeType["EDGE"]))
if len(CLASSIFIED) != ALL_EDGES:
    raise RuntimeError(
        "%d edges classified, %d in the partition" % (len(CLASSIFIED), ALL_EDGES)
    )
progress("hypothèses posées : %d arêtes" % ALL_EDGES)

if not mesh.Compute():
    raise RuntimeError("Compute() failed")
progress("maillage calculé : %d nœuds" % mesh.NbNodes())

MESH_GROUPS = []


def cell_group(name, shapes, kind):
    mesh.GroupOnGeom(
        grp=geometry_group(name, geometry_ids(shapes, kind), kind),
        name=name,
        typ=SMESH.FACE if kind == "FACE" else SMESH.EDGE,
    )
    MESH_GROUPS.append(name)


def node_group(name, shapes):
    mesh.GroupOnGeom(
        grp=geometry_group(name, geometry_ids(shapes, "VERTEX"), "VERTEX"),
        name=name,
        typ=SMESH.NODE,
    )
    MESH_GROUPS.append(name)


LANE = PARAMS["voie"]
cell_group("DALLE", [SLAB], "FACE")
cell_group("VOIE", [rectangle(XC[0], XC[-1], LANE[0], LANE[1])], "FACE")
cell_group(
    "TROTT",
    [
        rectangle(XC[0], XC[-1], YC[0], LANE[0]),
        rectangle(XC[0], XC[-1], LANE[1], YC[-1]),
    ],
    "FACE",
)
cell_group("RIVE_YM", [edge(vertex(XC[0], YC[0], Z), vertex(XC[-1], YC[0], Z))], "EDGE")
cell_group(
    "RIVE_YP", [edge(vertex(XC[0], YC[-1], Z), vertex(XC[-1], YC[-1], Z))], "EDGE"
)
CAPS = [edge(vertex(x, YC[0], Z), vertex(x, YC[-1], Z)) for x in PARAMS["x_files"]]
cell_group("CHEVETRES", CAPS, "EDGE")
for i, cap in enumerate(CAPS, start=1):
    cell_group("CHEV_%d" % i, [cap], "EDGE")
cell_group("PIEUX", ALL_PILE_EDGES, "EDGE")
progress("groupes de la dalle et des chevêtres")
for name, edges in PILE_EDGES.items():
    cell_group("PIEU_" + name, [e for (_, _, e) in edges], "EDGE")
for section in PARAMS["troncons"]:
    chosen = [
        e
        for edges in PILE_EDGES.values()
        for (top, bottom, e) in edges
        if section["bas"] - 1e-9 <= (top + bottom) / 2.0 <= section["haut"] + 1e-9
    ]
    cell_group(section["groupe"], chosen, "EDGE")
node_group("TETES", [vertex(p["x"], p["y"], LEVELS[0]) for p in PARAMS["pieux"]])
node_group("PIEDS", [vertex(p["x"], p["y"], LEVELS[-1]) for p in PARAMS["pieux"]])
node_group("COIN_ABOUT", [vertex(XC[0], YC[0], Z)])
for spring in PARAMS["ressorts"]:
    node_group(
        spring["groupe"],
        [
            vertex(p["x"], p["y"], spring["cote"])
            for p in PARAMS["pieux"]
            if p["famille"] == spring["famille"]
        ],
    )
progress("%d groupes" % len(MESH_GROUPS))

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
progress("MED écrit")
print("LOT47_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
