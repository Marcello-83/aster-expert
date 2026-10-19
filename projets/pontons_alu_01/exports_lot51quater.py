# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Exports of lot 51 quater for PONTONS-ALU-01: the files of lot 51 ter recomputed with
the houle of P60 and the impact of P61 (`combinaisons_lot51quater`), from the unit cases
of the lot 51 ter runs (tables printed by Code_Aster, read again, never rerun).

What changes from lot 51 ter (`exports_lot51ter`, reused as is):

- the events and the rules (P60, P61); the decomposition by slot is unchanged;
- `ancrage.csv` gains the houle event of the governing combination (HU, HD, HU_IMP_Mk
  or aucun) and the sensitivity HU_S5 (5 kPa forfait, no decision) in separate
  columns; `palee_equilibre.csv` gains the HU_S5 columns;
- `efforts_elementaires.npz` (float32, numpy `savez_compressed`) replaces the CSV for
  the transmission; the CSV is written for B10 only;
- `comparaison_variantes.csv` gains the anchoring of each pier (P60/P61 and HU_S5) and
  the governing houle event of PP My, of the characteristic SLS deflection and of the
  anchoring.

Checks of the consigne (§ Contrôles): resultants of the events (declared loads and
reactions of the run), identity with lot 51 ter (combinations without houle; P56
coefficients through the rules of this lot give comparaison_variantes.csv of lot 51 ter
exactly), explicit enumeration on B10 for 36 extremes drawn at random.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import json
import random
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51quater import (
    HOULE_ACTIONS,
    IMPACT_CASES,
    branches,
    check_exclusions,
    events_p60_p61,
    events_s5,
    magnitudes_p60,
)
from pontons_alu_01.combinaisons_lot51ter import (
    STATES,
    Event,
    brute_force,
    counts,
    envelope,
    event_rows,
    expanded_counts,
    governing,
    rule_rows,
)
from pontons_alu_01.exports_lot51 import EFGE, number, sha256, write
from pontons_alu_01.exports_lot51ter import (
    Governed,
    Quantity,
    VariantData51ter,
    _arrays,
    _rows_of,
    comparison,
    comparison_columns,
    export_variant,
    load_variant,
    pier_rows,
    pier_totals,
    pile_ends,
    pin_results,
    recombination_places,
)
from pontons_alu_01.generation_lot51ter import WAVE_CASES, applied_loads, zone_names
from pontons_alu_01.geometrie_lot51ter import geometry, span_length
from pontons_alu_01.variantes_lot51ter import variants

FloatArray = NDArray[np.float64]
LOT = "lot51quater"
KN = 1e-3
FORCES_CSV_VARIANT = "B10"
"""efforts_elementaires.csv is written (and delivered) for this variant only."""
DRAWS = 36
SEED = 51


# --------------------------------------------------------------------------- variants


@dataclasses.dataclass
class Variant51quater:
    """The data of one variant under three sets of events: P60/P61 (the lot), P56
    through the rules of this lot (identity with lot 51 ter), HU_S5 (sensitivity)."""

    vd: VariantData51ter
    p56: VariantData51ter
    s5: VariantData51ter
    load_s: float


def _event_sets(
    ctx: ProjectContext, vd: VariantData51ter
) -> tuple[dict[str, Event], dict[str, Event]]:
    data = {key: item.value for key, item in ctx.data().items().items()}
    kw: dict[str, Any] = {
        "zones": zone_names(vd.g),
        "cleats": [n for n, _, _ in vd.g.cleats],
        "modules": list(vd.g.modules()),
    }
    m = magnitudes_p60(data, vd.variant.purlin_side_mm)
    return events_p60_p61(m, **kw), events_s5(m, **kw)


def load(ctx: ProjectContext, code: str, state: dict[str, Any]) -> Variant51quater:
    """Tables of the lot 51 ter run of `code` (state of scripts/lot51ter.py) and the
    three sets of events."""
    t0 = time.perf_counter()
    base = load_variant(ctx, code, state)
    load_s = time.perf_counter() - t0
    ev, ev_s5 = _event_sets(ctx, base)
    return Variant51quater(
        vd=dataclasses.replace(base, ev=ev, bs=branches(ev)),
        p56=dataclasses.replace(base, bs=branches(base.ev)),
        s5=dataclasses.replace(base, ev=ev_s5, bs=branches(ev_s5)),
        load_s=load_s,
    )


