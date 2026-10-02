"""Coherence of a project declaration with the files it names (lot 41, étape 3).

`check_project` returns every problem it finds, as sentences an engineer can act
on -- a missing value, a group absent from the mesh, a load case without an
expected resultant, a fiche and a data file of two different structures -- and
`require_valid_project` turns a non-empty list into one `ProjectError`. No step
of `aster-expert projet` runs on a refused declaration.
"""

from __future__ import annotations

from collections.abc import Collection

from aster_expert.meshing.errors import MeshError
from aster_expert.meshing.invariants import load_invariants
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import (
    CombinationsSection,
    DataRef,
    Number,
    RebarMember,
)
from aster_expert.projet.errors import ProjectError


def _files(ctx: ProjectContext) -> list[str]:
    d = ctx.declaration
    problems = []
    wanted = [
        ("fiche", ctx.fiche_path, False),
        ("données", ctx.data_path, False),
        ("invariants du maillage", ctx.path(d.mesh.invariants), False),
    ]
    if d.data_sources is not None:
        wanted.append(("sources des données", ctx.path(d.data_sources), True))
    if d.mesh.script is not None:
        wanted.append(("script de maillage", ctx.path(d.mesh.script), False))
    if d.mesh.med is not None:
        wanted.append(("maillage", ctx.path(d.mesh.med), False))
    if d.comm.file is not None:
        wanted.append((".comm", ctx.path(d.comm.file), False))
    for label, path, is_dir in wanted:
        ok = path.is_dir() if is_dir else path.is_file()
        if not ok:
            problems.append(f"fichier introuvable ({label}) : {path}")
    if not (ctx.project_dir / "__init__.py").is_file():
        problems.append(
            f"le projet n'est pas un paquet Python (pas de __init__.py dans "
            f"{ctx.project_dir}) : ses extensions ne peuvent être importées"
        )
    return problems


def _identity(ctx: ProjectContext) -> list[str]:
    d = ctx.declaration
    problems = []
    data = ctx.data()
    if data.project != d.structure and data.project not in d.variants:
        admitted = ", ".join(repr(s) for s in (d.structure, *d.variants))
        problems.append(
            f"les données {ctx.data_path.name} sont celles de l'ouvrage "
            f"{data.project!r}, la déclaration admet {admitted}"
        )
    sheet = ctx.sheet()
    expected = d.fiche_project_name or d.structure
    if sheet.project_name != expected:
        problems.append(
            f"la fiche {ctx.fiche_path.name} est celle du projet "
            f"{sheet.project_name!r}, la déclaration attend {expected!r}"
        )
    return problems


def _required_data(ctx: ProjectContext) -> list[str]:
    items = ctx.data().items()
    problems = []
    for key in ctx.declaration.comm.required_data:
        item = items.get(key)
        if item is None:
            problems.append(
                f"donnée manquante : {key} (exigée par le générateur, "
                f"absente de {ctx.data_path.name})"
            )
        elif item.status != "fourni":
            problems.append(f"donnée à fournir : {key} (exigée par le générateur)")
    return problems


def _numbers(ctx: ProjectContext) -> list[Number]:
    d = ctx.declaration
    out: list[Number] = []
    if d.combinations is not None:
        c: CombinationsSection = d.combinations
        out += [c.gamma_g_unfavourable, c.gamma_q]
        if c.gamma_g_favourable is not None:
            out.append(c.gamma_g_favourable)
        for v in c.variables:
            out += [v.psi0, v.psi1, v.psi2]
        for a in c.accidental:
            out += list(a.coefficients.values())
    if d.rebar is not None:
        for m in d.rebar.members:
            member: RebarMember = m
            out += [
                member.hy,
                member.hz,
                member.cover,
                member.phi_mm,
                member.wk_mm,
                member.fck_mpa,
                member.fyk_mpa,
                member.eys_pa,
            ]
        for plate in d.rebar.plates:
            out += [
                plate.thickness_m,
                plate.cover_mm,
                plate.fck_mpa,
                plate.fyk_mpa,
                plate.fctm_mpa,
                plate.eys_mpa,
                plate.alpha_cc,
                plate.sigma_s_ratio,
                plate.sigma_c_els_mpa,
                plate.sigma_c_els_qp_mpa,
                plate.alpha_e,
                plate.kt,
                plate.wk_mm,
                plate.phi_mm,
            ]
    return out


def _data_refs(ctx: ProjectContext) -> list[str]:
    problems = []
    for n in _numbers(ctx):
        if isinstance(n, DataRef):
            try:
                ctx.number(n)
            except ProjectError as exc:
                problems.append(str(exc))
    return problems


