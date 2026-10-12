# ruff: noqa: E501, C401, PTH123, N816, E741, B905, B007 -- script Salomé (Python 3.9 : zip sans strict)
"""Maillage d'une travée de la panne PONTONS-ALU-01 (lot 50) -- script Salomé autonome.

Relancer (VM, Salomé-Méca en conteneur Singularity) :

    singularity exec ~/Desktop/salome_meca.sif salome -t --shutdown-servers=1 \
        maillage_pontons.py args:pontons.med

ou, par la chaîne de l'outil : `aster-expert projet pontons_alu_01 maillage`.
Produit `pontons.med` (et `pontons.meta.json`, `pontons.progress.txt`) à côté du
script, sans aucune dépendance au code d'AsterExpert. Seuls les paramètres ci-dessous
se modifient : la géométrie, les groupes et la discrétisation en découlent.

Repère : X le long du tablier, X = 0 à l'appui côté quai ; Y transversal ; Z = cote
NGF. Unités : m. Points de construction recalés sur la grille de 1 mm.
Règles (CLAUDE.md, « Scripts Salomé ») : une seule partition, groupes créés sur la
géométrie puis transférés au maillage, arguments nommés, nombre de segments imposé
par arête.
"""

import json
import math
import sys
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# PARAMETRES begin -------------------------------------------------------------------
L = 6.25  # m, portée : têtes de poteaux à X = L (P1)
B = 1.50  # m, entraxe des poutres principales (P2)
X_MONTANTS = (
    0.0,
    0.75,
    2.25,
    3.75,
    5.25,
    6.25,
)  # m, montants (D2 ; X = L : montant d'extrémité, P3)
DIAGONALES = (
    (0.0, 0.75),
    (0.75, 2.25),
    (2.25, 3.75),
    (3.75, 5.25),
    (5.25, 6.25),
)  # m, X en Y = +B/2 puis X en Y = -B/2 (D2)
Y_PANNES = (0.56, 0.19, -0.18, -0.55)  # m, pannes secondaires (D2)
X_AMARRAGE = (1.60, 4.60)  # m, amarrage sur les poutres principales (P13)
X_ACCOSTAGE = (1.63, 3.63)  # m, début et fin de l'accostage (P13)
Z_PLAN_MOYEN = 1.3575  # m NGF, plan moyen poutres, montants, diagonales (P21)
EXC_PANNES = 0.10  # m, axe des pannes au-dessus du plan moyen (P7)
Y_SUPPORTS = (-0.75, 0.0, 0.75)  # m, profilés supports à X = L (P3, D2)
Z_SUPPORT_BAS = 1.09  # m NGF, pied des profilés supports, dessus du chevêtre (P3, P17)
Z_SUPPORT_HAUT = (
    1.24  # m NGF, tête des profilés supports, dessous du tablier (P17, P21)
)
Y_CHEVETRE = (-1.00, 1.00)  # m, extrémités du chevêtre (P3)
Z_CHEVETRE = 0.89  # m NGF, axe du chevêtre (D2)
Y_POTEAUX = (-0.75, 0.75)  # m, axes des poteaux (P2, D2)
D_POTEAUX = (
    0.50  # m, diamètre des poteaux (P20, D3) : nus du chevêtre à Y = ±D/2 des axes
)
Z_POTEAU_TETE = 0.69  # m NGF, tête des poteaux, dessous du chevêtre (P1, D2)
Z_POTEAU_PIED = -0.63  # m NGF, pied des poteaux, dessus de la semelle (P1, P19)
Z_SEMELLE = -0.755  # m NGF, plan moyen de la semelle (D2)
X_SEMELLE = (L - 0.50, L + 0.76)  # m, demi-semelle (P19, D2)
Y_SEMELLE = (-1.45, 1.45)  # m (P19, D2)
TAILLE = 0.25  # m, longueur maximale d'un élément (consigne du lot 50)
N_MIN = 4  # nombre minimal d'éléments par barre (consigne du lot 50)
# PARAMETRES end ---------------------------------------------------------------------


