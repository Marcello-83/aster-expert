# ruff: noqa: E501
"""Template of `charges_salome.py` (lot 50 quinquies), filled by `charges_salome.write_script`.

The script is meant to be read and edited by hand by the engineer: parameters at the top,
one function per representation, no dead code. It reads `charges.med` itself (MEDReader of
ParaVis, no conversion) and runs in the ParaVis module of Salomé-Méca and with `pvbatch`.
Placeholders: `@@PROJET@@`, `@@FICHIER_MED@@`, `@@PREMIER_CAS@@`, `@@CAS@@`.
"""

SCRIPT_TEMPLATE = r'''# -*- coding: utf-8 -*-
# Charges de @@PROJET@@ : une flèche par nœud chargé, cas par cas, dans Salomé-Méca.
# Généré par aster_expert.livrables.charges_salome (lot 50 quinquies) : modifiable à la main.
#
# Lit charges.med tel que Code_Aster l'a écrit (champs FN_<cas> et FV_<cas> : forces
# nodales en N et N.m ; VARC_<cas>_TEMP_1 : température), sans fichier intermédiaire.
# Changer de cas : afficher_cas("Q") dans la console Python, ou l'oeil de l'objet « Cas Q »
# dans le navigateur de pipeline. Images sans écran :  pvbatch charges_salome.py --png <dossier>
import os
import sys

from paraview.simple import *  # noqa: F403

# ----------------------------------------------------------------------------------
# PARAMÈTRES
# ----------------------------------------------------------------------------------
# Chemin absolu de charges.med dans la machine (rempli à la génération).
FICHIER_MED = @@FICHIER_MED@@
# Cas affiché à l'ouverture (les autres sont cachés, dans le navigateur de pipeline).
CAS_AFFICHE = "@@PREMIER_CAS@@"
# Longueur en mètres d'une flèche de 1 kN. None : calculée pour chaque cas, de sorte que
# la plus grande flèche du cas vaille 15 % de la taille du modèle.
FACTEUR_ECHELLE = None
# Une flèche sur N nœuds (1 : toutes les flèches).
SOUS_ECHANTILLONNAGE = 1
# Dessiner aussi les forces nodales équivalentes (autoéquilibrées) des cas thermiques.
FLECHES_THERMIQUES = False

# Cas, dans l'ordre du calcul : nature, champs du MED et titre (cas et résultante, en kN).
CAS = @@CAS@@

FRACTION_FLECHE = 0.15
OBJETS = {}  # nom du cas -> [(objet, affichage)]


def _lecteur(champs, nom):
    """Un lecteur MED limité aux champs demandés (par leur nom dans le MED)."""
    lecteur = MEDReader(registrationName=nom, FileNames=[FICHIER_MED])
    lecteur.UpdatePipelineInformation()
    arbre = list(lecteur.GetProperty("FieldsTreeInfo"))[0::2]
    choix = []
    for champ in champs:
        trouves = [c for c in arbre if c.split("/")[-1].startswith(champ + "@@")]
        if not trouves:
            raise KeyError("champ " + champ + " absent de " + FICHIER_MED)
        choix += trouves
    lecteur.FieldsStatus = choix
    return lecteur


def _legende(courbe, vue, titre):
    barre = GetScalarBar(courbe, vue)
    barre.Title = titre
    barre.ComponentTitle = ""
    barre.TitleColor = [0.0, 0.0, 0.0]
    barre.LabelColor = [0.0, 0.0, 0.0]
    barre.RangeLabelFormat = "%-#.4g"
    return barre


def modele_filaire(vue):
    """Le maillage en fond, filaire gris. Renvoie la taille du modèle (diagonale, en m)."""
    maillage = MEDReader(registrationName="Modèle", FileNames=[FICHIER_MED])
    maillage.UpdatePipelineInformation()
    arbre = list(maillage.GetProperty("FieldsTreeInfo"))[0::2]
    maillage.FieldsStatus = [c for c in arbre if c.endswith("@@][@@P0")][:1]
    fusion = MergeBlocks(registrationName="Modèle filaire", Input=maillage)
    affichage = Show(fusion, vue)
    affichage.Representation = "Wireframe"
    affichage.AmbientColor = affichage.DiffuseColor = [0.55, 0.55, 0.55]
    affichage.ColorArrayName = [None, ""]
    xmin, xmax, ymin, ymax, zmin, zmax = fusion.GetDataInformation().GetBounds()
    return ((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2) ** 0.5


def fleches(cas, champ, taille, vue):
    """Flèches orientées selon le vecteur force, colorées selon la norme (kN), à l'échelle
    propre du cas : la plus grande flèche vaut FRACTION_FLECHE de la taille du modèle."""
    nom = cas["nom"]
    lecteur = _lecteur([champ], "Lecture " + champ)
    fusion = MergeBlocks(registrationName="Fusion " + champ, Input=lecteur)
    tableau = "F_kN_" + nom
    calcul = Calculator(registrationName="F en kN : " + nom, Input=fusion)
    calcul.AttributeType = "Point Data"
    calcul.ResultArrayName = tableau
    calcul.Function = (
        "(" + champ + "_DX*iHat + " + champ + "_DY*jHat + " + champ + "_DZ*kHat)/1000"
    )
    calcul.UpdatePipeline()
    maximum = calcul.PointData[tableau].GetRange(-1)[1]
    echelle = FACTEUR_ECHELLE
    if echelle is None:
        echelle = FRACTION_FLECHE * taille / maximum if maximum > 0 else 1.0
    glyphe = Glyph(registrationName="Cas " + nom, Input=calcul, GlyphType="Arrow")
    glyphe.OrientationArray = ["POINTS", tableau]
    glyphe.ScaleArray = ["POINTS", tableau]
    glyphe.VectorScaleMode = "Scale by Magnitude"
    glyphe.ScaleFactor = echelle
    glyphe.GlyphMode = "Every Nth Point"
    glyphe.Stride = SOUS_ECHANTILLONNAGE
    affichage = Show(glyphe, vue)
    ColorBy(affichage, ("POINTS", tableau, "Magnitude"))
    courbe = GetColorTransferFunction(tableau)
    courbe.ApplyPreset("Viridis (matplotlib)", True)
    courbe.AutomaticRescaleRangeMode = "Never"
    courbe.RescaleTransferFunction(0.0, max(maximum, 1e-12))
    _legende(courbe, vue, "Force nodale (kN) - cas " + nom)
    return glyphe, affichage


def temperature(cas, champ, vue):
    """Éléments colorés selon la température, plage symétrique autour de zéro."""
    nom = cas["nom"]
    lecteur = _lecteur([champ], "Lecture " + champ)
    fusion = MergeBlocks(registrationName="Cas " + nom, Input=lecteur)
    affichage = Show(fusion, vue)
    affichage.Representation = "Surface"
    affichage.LineWidth = 6
    affichage.RenderLinesAsTubes = 1
    ColorBy(affichage, ("POINTS", champ))
    courbe = GetColorTransferFunction(champ)
    courbe.ApplyPreset("Cool to Warm", True)
    courbe.AutomaticRescaleRangeMode = "Never"
    maximum = max(abs(v) for v in fusion.PointData[champ].GetRange())
    courbe.RescaleTransferFunction(-max(maximum, 1e-12), max(maximum, 1e-12))
    _legende(courbe, vue, "Température (champ TEMP) - cas " + nom)
    return fusion, affichage


def construire_cas(cas, taille, vue):
    """Tous les objets d'un cas, cachés."""
    objets = []
    if cas["nature"] == "mécanique" or FLECHES_THERMIQUES:
        objets.append(fleches(cas, cas["forces"], taille, vue))
    if cas["temperature"]:
        objets.append(temperature(cas, cas["temperature"], vue))
    for objet, affichage in objets:
        Hide(objet, vue)
        affichage.SetScalarBarVisibility(vue, False)
    OBJETS[cas["nom"]] = objets


TITRE = None


def afficher_cas(nom):
    """Affiche le cas `nom` seul : les autres sont cachés, la légende est celle du cas
    affiché (chaque cas a sa propre échelle de couleurs), le titre donne la résultante."""
    global TITRE
    vue = GetActiveViewOrCreate("RenderView")
    for objets in OBJETS.values():
        for objet, affichage in objets:
            Hide(objet, vue)
            affichage.SetScalarBarVisibility(vue, False)
    for objet, affichage in OBJETS[nom]:
        Show(objet, vue)
        affichage.SetScalarBarVisibility(vue, True)
    if TITRE is None:
        TITRE = Text(registrationName="Titre")
        affichage = Show(TITRE, vue)
        affichage.WindowLocation = "Upper Center"
        affichage.FontSize = 13
        affichage.Color = [0.0, 0.0, 0.0]
    TITRE.Text = [c["titre"] for c in CAS if c["nom"] == nom][0]
    Render(vue)


def enregistrer_images(dossier, vue, taille):
    """Une vue isométrique par cas dans `dossier`."""
    os.makedirs(dossier, exist_ok=True)
    centre = vue.CameraFocalPoint
    for cas in CAS:
        afficher_cas(cas["nom"])
        vue.CameraFocalPoint = centre
        vue.CameraPosition = [centre[0] + taille, centre[1] - 1.2 * taille, centre[2] + 0.9 * taille]
        vue.CameraViewUp = [0.0, 0.0, 1.0]
        vue.ResetCamera()
        fichier = cas["nom"] + "_iso.png"
        SaveScreenshot(os.path.join(dossier, fichier), vue)
        print("[PNG] " + fichier)


def main():
    if not os.path.isfile(FICHIER_MED):
        raise FileNotFoundError("renseigner FICHIER_MED en tête du script (introuvable : " + FICHIER_MED + ")")
    vue = GetActiveViewOrCreate("RenderView")
    vue.ViewSize = [1600, 1000]
    vue.OrientationAxesVisibility = 1
    try:
        vue.UseColorPaletteForBackground = 0
    except AttributeError:  # ParaView antérieur à 5.10
        pass
    vue.Background = [1.0, 1.0, 1.0]
    taille = modele_filaire(vue)
    for cas in CAS:
        construire_cas(cas, taille, vue)
    if "--png" in sys.argv:
        enregistrer_images(sys.argv[sys.argv.index("--png") + 1], vue, taille)
    else:
        afficher_cas(CAS_AFFICHE)
        vue.ResetCamera()
        print("Cas : " + ", ".join(c["nom"] for c in CAS) + ' ; afficher_cas("<cas>") pour changer de cas.')


main()
'''
