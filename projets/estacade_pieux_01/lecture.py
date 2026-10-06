"""Reading of the results of the jetty (lot 47): every step of the MED of a run,
extracted by `medcoupling` in the container (`scripts/med_results_dump.py`, mode
`extract_steps`), then arranged by load case on the host.

The MED holds, for each batch result `MBnn` and each thermal result `TEP`, `TEM`:
`DEPL` (DX, DY, DZ, every node), `EFGE_NOEU` of the slab (profile of the slab nodes:
NXX, NYY, MXX, MYY, MXY, QX, QY) and `EFGE_ELNO` of the beams (one row per element end
of the SEG2 level: N, VY, VZ, MT, MFY, MFZ). A batch result has one step per case, in
the order of `CAS_CHARGE` (CA-055), which is the order of `generation.json`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.projet.context import ProjectContext
from aster_expert.report.med_read import med_field_name, run_med_script, take_arrays

SLAB_COMPONENTS = ("NXX", "NYY", "MXX", "MYY", "MXY", "QX", "QY")
BEAM_COMPONENTS = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
FloatArray = np.ndarray[Any, np.dtype[np.float64]]
IntArray = np.ndarray[Any, np.dtype[np.int64]]
Runner = Callable[..., dict[str, Any]]


@dataclass
class Results:
    coords: FloatArray
    slab_nodes: IntArray
    """MED node indices of the slab profile (rows of `slab`)."""
    beam_cells: IntArray
    """SEG2 cell indices (level -1) of the beam rows, two rows per cell."""
    beam_nodes: IntArray
    """(2 * n_cells,) node of each beam row (element end)."""
    groups: dict[str, Any]
    slab: dict[str, FloatArray] = field(default_factory=dict)
    depl: dict[str, FloatArray] = field(default_factory=dict)
    beams: dict[str, FloatArray] = field(default_factory=dict)

    def cases(self) -> list[str]:
        return list(self.slab)

    def cell_group(self, name: str) -> set[int]:
        return set(self.groups["cell"]["-1"][name])

    def beam_rows(self, group: str) -> IntArray:
        """Rows of the beam arrays that belong to the cells of a SEG2 group."""
        cells = self.cell_group(group)
        mask = np.array([int(c) in cells for c in np.repeat(self.beam_cells, 2)])
        rows: IntArray = np.nonzero(mask)[0].astype(np.int64)
        return rows

    def row_cell(self) -> IntArray:
        return np.repeat(self.beam_cells, 2).astype(np.int64)


def _conn(arrays: dict[str, Any], level: int) -> IntArray:
    out: IntArray = np.asarray(arrays[f"conn_{level}"], dtype=np.int64)
    return out


def load_results(
    med: Path,
    batches: list[tuple[str, list[str]]],
    *,
    runner: Runner = run_med_script,
    memory_mb: int = 12288,
) -> Results:
    """Every case of `batches` [(MED result name, [case names in order])]."""
    names = [
        med_field_name(result, quantity)
        for result, _ in batches
        for quantity in ("DEPL", "EFGE_NOEU", "EFGE_ELNO")
    ]
    payload = runner(
        med, ["extract_steps", *names], memory_mb=memory_mb, timeout_seconds=7200
    )
    arrays = take_arrays(payload)
    first = batches[0][0]
    efge = med_field_name(first, "EFGE_NOEU")
    elno = med_field_name(first, "EFGE_ELNO") + "@-1"
    comps = payload["fields"][efge]["components"]
    if tuple(comps) != SLAB_COMPONENTS:
        message = f"composantes de EFGE_NOEU inattendues : {comps}"
        raise ValueError(message)
    cells = np.asarray(arrays[f"{elno}#cells"], dtype=np.int64)
    conn = _conn(arrays, -1)
    beam_nodes = np.asarray(conn[cells][:, :2].reshape(-1), dtype=np.int64)
    results = Results(
        coords=np.asarray(arrays["coords"], dtype=np.float64),
        slab_nodes=np.asarray(arrays[f"{efge}#nodes"], dtype=np.int64),
        beam_cells=cells,
        beam_nodes=beam_nodes,
        groups=payload["groups"],
    )
    for result, cases in batches:
        depl = arrays[med_field_name(result, "DEPL")]
        slab = arrays[med_field_name(result, "EFGE_NOEU")]
        beams = arrays[med_field_name(result, "EFGE_ELNO") + "@-1"]
        if not (len(depl) == len(slab) == len(beams) == len(cases)):
            message = f"{result} : {len(depl)} pas pour {len(cases)} cas"
            raise ValueError(message)
        if not np.array_equal(
            arrays[f"{med_field_name(result, 'EFGE_NOEU')}#nodes"], results.slab_nodes
        ):
            message = f"{result} : profil de la dalle différent du premier résultat"
            raise ValueError(message)
        depl_nodes = arrays.get(f"{med_field_name(result, 'DEPL')}#nodes")
        n_nodes = len(results.coords)
        for i, case in enumerate(cases):
            full = np.asarray(depl[i], dtype=np.float64)
            if depl_nodes is not None:
                # Profil : la ligne j porte le nœud depl_nodes[j].
                placed = np.full((n_nodes, full.shape[1]), np.nan)
                placed[np.asarray(depl_nodes, dtype=np.int64)] = full
                full = placed
            results.depl[case] = full
            results.slab[case] = np.asarray(slab[i], dtype=np.float64)
            results.beams[case] = np.asarray(beams[i], dtype=np.float64)
    return results


def run_med(run_dir: Path) -> Path:
    """MED of the results of a run: the `.rmed` copied by the `.export`, else the
    unit 80 of the execution directory (`proc.0/fort.80`)."""
    copied = sorted(run_dir.glob("*.rmed"))
    if copied:
        return copied[0]
    unit = run_dir / "proc.0" / "fort.80"
    if not unit.is_file():
        message = f"aucun MED de résultats dans {run_dir}"
        raise FileNotFoundError(message)
    return unit


def run_batches(generation: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """(MED result, cases) of a run, from the generator's report."""
    out = [(lot["resultat"], list(lot["cas"])) for lot in generation["lots"]]
    out.extend((name, [name]) for name in generation.get("cas_thermiques", []))
    return out


