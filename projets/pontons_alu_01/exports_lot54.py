# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 54 for PONTONS-ALU-01: the final PRO geometry (P67, P68), from the tables
Code_Aster printed during the runs of this lot (units 31, 32, 33), recombined with the
houle of P69 and the rule P70 (`combinaisons_lot54`).

The files are those of lot 52 (`exports_lot51ter.export_variant`, `exports_lot52`), with:

- `combinaisons.csv` and `evenements.csv` under P69 (no impact) and P70, and a new file
  `incompatibilites.csv`: the forbidden pairs (mooring event, berthing event) that
  `recombiner.py` (`scripts/recombiner_lot54.py`) leaves out, as the decomposition does
  (joint maximisation of the mooring and berthing slots);
- `ancrage.csv` and `palee_equilibre.csv` of lot 51 ter (no sensitivity HU_S5: under
  P69 the design houle is the 5 kPa forfait itself; P71: reactions for the record);
- `geometrie_noeuds.csv` (lot 52) and the check that every diagonal of the long spans
  has the same length (P67);
- for B54: the displacement files of lot 53 (`deplacements_lot53`, with P69 and P70);
- `comparaison_B52_B54.csv`: per family (main beams, purlins, posts, diagonals, cap
  beams, ties, piles) N min, N max, My, Mz and V extremes, plus the anchoring of each
  pier and the abutment, for B52 of lot 52 recombined with P69 and P70 and for B54.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import json
import math
import random
import re
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51ter import (
    Event,
    brute_force,
    counts,
    envelope,
    event_rows,
    expanded_counts,
    governing,
    rule_rows,
)
from pontons_alu_01.combinaisons_lot54 import (
    POST_HALF_WIDTH,
    Incompatibility,
    branches_p70,
    check_rules,
    events_p69,
    expected_centres,
    forbidden_pairs,
    incompatibilities,
    magnitudes_p69,
    with_exclusions,
    zone_centres,
)
from pontons_alu_01.exports_lot51 import mesh_dump, sha256, write
from pontons_alu_01.exports_lot51quater import write_npz
from pontons_alu_01.exports_lot51ter import (
    Quantity,
    VariantData51ter,
    _arrays,
    _rows_of,
    build_model,
    comparison,
    comparison_columns,
    criterion_am1,
    criterion_linearity,
    criterion_pins,
    criterion_tp,
    export_variant,
    pier_totals,
    read_run,
    recombination_places,
)
from pontons_alu_01.exports_lot52 import (
    FAMILY_QUANTITIES,
    NODE_COLUMNS,
    WELD_LIMIT_MM,
    check_npz,
    family_extremes,
    fold_link_reactions,
    node_geometry,
    node_summary,
    troncon_places,
)
from pontons_alu_01.generation_lot51ter import (
    Values51ter,
    all_cases,
    applied_loads,
    concrete_volumes,
    zone_names,
)
from pontons_alu_01.geometrie_lot51ter import Geometry51ter, span_length
from pontons_alu_01.variantes_lot51ter import Variant51ter

FloatArray = NDArray[np.float64]
LOT = "lot54"
KN = 1e-3
FORCES_CSV_VARIANT = "B54"
SEED = 54
DRAWS = 36
MIN_JOINT_DRAWS = 12
"""Of the 36 extremes of the enumeration check, at least 12 governed in a branch holding
both a mooring and a berthing slot (consigne, P70)."""
P70_DRAWS = 3
CAP_WEIGHT_KN = 14.4
"""0,60 × 0,40 × 2,40 × 25 kN (consigne § Contrôles)."""
DIAGONAL_TOLERANCE_M = 1e-3
B52_CODE = "B52"
SCRIPTS = Path(__file__).resolve().parent / "scripts"
RECOMBINER = SCRIPTS / "recombiner_lot54.py"
FAMILIES54 = (
    ("PP", "poutres principales", ("POUTRES_PRINC",)),
    ("PANNES", "pannes", ("PANNES_SEC",)),
    ("MONT", "montants", ("MONTANTS",)),
    ("DIAG", "diagonales", ("DIAGONALES",)),
    ("CHEV", "chevêtres", ("CHEVETRES",)),
    ("LONG", "longrines", ("LONGRINES",)),
    ("PILES", "piles", ("PILES",)),
)
RULES_TEXT = (
    "Jeu B′ révisé et ELU accidentel (P49, P57, P59 ; houle P69 ; P70 : amarrage local ou rupture d'amarre "
    "jamais avec un accostage au même poste)"
)


# --------------------------------------------------------------------------- loading


def lot_events(ctx: ProjectContext, g: Geometry51ter) -> dict[str, Event]:
    data = {key: item.value for key, item in ctx.data().items().items()}
    return events_p69(
        magnitudes_p69(data),
        zones=zone_names(g),
        cleats=[n for n, _, _ in g.cleats],
        modules=list(g.modules()),
    )


