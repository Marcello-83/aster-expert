"""Models derived from the reference (lot 49 ter): auxiliary models of E27 and declared
variants, `aster-expert projet <nom> livrables --modele <nom>`.

**Method.** A derived model is the production `.comm` kept word for word, plus:

1. before `AFFE_MODELE`, one `DEFI_GROUP(reuse=...)` on the mesh of the model: one
   cell group per rigid part (`CREA_GROUP_MA`, `INTERSEC` of the declared cell group
   and of each member group) and the node groups of the reactions (`CREA_GROUP_NO`,
   `GROUP_MA`, `NOM`) -- keywords of the catalogue 17.4 (`DEFI_GROUP`);
2. before the first solve, one `AFFE_CHAR_MECA(MODELE=..., DDL_IMPO=...,
   LIAISON_SOLIDE=...)`: U4.44.01, « Mot-clé DDL_IMPO » (degrees of freedom set to
   zero on `GROUP_NO` or `GROUP_MA`) and « Mot-clé LIAISON_SOLIDE » (« modéliser une
   partie indéformable d'une structure » ; an element whose nodes are all in the
   rigid part has no strain and no generalised force);
3. that load added to every solve: `CHAR_MECA_GLOBAL=(<loads>, DRV_<nom>)` of
   `MACRO_ELAS_MULT` (catalogue 17.4: `CHAR_MECA_GLOBAL`, several loads admitted),
   `EXCIT=(_F(CHARGE=...), _F(CHARGE=DRV_<nom>))` of `MECA_STATIQUE`. A solve of any
   other form is refused, never guessed.

The post-processing outputs of lot 49 (`aster_expert.livrables.postcomm`) are then
inserted as for the reference, restricted to the declared fields, the reactions
written on the support groups and on the new blocked and rigid node groups. The
derived run is not a copy of production: its tables are not compared; it is checked
by the harness D of this module (`controle`): Σ loads + Σ reactions + Σ spring forces
= 0 for every elementary case, and for every moving position the vertical reaction
equal to that of the reference (same load).

Nothing here knows a structure: groups, degrees of freedom, members and excluded
cases come from `engineering_summary.derived_models` of `projet.yaml`.
"""

from __future__ import annotations

import fnmatch
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.livrables.chaine import (
    DeliverablesState,
    _export_text,
    deliverables_dir,
    extract,
    load_deliverables_state,
    production,
    save_deliverables_state,
    sha256,
)
from aster_expert.livrables.inventaire import build_inventory
from aster_expert.livrables.postcomm import build_post_comm, field_keys
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import (
    DeliverableField,
    DeliverablesSection,
    DerivedModel,
    EngineeringSummarySection,
)
from aster_expert.projet.errors import ProjectError

DERIVED_DIR = "livrables_derives"
DECLARATION_FILE = "declaration_derivee.json"
CHECK_FILE = "controle_derive.json"
_MODEL = re.compile(r"^(\w+)\s*=\s*AFFE_MODELE\(", re.MULTILINE)
_SOLVE = re.compile(r"^\w+\s*=\s*(MACRO_ELAS_MULT|MECA_STATIQUE)\(", re.MULTILINE)
_GLOBAL = re.compile(r"CHAR_MECA_GLOBAL=(\w+|\([^)]*\))")
_EXCIT = re.compile(r"EXCIT=_F\(CHARGE=(\w+)\)")
SUBSTEPS = ("preparer", "executer", "verifier", "traiter", "controler")


def derived_root(ctx: ProjectContext, name: str) -> Path:
    return ctx.results_dir / DERIVED_DIR / name


def _summary(ctx: ProjectContext) -> EngineeringSummarySection:
    summary = ctx.declaration.engineering_summary
    if summary is None:
        message = f"{ctx.declaration.name} : pas de section `engineering_summary`"
        raise ProjectError(message)
    return summary


