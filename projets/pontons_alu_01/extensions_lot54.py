"""Extensions of PONTONS-ALU-01 declared in `projet.yaml` from lot 54 on: the final PRO
geometry of the whole pontoon (P67, P68), variant chosen by PONTONS_VARIANTE (default
B54, `variantes_lot54.yaml`). Same roles as `extensions_lot52`, whose helpers they call
on the geometry and the values of lot 54."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.extensions_lot52 import (
    _tables,
    scale_of_spring_terms,
    spring_terms_of,
    sum_spring_terms,
)
from pontons_alu_01.generation_lot51ter import applied_loads
from pontons_alu_01.generation_lot54 import build_comm, geometry_of, values
from pontons_alu_01.geometrie_lot54 import params_json
from pontons_alu_01.variantes_lot54 import current


def mesh_parameters(ctx: ProjectContext) -> bytes:  # noqa: ARG001 - signature des extensions
    """Parameter file of `maillage_ponton_52.py` for the current variant of lot 54."""
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


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """CTL-013: the applied load of a case, from the data, the variant and the
    parameters (no load is a function: `as_evaluated` equals `specified`)."""
    v = current()
    loads = applied_loads(values(ctx, v), geometry_of(v))[case]
    return {"as_evaluated": dict(loads), "specified": dict(loads)}


def _terms(ctx: ProjectContext, mess_text: str, case: str) -> list[dict[str, float]]:
    v = current()
    return spring_terms_of(
        geometry_of(v), values(ctx, v), _tables(ctx, mess_text), case
    )


def spring_forces(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions de ressorts
) -> dict[str, dict[str, float]]:
    """Σ k·u of the soil springs under the five footings (P19, P71), k = k_sol ×
    tributary area, u read in the listing (table S<case>)."""
    return sum_spring_terms(_terms(ctx, mess_text, case))


def spring_scale(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions d'échelle
) -> dict[str, Any]:
    """Scale of a self-equilibrated (thermal) case: max over DX, DY, DZ of Σ |k·u| on
    the soil springs of the five footings."""
    return scale_of_spring_terms(_terms(ctx, mess_text, case))


__all__ = [
    "generate",
    "mesh_parameters",
    "resultant",
    "spring_forces",
    "spring_scale",
]
