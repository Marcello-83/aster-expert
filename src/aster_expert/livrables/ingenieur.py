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
    BAR_SUFFIX,
    LEVEL,
    M_RES,
    SYNTHETIC,
    V_RES,
    Band,
    FamilyRows,
    SectionRows,
    add_level_rows,
    band_nodes,
    band_of,
    compose_tee,
    group_names,
    load_family,
    rule_mask,
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
    Level,
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


def _levels(summary: EngineeringSummarySection, family: MemberFamily) -> list[Level]:
    """Levels cut in a beam family: those of its sections and of their E27 axes."""
    out: list[Level] = []
    for section in summary.sections:
        if section.family != family.name:
            continue
        for rule in (
            section.rule,
            section.design_moment.axis_rule if section.design_moment else None,
        ):
            if rule is not None and rule.level is not None and rule.level not in out:
                out.append(rule.level)
    return out


def family_rows(
    d: Deliverables,
    infos: list[FieldInfo],
    summary: EngineeringSummarySection,
    family: MemberFamily,
) -> FamilyRows:
    """The rows of a family: the field rows, the T section composed (E25) and the
    rows interpolated at the declared levels (E24), lot 49 ter."""
    fr = load_family(d, _info(infos, family), family)
    tee = family.tee_section
    if tee is not None:
        plate_family = next(f for f in summary.families if f.name == tee.plate_family)
        keep = band_nodes(d.mesh, fr, group_names(d.mesh, plate_family.groups), tee)
        plate = load_family(
            d, _info(infos, plate_family), plate_family, keep_nodes=keep
        )
        compose_tee(fr, plate, tee)
    if family.kind == "poutre":
        for level in _levels(summary, family):
            add_level_rows(fr, level)
    return fr


def level_check(d: Deliverables, fr: FamilyRows) -> dict[str, Any] | None:
    """E24 (lot 49 ter): an interpolated row is exact for N, V and M only if its
    element carries no transverse distributed load (it would leave consistent nodal
    forces at its ends) and no spring inside (none: the element has two nodes). The
    largest transverse nodal force at the ends of the cut elements, over the
    elementary cases, is reported (0 expected)."""
    if not fr.synthetic:
        return None
    nodes: set[int] = set()
    axes: dict[int, Any] = {}
    for info in fr.synthetic.values():
        a, b = (np.asarray(c, dtype=float) for c in info["coordonnees_m"])
        axis = (b - a) / np.linalg.norm(b - a)
        for n in info["noeuds_med"]:
            nodes.add(n - 1)
            axes[n - 1] = axis
    worst = 0.0
    worst_at: dict[str, Any] | None = None
    for name, values, kind, entity, components in d.loads():
        if not name.startswith("FN_"):
            continue
        rows = np.nonzero((kind == 0) & np.isin(entity, sorted(nodes)))[0]
        v = values.reshape(len(kind), -1)
        cols = [components.index(c) for c in ("DX", "DY", "DZ") if c in components]
        for r in rows:
            force = np.zeros(3)
            force[: len(cols)] = v[r, cols]
            axis = axes[int(entity[r])]
            transverse = float(np.linalg.norm(force - np.dot(force, axis) * axis))
            if transverse > worst:
                worst = transverse
                worst_at = {"cas": name[3:], "noeud_med": int(entity[r]) + 1}
    return {
        "lignes_interpolees": len(fr.synthetic),
        "noeuds_d_extremite": len(nodes),
        "force_transversale_max_N": worst,
        "lieu": worst_at,
        "seuil_N": 1.0e-6,
        "verdict": "exacte" if worst <= 1.0e-6 else "à signaler",
        "regle": "interpolation linéaire exacte pour N, V, M sans charge transversale "
        "répartie ni ressort dans l'élément ; une charge répartie laisserait des "
        "forces nodales transversales aux extrémités",
    }


def bands(d: Deliverables, summary: EngineeringSummarySection) -> tuple[Band, ...]:
    """E26: the exclusion bands of the beam families that declare one."""
    out = []
    for family in summary.families:
        band = band_of(d.mesh, family)
        if band is not None:
            out.append(band)
    return tuple(out)