def source_line(vd: VariantData51ter, state: dict[str, Any]) -> str:
    s = state[vd.variant.code]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, lot 51 quater (houle P60 « tablier noyé », impact P61 ; cas unitaires du lot 51 ter "
        f"recombinés, aucune réexécution), variante {vd.variant.code} ({vd.variant.description}) : exécution "
        f"{run} du lot 51 ter, .comm sha256 {sha256(vd.comm)}, maillage sha256 {s['maillage']['med_sha256']}."
    )


# --------------------------------------------------------------------------- houle


def houle_of(combination: str, ev: dict[str, Event]) -> str:
    """The houle event named in a combination (« état: E1[..]×f + E2×f ») or « aucun »."""
    text = combination.split(": ", 1)[-1]
    for part in text.split(" + "):
        name = part.split("[", 1)[0].rsplit("×", 1)[0]
        if name in ev and ev[name].action in HOULE_ACTIONS:
            return name
    return "aucun"


def is_wave_case(case: str) -> bool:
    return any(case == w or case.startswith(f"{w}_M") for w in WAVE_CASES)


def wave_share(gov: Governed, f: dict[str, FloatArray], q: int) -> tuple[float, float]:
    """(contribution of the houle, its share of the variable actions) to quantity q in
    the governing combination; the impacts act on the module cases."""
    permanent = {"G1", "G2", "DEJ"}
    h = sum(c * f[k][q] for k, c in gov.coefficients.items() if is_wave_case(k))
    var = sum(c * f[k][q] for k, c in gov.coefficients.items() if k not in permanent)
    return float(h), (float(h / var) if var != 0.0 else float("nan"))


def governed(
    vd: VariantData51ter,
    f: dict[str, FloatArray],
    state: str,
    sign: float,
    where: list[str],
) -> list[Governed]:
    ext = envelope(vd.bs, vd.ev, f, state, sign=sign)
    out = []
    for q in range(len(where)):
        name, coefs = governing(vd.bs, vd.ev, ext, q)
        out.append(Governed(float(ext.value[q]), state, name, coefs, where[q]))
    return out


# --------------------------------------------------------------------------- lot files


ANCHOR_STATES = ("ELU_fondamental", "ELS_caracteristique")


def anchoring_rows(v: Variant51quater) -> tuple[list[list[Any]], dict[str, Any]]:
    """ancrage.csv of lot 51 ter, with the governing houle event and HU_S5."""
    vd = v.vd
    totals = pier_totals(vd)
    piers = list(vd.g.piers)
    ends = pile_ends(vd)
    pile_f = _arrays(vd, [(e, n) for _, _, _, n, e in ends], 0)
    pile_where = [f"{p} {pl} {pos}" for p, pl, pos, _, _ in ends]
    rows: list[list[Any]] = []
    summary: dict[str, Any] = {}
    for state in ANCHOR_STATES:
        govs = governed(vd, totals, state, -1.0, piers)
        govs_s5 = governed(v.s5, totals, state, -1.0, piers)
        piles = governed(vd, pile_f, state, 1.0, pile_where)
        piles_s5 = governed(v.s5, pile_f, state, 1.0, pile_where)
        for q, pier in enumerate(piers):
            g, g5 = govs[q], govs_s5[q]
            anchor, anchor5 = max(0.0, -g.value), max(0.0, -g5.value)
            h, share = wave_share(g, totals, q)
            h5, share5 = wave_share(g5, totals, q)
            event = houle_of(g.combination, vd.ev)
            rows += [
                [
                    pier,
                    state,
                    "SRz_min",
                    "semelle (Σ des forces du sol, > 0 vers le haut)",
                    g.value,
                    "N",
                    g.combination,
                    event,
                    g5.value,
                    g5.combination,
                    "",
                ],
                [
                    pier,
                    state,
                    "ancrage_requis",
                    "palée",
                    anchor,
                    "N",
                    g.combination,
                    event,
                    anchor5,
                    g5.combination,
                    "max(0 ; −ΣRz min)",
                ],
                [
                    pier,
                    state,
                    "part_HU",
                    "palée, combinaison de SRz_min",
                    share,
                    "-",
                    g.combination,
                    event,
                    share5,
                    g5.combination,
                    f"contribution de la houle (événement {event}) à ΣRz : {number(h)} N, rapportée à celle de "
                    f"toutes les actions variables ; HU_S5 : {number(h5)} N",
                ],
            ]
            summary.setdefault(pier, {})[state] = {
                "SRz_min_N": g.value,
                "ancrage_requis_N": anchor,
                "combinaison": g.combination,
                "evenement_houle": event,
                "houle_N": h,
                "part_houle": share,
                "SRz_min_HU_S5_N": g5.value,
                "ancrage_requis_HU_S5_N": anchor5,
                "combinaison_HU_S5": g5.combination,
            }
            for k, (p, pile, pos, node, e) in enumerate(ends):
                if p != pier:
                    continue
                pg, pg5 = piles[k], piles_s5[k]
                rows.append(
                    [
                        pier,
                        state,
                        "N_traction_max",
                        f"pile {pile}, {pos} (élément {e}, nœud {node})",
                        pg.value,
                        "N",
                        pg.combination,
                        houle_of(pg.combination, vd.ev),
                        pg5.value,
                        pg5.combination,
                        "traction" if pg.value > 0.0 else "pas de traction (N max ≤ 0)",
                    ]
                )
    return rows, summary


