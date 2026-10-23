# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 52 for PONTONS-ALU-01: the PRO geometry (P62 to P66), from the tables
Code_Aster printed during the runs of this lot (units 31, 32, 33), recombined with the
rules of lot 51 quater (houle P60 with the coefficient of the 50 mm purlins, impact
P61, sensitivity HU_S5).

The files are those of lot 51 quater (`exports_lot51quater.export`, itself built on
`exports_lot51ter.export_variant`), plus:

- `geometrie_noeuds.csv`: every crossing purlin/post, purlin/diagonal (and purlin/edge
  purlin of the cantilever) and post/main beam, with the top and bottom of each bar,
  the gap or overlap in mm and, for a post on a main beam, the length of the weld zone
  projected on the beam (width of the post + 2 × bhaz, bhaz = 30 mm, P63);
- in `comparaison_variantes.csv`, per family (main beams, purlins, posts, diagonals,
  piece of post between the main beam and the diagonal node): N min, N max, My, Mz and
  V extremes;
- `comparaison_B52_B12_lot51quater.csv`: every quantity of the comparison of B52
  against B12 of lot 51 quater.

The efforts CSV (`efforts_elementaires.csv`, about 190 MB) is written for B52 only, to
check the `.npz` with the independent reader; it is not delivered.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51quater import (
    branches,
    events_p60_p61,
    events_s5,
    magnitudes_p60,
)
from pontons_alu_01.combinaisons_lot51ter import counts, expanded_counts
from pontons_alu_01.exports_lot51 import mesh_dump, sha256, write
from pontons_alu_01.exports_lot51quater import (
    HOULE_COLUMNS,
    Variant51quater,
    check_counts,
    check_enumeration,
    check_resultants,
    comparison_extra,
    export,
    extra_columns,
    governing_houle,
)
from pontons_alu_01.exports_lot51ter import (
    Quantity,
    RunTables,
    VariantData51ter,
    _arrays,
    _max_over_states,
    _resultant_over_states,
    build_model,
    comparison,
    comparison_columns,
    criterion_am1,
    criterion_linearity,
    criterion_pins,
    criterion_tp,
    read_run,
)
from pontons_alu_01.generation_lot51ter import (
    all_cases,
    concrete_volumes,
    zone_names,
)
from pontons_alu_01.generation_lot52 import geometry_of, values
from pontons_alu_01.geometrie_lot51 import Link, Member
from pontons_alu_01.geometrie_lot51ter import Geometry51ter
from pontons_alu_01.geometrie_lot52 import diagonal_node
from pontons_alu_01.variantes_lot52 import Variant52, reference, variants

FloatArray = NDArray[np.float64]
LOT = "lot52"
KN = 1e-3
FORCES_CSV_VARIANT = "B52"
SEED = 52
BHAZ_MM = 30.0
"""Width of the heat-affected zone each side of a weld (EN 1999-1-1, 6.1.6.3, P63)."""
WELD_LIMIT_MM = 200.0
"""Width of the main beam: the weld zone must stay under it (P63)."""
PREVIOUS = ("lot51quater", "B12")
"""Variant of lot 51 quater compared with B52 (consigne § Contrôles)."""
SCRIPTS = Path(__file__).resolve().parent / "scripts"
NPZ_READER = SCRIPTS / "lire_npz_lot51quater.py"


# --------------------------------------------------------------------------- variants


