"""Lot 26, geometry 3 -- beam and inclined bar attached to a shell.

A beam whose end node is a node of the shell, and an inclined bar starting from
a node of the shell (a node created by the partition in the middle of a shell
edge). Run by `aster-expert mesh run --params params.json lot26_poutre_barre.py`
inside Salome (Python 3.9). Arguments: parameters file, output MED name.

Rules of CLAUDE.md, "Scripts Salome": one single partition of the whole
geometry; groups created on the geometry then transferred to the mesh; no
coordinate written here (everything comes from the parameters file); the
fingerprint of the parameters written next to the MED (`<stem>.meta.json`).
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


def segment(spec):
    start, end = spec["debut"], spec["fin"]
    return geompy.MakeEdge(geompy.MakeVertex(*start), geompy.MakeVertex(*end))


origin, u, v = (PARAMS["coque"][key] for key in ("origine", "u", "v"))
corners = [
    origin,
    [origin[i] + u[i] for i in range(3)],
    [origin[i] + u[i] + v[i] for i in range(3)],
    [origin[i] + v[i] for i in range(3)],
]
wire = geompy.MakePolyline([geompy.MakeVertex(*c) for c in corners], True)
coque = geompy.MakeFaceWires([wire], 1)
poutre = segment(PARAMS["poutre"])
barre = segment(PARAMS["barre"])

# ALTERED VARIANT (lot 26): the assembly below deliberately replaces the
# single partition; `aster-expert mesh check` must reject the result.
PARTITION = geompy.MakeCompound(
    [
        geompy.MakePartition(
            [coque, poutre], [], [], [], geompy.ShapeType["FACE"], 0, [], 1
        ),
        barre,
    ]
)


def geometry_group(name, shape, kind):
    """Group of `PARTITION` gathering every sub-shape lying in `shape`."""
    group = geompy.CreateGroup(PARTITION, geompy.ShapeType[kind], name)
    found = geompy.GetInPlace(PARTITION, shape)
    ids = set()
    for sub in geompy.SubShapeAll(found, geompy.ShapeType[kind]):
        ids.add(geompy.GetSubShapeID(PARTITION, sub))
    geompy.UnionIDs(group, sorted(ids))
    return group


GROUPS = [
    (geometry_group("COQUE", coque, "FACE"), SMESH.FACE),
    (geometry_group("POUTRE", poutre, "EDGE"), SMESH.EDGE),
    (geometry_group("BARRE", barre, "EDGE"), SMESH.EDGE),
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