def pier_rows_s5(v: Variant51quater) -> tuple[list[list[Any]], dict[str, Any]]:
    """palee_equilibre.csv of lot 51 ter with the HU_S5 columns appended."""
    rows, summary = pier_rows(v.vd)
    rows5, summary5 = pier_rows(v.s5)
    out = []
    for row, row5 in zip(rows, rows5, strict=True):
        n = len(STATES)
        # colonnes 7 à 7 + 2n : (SRz_min, combinaison) par état limite
        elu_f5 = row5[7 : 7 + 2 * n][0:2]
        els_c5 = row5[7 : 7 + 2 * n][2 * STATES.index("ELS_caracteristique") :][:2]
        elu_a5 = row5[7 : 7 + 2 * n][2 * STATES.index("ELU_accidentel") :][:2]
        out.append([*row, *elu_f5, *elu_a5, *els_c5, row5[-1]])
    for pier, s in summary.items():
        s["SRz_min_HU_S5"] = summary5[pier]["SRz_min"]
        s["lest_manquant_HU_S5_N"] = summary5[pier]["lest_manquant_N"]
    return out, summary


def force_tensor(
    vd: VariantData51ter,
) -> tuple[list[str], NDArray[np.int64], NDArray[np.int64], list[str], NDArray[Any]]:
    """Cases, element and node of each element end (every end Code_Aster printed in
    unit 31: aluminium bars, piles, ring), families, forces [case, end, component]."""
    keys = sorted(vd.tables.efge[vd.cases[0]])
    for c in vd.cases:
        if sorted(vd.tables.efge[c]) != keys:
            message = f"efforts : extrémités du cas {c} différentes de celles de {vd.cases[0]}"
            raise ValueError(message)
    forces = np.empty((len(vd.cases), len(keys), len(EFGE)), dtype=np.float64)
    for i, c in enumerate(vd.cases):
        table = vd.tables.efge[c]
        forces[i] = np.array([table[k] for k in keys])
    elements = np.array([e for e, _ in keys], dtype=np.int64)
    nodes = np.array([n for _, n in keys], dtype=np.int64)
    families = [
        vd.model.elements[e].family if e in vd.model.elements else "" for e, _ in keys
    ]
    return list(vd.cases), elements, nodes, families, forces


