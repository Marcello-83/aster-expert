"""MED, `.vtu`, ParaView script and pictures that let the engineer check how the loads
of a model are applied (lot 50 quater).

Rule agreed with MM: every project delivers a verification MED of its load cases with
its ParaView script. The sub-step `charges` of `aster-expert projet <nom> livrables`
produces them from what the sub-steps `traiter` already wrote, with nothing run again:

- the nodal forces of each elementary case are those the solver sees (`FN_<case>`, plus
  `FV_<case>` for the forces of a command variable such as a temperature), read in the
  MED of loads of the post-processing run;
- the **intensity of the distributed load per element** (N/m, global components) comes
  from the production `.comm`, read by the static parser and never executed:
  `AFFE_CHAR_MECA/FORCE_POUTRE` (`TOUT` or `GROUP_MA`; `FX`, `FY`, `FZ`, `MX`, `MY`,
  `MZ` are linear forces and moments in the **global** frame, U4.44.01); the local
  components (`N`, `VY`, `VZ`, `MT`, `MFY`, `MFZ`, `MGX`, `MGY`, `MGZ`),
  `TYPE_CHARGE='VENT'`, `TOUT` and every other load keyword are **listed, never
  drawn** (`non_traite` in the manifest);
- the temperature difference per element (K) is `CREA_CHAMP/AFFE/VALE` minus
  `AFFE_MATERIAU/AFFE_VARC/VALE_REF`, on the groups of the `AFFE_VARC`
  (`NOM_VARC='TEMP'` with a `CHAM_GD`); gravity and `FORCE_NODALE` have nodal forces
  only.

Written in `resultats/livrables/charges/`: `charges.med` (container,
`scripts/livrables_charges.py`: fields `CHARGE_NODALE`, `CHARGE_REPARTIE`,
`ECART_TEMPERATURE`, one time step per case, numéro d'ordre = rank in the
manifest), one `.vtu` per case (a standard ParaView reads it without plugin),
`charges_paraview.py`, `png/`, `resultantes.csv`, `manifeste.json`.

MED limitation: a MED time step carries no name, so the identifier of a case lives in
the manifest (`pas`), in the names of the `.vtu` files and in the pipeline of the
script.
"""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import json
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.arrondis import format_value, load_table
from aster_expert.livrables.chaine import (
    deliverables_dir,
    load_deliverables_state,
    production,
)
from aster_expert.livrables.charges_modele import SCRIPT_TEMPLATE
from aster_expert.livrables.donnees import Deliverables, FloatArray, IntArray, Mesh
from aster_expert.livrables.inventaire import (
    NEUTRAL_KEYWORDS,
    Inventory,
    Solve,
    build_inventory,
    concepts,
    literal,
)
from aster_expert.livrables.vtu import (
    Grid,
    check_identical,
    grid_from_mesh,
    select_cells,
    vertices,
    write_vtu,
)
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.parsing.models import (
    CommFileAnalysis,
    FactorKeywordValue,
    KeywordNode,
    Statement,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

SEG2 = 1
"""Geometric type of a linear element in the MED file (medcoupling `NORM_SEG2`)."""
NODAL_COMPONENTS = ("FX", "FY", "FZ", "MX", "MY", "MZ")
MED_COMPONENTS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")
"""Components of the nodal fields of the post-processing MED (`FN_`, `FV_`)."""
DISTRIBUTED_COMPONENTS = NODAL_COMPONENTS
NATURES = ("répartie", "pesanteur", "ponctuelle", "température")
"""Nature of a case, by priority: the arrow scale is common to the cases of one
nature (lot 50 quater, consigne: « réparties, ponctuelles, pesanteur »)."""
OUT_NAME = "charges"
SCRIPT_NAME = "charges_paraview.py"
ARROW_FRACTION = 0.12
"""The longest arrow of a nature is this fraction of the size of the model."""
SUPPORT_FAMILIES = {
    "reactions": ("appuis_reactions", "appuis (réactions : {groups})"),
    "ressorts": ("appuis_ressorts", "ressorts ({groups})"),
}


@dataclass
class CaseLoads:
    """What the `.comm` declares for one elementary case."""

    name: str
    distributed: list[tuple[list[str], dict[str, float]]] = field(default_factory=list)
    """(`GROUP_MA` names, global components N/m or N·m/m) per `FORCE_POUTRE`."""
    points: list[tuple[list[str], dict[str, float]]] = field(default_factory=list)
    """(`GROUP_NO` names, components N or N·m) per `FORCE_NODALE` occurrence."""
    gravity: list[tuple[float, tuple[float, ...]]] = field(default_factory=list)
    temperature: list[tuple[list[str], float]] = field(default_factory=list)
    """(groups, ΔT in K) per temperature occurrence."""
    skipped: list[str] = field(default_factory=list)

    @property
    def nature(self) -> str:
        if self.distributed:
            return NATURES[0]
        if self.gravity:
            return NATURES[1]
        if self.points:
            return NATURES[2]
        if self.temperature:
            return NATURES[3]
        return "autre"


@dataclass
class CaseData:
    loads: CaseLoads
    nodal: FloatArray
    """(nodes, 6): FX FY FZ MX MY MZ, N and N·m (the sum of `FN_` and `FV_`)."""
    distributed: FloatArray
    """(linear cells, 6): N/m and N·m/m, zero where the cell is not loaded."""
    temperature: FloatArray
    """(linear cells): ΔT in K, zero where none."""
    expected: dict[str, float] | None = None
    expected_source: str = ""


# --- reading the `.comm` ------------------------------------------------------------


def _occurrences(st: Statement, key: str) -> list[dict[str, KeywordNode]]:
    node = st.keywords.get(key)
    if isinstance(node, FactorKeywordValue):
        return [o.keywords for o in node.occurrences]
    return []


def _names(node: KeywordNode | None) -> list[str]:
    value = literal(node)
    if value is None:
        return []
    items = value if isinstance(value, list | tuple) else [value]
    return [str(i) for i in items]


def _number(node: KeywordNode | None) -> float | None:
    value = literal(node)
    return float(value) if isinstance(value, int | float) else None


def _statements(analysis: CommFileAnalysis) -> dict[str, Statement]:
    return {
        s.assigned_concept: s
        for s in analysis.statements
        if s.assigned_concept and s.command != "DETRUIRE"
    }


def _distributed(st: Statement, loads: CaseLoads, label: str) -> None:
    for occ in _occurrences(st, "FORCE_POUTRE"):
        kind = literal(occ.get("TYPE_CHARGE")) or "FORCE"
        keys = sorted(k for k in occ if k not in ("TOUT", "GROUP_MA", "TYPE_CHARGE"))
        unsupported = [k for k in keys if k not in DISTRIBUTED_COMPONENTS]
        groups = _names(occ.get("GROUP_MA"))
        if kind != "FORCE" or unsupported or not groups:
            reason = (
                "TYPE_CHARGE=" + str(kind)
                if kind != "FORCE"
                else f"composantes locales {unsupported}"
                if unsupported
                else "TOUT (toutes les poutres du modèle)"
            )
            loads.skipped.append(f"{label}/FORCE_POUTRE : {reason}")
            continue
        values = {k: _number(occ[k]) for k in keys}
        if any(v is None for v in values.values()):
            loads.skipped.append(f"{label}/FORCE_POUTRE : valeur non littérale")
            continue
        loads.distributed.append(
            (groups, {k: float(v) for k, v in values.items() if v is not None})
        )


def _points(st: Statement, loads: CaseLoads, label: str) -> None:
    for occ in _occurrences(st, "FORCE_NODALE"):
        groups = _names(occ.get("GROUP_NO"))
        keys = sorted(k for k in occ if k != "GROUP_NO")
        values = {k: _number(occ[k]) for k in keys}
        if (
            not groups
            or any(k not in NODAL_COMPONENTS for k in keys)
            or any(v is None for v in values.values())
        ):
            loads.skipped.append(f"{label}/FORCE_NODALE : occurrence non lisible")
            continue
        loads.points.append(
            (groups, {k: float(v) for k, v in values.items() if v is not None})
        )


def _gravity(st: Statement, loads: CaseLoads, label: str) -> None:
    for occ in _occurrences(st, "PESANTEUR"):
        g = _number(occ.get("GRAVITE"))
        direction = literal(occ.get("DIRECTION"))
        if g is None or not isinstance(direction, list | tuple):
            loads.skipped.append(f"{label}/PESANTEUR : valeur non littérale")
            continue
        loads.gravity.append((g, tuple(float(v) for v in direction)))


def _temperature(
    solve: Solve,
    inventory: Inventory,
    statements: dict[str, Statement],
    loads: CaseLoads,
) -> None:
    for source in inventory.varc.get(solve.cham_mater, ()):
        label = f"AFFE_MATERIAU {solve.cham_mater}/AFFE_VARC"
        if source.nom_varc != "TEMP" or source.kind != "CHAM_GD":
            loads.skipped.append(f"{label} : {source.nom_varc}/{source.kind}")
            continue
        material = statements.get(solve.cham_mater)
        field_st = statements.get(source.concept)
        reference = None
        if material is not None:
            for occ in _occurrences(material, "AFFE_VARC"):
                if concepts(occ.get("CHAM_GD")) == [source.concept]:
                    reference = _number(occ.get("VALE_REF"))
        if field_st is None or field_st.command != "CREA_CHAMP" or reference is None:
            loads.skipped.append(f"{label} : champ {source.concept} non lisible")
            continue
        for occ in _occurrences(field_st, "AFFE"):
            value = _number(occ.get("VALE"))
            groups = _names(occ.get("GROUP_MA"))
            if value is None or not groups:
                loads.skipped.append(f"{label} : AFFE de {source.concept} non lisible")
                continue
            loads.temperature.append((groups, value - reference))


def read_case_loads(
    analysis: CommFileAnalysis,
    inventory: Inventory,
    excluded: set[str],
) -> list[CaseLoads]:
    """The loads of every elementary case of the `.comm` (cases in `excluded` -- moving
    load positions -- left out), in the order of the solves."""
    statements = _statements(analysis)
    out: list[CaseLoads] = []
    for solve, case in inventory.cases():
        if case.name in excluded:
            continue
        loads = CaseLoads(case.name)
        for charge in inventory.loads_of(case):
            st = statements.get(charge)
            if st is None:
                loads.skipped.append(f"{charge} : charge non définie dans le .comm")
                continue
            label = f"AFFE_CHAR_MECA {charge}"
            for key in st.keywords:
                if key in NEUTRAL_KEYWORDS | {
                    "FORCE_POUTRE",
                    "FORCE_NODALE",
                    "PESANTEUR",
                }:
                    continue
                loads.skipped.append(f"{label}/{key} : non dessiné")
            _distributed(st, loads, label)
            _points(st, loads, label)
            _gravity(st, loads, label)
        _temperature(solve, inventory, statements, loads)
        out.append(loads)
    return out


# --- arrays -------------------------------------------------------------------------


@dataclass
class LinearCells:
    level: int
    ids: IntArray
    """Cell numbers in their level, of the linear elements, in order."""
    vtk: IntArray
    """VTK cell index of each of them in `grid_from_mesh`."""
    lengths: FloatArray

    def positions(self, mesh: Mesh, group: str) -> IntArray:
        found = mesh.cell_group(group)
        if found is None:
            message = f"groupe de mailles {group} absent du maillage des livrables"
            raise ProjectError(message)
        level, ids = found
        if level != self.level:
            return np.zeros(0, dtype=np.int64)
        return np.flatnonzero(np.isin(self.ids, ids))


def linear_cells(mesh: Mesh) -> LinearCells:
    """The linear elements (SEG2) of the mesh, all on one level."""
    _, order = grid_from_mesh(mesh.arrays)
    index = {key: i for i, key in enumerate(order)}
    levels = sorted(int(k.split("_")[1]) for k in mesh.arrays if k.startswith("type_"))
    found = [
        (lev, np.flatnonzero(mesh.arrays[f"type_{lev}"] == SEG2)) for lev in levels
    ]
    found = [(lev, ids) for lev, ids in found if ids.size]
    if len(found) != 1:
        message = (
            "charges : les mailles linéiques (SEG2) doivent être sur un seul niveau du "
            f"maillage, trouvées sur {[lev for lev, _ in found]}"
        )
        raise ProjectError(message)
    level, ids = found[0]
    conn = mesh.arrays[f"conn_{level}"][ids]
    coords = mesh.coords
    lengths = np.linalg.norm(coords[conn[:, 1]] - coords[conn[:, 0]], axis=1)
    return LinearCells(
        level=level,
        ids=ids.astype(np.int64),
        vtk=np.array([index[(level, int(i))] for i in ids], dtype=np.int64),
        lengths=lengths,
    )


def nodal_forces(d: Deliverables, case: str, n_nodes: int) -> FloatArray | None:
    """`FN_<case>` plus `FV_<case>` of the MED of loads, (nodes, 6); None if neither."""
    total = None
    for name, values, kind, entity, components in d.loads():
        if name not in (f"FN_{case}", f"FV_{case}"):
            continue
        if components and tuple(components) != MED_COMPONENTS:
            message = f"charges : composantes de {name} inattendues : {components}"
            raise ProjectError(message)
        rows = values.reshape(len(kind), -1)
        full = np.zeros((n_nodes, rows.shape[1]))
        full[entity[kind == 0]] = rows[kind == 0]
        total = full if total is None else total + full
    return total


def build_case(loads: CaseLoads, d: Deliverables, cells: LinearCells) -> CaseData:
    mesh = d.mesh
    n_nodes = len(mesh.coords)
    nodal = nodal_forces(d, loads.name, n_nodes)
    if nodal is None:
        message = f"charges : aucun champ de forces nodales (FN_/FV_) pour {loads.name}"
        raise ProjectError(message)
    distributed = np.zeros((len(cells.ids), 6))
    expected = np.zeros(3)
    has_expected = bool(loads.distributed or loads.points)
    for groups, components in loads.distributed:
        for group in groups:
            positions = cells.positions(mesh, group)
            if not positions.size:
                message = f"charges : {group} ({loads.name}) sans maille linéique"
                raise ProjectError(message)
            for comp, value in components.items():
                k = NODAL_COMPONENTS.index(comp)
                distributed[positions, k] += value
                if k < 3:
                    expected[k] += value * float(cells.lengths[positions].sum())
    for groups, components in loads.points:
        for group in groups:
            count = len(mesh.node_group(group))
            for comp, value in components.items():
                k = NODAL_COMPONENTS.index(comp)
                if k < 3:
                    expected[k] += value * count
    temperature = np.zeros(len(cells.ids))
    for groups, delta in loads.temperature:
        for group in groups:
            positions = cells.positions(mesh, group)
            temperature[positions] = delta
    data = CaseData(loads, nodal, distributed, temperature)
    if has_expected and not loads.gravity and not loads.skipped:
        data.expected = dict(zip(("FX", "FY", "FZ"), expected.tolist(), strict=True))
        data.expected_source = (
            "intégrale des charges déclarées dans le .comm (intensité × longueur, "
            "forces ponctuelles)"
        )
    return data


def case_summary(data: CaseData) -> dict[str, Any]:
    sums = data.nodal.sum(axis=0)
    norm = np.linalg.norm(data.nodal[:, :3], axis=1)
    intensity = np.linalg.norm(data.distributed[:, :3], axis=1)
    return {
        "nature": data.loads.nature,
        "somme_n": dict(zip(NODAL_COMPONENTS, (float(v) for v in sums), strict=True)),
        "max_noeud_kN": float(norm.max()) * 1.0e-3 if norm.size else 0.0,
        "max_repartie_kN_m": float(intensity.max()) * 1.0e-3 if intensity.size else 0.0,
        "mailles_chargees": int((intensity > 0).sum()),
        "ecart_temperature_k": [
            float(data.temperature.min()),
            float(data.temperature.max()),
        ],
        "non_traite": list(data.loads.skipped),
    }


# --- MED, VTU ------------------------------------------------------------------------


def write_med(
    ctx: ProjectContext,
    out: Path,
    source: Path,
    cases: list[CaseData],
    cells: LinearCells,
) -> dict[str, Any]:
    """`charges.med` of the container (see `scripts/livrables_charges.py`)."""
    from aster_expert.livrables.conteneur import (  # noqa: PLC0415
        SCRIPT_CHARGES,
        ContainerError,
        run_deliverables_container,
    )

    work_in = out / "_entree"
    work_in.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, Any] = {
        "ordre": np.array([c.loads.name for c in cases]),
        "cellules": cells.ids,
    }
    for c in cases:
        arrays[f"nodal/{c.loads.name}"] = c.nodal
        if c.loads.distributed:
            arrays[f"repartie/{c.loads.name}"] = c.distributed
        if c.loads.temperature:
            arrays[f"temperature/{c.loads.name}"] = c.temperature
    npz = work_in / "entree.npz"
    np.savez(npz, **arrays)
    spec = {
        "niveau_mailles_lineiques": cells.level,
        "composantes_nodales": list(NODAL_COMPONENTS),
        "composantes_reparties": list(DISTRIBUTED_COMPONENTS),
    }
    try:
        work = run_deliverables_container(
            {"source.med": source, "entree.npz": npz},
            spec,
            project_root=ctx.repo_root,
            work_root=ctx.repo_root / "data" / "processed" / "livrables",
            script=SCRIPT_CHARGES,
        )
    except (ContainerError, OSError) as exc:
        raise ProjectError(str(exc)) from exc
    finally:
        shutil.rmtree(work_in, ignore_errors=True)
    shutil.move(str(work / "charges.med"), str(out / "charges.med"))
    report: dict[str, Any] = json.loads((work / "out.json").read_text("utf-8"))
    return report