def derived_model(ctx: ProjectContext, name: str) -> DerivedModel:
    for model in _summary(ctx).derived_models:
        if model.name == name:
            return model
    known = ", ".join(m.name for m in _summary(ctx).derived_models) or "aucun"
    message = f"modèle dérivé {name} non déclaré (déclarés : {known})"
    raise ProjectError(message)


@dataclass(frozen=True)
class Transformed:
    text: str
    load: str
    rigid_groups: tuple[str, ...]
    reaction_groups: tuple[str, ...]
    solves: int


def _call_block(call: str, entries: list[str]) -> list[str]:
    if not entries:
        return []
    return [f"    {call}=(", *[f"        {e}," for e in entries], "    ),"]


def transform_comm(
    text: str, model: DerivedModel, member_groups: list[str]
) -> Transformed:
    """The production `.comm` with the derived load added (see module docstring)."""
    found = list(_MODEL.finditer(text))
    if len(found) != 1:
        message = f"modèle dérivé {model.name} : {len(found)} AFFE_MODELE (1 attendu)"
        raise ProjectError(message)
    model_name = found[0].group(1)
    tail = text[found[0].end() :]
    mesh_match = re.search(r"MAILLAGE=(\w+)", tail[: tail.find("\n)") + 2])
    if mesh_match is None:
        message = f"modèle dérivé {model.name} : maillage de AFFE_MODELE introuvable"
        raise ProjectError(message)
    mesh = mesh_match.group(1)
    load = f"DRV_{model.name}"
    groups_ma: list[str] = []
    groups_no: list[str] = []
    rigid: list[str] = []
    reactions: list[str] = []
    k = 0
    for part in model.rigid:
        members = [g for g in member_groups if fnmatch.fnmatchcase(g, part.per_member)]
        if not members:
            message = (
                f"modèle dérivé {model.name} : aucun groupe {part.per_member} "
                "dans le maillage"
            )
            raise ProjectError(message)
        for member in members:
            k += 1
            group = f"DRV_R{k:02d}"
            groups_ma.append(
                f'_F(NOM="{group}", INTERSEC=("{part.cell_group}", "{member}"))'
            )
            groups_no.append(f'_F(GROUP_MA="{group}", NOM="{group}")')
            rigid.append(group)
    blocks: list[str] = []
    for i, block in enumerate(model.blocks, start=1):
        dofs = ", ".join(f"{d}=0.0" for d in block.dofs)
        if block.node_group is not None:
            blocks.append(f'_F(GROUP_NO=("{block.node_group}",), {dofs})')
            reactions.append(block.node_group)
        else:
            group = f"DRV_B{i:02d}"
            groups_no.append(f'_F(GROUP_MA="{block.cell_group}", NOM="{group}")')
            blocks.append(f'_F(GROUP_MA=("{block.cell_group}",), {dofs})')
            reactions.append(group)
    header = [
        f"# Modèle dérivé {model.name} ({model.kind}, lot 49 ter) : {model.label}.",
        f"# {model.source}.",
        "# Généré par aster_expert.livrables.derives à partir du .comm de production,",
        "# reproduit sans autre changement que les blocs DRV ci-dessous",
        "# (U4.44.01 : DDL_IMPO, LIAISON_SOLIDE ; catalogue 17.4 : DEFI_GROUP,",
        "# CHAR_MECA_GLOBAL). Ce n'est pas le modèle de référence.",
        "",
    ]
    lines_groups: list[str] = []
    if groups_ma or groups_no:
        lines_groups = [
            f"# Modèle dérivé {model.name} : groupes des parties rigides et des "
            "réactions.",
            f"{mesh} = DEFI_GROUP(",
            f"    reuse={mesh},",
            f"    MAILLAGE={mesh},",
            *_call_block("CREA_GROUP_MA", groups_ma),
            *_call_block("CREA_GROUP_NO", groups_no),
            ")",
            "",
        ]
    lines_load = [
        f"# Modèle dérivé {model.name} : {model.purpose}",
        f"{load} = AFFE_CHAR_MECA(",
        f"    MODELE={model_name},",
        *_call_block("DDL_IMPO", blocks),
        *_call_block("LIAISON_SOLIDE", [f'_F(GROUP_MA="{g}")' for g in rigid]),
        ")",
        "",
    ]
    solves = list(_SOLVE.finditer(text))
    if not solves:
        message = f"modèle dérivé {model.name} : aucune résolution dans le .comm"
        raise ProjectError(message)
    first_solve = solves[0].start()
    model_at = found[0].start()
    if model_at > first_solve:
        message = (
            f"modèle dérivé {model.name} : AFFE_MODELE après la première résolution"
        )
        raise ProjectError(message)
    out = (
        "\n".join(header)
        + text[:model_at]
        + ("\n".join(lines_groups) if lines_groups else "")
        + text[model_at:first_solve]
        + "\n".join(lines_load)
        + text[first_solve:]
    )
    replaced = 0

    def _global(m: re.Match[str]) -> str:
        nonlocal replaced
        replaced += 1
        loads = m.group(1).strip("()").rstrip(",").strip()
        return f"CHAR_MECA_GLOBAL=({loads}, {load})"

    def _excit(m: re.Match[str]) -> str:
        nonlocal replaced
        replaced += 1
        return f"EXCIT=(_F(CHARGE={m.group(1)}), _F(CHARGE={load}))"

    out = _GLOBAL.sub(_global, out)
    out = _EXCIT.sub(_excit, out)
    if replaced != len(solves):
        message = (
            f"modèle dérivé {model.name} : {len(solves)} résolution(s), {replaced} "
            "chargement(s) global(aux) complété(s) ; forme non reconnue (refus)"
        )
        raise ProjectError(message)
    return Transformed(out, load, tuple(rigid), tuple(reactions), len(solves))


