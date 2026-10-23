# Déformées de la panne B (PONTONS-ALU-01, B54), ParaView 5.11 de Salomé-Méca, sans écran :
#   xvfb-run -a pvbatch --no-mpi vues_deformees_lot54_pv.py --dossier <champs_combines> --sortie <PNG>
# --dossier : champ_A.vtk, champ_B.vtk, champ_C.vtk (barres en lignes, vecteur u_mm en mm, champ
# combiné lu du MED par champ_combine_lot54.py) et champs_combines.json (amplification, repères).
# Vue de dessus, projection parallèle, 3 200 px de large ; non-déformée en filaire gris clair sous la
# déformée (filaire coloré, palette bleu-blanc-rouge continue) ; barre de couleur horizontale sous la
# vue, graduations rondes ; texte de 24 px (8,5 pt à 200 dpi, soit 16 cm de large) ; pas de titre.
# Les PNG sont rognés des marges blanches par le programme appelant (vues_deformees_lot54.py).
"""Deformed shapes of the panne B of B54 rendered by pvbatch (post-lot 54 control)."""

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from paraview.simple import (
    ColorBy,
    CreateView,
    GetColorTransferFunction,
    GetScalarBar,
    LegacyVTKReader,
    SaveScreenshot,
    Show,
    Text,
    Transform,
    WarpByVector,
)

WIDTH = 3200
FILL = 0.97
FONT = 24
NAMES = {
    "A": "panneB_deformee_A_DY_ELS_c.png",
    "B": "panneB_deformee_B_DY_ELU_acc.png",
    "C": "panneB_deformee_C_DX_hors_T_ELS_c.png",
}
BAR_ZONE = 190
TOP_ZONE = 110
LABEL_RISE = 34
GREY = [0.80, 0.80, 0.80]


def round_ticks(lo, hi):
    """Round graduations (0, 10, 20 ... mm) covering [lo, hi]."""
    span = max(abs(lo), abs(hi))
    step = 10.0 if span <= 90 else 20.0
    if span <= 25:
        step = 5.0
    # keep a negative bound only when it matters (> 5 % of the maximum)
    low = 0.0 if lo > -0.05 * max(hi, 1e-9) else math.floor(lo / step) * step
    high = math.ceil(hi / step) * step
    ticks = []
    t = low
    while t <= high + 1e-9:
        ticks.append(t)
        t += step
    return low, high, ticks


def render(key, folder, out, info, labels):
    reader = LegacyVTKReader(FileNames=[str(folder / f"champ_{key}.vtk")])
    reader.UpdatePipeline()
    pts = np.array(reader.GetClientSideObject().GetOutput().GetPoints().GetData())
    u = np.array(
        reader.GetClientSideObject().GetOutput().GetPointData().GetArray("u_mm")
    )
    amp = float(info["amplification"])
    comp = {"DX": 0, "DY": 1, "DZ": 2}[info["direction"]]
    moved = pts + u * amp * 1e-3
    xmin = min(pts[:, 0].min(), moved[:, 0].min())
    xmax = max(pts[:, 0].max(), moved[:, 0].max())
    ymin = min(pts[:, 1].min(), moved[:, 1].min())
    ymax = max(pts[:, 1].max(), moved[:, 1].max())
    lx, ly = xmax - xmin, ymax - ymin
    cx, cy = 0.5 * (xmin + xmax), 0.5 * (ymin + ymax)
    px = WIDTH * FILL / lx  # pixels per metre
    content_h = ly * px
    height = int(math.ceil(content_h + BAR_ZONE + TOP_ZONE))
    # world y of the pixel row at the centre of the content area
    centre_row = BAR_ZONE + content_h / 2.0
    focal_y = cy - (centre_row - height / 2.0) / px

    view = CreateView("RenderView")
    view.ViewSize = [WIDTH, height]
    view.OrientationAxesVisibility = 0
    try:
        view.UseColorPaletteForBackground = 0
    except AttributeError:
        pass
    view.Background = [1.0, 1.0, 1.0]
    view.CameraParallelProjection = 1
    view.CameraPosition = [cx, focal_y, 100.0]
    view.CameraFocalPoint = [cx, focal_y, 0.0]
    view.CameraViewUp = [0.0, 1.0, 0.0]
    view.CameraParallelScale = height / 2.0 / px

    ghost = Transform(Input=reader)
    ghost.Transform.Translate = [0.0, 0.0, -0.05]
    gd = Show(ghost, view)
    gd.Representation = "Wireframe"
    gd.ColorArrayName = [None, ""]
    gd.AmbientColor = gd.DiffuseColor = GREY
    gd.LineWidth = 2.5
    gd.RenderLinesAsTubes = 1

    warp = WarpByVector(Input=reader)
    warp.Vectors = ["POINTS", "u_mm"]
    warp.ScaleFactor = amp * 1e-3
    wd = Show(warp, view)
    wd.Representation = "Wireframe"
    ColorBy(wd, ("POINTS", "u_mm", "XYZ"[comp]))
    low, high, ticks = round_ticks(*info["bornes_coloration_mm"])
    lut = GetColorTransferFunction("u_mm")
    lut.ApplyPreset("Cool to Warm", True)
    lut.AutomaticRescaleRangeMode = "Never"
    lut.RescaleTransferFunction(low, high)
    wd.SetScalarBarVisibility(view, True)
    wd.LineWidth = 3.5
    wd.RenderLinesAsTubes = 1
    bar = GetScalarBar(lut, view)
    bar.Orientation = "Horizontal"
    bar.WindowLocation = "Any Location"
    bar.ScalarBarLength = 0.40
    bar.ScalarBarThickness = 26
    bar.Position = [0.30, 0.02]
    bar.Title = f"{info['direction']} (mm)"
    bar.ComponentTitle = ""
    bar.TitleFontSize = FONT
    bar.LabelFontSize = FONT
    bar.TitleColor = [0.0, 0.0, 0.0]
    bar.LabelColor = [0.0, 0.0, 0.0]
    bar.TitleBold = 0
    bar.LabelBold = 0
    bar.DrawTickMarks = 1
    bar.AutomaticLabelFormat = 0
    bar.LabelFormat = "%.0f"
    bar.RangeLabelFormat = "%.0f"
    bar.UseCustomLabels = 1
    bar.CustomLabels = ticks
    bar.AddRangeLabels = 0
    bar.TextPosition = "Ticks right/top, annotations left/bottom"

    top_row = BAR_ZONE + content_h
    for name, x in labels.items():
        t = Text(Text=name)
        td = Show(t, view)
        td.WindowLocation = "Any Location"
        td.Justification = "Center"
        td.FontSize = FONT
        td.Color = [0.25, 0.25, 0.25]
        td.Bold = 0
        # label above the strip, centred on the pier
        x_px = (x - cx) * px + WIDTH / 2.0
        td.Position = [x_px / WIDTH - 0.5 * 0.0, (top_row + LABEL_RISE) / height]
    view.Update()
    path = out / NAMES[key]
    SaveScreenshot(
        str(path),
        view,
        ImageResolution=[WIDTH, height],
        FontScaling="Do not scale fonts",
        TransparentBackground=0,
    )
    print(f"[PNG] {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier", required=True)
    parser.add_argument("--sortie", required=True)
    args = parser.parse_args()
    folder, out = Path(args.dossier), Path(args.sortie)
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((folder / "champs_combines.json").read_text(encoding="utf-8"))
    for key in ("A", "B", "C"):
        render(key, folder, out, report["vues"][key], report["reperes"])
    os._exit(0)  # pvbatch 5.11 sans écran plante à la fermeture (lot 51 quater)


main()
