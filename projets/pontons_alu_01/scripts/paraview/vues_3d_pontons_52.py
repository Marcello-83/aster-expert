# Vues 3D en volume de PONTONS-ALU-01 (lot 52), ParaView 5.11 de Salomé-Méca, sans écran :
#   xvfb-run -a pvbatch --no-mpi vues_3d_pontons_52.py --variante B10 --dossier <exports B10> \
#       --sortie <dossier PNG> [--combinaisons combinaisons_vues.json] [--vues 1,2,3,4,5,7,9]
# --dossier : les CSV livrés de la variante (noeuds, elements, appuis_axes, deplacements_elementaires).
# Profilés en volume à leur section (elements.csv : repère local, section) ; piles Ø 0,50 ; semelles
# 2,60 × 2,60 × 0,20 au plan moyen ; appuis articulés selon le schéma v4 (P65) : axe Ø 24 selon Y à
# +1,175, étrier en T (semelle 12 mm, deux oreilles 15 mm), joues 15 mm, platine 20 mm, calage 15 mm.
# Vue 7 : déformée de chaque combinaison du JSON (coefficients sur les cas élémentaires), facteur
# d'amplification et déplacement maximal en mm dans le titre. Projection parallèle, règle graduée.
# Vue 1 : depuis le porte-à-faux (X max) ; vue 2 : depuis la culée (X = 0). Vue 9 : zoom 3D sur un nœud
# poutre / montant / diagonale / panne (pannes posées sur les montants, P64).
# Couleur par famille, légende à droite ; PNG 1 920 × 1 080 nommés <variante>_vue<k>_<nom>.png.
"""Volume views of PONTONS-ALU-01 rendered by pvbatch (lot 52)."""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import vtk
from paraview.simple import (
    ColorBy,
    CreateView,
    GetColorTransferFunction,
    Ruler,
    SaveScreenshot,
    Show,
    Text,
    XMLPolyDataReader,
)

FAMILIES = (
    ("POUTRES_PRINC", "poutres principales", (0.12, 0.47, 0.71)),
    ("MONTANTS", "montants", (0.55, 0.75, 0.90)),
    ("DIAGONALES", "diagonales", (0.17, 0.63, 0.17)),
    ("PANNES_SEC", "pannes", (1.00, 0.50, 0.05)),
    ("PANNE_RIVE", "panne de rive", (0.84, 0.15, 0.16)),
    ("CHEVETRES", "chevêtres", (0.58, 0.40, 0.74)),
    ("LONGRINES", "longrines", (0.77, 0.69, 0.84)),
    ("PILES", "piles Ø 0,50", (0.55, 0.34, 0.29)),
    ("SEMELLES", "semelles 2,60 × 2,60 × 0,20", (0.50, 0.50, 0.50)),
    (
        "AXES",
        "appuis articulés (axe Ø 24, étrier, joues, platine ; schéma v4)",
        (0.89, 0.47, 0.76),
    ),
    ("CULEE", "appuis de la culée (culée non modélisée)", (0.10, 0.10, 0.10)),
)
FAMILY_ID = {k: i for i, (k, _, _) in enumerate(FAMILIES)}
SIDES = 24
WIDTH, HEIGHT = 1920, 1080


def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    return list(csv.DictReader(lines, delimiter=";"))


