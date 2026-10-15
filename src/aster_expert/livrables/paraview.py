"""ParaView scripts and pictures of the deliverables, generated from the manifest
(lot 49, reworked at lot 49 bis).

Two scripts, written next to the `.vtu` files:

- `paraview_charges.py`: the principle of MM's script (consigne of lot 49, annex A) --
  for each case a `Calculator` forming the force vector, a `Glyph` of arrows coloured
  by the norm (« Cool to Warm »), a legend per case, only the first case visible at
  opening. Lot 49 bis: the arrows are no longer drawn at every node of the mesh (blocks
  on a 0.05 m mesh): the nodal forces of a case are summed on a grid of cells whose
  size is the smallest that keeps at most `MAX_ARROWS` loaded cells
  (`load_grid`, Σ conserved exactly), one arrow per cell at the centroid of its loaded
  nodes, in kN -- a distributed load reads as a distributed field of arrows;
- `paraview_resultats.py`: for each elementary case, combination and envelope, a group
  of filters hidden by default (amplified deformed shape coloured by |u| in mm; maps of
  the shell forces in kN/m, kN·m/m; beams as tubes in kN, kN·m; reactions and spring
  forces as arrows in kN), with named legends in display units
  (`aster_expert.livrables.unites`).

The case lists, scale factors (the longest arrow, or the largest displacement, is a
fraction of the size of the model) and the extreme values written in the titles all
come from the manifest (`manifeste.json`), never from a list written by hand.

Both scripts run without a display (`pvbatch`): with `--png <directory>` each object
is saved in three views -- isometric, plan (from +Z) and elevation (from −Y) -- with a
title giving the case or the combination and its extreme value.

Rendering without a display in the VM (established at lot 49, `docs/essais_lot49.md`):
the ParaView 5.11 of the Salomé-Méca image, `xvfb-run -a pvbatch --no-mpi <script>`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.livrables.chaine import deliverables_dir, sha256
from aster_expert.livrables.donnees import Deliverables, FloatArray
from aster_expert.livrables.unites import display
from aster_expert.livrables.vtu import vertices, write_vtu
from aster_expert.livrables.vues import array_names, vtu_name
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

FRACTION_CHARGES = 0.10
FRACTION_DEFORMEE = 0.05
MAX_ARROWS = 400
"""Largest number of arrows of one case on the pictures of loads."""
PRINCIPAL = {
    "efforts_coques": ("MXX", "MYY", "NXX"),
    "efforts_poutres": ("N", "MFY", "MFZ"),
    "ressorts": ("N", "VY"),
    "reactions": ("DZ", "DY", "DX"),
}
"""Components drawn on the pictures, in this order of preference."""
VIEWS = (
    ("iso", (1.0, -1.6, 1.2), (0.0, 0.0, 1.0), False),
    ("plan", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), True),
    ("elevation", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), True),
)
"""(name, direction of the camera, view up, parallel projection)."""


# --- grid of the arrows of loads ---------------------------------------------------


def _node_spacing(points: FloatArray) -> float:
    """Smallest positive gap between the distinct coordinates of the loaded nodes, on
    any axis (the step of a regular mesh); 0 when every node is on one point."""
    gaps = []
    for k in range(3):
        values = np.unique(np.round(points[:, k], 6))
        if values.size > 1:
            gaps.append(float(np.diff(values).min()))
    return min(gaps) if gaps else 0.0


def load_grid(
    coords: FloatArray, forces: FloatArray, max_arrows: int = MAX_ARROWS
) -> tuple[FloatArray, FloatArray, float]:
    """(points, summed forces, cell size): the nodal forces summed on the cells of a
    regular grid whose size is a whole number of node spacings, the origin half a
    spacing before the first node (a cell of a regular mesh holds the same number of
    nodes in each direction: a uniform load gives arrows of one length, the edges
    their tributary share), the smallest size that leaves at most `max_arrows` loaded
    cells. The sum of the forces is kept exactly; each arrow sits at the centroid of
    its loaded nodes."""
    norm = np.linalg.norm(forces, axis=1)
    loaded = norm > 1.0e-12 * (float(norm.max()) if norm.size else 0.0)
    if not loaded.any():
        return np.zeros((0, 3)), np.zeros((0, 3)), 0.0
    points, values = coords[loaded], forces[loaded]
    spacing = _node_spacing(points)
    if spacing <= 0.0:
        spacing = 1.0
    origin = points.min(axis=0) - spacing / 2.0
    multiple = 1
    while True:
        size = multiple * spacing
        keys = np.floor((points - origin) / size + 1.0e-9).astype(np.int64)
        cells, inverse = np.unique(keys, axis=0, return_inverse=True)
        if len(cells) <= max_arrows:
            break
        multiple += 1
    inverse = inverse.reshape(-1)
    count = np.bincount(inverse, minlength=len(cells)).astype(np.float64)
    centre = np.column_stack(
        [np.bincount(inverse, points[:, k], len(cells)) / count for k in range(3)]
    )
    summed = np.column_stack(
        [np.bincount(inverse, values[:, k], len(cells)) for k in range(3)]
    )
    return centre, summed, size


def write_load_grids(d: Deliverables, out: Path) -> dict[str, Any]:
    """One `.vtu` of arrows per load field (`grille__<champ>.vtu`, forces in kN)."""
    coords = d.mesh.coords
    report: dict[str, Any] = {}
    for name, values, kind, entity, _components in d.loads():
        if not name.startswith(("FN_", "FV_")) or not (kind == 0).all():
            continue
        forces = np.zeros((len(coords), 3))
        forces[entity] = values.reshape(len(kind), -1)[:, :3]
        points, summed, size = load_grid(coords, forces)
        grid = vertices(points, np.arange(len(points), dtype=np.int64))
        for k, comp in enumerate(("DX", "DY", "DZ")):
            grid.point_data[f"F_{comp}"] = summed[:, k] * 1.0e-3
        file = f"grille__{name}.vtu"
        write_vtu(out / file, grid)
        norm = np.linalg.norm(summed, axis=1) * 1.0e-3
        report[name] = {
            "fichier": file,
            "fleches": int(len(points)),
            "pas_m": size,
            "max_kN": float(norm.max()) if norm.size else 0.0,
            "somme_kN": [float(v) * 1.0e-3 for v in forces.sum(axis=0)],
            "somme_grille_kN": [float(v) * 1.0e-3 for v in summed.sum(axis=0)],
        }
    return report


# --- extremes written in the titles --------------------------------------------------


def extremes(
    d: Deliverables, manifest: dict[str, Any], declared: Any
) -> dict[str, list[float]]:
    """Min and max (SI) of every component array drawn as a map (`declared`: the
    fields of the `deliverables` section)."""
    section_fields = {c["cle"]: c for c in manifest["champs"]}
    out: dict[str, list[float]] = {}
    infos = {i.key: i for i in d.field_infos(declared)}
    for key, champ in section_fields.items():
        if champ["famille"] not in ("efforts_coques", "efforts_poutres"):
            continue
        comps = [c["nom"] for c in champ["composantes"]]
        drawn = _pick(comps, champ["famille"])
        fa = d.field(infos[key])
        for npz_key, med in array_names(d, key):
            if npz_key.endswith(("_comb", "_pos")):
                continue
            values = fa.arrays[npz_key]
            for comp in drawn:
                column = values[:, comps.index(comp)]
                finite = column[np.isfinite(column)]
                if finite.size:
                    out[f"{med}_{comp}"] = [float(finite.min()), float(finite.max())]
    return out


# --- scripts -------------------------------------------------------------------------

_HEADER = """# Généré par aster_expert.livrables.paraview (lots 49, 49 bis) à partir du
# manifeste des livrables du projet {projet} : ne pas éditer, régénérer
# (aster-expert projet {projet} livrables --sous-etape images).
#
# Usage dans ParaView (View > Python Shell) :
#     exec(open(r"<chemin>/{script}").read())
# ou sans écran :
#     pvbatch --no-mpi {script} --png <dossier>
# Les fichiers .vtu sont lus dans DOSSIER (par défaut le dossier du script, ou le
# dossier courant quand le script est exécuté par exec()).
import json
import os
import sys

