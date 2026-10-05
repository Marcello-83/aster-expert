"""Extensions of ESTACADE-PIEUX-01 named by `projet.yaml` (lot 47): parameters of
the mesh, generator of the `.comm`, expected resultants of the load cases, forces of
the springs and the project's own level D products (resultant of every moving
position, double count of E2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aster_expert.controles.tables import TableIndex
from aster_expert.projet.context import ProjectContext
from estacade_pieux_01.charges_mobiles import all_cases
from estacade_pieux_01.discretisation import PRODUCTION_SIZE, JettyMesh
from estacade_pieux_01.donnees import ModelValues, model_values
from estacade_pieux_01.generation import (
    STATIC_CASES,
    Options,
    build_comm,
)

LEVEL_TOLERANCE = 1.0e-6
THRESHOLD = 1.0e-6


def reference_mesh(ctx: ProjectContext, size: float = PRODUCTION_SIZE) -> JettyMesh:
    """The production mesh (point U2): h = 0,05 m."""
    return JettyMesh(model_values(ctx), size)


def mesh_parameters(ctx: ProjectContext) -> bytes:
    return reference_mesh(ctx).parameters_bytes()


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


def pile_steel_volume(v: ModelValues) -> float:
    """Σ A·L of the piles (m3): every pile from the mid-plane node to the tip."""
    per_pile = sum(s.area * (s.z_top - s.z_bottom) for s in v.sections)
    return per_pile * len(v.piles())


def weights(v: ModelValues) -> dict[str, float]:
    """Self-weight terms (N), the cap beams counted whole (E2: double count)."""
    slab = v.gamma_concrete * v.length * v.width * v.thickness
    caps = v.gamma_concrete * len(v.x_files) * v.width * v.cap_width * v.cap_height
    overlap = v.gamma_concrete * v.cap_width * v.thickness * v.width
    return {
        "dalle_n": slab,
        "chevetres_n": caps,
        "pieux_n": v.gamma_steel * pile_steel_volume(v),
        "double_compte_par_chevetre_n": overlap,
        "double_compte_total_n": overlap * len(v.x_files),
    }


def applied_loads(v: ModelValues) -> dict[str, dict[str, float]]:
    """Applied resultant of each declared case (N), from the data only."""
    lane = v.length * (v.lane[1] - v.lane[0])
    sidewalks = v.length * (v.width - (v.lane[1] - v.lane[0]))
    w = weights(v)
    out = {
        "PP": {
            "DX": 0.0,
            "DY": 0.0,
            "DZ": -(w["dalle_n"] + w["chevetres_n"] + w["pieux_n"]),
        },
        "G2": {
            "DX": 0.0,
            "DY": 0.0,
            "DZ": -(
                v.g2_sidewalk * sidewalks
                + v.g2_lane * lane
                + 2.0 * v.g2_guard * v.length
            ),
        },
        "UDL": {"DX": 0.0, "DY": 0.0, "DZ": -v.udl * lane},
        "TR": {"DX": 0.0, "DY": 0.0, "DZ": -v.tr * sidewalks},
        "FR": {"DX": v.fr_total, "DY": 0.0, "DZ": 0.0},
        "TEP": {"DX": 0.0, "DY": 0.0, "DZ": 0.0},
        "TEM": {"DX": 0.0, "DY": 0.0, "DZ": 0.0},
    }
    for case in all_cases(v, PRODUCTION_SIZE):
        out[case.name] = {"DX": 0.0, "DY": 0.0, "DZ": -case.total}
    return out


def resultant(
    ctx: ProjectContext, case: str, **_inputs: Any
) -> dict[str, dict[str, float]]:
    """CTL-013: the applied load of a case, computed from the data (no load is
    evaluated through a function here, so `as_evaluated` equals `specified`)."""
    values = applied_loads(model_values(ctx))[case]
    return {"as_evaluated": dict(values), "specified": dict(values)}


def spring_stiffness_at(v: ModelValues, x: float, z: float) -> float:
    family = (
        "RIVE"
        if min(abs(x - v.x_files[0]), abs(x - v.x_files[-1])) < LEVEL_TOLERANCE
        else "EAU"
    )
    for s in v.springs:
        if s.family == family and abs(s.z - z) < LEVEL_TOLERANCE:
            return s.k
    message = f"aucun ressort {family} à la cote {z}"
    raise ValueError(message)


def spring_forces(
    ctx: ProjectContext,
    mess_text: str,
    case: str,
    *,
    comm_text: str,  # noqa: ARG001 - signature commune des extensions de ressorts
) -> dict[str, dict[str, float]]:
    """Σ k·u along DX and DY, per family (k of the data, u read in the listing)."""
    v = model_values(ctx)
    cached = ctx.cache.get("estacade_tables")
    if not isinstance(cached, TableIndex):
        cached = TableIndex(mess_text)
        ctx.cache["estacade_tables"] = cached
    out: dict[str, dict[str, float]] = {
        "RIVE": {"DX": 0.0, "DY": 0.0},
        "EAU": {"DX": 0.0, "DY": 0.0},
    }
    for row in cached.find(f"DR_{case}"):
        x, z = float(row["COOR_X"]), float(row["COOR_Z"])
        k = spring_stiffness_at(v, x, z)
        family = (
            "RIVE"
            if min(abs(x - v.x_files[0]), abs(x - v.x_files[-1])) < LEVEL_TOLERANCE
            else "EAU"
        )
        out[family]["DX"] += k * float(row["DX"])
        out[family]["DY"] += k * float(row["DY"])
    return out


def moving_resultants(v: ModelValues, mess_text: str, batches: int) -> dict[str, Any]:
    """Σ DZ of the tip reactions of every case of every batch, against the load."""
    tables = TableIndex(mess_text)
    expected = applied_loads(v)
    rows: dict[str, dict[str, Any]] = {}
    for i in range(1, batches + 1):
        for record in tables.find(f"RPIEDS_MB{i:02d}"):
            name = str(record["_head"]).split()[-1]
            applied = expected[name]["DZ"]
            reaction = float(record["DZ"])
            rows[name] = {
                "charge_dz_n": applied,
                "reaction_dz_n": reaction,
                "ecart_relatif": (applied + reaction) / abs(applied),
                "reactions_dx_dy_n": [float(record["DX"]), float(record["DY"])],
            }
    moving = [n for n in rows if n not in STATIC_CASES]
    worst = max((abs(rows[n]["ecart_relatif"]) for n in rows), default=float("nan"))
    return {
        "seuil": THRESHOLD,
        "cas": rows,
        "positions_mobiles": len(moving),
        "ecart_relatif_max": worst,
        "verdict": "RÉUSSI"
        if rows
        and len(moving) == len(all_cases(v, PRODUCTION_SIZE))
        and worst <= THRESHOLD
        else "ÉCHEC",
    }


def extra_controls(ctx: ProjectContext, run_dir: Path, out_dir: Path) -> list[Path]:
    v = model_values(ctx)
    mess = run_dir / "proc.0" / "fort.6"
    text = mess.read_text(encoding="utf-8", errors="replace")
    generation = json.loads(
        (ctx.results_dir / "generation.json").read_text(encoding="utf-8")
    )
    result = {
        "resultantes_toutes_positions": moving_resultants(
            v, text, len(generation["lots"])
        ),
        "double_compte_E2": weights(v),
        "options": Options().__dict__,
    }
    path = out_dir / "controles_projet.json"
    path.write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return [path]


__all__ = [
    "applied_loads",
    "extra_controls",
    "generate",
    "mesh_parameters",
    "reference_mesh",
    "resultant",
    "spring_forces",
    "weights",
]