def _norm_or_nan(values: FloatArray) -> FloatArray:
    norm = np.linalg.norm(values, axis=1)
    return np.where(norm > 0.0, norm, np.nan)


def write_vtus(
    d: Deliverables,
    out: Path,
    cases: list[CaseData],
    cells: LinearCells,
    support_groups: dict[str, list[str]],
) -> dict[str, Any]:
    """The `.vtu` of the script: the model, one file per case, the supports. Each file
    is read back and compared with what was written."""
    base, _ = grid_from_mesh(d.mesh.arrays)
    report: dict[str, Any] = {}

    def save(name: str, grid: Grid) -> None:
        path = out / name
        write_vtu(path, grid)
        report[name] = {"octets": path.stat().st_size, **check_identical(grid, path)}
        if not report[name]["identiques"]:
            message = f"charges : {name} relu différent de ce qui a été écrit"
            raise ProjectError(message)

    save("modele.vtu", Grid(base.points, base.connectivity, base.offsets, base.types))
    for c in cases:
        grid = select_cells(base, cells.vtk)
        for k, comp in enumerate(NODAL_COMPONENTS):
            grid.point_data[f"CHARGE_NODALE_{comp}"] = c.nodal[:, k]
        for k, comp in enumerate(DISTRIBUTED_COMPONENTS):
            grid.cell_data[f"CHARGE_REPARTIE_{comp}"] = c.distributed[:, k]
        grid.cell_data["INTENSITE_REPARTIE_kN_m"] = (
            _norm_or_nan(c.distributed[:, :3]) * 1.0e-3
        )
        grid.cell_data["ECART_TEMPERATURE_K"] = np.where(
            c.temperature != 0.0, c.temperature, np.nan
        )
        save(f"{OUT_NAME}_{c.loads.name}.vtu", grid)
    for family, groups in support_groups.items():
        found = [d.mesh.node_group(g) for g in groups]
        nodes = np.unique(np.concatenate(found or [np.zeros(0, dtype=np.int64)]))
        save(f"{SUPPORT_FAMILIES[family][0]}.vtu", vertices(base.points, nodes))
    return report


