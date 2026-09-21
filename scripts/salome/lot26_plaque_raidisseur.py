"""Lot 26, geometry 1 -- plate with a stiffener (two plates, one shared edge).

Run by `aster-expert mesh run --params params.json lot26_plaque_raidisseur.py`
inside Salome (Python 3.9). Arguments: parameters file, output MED name.

Rules of CLAUDE.md, "Scripts Salome":
  * the whole geometry is one single partition, built before meshing;
  * groups are created on the geometry, then transferred to the mesh;
  * no coordinate is written here: everything comes from the parameters file;
  * the fingerprint of the parameters is written next to the MED
    (`<stem>.meta.json`).
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


def rectangle(name, corners):
    """Planar face through four corners given as (x, y, z)."""
    vertices = [geompy.MakeVertex(*c) for c in corners]
    wire = geompy.MakePolyline(vertices, True)
    return geompy.MakeFaceWires([wire], 1, name)


def rectangle_corners(spec):
    """Corners of a rectangle given by its origin and two edge vectors."""
    o, u, v = spec["origine"], spec["u"], spec["v"]
    return [
        o,
        [o[i] + u[i] for i in range(3)],
        [o[i] + u[i] + v[i] for i in range(3)],
        [o[i] + v[i] for i in range(3)],
    ]


plaque = rectangle("PLAQUE", rectangle_corners(PARAMS["plaque"]))
raidisseur = rectangle("RAIDISSEUR", rectangle_corners(PARAMS["raidisseur"]))
arete_a, arete_b = PARAMS["arete_commune"]
arete = geompy.MakeEdge(geompy.MakeVertex(*arete_a), geompy.MakeVertex(*arete_b))

# ASSEMBLY begin: one single partition of the whole geometry.
PARTITION = geompy.MakePartition(
    [plaque, raidisseur], [], [], [], geompy.ShapeType["FACE"], 0, [], 0
)
# ASSEMBLY end


def geometry_group(name, shapes, kind):
    """Group of `PARTITION` gathering every sub-shape lying in `shapes`."""
    group = geompy.CreateGroup(PARTITION, geompy.ShapeType[kind], name)
    ids = set()
    for shape in shapes:
        found = geompy.GetInPlace(PARTITION, shape)
        for sub in geompy.SubShapeAll(found, geompy.ShapeType[kind]):
            ids.add(geompy.GetSubShapeID(PARTITION, sub))
    geompy.UnionIDs(group, sorted(ids))
    return group


GROUPS = [
    (geometry_group("PLAQUE", [plaque], "FACE"), SMESH.FACE),
    (geometry_group("RAIDISSEUR", [raidisseur], "FACE"), SMESH.FACE),
    (geometry_group("ARETE", [arete], "EDGE"), SMESH.EDGE),
]

mesh = smesh.Mesh(PARTITION, "maillage")
regular = mesh.Segment()
regular.LocalLength(PARAMS["taille"], 0, PARAMS["precision"])
mesh.Quadrangle()
if not mesh.Compute():
    raise RuntimeError("Compute() failed")
for group, kind in GROUPS:
    mesh.GroupOnGeom(group, group.GetName(), kind)

mesh.ExportMED(str(MED_PATH), auto_groups=False, overwrite=True)

meta = {"params_sha256": hashlib.sha256(RAW).hexdigest()}
MED_PATH.with_suffix(".meta.json").write_text(json.dumps(meta))
print("LOT26_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
