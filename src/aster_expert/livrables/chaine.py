"""`aster-expert projet <nom> livrables` (lot 49): the deliverables of a project, from
its archived production run.

Steps, each recorded in `resultats/livrables/etat.json`:

1. `preparer`: the post-processing `.comm` (`aster_expert.livrables.postcomm`) next
   to a copy of the production mesh and `.export`, confronted to the catalogue (level B,
   verdict `valide` required);
2. `executer`: the post-processing run;
3. `verifier`: every table value of the post-processing listing (`E20.12`) equals the
   production one -- the copy reproduces the computation, or nothing is delivered;
4. `traiter`: combinations, envelopes and arrays (`scripts/livrables_med.py` in the
   container), moved to `resultats/livrables/`;
5. the views, checks and workbook (`aster_expert.livrables.vues`, `.charges`,
   `.paraview`, `.classeur`) run on what step 4 wrote.

The production `.comm`, its run and its validation levels are never touched.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aster_expert.livrables.combinaisons import CombinationSet, combinations_of
from aster_expert.livrables.inventaire import Inventory, build_inventory
from aster_expert.livrables.postcomm import PostPlan, build_post_comm
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

STATE_NAME = "etat.json"
_NUMBER = re.compile(r"^-?\d\.\d{12}E[+-]\d{2}$")


class DeliverablesState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    production_run: str | None = None
    production_comm_sha256: str | None = None
    post_comm: str | None = None
    post_comm_sha256: str | None = None
    validation: dict[str, Any] | None = None
    post_run: str | None = None
    tables: dict[str, Any] | None = None
    outputs: dict[str, str] = Field(default_factory=dict)


def deliverables_dir(ctx: ProjectContext) -> Path:
    return ctx.results_dir / "livrables"


def load_deliverables_state(ctx: ProjectContext) -> DeliverablesState:
    path = deliverables_dir(ctx) / STATE_NAME
    if not path.is_file():
        return DeliverablesState()
    return DeliverablesState.model_validate_json(path.read_text(encoding="utf-8"))


def save_deliverables_state(ctx: ProjectContext, state: DeliverablesState) -> None:
    path = deliverables_dir(ctx) / STATE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=1) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Production:
    run_dir: Path
    comm: Path
    export: Path
    mesh: Path
    text: str


def production(ctx: ProjectContext) -> Production:
    """The archived production run of the project and its `.comm`, which must be the
    project's `.comm` byte for byte."""
    from aster_expert.projet.pipeline import load_state  # noqa: PLC0415

    state = load_state(ctx)
    if not state.execution_dir or not state.comm:
        message = "livrables : pas d'exécution de production (étape executer)"
        raise ProjectError(message)
    run_dir = Path(state.execution_dir)
    stem = Path(state.comm).stem
    comm = run_dir / f"{stem}.comm"
    export = run_dir / f"{stem}.export"
    project_comm = Path(state.comm)
    if not comm.is_file() or not export.is_file():
        message = f"livrables : {comm.name} ou {export.name} absent de {run_dir}"
        raise ProjectError(message)
    if project_comm.is_file():
        from aster_expert.projet.paquet import normalize_comm  # noqa: PLC0415

        # Règle de conservation des niveaux (lot 45) : même .comm hors commentaires et
        # en-tête (l'en-tête porte l'empreinte de la fiche).
        same = normalize_comm(comm.read_text(encoding="utf-8")) == normalize_comm(
            project_comm.read_text(encoding="utf-8")
        )
        if not same:
            message = (
                f"livrables : le .comm de l'exécution {run_dir.name} n'est pas celui "
                "du projet hors commentaires (régénérer et exécuter d'abord)"
            )
            raise ProjectError(message)
    meshes = [p for p in run_dir.iterdir() if p.suffix in (".mmed", ".med", ".mail")]
    if len(meshes) != 1:
        message = f"livrables : maillage introuvable ou ambigu dans {run_dir}"
        raise ProjectError(message)
    return Production(
        run_dir=run_dir,
        comm=comm,
        export=export,
        mesh=meshes[0],
        text=comm.read_text(encoding="utf-8"),
    )


@dataclass
class Prepared:
    inventory: Inventory
    combinations: CombinationSet | None
    mobile: list[str]
    plan: PostPlan
    text: str