from paraview.simple import *  # noqa: F403

try:
    DOSSIER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DOSSIER = os.getcwd()
with open(os.path.join(DOSSIER, {fichier_manifeste!r}), encoding="utf-8") as _f:
    MANIFESTE = json.load(_f)
PNG = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
COLOR_PRESET = "Cool to Warm"
VUES = {vues!r}
TAILLE = MANIFESTE["taille_du_modele_m"]


def _vue():
    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1600, 1000]
    view.OrientationAxesVisibility = 1
    try:
        view.UseColorPaletteForBackground = 0
    except AttributeError:
        pass
    view.Background = [1.0, 1.0, 1.0]
    return view


def _camera(view, direction, haut, parallele):
    view.CameraParallelProjection = 1 if parallele else 0
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    view.CameraPosition = list(direction)
    view.CameraViewUp = list(haut)
    view.ResetCamera()


def _barre(lut, view, titre):
    bar = GetScalarBar(lut, view)
    bar.Title = titre
    bar.ComponentTitle = ""
    bar.TitleColor = [0.0, 0.0, 0.0]
    bar.LabelColor = [0.0, 0.0, 0.0]
    bar.RangeLabelFormat = "%-#.4g"
    bar.Visibility = 0
    return bar


TITRE = Text(Text="")
TITRE_AFFICHAGE = None


