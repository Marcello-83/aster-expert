# ruff: noqa: E501 -- libellés des dessins, phrases entières
"""Views of lot 53 for PONTONS-ALU-01 (consigne § MED et vues), variant B52.

- View A: plan of the deformed shape, combination max |DY| at the characteristic SLS
  (field CO_ELSC_DY); view B: the same at the accidental ULS (CO_ELUA_DY); view C:
  elevation of the deformed shape, max |DX| at the characteristic SLS without the
  temperature (CO_ELSC_DX_HT). matplotlib, from the node coordinates, the bars of the
  model and the nodal fields of the MED step (`med_travail/champs.npz`, the arrays
  written in the MED). Amplification written on the view; values in mm at each pier
  (deck at the pins and pile heads, read by the output points of `deplacements_lot53`)
  and at the tip of the cantilever.
- The ParaVis script `scripts/paraview/afficher_pontons_salome_53.py` is run once by
  pvbatch (Salomé-Méca image, no screen) on the MED of the lot: two PNG prove it loads
  the new fields (deformed shape coloured by DY, by family).
- Each PNG is checked: not empty, 1 920 × 1 080 pixels at least.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from aster_expert.projet.context import ProjectContext  # noqa: E402
from pontons_alu_01.deplacements_lot53 import (  # noqa: E402
    CODE,
    LOT,
    MM,
    OutPoint,
    output_points,
    point_value,
)
from pontons_alu_01.exports_lot51ter import VariantData51ter  # noqa: E402
from pontons_alu_01.exports_lot52 import load_variant  # noqa: E402
from pontons_alu_01.med_lot53 import MED_NAME  # noqa: E402
from pontons_alu_01.vues_lot51quater import HEIGHT, WIDTH, png_size  # noqa: E402

FloatArray = NDArray[np.float64]
PARAVIS = (
    Path(__file__).resolve().parent
    / "scripts"
    / "paraview"
    / "afficher_pontons_salome_53.py"
)
PLAN_FAMILIES = (
    "POUTRES_PRINC",
    "PANNES_SEC",
    "PANNE_RIVE",
    "MONTANTS",
    "DIAGONALES",
    "CHEVETRES",
    "LONGRINES",
)
ELEVATION_FAMILIES = (*PLAN_FAMILIES, "PILES")
AMPLIFICATIONS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 500)
VIEWS = (
    ("A", "CO_ELSC_DY", "plan", 1, "B52_vueA_plan_deformee_DY_ELS_c.png"),
    ("B", "CO_ELUA_DY", "plan", 1, "B52_vueB_plan_deformee_DY_ELU_acc.png"),
    (
        "C",
        "CO_ELSC_DX_HT",
        "elevation",
        0,
        "B52_vueC_elevation_deformee_DX_ELS_c_hors_T.png",
    ),
)


def _fr(v: float, digits: int = 1) -> str:
    return f"{v:.{digits}f}".replace(".", ",").replace("-", "−")


def amplification(peak_m: float, target_m: float) -> int:
    """The largest round factor that keeps the peak drawn under `target_m`."""
    ok = [a for a in AMPLIFICATIONS if a * peak_m <= target_m]
    return ok[-1] if ok else AMPLIFICATIONS[0]


def _segments(
    vd: VariantData51ter,
    families: tuple[str, ...],
    u: FloatArray,
    a: float,
    axes: tuple[int, int],
    comp: int,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    c = vd.model.coords
    pairs = [e.nodes for e in vd.model.elements.values() if e.family in families]
    idx = np.array(pairs, dtype=np.int64) - 1
    i, j = axes
    base = np.stack([c[idx][:, :, i], c[idx][:, :, j]], axis=-1)
    moved = np.stack(
        [c[idx][:, :, i] + a * u[idx][:, :, i], c[idx][:, :, j] + a * u[idx][:, :, j]],
        axis=-1,
    )
    colour = u[idx][:, :, comp].mean(axis=1) * MM
    return base, moved, colour


def _pier_values(
    vd: VariantData51ter, pts: list[OutPoint], u: FloatArray, comp: int
) -> dict[str, tuple[float, float, float]]:
    """Per pier: x of the pier, value at the deck (pins, extreme in |.|), at the pile
    heads (extreme in |.|), mm."""
    depl = {n + 1: u[n] for n in range(u.shape[0])}
    c = vd.model.coords
    out: dict[str, tuple[float, float, float]] = {}
    for f in vd.g.footings:
        deck = [
            point_value(p, depl, c)[comp]
            for p in pts
            if p.place == f.pier and p.kind == "axe"
        ]
        head = [
            point_value(p, depl, c)[comp]
            for p in pts
            if p.place == f.pier and p.kind == "tete"
        ]
        out[f.pier] = (
            float(f.centre[0]),
            max(deck, key=abs) * MM,
            max(head, key=abs) * MM,
        )
    return out


def draw(
    vd: VariantData51ter,
    pts: list[OutPoint],
    u: FloatArray,
    kind: str,
    comp: int,
    title: str,
    path: Path,
) -> dict[str, Any]:
    name = "DY" if comp == 1 else "DX"
    axes = (0, 1) if kind == "plan" else (0, 2)
    families = PLAN_FAMILIES if kind == "plan" else ELEVATION_FAMILIES
    peak = float(np.abs(u[:, comp]).max())
    a = amplification(peak, 0.9 if kind == "plan" else 1.2)
    base, moved, colour = _segments(vd, families, u, a, axes, comp)
    fig, ax = plt.subplots(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100)
    ax.add_collection(
        LineCollection(
            list(base), colors="#c8c8c8", linewidths=0.8, label="non déformée"
        )
    )
    lim = float(np.abs(colour).max()) or 1.0
    lc = LineCollection(list(moved), cmap="coolwarm", linewidths=1.6)
    lc.set_array(colour)
    lc.set_clim(-lim, lim)
    ax.add_collection(lc)
    bar = fig.colorbar(lc, ax=ax, fraction=0.025, pad=0.01)
    bar.set_label(f"{name} (mm), moyenne des deux nœuds de la barre")
    ax.autoscale()
    depl = {n + 1: u[n] for n in range(u.shape[0])}
    values = _pier_values(vd, pts, u, comp)
    y_text = (max(moved[:, :, 1].max(), base[:, :, 1].max())) + 0.15
    for pier, (x, deck, head) in values.items():
        ax.annotate(
            f"{pier}\ntablier {_fr(deck)} mm\ntête {_fr(head)} mm",
            (x, y_text),
            ha="center",
            va="bottom",
            fontsize=11,
        )
    tips = [p for p in pts if p.kind == "porte_a_faux"]
    tip_vals = [point_value(p, depl, vd.model.coords)[comp] * MM for p in tips]
    tip = max(tip_vals, key=abs)
    y_low = min(moved[:, :, 1].min(), base[:, :, 1].min()) - 0.15
    ax.annotate(
        f"bout du porte-à-faux : {name} {_fr(tip)} mm\n(YM {_fr(tip_vals[0])}, YP {_fr(tip_vals[1])})",
        (tips[0].x, y_low),
        ha="right",
        va="top",
        fontsize=11,
        color="#7f0000",
    )
    ax.set_ylim(bottom=y_low - (0.5 if kind == "plan" else 0.6))
    if kind == "elevation":
        cul = [p for p in pts if p.kind == "culee"]
        cv = max(
            (point_value(p, depl, vd.model.coords)[comp] * MM for p in cul), key=abs
        )
        ax.annotate(
            f"culée\n{name} {_fr(cv)} mm",
            (0.0, y_text),
            ha="center",
            va="bottom",
            fontsize=11,
        )
    ax.set_ylim(top=y_text + (1.1 if kind == "plan" else 1.3))
    ax.set_xlabel("X (m), depuis la ligne d'appui de la culée")
    ax.set_ylabel("Y (m)" if kind == "plan" else "Z (m NGF)")
    ax.set_title(
        f"{title}\ndéformée amplifiée × {a} (gris : non déformée) ; "
        + (
            "échelle des Y dilatée par rapport aux X"
            if kind == "plan"
            else "échelle des Z dilatée par rapport aux X"
        )
        + f" ; {name} max = {_fr(peak * MM)} mm",
        fontsize=12,
    )
    ax.grid(True, color="#eeeeee")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return {
        "amplification": a,
        "pic_mm": peak * MM,
        "palees_mm": {k: {"tablier": v[1], "tete": v[2]} for k, v in values.items()},
        "porte_a_faux_mm": tip,
    }


def run_paravis(ctx: ProjectContext, med_path: Path, out: Path) -> list[str]:
    """pvbatch on the ParaVis script of the lot, without screen (VM only)."""
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415

    salome = load_mesh_config(ctx.repo_root / "config" / "validation.yaml").salome
    image = Path(str(salome.image_path)).expanduser()
    runtime = shutil.which("singularity")
    if runtime is None or not image.is_file():
        message = "ParaVis : Singularity ou l'image Salomé-Méca absent (VM seulement)"
        raise RuntimeError(message)
    work = med_path.parent
    shutil.copyfile(PARAVIS, work / PARAVIS.name)
    command = (
        f"source {salome.install_root}/salome_prerequisites.sh >/dev/null 2>&1; "
        "unset DISPLAY; export HWLOC_COMPONENTS=-gl; "
        f"cd {work} && xvfb-run -a -s '-screen 0 1920x1200x24' pvbatch "
        f"--no-mpi {PARAVIS.name} --png {out.resolve()}"
    )
    argv = [runtime, "exec", "--containall", "--cleanenv", "--no-home"]
    for folder in sorted({work.resolve(), out.resolve()}):
        argv += ["--bind", f"{folder}:{folder}"]
    argv += [str(image), "bash", "-c", command]
    result = subprocess.run(  # noqa: S603 -- argv fixe
        argv, capture_output=True, text=True, timeout=1800, check=False
    )
    (out / "pvbatch_paravis_53.log").write_text(result.stdout + result.stderr, "utf-8")
    (work / PARAVIS.name).unlink(missing_ok=True)
    if result.returncode != 0:
        message = f"pvbatch : code {result.returncode} : {result.stderr[-800:]}"
        raise RuntimeError(message)
    return sorted(p.name for p in out.glob("B52_paravis_*.png"))


def step_vues(ctx: ProjectContext) -> dict[str, Any]:
    root = ctx.results_dir / LOT
    out = root / "vues"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("B52_*.png"):
        old.unlink()
    state = json.loads((ctx.results_dir / "lot52" / "etat.json").read_text("utf-8"))
    vd = load_variant(ctx, CODE, state)
    pts = output_points(vd)
    summary_path = root / "exports" / "synthese.json"
    summary = json.loads(summary_path.read_text("utf-8"))
    titles = {c["key"]: (c["title"], c["source"]) for c in summary["champs_med"]}
    report: dict[str, Any] = {}
    with np.load(root / CODE / "med_travail" / "champs.npz") as stored:
        for letter, key, kind, comp, name in VIEWS:
            title, source = titles[key]
            report[f"vue {letter}"] = draw(
                vd,
                pts,
                stored[key],
                kind,
                comp,
                f"PONTONS-ALU-01, B52 (lot 53) — vue {letter} : {title} (champ {key})\n{source}",
                out / name,
            )
    report["paravis"] = run_paravis(ctx, root / CODE / "MED" / MED_NAME, out)
    pngs: dict[str, Any] = {}
    for p in sorted(out.glob("B52_*.png")):
        w, h = png_size(p)
        pngs[p.name] = {
            "octets": p.stat().st_size,
            "largeur": w,
            "hauteur": h,
            "conforme": p.stat().st_size > 0 and w >= WIDTH and h >= HEIGHT,
        }
    report["png"] = pngs
    report["reussi"] = all(v["conforme"] for v in pngs.values()) and len(pngs) == 5
    (out / "controle_png.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    summary["controle_vues"] = report
    summary_path.write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )
    print(
        f"{CODE} : {len(pngs)} PNG, contrôle {'RÉUSSI' if report['reussi'] else 'ÉCHEC'}"
    )
    return report


__all__ = ["amplification", "step_vues"]
