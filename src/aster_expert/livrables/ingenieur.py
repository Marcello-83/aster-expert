"""Engineering summary of the deliverables (lot 49 bis): sub-step `ingenieur` of
`aster-expert projet <nom> livrables`.

From the arrays the container wrote (lot 49), never from a new Code_Aster run, and
from the declaration `engineering_summary` of `projet.yaml`:

1. per family of members and per limit state, the envelope of every component with
   the governing combination and moving position (`aster_expert.livrables.torseurs`);
2. per design section, the design values with their concomitant torsors, the line
   « section × combinaison », and per member the detail of a beam family;
3. the export for MM's bending software (`aster_expert.livrables.flexion`);
4. the serviceability criteria (`aster_expert.livrables.service`);
5. the data of the diagrams (beams along their axis, cuts of the shells), drawn by
   `aster_expert.livrables.diagrammes`;
6. the equilibrium by limit state: for every combination and every position, Σ loads
   (MED of loads, and for a moving position the resultant declared for its reference
   position) + Σ reactions + Σ spring forces;
7. the cross-check: every value of the summary is asked again to `aster-expert
   resultats lire` (`aster_expert.livrables.lecture.query`), component by component.

Everything is written in `resultats/livrables/paquet/` (copied by the results package,
section `visualisation`); the long raw tables of lot 49 go to `livrables/annexes/` as
CSV files, out of the workbook.
"""

from __future__ import annotations