class Builder:
    """Quads and polygons of a vtkPolyData, one family id per cell."""

    def __init__(self):
        self.points = vtk.vtkPoints()
        self.polys = vtk.vtkCellArray()
        self.family = vtk.vtkIntArray()
        self.family.SetName("famille")

    def face(self, corners, fam):
        ids = [self.points.InsertNextPoint(*map(float, c)) for c in corners]
        poly = vtk.vtkPolygon()
        poly.GetPointIds().SetNumberOfIds(len(ids))
        for i, pid in enumerate(ids):
            poly.GetPointIds().SetId(i, pid)
        self.polys.InsertNextCell(poly)
        self.family.InsertNextValue(FAMILY_ID[fam])

    def prism(self, a, b, ring, fam, *, inner=None):
        """Prism along a→b of section `ring` (offsets from the axis); hollow if `inner`."""
        n = len(ring)
        outer_a = [a + r for r in ring]
        outer_b = [b + r for r in ring]
        for i in range(n):
            j = (i + 1) % n
            self.face([outer_a[i], outer_a[j], outer_b[j], outer_b[i]], fam)
        if inner is None:
            self.face(outer_a[::-1], fam)
            self.face(outer_b, fam)
            return
        inner_a = [a + r for r in inner]
        inner_b = [b + r for r in inner]
        for i in range(n):
            j = (i + 1) % n
            self.face([inner_a[j], inner_a[i], inner_b[i], inner_b[j]], fam)
            self.face([outer_a[i], inner_a[i], inner_a[j], outer_a[j]], fam)
            self.face([outer_b[j], inner_b[j], inner_b[i], outer_b[i]], fam)

    def box(self, lo, hi, fam):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        a = np.array([0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2]])
        b = np.array([a[0], a[1], hi[2]])
        hx, hy = 0.5 * (hi[0] - lo[0]), 0.5 * (hi[1] - lo[1])
        ring = [
            np.array([sx * hx, sy * hy, 0.0])
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        self.prism(a, b, ring, fam)

    def write(self, path):
        pd = vtk.vtkPolyData()
        pd.SetPoints(self.points)
        pd.SetPolys(self.polys)
        pd.GetCellData().AddArray(self.family)
        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetFileName(str(path))
        writer.SetInputData(pd)
        writer.Write()


def rect_ring(y, z, hy, hz):
    return [
        s1 * hy * y + s2 * hz * z for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))
    ]


def circle_ring(y, z, r):
    return [
        r
        * (
            math.cos(2 * math.pi * k / SIDES) * y
            + math.sin(2 * math.pi * k / SIDES) * z
        )
        for k in range(SIDES)
    ]


def section_rings(section, y, z):
    """(outer ring, inner ring or None) of a section label of elements.csv."""
    kind, dims = section.split(" ", 1)
    if kind == "tube":
        a, _, t = (float(x) / 1000.0 for x in dims.split("x"))
        return rect_ring(y, z, a / 2, a / 2), rect_ring(y, z, a / 2 - t, a / 2 - t)
    if kind == "BA":
        b, h = (float(x) for x in dims.split("x"))
        return rect_ring(y, z, b / 2, h / 2), None
    if kind == "pile":
        return circle_ring(y, z, float(dims.lstrip("D")) / 2), None
    raise ValueError(f"section inconnue : {section}")