def _titre(view, texte):
    global TITRE_AFFICHAGE
    TITRE.Text = texte
    if TITRE_AFFICHAGE is None:
        TITRE_AFFICHAGE = Show(TITRE, view)
        TITRE_AFFICHAGE.WindowLocation = "Upper Center"
        TITRE_AFFICHAGE.FontSize = 13
        TITRE_AFFICHAGE.Color = [0.0, 0.0, 0.0]


def _images(view, objet, lut, nom, titre):
    Show(objet, view)
    GetScalarBar(lut, view).Visibility = 1
    _titre(view, titre)
    for vue, direction, haut, parallele in VUES:
        _camera(view, direction, haut, parallele)
        fichier = "{{}}_{{}}.png".format(nom, vue)
        SaveScreenshot(os.path.join(PNG, fichier), view)
        print("[PNG] " + fichier)
    Hide(objet, view)
    GetScalarBar(lut, view).Visibility = 0
"""

_CHARGES = """
CAS = MANIFESTE["cas"]
FRACTION = {fraction}
view = _vue()
fond = OpenDataFile(os.path.join(DOSSIER, "charges.vtu"))
RenameSource("modèle (charges.vtu)", fond)
contour = Show(fond, view)
contour.Representation = "Wireframe"
contour.AmbientColor = contour.DiffuseColor = [0.6, 0.6, 0.6]
contour.Opacity = 0.3
glyphs = []
for cas in CAS:
    nom, maximum = cas["nom"], cas["max_kN"]
    source = OpenDataFile(os.path.join(DOSSIER, cas["fichier"]))
    RenameSource("Grille_" + nom, source)
    calc = Calculator(Input=source)
    calc.AttributeType = "Point Data"
    calc.ResultArrayName = "F_kN_" + nom
    calc.Function = '"F_DX"*iHat + "F_DY"*jHat + "F_DZ"*kHat'
    RenameSource("Calc_" + nom, calc)
    glyph = Glyph(Input=calc, GlyphType="Arrow")
    glyph.OrientationArray = ["POINTS", "F_kN_" + nom]
    glyph.ScaleArray = ["POINTS", "F_kN_" + nom]
    glyph.VectorScaleMode = "Scale by Magnitude"
    glyph.ScaleFactor = FRACTION * TAILLE / maximum if maximum > 0 else 1.0
    glyph.GlyphMode = "All Points"
    RenameSource("Glyph_" + nom, glyph)
    affichage = Show(glyph, view)
    ColorBy(affichage, ("POINTS", "F_kN_" + nom, "Magnitude"))
    lut = GetColorTransferFunction("F_kN_" + nom)
    lut.ApplyPreset(COLOR_PRESET, True)
    affichage.RescaleTransferFunctionToDataRange(True)
    legende = "norme de F, " + nom + " (kN par maille de {{:.2f}} m)"
    _barre(lut, view, legende.format(cas["pas_m"]))
    Hide(glyph, view)
    glyphs.append((cas, glyph, lut))

if PNG:
    os.makedirs(PNG, exist_ok=True)
    for cas, glyph, lut in glyphs:
        somme = ", ".join("{{:.1f}}".format(v) for v in cas["somme_kN"])
        titre = (
            "{{}} : forces nodales sommées par maille de {{:.2f}} m ({{}} flèches) ; "
            "norme max = {{:.1f}} kN ; résultante = ({{}}) kN"
        ).format(cas["nom"], cas["pas_m"], cas["fleches"], cas["max_kN"], somme)
        _images(view, glyph, lut, "charges_" + cas["nom"], titre)