# --- checks -------------------------------------------------------------------------


def resultants(
    ctx: ProjectContext, d: Deliverables, cases: list[CaseData]
) -> list[dict[str, Any]]:
    """Sum of the nodal forces of the MED against the expected resultant of each
    mechanical case: the integral of the loads declared in the `.comm` where it can be
    computed, else the resultant declared by the project (`controls.cases`, CTL-013)."""
    from aster_expert.livrables.vues import control_loads  # noqa: PLC0415

    controls = ctx.declaration.controls
    threshold = controls.threshold if controls else 1.0e-6
    declared = control_loads(ctx, d)["cas"]
    rows = []
    for c in cases:
        sums = c.nodal.sum(axis=0)
        row: dict[str, Any] = {
            "cas": c.loads.name,
            "nature": c.loads.nature,
            "mesure_n": [float(v) for v in sums[:3]],
        }
        expected, source = c.expected, c.expected_source
        if expected is None:
            entry = declared.get(c.loads.name, {})
            if "attendu_tel_qu_evalue_n" in entry:
                values = entry["attendu_tel_qu_evalue_n"]
                expected = {"FX": values["DX"], "FY": values["DY"], "FZ": values["DZ"]}
                source = "résultante déclarée par le projet (controls.cases, CTL-013)"
        if c.loads.nature == NATURES[3]:
            total = float(np.abs(c.nodal[:, :3]).sum())
            gap = float(np.abs(sums[:3]).max())
            row.update(
                attendu_n=None,
                source="forces de la dilatation : somme nulle (autoéquilibre)",
                ecart_relatif=gap / total if total else math.nan,
                verdict="INFORMATIF",
            )
        elif expected is None:
            row.update(
                attendu_n=None,
                source="aucune résultante attendue calculable",
                ecart_relatif=math.nan,
                verdict="SANS RÉSULTANTE ATTENDUE",
            )
        else:
            want = np.array([expected["FX"], expected["FY"], expected["FZ"]])
            scale = float(np.abs(want).max()) or 1.0
            gap = float(np.abs(sums[:3] - want).max()) / scale
            row.update(
                attendu_n=[float(v) for v in want],
                source=source,
                ecart_relatif=gap,
                verdict="RÉUSSI" if gap <= threshold else "ÉCHEC",
            )
        row["seuil"] = threshold
        rows.append(row)
    return rows


