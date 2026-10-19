# -*- coding: utf-8 -*-
# Mode d'emploi (PONTONS-ALU-01, lot 52) :
# 1. Mettre ce script à côté du dossier MED/ de la variante (B52/MED), ou renseigner DOSSIER_MED.
# 2. Salomé-Méca, module ParaVis : Fichier > Charger un script Python (ou Outils > Python Shell, exec(open(...).read())).
# 3. S'affichent : la déformée de COMBINAISON (facteur FACTEUR_DEFORMEE) colorée par famille ou, COLORATION, par une
#    composante d'effort SUR LA DÉFORMÉE (lot 52 : maillage PONTON_<variante>_ELNO de resultats.med, deux nœuds propres
#    par élément, où DEPL et efforts sont deux champs aux nœuds du même support) ; les charges de CHARGE en flèches.
# 4. Console : afficher_charge("EV_HU"), afficher_deformee("PP_MY_EXTREME", 50), colorier("MFY"), colorier("famille").
# 5. Charges : FN_<cas> (cas unitaires), EV_<événement> (HU, HD, HU_F, HU_IMP_M0..M5) ; combinaisons de resultats.med :
#    PP_MY_EXTREME, FLECHE_ELS_F, CULEE_SRX, IMPACT_M0 (DEPL, EFGE_ELNO) ; ENV_ELU__EFGE_ELNO (enveloppes ELU) ; sur le
#    maillage ELNO : E_<combinaison>__DEPL, E_<combinaison>__EFGE (N, VY, VZ, MT, MFY, MFZ), E_ENV_ELU__EFGE_ELNO.
# 6. Composantes d'effort (repère local, N et N.m) : N, VY, VZ, MT, MFY, MFZ ; enveloppe : N_MAX ... MFZ_MIN.
# 7. Sans écran : pvbatch afficher_pontons_salome.py --png <dossier>.
"""Load structure.med, charges.med and resultats.med of PONTONS-ALU-01 in ParaVis."""

import os
import sys

from paraview.simple import *  # noqa: F403

# ----------------------------------------------------------------------------------- paramètres
try:
    ICI = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exec() dans la console ParaVis
    ICI = os.getcwd()
DOSSIER_MED = os.path.join(ICI, "MED")
CHARGE = "EV_HU_IMP_M0"
COMBINAISON = "PP_MY_EXTREME"
FACTEUR_DEFORMEE = 20.0
COLORATION = "famille"  # « famille », ou une composante : N, VY, VZ, MT, MFY, MFZ
FRACTION_FLECHE = 0.15

FAMILLES = (
    ("POUTRES_PRINC", (0.12, 0.47, 0.71)),
    ("MONTANTS", (0.55, 0.75, 0.90)),
    ("MONTANTS_TRONCONS", (0.10, 0.20, 0.60)),
    ("DIAGONALES", (0.17, 0.63, 0.17)),
    ("PANNES_SEC", (1.00, 0.50, 0.05)),
    ("PANNE_RIVE", (0.84, 0.15, 0.16)),
    ("CHEVETRES", (0.58, 0.40, 0.74)),
    ("LONGRINES", (0.77, 0.69, 0.84)),
    ("PILES", (0.55, 0.34, 0.29)),
    ("SEMELLE", (0.50, 0.50, 0.50)),
)
OBJETS = {}


def _med(nom):
    return os.path.join(DOSSIER_MED, nom)


def _lecteur(fichier, champs, nom, groupes=None):
    """MEDReader limité aux champs (noms du MED) et, au besoin, aux groupes demandés."""
    lecteur = MEDReader(registrationName=nom, FileNames=[_med(fichier)])
    lecteur.UpdatePipelineInformation()
    arbre = list(lecteur.GetProperty("FieldsTreeInfo"))[0::2]
    choix = []
    for champ in champs:
        trouves = [c for c in arbre if c.split("/")[-1].startswith(champ + "@@")]
        if not trouves:
            raise KeyError(champ + " absent de " + fichier)
        choix += trouves
    if not champs:
        choix = [c for c in arbre if c.endswith("@@][@@P0")][:1]
    lecteur.FieldsStatus = choix
    if groupes is not None:
        lecteur = ExtractGroup(registrationName=nom + " (groupes)", Input=lecteur)
        lecteur.AllGroups = ["GRP_" + g for g in groupes]
    return MergeBlocks(registrationName=nom + " (fusion)", Input=lecteur)