def fold_link_reactions(
    tables: RunTables, model: Any, g: Geometry51ter
) -> dict[str, int]:
    """CA-036: REAC_NODA of a node linked by LIAISON_SOLIDE carries the force of the
    link, which cancels only over the linked nodes. The abutment nodes and the ears are
    the B ends of links LM_ (P64), whose A ends (post ends) are printed in unit 33 too:
    their REAC_NODA is added to that of the support node and removed, so that every
    reaction read downstream is the force of the support alone. Returns, per support
    group, the number of folded ends."""
    abutment = set(g.node_groups["APP_CULEE"])
    ears = {p for a in g.axes for p in a.ears}
    folded = {"APP_CULEE": 0, "AXES": 0}
    pairs = []
    for lk in g.links:
        if not lk.name.startswith("LM_") or (lk.b not in abutment and lk.b not in ears):
            continue
        (a,) = model.group_nodes[f"{lk.name}_A"]
        (b,) = model.group_nodes[f"{lk.name}_B"]
        pairs.append((a, b))
        folded["APP_CULEE" if lk.b in abutment else "AXES"] += 1
    for reac in tables.reac.values():
        for a, b in pairs:
            if a not in reac or b not in reac:
                message = f"REAC_NODA : nœuds liés {a}, {b} absents de l'unité 33"
                raise ValueError(message)
            reac[b] = reac[b] + reac.pop(a)
    return folded


def load_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any]
) -> VariantData51ter:
    """The tables of the lot 52 run of `code`, its model, the events P60/P61."""
    v = variants()[code]
    g = geometry_of(v)
    run_dir = Path(state[code]["execution"]["execution_dir"])
    tables = read_run(run_dir, g)
    dump = mesh_dump(ctx, Path(state[code]["maillage"]["med"]))
    model = build_model(dump, tables, g, v)
    fold_link_reactions(tables, model, g)
    data = {key: item.value for key, item in ctx.data().items().items()}
    ev = events_p60_p61(
        magnitudes_p60(data, v.purlin_side_mm),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )
    return VariantData51ter(
        v,
        model,
        tables,
        g,
        all_cases(g),
        ev,
        branches(ev),
        Path(state[code]["comm"]),
        values(ctx, v),
        {m.name: m.span for m in g.members},
    )


def load(ctx: ProjectContext, code: str, state: dict[str, Any]) -> Variant51quater:
    """The variant under P60/P61 (the lot) and HU_S5 (sensitivity); no P56 set (`p56`
    is the lot's own set, unused)."""
    t0 = time.perf_counter()
    vd = load_variant(ctx, code, state)
    load_s = time.perf_counter() - t0
    data = {key: item.value for key, item in ctx.data().items().items()}
    ev_s5 = events_s5(
        magnitudes_p60(data, vd.variant.purlin_side_mm),
        zones=zone_names(vd.g),
        cleats=[n for n, _, _ in vd.g.cleats],
        modules=list(vd.g.modules()),
    )
    return Variant51quater(
        vd=vd,
        p56=vd,
        s5=dataclasses.replace(vd, ev=ev_s5, bs=branches(ev_s5)),
        load_s=load_s,
    )


def source_line(vd: VariantData51ter, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, lot 52 (géométrie PRO : P62 à P66 ; houle P60, impact P61), variante "
        f"{vd.variant.code} ({vd.variant.description}) : exécution {run}, .comm sha256 {sha256(vd.comm)}, "
        f"maillage sha256 {s['maillage']['med_sha256']}."
    )


# --------------------------------------------------------------------------- node geometry


def _member_at(
    g: Geometry51ter,
    point: tuple[float, float, float],
    span: str,
    families: tuple[str, ...],
) -> Member:
    """The bar of `families` through `point`, that of `span` first (a node at the end
    of PT5 is also the start of PF)."""
    found = [m for m in g.members if m.family in families and point in m.points]
    if not found:
        message = f"{point} : aucune barre de {families}"
        raise ValueError(message)
    return sorted(found, key=lambda m: m.span != span)[0]


def _side(v: Variant52, family: str) -> float:
    """Outer side of the tube of a family, m."""
    return (
        1e-3
        * {
            "POUTRES_PRINC": v.beam_side_mm,
            "MONTANTS": v.post_side_mm,
            "DIAGONALES": v.post_side_mm,
            "PANNES_SEC": v.purlin_side_mm,
            "PANNE_RIVE": v.purlin_side_mm,
        }[family]
    )