def write_resultants_csv(
    ctx: ProjectContext, path: Path, rows: list[dict[str, Any]]
) -> None:
    table = load_table(ctx.repo_root)

    def kn(value: float) -> str:
        return format_value(value * 1.0e-3, "kN", table)

    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            "# Somme des forces nodales du MED (charges.med) et résultante attendue, "
            "repère global, kN (arrondi de la table config/arrondis.yaml ; l'écart "
            "relatif porte sur les valeurs non arrondies).\n"
        )
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(
            [
                "cas",
                "nature",
                "SFX_kN",
                "SFY_kN",
                "SFZ_kN",
                "attendu_FX_kN",
                "attendu_FY_kN",
                "attendu_FZ_kN",
                "ecart_relatif",
                "seuil",
                "verdict",
                "source_attendu",
            ]  # fmt: skip
        )
        for r in rows:
            wanted = r["attendu_n"] or [None, None, None]
            writer.writerow(
                [
                    r["cas"],
                    r["nature"],
                    *(kn(v) for v in r["mesure_n"]),
                    *("" if v is None else kn(v) for v in wanted),
                    ""
                    if math.isnan(r["ecart_relatif"])
                    else f"{r['ecart_relatif']:.2e}",
                    f"{r['seuil']:.0e}",
                    r["verdict"],
                    r["source"],
                ]
            )