def _mesh_groups(ctx: ProjectContext) -> list[str]:
    d = ctx.declaration
    try:
        invariants = load_invariants(ctx.path(d.mesh.invariants))
    except MeshError as exc:
        return [str(exc)]
    names = {g.name for g in invariants.groups}
    wanted: list[tuple[str, str]] = []
    if d.controls is not None:
        wanted += [
            (s.group, "groupe d'appui") for s in d.controls.supports if s.in_mesh
        ]
    if d.rebar is not None:
        wanted += [(m.group, "élément à ferrailler") for m in d.rebar.members]
        wanted += [(p.group, "plaque à ferrailler") for p in d.rebar.plates]
        wanted += [
            (p.check_node, "nœud de contrôle du ferraillage") for p in d.rebar.plates
        ]
    return [
        f"groupe absent du maillage : {group} ({role}, absent des invariants "
        f"{d.mesh.invariants})"
        for group, role in wanted
        if group not in names
    ]


def _cases(ctx: ProjectContext) -> list[str]:
    d = ctx.declaration
    problems = []
    declared: list[str] = []
    if d.controls is not None:
        declared = [c.name for c in d.controls.cases]
        duplicates = sorted({n for n in declared if declared.count(n) > 1})
        if duplicates:
            problems.append(f"cas de charge déclarés deux fois : {duplicates}")
        problems += [
            f"cas de charge sans résultante attendue : {c.name}"
            for c in d.controls.cases
            if c.expected_resultant is None
        ]
        for plane in d.controls.symmetry_planes:
            problems += [
                f"plan de symétrie {plane.normal} = {plane.position} : cas {n} "
                "non déclaré"
                for n in plane.cases
                if n not in declared
            ]
    comb = d.combinations
    if comb is not None:
        used = set(comb.permanent) | {v.name for v in comb.variables}
        for a in comb.accidental:
            used |= set(a.coefficients)
        if comb.forces is not None:
            missing = sorted(used - set(comb.forces.cases))
            if missing:
                problems.append(
                    f"combinaisons : cas sans table d'efforts déclarée : {missing}"
                )
            if comb.forces.reference_case not in comb.forces.cases:
                problems.append(
                    f"combinaisons : cas de référence {comb.forces.reference_case} "
                    "absent des cas d'efforts"
                )
        if declared:
            unknown = sorted(used - set(declared))
            if unknown:
                problems.append(
                    f"combinaisons : cas non déclarés dans les contrôles : {unknown}"
                )
    return problems


def _extensions(ctx: ProjectContext) -> list[str]:
    d = ctx.declaration
    refs: list[str] = []
    if d.mesh.parameters:
        refs.append(d.mesh.parameters)
    if d.comm.generator:
        refs.append(d.comm.generator)
    if d.controls is not None:
        if d.controls.springs is not None:
            refs.append(d.controls.springs.forces)
            if d.controls.springs.stiffness_check:
                refs.append(d.controls.springs.stiffness_check)
        refs += [
            c.expected_resultant
            for c in d.controls.cases
            if isinstance(c.expected_resultant, str)
        ]
        if d.controls.extra:
            refs.append(d.controls.extra)
    if d.combinations is not None and d.combinations.report:
        refs.append(d.combinations.report)
    if d.rebar is not None:
        refs += [m.report for m in d.rebar.members if m.report]
    if d.synthesis is not None:
        refs.append(d.synthesis.extension)
    problems = []
    for ref in dict.fromkeys(refs):
        try:
            ctx.extension(ref)
        except ProjectError as exc:
            problems.append(str(exc))
    return problems


CHECKS = {
    "identite": _identity,
    "donnees_generateur": _required_data,
    "donnees_declarees": _data_refs,
    "groupes": _mesh_groups,
    "cas": _cases,
    "extensions": _extensions,
}
"""The checks after the files, by name, in their order."""

FOR_GENERATION = ("identite", "donnees_generateur", "groupes", "cas", "extensions")
FOR_REPORT = ("identite", "extensions")


def check_project(
    ctx: ProjectContext, parts: Collection[str] = tuple(CHECKS)
) -> list[str]:
    """Every problem of the declaration, in a stable order. Files first: the
    other checks read them. `parts` restricts the checks to what a command
    needs (a synthesis does not need the data of the reinforcement)."""
    problems = _files(ctx)
    if problems:
        return problems
    for name, check in CHECKS.items():
        if name not in parts:
            continue
        try:
            problems += check(ctx)
        except ProjectError as exc:
            problems.append(str(exc))
    return problems


def require_valid_project(
    ctx: ProjectContext, parts: Collection[str] = tuple(CHECKS)
) -> None:
    problems = check_project(ctx, parts)
    if problems:
        message = f"projet {ctx.declaration.name} : déclaration refusée"
        raise ProjectError(message, tuple(problems))


__all__ = [
    "CHECKS",
    "FOR_GENERATION",
    "FOR_REPORT",
    "check_project",
    "require_valid_project",
]
