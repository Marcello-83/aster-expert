# ruff: noqa: E501, C401, PTH123, N816, E741, B905, B007, PLR2004 -- script Salomé (Python 3.9 : zip sans strict)
"""Maillage du ponton intégral de PONTONS-ALU-01, géométrie PRO (lot 52) -- script Salomé autonome.

Relancer (VM, Salomé-Méca en conteneur Singularity) :

    singularity exec ~/Desktop/salome_meca.sif salome -t --shutdown-servers=1 \
        maillage_ponton_52.py args:params.json,ponton.med

ou, par la chaîne de l'outil : `aster-expert projet pontons_alu_01 maillage`. Le fichier
de paramètres est facultatif (`args:ponton.med` seul) : il ne peut changer que les
stations des palées (STATIONS, ENTRAXE_CHEVETRES), les hauteurs libres des piles de
chaque palée (H_PILES), le porte-à-faux d'extrémité (L_PF) et la cote des pannes
(COTE_PANNES), la cote des montants et des diagonales (COTE_MONTANTS) et la distance
E_DIAG du nœud diagonale–montant à l'axe de la poutre principale, variantes de la consigne
du lot 52, et depuis le lot 54 les positions des montants intérieurs (X_MONTANTS, P67), la
largeur des chevêtres selon X (B_CHEVETRE) et leurs extrémités en Y (Y_CHEVETRE, P68) ; les
valeurs par défaut sont celles du lot 52. Produit `ponton.med`,
`ponton.meta.json` (empreinte SHA-256 du fichier de paramètres) et
`ponton.progress.txt`, sans aucune dépendance au code d'AsterExpert.

Repère : X le long du ponton depuis la ligne d'appui de la culée, Y transversal, Z = cote
NGF. Unités : m. Points de construction recalés sur la grille de 1 mm. Cotes de l'AVP
(P53) : dessus des poutres et des pannes +1,40, axe des appuis à axe +1,16 (P54), dessus
des chevêtres +1,09, anneau BA 0,40 × 0,40. Travées : T1 (culée → palée P1), puis pour
chaque palée Pk sa petite travée PTk entre ses deux chevêtres et la grande travée T(k+1)
jusqu'à la palée suivante ; après P5, la petite travée PT5 se prolonge sans éclissage par
le porte-à-faux PF, fermé par une panne de rive transversale. Palées, travées et zones
sont engendrées par boucle. Les axes des appuis ne sont pas maillés (groupes d'un nœud
AX_<palée><chevêtre>_<rive>_1, _2, _K). Deux nœuds liés sont toujours distincts : la
petite travée et les longrines s'arrêtent à JEU (1 mm) du nœud auquel elles sont liées.
Lot 52 (P64, treillis horizontal constructible) : montants et diagonales sous les pannes, axe
à Z_DESSUS − COTE_PANNES − COTE_MONTANTS / 2 (+1,29) ; chaque montant relié à la poutre
principale par une liaison rigide verticale (LM_, 0,01 m) ; diagonales soudées sur les
montants au nœud |Y| = B/2 − E_DIAG (dessin en N conservé) ; pannes posées sur les montants et
les diagonales (LR_, 0,085 m) ; tronçons de montant entre la poutre et le nœud de diagonale
dans le groupe MONTANTS_TRONCONS. Axe des appuis à +1,175 (P65).
Lot 54 (P67, P68) : la largeur des chevêtres B_CHEVETRE (0,60) se distingue de celle des
longrines B_ANNEAU (0,40) ; les longrines sont coupées au nu des chevêtres (angles de l'anneau
dans l'épaisseur du chevêtre, groupe ANGLES_ANNEAU) ; montants et chevêtres par paramètres.
Règles (CLAUDE.md, « Scripts Salomé ») : une seule partition, groupes créés sur la
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
STATIONS = (
    6.25,
    14.02,
    21.79,
    29.56,
    37.33,
)  # m, axe du chevêtre C1 de chaque palée (consigne, stations)
ENTRAXE_CHEVETRES = (
    1.52  # m, entre les chevêtres C1 et C2 d'une palée (petite travée, P48)
)
L_PF = 1.25  # m, porte-à-faux après le chevêtre C2 de P5 (panne B ; A : 1,05)
H_PILES = (
    1.30,
    1.95,
    2.50,
    3.50,
    3.90,
)  # m, hauteur libre des piles de P1 à P5 (panne B, diagnostic A25-13959)
COTE_PANNES = (
    0.05  # m, tube carré des pannes (P63 : 50 mm) : axe à cote/2 sous le dessus
)
COTE_MONTANTS = (
    0.12  # m, tube carré des montants et des diagonales (P63), sous les pannes (P64)
)
E_DIAG = (
    0.25  # m, nœud diagonale–montant à E_DIAG de l'axe de la poutre principale (P64)
)
JEU = 0.001  # m, jeu de modélisation aux éclissages et aux bouts des longrines
B = 1.86  # m, entraxe des poutres principales, en rive du tablier (P24)
LARGEUR_TABLIER = 2.00  # m, largeur chargée (P35)
X_MONTANTS = (
    0.75,
    2.25,
    3.75,
    5.25,
)  # m, montants intérieurs d'une grande travée, depuis son origine
Y_PANNES = (0.56, 0.19, -0.18, -0.55)  # m, pannes secondaires (D2)
X_TAQUETS = (1.60, 4.60)  # m, taquets d'une grande travée, depuis son origine (AVP)
L_ZONE = 1.0  # m, longueur d'une zone d'accostage
Z_DESSUS = 1.40  # m NGF, dessus des poutres principales et des pannes (P53)
H_POUTRES = (
    0.20  # m, hauteur des poutres principales : axe à H/2 sous le dessus (P53 : +1,30)
)
Z_AXE = 1.175  # m NGF, axe Ø 24 des appuis articulés (P65, schéma v4)
Z_DESSUS_CHEVETRE = 1.09  # m NGF, dessus de l'anneau BA (P53)
H_ANNEAU = 0.40  # m, hauteur des chevêtres et longrines (P53 : arase inférieure +0,69)
B_ANNEAU = 0.40  # m, largeur des longrines (et des chevêtres jusqu'au lot 52)
B_CHEVETRE = 0.40  # m, largeur des chevêtres selon X (P43 ; lot 54 : 0,60, P68)
Y_CHEVETRE = (-1.05, 1.05)  # m, extrémités des chevêtres (P24, P48)
Y_APPUIS = (-0.93, 0.93)  # m, appuis à axe sous les poutres principales (P44)
Y_PILES = (-0.75, 0.75)  # m, axes des piles (P48)
D_PILES = 0.50  # m, diamètre des piles (P58)
EP_SEMELLE = 0.20  # m, épaisseur de la semelle (P48)
COTE_SEMELLE = 2.60  # m, semelle carrée centrée sur la palée (P48)
TAILLE = 0.25  # m, longueur maximale d'un élément
N_MIN = 4  # nombre minimal d'éléments par barre
# PARAMETRES end ---------------------------------------------------------------------

BASE = Path(sys.argv[0]).resolve().parent
ARGS = sys.argv[1:]
PARAMS_PATH = BASE / ARGS[0] if len(ARGS) == 2 else None
MED_PATH = BASE / (ARGS[-1] if ARGS else "ponton.med")
PARAMS_SHA = None
if PARAMS_PATH is not None:
    raw = PARAMS_PATH.read_bytes()
    PARAMS_SHA = hashlib.sha256(raw).hexdigest()
    for cle, valeur in json.loads(raw.decode("utf-8")).items():
        if cle == "STATIONS":
            STATIONS = tuple(float(v) for v in valeur)
        elif cle == "ENTRAXE_CHEVETRES":
            ENTRAXE_CHEVETRES = float(valeur)
        elif cle == "H_PILES":
            H_PILES = tuple(float(v) for v in valeur)
        elif cle == "L_PF":
            L_PF = float(valeur)
        elif cle == "COTE_PANNES":
            COTE_PANNES = float(valeur)
        elif cle == "COTE_MONTANTS":
            COTE_MONTANTS = float(valeur)
        elif cle == "E_DIAG":
            E_DIAG = float(valeur)
        elif cle == "X_MONTANTS":
            X_MONTANTS = tuple(float(v) for v in valeur)
        elif cle == "Y_CHEVETRE":
            Y_CHEVETRE = tuple(float(v) for v in valeur)
        elif cle == "B_CHEVETRE":
            B_CHEVETRE = float(valeur)
        else:
            raise RuntimeError("paramètre %s non modifiable par une variante" % cle)
if len(H_PILES) != len(STATIONS):
    raise RuntimeError("une hauteur de piles par palée")


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
ZP = grille(Z_DESSUS - H_POUTRES / 2.0)
ZS = grille(Z_DESSUS - COTE_PANNES / 2.0)
ZM = grille(
    Z_DESSUS - COTE_PANNES - COTE_MONTANTS / 2.0
)  # axe des montants et diagonales (P64)
YD = DEMI - E_DIAG  # |Y| du nœud diagonale–montant (P64)
ZA = grille(Z_DESSUS_CHEVETRE - H_ANNEAU / 2.0)
Z_TETE = grille(Z_DESSUS_CHEVETRE - H_ANNEAU)
E = ENTRAXE_CHEVETRES
N_PALEES = len(STATIONS)
# Travées dans l'ordre des X : (nom, nature, x début, x fin).
TRAVEES = []
x_prec = 0.0
for k, xk in enumerate(STATIONS, start=1):
    TRAVEES.append(("T%d" % k, "grande", grille(x_prec), grille(xk)))
    fin = xk + E if k == N_PALEES else xk + E - JEU
    TRAVEES.append(("PT%d" % k, "petite", grille(xk + JEU), grille(fin)))
    x_prec = xk + E
TRAVEES.append(("PF", "porte_a_faux", grille(x_prec), grille(x_prec + L_PF)))
COTES = (("YM", -1.0), ("YP", 1.0))
INTERIEURES = [y for y in Y_PANNES if -DEMI < y < DEMI]
YS_TABLIER = sorted(set([-DEMI, DEMI] + INTERIEURES))
if not all(-YD < y < YD for y in INTERIEURES):
    raise RuntimeError("panne hors de l'étendue des diagonales (|Y| < B/2 − E_DIAG)")
YS_MONTANT = sorted(set([-DEMI, -YD, YD, DEMI] + INTERIEURES))
YS_DIAGONALE = sorted(set([-YD, YD] + INTERIEURES))
TRONCONS = []  # morceaux de montant entre la poutre et le nœud de diagonale (|Y| >= YD)
BARRES = {}  # nom -> (famille, morceaux)
LIENS = {}  # nom -> (point A, point B)
GROUPES_ZONES = {}  # nom -> (barre, x début, x fin, y)
TAQUETS = []
NOEUDS_SEULS = {}  # groupes d'un nœud hors liaisons (culée, oreilles et chevêtres des appuis à axe)
ANGLES = []  # morceaux de longrine dans l'épaisseur d'un chevêtre (angles de l'anneau)


def ajouter_barre(nom, famille, points, n_min=N_MIN):
    BARRES[nom] = (famille, barre(points, n_min))


def lien(nom, a, b):
    if a == b:
        raise RuntimeError("liaison %s : nœuds confondus" % nom)
    LIENS[nom] = (a, b)


for travee, nature, x0, x1 in TRAVEES:
    if nature == "grande":
        if x1 - x0 <= X_MONTANTS[-1] + 1e-9:
            raise RuntimeError("travée %s trop courte pour ses montants" % travee)
        montants = [x0] + [grille(x0 + x) for x in X_MONTANTS] + [x1]
        diagonales = list(zip(montants, montants[1:]))
        taquets = [grille(x0 + x) for x in X_TAQUETS]
        milieu = (x0 + x1) / 2.0
        zones = [
            ("%sD" % travee, x0, grille(x0 + L_ZONE)),
            (
                "%sM" % travee,
                grille(milieu - L_ZONE / 2.0),
                grille(milieu + L_ZONE / 2.0),
            ),
            ("%sF" % travee, grille(x1 - L_ZONE), x1),
        ]
    elif nature == "petite":
        montants = [x0, x1]
        diagonales = [(x0, x1)]
        taquets = []
        k = int(travee[2:])
        milieu = STATIONS[k - 1] + E / 2.0
        zones = [(travee, grille(milieu - L_ZONE / 2.0), grille(milieu + L_ZONE / 2.0))]
    else:
        montants = []
        diagonales = []
        taquets = []
        zones = [(travee, grille(x1 - L_ZONE), x1)]
    TAQUETS.extend(taquets)

    def x_diagonale(d, y):
        return d[0] + (YD - y) / (2.0 * YD) * (d[1] - d[0])

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
        ajouter_barre(
            "MONT_%s_%d" % (travee, i),
            "MONTANTS",
            [point(xm, y, ZM) for y in YS_MONTANT],
        )
        for cote, signe in COTES:
            lien(
                "LM_%s_%d_%s" % (travee, i, cote),
                point(xm, signe * DEMI, ZM),
                point(xm, signe * DEMI, ZP),
            )
            TRONCONS.append((point(xm, signe * YD, ZM), point(xm, signe * DEMI, ZM)))
    for i, d in enumerate(diagonales, start=1):
        ajouter_barre(
            "DIAG_%s_%d" % (travee, i),
            "DIAGONALES",
            [point(x_diagonale(d, y), y, ZM) for y in reversed(YS_DIAGONALE)],
        )
    if nature == "porte_a_faux":
        ajouter_barre("RIVE_PF", "PANNE_RIVE", [point(x1, y, ZP) for y in YS_TABLIER])
    for i, yp in enumerate(Y_PANNES, start=1):
        if nature == "porte_a_faux":
            xs = [x0, x1]
            liees = [x1]  # en x0, la liaison est celle du montant de PT5
        else:
            xs = sorted(
                set(montants) | set(grille(x_diagonale(d, yp)) for d in diagonales)
            )
            liees = xs
        ajouter_barre(
            "PANNE_%s_%d" % (travee, i), "PANNES_SEC", [point(x, yp, ZS) for x in xs]
        )
        for x in liees:
            lien(
                "LR_%s_%d_%02d" % (travee, i, xs.index(x) + 1),
                point(x, yp, ZS),
                point(x, yp, ZP if nature == "porte_a_faux" else ZM),
            )

# Culée (X = 0) : extrémités des poutres principales de T1.
NOEUDS_SEULS["APP_CULEE_YM"] = [point(0.0, -DEMI, ZP)]
NOEUDS_SEULS["APP_CULEE_YP"] = [point(0.0, DEMI, ZP)]
NOEUDS_SEULS["APP_CULEE"] = [point(0.0, -DEMI, ZP), point(0.0, DEMI, ZP)]

# Palées : appuis à axe (P44, P54), anneau, piles et semelle, une itération par palée.
Y_CH = sorted(
    set(grille(y) for y in Y_CHEVETRE + Y_APPUIS + Y_PILES + (0.0,))
    | set(grille(y + s * D_PILES / 2.0) for y in Y_PILES for s in (-1, 1))
)
Y_CH = [y for y in Y_CH if Y_CHEVETRE[0] - 1e-9 <= y <= Y_CHEVETRE[1] + 1e-9]
SEMELLES = {}  # palée -> (xs, ys, z)
for k, xk in enumerate(STATIONS, start=1):
    palee = "P%d" % k
    xc1, xc2 = grille(xk), grille(xk + E)
    t_av = TRAVEES[2 * (k - 1)]  # grande travée qui arrive sur C1
    pt = TRAVEES[2 * (k - 1) + 1]
    t_ap = TRAVEES[2 * (k - 1) + 2]  # grande travée (ou porte-à-faux) qui part de C2
    appuis = {
        "C1": (xc1, [t_av[3], pt[2]]),
        "C2": (xc2, [t_ap[2], pt[3]] if k < N_PALEES else [pt[3]]),
    }
    for chevetre, (x, oreilles) in appuis.items():
        for cote, signe in COTES:
            y = signe * DEMI
            base = "AX_%s%s_%s" % (palee, chevetre, cote)
            for j, x_oreille in enumerate(oreilles, start=1):
                NOEUDS_SEULS["%s_%d" % (base, j)] = [point(x_oreille, y, ZP)]
            NOEUDS_SEULS["%s_K" % base] = [point(x, y, ZA)]
    for chevetre, x in (("C1", xc1), ("C2", xc2)):
        ajouter_barre(
            "CHEV_%s_%s" % (palee, chevetre),
            "CHEVETRES",
            [point(x, y, ZA) for y in Y_CH],
        )
    xl = sorted(
        {
            grille(xc1 + JEU),
            grille(xc2 - JEU),
            grille(xc1 + B_CHEVETRE / 2.0),
            grille(xc2 - B_CHEVETRE / 2.0),
            grille(xc1 + D_PILES / 2.0),
            grille(xc2 - D_PILES / 2.0),
            grille((xc1 + xc2) / 2.0),
        }
    )
    z_pied = grille(Z_TETE - H_PILES[k - 1])
    zf = grille(z_pied - EP_SEMELLE / 2.0)
    for (cote, _), y in zip(COTES, Y_PILES):
        nom = "LONG_%s_%s" % (palee, cote)
        ajouter_barre(nom, "LONGRINES", [point(x, y, ZA) for x in xl])
        for a, c in (
            (xl[0], grille(xc1 + B_CHEVETRE / 2.0)),
            (grille(xc2 - B_CHEVETRE / 2.0), xl[-1]),
        ):
            ANGLES.append((point(a, y, ZA), point(c, y, ZA)))
    for chevetre, x, x_longrine in (("C1", xc1, xl[0]), ("C2", xc2, xl[-1])):
        for (cote, _), y in zip(COTES, Y_PILES):
            suffixe = "%s_%s_%s" % (palee, chevetre, cote)
            ajouter_barre(
                "PILE_%s" % suffixe, "PILES", [point(x, y, z_pied), point(x, y, Z_TETE)]
            )
            lien("TP_%s" % suffixe, point(x, y, Z_TETE), point(x, y, ZA))
            lien("LG_%s" % suffixe, point(x_longrine, y, ZA), point(x, y, ZA))
            lien("PS_%s" % suffixe, point(x, y, z_pied), point(x, y, zf))
    centre = xk + E / 2.0
    xs = sorted(
        set(
            grille(x)
            for x in (
                centre - COTE_SEMELLE / 2.0,
                centre + COTE_SEMELLE / 2.0,
                xc1,
                xc2,
            )
        )
    )
    ys = sorted(
        set(grille(y) for y in (-COTE_SEMELLE / 2.0, COTE_SEMELLE / 2.0) + Y_PILES)
    )
    SEMELLES[palee] = (xs, ys, zf)

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


def rectangle(x0, x1, y0, y1, z):
    wire = geompy.MakePolyline(
        thePoints=[
            vertex((x0, y0, z)),
            vertex((x1, y0, z)),
            vertex((x1, y1, z)),
            vertex((x0, y1, z)),
        ],
        theIsClosed=True,
    )
    return geompy.MakeFaceWires(theWires=[wire], isPlanarWanted=1)


ARETES = {
    nom: [(p, q, n, edge(p, q)) for (p, q, n) in morceaux]
    for nom, (_, morceaux) in BARRES.items()
}
FACES = {}
COUPES = []
for palee, (xs, ys, z) in SEMELLES.items():
    FACES[palee] = rectangle(xs[0], xs[-1], ys[0], ys[-1], z)
    COUPES += [edge((x, ys[0], z), (x, ys[-1], z)) for x in xs[1:-1]]
    COUPES += [edge((xs[0], y, z), (xs[-1], y, z)) for y in ys[1:-1]]
TOUTES = [e for morceaux in ARETES.values() for (_, _, _, e) in morceaux]
progress("géométrie construite : %d arêtes de barres" % len(TOUTES))

# ASSEMBLY begin: une seule partition de toute la géométrie.
PARTITION = geompy.MakePartition(
    ListShapes=list(FACES.values()) + TOUTES,
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


mesh = smesh.Mesh(PARTITION, "ponton")
mesh.Quadrangle()

PAR_NOMBRE = {}
for morceaux in ARETES.values():
    for p, q, n, e in morceaux:
        PAR_NOMBRE.setdefault(n, []).append(e)
for xs, ys, z in SEMELLES.values():
    for k in range(len(xs) - 1):
        n = segments(xs[k + 1] - xs[k])
        for y in ys:
            PAR_NOMBRE.setdefault(n, []).append(edge((xs[k], y, z), (xs[k + 1], y, z)))
    for k in range(len(ys) - 1):
        n = segments(ys[k + 1] - ys[k])
        for x in xs:
            PAR_NOMBRE.setdefault(n, []).append(edge((x, ys[k], z), (x, ys[k + 1], z)))
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
progress("hypothèses posées, calcul du maillage")
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
progress("groupes des barres")
groupe_mailles("ANGLES_ANNEAU", [edge(a, c) for a, c in ANGLES])
groupe_mailles(
    "MONTANTS_TRONCONS",
    [
        e
        for nom in FAMILLES["MONTANTS"]
        for (p, q, _, e) in ARETES[nom]
        if any(
            a[0] == p[0] == q[0]
            and min(a[1], c[1]) - 1e-9 <= min(p[1], q[1])
            and max(p[1], q[1]) <= max(a[1], c[1]) + 1e-9
            for a, c in TRONCONS
        )
    ],
)
groupe_mailles(
    "LONGRINES_COURANT",
    [
        e
        for nom in FAMILLES["LONGRINES"]
        for (p, q, _, e) in ARETES[nom]
        if not any(
            a[1] == p[1]
            and min(a[0], c[0]) - 1e-9 <= p[0] <= max(a[0], c[0]) + 1e-9
            and min(a[0], c[0]) - 1e-9 <= q[0] <= max(a[0], c[0]) + 1e-9
            for a, c in ANGLES
        )
    ],
)
groupe_mailles("SEMELLE", list(FACES.values()), "FACE")
for palee, face in sorted(FACES.items()):
    groupe_mailles("SEMELLE_%s" % palee, [face], "FACE")
for nom, (_, a, c, y) in sorted(GROUPES_ZONES.items()):
    groupe_mailles(nom, [edge(point(a, y, ZP), point(c, y, ZP))])
progress("groupes des zones")
for k, x in enumerate(TAQUETS, start=1):
    for cote, signe in COTES:
        groupe_noeuds("TQ%d_%s" % (k, cote), [point(x, signe * DEMI, ZP)])
for nom, pts in sorted(NOEUDS_SEULS.items()):
    groupe_noeuds(nom, pts)
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
    "STATIONS": list(STATIONS),
    "ENTRAXE_CHEVETRES": ENTRAXE_CHEVETRES,
    "H_PILES": list(H_PILES),
    "L_PF": L_PF,
    "COTE_PANNES": COTE_PANNES,
    "COTE_MONTANTS": COTE_MONTANTS,
    "E_DIAG": E_DIAG,
    "X_MONTANTS": list(X_MONTANTS),
    "Y_CHEVETRE": list(Y_CHEVETRE),
    "B_CHEVETRE": B_CHEVETRE,
    "cotes": {
        "poutres": ZP,
        "pannes": ZS,
        "montants": ZM,
        "axe_appui": grille(Z_AXE),
        "dessus_chevetre": grille(Z_DESSUS_CHEVETRE),
        "axe_anneau": ZA,
        "tete_piles": Z_TETE,
        "semelles_plan_moyen": {p: s[2] for p, s in SEMELLES.items()},
    },
    "travees": [list(t) for t in TRAVEES],
    "segments": SEGMENTS,
    "groupes": GROUPES,
    "noeuds": mesh.NbNodes(),
    "quadrangles": mesh.NbFaces(),
    "segments_maillés": mesh.NbEdges(),
    "liaisons": len(LIENS),
}
MED_PATH.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False))
progress("MED écrit")
print("PONTON_MESH_OK", mesh.NbNodes(), mesh.NbFaces(), mesh.NbEdges())
