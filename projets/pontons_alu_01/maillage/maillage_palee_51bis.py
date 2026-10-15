# ruff: noqa: E501, C401, PTH123, N816, E741, B905, B007, PLR2004 -- script Salomé (Python 3.9 : zip sans strict)
"""Maillage d'une palée type et des trois travées de PONTONS-ALU-01 (lot 51 bis) --
script Salomé autonome.

Relancer (VM, Salomé-Méca en conteneur Singularity) :

    singularity exec ~/Desktop/salome_meca.sif salome -t --shutdown-servers=1 \
        maillage_palee_51bis.py args:params.json,palee.med

ou, par la chaîne de l'outil : `aster-expert projet pontons_alu_01 maillage`. Le fichier
de paramètres est facultatif (`args:palee.med` seul) : il ne peut changer que `H_ANNEAU`
(hauteur des chevêtres et longrines) et `H_PILES` (hauteur libre des piles, du dessus de
la semelle à la sous-face de l'anneau), variantes de la consigne du lot 51 bis, § 1.
Produit `palee.med`, `palee.meta.json` (empreinte SHA-256 du fichier de paramètres) et
`palee.progress.txt`, sans aucune dépendance au code d'AsterExpert. Seuls les paramètres
ci-dessous se modifient.

Repère : X le long du ponton depuis le quai, Y transversal, Z = cote NGF. Unités : m.
Points de construction recalés sur la grille de 1 mm. Lot 51 bis : tablier rehaussé de
0,50 m (P47), appuis articulés à axe (P44) sans profilé support ni néoprène : l'axe n'est
pas un nœud du maillage, il est écrit dans le .comm par des relations entre les nœuds
d'extrémité des poutres principales (groupes AX_<appui>_<rive>_1 et _2) et le nœud du
chevêtre sous l'appui (AX_<appui>_<rive>_K). Deux nœuds reliés sont toujours distincts :
la petite travée et les longrines s'arrêtent à JEU (1 mm) du nœud auquel elles sont
liées. Règles (CLAUDE.md, « Scripts Salomé ») : une seule partition, groupes créés sur la
géométrie puis transférés au maillage, arguments nommés, nombre de segments imposé par
arête.
"""

import hashlib
import json
import math
import sys
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# PARAMETRES begin -------------------------------------------------------------------
L = 6.25  # m, portée des grandes travées T1 et T2 (P35)
X_PALEE = (6.25, 7.77)  # m, axes des chevêtres C1 et C2 (P48 : entraxes du lot 51)
JEU = 0.001  # m, jeu de modélisation aux éclissages et aux bouts des longrines
B = 1.86  # m, entraxe des poutres principales, en rive du tablier (P24)
LARGEUR_TABLIER = 2.00  # m, largeur chargée (P35)
X_MONTANTS = (
    0.0,
    0.75,
    2.25,
    3.75,
    5.25,
    6.25,
)  # m, montants d'une grande travée, depuis son origine
DIAGONALES = (
    (0.0, 0.75),
    (0.75, 2.25),
    (2.25, 3.75),
    (3.75, 5.25),
    (5.25, 6.25),
)  # m, X en Y = +B/2 puis X en Y = -B/2, depuis l'origine de la travée
Y_PANNES = (0.56, 0.19, -0.18, -0.55)  # m, pannes secondaires (D2)
X_TAQUETS = (1.60, 4.60)  # m, taquets d'une grande travée, depuis son origine (AVP)
NOMS_ZONES = (
    "QU",
    "MI1",
    "CH1",
    "PT",
    "PA2",
)  # zones d'accostage (consigne du lot 51, § 3)
ZONES_ACCOSTAGE = (
    (0.0, 1.0),
    (2.625, 3.625),
    (5.25, 6.25),
    (6.51, 7.51),
    (7.77, 8.77),
)  # m, X début et X fin de chaque zone
REHAUSSE = 0.50  # m, rehausse de toutes les cotes aluminium du lot 51 (P47)
Z_PLAN_MOYEN = (
    1.3575 + REHAUSSE
)  # m NGF, plan moyen poutres, montants, diagonales (P21, P47)
EXC_PANNES = 0.10  # m, axe des pannes au-dessus du plan moyen (P7)
H_POUTRES = 0.20  # m, hauteur des poutres principales (tube 200 x 200, P36) : sous-face à H/2 sous le plan moyen
DESCENTE_AXE = 0.17  # m, axe d'appui sous la sous-face des poutres principales (P47)
H_CHAPE = 0.10  # m, dessus du chevêtre sous l'axe d'appui (P47)
Y_CHEVETRE = (-1.05, 1.05)  # m, extrémités des chevêtres (P24, P48)
Y_APPUIS = (-0.93, 0.93)  # m, appuis à axe sous les poutres principales (P44)
Y_PILES = (-0.75, 0.75)  # m, axes des piles (P48 : ceux du lot 51)
D_PILES = 0.50  # m, diamètre des piles : nus à ±D/2 des axes
H_ANNEAU = 0.80  # m, hauteur des chevêtres et longrines (P48 ; 0,40 ou 0,80)
H_PILES = 1.30  # m, hauteur libre des piles, dessus de la semelle -> sous-face de l'anneau (consigne § 1)
EP_SEMELLE = 0.20  # m, épaisseur de la semelle (P48, diagnostic Sixense)
X_SEMELLE = (5.71, 8.31)  # m, semelle 2,60 m centrée sur les piles (X = 7,01, P48)
Y_SEMELLE = (-1.30, 1.30)  # m, semelle 2,60 m (P48)
TAILLE = 0.25  # m, longueur maximale d'un élément
N_MIN = 4  # nombre minimal d'éléments par barre
# PARAMETRES end ---------------------------------------------------------------------