elif glyphs:
    cas, glyph, lut = glyphs[0]
    Show(glyph, view)
    GetScalarBar(lut, view).Visibility = 1
    _titre(view, cas["nom"] +  " : norme max de F = {{:.1f}} kN".format(cas["max_kN"]))
    view.ResetCamera()
    Render()
    print("Charges : " + ", ".join(c["nom"] for c in CAS))
    print("Activer un autre cas : icône œil de Glyph_<cas> dans le Pipeline Browser.")
"""

_RESULTATS = '''
GROUPES = MANIFESTE["groupes"]
FRACTION = {fraction}
SOURCES = {{}}


def _source(fichier):
    if fichier not in SOURCES:
        SOURCES[fichier] = OpenDataFile(os.path.join(DOSSIER, fichier))
        RenameSource(fichier, SOURCES[fichier])
    return SOURCES[fichier]


def _legende(affichage, view, tableau, association, titre, composante=None):
    if composante is None:
        ColorBy(affichage, (association, tableau))
    else:
        ColorBy(affichage, (association, tableau, composante))
    lut = GetColorTransferFunction(tableau)
    lut.ApplyPreset(COLOR_PRESET, True)
    affichage.RescaleTransferFunctionToDataRange(True)
    _barre(lut, view, titre)
    return lut


def construire(groupe, view):
    """Les filtres d'un cas, d'une combinaison ou d'une enveloppe, masqués :
    une liste de (filtre, table de couleurs, nature, titre)."""
    objets = []
    dep = groupe.get("deplacement")
    if dep:
        calc = Calculator(Input=_source(dep["fichier"]))
        calc.AttributeType = "Point Data"
        calc.ResultArrayName = "U_" + groupe["nom"]
        calc.Function = '"{{0}}_DX"*iHat + "{{0}}_DY"*jHat + "{{0}}_DZ"*kHat'.format(
            dep["prefixe"]
        )
        warp = WarpByVector(Input=calc)
        warp.Vectors = ["POINTS", "U_" + groupe["nom"]]
        facteur = FRACTION * TAILLE / dep["max"] if dep["max"] > 0 else 1.0
        warp.ScaleFactor = facteur
        mm = Calculator(Input=warp)
        mm.AttributeType = "Point Data"
        mm.ResultArrayName = "U_mm_" + groupe["nom"]
        mm.Function = 'mag("U_{{}}")*1000'.format(groupe["nom"])
        RenameSource("{{}} : déformée x{{:.4g}}".format(groupe["nom"], facteur), mm)
        affichage = Show(mm, view)
        lut = _legende(affichage, view, "U_mm_" + groupe["nom"], "POINTS",
                       "déplacement " + groupe["nom"] + " (mm)")
        titre = "{{}} : déformée amplifiée x{{:.4g}} ; déplacement max = {{:.2f}} mm"
        titre = titre.format(
            groupe["nom"], facteur, dep["max"] * 1000.0)
        objets.append((mm, lut, "deformee", titre))
    for carte in groupe.get("cartes", []):
        association = carte["association"]
        calc = Calculator(Input=_source(carte["fichier"]))
        calc.AttributeType = "Cell Data" if association == "CELLS" else "Point Data"
        calc.ResultArrayName = carte["tableau"] + "_aff"
        calc.Function = '"{{}}"*{{}}'.format(carte["tableau"], carte["facteur"])
        seuil = Threshold(Input=calc)
        seuil.Scalars = [association, carte["tableau"] + "_aff"]
        seuil.LowerThreshold = -1.0e300
        seuil.UpperThreshold = 1.0e300
        filtre = seuil
        if association == "CELLS" and carte.get("tubes"):
            filtre = Tube(Input=ExtractSurface(Input=seuil))
            filtre.Radius = 0.004 * TAILLE
        RenameSource(groupe["nom"] + " : " + carte["titre"], filtre)
        affichage = Show(filtre, view)
        lut = _legende(affichage, view, carte["tableau"] + "_aff", association,
                       carte["titre"])
        bornes = carte.get("extremes")
        titre = "{{}} : {{}}".format(groupe["nom"], carte["titre"])
        if bornes:
            titre += " ; min = {{:.1f}}, max = {{:.1f}} {{}}".format(
                bornes[0] * carte["facteur"],
                bornes[1] * carte["facteur"],
                carte["unite"],
            )
        objets.append((filtre, lut, "carte_" + carte["image"], titre))
    for fleche in groupe.get("fleches", []):
        source = _source(fleche["fichier"])
        base = source
        if fleche["association"] == "CELLS":
            base = CellCenters(Input=source)
        calc = Calculator(Input=base)
        calc.AttributeType = "Point Data"
        calc.ResultArrayName = "V_" + fleche["nom"]
        calc.Function = fleche["fonction"]
        seuil = Threshold(Input=calc)
        seuil.Scalars = ["POINTS", fleche["filtre"]]
        seuil.LowerThreshold = -1.0e300
        seuil.UpperThreshold = 1.0e300
        glyph = Glyph(Input=seuil, GlyphType="Arrow")
        glyph.OrientationArray = ["POINTS", "V_" + fleche["nom"]]
        glyph.ScaleArray = ["POINTS", "V_" + fleche["nom"]]
        glyph.VectorScaleMode = "Scale by Magnitude"
        maximum = fleche["max_kN"]
        glyph.ScaleFactor = 0.1 * TAILLE / maximum if maximum > 0 else 1.0
        glyph.GlyphMode = "All Points"
        RenameSource(groupe["nom"] + " : " + fleche["titre"], glyph)
        affichage = Show(glyph, view)
        lut = _legende(affichage, view, "V_" + fleche["nom"], "POINTS", fleche["titre"],
                       "Magnitude")
        titre = "{{}} : {{}} ; norme max = {{:.1f}} kN".format(
            groupe["nom"], fleche["titre"], fleche["max_kN"])
        objets.append((glyph, lut, fleche["nom"].split("_")[0].lower(), titre))
    for objet, lut, _kind, _titre_objet in objets:
        Hide(objet, view)
        GetScalarBar(lut, view).Visibility = 0
    return objets


view = _vue()
if PNG:
    os.makedirs(PNG, exist_ok=True)
    for groupe in GROUPES:
        if not groupe.get("png"):
            continue
        for objet, lut, kind, titre in construire(groupe, view):
            nom = "resultats_{{}}_{{}}".format(groupe["nom"], kind)
            _images(view, objet, lut, nom, titre)
else:
    tous = [construire(groupe, view) for groupe in GROUPES]
    if tous and tous[0]:
        objet, lut, _, titre = tous[0][0]
        Show(objet, view)
        GetScalarBar(lut, view).Visibility = 1
        _titre(view, titre)
    view.ResetCamera()
    Render()
    print("Groupes : " + ", ".join(g["nom"] for g in GROUPES))
    print("Chaque groupe est masqué : icône œil dans le Pipeline Browser.")
'''


def charges_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Cases of the script of loads: one per `FN_<case>` (and `FV_` for the forces of
    a temperature) that has a grid of arrows in the manifest."""
    grids = manifest.get("grilles_charges", {})
    out = []
    for load in manifest["charges"]:
        name = load["nom_med"]
        if not name.startswith(("FN_", "FV_")) or name not in grids:
            continue
        grid = grids[name]
        if not grid["fleches"]:
            continue
        out.append({"nom": name, "champ": name, **grid})
    return out


