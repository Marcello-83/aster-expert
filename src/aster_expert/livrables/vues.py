"""Views, checks, tables and manifest of the deliverables (lot 49).

Sub-step `vues` of `aster-expert projet <nom> livrables`, on what the container wrote
(`aster_expert.livrables.donnees`):

1. `.vtu` conversion of the MED fields (cases, combinations, envelopes, loads), each
   file read back and compared value for value (`aster_expert.livrables.vtu`);
2. CTL-013 on the MED of loads: Σ of the nodal forces of each elementary case against
   the resultant the project declares (`controls.cases`, the harness's own extension
   and inputs), with the point where the vertical resultant applies;
3. equilibrium read in the deliverables: Σ loads + Σ reactions + Σ spring forces;
4. extrema by family and component (with place, governing combination and moving
   load position, exclusion discs of PAT-013), values at the reading points,
   envelopes along the linear members;
5. the manifest (`manifeste.json`): files with SHA-256, source runs, `.comm`, mesh,
   Code_Aster version, cases, combinations, fields and units, scale data of the
   ParaView scripts.

The files of steps 2 to 5 are written in `resultats/livrables/paquet/`, the part of
the deliverables the results package copies (section `visualisation`); the workbook
is built from them, without recomputing anything.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.arrondis import RoundingTable, format_value, load_table
from aster_expert.livrables.calcul import resultant
from aster_expert.livrables.chaine import (
    deliverables_dir,
    load_deliverables_state,
    sha256,
)
from aster_expert.livrables.donnees import (
    Deliverables,
    FieldArrays,
    FieldInfo,
    FloatArray,
    Mesh,
)
from aster_expert.livrables.unites import display, si_unit
from aster_expert.livrables.vtu import Grid, check_identical, grid_from_mesh, write_vtu
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

PACKAGE_DIR = "paquet"
TRANSLATIONS = ("DX", "DY", "DZ")


# --- names -----------------------------------------------------------------------


def comb_label(name: str) -> str:
    return name.replace(" ", "_")


def array_names(d: Deliverables, key: str) -> list[tuple[str, str]]:
    """(npz key, MED name) of every array of a field: cases, combinations, envelopes."""
    out = [(f"cas/{c}", f"CAS_{c}__{key}") for c in d.elementary]
    for i, comb in enumerate(d.combinations):
        label = comb_label(comb.name)
        if comb.mobile_cases:
            out.append((f"comb/{i}/max", f"COMB_{label}__{key}__MAX"))
            out.append((f"comb/{i}/min", f"COMB_{label}__{key}__MIN"))
        else:
            out.append((f"comb/{i}/max", f"COMB_{label}__{key}"))
    if d.combinations and d.spec.get("envelopes"):
        for suffix in ("max", "min", "max_comb", "min_comb", "max_pos", "min_pos"):
            out.append((f"env/{suffix}", f"ENV__{key}__{suffix.upper()}"))
    return out


# --- VTU ---------------------------------------------------------------------------


def _category(npz_key: str) -> str:
    return {"cas": "cas", "comb": "combinaisons", "env": "enveloppes"}[
        npz_key.split("/")[0]
    ]


def _scatter(
    fa: FieldArrays,
    values: FloatArray,
    order: dict[tuple[int, int], int],
    n_points: int,
    n_cells: int,
    prefix: str,
    components: Iterable[str],
) -> tuple[dict[str, FloatArray], dict[str, FloatArray]]:
    """Per-component point and cell arrays of one MED field (NaN where the field is not
    defined)."""
    point: dict[str, FloatArray] = {}
    cell: dict[str, FloatArray] = {}
    values = values.reshape(len(fa.kind), -1).astype(np.float64)
    nodes = fa.kind == 0
    if nodes.any():
        for c, comp in enumerate(components):
            full = np.full(n_points, np.nan)
            full[fa.entity[nodes]] = values[nodes, c]
            point[f"{prefix}_{comp}"] = full
    elements = fa.kind > 0
    if elements.any():
        vtk_index = np.array(
            [
                order[(int(lv), int(e))]
                for lv, e in zip(fa.level[elements], fa.entity[elements], strict=True)
            ]
        )
        locals_ = fa.local[elements]
        gauss = fa.kind[elements] == 2
        for c, comp in enumerate(components):
            for local in np.unique(locals_):
                rows = locals_ == local
                full = np.full(n_cells, np.nan)
                full[vtk_index[rows]] = values[elements][rows, c]
                suffix = "" if gauss.all() else f"_{int(local) + 1}"
                cell[f"{prefix}_{comp}{suffix}"] = full
    return point, cell


def export_vtu(d: Deliverables, infos: list[FieldInfo], out: Path) -> dict[str, Any]:
    """`cas.vtu`, `combinaisons.vtu`, `enveloppes.vtu`, `charges.vtu`, each read back
    and compared to its source arrays."""
    base, order_list = grid_from_mesh(d.mesh.arrays)
    order = {key: i for i, key in enumerate(order_list)}
    n_points, n_cells = len(base.points), len(base.types)
    grids: dict[str, Grid] = {}

    def grid(name: str) -> Grid:
        if name not in grids:
            grids[name] = Grid(base.points, base.connectivity, base.offsets, base.types)
        return grids[name]

    for info in infos:
        fa = d.field(info)
        for npz_key, med_name in array_names(d, info.key):
            values = fa.arrays[npz_key]
            point, cell = _scatter(
                fa, values, order, n_points, n_cells, med_name, info.components
            )
            g = grid(_category(npz_key))
            g.point_data.update(point)
            g.cell_data.update(cell)
    g = grid("charges")
    for name, values, kind, entity, components in d.loads():
        if not (kind == 0).all():
            continue
        values = values.reshape(len(kind), -1)
        for c, comp in enumerate(
            components or [f"C{i}" for i in range(values.shape[1])]
        ):
            full = np.full(n_points, np.nan)
            full[entity] = values[:, c]
            g.point_data[f"{name}_{comp}"] = full
    report: dict[str, Any] = {}
    for name, g in grids.items():
        path = out / f"{name}.vtu"
        write_vtu(path, g)
        report[name] = {
            "fichier": path.name,
            "octets": path.stat().st_size,
            **check_identical(g, path),
        }
    return report


# --- loads -------------------------------------------------------------------------


def _node_values(values: FloatArray, kind: Any, entity: Any, n: int) -> FloatArray:
    full = np.zeros((n, values.reshape(len(kind), -1).shape[1]))
    full[entity[kind == 0]] = values.reshape(len(kind), -1)[kind == 0]
    return full


def control_loads(ctx: ProjectContext, d: Deliverables) -> dict[str, Any]:
    """CTL-013 on the MED of loads (see module docstring)."""
    from aster_expert.controles.equilibre import expected_resultant  # noqa: PLC0415
    from aster_expert.projet.pipeline import load_state  # noqa: PLC0415

    controls = ctx.declaration.controls
    declared = {c.name: c for c in controls.cases} if controls else {}
    threshold = controls.threshold if controls else 1.0e-6
    state = load_state(ctx)
    out_dir = deliverables_dir(ctx) / "controle_charges"
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {
        "comm_path": Path(state.comm or ""),
        "mesh_path": Path(state.mesh_med or ""),
        "out_dir": out_dir,
    }
    coords = d.mesh.coords
    cases: dict[str, Any] = {}
    for name, values, kind, entity, components in d.loads():
        if not name.startswith(("FN_", "FV_")):
            continue
        case = name[3:]
        full = _node_values(values, kind, entity, len(coords))
        sums = resultant(coords, full)
        entry: dict[str, Any] = {
            "champ_med": name,
            "nature": "forces" if name.startswith("FN_") else "forces_varc",
            "somme_n": sums,
            "composantes": components,
        }
        if name.startswith("FV_"):
            total = float(np.abs(full[:, :3]).sum())
            gap = max(abs(sums[c]) for c in ("FX", "FY", "FZ"))
            entry["autoequilibre"] = {
                "somme_des_modules_n": total,
                "ecart_relatif": gap / total if total else math.nan,
            }
        elif case in declared and declared[case].expected_resultant is not None:
            evaluated, specified = expected_resultant(ctx, declared[case], **inputs)
            measured = {"DX": sums["FX"], "DY": sums["FY"], "DZ": sums["FZ"]}
            scale = max(abs(v) for v in evaluated.values()) or 1.0
            gap = max(abs(measured[c] - evaluated[c]) for c in measured) / scale
            entry["attendu_tel_qu_evalue_n"] = evaluated
            entry["attendu_specifie_n"] = specified
            entry["ecart_relatif"] = gap
            entry["seuil"] = threshold
            entry["verdict"] = "RÉUSSI" if gap <= threshold else "ÉCHEC"
            if declared[case].informative:
                entry["verdict"] = "INFORMATIF"
        else:
            entry["verdict"] = "SANS RÉSULTANTE DÉCLARÉE"
        cases[case] = entry
    failed = sorted(c for c, e in cases.items() if e.get("verdict") == "ÉCHEC")
    return {
        "controle": "CTL-013 sur le MED des charges (lot 49)",
        "source": "somme des forces nodales du champ FN_<cas> (CALC_VECT_ELEM, "
        "ASSE_VECTEUR) ; résultante attendue de controls.cases (projet.yaml)",
        "seuil": threshold,
        "cas": cases,
        "echecs": failed,
        "verdict": "ÉCHEC" if failed else "RÉUSSI",
    }


# --- extrema, points, envelopes ------------------------------------------------------


def _excluded(mesh: Mesh, nodes: Any, disks: Iterable[Any], groups: set[str]) -> Any:
    mask = np.zeros(len(nodes), dtype=bool)
    xy = mesh.coords[nodes, :2]
    for disk in disks:
        if disk.groups and not (set(disk.groups) & groups):
            continue
        for centre in mesh.coords[mesh.node_group(disk.node_group), :2]:
            mask |= np.hypot(*(xy - centre).T) <= disk.radius + 1.0e-9
    return mask


def _place(d: Deliverables, fa: FieldArrays, row: int, nodes: Any) -> dict[str, Any]:
    node = int(nodes[row])
    place: dict[str, Any] = {
        "noeud_med": node + 1,
        "coordonnees_m": [float(x) for x in d.mesh.coords[node]],
    }
    if fa.kind[row] > 0:
        level, cell = int(fa.level[row]), int(fa.entity[row])
        place["maille_med"] = cell + 1
        place["niveau"] = level
        place["extremite"] = int(fa.local[row]) + 1
        place["groupes"] = [
            g for g in d.mesh.cell_groups_of(level, cell) if g in fa.info.groups
        ] or d.mesh.cell_groups_of(level, cell)[:3]
    else:
        place["groupes"] = [
            g
            for g in (*fa.info.groups, *fa.info.node_groups)
            if node in set(d.mesh.node_group(g).tolist())
        ]
    return place


def _governing(
    d: Deliverables, fa: FieldArrays, which: str, row: int, column: int
) -> dict[str, Any]:
    comb_index = int(fa.arrays[f"env/{which}_comb"][row, column])
    pos_index = int(fa.arrays[f"env/{which}_pos"][row, column])
    comb = d.combinations[comb_index]
    return {
        "combinaison": comb.name,
        "famille_combinaison": comb.family,
        "position_mobile": comb.mobile_cases[pos_index] if pos_index >= 0 else None,
        "charge_mobile": comb.mobile_label,
    }


def extrema(
    ctx: ProjectContext, d: Deliverables, infos: list[FieldInfo]
) -> list[dict[str, Any]]:
    """Max and min of every component, over the envelope of the combinations (or the
    elementary cases when no combination is declared), outside the exclusion discs."""
    section = ctx.declaration.deliverables
    assert section is not None
    rows_out: list[dict[str, Any]] = []
    for info in infos:
        fa = d.field(info)
        nodes = fa.node_of_row(d.mesh)
        excluded = _excluded(d.mesh, nodes, section.exclusion_disks, set(info.groups))
        has_env = "env/max" in fa.arrays
        for c, comp in enumerate(info.components):
            unit = si_unit(info.family, info.field, comp)
            for which in ("max", "min"):
                if has_env:
                    column = fa.arrays[f"env/{which}"][:, c]
                    governing_case = None
                else:
                    stack = np.stack(
                        [fa.arrays[f"cas/{n}"][:, c] for n in d.elementary]
                    )
                    column = stack.max(axis=0) if which == "max" else stack.min(axis=0)
                    pick = (
                        stack.argmax(axis=0) if which == "max" else stack.argmin(axis=0)
                    )
                    governing_case = pick
                valid = ~np.isnan(column) & ~excluded
                if not valid.any():
                    continue
                candidates = np.where(valid)[0]
                row = int(
                    candidates[
                        np.argmax(column[valid])
                        if which == "max"
                        else np.argmin(column[valid])
                    ]
                )
                entry: dict[str, Any] = {
                    "famille": info.family,
                    "champ": info.field,
                    "cle": info.key,
                    "composante": comp,
                    "extremum": which,
                    "valeur_si": float(column[row]),
                    "unite_si": unit,
                    "lieu": _place(d, fa, row, nodes),
                    "hors_disques": bool(excluded.any()),
                }
                if has_env:
                    entry.update(_governing(d, fa, which, row, c))
                elif governing_case is not None:
                    entry["cas"] = d.elementary[int(governing_case[row])]
                rows_out.append(entry)
    return rows_out


def reading_points(
    ctx: ProjectContext, d: Deliverables, infos: list[FieldInfo]
) -> list[dict[str, Any]]:
    """Values of every field at the declared reading points, per elementary case and
    for the envelope."""
    section = ctx.declaration.deliverables
    assert section is not None
    out: list[dict[str, Any]] = []
    for point in section.points:
        targets = set(d.mesh.node_group(point.node_group).tolist())
        cell_ids: set[int] | None = None
        if point.cell_group:
            found = d.mesh.cell_group(point.cell_group)
            cell_ids = set(found[1].tolist()) if found else set()
        for info in infos:
            fa = d.field(info)
            nodes = fa.node_of_row(d.mesh)
            for row in range(len(nodes)):
                if int(nodes[row]) not in targets:
                    continue
                if fa.kind[row] > 0 and (
                    cell_ids is None or int(fa.entity[row]) not in cell_ids
                ):
                    continue
                place = _place(d, fa, row, nodes)
                for source in [f"cas/{n}" for n in d.elementary] + (
                    ["env/max", "env/min"] if "env/max" in fa.arrays else []
                ):
                    values = fa.arrays[source][row]
                    out.append(
                        {
                            "point": point.label,
                            "cle": info.key,
                            "famille": info.family,
                            "source": source,
                            "lieu": place,
                            "valeurs_si": {
                                comp: float(values[c])
                                for c, comp in enumerate(info.components)
                            },
                        }
                    )
    return out


def linear_envelopes(d: Deliverables, infos: list[FieldInfo]) -> list[dict[str, Any]]:
    """Envelope of the element-node fields (beams), element end by element end."""
    out: list[dict[str, Any]] = []
    for info in infos:
        fa = d.field(info)
        if "env/max" not in fa.arrays or not (fa.kind == 1).any():
            continue
        nodes = fa.node_of_row(d.mesh)
        for row in np.where(fa.kind == 1)[0]:
            row = int(row)
            node = int(nodes[row])
            level, cell = int(fa.level[row]), int(fa.entity[row])
            entry: dict[str, Any] = {
                "cle": info.key,
                "maille_med": cell + 1,
                "extremite": int(fa.local[row]) + 1,
                "noeud_med": node + 1,
                "x_m": float(d.mesh.coords[node, 0]),
                "y_m": float(d.mesh.coords[node, 1]),
                "z_m": float(d.mesh.coords[node, 2]),
                "niveau": level,
            }
            for c, comp in enumerate(info.components):
                entry[f"{comp}_max"] = float(fa.arrays["env/max"][row, c])
                entry[f"{comp}_min"] = float(fa.arrays["env/min"][row, c])
            out.append(entry)
    return out


def equilibrium(
    ctx: ProjectContext, d: Deliverables, infos: list[FieldInfo], loads: dict[str, Any]
) -> dict[str, Any]:
    """Σ loads + Σ reactions + Σ spring forces of each elementary case, read in the
    deliverables (reactions: REAC_NODA on the declared node groups; springs: −SIEF_ELGA
    of the discrete elements, the force of the spring on the structure)."""
    out: dict[str, Any] = {}
    reac = [i for i in infos if i.family == "reactions"]
    springs = [i for i in infos if i.family == "ressorts"]
    controls = ctx.declaration.controls
    supports = {s.group for s in controls.supports} if controls else set()
    written = {g for i in reac for g in i.node_groups}
    for case in d.elementary:
        load = loads["cas"].get(case, {}).get("somme_n")
        entry: dict[str, Any] = {"charge_n": load}
        total_r = np.zeros(3)
        for info in reac:
            fa = d.field(info)
            values = fa.arrays[f"cas/{case}"]
            cols = [
                info.components.index(c) for c in TRANSLATIONS if c in info.components
            ]
            total_r[: len(cols)] += np.nansum(values[:, cols], axis=0)
        total_s = np.zeros(3)
        for info in springs:
            fa = d.field(info)
            values = fa.arrays[f"cas/{case}"]
            for k, comp in enumerate(("N", "VY", "VZ")):
                if comp in info.components:
                    total_s[k] -= float(
                        np.nansum(values[:, info.components.index(comp)])
                    )
        entry["reactions_n"] = dict(
            zip(("FX", "FY", "FZ"), map(float, total_r), strict=True)
        )
        entry["ressorts_n"] = dict(
            zip(("FX", "FY", "FZ"), map(float, total_s), strict=True)
        )
        if load is not None:
            entry["bilan_n"] = {
                k: load[k] + entry["reactions_n"][k] + entry["ressorts_n"][k]
                for k in ("FX", "FY", "FZ")
            }
        out[case] = entry
    return {
        "cas": out,
        "appuis_non_livres": sorted(supports - written),
        "note": "réactions des seuls groupes livrés ; un appui non livré (motif dans "
        "projet.yaml) laisse un bilan non nul sur ses composantes",
    }


# --- CSV -----------------------------------------------------------------------------


def _display(value: float | None, unit_si: str, table: RoundingTable) -> str:
    """A value in its display unit, with the decimals of `config/arrondis.yaml`."""
    if value is None or math.isnan(value):
        return ""
    target = display(unit_si)
    return format_value(value * target.factor, target.unit, table)


def write_csv(path: Path, header: list[str], rows: Iterable[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)


# --- step ----------------------------------------------------------------------------


def manifest(
    ctx: ProjectContext, d: Deliverables, infos: list[FieldInfo], vtu: dict[str, Any]
) -> dict[str, Any]:
    from aster_expert.projet.pipeline import load_state  # noqa: PLC0415

    state = load_deliverables_state(ctx)
    project_state = load_state(ctx)
    root = deliverables_dir(ctx)
    coords = d.mesh.coords
    span = coords.max(axis=0) - coords.min(axis=0)
    size = float(np.linalg.norm(span))
    files = {}
    for path in [
        root / "med" / "resultats.med",
        root / "med" / "charges.med",
        *sorted((root / "vtu").glob("*.vtu")),
    ]:
        files[path.relative_to(root).as_posix()] = {
            "sha256": sha256(path),
            "octets": path.stat().st_size,
        }
    scales: dict[str, Any] = {
        "taille_du_modele_m": size,
        "charges": {},
        "deplacements": {},
    }
    for name, values, kind, entity, _comps in d.loads():
        full = _node_values(values, kind, entity, len(coords))
        scales["charges"][name] = float(np.linalg.norm(full[:, :3], axis=1).max())
    scales["fleches"] = {}
    for info in infos:
        if info.family not in ("reactions", "ressorts"):
            continue
        fa = d.field(info)
        cols = [
            info.components.index(c)
            for c in ("DX", "DY", "DZ", "N", "VY", "VZ")
            if c in info.components
        ]
        for npz_key, med_name in array_names(d, info.key):
            if npz_key.endswith(("_comb", "_pos")):
                continue
            norm = np.linalg.norm(fa.arrays[npz_key][:, cols], axis=1)
            scales["fleches"][med_name] = (
                float(np.nanmax(norm)) if np.isfinite(norm).any() else 0.0
            )
    for info in infos:
        if info.field != "DEPL":
            continue
        fa = d.field(info)
        cols = [info.components.index(c) for c in TRANSLATIONS]
        for npz_key, med_name in array_names(d, info.key):
            if npz_key.endswith(("_comb", "_pos")):
                continue
            norm = np.linalg.norm(fa.arrays[npz_key][:, cols], axis=1)
            scales["deplacements"][med_name] = float(np.nanmax(norm))
    report = json.loads(
        (Path(state.post_run or "") / "compte_rendu.json").read_text(encoding="utf-8")
    )["report"]
    return {
        "schema_version": 1,
        "projet": ctx.declaration.name,
        "code_aster": {
            "version": report.get("aster_version"),
            "image_digest": report.get("image_digest"),
        },
        "execution_production": state.production_run,
        "comm_production_sha256": state.production_comm_sha256,
        "execution_post_traitement": state.post_run,
        "comm_post_traitement_sha256": state.post_comm_sha256,
        "validation_post_traitement": state.validation,
        "tables_identiques": state.tables,
        "maillage": {
            "chemin": project_state.mesh_med,
            "sha256": sha256(Path(project_state.mesh_med))
            if project_state.mesh_med
            else None,
        },
        "fichiers": files,
        "vtu": vtu,
        "cas_elementaires": d.elementary,
        "combinaisons": [
            {
                "indice": i,
                "nom": c.name,
                "famille": c.family,
                "definition": c.definition,
                "charge_mobile": c.mobile_label,
                "positions": list(c.mobile_cases),
            }
            for i, c in enumerate(d.combinations)
        ],
        "champs": [
            {
                "cle": info.key,
                "champ": info.field,
                "famille": info.family,
                "groupes": list(info.groups),
                "groupes_noeuds": list(info.node_groups),
                "convention": info.convention,
                "composantes": [
                    {
                        "nom": comp,
                        "unite_si": si_unit(info.family, info.field, comp),
                        "unite_affichage": display(
                            si_unit(info.family, info.field, comp)
                        ).unit,
                    }
                    for comp in info.components
                ],
                "noms_med": [m for _k, m in array_names(d, info.key)],
            }
            for info in infos
        ],
        "charges": [
            {
                "nom_med": name,
                "composantes": comps,
                "unite_si": "N (DX…DZ), N·m (DRX…DRZ)",
            }
            for name, _v, _k, _e, comps in d.loads()
        ],
        "echelles": scales,
    }


def step_vues(ctx: ProjectContext, rt: Any) -> list[str]:  # noqa: ARG001
    section = ctx.declaration.deliverables
    if section is None:
        message = "livrables : section `deliverables` absente"
        raise ProjectError(message)
    root = deliverables_dir(ctx)
    d = Deliverables(root)
    infos = d.field_infos(section.fields)
    vtu = export_vtu(d, infos, root / "vtu")
    bad = [k for k, v in vtu.items() if not v["identiques"]]
    if bad:
        message = f"livrables : VTU relus différents de leur source : {bad}"
        raise ProjectError(message)
    package = root / PACKAGE_DIR
    package.mkdir(parents=True, exist_ok=True)
    loads = control_loads(ctx, d)
    (package / "controle_charges.json").write_text(
        json.dumps(loads, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    balance = equilibrium(ctx, d, infos, loads)
    (package / "equilibre_livrables.json").write_text(
        json.dumps(balance, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    table = load_table(ctx.repo_root)
    found = extrema(ctx, d, infos)
    (package / "synthese.json").write_text(
        json.dumps(found, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_csv(
        package / "synthese.csv",
        [
            "famille",
            "champ",
            "composante",
            "extremum",
            "valeur",
            "unite",
            "groupes",
            "noeud_med",
            "maille_med",
            "X_m",
            "Y_m",
            "Z_m",
            "combinaison",
            "position_mobile",
            "cas",
        ],
        (
            [
                e["famille"],
                e["champ"],
                e["composante"],
                e["extremum"],
                _display(e["valeur_si"], e["unite_si"], table),
                display(e["unite_si"]).unit,
                " ".join(e["lieu"].get("groupes", [])),
                e["lieu"]["noeud_med"],
                e["lieu"].get("maille_med", ""),
                *(f"{x:.3f}" for x in e["lieu"]["coordonnees_m"]),
                e.get("combinaison", ""),
                e.get("position_mobile") or "",
                e.get("cas", ""),
            ]
            for e in found
        ),
    )
    points = reading_points(ctx, d, infos)
    (package / "points.json").write_text(
        json.dumps(points, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    linear = linear_envelopes(d, infos)
    (package / "enveloppes_lineiques.json").write_text(
        json.dumps(linear, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    data = manifest(ctx, d, infos, vtu)
    (root / "manifeste.json").write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    shutil_copy(root / "manifeste.json", package / "manifeste.json")
    lines = [
        "VTU : "
        + ", ".join(
            f"{v['fichier']} ({v['octets'] / 1e6:.1f} Mo, {v['tableaux']} tableaux, "
            f"identiques : {'oui' if v['identiques'] else 'NON'})"
            for v in vtu.values()
        ),
        f"CTL-013 sur le MED des charges : {loads['verdict']} "
        f"({len(loads['cas'])} champ(s), échecs : {loads['echecs'] or 'aucun'})",
        f"Synthèse : {len(found)} extremum(s) ; points : {len(points)} ligne(s) ; "
        f"enveloppes linéiques : {len(linear)} ligne(s)",
    ]
    from aster_expert.livrables.paraview import step_paraview  # noqa: PLC0415

    lines += step_paraview(ctx, data)
    if loads["verdict"] != "RÉUSSI":
        message = f"livrables : {lines[1]}"
        raise ProjectError(message)
    return lines


def shutil_copy(source: Path, target: Path) -> None:
    target.write_bytes(source.read_bytes())


__all__ = [
    "array_names",
    "control_loads",
    "equilibrium",
    "export_vtu",
    "extrema",
    "linear_envelopes",
    "manifest",
    "reading_points",
    "step_vues",
]