BASE = Path(sys.argv[0]).resolve().parent
ARGS = sys.argv[1:]
PARAMS_PATH = BASE / ARGS[0] if len(ARGS) == 2 else None
MED_PATH = BASE / (ARGS[-1] if ARGS else "palee.med")
PARAMS_SHA = None
if PARAMS_PATH is not None:
    raw = PARAMS_PATH.read_bytes()
    PARAMS_SHA = hashlib.sha256(raw).hexdigest()
    for cle, valeur in json.loads(raw.decode("utf-8")).items():
        if cle == "H_PILES":
            H_PILES = float(valeur)
        elif cle == "H_ANNEAU":
            H_ANNEAU = float(valeur)
        else:
            raise RuntimeError("paramètre %s non modifiable par une variante" % cle)


def grille(v):
    """Coordonnée recalée sur la grille de 1 mm (arrondi au plus proche, demi vers le
    haut), après suppression du bruit binaire (arrondi à 1e-9)."""
    return (
        float(
            Decimal(repr(round(v, 9))).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
        )
        + 0.0
    )


def point(x, y, z):
    return (grille(x), grille(y), grille(z))


def segments(longueur):
    return max(1, int(math.ceil(longueur / TAILLE - 1e-9)))


def barre(points, n_min=N_MIN):
    """Tronçons d'une barre continue passant par `points` avec leur nombre de segments :
    au plus TAILLE, au moins n_min éléments sur la barre."""
    morceaux = [
        [p, q, segments(math.dist(p, q))] for p, q in zip(points, points[1:]) if p != q
    ]
    while sum(m[2] for m in morceaux) < n_min:
        plus_long = max(morceaux, key=lambda m: math.dist(m[0], m[1]) / m[2])
        plus_long[2] += 1
    return [tuple(m) for m in morceaux]