def load_run(
    ctx: ProjectContext,
    v: Variant51ter,
    g: Geometry51ter,
    vals: Values51ter,
    entry: dict[str, Any],
) -> VariantData51ter:
    """The tables of a run (lot 54, or B52 of lot 52), its model with the link
    reactions folded (CA-036), the events of P69 and the branches of P70."""
    run_dir = Path(entry["execution"]["execution_dir"])
    tables = read_run(run_dir, g)
    dump = mesh_dump(ctx, Path(entry["maillage"]["med"]))
    model = build_model(dump, tables, g, v)
    fold_link_reactions(tables, model, g)
    ev = lot_events(ctx, g)
    return VariantData51ter(
        v,
        model,
        tables,
        g,
        all_cases(g),
        ev,
        branches_p70(ev, g),
        Path(entry["comm"]),
        vals,
        {m.name: m.span for m in g.members},
    )


def load(ctx: ProjectContext, code: str, state: dict[str, Any]) -> VariantData51ter:
    from pontons_alu_01.generation_lot54 import geometry_of, values  # noqa: PLC0415
    from pontons_alu_01.variantes_lot54 import variants  # noqa: PLC0415

    v = variants()[code]
    return load_run(ctx, v, geometry_of(v), values(ctx, v), state[code])


def load_b52(ctx: ProjectContext) -> VariantData51ter:
    """B52 of lot 52 (tables of its run, `resultats/lot52/etat.json`) under P69/P70."""
    from pontons_alu_01.generation_lot52 import geometry_of, values  # noqa: PLC0415
    from pontons_alu_01.variantes_lot52 import variants  # noqa: PLC0415

    state = json.loads((ctx.results_dir / "lot52" / "etat.json").read_text("utf-8"))
    v = variants()[B52_CODE]
    return load_run(ctx, v, geometry_of(v), values(ctx, v), state[B52_CODE])


def source_line(vd: VariantData51ter, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, géométrie PRO définitive (treillis régulier P67, chevêtres 0,60 × 0,40 P68 ; houle P69, "
        f"règle P70), variante {vd.variant.code} ({vd.variant.description}) : exécution {run}, .comm sha256 "
        f"{sha256(vd.comm)}, maillage sha256 {s['maillage']['med_sha256']}."
    )


# --------------------------------------------------------------------------- files


def incompatibility_rows(items: list[Incompatibility]) -> list[list[Any]]:
    return [
        [
            i.mooring,
            i.berthing,
            i.side,
            i.cleat,
            i.x_cleat,
            i.zone,
            i.x_zone,
            i.distance,
        ]
        for i in sorted(items, key=lambda i: (i.cleat, i.side, i.mooring, i.berthing))
    ]


def export(
    vd: VariantData51ter,
    state: dict[str, Any],
    out: Path,
    *,
    source: str,
    forces_csv: bool,
) -> tuple[dict[str, int], dict[str, Any]]:
    """The files of lot 52 for one variant, under P69 and P70."""
    files, details = export_variant(
        vd, state, out, source=source, forces_csv=forces_csv
    )
    tally = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    items = incompatibilities(vd.ev, vd.g)
    free = counts(with_exclusions(vd.bs, set()))
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        f"{source} {RULES_TEXT} en règles : une combinaison = une option par emplacement d'une branche ; "
        "option = « événement×facteur » (evenements.csv) ou ∅. Houle : HU, HD (caractéristiques), HU_F à l'ELS "
        "fréquent ; aucun impact. Q et QD : dispositions défavorables par modules (lignes d'influence, colonne "
        "portee de evenements.csv). P70 : une combinaison qui réunit les deux événements d'une ligne "
        "d'incompatibilites.csv n'existe pas ; effectif_branche et effectif_dispositions en tiennent compte. "
        "Effectifs en règles : "
        + ", ".join(f"{s} {n}" for s, n in tally.items())
        + f", total {sum(tally.values())} (sans P70 : {sum(free.values())}) ; avec les 63 dispositions de Q et "
        "de QD comptées : "
        + ", ".join(f"{s} {n}" for s, n in expanded.items())
        + f", total {sum(expanded.values())}. recombiner.py les énumère.",
        [
            "etat_limite",
            "branche",
            "emplacement",
            "action",
            "nombre_options",
            "effectif_branche",
            "effectif_dispositions",
            "options",
        ],
        rule_rows(vd.bs, vd.ev),
    )
    files["evenements.csv"] = write(
        out / "evenements.csv",
        f"{source} Événements des actions (valeurs caractéristiques) : coefficient appliqué au cas élémentaire "
        "unitaire (kN sur 1 kN, kN/m sur 1 kN/m, kPa sur 1 kPa). portee : « fixe » ou « module Mk » (Q et QD, "
        "chaque module chargé ou non, choix défavorable). Houle (P69) : HU = 5,0 × (HU_TUBES + HU_PANNES + "
        "HU_PLATELAGE), HD = 5,0 × HD_TABLIER, HU_F = 2,728 HU_TUBES + 2,516 HU_PANNES + 2,425 HU_PLATELAGE "
        "(ELS fréquent) ; aucun impact. G_DEJ_090 = 0,9 × (G1 + G2) + DEJ, G_DEJ_100 = G1 + G2 + DEJ (P49).",
        ["action", "evenement", "portee", "cas", "coefficient"],
        event_rows(vd.ev),
    )
    files["incompatibilites.csv"] = write(
        out / "incompatibilites.csv",
        f"{source} P70 : paires d'événements interdites dans une même combinaison, un amarrage local (AML_) ou "
        "une rupture d'amarre (AMF_) et un accostage (AC_ ou ACA_) de la même rive, centre de la zone "
        f"d'accostage à moins de {POST_HALF_WIDTH:g} m du taquet en X (demi-largeur de poste de 3,20 m). AM1 et "
        "AM2 restent combinables avec AC et ACA. Centres : début Xd + 0,5, milieu (Xd + Xf)/2, fin Xf − 0,5, "
        "PTk au milieu, PF 38,85 + Lpf − 0,5. Unités : m.",
        [
            "evenement_amarrage",
            "evenement_accostage",
            "rive",
            "taquet",
            "x_taquet",
            "zone",
            "x_centre_zone",
            "distance_x",
        ],
        incompatibility_rows(items),
    )
    shutil.copyfile(RECOMBINER, out / "recombiner.py")
    details["npz"] = write_npz(vd, out / "efforts_elementaires.npz")
    nodes = node_geometry(vd.variant, vd.g)  # type: ignore[arg-type]
    files["geometrie_noeuds.csv"] = write(
        out / "geometrie_noeuds.csv",
        f"{source} Unités : m (cotes NGF, coordonnées), mm (jeu, zone de soudure). Un croisement par liaison "
        "rigide du tablier : panne/montant et panne/diagonale (LR_, la panne pose sur la barre, P64), "
        "panne/panne de rive du porte-à-faux (LR_ de PF), montant/poutre (LM_, montant soudé sur le flanc de la "
        "poutre principale). Montants des grandes travées à Xd + k × 1,25 (P67). Cotes de dessus et de dessous "
        "= axe ± demi-cote extérieure du tube. jeu_mm : dessous de la barre du dessus − dessus de la barre du "
        "dessous (< 0 : recouvrement) ; pour montant/poutre, plus petite marge du montant dans la hauteur du "
        "flanc. zone_soudure_mm : largeur du montant + 2 × 30 mm (bhaz, EN 1999-1-1, 6.1.6.3, P63), à comparer "
        f"aux {WELD_LIMIT_MM:g} mm de la poutre.",
        list(NODE_COLUMNS),
        [[r[c] for c in NODE_COLUMNS] for r in nodes],
    )
    details["geometrie_noeuds"] = node_summary(nodes)
    details["diagonales"] = check_diagonals(vd)
    return files, details


