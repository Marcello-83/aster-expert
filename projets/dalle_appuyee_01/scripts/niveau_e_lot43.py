"""Lot 43 : suite de convergence et niveau E de la dalle (critère écrit avant
exécution dans docs/essais_lot43.md, commit 4093f12).

Pour chaque taille de `maillage.tailles_convergence` : maillage Salomé, `mesh
check` contre les invariants versionnés, génération du `.comm` par le générateur
du projet, exécution réelle, lecture des tables du listing ; puis évaluation des
critères E0-E2 (Navier), D5-D7, F2-F4, et des informations E3 et F1.

Sorties : `resultats/convergence/<taille>/` (non versionné) et
`references/niveau_e_lot43.json` (versionné, valeurs lues et verdicts).

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/niveau_e_lot43.py`
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from invariants_lot43 import invariants_path, meshes, size_label

from aster_expert.controles.tables import TableIndex
from aster_expert.ferraillage.plaque import (
    DENSITIES,
    efge_title,
    ferr_title,
    plate_values,
    rebar_combinations,
    titled_table,
)
from aster_expert.meshing.check import check_med
from aster_expert.meshing.config import load_mesh_config
from aster_expert.meshing.run import run_salome_script
from aster_expert.projet.context import load_project
from aster_expert.projet.pipeline import Runtime, _export_text, execute
from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.ultimate import design_ultimate
from dalle_appuyee_01.discretisation import SlabMesh
from dalle_appuyee_01.generation import build_comm, combination_name

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
OUT = PROJECT / "resultats" / "convergence"
REFERENCE = PROJECT / "references" / "navier_lot43.json"
RESULT = PROJECT / "references" / "niveau_e_lot43.json"
CASES = ("G", "Q")
QUANTITIES = ("w", "mx", "my")
E2_THRESHOLD = 0.01
EXACT = 1.0e-6


def run_mesh(mesh: SlabMesh, rt: Runtime) -> tuple[Path, dict[str, Any]]:
    """Salomé then `mesh check`; refuses a mesh with an invariant off."""
    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    work = OUT / size_label(mesh.size)
    work.mkdir(parents=True, exist_ok=True)
    params = work / "params.json"
    params.write_bytes(mesh.parameters_bytes())
    run = run_salome_script(
        PROJECT / "maillage" / "dalle_mesh.py",
        project_root=ROOT,
        config=config,
        params=params,
    )
    digest, _ = rt.aster()
    report = check_med(
        Path(run.med_path),
        invariants_path(mesh),
        project_root=ROOT,
        config=config,
        docker_bin=rt.docker_bin(),
        image_ref=f"{rt.image_repository}@{digest}",
    )
    held = sum(r.ok for r in report.results)
    if not report.ok:
        message = f"mesh check {size_label(mesh.size)} : {held}/{len(report.results)}"
        raise RuntimeError(message)
    return Path(run.med_path), {
        "med": str(Path(run.med_path).relative_to(ROOT)),
        "mesh_check": f"{held}/{len(report.results)}",
        "from_cache": run.from_cache,
    }


def run_case(mesh: SlabMesh, med: Path, rt: Runtime) -> tuple[str, dict[str, Any]]:
    ctx = load_project("dalle_appuyee_01", ROOT)
    work = OUT / size_label(mesh.size)
    stem = f"dalle_{size_label(mesh.size)}"
    text, report = build_comm(
        ctx, mesh_label=f"{size_label(mesh.size)} ({mesh.nx} x {mesh.ny})"
    )
    comm = work / f"{stem}.comm"
    comm.write_text(text, encoding="utf-8")
    shutil.copyfile(med, work / f"{stem}.mmed")
    (work / f"{stem}.export").write_text(_export_text(ctx, stem), encoding="utf-8")
    result = execute(ctx, rt, comm)
    mess = Path(result.work_dir) / "proc.0" / "fort.6"
    return mess.read_text(encoding="utf-8", errors="replace"), {
        "comm_sha256": report["comm_sha256"],
        "statut": result.status,
        "diagnostic": result.diag,
        "duree_s": round(result.duration_s or 0.0, 1),
        "alarmes": sum(1 for m in result.messages if m.kind == "<A>"),
        "repertoire": str(Path(result.work_dir).relative_to(ROOT)),
    }


def _f(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def read_case(text: str, case: str) -> dict[str, Any]:
    tables = TableIndex(text)
    depl = tables.find(f"DEPL_CENTRE_{case}")[0]
    noeu = titled_table(text, f"EFN_CENTRE_{case}")[0]
    elno = titled_table(text, f"EFE_CENTRE_{case}")
    at_centre = [r for r in elno if r["NOEUD"] == noeu["NOEUD"]]
    corners = []
    for r in tables.find(f"REACN_APPUI_{case}"):
        x, y = _f(r, "COOR_X"), _f(r, "COOR_Y")
        if x in (0.0, 6.0) and y in (0.0, 4.0):
            corners.append({"x": x, "y": y, "DZ": _f(r, "DZ")})
    edge_mid = [
        _f(r, "DZ")
        for r in tables.find(f"REACN_APPUI_{case}")
        if abs(_f(r, "COOR_X") - 3.0) < 1e-9 and _f(r, "COOR_Y") == 0.0
    ]
    return {
        "DZ": _f(depl, "DZ"),
        "MXX": _f(noeu, "MXX"),
        "MYY": _f(noeu, "MYY"),
        "MXY": _f(noeu, "MXY"),
        "elno_centre": [
            {
                "maille": r["MAILLE"],
                "MXX": _f(r, "MXX"),
                "MYY": _f(r, "MYY"),
                "MXY": _f(r, "MXY"),
            }
            for r in at_centre
        ],
        "reactions_coins_DZ": corners,
        "reaction_milieu_bord_y0_DZ": edge_mid,
    }


def closed_form_area(m: float, d: float, fcd: float, fyd: float) -> float:
    """Independent hand formula, rectangular block (EN 1992-1-1, lambda = 0,8,
    eta = 1), m2/m, M in MN.m/m: mu = M/(b d2 fcd), alpha = 1,25 (1 - sqrt(1 - 2 mu)),
    z = d (1 - 0,4 alpha), As = M / (z fyd), b = 1 m (pivot A or B, no compression
    steel)."""
    mu = m / (d * d * fcd)
    alpha = 1.25 * (1.0 - math.sqrt(1.0 - 2.0 * mu))
    z = d * (1.0 - 0.4 * alpha)
    return m / (z * fyd)


def rebar_at_centre(text: str) -> dict[str, Any]:
    """F1-F4 inputs on one mesh: ULS densities of the cells around the centre,
    hand calculation at the centre node, sensitivity of SIGC_*_ELS."""
    ctx = load_project("dalle_appuyee_01", ROOT)
    plate = ctx.declaration.rebar.plates[0]  # type: ignore[union-attr]
    v = plate_values(ctx, plate)
    out: dict[str, Any] = {}
    for index, combination, family in rebar_combinations(ctx, plate):
        ferr = {
            r["MAILLE"]: {c: float(r[c]) for c in DENSITIES}
            for r in titled_table(text, ferr_title(index))
        }
        if family.type_comb == "ELS":
            sens = {
                r["MAILLE"]: {c: float(r[c]) for c in DENSITIES}
                for r in titled_table(text, ferr_title(index, "S"))
            }
            gaps = [
                abs(ferr[m][c] - sens[m][c]) / max(abs(ferr[m][c]), abs(sens[m][c]))
                if max(abs(ferr[m][c]), abs(sens[m][c])) > 1e-12
                else abs(ferr[m][c] - sens[m][c])
                for m in ferr
                for c in DENSITIES
            ]
            out["F4_ecart_max_sensibilite"] = max(gaps)
        if family.type_comb != "ELU":
            continue
        cells = sorted(
            {r["MAILLE"] for r in titled_table(text, efge_title(index))}, key=int
        )
        node = titled_table(
            text, f"EFN_C_{combination_name(_combo_number(ctx, combination.name))}"
        )[0]
        mxx, myy, mxy = (float(node[c]) for c in ("MXX", "MYY", "MXY"))
        assert family.gamma_c is not None and family.gamma_s is not None
        concrete = Concrete(
            fck=v.fck / 1e6, gamma_c=family.gamma_c, alpha_cc=v.alpha_cc
        )
        steel = Steel(fyk=v.fyk / 1e6, es=v.eys / 1e6, gamma_s=family.gamma_s)
        section = Rectangle(
            width=1.0, depth=v.thickness, cover_pos=v.cover, cover_neg=v.cover
        )
        hand_x = design_ultimate(section, concrete, steel, 0.0, mxx / 1e6)
        hand_y = design_ultimate(section, concrete, steel, 0.0, myy / 1e6)
        d = v.thickness - v.cover
        closed_x = closed_form_area(-mxx / 1e6, d, concrete.fcd, steel.fyd)
        closed_y = closed_form_area(-myy / 1e6, d, concrete.fcd, steel.fyd)
        mean_cells = {c: sum(ferr[m][c] for m in cells) / len(cells) for c in DENSITIES}
        out["ELU"] = {
            "combinaison": combination.name,
            "efforts_centre_N_m_par_m": {"MXX": mxx, "MYY": myy, "MXY": mxy},
            "mailles_voisines": cells,
            "densites_mailles": {m: ferr[m] for m in cells},
            "moyenne_mailles": mean_cells,
            "manuel_module": {
                "DNSXI": hand_x.as_neg,
                "DNSXS": hand_x.as_pos,
                "DNSYI": hand_y.as_neg,
                "DNSYS": hand_y.as_pos,
            },
            "manuel_formule_fermee": {"DNSXI": closed_x, "DNSYI": closed_y},
            "F3_ecart_module_formule": max(
                abs(hand_x.as_neg - closed_x) / closed_x,
                abs(hand_y.as_neg - closed_y) / closed_y,
            ),
            "F2_ecart_centre": {
                c: abs(
                    mean_cells[c] - (hand_x.as_neg if c == "DNSXI" else hand_y.as_neg)
                )
                / (hand_x.as_neg if c == "DNSXI" else hand_y.as_neg)
                for c in ("DNSXI", "DNSYI")
            },
            "max_dalle": {c: max(ferr[m][c] for m in ferr) for c in DENSITIES},
        }
    return out


def _combo_number(ctx: Any, name: str) -> int:
    from aster_expert.combinaisons.enumeration import (
        enumerate_combinations,  # noqa: PLC0415
    )

    names = [
        c.name for c in enumerate_combinations(ctx.declaration.combinations, ctx.number)
    ]
    return names.index(name) + 1


def main() -> int:
    rt = Runtime(ROOT)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))["cas"]
    series: list[dict[str, Any]] = []
    for mesh in meshes():
        med, mesh_info = run_mesh(mesh, rt)
        text, run_info = run_case(mesh, med, rt)
        cases = {case: read_case(text, case) for case in CASES}
        for case, values in cases.items():
            ref = reference[case]
            values["w"] = -values["DZ"]
            values["mx"] = -values["MXX"]
            values["my"] = -values["MYY"]
            values["erreurs"] = {
                q: (values[q] - ref[f"{q}_m" if q == "w" else f"{q}_nm_par_m"])
                / ref[f"{q}_m" if q == "w" else f"{q}_nm_par_m"]
                for q in QUANTITIES
            }
        series.append(
            {
                "taille_m": mesh.size,
                "mailles": f"{mesh.nx} x {mesh.ny}",
                "maillage": mesh_info,
                "execution": run_info,
                "cas": cases,
                "ferraillage": rebar_at_centre(text),
            }
        )
        print(
            f"{size_label(mesh.size)} : {run_info['statut']} {run_info['duree_s']} s, {mesh_info['mesh_check']}"
        )
    verdicts = evaluate(series)
    RESULT.write_text(
        json.dumps(
            {"series": series, "verdicts": verdicts}, indent=1, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    for key, value in verdicts.items():
        print(key, value["verdict"], value.get("detail", ""))
    return 0


def evaluate(series: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    v: dict[str, dict[str, Any]] = {}
    signs = all(
        s["cas"][c]["DZ"] < 0 and s["cas"][c]["MXX"] < 0 and s["cas"][c]["MYY"] < 0
        for s in series
        for c in CASES
    )
    v["E0"] = {"verdict": "RÉUSSI" if signs else "ÉCHEC"}
    decreasing = {}
    for c in CASES:
        for q in QUANTITIES:
            errs = [abs(s["cas"][c]["erreurs"][q]) for s in series]
            decreasing[f"{c}.{q}"] = {
                "erreurs": errs,
                "decroit": all(b < a for a, b in zip(errs, errs[1:], strict=False)),
            }
    v["E1"] = {
        "verdict": "RÉUSSI"
        if all(d["decroit"] for d in decreasing.values())
        else "ÉCHEC",
        "detail": decreasing,
    }
    finest = series[-1]
    e2 = {
        f"{c}.{q}": abs(finest["cas"][c]["erreurs"][q])
        for c in CASES
        for q in QUANTITIES
    }
    v["E2"] = {
        "verdict": "RÉUSSI" if max(e2.values()) <= E2_THRESHOLD else "ÉCHEC",
        "detail": e2,
    }
    d5 = {
        f"{c}": abs(finest["cas"][c]["MXY"])
        / max(abs(finest["cas"][c]["MXX"]), abs(finest["cas"][c]["MYY"]))
        for c in CASES
    }
    v["D5"] = {
        "verdict": "RÉUSSI" if max(d5.values()) <= EXACT else "ÉCHEC",
        "detail": d5,
    }
    g, q = finest["cas"]["G"], finest["cas"]["Q"]
    d6 = {k: abs(g[k] / q[k] - 0.75) / 0.75 for k in ("DZ", "MXX", "MYY")}
    v["D6"] = {
        "verdict": "RÉUSSI" if max(d6.values()) <= EXACT else "ÉCHEC",
        "detail": d6,
    }
    v["D7"] = {
        "verdict": "INFORMATIF",
        "detail": {c: finest["cas"][c]["reactions_coins_DZ"] for c in CASES},
    }
    f2 = {
        k: [s["ferraillage"]["ELU"]["F2_ecart_centre"][k] for s in series]
        for k in ("DNSXI", "DNSYI")
    }
    v["F2"] = {
        "verdict": "RÉUSSI"
        if all(all(b < a for a, b in zip(e, e[1:], strict=False)) for e in f2.values())
        else "ÉCHEC",
        "detail": f2,
    }
    f3 = max(s["ferraillage"]["ELU"]["F3_ecart_module_formule"] for s in series)
    v["F3"] = {"verdict": "RÉUSSI" if f3 <= EXACT else "ÉCHEC", "detail": f3}
    f4 = max(s["ferraillage"]["F4_ecart_max_sensibilite"] for s in series)
    v["F4"] = {
        "verdict": "RÉUSSI" if f4 <= EXACT else "ÉCHEC (limite active)",
        "detail": f4,
    }
    v["E3"] = {
        "verdict": "INFORMATIF",
        "detail": {c: finest["cas"][c]["elno_centre"] for c in CASES},
    }
    return v


if __name__ == "__main__":
    raise SystemExit(main())