# --- ParaView script -----------------------------------------------------------------


def _title(ctx: ProjectContext, data: CaseData) -> str:
    table = load_table(ctx.repo_root)
    sums = data.nodal.sum(axis=0)
    parts = [
        f"Σ{c} = {format_value(float(v) * 1.0e-3, 'kN', table, decimal_comma=True)} kN"
        for c, v in zip(("FX", "FY", "FZ"), sums[:3], strict=True)
    ]
    return f"{data.loads.name} - charge {data.loads.nature} - " + " ; ".join(parts)


def scales(cases: list[CaseData], size: float) -> dict[str, dict[str, float]]:
    """Per nature: the largest nodal force (kN), the length in metres of an arrow of
    1 kN (the longest arrow is `ARROW_FRACTION` of the model), the largest intensity
    (kN/m)."""
    out: dict[str, dict[str, float]] = {}
    for nature in sorted({c.loads.nature for c in cases}):
        mine = [c for c in cases if c.loads.nature == nature]
        biggest = max(
            float(np.linalg.norm(c.nodal[:, :3], axis=1).max()) * 1.0e-3 for c in mine
        )
        intensity = max(
            (float(np.linalg.norm(c.distributed[:, :3], axis=1).max()) * 1.0e-3)
            for c in mine
        )
        out[nature] = {
            "max_kN": biggest,
            "m_par_kN": ARROW_FRACTION * size / biggest if biggest > 0 else 1.0,
            "max_repartie_kN_m": intensity,
        }
    return out


