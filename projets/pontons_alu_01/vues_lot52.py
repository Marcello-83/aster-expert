# ruff: noqa: E501 -- libellés des dessins, phrases entières
"""Views of lot 52 for PONTONS-ALU-01 (consigne § Vues et MED), variant B52.

- Views 1 to 5, 7 and 9: `scripts/paraview/vues_3d_pontons_52.py`, run by pvbatch
  (ParaView 5.11 of the Salomé-Méca image, no screen), from the CSV exports of the
  variant and the combinations written by the MED step (`combinaisons_vues.json`).
  View 1: from the cantilever; view 2: from the abutment; view 9: 3D zoom on a node main
  beam / post / diagonal / purlins.
- View 6 (transverse section at the axis of C1 of P1) and view 8 (plan of the horizontal
  truss of T1 and PT1): plane drawings by matplotlib from the geometry of the variant.
  View 6 draws the pin of P65 (schéma v4): axis Ø 24 along Y (a bar in this section),
  T stirrup (flange 12 mm, two ears 15 mm), cheeks 15 mm, plate 20 mm on 15 mm shims,
  M20 rods; the widths along Y that the schema does not dimension are read at its scale
  (representation).
- Each PNG is checked: not empty, 1 920 × 1 080 pixels at least.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

from aster_expert.projet.context import ProjectContext  # noqa: E402
from pontons_alu_01.generation_lot52 import geometry_of  # noqa: E402
from pontons_alu_01.geometrie_lot52 import diagonal_node  # noqa: E402
from pontons_alu_01.variantes_lot52 import variants  # noqa: E402
from pontons_alu_01.vues_lot51quater import (  # noqa: E402
    HEIGHT,
    PLANKS_TOP,
    WIDTH,
    png_size,
    run_pvbatch,
)

LOT = "lot52"
SCRIPT = (
    Path(__file__).resolve().parent / "scripts" / "paraview" / "vues_3d_pontons_52.py"
)
COLORS = {
    "POUTRES_PRINC": "#1f77b4",
    "MONTANTS": "#8cbfe6",
    "DIAGONALES": "#2ca02c",
    "PANNES_SEC": "#ff7f0e",
    "APPUI": "#e377c2",
}


def _fr(z: float) -> str:
    return f"{z:+.3f}".replace(".", ",")


def section_view(code: str, path: Path) -> None:  # noqa: PLR0915 -- un dessin, pièce par pièce
    """View 6: transverse section at the axis of C1 of P1 (X = station 1), pin of P65;
    left the whole section, right a zoom on the pin of side YP (schéma v4, vue B)."""
    v = variants()[code]
    g = geometry_of(v)
    lv = g.levels
    f = g.footings[0]
    p = g.parameters
    half = p["B"] / 2.0
    beam = v.beam_side_mm / 1000.0
    purlin = v.purlin_side_mm / 1000.0
    post = v.post_side_mm / 1000.0
    za = lv["axe_appui"]
    top_footing = f.z + 0.10
    fig, (ax, zoom) = plt.subplots(
        1, 2, figsize=(WIDTH / 100, HEIGHT / 100), dpi=100, width_ratios=(1.25, 1.0)
    )
    pieces: list[tuple[float, float, float, float, str, str | None]] = [
        (
            -1.0,
            lv["dessus_tablier"],
            2.0,
            PLANKS_TOP - lv["dessus_tablier"],
            "#c8a165",
            "platelage (dessin, non modélisé)",
        ),
        (
            -half + beam / 2,
            lv["montants"] - post / 2,
            2 * half - beam,
            post,
            COLORS["MONTANTS"],
            f"montant {v.post_label} au droit de l'appui (axe +1,29, P64)",
        ),
    ]
    for k, y in enumerate(p["Y_PANNES"]):
        pieces.append(
            (
                y - purlin / 2,
                lv["pannes"] - purlin / 2,
                purlin,
                purlin,
                COLORS["PANNES_SEC"],
                f"pannes {v.purlin_label} posées sur le montant" if k == 0 else None,
            )
        )
    for k, s in enumerate((-1, 1)):
        y = s * half
        first = k == 0
        pieces += [
            (
                y - beam / 2,
                lv["poutres"] - beam / 2,
                beam,
                beam,
                COLORS["POUTRES_PRINC"],
                "poutres principales 200 × 200" if first else None,
            ),
            (
                y - 0.075,
                za + 0.013,
                0.150,
                0.012,
                "#b07aa1",
                "étrier en T inox duplex : semelle 12 mm (boulons aveugles M12)"
                if first
                else None,
            ),
            (
                y - 0.016,
                za - 0.040,
                0.015,
                0.053,
                "#d4a6c8",
                "oreilles 15 mm, une par travée, côte à côte" if first else None,
            ),
            (y + 0.001, za - 0.040, 0.015, 0.053, "#d4a6c8", None),
            (
                y - 0.033,
                za - 0.050,
                0.015,
                0.060,
                "#9c9c9c",
                "joues 15 mm soudées sur la platine" if first else None,
            ),
            (y + 0.018, za - 0.050, 0.015, 0.060, "#9c9c9c", None),
            (
                y - 0.045,
                za - 0.012,
                0.090,
                0.024,
                COLORS["APPUI"],
                "axe inox Ø 24 selon Y (barre transversale)" if first else None,
            ),
            (
                y - 0.17,
                za - 0.070,
                0.34,
                0.020,
                "#7f7f7f",
                "platine inox 20 mm" if first else None,
            ),
            (
                y - 0.17,
                za - 0.085,
                0.34,
                0.015,
                "#bdbdbd",
                "calage 15 mm" if first else None,
            ),
            (
                y - 0.130,
                lv["dessus_chevetre"] - 0.15,
                0.020,
                0.19,
                "#6b6b6b",
                "tiges M20 A4-80 scellées" if first else None,
            ),
            (y + 0.110, lv["dessus_chevetre"] - 0.15, 0.020, 0.19, "#6b6b6b", None),
        ]
    cap = list(p["Y_CHEVETRE"])
    pieces.append(
        (
            cap[0],
            lv["tete_piles"],
            cap[1] - cap[0],
            lv["dessus_chevetre"] - lv["tete_piles"],
            "#9467bd",
            "chevêtre 0,40 × 0,40",
        )
    )
    for k, y in enumerate(p["Y_PILES"]):
        pieces.append(
            (
                y - 0.25,
                top_footing,
                0.50,
                lv["tete_piles"] - top_footing,
                "#8c564b",
                "piles Ø 0,50" if k == 0 else None,
            )
        )
    pieces.append(
        (
            f.ys[0],
            f.z - 0.10,
            f.ys[-1] - f.ys[0],
            0.20,
            "#7f7f7f",
            "semelle 2,60 × 0,20",
        )
    )
    for target in (ax, zoom):
        for y0, z0, w, h, color, label in pieces:
            target.add_patch(
                Rectangle(
                    (y0, z0),
                    w,
                    h,
                    facecolor=color,
                    edgecolor="black",
                    lw=0.4,
                    label=label if target is zoom else None,
                )
            )
        target.set_aspect("equal")
        target.set_xlabel("Y (m)")
    ax.set_ylabel("Z (m NGF)")
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(f.z - 0.3, PLANKS_TOP + 0.15)
    ax.plot([0.6, 1.1], [f.z - 0.2] * 2, color="black", lw=3)
    ax.text(0.85, f.z - 0.22, "0,50 m", ha="center", va="top", fontsize=10)
    for z, label in (
        (PLANKS_TOP, "+1,445 dessus du platelage"),
        (lv["dessus_chevetre"], "+1,090 dessus du chevêtre"),
        (lv["tete_piles"], "+0,690 tête des piles"),
        (top_footing, f"{_fr(top_footing)} dessus de la semelle"),
        (f.z - 0.10, f"{_fr(f.z - 0.10)} fond de la semelle"),
    ):
        ax.plot([-1.55, -1.1], [z, z], color="black", lw=0.5)
        ax.text(
            -1.55, z + 0.01, label.replace(" ", " NGF  ", 1), fontsize=9, va="bottom"
        )
    ax.add_patch(
        Rectangle(
            (half - 0.25, za - 0.15),
            0.5,
            0.42,
            fill=False,
            edgecolor="#d62728",
            lw=1.2,
            ls="--",
        )
    )
    ax.set_title("coupe complète (cadre : zoom à droite)", fontsize=11)
    y0 = half
    zoom.set_xlim(y0 - 0.24, y0 + 0.66)
    zoom.set_ylim(lv["dessus_chevetre"] - 0.10, PLANKS_TOP + 0.02)
    levels = [
        (PLANKS_TOP, "dessus du platelage"),
        (lv["dessus_tablier"], "dessus des tubes et des pannes"),
        (lv["pannes"] - purlin / 2, "sous-face des pannes = dessus des montants"),
        (lv["poutres"], "axe des tubes 200 × 200"),
        (lv["montants"], "axe des montants et diagonales (P64)"),
        (lv["sous_face_poutres"], "sous-face des tubes"),
        (za + 0.013, "dessous des semelles d'étrier"),
        (za, "axe Ø 24 (P65)"),
        (za - 0.040, "bas des oreilles"),
        (za - 0.050, "dessus de platine"),
        (lv["dessus_chevetre"], "dessus du chevêtre"),
    ]
    text_y = None
    x_line = y0 + 0.13
    for z, label in sorted(levels, reverse=True):
        ty = z if text_y is None else min(z, text_y - 0.018)
        text_y = ty
        zoom.plot([y0 + 0.11, x_line + 0.03], [z, z], color="black", lw=0.5)
        zoom.plot([x_line + 0.03, x_line + 0.05], [z, ty], color="black", lw=0.5)
        zoom.text(x_line + 0.055, ty, f"{_fr(z)}  {label}", va="center", fontsize=9)
    zoom.set_title(
        "appui YP (Y bloqué), schéma v4 : axe Ø 24 transversal, étrier en T",
        fontsize=11,
    )
    fig.legend(loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle(
        f"PONTONS-ALU-01, variante {code} - vue 6 : coupe transversale sur la palée P1, axe du chevêtre C1 "
        f"(X = {v.stations[0]:g} m) ; appui articulé selon le schéma v4 (P65), cotes NGF".replace(
            "6.25", "6,25"
        ),
        fontsize=13,
    )
    fig.subplots_adjust(left=0.05, right=0.98, top=0.90, bottom=0.17, wspace=0.08)
    fig.savefig(path, dpi=100)
    plt.close(fig)


def plan_view(code: str, path: Path) -> None:
    """View 8: plan of the horizontal truss of T1 and PT1 (posts, diagonals, nodes at
    e_diag from the main beams, purlins drawn transparent)."""
    v = variants()[code]
    g = geometry_of(v)
    p = g.parameters
    yd = diagonal_node(p)
    half = p["B"] / 2.0
    beam = v.beam_side_mm / 1000.0
    purlin = v.purlin_side_mm / 1000.0
    post = v.post_side_mm / 1000.0
    spans = ("T1", "PT1")
    x_max = g.span("PT1").x1 + 0.3
    fig, ax = plt.subplots(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100)
    for side in ("YM", "YP"):
        for sp in spans:
            m = g.member(f"PP_{sp}_{side}")
            y = m.points[0][1]
            ax.add_patch(
                Rectangle(
                    (m.points[0][0], y - beam / 2),
                    m.points[-1][0] - m.points[0][0],
                    beam,
                    facecolor=COLORS["POUTRES_PRINC"],
                    edgecolor="black",
                    lw=0.4,
                    label="poutres principales 200 × 200"
                    if (side, sp) == ("YM", "T1")
                    else None,
                )
            )
    first = {"MONTANTS": True, "DIAGONALES": True}
    for sp in spans:
        for m in g.members:
            if m.span != sp or m.family not in ("MONTANTS", "DIAGONALES"):
                continue
            a, b = m.points[0], m.points[-1]
            if m.family == "MONTANTS":
                # dessin : le montant s'arrête au flanc des poutres (liaison LM_ au modèle)
                a = (a[0], a[1] + beam / 2, a[2])
                b = (b[0], b[1] - beam / 2, b[2])
            dx, dy = b[0] - a[0], b[1] - a[1]
            norm = (dx * dx + dy * dy) ** 0.5
            nx, ny = -dy / norm * post / 2, dx / norm * post / 2
            ax.add_patch(
                Polygon(
                    [
                        (a[0] + nx, a[1] + ny),
                        (b[0] + nx, b[1] + ny),
                        (b[0] - nx, b[1] - ny),
                        (a[0] - nx, a[1] - ny),
                    ],
                    closed=True,
                    facecolor=COLORS[m.family],
                    edgecolor="black",
                    lw=0.4,
                    alpha=0.9,
                    label=(
                        f"{'montants' if m.family == 'MONTANTS' else 'diagonales'} {v.post_label} (axe +1,29)"
                        if first[m.family]
                        else None
                    ),
                )
            )
            first[m.family] = False
            label = m.name.removeprefix("MONT_" if m.family == "MONTANTS" else "DIAG_")
            if m.family == "MONTANTS":
                # Toutes sous le dessin (la légende occupe le haut) ; PT1 décalée vers la
                # droite : son premier montant est à 1 mm du dernier de T1.
                ax.text(
                    a[0] + (0.12 if sp != "T1" else 0.0),
                    -half - 0.15,
                    f"M {label}",
                    ha="center",
                    va="top",
                    fontsize=9,
                    rotation=90,
                )
            else:
                ax.text(
                    (a[0] + b[0]) / 2 + 0.05,
                    (a[1] + b[1]) / 2,
                    f"D {label}",
                    fontsize=9,
                    color="#145214",
                )
    nodes = sorted(
        {
            (round(m.points[0][0], 3), round(m.points[0][1], 3))
            for m in g.members
            if m.family == "DIAGONALES" and m.span in spans
        }
        | {
            (round(m.points[-1][0], 3), round(m.points[-1][1], 3))
            for m in g.members
            if m.family == "DIAGONALES" and m.span in spans
        }
    )
    for k, (x, y) in enumerate(nodes):
        ax.add_patch(
            Circle(
                (x, y),
                0.035,
                facecolor="white",
                edgecolor="#d62728",
                lw=1.5,
                label=f"nœuds diagonale–montant, |Y| = {yd:.2f} (e = {v.e_diag:g} m de l'axe des poutres)".replace(
                    ".", ","
                )
                if k == 0
                else None,
            )
        )
    for sp in spans:
        for m in g.members:
            if m.span == sp and m.family == "PANNES_SEC":
                a, b = m.points[0], m.points[-1]
                ax.add_patch(
                    Rectangle(
                        (a[0], a[1] - purlin / 2),
                        b[0] - a[0],
                        purlin,
                        facecolor=COLORS["PANNES_SEC"],
                        edgecolor="#a04000",
                        lw=0.4,
                        alpha=0.35,
                        label=f"pannes {v.purlin_label} (transparence, au-dessus)"
                        if m.name.endswith("_1") and sp == "T1"
                        else None,
                    )
                )
    ax.annotate(
        "",
        xy=(0.35, half),
        xytext=(0.35, yd),
        arrowprops={"arrowstyle": "<->", "lw": 1.0},
    )
    ax.text(
        0.38,
        (half + yd) / 2,
        f"e = {v.e_diag:g} m".replace(".", ","),
        va="center",
        fontsize=10,
    )
    ax.plot([x_max - 1.4, x_max - 0.4], [-half - 0.55] * 2, color="black", lw=3)
    ax.text(x_max - 0.9, -half - 0.6, "1,00 m", ha="center", va="top", fontsize=10)
    ax.set_xlim(-0.3, x_max)
    ax.set_ylim(-half - 0.75, half + 0.45)
    ax.set_aspect("equal")
    ax.set_xlabel("X (m), depuis la ligne d'appui de la culée")
    ax.set_ylabel("Y (m)")
    ax.legend(loc="upper center", fontsize=9, ncol=3, bbox_to_anchor=(0.5, 1.0))
    ax.set_title(
        f"PONTONS-ALU-01, variante {code} - vue 8 : vue en plan du treillis horizontal de T1 et PT1 (P64) ; "
        "montants M, diagonales D (dessin en N), nœuds à e = 0,25 m, pannes en transparence",
        fontsize=12,
    )
    fig.savefig(path, dpi=100)
    plt.close(fig)


def step_vues(ctx: ProjectContext, codes: list[str], state: dict[str, Any]) -> None:
    del state
    root = ctx.results_dir / LOT
    out = root / "vues"
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    for code in codes:
        combos = root / code / "combinaisons_vues.json"
        for old in out.glob(f"{code}_vue*.png"):
            old.unlink()
        run_pvbatch(
            ctx,
            code,
            root / "exports" / code,
            out,
            combos if combos.is_file() else None,
            script=SCRIPT,
        )
        section_view(code, out / f"{code}_vue6_coupe_transversale_P1_appui_v4.png")
        plan_view(code, out / f"{code}_vue8_plan_treillis_T1_PT1.png")
        made = sorted(out.glob(f"{code}_vue*.png"))
        for p in made:
            w, h = png_size(p)
            report[p.name] = {
                "octets": p.stat().st_size,
                "largeur": w,
                "hauteur": h,
                "conforme": p.stat().st_size > 0 and w >= WIDTH and h >= HEIGHT,
            }
        print(f"{code} : {len(made)} vues")
    (out / "controle_png.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    os.sync()


__all__ = ["plan_view", "section_view", "step_vues"]