def derived_section(
    section: DeliverablesSection, model: DerivedModel, transformed: Transformed
) -> DeliverablesSection:
    """The deliverables of the reference restricted to the declared fields, the
    reactions written on the new groups too; no combination nor envelope written."""
    keys = field_keys(section.fields)
    unknown = sorted(set(model.fields) - set(keys))
    if unknown:
        message = f"modèle dérivé {model.name} : champs {unknown} non livrés ({keys})"
        raise ProjectError(message)
    fields = []
    for key, f in zip(keys, section.fields, strict=True):
        if key not in model.fields:
            continue
        if f.field == "REAC_NODA":
            extra = (*transformed.reaction_groups, *transformed.rigid_groups)
            f = f.model_copy(
                update={"node_groups": tuple(dict.fromkeys((*f.node_groups, *extra)))}
            )
        fields.append(f)
    return section.model_copy(update={"fields": tuple(fields), "envelopes": False})


def _member_groups(ctx: ProjectContext) -> list[str]:
    from aster_expert.livrables.donnees import Deliverables  # noqa: PLC0415

    mesh = Deliverables(deliverables_dir(ctx)).mesh
    out = []
    for key in mesh.arrays:
        if key.startswith("gma_"):
            out.append(key.split("_", 2)[2])
    return out