# TOPOLOGIE ---------------------------------------------------------------------------
DEMI = B / 2.0
ZP = grille(Z_PLAN_MOYEN)
ZS = grille(Z_PLAN_MOYEN + EXC_PANNES)
# Cotes déduites (P47) : axe d'appui DESCENTE_AXE sous la sous-face des poutres
# principales, dessus du chevêtre H_CHAPE sous l'axe, anneau et piles sous le chevêtre.
Z_AXE = grille(ZP - H_POUTRES / 2.0 - DESCENTE_AXE)
Z_DESSUS_CHEVETRE = grille(Z_AXE - H_CHAPE)
XC1, XC2 = grille(X_PALEE[0]), grille(X_PALEE[1])
TRAVEES = {
    "T1": (0.0, grille(L)),
    "PT": (grille(X_PALEE[0] + JEU), grille(X_PALEE[1] - JEU)),
    "T2": (XC2, grille(X_PALEE[1] + L)),
}
COTES = (("YM", -1.0), ("YP", 1.0))
INTERIEURES = [y for y in Y_PANNES if -DEMI < y < DEMI]
BARRES = {}  # nom -> (famille, morceaux)
LIENS = {}  # nom -> (point A, point B)
GROUPES_ZONES = {}  # nom -> (barre, x début, x fin)
TAQUETS = []
NOEUDS_SEULS = {}  # groupes d'un nœud hors liaisons (oreilles et chevêtres des appuis à axe)


def ajouter_barre(nom, famille, points, n_min=N_MIN):
    BARRES[nom] = (famille, barre(points, n_min))


def lien(nom, a, b):
    if a == b:
        raise RuntimeError("liaison %s : nœuds confondus" % nom)
    LIENS[nom] = (a, b)


def x_diagonale(d, y):
    return d[0] + (DEMI - y) / B * (d[1] - d[0])


for travee in ("T1", "PT", "T2"):
    x0, x1 = TRAVEES[travee]
    if travee == "PT":
        montants = [x0, x1]
        diagonales = [(x0, x1)]
        taquets = []
    else:
        montants = [grille(x0 + x) for x in X_MONTANTS]
        diagonales = [(grille(x0 + a), grille(x0 + c)) for a, c in DIAGONALES]
        taquets = [grille(x0 + x) for x in X_TAQUETS]
        TAQUETS.extend(taquets)
    zones = [
        (n, grille(z[0]), grille(z[1]))
        for n, z in zip(NOMS_ZONES, ZONES_ACCOSTAGE)
        if x0 <= z[0] and z[1] <= x1 + 1e-9
    ]
    xs_pp = sorted(
        set(montants)
        | set(x for d in diagonales for x in d)
        | set(taquets)
        | set(x for _, a, c in zones for x in (a, c))
        | {x0, x1}
    )
    for cote, signe in COTES:
        nom = "PP_%s_%s" % (travee, cote)
        ajouter_barre(nom, "POUTRES_PRINC", [point(x, signe * DEMI, ZP) for x in xs_pp])
        for n, a, c in zones:
            GROUPES_ZONES["ACC_%s_%s" % (n, cote)] = (nom, a, c, signe * DEMI)
    for i, xm in enumerate(montants, start=1):
        ys = sorted(set([-DEMI, DEMI] + INTERIEURES))
        ajouter_barre(
            "MONT_%s_%d" % (travee, i), "MONTANTS", [point(xm, y, ZP) for y in ys]
        )
    for i, d in enumerate(diagonales, start=1):
        ys = sorted(set([-DEMI, DEMI] + INTERIEURES), reverse=True)
        ajouter_barre(
            "DIAG_%s_%d" % (travee, i),
            "DIAGONALES",
            [point(x_diagonale(d, y), y, ZP) for y in ys],
        )
    for i, yp in enumerate(Y_PANNES, start=1):
        xs = sorted(set(montants) | set(grille(x_diagonale(d, yp)) for d in diagonales))
        ajouter_barre(
            "PANNE_%s_%d" % (travee, i), "PANNES_SEC", [point(x, yp, ZS) for x in xs]
        )
        for k, x in enumerate(xs, start=1):
            lien("LR_%s_%d_%02d" % (travee, i, k), point(x, yp, ZS), point(x, yp, ZP))

