"""`aster-expert projet <nom> <étape>`: the existing commands chained on one
project (lot 41, étape 2.5).

Steps, in order (`tout` runs them all):

1. `verifier`   -- the declaration against its files, the fiche's blockers;
2. `maillage`   -- `mesh run` (Salomé skipped when the mesh cache already holds a
   verified MED for the script and parameters fingerprints) then `mesh check`;
3. `generer`    -- the project's generator, after the refusals of étape 3;
4. `valider`    -- level B, `checkCommandSyntax` in the container;
5. `executer`   -- level C, `run_aster` in the container, with its report;
6. `controles`  -- level D: equilibrium, gravity, symmetry;
7. `synthese`   -- the project's synthesis of the execution;
8. `combinaisons` -- combined element forces;
9. `ferraillage` -- `CALC_FERRAILLAGE` on the combined forces, then the checks.

Every output goes under the project's results directory; `etat.json` there
records what each step produced (MED, `.comm`, execution directory), so that a
step can run alone on what the previous ones left. A step never runs on a
declaration `check_project` refuses, and never reads a file of another project.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from aster_expert.projet.check import (
    FOR_GENERATION,
    FOR_REPORT,
    require_valid_project,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

STATE_NAME = "etat.json"
STEPS = (
    "verifier",
    "maillage",
    "generer",
    "valider",
    "executer",
    "controles",
    "synthese",
    "combinaisons",
    "ferraillage",
)
"""Steps of `tout`, in order. `livrables` (lot 49) is asked for by name: it runs a
post-processing execution of its own."""


class ProjectState(BaseModel):
    """What the steps produced, for the next ones."""

    model_config = ConfigDict(extra="forbid")

    mesh_med: str | None = None
    mesh_check_report: str | None = None
    comm: str | None = None
    validation: dict[str, Any] | None = None
    execution_dir: str | None = None
    rebar_executions: dict[str, str] = {}


def _state_path(ctx: ProjectContext) -> Path:
    return ctx.results_dir / STATE_NAME


def load_state(ctx: ProjectContext) -> ProjectState:
    path = _state_path(ctx)
    if not path.is_file():
        return ProjectState()
    return ProjectState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(ctx: ProjectContext, state: ProjectState) -> None:
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    _state_path(ctx).write_text(state.model_dump_json(indent=2) + "\n", "utf-8")


def _require(value: str | None, what: str, step: str) -> Path:
    if value is None:
        message = f"{what} inconnu : lancer d'abord l'étape « {step} »"
        raise ProjectError(message)
    path = Path(value)
    if not path.exists():
        message = f"{what} introuvable : {path} (relancer l'étape « {step} »)"
        raise ProjectError(message)
    return path


def display_path(path: Path, repo_root: Path) -> Path:
    """Relative to the repository when the command runs from it (the form the
    reports of the first project recorded), absolute otherwise."""
    resolved = path.resolve()
    if Path.cwd().resolve() == repo_root.resolve() and resolved.is_relative_to(
        repo_root.resolve()
    ):
        return resolved.relative_to(repo_root.resolve())
    return resolved


class Runtime:
    """Access to the container and to the configuration of the repository."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def aster(self) -> tuple[str, str]:
        """(digest, version) of the installation detected and its catalogue."""
        from aster_expert.execution.errors import (  # noqa: PLC0415
            EnvironmentDetectionError,
        )
        from aster_expert.validation.errors import ValidationRunError  # noqa: PLC0415
        from aster_expert.validation.validate import (  # noqa: PLC0415
            resolve_digest_for_version,
        )

        try:
            return resolve_digest_for_version(
                self.repo_root / "data" / "processed" / "catalogue",
                None,
                self.repo_root / "config" / "versions.yaml",
            )
        except (EnvironmentDetectionError, ValidationRunError, OSError) as exc:
            message = f"version de Code_Aster non résolue : {exc}"
            raise ProjectError(message) from exc

    def docker_bin(self) -> Path:
        from aster_expert.execution.docker_client import (  # noqa: PLC0415
            find_docker_binary,
        )
        from aster_expert.execution.errors import (  # noqa: PLC0415
            EnvironmentDetectionError,
        )

        try:
            return find_docker_binary(os.environ.get("ASTER_DOCKER_BIN") or None)
        except EnvironmentDetectionError as exc:
            message = f"Docker introuvable : {exc}"
            raise ProjectError(message) from exc

    @property
    def image_repository(self) -> str:
        return os.environ.get("ASTER_IMAGE_REPOSITORY", "simvia/code_aster")

    @property
    def workroot(self) -> Path:
        raw = (os.environ.get("ASTER_CONTAINER_WORKROOT") or "").strip()
        return Path(raw) if raw else self.repo_root / "data" / "processed" / "workroot"


