"""Views of lot 51 quater for PONTONS-ALU-01 (consigne § Vues 3D), variants B10 and B12.

- Views 1 to 5 and 7: `scripts/paraview/vues_3d_pontons.py`, run by pvbatch (ParaView
  5.11 of the Salomé-Méca image, no screen, `xvfb-run`), from the CSV exports of the
  variant and,
  for the deformed shapes, the four combinations written by the MED step
  (`combinaisons_vues.json`).
- View 6 (transverse section on pier P1, chevêtre C1, with the NGF levels of P53 and
  P54): a plane drawing by matplotlib from the geometry of the variant.
- Each PNG is checked: not empty, 1 920 × 1 080 pixels at least.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from aster_expert.projet.context import ProjectContext  # noqa: E402
from pontons_alu_01.geometrie_lot51ter import geometry  # noqa: E402
from pontons_alu_01.variantes_lot51ter import variants  # noqa: E402

LOT = "lot51quater"
SCRIPT = Path(__file__).resolve().parent / "scripts" / "paraview" / "vues_3d_pontons.py"
WIDTH, HEIGHT = 1920, 1080
PLANKS_TOP = 1.445
"""Top of the planks (m NGF), consigne of lot 51 quater (P60): drawn, not modelled."""


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        head = stream.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        message = f"{path.name} : pas un PNG"
        raise ValueError(message)
    width, height = struct.unpack(">II", head[16:24])
    return int(width), int(height)


def run_pvbatch(
    ctx: ProjectContext, code: str, exports: Path, out: Path, combos: Path | None
) -> list[str]:
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415

    salome = load_mesh_config(ctx.repo_root / "config" / "validation.yaml").salome
    image = Path(str(salome.image_path)).expanduser()
    runtime = shutil.which("singularity")
    if runtime is None or not image.is_file():
        message = "vues 3D : Singularity ou l'image Salomé-Méca absent (VM seulement)"
        raise RuntimeError(message)
    out.mkdir(parents=True, exist_ok=True)
    folders = {SCRIPT.parent, exports.resolve(), out.resolve()}
    if combos is not None:
        folders.add(combos.resolve().parent)
    extra = f" --combinaisons {combos.resolve()}" if combos is not None else ""
    command = (
        f"source {salome.install_root}/salome_prerequisites.sh >/dev/null 2>&1; "
        "unset DISPLAY; export HWLOC_COMPONENTS=-gl; "
        f"cd {out.resolve()} && xvfb-run -a -s '-screen 0 1920x1200x24' pvbatch "
        f"--no-mpi {SCRIPT} --variante {code} --dossier {exports.resolve()} "
        f"--sortie {out.resolve()}{extra}"
    )
    argv = [runtime, "exec", "--containall", "--cleanenv", "--no-home"]
    for folder in sorted(folders):
        argv += ["--bind", f"{folder}:{folder}"]
    argv += [str(image), "bash", "-c", command]
    result = subprocess.run(  # noqa: S603 -- fixed argv
        argv, capture_output=True, text=True, timeout=3600, check=False
    )
    (out / f"pvbatch_{code}.log").write_text(result.stdout + result.stderr, "utf-8")
    if result.returncode != 0:
        message = f"pvbatch {code} : code {result.returncode} : {result.stderr[-800:]}"
        raise RuntimeError(message)
    return [
        line[6:] for line in result.stdout.splitlines() if line.startswith("[PNG] ")
    ]


def transverse_positions(exports: Path) -> dict[str, list[float]]:
    """Y of the nodes of each family in noeuds.csv of the variant (model positions)."""
    with (exports / "noeuds.csv").open(encoding="utf-8") as stream:
        lines = [line for line in stream if not line.startswith("#")]
    out: dict[str, set[float]] = {}
    for row in csv.DictReader(lines, delimiter=";"):
        for group in row["groupes"].split("|"):
            out.setdefault(group, set()).add(float(row["y"]))
    return {k: sorted(v) for k, v in out.items()}


def section_view(code: str, exports: Path, path: Path) -> None:
    """View 6: transverse section at the axis of chevêtre C1 of pier P1."""
    v = variants()[code]
    g = geometry(v.mesh_overrides)
    lv = g.levels
    f = g.footings[0]
    beam = v.beam_side_mm / 1000.0
    purlin = v.purlin_side_mm / 1000.0
    ys = transverse_positions(exports)
    beams_y = max(ys["POUTRES_PRINC"])
    pins_y = beams_y
    purlins_y = ys["PANNES_SEC"]
    piles_y = ys["PILES"]
    cap = ys["CHEV_P1_C1"]
    fig, ax = plt.subplots(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100)
    ax.add_patch(
        Rectangle(
            (-1.0, lv["dessus_tablier"]),
            2.0,
            PLANKS_TOP - lv["dessus_tablier"],
            color="#c8a165",
            label="platelage (dessin, non modélisé)",
        )
    )
    for s in (-1, 1):
        y = s * beams_y
        ax.add_patch(
            Rectangle(
                (y - beam / 2, lv["poutres"] - beam / 2),
                beam,
                beam,
                color="#1f77b4",
                label="poutres principales" if s < 0 else None,
            )
        )
        ax.add_patch(
            Rectangle(
                (s * pins_y - 0.15, lv["axe_appui"] - 0.07),
                0.30,
                0.035,
                color="#e377c2",
                label="platines (représentation)" if s < 0 else None,
            )
        )
        ax.add_patch(
            Circle(
                (s * pins_y, lv["axe_appui"]),
                0.02,
                color="#7f1f5f",
                label="axes d'appui Ø 0,04 (représentation)" if s < 0 else None,
            )
        )
    for k, y in enumerate(purlins_y):
        ax.add_patch(
            Rectangle(
                (y - purlin / 2, lv["pannes"] - purlin / 2),
                purlin,
                purlin,
                color="#ff7f0e",
                label="pannes" if k == 0 else None,
            )
        )
    ax.add_patch(
        Rectangle(
            (cap[0], lv["tete_piles"]),
            cap[-1] - cap[0],
            lv["dessus_chevetre"] - lv["tete_piles"],
            color="#9467bd",
            label="chevêtre 0,40 × 0,40",
        )
    )
    top_footing = f.z + 0.10
    for k, y in enumerate(piles_y):
        ax.add_patch(
            Rectangle(
                (y - 0.25, top_footing),
                0.50,
                lv["tete_piles"] - top_footing,
                color="#8c564b",
                label="piles Ø 0,50" if k == 0 else None,
            )
        )
    ax.add_patch(
        Rectangle(
            (f.ys[0], f.z - 0.10),
            f.ys[-1] - f.ys[0],
            0.20,
            color="#7f7f7f",
            label="semelle 2,60 × 0,20",
        )
    )
    levels = [
        (PLANKS_TOP, "dessus du platelage"),
        (lv["dessus_tablier"], "dessus des poutres et des pannes"),
        (lv["pannes"], f"axe des pannes {v.purlin_side_mm:g} × {v.purlin_side_mm:g}"),
        (lv["poutres"], "axe des poutres principales"),
        (lv["sous_face_poutres"], "sous-face des poutres principales"),
        (lv["axe_appui"], "axe d'appui (P54)"),
        (lv["dessus_chevetre"], "dessus du chevêtre"),
        (lv["axe_anneau"], "axe de l'anneau"),
        (lv["tete_piles"], "arase inférieure de l'anneau, tête des piles"),
        (top_footing, "dessus de la semelle"),
        (f.z, "plan moyen de la semelle (modèle)"),
        (f.z - 0.10, "fond de la semelle"),
    ]
    text_y = None
    for z, label in sorted(levels, reverse=True):
        ty = z if text_y is None else min(z, text_y - 0.075)
        text_y = ty
        ax.plot([1.35, 1.75], [z, z], color="black", lw=0.6)
        ax.plot([1.75, 1.85], [z, ty], color="black", lw=0.6)
        ax.text(
            1.88,
            ty,
            f"{z:+.3f} NGF   {label}".replace(".", ","),
            va="center",
            fontsize=11,
        )
    ax.plot([2.6, 3.1], [f.z - 0.35] * 2, color="black", lw=3)
    ax.text(2.85, f.z - 0.42, "0,50 m", ha="center", va="top", fontsize=11)
    ax.set_xlim(-2.0, 3.6)
    ax.set_ylim(f.z - 0.6, PLANKS_TOP + 0.25)
    ax.set_aspect("equal")
    ax.set_xlabel("Y (m)")
    ax.set_ylabel("Z (m NGF)")
    ax.legend(loc="upper left", fontsize=10)
    ax.set_title(
        f"PONTONS-ALU-01, variante {code} - vue 6 : coupe transversale sur la palée "
        "P1, "
        f"axe du chevêtre C1 (X = {v.stations[0]:g} m), cotes NGF (P53, P54)",
        fontsize=13,
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
        )
        section = out / f"{code}_vue6_coupe_transversale_P1.png"
        section_view(code, root / "exports" / code, section)
        # pvbatch quitte par os._exit : ses lignes [PNG] peuvent manquer, on recense
        # les fichiers écrits.
        made = sorted(str(p) for p in out.glob(f"{code}_vue*.png"))
        for name in made:
            p = Path(name)
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


__all__ = ["png_size", "section_view", "step_vues"]
