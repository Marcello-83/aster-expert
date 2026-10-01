"""Vues 2D d'un calcul du quai, lues dans le MED de résultats (lot 36).

Moteur : `matplotlib` (backend Agg, sans interface). ParaVis hors interface est
impossible ici (ni serveur X virtuel ni EGL/OSMesa, docs/essais_lot36.md, étape 4) ;
les vues sont donc des projections 2D (développée X-Z de l'écran, coupes Y-Z, plans
X-Y, profils), jamais un rendu 3D.

Toutes les grandeurs viennent de `quai_cw_test_01.report.med_source.MedData` (champs du
MED de résultats) ; aucune n'est relue d'un listing. Chaque vue porte ses unités, sa
légende de couleur, son cas élémentaire et, pour la déformée, son facteur
d'amplification. Aucune vue n'est un verdict : les limites de butée sont des données
du contrôle du lot 35 (constats), pas des critères de dimensionnement.

Repère : X le long du quai, Y vers la terre, Z ascendant (point 9 de la fiche).
Composantes d'efforts : repère de l'élément (`EFGE_ELNO`/`EFGE_NOEU`, U4.42.01) ;
pour les tubes et les palplanches `x_l` est vertical (`VECTEUR = (0, 0, 1)`), donc
`MXX`/`NXX` sont le moment et l'effort normal **verticaux** par mètre de largeur ;
pour la poutre `x_l = +X`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from aster_expert.report.med_read import med_field_name  # noqa: E402
from aster_expert.report.tables import Record  # noqa: E402
from quai_cw_test_01.report import quantities as q  # noqa: E402
from quai_cw_test_01.report.loads import AppliedLoads  # noqa: E402
from quai_cw_test_01.report.med_source import MedData  # noqa: E402

# Palette de référence (dataviz) : bleu / orange autour d'un neutre, séquentiel bleu.
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
NEUTRAL = "#f0efec"

matplotlib.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GREY,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "text.color": INK,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "font.size": 9,
        "axes.grid": True,
        "grid.color": "#e2e1dc",
        "grid.linewidth": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.4,
    }
)
DIVERGING = matplotlib.colors.LinearSegmentedColormap.from_list(
    "bleu_orange", [BLUE, NEUTRAL, ORANGE]
)


@dataclass(frozen=True)
class FigureFile:
    case: str
    kind: str
    title: str
    path: Path


@dataclass(frozen=True)
class FigureContext:
    """Ce dont les vues ont besoin en plus du MED (données du modèle)."""

    axes: list[float]
    radius: float
    spring_nodes: dict[tuple[float, float, float], q.SpringNode]
    """Nœuds à ressort avec la butée limite côté bassin (capacité `capacity_n`)."""
    spring_nodes_terre: dict[tuple[float, float, float], q.SpringNode]
    """Les mêmes nœuds avec la butée limite côté terre."""
    loads: AppliedLoads
    tie_direction: tuple[float, float]
    """`(cos, sin)` du tirant, de la tête vers l'ancrage (plan Y-Z)."""
    tie_head: tuple[float, float]
    """`(y, z)` de l'accrochage du tirant sur le tube."""
    tie_anchor: tuple[float, float]
    """`(y, z)` de l'extrémité `ANC_xx`."""
    label: str = ""
    """Identifie le calcul dans le titre des vues (`base`, `V1`)."""


# --- géométrie de l'écran ----------------------------------------------------


def _centroids(med: MedData) -> np.ndarray:
    return np.asarray(med.coords[med.conn[0]].mean(axis=1))


def _spring_key(point: np.ndarray) -> tuple[float, float, float]:
    """Clé d'un nœud à ressort : position arrondie au micromètre (`spring_nodes`)."""
    x, y, z = (round(float(c), 6) + 0.0 for c in point)
    return (x, y, z)


def _shell_sets(med: MedData) -> dict[str, np.ndarray]:
    groups = med.cell_groups[0]
    tubes = groups["TUBES"]
    palps = groups["PALPS"]
    centroid = _centroids(med)
    return {
        "tubes_terre": tubes[centroid[tubes, 1] > 1e-9],
        "tubes_bassin": tubes[centroid[tubes, 1] < -1e-9],
        "palps": palps,
    }


def _polys_xz(med: MedData, cells: np.ndarray) -> np.ndarray:
    pts = med.coords[med.conn[0][cells]]
    return np.asarray(pts[:, :, [0, 2]])


def _cell_mean_nodal(med: MedData, cells: np.ndarray, nodal: np.ndarray) -> np.ndarray:
    return np.asarray(nodal[med.conn[0][cells]].mean(axis=1))