# --------------------------------------------------------------------------- checks


def check_diagonals(vd: VariantData51ter) -> dict[str, Any]:
    """P67: length of every diagonal of the long spans, end to end, from the nodes of
    the mesh (model coordinates)."""
    long_spans = {s.name for s in vd.g.spans if s.nature == "grande"}
    lengths: dict[str, float] = {}
    for m in vd.g.family("DIAGONALES"):
        if m.span not in long_spans:
            continue
        nodes = {
            n for e in vd.model.elements.values() if e.group == m.name for n in e.nodes
        }
        pts = [np.asarray(vd.model.coords[n - 1][:3], dtype=float) for n in nodes]
        ends = (min(pts, key=lambda p: p[1]), max(pts, key=lambda p: p[1]))
        lengths[m.name] = float(np.linalg.norm(ends[1] - ends[0]))
    spread = max(lengths.values()) - min(lengths.values())
    return {
        "nombre": len(lengths),
        "longueur_min_m": min(lengths.values()),
        "longueur_max_m": max(lengths.values()),
        "ecart_m": spread,
        "reussi": spread <= DIAGONAL_TOLERANCE_M,
    }


def check_cap_weight(vd: VariantData51ter) -> dict[str, Any]:
    """Self-weight of one cap beam: section and density read in the `.comm`, length
    from the mesh nodes of CHEV_P1_C1, against 0,60 × 0,40 × 2,40 × 25 kN."""
    text = vd.comm.read_text("utf-8")
    sec = re.search(
        r'GROUP_MA="CHEVETRES", SECTION="RECTANGLE", CARA=\("HY", "HZ"\), VALE=\(([^,]+), ([^)]+)\)',
        text,
    )
    rho = re.search(
        r"BETON = DEFI_MATERIAU\(ELAS=_F\(E=[^,]+, NU=[^,]+, RHO=([^)]+)\)", text
    )
    if sec is None or rho is None:
        message = "section des chevêtres ou masse volumique du béton absente du .comm"
        raise ValueError(message)
    hy, hz, density = float(sec.group(1)), float(sec.group(2)), float(rho.group(1))
    out: dict[str, Any] = {
        "HY_m": hy,
        "HZ_m": hz,
        "RHO_kg_m3": density,
        "chevetres": {},
    }
    worst = 0.0
    for m in vd.g.family("CHEVETRES"):
        length = sum(
            float(
                np.linalg.norm(
                    np.asarray(vd.model.coords[e.nodes[1] - 1][:3], dtype=float)
                    - np.asarray(vd.model.coords[e.nodes[0] - 1][:3], dtype=float)
                )
            )
            for e in vd.model.elements.values()
            if e.group == m.name
        )
        weight = density * 9.81 * hy * hz * length * KN
        rel = abs(weight - CAP_WEIGHT_KN) / CAP_WEIGHT_KN
        worst = max(worst, rel)
        out["chevetres"][m.name] = {"longueur_m": length, "poids_kN": weight}
    out["attendu_kN"] = CAP_WEIGHT_KN
    out["ecart_relatif_max"] = worst
    out["reussi"] = worst <= 0.01
    return out