def build_manifest(
    ctx: ProjectContext,
    d: Deliverables,
    cases: list[CaseData],
    support_groups: dict[str, list[str]],
    plan_views: tuple[str, ...],
) -> dict[str, Any]:
    coords = d.mesh.coords
    size = float(np.linalg.norm(coords.max(axis=0) - coords.min(axis=0)))
    shown = list(cases)
    return {
        "projet": ctx.declaration.name,
        "taille_du_modele_m": size,
        "centre": [float(v) for v in (coords.max(axis=0) + coords.min(axis=0)) / 2],
        "echelles": scales(shown, size),
        "cas_en_plan": [c for c in plan_views if c in {x.loads.name for x in shown}],
        "appuis": [
            {
                "fichier": f"{SUPPORT_FAMILIES[f][0]}.vtu",
                "famille": f,
                "legende": SUPPORT_FAMILIES[f][1].format(groups=", ".join(g)),
            }
            for f, g in support_groups.items()
        ],
        "cas": [
            {
                "rang": i,
                "nom": c.loads.name,
                "fichier": f"{OUT_NAME}_{c.loads.name}.vtu",
                "titre": _title(ctx, c),
                **case_summary(c),
            }
            for i, c in enumerate(shown, 1)
        ],
    }


def write_script(manifest: dict[str, Any], out: Path) -> Path:
    """`charges_paraview.py`: the template with its parameters and the manifest."""
    text = (
        SCRIPT_TEMPLATE.replace("@@PROJET@@", manifest["projet"])
        .replace("@@PREMIER_CAS@@", manifest["cas"][0]["nom"])
        .replace("@@CAS_EN_PLAN@@", repr(tuple(manifest["cas_en_plan"])))
        .replace(
            "@@MANIFESTE@@",
            json.dumps(manifest, indent=1, ensure_ascii=False),
        )
    )
    path = out / SCRIPT_NAME
    path.write_text(text, encoding="utf-8")
    compile(text, str(path), "exec")
    return path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --- the sub-step -------------------------------------------------------------------


