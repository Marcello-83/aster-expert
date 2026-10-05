"""Level D controls of an executed project: equilibrium, symmetry, gravity
(lot 41, étape 2.4).

Reads only the project declaration (`controls` section) and the results (the
`.mess` tables the project's `.comm` prints); what only the project knows -- the
expected resultant of a load case, the forces of its springs -- comes from the
extensions the declaration names. Same arithmetic, in the same order, as the
lot 34 analysis of the first project, which it replaces: its output file is
identical, byte for byte, for the same inputs.

For each case and each component c:

    applied_c + Σ reactions_c (blocked components only) + Σ springs_c = 0

- reactions: the declared reaction table of each support group; only the
  components actually blocked enter the sum (lot 34: under `LIAISON_SOLIDE` the
  free components of a tied node carry non-zero link forces, which cancel over
  the model), the others are reported apart;
- springs: minus Σ k·u along the springs' direction (the spring pushes back);
- applied: the expected resultant, as evaluated by Code_Aster's own rule when
  the project gives it, and as specified.

The gap is referred to the largest component of the applied load; a case passes
when every gap is within the declared threshold. Informative cases are reported
without verdict. Symmetry: every node of the case's table is paired with its
mirror image through each declared plane; the worst gap is referred to the
largest displacement of the case.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from aster_expert.controles.harnais import (
    GENERIC_CONTROLS,
    VERDICTS_THAT_COUNT,
    run_harness,
)
from aster_expert.controles.tables import Record, TableIndex
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import (
    ControlsSection,
    LoadCase,
    Resultant,
    SymmetryPlane,
)
from aster_expert.projet.errors import ProjectError

COMPONENTS = ("DX", "DY", "DZ")
_COORD = {"X": "COOR_X", "Y": "COOR_Y", "Z": "COOR_Z"}
_DISPLACEMENT = {"X": "DX", "Y": "DY", "Z": "DZ"}


def group_reactions(
    tables: TableIndex, controls: ControlsSection, case: str
) -> dict[str, dict[str, float]]:
    """Resultant reaction of each support group (and of all nodes, when
    declared), read from its table."""
    wanted = [(s.group, s.table) for s in controls.supports]
    if controls.total_reactions is not None:
        wanted.append((controls.total_reactions.label, controls.total_reactions.table))
    out: dict[str, dict[str, float]] = {}
    for group, table in wanted:
        title = table.format(case=case)
        try:
            records = tables.find(title)
        except KeyError as exc:
            message = f"table de réactions {title} absente du listing ({group})"
            raise ProjectError(message) from exc
        if len(records) != 1:
            message = f"table {title} : {len(records)} lignes, une seule attendue"
            raise ProjectError(message)
        out[group] = {c: float(records[0][c]) for c in COMPONENTS}
    return out


def balance_terms(
    controls: ControlsSection,
    applied_eval: dict[str, float],
    applied_spec: dict[str, float],
    reactions: dict[str, dict[str, float]],
    springs: dict[str, float],
) -> dict[str, dict[str, float]]:
    blocked = {s.group: s.blocked for s in controls.supports}
    direction = controls.springs.direction if controls.springs else None
    spring_on_structure = {
        c: (-sum(springs.values()) if c == direction else 0.0) for c in COMPONENTS
    }
    blocked_sum = {
        c: sum(reactions[g][c] for g, comps in blocked.items() if c in comps)
        for c in COMPONENTS
    }
    scale = max(abs(applied_eval[k]) for k in COMPONENTS)
    terms: dict[str, dict[str, float]] = {}
    for c in COMPONENTS:
        balance = applied_eval[c] + blocked_sum[c] + spring_on_structure[c]
        balance_spec = applied_spec[c] + blocked_sum[c] + spring_on_structure[c]
        free_sum = sum(
            reactions[g][c] for g, comps in blocked.items() if c not in comps
        )
        terms[c] = {
            "applied_as_evaluated_n": applied_eval[c],
            "applied_specified_n": applied_spec[c],
            "reactions_blocked_n": blocked_sum[c],
            "springs_on_structure_n": spring_on_structure[c],
            "balance_n": balance,
            "relative_gap": balance / scale if scale else math.nan,
            "relative_gap_vs_specified": balance_spec / scale if scale else math.nan,
            "reactions_free_components_n": free_sum,
            "reactions_free_components_relative": free_sum / scale
            if scale
            else math.nan,
        }
    return terms


def symmetry_check(
    tables: TableIndex, plane: SymmetryPlane, case: str
) -> dict[str, Any]:
    """Pair each node of the table with its mirror image through the plane and
    compare the displacements: normal component opposite, the two others equal."""
    records: list[Record] = tables.find(plane.table.format(case=case))
    tolerance = plane.coordinate_tolerance
    normal_coord = _COORD[plane.normal]
    normal_disp = _DISPLACEMENT[plane.normal]
    in_plane = [d for d in COMPONENTS if d != normal_disp]

    def key(r: Record, *, mirror: bool) -> tuple[int, int, int]:
        coords = []
        for axis in ("X", "Y", "Z"):
            value = float(r[_COORD[axis]])
            if mirror and _COORD[axis] == normal_coord:
                value = (
                    -value if plane.position == 0.0 else 2.0 * plane.position - value
                )
            coords.append(round(value / tolerance))
        return (coords[0], coords[1], coords[2])

    by_key = {key(r, mirror=False): r for r in records}
    max_abs_depl = max(
        (abs(float(r[c])) for r in records for c in COMPONENTS), default=0.0
    )
    worst = 0.0
    worst_detail: dict[str, Any] | None = None
    unmatched = 0
    checked = 0
    for r in records:
        m = by_key.get(key(r, mirror=True))
        if m is None:
            unmatched += 1
            continue
        checked += 1
        gaps = {d: abs(float(r[d]) - float(m[d])) for d in in_plane}
        gaps[normal_disp] = abs(float(r[normal_disp]) + float(m[normal_disp]))
        gap = max(gaps.values())
        if gap > worst:
            worst = gap
            worst_detail = {
                "point": (r["COOR_X"], r["COOR_Y"], r["COOR_Z"]),
                **{f"{d.lower()}_gap": gaps[d] for d in (*in_plane, normal_disp)},
            }
    return {
        "n_nodes": len(records),
        "n_pairs_checked": checked // 2,
        "n_unmatched": unmatched,
        "max_abs_depl_m": max_abs_depl,
        "worst_gap_m": worst,
        "worst_relative_gap": (worst / max_abs_depl) if max_abs_depl else math.nan,
        "worst_detail": worst_detail,
    }


def expected_resultant(
    ctx: ProjectContext, case: LoadCase, **inputs: Path
) -> tuple[dict[str, float], dict[str, float]]:
    """(as evaluated, as specified) applied load of a case."""
    expected = case.expected_resultant
    if expected is None:
        message = f"cas de charge {case.name} sans résultante attendue"
        raise ProjectError(message)
    if isinstance(expected, Resultant):
        values = {c: float(getattr(expected, c)) for c in COMPONENTS}
        return values, values
    result = ctx.extension(expected)(ctx, case.name, **inputs)
    try:
        as_evaluated = {c: float(result["as_evaluated"][c]) for c in COMPONENTS}
        specified = {c: float(result["specified"][c]) for c in COMPONENTS}
    except (KeyError, TypeError) as exc:
        message = (
            f"cas {case.name} : l'extension {expected} doit rendre "
            "{'as_evaluated': {DX, DY, DZ}, 'specified': {DX, DY, DZ}}"
        )
        raise ProjectError(message) from exc
    return as_evaluated, specified


def level_d_controls(
    ctx: ProjectContext,
    *,
    mess_path: Path,
    comm_path: Path,
    mesh_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    """Run the declared controls on an execution; write the equilibrium file
    (`controls.output`) and the trunk's summary (`controles_d.json`,
    `controles_d.md`). Returns the equilibrium result."""
    controls = ctx.declaration.controls
    if controls is None:
        message = f"le projet {ctx.declaration.name} ne déclare aucun contrôle D"
        raise ProjectError(message)
    out_dir.mkdir(parents=True, exist_ok=True)
    mess_text = mess_path.read_text(encoding="utf-8", errors="replace")
    comm_text = comm_path.read_text(encoding="utf-8")
    tables = TableIndex(mess_text)
    inputs = {"comm_path": comm_path, "mesh_path": mesh_path, "out_dir": out_dir}

    result: dict[str, Any] = {
        "threshold": controls.threshold,
        "cases": {},
        "informative_cases": {},
        "symmetry": {},
    }
    springs_ext = controls.springs
    if springs_ext is not None and springs_ext.stiffness_check is not None:
        result["spring_stiffness"] = ctx.extension(springs_ext.stiffness_check)(
            ctx, comm_text
        )
    spring_key = (
        f"springs_k_{springs_ext.direction.lower()}_by_band_n"
        if springs_ext is not None
        else None
    )

    for case in controls.cases:
        applied_eval, applied_spec = expected_resultant(ctx, case, **inputs)
        reactions = group_reactions(tables, controls, case.name)
        springs: dict[str, float] = (
            ctx.extension(springs_ext.forces)(
                ctx, mess_text, case.name, comm_text=comm_text
            )
            if springs_ext is not None
            else {}
        )
        terms = balance_terms(controls, applied_eval, applied_spec, reactions, springs)
        if case.informative:
            result["informative_cases"][case.name] = {"components": terms}
            continue
        entry: dict[str, Any] = {
            "components": terms,
            "reactions_by_group_n": reactions,
            "verdict": "RÉUSSI"
            if all(abs(t["relative_gap"]) <= controls.threshold for t in terms.values())
            else "ÉCHEC",
        }
        if spring_key is not None:
            entry[spring_key] = springs
        if controls.total_reactions is not None:
            entry["reaction_sum_all_nodes_n"] = reactions[
                controls.total_reactions.label
            ]
        result["cases"][case.name] = entry

    single_plane = len(controls.symmetry_planes) == 1
    for plane in controls.symmetry_planes:
        for name in plane.cases:
            try:
                check = symmetry_check(tables, plane, name)
            except KeyError:
                continue
            label = name if single_plane else f"{name} {plane.normal}={plane.position}"
            result["symmetry"][label] = check

    (out_dir / controls.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = summarize(ctx, result)
    # Lot 45 : les empreintes de ce qui a été contrôlé, pour que le paquet de
    # résultats rattache ces verdicts à une exécution précise.
    summary["provenance"] = {
        "mess_sha256": hashlib.sha256(mess_path.read_bytes()).hexdigest(),
        "comm_sha256": hashlib.sha256(comm_path.read_bytes()).hexdigest(),
    }
    (out_dir / "controles_d.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "controles_d.md").write_text(render_summary(summary), encoding="utf-8")
    return result


def summarize(ctx: ProjectContext, result: dict[str, Any]) -> dict[str, Any]:
    """The trunk's own verdicts: equilibrium per case, gravity, symmetry. A
    level D control, never a level E validation."""
    controls = ctx.declaration.controls
    assert controls is not None
    threshold = controls.threshold
    vertical = controls.vertical
    cases: dict[str, Any] = {}
    for name, entry in result["cases"].items():
        worst = max(abs(t["relative_gap"]) for t in entry["components"].values())
        cases[name] = {"worst_relative_gap": worst, "verdict": entry["verdict"]}
    gravity: dict[str, Any] = {}
    for case in controls.cases:
        if not case.gravity or case.name not in result["cases"]:
            continue
        term = result["cases"][case.name]["components"][vertical]
        gap = abs(term["relative_gap"])
        gravity[case.name] = {
            "component": vertical,
            "applied_n": term["applied_as_evaluated_n"],
            "reactions_blocked_n": term["reactions_blocked_n"],
            "springs_on_structure_n": term["springs_on_structure_n"],
            "relative_gap": gap,
            "verdict": "RÉUSSI" if gap <= threshold else "ÉCHEC",
        }
    symmetry = {
        name: {
            "n_pairs_checked": s["n_pairs_checked"],
            "n_unmatched": s["n_unmatched"],
            "worst_relative_gap": s["worst_relative_gap"],
            "verdict": "RÉUSSI"
            if s["n_pairs_checked"] > 0 and s["worst_relative_gap"] <= threshold
            else "ÉCHEC",
        }
        for name, s in result["symmetry"].items()
    }
    informative = {
        name: {
            "worst_relative_gap": max(
                abs(t["relative_gap"]) for t in entry["components"].values()
            )
        }
        for name, entry in result["informative_cases"].items()
    }
    verdicts = [c["verdict"] for c in (*cases.values(), *gravity.values())] + [
        s["verdict"] for s in symmetry.values()
    ]
    summary: dict[str, Any] = {
        "project": ctx.declaration.name,
        "level": "D",
        "threshold": threshold,
        "equilibrium": cases,
        "gravity": gravity,
        "symmetry": symmetry,
        "informative": informative,
        "verdict": "RÉUSSI"
        if verdicts and all(v == "RÉUSSI" for v in verdicts)
        else "ÉCHEC",
    }
    # Lot 46 : le harnais par défaut. CTL-005 et CTL-006 relisent les verdicts
    # ci-dessus (inchangés) ; CTL-013 et CTL-012 y ajoutent les leurs, qui comptent
    # dans le verdict d'ensemble.
    summary["harness"] = run_harness(ctx, result, summary)
    extra = [
        c["verdict"]
        for control_id, c in summary["harness"]["controls"].items()
        if control_id in GENERIC_CONTROLS + ("CTL-012",)
        and c["verdict"] in VERDICTS_THAT_COUNT
    ]
    if summary["verdict"] == "RÉUSSI" and any(v != "RÉUSSI" for v in extra):
        summary["verdict"] = "ÉCHEC"
    return summary


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"# Contrôles de niveau D — {summary['project']}",
        "",
        "Contrôles de cohérence d'un calcul exécuté (niveau D) : équilibre, pesanteur, "
        "symétrie. Ce n'est jamais une validation par comparaison à une référence "
        "(niveau E).",
        "",
        f"Seuil : {summary['threshold']:.1e} en relatif. Verdict d'ensemble : "
        f"**{summary['verdict']}**.",
        "",
        "## Équilibre",
        "",
        "| Cas | Écart relatif maximal | Verdict |",
        "| --- | --- | --- |",
    ]
    for name, c in summary["equilibrium"].items():
        lines.append(f"| {name} | {c['worst_relative_gap']:.2e} | {c['verdict']} |")
    for name, c in summary["informative"].items():
        lines.append(f"| {name} (informatif) | {c['worst_relative_gap']:.2e} | — |")
    lines += ["", "## Pesanteur", ""]
    if summary["gravity"]:
        lines += [
            "| Cas | Composante | Charge appliquée (N) | Réactions bloquées (N) "
            "| Ressorts (N) | Écart relatif | Verdict |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for name, g in summary["gravity"].items():
            lines.append(
                f"| {name} | {g['component']} | {g['applied_n']:.6e} "
                f"| {g['reactions_blocked_n']:.6e} | {g['springs_on_structure_n']:.6e} "
                f"| {g['relative_gap']:.2e} | {g['verdict']} |"
            )
    else:
        lines.append("Aucun cas de pesanteur déclaré.")
    lines += ["", "## Symétrie", ""]
    if summary["symmetry"]:
        lines += [
            "| Cas | Paires | Non appariés | Écart relatif maximal | Verdict |",
            "| --- | --- | --- | --- | --- |",
        ]
        for name, s in summary["symmetry"].items():
            lines.append(
                f"| {name} | {s['n_pairs_checked']} | {s['n_unmatched']} "
                f"| {s['worst_relative_gap']:.2e} | {s['verdict']} |"
            )
    else:
        lines.append("Aucun plan de symétrie déclaré.")
    return "\n".join(lines) + "\n"


__all__ = [
    "COMPONENTS",
    "balance_terms",
    "expected_resultant",
    "group_reactions",
    "level_d_controls",
    "render_summary",
    "summarize",
    "symmetry_check",
]