def check_resultants_p69(vd: VariantData51ter) -> dict[str, Any]:
    """Resultants of HU, HD and HU_F: (a) Σ coefficient × declared resultant of the
    unit cases against coefficient × width × loaded length; (b) the same against the
    vertical reactions of the run (abutment + soil of the piers)."""
    loads = applied_loads(vd.vals, vd.g)
    supports = [
        vd.model.group_nodes["APP_CULEE_YM"][0],
        vd.model.group_nodes["APP_CULEE_YP"][0],
    ]
    soil = pier_totals(vd)

    def reaction(case: str) -> float:
        abut = sum(vd.tables.reac[case][n][2] for n in supports)
        return float(abut + soil[case].sum())

    length = sum(span_length(vd.g, s.name) for s in vd.g.spans)
    widths = {
        "HU_TUBES": 2 * vd.vals.width_tube,
        "HU_PANNES": 4 * vd.vals.width_purlin,
        "HU_PLATELAGE": vd.vals.width_planks,
        "HD_TABLIER": -vd.vals.width_deck_top,
    }
    out: dict[str, Any] = {"longueur_chargee_m": length, "largeurs_m": widths}
    for name in ("HU", "HD", "HU_F"):
        e = vd.ev[name]
        declared = sum(c * loads[k]["DZ"] for k, c in e.coefficients.items())
        reactions = sum(c * reaction(k) for k, c in e.coefficients.items())
        formula = sum(c * widths[k] for k, c in e.coefficients.items()) * length * 1e3
        out[name] = {
            "coefficients_kPa": dict(e.coefficients),
            "declaree_N": declared,
            "formule_N": formula,
            "reactions_N": reactions,
            "ecart_relatif_formule": abs(declared - formula) / abs(formula),
            "ecart_relatif_reactions": abs(declared + reactions) / abs(declared),
        }
    out["reussi"] = all(
        v_["ecart_relatif_formule"] <= 1e-6 and v_["ecart_relatif_reactions"] <= 1e-6
        for k, v_ in out.items()
        if isinstance(v_, dict) and "declaree_N" in v_
    )
    return out


