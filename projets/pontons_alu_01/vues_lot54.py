# ruff: noqa: E501 -- libellés des dessins, phrases entières
"""Views of lot 54 for PONTONS-ALU-01, variant B54: the figures of the notes handed to
the client (consigne § Vues pour les notes).

Rules of presentation: short French titles without lot, variant, internal code or
decision number; text ≥ 11 pt and legends ≥ 10 pt on a figure 16 cm wide; white
background, 200 dpi, white margins trimmed; one colour per family, the same on every
view (`COLORS`). All views are drawn by matplotlib from the geometry of the variant
(`geometrie_lot54`, members at their sections) and, for the deformed shapes, from the
nodal DEPL of the run (unit cases combined with the coefficients of the governing
combination):

1, 2: whole pontoon, isometric, from the cantilever and from the abutment (bars as
lines); 3: abutment and span T1; 4: pier P1 (piles, footing, ring with the cap beams
0,60 prolonged to ±1,20, supports) in volume; 5: pier P5, PT5 and the cantilever;
6: transverse section on pier P1; 7: plan of the truss of T1 and PT1 with the
dimensions of the posts and the nodes at e = 0,25; 8: zoom on a node beam / post /
diagonal / purlin in volume; 9: deformed shape (× 10) under the fundamental ULS
combination that maximises ΣRX of the abutment; 10: deformed shape under the
characteristic SLS combination that maximises the upward deflection of T2; 11 A, B, C:
the views of lot 53 (DY at the characteristic SLS, DY at the accidental ULS, DX
without temperature at the characteristic SLS) with the values at the piers.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Circle, Patch, Polygon, Rectangle  # noqa: E402
from mpl_toolkits.mplot3d.art3d import (  # type: ignore[import-untyped]  # noqa: E402
    Line3DCollection,
    Poly3DCollection,
)
from numpy.typing import NDArray  # noqa: E402
from PIL import Image  # noqa: E402

from aster_expert.projet.context import ProjectContext  # noqa: E402
from pontons_alu_01.combinaisons_lot51ter import envelope, governing  # noqa: E402
from pontons_alu_01.exports_lot51ter import (  # noqa: E402
    VariantData51ter,
    deflection_arrays,
    without_tangential,
)
from pontons_alu_01.geometrie_lot51ter import Geometry51ter  # noqa: E402
from pontons_alu_01.variantes_lot54 import Variant54  # noqa: E402

FloatArray = NDArray[np.float64]
LOT = "lot54"
CODE = "B54"
PREFIX = "panneB"
DPI = 200
WIDTH_IN = 16.0 / 2.54
TEXT_PT = 11
LEGEND_PT = 10
TRIM_MARGIN_PX = 12
MAX_WIDTH_PX = round(WIDTH_IN * DPI)
"""1 260 px: 16 cm at 200 dpi, so that the text keeps its size printed 16 cm wide."""
MM = 1e3
COLORS = {
    "POUTRES_PRINC": "#1c4e9c",
    "PANNES_SEC": "#2b9348",
    "MONTANTS": "#f08c00",
    "DIAGONALES": "#c92a2a",
    "CHEVETRES": "#7048e8",
    "LONGRINES": "#a0522d",
    "PILES": "#0b7285",
    "SEMELLE": "#8d99ae",
    "APPUIS": "#e64980",
}
"""One colour per family, the same on every view."""
LABELS = {
    "POUTRES_PRINC": "poutres principales",
    "PANNES_SEC": "pannes",
    "MONTANTS": "montants",
    "DIAGONALES": "diagonales",
    "CHEVETRES": "chevêtres",
    "LONGRINES": "longrines",
    "PILES": "piles",
    "SEMELLE": "semelles",
    "APPUIS": "appuis",
}
FAMILY_OF = {"PANNE_RIVE": "PANNES_SEC"}
"""The edge purlin of the cantilever is drawn as a purlin."""
LINE_WIDTH = {
    "POUTRES_PRINC": 2.2,
    "PANNES_SEC": 0.8,
    "MONTANTS": 1.4,
    "DIAGONALES": 1.4,
    "CHEVETRES": 3.0,
    "LONGRINES": 2.4,
    "PILES": 2.6,
}
GHOST = "#c9ced6"
PLANKS_THICKNESS = 0.045
"""m, thickness of the timber deck drawn on the section (drawing only, not modelled)."""


def _fr(v: float, digits: int = 1) -> str:
    return f"{v:.{digits}f}".replace(".", ",").replace("-", "−")


def _style() -> None:
    plt.rcParams.update(
        {
            "font.size": TEXT_PT,
            "axes.titlesize": TEXT_PT + 1,
            "axes.labelsize": TEXT_PT,
            "xtick.labelsize": TEXT_PT,
            "ytick.labelsize": TEXT_PT,
            "legend.fontsize": LEGEND_PT,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def trim(path: Path, margin: int = TRIM_MARGIN_PX) -> tuple[int, int]:
    """Crop the white margins of a PNG (white background), keep 200 dpi."""
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        arr = np.asarray(rgb)
        mask = (arr < 250).any(axis=2)
        ys, xs = np.nonzero(mask)
        box = (
            max(0, int(xs.min()) - margin),
            max(0, int(ys.min()) - margin),
            min(arr.shape[1], int(xs.max()) + 1 + margin),
            min(arr.shape[0], int(ys.max()) + 1 + margin),
        )
        out = rgb.crop(box)
    out.save(path, dpi=(DPI, DPI))
    return out.size


def save(fig: Any, path: Path) -> None:
    """Save on a canvas of exactly 16 cm (the legend kept inside, the axes moved up
    above it), then trim the white margins: printed 16 cm wide, the text is never
    smaller than its size in points."""
    if fig.legends:
        fig.canvas.draw()
        top = (
            fig.legends[0]
            .get_window_extent()
            .transformed(fig.transFigure.inverted())
            .y1
        )
        for ax in fig.axes:
            gap = 0.01 if ax.name == "3d" else 0.15
            pos = ax.get_position()
            if pos.y0 < top + gap:
                ax.set_position([pos.x0, top + gap, pos.width, pos.y1 - top - gap])
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    trim(path)


def legend(fig: Any, families: Iterable[str], extra: Sequence[Any] = ()) -> None:
    handles = [Patch(color=COLORS[f], label=LABELS[f]) for f in families]
    handles += list(extra)
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=min(3, len(handles)),
        frameon=False,
        fontsize=LEGEND_PT,
        bbox_to_anchor=(0.5, -0.01),
    )


# --------------------------------------------------------------------------- volumes


Point3 = tuple[float, float, float]


def prism(a: Point3, b: Point3, width: float, height: float) -> list[list[Point3]]:
    """Faces of a box along a horizontal or oblique axis a → b, `width` across in the
    horizontal plane, `height` vertical."""
    pa, pb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    axis = pb - pa
    horiz = np.array([axis[0], axis[1], 0.0])
    if np.linalg.norm(horiz) < 1e-12:  # axe vertical
        across = np.array([1.0, 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])
    else:
        across = np.array([-horiz[1], horiz[0], 0.0]) / np.linalg.norm(horiz)
        up = np.array([0.0, 0.0, 1.0])
    w, h = across * width / 2.0, up * height / 2.0
    corners = [w + h, -w + h, -w - h, w - h]
    ring_a = [tuple(pa + c) for c in corners]
    ring_b = [tuple(pb + c) for c in corners]
    faces = [ring_a, ring_b]
    for k in range(4):
        faces.append([ring_a[k], ring_a[(k + 1) % 4], ring_b[(k + 1) % 4], ring_b[k]])
    return faces


def cylinder(
    x: float, y: float, z0: float, z1: float, r: float, n: int = 20
) -> list[list[Point3]]:
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    lo = [(x + r * math.cos(a), y + r * math.sin(a), z0) for a in t]
    hi = [(x + r * math.cos(a), y + r * math.sin(a), z1) for a in t]
    faces = [lo, hi]
    for k in range(n):
        faces.append([lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]])
    return faces


def slab(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> list[list[Point3]]:
    return prism(
        ((x0, (y0 + y1) / 2, (z0 + z1) / 2)),
        (x1, (y0 + y1) / 2, (z0 + z1) / 2),
        y1 - y0,
        z1 - z0,
    )


def _darker(color: str, k: float = 0.65) -> tuple[float, float, float]:
    r, g, b = mpl.colors.to_rgb(color)
    return (r * k, g * k, b * k)


def pieces(a: Point3, b: Point3, step: float) -> list[tuple[Point3, Point3]]:
    """a → b cut in pieces of at most `step` (finer depth sorting of the faces)."""
    n = max(1, math.ceil(math.dist(a, b) / step))
    pts = [tuple(a[k] + (b[k] - a[k]) * i / n for k in range(3)) for i in range(n + 1)]
    return list(zip(pts, pts[1:], strict=False))  # type: ignore[arg-type]


def solids(
    v: Variant54,
    g: Geometry51ter,
    box: tuple[float, float, float, float, float, float],
    step: float = 0.2,
) -> tuple[list[list[Point3]], list[Any], set[str]]:
    """Faces and face colours of every piece inside `box` (x0, x1, y0, y1, z0, z1),
    at its section, cut in pieces of at most `step`; the families drawn."""
    x0, x1, y0, y1, z0, z1 = box
    sides = {
        "POUTRES_PRINC": (v.beam_side_mm / 1e3, v.beam_side_mm / 1e3),
        "PANNES_SEC": (v.purlin_side_mm / 1e3, v.purlin_side_mm / 1e3),
        "PANNE_RIVE": (v.purlin_side_mm / 1e3, v.purlin_side_mm / 1e3),
        "MONTANTS": (v.post_side_mm / 1e3, v.post_side_mm / 1e3),
        "DIAGONALES": (v.post_side_mm / 1e3, v.post_side_mm / 1e3),
        "CHEVETRES": (v.cap_width, 0.40),
        "LONGRINES": (0.40, 0.40),
    }

    def inside(p: Point3) -> bool:
        return x0 - 1e-9 <= p[0] <= x1 + 1e-9 and y0 - 1e-9 <= p[1] <= y1 + 1e-9

    def clip(a: Point3, b: Point3) -> tuple[Point3, Point3] | None:
        """The part of segment a–b inside the box in X and Y (Liang–Barsky)."""
        ta, tb = 0.0, 1.0
        for k, lo_, hi_ in ((0, x0, x1), (1, y0, y1)):
            d = b[k] - a[k]
            if abs(d) < 1e-12:
                if not lo_ - 1e-9 <= a[k] <= hi_ + 1e-9:
                    return None
                continue
            t0, t1 = (lo_ - a[k]) / d, (hi_ - a[k]) / d
            ta, tb = max(ta, min(t0, t1)), min(tb, max(t0, t1))
        if tb <= ta + 1e-12:
            return None
        pa = tuple(a[k] + ta * (b[k] - a[k]) for k in range(3))
        pb = tuple(a[k] + tb * (b[k] - a[k]) for k in range(3))
        return pa, pb  # type: ignore[return-value]

    faces: list[list[Point3]] = []
    colors: list[Any] = []
    drawn: set[str] = set()

    def add(fs: list[list[Point3]], family: str) -> None:
        faces.extend(fs)
        colors.extend([COLORS[family]] * len(fs))
        drawn.add(family)

    flank = g.parameters["B"] / 2.0 - v.beam_side_mm / 2e3
    for m in g.members:
        if m.family == "PILES":
            continue
        fam = FAMILY_OF.get(m.family, m.family)
        a, b = m.points[0], m.points[-1]
        if m.family == "LONGRINES":
            # longrines dessinées entre les nus des chevêtres (angles dans le chevêtre)
            jeu = g.parameters["JEU"]
            a = (a[0] - jeu + v.cap_width / 2.0, a[1], a[2])
            b = (b[0] + jeu - v.cap_width / 2.0, b[1], b[2])
        if m.family == "MONTANTS":
            # le montant aboute le flanc des poutres principales
            a = (a[0], max(a[1], -flank), a[2])
            b = (b[0], min(b[1], flank), b[2])
        cut = clip(a, b)
        if cut is None:
            continue
        w, h = sides[m.family]
        for pa, pb in pieces(cut[0], cut[1], step):
            if m.family == "CHEVETRES":
                # le chevêtre est porté selon Y : largeur selon X
                add(
                    slab(
                        pa[0] - w / 2,
                        pa[0] + w / 2,
                        pa[1],
                        pb[1],
                        pa[2] - h / 2,
                        pa[2] + h / 2,
                    ),
                    fam,
                )
            else:
                add(prism(pa, pb, w, h), fam)
    for m in g.family("PILES"):
        a, b = m.points[0], m.points[-1]
        if inside(a) and z0 <= min(a[2], b[2]) and max(a[2], b[2]) <= z1:
            add(cylinder(a[0], a[1], min(a[2], b[2]), max(a[2], b[2]), 0.25), "PILES")
    for f in g.footings:
        if f.xs[0] < x1 and f.xs[-1] > x0 and z0 <= f.z <= z1:
            add(
                slab(f.xs[0], f.xs[-1], f.ys[0], f.ys[-1], f.z - 0.10, f.z + 0.10),
                "SEMELLE",
            )
    lv = g.levels
    for ax_ in g.axes:
        p = ax_.pin
        if inside(p) and z0 <= p[2] <= z1:
            add(
                slab(
                    p[0] - 0.06,
                    p[0] + 0.06,
                    p[1] - 0.08,
                    p[1] + 0.08,
                    lv["dessus_chevetre"],
                    lv["sous_face_poutres"],
                ),
                "APPUIS",
            )
    for y in (-g.parameters["B"] / 2.0, g.parameters["B"] / 2.0):
        if inside((0.0, y, 0.0)):
            add(
                slab(
                    -0.12,
                    0.10,
                    y - 0.10,
                    y + 0.10,
                    lv["sous_face_poutres"] - 0.25,
                    lv["sous_face_poutres"],
                ),
                "APPUIS",
            )
    return faces, colors, drawn


def axes3d(
    fig: Any,
    rect: Sequence[float],
    lims: Sequence[tuple[float, float]],
    elev: float,
    azim: float,
    zoom: float = 1.0,
) -> Any:
    ax = fig.add_axes(rect, projection="3d")
    ax.set_proj_type("ortho")
    ax.view_init(elev=elev, azim=azim)
    for setter, (lo, hi) in zip(
        (ax.set_xlim, ax.set_ylim, ax.set_zlim), lims, strict=True
    ):
        setter(lo, hi)
    ax.set_box_aspect(tuple(hi - lo for lo, hi in lims), zoom=zoom)
    ax.set_axis_off()
    return ax


def draw_solids(ax: Any, faces: list[list[Point3]], colors: list[Any]) -> None:
    coll = Poly3DCollection(
        faces,
        facecolors=colors,
        edgecolors=[_darker(c, 0.85) for c in colors],
        linewidths=0.2,
    )
    ax.add_collection3d(coll)


# --------------------------------------------------------------------------- lines


def segments(
    vd: VariantData51ter, u: FloatArray | None = None, a: float = 0.0
) -> dict[str, FloatArray]:
    """Per family, the element segments [n, 2, 3] of the model, moved by a × u."""
    c = np.asarray(vd.model.coords, dtype=float)[:, :3]
    if u is not None:
        c = c + a * u[:, :3]
    out: dict[str, list[Any]] = {}
    for e in vd.model.elements.values():
        fam = FAMILY_OF.get(e.family, e.family)
        if fam not in LINE_WIDTH:
            continue
        out.setdefault(fam, []).append(c[np.asarray(e.nodes) - 1])
    return {k: np.asarray(v) for k, v in out.items()}


def draw_lines3d(
    ax: Any, segs: dict[str, FloatArray], *, ghost: bool = False, scale: float = 1.0
) -> None:
    for fam, s in segs.items():
        ax.add_collection3d(
            Line3DCollection(
                list(s),
                colors=GHOST if ghost else COLORS[fam],
                linewidths=(0.6 if ghost else LINE_WIDTH[fam] * scale),
            )
        )


def draw_footings3d(ax: Any, g: Geometry51ter) -> None:
    faces: list[list[Point3]] = []
    for f in g.footings:
        faces += slab(f.xs[0], f.xs[-1], f.ys[0], f.ys[-1], f.z - 0.10, f.z + 0.10)
    ax.add_collection3d(
        Poly3DCollection(
            faces,
            facecolors=COLORS["SEMELLE"],
            edgecolors=_darker(COLORS["SEMELLE"]),
            linewidths=0.2,
            alpha=0.55,
        )
    )


def overall_view(
    vd: VariantData51ter, title: str, azim: float, path: Path, *, label_side: float
) -> None:
    g = vd.g
    v = vd.variant
    assert isinstance(v, Variant54)
    fig = plt.figure(figsize=(WIDTH_IN, 4.2))
    x_max = max(s.x1 for s in g.spans)
    faces, colors, _ = solids(v, g, (-0.3, x_max + 0.1, -1.7, 1.7, -9.0, 9.0), 0.8)
    pts = np.asarray([p for f in faces for p in f])
    lims = [(float(pts[:, k].min()), float(pts[:, k].max())) for k in range(3)]
    ax = axes3d(fig, (0.0, 0.1, 1.0, 0.8), lims, 20.0, azim, zoom=1.9)
    draw_solids(ax, faces, colors)
    for f in g.footings:
        ax.text(
            f.centre[0],
            label_side * 1.6,
            f.z - 0.15,
            f.pier,
            ha="center",
            fontsize=TEXT_PT,
        )
    ax.text(0.0, label_side * 1.6, 0.9, "culée", ha="center", fontsize=TEXT_PT)
    ax.text(x_max, label_side * 1.6, 0.9, "porte-à-faux", ha="center", fontsize=TEXT_PT)
    fig.suptitle(title, fontsize=TEXT_PT + 1, y=0.98)
    legend(
        fig,
        (
            "POUTRES_PRINC",
            "PANNES_SEC",
            "MONTANTS",
            "DIAGONALES",
            "CHEVETRES",
            "LONGRINES",
            "PILES",
            "SEMELLE",
            "APPUIS",
        ),
    )
    save(fig, path)


def volume_view(
    v: Variant54,
    g: Geometry51ter,
    title: str,
    box: tuple[float, float, float, float, float, float],
    elev: float,
    azim: float,
    path: Path,
    *,
    height_in: float = 4.6,
    notes: Sequence[tuple[Point3, str]] = (),
    step: float = 0.2,
    zoom: float = 1.3,
) -> None:
    fig = plt.figure(figsize=(WIDTH_IN, height_in))
    faces, colors, drawn = solids(v, g, box, step)
    pts = np.asarray([p for f in faces for p in f])
    lims = [
        (float(pts[:, k].min()) - 0.05, float(pts[:, k].max()) + 0.05) for k in range(3)
    ]
    ax = axes3d(fig, (0.0, 0.09, 1.0, 0.85), lims, elev, azim, zoom=zoom)
    draw_solids(ax, faces, colors)
    for p, text in notes:
        ax.text(*p, text, fontsize=TEXT_PT, ha="center")
    fig.suptitle(title, fontsize=TEXT_PT + 1, y=0.98)
    legend(fig, [f for f in COLORS if f in drawn])
    save(fig, path)


# --------------------------------------------------------------------------- 2-D views


def section_view(v: Variant54, g: Geometry51ter, path: Path) -> None:
    """View 6: transverse section on the axis of C1 of P1."""
    lv = g.levels
    f = g.footings[0]
    p = g.parameters
    half = p["B"] / 2.0
    beam, thick = v.beam_side_mm / 1e3, v.beam_thickness_mm / 1e3
    purlin = v.purlin_side_mm / 1e3
    post = v.post_side_mm / 1e3
    lo, hi = v.cap_ends
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.8))
    top_footing = f.z + 0.10

    def rect(y: float, z: float, w: float, h: float, fam: str, **kw: Any) -> None:
        ax.add_patch(
            Rectangle(
                (y, z),
                w,
                h,
                facecolor=kw.pop("fc", COLORS[fam]),
                edgecolor=_darker(COLORS[fam]),
                linewidth=0.8,
                **kw,
            )
        )

    rect(f.ys[0], f.z - 0.10, f.ys[-1] - f.ys[0], 0.20, "SEMELLE")
    for y in p["Y_PILES"]:
        rect(y - 0.25, top_footing, 0.50, lv["tete_piles"] - top_footing, "PILES")
    rect(
        lo,
        lv["tete_piles"],
        hi - lo,
        lv["dessus_chevetre"] - lv["tete_piles"],
        "CHEVETRES",
    )
    rect(
        -half + beam / 2,
        lv["montants"] - post / 2,
        2 * half - beam,
        post,
        "MONTANTS",
        fc="none",
        linestyle="--",
    )
    for s in (-1, 1):
        y = s * half
        rect(
            y - 0.075,
            lv["dessus_chevetre"],
            0.15,
            lv["sous_face_poutres"] - lv["dessus_chevetre"],
            "APPUIS",
        )
        ax.add_patch(
            Circle(
                (y, lv["axe_appui"]),
                0.012,
                facecolor="white",
                edgecolor="black",
                linewidth=0.8,
                zorder=5,
            )
        )
        rect(y - beam / 2, lv["poutres"] - beam / 2, beam, beam, "POUTRES_PRINC")
        ax.add_patch(
            Rectangle(
                (y - beam / 2 + thick, lv["poutres"] - beam / 2 + thick),
                beam - 2 * thick,
                beam - 2 * thick,
                facecolor="white",
                edgecolor="none",
            )
        )
    for y in p["Y_PANNES"]:
        rect(y - purlin / 2, lv["pannes"] - purlin / 2, purlin, purlin, "PANNES_SEC")
    ax.add_patch(
        Rectangle(
            (-p["LARGEUR_TABLIER"] / 2, lv["dessus_tablier"]),
            p["LARGEUR_TABLIER"],
            PLANKS_THICKNESS,
            facecolor="#d2a86e",
            edgecolor="#8a6a3c",
            linewidth=0.8,
        )
    )

    def level(z: float, text: str, y: float = 1.45) -> None:
        ax.plot([y - 0.05, y + 0.05], [z, z], color="black", linewidth=0.8)
        ax.text(y + 0.08, z, text, va="center", fontsize=TEXT_PT)

    level(lv["dessus_tablier"], f"tablier +{_fr(lv['dessus_tablier'], 2)}")
    ax.plot(
        [-half, -1.55], [lv["axe_appui"], lv["axe_appui"]], color="black", linewidth=0.6
    )
    ax.text(
        -1.6,
        lv["axe_appui"],
        f"axe +{_fr(lv['axe_appui'], 3)}",
        ha="right",
        va="center",
        fontsize=TEXT_PT,
    )
    level(lv["dessus_chevetre"], f"chevêtre +{_fr(lv['dessus_chevetre'], 2)}")
    level(lv["tete_piles"], f"arase +{_fr(lv['tete_piles'], 2)}")
    level(top_footing, f"semelle {_fr(top_footing, 2)}")
    zc = f.z - 0.32
    for y in (lo, hi):
        ax.plot(
            [y, y],
            [lv["tete_piles"], zc - 0.04],
            color="black",
            linewidth=0.5,
            linestyle=":",
        )
    ax.annotate(
        "", (lo, zc), (hi, zc), arrowprops={"arrowstyle": "<->", "linewidth": 0.8}
    )
    ax.text(
        0.0,
        zc - 0.04,
        f"chevêtre {_fr(v.cap_width, 2)} (selon X) × 0,40 : Y de {_fr(lo, 2)} à +{_fr(hi, 2)}",
        ha="center",
        va="top",
        fontsize=TEXT_PT,
    )
    for s in (-1, 1):
        ax.text(
            s * half,
            lv["dessus_tablier"] + 0.12,
            f"{'−' if s < 0 else '+'}{_fr(half, 2)}",
            ha="center",
            fontsize=TEXT_PT,
        )
    ax.set_xlim(-2.1, 2.4)
    ax.set_ylim(f.z - 0.6, lv["dessus_tablier"] + 0.25)
    ax.set_aspect("equal")
    ax.set_xlabel("Y (m)")
    ax.set_ylabel("Z (m NGF)")
    ax.set_title("Panne B – coupe transversale sur la palée P1", fontsize=TEXT_PT + 1)
    extra = [
        Patch(
            facecolor="#d2a86e", edgecolor="#8a6a3c", label="platelage bois (dessin)"
        ),
        Patch(
            facecolor="none",
            edgecolor=COLORS["MONTANTS"],
            linestyle="--",
            label="montant au droit de la palée",
        ),
    ]
    legend(
        fig,
        ("POUTRES_PRINC", "PANNES_SEC", "CHEVETRES", "PILES", "SEMELLE", "APPUIS"),
        extra,
    )
    save(fig, path)


def plan_view(v: Variant54, g: Geometry51ter, path: Path) -> None:
    """View 7: plan of the truss of T1 and PT1, posts dimensioned, nodes at e = 0,25,
    purlins in transparency."""
    p = g.parameters
    half = p["B"] / 2.0
    yd = half - v.e_diag
    beam = v.beam_side_mm / 1e3
    post = v.post_side_mm / 1e3
    purlin = v.purlin_side_mm / 1e3
    spans = [s for s in g.spans if s.name in ("T1", "PT1")]
    x_end = spans[-1].x1
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 4.2))

    def bar(
        a: tuple[float, float],
        b: tuple[float, float],
        w: float,
        fam: str,
        alpha: float = 1.0,
        z: int = 2,
    ) -> None:
        d = np.array([b[0] - a[0], b[1] - a[1]])
        n = np.array([-d[1], d[0]]) / np.linalg.norm(d) * w / 2
        pa, pb = np.array(a), np.array(b)
        ax.add_patch(
            Polygon(
                [pa + n, pb + n, pb - n, pa - n],
                closed=True,
                facecolor=COLORS[fam],
                edgecolor=_darker(COLORS[fam]),
                linewidth=0.4,
                alpha=alpha,
                zorder=z,
            )
        )

    for m in g.members:
        if m.span not in ("T1", "PT1"):
            continue
        a, b = m.points[0][:2], m.points[-1][:2]
        if m.family == "POUTRES_PRINC":
            bar(a, b, beam, "POUTRES_PRINC", z=3)
        elif m.family == "MONTANTS":
            bar(a, b, post, "MONTANTS", z=2)
        elif m.family == "DIAGONALES":
            bar(a, b, post, "DIAGONALES", z=2)
        elif m.family == "PANNES_SEC":
            bar(a, b, purlin, "PANNES_SEC", alpha=0.35, z=4)
    nodes = [
        (m.points[0][0], y)
        for m in g.family("MONTANTS")
        if m.span in ("T1", "PT1")
        for y in (-yd, yd)
    ]
    ax.scatter(
        [n[0] for n in nodes], [n[1] for n in nodes], s=14, color="black", zorder=6
    )
    xs = sorted({m.points[0][0] for m in g.family("MONTANTS") if m.span == "T1"})
    y_dim = half + 0.35
    for x in xs:
        ax.plot([x, x], [half + 0.12, y_dim + 0.05], color="black", linewidth=0.6)
        ax.text(x, y_dim + 0.08, _fr(x, 2), ha="center", va="bottom", fontsize=TEXT_PT)
    ax.plot([xs[0], xs[-1]], [y_dim, y_dim], color="black", linewidth=0.6)
    pt = spans[-1]
    ax.plot([pt.x1, pt.x1], [half + 0.12, y_dim + 0.05], color="black", linewidth=0.6)
    ax.plot([pt.x0, pt.x1], [y_dim, y_dim], color="black", linewidth=0.6)
    ax.text(
        pt.x1, y_dim + 0.08, _fr(pt.x1, 2), ha="center", va="bottom", fontsize=TEXT_PT
    )
    ax.text(
        (pt.x0 + pt.x1) / 2,
        y_dim - 0.06,
        "PT1",
        ha="center",
        va="top",
        fontsize=TEXT_PT,
    )
    # cote de e : de l'axe de la poutre (+B/2) au nœud (+B/2 − e), à gauche du montant
    x_e = xs[1] - 0.22
    ax.plot([x_e, x_e], [yd, half], color="black", linewidth=1.0, zorder=10)
    for y in (yd, half):
        ax.plot(
            [x_e - 0.05, x_e + 0.05], [y, y], color="black", linewidth=1.0, zorder=10
        )
    ax.text(
        x_e - 0.08,
        (half + yd) / 2,
        "e",
        ha="right",
        va="center",
        fontsize=TEXT_PT,
        zorder=10,
    )
    ax.annotate(
        "nœud diagonale–montant à e = 0,25 m de l'axe de la poutre",
        (xs[1], -yd),
        (xs[0], -half - 0.42),
        fontsize=TEXT_PT,
        va="top",
        ha="left",
        arrowprops={"arrowstyle": "->", "linewidth": 0.8},
        zorder=8,
    )
    ax.set_xlim(-0.3, x_end + 0.3)
    ax.set_ylim(-half - 0.95, y_dim + 0.75)
    ax.set_aspect("equal")
    ax.set_xlabel("X (m), depuis la culée")
    ax.set_ylabel("Y (m)")
    ax.set_title(
        "Panne B – treillis horizontal des travées T1 et PT1 (vue en plan)",
        fontsize=TEXT_PT + 1,
    )
    extra = [
        Patch(
            facecolor=COLORS["PANNES_SEC"], alpha=0.35, label="pannes (en transparence)"
        ),
        mpl.lines.Line2D(
            [],
            [],
            marker="o",
            color="black",
            linestyle="none",
            markersize=4,
            label="nœuds diagonale–montant",
        ),
    ]
    legend(fig, ("POUTRES_PRINC", "MONTANTS", "DIAGONALES"), extra)
    save(fig, path)


# --------------------------------------------------------------------------- deformed shapes


def nodal(vd: VariantData51ter, coefs: dict[str, float]) -> FloatArray:
    n = len(vd.model.coords)
    u = np.zeros((n, 6))
    for case, c in coefs.items():
        d = vd.tables.depl[case]
        for node, val in d.items():
            u[node - 1] += c * np.asarray(val[:6], dtype=float)
    return u


def abutment_rx(vd: VariantData51ter) -> dict[str, FloatArray]:
    nodes = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    return {
        c: np.array([sum(float(vd.tables.reac[c][n][0]) for n in nodes)])
        for c in vd.cases
    }


def governing_of(
    vd: VariantData51ter,
    f: dict[str, FloatArray],
    state: str,
    q: int | None = None,
    *,
    without: tuple[str, ...] = (),
) -> tuple[float, str, dict[str, float], int]:
    """The larger |extreme| (max or min) of a quantity over `state`, its combination."""
    best: tuple[float, str, dict[str, float], int] | None = None
    for sign in (1.0, -1.0):
        ext = envelope(vd.bs, vd.ev, f, state, sign=sign, without=without)
        k = int(np.argmax(np.abs(ext.value))) if q is None else q
        name, coefs = governing(vd.bs, vd.ev, ext, k)
        if best is None or abs(float(ext.value[k])) > abs(best[0]):
            best = (float(ext.value[k]), name, coefs, k)
    assert best is not None
    return best


def deformed_iso(
    vd: VariantData51ter, u: FloatArray, amp: float, title: str, note: str, path: Path
) -> None:
    g = vd.g
    fig = plt.figure(figsize=(WIDTH_IN, 3.9))
    x_max = max(s.x1 for s in g.spans)
    lims = [(-0.5, x_max + 0.5), (-1.8, 1.8), (min(f.z for f in g.footings) - 0.2, 1.6)]
    ax = axes3d(fig, (0.0, 0.1, 1.0, 0.75), lims, 20.0, 215.0, zoom=1.45)
    draw_lines3d(ax, segments(vd), ghost=True)
    draw_lines3d(ax, segments(vd, u, amp), scale=0.8)
    fig.suptitle(title, fontsize=TEXT_PT + 1, y=0.99)
    fig.text(0.5, 0.9, note, ha="center", fontsize=TEXT_PT)
    legend(
        fig,
        (
            "POUTRES_PRINC",
            "PANNES_SEC",
            "MONTANTS",
            "DIAGONALES",
            "CHEVETRES",
            "LONGRINES",
            "PILES",
        ),
        [mpl.lines.Line2D([], [], color=GHOST, label="non déformée")],
    )
    save(fig, path)


def deformed_2d(
    vd: VariantData51ter,
    u: FloatArray,
    amp: float,
    axes: tuple[int, int],
    title: str,
    notes: Sequence[tuple[float, float, str, str]],
    path: Path,
    *,
    families: Sequence[str],
    height: float = 3.8,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    table: Sequence[tuple[float, Sequence[str]]] = (),
    row_labels: Sequence[str] = (),
    only: int | None = None,
) -> None:
    """A deformed shape in a plane; `table`: columns (x, lines) written under the
    drawing, inside the axes, one line per row of `row_labels`."""
    i, j = axes
    if only is not None:  # seule la composante représentée est amplifiée
        mask = np.zeros_like(u)
        mask[:, only] = u[:, only]
        u = mask
    fig, ax = plt.subplots(figsize=(WIDTH_IN, height))
    for ghost, segs in ((True, segments(vd)), (False, segments(vd, u, amp))):
        for fam in families:
            if fam not in segs:
                continue
            s = segs[fam][:, :, [i, j]]
            ax.add_collection(
                LineCollection(
                    list(s),
                    colors=GHOST if ghost else COLORS[fam],
                    linewidths=0.6 if ghost else LINE_WIDTH[fam] * 0.7,
                    zorder=1 if ghost else 2,
                )
            )
    ax.autoscale()
    for x, y, text, va in notes:
        ax.text(
            x,
            y,
            text,
            ha="center",
            va=va,
            fontsize=TEXT_PT,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5},
        )
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    blend = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
    n_rows = max((len(lines) for _, lines in table), default=0)
    for x, lines in table:
        for k, line in enumerate(lines):
            ax.text(
                x,
                0.03 + (n_rows - 1 - k) * 0.085,
                line,
                transform=blend,
                ha="center",
                va="bottom",
                fontsize=TEXT_PT,
            )
    for k, label in enumerate(row_labels):
        ax.text(
            0.01,
            0.03 + (n_rows - 1 - k) * 0.085,
            label,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=TEXT_PT,
        )
    ax.set_xlabel("X (m), depuis la culée")
    ax.set_ylabel("Y (m)" if j == 1 else "Z (m NGF)")
    ax.set_title(title, fontsize=TEXT_PT + 1)
    ax.grid(True, color="#eeeeee")
    legend(fig, families, [mpl.lines.Line2D([], [], color=GHOST, label="non déformée")])
    save(fig, path)


def amplification(peak_m: float, target_m: float) -> int:
    ok = [a for a in (1, 2, 5, 10, 20, 25, 50, 100, 200) if a * peak_m <= target_m]
    return ok[-1] if ok else 1


# --------------------------------------------------------------------------- step


def png_check(path: Path) -> dict[str, Any]:
    with Image.open(path) as im:
        w, h = im.size
        dpi = im.info.get("dpi", (0, 0))
        arr = np.asarray(im.convert("RGB"))
    corners = [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]
    white = all((c >= 250).all() for c in corners)
    return {
        "octets": path.stat().st_size,
        "largeur": w,
        "hauteur": h,
        "dpi": [round(float(d)) for d in dpi],
        "fond_blanc": bool(white),
        "largeur_max_16cm": w <= MAX_WIDTH_PX,
        "conforme": path.stat().st_size > 0
        and white
        and round(float(dpi[0])) == DPI
        and w <= MAX_WIDTH_PX,
    }


def step_vues(
    ctx: ProjectContext, codes: list[str], state: dict[str, Any]
) -> dict[str, Any]:
    from pontons_alu_01 import deplacements_lot53 as d53  # noqa: PLC0415
    from pontons_alu_01.exports_lot54 import load  # noqa: PLC0415
    from pontons_alu_01.variantes_lot54 import variants  # noqa: PLC0415

    _style()
    out = ctx.results_dir / LOT / "vues"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    report: dict[str, Any] = {}
    if CODE not in codes:
        return report
    v = variants()[CODE]
    vd = load(ctx, CODE, state)
    g = vd.g
    lv = g.levels
    f1, f5 = g.footings[0], g.footings[-1]
    x_max = max(s.x1 for s in g.spans)

    def name(k: str, s: str) -> Path:
        return out / f"{PREFIX}_vue{k}_{s}.png"

    overall_view(
        vd,
        "Panne B – vue d'ensemble depuis le porte-à-faux",
        35.0,
        name("01", "ensemble_depuis_porte_a_faux"),
        label_side=1.0,
    )
    overall_view(
        vd,
        "Panne B – vue d'ensemble depuis la culée",
        215.0,
        name("02", "ensemble_depuis_culee"),
        label_side=-1.0,
    )
    t1 = g.spans[0]
    volume_view(
        v,
        g,
        "Panne B – culée et travée T1",
        (-0.15, t1.x1 + 0.05, -1.6, 1.6, -9.0, 9.0),
        24.0,
        230.0,
        name("03", "culee_travee_T1"),
        height_in=3.6,
        notes=[
            ((0.0, 0.0, lv["dessus_tablier"] + 0.35), "culée"),
            ((f1.centre[0], 0.0, lv["dessus_tablier"] + 0.35), "P1"),
        ],
        zoom=1.6,
    )
    volume_view(
        v,
        g,
        "Panne B – palée P1",
        (f1.xs[0] - 0.05, f1.xs[-1] + 0.05, -1.6, 1.6, -9.0, 9.0),
        18.0,
        235.0,
        name("04", "palee_P1"),
        height_in=5.4,
        notes=[((f1.centre[0], 0.0, lv["dessus_tablier"] + 0.25), "P1")],
    )
    volume_view(
        v,
        g,
        "Panne B – palée P5, petite travée PT5 et porte-à-faux",
        (f5.xs[0] - 0.4, x_max + 0.05, -1.6, 1.6, -9.0, 9.0),
        20.0,
        40.0,
        name("05", "palee_P5_PT5_porte_a_faux"),
        height_in=5.2,
        notes=[
            ((f5.centre[0], 0.0, lv["dessus_tablier"] + 0.4), "P5"),
            ((x_max, 0.0, lv["dessus_tablier"] + 0.4), "porte-à-faux"),
        ],
        zoom=0.95,
    )
    section_view(v, g, name("06", "coupe_transversale_P1"))
    plan_view(v, g, name("07", "treillis_T1_PT1_plan"))
    t2 = g.spans[2]
    xn = t2.x0 + 1.25
    volume_view(
        v,
        g,
        "Panne B – nœud poutre, montant, diagonale et panne",
        (xn - 0.75, xn + 0.85, 0.1, 1.06, 1.1, 1.5),
        32.0,
        300.0,
        name("08", "noeud_poutre_montant_diagonale_panne"),
        height_in=4.6,
        step=0.05,
    )
    # Vue 9 : ELU fondamental, ΣRX de la culée extrême.
    rx = abutment_rx(vd)
    val, comb, coefs, _ = governing_of(vd, rx, "ELU_fondamental")
    u9 = nodal(vd, coefs)
    deformed_iso(
        vd,
        u9,
        10.0,
        "Panne B – déformée à l'ELU fondamental (réaction longitudinale maximale de la culée)",
        f"ΣRX de la culée = {_fr(val * 1e-3, 1)} kN ; déformée amplifiée × 10",
        name("09", "deformee_ELU_culee_RX"),
    )
    report["vue 9"] = {"SRX_culee_kN": val * 1e-3, "combinaison": comb}
    # Vue 10 : ELS caractéristique, flèche vers le haut de T2 (P51, P62 : relative à la corde, actions variables seules, sans la composante tangentielle d'accostage).
    f_t2, where, length = deflection_arrays(vd, "T2")
    f_t2 = without_tangential(f_t2)
    ext = envelope(vd.bs, vd.ev, f_t2, "ELS_caracteristique", sign=1.0, without=("G",))
    q = int(np.argmax(ext.value))
    comb10, coefs10 = governing(vd.bs, vd.ev, ext, q)
    coefs10 = {
        c: k
        for c, k in coefs10.items()
        if c not in ("G1", "G2", "DEJ") and not c.startswith(("ACX_", "ACZ_"))
    }
    u10 = nodal(vd, coefs10)
    up = float(ext.value[q]) * MM
    amp10 = amplification(float(np.abs(u10[:, 2]).max()), 0.6)
    x_t2 = (t2.x0 + t2.x1) / 2
    deformed_2d(
        vd,
        u10,
        amp10,
        (0, 2),
        "Panne B – déformée à l'ELS caractéristique (houle, soulèvement maximal de T2)",
        [
            (
                x_t2,
                2.25,
                f"flèche de T2 vers le haut : {_fr(up)} mm (L/{length * MM / abs(up):.0f}) ;"
                f" déformée amplifiée × {amp10}",
                "bottom",
            )
        ],
        name("10", "deformee_ELS_c_fleche_T2"),
        families=("POUTRES_PRINC", "LONGRINES", "PILES"),
        height=3.6,
        xlim=(-0.5, 23.0),
        ylim=(min(f.z for f in g.footings[:3]) - 0.3, 3.0),
    )
    report["vue 10"] = {
        "fleche_mm": up,
        "lieu": where[q],
        "amplification": amp10,
        "combinaison": comb10,
        "definition": "relative à la corde, actions variables seules, sans composante tangentielle d'accostage (P51, P62)",
    }
    # Vues 11 A, B, C : celles du lot 53.
    r = d53.compute(ctx, state, vd)
    choices = {
        c.key: c
        for c in d53.field_choices(r.pts, r.qs, r.events, r.ev_values, r.combos)
    }

    def depl_of(u: FloatArray) -> dict[int, FloatArray]:
        return {n + 1: u[n] for n in range(u.shape[0])}

    for letter, key, kind, comp, title, fname in (
        (
            "A",
            "CO_ELSC_DY",
            "plan",
            1,
            "Panne B – déplacements transversaux DY, ELS caractéristique",
            "11A_DY_ELS_c",
        ),
        (
            "B",
            "CO_ELUA_DY",
            "plan",
            1,
            "Panne B – déplacements transversaux DY, ELU accidentel",
            "11B_DY_ELU_acc",
        ),
        (
            "C",
            "CO_ELSC_DX_HT",
            "elevation",
            0,
            "Panne B – déplacements longitudinaux DX hors thermique, ELS caractéristique",
            "11C_DX_hors_T_ELS_c",
        ),
    ):
        u = nodal(vd, choices[key].coefficients)
        peak = float(np.abs(u[:, comp]).max())
        amp = amplification(peak, 0.9 if kind == "plan" else 1.2)
        notes = []
        columns: list[tuple[float, Sequence[str]]] = []
        values: dict[str, Any] = {}
        top = 1.65 if kind == "plan" else 1.75
        low = -1.45 if kind == "plan" else min(f.z for f in g.footings) - 0.25
        for f in g.footings:
            deck = (
                max(
                    (
                        d53.point_value(p, depl_of(u), vd.model.coords)[comp]
                        for p in r.pts
                        if p.place == f.pier and p.kind == "axe"
                    ),
                    key=abs,
                )
                * MM
            )
            head = (
                max(
                    (
                        d53.point_value(p, depl_of(u), vd.model.coords)[comp]
                        for p in r.pts
                        if p.place == f.pier and p.kind == "tete"
                    ),
                    key=abs,
                )
                * MM
            )
            columns.append((float(f.centre[0]), (f.pier, _fr(deck), _fr(head))))
            values[f.pier] = {"tablier_mm": deck, "tete_mm": head}
        tip = (
            max(
                (
                    d53.point_value(p, depl_of(u), vd.model.coords)[comp]
                    for p in r.pts
                    if p.kind == "porte_a_faux"
                ),
                key=abs,
            )
            * MM
        )
        notes.append((x_max - 4.0, top, f"bout du porte-à-faux : {_fr(tip)}", "bottom"))
        fams = (
            "POUTRES_PRINC",
            "PANNES_SEC",
            "MONTANTS",
            "DIAGONALES",
            "CHEVETRES",
            "LONGRINES",
        ) + (("PILES",) if kind == "elevation" else ())
        deformed_2d(
            vd,
            u,
            float(amp),
            (0, 1 if kind == "plan" else 2),
            f"{title}\n(valeurs en mm aux palées ; {'DY' if comp == 1 else 'DX'} amplifié × {amp})",
            notes,
            name(fname[:3], fname[4:]),
            families=fams,
            height=4.4 if kind == "plan" else 4.6,
            ylim=(-3.1, 2.2) if kind == "plan" else (low - 2.2, 2.3),
            table=columns,
            row_labels=("", "tablier", "tête de pile"),
            only=comp,
            xlim=(-9.5, x_max + 1.0),
        )
        report[f"vue 11{letter}"] = {
            "amplification": amp,
            "pic_mm": peak * MM,
            "palees": values,
            "porte_a_faux_mm": tip,
            "combinaison": choices[key].source,
        }
    pngs = {p.name: png_check(p) for p in sorted(out.glob("*.png"))}
    report["png"] = pngs
    report["reussi"] = len(pngs) == 13 and all(x["conforme"] for x in pngs.values())
    (out / "controle_png.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )
    print(
        f"{CODE} : {len(pngs)} PNG, contrôle {'RÉUSSI' if report['reussi'] else 'ÉCHEC'}"
    )
    return report


__all__ = ["COLORS", "step_vues", "trim"]