def write_npz(vd: VariantData51ter, path: Path) -> dict[str, Any]:
    cases, elements, nodes, families, forces = force_tensor(vd)
    np.savez_compressed(
        path,
        cas=np.array(cases),
        elements=elements.astype(np.int32),
        noeuds=nodes.astype(np.int32),
        composantes=np.array(EFGE),
        familles=np.array(families),
        efforts=forces.astype(np.float32),
    )
    return {
        "taille_octets": path.stat().st_size,
        "forme": list(forces.shape),
        "extremites": len(elements),
        "elements": len(set(elements.tolist())),
        "familles": sorted(set(families)),
        "ecart_float32_relatif_max": float(
            np.max(
                np.abs(forces.astype(np.float32).astype(np.float64) - forces)
                / np.maximum(np.abs(forces), 1e-30)
            )
        ),
    }


def export(
    v: Variant51quater,
    state: dict[str, Any],
    out: Path,
    *,
    source: str | None = None,
    forces_csv: bool | None = None,
) -> tuple[dict[str, int], dict[str, Any]]:
    """The files of lot 51 quater for one variant; lot 52 passes its source line and
    whether efforts_elementaires.csv is kept."""
    vd = v.vd
    src = source if source is not None else source_line(vd, state)
    if forces_csv is None:
        forces_csv = vd.variant.code == FORCES_CSV_VARIANT
    files, details = export_variant(vd, state, out, source=src, forces_csv=forces_csv)
    if not forces_csv:
        (out / "efforts_elementaires.csv").unlink(missing_ok=True)
    tally = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    files["combinaisons.csv"] = write(
        out / "combinaisons.csv",
        f"{src} Jeu B′ révisé et ELU accidentel (P49, P56 révisée par P60, P57, P59, P61) en règles : une "
        "combinaison = une option par emplacement d'une branche ; option = « événement×facteur » (evenements.csv) "
        "ou ∅. Houle : HU, HD (P60) ou l'un des six impacts HU_IMP_Mk (P61), alternatifs dans l'emplacement de la "
        "houle, à l'ELU fondamental et à l'ELS caractéristique seulement ; HU_F à l'ELS fréquent. Q et QD : "
        "dispositions défavorables par modules (lignes d'influence, colonne portee de evenements.csv). "
        "Effectifs en règles : "
        + ", ".join(f"{s} {n}" for s, n in tally.items())
        + f", total {sum(tally.values())} ; avec les 63 dispositions de Q et de QD comptées : "
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
        f"{src} Événements des actions (valeurs caractéristiques) : coefficient appliqué au cas élémentaire "
        "unitaire (kN sur 1 kN, kN/m sur 1 kN/m, kPa sur 1 kPa). portee : « fixe » ou « module Mk » (Q et QD, "
        "chaque module chargé ou non, choix défavorable). Houle (P60, tablier noyé) : HU, HD caractéristiques, "
        "HU_F fréquent (inchangé) ; impacts (P61, action HI) : HU_IMP_Mk = p_imp × (HU_TUBES_Mk + HU_PANNES_Mk + "
        "HU_PLATELAGE_Mk), un module à la fois ; G_DEJ_090 = 0,9 × (G1 + G2) + DEJ, G_DEJ_100 = G1 + G2 + DEJ "
        "(P49). La sensibilité HU_S5 n'est pas un événement de ces règles (ancrage.csv, palee_equilibre.csv).",
        ["action", "evenement", "portee", "cas", "coefficient"],
        event_rows(vd.ev),
    )
    pr, pier_summary = pier_rows_s5(v)
    files["palee_equilibre.csv"] = write(
        out / "palee_equilibre.csv",
        f"{src} Unités : m, m3, N. Une ligne par palée : volume de béton modélisé (angles de l'anneau comptés "
        "une fois), poids, poids déjaugé, ΣRz min du sol (> 0 vers le haut) par état limite avec sa "
        "combinaison (P60, P61), ressorts tendus dans la combinaison de l'ELU fondamental (sol linéaire, traction "
        "admise, P19), lest manquant = max(0 ; −ΣRz min ELU) / 0,9. Colonnes _HU_S5 : sensibilité sans décision "
        "(forfait AVP de 5 kPa sur HU_TUBES, HU_PANNES, HU_PLATELAGE à la place de HU, sans impact), hors de "
        "toute autre enveloppe.",
        [
            "palee",
            "x_c1",
            "hauteur_piles",
            "z_plan_moyen_semelle",
            "volume_beton",
            "poids_beton",
            "poids_deja",
            *(x for s in STATES for x in (f"SRz_min_{s}", f"combinaison_{s}")),
            "ressorts_traction_ELU_fondamental",
            "lest_manquant",
            "SRz_min_ELU_fondamental_HU_S5",
            "combinaison_ELU_fondamental_HU_S5",
            "SRz_min_ELU_accidentel_HU_S5",
            "combinaison_ELU_accidentel_HU_S5",
            "SRz_min_ELS_caracteristique_HU_S5",
            "combinaison_ELS_caracteristique_HU_S5",
            "lest_manquant_HU_S5",
        ],
        pr,
    )
    ar, anchor_summary = anchoring_rows(v)
    files["ancrage.csv"] = write(
        out / "ancrage.csv",
        f"{src} Unités : N. Ancrage que demanderait chaque palée (aucun ancrage modélisé : le soulèvement se "
        "constate) : ΣRz min du sol, effort d'ancrage requis = max(0 ; −ΣRz min), part de la houle dans la "
        "combinaison gouvernante, traction maximale de chaque pile en tête et en pied ; ELU fondamental et "
        "ELS caractéristique ; houle P60 et impact P61. evenement_houle : événement de houle de la combinaison "
        "gouvernante (HU, HD, HU_IMP_Mk ou aucun). valeur_HU_S5, combinaison_HU_S5 : sensibilité sans décision, "
        "forfait AVP de 5 kPa sur HU_TUBES, HU_PANNES, HU_PLATELAGE à la place de HU, sans impact.",
        [
            "palee",
            "etat_limite",
            "grandeur",
            "lieu",
            "valeur",
            "unite",
            "combinaison",
            "evenement_houle",
            "valeur_HU_S5",
            "combinaison_HU_S5",
            "detail",
        ],
        ar,
    )
    shutil.copyfile(
        Path(__file__).resolve().parent / "scripts" / "recombiner_lot51quater.py",
        out / "recombiner.py",
    )
    npz = write_npz(vd, out / "efforts_elementaires.npz")
    details["palees"] = pier_summary
    details["ancrage"] = anchor_summary
    details["npz"] = npz
    return files, details


