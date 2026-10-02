# ruff: noqa: E501, C401, PTH123
"""Lot 43 -- mesh of the slab DALLE-APPUYEE-01 (section B of the arbitration).

Run by `aster-expert mesh run --params <params.json> dalle_mesh.py` inside Salome
(Python 3.9). Arguments: parameters file, output MED name. The parameters come from
`dalle_appuyee_01.discretisation.SlabMesh.parameters`; nothing numerical is written
here.

Rules of CLAUDE.md, "Scripts Salome" (pattern PAT-008):

- one single partition of the whole geometry (`# ASSEMBLY begin/end`): the slab cut
  by the lines x = L/2 and y = B/2, so that the centre is a vertex;
- groups created on the geometry (`CreateGroup`, `GetInPlace`, `UnionIDs`) then
  transferred to the mesh (`GroupOnGeom`), never picked by hand;
- every GEOM / SMESH call with more than three parameters passes them by name;
- each edge receives the integer number of segments of the parameters file, imposed
  by a sub-mesh hypothesis on a group of edges;
- the fingerprint of the parameters and the segments imposed are written next to the
  MED (`<stem>.meta.json`).

Frame (point 9): origin at corner A, X along the 6.00 m side, Y along the 4.00 m
side, Z up, slab in the plane z = 0.

Names and signatures of GEOM / SMESH: `data/examples/lot26_essais/
signatures_geom_smesh.txt` and the lot 27 probe, never from memory.
"""

import hashlib
import json
import sys
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

LX = PARAMS["longueur"]
LY = PARAMS["largeur"]
NX_HALF = PARAMS["segments_x_demi"]
NY_HALF = PARAMS["segments_y_demi"]

V_A = geompy.MakeVertex(0.0, 0.0, 0.0)
V_B = geompy.MakeVertex(LX, 0.0, 0.0)
V_C = geompy.MakeVertex(LX, LY, 0.0)
V_D = geompy.MakeVertex(0.0, LY, 0.0)
V_CENTRE = geompy.MakeVertex(LX / 2.0, LY / 2.0, 0.0)

EDGE_Y0 = geompy.MakeEdge(V_A, V_B)
EDGE_X6 = geompy.MakeEdge(V_B, V_C)
EDGE_Y4 = geompy.MakeEdge(V_D, V_C)
EDGE_X0 = geompy.MakeEdge(V_A, V_D)
MID_X = geompy.MakeEdge(
    geompy.MakeVertex(LX / 2.0, 0.0, 0.0), geompy.MakeVertex(LX / 2.0, LY, 0.0)
)
MID_Y = geompy.MakeEdge(
    geompy.MakeVertex(0.0, LY / 2.0, 0.0), geompy.MakeVertex(LX, LY / 2.0, 0.0)
)

WIRE = geompy.MakePolyline(thePoints=[V_A, V_B, V_C, V_D], theIsClosed=True)
SLAB = geompy.MakeFaceWires(theWires=[WIRE], isPlanarWanted=1)

# ASSEMBLY begin: one single partition of the whole geometry.
PARTITION = geompy.MakePartition(
    ListShapes=[SLAB],
    ListTools=[MID_X, MID_Y],
    ListKeepInside=[],
    ListRemoveInside=[],
    Limit=geompy.ShapeType["FACE"],
    RemoveWebs=0,
    ListMaterials=[],
    KeepNonlimitShapes=0,
)
# ASSEMBLY end


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


mesh = smesh.Mesh(PARTITION, "dalle")
mesh.Quadrangle()

SEGMENTS = {}
EDGE_CLASSES = (
    ("along X (half length)", NX_HALF, [EDGE_Y0, EDGE_Y4, MID_Y]),
    ("along Y (half width)", NY_HALF, [EDGE_X0, EDGE_X6, MID_X]),
)
CLASSIFIED = 0
for label, count, shapes in EDGE_CLASSES:
    ids = geometry_ids(shapes, "EDGE")
    mesh.Segment(geom=geometry_group("SEG " + label, ids, "EDGE")).NumberOfSegments(
        count
    )
    SEGMENTS[label] = {"segments": count, "edges": len(ids)}
    CLASSIFIED += len(ids)
ALL_EDGES = len(geompy.SubShapeAll(PARTITION, geompy.ShapeType["EDGE"]))
if CLASSIFIED != ALL_EDGES:
    raise RuntimeError(
        "%d edges classified, %d in the partition" % (CLASSIFIED, ALL_EDGES)
    )

if not mesh.Compute():
    raise RuntimeError("Compute() failed")

MESH_GROUPS = []


def cell_group(name, shapes, kind):
    mesh.GroupOnGeom(
        grp=geometry_group(name, geometry_ids(shapes, kind), kind),
        name=name,
        typ=SMESH.FACE if kind == "FACE" else SMESH.EDGE,
    )
    MESH_GROUPS.append(name)


def node_group(name, shapes, kind):
    mesh.GroupOnGeom(
        grp=geometry_group(name, geometry_ids(shapes, kind), kind),
        name=name,
        typ=SMESH.NODE,
    )
    MESH_GROUPS.append(name)


cell_group("DALLE", [SLAB], "FACE")
cell_group("APPUI_X0", [EDGE_X0], "EDGE")
cell_group("APPUI_X6", [EDGE_X6], "EDGE")
cell_group("APPUI_Y0", [EDGE_Y0], "EDGE")
cell_group("APPUI_Y4", [EDGE_Y4], "EDGE")
node_group("APPUIS", [EDGE_X0, EDGE_X6, EDGE_Y0, EDGE_Y4], "EDGE")
node_group("P_A", [V_A], "VERTEX")
node_group("P_B", [V_B], "VERTEX")
node_group("CENTRE", [V_CENTRE], "VERTEX")

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
print("LOT43_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
