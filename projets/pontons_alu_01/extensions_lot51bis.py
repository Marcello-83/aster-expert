"""Extensions of PONTONS-ALU-01 declared in `projet.yaml` from lot 51 bis on: a pier
type and three spans on pin bearings, variant chosen by PONTONS_VARIANTE (default H80C).
Same roles as `extensions_lot51`; the expected resultant of DEJ is 10 kN/m³ × the
volume of concrete as modelled (P49)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aster_expert.controles.tables import TableIndex
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.extensions_lot51 import tributary_areas
from pontons_alu_01.generation_lot51bis import applied_loads, build_comm, values
from pontons_alu_01.geometrie_lot51bis import Geometry51bis, geometry, params_json
from pontons_alu_01.variantes_lot51bis import current


def mesh_parameters(ctx: ProjectContext) -> bytes:  # noqa: ARG001 - signature des extensions
    """Parameter file of `maillage_palee_51bis.py` for the current variant."""
    return params_json(current().mesh_overrides)


def generate(
    ctx: ProjectContext,
    *,
    fiche_path: Path,  # noqa: ARG001 -- la fiche est lue par le tronc commun (bloqueurs)
    data_path: Path,  # noqa: ARG001
    med_path: Path,
    aster_version: str,
) -> tuple[str, dict[str, Any]]:
    text, report = build_comm(ctx, mesh_label=med_path.name)
    report["aster_version"] = aster_version
    out = ctx.results_dir / "generation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return text, report


def _geometry() -> Geometry51bis:
    return geometry(current().mesh_overrides)


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """CTL-013: the applied load of a case, from the data, the variant and the
    parameters (no load is a function: `as_evaluated` equals `specified`)."""
    loads = applied_loads(values(ctx, current()), _geometry())[case]
    return {"as_evaluated": dict(loads), "specified": dict(loads)}


def _tables(ctx: ProjectContext, mess_text: str) -> TableIndex:
    key = f"pontons51bis_tables_{id(mess_text)}"
    cached = ctx.cache.get(key)
    if not isinstance(cached, TableIndex):
        cached = TableIndex(mess_text)
        ctx.cache[key] = cached
    return cached


def _spring_terms(
    ctx: ProjectContext, mess_text: str, case: str
) -> list[dict[str, float]]:
    v = values(ctx, current())
    areas = tributary_areas(_geometry())
    stiffness = {"DX": v.kt, "DY": v.kt, "DZ": v.kn}
    terms = []
    for row in _tables(ctx, mess_text).find(f"DS_{case}"):
        key = (round(float(row["COOR_X"]), 6), round(float(row["COOR_Y"]), 6))
        area = areas[key]
        terms.append({c: stiffness[c] * area * float(row[c]) for c in stiffness})
    return terms


def spring_forces(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions de ressorts
) -> dict[str, dict[str, float]]:
    """Σ k·u of the soil springs under the footing (P19), k = k_sol × tributary area,
    u read in the listing (table DS_<case>)."""
    sums = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    for term in _spring_terms(ctx, mess_text, case):
        for c in sums:
            sums[c] += term[c]
    return {"SOL": sums}


def spring_scale(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions d'échelle
) -> dict[str, Any]:
    """Scale of a self-equilibrated (thermal) case: max over DX, DY, DZ of Σ |k·u| on
    the soil springs."""
    sums = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    for term in _spring_terms(ctx, mess_text, case):
        for c in sums:
            sums[c] += abs(term[c])
    return {
        "value_n": max(sums.values()),
        "definition": "max sur DX, DY, DZ de Σ |k·u| aux nœuds de la semelle "
        + ", ".join(f"{c} : {s:.6e} N" for c, s in sums.items()),
    }


__all__ = [
    "generate",
    "mesh_parameters",
    "resultant",
    "spring_forces",
    "spring_scale",
]