# --------------------------------------------------------------------------- comparison


def comparison_extra(v: Variant51quater) -> dict[str, Quantity]:
    """Anchoring of each pier (P60/P61 and HU_S5, kN) and the governing houle event of
    PP My, of the characteristic SLS deflection and of the anchoring."""
    vd = v.vd
    totals = pier_totals(vd)
    piers = list(vd.g.piers)
    out: dict[str, Quantity] = {}
    for state, tag in (("ELU_fondamental", "ELU"), ("ELS_caracteristique", "ELS_C")):
        for data, suffix, lab in ((vd, "", "P60/P61"), (v.s5, "_S5", "HU_S5")):
            for g in governed(data, totals, state, -1.0, piers):
                out[f"ANCRAGE_{g.where}_{tag}{suffix}"] = Quantity(
                    f"effort d'ancrage requis {g.where}, {state}, {lab}",
                    "kN",
                    max(0.0, -g.value) * KN,
                    state,
                    g.combination,
                    g.where,
                )
    return out


@dataclasses.dataclass
class HouleQuantity(Quantity):
    """A text quantity: the houle event of a governing combination."""

    event: str = ""


def governing_houle(
    v: Variant51quater, comp: dict[str, Quantity]
) -> dict[str, HouleQuantity]:
    """Text quantities: the houle event of the governing combination."""
    ev = v.vd.ev
    spans = [s.name for s in v.vd.g.spans if s.nature == "grande"] + ["PF"]
    worst = min(spans, key=lambda s: comp[f"LF_{s}_C"].value)
    out: dict[str, HouleQuantity] = {}
    for key, source in (
        ("HOULE_PP_My", comp["PP_My"]),
        ("HOULE_FL_C", comp[f"FL_{worst}_C"]),
        ("HOULE_ANCRAGE_ELU", comp["ANCRAGE_ELU"]),
        ("HOULE_ANCRAGE_ELS_C", comp["ANCRAGE_ELS_C"]),
    ):
        out[key] = HouleQuantity(
            f"événement de houle gouvernant : {source.label}",
            "-",
            float("nan"),
            source.state,
            source.combination,
            source.where,
            houle_of(source.combination, ev),
        )
    return out