import csv
import fnmatch
import json
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from aster_expert.arrondis import format_value, load_table
from aster_expert.livrables.chaine import deliverables_dir, sha256
from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.donnees import Deliverables, FieldInfo
from aster_expert.livrables.flexion import file_name, write_export
from aster_expert.livrables.lecture import Query, query
from aster_expert.livrables.sections import (
    LEVEL,
    M_RES,
    V_RES,
    FamilyRows,
    group_names,
    load_family,
    section_rows,
    singular_rows,
)
from aster_expert.livrables.service import evaluate_all
from aster_expert.livrables.torseurs import (
    STATE_LABELS,
    StateEnvelope,
    combination_lines,
    combinations_of_state,
    envelope,
    member_lines,
    primary_column,
    section_torsors,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import (
    LIMIT_STATES,
    EngineeringSummarySection,
    LimitState,
    MemberFamily,
)
from aster_expert.projet.errors import ProjectError

PACKAGE_DIR = "paquet"
EXPORT_DIR = "flexion_composee"
DIAGRAM_STATES = ("ELU_fondamental", "ELS_caracteristique")
CROSS_TOLERANCE = 1.0e-9
"""Relative gap admitted between a value of the summary and `resultats lire`: the two
superpose the same arrays in the same order, they differ by rounding only."""


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", "utf-8")


def _summary(ctx: ProjectContext) -> EngineeringSummarySection:
    summary = ctx.declaration.engineering_summary
    if summary is None:
        message = f"{ctx.declaration.name} : pas de section `engineering_summary`"
        raise ProjectError(message)
    return summary


def _info(infos: list[FieldInfo], family: MemberFamily) -> FieldInfo:
    for info in infos:
        if info.key == family.field:
            return info
    message = (
        f"famille {family.name} : champ {family.field} absent des livrables "
        f"({', '.join(i.key for i in infos)})"
    )
    raise ProjectError(message)


def _states(summary: EngineeringSummarySection) -> list[LimitState]:
    declared = {s.state for s in summary.limit_states}
    return [s for s in LIMIT_STATES if s in declared]


def _diagram_rows(
    fr: FamilyRows, envelopes: dict[str, StateEnvelope]
) -> dict[str, Any]:
    """Beams: N, M, V at every element end, max and min per limit state."""
    family = fr.family
    axis = family.axis or "Z"
    moment = M_RES if family.circular else (family.moments or ("",))[0]
    shear = V_RES if family.circular else (family.shears or ("",))[0]
    quantities = [q for q in ("N", moment, shear) if q and q in fr.columns]
    rows = []
    for k in range(len(fr.index)):
        entry: dict[str, Any] = {
            "groupe": fr.member[k],
            "abscisse_m": float(fr.xyz[k, "XYZ".index(axis)]),
            "maille_med": int(fr.element[k]) + 1,
            "extremite": int(fr.local[k]) + 1,
        }
        for state, env in envelopes.items():
            if state not in DIAGRAM_STATES:
                continue
            for q in quantities:
                c = fr.column(q)
                entry[f"{state}/{q}/max"] = float(env.maximum[k, c])
                entry[f"{state}/{q}/min"] = float(env.minimum[k, c])
        rows.append(entry)
    return {
        "famille": family.name,
        "axe": axis,
        "grandeurs": {"N": "N", "M": moment, "V": shear},
        "etats": [s for s in envelopes if s in DIAGRAM_STATES],
        "lignes": rows,
    }


def _cut_rows(
    ctx: ProjectContext,
    d: Deliverables,
    fr: FamilyRows,
    envelopes: dict[str, StateEnvelope],
) -> list[dict[str, Any]]:
    summary = _summary(ctx)
    out = []
    for cut in summary.cuts:
        if cut.family != fr.family.name:
            continue
        axis = "XYZ".index(cut.axis)
        values = np.unique(np.round(fr.xyz[:, axis], 6))
        chosen = float(values[np.argmin(np.abs(values - cut.value))])
        on = np.where(np.abs(fr.xyz[:, axis] - chosen) <= LEVEL)[0]
        along = fr.xyz[on, "XYZ".index(cut.along)]
        order = on[np.argsort(along, kind="stable")]
        flagged, reasons = singular_rows(
            fr, d.mesh, ctx.declaration.deliverables, cut.shared_with
        )
        points = []
        for k in order:
            point: dict[str, Any] = {
                "abscisse_m": float(fr.xyz[k, "XYZ".index(cut.along)]),
                "exclu": bool(flagged[k]),
                "motif": reasons.get(int(k)),
            }
            for state, env in envelopes.items():
                if state not in DIAGRAM_STATES:
                    continue
                for comp in cut.components:
                    c = fr.column(comp)
                    point[f"{state}/{comp}/max"] = float(env.maximum[k, c])
                    point[f"{state}/{comp}/min"] = float(env.minimum[k, c])
            points.append(point)
        out.append(
            {
                "coupe": cut.name,
                "famille": cut.family,
                "axe": cut.axis,
                "valeur_declaree_m": cut.value,
                "valeur_lue_m": chosen,
                "le_long_de": cut.along,
                "composantes": list(cut.components),
                "etats": [s for s in envelopes if s in DIAGRAM_STATES],
                "points": points,
            }
        )
    return out


def _family_pass(
    ctx: ProjectContext,
    d: Deliverables,
    info: FieldInfo,
    family: MemberFamily,
    combinations: list[GenericCombination],
    med_sha: str | None,
    package: Path,
) -> dict[str, Any]:
    summary = _summary(ctx)
    fr = load_family(d, info, family)
    sections = [
        section_rows(fr, d.mesh, s, ctx.declaration.deliverables)
        for s in summary.sections
        if s.family == family.name
    ]
    envelopes: dict[str, StateEnvelope] = {}
    for state in _states(summary):
        combos = combinations_of_state(combinations, summary, state)
        envelopes[state] = envelope(fr, combos, state, sections)
    torsors: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []
    for sec in sections:
        for env in envelopes.values():
            torsors += section_torsors(fr, combinations, env, sec)
            lines += combination_lines(fr, combinations, env, sec.section.name)
        export = sec.section.bending_export
        if export is None:
            continue
        for plane in export.planes:
            name = file_name(sec.section.name, plane, len(export.planes))
            text, rows = write_export(
                ctx, summary, fr, combinations, envelopes, sec, plane, med_sha
            )
            path = package / EXPORT_DIR / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
            exports.append(
                {
                    "section": sec.section.name,
                    "fichier": f"{EXPORT_DIR}/{name}",
                    "plan": plane.label,
                    "lignes": [
                        {
                            "type": r.type_label,
                            "cas": r.case,
                            "N_kN": r.n_kn,
                            "M_kNm": r.m_knm,
                            "combinaison": r.entry["combinaison"],
                            "position_mobile": r.entry["position_mobile"],
                            "lieu": r.entry["lieu"],
                        }
                        for r in rows
                    ],
                }
            )
    if family.members:
        for env in envelopes.values():
            members += member_lines(fr, combinations, env)
    diagram = _diagram_rows(fr, envelopes) if family.kind == "poutre" else None
    cuts = _cut_rows(ctx, d, fr, envelopes) if family.kind == "coque" else []
    return {
        "famille": {
            "nom": family.name,
            "type": family.kind,
            "champ": info.key,
            "groupes": list(family.groups),
            "membres": family.members,
            "grandeurs": list(family.quantities),
            "section_circulaire": family.circular,
            "grandeur_principale": primary_column(fr),
            "colonnes": list(fr.columns),
            "convention": info.convention,
            "reserve": family.caveat,
            "lignes": int(len(fr.index)),
            "evaluations": {s: e.evaluations for s, e in envelopes.items()},
        },
        "sections": [
            {
                "nom": s.section.name,
                "libelle": s.section.label,
                "famille": family.name,
                "regle": s.section.rule.description,
                "justification": s.section.justification,
                "lignes": int(s.mask.sum()),
                "lignes_exclues": int((s.mask & s.singular).sum()),
                "exclusion": s.section.exclude_singular,
                "lecture": s.notes,
                "reserve": s.section.caveat,
                "export": None
                if s.section.bending_export is None
                else [
                    file_name(s.section.name, p, len(s.section.bending_export.planes))
                    for p in s.section.bending_export.planes
                ],
                "non_exporte": s.section.not_exported,
            }
            for s in sections
        ],
        "torseurs": torsors,
        "lignes_combinaisons": lines,
        "membres": members,
        "exports": exports,
        "diagramme": diagram,
        "coupes": cuts,
    }


def _position_loads(
    ctx: ProjectContext, combinations: list[GenericCombination]
) -> dict[str, dict[str, float] | None]:
    """Resultant of every moving position: that of the declared case (in
    `controls.cases`) matching the same `moving_cases` pattern."""
    from aster_expert.controles.equilibre import expected_resultant  # noqa: PLC0415
    from aster_expert.projet.pipeline import load_state  # noqa: PLC0415

    section = ctx.declaration.deliverables
    controls = ctx.declaration.controls
    positions = sorted({p for c in combinations for p in c.mobile_cases})
    if not positions or section is None:
        return {}
    state = load_state(ctx)
    out_dir = deliverables_dir(ctx) / "controle_charges"
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {
        "comm_path": Path(state.comm or ""),
        "mesh_path": Path(state.mesh_med or ""),
        "out_dir": out_dir,
    }
    references: dict[str, dict[str, float] | None] = {}
    for moving in section.moving_cases:
        declared = [
            c
            for c in (controls.cases if controls else ())
            if fnmatch.fnmatchcase(c.name, moving) and c.expected_resultant is not None
        ]
        references[moving] = (
            expected_resultant(ctx, declared[0], **inputs)[0] if declared else None
        )
    out: dict[str, dict[str, float] | None] = {}
    for p in positions:
        pattern = next(
            (q for q in section.moving_cases if fnmatch.fnmatchcase(p, q)), None
        )
        out[p] = references.get(pattern) if pattern else None
    return out


def _sums(d: Deliverables, infos: list[FieldInfo], name: str) -> np.ndarray[Any, Any]:
    """Σ reactions + Σ spring forces on the structure of a case or position."""
    total = np.zeros(3)
    for info in infos:
        if info.family not in ("reactions", "ressorts"):
            continue
        fa = d.field(info)
        key = f"cas/{name}" if f"cas/{name}" in fa.arrays else f"pos/{name}"
        values = fa.arrays[key]
        if info.family == "reactions":
            for k, comp in enumerate(("DX", "DY", "DZ")):
                if comp in info.components:
                    total[k] += float(np.nansum(values[:, info.components.index(comp)]))
        else:
            for k, comp in enumerate(("N", "VY", "VZ")):
                if comp in info.components:
                    total[k] -= float(np.nansum(values[:, info.components.index(comp)]))
    return total


def equilibrium_by_state(
    ctx: ProjectContext,
    d: Deliverables,
    infos: list[FieldInfo],
    combinations: list[GenericCombination],
    package: Path,
) -> dict[str, Any]:
    summary = _summary(ctx)
    controls = ctx.declaration.controls
    threshold = controls.threshold if controls else 1.0e-6
    balance = json.loads((package / "equilibre_livrables.json").read_text("utf-8"))
    supports_missing = balance.get("appuis_non_livres") or []
    # Composantes que bloque un appui non livré : leur bilan est rapporté sans verdict.
    unknown = {
        {"DX": 0, "DY": 1, "DZ": 2}[c]
        for s in (controls.supports if controls else ())
        if s.group in supports_missing
        for c in s.blocked
        if c in ("DX", "DY", "DZ")
    }
    judged = [k for k in range(3) if k not in unknown]
    loads: dict[str, np.ndarray[Any, Any]] = {}
    for case, entry in balance["cas"].items():
        load = entry.get("charge_n")
        loads[case] = (
            np.array([load[k] for k in ("FX", "FY", "FZ")]) if load else np.zeros(3)
        )
    reactions = {case: _sums(d, infos, case) for case in balance["cas"]}
    position_loads = _position_loads(ctx, combinations)
    for p in position_loads:
        reactions[p] = _sums(d, infos, p)
    out: dict[str, Any] = {}
    for state in _states(summary):
        worst = 0.0
        worst_at: dict[str, Any] | None = None
        count = 0
        undeclared: set[str] = set()
        for _ci, comb in combinations_of_state(combinations, summary, state):
            load = sum((c * loads[n] for n, c in comb.fixed.items() if c), np.zeros(3))
            react = sum(
                (c * reactions[n] for n, c in comb.fixed.items() if c), np.zeros(3)
            )
            options: list[tuple[str | None, Any, Any]] = [(None, load, react)]
            if comb.mobile_cases:
                options = []
                for p in comb.mobile_cases:
                    ref = position_loads.get(p)
                    if ref is None:
                        undeclared.add(p)
                        continue
                    f = np.array([ref["DX"], ref["DY"], ref["DZ"]])
                    options.append(
                        (
                            p,
                            load + comb.mobile_coefficient * f,
                            react + comb.mobile_coefficient * reactions[p],
                        )
                    )
            for position, applied, carried in options:
                count += 1
                scale = float(np.max(np.abs(applied))) or 1.0
                residual = np.abs(applied + carried)
                gap = float(np.max(residual[judged])) / scale if judged else 0.0
                if gap >= worst:
                    worst = gap
                    worst_at = {
                        "combinaison": comb.name,
                        "position_mobile": position,
                        "charge_n": dict(
                            zip(("FX", "FY", "FZ"), map(float, applied), strict=True)
                        ),
                        "reactions_et_ressorts_n": dict(
                            zip(("FX", "FY", "FZ"), map(float, carried), strict=True)
                        ),
                    }
        verdict = "RÉUSSI" if worst <= threshold and not undeclared else "ÉCHEC"
        if not judged:
            verdict = "SANS VERDICT"
        out[state] = {
            "etat_limite": STATE_LABELS[state],
            "evaluations": count,
            "ecart_relatif_max": worst,
            "pire": worst_at,
            "seuil": threshold,
            "positions_sans_charge_declaree": sorted(undeclared),
            "composantes_jugees": [("FX", "FY", "FZ")[k] for k in judged],
            "verdict": verdict,
        }
    return {
        "controle": "Σ charges + Σ réactions + Σ forces des ressorts = 0, par "
        "combinaison et par position mobile, par état limite (lot 49 bis)",
        "source": "charges : somme des forces nodales du MED des charges (cas "
        "élémentaires) et résultante déclarée de la position de référence "
        "(controls.cases) pour une position mobile ; réactions et ressorts lus dans "
        "les livrables",
        "appuis_non_livres": supports_missing,
        "etats": out,
    }


def cross_check(
    ctx: ProjectContext,
    d: Deliverables,
    infos: list[FieldInfo],
    torsors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Every torsor of the summary asked again to `resultats lire`."""
    summary = _summary(ctx)
    by_name = {f.name: f for f in summary.families}
    checked = 0
    worst = 0.0
    failures: list[dict[str, Any]] = []
    for t in torsors:
        family = by_name[t["famille"]]
        info = _info(infos, family)
        lieu = t["lieu"]
        case = t["combinaison"]
        if t["position_mobile"]:
            case = f"{case}@{t['position_mobile']}"
        groups = (
            (lieu["groupe"],)
            if lieu["groupe"]
            else tuple(group_names(d.mesh, family.groups))
        )
        answer = query(
            ctx,
            Query(
                groupes=groups,
                champ=info.key,
                cas=(case,),
                mode="point",
                point=tuple(lieu["coordonnees_m"]),
                disques=False,
                tolerance=LEVEL,
            ),
            deliverables=d,
        )
        found: dict[str, float] = {}
        for r in answer.rows:
            if r["noeud_med"] != lieu["noeud_med"]:
                continue
            if lieu["maille_med"] is not None and (
                r["maille_med"] != lieu["maille_med"]
                or (
                    lieu["extremite"] is not None
                    and r["extremite"] != lieu["extremite"]
                )
            ):
                continue
            if r["cas_ou_combinaison"].endswith("(min)"):
                continue
            found[r["composante"]] = float(r["valeur_si"])
        if "MFY" in found and "MFZ" in found:
            found[M_RES] = math.hypot(found["MFY"], found["MFZ"])
        if "VY" in found and "VZ" in found:
            found[V_RES] = math.hypot(found["VY"], found["VZ"])
        scale = max((abs(v) for v in t["torseur_si"].values()), default=1.0) or 1.0
        for comp, value in t["torseur_si"].items():
            checked += 1
            if comp not in found:
                failures.append(
                    {
                        "torseur": t["section"],
                        "composante": comp,
                        "motif": "absente de resultats lire",
                    }
                )
                continue
            gap = abs(found[comp] - value) / scale
            worst = max(worst, gap)
            if gap > CROSS_TOLERANCE:
                failures.append(
                    {
                        "section": t["section"],
                        "etat_limite": t["etat_limite"],
                        "grandeur": t["grandeur"],
                        "composante": comp,
                        "synthese": value,
                        "resultats_lire": found[comp],
                        "ecart_relatif": gap,
                    }
                )
    return {
        "controle": "chaque torseur de la synthèse ingénieur relu par `aster-expert "
        "resultats lire` (combinaison@position, nœud et extrémité d'élément)",
        "torseurs": len(torsors),
        "valeurs_comparees": checked,
        "ecart_relatif_max": worst,
        "tolerance": CROSS_TOLERANCE,
        "echecs": failures[:50],
        "verdict": "RÉUSSI" if not failures else "ÉCHEC",
    }


def write_annexes(root: Path, package: Path) -> list[str]:
    """The long raw tables of lot 49 as CSV annexes, out of the workbook."""
    out_dir = root / "annexes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("points.json", "enveloppes_lineiques.json"):
        # Tables longues du lot 49 : annexes, hors du paquet et du classeur.
        if (package / name).is_file():
            shutil.move(str(package / name), str(out_dir / name))
    written = []
    points_path = out_dir / "points.json"
    if points_path.is_file():
        points = json.loads(points_path.read_text("utf-8"))
        comps = sorted({c for p in points for c in p["valeurs_si"]})
        with (out_dir / "efforts_aux_points.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as h:
            w = csv.writer(h, delimiter=";")
            w.writerow(
                [
                    "point",
                    "champ",
                    "source",
                    "noeud_med",
                    "maille_med",
                    "extremite",
                    "X_m",
                    "Y_m",
                    "Z_m",
                    *comps,
                ]
            )
            for p in points:
                x, y, z = p["lieu"]["coordonnees_m"]
                w.writerow(
                    [
                        p["point"],
                        p["cle"],
                        p["source"],
                        p["lieu"]["noeud_med"],
                        p["lieu"].get("maille_med", ""),
                        p["lieu"].get("extremite", ""),
                        f"{x:.3f}",
                        f"{y:.3f}",
                        f"{z:.3f}",
                        *[
                            repr(p["valeurs_si"][c]) if c in p["valeurs_si"] else ""
                            for c in comps
                        ],
                    ]
                )
        written.append("efforts_aux_points.csv")
    linear_path = out_dir / "enveloppes_lineiques.json"
    if linear_path.is_file():
        linear = json.loads(linear_path.read_text("utf-8"))
        if linear:
            keys = list(linear[0])
            with (out_dir / "enveloppes_lineiques.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as h:
                w = csv.writer(h, delimiter=";")
                w.writerow(keys)
                w.writerows([[e.get(k, "") for k in keys] for e in linear])
            written.append("enveloppes_lineiques.csv")
    return written


def step_ingenieur(ctx: ProjectContext, rt: Any) -> list[str]:  # noqa: ARG001
    from aster_expert.livrables.diagrammes import draw_all  # noqa: PLC0415

    summary = _summary(ctx)
    section = ctx.declaration.deliverables
    if section is None:
        message = "livrables : section `deliverables` absente"
        raise ProjectError(message)
    root = deliverables_dir(ctx)
    package = root / PACKAGE_DIR
    if not (package / "equilibre_livrables.json").is_file():
        message = "synthèse ingénieur : sous-étape vues d'abord"
        raise ProjectError(message)
    d = Deliverables(root, keep_fields=True)
    infos = d.field_infos(section.fields)
    combinations = d.combinations
    med = root / "med" / "resultats.med"
    med_sha = sha256(med) if med.is_file() else None
    if (package / EXPORT_DIR).exists():
        shutil.rmtree(package / EXPORT_DIR)
    families = []
    for family in summary.families:
        families.append(
            _family_pass(
                ctx, d, _info(infos, family), family, combinations, med_sha, package
            )
        )
    torsors = [t for f in families for t in f["torseurs"]]
    service = evaluate_all(d, combinations, summary)
    balance = equilibrium_by_state(ctx, d, infos, combinations, package)
    checked = cross_check(ctx, d, infos, torsors)
    header = {
        "projet": ctx.declaration.name,
        "med_resultats_sha256": med_sha,
        "etats_limites": [
            {
                "etat": s,
                "libelle": STATE_LABELS[s],
                "familles_de_combinaisons": list(
                    next(x for x in summary.limit_states if x.state == s).families
                ),
            }
            for s in _states(summary)
        ],
        "etats_absents": [
            {"etat": a.state, "libelle": STATE_LABELS[a.state], "motif": a.reason}
            for a in summary.absent_limit_states
        ],
        "fissuration": {
            "etat": summary.cracking.state,
            "libelle": STATE_LABELS[summary.cracking.state],
            "source": summary.cracking.source,
        },
        "methode": "superposition des cas élémentaires et des positions mobiles "
        "livrés (lot 49) avec les coefficients déclarés ; aucun calcul Code_Aster",
    }
    _dump(
        package / "synthese_ingenieur.json",
        {
            **header,
            "familles": [f["famille"] for f in families],
            "sections": [s for f in families for s in f["sections"]],
            "torseurs": torsors,
            "exports": [e for f in families for e in f["exports"]],
        },
    )
    _dump(
        package / "torseurs_combinaisons.json",
        [line for f in families for line in f["lignes_combinaisons"]],
    )
    _dump(package / "detail_membres.json", [m for f in families for m in f["membres"]])
    _dump(
        package / "diagrammes.json",
        {
            "poutres": [f["diagramme"] for f in families if f["diagramme"]],
            "coupes": [c for f in families for c in f["coupes"]],
        },
    )
    _dump(
        package / "verifications_service.json",
        {
            "criteres": service,
            **(
                {"motif_absence": summary.no_service_criteria}
                if summary.no_service_criteria
                else {}
            ),
        },
    )
    _dump(package / "equilibre_etats_limites.json", balance)
    _dump(package / "controles_croises.json", checked)
    annexes = write_annexes(root, package)
    images = draw_all(package)
    table = load_table(ctx.repo_root)
    lines = [
        f"Synthèse ingénieur : {len(families)} famille(s), "
        f"{sum(len(f['sections']) for f in families)} section(s), "
        f"{len(torsors)} torseur(s) dimensionnant(s) ; "
        f"{sum(len(f['exports']) for f in families)} fichier(s) de flexion composée",
        "Critères de service : "
        + (
            ", ".join(
                f"{c['critere']} {c.get('verdict', 'sans verdict')}"
                f" ({format_value(c['gouvernant']['valeur_m'] * 1e3, 'mm', table)} mm"
                f" / {format_value(c['limite_m'] * 1e3, 'mm', table)} mm)"
                for c in service
                if "gouvernant" in c
            )
            or "aucun (" + str(summary.no_service_criteria) + ")"
        ),
        "Équilibre par état limite : "
        + ", ".join(
            f"{v['etat_limite']} {v['verdict']} ({v['ecart_relatif_max']:.1e}, "
            f"{v['evaluations']} évaluations)"
            for v in balance["etats"].values()
        ),
        f"Contrôle croisé par resultats lire : {checked['verdict']} "
        f"({checked['valeurs_comparees']} valeurs, écart max "
        f"{checked['ecart_relatif_max']:.1e})",
        f"Annexes CSV : {', '.join(annexes) or 'aucune'} ; diagrammes : {len(images)} "
        "image(s)",
    ]
    if checked["verdict"] != "RÉUSSI":
        message = f"synthèse ingénieur : {lines[3]}"
        raise ProjectError(message)
    return lines


__all__ = [
    "CROSS_TOLERANCE",
    "cross_check",
    "equilibrium_by_state",
    "step_ingenieur",
    "write_annexes",
]
