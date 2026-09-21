"""Lot 27 probe: signatures of the GEOM / SMESH functions used by `combiwall_mesh.py`.

Run headless (`aster-expert mesh run scripts/salome/lot27_sonde_signatures.py`);
prints one line per name, `inspect.signature` of the real objects of the installed
version, and fails if one of them does not exist. No name is taken from memory:
the ones below are those the mesh script calls, the probe says whether they exist.
"""

import inspect

import salome
import SMESH
from salome.geom import geomBuilder
from salome.smesh import smeshBuilder

salome.salome_init()
geompy = geomBuilder.New()
smesh = smeshBuilder.New()

GEOM_NAMES = [
    "MakeVertex", "MakeEdge", "MakeFaceWires", "MakePolyline", "MakeCompound",
    "MakePartition", "CreateGroup", "GetInPlace", "SubShapeAll",
    "GetSubShapeID", "UnionIDs", "GetObjectIDs",
]  # fmt: skip
MESH_NAMES = [
    "Segment", "Quadrangle", "Compute", "GroupOnGeom", "ExportMED",
    "NbNodes", "NbFaces", "NbEdges", "UnionListOfGroups", "RemoveGroup",
    "GetGroups",
]  # fmt: skip
for name in GEOM_NAMES:
    print("GEOM", name, inspect.signature(getattr(geompy, name)))
mesh_class = smeshBuilder.Mesh
for name in MESH_NAMES:
    print("SMESH Mesh", name, inspect.signature(getattr(mesh_class, name)))
print("SMESH smeshBuilder.Mesh", inspect.signature(mesh_class.__init__))
print("SMESH constants NODE, EDGE, FACE", SMESH.NODE, SMESH.EDGE, SMESH.FACE)
mesh = smesh.Mesh(geompy.MakeVertex(0, 0, 0), "sonde")
segment = mesh.Segment()
print("SMESH algo Segment ->", type(segment).__name__)
print("SMESH NumberOfSegments", inspect.signature(segment.NumberOfSegments))
print("SMESH Quadrangle ->", type(mesh.Quadrangle).__name__)
print("LOT27_PROBE_OK")