# --- steps -------------------------------------------------------------------------


def step_verifier(ctx: ProjectContext, rt: Runtime) -> list[str]:  # noqa: ARG001
    require_valid_project(ctx)
    blockers = ctx.blockers_for("verifier")
    if blockers:
        message = f"projet {ctx.declaration.name} : la fiche ou les données bloquent"
        raise ProjectError(message, blockers)
    planned = len(ctx.sheet().planned_commands)
    exemption = ctx.declaration.planned_commands_exemption
    if not planned and exemption is None:
        message = (
            f"projet {ctx.declaration.name} : la fiche ne déclare aucune commande "
            "prévue (`planned_commands`), donc `fiche obligatoires` ne lit rien"
        )
        raise ProjectError(
            message,
            (
                "écrire les commandes : aster-expert fiche prevoir "
                f"{ctx.declaration.name} --ecrire",
                "ou déclarer `planned_commands_exemption` (motif) dans projet.yaml",
            ),
        )
    if ctx.declaration.deliverables is None:
        message = (
            f"projet {ctx.declaration.name} : la section `deliverables` (contrat de "
            "livrables, lot 49) est obligatoire"
        )
        raise ProjectError(
            message,
            (
                "déclarer les champs livrés par famille (déplacements, efforts, "
                "réactions, ressorts...), les combinaisons et les livrables non "
                "pertinents avec leur motif (aster_expert.projet.declaration."
                "DeliverablesSection)",
            ),
        )
    planned_line = (
        f"Commandes prévues : {planned} (`fiche obligatoires`)."
        if planned
        else f"Commandes prévues : aucune, exemption déclarée : {exemption}"
    )
    return [
        f"Déclaration {ctx.declaration.name} ({ctx.declaration.structure}) : "
        "cohérente avec ses fichiers.",
        f"Fiche : {len(ctx.sheet().entries)} entrées, aucun bloqueur de génération.",
        planned_line,
        *ctx.waiver_notes("verifier"),
    ]


def step_maillage(ctx: ProjectContext, rt: Runtime) -> list[str]:
    from aster_expert.meshing.check import check_med  # noqa: PLC0415
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415
    from aster_expert.meshing.errors import MeshError  # noqa: PLC0415
    from aster_expert.meshing.run import run_salome_script  # noqa: PLC0415

    require_valid_project(ctx)
    d = ctx.declaration
    try:
        config = load_mesh_config(ctx.repo_root / "config" / "validation.yaml")
    except MeshError as exc:
        message = f"configuration du maillage : {exc}"
        raise ProjectError(message) from exc
    out = ctx.results_dir / "maillage"
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    if d.mesh.med is not None:
        med = ctx.path(d.mesh.med)
        lines.append(f"Maillage déclaré : {med}")
    elif d.mesh.script is not None:
        params = None
        if d.mesh.parameters is not None:
            params = out / "params.json"
            params.write_bytes(ctx.extension(d.mesh.parameters)(ctx))
        try:
            run = run_salome_script(
                ctx.path(d.mesh.script),
                project_root=ctx.repo_root,
                config=config,
                params=params,
            )
        except MeshError as exc:
            message = f"mesh run : {exc}"
            raise ProjectError(message) from exc
        med = Path(run.med_path)
        lines.append(
            (
                "MED déjà vérifié (cache), Salomé non relancé : "
                if run.from_cache
                else "MED produit : "
            )
            + str(med)
        )
    else:
        message = "maillage : ni `med` ni `script` déclaré"
        raise ProjectError(message)
    digest, _ = rt.aster()
    try:
        report = check_med(
            med,
            ctx.path(d.mesh.invariants),
            project_root=ctx.repo_root,
            config=config,
            docker_bin=rt.docker_bin(),
            image_ref=f"{rt.image_repository}@{digest}",
        )
    except MeshError as exc:
        message = f"mesh check : {exc}"
        raise ProjectError(message) from exc
    shutil.copyfile(report.report_path, out / "rapport_mesh_check.txt")
    held = sum(r.ok for r in report.results)
    lines.append(
        f"mesh check : {held}/{len(report.results)} invariants tenus "
        f"({out / 'rapport_mesh_check.txt'})"
    )
    if not report.ok:
        first = next((r for r in report.results if not r.ok), None)
        message = (
            f"mesh check : invariant en écart, premier : {first.label} "
            f"(attendu {first.expected}, obtenu {first.obtained})"
            if first is not None
            else "mesh check : invariant en écart"
        )
        raise ProjectError(message)
    state = load_state(ctx)
    state.mesh_med = str(med)
    state.mesh_check_report = str(out / "rapport_mesh_check.txt")
    save_state(ctx, state)
    return lines