def _pick(components: list[str], family: str) -> list[str]:
    preferred = [c for c in PRINCIPAL.get(family, ()) if c in components]
    return preferred or components[:1]


def result_groups(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """One group per elementary case, combination (max/min) and envelope, read from the
    manifest; `png` marks the groups drawn on the pictures (elementary cases and the
    envelope)."""
    groups: dict[str, dict[str, Any]] = {}
    depl_scale = manifest["echelles"]["deplacements"]
    arrows = manifest["echelles"].get("fleches", {})
    bounds = manifest.get("extremes", {})

    def group(name: str, png: bool) -> dict[str, Any]:
        if name not in groups:
            groups[name] = {"nom": name, "cartes": [], "fleches": [], "png": png}
        return groups[name]

    for champ in manifest["champs"]:
        comps = [c["nom"] for c in champ["composantes"]]
        units = {c["nom"]: c["unite_si"] for c in champ["composantes"]}
        for med in champ["noms_med"]:
            if med.endswith(("_COMB", "_POS")):
                continue
            if med.startswith("CAS_"):
                name, category, png = med[4:].split("__")[0], "cas", True
            elif med.startswith("COMB_"):
                parts = med[5:].split("__")
                name = parts[0] + ("__" + parts[2] if len(parts) > 2 else "")
                category, png = "combinaisons", False
            else:
                parts = med.split("__")
                name, category, png = "ENV_" + parts[2], "enveloppes", True
            fichier = vtu_name(category, champ["cle"])
            g = group(name, png)
            family = champ["famille"]
            if family == "deplacements":
                g["deplacement"] = {
                    "prefixe": med,
                    "max": depl_scale.get(med, 0.0),
                    "fichier": fichier,
                }
            elif family in ("efforts_coques", "efforts_poutres", "contraintes_volumes"):
                for comp in _pick(comps, family):
                    beam = family == "efforts_poutres"
                    elno = champ["champ"].endswith("_ELNO")
                    shown = display(units[comp])
                    g["cartes"].append(
                        {
                            "tableau": f"{med}_{comp}" + ("_1" if elno else ""),
                            "association": "CELLS" if elno else "POINTS",
                            "titre": f"{comp} {name} ({shown.unit})",
                            "composante": comp,
                            "facteur": shown.factor,
                            "unite": shown.unit,
                            "extremes": bounds.get(f"{med}_{comp}"),
                            "image": f"{champ['cle']}_{comp}",
                            "tubes": beam,
                            "fichier": fichier,
                        }
                    )
            elif family == "reactions":
                vector = " + ".join(
                    f'0.001*"{med}_{c}"*{axis}'
                    for c, axis in (("DX", "iHat"), ("DY", "jHat"), ("DZ", "kHat"))
                    if c in comps
                )
                g["fleches"].append(
                    {
                        "nom": f"R_{name}",
                        "association": "POINTS",
                        "fonction": vector,
                        "fichier": fichier,
                        "filtre": f"{med}_{comps[0]}",
                        "titre": f"réactions {name} (kN)",
                        "max_kN": arrows.get(med, 0.0) * 1.0e-3,
                    }
                )
            elif family == "ressorts":
                fn = " + ".join(
                    f'-0.001*"{med}_{c}"*{axis}'
                    for c, axis in (("N", "iHat"), ("VY", "jHat"), ("VZ", "kHat"))
                    if c in comps
                )
                g["fleches"].append(
                    {
                        "nom": f"S_{name}",
                        "association": "CELLS",
                        "fonction": fn,
                        "filtre": f"{med}_{comps[0]}",
                        "titre": f"forces des ressorts {name} (kN)",
                        "fichier": fichier,
                        "max_kN": arrows.get(med, 0.0) * 1.0e-3,
                    }
                )
    return list(groups.values())


def write_scripts(manifest: dict[str, Any], out: Path) -> tuple[Path, Path]:
    projet = manifest["projet"]
    size = manifest["echelles"]["taille_du_modele_m"]
    views = [list(v) for v in VIEWS]
    charges = {"cas": charges_entries(manifest), "taille_du_modele_m": size}
    resultats = {"groupes": result_groups(manifest), "taille_du_modele_m": size}
    path_c = out / "paraview_charges.py"
    path_r = out / "paraview_resultats.py"
    path_c.with_suffix(".json").write_text(
        json.dumps(charges, ensure_ascii=False), encoding="utf-8"
    )
    path_r.with_suffix(".json").write_text(
        json.dumps(resultats, ensure_ascii=False), encoding="utf-8"
    )
    path_c.write_text(
        _HEADER.format(
            projet=projet,
            script=path_c.name,
            fichier_manifeste=path_c.with_suffix(".json").name,
            vues=views,
        )
        + _CHARGES.format(fraction=FRACTION_CHARGES),
        encoding="utf-8",
    )
    path_r.write_text(
        _HEADER.format(
            projet=projet,
            script=path_r.name,
            fichier_manifeste=path_r.with_suffix(".json").name,
            vues=views,
        )
        + _RESULTATS.format(fraction=FRACTION_DEFORMEE),
        encoding="utf-8",
    )
    return path_c, path_r


def render_png(ctx: ProjectContext, script: Path, png_dir: Path) -> list[str]:
    """Run `script` with `--png` in the Salomé-Méca image (see module docstring)."""
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415

    salome = load_mesh_config(ctx.repo_root / "config" / "validation.yaml").salome
    image = Path(str(salome.image_path)).expanduser()
    runtime = shutil.which("singularity")
    if runtime is None or not image.is_file():
        message = "rendu PNG : Singularity ou l'image Salomé-Méca absent (VM seulement)"
        raise ProjectError(message)
    work = script.parent
    png_dir.mkdir(parents=True, exist_ok=True)
    install = salome.install_root
    command = (
        f"source {install}/salome_prerequisites.sh >/dev/null 2>&1; unset DISPLAY; "
        f"cd /w && xvfb-run -a -s '-screen 0 1600x1200x24' pvbatch --no-mpi "
        f"{script.name} --png /png"
    )
    result = subprocess.run(  # noqa: S603 -- fixed argv
        [
            runtime,
            "exec",
            "--containall",
            "--cleanenv",
            "--no-home",
            "--bind",
            f"{work}:/w",
            "--bind",
            f"{png_dir}:/png",
            str(image),
            "bash",
            "-c",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=7200,
        check=False,
    )
    (png_dir / f"{script.stem}.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    if result.returncode != 0:
        message = (
            f"rendu PNG de {script.name} : code {result.returncode} : "
            f"{(result.stderr or result.stdout)[-800:]}"
        )
        raise ProjectError(message)
    return [
        line[6:] for line in result.stdout.splitlines() if line.startswith("[PNG] ")
    ]


def step_images(ctx: ProjectContext) -> list[str]:
    """Grids of arrows, extremes, scripts and pictures, from the existing manifest
    (sub-step `images`; the `.vtu` of the fields are not rewritten)."""
    root = deliverables_dir(ctx)
    manifest_path = root / "manifeste.json"
    if not manifest_path.is_file():
        message = "images : manifeste absent (sous-étape vues d'abord)"
        raise ProjectError(message)
    manifest = json.loads(manifest_path.read_text("utf-8"))
    d = Deliverables(root)
    vtu = root / "vtu"
    for old in vtu.glob("grille__*.vtu"):
        old.unlink()
    manifest["grilles_charges"] = write_load_grids(d, vtu)
    for grid in manifest["grilles_charges"].values():
        path = vtu / grid["fichier"]
        manifest["fichiers"][f"vtu/{grid['fichier']}"] = {
            "sha256": sha256(path),
            "octets": path.stat().st_size,
        }
    section = ctx.declaration.deliverables
    assert section is not None
    manifest["extremes"] = extremes(d, manifest, section.fields)
    text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    manifest_path.write_text(text, "utf-8")
    package = root / "paquet"
    package.mkdir(exist_ok=True)
    (package / "manifeste.json").write_text(text, "utf-8")
    path_c, path_r = write_scripts(manifest, vtu)
    arrows = sum(g["fleches"] for g in manifest["grilles_charges"].values())
    head = (
        f"Scripts ParaView : {path_c.name}, {path_r.name} (générés du manifeste) ; "
        f"{len(manifest['grilles_charges'])} grille(s) de flèches ({arrows} flèches "
        f"au plus {MAX_ARROWS} par cas)"
    )
    if os.environ.get("ASTER_EXPERT_LIVRABLES_SANS_PNG"):
        return [head + " ; rendu PNG NON FAIT (ASTER_EXPERT_LIVRABLES_SANS_PNG)"]
    png = root / "png"
    if png.exists():
        shutil.rmtree(png)
    made = render_png(ctx, path_c, png) + render_png(ctx, path_r, png)
    return [
        head + f" ; {len(made)} image(s) PNG (vues iso, plan, élévation) rendues sans "
        "écran (xvfb-run, pvbatch --no-mpi)"
    ]


def step_paraview(ctx: ProjectContext, manifest: dict[str, Any]) -> list[str]:
    """Lot 49 entry point, kept for `vues`: the pictures are now the sub-step
    `images`, run after it."""
    del manifest
    return [
        "Images ParaView : sous-étape `images` (grilles de flèches, extrema, trois "
        "vues)"
        f" de {ctx.declaration.name}"
    ]


__all__ = [
    "MAX_ARROWS",
    "VIEWS",
    "charges_entries",
    "extremes",
    "load_grid",
    "render_png",
    "result_groups",
    "step_images",
    "step_paraview",
    "vtu_name",
    "write_load_grids",
    "write_scripts",
]