class Model:
    def __init__(self, folder):
        nodes = read_csv(folder / "noeuds.csv")
        self.coords = np.array([[float(r[c]) for c in "xyz"] for r in nodes])
        self.groups = {}
        for r in nodes:
            for g in r["groupes"].split("|"):
                if g:
                    self.groups.setdefault(g, []).append(int(r["noeud"]) - 1)
        self.elements = [
            (
                int(r["noeud1"]) - 1,
                int(r["noeud2"]) - 1,
                r["famille"],
                r["section"],
                np.array([float(r[f"yl_{c}"]) for c in "xyz"]),
                np.array([float(r[f"zl_{c}"]) for c in "xyz"]),
            )
            for r in read_csv(folder / "elements.csv")
            if r["type"].startswith("SEG2")
        ]
        pins = {}
        for r in read_csv(folder / "appuis_axes.csv"):
            pins[(r["palee"], r["chevetre"], r["rive"])] = np.array(
                [float(r[c]) for c in "xyz"]
            )
        self.pins = list(pins.values())
        self.folder = folder
        self.length = float(self.coords[:, 0].max())

    def displacement(self, coefficients):
        """Σ coefficient × DEPL (translations) of the unit cases, per node."""
        u = np.zeros_like(self.coords)
        wanted = set(coefficients)
        with (self.folder / "deplacements_elementaires.csv").open(
            encoding="utf-8"
        ) as stream:
            lines = (line for line in stream if not line.startswith("#"))
            for r in csv.DictReader(lines, delimiter=";"):
                if r["cas"] in wanted:
                    c = coefficients[r["cas"]]
                    u[int(r["noeud"]) - 1] += c * np.array(
                        [float(r["DX"]), float(r["DY"]), float(r["DZ"])]
                    )
        return u

    def nearest(self, p):
        return int(np.argmin(np.sum((self.coords - p) ** 2, axis=1)))

    def build(self, path, *, u=None, scale=0.0, xmin=-1e9, xmax=1e9, box=None):
        disp = np.zeros_like(self.coords) if u is None else scale * u
        pos = self.coords + disp
        b = Builder()
        for n1, n2, fam, section, y, z in self.elements:
            mid = 0.5 * (self.coords[n1] + self.coords[n2])
            if not xmin <= mid[0] <= xmax:
                continue
            if box is not None and not all(
                box[0][k] <= mid[k] <= box[1][k] for k in range(3)
            ):
                continue
            outer, inner = section_rings(section, y, z)
            b.prism(pos[n1], pos[n2], outer, fam, inner=inner)
        for name, ids in sorted(self.groups.items()):
            if not name.startswith("SEMELLE_P") or box is not None:
                continue
            c = self.coords[ids]
            if not xmin <= c[:, 0].mean() <= xmax:
                continue
            d = disp[ids].mean(axis=0)
            zc = c[:, 2].mean()
            b.box(
                [c[:, 0].min() + d[0], c[:, 1].min() + d[1], zc - 0.10 + d[2]],
                [c[:, 0].max() + d[0], c[:, 1].max() + d[1], zc + 0.10 + d[2]],
                "SEMELLES",
            )
        ey, ez = np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0])
        for p in self.pins:
            if not xmin <= p[0] <= xmax:
                continue
            if box is not None and not all(
                box[0][k] - 0.3 <= p[k] <= box[1][k] + 0.3 for k in range(3)
            ):
                continue
            d = disp[self.nearest(p)]
            q = p + d
            # Schéma v4 (P65), cotes relatives à l'axe (+1,175) : axe Ø 24 selon Y,
            # étrier en T (semelle 1,188-1,200, oreilles 15 mm côte à côte jusqu'à
            # 1,135), joues 15 mm, platine 1,105-1,125, calage 1,090-1,105.
            b.prism(
                q - 0.05 * ey,
                q + 0.05 * ey,
                circle_ring(np.array([0, 0, 1.0]), ez, 0.012),
                "AXES",
            )
            for lo, hi in (
                ((-0.10, -0.075, 0.013), (0.10, 0.075, 0.025)),
                ((-0.05, -0.016, -0.040), (0.05, -0.001, 0.013)),
                ((-0.05, 0.001, -0.040), (0.05, 0.016, 0.013)),
                ((-0.06, -0.033, -0.050), (0.06, -0.018, 0.010)),
                ((-0.06, 0.018, -0.050), (0.06, 0.033, 0.010)),
                ((-0.15, -0.17, -0.070), (0.15, 0.17, -0.050)),
                ((-0.15, -0.17, -0.085), (0.15, 0.17, -0.070)),
            ):
                b.box(q + np.array(lo), q + np.array(hi), "AXES")
        for g in ("APP_CULEE_YM", "APP_CULEE_YP"):
            for n in self.groups.get(g, []):
                q = self.coords[n] + disp[n]
                if xmin <= q[0] <= xmax and box is None:
                    b.box(
                        q - 0.10 - np.array([0, 0, 0.10]),
                        q + 0.10 - np.array([0, 0, 0.10]),
                        "CULEE",
                    )
        b.write(path)


def wrap(text, width=150):
    out, line = [], ""
    for part in text.split(" + "):
        piece = part if not line else " + " + part
        if len(line) + len(piece) > width:
            out.append(line)
            line = "   + " + part
        else:
            line += piece
    out.append(line)
    return "\n".join(out)


