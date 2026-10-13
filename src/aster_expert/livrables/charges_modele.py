# ruff: noqa: E501
"""Template of `charges_paraview.py` (lot 50 quater), filled by `charges_verif.write_script`.

The script is meant to be read and edited by hand by the engineer: parameters at the top,
one function per representation, no dead code. It runs in the ParaView interface (Python
Shell > Run Script) and with `pvpython` / `pvbatch`. Placeholders: `@@PROJET@@`,
`@@PREMIER_CAS@@`, `@@CAS_EN_PLAN@@`, `@@MANIFESTE@@`.
"""

SCRIPT_TEMPLATE = r'''# -*- coding: utf-8 -*-
# Contrôle de l'application des charges de @@PROJET@@ dans ParaView.
# Généré par aster_expert.livrables.charges_verif (lot 50 quater) à partir du MED de
# vérification des charges (charges.med) : modifiable à la main.
#
# Les .vtu portent exactement les champs du MED charges.med (CHARGE_NODALE,
# CHARGE_REPARTIE, ECART_TEMPERATURE) : un ParaView standard les lit sans greffon.
# Ouvrir : View > Python Shell > Run Script, ou  pvpython charges_paraview.py
# Changer de cas : dans le Python Shell, afficher_cas("Q") ; ou l'oeil des objets du
# navigateur de pipeline (chaque objet porte le nom de son cas).
# Images sans écran :  pvbatch charges_paraview.py --png <dossier>
# Unités des fichiers : forces nodales N et N·m, charges réparties N/m et N·m/m ; les
# légendes sont en kN et kN/m. Repère global, Z vers le haut.
import json
import os
import sys

from paraview.simple import *  # noqa: F403

# ----------------------------------------------------------------------------------
# PARAMÈTRES
# ----------------------------------------------------------------------------------
# Dossier des fichiers .vtu (un par cas, charges_<cas>.vtu). None : le dossier du script.
DOSSIER = None
# Cas affiché à l'ouverture (les autres sont cachés, dans le navigateur de pipeline).
CAS_AFFICHE = "@@PREMIER_CAS@@"
# Longueur en mètres d'une flèche de 1 kN. None : calculée, commune aux cas de même
# nature (la flèche la plus longue d'une nature vaut 12 % de la taille du modèle).
FACTEUR_ECHELLE = None
# Une flèche sur N nœuds (1 : toutes les flèches).
SOUS_ECHANTILLONNAGE = 1
# Cas dont on enregistre aussi la vue en plan (vue de dessus) avec --png.
CAS_EN_PLAN = @@CAS_EN_PLAN@@
# Épaisseur des mailles linéiques colorées, en pixels.
EPAISSEUR_TRAIT = 6
# Couleur des mailles non chargées (ni intensité, ni écart de température).
GRIS_NEUTRE = [0.72, 0.72, 0.72]

MANIFESTE = json.loads(r"""@@MANIFESTE@@""")

try:
    _ICI = os.path.dirname(os.path.abspath(__file__))
except NameError:  # exec() dans le Python Shell : pas de __file__
    _ICI = os.getcwd()
DOSSIER = DOSSIER or _ICI
PNG = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
TAILLE = MANIFESTE["taille_du_modele_m"]
CENTRE = MANIFESTE["centre"]
CAS = {}  # nom du cas -> {"objets": [(objet, affichage, courbe de couleurs)], "titre": ...}


def _chemin(fichier):
    return os.path.join(DOSSIER, fichier)


def _echelle(cas):
    if FACTEUR_ECHELLE is not None:
        return FACTEUR_ECHELLE
    return MANIFESTE["echelles"][cas["nature"]]["m_par_kN"]


def _legende(courbe, vue, titre):
    barre = GetScalarBar(courbe, vue)
    barre.Title = titre
    barre.ComponentTitle = ""
    barre.TitleColor = [0.0, 0.0, 0.0]
    barre.LabelColor = [0.0, 0.0, 0.0]
    barre.RangeLabelFormat = "%-#.4g"
    return barre


def modele_filaire(vue):
    """Le modèle complet en fond, filaire gris clair."""
    source = OpenDataFile(_chemin("modele.vtu"))
    RenameSource("modèle filaire", source)
    affichage = Show(source, vue)
    affichage.Representation = "Wireframe"
    affichage.AmbientColor = affichage.DiffuseColor = [0.55, 0.55, 0.55]
    affichage.ColorArrayName = [None, ""]
    return source


def appuis(vue):
    """Les appuis, en symboles distincts : sphères rouges (réactions), cubes bleus
    (ressorts)."""
    symboles = {
        "reactions": ("Sphere", [0.85, 0.1, 0.1], 0.02),
        "ressorts": ("Box", [0.1, 0.3, 0.85], 0.006),
    }
    for appui in MANIFESTE["appuis"]:
        forme, couleur, taille = symboles[appui["famille"]]
        source = OpenDataFile(_chemin(appui["fichier"]))
        RenameSource("appuis : " + appui["famille"], source)
        glyphe = Glyph(Input=source, GlyphType=forme)
        glyphe.ScaleArray = ["POINTS", "No scale array"]
        glyphe.ScaleFactor = taille * TAILLE
        glyphe.GlyphMode = "All Points"
        RenameSource(appui["legende"], glyphe)
        affichage = Show(glyphe, vue)
        affichage.AmbientColor = affichage.DiffuseColor = couleur
        affichage.ColorArrayName = [None, ""]


def fleches_nodales(cas, source, vue):
    """Forces nodales : flèches orientées selon le vecteur, colorées selon la norme (kN),
    à l'échelle commune des cas de même nature."""
    nom, nature = cas["nom"], cas["nature"]
    tableau = "F_kN_" + nature
    calcul = Calculator(Input=source)
    calcul.AttributeType = "Point Data"
    calcul.ResultArrayName = tableau
    calcul.Function = (
        '("CHARGE_NODALE_FX"*iHat + "CHARGE_NODALE_FY"*jHat + "CHARGE_NODALE_FZ"*kHat)/1000'
    )
    RenameSource("F en kN : " + nom, calcul)
    glyphe = Glyph(Input=calcul, GlyphType="Arrow")
    glyphe.OrientationArray = ["POINTS", tableau]
    glyphe.ScaleArray = ["POINTS", tableau]
    glyphe.VectorScaleMode = "Scale by Magnitude"
    glyphe.ScaleFactor = _echelle(cas)
    glyphe.GlyphMode = "Every Nth Point"
    glyphe.Stride = SOUS_ECHANTILLONNAGE
    RenameSource("Forces nodales : " + nom, glyphe)
    affichage = Show(glyphe, vue)
    ColorBy(affichage, ("POINTS", tableau, "Magnitude"))
    courbe = GetColorTransferFunction(tableau)
    courbe.ApplyPreset("Cool to Warm", True)
    courbe.RescaleTransferFunction(0.0, max(MANIFESTE["echelles"][nature]["max_kN"], 1e-12))
    courbe.AutomaticRescaleRangeMode = "Never"
    _legende(courbe, vue, "Force nodale (kN), cas de charge " + nature)
    return glyphe, affichage, courbe


def _mailles_colorees(cas, source, vue, tableau, titre, maximum):
    affichage = Show(source, vue)
    affichage.Representation = "Surface"
    affichage.LineWidth = EPAISSEUR_TRAIT
    affichage.RenderLinesAsTubes = 1
    ColorBy(affichage, ("CELLS", tableau))
    courbe = GetColorTransferFunction(tableau)
    courbe.ApplyPreset("Viridis (matplotlib)", True)
    courbe.NanColor = GRIS_NEUTRE
    courbe.AutomaticRescaleRangeMode = "Never"
    courbe.RescaleTransferFunction(0.0, max(maximum, 1e-12))
    _legende(courbe, vue, titre)
    return source, affichage, courbe


def charge_repartie(cas, source, vue):
    """Charge répartie : mailles colorées selon l'intensité (kN/m), non chargées en gris."""
    maximum = MANIFESTE["echelles"][cas["nature"]]["max_repartie_kN_m"]
    return _mailles_colorees(
        cas, source, vue, "INTENSITE_REPARTIE_kN_m", "Intensité de la charge répartie (kN/m)", maximum
    )


def ecart_temperature(cas, source, vue):
    """Température : mailles colorées selon l'écart ΔT (K), non affectées en gris."""
    ecart = max(abs(v) for v in cas["ecart_temperature_k"])
    return _mailles_colorees(cas, source, vue, "ECART_TEMPERATURE_K", "Écart de température ΔT (K)", ecart)


def construire_cas(cas, vue):
    """Tous les objets d'un cas, cachés."""
    source = OpenDataFile(_chemin(cas["fichier"]))
    RenameSource("Cas " + cas["nom"], source)
    objets = [fleches_nodales(cas, source, vue)]
    if cas["mailles_chargees"]:
        objets.append(charge_repartie(cas, source, vue))
    if cas["ecart_temperature_k"] != [0.0, 0.0]:
        objets.append(ecart_temperature(cas, source, vue))
    for objet, affichage, courbe in objets:
        Hide(objet, vue)
        affichage.SetScalarBarVisibility(vue, False)
    CAS[cas["nom"]] = {"objets": objets, "titre": cas["titre"]}


TITRE = Text(registrationName="Titre")
TITRE_AFFICHAGE = None


def afficher_cas(nom):
    """Affiche le cas `nom` seul, avec son titre (cas, nature, résultante)."""
    global TITRE_AFFICHAGE
    vue = GetActiveViewOrCreate("RenderView")
    for autre in CAS.values():
        for objet, affichage, _courbe in autre["objets"]:
            Hide(objet, vue)
            affichage.SetScalarBarVisibility(vue, False)
    for objet, affichage, _courbe in CAS[nom]["objets"]:
        Show(objet, vue)
        affichage.SetScalarBarVisibility(vue, True)
    TITRE.Text = CAS[nom]["titre"]
    if TITRE_AFFICHAGE is None:
        TITRE_AFFICHAGE = Show(TITRE, vue)
        TITRE_AFFICHAGE.WindowLocation = "Upper Center"
        TITRE_AFFICHAGE.FontSize = 13
        TITRE_AFFICHAGE.Color = [0.0, 0.0, 0.0]
    Render(vue)


def _camera(vue, direction, haut, parallele):
    vue.CameraParallelProjection = 1 if parallele else 0
    vue.CameraFocalPoint = list(CENTRE)
    vue.CameraPosition = [c + d * TAILLE for c, d in zip(CENTRE, direction)]
    vue.CameraViewUp = list(haut)
    vue.ResetCamera()


def enregistrer_images(vue):
    """Une vue isométrique par cas, plus la vue en plan des cas de CAS_EN_PLAN."""
    os.makedirs(PNG, exist_ok=True)
    for nom in CAS:
        afficher_cas(nom)
        vues = [("iso", (1.0, -1.2, 0.9), (0.0, 0.0, 1.0), False)]
        if nom in CAS_EN_PLAN:
            vues.append(("plan", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), True))
        for suffixe, direction, haut, parallele in vues:
            _camera(vue, direction, haut, parallele)
            fichier = "{}_{}.png".format(nom, suffixe)
            SaveScreenshot(os.path.join(PNG, fichier), vue)
            print("[PNG] " + fichier)


def main():
    vue = GetActiveViewOrCreate("RenderView")
    vue.ViewSize = [1600, 1000]
    vue.OrientationAxesVisibility = 1
    try:
        vue.UseColorPaletteForBackground = 0
    except AttributeError:  # ParaView antérieur à 5.10
        pass
    vue.Background = [1.0, 1.0, 1.0]
    modele_filaire(vue)
    appuis(vue)
    for cas in MANIFESTE["cas"]:
        construire_cas(cas, vue)
    if PNG:
        enregistrer_images(vue)
    else:
        afficher_cas(CAS_AFFICHE)
        vue.ResetCamera()
        print("Cas : " + ", ".join(CAS) + " ; afficher_cas(\"<cas>\") pour changer de cas.")


main()
'''