def _export_text(ctx: ProjectContext, stem: str) -> str:
    """The `.export` of a generated `.comm`. Lot 47 quater: `ncpus` and `mpi_nbcpu` come
    from `projet.yaml` (`comm.export`), else from the machine's execution settings
    (`config/machine.local.yaml`, then `config/validation.yaml`); `aster-expert run`
    passes the same values to `docker run`."""
    from aster_expert.execution.config import load_execution_config  # noqa: PLC0415

    e = ctx.declaration.comm.export
    settings = load_execution_config(
        ctx.repo_root / "config" / "validation.yaml"
    ).resource_settings(ctx.repo_root)
    ncpus = e.ncpus if e.ncpus is not None else settings.ncpus
    mpi = e.mpi_nbcpu if e.mpi_nbcpu is not None else settings.mpi_processes
    return (
        f"P time_limit {e.time_limit}\nP memory_limit {e.memory_limit}\n"
        f"P ncpus {ncpus}\nP mpi_nbcpu {mpi}\nP mpi_nbnoeud 1\nF comm {stem}.comm D 1\n"
        f"F {e.mesh_format} {stem}.{e.mesh_format} D {e.mesh_unit}\n"
    )


def generate(
    ctx: ProjectContext,
    rt: Runtime,
    *,
    med: Path | None = None,
    output: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Refusals first (declaration, blockers), then the project's generator; the
    `.comm` is written with its `.export` and a copy of the mesh next to it."""
    require_valid_project(ctx, FOR_GENERATION)
    blockers = ctx.blockers_for("generer")
    if blockers:
        message = "génération refusée, la fiche ou les données ne sont pas prêtes"
        raise ProjectError(message, blockers)
    d = ctx.declaration
    state = load_state(ctx)
    mesh = med or _require(state.mesh_med, "maillage vérifié", "maillage")
    target = output or ctx.path(d.comm.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any]
    if d.comm.file is not None:
        text = ctx.path(d.comm.file).read_text(encoding="utf-8")
        report = {"source": d.comm.file}
    else:
        assert d.comm.generator is not None
        _, version = rt.aster()
        try:
            text, report = ctx.extension(d.comm.generator)(
                ctx,
                fiche_path=ctx.fiche_path,
                data_path=ctx.data_path,
                med_path=mesh,
                aster_version=version,
            )
        except ValueError as exc:
            message = f"le générateur du projet refuse : {exc}"
            raise ProjectError(message) from exc
    target.write_text(text, encoding="utf-8")
    stem = target.stem
    fmt = d.comm.export.mesh_format
    shutil.copyfile(mesh, target.with_name(f"{stem}.{fmt}"))
    target.with_name(f"{stem}.export").write_text(_export_text(ctx, stem), "utf-8")
    state.comm = str(target)
    save_state(ctx, state)
    return target, report


def step_generer(ctx: ProjectContext, rt: Runtime) -> list[str]:
    target, report = generate(ctx, rt)
    lines = [f".comm écrit : {target}"]
    if "comm_sha256" in report:
        lines.append(f"SHA-256 : {report['comm_sha256']}")
    return lines


def step_valider(ctx: ProjectContext, rt: Runtime) -> list[str]:
    from aster_expert.validation.errors import ValidationRunError  # noqa: PLC0415
    from aster_expert.validation.validate import validate_comm_file  # noqa: PLC0415

    state = load_state(ctx)
    comm = _require(state.comm, ".comm", "generer")
    try:
        report = validate_comm_file(
            comm,
            project_root=ctx.repo_root,
            workroot=rt.workroot,
            docker_bin=rt.docker_bin(),
            image_repository=rt.image_repository,
            timeout=int(os.environ.get("ASTER_RUN_TIMEOUT", "1800")),
        )
    except ValidationRunError as exc:
        message = f"validation : {exc}"
        raise ProjectError(message) from exc
    n_checked = len(report.commands_checked)
    n_total = n_checked + len(report.commands_not_checked)
    summary = {
        "validation_level": report.validation_level,
        "valid": report.valid,
        "verdict": report.verdict,
        "commands_checked": n_checked,
        "commands_total": n_total,
        "errors": len(report.errors),
    }
    (ctx.results_dir / "validation.json").write_text(
        json.dumps(json.loads(report.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    state.validation = summary
    save_state(ctx, state)
    line = (
        f"Niveau B : valid={report.valid}, verdict={report.verdict}, "
        f"{n_checked}/{n_total} commandes confrontées, {len(report.errors)} erreur(s)"
    )
    if not report.valid:
        message = f"validation refusée : {line}"
        raise ProjectError(message)
    return [line]


def _place_declaration(ctx: ProjectContext, comm: Path) -> None:
    """Copy the project's declaration of the knowledge applied next to the `.comm`
    (lot 46). Absent: nothing is copied and `execute_comm_file` refuses the run."""
    from aster_expert.connaissances.declaration import companion_path  # noqa: PLC0415

    declared = ctx.declaration.knowledge_applied
    if declared is None:
        return
    source = ctx.path(declared)
    if source.is_file():
        shutil.copyfile(source, companion_path(comm))


def execute(ctx: ProjectContext, rt: Runtime, comm: Path) -> Any:
    """`run_aster` in the container on `comm` (its `.export` next to it);
    refused unless it ends at `FIN`, with the `<F>` errors in the message."""
    from aster_expert.execution.config import load_execution_config  # noqa: PLC0415
    from aster_expert.execution.errors import (  # noqa: PLC0415
        EnvironmentDetectionError,
        ExecutionRunError,
    )
    from aster_expert.execution.execute import execute_comm_file  # noqa: PLC0415

    _place_declaration(ctx, comm)
    try:
        config = load_execution_config(ctx.repo_root / "config" / "validation.yaml")
        digest, version = rt.aster()
        report = execute_comm_file(
            comm,
            project_root=ctx.repo_root,
            config=config,
            docker_bin=rt.docker_bin(),
            image_repository=rt.image_repository,
            image_digest=digest,
            aster_version=version,
            network=os.environ.get("ASTER_CONTAINER_NETWORK", "none"),
        )
    except (EnvironmentDetectionError, ExecutionRunError) as exc:
        message = f"exécution : {exc}"
        raise ProjectError(message) from exc
    if report.status not in ("completed_ok", "completed_with_alarms"):
        errors = tuple(
            f"{m.kind} {m.identifier or ''} (ligne {m.line}) : {m.text[:300]}"
            for m in report.messages
            if m.kind != "<A>"
        )
        message = (
            f"exécution de {comm.name} : statut {report.status} ({report.diag}), "
            f"compte rendu dans {report.work_dir}"
        )
        raise ProjectError(message, errors)
    return report


def step_executer(ctx: ProjectContext, rt: Runtime) -> list[str]:
    state = load_state(ctx)
    comm = _require(state.comm, ".comm", "generer")
    report = execute(ctx, rt, comm)
    state.execution_dir = report.work_dir
    save_state(ctx, state)
    alarms = sum(1 for m in report.messages if m.kind == "<A>")
    return [
        f"Exécution : {report.status} ({report.diag}), {report.duration_s:.1f} s, "
        f"{alarms} alarme(s)",
        f"Compte rendu : {Path(report.work_dir) / 'compte_rendu.md'}",
    ]


def _run_files(ctx: ProjectContext) -> tuple[Path, Path, Path]:
    """(execution directory, its `.mess`, its `.comm`)."""
    state = load_state(ctx)
    run_dir = _require(state.execution_dir, "répertoire d'exécution", "executer")
    comm = _require(state.comm, ".comm", "generer")
    return run_dir, run_dir / "proc.0" / "fort.6", run_dir / comm.name


def step_controles(ctx: ProjectContext, rt: Runtime) -> list[str]:  # noqa: ARG001
    from aster_expert.controles.equilibre import level_d_controls  # noqa: PLC0415

    require_valid_project(ctx)
    run_dir, mess, run_comm = _run_files(ctx)
    state = load_state(ctx)
    mesh = _require(state.mesh_med, "maillage vérifié", "maillage")
    out = ctx.results_dir / "controles"
    level_d_controls(
        ctx, mess_path=mess, comm_path=run_comm, mesh_path=mesh, out_dir=out
    )
    summary = json.loads((out / "controles_d.json").read_text(encoding="utf-8"))
    lines = [
        f"Contrôles D : {summary['verdict']} (équilibre, pesanteur, symétrie) -- "
        f"{out / 'controles_d.md'}"
    ]
    # Lot 47 : l'extension `controls.extra` déclarée par le projet (produits propres
    # au projet) n'était appelée par aucune étape.
    extra = ctx.declaration.controls.extra if ctx.declaration.controls else None
    if extra is not None:
        produced = ctx.extension(extra)(ctx, run_dir, out)
        lines.extend(f"Produit du projet : {path}" for path in produced)
    return lines


def step_synthese(ctx: ProjectContext, rt: Runtime, *, views: bool = True) -> list[str]:  # noqa: ARG001
    d = ctx.declaration
    if d.synthesis is None:
        message = f"le projet {d.name} ne déclare pas de synthèse"
        raise ProjectError(message)
    require_valid_project(ctx, FOR_REPORT)
    run_dir, _, run_comm = _run_files(ctx)
    level_d = (
        ctx.results_dir
        / "controles"
        / (d.controls.output if d.controls else "equilibre.json")
    )
    root = ctx.repo_root
    lines: list[str] = ctx.extension(d.synthesis.extension)(
        ctx,
        result=display_path(run_dir, root),
        out_dir=ctx.results_dir / "synthese",
        data_path=display_path(ctx.data_path, root),
        comm_path=display_path(run_comm, root),
        level_d_path=level_d if level_d.is_file() else None,
        views=views,
    )
    return lines


def step_combinaisons(ctx: ProjectContext, rt: Runtime) -> list[str]:  # noqa: ARG001
    from aster_expert.combinaisons.efforts import (  # noqa: PLC0415
        combined_forces,
        write_combined_forces,
    )

    require_valid_project(ctx)
    section = ctx.declaration.combinations
    if section is None:
        message = f"le projet {ctx.declaration.name} ne déclare pas de combinaisons"
        raise ProjectError(message)
    _, mess, run_comm = _run_files(ctx)
    comm = _require(load_state(ctx).comm, ".comm", "generer")
    result = combined_forces(ctx, mess.resolve())
    out = ctx.results_dir / section.output
    written = write_combined_forces(
        ctx, result, out, comm_path=comm.resolve(), run_comm_path=run_comm.resolve()
    )
    return [
        f"{len(result.combinations)} combinaisons, {len(written)} fichiers dans {out}"
    ]


def step_ferraillage(ctx: ProjectContext, rt: Runtime) -> list[str]:
    from aster_expert.ferraillage.poutre import (  # noqa: PLC0415
        analyze_member,
        prepare_member,
    )

    require_valid_project(ctx)
    rebar = ctx.declaration.rebar
    if rebar is None:
        message = (
            f"le projet {ctx.declaration.name} ne déclare aucun élément à ferrailler"
        )
        raise ProjectError(message)
    blockers = ctx.blockers_for("ferraillage")
    if blockers:
        message = (
            f"ferraillage refusé : la fiche ou les données de {ctx.declaration.name} "
            "bloquent cette étape"
        )
        raise ProjectError(message, blockers)
    _, mess, _ = _run_files(ctx)
    lines = []
    state = load_state(ctx)
    for member in rebar.members:
        out = ctx.results_dir / member.output
        comm = prepare_member(ctx, member, mess, out)
        report = execute(ctx, rt, comm)
        state.rebar_executions[member.group] = report.work_dir
        save_state(ctx, state)
        run_dir = Path(report.work_dir)
        root = ctx.repo_root
        executed_at = report.executed_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        (out / "rapports").mkdir(parents=True, exist_ok=True)
        (out / "rapports" / "executions.json").write_text(
            json.dumps(
                {
                    comm.stem: {
                        "aster_version": report.aster_version,
                        "image_digest": report.image_digest,
                        "comm_path": str(display_path(comm, root)),
                        "comm_sha256": _sha(comm),
                        "diagnostic": report.diag,
                        "duration_s": round(report.duration_s or 0.0, 1),
                        "executed_at": executed_at,
                        "work_dir": str(display_path(run_dir, root)),
                    }
                },
                ensure_ascii=False,
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
        result = analyze_member(ctx, member, run_dir, out)
        check = result.summary["controle_main"]
        lines.append(
            f"{member.label} : {result.summary['sections']} sections × "
            f"{result.n_combinations} combinaisons ; contrôle du module "
            f"{check['comparaisons']} comparaisons, {check['echecs']} échec(s) dans le "
            f"critère -- {out}"
        )
    for plate in rebar.plates:
        # Lot 43 : une plaque se ferraille dans l'exécution du projet lui-même
        # (CALC_FERRAILLAGE écrit par le générateur), rien n'est relancé ici.
        from aster_expert.ferraillage.plaque import analyze_plate  # noqa: PLC0415

        plate_out = ctx.results_dir / plate.output
        plate_result = analyze_plate(ctx, plate, mess, plate_out)
        chk = plate_result["controle_independant"]
        lines.append(
            f"{plate.label} : {len(plate_result['combinaisons'])} combinaisons "
            "ferraillées ; "
            f"contrôle indépendant au nœud {chk['noeud']} : {chk['reussites_moyenne']}/"
            f"{chk['comparaisons']} mailles reproduites -- {plate_out}"
        )
    return lines


def step_livrables(
    ctx: ProjectContext,
    rt: Runtime,
    *,
    only: str | None = None,
    ncpus: int = 1,
    model: str | None = None,
) -> list[str]:
    """Lot 49: the deliverables (`aster_expert.livrables.chaine`); lot 49 ter: those
    of a derived model (`aster_expert.livrables.derives`)."""
    from aster_expert.livrables.chaine import run_deliverables  # noqa: PLC0415

    if model is not None:
        from aster_expert.livrables.derives import run_derived  # noqa: PLC0415

        return run_derived(ctx, rt, model, only=only, ncpus=ncpus)
    return run_deliverables(ctx, rt, only=only, ncpus=ncpus)


def _sha(path: Path) -> str:
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(path.read_bytes()).hexdigest()


STEP_FUNCTIONS: dict[str, Callable[[ProjectContext, Runtime], list[str]]] = {
    "verifier": step_verifier,
    "maillage": step_maillage,
    "generer": step_generer,
    "valider": step_valider,
    "executer": step_executer,
    "controles": step_controles,
    "synthese": step_synthese,
    "combinaisons": step_combinaisons,
    "ferraillage": step_ferraillage,
    "livrables": lambda ctx, rt: step_livrables(ctx, rt),
}


def declared(ctx: ProjectContext, step: str) -> bool:
    """Does the project declare what the step needs (`tout` skips the others)?"""
    d = ctx.declaration
    return {
        "controles": d.controls is not None,
        "synthese": d.synthesis is not None,
        "combinaisons": d.combinations is not None
        and d.combinations.forces is not None,
        "ferraillage": d.rebar is not None,
        "livrables": d.deliverables is not None,
    }.get(step, True)


def run_step(
    ctx: ProjectContext, rt: Runtime, step: str, *, views: bool = True
) -> list[str]:
    if step == "tout":
        lines: list[str] = []
        for name in STEPS:
            lines.append(f"== {name}")
            if not declared(ctx, name):
                lines.append("étape sans objet : le projet ne la déclare pas")
                continue
            lines += run_step(ctx, rt, name, views=views)
        return lines
    if step not in STEP_FUNCTIONS:
        message = (
            f"étape inconnue : {step} (étapes : "
            f"{', '.join((*STEPS, 'livrables', 'tout'))})"
        )
        raise ProjectError(message)
    if step == "synthese":
        return step_synthese(ctx, rt, views=views)
    return STEP_FUNCTIONS[step](ctx, rt)


__all__ = [
    "STEPS",
    "ProjectState",
    "Runtime",
    "display_path",
    "execute",
    "generate",
    "load_state",
    "run_step",
    "save_state",
]