def _recombiner(out: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot54", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    return rec


def _forbidden_in(name: str, forbidden: set[frozenset[str]]) -> list[tuple[str, str]]:
    """Forbidden pairs named in a combination label."""
    parts = [
        p.split("[", 1)[0].rsplit("×", 1)[0]
        for p in name.split(": ", 1)[-1].split(" + ")
    ]
    return [
        (a, b)
        for a, b in itertools.combinations(parts, 2)
        if frozenset((a, b)) in forbidden
    ]


def check_enumeration(
    out: Path,
    vd: VariantData51ter,
    *,
    seed: int = SEED,
) -> dict[str, Any]:
    """36 extremes drawn at random (seed 54), at least 12 of them governed in a branch
    holding both a mooring and a berthing slot (drawing goes on until then, the other
    draws being skipped once 24 are kept): the decomposition against (a) the
    delivered recombiner.py, combination by combination, and (b) the explicit
    enumeration of every pattern (`brute_force`), both with the pairs of P70 left
    out; no governing combination holds a forbidden pair."""
    rec = _recombiner(out)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    forbidden_csv = rec.read_forbidden(out)
    forbidden = forbidden_pairs(incompatibilities(vd.ev, vd.g))
    places = recombination_places(vd)
    rows = _rows_of(vd, ("POUTRES_PRINC", "PILES", "CHEVETRES", "LONGRINES"))
    places.append(("MFZ barres", _arrays(vd, rows, 5), [f"{e}/{n}" for e, n in rows]))
    places += troncon_places(vd)
    rng = random.Random(seed)
    checks: list[dict[str, Any]] = []
    tries = 0
    while len(checks) < DRAWS:
        tries += 1
        label, f, where = places[rng.randrange(len(places))]
        q = rng.randrange(len(where))
        state = rng.choice(("ELU_fondamental", "ELU_accidentel", "ELS_caracteristique"))
        sign = rng.choice((1.0, -1.0))
        ext = envelope(
            vd.bs, vd.ev, {c: a[q : q + 1] for c, a in f.items()}, state, sign=sign
        )
        branch = vd.bs[ext.choice[0][0]]
        joint = bool(branch.exclusions)
        n_joint = sum(1 for c in checks if c["branche_AM_AC"])
        if not joint and len(checks) - n_joint >= DRAWS - MIN_JOINT_DRAWS:
            continue
        values_q = {c: float(f[c][q]) for c in vd.cases}
        brute = rec.extremes(
            [r for r in rules if r[0] == state], events_csv, values_q, forbidden_csv
        )[state]
        reference = brute[0] if sign > 0 else brute[2]
        explicit = [
            brute_force(b, vd.ev, values_q, sign) for b in vd.bs if b.state == state
        ]
        exhaustive = max(explicit) if sign > 0 else min(explicit)
        value = float(ext.value[0])
        rel = abs(value - reference) / max(abs(reference), 1e-300)
        rel2 = abs(value - exhaustive) / max(abs(exhaustive), 1e-300)
        name = governing(vd.bs, vd.ev, ext, 0)[0]
        checks.append(
            {
                "grandeur": label,
                "lieu": where[q],
                "etat_limite": state,
                "extreme": "max" if sign > 0 else "min",
                "branche": f"{branch.state}/{branch.name}",
                "branche_AM_AC": joint,
                "decomposition": value,
                "recombiner": reference,
                "enumeration_explicite": exhaustive,
                "ecart_relatif_recombiner": rel,
                "ecart_relatif_explicite": rel2,
                "combinaison_decomposition": name,
                "combinaison_recombiner": brute[1] if sign > 0 else brute[3],
                "paires_interdites_dans_la_combinaison": _forbidden_in(name, forbidden),
                "reussi": rel <= 1e-9
                and rel2 <= 1e-9
                and not _forbidden_in(name, forbidden),
            }
        )
    return {
        "tirages": tries,
        "extremes": len(checks),
        "dans_branches_AM_AC": sum(1 for c in checks if c["branche_AM_AC"]),
        "ecart_relatif_max_recombiner": max(
            c["ecart_relatif_recombiner"] for c in checks
        ),
        "ecart_relatif_max_explicite": max(
            c["ecart_relatif_explicite"] for c in checks
        ),
        "reussi": all(c["reussi"] for c in checks)
        and sum(1 for c in checks if c["branche_AM_AC"]) >= MIN_JOINT_DRAWS,
        "detail": checks,
    }


def check_counts(out: Path, vd: VariantData51ter) -> dict[str, Any]:
    """Counts by formula, by recombiner.py and by explicit enumeration of the rules
    (allowed choices only, without duplicates); breaches of B′, P57 and of the
    structure of P70; the combinations P70 leaves out."""
    rec = _recombiner(out)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    forbidden_csv = rec.read_forbidden(out)
    forbidden = forbidden_pairs(incompatibilities(vd.ev, vd.g))
    formula = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    seen = set()
    total = 0
    breaches = 0
    for b in vd.bs:
        for picks in itertools.product(*(range(len(s.options)) for s in b.slots)):
            if not b.allows(picks):
                continue
            names = [b.slots[k].options[i][0] for k, i in enumerate(picks)]
            named = [n for n in names if n is not None]
            breaches += sum(
                1
                for a, c in itertools.combinations(named, 2)
                if frozenset((a, c)) in forbidden
            )
            seen.add(
                (
                    b.state,
                    *sorted(
                        (n, b.slots[k].options[i][1])
                        for k, i in enumerate(picks)
                        if (n := b.slots[k].options[i][0]) is not None
                    ),
                )
            )
            total += 1
    free = counts(with_exclusions(vd.bs, set()))
    result: dict[str, Any] = {
        "formule": formula,
        "formule_total": sum(formula.values()),
        "recombiner": rec.count(rules, forbidden_csv),
        "dispositions_formule": expanded,
        "dispositions_total": sum(expanded.values()),
        "dispositions_recombiner": rec.count(rules, forbidden_csv, events_csv),
        "enumerees": total,
        "distinctes": len(seen),
        "paires_interdites_enumerees": breaches,
        "sans_P70_total": sum(free.values()),
        "exclues_par_P70": sum(free.values()) - sum(formula.values()),
        "paires_evenements_interdites": len(forbidden),
        "paires_csv": len(forbidden_csv),
        "branches_avec_P70": sum(1 for b in vd.bs if b.exclusions),
        "exclusions": check_rules(vd.bs, vd.ev),
    }
    result["reussi"] = (
        result["recombiner"] == formula
        and result["dispositions_recombiner"] == expanded
        and total == len(seen) == sum(formula.values())
        and breaches == 0
        and forbidden == forbidden_csv
        and not result["exclusions"]
    )
    return result


def check_centres(vd: VariantData51ter) -> dict[str, Any]:
    """The berthing zone centres of the geometry against those written in P70."""
    got, want = zone_centres(vd.g), expected_centres(vd.g)
    worst = max(abs(got[z] - want[z]) for z in got)
    return {
        "zones": len(got),
        "ecart_max_m": worst,
        "reussi": worst <= 1e-9 and got.keys() == want.keys(),
    }


def p70_effect(vd: VariantData51ter, *, seed: int = SEED) -> dict[str, Any]:
    """Where P70 changes an extreme: every element end of the bars, N, MFY and MFZ,
    three states, both senses; the envelope with and without the rule. Three of the
    changed extremes drawn at random (seed 54): the forbidden pair that gave the
    extreme without the rule, the value with the rule and its combination."""
    free = with_exclusions(vd.bs, set())
    forbidden = forbidden_pairs(incompatibilities(vd.ev, vd.g))
    rows = _rows_of(
        vd,
        (
            "POUTRES_PRINC",
            "MONTANTS",
            "DIAGONALES",
            "PANNES_SEC",
            "PANNE_RIVE",
            "CHEVETRES",
            "LONGRINES",
            "PILES",
        ),
    )
    where = [f"élément {e} nœud {n} ({vd.model.elements[e].member})" for e, n in rows]
    changed: list[dict[str, Any]] = []
    n_values = 0
    for comp, k in (("N", 0), ("MFY", 4), ("MFZ", 5)):
        f = _arrays(vd, rows, k)
        for state in ("ELU_fondamental", "ELU_accidentel", "ELS_caracteristique"):
            for sign in (1.0, -1.0):
                a = envelope(vd.bs, vd.ev, f, state, sign=sign)
                b = envelope(free, vd.ev, f, state, sign=sign)
                n_values += a.value.size
                for q in np.nonzero(
                    np.abs(a.value - b.value) > 1e-9 * np.maximum(np.abs(b.value), 1.0)
                )[0]:
                    without_name = governing(free, vd.ev, b, int(q))[0]
                    pairs = _forbidden_in(without_name, forbidden)
                    if not pairs:
                        continue
                    changed.append(
                        {
                            "lieu": where[int(q)],
                            "composante": comp,
                            "etat_limite": state,
                            "extreme": "max" if sign > 0 else "min",
                            "sans_regle": float(b.value[q]),
                            "combinaison_sans_regle": without_name,
                            "paire_interdite": pairs,
                            "avec_regle": float(a.value[q]),
                            "combinaison_avec_regle": governing(
                                vd.bs, vd.ev, a, int(q)
                            )[0],
                        }
                    )
    rng = random.Random(seed)
    drawn = rng.sample(changed, min(P70_DRAWS, len(changed)))
    for d in drawn:
        d["ecart_relatif"] = abs(d["avec_regle"] - d["sans_regle"]) / abs(
            d["sans_regle"]
        )
        d["paires_interdites_avec_regle"] = _forbidden_in(
            d["combinaison_avec_regle"], forbidden
        )
    return {
        "valeurs_examinees": n_values,
        "extremes_changes": len(changed),
        "tirages": drawn,
        "reussi": all(not d["paires_interdites_avec_regle"] for d in drawn)
        and all(
            (d["avec_regle"] <= d["sans_regle"])
            if d["extreme"] == "max"
            else (d["avec_regle"] >= d["sans_regle"])
            for d in drawn
        ),
    }


# --------------------------------------------------------------------------- comparison


def family_columns54() -> tuple[str, ...]:
    return tuple(f"FAM_{k}_{q}" for k, _, _ in FAMILIES54 for q in FAMILY_QUANTITIES)


def anchoring_quantities(details: dict[str, Any]) -> dict[str, Quantity]:
    """Anchoring of each pier (ELU and characteristic SLS), from the summaries of
    `anchoring_rows` (`export_variant`)."""
    out: dict[str, Quantity] = {}
    for pier, by_state in details["ancrage"].items():
        for state, tag in (
            ("ELU_fondamental", "ELU"),
            ("ELS_caracteristique", "ELS_C"),
        ):
            s = by_state[state]
            out[f"ANCRAGE_{pier}_{tag}"] = Quantity(
                f"effort d'ancrage requis {pier}, {state}",
                "kN",
                s["ancrage_requis_N"] * KN,
                state,
                s["combinaison"],
                pier,
            )
    return out


def comparison_rows(b52: dict[str, Any], b54: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for key, q in b54.items():
        old = b52.get(key)
        if old is None:
            continue
        a, b = float(q["value"]), float(old["value"])
        rel: Any = (a - b) / abs(b) if b != 0.0 and math.isfinite(b) else ""
        rows.append(
            [
                key,
                q["label"],
                q["unit"],
                b,
                a,
                a - b,
                rel,
                old["state"],
                old["combination"],
                old["where"],
                q["state"],
                q["combination"],
                q["where"],
            ]
        )
    return rows


# --------------------------------------------------------------------------- steps


def run_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any]
) -> dict[str, Any]:
    root = ctx.results_dir / LOT / "exports"
    t0 = time.perf_counter()
    vd = load(ctx, code, state)
    load_s = time.perf_counter() - t0
    out = root / code
    src = source_line(vd, state)
    t1 = time.perf_counter()
    files, details = export(
        vd, state, out, source=src, forces_csv=code == FORCES_CSV_VARIANT
    )
    t2 = time.perf_counter()
    comp = comparison(vd)
    fam = family_extremes(vd, FAMILIES54)
    anchor = anchoring_quantities(details)
    t3 = time.perf_counter()
    info: dict[str, Any] = {
        "statut": "calculée",
        "fichiers": files,
        "effectifs": counts(vd.bs),
        "effectifs_dispositions": expanded_counts(vd.bs, vd.ev),
        "volumes_beton_m3": concrete_volumes(vd.vals, vd.g),
        "cotes_m_ngf": vd.g.levels,
        "details": details,
        "comparaison": {
            k: dataclasses.asdict(q) for k, q in {**comp, **fam, **anchor}.items()
        },
        "temps_s": {
            "lecture_tables": load_s,
            "exports": t2 - t1,
            "comparaison": t3 - t2,
            "recombinaison": t3 - t1,
        },
        "controle_resultantes_houle": check_resultants_p69(vd),
        "controle_poids_chevetre": check_cap_weight(vd),
        "controle_linearite": criterion_linearity(vd),
        "controle_AM1": criterion_am1(vd),
        "controle_TP": criterion_tp(vd),
        "controle_appuis_axe": criterion_pins(vd),
        "controle_centres_P70": check_centres(vd),
    }
    if code == FORCES_CSV_VARIANT:
        t4 = time.perf_counter()
        info["controle_enumeration"] = check_enumeration(out, vd)
        info["controle_effectifs"] = check_counts(out, vd)
        info["temps_s"]["enumeration"] = time.perf_counter() - t4
        t5 = time.perf_counter()
        info["effet_P70"] = p70_effect(vd)
        info["temps_s"]["effet_P70"] = time.perf_counter() - t5
        info["controle_npz"] = check_npz(out)
        t6 = time.perf_counter()
        info["deplacements"] = displacements(ctx, vd, state, out)
        info["temps_s"]["deplacements"] = time.perf_counter() - t6
    return info


