"""Contrôle post-lot 54: combined displacement field of B54 from the unit-case MED.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/champ_combine_lot54.py \
        --med-dir <dossier de resultats.med et charges.med> --execution <exécution> \
        --maillage <maillage.med> --comm <.comm> --sortie <dossier> [--lot54 <dépôt B54>]

For each of the three views of the panne B (A: SLS characteristic, DY at the tip of the
cantilever; B: accidental ULS, same criterion; C: SLS characteristic, DX without
temperature at the axis of P5), takes the label of the governing combination in
`deplacements_combinaisons.csv` of lot 54, the coefficients of `evenements.csv`, and sums
coefficient × unit field (DEPL of `resultats.med`, read by medcoupling in the Code_Aster
image). G and Q are included. Checks the value at the output point against the CSV (0.01
mm) and against the nodal field of the tables of the run, then writes one legacy VTK
polydata file per view (bars as lines, DEPL in mm) for `vues_deformees_lot54_pv.py`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.projet.context import ProjectContext, load_project
from pontons_alu_01 import deplacements_lot53 as d53
from pontons_alu_01.controle_lot54 import (
    LOT54,
    build_state,
    event_table,
    label_coefficients,
    rows_of,
)
from pontons_alu_01.exports_lot54 import load
from pontons_alu_01.med_lot51quater import READ_SCRIPT, in_image

ROOT = Path(__file__).resolve().parents[3]
VIEWS = (
    ("A", "PF_bout_YM", "DY", "ELS_caracteristique", "total", 10),
    ("B", "PF_bout_YM", "DY", "ELU_accidentel", "total", 10),
    ("C", "P5C2_YM_axe", "DX", "ELS_caracteristique", "total_hors_T", 25),
)
TOLERANCE_MM = 0.01


def read_med(
    ctx: ProjectContext, med_dir: Path, work: Path
) -> tuple[dict[str, Any], np.ndarray]:
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "lu.json").is_file():
        for name in ("resultats.med", "charges.med"):
            shutil.copyfile(med_dir / name, work / name)
        shutil.copyfile(READ_SCRIPT, work / READ_SCRIPT.name)
        in_image(
            ctx,
            work,
            f"python3 {READ_SCRIPT.name} resultats.med charges.med lu.npz lu.json",
        )
        for name in ("resultats.med", "charges.med"):
            (work / name).unlink(missing_ok=True)
    meta = json.loads((work / "lu.json").read_text("utf-8"))
    with np.load(work / "lu.npz") as data:
        depl = data["depl"].copy()
    return meta, depl


def reperes(pts: dict[str, Any]) -> dict[str, float]:
    """Label -> X (m): the piers P1 to P5 (mean X of their hinge axes) and the abutment."""
    axes: dict[str, list[float]] = {}
    for p in pts.values():
        if p.kind == "axe":
            axes.setdefault(p.place, []).append(p.x)
    labels = {k: float(np.mean(v)) for k, v in sorted(axes.items())}
    abutment = [p.x for p in pts.values() if p.kind == "culee"]
    labels["culée"] = float(np.mean(abutment)) if abutment else 0.0
    return labels


def write_vtk(
    path: Path,
    coords: np.ndarray,
    segments: list[tuple[int, int]],
    u_mm: np.ndarray,
) -> None:
    """Legacy ASCII polydata: points, lines (SEG2), point data `u_mm` (3 components)."""
    with path.open("w", encoding="utf-8") as out:
        out.write(
            "# vtk DataFile Version 3.0\nB54 combined displacement field\nASCII\n"
        )
        out.write(f"DATASET POLYDATA\nPOINTS {len(coords)} double\n")
        np.savetxt(out, coords, fmt="%.9g")
        out.write(f"LINES {len(segments)} {3 * len(segments)}\n")
        for a, b in segments:
            out.write(f"2 {a - 1} {b - 1}\n")
        out.write(f"POINT_DATA {len(coords)}\nVECTORS u_mm double\n")
        np.savetxt(out, u_mm, fmt="%.9g")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--med-dir", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--maillage", type=Path, required=True)
    parser.add_argument("--comm", type=Path, required=True)
    parser.add_argument("--lot54", type=Path, default=LOT54)
    parser.add_argument("--sortie", type=Path, required=True)
    args = parser.parse_args()
    ctx = load_project("pontons_alu_01", ROOT)
    out = args.sortie
    out.mkdir(parents=True, exist_ok=True)
    state = build_state(args.execution, args.maillage, args.comm)
    vd = load(ctx, "B54", state)
    pts = {p.name: p for p in d53.output_points(vd)}
    coords = np.asarray(vd.model.coords)
    segments = [e.nodes for e in vd.model.elements.values()]

    meta, depl = read_med(ctx, args.med_dir, out / "med_lecture")
    cases = meta["cas"]
    index = {c: i for i, c in enumerate(cases)}
    table = event_table(args.lot54 / "evenements.csv")
    combos = rows_of(args.lot54 / "deplacements_combinaisons.csv")
    nodes = depl.shape[1]
    if nodes != coords.shape[0]:
        message = f"MED : {nodes} nœuds, maillage : {coords.shape[0]}"
        raise SystemExit(message)

    # the MED unit fields against the tables of the run (node order, case order)
    worst_unit = 0.0
    for case in ("G1", "Q_M0", "QD_M3", "HU_TUBES", "TP"):
        ref = np.array([vd.tables.depl[case][k][:6] for k in range(1, nodes + 1)])
        worst_unit = max(
            worst_unit,
            float(np.abs(depl[index[case]] - ref).max() / np.abs(ref).max()),
        )

    report: dict[str, Any] = {
        "cas_med": len(cases),
        "ecart_relatif_med_tables_cas_controles": worst_unit,
        "vues": {},
        "reperes": reperes(pts),
    }
    ok = worst_unit <= 1e-9
    for key, point, direction, limit, column, amplification in VIEWS:
        row = next(
            r
            for r in combos
            if r["point"] == point
            and r["direction"] == direction
            and r["etat_limite"] == limit
        )
        label = row[f"{column}_combinaison_max"]
        expected = float(row[f"{column}_max"])
        _, coefs = label_coefficients(label, table)
        field = np.zeros((nodes, 6))
        for case, c in coefs.items():
            field += c * depl[index[case]]
        from_tables = d53.nodal_field(vd, coefs)
        gap_tables = float(
            np.abs(field - from_tables).max() / np.abs(from_tables).max()
        )
        value = float(
            d53.point_value(
                pts[point], {n + 1: field[n] for n in range(nodes)}, coords
            )[["DX", "DY", "DZ"].index(direction)]
            * 1e3
        )
        node = pts[point].node
        comp = ["DX", "DY", "DZ"].index(direction)
        node_value = None if node is None else float(field[node - 1][comp] * 1e3)
        u_mm = field[:, :3] * 1e3
        write_vtk(out / f"champ_{key}.vtk", coords, segments, u_mm)
        peak = float(np.abs(u_mm).max())
        item = {
            "etiquette": label,
            "point": point,
            "direction": direction,
            "etat_limite": limit,
            "colonne": column,
            "valeur_champ_mm": value,
            "valeur_noeud_mm": node_value,
            "valeur_csv_mm": expected,
            "ecart_mm": value - expected,
            "ecart_relatif_champ_tables": gap_tables,
            "amplification": amplification,
            "deplacement_max_mm": peak,
            "bornes_coloration_mm": [
                float(u_mm[:, comp].min()),
                float(u_mm[:, comp].max()),
            ],
            "termes": len(coefs),
        }
        report["vues"][key] = item
        ok = ok and abs(value - expected) <= TOLERANCE_MM and gap_tables <= 1e-9
        print(
            f"vue {key} : {point} {direction} = {value:.4f} mm (csv {expected:.4f}, "
            f"écart {value - expected:+.2e}) ; champ MED − tables {gap_tables:.1e}"
        )
    report["reussi"] = bool(ok)
    (out / "champs_combines.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    np.save(out / "coords.npy", coords)
    print("RÉUSSI" if ok else "ÉCHEC")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