def grille(v):
    """Coordonnée recalée sur la grille de 1 mm (arrondi au plus proche, demi vers le haut)."""
    return float(Decimal(repr(v)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def point(x, y, z):
    return (grille(x), grille(y), grille(z))


def segments(longueur):
    return max(1, int(math.ceil(longueur / TAILLE - 1e-9)))


def longueur(p, q):
    return math.dist(p, q)


def barre(points):
    """Tronçons d'une barre continue passant par `points`, avec leur nombre de
    segments : au plus TAILLE, et au moins N_MIN éléments sur la barre."""
    morceaux = [
        [p, q, segments(longueur(p, q))] for p, q in zip(points, points[1:]) if p != q
    ]
    while sum(m[2] for m in morceaux) < N_MIN:
        plus_long = max(morceaux, key=lambda m: longueur(m[0], m[1]) / m[2])
        plus_long[2] += 1
    return [tuple(m) for m in morceaux]


# TABLIER ----------------------------------------------------------------------------
ZP = grille(Z_PLAN_MOYEN)
ZS = grille(Z_PLAN_MOYEN + EXC_PANNES)
YM, YP = -B / 2.0, B / 2.0


def x_diagonale(d, y):
    """Abscisse de la diagonale d = (x en +B/2, x en -B/2) à l'ordonnée y."""
    return d[0] + (YP - y) / B * (d[1] - d[0])


# Croisements des pannes avec les montants et les diagonales (P7) : par panne, la liste
# des abscisses ; un nœud de panne et le nœud du dessous par croisement.
CROISEMENTS = {}
for yp in Y_PANNES:
    xs = set(grille(x) for x in X_MONTANTS)
    xs |= set(grille(x_diagonale(d, yp)) for d in DIAGONALES)
    CROISEMENTS[yp] = sorted(xs)

X_PP = sorted(
    set(grille(x) for x in X_MONTANTS)
    | set(grille(x) for d in DIAGONALES for x in d)
    | set(grille(x) for x in X_AMARRAGE + X_ACCOSTAGE)
    | {0.0, grille(L)}
)
POUTRES = {
    "PP_YM": barre([point(x, YM, ZP) for x in X_PP]),
    "PP_YP": barre([point(x, YP, ZP) for x in X_PP]),
}
MONTANTS = {}
for i, xm in enumerate(X_MONTANTS, start=1):
    ys = {YM, YP} | set(y for y in Y_PANNES if YM < y < YP)
    if abs(xm - L) < 1e-9:
        ys |= set(Y_SUPPORTS)  # montant d'extrémité : nœuds au droit des supports (P3)
    ys = sorted(ys)
    MONTANTS["MONT_%d" % i] = barre([point(xm, y, ZP) for y in ys])
DIAGS = {}
for i, d in enumerate(DIAGONALES, start=1):
    ys = sorted({YM, YP} | set(y for y in Y_PANNES if YM < y < YP), reverse=True)
    DIAGS["DIAG_%d" % i] = barre([point(x_diagonale(d, y), y, ZP) for y in ys])
PANNES = {}
for i, yp in enumerate(Y_PANNES, start=1):
    PANNES["PANNE_%d" % i] = barre([point(x, yp, ZS) for x in CROISEMENTS[yp]])
# Liaisons rigides panne / montant ou diagonale (P7) : nœud de panne, nœud du dessous.
LIENS = [
    (point(x, yp, ZS), point(x, yp, ZP)) for yp in Y_PANNES for x in CROISEMENTS[yp]
]

# SUPPORTS ---------------------------------------------------------------------------
SUPPORTS = {}
for i, ys in enumerate(Y_SUPPORTS, start=1):
    SUPPORTS["SUP_%d" % i] = barre(
        [point(L, ys, Z_SUPPORT_BAS), point(L, ys, Z_SUPPORT_HAUT)]
    )
# Tête de profilé support -> nœud du tablier au-dessus (liaison rigide, soudure P18).
LIENS += [(point(L, ys, Z_SUPPORT_HAUT), point(L, ys, ZP)) for ys in Y_SUPPORTS]

# CHEVETRE ---------------------------------------------------------------------------
Y_CH = sorted(
    set(grille(y) for y in Y_CHEVETRE + Y_SUPPORTS + Y_POTEAUX)
    | set(grille(y + s * D_POTEAUX / 2.0) for y in Y_POTEAUX for s in (-1, 1))
)
Y_CH = [y for y in Y_CH if Y_CHEVETRE[0] - 1e-9 <= y <= Y_CHEVETRE[1] + 1e-9]
CHEVETRE = {"CHEVETRE": barre([point(L, y, Z_CHEVETRE) for y in Y_CH])}
# Pied de profilé support -> chevêtre : articulation (P18), écrite dans le .comm.
ROTULES = [(point(L, ys, Z_SUPPORT_BAS), point(L, ys, Z_CHEVETRE)) for ys in Y_SUPPORTS]

# POTEAUX ----------------------------------------------------------------------------
POTEAUX = {}
for i, yc in enumerate(Y_POTEAUX, start=1):
    POTEAUX["POT_%d" % i] = barre(
        [point(L, yc, Z_POTEAU_PIED), point(L, yc, Z_POTEAU_TETE)]
    )
# Tête de poteau -> axe du chevêtre ; pied de poteau -> plan moyen de la semelle.
LIENS += [(point(L, yc, Z_POTEAU_TETE), point(L, yc, Z_CHEVETRE)) for yc in Y_POTEAUX]
LIENS += [(point(L, yc, Z_POTEAU_PIED), point(L, yc, Z_SEMELLE)) for yc in Y_POTEAUX]

# SEMELLE ----------------------------------------------------------------------------
XS_SEM = sorted(set(grille(x) for x in X_SEMELLE) | {grille(L)})
YS_SEM = sorted(set(grille(y) for y in Y_SEMELLE + Y_POTEAUX))
ZF = grille(Z_SEMELLE)

import salome  # noqa: E402
import SMESH  # noqa: E402
from salome.geom import geomBuilder  # noqa: E402
from salome.smesh import smeshBuilder  # noqa: E402

salome.salome_init()
geompy = geomBuilder.New()
smesh = smeshBuilder.New()

BASE = Path(sys.argv[0]).resolve().parent
MED_PATH = BASE / (sys.argv[1] if sys.argv[1:] else "pontons.med")
PROGRESS = MED_PATH.with_suffix(".progress.txt")
START = time.time()


def progress(text):
    with open(PROGRESS, "a", encoding="utf-8") as stream:
        stream.write("%8.1f s  %s\n" % (time.time() - START, text))


def vertex(p):
    return geompy.MakeVertex(theX=p[0], theY=p[1], theZ=p[2])


def edge(p, q):
    return geompy.MakeEdge(thePnt1=vertex(p), thePnt2=vertex(q))


def rectangle(x0, x1, y0, y1):
    wire = geompy.MakePolyline(
        thePoints=[
            vertex((x0, y0, ZF)),
            vertex((x1, y0, ZF)),
            vertex((x1, y1, ZF)),
            vertex((x0, y1, ZF)),
        ],
        theIsClosed=True,
    )
    return geompy.MakeFaceWires(theWires=[wire], isPlanarWanted=1)


BARRES = {}
for famille in (POUTRES, MONTANTS, DIAGS, PANNES, SUPPORTS, CHEVETRE, POTEAUX):
    for nom, morceaux in famille.items():
        BARRES[nom] = [(p, q, n, edge(p, q)) for (p, q, n) in morceaux]
SEMELLE = rectangle(XS_SEM[0], XS_SEM[-1], YS_SEM[0], YS_SEM[-1])
COUPES = [edge((x, YS_SEM[0], ZF), (x, YS_SEM[-1], ZF)) for x in XS_SEM[1:-1]]
COUPES += [edge((XS_SEM[0], y, ZF), (XS_SEM[-1], y, ZF)) for y in YS_SEM[1:-1]]
TOUTES = [e for morceaux in BARRES.values() for (_, _, _, e) in morceaux]
progress("géométrie construite : %d arêtes de barres" % len(TOUTES))

# ASSEMBLY begin: une seule partition de toute la géométrie.
PARTITION = geompy.MakePartition(
    ListShapes=[SEMELLE] + TOUTES,
    ListTools=COUPES,
    ListKeepInside=[],
    ListRemoveInside=[],
    Limit=geompy.ShapeType["FACE"],
    RemoveWebs=0,
    ListMaterials=[],
    KeepNonlimitShapes=1,
)
# ASSEMBLY end
progress("partition faite")


def ids(shapes, kind):
    found = geompy.GetInPlace(
        theShapeWhere=PARTITION, theShapeWhat=geompy.MakeCompound(theShapes=shapes)
    )
    return set(
        geompy.GetSubShapeID(PARTITION, s)
        for s in geompy.SubShapeAll(found, geompy.ShapeType[kind])
    )


def groupe_geom(nom, identifiants, kind):
    g = geompy.CreateGroup(
        theMainShape=PARTITION, theShapeType=geompy.ShapeType[kind], theName=nom
    )
    geompy.UnionIDs(theGroup=g, theSubShapes=sorted(identifiants))
    return g


mesh = smesh.Mesh(PARTITION, "pontons")
mesh.Quadrangle()

# DISCRETISATION : nombre de segments imposé par arête, regroupé par nombre.
PAR_NOMBRE = {}
for morceaux in BARRES.values():
    for p, q, n, e in morceaux:
        PAR_NOMBRE.setdefault(n, []).append(e)
for k in range(len(XS_SEM) - 1):
    n = segments(XS_SEM[k + 1] - XS_SEM[k])
    for y in YS_SEM:
        PAR_NOMBRE.setdefault(n, []).append(
            edge((XS_SEM[k], y, ZF), (XS_SEM[k + 1], y, ZF))
        )
for k in range(len(YS_SEM) - 1):
    n = segments(YS_SEM[k + 1] - YS_SEM[k])
    for x in XS_SEM:
        PAR_NOMBRE.setdefault(n, []).append(
            edge((x, YS_SEM[k], ZF), (x, YS_SEM[k + 1], ZF))
        )
CLASSEES = set()
SEGMENTS = {}
for n, aretes in sorted(PAR_NOMBRE.items()):
    identifiants = ids(aretes, "EDGE")
    if identifiants & CLASSEES:
        raise RuntimeError("arêtes classées deux fois (%d segments)" % n)
    CLASSEES |= identifiants
    mesh.Segment(geom=groupe_geom("SEG %d" % n, identifiants, "EDGE")).NumberOfSegments(
        n
    )
    SEGMENTS[str(n)] = len(identifiants)
TOTAL = len(geompy.SubShapeAll(PARTITION, geompy.ShapeType["EDGE"]))
if len(CLASSEES) != TOTAL:
    raise RuntimeError("%d arêtes classées sur %d" % (len(CLASSEES), TOTAL))
if not mesh.Compute():
    raise RuntimeError("Compute() a échoué")
progress("maillage calculé : %d nœuds" % mesh.NbNodes())

# GROUPES ----------------------------------------------------------------------------
GROUPES = []


def groupe_mailles(nom, aretes, kind="EDGE"):
    typ = SMESH.FACE if kind == "FACE" else SMESH.EDGE
    mesh.GroupOnGeom(grp=groupe_geom(nom, ids(aretes, kind), kind), name=nom, typ=typ)
    GROUPES.append(nom)


def groupe_noeuds(nom, points):
    mesh.GroupOnGeom(
        grp=groupe_geom(nom, ids([vertex(p) for p in points], "VERTEX"), "VERTEX"),
        name=nom,
        typ=SMESH.NODE,
    )
    GROUPES.append(nom)


def aretes(noms):
    return [e for nom in noms for (_, _, _, e) in BARRES[nom]]


for famille, noms in (
    ("POUTRES_PRINC", POUTRES),
    ("MONTANTS", MONTANTS),
    ("DIAGONALES", DIAGS),
    ("PANNES_SEC", PANNES),
    ("SUPPORTS", SUPPORTS),
    ("POTEAUX", POTEAUX),
):
    groupe_mailles(famille, aretes(noms))
    for nom in noms:
        groupe_mailles(nom, aretes([nom]))  # un groupe par élément (extrêmes)
groupe_mailles("CHEVETRE", aretes(CHEVETRE))
groupe_mailles("SEMELLE", [SEMELLE], "FACE")
# Accostage (P13) : éléments de chaque poutre principale entre X_ACCOSTAGE.
for nom, y in (("ACC_YM", YM), ("ACC_YP", YP)):
    groupe_mailles(
        nom, [edge(point(X_ACCOSTAGE[0], y, ZP), point(X_ACCOSTAGE[1], y, ZP))]
    )
groupe_noeuds("APP_QUAI", [point(0.0, YM, ZP), point(0.0, YP, ZP)])
groupe_noeuds("PIEDS_SUPPORTS", [point(L, ys, Z_SUPPORT_BAS) for ys in Y_SUPPORTS])
groupe_noeuds("TETES_POTEAUX", [point(L, yc, Z_POTEAU_TETE) for yc in Y_POTEAUX])
groupe_noeuds("PIEDS_POTEAUX", [point(L, yc, Z_SEMELLE) for yc in Y_POTEAUX])
for nom, y in (("AMAR_YM", YM), ("AMAR_YP", YP)):
    groupe_noeuds(nom, [point(x, y, ZP) for x in X_AMARRAGE])
for i, (haut, bas) in enumerate(LIENS, start=1):
    groupe_noeuds("LR_%02d" % i, [haut, bas])
for i, (support, chevetre) in enumerate(ROTULES, start=1):
    groupe_noeuds("ROT_S%d" % i, [support])
    groupe_noeuds("ROT_C%d" % i, [chevetre])
progress("%d groupes" % len(GROUPES))

mesh.ExportMED(str(MED_PATH), auto_groups=False, overwrite=True)
meta = {
    "segments": SEGMENTS,
    "groupes": GROUPES,
    "noeuds": mesh.NbNodes(),
    "quadrangles": mesh.NbFaces(),
    "segments_maillés": mesh.NbEdges(),
    "liens_rigides": len(LIENS),
}
MED_PATH.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False))
progress("MED écrit")
print("PONTONS_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