def run_b52(ctx: ProjectContext) -> dict[str, Any]:
    """B52 of lot 52 recombined with P69 and P70: families, anchoring, abutment."""
    from pontons_alu_01.exports_lot51ter import (  # noqa: PLC0415
        abutment_rows,
        anchoring_rows,
    )

    t0 = time.perf_counter()
    vd = load_b52(ctx)
    load_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    fam = family_extremes(vd, FAMILIES54)
    _, anchor = anchoring_rows(vd)
    _, abut = abutment_rows(vd)
    anchors = anchoring_quantities({"ancrage": anchor})
    t2 = time.perf_counter()
    return {
        "statut": "calculée",
        "regles": "P69, P70 (cas unitaires de l'exécution B52 du lot 52)",
        "comparaison": {
            k: dataclasses.asdict(q) for k, q in {**fam, **anchors}.items()
        },
        "culee": abut,
        "effectifs": counts(vd.bs),
        "temps_s": {"lecture_tables": load_s, "recombinaison": t2 - t1},
    }


def displacements(
    ctx: ProjectContext, vd: VariantData51ter, state: dict[str, Any], out: Path
) -> dict[str, Any]:
    """The displacement files of lot 53 for B54, under P69 and P70."""
    from pontons_alu_01 import deplacements_lot53 as d53  # noqa: PLC0415

    r = d53.compute(ctx, state, vd)
    synthesis = d53.synthesis_rows(r.vd, r.pts, r.qs, r.combos)
    cases = d53.exported_cases(r.vd)
    files = d53.write_exports(
        out,
        source_line(vd, state),
        r.pts,
        r.qs,
        r.unit,
        cases,
        r.ev_ext,
        r.combos,
        synthesis,
        relabel={
            "(evenements.csv du lot 52)": "(evenements.csv)",
            "(coefficients d'evenements.csv du lot 52, sans facteur partiel ni ψ)": "(coefficients d'evenements.csv, sans facteur partiel ni ψ)",
            "Extrêmes des combinaisons du lot 52 (règles de combinaisons.csv": "Extrêmes des combinaisons (règles de combinaisons.csv",
            "P49, P57, P59, P60, P61)": "P49, P57, P59, P69, P70 : paires d'incompatibilites.csv exclues)",
        },
    )
    return {
        "fichiers": files,
        "points": len(r.pts),
        "grandeurs": len(r.qs),
        "synthese": synthesis,
        "temps_s": r.timings,
        "plus_grands_DY": d53.largest(r.pts, r.qs, r.combos, r.ev_ext, 1),
        "plus_grands_DX": d53.largest(r.pts, r.qs, r.combos, r.ev_ext, 0),
        "controle_liaisons": d53.check_links(r.pts, r.unit),
        "controle_enumeration": d53.check_brute_force(r.vd, r.f, r.qs, r.pts, r.combos),
    }