def _taille(source):
    b = source.GetDataInformation().GetBounds()
    return ((b[1] - b[0]) ** 2 + (b[3] - b[2]) ** 2 + (b[5] - b[4]) ** 2) ** 0.5


def _cacher(cle, vue):
    for objet in OBJETS.pop(cle, []):
        Hide(objet, vue)


def _deplacement(source, champ, facteur, nom):
    calcul = Calculator(registrationName="u " + nom, Input=source)
    calcul.AttributeType = "Point Data"
    calcul.ResultArrayName = "u"
    calcul.Function = champ + "_DX*iHat + " + champ + "_DY*jHat + " + champ + "_DZ*kHat"
    deformee = WarpByVector(registrationName="Déformée " + nom, Input=calcul)
    deformee.Vectors = ["POINTS", "u"]
    deformee.ScaleFactor = facteur
    return deformee


def afficher_deformee(combinaison=None, facteur=None, coloration=None):
    """Structure (déformée de `combinaison` × `facteur`, 0 : non déformée), colorée par
    famille ou par une composante d'effort de la même combinaison (ELNO aux nœuds)."""
    global COMBINAISON, FACTEUR_DEFORMEE, COLORATION
    COMBINAISON = combinaison or COMBINAISON
    FACTEUR_DEFORMEE = FACTEUR_DEFORMEE if facteur is None else facteur
    COLORATION = coloration or COLORATION
    vue = GetActiveViewOrCreate("RenderView")
    _cacher("structure", vue)
    objets = []
    depl = COMBINAISON + "__DEPL"
    if COLORATION == "famille":
        for famille, couleur in FAMILLES:
            source = _lecteur("resultats.med", [depl], famille, groupes=[famille])
            objet = _deplacement(source, depl, FACTEUR_DEFORMEE, famille)
            affichage = Show(objet, vue)
            affichage.ColorArrayName = [None, ""]
            affichage.AmbientColor = affichage.DiffuseColor = list(couleur)
            affichage.LineWidth = 4
            affichage.RenderLinesAsTubes = 1
            objets.append(objet)
    else:
        # Lot 52 : maillage ELNO (deux nœuds propres par élément), DEPL et efforts aux nœuds
        # du même support : la déformée est colorée par la composante d'effort.
        efge = "E_" + COMBINAISON + "__EFGE"
        depl_e = "E_" + COMBINAISON + "__DEPL"
        source = _lecteur("resultats.med", [depl_e, efge], "efforts " + COMBINAISON)
        objet = _deplacement(source, depl_e, FACTEUR_DEFORMEE, "efforts " + COMBINAISON)
        affichage = Show(objet, vue)
        ColorBy(affichage, ("POINTS", efge, COLORATION))
        affichage.LineWidth = 5
        affichage.RenderLinesAsTubes = 1
        courbe = GetColorTransferFunction(efge)
        courbe.ApplyPreset("Cool to Warm", True)
        affichage.RescaleTransferFunctionToDataRange(False, True)
        affichage.SetScalarBarVisibility(vue, True)
        barre = GetScalarBar(courbe, vue)
        barre.Title = COMBINAISON + " : " + COLORATION + " (N, N.m)"
        barre.ComponentTitle = ""
        barre.TitleColor = barre.LabelColor = [0.0, 0.0, 0.0]
        objets.append(objet)
    OBJETS["structure"] = objets
    _titre(vue)
    Render(vue)


def colorier(coloration):
    afficher_deformee(coloration=coloration)