def _elno_cell_mean(
    med: MedData, field: str, component: str, cells: np.ndarray
) -> np.ndarray:
    """Moyenne des quatre valeurs nodales de chaque maille de coque de `cells`
    (`EFGE_ELNO` niveau 0) ; une maille absente du champ vaut NaN."""
    values = med.arrays[f"{field}@0"][:, med.comp(field, component)]
    listed = med.arrays[f"{field}@0#cells"]
    means = values.reshape(-1, 4).mean(axis=1)
    lookup = np.full(len(med.conn[0]), np.nan)
    lookup[listed] = means
    return np.asarray(lookup[cells])


CLIP_PERCENTILE = 99.5
CLIP_NOTE = "échelle limitée au 99,5e centile de |valeur|"


def _symmetric_norm(values: np.ndarray, *, clip: bool = False) -> TwoSlopeNorm:
    """Échelle symétrique autour de 0 ; `clip` la limite au centile
    `CLIP_PERCENTILE` de |valeur| (les singularités locales, comme l'accrochage des
    tirants, l'écraseraient sinon ; les extrêmes vrais sont dans la synthèse)."""
    magnitude = np.abs(values[np.isfinite(values)])
    vmax = float(np.percentile(magnitude, CLIP_PERCENTILE) if clip else magnitude.max())
    vmax = vmax if vmax > 0.0 else 1.0
    return TwoSlopeNorm(vcenter=0.0, vmin=-vmax, vmax=vmax)


def _xz_map(
    ax: Axes,
    med: MedData,
    cells: np.ndarray,
    values: np.ndarray,
    norm: TwoSlopeNorm,
    title: str,
) -> PolyCollection:
    poly = PolyCollection(
        list(_polys_xz(med, cells)),
        array=values,
        cmap=DIVERGING,
        norm=norm,
        edgecolors="face",
        linewidths=0.2,
    )
    ax.add_collection(poly)
    ax.set_xlim(
        float(med.coords[:, 0].min()) - 0.3, float(med.coords[:, 0].max()) + 0.3
    )
    ax.set_ylim(
        float(med.coords[:, 2].min()) - 0.5, float(med.coords[:, 2].max()) + 0.5
    )
    ax.set_aspect("equal")
    ax.set_xlabel("X (m), le long du quai")
    ax.set_ylabel("Z (m CM)")
    ax.set_title(title)
    return poly


def _save(fig: Figure, path: Path) -> Path:
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def _suptitle(fig: Figure, ctx: FigureContext, case: str, text: str) -> None:
    tag = f" [{ctx.label}]" if ctx.label else ""
    fig.suptitle(f"Cas {case}{tag} — {text}", fontsize=11, color=INK)


# --- vues ----------------------------------------------------------------------


def amplification(max_displacement: float) -> float:
    """Facteur d'amplification de la déformée : celui qui porte le plus grand
    déplacement à ~0,5 m à l'écran, arrondi à un chiffre significatif."""
    if max_displacement <= 0.0:
        return 1.0
    return float(f"{0.5 / max_displacement:.1g}")


