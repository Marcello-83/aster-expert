"""Combined element forces of an executed project (lot 41, étape 2.4).

The elementary cases are linear-elastic results whose element forces the
project's `.comm` prints, one table per case (`combinations.forces`); combining
them is a linear operation on numbers Code_Aster already computed, done here
rather than by re-running Code_Aster (same choice as the first project's lot 38).

`EFGE_ELNO` is not averaged by Code_Aster: an inner node carries one row per
adjacent element. The export averages them per node for readability -- never
for an equilibrium check.

Outputs (`combinations.output` of the declaration, under the results directory):
`combinaisons.csv` (every combination, every node), `extrema.csv` (per
combination, the node where each component is extreme, with the concurrent
components), `controle_manuel.json` (one combination recomputed independently,
cases grouped by coefficient, compared with `combine`) and, when the project
declares a report extension, its Markdown.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aster_expert.combinaisons.enumeration import (
    Combination,
    combine,
    enumerate_combinations,
    grouped_by_coefficient,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import ElementForces
from aster_expert.projet.errors import ProjectError

NodeValues = dict[str, float]
_LOCATION_COLUMNS = 6
"""`MAILLE`, `NOEUD`, `SOUS_POINT`, `COOR_X`, `COOR_Y`, `COOR_Z` of a
`CREA_TABLE/RESU` table of an `ELNO` field, before the components."""


def _marker(forces: ElementForces) -> re.Pattern[str]:
    prefix, _, suffix = forces.table.partition("{case}")
    return re.compile(rf"^##{re.escape(prefix)}(\w+){re.escape(suffix)}ASTER\s")


def parse_element_tables(
    text_lines: list[str], forces: ElementForces
) -> dict[str, list[dict[str, float]]]:
    """`{case: rows}`, one row per (element, node), in the order of the table."""
    marker = _marker(forces)
    width = len(forces.components) + _LOCATION_COLUMNS
    out: dict[str, list[dict[str, float]]] = {}
    i = 0
    n = len(text_lines)
    while i < n:
        m = marker.match(text_lines[i])
        if m is None:
            i += 1
            continue
        case = m.group(1)
        header = text_lines[i + 1].split()
        rows = []
        j = i + 2
        while j < n and text_lines[j].strip() and not text_lines[j].startswith("#"):
            cells = text_lines[j].split()
            numeric = [float(c) for c in cells[-width:]]
            names = header[-width:]
            rows.append(dict(zip(names, numeric, strict=True)))
            j += 1
        out[case] = rows
        i = j
    return out


def average_by_node(
    rows: list[dict[str, float]], components: tuple[str, ...]
) -> dict[int, NodeValues]:
    by_node: dict[int, list[dict[str, float]]] = {}
    for row in rows:
        by_node.setdefault(int(row["NOEUD"]), []).append(row)
    result: dict[int, NodeValues] = {}
    for node, group in by_node.items():
        result[node] = {
            "x": group[0]["COOR_X"],
            **{c: sum(g[c] for g in group) / len(group) for c in components},
        }
    return result


@dataclass
class CombinedForces:
    mess_path: Path
    diagnostic: str
    """Last `DIAGNOSTIC JOB` line of the listing."""
    forces: ElementForces
    combinations: list[Combination]
    cases: dict[str, dict[int, NodeValues]]
    combined: dict[str, dict[int, NodeValues]]
    manual_check: dict[str, Any] | None


def load_cases(
    mess_path: Path, forces: ElementForces
) -> tuple[dict[str, list[dict[str, float]]], str]:
    lines = mess_path.read_text(encoding="utf-8", errors="strict").splitlines()
    raw = parse_element_tables(lines, forces)
    missing = set(forces.cases) - set(raw)
    if missing:
        message = f"tables d'efforts absentes de {mess_path} : {sorted(missing)}"
        raise ProjectError(message)
    diagnostic = [line for line in lines if "DIAGNOSTIC JOB" in line]
    return raw, diagnostic[-1].strip() if diagnostic else ""


def combined_per_node(
    cases: dict[str, dict[int, NodeValues]],
    combinations: list[Combination],
    forces: ElementForces,
) -> dict[str, dict[int, NodeValues]]:
    reference = cases[forces.reference_case]
    nodes = sorted(next(iter(cases.values())))
    out: dict[str, dict[int, NodeValues]] = {}
    for combination in combinations:
        per_node: dict[int, NodeValues] = {}
        for node in nodes:
            values = {
                comp: combine(
                    combination.coefficients,
                    {
                        case: cases[case][node][comp]
                        for case in combination.coefficients
                    },
                )
                for comp in forces.components
            }
            per_node[node] = {"x": reference[node]["x"], **values}
        out[combination.name] = per_node
    return out


def extrema(
    per_node: dict[int, NodeValues], components: tuple[str, ...]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for comp in components:
        node = max(per_node, key=lambda n: abs(per_node[n][comp]))
        out[comp] = {"node": node, **per_node[node]}
    return out


def manual_check(
    cases: dict[str, dict[int, NodeValues]],
    combinations: list[Combination],
    name: str,
    node: int,
    components: tuple[str, ...],
) -> dict[str, Any]:
    """One combination recomputed independently (cases grouped by coefficient),
    compared with `combine`."""
    target = next((c for c in combinations if c.name == name), None)
    if target is None:
        message = f"contrôle manuel : combinaison {name} inconnue"
        raise ProjectError(message)
    hand = {
        comp: grouped_by_coefficient(
            target.coefficients,
            {case: cases[case][node][comp] for case in target.coefficients},
        )
        for comp in components
    }
    code = {
        comp: combine(
            target.coefficients,
            {case: cases[case][node][comp] for case in target.coefficients},
        )
        for comp in components
    }
    gaps = {c: abs(hand[c] - code[c]) for c in components}
    return {
        "combination": target.name,
        "coefficients": target.coefficients,
        "node": node,
        "hand": hand,
        "code": code,
        "max_absolute_gap": max(gaps.values()),
    }


def combined_forces(ctx: ProjectContext, mess_path: Path) -> CombinedForces:
    section = ctx.declaration.combinations
    if section is None or section.forces is None:
        message = (
            f"le projet {ctx.declaration.name} ne déclare pas d'efforts à combiner"
        )
        raise ProjectError(message)
    forces = section.forces
    raw, diagnostic = load_cases(mess_path, forces)
    cases = {
        case: average_by_node(raw[case], forces.components) for case in forces.cases
    }
    combinations = enumerate_combinations(section, ctx.number)
    combined = combined_per_node(cases, combinations, forces)
    check = None
    if section.manual_check is not None:
        reference = cases[forces.reference_case]
        node = min(
            reference,
            key=lambda n: abs(reference[n]["x"] - section.manual_check.node_nearest_x),  # type: ignore[union-attr]
        )
        check = manual_check(
            cases,
            combinations,
            section.manual_check.combination,
            node,
            forces.components,
        )
    return CombinedForces(
        mess_path=mess_path,
        diagnostic=diagnostic,
        forces=forces,
        combinations=combinations,
        cases=cases,
        combined=combined,
        manual_check=check,
    )


def write_combined_forces(
    ctx: ProjectContext, result: CombinedForces, out_dir: Path, **context: Path
) -> list[Path]:
    """Write the CSV files, the manual check and the files of the project's
    report extension (`f(ctx, result, **context) -> {file name: text}`)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    components = result.forces.components
    written = []
    path = out_dir / "combinaisons.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["combinaison", "famille", "noeud", "x_m", *components])
        for combination in result.combinations:
            for node, values in sorted(result.combined[combination.name].items()):
                writer.writerow(
                    [
                        combination.name,
                        combination.family,
                        node,
                        f"{values['x']:.6f}",
                        *(f"{values[c]:.6e}" for c in components),
                    ]
                )
    written.append(path)
    path = out_dir / "extrema.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "combinaison",
                "famille",
                "composante_extremale",
                "noeud",
                "x_m",
                *components,
            ]
        )
        for combination in result.combinations:
            for comp, row in extrema(
                result.combined[combination.name], components
            ).items():
                writer.writerow(
                    [
                        combination.name,
                        combination.family,
                        comp,
                        row["node"],
                        f"{row['x']:.6f}",
                        *(f"{row[c]:.6e}" for c in components),
                    ]
                )
    written.append(path)
    section = ctx.declaration.combinations
    assert section is not None
    if section.report is not None:
        files: dict[str, str] = ctx.extension(section.report)(ctx, result, **context)
        for name, content in files.items():
            path = out_dir / name
            path.write_text(content, encoding="utf-8")
            written.append(path)
    if result.manual_check is not None:
        path = out_dir / "controle_manuel.json"
        path.write_text(
            json.dumps(result.manual_check, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


__all__ = [
    "CombinedForces",
    "average_by_node",
    "combined_forces",
    "combined_per_node",
    "extrema",
    "load_cases",
    "manual_check",
    "parse_element_tables",
    "write_combined_forces",
]