def prepare_text(ctx: ProjectContext, prod: Production) -> Prepared:
    section = ctx.declaration.deliverables
    if section is None:
        message = "livrables : section `deliverables` absente de projet.yaml"
        raise ProjectError(message)
    analysis = parse_comm_source(prod.text, file_path=str(prod.comm))
    inventory = build_inventory(
        analysis,
        static_results=section.static_results,
        ignored=[i.result for i in section.ignored_results],
    )
    names = [c.name for _s, c in inventory.cases()]
    mobile = [
        n for n in names if any(fnmatch.fnmatchcase(n, p) for p in section.moving_cases)
    ]
    combos = combinations_of(ctx)
    if combos is not None:
        missing = sorted(
            {c for comb in combos.combinations for c in comb.cases()} - set(names)
        )
        if missing:
            message = f"livrables : cas des combinaisons absents du .comm : {missing}"
            raise ProjectError(message)
        not_mobile = sorted(combos.mobile_cases() - set(mobile))
        if not_mobile:
            message = (
                "livrables : positions mobiles des combinaisons non déclarées dans "
                f"moving_cases : {not_mobile[:5]}"
            )
            raise ProjectError(message)
    known = {g for s in analysis.statements for g in (*s.mesh_groups, *s.node_groups)}
    text, plan = build_post_comm(
        prod.text, inventory, section, mobile_cases=mobile, known_groups=known
    )
    return Prepared(inventory, combos, mobile, plan, text)