def _check_signs(fr: FamilyRows, sections: list[SectionRows]) -> None:
    """D3: a span or support section of a family bending one way declares the sign it
    keeps for each bending component."""
    family = fr.family
    if family.circular:
        return
    moments = (
        list(family.moments)
        if family.kind == "poutre"
        else [m for m in ("MXX", "MYY") if m in fr.columns]
    )
    for sec in sections:
        if sec.section.zone not in ("travee", "appui", "chapeau", "nu"):
            continue
        missing = [m for m in moments if m not in sec.section.moment_signs]
        if missing:
            message = (
                f"section {sec.section.name} ({sec.section.zone}) : signe retenu non "
                f"déclaré pour {missing} (`moment_signs`, D3)"
            )
            raise ProjectError(message)


def disjoint_zones(fr: FamilyRows, sections: list[SectionRows]) -> dict[str, Any]:
    """D3 (lot 49 ter): no node and no element end in two sections of one family,
    unless declared (`shared_rows`). Raises on a shared row; returns the check."""
    pairs = []
    for i, a in enumerate(sections):
        for b in sections[i + 1 :]:
            declared = (
                b.section.name in a.section.shared_rows
                or a.section.name in b.section.shared_rows
            )
            rows = np.nonzero(a.mask & b.mask)[0]
            nodes_a = set(fr.node[a.mask & (fr.kind != SYNTHETIC)].tolist())
            nodes_b = set(fr.node[b.mask & (fr.kind != SYNTHETIC)].tolist())
            nodes = sorted(nodes_a & nodes_b)
            pairs.append(
                {
                    "sections": [a.section.name, b.section.name],
                    "lignes_communes": int(rows.size),
                    "noeuds_communs": len(nodes),
                    "partage_declare": declared,
                }
            )
            if (rows.size or nodes) and not declared:
                where = fr.place(int(rows[0])) if rows.size else {"noeud_med": nodes[0]}
                message = (
                    f"famille {fr.family.name} : les sections {a.section.name} et "
                    f"{b.section.name} se recouvrent ({rows.size} ligne(s), "
                    f"{len(nodes)} nœud(s), par exemple {where}) ; zones disjointes "
                    "exigées (D3) ou partage déclaré (`shared_rows`)"
                )
                raise ProjectError(message)
    return {"famille": fr.family.name, "paires": pairs}


def identical_lines(torsors: list[dict[str, Any]]) -> None:
    """D3: two identical lines (same place, same combination and position, same
    value) in two sections are refused unless the sharing is declared."""
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for t in torsors:
        if not t.get("significative", True) or "e27" in t:
            continue
        lieu = t["lieu"]
        key = (
            t["famille"],
            t["etat_limite"],
            lieu.get("noeud_med"),
            lieu.get("maille_med"),
            lieu.get("extremite"),
            tuple(lieu["coordonnees_m"]),
            t["combinaison"],
            t["position_mobile"],
            t["colonne"],
            round(float(t["valeur_si"]), 9),
        )
        other = seen.get(key)
        if other is not None and other["section"] != t["section"]:
            if t["section"] in other.get("partages", ()) or other["section"] in t.get(
                "partages", ()
            ):
                continue
            message = (
                f"lignes identiques dans les sections {other['section']} et "
                f"{t['section']} ({t['grandeur']}, {t['etat_limite']}, "
                f"{t['combinaison']}) : refusées sauf partage déclaré (D3)"
            )
            raise ProjectError(message)
        seen.setdefault(key, t)