# Appuis à axe (P44) : l'axe n'est pas maillé ; groupes d'un nœud pour les extrémités
# des poutres principales qui s'y rejoignent (oreille 1 : grande travée, oreille 2 :
# petite travée) et pour le nœud du chevêtre sous l'appui. A3 (X = 14,02) : une oreille,
# support fixe.
ZA = grille(Z_DESSUS_CHEVETRE - H_ANNEAU / 2.0)
APPUIS = {
    "A1": (XC1, [TRAVEES["T1"][1], TRAVEES["PT"][0]], ZA),
    "A2": (XC2, [TRAVEES["T2"][0], TRAVEES["PT"][1]], ZA),
    "A3": (TRAVEES["T2"][1], [TRAVEES["T2"][1]], None),
}
for nom, (x, oreilles, z_chevetre) in APPUIS.items():
    for cote, signe in COTES:
        y = signe * DEMI
        for k, x_oreille in enumerate(oreilles, start=1):
            NOEUDS_SEULS["AX_%s_%s_%d" % (nom, cote, k)] = point(x_oreille, y, ZP)
        if z_chevetre is not None:
            NOEUDS_SEULS["AX_%s_%s_K" % (nom, cote)] = point(x, y, z_chevetre)

# Anneau (P40, P48), piles et semelle (P48).
Y_CH = sorted(
    set(grille(y) for y in Y_CHEVETRE + Y_APPUIS + Y_PILES + (0.0,))
    | set(grille(y + s * D_PILES / 2.0) for y in Y_PILES for s in (-1, 1))
)
Y_CH = [y for y in Y_CH if Y_CHEVETRE[0] - 1e-9 <= y <= Y_CHEVETRE[1] + 1e-9]
for chevetre, x in (("C1", XC1), ("C2", XC2)):
    ajouter_barre("CHEV_%s" % chevetre, "CHEVETRES", [point(x, y, ZA) for y in Y_CH])
XL = sorted(
    {
        TRAVEES["PT"][0],
        TRAVEES["PT"][1],
        grille(XC1 + D_PILES / 2.0),
        grille(XC2 - D_PILES / 2.0),
        grille((XC1 + XC2) / 2.0),
    }
)
Z_TETE = grille(Z_DESSUS_CHEVETRE - H_ANNEAU)
Z_PIED = grille(Z_TETE - H_PILES)
ZF = grille(Z_PIED - EP_SEMELLE / 2.0)
for (cote, _), y in zip(COTES, Y_PILES):
    ajouter_barre("LONG_%s" % cote, "LONGRINES", [point(x, y, ZA) for x in XL])
for chevetre, x, x_longrine in (("C1", XC1, XL[0]), ("C2", XC2, XL[-1])):
    for (cote, _), y in zip(COTES, Y_PILES):
        ajouter_barre(
            "PILE_%s_%s" % (chevetre, cote),
            "PILES",
            [point(x, y, Z_PIED), point(x, y, Z_TETE)],
        )
        lien("TP_%s_%s" % (chevetre, cote), point(x, y, Z_TETE), point(x, y, ZA))
        lien("LG_%s_%s" % (chevetre, cote), point(x_longrine, y, ZA), point(x, y, ZA))
        lien("PS_%s_%s" % (chevetre, cote), point(x, y, Z_PIED), point(x, y, ZF))
XS_SEM = sorted(set(grille(x) for x in X_SEMELLE + (XC1, XC2)))
YS_SEM = sorted(set(grille(y) for y in Y_SEMELLE + Y_PILES))

import salome  # noqa: E402
import SMESH  # noqa: E402
from salome.geom import geomBuilder  # noqa: E402
from salome.smesh import smeshBuilder  # noqa: E402

salome.salome_init()
geompy = geomBuilder.New()
smesh = smeshBuilder.New()
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


ARETES = {
    nom: [(p, q, n, edge(p, q)) for (p, q, n) in morceaux]
    for nom, (_, morceaux) in BARRES.items()
}
SEMELLE = rectangle(XS_SEM[0], XS_SEM[-1], YS_SEM[0], YS_SEM[-1])
COUPES = [edge((x, YS_SEM[0], ZF), (x, YS_SEM[-1], ZF)) for x in XS_SEM[1:-1]]
COUPES += [edge((XS_SEM[0], y, ZF), (XS_SEM[-1], y, ZF)) for y in YS_SEM[1:-1]]
TOUTES = [e for morceaux in ARETES.values() for (_, _, _, e) in morceaux]
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