def render(vtp, png, title, direction, *, ruler, ghost=None):
    view = CreateView("RenderView")
    view.ViewSize = [WIDTH, HEIGHT]
    view.OrientationAxesVisibility = 1
    try:
        view.UseColorPaletteForBackground = 0
    except AttributeError:
        pass
    view.Background = [1.0, 1.0, 1.0]
    reader = XMLPolyDataReader(FileName=[str(vtp)])
    disp = Show(reader, view)
    ColorBy(disp, ("CELLS", "famille"))
    lut = GetColorTransferFunction("famille")
    lut.InterpretValuesAsCategories = 1
    lut.Annotations = [
        x for i, (_, label, _) in enumerate(FAMILIES) for x in (str(i), label)
    ]
    lut.IndexedColors = [c for _, _, rgb in FAMILIES for c in rgb]
    disp.SetScalarBarVisibility(view, True)
    bar = lut.GetScalarBar() if hasattr(lut, "GetScalarBar") else None
    if bar is None:
        from paraview.simple import GetScalarBar

        bar = GetScalarBar(lut, view)
    bar.Title = "famille"
    bar.TitleColor = [0, 0, 0]
    bar.LabelColor = [0, 0, 0]
    bar.TitleFontSize = 18
    bar.LabelFontSize = 16
    bar.WindowLocation = "Any Location"
    bar.Position = [0.86, 0.10]
    bar.ScalarBarLength = 0.6
    if ghost is not None:
        g = XMLPolyDataReader(FileName=[str(ghost)])
        gd = Show(g, view)
        gd.SetRepresentationType("Wireframe")
        gd.AmbientColor = [0.7, 0.7, 0.7]
        gd.DiffuseColor = [0.7, 0.7, 0.7]
        gd.Opacity = 0.25
        gd.ColorArrayName = ["POINTS", ""]
    r = Ruler(Point1=list(ruler[0]), Point2=list(ruler[1]))
    rd = Show(r, view)
    rd.LabelFormat = "%-#6.3g m"
    rd.AxisColor = [0, 0, 0]
    rd.Color = [0, 0, 0]
    rd.FontSize = 18
    t = Text(Text=title)
    td = Show(t, view)
    td.WindowLocation = "Upper Left Corner"
    td.FontSize = 20
    td.Color = [0, 0, 0]
    view.CameraParallelProjection = 1
    view.ResetCamera()
    cam = view.GetActiveCamera()
    fp = np.array(cam.GetFocalPoint())
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    cam.SetPosition(*(fp + 100.0 * d))
    cam.SetViewUp(0.0, 0.0, 1.0)
    view.ResetCamera()
    cam.SetParallelScale(cam.GetParallelScale() * 0.95)
    SaveScreenshot(str(png), view, ImageResolution=[WIDTH, HEIGHT])
    print(f"[PNG] {png}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variante", required=True)
    parser.add_argument("--dossier", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--combinaisons", type=Path)
    parser.add_argument("--vues", default="1,2,3,4,5,7,9")
    args = parser.parse_args()
    out = args.sortie
    out.mkdir(parents=True, exist_ok=True)
    m = Model(args.dossier)
    v = args.variante
    head = f"PONTONS-ALU-01, variante {v}"
    stations = sorted(
        {
            round(float(x), 3)
            for x in m.coords[[i for i in m.groups.get("TETES_PILES", [])], 0]
        }
    )
    x1 = stations[0] if stations else 6.25
    x5 = stations[-2] if len(stations) > 1 else 37.33
    zmin = float(m.coords[:, 2].min()) - 0.1
    vues = {int(k) for k in args.vues.split(",")}
    full = out / f"_{v}_complet.vtp"
    if vues & {1, 2, 7}:
        m.build(full)
    ruler_full = ((0.0, -2.0, zmin), (10.0, -2.0, zmin))
    if 1 in vues:
        render(
            full,
            out / f"{v}_vue1_ponton_iso_depuis_porte_a_faux.png",
            f"{head} - vue 1 : ponton entier, vue depuis le porte-à-faux (X = {m.length:.2f} m)",
            (1.0, -0.9, 0.6),
            ruler=ruler_full,
        )
    if 2 in vues:
        render(
            full,
            out / f"{v}_vue2_ponton_iso_depuis_culee.png",
            f"{head} - vue 2 : ponton entier, vue depuis la culée (X = 0)",
            (-1.0, 0.9, 0.6),
            ruler=ruler_full,
        )
    zooms = (
        (3, "culee_T1", "culée et travée T1", -0.6, x1 + 0.3, (-1.0, -1.0, 0.7)),
        (
            4,
            "palee_P1",
            "palée P1 et ses deux lignes d'appui (chevêtres, longrines, piles, axes)",
            x1 - 0.8,
            x1 + 2.3,
            (1.0, -1.2, 0.5),
        ),
        (
            5,
            "P5_PT5_porte_a_faux",
            "palée P5, petite travée PT5 et porte-à-faux",
            x5 - 0.8,
            m.length + 0.3,
            (1.0, -1.0, 0.6),
        ),
    )
    for k, name, label, a, b, direction in zooms:
        if k not in vues:
            continue
        vtp = out / f"_{v}_{name}.vtp"
        m.build(vtp, xmin=a, xmax=b)
        inside = (m.coords[:, 0] >= a) & (m.coords[:, 0] <= b)
        zloc = float(m.coords[inside, 2].min()) - 0.1
        x0 = max(a, 0.0) + 0.2
        render(
            vtp,
            out / f"{v}_vue{k}_{name}.png",
            f"{head} - vue {k} : {label}, zoom",
            direction,
            ruler=((x0, -1.4, zloc), (x0 + 1.0, -1.4, zloc)),
        )
    if 9 in vues:
        # Nœud de la travée T1 : montant n° 2 (X = 0,75 m depuis la culée), rive YP.
        posts = sorted(
            {
                round(float(m.coords[n1, 0]), 3)
                for n1, _, fam, *_ in m.elements
                if fam == "MONTANTS"
            }
        )
        xn = posts[1]
        box = ((xn - 0.45, 0.30, 1.0), (xn + 0.45, 1.05, 1.6))
        vtp = out / f"_{v}_noeud.vtp"
        m.build(vtp, box=box)
        render(
            vtp,
            out / f"{v}_vue9_noeud_poutre_montant_diagonale_panne.png",
            f"{head} - vue 9 : nœud poutre principale / montant / diagonale / pannes (T1, X = {xn:g} m, rive YP), "
            "zoom 3D\nmontants et diagonales 120 × 120 sous les pannes (dessus +1,35), pannes 50 × 50 posées "
            "dessus (P64) ; montant soudé sur le flanc de la poutre 200 × 200",
            (0.9, -0.55, 0.30),
            ruler=((xn - 0.35, 0.40, 1.15), (xn - 0.25, 0.40, 1.15)),
        )
    if 7 in vues and args.combinaisons:
        for i, c in enumerate(
            json.loads(args.combinaisons.read_text(encoding="utf-8")), start=1
        ):
            u = m.displacement(c["coefficients"])
            norms = np.linalg.norm(u, axis=1)
            n = int(np.argmax(norms))
            umax = float(norms[n])
            raw = 1.0 / umax if umax > 0 else 1.0
            mag = 10 ** math.floor(math.log10(raw))
            scale = max(s * mag for s in (1, 2, 5) if s * mag <= raw)
            vtp = out / f"_{v}_deformee_{c['cle']}.vtp"
            m.build(vtp, u=u, scale=scale)
            title = (
                f"{head} - vue 7.{i} : déformée, {c['titre']} ({c['grandeur']})\n"
                f"facteur d'amplification x{scale:g} ; déplacement maximal {umax * 1000:.1f} mm "
                f"(nœud {n + 1}, X = {m.coords[n, 0]:.2f} m) ; en gris : structure non déformée\n"
                + wrap(c["combinaison"])
            )
            render(
                vtp,
                out / f"{v}_vue7_{i}_deformee_{c['cle']}.png",
                title,
                (0.35, -1.0, 0.35),
                ruler=ruler_full,
                ghost=full,
            )
    for f in out.glob("_*.vtp"):
        f.unlink()
    sys.stdout.flush()
    # pvbatch 5.11 sans écran plante à sa fermeture (SIGSEGV dans swrast) une fois les PNG
    # écrits : sortie immédiate.
    os._exit(0)


if __name__ == "__main__":
    main()
