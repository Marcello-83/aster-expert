# -*- coding: utf-8 -*-
# Mode d'emploi (PONTONS-ALU-01, lot 53 : déplacements sous accostage et amarrage) :
# 1. Mettre ce script à côté de resultats_deplacements_lot53.med (ou du dossier MED/ qui le contient), ou renseigner
#    FICHIER_MED.
# 2. Salomé-Méca, module ParaVis : Fichier > Charger un script Python (ou Outils > Python Shell, exec(open(...).read())).
# 3. S'affiche la déformée du champ CHAMP (facteur FACTEUR_DEFORMEE), colorée par une composante du déplacement
#    (COLORATION : DX, DY, DZ, en mm) sur le support commun PONTON_B52_ELNO, ou par famille sur le maillage d'origine.
# 4. Console : afficher_deformee("CO_ELUA_DY", 20, "DY"), afficher_deformee("CO_ELSC_DX_HT", 50, "DX"),
#    afficher_deformee("EV_AM1_PX", 100, "famille").
# 5. Champs du lot 53 (table de correspondance : compte rendu du lot 53) :
#    événements caractéristiques EV_AC_DY, EV_ACA_DY, EV_AML_DY, EV_AMF_DY (les plus défavorables en |DY|), EV_AM1_PX
#    (AM1_+X), EV_AM2_YP ; combinaisons CO_ELSC_DY (max |DY| ELS caractéristique), CO_ELSC_DX_HT (max |DX| ELS
#    caractéristique hors thermique), CO_ELSF_DY (max |DY| ELS fréquent), CO_ELUA_DY (max |DY| ELU accidentel).
#    Sur le maillage d'origine : <champ>__DEPL ; sur PONTON_B52_ELNO : E_<champ>__DEPL. Les champs du lot 52
#    (PP_MY_EXTREME, FLECHE_ELS_F, CULEE_SRX, IMPACT_M0, ENV_ELU) sont conservés dans le même fichier.
# 6. Sans écran : pvbatch afficher_pontons_salome_53.py --png <dossier>.
"""Load resultats_deplacements_lot53.med of PONTONS-ALU-01 in ParaVis."""

import os
import sys

from paraview.simple import *  # noqa: F403

# ----------------------------------------------------------------------------------- paramètres
try:
    ICI = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exec() dans la console ParaVis
    ICI = os.getcwd()
NOM_MED = "resultats_deplacements_lot53.med"
FICHIER_MED = os.path.join(ICI, NOM_MED)
if not os.path.isfile(FICHIER_MED):
    FICHIER_MED = os.path.join(ICI, "MED", NOM_MED)
CHAMP = "CO_ELSC_DY"
FACTEUR_DEFORMEE = 20.0
COLORATION = "DY"  # « famille », ou une composante du déplacement : DX, DY, DZ

FAMILLES = (
    ("POUTRES_PRINC", (0.12, 0.47, 0.71)),
    ("MONTANTS", (0.55, 0.75, 0.90)),
    ("DIAGONALES", (0.17, 0.63, 0.17)),
    ("PANNES_SEC", (1.00, 0.50, 0.05)),
    ("PANNE_RIVE", (0.84, 0.15, 0.16)),
    ("CHEVETRES", (0.58, 0.40, 0.74)),
    ("LONGRINES", (0.77, 0.69, 0.84)),
    ("PILES", (0.55, 0.34, 0.29)),
    ("SEMELLE", (0.50, 0.50, 0.50)),
)
OBJETS = {}
TITRE = []


def _lecteur(champs, nom, groupes=None):
    """MEDReader limité aux champs (noms du MED) et, au besoin, aux groupes demandés."""
    lecteur = MEDReader(registrationName=nom, FileNames=[FICHIER_MED])
    lecteur.UpdatePipelineInformation()
    arbre = list(lecteur.GetProperty("FieldsTreeInfo"))[0::2]
    choix = []
    for champ in champs:
        trouves = [c for c in arbre if c.split("/")[-1].startswith(champ + "@@")]
        if not trouves:
            raise KeyError(champ + " absent de " + FICHIER_MED)
        choix += trouves
    lecteur.FieldsStatus = choix
    if groupes is not None:
        lecteur = ExtractGroup(registrationName=nom + " (groupes)", Input=lecteur)
        lecteur.AllGroups = ["GRP_" + g for g in groupes]
    return MergeBlocks(registrationName=nom + " (fusion)", Input=lecteur)


def _cacher(cle, vue):
    for objet in OBJETS.pop(cle, []):
        Hide(objet, vue)