def _section(v: Variant52, family: str) -> str:
    s, t = {
        "POUTRES_PRINC": (v.beam_side_mm, v.beam_thickness_mm),
        "MONTANTS": (v.post_side_mm, v.post_thickness_mm),
        "DIAGONALES": (v.post_side_mm, v.post_thickness_mm),
        "PANNES_SEC": (v.purlin_side_mm, v.purlin_thickness_mm),
        "PANNE_RIVE": (v.purlin_side_mm, v.purlin_thickness_mm),
    }[family]
    return f"tube {s:g}x{s:g}x{t:g}"


CROSSING = {
    "MONTANTS": "panne/montant",
    "DIAGONALES": "panne/diagonale",
    "PANNE_RIVE": "panne/panne de rive",
}


def node_geometry(v: Variant52, g: Geometry51ter) -> list[dict[str, Any]]:
    """Every crossing of the deck (links LR_ and LM_), from the geometry and the
    sections of the variant: top and bottom of each bar (axis ± side / 2), gap (> 0) or
    overlap (< 0) in mm; for a post on a main beam, the margins of the post in the
    height of the flank and the weld zone projected on the beam."""
    rows: list[dict[str, Any]] = []
    links: list[Link] = [lk for lk in g.links if lk.name.startswith(("LR_", "LM_"))]
    for lk in links:
        span = lk.name.split("_")[1]
        if lk.name.startswith("LM_"):
            upper = _member_at(g, lk.a, span, ("MONTANTS",))
            lower = _member_at(g, lk.b, span, ("POUTRES_PRINC",))
        else:
            upper = _member_at(g, lk.a, span, ("PANNES_SEC",))
            lower = _member_at(g, lk.b, span, tuple(CROSSING))
        if lk.name.startswith("LM_"):
            post, beam = upper, lower  # A : bout du montant, B : nœud de la poutre
            kind = "montant/poutre"
        else:
            post, beam = lower, upper
            kind = CROSSING[lower.family]
        top_m, low_m = (upper, lower) if kind != "montant/poutre" else (beam, post)
        z_top, z_low = (
            (lk.a[2], lk.b[2]) if kind != "montant/poutre" else (lk.b[2], lk.a[2])
        )
        a_top, a_low = _side(v, top_m.family) / 2.0, _side(v, low_m.family) / 2.0
        row: dict[str, Any] = {
            "croisement": kind,
            "liaison": lk.name,
            "travee": span,
            "x": lk.a[0],
            "y": lk.a[1],
            "barre_dessus": top_m.name,
            "section_dessus": _section(v, top_m.family),
            "z_axe_dessus": z_top,
            "z_haut_dessus": z_top + a_top,
            "z_bas_dessus": z_top - a_top,
            "barre_dessous": low_m.name,
            "section_dessous": _section(v, low_m.family),
            "z_axe_dessous": z_low,
            "z_haut_dessous": z_low + a_low,
            "z_bas_dessous": z_low - a_low,
            "longueur_liaison": abs(lk.a[2] - lk.b[2]),
        }
        if kind == "montant/poutre":
            # Le montant aboute le flanc de la poutre : marges dans la hauteur du flanc.
            up = (z_top + a_top) - (z_low + a_low)
            down = (z_low - a_low) - (z_top - a_top)
            row["jeu_mm"] = round(1e3 * min(up, down), 6)
            row["detail"] = (
                f"montant aboutant le flanc de la poutre : marge en haut {1e3 * up:.1f} mm, "
                f"en bas {1e3 * down:.1f} mm (≥ 0 : le montant reste dans la hauteur du flanc)"
            )
            row["zone_soudure_mm"] = 1e3 * _side(v, "MONTANTS") + 2.0 * BHAZ_MM
        else:
            gap = (z_top - a_top) - (z_low + a_low)
            row["jeu_mm"] = round(1e3 * gap, 6)
            row["detail"] = (
                "contact (pose directe)"
                if abs(row["jeu_mm"]) < 1e-6
                else ("jeu" if gap > 0 else "RECOUVREMENT")
            )
            row["zone_soudure_mm"] = ""
        rows.append(row)
    return rows