def _export_text(prod: Production, stem: str, mesh_name: str, ncpus: int) -> str:
    lines = []
    for line in prod.export.read_text(encoding="utf-8").splitlines():
        words = line.split()
        if len(words) >= 3 and words[0] == "F" and words[1] == "comm":
            words[2] = f"{stem}.comm"
            line = " ".join(words)
        elif len(words) >= 3 and words[0] == "F" and words[2] == prod.mesh.name:
            words[2] = mesh_name
            line = " ".join(words)
        elif len(words) >= 3 and words[0] == "P" and words[1] == "ncpus":
            line = f"P ncpus {ncpus}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def step_preparer(ctx: ProjectContext, rt: Any, *, ncpus: int = 1) -> list[str]:
    from aster_expert.validation.errors import ValidationRunError  # noqa: PLC0415
    from aster_expert.validation.validate import validate_comm_file  # noqa: PLC0415

    prod = production(ctx)
    prepared = prepare_text(ctx, prod)
    out = deliverables_dir(ctx) / "post"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{prod.comm.stem}_livrables"
    comm = out / f"{stem}.comm"
    comm.write_text(prepared.text, encoding="utf-8")
    mesh_name = f"{stem}{prod.mesh.suffix}"
    shutil.copyfile(prod.mesh, out / mesh_name)
    (out / f"{stem}.export").write_text(
        _export_text(prod, stem, mesh_name, ncpus), encoding="utf-8"
    )
    plan = prepared.plan.as_dict()
    plan["cas_mobiles"] = prepared.mobile
    (out / "plan.json").write_text(
        json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    try:
        report = validate_comm_file(
            comm,
            project_root=ctx.repo_root,
            workroot=rt.workroot,
            docker_bin=rt.docker_bin(),
            image_repository=rt.image_repository,
            timeout=3600,
        )
    except ValidationRunError as exc:
        message = f"livrables, validation : {exc}"
        raise ProjectError(message) from exc
    n_checked = len(report.commands_checked)
    summary = {
        "validation_level": report.validation_level,
        "verdict": report.verdict,
        "valid": report.valid,
        "commands_checked": n_checked,
        "commands_total": n_checked + len(report.commands_not_checked),
        "errors": len(report.errors),
    }
    (out / "validation.json").write_text(
        report.model_dump_json(indent=1) + "\n", encoding="utf-8"
    )
    state = load_deliverables_state(ctx)
    state.production_run = str(prod.run_dir)
    state.production_comm_sha256 = sha256(prod.comm)
    state.post_comm = str(comm)
    state.post_comm_sha256 = sha256(comm)
    state.validation = summary
    state.post_run = None
    state.tables = None
    save_deliverables_state(ctx, state)
    line = (
        f"Post-traitement : {comm.name}, niveau B {report.verdict} "
        f"({summary['commands_checked']}/{summary['commands_total']} commandes, "
        f"{summary['errors']} erreur(s)) ; {len(prepared.plan.loads)} champ(s) de "
        f"charges, {len(prepared.mobile)} position(s) mobile(s)"
    )
    if report.verdict != "valide":
        message = f"livrables : {line}"
        raise ProjectError(message)
    return [line]


def step_executer(ctx: ProjectContext, rt: Any) -> list[str]:
    from aster_expert.projet.pipeline import execute  # noqa: PLC0415

    state = load_deliverables_state(ctx)
    if not state.post_comm or state.validation is None:
        message = "livrables : étape preparer d'abord"
        raise ProjectError(message)
    comm = Path(state.post_comm)
    if sha256(comm) != state.post_comm_sha256:
        message = (
            "livrables : le .comm de post-traitement a changé depuis sa validation"
        )
        raise ProjectError(message)
    report = execute(ctx, rt, comm)
    state.post_run = report.work_dir
    state.tables = None
    save_deliverables_state(ctx, state)
    return [
        f"Exécution de post-traitement : {report.status} ({report.diag}), "
        f"{report.duration_s:.1f} s ; {report.work_dir}"
    ]


def table_numbers(mess: Path) -> list[float]:
    """Every number printed with 12 decimals (`IMPR_TABLE(FORMAT_R='E20.12')`)."""
    values: list[float] = []
    for line in mess.read_text(encoding="utf-8", errors="replace").splitlines():
        values += [float(w) for w in line.split() if _NUMBER.match(w)]
    return values


def compare_tables(production_mess: Path, post_mess: Path) -> dict[str, Any]:
    a, b = table_numbers(production_mess), table_numbers(post_mess)
    identical = a == b
    out: dict[str, Any] = {
        "valeurs_production": len(a),
        "valeurs_post_traitement": len(b),
        "identiques": identical,
    }
    if not identical and len(a) == len(b):
        diffs = [abs(x - y) for x, y in zip(a, b, strict=True)]
        scale = max((abs(x) for x in a), default=1.0) or 1.0
        out["ecart_absolu_max_rapporte"] = max(diffs) / scale
        out["valeurs_differentes"] = sum(1 for d in diffs if d)
    return out


def _mess(run_dir: Path) -> Path:
    found = sorted(run_dir.rglob("fort.6"))
    if not found:
        message = f"livrables : pas de listing dans {run_dir}"
        raise ProjectError(message)
    return found[0]


def step_verifier(ctx: ProjectContext, rt: Any) -> list[str]:  # noqa: ARG001
    state = load_deliverables_state(ctx)
    if not state.post_run or not state.production_run:
        message = "livrables : étape executer d'abord"
        raise ProjectError(message)
    result = compare_tables(
        _mess(Path(state.production_run)), _mess(Path(state.post_run))
    )
    state.tables = result
    save_deliverables_state(ctx, state)
    line = (
        f"Tables E20.12 : {result['valeurs_production']} valeurs en production, "
        f"{result['valeurs_post_traitement']} en post-traitement, identiques : "
        f"{'oui' if result['identiques'] else 'NON'}"
    )
    if not result["identiques"]:
        message = f"livrables : le post-traitement ne reproduit pas le calcul ({line})"
        raise ProjectError(message)
    return [line]


def _spec(ctx: ProjectContext, plan: dict[str, Any]) -> dict[str, Any]:
    combos = combinations_of(ctx)
    section = ctx.declaration.deliverables
    assert section is not None
    mobile = set(plan["cas_mobiles"])
    cases: dict[str, dict[str, Any]] = {}
    for result in plan["resultats"]:
        for case in result["cas"]:
            cases[case["nom"]] = {
                "token": result["jeton"],
                "order": case["nume_ordre"],
                "elementary": case["nom"] not in mobile,
            }
    keys = [f["cle"] for f in plan["resultats"][0]["champs"]]
    fields = []
    for index, key in enumerate(keys):
        fields.append(
            {
                "key": key,
                "work": {
                    r["jeton"]: r["champs"][index]["nom_med"] for r in plan["resultats"]
                },
            }
        )
    return {
        "cases_med": "cas.med",
        "work_med": "travail.med",
        "loads_med": "charges.med",
        "fields": fields,
        "cases": cases,
        "combinations": [
            c.model_dump(mode="json") for c in (combos.combinations if combos else ())
        ],
        "envelopes": bool(section.envelopes and combos),
    }


def step_traiter(ctx: ProjectContext, rt: Any) -> list[str]:  # noqa: ARG001
    from aster_expert.livrables.conteneur import (  # noqa: PLC0415
        ContainerError,
        run_deliverables_container,
    )

    state = load_deliverables_state(ctx)
    if not state.tables or not state.tables.get("identiques") or not state.post_run:
        message = "livrables : étape verifier d'abord (tables identiques exigées)"
        raise ProjectError(message)
    out = deliverables_dir(ctx)
    plan = json.loads((out / "post" / "plan.json").read_text(encoding="utf-8"))
    proc = Path(state.post_run) / "proc.0"
    files = {
        "cas.med": proc / f"fort.{plan['unite_med_cas']}",
        "travail.med": proc / f"fort.{plan['unite_med_travail']}",
        "charges.med": proc / f"fort.{plan['unite_med_charges']}",
    }
    absent = [str(p) for p in files.values() if not p.is_file()]
    if absent:
        message = f"livrables : MED absents de l'exécution : {absent}"
        raise ProjectError(message)
    spec = _spec(ctx, plan)
    try:
        work = run_deliverables_container(
            files,
            spec,
            project_root=ctx.repo_root,
            work_root=ctx.repo_root / "data" / "processed" / "livrables",
        )
    except (ContainerError, OSError) as exc:
        raise ProjectError(str(exc)) from exc
    target = out / "med"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("resultats.med", "charges.med"):
        shutil.move(str(work / name), str(target / name))
    data = out / "donnees"
    if data.exists():
        shutil.rmtree(data)
    shutil.move(str(work / "donnees"), str(data))
    shutil.copyfile(work / "out.json", out / "conteneur.json")
    (out / "spec.json").write_text(
        json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    state.outputs = {
        "resultats_med": str(target / "resultats.med"),
        "charges_med": str(target / "charges.med"),
        "donnees": str(data),
        "conteneur": str(work),
    }
    save_deliverables_state(ctx, state)
    sizes = {n: (target / n).stat().st_size for n in ("resultats.med", "charges.med")}
    written = json.loads((out / "conteneur.json").read_text(encoding="utf-8"))["ecrits"]
    return [
        f"MED des résultats : {sizes['resultats.med'] / 1e6:.1f} Mo ; MED des "
        f"charges : {sizes['charges.med'] / 1e6:.1f} Mo ; {len(written)} champs de "
        "combinaisons et d'enveloppes ajoutés"
    ]


SUBSTEPS = (
    "preparer",
    "executer",
    "verifier",
    "traiter",
    "vues",
    "ingenieur",
    "images",
    "classeur",
)


def run_deliverables(
    ctx: ProjectContext, rt: Any, *, only: str | None = None, ncpus: int = 1
) -> list[str]:
    """Every sub-step in order, or the one named by `only`. `classeur` reads the
    results package: it runs after `aster-expert projet exporter-resultats`, so the
    full sequence stops before it (`classeur` is asked for by name)."""
    from aster_expert.livrables.classeur import write_workbook  # noqa: PLC0415
    from aster_expert.livrables.ingenieur import step_ingenieur  # noqa: PLC0415
    from aster_expert.livrables.paraview import step_images  # noqa: PLC0415
    from aster_expert.livrables.vues import step_vues  # noqa: PLC0415

    functions = {
        "preparer": lambda: step_preparer(ctx, rt, ncpus=ncpus),
        "executer": lambda: step_executer(ctx, rt),
        "verifier": lambda: step_verifier(ctx, rt),
        "traiter": lambda: step_traiter(ctx, rt),
        "vues": lambda: step_vues(ctx, rt),
        "ingenieur": lambda: step_ingenieur(ctx, rt),
        "images": lambda: step_images(ctx),
        "classeur": lambda: [write_workbook(ctx)],
    }
    if only is not None and only not in functions:
        message = f"sous-étape inconnue : {only} ({', '.join(SUBSTEPS)})"
        raise ProjectError(message)
    lines: list[str] = []
    for name in (only,) if only else SUBSTEPS[:-1]:
        lines.append(f"-- livrables : {name}")
        lines += functions[name]()
    return lines


__all__ = [
    "SUBSTEPS",
    "DeliverablesState",
    "compare_tables",
    "deliverables_dir",
    "load_deliverables_state",
    "prepare_text",
    "production",
    "run_deliverables",
    "step_executer",
    "step_preparer",
    "step_traiter",
    "step_verifier",
    "table_numbers",
]