mesh = smesh.Mesh(PARTITION, "palee")
mesh.Quadrangle()

PAR_NOMBRE = {}
for morceaux in ARETES.values():
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
for n, aretes_n in sorted(PAR_NOMBRE.items()):
    identifiants = ids(aretes_n, "EDGE")
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

GROUPES = []


def groupe_mailles(nom, aretes_g, kind="EDGE"):
    typ = SMESH.FACE if kind == "FACE" else SMESH.EDGE
    mesh.GroupOnGeom(grp=groupe_geom(nom, ids(aretes_g, kind), kind), name=nom, typ=typ)
    GROUPES.append(nom)


def groupe_noeuds(nom, points):
    mesh.GroupOnGeom(
        grp=groupe_geom(nom, ids([vertex(p) for p in points], "VERTEX"), "VERTEX"),
        name=nom,
        typ=SMESH.NODE,
    )
    GROUPES.append(nom)


FAMILLES = {}
for nom, (famille, _) in BARRES.items():
    FAMILLES.setdefault(famille, []).append(nom)
for famille, noms in FAMILLES.items():
    groupe_mailles(famille, [e for nom in noms for (_, _, _, e) in ARETES[nom]])
    for nom in noms:
        groupe_mailles(nom, [e for (_, _, _, e) in ARETES[nom]])  # un groupe par barre
groupe_mailles("SEMELLE", [SEMELLE], "FACE")
for nom, (_, a, c, y) in sorted(GROUPES_ZONES.items()):
    groupe_mailles(nom, [edge(point(a, y, ZP), point(c, y, ZP))])
groupe_noeuds("APP_QUAI", [point(0.0, -DEMI, ZP), point(0.0, DEMI, ZP)])
groupe_noeuds("APP_QUAI_YM", [point(0.0, -DEMI, ZP)])
groupe_noeuds("APP_QUAI_YP", [point(0.0, DEMI, ZP)])
groupe_noeuds("APP_A3", [point(TRAVEES["T2"][1], s * DEMI, ZP) for _, s in COTES])
for k, x in enumerate(TAQUETS, start=1):
    for cote, signe in COTES:
        groupe_noeuds("TQ%d_%s" % (k, cote), [point(x, signe * DEMI, ZP)])
for nom, p in sorted(NOEUDS_SEULS.items()):
    groupe_noeuds(nom, [p])
groupe_noeuds(
    "TETES_PILES", [LIENS[n][0] for n in sorted(LIENS) if n.startswith("TP_")]
)
groupe_noeuds(
    "PIEDS_PILES", [LIENS[n][0] for n in sorted(LIENS) if n.startswith("PS_")]
)
for nom, (a, b) in sorted(LIENS.items()):
    groupe_noeuds(nom + "_A", [a])
    groupe_noeuds(nom + "_B", [b])
progress("%d groupes" % len(GROUPES))

mesh.ExportMED(str(MED_PATH), auto_groups=False, overwrite=True)
meta = {
    "params_sha256": PARAMS_SHA,
    "H_PILES": H_PILES,
    "H_ANNEAU": H_ANNEAU,
    "cotes": {
        "plan_moyen": ZP,
        "axe_appui": Z_AXE,
        "dessus_chevetre": Z_DESSUS_CHEVETRE,
        "axe_anneau": ZA,
        "tete_piles": Z_TETE,
        "dessus_semelle": Z_PIED,
        "plan_moyen_semelle": ZF,
    },
    "segments": SEGMENTS,
    "groupes": GROUPES,
    "noeuds": mesh.NbNodes(),
    "quadrangles": mesh.NbFaces(),
    "segments_maillés": mesh.NbEdges(),
    "liaisons": len(LIENS),
}
MED_PATH.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False))
progress("MED écrit")
print("PALEE_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