def _deplacement(source, champ, facteur, nom):
    calcul = Calculator(registrationName="u " + nom, Input=source)
    calcul.AttributeType = "Point Data"
    calcul.ResultArrayName = "u"
    calcul.Function = champ + "_DX*iHat + " + champ + "_DY*jHat + " + champ + "_DZ*kHat"
    millimetres = Calculator(registrationName="u (mm) " + nom, Input=calcul)
    millimetres.AttributeType = "Point Data"
    millimetres.ResultArrayName = "u_mm"
    millimetres.Function = "u*1000"
    deformee = WarpByVector(registrationName="Déformée " + nom, Input=millimetres)
    deformee.Vectors = ["POINTS", "u"]
    deformee.ScaleFactor = facteur
    return deformee


def afficher_deformee(champ=None, facteur=None, coloration=None):
    """Déformée de `champ` × `facteur`, colorée par famille ou par une composante du
    déplacement (mm) du même champ, aux nœuds du support commun."""
    global CHAMP, FACTEUR_DEFORMEE, COLORATION
    CHAMP = champ or CHAMP
    FACTEUR_DEFORMEE = FACTEUR_DEFORMEE if facteur is None else facteur
    COLORATION = coloration or COLORATION
    vue = GetActiveViewOrCreate("RenderView")
    _cacher("structure", vue)
    objets = []
    if COLORATION == "famille":
        depl = CHAMP + "__DEPL"
        for famille, couleur in FAMILLES:
            source = _lecteur([depl], famille, groupes=[famille])
            objet = _deplacement(source, depl, FACTEUR_DEFORMEE, famille)
            affichage = Show(objet, vue)
            affichage.ColorArrayName = [None, ""]
            affichage.AmbientColor = affichage.DiffuseColor = list(couleur)
            affichage.LineWidth = 4
            affichage.RenderLinesAsTubes = 1
            objets.append(objet)
    else:
        depl = "E_" + CHAMP + "__DEPL"
        source = _lecteur([depl], "déplacements " + CHAMP)
        objet = _deplacement(source, depl, FACTEUR_DEFORMEE, CHAMP)
        affichage = Show(objet, vue)
        ColorBy(
            affichage, ("POINTS", "u_mm", {"DX": "X", "DY": "Y", "DZ": "Z"}[COLORATION])
        )
        affichage.LineWidth = 5
        affichage.RenderLinesAsTubes = 1
        courbe = GetColorTransferFunction("u_mm")
        courbe.ApplyPreset("Cool to Warm", True)
        affichage.RescaleTransferFunctionToDataRange(False, True)
        affichage.SetScalarBarVisibility(vue, True)
        barre = GetScalarBar(courbe, vue)
        barre.Title = CHAMP + " : " + COLORATION + " (mm)"
        barre.ComponentTitle = ""
        barre.TitleColor = barre.LabelColor = [0.0, 0.0, 0.0]
        objets.append(objet)
    OBJETS["structure"] = objets
    _titre(vue)
    Render(vue)


def _titre(vue):
    if not TITRE:
        TITRE.append(Text(registrationName="Titre"))
        affichage = Show(TITRE[0], vue)
        affichage.WindowLocation = "Upper Center"
        affichage.FontSize = 14
        affichage.Color = [0.0, 0.0, 0.0]
    coloration = (
        "par famille" if COLORATION == "famille" else "par " + COLORATION + " (mm)"
    )
    TITRE[0].Text = (
        "PONTONS-ALU-01 (B52, lot 53) : déformée "
        + CHAMP
        + " x"
        + str(FACTEUR_DEFORMEE)
        + ", coloration "
        + coloration
    )


def main():
    if not os.path.isfile(FICHIER_MED):
        raise FileNotFoundError(
            "renseigner FICHIER_MED en tête du script : " + FICHIER_MED + " introuvable"
        )
    vue = GetActiveViewOrCreate("RenderView")
    vue.ViewSize = [1920, 1080]
    try:
        vue.UseColorPaletteForBackground = 0
    except AttributeError:
        pass
    vue.Background = [1.0, 1.0, 1.0]
    afficher_deformee()
    vue.CameraPosition = [20.0, 0.0, 60.0]
    vue.CameraFocalPoint = [20.0, 0.0, 0.0]
    vue.CameraViewUp = [0.0, 1.0, 0.0]
    vue.ResetCamera()
    if "--png" in sys.argv:
        dossier = sys.argv[sys.argv.index("--png") + 1]
        os.makedirs(dossier, exist_ok=True)
        SaveScreenshot(
            os.path.join(dossier, "B52_paravis_CO_ELSC_DY_DY.png"),
            vue,
            ImageResolution=[1920, 1080],
        )
        afficher_deformee("CO_ELSC_DX_HT", 50.0, "famille")
        vue.CameraPosition = [20.0, -60.0, 0.0]
        vue.CameraViewUp = [0.0, 0.0, 1.0]
        vue.ResetCamera()
        SaveScreenshot(
            os.path.join(dossier, "B52_paravis_CO_ELSC_DX_HT_famille.png"),
            vue,
            ImageResolution=[1920, 1080],
        )
        # pvbatch 5.11 sans écran plante à sa fermeture : sortie immédiate, images écrites.
        os._exit(0)


main()