NODE_COLUMNS = (
    "croisement",
    "liaison",
    "travee",
    "x",
    "y",
    "barre_dessus",
    "section_dessus",
    "z_axe_dessus",
    "z_haut_dessus",
    "z_bas_dessus",
    "barre_dessous",
    "section_dessous",
    "z_axe_dessous",
    "z_haut_dessous",
    "z_bas_dessous",
    "longueur_liaison",
    "jeu_mm",
    "zone_soudure_mm",
    "detail",
)


def node_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for kind in sorted({r["croisement"] for r in rows}):
        sub = [r for r in rows if r["croisement"] == kind]
        gaps = [float(r["jeu_mm"]) for r in sub]
        welds = [float(r["zone_soudure_mm"]) for r in sub if r["zone_soudure_mm"] != ""]
        out[kind] = {
            "nombre": len(sub),
            "jeu_min_mm": min(gaps),
            "jeu_max_mm": max(gaps),
            "recouvrements": sum(1 for x in gaps if x < -1e-6),
            "longueur_liaison_m": sorted(
                {round(r["longueur_liaison"], 6) for r in sub}
            ),
            "zone_soudure_max_mm": max(welds) if welds else None,
        }
    welds_all = [
        float(r["zone_soudure_mm"]) for r in rows if r["zone_soudure_mm"] != ""
    ]
    out["reussi"] = all(float(r["jeu_mm"]) >= -1e-6 for r in rows) and (
        max(welds_all) <= WELD_LIMIT_MM
    )
    return out


# --------------------------------------------------------------------------- families


def troncon_rows(vd: VariantData51ter) -> list[tuple[int, int]]:
    """Element ends of the pieces of post between a main beam and the diagonal node
    (|Y| ≥ B/2 − e_diag at both nodes: group MONTANTS_TRONCONS)."""
    yd = diagonal_node(vd.g.parameters)
    out = []
    for e in sorted(vd.model.elements.values(), key=lambda e: e.number):
        if e.family != "MONTANTS":
            continue
        ys = [abs(float(vd.model.coords[n - 1][1])) for n in e.nodes]
        if min(ys) >= yd - 1e-9:
            out += [(e.number, n) for n in e.nodes]
    return out


FAMILIES = (
    ("PP", "poutres principales", ("POUTRES_PRINC",)),
    ("PANNES", "pannes", ("PANNES_SEC",)),
    ("MONT", "montants", ("MONTANTS",)),
    ("DIAG", "diagonales", ("DIAGONALES",)),
    ("TRONCON", "tronçons de montant entre poutre et nœud de diagonale", ()),
)
FAMILY_QUANTITIES = ("N_min", "N_max", "My", "Mz", "V")


def family_columns() -> tuple[str, ...]:
    return tuple(f"FAM_{k}_{q}" for k, _, _ in FAMILIES for q in FAMILY_QUANTITIES)


def family_extremes(
    vd: VariantData51ter,
    families: tuple[tuple[str, str, tuple[str, ...]], ...] = FAMILIES,
) -> dict[str, Quantity]:
    """Per family: N min, N max, My and Mz extreme in absolute value (signed), V max
    (√(VY² + VZ²)), over the four compared limit states (lot 54: its own families)."""
    out: dict[str, Quantity] = {}
    for key, label, fams in families:
        if fams:
            rows = [
                (e.number, n)
                for e in sorted(vd.model.elements.values(), key=lambda e: e.number)
                if e.family in fams
                for n in e.nodes
            ]
        else:
            rows = troncon_rows(vd)
        where = [
            f"élément {e} nœud {n} ({vd.model.elements[e].member})" for e, n in rows
        ]
        n_arr = _arrays(vd, rows, 0)
        items = {
            "N_min": (
                "N min",
                "kN",
                _max_over_states(vd, n_arr, sign=-1, where=where, scale=KN),
            ),
            "N_max": (
                "N max",
                "kN",
                _max_over_states(vd, n_arr, sign=1, where=where, scale=KN),
            ),
            "My": (
                "My extrême en valeur absolue, signé (MFY)",
                "kN·m",
                _max_over_states(
                    vd,
                    _arrays(vd, rows, 4),
                    sign=1,
                    where=where,
                    scale=KN,
                    absolute=True,
                ),
            ),
            "Mz": (
                "Mz extrême en valeur absolue, signé (MFZ)",
                "kN·m",
                _max_over_states(
                    vd,
                    _arrays(vd, rows, 5),
                    sign=1,
                    where=where,
                    scale=KN,
                    absolute=True,
                ),
            ),
            "V": (
                "V max (√(VY² + VZ²))",
                "kN",
                _resultant_over_states(
                    vd, _arrays(vd, rows, 1), _arrays(vd, rows, 2), where, KN
                ),
            ),
        }
        for q, (lab, unit, quantity) in items.items():
            quantity.label, quantity.unit = f"{label} : {lab}", unit
            out[f"FAM_{key}_{q}"] = quantity
    return out


