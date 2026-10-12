"""Extensions of PONTONS-ALU-01 declared in `projet.yaml` (lot 50)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aster_expert.controles.tables import TableIndex
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation import applied_loads, build_comm, values
from pontons_alu_01.geometrie import Geometry, geometry


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


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """CTL-013: the applied load of a case, from the data and the parameters (no load
    is a function, so `as_evaluated` equals `specified`)."""
    loads = applied_loads(values(ctx), geometry())[case]
    return {"as_evaluated": dict(loads), "specified": dict(loads)}


def tributary_areas(g: Geometry) -> dict[tuple[float, float], float]:
    """Area attached to each node of the footing grid: a quarter of each adjacent
    quadrangle, as RIGI_PARASOL distributes it (U4.42.01, Remarque 1)."""
    from pontons_alu_01.geometrie import footing_divisions  # noqa: PLC0415

    nx, ny = footing_divisions(g)

    def stations(bounds: tuple[float, ...], counts: list[int]) -> list[float]:
        out = [bounds[0]]
        for (a, b), n in zip(
            zip(bounds, bounds[1:], strict=False), counts, strict=False
        ):
            out += [a + (b - a) * k / n for k in range(1, n + 1)]
        return out

    xs, ys = stations(g.footing_x, nx), stations(g.footing_y, ny)

    def half_widths(s: list[float]) -> list[float]:
        return [
            ((s[i] - s[i - 1]) if i > 0 else 0.0) / 2.0
            + ((s[i + 1] - s[i]) if i + 1 < len(s) else 0.0) / 2.0
            for i in range(len(s))
        ]

    wx, wy = half_widths(xs), half_widths(ys)
    return {
        (round(x, 6), round(y, 6)): ax * ay
        for x, ax in zip(xs, wx, strict=False)
        for y, ay in zip(ys, wy, strict=False)
    }


def _tables(ctx: ProjectContext, mess_text: str) -> TableIndex:
    cached = ctx.cache.get("pontons_tables")
    if not isinstance(cached, TableIndex):
        cached = TableIndex(mess_text)
        ctx.cache["pontons_tables"] = cached
    return cached


def _spring_terms(
    ctx: ProjectContext, mess_text: str, case: str
) -> list[dict[str, float]]:
    v = values(ctx)
    areas = tributary_areas(geometry())
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
    """Scale of a self-equilibrated case (thermal, CTL-005 and CTL-013 version 2): max
    over DX, DY, DZ of Σ |k·u| on the soil springs."""
    sums = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    for term in _spring_terms(ctx, mess_text, case):
        for c in sums:
            sums[c] += abs(term[c])
    return {
        "value_n": max(sums.values()),
        "definition": "max sur DX, DY, DZ de Σ |k·u| aux nœuds de la semelle "
        + ", ".join(f"{c} : {s:.6e} N" for c, s in sums.items()),
    }


def deliverable_combinations(
    ctx: ProjectContext,  # noqa: ARG001 - signature des extensions de combinaisons
) -> list[dict[str, Any]]:
    """Lot 50 (`deliverables.combinations`): sets A (S2) and B (PRO), D5."""
    from pontons_alu_01.combinaisons import combinations  # noqa: PLC0415

    return [c.as_dict() for c in combinations(selected_set())]


def selected_set() -> str:
    """Set of combinations handed to the deliverables chain: `B` (PRO) by default,
    `A` or `AB` through the variable PONTONS_JEU (the summary envelopes one set at a
    time: the limit states of the trunk would mix the two)."""
    import os  # noqa: PLC0415

    value = os.environ.get("PONTONS_JEU", "B")
    if value not in {"A", "B", "AB"}:
        message = f"PONTONS_JEU = {value!r} : A, B ou AB attendu"
        raise ValueError(message)
    return value


__all__ = [
    "deliverable_combinations",
    "generate",
    "resultant",
    "spring_forces",
    "spring_scale",
    "tributary_areas",
]