def afficher_charge(charge=None):
    """Flèches de la charge `charge` (champ de charges.med), à l'échelle propre du cas."""
    global CHARGE
    CHARGE = charge or CHARGE
    vue = GetActiveViewOrCreate("RenderView")
    _cacher("charge", vue)
    source = _lecteur("charges.med", [CHARGE], "charge " + CHARGE)
    calcul = Calculator(registrationName="F (kN) " + CHARGE, Input=source)
    calcul.AttributeType = "Point Data"
    calcul.ResultArrayName = "F_kN"
    calcul.Function = (
        "("
        + CHARGE
        + "_DX*iHat + "
        + CHARGE
        + "_DY*jHat + "
        + CHARGE
        + "_DZ*kHat)/1000"
    )
    calcul.UpdatePipeline()
    maximum = calcul.PointData["F_kN"].GetRange(-1)[1]
    echelle = FRACTION_FLECHE * _taille(calcul) / maximum if maximum > 0 else 1.0
    fleches = Glyph(
        registrationName="Flèches " + CHARGE, Input=calcul, GlyphType="Arrow"
    )
    fleches.OrientationArray = ["POINTS", "F_kN"]
    fleches.ScaleArray = ["POINTS", "F_kN"]
    fleches.VectorScaleMode = "Scale by Magnitude"
    fleches.ScaleFactor = echelle
    fleches.GlyphMode = "All Points"
    affichage = Show(fleches, vue)
    ColorBy(affichage, ("POINTS", "F_kN", "Magnitude"))
    courbe = GetColorTransferFunction("F_kN")
    courbe.ApplyPreset("Viridis (matplotlib)", True)
    courbe.RescaleTransferFunction(0.0, max(maximum, 1e-12))
    affichage.SetScalarBarVisibility(vue, True)
    barre = GetScalarBar(courbe, vue)
    barre.Title = "Force nodale (kN) : " + CHARGE
    barre.ComponentTitle = ""
    barre.TitleColor = barre.LabelColor = [0.0, 0.0, 0.0]
    OBJETS["charge"] = [fleches]
    _titre(vue)
    Render(vue)


TITRE = []


def _titre(vue):
    if not TITRE:
        TITRE.append(Text(registrationName="Titre"))
        affichage = Show(TITRE[0], vue)
        affichage.WindowLocation = "Upper Center"
        affichage.FontSize = 14
        affichage.Color = [0.0, 0.0, 0.0]
    if COLORATION == "famille":
        structure = (
            "déformée "
            + COMBINAISON
            + " x"
            + str(FACTEUR_DEFORMEE)
            + ", coloration par famille"
        )
    else:
        structure = (
            "déformée "
            + COMBINAISON
            + " x"
            + str(FACTEUR_DEFORMEE)
            + ", colorée par "
            + COLORATION
            + " (N, N.m)"
        )
    TITRE[0].Text = (
        "PONTONS-ALU-01 ("
        + os.path.basename(os.path.dirname(DOSSIER_MED))
        + ") : "
        + structure
        + " ; charge "
        + CHARGE
    )


def main():
    for nom in ("structure.med", "charges.med", "resultats.med"):
        if not os.path.isfile(_med(nom)):
            raise FileNotFoundError(
                "renseigner DOSSIER_MED en tête du script : "
                + _med(nom)
                + " introuvable"
            )
    vue = GetActiveViewOrCreate("RenderView")
    vue.ViewSize = [1920, 1080]
    try:
        vue.UseColorPaletteForBackground = 0
    except AttributeError:
        pass
    vue.Background = [1.0, 1.0, 1.0]
    afficher_deformee()
    afficher_charge()
    vue.CameraPosition = [60.0, -45.0, 30.0]
    vue.CameraFocalPoint = [20.0, 0.0, 0.0]
    vue.CameraViewUp = [0.0, 0.0, 1.0]
    vue.ResetCamera()
    if "--png" in sys.argv:
        dossier = sys.argv[sys.argv.index("--png") + 1]
        os.makedirs(dossier, exist_ok=True)
        SaveScreenshot(
            os.path.join(dossier, "salome_famille.png"),
            vue,
            ImageResolution=[1920, 1080],
        )
        afficher_deformee("PP_MY_EXTREME", 50.0, "MFY")
        afficher_charge("EV_HU")
        SaveScreenshot(
            os.path.join(dossier, "salome_MFY.png"), vue, ImageResolution=[1920, 1080]
        )
        # pvbatch 5.11 sans écran plante à sa fermeture : sortie immédiate, images écrites.
        os._exit(0)


main()
