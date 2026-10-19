"""Lot 52 of PONTONS-ALU-01: PRO geometry (P62 to P66), from the mesh to the delivery.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot52.py <étape> \
        [--variantes B52,A52,B52P4] [--paralleles 3] [--depot <dossier>]

Étapes : `maillage` (Salomé et `mesh check` seuls), `executer` (maillage par géométrie,
`mesh check`, génération, niveau B, exécution en parallèle), `controles` (harnais D du tronc
commun, variante par variante), `exports` (recombinaison P60/P61, CSV, `.npz`, comparaison,
géométrie des nœuds, contrôles, `exports_lot52`), `med` (B52 : structure, charges et
résultats sur un support commun, `med_lot52`), `vues` (B52, `vues_lot52`), `depot` (copie
sur le partage, empreintes), `tout`. Même enchaînement que scripts/lot51ter.py et
scripts/lot51quater.py ; tout est écrit sous `resultats/lot52/`, l'état de chaque variante
dans `resultats/lot52/etat.json`. Le .comm, le maillage et les invariants viennent des
seuls modules du projet (generation_lot52, maillage_ponton_52.py, invariants_lot52) et la
vérification du tronc commun (mesh check, validation B, harnais D).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from aster_expert.meshing.check import check_med
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.run import run_salome_script
from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.errors import ProjectError
from aster_expert.projet.pipeline import Runtime, _export_text, execute
from aster_expert.validation.validate import validate_comm_file
from pontons_alu_01.geometrie_lot52 import SCRIPT, geometry, params_json
from pontons_alu_01.invariants_lot52 import text as invariants_text
from pontons_alu_01.variantes_lot52 import ENV, Variant52, variants

ROOT = Path(__file__).resolve().parents[3]
STEM = "pontons_alu_01"
LOT = "lot52"
MED_VARIANTS = ("B52",)


def lot_dir(ctx: ProjectContext) -> Path:
    return ctx.results_dir / LOT


def load_state(ctx: ProjectContext) -> dict[str, Any]:
    path = lot_dir(ctx) / "etat.json"
    if path.is_file():
        loaded: dict[str, Any] = json.loads(path.read_text("utf-8"))
        return loaded
    return {}


def save_state(ctx: ProjectContext, state: dict[str, Any]) -> None:
    path = lot_dir(ctx) / "etat.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", "utf-8")


def mesh_key(v: Variant52) -> str:
    """Variants with the same mesh share it (B52 and B52P4: same outer sizes)."""
    return f"g{v.geometry}_pannes{v.purlin_side_mm:g}_montants{v.post_side_mm:g}"


def mesh(ctx: ProjectContext, rt: Runtime, v: Variant52) -> dict[str, Any]:
    """Salome run (or its cache) and `mesh check` for one mesh key."""
    out = lot_dir(ctx) / "maillage"
    out.mkdir(parents=True, exist_ok=True)
    overrides = v.mesh_overrides
    key = mesh_key(v)
    params = out / f"params_{key}.json"
    params.write_bytes(params_json(overrides))
    inv = out / f"invariants_{key}.yaml"
    inv.write_text(invariants_text(geometry(overrides)), encoding="utf-8")
    config = load_mesh_config(ctx.repo_root / "config" / "validation.yaml")
    run = run_salome_script(
        SCRIPT, project_root=ctx.repo_root, config=config, params=params
    )
    digest, _ = rt.aster()
    report = check_med(
        Path(run.med_path),
        inv,
        project_root=ctx.repo_root,
        config=config,
        docker_bin=rt.docker_bin(),
        image_ref=f"{rt.image_repository}@{digest}",
    )
    held = sum(r.ok for r in report.results)
    if not report.ok:
        message = f"mesh check {key} : {held}/{len(report.results)}"
        raise ProjectError(message)
    shutil.copyfile(report.report_path, out / f"rapport_mesh_check_{key}.txt")
    return {
        "med": run.med_path,
        "med_sha256": run.med_sha256,
        "from_cache": run.from_cache,
        "mesh_check": f"{held}/{len(report.results)}",
    }


def prepare(
    ctx: ProjectContext, rt: Runtime, v: Variant52, med: Path
) -> dict[str, Any]:
    """`.comm`, `.export` and mesh copy of one variant, then level B."""
    from pontons_alu_01.generation_lot52 import build_comm  # noqa: PLC0415

    target = lot_dir(ctx) / v.code / f"{STEM}.comm"
    target.parent.mkdir(parents=True, exist_ok=True)
    text, report = build_comm(ctx, mesh_label=med.name, variant=v)
    _, version = rt.aster()
    report["aster_version"] = version
    target.write_text(text, encoding="utf-8")
    (target.parent / "generation.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    fmt = ctx.declaration.comm.export.mesh_format
    shutil.copyfile(med, target.with_name(f"{STEM}.{fmt}"))
    target.with_name(f"{STEM}.export").write_text(_export_text(ctx, STEM), "utf-8")
    validation = validate_comm_file(
        target,
        project_root=ctx.repo_root,
        workroot=rt.workroot,
        docker_bin=rt.docker_bin(),
        image_repository=rt.image_repository,
        timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
    )
    n_checked = len(validation.commands_checked)
    n_total = n_checked + len(validation.commands_not_checked)
    if not validation.valid:
        message = f"{v.code} : niveau B {validation.verdict}, {n_checked}/{n_total}"
        raise ProjectError(message)
    return {
        "comm": str(target),
        "validation": f"{validation.verdict}, {n_checked}/{n_total} commandes",
    }


def run_one(ctx: ProjectContext, rt: Runtime, comm: Path) -> dict[str, Any]:
    try:
        report = execute(ctx, rt, comm)
    except ProjectError as exc:
        return {
            "statut": "échec",
            "message": str(exc),
            "erreurs": list(exc.problems),
        }
    alarms = [m.identifier for m in report.messages if m.kind == "<A>"]
    return {
        "statut": report.status,
        "execution_dir": report.work_dir,
        "duree_s": report.duration_s,
        "alarmes": alarms,
    }


def step_maillage(ctx: ProjectContext, rt: Runtime, codes: list[str]) -> None:
    state = load_state(ctx)
    all_v = variants()
    done: dict[str, dict[str, Any]] = {}
    for code in codes:
        key = mesh_key(all_v[code])
        if key not in done:
            done[key] = mesh(ctx, rt, all_v[code])
            print(f"maillage {key} : {done[key]}")
        state.setdefault(code, {})["maillage"] = done[key]
    save_state(ctx, state)


def step_executer(
    ctx: ProjectContext, rt: Runtime, codes: list[str], workers: int
) -> None:
    state = load_state(ctx)
    all_v = variants()
    meshes: dict[str, dict[str, Any]] = {}
    for code in codes:
        key = mesh_key(all_v[code])
        if key not in meshes:
            meshes[key] = mesh(ctx, rt, all_v[code])
            print(f"maillage {key} : {meshes[key]}")
    prepared: dict[str, Path] = {}
    for code in codes:
        v = all_v[code]
        info = prepare(ctx, rt, v, Path(meshes[mesh_key(v)]["med"]))
        state.setdefault(code, {}).update({"maillage": meshes[mesh_key(v)], **info})
        prepared[code] = Path(info["comm"])
        print(f"{code} : {info['validation']}")
    save_state(ctx, state)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {c: pool.submit(run_one, ctx, rt, p) for c, p in prepared.items()}
        for code, fut in futures.items():
            result = fut.result()
            state[code]["execution"] = result
            print(f"{code} : {result['statut']} {result.get('message', '')[:300]}")
    save_state(ctx, state)


def step_controles(ctx: ProjectContext, codes: list[str]) -> None:
    from aster_expert.controles.equilibre import level_d_controls  # noqa: PLC0415

    state = load_state(ctx)
    for code in codes:
        execution = state.get(code, {}).get("execution", {})
        if "execution_dir" not in execution:
            print(f"{code} : pas d'exécution réussie, harnais non lancé")
            continue
        run_dir = Path(execution["execution_dir"])
        os.environ[ENV] = code
        ctx.cache.clear()
        out = lot_dir(ctx) / code / "controles"
        level_d_controls(
            ctx,
            mess_path=run_dir / "proc.0" / "fort.6",
            comm_path=run_dir / f"{STEM}.comm",
            mesh_path=Path(state[code]["maillage"]["med"]),
            out_dir=out,
        )
        summary = json.loads((out / "controles_d.json").read_text("utf-8"))
        state[code]["controles"] = summary["verdict"]
        print(f"{code} : harnais D {summary['verdict']}")
    os.environ.pop(ENV, None)
    save_state(ctx, state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "etape",
        choices=(
            "maillage",
            "executer",
            "controles",
            "exports",
            "med",
            "vues",
            "depot",
            "tout",
        ),
    )
    parser.add_argument("--variantes", default="")
    parser.add_argument("--paralleles", type=int, default=3)
    parser.add_argument("--depot", type=Path, default=None)
    args = parser.parse_args()
    ctx = load_project(STEM, ROOT)
    rt = Runtime(ROOT)
    codes = [c for c in args.variantes.split(",") if c] or list(variants())
    try:
        if args.etape == "maillage":
            step_maillage(ctx, rt, codes)
        if args.etape in ("executer", "tout"):
            step_executer(ctx, rt, codes, args.paralleles)
        if args.etape in ("controles", "tout"):
            step_controles(ctx, codes)
        if args.etape in ("exports", "tout"):
            from pontons_alu_01.exports_lot52 import step_exports  # noqa: PLC0415

            step_exports(ctx, codes, load_state(ctx), workers=args.paralleles)
        if args.etape in ("med", "tout"):
            from pontons_alu_01.med_lot52 import step_med  # noqa: PLC0415

            step_med(ctx, [c for c in codes if c in MED_VARIANTS], load_state(ctx))
        if args.etape in ("vues", "tout"):
            from pontons_alu_01.vues_lot52 import step_vues  # noqa: PLC0415

            step_vues(ctx, [c for c in codes if c in MED_VARIANTS], load_state(ctx))
        if args.etape in ("depot", "tout"):
            from pontons_alu_01.depot_lot52 import step_depot  # noqa: PLC0415

            step_depot(ctx, codes, args.depot)
    except ProjectError:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