def slab_xy(results: Results) -> tuple[FloatArray, FloatArray]:
    xyz = results.coords[results.slab_nodes]
    return xyz[:, 0], xyz[:, 1]


def comp(name: str) -> int:
    return SLAB_COMPONENTS.index(name)


def bcomp(name: str) -> int:
    return BEAM_COMPONENTS.index(name)


def read_convergence(ctx: ProjectContext, runs: dict[str, Path]) -> dict[str, Any]:
    """Quantities of the criterion of docs/essais_lot47.md § 2.7, per mesh, and the
    verdict (decreasing successive gap, production gap <= 2 %)."""
    import json  # noqa: PLC0415

    from estacade_pieux_01.donnees import model_values  # noqa: PLC0415

    v = model_values(ctx)
    file2 = v.x_files[1]
    half = v.cap_width / 2.0
    per_mesh: dict[str, dict[str, float]] = {}
    for label, run_dir in runs.items():
        stem = f"conv_{label}"
        generation = json.loads(
            (
                ctx.results_dir / "convergence" / label / f"{stem}.generation.json"
            ).read_text(encoding="utf-8")
        )
        med = run_med(run_dir)
        results = load_results(med, run_batches(generation))
        x, _ = slab_xy(results)
        travee = results.slab["TSA_M15"]
        appui = results.slab["TSA_M20"]
        dz_slab = {
            c: results.depl[c][results.slab_nodes, 2] for c in ("TSA_M15", "TSA_M20")
        }
        near = np.abs(x - file2) <= half + 1e-9
        per_mesh[label] = {
            "travee_max_moins_MXX": float(np.max(-travee[:, comp("MXX")])),
            "travee_max_abs_QX": float(np.max(np.abs(travee[:, comp("QX")]))),
            "travee_max_abs_DZ": float(np.max(np.abs(dz_slab["TSA_M15"]))),
            "appui_max_MXX_file2": float(np.max(appui[near, comp("MXX")])),
            "appui_max_abs_QX": float(np.max(np.abs(appui[:, comp("QX")]))),
            "appui_max_abs_DZ": float(np.max(np.abs(dz_slab["TSA_M20"]))),
        }
    order = ["h0p100", "h0p050", "h0p025"]
    verdicts: dict[str, Any] = {}
    for quantity in per_mesh[order[0]]:
        q = [per_mesh[m][quantity] for m in order]
        coarse_gap = abs(q[0] - q[1])
        fine_gap = abs(q[1] - q[2])
        production = fine_gap / abs(q[2]) if q[2] else float("nan")
        decreasing = coarse_gap > fine_gap
        verdicts[quantity] = {
            "valeurs": q,
            "ecart_0p10_0p05": coarse_gap,
            "ecart_0p05_0p025": fine_gap,
            "rapport_ecarts": coarse_gap / fine_gap if fine_gap else float("inf"),
            "ecart_relatif_production": production,
            "decroit": decreasing,
            "verdict": "RÉUSSI" if decreasing and production <= 0.02 else "ÉCHEC",
        }
    return {
        "critere": "docs/essais_lot47.md § 2.7",
        "maillages": order,
        "valeurs": per_mesh,
        "verdicts": verdicts,
        "runs": {k: str(p) for k, p in runs.items()},
    }


__all__ = [
    "BEAM_COMPONENTS",
    "SLAB_COMPONENTS",
    "Results",
    "load_results",
    "read_convergence",
    "run_batches",
    "run_med",
    "slab_xy",
]
