"""ParaView scripts of the deliverables, generated from the manifest (lot 49).

Two scripts, written next to the `.vtu` files:

- `paraview_charges.py`: the principle of MM's script (consigne, annex A) --
  for each case a `Calculator` forming the force vector from `FN_<case>_DX/DY/DZ`, a
  `Glyph` of arrows coloured by the norm (« Cool to Warm »), a legend per case, only the
  first case visible at opening -- with the list of cases and the scale factor read
  from the manifest: the longest arrow of a case is `FRACTION` of the size of the model
  (diagonal of its bounding box), never a constant;
- `paraview_resultats.py`: for each elementary case, combination and envelope, a group
  of filters hidden by default (amplified deformed shape, `WarpByVector`, with a factor
  computed the same way; maps of the shell forces; beams as coloured tubes; reactions
  spring forces as glyphs), with named legends and units.

Both read the `.vtu` (a standard ParaView reads them; the MED needs the `MEDReader`
plugin, shipped with the official binaries only from ParaView 5.12). Both also run
without a display (`pvbatch`): with the argument `--png <directory>` they save the
pictures of the deliverables instead of building the interactive pipeline.

Rendering without a display in the VM (established at lot 49, `docs/essais_lot49.md`):
the ParaView 5.11 of the Salomé-Méca image, `xvfb-run -a pvbatch --no-mpi <script>`;
without `--no-mpi` pvbatch blocks at the MPI start, and `--force-offscreen-rendering`
aborts (no EGL/OSMesa in that build).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from aster_expert.livrables.chaine import deliverables_dir
from aster_expert.livrables.unites import si_unit
from aster_expert.livrables.vues import vtu_name
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

FRACTION_CHARGES = 0.10
FRACTION_DEFORMEE = 0.05
PRINCIPAL = {
    "efforts_coques": ("MXX", "MYY", "NXX"),
    "efforts_poutres": ("N", "MFY", "MFZ"),
    "ressorts": ("N", "VY"),
    "reactions": ("DZ", "DY", "DX"),
}
"""Components drawn on the pictures, in this order of preference."""

_HEADER = """# Généré par aster_expert.livrables.paraview (lot 49) à partir du manifeste
# des livrables du projet {projet} : ne pas éditer, régénérer
# (aster-expert projet {projet} livrables --sous-etape vues).
#
# Usage dans ParaView (View > Python Shell) :
#     exec(open(r"<chemin>/{script}").read())
# ou sans écran :
#     pvbatch --no-mpi {script} --png <dossier>
# Les fichiers .vtu sont lus dans DOSSIER (par défaut le dossier du script, ou le
# dossier courant quand le script est exécuté par exec()).
import json
import os
import os
import sys

from paraview.simple import *  # noqa: F403

try:
    DOSSIER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    DOSSIER = os.getcwd()
MANIFESTE = json.loads({manifeste!r})
PNG = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
COLOR_PRESET = "Cool to Warm"
"""

_CHARGES = """
CAS = MANIFESTE["cas"]
TAILLE = MANIFESTE["taille_du_modele_m"]
FRACTION = {fraction}


def _vue():
    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1600, 1000]
    view.OrientationAxesVisibility = 1
    return view


source = OpenDataFile(os.path.join(DOSSIER, "charges.vtu"))
RenameSource("charges.vtu", source)
view = _vue()
contour = Show(source, view)
contour.Representation = "Wireframe"
contour.AmbientColor = contour.DiffuseColor = [0.6, 0.6, 0.6]
contour.Opacity = 0.3
glyphs = []
for cas in CAS:
    nom, champ, maximum = cas["nom"], cas["champ"], cas["max"]
    calc = Calculator(Input=source)
    calc.AttributeType = "Point Data"
    calc.ResultArrayName = "F_VEC_" + nom
    calc.Function = '"{{0}}_DX"*iHat + "{{0}}_DY"*jHat + "{{0}}_DZ"*kHat'.format(champ)
    RenameSource("Calc_" + nom, calc)
    glyph = Glyph(Input=calc, GlyphType="Arrow")
    glyph.OrientationArray = ["POINTS", "F_VEC_" + nom]
    glyph.ScaleArray = ["POINTS", "F_VEC_" + nom]
    glyph.VectorScaleMode = "Scale by Magnitude"
    glyph.ScaleFactor = FRACTION * TAILLE / maximum if maximum > 0 else 1.0
    glyph.GlyphMode = "All Points"
    RenameSource("Glyph_" + nom, glyph)
    display = Show(glyph, view)
    ColorBy(display, ("POINTS", "F_VEC_" + nom, "Magnitude"))
    lut = GetColorTransferFunction("F_VEC_" + nom)
    lut.ApplyPreset(COLOR_PRESET, True)
    display.RescaleTransferFunctionToDataRange(True)
    bar = GetScalarBar(lut, view)
    bar.Title = "|F| " + nom + " (N)"
    bar.ComponentTitle = ""
    bar.Visibility = 0
    Hide(glyph, view)
    glyphs.append((nom, glyph, lut))