def extra_columns(piers: list[str]) -> tuple[str, ...]:
    return tuple(
        f"ANCRAGE_{p}_{tag}{suffix}"
        for p in piers
        for tag in ("ELU", "ELS_C")
        for suffix in ("", "_S5")
    )


HOULE_COLUMNS = (
    "HOULE_PP_My",
    "HOULE_FL_C",
    "HOULE_ANCRAGE_ELU",
    "HOULE_ANCRAGE_ELS_C",
)


# --------------------------------------------------------------------------- checks


def check_resultants(v: Variant51quater) -> dict[str, Any]:
    """Resultants of the events HU, HD and HU_IMP_Mk: (a) Σ coefficient × declared
    resultant of the unit cases against the consigne's formula (loaded length);
    (b) the same against the vertical reactions of the run (abutment + soil of the
    piers), which must balance it."""
    vd = v.vd
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
    }
    out: dict[str, Any] = {"longueur_chargee_m": length, "largeurs_m": widths}
    for name in ["HU", "HD", *(f"HU_IMP_{m}" for m in vd.g.modules())]:
        e = vd.ev[name]
        declared = sum(c * loads[k]["DZ"] for k, c in e.coefficients.items())
        reactions = sum(c * reaction(k) for k, c in e.coefficients.items())
        if name == "HD":
            formula = -vd.ev["HD"].coefficients["HD_TABLIER"] * vd.vals.width_deck_top
            formula *= length * 1000.0
        elif name == "HU":
            formula = sum(e.coefficients[c] * widths[c] for c in IMPACT_CASES) * (
                length * 1000.0
            )
        else:
            module = name.removeprefix("HU_IMP_")
            lm = sum(span_length(vd.g, s) for s in vd.g.modules()[module])
            p = next(iter(e.coefficients.values()))
            formula = p * sum(widths.values()) * lm * 1000.0
        out[name] = {
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


def check_identity_p56(v: Variant51quater, previous: dict[str, Any]) -> dict[str, Any]:
    """Comparison of lot 51 ter recomputed with the P56 events through the rules of this
    lot: each value and governing combination against synthese.json of lot 51 ter."""
    comp = comparison(v.p56)
    worst = 0.0
    differences = []
    for key, q in comp.items():
        old = previous[key]
        a, b = float(q.value), float(old["value"])
        rel = 0.0 if a == b else abs(a - b) / max(abs(b), 1e-300)
        worst = max(worst, rel)
        if rel != 0.0 or q.combination != old["combination"] or q.where != old["where"]:
            differences.append(key)
    return {
        "grandeurs": len(comp),
        "ecart_relatif_max": worst,
        "differences": differences,
        "reussi": not differences,
    }


def check_without_houle(v: Variant51quater) -> dict[str, Any]:
    """Combinations without houle: the envelopes with the houle left out are the same
    under the rules of lot 51 ter (P56) and of this lot (P60, P61), every state, both
    senses, at every place of the recombination check of lot 51 ter."""
    worst = 0.0
    n = 0
    for _, f, _ in recombination_places(v.vd):
        for state in STATES:
            for sign in (1.0, -1.0):
                a = envelope(
                    v.vd.bs, v.vd.ev, f, state, sign=sign, without=HOULE_ACTIONS
                )
                b = envelope(
                    v.p56.bs, v.p56.ev, f, state, sign=sign, without=HOULE_ACTIONS
                )
                worst = max(worst, float(np.max(np.abs(a.value - b.value))))
                n += a.value.size
    return {"valeurs": n, "ecart_absolu_max": worst, "reussi": worst == 0.0}


def _recombiner(out: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "recombiner_lot51quater", out / "recombiner.py"
    )
    assert spec is not None and spec.loader is not None
    rec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rec)
    return rec


