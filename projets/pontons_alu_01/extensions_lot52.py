"""Extensions of PONTONS-ALU-01 declared in `projet.yaml` from lot 52 on: the PRO
geometry of the whole pontoon (P62 to P66), variant chosen by PONTONS_VARIANTE (default
B52, `variantes_lot52.yaml`). Same roles as `extensions_lot51ter`, on the geometry and
the values of lot 52."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aster_expert.controles.tables import TableIndex
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation_lot51ter import Values51ter, applied_loads
from pontons_alu_01.generation_lot52 import build_comm, values
from pontons_alu_01.geometrie_lot51ter import Geometry51ter, tributary_areas
from pontons_alu_01.geometrie_lot52 import geometry, params_json
from pontons_alu_01.variantes_lot52 import current


def mesh_parameters(ctx: ProjectContext) -> bytes:  # noqa: ARG001 - signature des extensions
    """Parameter file of `maillage_ponton_52.py` for the current variant."""
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


def _geometry() -> Geometry51ter:
    return geometry(current().mesh_overrides)


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """CTL-013: the applied load of a case, from the data, the variant and the
    parameters (no load is a function: `as_evaluated` equals `specified`)."""
    loads = applied_loads(values(ctx, current()), _geometry())[case]
    return {"as_evaluated": dict(loads), "specified": dict(loads)}


def _tables(ctx: ProjectContext, mess_text: str) -> TableIndex:
    """The tables of a listing, read once per listing (lot 54 shares the cache)."""
    key = f"pontons52_tables_{id(mess_text)}"
    cached = ctx.cache.get(key)
    if not isinstance(cached, TableIndex):
        cached = TableIndex(mess_text)
        ctx.cache[key] = cached
    return cached


def spring_terms_of(
    g: Geometry51ter, v: Values51ter, tables: TableIndex, case: str
) -> list[dict[str, float]]:
    """k·u of every footing node of `case` (lot 54 passes its geometry and values)."""
    areas = tributary_areas(g)
    stiffness = {"DX": v.kt, "DY": v.kt, "DZ": v.kn}
    terms = []
    rows = tables.find(f"S{case}")
    if len(rows) != len(areas):
        message = f"S{case} : {len(rows)} nœuds de semelle, {len(areas)} attendus"
        raise ValueError(message)
    for row in rows:
        key = (round(float(row["COOR_X"]), 6), round(float(row["COOR_Y"]), 6))
        _, area = areas[key]
        terms.append({c: stiffness[c] * area * float(row[c]) for c in stiffness})
    return terms


def _spring_terms(
    ctx: ProjectContext, mess_text: str, case: str
) -> list[dict[str, float]]:
    return spring_terms_of(
        _geometry(), values(ctx, current()), _tables(ctx, mess_text), case
    )


def sum_spring_terms(terms: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    sums = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    for term in terms:
        for c in sums:
            sums[c] += term[c]
    return {"SOL": sums}


def scale_of_spring_terms(terms: list[dict[str, float]]) -> dict[str, Any]:
    sums = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    for term in terms:
        for c in sums:
            sums[c] += abs(term[c])
    return {
        "value_n": max(sums.values()),
        "definition": "max sur DX, DY, DZ de Σ |k·u| aux nœuds des cinq semelles "
        + ", ".join(f"{c} : {s:.6e} N" for c, s in sums.items()),
    }


def spring_forces(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions de ressorts
) -> dict[str, dict[str, float]]:
    """Σ k·u of the soil springs under the five footings (P19), k = k_sol × tributary
    area, u read in the listing (table S<case>)."""
    return sum_spring_terms(_spring_terms(ctx, mess_text, case))


def spring_scale(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions d'échelle
) -> dict[str, Any]:
    """Scale of a self-equilibrated (thermal) case: max over DX, DY, DZ of Σ |k·u| on
    the soil springs of the five footings."""
    return scale_of_spring_terms(_spring_terms(ctx, mess_text, case))


__all__ = [
    "generate",
    "scale_of_spring_terms",
    "spring_terms_of",
    "sum_spring_terms",
    "mesh_parameters",
    "resultant",
    "spring_forces",
    "spring_scale",
]