if PNG:
    os.makedirs(PNG, exist_ok=True)
    for nom, glyph, lut in glyphs:
        for other_nom, other, other_lut in glyphs:
            Hide(other, view)
            GetScalarBar(other_lut, view).Visibility = 0
        Show(glyph, view)
        GetScalarBar(lut, view).Visibility = 1
        view.ResetCamera()
        view.CameraPosition = [1.0, -1.6, 1.2]
        view.CameraFocalPoint = [0.0, 0.0, 0.0]
        view.CameraViewUp = [0.0, 0.0, 1.0]
        view.ResetCamera()
        SaveScreenshot(os.path.join(PNG, "charges_" + nom + ".png"), view)
        print("[PNG] charges_" + nom + ".png")
elif glyphs:
    nom, glyph, lut = glyphs[0]
    Show(glyph, view)
    GetScalarBar(lut, view).Visibility = 1
    view.ResetCamera()
    Render()
    print("Charges : " + ", ".join(c["nom"] for c in CAS))
    print("Activer un autre cas : icône œil de Glyph_<cas> dans le Pipeline Browser.")
"""

_RESULTATS = '''
GROUPES = MANIFESTE["groupes"]
TAILLE = MANIFESTE["taille_du_modele_m"]
FRACTION = {fraction}
SOURCES = {{}}


def _source(fichier):
    if fichier not in SOURCES:
        SOURCES[fichier] = OpenDataFile(os.path.join(DOSSIER, fichier))
        RenameSource(fichier, SOURCES[fichier])
    return SOURCES[fichier]


def _vue():
    view = GetActiveViewOrCreate("RenderView")
    view.ViewSize = [1600, 1000]
    return view


def _legende(display, view, tableau, association, titre, composante=None):
    if composante is None:
        ColorBy(display, (association, tableau))
    else:
        ColorBy(display, (association, tableau, composante))
    lut = GetColorTransferFunction(tableau)
    lut.ApplyPreset(COLOR_PRESET, True)
    display.RescaleTransferFunctionToDataRange(True)
    bar = GetScalarBar(lut, view)
    bar.Title = titre
    bar.ComponentTitle = ""
    return lut


def construire(groupe, view):
    """Les filtres d'un cas, d'une combinaison ou d'une enveloppe, masqués :
    une liste de (filtre, table de couleurs, nature)."""
    objets = []
    dep = groupe.get("deplacement")
    if dep:
        calc = Calculator(Input=_source(dep["fichier"]))
        calc.AttributeType = "Point Data"
        calc.ResultArrayName = "U_" + groupe["nom"]
        calc.Function = '"{{0}}_DX"*iHat + "{{0}}_DY"*jHat + "{{0}}_DZ"*kHat'.format(
            dep["prefixe"]
        )
        RenameSource(groupe["nom"] + " : U", calc)
        warp = WarpByVector(Input=calc)
        warp.Vectors = ["POINTS", "U_" + groupe["nom"]]
        warp.ScaleFactor = FRACTION * TAILLE / dep["max"] if dep["max"] > 0 else 1.0
        titre = "{{}} : déformée x{{:.4g}}".format(groupe["nom"], warp.ScaleFactor)
        RenameSource(titre, warp)
        display = Show(warp, view)
        lut = _legende(display, view, "U_" + groupe["nom"], "POINTS",
                       "|u| " + groupe["nom"] + " (m)", "Magnitude")
        objets.append((warp, lut, "deformee"))
    for carte in groupe.get("cartes", []):
        association = carte["association"]
        source = _source(carte["fichier"])
        seuil = Threshold(Input=source)
        seuil.Scalars = [association, carte["tableau"]]
        seuil.LowerThreshold = -1.0e300
        seuil.UpperThreshold = 1.0e300
        filtre = seuil
        if association == "CELLS" and carte.get("tubes"):
            filtre = Tube(Input=ExtractSurface(Input=seuil))
            filtre.Radius = 0.004 * TAILLE
        RenameSource(groupe["nom"] + " : " + carte["titre"], filtre)
        display = Show(filtre, view)
        lut = _legende(display, view, carte["tableau"], association, carte["titre"])
        objets.append((filtre, lut, "carte_" + carte["image"]))
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
        glyph.ScaleFactor = 0.1 * TAILLE / fleche["max"] if fleche["max"] > 0 else 1.0
        glyph.GlyphMode = "All Points"
        RenameSource(groupe["nom"] + " : " + fleche["titre"], glyph)
        display = Show(glyph, view)
        lut = _legende(
            display, view, "V_" + fleche["nom"], "POINTS", fleche["titre"], "Magnitude"
        )
        objets.append((glyph, lut, fleche["nom"].split("_")[0].lower()))
    for objet, lut, _kind in objets:
        Hide(objet, view)
        GetScalarBar(lut, view).Visibility = 0
    return objets


def _camera(view):
    view.ResetCamera()
    view.CameraPosition = [1.0, -1.6, 1.2]
    view.CameraFocalPoint = [0.0, 0.0, 0.0]
    view.CameraViewUp = [0.0, 0.0, 1.0]
    view.ResetCamera()


view = _vue()
if PNG:
    os.makedirs(PNG, exist_ok=True)
    for groupe in GROUPES:
        if not groupe.get("png"):
            continue
        objets = construire(groupe, view)
        for objet, lut, kind in objets:
            for other, other_lut, _ in objets:
                Hide(other, view)
                GetScalarBar(other_lut, view).Visibility = 0
            Show(objet, view)
            GetScalarBar(lut, view).Visibility = 1
            _camera(view)
            name = "resultats_{{}}_{{}}.png".format(groupe["nom"], kind)
            SaveScreenshot(os.path.join(PNG, name), view)
            print("[PNG] " + name)
        for objet, lut, _ in objets:
            Hide(objet, view)
            GetScalarBar(lut, view).Visibility = 0
else:
    tous = [construire(groupe, view) for groupe in GROUPES]
    if tous and tous[0]:
        objet, lut, _ = tous[0][0]
        Show(objet, view)
        GetScalarBar(lut, view).Visibility = 1
    view.ResetCamera()
    Render()
    print("Groupes : " + ", ".join(g["nom"] for g in GROUPES))
    print("Chaque groupe est masqué : icône œil dans le Pipeline Browser.")
'''


def charges_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Cases of the script of loads: one per `FN_<case>` (and `FV_` for the forces of
    a temperature), read from the manifest."""
    scales = manifest["echelles"]["charges"]
    out = []
    for load in manifest["charges"]:
        name = load["nom_med"]
        if not name.startswith(("FN_", "FV_")):
            continue
        out.append({"nom": name, "champ": name, "max": scales.get(name, 0.0)})
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

    def group(name: str, png: bool) -> dict[str, Any]:
        if name not in groups:
            groups[name] = {
                "nom": name,
                "cartes": [],
                "fleches": [],
                "png": png,
            }
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
                    g["cartes"].append(
                        {
                            "tableau": f"{med}_{comp}" + ("_1" if elno else ""),
                            "association": "CELLS" if elno else "POINTS",
                            "titre": f"{comp} {name} ({units[comp]})",
                            "composante": comp,
                            "image": f"{champ['cle']}_{comp}",
                            "tubes": beam,
                            "fichier": fichier,
                        }
                    )
            elif family == "reactions":
                vector = " + ".join(
                    f'"{med}_{c}"*{axis}'
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
                        "titre": f"réactions {name} (N)",
                        "max": arrows.get(med, 0.0),
                    }
                )
            elif family == "ressorts":
                fn = " + ".join(
                    f'-"{med}_{c}"*{axis}'
                    for c, axis in (("N", "iHat"), ("VY", "jHat"), ("VZ", "kHat"))
                    if c in comps
                )
                g["fleches"].append(
                    {
                        "nom": f"S_{name}",
                        "association": "CELLS",
                        "fonction": fn,
                        "filtre": f"{med}_{comps[0]}",
                        "titre": f"forces des ressorts {name} (N)",
                        "fichier": fichier,
                        "max": arrows.get(med, 0.0),
                    }
                )
    return list(groups.values())