def troncon_places(
    vd: VariantData51ter,
) -> list[tuple[str, dict[str, FloatArray], list[str]]]:
    rows = troncon_rows(vd)
    where = [f"{e}/{n}" for e, n in rows]
    return [
        (f"{c} tronçons de montant", _arrays(vd, rows, k), where)
        for c, k in (("N", 0), ("MFY", 4), ("MFZ", 5))
    ]


# --------------------------------------------------------------------------- checks


def check_npz(out: Path) -> dict[str, Any]:
    """The independent reader (numpy and csv only) against efforts_elementaires.csv."""
    result = subprocess.run(  # noqa: S603 -- argv fixe
        [
            sys.executable,
            "-I",
            str(NPZ_READER),
            str(out / "efforts_elementaires.npz"),
            str(out / "efforts_elementaires.csv"),
            "--graine",
            str(SEED),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    (out.parent / f"lecture_npz_{out.name}.txt").write_text(
        result.stdout + result.stderr, "utf-8"
    )
    return {
        "code": result.returncode,
        "sortie": result.stdout.strip().splitlines()[-3:],
    }


# --------------------------------------------------------------------------- steps


def run_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any]
) -> dict[str, Any]:
    root = ctx.results_dir / LOT / "exports"
    v = load(ctx, code, state)
    vd = v.vd
    assert isinstance(vd.variant, Variant52)
    out = root / code
    t0 = time.perf_counter()
    files, details = export(
        v,
        state,
        out,
        source=source_line(vd, state),
        forces_csv=code == FORCES_CSV_VARIANT,
    )
    nodes = node_geometry(vd.variant, vd.g)
    files["geometrie_noeuds.csv"] = write(
        out / "geometrie_noeuds.csv",
        f"{source_line(vd, state)} Unités : m (cotes NGF, coordonnées), mm (jeu, zone de soudure). Un croisement "
        "par liaison rigide du tablier : panne/montant et panne/diagonale (LR_, la panne pose sur la barre, "
        "P64), panne/panne de rive du porte-à-faux (LR_ de PF, hypothèse du lot 51 ter inchangée), "
        "montant/poutre (LM_, montant soudé sur le flanc de la poutre principale). Cotes de dessus et de "
        "dessous = axe ± demi-cote extérieure du tube. jeu_mm : dessous de la barre du dessus − dessus de la "
        "barre du dessous (< 0 : recouvrement) ; pour montant/poutre, plus petite marge du montant dans la "
        "hauteur du flanc (dessus et dessous). zone_soudure_mm : longueur de la zone adoucie projetée sur la "
        f"poutre = largeur du montant + 2 × {BHAZ_MM:g} mm (bhaz, EN 1999-1-1, 6.1.6.3, P63), à comparer "
        f"aux {WELD_LIMIT_MM:g} mm de la poutre.",
        list(NODE_COLUMNS),
        [[r[c] for c in NODE_COLUMNS] for r in nodes],
    )
    t1 = time.perf_counter()
    comp = comparison(vd)
    extra = comparison_extra(v)
    houle = governing_houle(v, comp)
    fam = family_extremes(vd)
    t2 = time.perf_counter()
    info: dict[str, Any] = {
        "statut": "calculée",
        "fichiers": files,
        "effectifs": counts(vd.bs),
        "effectifs_dispositions": expanded_counts(vd.bs, vd.ev),
        "volumes_beton_m3": concrete_volumes(vd.vals, vd.g),
        "cotes_m_ngf": vd.g.levels,
        "details": details,
        "geometrie_noeuds": node_summary(nodes),
        "comparaison": {
            k: dataclasses.asdict(q)
            for k, q in {**comp, **extra, **houle, **fam}.items()
        },
        "temps_s": {
            "lecture_tables": v.load_s,
            "exports": t1 - t0,
            "comparaison": t2 - t1,
            "recombinaison": t2 - t0,
        },
        "controle_resultantes": check_resultants(v),
        "controle_linearite": criterion_linearity(vd),
        "controle_AM1": criterion_am1(vd),
        "controle_TP": criterion_tp(vd),
        "controle_appuis_axe": criterion_pins(vd),
    }
    if code == FORCES_CSV_VARIANT:
        t3 = time.perf_counter()
        info["controle_enumeration"] = check_enumeration(
            out, v, seed=SEED, extra_places=troncon_places(vd)
        )
        info["controle_effectifs"] = check_counts(out, v)
        info["temps_s"]["enumeration"] = time.perf_counter() - t3
        info["controle_npz"] = check_npz(out)
    return info