def opposite_signs(torsors: list[dict[str, Any]]) -> None:
    """D3: an extreme of the opposite sign stays out unless it dimensions -- larger in
    modulus than the value of every section of the family that keeps that sign, for
    the same state and component; it is then kept and declared."""
    for t in torsors:
        if not t.get("signe_oppose"):
            continue
        rivals = [
            abs(float(o["valeur_si"]))
            for o in torsors
            if o["famille"] == t["famille"]
            and o["etat_limite"] == t["etat_limite"]
            and o["colonne"] == t["colonne"]
            and o["sens"] == t["sens"]
            and not o.get("signe_oppose")
            and o.get("significative", True)
        ]
        value = abs(float(t["valeur_si"]))
        if rivals and value <= max(rivals):
            t["motif"] = (
                f"signe opposé (D3) : {value * 1e-3:.1f} k, inférieur à la valeur des "
                f"sections qui retiennent ce signe ({max(rivals) * 1e-3:.1f} k) : non "
                "dimensionnant"
            )
            t["dimensionnant"] = False
        else:
            t["significative"] = True
            t["dimensionnant"] = True
            t["motif"] = (
                "signe opposé dimensionnant (D3) : supérieur à la valeur de toute "
                "section qui retient ce signe ; retenu et déclaré"
            )


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
            fr,
            d.mesh,
            ctx.declaration.deliverables,
            cut.shared_with,
            bands(d, summary),
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
    infos: list[FieldInfo],
    family: MemberFamily,
    combinations: list[GenericCombination],
    med_sha: str | None,
    package: Path,
    auxiliaries: dict[str, Any],
) -> dict[str, Any]:
    summary = _summary(ctx)
    info = _info(infos, family)
    fr = family_rows(d, infos, summary, family)
    shell_bands = bands(d, summary) if family.kind == "coque" else ()
    sections = [
        section_rows(fr, d.mesh, s, ctx.declaration.deliverables, shell_bands)
        for s in summary.sections
        if s.family == family.name
    ]
    _check_signs(fr, sections)
    zones = disjoint_zones(fr, sections)
    envelopes: dict[str, StateEnvelope] = {}
    state_combos: dict[str, list[tuple[int, GenericCombination]]] = {}
    for state in _states(summary):
        combos = combinations_of_state(combinations, summary, state)
        state_combos[state] = combos
        envelopes[state] = envelope(fr, combos, state, sections)
    torsors: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []
    e27: dict[str, dict[str, dict[str, Any]]] = {}
    for sec in sections:
        for env in envelopes.values():
            found = section_torsors(fr, combinations, env, sec)
            for t in found:
                t["partages"] = list(sec.section.shared_rows)
                if sec.section.zone == "comparaison":
                    t["comparaison_seulement"] = True
            torsors += found
            lines += combination_lines(fr, combinations, env, sec.section.name)
        if sec.section.design_moment is not None:
            e27[sec.section.name] = support_moments(
                ctx, d, fr, sec, combinations, state_combos, auxiliaries
            )
            torsors += list(e27[sec.section.name].values())
    for sec in sections:
        export = sec.section.bending_export
        if export is None:
            continue
        for plane in export.planes:
            name = file_name(sec.section.name, plane, len(export.planes))
            text, rows = write_export(
                ctx,
                summary,
                fr,
                combinations,
                envelopes,
                sec,
                plane,
                med_sha,
                e27.get(sec.section.name, {}),
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
                            "e27": r.entry.get("e27") is not None,
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
            "lignes_interpolees": len(fr.synthetic),
            "interpolation": level_check(d, fr),
            "section_en_T": fr.tee,
            "bande_exclusion": None
            if family.exclusion_band is None
            else {
                "demi_largeur_m": family.exclusion_band.half_width,
                "source": family.exclusion_band.source,
            },
            "evaluations": {s: e.evaluations for s, e in envelopes.items()},
            "zones": zones,
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
                "zone": s.section.zone,
                "signes": dict(s.section.moment_signs),
                "moment_appui": None
                if s.section.design_moment is None
                else {
                    "grandeur": s.section.design_moment.quantity,
                    "fraction": s.section.design_moment.fraction,
                    "auxiliaire": s.section.design_moment.auxiliary,
                    "axe": s.section.design_moment.axis_rule.description,
                    "appuis": s.section.design_moment.supports.model_dump(),
                    "source": s.section.design_moment.source,
                },
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


def _auxiliary(
    ctx: ProjectContext, auxiliaries: dict[str, Any], name: str
) -> tuple[Deliverables, list[FieldInfo], dict[str, Any]]:
    from aster_expert.livrables.derives import open_derived  # noqa: PLC0415

    if name not in auxiliaries:
        try:
            auxiliaries[name] = open_derived(ctx, name)
        except FileNotFoundError as exc:
            message = (
                f"E27 : livrables du modèle auxiliaire {name} absents ({exc}) ; "
                f"`aster-expert projet {ctx.declaration.name} livrables --modele "
                f"{name}` d'abord"
            )
            raise ProjectError(message) from exc
    found: tuple[Deliverables, list[FieldInfo], dict[str, Any]] = auxiliaries[name]
    return found


def _axis_rows(ctx: ProjectContext, d: Deliverables, fr: FamilyRows, rule: Any) -> Any:
    """Rows of an E27 axis rule, out of the exclusion discs (PAT-013) for a shell."""
    mask, _notes = rule_mask(fr, d.mesh, rule)
    if fr.family.kind == "coque":
        discs, _ = singular_rows(fr, d.mesh, ctx.declaration.deliverables, ())
        mask &= ~discs
    return np.nonzero(mask)[0]


def support_moments(
    ctx: ProjectContext,
    d: Deliverables,
    fr: FamilyRows,
    sec: SectionRows,
    combinations: list[GenericCombination],
    state_combos: dict[str, list[tuple[int, GenericCombination]]],
    auxiliaries: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """E27 entries of a section, per limit state (`aster_expert.livrables.appuis`)."""
    from aster_expert.livrables.appuis import (  # noqa: PLC0415
        describe,
        design_moment,
        section_sign,
    )
    from aster_expert.livrables.derives import derived_model  # noqa: PLC0415

    dm = sec.section.design_moment
    assert dm is not None
    summary = _summary(ctx)
    model = derived_model(ctx, dm.auxiliary)
    aux_d, aux_infos, _recorded = _auxiliary(ctx, auxiliaries, dm.auxiliary)
    aux_fr = family_rows(aux_d, aux_infos, summary, fr.family)
    results = design_moment(
        mesh=d.mesh,
        ref=fr,
        sec=sec,
        ref_axis_rows=_axis_rows(ctx, d, fr, dm.axis_rule),
        aux=aux_fr,
        aux_axis_rows=_axis_rows(ctx, aux_d, aux_fr, dm.axis_rule),
        dm=dm,
        state_combinations=state_combos,
        excluded=model.excluded_cases,
    )
    sign = section_sign(sec, dm)
    variants: dict[str, Any] = {}
    for name in dm.variants:
        var_d, var_infos, _rec = _auxiliary(ctx, auxiliaries, name)
        var_fr = family_rows(var_d, var_infos, summary, fr.family)
        var_sec = section_rows(
            var_fr, var_d.mesh, sec.section, ctx.declaration.deliverables
        )
        var_results = design_moment(
            mesh=var_d.mesh,
            ref=var_fr,
            sec=var_sec,
            ref_axis_rows=_axis_rows(ctx, var_d, var_fr, dm.axis_rule),
            aux=aux_fr,
            aux_axis_rows=_axis_rows(ctx, aux_d, aux_fr, dm.axis_rule),
            dm=dm,
            state_combinations=state_combos,
            excluded=model.excluded_cases,
        )
        variants[name] = (var_fr, var_sec, var_results)
    out: dict[str, dict[str, Any]] = {}
    for state, result in results.items():
        entry = describe(
            result,
            ref=fr,
            aux=aux_fr,
            sec=sec,
            dm=dm,
            combinations=combinations,
            sign=sign,
        )
        if entry is not None:
            entry["e27"]["cas_exclus_auxiliaire"] = list(model.excluded_cases)
            entry["e27"]["motif_exclusion"] = model.excluded_reason
            entry["triplet"] = {
                "N": "N" if fr.family.kind == "poutre" else "NXX",
                "M": dm.quantity,
                "V": (
                    V_RES
                    if dm.quantity == M_RES
                    else {"MFY": "VZ", "MFZ": "VY", "MXX": "QX", "MYY": "QY"}.get(
                        dm.quantity
                    )
                ),
            }
            entry["sens"] = "e27"
            entry["partages"] = []
            reference_dim = entry["e27"]["M_dim_si"]
            entry["e27"]["variantes"] = {}
            for name, (var_fr, var_sec, var_results) in variants.items():
                described = describe(
                    var_results[state],
                    ref=var_fr,
                    aux=aux_fr,
                    sec=var_sec,
                    dm=dm,
                    combinations=combinations,
                    sign=sign,
                )
                if described is None:
                    continue
                var_dim = described["e27"]["M_dim_si"]
                variation = (var_dim - reference_dim) / abs(reference_dim)
                envelope = (
                    dm.variant_threshold is not None
                    and abs(variation) > dm.variant_threshold
                )
                entry["e27"]["variantes"][name] = {
                    "M_nu_si": described["e27"]["M_nu_si"],
                    "M_dim_si": var_dim,
                    "terme_gouvernant": described["e27"]["terme_gouvernant"],
                    "combinaison": described["combinaison"],
                    "position_mobile": described["position_mobile"],
                    "variation": variation,
                    "seuil": dm.variant_threshold,
                    "enveloppe": envelope,
                }
                if envelope and var_dim > entry["e27"]["M_dim_si"]:
                    # Critère écrit avant l'exécution : au-delà du seuil, la valeur de
                    # dimensionnement est l'enveloppe de la référence et des variantes.
                    entry["e27"]["M_dim_si"] = var_dim
                    entry["valeur_si"] = sign * var_dim
                    for key in (
                        "lieu",
                        "combinaison",
                        "famille_combinaison",
                        "position_mobile",
                        "charge_mobile",
                        "torseur_si",
                    ):
                        entry[key] = described[key]
                    entry["e27"]["gouverne_par"] = (
                        f"{name} (enveloppe, écart {variation:+.1%} > seuil ; torseur "
                        f"lu dans {name})"
                    )
                    entry["modele_lu"] = name
                    entry["e27"]["terme_gouvernant"] = (
                        f"{described['e27']['terme_gouvernant']} de {name} "
                        f"(enveloppe, {variation:+.1%})"
                    )
            out[state] = entry
    return out


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
    auxiliaries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Every torsor of the summary asked again to `resultats lire`, in the model it
    was read in (the reference, or a declared variant that governs, lot 49 ter)."""
    reference = d
    summary = _summary(ctx)
    by_name = {f.name: f for f in summary.families}
    checked = 0
    worst = 0.0
    failures: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}

    def _read(
        d: Deliverables,
        family: MemberFamily,
        info: FieldInfo,
        case: str,
        group: str | None,
        point: list[float],
        node: int,
        element: int | None,
        end: int | None,
    ) -> dict[str, float]:
        groups = (group,) if group else tuple(group_names(d.mesh, family.groups))
        answer = query(
            ctx,
            Query(
                groupes=groups,
                champ=info.key,
                cas=(case,),
                mode="point",
                point=tuple(point),
                disques=False,
                tolerance=LEVEL,
            ),
            deliverables=d,
        )
        found: dict[str, float] = {}
        for r in answer.rows:
            if r["noeud_med"] != node:
                continue
            if element is not None and (
                r["maille_med"] != element
                or (end is not None and r["extremite"] != end)
            ):
                continue
            if r["cas_ou_combinaison"].endswith("(min)"):
                continue
            found[r["composante"]] = float(r["valeur_si"])
        return found

    for t in torsors:
        family = by_name[t["famille"]]
        info = _info(infos, family)
        source = reference
        if t.get("modele_lu"):
            source = _auxiliary(ctx, auxiliaries or {}, t["modele_lu"])[0]
        lieu = t["lieu"]
        case = t["combinaison"]
        if t["position_mobile"]:
            case = f"{case}@{t['position_mobile']}"
        found: dict[str, float] = {}
        if lieu.get("interpolation"):
            interp = lieu["interpolation"]
            for node, end, weight, xyz in zip(
                interp["noeuds_med"],
                interp["extremites"],
                interp["poids"],
                interp["coordonnees_extremites_m"],
                strict=True,
            ):
                part = _read(
                    source,
                    family,
                    info,
                    case,
                    lieu["groupe"],
                    xyz,
                    node,
                    lieu["maille_med"],
                    end,
                )
                for comp, value in part.items():
                    found[comp] = found.get(comp, 0.0) + weight * value
        else:
            found = _read(
                source,
                family,
                info,
                case,
                lieu["groupe"],
                lieu["coordonnees_m"],
                lieu["noeud_med"],
                lieu["maille_med"],
                lieu["extremite"],
            )
        tee = family.tee_section
        if tee is not None:
            # Section en T (E25) : seule la barre est relue ; l'intégrale de bande est
            # contrôlée par l'équilibre d'une coupe (preuve de D1).
            for tee_part in tee.parts:
                if tee_part.beam in found:
                    found[f"{tee_part.beam}{BAR_SUFFIX}"] = found.pop(tee_part.beam)
        if "MFY" in found and "MFZ" in found:
            found[M_RES] = math.hypot(found["MFY"], found["MFZ"])
        if "VY" in found and "VZ" in found:
            found[V_RES] = math.hypot(found["VY"], found["VZ"])
        if "QX" in found and "QY" in found:
            found[V_RES] = math.hypot(found["QX"], found["QY"])
        scale = max((abs(v) for v in t["torseur_si"].values()), default=1.0) or 1.0
        for comp, value in t["torseur_si"].items():
            if tee is not None and comp in {p.beam for p in tee.parts}:
                skipped["section en T (bande)"] = (
                    skipped.get("section en T (bande)", 0) + 1
                )
                continue
            if "e27" in t and comp == t["colonne"]:
                skipped["M_dim (E27)"] = skipped.get("M_dim (E27)", 0) + 1
                continue
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
        "valeurs_non_relues": skipped,
        "note": "section en T : barre relue, bande contrôlée par l'équilibre d'une "
        "coupe ; M_dim (E27) : combinaison de deux modèles, ses termes relus par "
        "leurs propres torseurs ; ligne interpolée : ses deux extrémités relues",
        "ecart_relatif_max": worst,
        "tolerance": CROSS_TOLERANCE,
        "echecs": failures[:50],
        "verdict": "RÉUSSI" if not failures else "ÉCHEC",
    }


CUT_TOLERANCE = 1.0e-6
"""Relative gap admitted between the total moment of a cut and the equilibrium of the
free body (exact: the same nodal forces, lot 49 ter)."""


def cut_checks(
    d: Deliverables,
    infos: list[FieldInfo],
    summary: EngineeringSummarySection,
) -> dict[str, Any] | None:
    """Proof of the T sections (lot 49 ter, D1): equilibrium of the declared cuts."""
    from aster_expert.livrables.coupe import cut_equilibrium  # noqa: PLC0415

    found = []
    for family in summary.families:
        tee = family.tee_section
        for cut in tee.equilibrium_cuts if tee else ():
            entry = cut_equilibrium(d, infos, summary, family, cut)
            entry["famille"] = family.name
            entry["verdict"] = (
                "RÉUSSI" if entry["ecart_relatif"] <= CUT_TOLERANCE else "ÉCHEC"
            )
            found.append(entry)
    if not found:
        return None
    return {
        "controle": "équilibre d'une coupe de section en T (lot 49 ter, preuve de "
        "D1 ; CTL-005 étendu) : moment total de la coupe (barres + plaque sur toute la "
        "largeur) contre l'équilibre du corps libre (forces nodales, réactions, "
        "ressorts)",
        "tolerance": CUT_TOLERANCE,
        "coupes": found,
        "verdict": "RÉUSSI"
        if all(c["verdict"] == "RÉUSSI" for c in found)
        else "ÉCHEC",
    }


def derived_summary(
    ctx: ProjectContext, summary: EngineeringSummarySection
) -> dict[str, Any]:
    """Declaration and harness D of each derived model (lot 49 ter)."""
    from aster_expert.livrables.derives import CHECK_FILE, derived_root  # noqa: PLC0415

    out: dict[str, Any] = {}
    for m in summary.derived_models:
        conditions = [
            f"DDL_IMPO {' '.join(b.dofs)} = 0 sur "
            + (
                f"GROUP_NO {b.node_group}"
                if b.node_group
                else f"GROUP_MA {b.cell_group}"
            )
            for b in m.blocks
        ] + [
            f"LIAISON_SOLIDE sur {r.cell_group} ∩ chaque {r.per_member}"
            for r in m.rigid
        ]
        check = derived_root(ctx, m.name) / CHECK_FILE
        out[m.name] = {
            "nature": m.kind,
            "libelle": m.label,
            "objet": m.purpose,
            "conditions": " ; ".join(conditions),
            "cas_exclus": list(m.excluded_cases),
            "motif_exclusion": m.excluded_reason,
            "source": m.source,
            "controle": json.loads(check.read_text("utf-8"))
            if check.is_file()
            else None,
        }
    return out


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
    auxiliaries: dict[str, Any] = {}
    for family in summary.families:
        families.append(
            _family_pass(
                ctx, d, infos, family, combinations, med_sha, package, auxiliaries
            )
        )
    torsors = [t for f in families for t in f["torseurs"]]
    opposite_signs(torsors)
    identical_lines(torsors)
    service = evaluate_all(d, combinations, summary)
    balance = equilibrium_by_state(ctx, d, infos, combinations, package)
    checked = cross_check(ctx, d, infos, torsors, auxiliaries)
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
    if summary.derived_models:
        _dump(package / "modeles_derives.json", derived_summary(ctx, summary))
    cuts = cut_checks(d, infos, summary)
    if cuts:
        _dump(package / "equilibre_coupes.json", cuts)
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
    "CUT_TOLERANCE",
    "bands",
    "cut_checks",
    "cross_check",
    "derived_summary",
    "disjoint_zones",
    "equilibrium_by_state",
    "family_rows",
    "identical_lines",
    "opposite_signs",
    "step_ingenieur",
    "support_moments",
    "write_annexes",
]
