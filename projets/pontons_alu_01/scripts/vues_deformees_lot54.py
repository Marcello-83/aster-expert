"""Contrôle post-lot 54: renders the three deformed shapes of the panne B (pvbatch of
Salomé-Méca in Singularity), trims the white margins and checks the images.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/vues_deformees_lot54.py \
        --dossier <champs combinés> --sortie <dossier PNG>

Writes the three PNG (3 200 px wide), `controle_vues.json` (size, share of the width taken
by the structure, no contact with the border, background) and prints a summary.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from aster_expert.meshing.config import load_mesh_config

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).resolve().parent / "paraview" / "vues_deformees_lot54_pv.py"
NAMES = (
    "panneB_deformee_A_DY_ELS_c.png",
    "panneB_deformee_B_DY_ELU_acc.png",
    "panneB_deformee_C_DX_hors_T_ELS_c.png",
)
MARGIN = 24


def run_pvbatch(folder: Path, out: Path) -> str:
    salome = load_mesh_config(ROOT / "config" / "validation.yaml").salome
    image = Path(str(salome.image_path)).expanduser()
    runtime = shutil.which("singularity")
    if runtime is None or not image.is_file():
        message = "Singularity ou image Salomé-Méca absent (VM seulement)"
        raise RuntimeError(message)
    out.mkdir(parents=True, exist_ok=True)
    command = (
        f"source {salome.install_root}/salome_prerequisites.sh >/dev/null 2>&1; "
        "unset DISPLAY; export HWLOC_COMPONENTS=-gl; "
        f"cd {out.resolve()} && xvfb-run -a -s '-screen 0 3600x1800x24' pvbatch "
        f"--no-mpi {SCRIPT} --dossier {folder.resolve()} --sortie {out.resolve()}"
    )
    argv = [runtime, "exec", "--containall", "--cleanenv", "--no-home"]
    for path in sorted({SCRIPT.parent, folder.resolve(), out.resolve()}):
        argv += ["--bind", f"{path}:{path}"]
    argv += [str(image), "bash", "-c", command]
    result = subprocess.run(  # noqa: S603 -- fixed argv
        argv, capture_output=True, text=True, timeout=3600, check=False
    )
    (out / "pvbatch_deformees_lot54.log").write_text(
        result.stdout + result.stderr, "utf-8"
    )
    if result.returncode != 0:
        message = f"pvbatch : code {result.returncode} : {result.stderr[-800:]}"
        raise RuntimeError(message)
    return result.stdout


def trim(path: Path) -> dict[str, object]:
    img = Image.open(path).convert("RGB")
    a = np.asarray(img)
    ink = (a < 245).any(axis=2)
    rows = np.flatnonzero(ink.any(axis=1))
    top, bottom = max(rows[0] - MARGIN, 0), min(rows[-1] + MARGIN + 1, a.shape[0])
    # keep the full width (3 200 px asked): trim the height only
    img.crop((0, int(top), a.shape[1], int(bottom))).save(path, dpi=(200, 200))
    b = np.asarray(Image.open(path).convert("RGB"))
    ink = (b < 245).any(axis=2)
    cols = np.flatnonzero(ink.any(axis=0))
    rows = np.flatnonzero(ink.any(axis=1))
    # the structure alone: the coloured or grey pixels, not the black text
    sat = (b.max(axis=2).astype(int) - b.min(axis=2).astype(int)) > 12
    grey = np.abs(b.astype(int) - 204).max(axis=2) < 6
    struct = sat | grey
    scol = np.flatnonzero(struct.any(axis=0))
    return {
        "taille_px": [int(b.shape[1]), int(b.shape[0])],
        "encre_gauche_px": int(cols[0]),
        "encre_droite_px": int(b.shape[1] - 1 - cols[-1]),
        "encre_haut_px": int(rows[0]),
        "encre_bas_px": int(b.shape[0] - 1 - rows[-1]),
        "part_largeur_ouvrage": float((scol[-1] - scol[0] + 1) / b.shape[1]),
        "fond_blanc": bool((b[0, 0] == 255).all()),
        "aucune_troncature": bool(
            cols[0] > 0
            and cols[-1] < b.shape[1] - 1
            and rows[0] > 0
            and rows[-1] < b.shape[0] - 1
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dossier", type=Path, required=True)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    run_pvbatch(args.dossier, args.sortie)
    report = {name: trim(args.sortie / name) for name in NAMES}
    (args.sortie / "controle_vues.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    ok = True
    for name, r in report.items():
        good = (
            r["taille_px"][0] == 3200  # type: ignore[index]
            and r["part_largeur_ouvrage"] >= 0.85  # type: ignore[operator]
            and r["aucune_troncature"]
            and r["fond_blanc"]
        )
        ok = ok and bool(good)
        print(name, r, "OK" if good else "ÉCART")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