def support_groups_of(ctx: ProjectContext, d: Deliverables) -> dict[str, list[str]]:
    section = ctx.declaration.deliverables
    assert section is not None
    out: dict[str, list[str]] = {}
    for info in d.field_infos(section.fields):
        if info.family == "reactions" and info.node_groups:
            out["reactions"] = list(info.node_groups)
        elif info.family == "ressorts" and info.groups:
            out["ressorts"] = list(info.groups)
    return out


def step_charges(ctx: ProjectContext, rt: object = None) -> list[str]:  # noqa: ARG001
    """Sub-step `charges` (see the module docstring)."""
    from aster_expert.livrables.paraview import render_png  # noqa: PLC0415

    state = load_deliverables_state(ctx)
    root = deliverables_dir(ctx)
    source = root / "med" / "charges.med"
    if not state.outputs or not source.is_file():
        message = "charges : étape traiter d'abord (MED des charges absent)"
        raise ProjectError(message)
    section = ctx.declaration.deliverables
    assert section is not None
    d = Deliverables(root)
    prod = production(ctx)
    analysis = parse_comm_source(prod.text, file_path=str(prod.comm))
    inventory = build_inventory(
        analysis,
        static_results=section.static_results,
        ignored=[i.result for i in section.ignored_results],
    )
    mobile = {
        case.name
        for _solve, case in inventory.cases()
        if any(fnmatch.fnmatchcase(case.name, p) for p in section.moving_cases)
    }
    loads = read_case_loads(analysis, inventory, mobile)
    cells = linear_cells(d.mesh)
    cases = [build_case(item, d, cells) for item in loads]
    out = root / OUT_NAME
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    med_report = write_med(ctx, out, source, cases, cells)
    groups = support_groups_of(ctx, d)
    vtu_report = write_vtus(d, out, cases, cells, groups)
    manifest = build_manifest(ctx, d, cases, groups, section.load_plan_views)
    manifest["pas_du_med"] = {
        nom: pas
        for champ in med_report["champs"].values()
        for nom, pas in champ["pas"].items()
    }
    manifest["med"] = med_report
    manifest["vtu"] = vtu_report
    rows = resultants(ctx, d, cases)
    manifest["resultantes"] = rows
    write_resultants_csv(ctx, out / "resultantes.csv", rows)
    script = write_script(manifest, out)
    (out / "manifeste.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        f"MED des charges : {len(cases)} cas, champs {sorted(med_report['champs'])}, "
        f"relecture {med_report['relecture']['valeurs_comparees']} valeurs, "
        f"{med_report['relecture']['pas_en_ecart']} pas en écart",
        f"{len(vtu_report)} fichier(s) .vtu relus à l'identique ; script {script.name}",
    ]
    if not _no_png():
        made = render_png(ctx, script, out / "png")
        lines.append(f"{len(made)} image(s) PNG rendues avec le script livré")
    failed = [r["cas"] for r in rows if r["verdict"] == "ÉCHEC"]
    lines.append(
        "résultantes : "
        + (
            "ÉCHEC pour " + ", ".join(failed)
            if failed
            else "aucun écart au-delà du seuil"
        )
    )
    return lines