def _run_variant_job(
    repo_root: Path, code: str, state: dict[str, Any]
) -> dict[str, Any]:
    from aster_expert.projet.context import load_project  # noqa: PLC0415

    ctx = load_project("pontons_alu_01", repo_root)
    return run_variant(ctx, code, state)


def step_exports(
    ctx: ProjectContext, codes: list[str], state: dict[str, Any], workers: int = 1
) -> None:
    from concurrent.futures import ProcessPoolExecutor  # noqa: PLC0415

    root = ctx.results_dir / LOT / "exports"
    root.mkdir(parents=True, exist_ok=True)
    summary_path = root / "synthese.json"
    summary: dict[str, Any] = (
        json.loads(summary_path.read_text("utf-8")) if summary_path.is_file() else {}
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            code: pool.submit(_run_variant_job, ctx.repo_root, code, state)
            for code in codes
            if "execution_dir" in state.get(code, {}).get("execution", {})
        }
        for code, fut in futures.items():
            summary[code] = fut.result()
            summary_path.write_text(
                json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
                "utf-8",
            )
            t = summary[code]["temps_s"]
            print(f"{code} : exports écrits, recombinaison {t['recombinaison']:.1f} s")
    write_comparison(root, summary)
    previous = ctx.results_dir / PREVIOUS[0] / "exports" / "synthese.json"
    if previous.is_file() and "B52" in summary:
        write_previous_comparison(
            root, summary["B52"], json.loads(previous.read_text("utf-8"))[PREVIOUS[1]]
        )


