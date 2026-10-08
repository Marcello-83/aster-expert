"""Lot 49, step 3.3 -- mutation test of the MED of loads.

A load is moved on purpose to another group of cells in a copy of the post-processing
`.comm` of the slab (never in the project's own files): `CH_Q`
(`FORCE_COQUE/FZ` = −10 kN/m² on `DALLE`, resultant −240 kN declared in
`projet.yaml`) is applied on the shell cells of `CENTRE_V` (the cells around the centre
node, `INTERSEC` with `DALLE`: `CENTRE_V` also holds edges outside the model, DIAG-017).
The mutated copy is run, its MED of loads read (`medcoupling`, in the container), and
the control of the deliverables (CTL-013 on the MED: Σ of the nodal forces against the
declared resultant) must fail, while the point of application of the vertical
resultant and the pictures show where the load went.

Sub-commands (run in order):

- `preparer`: `resultats/livrables_mutation/` (mutated `.comm`, `.export`, mesh);
- `lancer`: `aster-expert run` on it;
- `analyser`: `mutation.json` (control of the original and of the mutated loads, point
  of application), `charges.vtu` and the pictures of the mutated loads.

Usage:
  .venv/bin/python projets/dalle_appuyee_01/scripts/mutation_charges_lot49.py preparer
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.livrables.calcul import resultant
from aster_expert.livrables.paraview import render_png, write_scripts
from aster_expert.livrables.vtu import Grid, check_identical, grid_from_mesh, write_vtu
from aster_expert.projet.context import load_project
from aster_expert.report.med_read import run_med_script, take_arrays

PROJECT = "dalle_appuyee_01"
ORIGINAL = 'CH_Q = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="DALLE", FZ=-10000.0))'
MUTATED = (
    "# Essai de mutation (lot 49) : CENTRE_V porte aussi des segments hors du modèle\n"
    "# (DIAG-017) ; la charge va sur ses seules mailles de dalle.\n"
    'MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=_F(NOM="MUT_Q", '
    'INTERSEC=("CENTRE_V", "DALLE")))\n'
    'CH_Q = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="MUT_Q", FZ=-10000.0))'
)
STEM = "dalle_mutation"


def _ctx() -> Any:
    return load_project(PROJECT, ROOT)


def _dir() -> Path:
    out: Path = _ctx().results_dir / "livrables_mutation"
    return out


def preparer() -> None:
    post = _ctx().results_dir / "livrables" / "post"
    text = (post / "dalle_livrables.comm").read_text(encoding="utf-8")
    if text.count(ORIGINAL) != 1:
        message = "définition de CH_Q introuvable telle quelle dans le .comm"
        raise SystemExit(message)
    out = _dir()
    out.mkdir(parents=True, exist_ok=True)
    mutated = text.replace(ORIGINAL, MUTATED).replace(
        "# Lot 49 -- .comm de post-traitement des livrables",
        "# Lot 49 -- ESSAI DE MUTATION (CH_Q déplacée sur CENTRE_V), copie du .comm de "
        "post-traitement des livrables",
    )
    (out / f"{STEM}.comm").write_text(mutated, encoding="utf-8")
    shutil.copyfile(post / "dalle_livrables.mmed", out / f"{STEM}.mmed")
    shutil.copyfile(
        post / "dalle_livrables.connaissances.yaml", out / f"{STEM}.connaissances.yaml"
    )
    export = (post / "dalle_livrables.export").read_text(encoding="utf-8")
    (out / f"{STEM}.export").write_text(
        export.replace("dalle_livrables", STEM), encoding="utf-8"
    )
    print(f"{out / (STEM + '.comm')} : CH_Q sur CENTRE_V ∩ DALLE au lieu de DALLE")


def lancer() -> None:
    comm = _dir() / f"{STEM}.comm"
    completed = subprocess.run(  # noqa: S603 - fixed argv
        [str(ROOT / ".venv/bin/aster-expert"), "run", str(comm)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    (_dir() / "execution.log").write_text(output, encoding="utf-8")
    run = next(
        (
            w
            for w in output.split()
            if "data/processed/runs/" in w and "proc.0" not in w
        ),
        None,
    )
    print(f"code {completed.returncode} ; {run}")


def _loads(med: Path) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    payload = run_med_script(med, ["extract", "FN_G", "FN_Q"], project_root=ROOT)
    return payload, take_arrays(payload)


def _run_dir() -> Path:
    log = (_dir() / "execution.log").read_text(encoding="utf-8")
    for line in log.splitlines():
        if line.startswith("Répertoire"):
            return Path(line.split(":", 1)[1].strip())
    message = "répertoire d'exécution introuvable dans execution.log"
    raise SystemExit(message)


def analyser() -> None:
    from aster_expert.controles.equilibre import expected_resultant  # noqa: PLC0415

    ctx = _ctx()
    plan = json.loads(
        (ctx.results_dir / "livrables" / "post" / "plan.json").read_text("utf-8")
    )
    unit = plan["unite_med_charges"]
    original = ctx.results_dir / "livrables" / "med" / "charges.med"
    mutated = _run_dir() / "proc.0" / f"fort.{unit}"
    case = next(c for c in ctx.declaration.controls.cases if c.name == "Q")
    expected, _spec = expected_resultant(
        ctx, case, comm_path=Path(), mesh_path=Path(), out_dir=_dir()
    )
    report: dict[str, Any] = {
        "mutation": f"{ORIGINAL} -> {MUTATED}",
        "attendu_n": expected,
    }
    for label, med in (("original", original), ("mute", mutated)):
        _payload, arrays = _loads(med)
        coords = arrays["coords"]
        if coords.shape[1] < 3:
            coords = np.hstack([coords, np.zeros((len(coords), 3 - coords.shape[1]))])
        sums = resultant(coords, arrays["FN_Q"])
        gap = abs(sums["FZ"] - expected["DZ"]) / max(abs(v) for v in expected.values())
        report[label] = {
            "somme_n": sums,
            "ecart_relatif": gap,
            "verdict": "RÉUSSI"
            if gap <= ctx.declaration.controls.threshold
            else "ÉCHEC",
        }
        if label == "mute":
            mesh = {k: v for k, v in arrays.items() if k.startswith("conn_")}
            mesh["coords"] = arrays["coords"]
            for k in list(mesh):
                if k.startswith("conn_"):
                    level = k.split("_")[1]
                    width = mesh[k].shape[1]
                    mesh[f"type_{level}"] = np.full(
                        len(mesh[k]), {4: 4, 3: 3, 2: 1, 1: 0}[width]
                    )
            grid, _order = grid_from_mesh(mesh)
            g = Grid(grid.points, grid.connectivity, grid.offsets, grid.types)
            for name in ("FN_G", "FN_Q"):
                for c, comp in enumerate(("DX", "DY", "DZ")):
                    g.point_data[f"{name}_{comp}"] = arrays[name][:, c].astype(float)
            vtu = _dir() / "vtu"
            write_vtu(vtu / "charges.vtu", g)
            report["vtu"] = check_identical(g, vtu / "charges.vtu")
            norms = {
                n: float(np.linalg.norm(arrays[n][:, :3], axis=1).max())
                for n in ("FN_G", "FN_Q")
            }
            size = float(np.linalg.norm(g.points.max(axis=0) - g.points.min(axis=0)))
            manifest = {
                "projet": f"{PROJECT} (mutation)",
                "echelles": {
                    "taille_du_modele_m": size,
                    "charges": norms,
                    "deplacements": {},
                },
                "charges": [
                    {"nom_med": n, "composantes": ["DX", "DY", "DZ"]} for n in norms
                ],
                "champs": [],
            }
            script, _r = write_scripts(manifest, vtu)
            report["png"] = render_png(ctx, script, _dir() / "png")
    out = _dir() / "mutation.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(
        json.dumps(
            {k: report[k] for k in ("original", "mute")}, indent=1, ensure_ascii=False
        )
    )


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    {"preparer": preparer, "lancer": lancer, "analyser": analyser}[argv[0]]()


if __name__ == "__main__":
    main(sys.argv[1:])
