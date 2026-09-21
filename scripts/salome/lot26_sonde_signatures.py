"""Lot 26 probe: signatures of the GEOM / SMESH functions used by the lot 26 scripts.

Run headless (`salome -t --shutdown-servers=1 lot26_sonde_signatures.py`); prints
one line per function, `inspect.signature` of the real objects of the installed
version, and fails if one of them does not exist.
"""

import inspect

import salome
from salome.geom import geomBuilder
from salome.smesh import smeshBuilder

salome.salome_init()
geompy = geomBuilder.New()
smesh = smeshBuilder.New()

GEOM_NAMES = [
    "MakeVertex", "MakeEdge", "MakePolyline", "MakeFaceWires", "MakeCompound",
    "MakePartition", "CreateGroup", "GetInPlace", "SubShapeAll",
    "GetSubShapeID", "UnionIDs",
]  # fmt: skip
MESH_NAMES = [
    "Segment", "Quadrangle", "Compute", "GroupOnGeom", "ExportMED",
    "NbNodes", "NbFaces", "NbEdges",
]  # fmt: skip
for name in GEOM_NAMES:
    print("GEOM", name, inspect.signature(getattr(geompy, name)))
mesh_class = smeshBuilder.Mesh
for name in MESH_NAMES:
    print("SMESH Mesh", name, inspect.signature(getattr(mesh_class, name)))
print("SMESH smeshBuilder.Mesh", inspect.signature(mesh_class.__init__))
mesh = smesh.Mesh(geompy.MakeVertex(0, 0, 0), "sonde")
segment = mesh.Segment()
print("SMESH algo Segment ->", type(segment).__name__)
print("SMESH LocalLength", inspect.signature(segment.LocalLength))
print("SMESH Quadrangle ->", type(mesh.Quadrangle).__name__)
print("LOT26_PROBE_OK")