def check_enumeration(
    out: Path,
    v: Variant51quater,
    *,
    seed: int = SEED,
    extra_places: list[tuple[str, dict[str, FloatArray], list[str]]] | None = None,
) -> list[dict[str, Any]]:
    """36 extremes drawn at random (fixed seed): place, quantity, state and sense; the
    decomposition against (a) the delivered recombiner.py, combination by combination,
    and (b) the explicit enumeration of every pattern (`brute_force`). Lot 52: its seed
    and its extra places."""
    vd = v.vd
    rec = _recombiner(out)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    places = recombination_places(vd)
    rows = _rows_of(vd, ("POUTRES_PRINC", "PILES", "CHEVETRES", "LONGRINES"))
    places.append(("MFZ barres", _arrays(vd, rows, 5), [f"{e}/{n}" for e, n in rows]))
    places += extra_places or []
    rng = random.Random(seed)
    checks = []
    for _ in range(DRAWS):
        label, f, where = places[rng.randrange(len(places))]
        q = rng.randrange(len(where))
        state = rng.choice(("ELU_fondamental", "ELU_accidentel", "ELS_caracteristique"))
        sign = rng.choice((1.0, -1.0))
        ext = envelope(vd.bs, vd.ev, f, state, sign=sign)
        values_q = {c: float(f[c][q]) for c in vd.cases}
        brute = rec.extremes([r for r in rules if r[0] == state], events_csv, values_q)[
            state
        ]
        reference = brute[0] if sign > 0 else brute[2]
        explicit = [
            brute_force(b, vd.ev, values_q, sign) for b in vd.bs if b.state == state
        ]
        exhaustive = max(explicit) if sign > 0 else min(explicit)
        value = float(ext.value[q])
        rel = abs(value - reference) / max(abs(reference), 1e-300)
        rel2 = abs(value - exhaustive) / max(abs(exhaustive), 1e-300)
        name = governing(vd.bs, vd.ev, ext, q)[0]
        checks.append(
            {
                "grandeur": label,
                "lieu": where[q],
                "etat_limite": state,
                "extreme": "max" if sign > 0 else "min",
                "decomposition": value,
                "recombiner": reference,
                "enumeration_explicite": exhaustive,
                "ecart_relatif_recombiner": rel,
                "ecart_relatif_explicite": rel2,
                "combinaison_decomposition": name,
                "combinaison_recombiner": brute[1] if sign > 0 else brute[3],
                "evenement_houle": houle_of(name, vd.ev),
                "reussi": rel <= 1e-9 and rel2 <= 1e-9,
            }
        )
    return checks


def check_counts(out: Path, v: Variant51quater) -> dict[str, Any]:
    """Counts by formula, by recombiner.py and by enumeration of the rules without
    duplicates; exclusions (B′, P57, P61) in the rules."""
    vd = v.vd
    rec = _recombiner(out)
    rules = rec.read_rules(out)
    events_csv = rec.read_events(out)
    formula = counts(vd.bs)
    expanded = expanded_counts(vd.bs, vd.ev)
    seen = set()
    total = 0
    for b in vd.bs:
        for choice in itertools.product(*(s.options for s in b.slots)):
            seen.add((b.state, *sorted((n, f) for n, f in choice if n is not None)))
            total += 1
    result: dict[str, Any] = {
        "formule": formula,
        "formule_total": sum(formula.values()),
        "recombiner": rec.count(rules),
        "dispositions_formule": expanded,
        "dispositions_total": sum(expanded.values()),
        "dispositions_recombiner": rec.count(rules, events_csv),
        "enumerees": total,
        "distinctes": len(seen),
        "exclusions": check_exclusions(vd.bs, vd.ev),
    }
    result["reussi"] = (
        result["recombiner"] == formula
        and result["dispositions_recombiner"] == expanded
        and total == len(seen) == sum(formula.values())
        and not result["exclusions"]
    )
    return result


# --------------------------------------------------------------------------- steps