def write_scripts(manifest: dict[str, Any], out: Path) -> tuple[Path, Path]:
    projet = manifest["projet"]
    size = manifest["echelles"]["taille_du_modele_m"]
    charges = {
        "cas": charges_entries(manifest),
        "taille_du_modele_m": size,
    }
    resultats = {"groupes": result_groups(manifest), "taille_du_modele_m": size}
    path_c = out / "paraview_charges.py"
    path_r = out / "paraview_resultats.py"
    path_c.write_text(
        _HEADER.format(
            projet=projet,
            script=path_c.name,
            manifeste=json.dumps(charges, ensure_ascii=False),
        )
        + _CHARGES.format(fraction=FRACTION_CHARGES),
        encoding="utf-8",
    )
    path_r.write_text(
        _HEADER.format(
            projet=projet,
            script=path_r.name,
            manifeste=json.dumps(resultats, ensure_ascii=False),
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
        timeout=3600,
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


def step_paraview(ctx: ProjectContext, manifest: dict[str, Any]) -> list[str]:
    root = deliverables_dir(ctx)
    vtu = root / "vtu"
    path_c, path_r = write_scripts(manifest, vtu)
    if os.environ.get("ASTER_EXPERT_LIVRABLES_SANS_PNG"):
        return [
            f"Scripts ParaView : {path_c.name}, {path_r.name} (générés du manifeste) ; "
            "rendu PNG NON FAIT (ASTER_EXPERT_LIVRABLES_SANS_PNG)"
        ]
    png = root / "png"
    if png.exists():
        shutil.rmtree(png)
    made = render_png(ctx, path_c, png) + render_png(ctx, path_r, png)
    return [
        f"Scripts ParaView : {path_c.name}, {path_r.name} (générés du manifeste) ; "
        f"{len(made)} image(s) PNG rendues sans écran (xvfb-run, pvbatch --no-mpi)"
    ]


__all__ = [
    "charges_entries",
    "render_png",
    "result_groups",
    "si_unit",
    "step_paraview",
    "write_scripts",
]