def write_comparison(root: Path, summary: dict[str, Any]) -> None:
    g = geometry_of(variants()[reference()])
    columns = comparison_columns(g)
    extra = (*extra_columns(list(g.piers)), *family_columns())
    labels: dict[str, str] = {}
    main_rows: list[list[Any]] = []
    detail_rows: list[list[Any]] = []
    for code, v in variants().items():
        info = summary.get(code)
        if info is None or info.get("statut") != "calculée":
            main_rows.append(
                [
                    code,
                    v.description,
                    "non calculée",
                    *([""] * (len(columns) + len(extra) + len(HOULE_COLUMNS))),
                ]
            )
            continue
        comp = info["comparaison"]
        main_rows.append(
            [
                code,
                v.description,
                "calculée",
                *(float(comp[c]["value"]) for c in (*columns, *extra)),
                *(comp[c]["event"] for c in HOULE_COLUMNS),
            ]
        )
        for key in (*columns, *extra, *HOULE_COLUMNS):
            q = comp[key]
            labels[key] = f"{q['label']} [{q['unit']}]"
            detail_rows.append(
                [
                    code,
                    key,
                    q["label"],
                    q["unit"],
                    q["event"] if key in HOULE_COLUMNS else float(q["value"]),
                    q["state"],
                    q["combination"],
                    q["where"],
                ]
            )
    header = (
        "PONTONS-ALU-01, lot 52 : comparaison des variantes de la géométrie PRO (P62 à P66), houle P60 "
        "« tablier noyé » et impact P61. Valeurs : enveloppes du jeu B′ révisé (ELU fondamental, ELS "
        "caractéristique, ELS fréquent) et de l'ELU accidentel, avec DEJ (P49), P57, P59, sauf les flèches (P51, "
        "P62 : ELS fréquent, ELS caractéristique avec la houle et sans la composante tangentielle d'accostage ; "
        "actions variables seules ; grandes travées relatives à la corde, porte-à-faux relatif à l'appui et à la "
        "corde de PT5, L = 2 Lpf) et les états limites nommés. Colonnes ANCRAGE_Pk_* : effort d'ancrage requis "
        "par palée, P60/P61 et, suffixe _S5, sensibilité HU_S5 sans décision (5 kPa). Colonnes FAM_* : extrêmes "
        "par famille (PP poutres principales, PANNES, MONT montants, DIAG diagonales, TRONCON tronçons de "
        "montant entre la poutre et le nœud de diagonale). Colonnes HOULE_* : événement de houle de la "
        "combinaison gouvernante. Unités : kN, kN·m, mm. Colonnes : "
        + " ; ".join(
            f"{k} = {labels.get(k, k)}" for k in (*columns, *extra, *HOULE_COLUMNS)
        )
        + ". Détail : comparaison_variantes_detail.csv."
    )
    write(
        root / "comparaison_variantes.csv",
        header,
        ["variante", "description", "statut", *columns, *extra, *HOULE_COLUMNS],
        main_rows,
    )
    write(
        root / "comparaison_variantes_detail.csv",
        "PONTONS-ALU-01, lot 52 : grandeurs de comparaison, état limite, combinaison et lieu qui gouvernent "
        "(colonne valeur : l'événement de houle pour les grandeurs HOULE_*).",
        [
            "variante",
            "grandeur",
            "libelle",
            "unite",
            "valeur",
            "etat_limite",
            "combinaison",
            "lieu",
        ],
        detail_rows,
    )


def write_previous_comparison(
    root: Path, b52: dict[str, Any], b12: dict[str, Any]
) -> None:
    """B52 against B12 of lot 51 quater, every quantity both compare."""
    rows = []
    for key, q in b52["comparaison"].items():
        old = b12["comparaison"].get(key)
        if old is None or key in HOULE_COLUMNS:
            continue
        a, b = float(q["value"]), float(old["value"])
        rows.append(
            [
                key,
                q["label"],
                q["unit"],
                a,
                b,
                a - b,
                (a - b) / abs(b) if b not in (0.0,) and np.isfinite(b) else "",
                q["combination"],
                q["where"],
                old["combination"],
                old["where"],
            ]
        )
    write(
        root / "comparaison_B52_B12_lot51quater.csv",
        "PONTONS-ALU-01, lot 52 : B52 (géométrie PRO, P63 à P65 : montants et diagonales 120 × 120 × 6 sous les "
        "pannes, pannes 50 × 50 × 5, axe +1,175) contre B12 du lot 51 quater (montants et diagonales 150 × 150 × 7 "
        "dans le plan des poutres, pannes 60 × 60 × 5, HU_PANNES × 2,11, axe +1,16) ; mêmes règles (P60, P61). "
        "ecart = B52 − B12, ecart_relatif = écart / |B12|. Unités : kN, kN·m, mm.",
        [
            "grandeur",
            "libelle",
            "unite",
            "B52",
            "B12_lot51quater",
            "ecart",
            "ecart_relatif",
            "combinaison_B52",
            "lieu_B52",
            "combinaison_B12",
            "lieu_B12",
        ],
        rows,
    )


def step_copy_reader(out: Path) -> None:
    shutil.copyfile(NPZ_READER, out / "lire_npz.py")


__all__ = [
    "FAMILIES",
    "load",
    "load_variant",
    "node_geometry",
    "node_summary",
    "step_exports",
    "troncon_rows",
]