README = """\
Contrôle des charges de {projet} dans ParaView. Windows : ParaView 5.10 ou plus récent.
1. Copier ce dossier entier : le script et les .vtu doivent rester côte à côte.
2. ParaView > View > Python Shell > Run Script > charges_paraview.py : {premier} s'affiche.
3. Autre cas : dans le Python Shell, afficher_cas("<cas>") ; cas : {cas}.
4. Ou l'oeil des objets « Cas <nom> » et « Forces nodales : <nom> » du pipeline.
5. Paramètres en tête du script : CAS_AFFICHE, FACTEUR_ECHELLE (m par kN), SOUS_ECHANTILLONNAGE.
6. charges.med = mêmes champs que les .vtu, un pas par cas (« pas » de manifeste.json) ; MEDReader.
7. Fichiers en N, N·m, N/m, K ; légendes en kN et kN/m ; repère global, Z vers le haut.
8. resultantes.csv : somme des forces nodales du MED contre l'intégrale des charges.
9. png/ : rendu par ce même script (pvbatch charges_paraview.py --png <dossier>) ; sha256sum -c empreintes.sha256
"""  # noqa: E501


def deposit(ctx: ProjectContext, destination: Path) -> list[str]:
    """Copy the deliverables of `charges` to `destination` (the exchange folder), with
    `LISEZMOI.txt` (ten lines at most) and `empreintes.sha256`."""
    source = deliverables_dir(ctx) / OUT_NAME
    manifest_path = source / "manifeste.json"
    if not manifest_path.is_file():
        message = "charges : livrables absents (sous-étape charges d'abord)"
        raise ProjectError(message)
    manifest = json.loads(manifest_path.read_text("utf-8"))
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix == ".log":
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append(target)
    names = [c["nom"] for c in manifest["cas"]]
    readme = destination / "LISEZMOI.txt"
    readme.write_text(
        README.format(
            projet=manifest["projet"], premier=names[0], cas=", ".join(names)
        ),
        encoding="utf-8",
    )
    copied.append(readme)
    fingerprints = destination / "empreintes.sha256"
    fingerprints.write_text(
        "".join(
            f"{sha256_of(p)}  {p.relative_to(destination).as_posix()}\n"
            for p in sorted(copied)
        ),
        encoding="utf-8",
    )
    return [str(p.relative_to(destination)) for p in sorted(copied)]


def _no_png() -> bool:
    import os  # noqa: PLC0415

    return bool(os.environ.get("ASTER_EXPERT_LIVRABLES_SANS_PNG"))


__all__ = [
    "SCRIPT_NAME",
    "CaseData",
    "CaseLoads",
    "LinearCells",
    "build_case",
    "build_manifest",
    "deposit",
    "linear_cells",
    "read_case_loads",
    "resultants",
    "step_charges",
    "write_script",
    "write_vtus",
]