def step_preparer(
    ctx: ProjectContext, rt: Any, name: str, *, ncpus: int = 1
) -> list[str]:
    from aster_expert.validation.errors import ValidationRunError  # noqa: PLC0415
    from aster_expert.validation.validate import validate_comm_file  # noqa: PLC0415

    model = derived_model(ctx, name)
    section = ctx.declaration.deliverables
    if section is None:
        message = "livrables : section `deliverables` absente"
        raise ProjectError(message)
    prod = production(ctx)
    transformed = transform_comm(prod.text, model, _member_groups(ctx))
    sub = derived_section(section, model, transformed)
    analysis = parse_comm_source(transformed.text, file_path=f"{model.name}.comm")
    inventory = build_inventory(
        analysis,
        static_results=sub.static_results,
        ignored=[i.result for i in sub.ignored_results],
    )
    names = [c.name for _s, c in inventory.cases()]
    mobile = [
        n for n in names if any(fnmatch.fnmatchcase(n, p) for p in sub.moving_cases)
    ]
    known = {g for s in analysis.statements for g in (*s.mesh_groups, *s.node_groups)}
    known |= set(transformed.rigid_groups) | set(transformed.reaction_groups)
    text, plan = build_post_comm(
        transformed.text, inventory, sub, mobile_cases=mobile, known_groups=known
    )
    root = derived_root(ctx, name)
    out = root / "post"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    stem = f"{prod.comm.stem}_{name.lower()}"
    comm = out / f"{stem}.comm"
    comm.write_text(text, encoding="utf-8")
    (out / f"{stem}_modele.comm").write_text(transformed.text, encoding="utf-8")
    mesh_name = f"{stem}{prod.mesh.suffix}"
    shutil.copyfile(prod.mesh, out / mesh_name)
    (out / f"{stem}.export").write_text(
        _export_text(prod, stem, mesh_name, ncpus), encoding="utf-8"
    )
    plan_dict = plan.as_dict()
    plan_dict["cas_mobiles"] = mobile
    (out / "plan.json").write_text(
        json.dumps(plan_dict, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root / DECLARATION_FILE).write_text(
        json.dumps(
            {
                "modele": model.model_dump(mode="json"),
                "livrables": sub.model_dump(mode="json"),
                "chargement": transformed.load,
                "groupes_rigides": list(transformed.rigid_groups),
                "groupes_reactions": list(transformed.reaction_groups),
                "resolutions": transformed.solves,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
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
        message = f"modèle dérivé {name}, validation : {exc}"
        raise ProjectError(message) from exc
    (out / "validation.json").write_text(
        report.model_dump_json(indent=1) + "\n", encoding="utf-8"
    )
    n_checked = len(report.commands_checked)
    state = DeliverablesState(
        production_run=str(prod.run_dir),
        production_comm_sha256=sha256(prod.comm),
        post_comm=str(comm),
        post_comm_sha256=sha256(comm),
        validation={
            "validation_level": report.validation_level,
            "verdict": report.verdict,
            "valid": report.valid,
            "commands_checked": n_checked,
            "commands_total": n_checked + len(report.commands_not_checked),
            "errors": len(report.errors),
        },
    )
    save_deliverables_state(ctx, state, root)
    line = (
        f"Modèle dérivé {name} : {comm.name}, niveau B {report.verdict} "
        f"({n_checked}/{n_checked + len(report.commands_not_checked)} commandes, "
        f"{len(report.errors)} erreur(s)) ; {transformed.solves} résolution(s) "
        f"complétée(s) par {transformed.load} ; {len(transformed.rigid_groups)} "
        f"partie(s) rigide(s) ; réactions sur "
        f"{', '.join(transformed.reaction_groups) or '—'}"
    )
    if report.verdict != "valide":
        message = f"livrables : {line}"
        raise ProjectError(message)
    return [line]


def step_verifier(ctx: ProjectContext, name: str) -> list[str]:
    """A derived run is not a copy of production: no table comparison; its run must
    have ended at `FIN` (checked by `execute`), recorded here for `traiter`."""
    root = derived_root(ctx, name)
    state = load_deliverables_state(ctx, root)
    if not state.post_run:
        message = f"modèle dérivé {name} : étape executer d'abord"
        raise ProjectError(message)
    state.tables = {
        "identiques": None,
        "motif": "modèle dérivé : les tables diffèrent de la production par "
        "construction ; contrôle par le harnais D (sous-étape controler)",
    }
    save_deliverables_state(ctx, state, root)
    return [f"Modèle dérivé {name} : exécution terminée ({state.post_run})"]


def step_traiter(ctx: ProjectContext, name: str) -> list[str]:
    root = derived_root(ctx, name)
    state = load_deliverables_state(ctx, root)
    if not state.post_run or state.tables is None:
        message = f"modèle dérivé {name} : étape verifier d'abord"
        raise ProjectError(message)
    plan = json.loads((root / "post" / "plan.json").read_text(encoding="utf-8"))
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
    spec = {
        "cases_med": "cas.med",
        "work_med": "travail.med",
        "loads_med": "charges.med",
        "fields": [
            {
                "key": key,
                "work": {
                    r["jeton"]: r["champs"][i]["nom_med"] for r in plan["resultats"]
                },
            }
            for i, key in enumerate(keys)
        ],
        "cases": cases,
        "combinations": [],
        "envelopes": False,
    }
    return extract(ctx, root, state, spec)


def open_derived(
    ctx: ProjectContext, name: str
) -> tuple[Any, list[Any], dict[str, Any]]:
    """(Deliverables, field infos, recorded declaration) of a derived model."""
    from aster_expert.livrables.donnees import Deliverables  # noqa: PLC0415

    root = derived_root(ctx, name)
    recorded = json.loads((root / DECLARATION_FILE).read_text(encoding="utf-8"))
    fields = [
        DeliverableField.model_validate(f) for f in recorded["livrables"]["fields"]
    ]
    d = Deliverables(root, keep_fields=True)
    # Mêmes cas que la référence : ses combinaisons valent pour le modèle dérivé (la
    # sous-étape traiter n'en écrit aucune).
    d.__dict__["combinations"] = Deliverables(deliverables_dir(ctx)).combinations
    return d, d.field_infos(fields), recorded


def _support_sums(d: Any, infos: list[Any], key: str) -> np.ndarray[Any, Any]:
    """Σ reactions (each node once) + Σ spring forces on the structure."""
    total = np.zeros(3)
    for info in infos:
        if info.family == "reactions":
            fa = d.field(info)
            values = fa.arrays[key]
            nodes = fa.entity
            _, first = np.unique(nodes, return_index=True)
            for k, comp in enumerate(("DX", "DY", "DZ")):
                if comp in info.components:
                    column = values[first, info.components.index(comp)]
                    total[k] += float(np.nansum(column))
        elif info.family == "ressorts":
            values = d.field(info).arrays[key]
            for k, comp in enumerate(("N", "VY", "VZ")):
                if comp in info.components:
                    total[k] -= float(np.nansum(values[:, info.components.index(comp)]))
    return total


def control(ctx: ProjectContext, name: str) -> dict[str, Any]:
    """Harness D of a derived model (see module docstring)."""
    from aster_expert.livrables.calcul import resultant  # noqa: PLC0415
    from aster_expert.livrables.donnees import Deliverables  # noqa: PLC0415
    from aster_expert.livrables.vues import _node_values  # noqa: PLC0415

    d, infos, _recorded = open_derived(ctx, name)
    controls = ctx.declaration.controls
    threshold = controls.threshold if controls else 1.0e-6
    coords = d.mesh.coords
    cases: dict[str, Any] = {}
    worst = 0.0
    for med_name, values, kind, entity, _components in d.loads():
        if not med_name.startswith(("FN_", "FV_")):
            continue
        case = med_name[3:]
        full = _node_values(values, kind, entity, len(coords))
        sums = resultant(coords, full)
        load = np.array([sums["FX"], sums["FY"], sums["FZ"]])
        carried = _support_sums(d, infos, f"cas/{case}")
        if med_name.startswith("FV_"):
            scale = float(np.abs(full[:, :3]).sum()) or 1.0
        else:
            scale = float(np.max(np.abs(load))) or 1.0
        gap = float(np.max(np.abs(load + carried))) / scale
        worst = max(worst, gap)
        cases[case] = {
            "charge_n": dict(zip(("FX", "FY", "FZ"), map(float, load), strict=True)),
            "reactions_et_ressorts_n": dict(
                zip(("FX", "FY", "FZ"), map(float, carried), strict=True)
            ),
            "ecart_relatif": gap,
            "echelle": "somme des modules" if med_name.startswith("FV_") else "charge",
            "verdict": "RÉUSSI" if gap <= threshold else "ÉCHEC",
        }
    reference = Deliverables(deliverables_dir(ctx), keep_fields=False)
    ref_infos = reference.field_infos(ctx.declaration.deliverables.fields)  # type: ignore[union-attr]
    ref_infos = [i for i in ref_infos if i.family in ("reactions", "ressorts")]
    positions = [c for c, i in d.spec["cases"].items() if not i["elementary"]]
    ref_positions = {c for c, i in reference.spec["cases"].items()}
    with np.load(reference.data / f"{ref_infos[0].key}.npz") as npz:
        stored = {k[len("pos/") :] for k in npz.files if k.startswith("pos/")}
    skipped = sorted(p for p in positions if p not in stored or p not in ref_positions)
    positions = [p for p in positions if p not in skipped]
    worst_pos = 0.0
    worst_at = None
    for position in positions:
        mine = _support_sums(d, infos, f"pos/{position}")
        ref = _support_sums(reference, ref_infos, f"pos/{position}")
        scale = float(np.max(np.abs(ref))) or 1.0
        gap = abs(mine[2] - ref[2]) / scale
        if gap >= worst_pos:
            worst_pos, worst_at = gap, position
    failed = sorted(c for c, e in cases.items() if e["verdict"] == "ÉCHEC")
    verdict = "RÉUSSI" if not failed and worst_pos <= threshold and cases else "ÉCHEC"
    report = {
        "controle": "harnais D d'un modèle dérivé (lot 49 ter) : Σ charges + Σ "
        "réactions + Σ forces des ressorts = 0 par cas élémentaire ; réaction "
        "verticale de chaque position mobile égale à celle de la référence",
        "modele": name,
        "seuil": threshold,
        "cas": cases,
        "ecart_relatif_max_cas": worst,
        "positions": len(positions),
        "positions_absentes_de_la_reference": skipped,
        "ecart_relatif_max_positions_FZ": worst_pos,
        "position_pire": worst_at,
        "echecs": failed,
        "verdict": verdict,
    }
    path = derived_root(ctx, name) / CHECK_FILE
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8")
    return report


def step_controler(ctx: ProjectContext, name: str) -> list[str]:
    report = control(ctx, name)
    line = (
        f"Modèle dérivé {name}, harnais D : {report['verdict']} ({len(report['cas'])} "
        f"cas, écart max {report['ecart_relatif_max_cas']:.1e} ; "
        f"{report['positions']} positions, écart FZ max "
        f"{report['ecart_relatif_max_positions_FZ']:.1e})"
    )
    if report["verdict"] != "RÉUSSI":
        message = f"modèle dérivé {name} : {line}"
        raise ProjectError(message)
    return [line]


def run_derived(
    ctx: ProjectContext, rt: Any, name: str, *, only: str | None = None, ncpus: int = 1
) -> list[str]:
    from aster_expert.livrables.chaine import step_executer  # noqa: PLC0415

    functions = {
        "preparer": lambda: step_preparer(ctx, rt, name, ncpus=ncpus),
        "executer": lambda: step_executer(ctx, rt, derived_root(ctx, name)),
        "verifier": lambda: step_verifier(ctx, name),
        "traiter": lambda: step_traiter(ctx, name),
        "controler": lambda: step_controler(ctx, name),
    }
    if only is not None and only not in functions:
        message = (
            f"sous-étape inconnue pour un modèle dérivé : {only} "
            f"({', '.join(SUBSTEPS)})"
        )
        raise ProjectError(message)
    lines: list[str] = []
    for step in (only,) if only else SUBSTEPS:
        lines.append(f"-- modèle dérivé {name} : {step}")
        lines += functions[step]()
    return lines


__all__ = [
    "DERIVED_DIR",
    "SUBSTEPS",
    "Transformed",
    "control",
    "derived_model",
    "derived_root",
    "derived_section",
    "open_derived",
    "run_derived",
    "transform_comm",
]