def _job(repo_root: Path, code: str, state: dict[str, Any]) -> dict[str, Any]:
    from aster_expert.projet.context import load_project  # noqa: PLC0415

    ctx = load_project("pontons_alu_01", repo_root)
    if code == B52_CODE:
        return run_b52(ctx)
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
    jobs = [
        c for c in codes if "execution_dir" in state.get(c, {}).get("execution", {})
    ]
    if (ctx.results_dir / "lot52" / "etat.json").is_file():
        jobs.append(B52_CODE)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {code: pool.submit(_job, ctx.repo_root, code, state) for code in jobs}
        for code, fut in futures.items():
            summary[code] = fut.result()
            summary_path.write_text(
                json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n",
                "utf-8",
            )
            t = summary[code]["temps_s"]
            print(f"{code} : exports écrits, recombinaison {t['recombinaison']:.1f} s")
    if B52_CODE in summary and "B54" in summary:
        write_b52_b54(root, summary[B52_CODE], summary["B54"])
    write_variants(root, summary)


def write_b52_b54(root: Path, b52: dict[str, Any], b54: dict[str, Any]) -> None:
    keys = {
        *family_columns54(),
        *(k for k in b54["comparaison"] if k.startswith("ANCRAGE_")),
    }
    b54c = {k: q for k, q in b54["comparaison"].items() if k in keys}
    rows = comparison_rows(b52["comparaison"], b54c)
    write(
        root / "comparaison_B52_B54.csv",
        "PONTONS-ALU-01 : B52 (géométrie PRO du lot 52, montants à Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25, "
        "chevêtres 0,40 × 0,40 de Y = −1,05 à +1,05) recombiné avec les règles de ce lot (houle P69, P70), contre "
        "B54 (treillis régulier P67, chevêtres 0,60 × 0,40 prolongés à ±1,20, P68 ; mêmes règles). Par famille : "
        "N min, N max, My et Mz extrêmes en valeur absolue (signés), V max = √(VY² + VZ²), sur l'ELU fondamental, "
        "l'ELS caractéristique, l'ELS fréquent et l'ELU accidentel ; ANCRAGE_* : effort d'ancrage requis par palée "
        "(aucun ancrage modélisé, P71 : pour mémoire). ecart = B54 − B52, ecart_relatif = écart / |B52|. Unités : "
        "kN, kN·m.",
        [
            "grandeur",
            "libelle",
            "unite",
            "B52",
            "B54",
            "ecart",
            "ecart_relatif",
            "etat_B52",
            "combinaison_B52",
            "lieu_B52",
            "etat_B54",
            "combinaison_B54",
            "lieu_B54",
        ],
        rows,
    )