def deformed_shape(
    med: MedData, ctx: FigureContext, case: str, out: Path
) -> FigureFile:
    depl = med.node_field(case, "DEPL")
    factor = amplification(float(np.abs(depl[:, :3]).max()))
    xyz = med.coords
    moved = xyz + factor * depl[:, :3]
    tube_nodes = np.unique(med.conn[0][med.cell_groups[0]["TUBES"]])
    z_head = float(xyz[tube_nodes, 2].max())
    fig = plt.figure(figsize=(15, 9), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, width_ratios=[2.2, 1])
    ax_head = fig.add_subplot(grid[0, 0])
    ax_dredge = fig.add_subplot(grid[1, 0])
    ax_cut = fig.add_subplot(grid[:, 1])

    def ring(ax: Axes, z: float, label: str) -> None:
        nodes = tube_nodes[np.abs(xyz[tube_nodes, 2] - z) < 1e-6]
        ax.plot(xyz[nodes, 0], xyz[nodes, 1], ".", ms=2.5, color=GREY, label="initiale")
        ax.plot(
            moved[nodes, 0],
            moved[nodes, 1],
            ".",
            ms=2.5,
            color=ORANGE,
            label=f"déformée ×{factor:g}",
        )
        ax.set_aspect("equal")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m), vers la terre")
        ax.set_title(label)
        ax.legend(loc="upper right", markerscale=4, frameon=False)

    ring(ax_head, z_head, f"Plan à la tête (Z = {z_head:+.2f} m CM)")
    ring(ax_dredge, -12.0, "Plan à la cote de dragage (Z = −12,00 m CM)")
    axis5 = ctx.axes[len(ctx.axes) // 2]
    nodes = tube_nodes[np.abs(xyz[tube_nodes, 0] - axis5) < 1e-6]
    nodes = nodes[np.argsort(xyz[nodes, 2])]
    for side, sign in (("bassin", -1), ("terre", 1)):
        mine = nodes[np.sign(xyz[nodes, 1]) == sign]
        ax_cut.plot(xyz[mine, 1], xyz[mine, 2], "-", color=GREY, lw=1.0)
        ax_cut.plot(
            moved[mine, 1],
            moved[mine, 2],
            "-",
            color=ORANGE if sign < 0 else BLUE,
            label=f"génératrice {side}, déformée ×{factor:g}",
        )
    ax_cut.plot([], [], color=GREY, label="initiale")
    ax_cut.set_xlabel("Y (m), vers la terre")
    ax_cut.set_ylabel("Z (m CM)")
    ax_cut.set_title(f"Coupe Y-Z, tube central (X = {axis5:g} m)")
    ax_cut.legend(loc="lower center", frameon=False, fontsize=8)
    _suptitle(
        fig,
        ctx,
        case,
        f"déformée amplifiée ×{factor:g} (déplacement maximal "
        f"{np.abs(depl[:, :3]).max() * 1e3:.2f} mm, non amplifié)",
    )
    path = _save(fig, out / f"deformee_{case}.png")
    return FigureFile(case, "deformee", f"Déformée amplifiée ×{factor:g}", path)


def dy_map(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    sets = _shell_sets(med)
    dy = med.node_field(case, "DEPL")[:, 1] * 1e3
    fig, axes = plt.subplots(1, 2, figsize=(13, 8), constrained_layout=True)
    norm = _symmetric_norm(dy[np.unique(med.conn[0])])
    for ax, key, title in (
        (axes[0], "tubes_terre", "Face côté terre (Y ≥ 0) et palplanches"),
        (axes[1], "tubes_bassin", "Face côté bassin (Y ≤ 0) et palplanches"),
    ):
        cells = np.concatenate([sets[key], sets["palps"]])
        poly = _xz_map(ax, med, cells, _cell_mean_nodal(med, cells, dy), norm, title)
    cbar = fig.colorbar(poly, ax=axes, shrink=0.6, location="bottom", pad=0.04)
    cbar.set_label("DY (mm) — positif vers la terre")
    _suptitle(
        fig,
        ctx,
        case,
        "cartographie du déplacement horizontal DY de l'écran (développée X-Z)",
    )
    path = _save(fig, out / f"dy_ecran_{case}.png")
    return FigureFile(case, "dy_ecran", "Cartographie de DY sur l'écran", path)


def tube_efforts(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    sets = _shell_sets(med)
    field = med_field_name(f"{case}_ET", "EFGE_ELNO")
    fig, axes = plt.subplots(2, 2, figsize=(14, 13), constrained_layout=True)
    for row, (component, label) in enumerate(
        (
            ("MXX", "MXX, moment vertical (kN.m/m)"),
            ("NXX", "NXX, effort normal vertical (kN/m)"),
        )
    ):
        both = np.concatenate([sets["tubes_terre"], sets["tubes_bassin"]])
        values = _elno_cell_mean(med, field, component, both) * 1e-3
        norm = _symmetric_norm(values, clip=True)
        for col, (key, title) in enumerate(
            (
                ("tubes_terre", "face terre (Y ≥ 0)"),
                ("tubes_bassin", "face bassin (Y ≤ 0)"),
            )
        ):
            cells = sets[key]
            poly = _xz_map(
                axes[row, col],
                med,
                cells,
                _elno_cell_mean(med, field, component, cells) * 1e-3,
                norm,
                f"{component} — tubes, {title}",
            )
        cbar = fig.colorbar(poly, ax=axes[row, :], shrink=0.7, pad=0.02, extend="both")
        cbar.set_label(f"{label} — {CLIP_NOTE}")
    _suptitle(
        fig, ctx, case, "efforts généralisés des tubes (EFGE_ELNO, moyenne par maille)"
    )
    path = _save(fig, out / f"efforts_tubes_{case}.png")
    return FigureFile(case, "efforts_tubes", "Efforts généralisés des tubes", path)


def palp_efforts(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    name = med_field_name(f"{case}_EP", "EFGE_NOEU")
    values = med.arrays[name]
    nodes = med.arrays[f"{name}#nodes"]
    cells = med.cell_groups[0]["PALPS"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 8.5), constrained_layout=True)
    for ax, component, label in (
        (axes[0], "MXX", "MXX, moment vertical (kN.m/m)"),
        (axes[1], "NXX", "NXX, effort normal vertical (kN/m)"),
    ):
        nodal = np.full(len(med.coords), np.nan)
        nodal[nodes] = values[:, med.comp(name, component)] * 1e-3
        cell_values = _cell_mean_nodal(med, cells, nodal)
        poly = _xz_map(
            ax,
            med,
            cells,
            cell_values,
            _symmetric_norm(cell_values, clip=True),
            f"{component} — palplanches (EFGE_NOEU)",
        )
        cbar = fig.colorbar(
            poly, ax=ax, shrink=0.9, location="bottom", pad=0.06, extend="both"
        )
        cbar.set_label(f"{label}\n{CLIP_NOTE}", fontsize=8)
    _suptitle(
        fig,
        ctx,
        case,
        "efforts généralisés des palplanches (EFGE_NOEU, moyenne par maille)",
    )
    path = _save(fig, out / f"efforts_palplanches_{case}.png")
    return FigureFile(
        case, "efforts_palplanches", "Efforts généralisés des palplanches", path
    )


def _arrows_y(
    ax: Axes,
    y0: float,
    zs: np.ndarray,
    forces: np.ndarray,
    scale: float,
    color: str,
) -> None:
    for z, f in zip(zs, forces, strict=True):
        if abs(f) * scale > 1e-3:
            ax.annotate(
                "",
                xy=(y0 + f * scale, z),
                xytext=(y0, z),
                arrowprops={"arrowstyle": "-|>", "color": color, "lw": 0.9},
            )


def arrows(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    """Flèches sur la coupe Y-Z du tube central : poussée appliquée, réactions des
    ressorts (force sur l'écran, −k·DY), tirant ; et, en plan, charges de poutre,
    amarrage, accostage."""
    depl = med.node_field(case, "DEPL")
    xyz = med.coords
    axis5 = ctx.axes[len(ctx.axes) // 2]
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(14, 9), width_ratios=[1.35, 1], constrained_layout=True
    )
    # écran (génératrices bassin et terre du tube central)
    tube_nodes = np.unique(med.conn[0][med.cell_groups[0]["TUBES"]])
    on_axis = tube_nodes[np.abs(xyz[tube_nodes, 0] - axis5) < 1e-6]
    for sign, color in ((-1, ORANGE), (1, BLUE)):
        mine = on_axis[np.sign(xyz[on_axis, 1]) == sign]
        mine = mine[np.argsort(xyz[mine, 2])]
        ax.plot(xyz[mine, 1], xyz[mine, 2], "-", color=color, lw=1.6)
    # poussée appliquée côté terre : flèches vers le bassin (−Y)
    notes: list[str] = []
    if case in ctx.loads.pressure_pa:
        pts = ctx.loads.pressure_pa[case]
        zs = np.arange(-26.0, 2.61, 1.0)
        zz = np.array([p[0] for p in pts])
        pp = np.array([p[1] for p in pts])
        # points d'une interface (deux valeurs à la même cote) : la valeur du dessous
        _, first = np.unique(zz, return_index=True)
        p_at = np.interp(zs, zz[np.sort(first)], pp[np.sort(first)])
        scale_p = 6.0 / max(float(p_at.max()), 1.0)
        _arrows_y(ax, float(ctx.radius) + 6.0, zs, -p_at, scale_p, INK2)
        notes.append(
            f"poussée appliquée (flèches noires) : "
            f"pression max {p_at.max() / 1e3:.1f} kPa"
        )
    # ressorts : force sur l'écran, génératrice bassin du tube central
    springs = np.unique(med.conn[-2].ravel())
    mine = springs[(np.abs(xyz[springs, 0] - axis5) < 1e-6) & (xyz[springs, 1] < 0)]
    mine = mine[np.argsort(xyz[mine, 2])]
    keys = [_spring_key(xyz[n]) for n in mine]
    stiff = np.array([ctx.spring_nodes[k].stiffness for k in keys])
    force = -stiff * depl[mine, 1]
    scale_f = 4.0 / max(float(np.abs(force).max()), 1.0)
    _arrows_y(ax, -ctx.radius, xyz[mine, 2], force, scale_f, ORANGE)
    notes.append(
        f"réaction des ressorts (flèches orange, force sur l'écran, "
        f"positive vers +Y) : "
        f"maximum {np.abs(force).max() / 1e3:.1f} kN par nœud"
    )
    # tirant
    ties = q.tie_forces(_tie_rows(med, case), ctx.axes)
    n_tie = ties[len(ties) // 2].n
    (y0, z0), (y1, z1) = ctx.tie_head, ctx.tie_anchor
    ax.plot([y0, y1], [z0, z1], "-", color=AQUA, lw=2.0)
    ax.annotate(
        f"tirant : N = {n_tie / 1e3:.1f} kN (tube central)",
        xy=((y0 + y1) / 2, (z0 + z1) / 2),
        xytext=(6, 6),
        textcoords="offset points",
        color=INK2,
    )
    ax.set_xlim(-6.0, 26.0)
    ax.set_ylim(-27.0, 5.0)
    ax.set_xlabel("Y (m), vers la terre\n" + "\n".join(notes), fontsize=8)
    ax.set_ylabel("Z (m CM)")
    ax.set_title("Coupe Y-Z du tube central : poussée, ressorts, tirant")
    # plan : poutre, amarrage, accostage
    beam_notes: list[str] = []
    x_lo, x_hi = min(ctx.axes), max(ctx.axes)
    ax2.plot([x_lo, x_hi], [0.34, 0.34], "-", color=GREY, lw=4, solid_capstyle="butt")
    for x in ctx.axes:
        ax2.plot([x], [0.34], "o", color=GREY, ms=3)
    if case in ctx.loads.beam:
        b = ctx.loads.beam[case]
        beam_notes.append(
            f"charge de poutre : FY = {b.fy_per_m / 1e3:.2f} kN/m, "
            f"MX = {b.mx_per_m / 1e3:.2f} kN.m/m"
            + (f", poids {b.fz_per_m / 1e3:.2f} kN/m" if b.fz_per_m is not None else "")
        )
        for x in np.linspace(x_lo, x_hi, 21):
            ax2.annotate(
                "",
                xy=(x, 0.34 + (0.9 if b.fy_per_m > 0 else -0.9)),
                xytext=(x, 0.34),
                arrowprops={"arrowstyle": "-|>", "color": INK2, "lw": 0.7},
            )
    if case == "Q3":
        fy, fz, mx = ctx.loads.bollard_n
        ax2.annotate(
            "",
            xy=(0.0, 0.34 + math.copysign(2.0, fy)),
            xytext=(0.0, 0.34),
            arrowprops={"arrowstyle": "-|>", "color": ORANGE, "lw": 1.6},
        )
        beam_notes.append(
            f"amarrage (BOLLARD, X = 0) : FY = {fy / 1e3:.0f} kN, "
            f"FZ = {fz / 1e3:.0f} kN, "
            f"MX = {mx / 1e3:.0f} kN.m"
        )
    if case == "A":
        cells = med.cell_groups[0].get("DEFENSE")
        if cells is not None and len(cells):
            pts = xyz[med.conn[0][cells]].reshape(-1, 3)
            x0, x1 = float(pts[:, 0].min()), float(pts[:, 0].max())
            for x in np.linspace(x0, x1, 6):
                ax2.annotate(
                    "",
                    xy=(x, -0.71 + 0.0),
                    xytext=(x, -0.71 - 1.6),
                    arrowprops={"arrowstyle": "-|>", "color": ORANGE, "lw": 1.6},
                )
            beam_notes.append(
                f"accostage (DEFENSE, X = {x0:.2f} à {x1:.2f} m) : "
                f"poussée vers la terre (+Y)"
            )
    ax2.set_xlabel(
        "X (m)\n" + ("\n".join(beam_notes) or "aucune charge de poutre ni ponctuelle"),
        fontsize=8,
    )
    ax2.set_ylabel("Y (m)")
    ax2.set_ylim(-3.0, 3.0)
    ax2.set_title("Plan : poutre de couronnement, amarrage, accostage")
    _suptitle(
        fig,
        ctx,
        case,
        "charges appliquées, réactions des ressorts et tirants (flèches)",
    )
    path = _save(fig, out / f"fleches_{case}.png")
    return FigureFile(case, "fleches", "Flèches : charges, ressorts, tirants", path)


def _tie_rows(med: MedData, case: str) -> list[Record]:
    from quai_cw_test_01.report.med_source import _elno_rows

    field = med_field_name(f"{case}_ET", "EFGE_ELNO")
    return _elno_rows(med, field, -1, "TIRANTS", ("N",))


def beam_diagrams(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    from quai_cw_test_01.report.med_source import _elno_rows

    field = med_field_name(f"{case}_ET", "EFGE_ELNO")
    rows = _elno_rows(
        med, field, -1, "POUTRE_COUR", ("N", "VY", "VZ", "MT", "MFY", "MFZ")
    )
    by_cell: dict[str, list[Record]] = {}
    for r in rows:
        by_cell.setdefault(str(r["MAILLE"]), []).append(r)
    fig, axes = plt.subplots(
        2, 2, figsize=(13, 8), sharex=True, constrained_layout=True
    )
    panels = (
        (axes[0, 0], "MFY", "MFY : moment autour de Y (kN.m), flexion verticale", BLUE),
        (
            axes[0, 1],
            "MFZ",
            "MFZ : moment autour de Z (kN.m), flexion horizontale",
            ORANGE,
        ),
        (axes[1, 0], "VZ", "VZ : effort tranchant selon Z (kN)", BLUE),
        (axes[1, 1], "VY", "VY : effort tranchant selon Y (kN)", ORANGE),
    )
    for ax, comp, title, color in panels:
        for cell in by_cell.values():
            cell = sorted(cell, key=lambda r: float(r["COOR_X"]))
            ax.plot(
                [float(r["COOR_X"]) for r in cell],
                [float(r[comp]) * 1e-3 for r in cell],
                "-o",
                ms=2.5,
                color=color,
            )
        ax.axhline(0.0, color=GREY, lw=0.6)
        ax.set_title(title)
        ax.set_ylabel("kN.m" if comp.startswith("MF") else "kN")
    for x in ctx.axes:
        for ax in axes.ravel():
            ax.axvline(x, color="#e2e1dc", lw=0.5)
    axes[1, 0].set_xlabel("X (m), le long de la poutre (traits fins : axes des tubes)")
    axes[1, 1].set_xlabel("X (m), le long de la poutre")
    _suptitle(
        fig,
        ctx,
        case,
        "poutre de couronnement : moments et efforts tranchants (EFGE_ELNO, x_l = +X)",
    )
    path = _save(fig, out / f"poutre_{case}.png")
    return FigureFile(case, "poutre", "Diagrammes de la poutre de couronnement", path)


def _generatrix(med: MedData, x: float, sign: int) -> np.ndarray:
    tube_nodes = np.unique(med.conn[0][med.cell_groups[0]["TUBES"]])
    xyz = med.coords
    mine = tube_nodes[
        (np.abs(xyz[tube_nodes, 0] - x) < 1e-6) & (np.sign(xyz[tube_nodes, 1]) == sign)
    ]
    return np.asarray(mine[np.argsort(xyz[mine, 2])])


def _elno_node_mean(med: MedData, field: str, component: str) -> np.ndarray:
    """Moyenne, par nœud, des valeurs par élément (`EFGE_ELNO` des coques) de toutes
    les mailles qui le portent ; NaN hors des mailles du champ."""
    values = med.arrays[f"{field}@0"][:, med.comp(field, component)]
    cells = med.arrays[f"{field}@0#cells"]
    nodes = med.conn[0][cells].reshape(-1)
    total = np.zeros(len(med.coords))
    count = np.zeros(len(med.coords))
    np.add.at(total, nodes, values)
    np.add.at(count, nodes, 1.0)
    out = np.full(len(med.coords), np.nan)
    np.divide(total, count, out=out, where=count > 0)
    return out


def tube_profiles(med: MedData, ctx: FigureContext, case: str, out: Path) -> FigureFile:
    depl = med.node_field(case, "DEPL")
    field = med_field_name(f"{case}_ET", "EFGE_ELNO")
    mxx = _elno_node_mean(med, field, "MXX") * 1e-3
    nxx = _elno_node_mean(med, field, "NXX") * 1e-3
    tubes = [(len(ctx.axes) // 2 + 1, ctx.axes[len(ctx.axes) // 2]), (1, ctx.axes[0])]
    fig, axes = plt.subplots(
        2, 3, figsize=(14, 11), sharey=True, constrained_layout=True
    )
    for row, (number, x) in enumerate(tubes):
        for sign, color, label in (
            (-1, ORANGE, "génératrice bassin (Y<0)"),
            (1, BLUE, "génératrice terre (Y>0)"),
        ):
            nodes = _generatrix(med, x, sign)
            z = med.coords[nodes, 2]
            axes[row, 0].plot(depl[nodes, 1] * 1e3, z, color=color, label=label)
            axes[row, 1].plot(mxx[nodes], z, color=color)
            axes[row, 2].plot(nxx[nodes], z, color=color)
        for col, values in ((1, mxx), (2, nxx)):
            plotted = np.concatenate(
                [values[_generatrix(med, x, sign)] for sign in (-1, 1)]
            )
            plotted = plotted[np.isfinite(plotted)]
            low, high = np.percentile(plotted, [1.0, 99.0])
            margin = 0.15 * (high - low if high > low else 1.0)
            axes[row, col].set_xlim(low - margin, high + margin)
            true_max = float(np.abs(plotted).max())
            if true_max > max(abs(low), abs(high)) + margin:
                axes[row, col].text(
                    0.02,
                    0.02,
                    f"pics de tête hors échelle (|valeur| max {true_max:.3g}) :\n"
                    "accrochage du tirant, singularité connue",
                    transform=axes[row, col].transAxes,
                    fontsize=7,
                    color=INK2,
                )
        axes[row, 0].set_title(f"TUBE_{number:02d} : DY (mm)")
        axes[row, 1].set_title(f"TUBE_{number:02d} : MXX, moment vertical (kN.m/m)")
        axes[row, 2].set_title(f"TUBE_{number:02d} : NXX, effort normal (kN/m)")
        axes[row, 0].set_ylabel("Z (m CM)")
        for ax in axes[row]:
            ax.axvline(0.0, color=GREY, lw=0.6)
        axes[row, 0].legend(frameon=False, loc="best")
    _suptitle(
        fig,
        ctx,
        case,
        "profils le long de TUBE_05 et TUBE_01 (génératrices bassin et terre)",
    )
    path = _save(fig, out / f"profils_{case}.png")
    return FigureFile(case, "profils", "Profils DY(z), M(z), N(z)", path)


def pivot_level(z: np.ndarray, dy: np.ndarray) -> float | None:
    """Cote où DY change de signe pour la première fois en descendant de la tête
    (interpolation linéaire entre deux nœuds), `None` s'il n'y en a pas. `z`
    croissant."""
    order = np.argsort(-z)
    zz, dd = z[order], dy[order]
    for i in range(len(zz) - 1):
        if dd[i] * dd[i + 1] < 0.0:
            return float(zz[i] + (zz[i + 1] - zz[i]) * dd[i] / (dd[i] - dd[i + 1]))
    return None


def bearing_profile(
    med: MedData, ctx: FigureContext, case: str, out: Path
) -> FigureFile:
    """Pression de réaction des ressorts (k·DY/A) sur la génératrice bassin du tube
    central, comparée à la butée limite (côté bassin en compression, côté terre en
    traction), avec la cote de pivot. Constat sur le domaine du modèle linéaire."""
    depl = med.node_field(case, "DEPL")
    xyz = med.coords
    axis5 = ctx.axes[len(ctx.axes) // 2]
    springs = np.unique(med.conn[-2].ravel())
    mine = springs[(np.abs(xyz[springs, 0] - axis5) < 1e-6) & (xyz[springs, 1] < 0)]
    mine = mine[np.argsort(xyz[mine, 2])]
    keys = [_spring_key(xyz[n]) for n in mine]
    nodes = [ctx.spring_nodes[k] for k in keys]
    z = np.array([n.z for n in nodes])
    dy = depl[mine, 1]
    pressure = np.array(
        [n.stiffness * d / n.area for n, d in zip(nodes, dy, strict=True)]
    )  # Pa, DY>0 : traction
    limit_bassin = np.array([n.capacity_n / n.area for n in nodes])
    fig, ax = plt.subplots(figsize=(8, 10), constrained_layout=True)
    ax.plot(
        -pressure * 1e-3,
        z,
        "-o",
        ms=3,
        color=BLUE,
        label="réaction des ressorts (compression > 0)",
    )
    ax.plot(
        limit_bassin * 1e-3,
        z,
        "--",
        color=ORANGE,
        label="butée limite côté bassin (Rankine)",
    )
    terre = np.array(
        [
            ctx.spring_nodes_terre[k].capacity_n / ctx.spring_nodes_terre[k].area
            for k in keys
        ]
    )
    ax.plot(
        -terre * 1e-3,
        z,
        ":",
        color=AQUA,
        label="butée limite côté terre (traction, signe −)",
    )
    zp = pivot_level(z, dy)
    if zp is not None:
        ax.axhline(zp, color=INK2, lw=0.9)
        ax.annotate(
            f"cote de pivot (DY = 0) : {zp:.2f} m CM",
            xy=(ax.get_xlim()[0], zp),
            xytext=(4, 4),
            textcoords="offset points",
            color=INK2,
        )
    ax.axvline(0.0, color=GREY, lw=0.6)
    ax.set_xlabel("Pression (kPa) — compression positive, traction négative")
    ax.set_ylabel("Z (m CM)")
    ax.set_title("Génératrice bassin du tube central (TUBE_05)")
    ax.legend(frameon=False, loc="lower right")
    _suptitle(
        fig,
        ctx,
        case,
        "pression de réaction des ressorts et butée limite (constat, sans verdict)",
    )
    path = _save(fig, out / f"butee_{case}.png")
    return FigureFile(case, "butee", "Pression de réaction et butée limite", path)


def tube_section_profiles(
    med: MedData, ctx: FigureContext, case: str, out: Path
) -> FigureFile:
    """Lot 37 : `N(z)`, `M(z)`, `T(z)` de `TUBE_05` et de `TUBE_01` (demi-tube), tubes
    vus comme des poutres (`quai_cw_test_01.report.sections`)."""
    from quai_cw_test_01.report import section_statics as ss  # noqa: PLC0415

    n_tubes = len(ctx.axes)
    tubes = [
        (n_tubes // 2 + 1, BLUE, "TUBE_05"),
        (1, ORANGE, "TUBE_01 (demi-tube)"),
    ]
    fig, axes = plt.subplots(
        1, 3, figsize=(14, 7), sharey=True, constrained_layout=True
    )
    for number, color, label in tubes:
        levels = ss.tube_levels(med, case, number, ctx.axes[number - 1])
        z = [lv.z for lv in levels]
        axes[0].plot([lv.mean.n * 1e-3 for lv in levels], z, color=color, label=label)
        axes[1].plot([lv.mean.mx * 1e-3 for lv in levels], z, color=color)
        axes[2].plot([lv.mean.ty * 1e-3 for lv in levels], z, color=color)
        axes[2].plot(
            [lv.mean.ty_nxy * 1e-3 for lv in levels],
            z,
            color=color,
            ls=":",
            lw=1.0,
        )
    axes[0].set_title("N = ∫ NXX ds : effort normal (kN, traction > 0)")
    axes[1].set_title("M = ∫ NXX·y ds : moment d'axe X (kN.m)")
    axes[2].set_title("T : effort tranchant selon Y (kN) ; pointillé : part NXY")
    axes[0].set_ylabel("Z (m CM)")
    for ax in axes:
        ax.axvline(0.0, color=GREY, lw=0.6)
    axes[0].legend(frameon=False, loc="best")
    _suptitle(
        fig,
        ctx,
        case,
        "efforts d'ensemble des tubes vus comme des poutres (par tube, non par mètre)",
    )
    path = _save(fig, out / f"efforts_tube_{case}.png")
    return FigureFile(
        case, "efforts_tube", "Efforts d'ensemble N(z), M(z), T(z) des tubes", path
    )


VIEWS = (
    deformed_shape,
    dy_map,
    tube_efforts,
    palp_efforts,
    arrows,
    beam_diagrams,
    tube_profiles,
    tube_section_profiles,
    bearing_profile,
)


def make_figures(
    med: MedData, ctx: FigureContext, out_dir: Path, cases: Sequence[str] | None = None
) -> list[FigureFile]:
    """Toutes les vues de tous les cas élémentaires, en PNG dans `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made: list[FigureFile] = []
    for case in cases or med.cases:
        for view in VIEWS:
            made.append(view(med, ctx, case, out_dir))
    return made


def build_context(data_path: Path, *, label: str = "") -> FigureContext:
    """Contexte des vues : géométrie, aires, butées, charges, tirant."""
    from aster_expert.agent.model_data import load_model_data
    from quai_cw_test_01.generation.terre import butee_terre_pa
    from quai_cw_test_01.generation.values import ModelValues
    from quai_cw_test_01.meshing.combiwall import build_params, spring_node_areas
    from quai_cw_test_01.report.build import _butee_pa
    from quai_cw_test_01.report.loads import applied_loads

    data = load_model_data(data_path)
    params = build_params(data)
    mv = ModelValues(data)
    axes = [float(x) for x in params["tube"]["axes_x"]]
    k_h = {
        "RESS_AV_ARGI": float(mv.raw("sol.k_h_argile_marneuse_raide")),
        "RESS_AV_MARNE": float(mv.raw("sol.k_h_marne_compacte")),
    }
    areas = spring_node_areas(params)
    tie = params["tirants"]
    run_y, drop_z = tie["fin_y"] - tie["debut_y"], tie["fin_z"] - tie["debut_z"]
    length = math.hypot(run_y, drop_z)
    return FigureContext(
        axes=axes,
        radius=float(params["tube"]["rayon"]),
        spring_nodes=q.spring_nodes(areas, k_h, _butee_pa(data)),
        spring_nodes_terre=q.spring_nodes(areas, k_h, butee_terre_pa()),
        loads=applied_loads(data),
        tie_direction=(run_y / length, drop_z / length),
        tie_head=(float(tie["debut_y"]), float(tie["debut_z"])),
        tie_anchor=(float(tie["fin_y"]), float(tie["fin_z"])),
        label=label,
    )