def run_variant(
    ctx: ProjectContext, code: str, state: dict[str, Any], previous: dict[str, Any]
) -> dict[str, Any]:
    """Exports, comparison and checks of one variant; times of the recombination."""
    root = ctx.results_dir / LOT / "exports"
    v = load(ctx, code, state)
    out = root / code
    t0 = time.perf_counter()
    files, details = export(v, state, out)
    t1 = time.perf_counter()
    comp = comparison(v.vd)
    extra = comparison_extra(v)
    houle = governing_houle(v, comp)
    t2 = time.perf_counter()
    info: dict[str, Any] = {
        "statut": "calculée",
        "fichiers": files,
        "effectifs": counts(v.vd.bs),
        "effectifs_dispositions": expanded_counts(v.vd.bs, v.vd.ev),
        "details": details,
        "comparaison": {
            k: dataclasses.asdict(q) for k, q in {**comp, **extra, **houle}.items()
        },
        "temps_s": {
            "lecture_tables": v.load_s,
            "exports": t1 - t0,
            "comparaison": t2 - t1,
            "recombinaison": t2 - t0,
        },
        "controle_resultantes": check_resultants(v),
    }
    t3 = time.perf_counter()
    info["controle_identite_P56"] = check_identity_p56(v, previous[code]["comparaison"])
    info["controle_sans_houle"] = check_without_houle(v)
    info["temps_s"]["controles_identite"] = time.perf_counter() - t3
    if code == "B10":
        t4 = time.perf_counter()
        info["controle_enumeration"] = check_enumeration(out, v)
        info["controle_effectifs"] = check_counts(out, v)
        info["temps_s"]["enumeration"] = time.perf_counter() - t4
    return info


def step_exports(
    ctx: ProjectContext, codes: list[str], state: dict[str, Any], workers: int = 1
) -> None:
    from concurrent.futures import ProcessPoolExecutor  # noqa: PLC0415

    root = ctx.results_dir / LOT / "exports"
    root.mkdir(parents=True, exist_ok=True)
    previous = json.loads(
        (ctx.results_dir / "lot51ter" / "exports" / "synthese.json").read_text("utf-8")
    )
    summary_path = root / "synthese.json"
    summary: dict[str, Any] = (
        json.loads(summary_path.read_text("utf-8")) if summary_path.is_file() else {}
    )
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            code: pool.submit(_run_variant_job, ctx.repo_root, code, state, previous)
            for code in codes
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


def _run_variant_job(
    repo_root: Path, code: str, state: dict[str, Any], previous: dict[str, Any]
) -> dict[str, Any]:
    from aster_expert.projet.context import load_project  # noqa: PLC0415

    ctx = load_project("pontons_alu_01", repo_root)
    return run_variant(ctx, code, state, previous)


def write_comparison(root: Path, summary: dict[str, Any]) -> None:
    g = geometry(variants()["B10"].mesh_overrides)
    columns = comparison_columns(g)
    extra = extra_columns(list(g.piers))
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
        "PONTONS-ALU-01, lot 51 quater : comparaison des variantes (ponton intégral), houle P60 « tablier noyé » "
        "et impact quasi statique P61 (cas unitaires du lot 51 ter recombinés). Valeurs : enveloppes du jeu B′ "
        "révisé (ELU fondamental, ELS caractéristique, ELS fréquent) et de l'ELU accidentel, avec DEJ (P49), P57, "
        "P59, sauf les flèches (P51 : ELS fréquent, ELS caractéristique sans la composante tangentielle "
        "d'accostage ; actions variables seules ; grandes travées relatives à la corde, porte-à-faux relatif à "
        "l'appui et à la corde de PT5, L = 2 Lpf) et les états limites nommés. Colonnes ANCRAGE_Pk_* : effort "
        "d'ancrage requis par palée, P60/P61 et, suffixe _S5, sensibilité HU_S5 sans décision (5 kPa). Colonnes "
        "HOULE_* : événement de houle de la combinaison gouvernante (HU, HD, HU_IMP_Mk ou aucun) ; HOULE_FL_C : "
        "flèche de l'ELS caractéristique de la travée au plus petit L/f. Unités : kN, kN·m, mm. Colonnes : "
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
        "PONTONS-ALU-01, lot 51 quater : grandeurs de comparaison, état limite, combinaison et lieu qui gouvernent "
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


__all__ = [
    "Variant51quater",
    "anchoring_rows",
    "check_counts",
    "check_enumeration",
    "check_identity_p56",
    "check_resultants",
    "check_without_houle",
    "export",
    "houle_of",
    "load",
    "pin_results",
    "step_exports",
    "write_comparison",
    "write_npz",
]