def write_variants(root: Path, summary: dict[str, Any]) -> None:
    from pontons_alu_01.generation_lot54 import geometry_of  # noqa: PLC0415
    from pontons_alu_01.variantes_lot54 import reference, variants  # noqa: PLC0415

    g = geometry_of(variants()[reference()])
    columns = (*comparison_columns(g), *family_columns54())
    rows: list[list[Any]] = []
    labels: dict[str, str] = {}
    for code, v in variants().items():
        info = summary.get(code)
        if info is None or info.get("statut") != "calculée":
            rows.append([code, v.description, "non calculée", *([""] * len(columns))])
            continue
        comp = info["comparaison"]
        rows.append(
            [
                code,
                v.description,
                "calculée",
                *(float(comp[c]["value"]) for c in columns),
            ]
        )
        labels.update({c: f"{comp[c]['label']} [{comp[c]['unit']}]" for c in columns})
    write(
        root / "comparaison_variantes.csv",
        "PONTONS-ALU-01, géométrie PRO définitive (P67, P68), houle P69, règle P70 : comparaison des variantes "
        "B54 et A54. Enveloppes du jeu B′ révisé et de l'ELU accidentel (P49, P57, P59), flèches de P51 et P62. "
        "Colonnes : " + " ; ".join(f"{k} = {labels.get(k, k)}" for k in columns) + ".",
        ["variante", "description", "statut", *columns],
        rows,
    )


__all__ = [
    "FAMILIES54",
    "check_cap_weight",
    "check_counts",
    "check_diagonals",
    "check_enumeration",
    "check_resultants_p69",
    "load",
    "load_b52",
    "p70_effect",
    "step_exports",
]
