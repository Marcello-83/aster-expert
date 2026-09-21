"""Lot 26, geometry 2 -- faceted tube joined by two flat plates on its Y = 0 lines.

Reduction of the tube / sheet-pile junction of the quay. Run by
`aster-expert mesh run --params params.json lot26_tube_plaques.py` inside
Salome (Python 3.9). Arguments: parameters file, output MED name.

Rules of CLAUDE.md, "Scripts Salome": one single partition of the whole
geometry; groups created on the geometry then transferred to the mesh; no
coordinate written here (everything comes from the parameters file); the
fingerprint of the parameters written next to the MED (`<stem>.meta.json`).

Every facet of the tube and every plate is built one elevation interval at a
time, the elevations being the `cotes` of the parameters: the imposed
elevations are therefore lines of the partition.
"""

import hashlib
import json
import math
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

RADIUS = PARAMS["tube"]["rayon"]
FACETS = PARAMS["tube"]["facettes"]
WIDTH = PARAMS["plaques"]["largeur"]
LEVELS = PARAMS["cotes"]
CENTER_DEG = PARAMS["empreinte"]["angle_centre_deg"]
HALF_DEG = PARAMS["empreinte"]["demi_angle_deg"]
ANGLE_TOL_DEG = 1e-6


def clean(value):
    """Remove the rounding noise of cos/sin (an exact 0 stays an exact 0)."""
    return round(value, 12) + 0.0


def rectangle(corners):
    vertices = [geompy.MakeVertex(*corner) for corner in corners]
    wire = geompy.MakePolyline(vertices, True)
    return geompy.MakeFaceWires([wire], 1)


def ring_point(k, z):
    angle = 2.0 * math.pi * k / FACETS
    return (clean(RADIUS * math.cos(angle)), clean(RADIUS * math.sin(angle)), z)


def facet_angles_deg(k):
    return (360.0 * k / FACETS, 360.0 * (k + 1) / FACETS)


def in_window(k):
    """True when facet k lies inside [CENTER - HALF, CENTER + HALF] (degrees)."""
    low, high = CENTER_DEG - HALF_DEG, CENTER_DEG + HALF_DEG
    for angle in facet_angles_deg(k):
        shifted = (angle - low) % 360.0
        if shifted > (high - low) + ANGLE_TOL_DEG:
            return False
    return True


intervals = list(zip(LEVELS[:-1], LEVELS[1:]))  # noqa: B905 (Python 3.9)

tube_faces = []
imprint_faces = []
lock_edges = {"D": [], "G": []}
for k in range(FACETS):
    for z0, z1 in intervals:
        a0, a1 = ring_point(k, z0), ring_point(k + 1, z0)
        b0, b1 = ring_point(k, z1), ring_point(k + 1, z1)
        face = rectangle([a0, a1, b1, b0])
        tube_faces.append(face)
        if in_window(k):
            imprint_faces.append(face)
        if k == 0:
            lock_edges["D"].append(
                geompy.MakeEdge(*[geompy.MakeVertex(*p) for p in (a0, b0)])
            )
        if k == FACETS // 2:
            lock_edges["G"].append(
                geompy.MakeEdge(*[geompy.MakeVertex(*p) for p in (a0, b0)])
            )

plates = {"D": [], "G": []}
for z0, z1 in intervals:
    plates["D"].append(
        rectangle(
            [
                (RADIUS, 0.0, z0),
                (RADIUS + WIDTH, 0.0, z0),
                (RADIUS + WIDTH, 0.0, z1),
                (RADIUS, 0.0, z1),
            ]
        )
    )
    plates["G"].append(
        rectangle(
            [
                (-RADIUS - WIDTH, 0.0, z0),
                (-RADIUS, 0.0, z0),
                (-RADIUS, 0.0, z1),
                (-RADIUS - WIDTH, 0.0, z1),
            ]
        )
    )

# ASSEMBLY begin: one single partition of the whole geometry.
PARTITION = geompy.MakePartition(
    tube_faces + plates["D"] + plates["G"],
    [],
    [],
    [],
    geompy.ShapeType["FACE"],
    0,
    [],
    0,
)
# ASSEMBLY end


def geometry_group(name, shapes, kind):
    """Group of `PARTITION` gathering every sub-shape lying in `shapes`."""
    group = geompy.CreateGroup(PARTITION, geompy.ShapeType[kind], name)
    found = geompy.GetInPlace(PARTITION, geompy.MakeCompound(shapes))
    ids = set()
    for sub in geompy.SubShapeAll(found, geompy.ShapeType[kind]):
        ids.add(geompy.GetSubShapeID(PARTITION, sub))
    geompy.UnionIDs(group, sorted(ids))
    return group


GROUPS = [
    (geometry_group("TUBE", tube_faces, "FACE"), SMESH.FACE),
    (geometry_group("PLAQUE_D", plates["D"], "FACE"), SMESH.FACE),
    (geometry_group("PLAQUE_G", plates["G"], "FACE"), SMESH.FACE),
    (geometry_group("EMPREINTE", imprint_faces, "FACE"), SMESH.FACE),
    (geometry_group("SERRURE_D", lock_edges["D"], "EDGE"), SMESH.EDGE),
    (geometry_group("SERRURE_G", lock_edges["G"], "EDGE"), SMESH.EDGE),
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
