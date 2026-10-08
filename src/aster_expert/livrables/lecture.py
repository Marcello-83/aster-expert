"""`aster-expert resultats lire <projet>` and the MCP tool `query_results` (lot 49).

Answers a question on the results by reading the arrays of the deliverables
(`resultats/livrables/donnees/`, written from the MED of the post-processing run),
never from memory and never with a throw-away script. Filters:

- `groupes`: cell or node groups (a row is kept when its element belongs to one of
  them, or its node does);
- `champ` (key of a declared field: `DEPL`, `EFGE_NOEU`, `EFGE_ELNO_2`...) and
  `composantes`;
- `cas`: elementary cases, combinations (by name: both the max and the min of a
  combination that envelopes a moving load), or `enveloppe`;
- `mode`: `extremum` (max and min of each component, with place, governing
  combination and moving position), `point` (the node nearest to `point`), `coupe`
  (the rows on the plane `axe = valeur`), `somme` (Σ over the rows), `tout`;
- exclusion discs (PAT-013): those `projet.yaml` declares, applied by default to an
  `extremum`, or one given here (`disque_groupe`, `disque_rayon`).

The answer is a CSV (`;`, values in SI units, then in display units rounded by
`config/arrondis.yaml`) and one line of provenance (manifest, MED and runs, with their
SHA-256).
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from aster_expert.arrondis import format_value, load_table
from aster_expert.livrables.donnees import Deliverables, FieldArrays, FieldInfo
from aster_expert.livrables.unites import display, si_unit
from aster_expert.projet.context import ProjectContext, load_project
from aster_expert.projet.errors import ProjectError

Mode = Literal["extremum", "point", "coupe", "somme", "tout"]
COLUMNS = [
    "source",
    "cas_ou_combinaison",
    "champ",
    "composante",
    "valeur_si",
    "unite_si",
    "valeur",
    "unite",
    "noeud_med",
    "maille_med",
    "extremite",
    "x_m",
    "y_m",
    "z_m",
    "extremum",
    "combinaison_gouvernante",
    "position_mobile",
]


@dataclass
class Query:
    groupes: tuple[str, ...] = ()
    noeuds: str | None = None
    """Node group every row must be carried by (AND with `groupes`)."""
    champ: str | None = None
    composantes: tuple[str, ...] = ()
    cas: tuple[str, ...] = ()
    mode: Mode = "extremum"
    point: tuple[float, ...] | None = None
    coupe: str | None = None
    """`AXE=valeur` (`Y=0`), with `tolerance`."""
    tolerance: float = 1.0e-6
    disques: bool = True
    disque_groupe: str | None = None
    disque_rayon: float | None = None
    limite: int = 100000


@dataclass
class Answer:
    rows: list[dict[str, Any]] = field(default_factory=list)
    provenance: str = ""
    notes: list[str] = field(default_factory=list)

    def csv(self) -> str:
        buffer = io.StringIO()
        buffer.write(f"# {self.provenance}\n")
        for note in self.notes:
            buffer.write(f"# {note}\n")
        writer = csv.DictWriter(
            buffer, fieldnames=COLUMNS, delimiter=";", lineterminator="\n"
        )
        writer.writeheader()
        for row in self.rows:
            writer.writerow({k: row.get(k, "") for k in COLUMNS})
        return buffer.getvalue()


def _expression(text: str) -> dict[str, float]:
    """`PP+G2`, `1.35*PP+1.5*Q-0.5*TEM`: coefficient of each case."""
    out: dict[str, float] = {}
    for term in text.replace("-", "+-").split("+"):
        term = term.strip()
        if not term:
            continue
        sign = -1.0 if term.startswith("-") else 1.0
        term = term.lstrip("-").strip()
        coefficient, star, name = term.partition("*")
        if not star:
            coefficient, name = "1", coefficient
        out[name.strip()] = out.get(name.strip(), 0.0) + sign * float(coefficient)
    return out


def _sources(
    d: Deliverables, fa: FieldArrays, names: tuple[str, ...]
) -> list[tuple[str, str, Any]]:
    """(key, label, values) of the requested cases: elementary cases, positions of a
    moving load (`TSB_P25`), combinations (by name; a combination with a moving load
    gives its max and min, or its value at one position: `<name>@<position>`), the
    envelope (`enveloppe`), or a sum of cases (`expr:PP+G2`, `expr:1.35*PP+1.5*Q`)."""
    combos = {c.name: i for i, c in enumerate(d.combinations)}
    out: list[tuple[str, str, Any]] = []

    def array_of(case: str) -> Any:
        for prefix in ("cas/", "pos/"):
            if prefix + case in fa.arrays:
                return fa.arrays[prefix + case]
        message = f"cas inconnu : {case}"
        raise ProjectError(message)

    wanted = names or tuple(d.elementary)
    for name in wanted:
        if name.startswith("expr:"):
            terms = _expression(name[len("expr:") :])
            total = sum(c * array_of(n) for n, c in terms.items())
            out.append(("expr", name[len("expr:") :], total))
        elif "@" in name and name.split("@")[0] in combos:
            comb_name, position = name.split("@", 1)
            comb = d.combinations[combos[comb_name]]
            if position not in comb.mobile_cases:
                message = f"{position} n'est pas une position de {comb_name}"
                raise ProjectError(message)
            total = sum(c * array_of(n) for n, c in comb.fixed.items())
            total = total + comb.mobile_coefficient * array_of(position)
            out.append((f"comb/{combos[comb_name]}@{position}", name, total))
        elif name in d.elementary:
            out.append((f"cas/{name}", name, fa.arrays[f"cas/{name}"]))
        elif f"pos/{name}" in fa.arrays:
            out.append((f"pos/{name}", name, fa.arrays[f"pos/{name}"]))
        elif name in combos:
            i = combos[name]
            if d.combinations[i].mobile_cases:
                out += [
                    (f"comb/{i}/max", name + " (max)", fa.arrays[f"comb/{i}/max"]),
                    (f"comb/{i}/min", name + " (min)", fa.arrays[f"comb/{i}/min"]),
                ]
            else:
                out.append((f"comb/{i}/max", name, fa.arrays[f"comb/{i}/max"]))
        elif name.lower() == "enveloppe":
            if "env/max" not in fa.arrays:
                message = "aucune enveloppe dans les livrables (pas de combinaison)"
                raise ProjectError(message)
            out += [
                ("env/max", "enveloppe (max)", fa.arrays["env/max"]),
                ("env/min", "enveloppe (min)", fa.arrays["env/min"]),
            ]
        else:
            message = (
                f"cas ou combinaison inconnu : {name} (cas : "
                f"{', '.join(d.elementary)} ; combinaisons : {len(combos)} ; "
                "positions mobiles ; « enveloppe » ; <combinaison>@<position> ; "
                "expr:<a*CAS+b*CAS>)"
            )
            raise ProjectError(message)
    return out


def _rows_in_groups(
    d: Deliverables, fa: FieldArrays, nodes: Any, groups: tuple[str, ...]
) -> Any:
    """Rows of a cell group (its elements, and for a nodal field its nodes) or of a
    node group (any row carried by one of its nodes)."""
    if not groups:
        return np.ones(len(nodes), dtype=bool)
    keep = np.zeros(len(nodes), dtype=bool)
    for group in groups:
        cells = d.mesh.cell_group(group)
        if f"gno_{group}" in d.mesh.arrays:
            keep |= np.isin(nodes, d.mesh.arrays[f"gno_{group}"])
        elif cells is not None:
            level, ids = cells
            keep |= (fa.kind > 0) & (fa.level == level) & np.isin(fa.entity, ids)
            # Nodal values and point elements (springs) at the nodes of the group.
            keep |= (fa.kind != 1) & np.isin(nodes, d.mesh.node_group(group))
        else:
            message = f"groupe {group} absent du maillage des livrables"
            raise ProjectError(message)
    return keep


def _disc_mask(
    ctx: ProjectContext, d: Deliverables, nodes: Any, info: FieldInfo, q: Query
) -> Any:
    mask = np.zeros(len(nodes), dtype=bool)
    if not q.disques:
        return mask
    xy = d.mesh.coords[nodes, :2]
    discs: list[tuple[str, float]] = []
    if q.disque_groupe and q.disque_rayon:
        discs.append((q.disque_groupe, q.disque_rayon))
    else:
        section = ctx.declaration.deliverables
        for disk in section.exclusion_disks if section else ():
            if not disk.groups or set(disk.groups) & set(info.groups):
                discs.append((disk.node_group, disk.radius))
    for group, radius in discs:
        for centre in d.mesh.coords[d.mesh.node_group(group), :2]:
            mask |= np.hypot(*(xy - centre).T) <= radius + 1.0e-9
    return mask


def _row(
    d: Deliverables,
    fa: FieldArrays,
    nodes: Any,
    row: int,
    source: tuple[str, str],
    comp: str,
    value: float,
    table: Any,
) -> dict[str, Any]:
    unit = si_unit(fa.info.family, fa.info.field, comp)
    shown = display(unit)
    node = int(nodes[row])
    x, y, z = (float(v) for v in d.mesh.coords[node])
    out: dict[str, Any] = {
        "source": source[0],
        "cas_ou_combinaison": source[1],
        "champ": fa.info.key,
        "composante": comp,
        "valeur_si": repr(float(value)),
        "unite_si": unit,
        "valeur": format_value(value * shown.factor, shown.unit, table),
        "unite": shown.unit,
        "noeud_med": node + 1,
        "maille_med": int(fa.entity[row]) + 1 if fa.kind[row] > 0 else "",
        "extremite": int(fa.local[row]) + 1 if fa.kind[row] == 1 else "",
        "x_m": f"{x:.3f}",
        "y_m": f"{y:.3f}",
        "z_m": f"{z:.3f}",
    }
    if source[0].startswith("env/"):
        which = source[0].split("/")[1]
        c = fa.info.components.index(comp)
        ci = int(fa.arrays[f"env/{which}_comb"][row, c])
        pi = int(fa.arrays[f"env/{which}_pos"][row, c])
        comb = d.combinations[ci]
        out["combinaison_gouvernante"] = comb.name
        out["position_mobile"] = comb.mobile_cases[pi] if pi >= 0 else ""
    elif source[0].startswith("comb/") and source[0].endswith(("/max", "/min")):
        i = int(source[0].split("/")[1])
        comb = d.combinations[i]
        pos_key = source[0] + "_pos"
        if comb.mobile_cases and pos_key in fa.arrays:
            c = fa.info.components.index(comp)
            pi = int(fa.arrays[pos_key][row, c])
            out["position_mobile"] = comb.mobile_cases[pi] if pi >= 0 else ""
    return out


def query(ctx: ProjectContext, q: Query) -> Answer:
    section = ctx.declaration.deliverables
    if section is None:
        message = f"{ctx.declaration.name} : pas de section `deliverables`"
        raise ProjectError(message)
    root = ctx.results_dir / "livrables"
    try:
        d = Deliverables(root)
    except FileNotFoundError as exc:
        raise ProjectError(str(exc)) from exc
    infos = d.field_infos(section.fields)
    keys = [i.key for i in infos]
    if q.champ is not None and q.champ not in keys:
        message = f"champ inconnu : {q.champ} (champs livrés : {', '.join(keys)})"
        raise ProjectError(message)
    table = load_table(ctx.repo_root)
    answer = Answer(provenance=provenance(ctx, root))
    for info in infos:
        if q.champ is not None and info.key != q.champ:
            continue
        comps = [c for c in info.components if not q.composantes or c in q.composantes]
        if not comps:
            continue
        fa = d.field(info)
        nodes = fa.node_of_row(d.mesh)
        keep = _rows_in_groups(d, fa, nodes, q.groupes)
        if q.noeuds:
            keep &= np.isin(nodes, d.mesh.node_group(q.noeuds))
        if q.mode == "coupe":
            if not q.coupe or "=" not in q.coupe:
                message = "mode coupe : --coupe AXE=valeur (X, Y ou Z)"
                raise ProjectError(message)
            axis, value = q.coupe.split("=", 1)
            axis_index = "XYZ".index(axis.strip().upper())
            keep &= (
                np.abs(d.mesh.coords[nodes, axis_index] - float(value)) <= q.tolerance
            )
        if q.mode == "point":
            if q.point is None:
                message = "mode point : --point x,y[,z]"
                raise ProjectError(message)
            target = np.array([*q.point, *([0.0] * (3 - len(q.point)))])
            candidates = np.where(keep)[0]
            if candidates.size == 0:
                continue
            distance = np.linalg.norm(d.mesh.coords[nodes[candidates]] - target, axis=1)
            nearest = int(nodes[candidates[int(np.argmin(distance))]])
            keep &= nodes == nearest
            answer.notes.append(
                f"{info.key} : nœud le plus proche de {tuple(q.point)} : nœud MED "
                f"{nearest + 1}, à {float(distance.min()):.4g} m"
            )
        excluded = (
            _disc_mask(ctx, d, nodes, info, q)
            if q.mode == "extremum"
            else np.zeros(len(nodes), bool)
        )
        if excluded.any():
            answer.notes.append(
                f"{info.key} : {int((keep & excluded).sum())} ligne(s) exclue(s) "
                "par les disques d'exclusion (PAT-013)"
            )
        for key, label, values in _sources(d, fa, q.cas):
            source = (key, label)
            for comp in comps:
                c = info.components.index(comp)
                column = values[:, c].astype(np.float64)
                valid = keep & ~excluded & ~np.isnan(column)
                if not valid.any():
                    continue
                rows = np.where(valid)[0]
                if q.mode == "extremum":
                    for label, pick in (
                        ("max", rows[int(np.argmax(column[rows]))]),
                        ("min", rows[int(np.argmin(column[rows]))]),
                    ):
                        entry = _row(
                            d,
                            fa,
                            nodes,
                            int(pick),
                            source,
                            comp,
                            float(column[pick]),
                            table,
                        )
                        entry["extremum"] = label
                        answer.rows.append(entry)
                elif q.mode == "somme":
                    total = float(column[rows].sum())
                    unit = si_unit(info.family, info.field, comp)
                    shown = display(unit)
                    answer.rows.append(
                        {
                            "source": source[0],
                            "cas_ou_combinaison": source[1],
                            "champ": info.key,
                            "composante": comp,
                            "valeur_si": repr(total),
                            "unite_si": unit,
                            "valeur": format_value(
                                total * shown.factor, shown.unit, table
                            ),
                            "unite": shown.unit,
                            "extremum": f"somme sur {rows.size} ligne(s)",
                        }
                    )
                else:
                    for r in rows:
                        answer.rows.append(
                            _row(
                                d,
                                fa,
                                nodes,
                                int(r),
                                source,
                                comp,
                                float(column[r]),
                                table,
                            )
                        )
                if len(answer.rows) > q.limite:
                    message = (
                        f"plus de {q.limite} lignes : restreindre (groupe, champ, "
                        "composante, cas) ou relever --limite"
                    )
                    raise ProjectError(message)
    if not answer.rows:
        answer.notes.append("aucune ligne ne répond aux filtres")
    return answer


def provenance(ctx: ProjectContext, root: Path) -> str:
    manifest_path = root / "manifeste.json"
    if not manifest_path.is_file():
        return f"provenance : {root} (manifeste absent : sous-étape vues à faire)"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    med = manifest["fichiers"].get("med/resultats.med", {})
    return (
        f"provenance : projet {ctx.declaration.name} ; Code_Aster "
        f"{manifest['code_aster'].get('version')} ; post-traitement "
        f"{Path(manifest['execution_post_traitement'] or '').name} (tables "
        f"identiques à la production "
        f"{Path(manifest['execution_production'] or '').name}) ; "
        f".comm de production sha256 {manifest['comm_production_sha256']} ; "
        f"resultats.med sha256 {med.get('sha256')}"
    )


def query_project(project_root: Path, name: str, q: Query) -> Answer:
    return query(load_project(name, project_root), q)


__all__ = ["COLUMNS", "Answer", "Query", "provenance", "query", "query_project"]
