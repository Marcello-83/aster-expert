"""Concomitant torsors of the design sections, by limit state (lot 49 bis).

Read, never recomputed by Code_Aster: a combination is the superposition of the
elementary cases the post-processing run wrote (`cas/<case>`), with the coefficients
the project declares, plus `coefficient × <position>` for each position of a moving
load (`pos/<position>`) -- the arithmetic of the combinations of lot 49
(`aster_expert.livrables.calcul`) and of `aster-expert resultats lire`
(`<combinaison>@<position>`). Each value is checked afterwards against that command
(`aster_expert.livrables.ingenieur.cross_check`).

For each limit state (`engineering_summary.limit_states`: the combination families
that make it) and each row of a family, the max and the min of every component (and
of the resultants of a circular beam) are kept with the combination and the position
that give them. The design value of a section is the extreme over its rows; its
torsor is the full vector at that row, for that combination and that position: the
concomitant N, V, M. Rows a section cannot use (singular, `sections.singular_rows`)
are left out of the design value; the extreme read there is kept, marked « non
significative » with its reason.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np

from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.donnees import FloatArray
from aster_expert.livrables.sections import M_RES, V_RES, FamilyRows, SectionRows
from aster_expert.livrables.unites import si_unit
from aster_expert.projet.declaration import EngineeringSummarySection, LimitState
from aster_expert.projet.errors import ProjectError

STATE_LABELS: dict[str, str] = {
    "ELU_fondamental": "ELU fondamental",
    "ELU_accidentel": "ELU accidentel",
    "ELS_caracteristique": "ELS caractéristique",
    "ELS_frequent": "ELS fréquent",
    "ELS_quasi_permanent": "ELS quasi permanent",
}
SHORT_LABELS: dict[str, str] = {
    "ELU_fondamental": "ELU",
    "ELU_accidentel": "ELU acc.",
    "ELS_caracteristique": "ELS car.",
    "ELS_frequent": "ELS fréq.",
    "ELS_quasi_permanent": "ELS QP",
}
SHEAR_OF_MOMENT = {"MFY": "VZ", "MFZ": "VY", "MXX": "QX", "MYY": "QY"}
NORMAL_OF_MOMENT = {"MFY": "N", "MFZ": "N", "MXX": "NXX", "MYY": "NYY"}


def combinations_of_state(
    combinations: list[GenericCombination],
    summary: EngineeringSummarySection,
    state: LimitState,
) -> list[tuple[int, GenericCombination]]:
    declared = next(s for s in summary.limit_states if s.state == state)
    found = [
        (i, c) for i, c in enumerate(combinations) if c.family in declared.families
    ]
    if not found:
        message = (
            f"état limite {state} : aucune combinaison des familles "
            f"{list(declared.families)}"
        )
        raise ProjectError(message)
    return found


def evaluate(
    fr: FamilyRows,
    combinations: list[tuple[int, GenericCombination]],
    *,
    exclude: tuple[str, ...] = (),
) -> Iterator[tuple[int, int, FloatArray]]:
    """(combination index, position index or −1, extended values) of every
    combination and every position of its moving load."""
    for ci, comb in combinations:
        base = np.zeros((len(fr.index), len(fr.raw)))
        for case, coefficient in comb.fixed.items():
            if case in exclude or coefficient == 0.0:
                continue
            if case not in fr.cases:
                message = f"combinaison {comb.name} : cas {case} absent des livrables"
                raise ProjectError(message)
            base = base + coefficient * fr.cases[case]
        if not comb.mobile_cases:
            yield ci, -1, fr.extend(base)
            continue
        for pi, position in enumerate(comb.mobile_cases):
            if position not in fr.cases:
                message = f"position {position} absente des livrables"
                raise ProjectError(message)
            yield ci, pi, fr.extend(base + comb.mobile_coefficient * fr.cases[position])


def value_at(
    fr: FamilyRows,
    comb: GenericCombination,
    position: int,
    row: int,
    *,
    exclude: tuple[str, ...] = (),
) -> FloatArray:
    """The extended vector of one row for one combination and one position."""
    vector = np.zeros(len(fr.raw))
    for case, coefficient in comb.fixed.items():
        if case in exclude or coefficient == 0.0:
            continue
        vector = vector + coefficient * fr.cases[case][row]
    if position >= 0:
        vector = (
            vector
            + comb.mobile_coefficient * fr.cases[comb.mobile_cases[position]][row]
        )
    out: FloatArray = fr.extend(vector[None, :])[0]
    return out


@dataclass
class StateEnvelope:
    """Max and min of every extended column at every row, for one limit state, with
    the combination and the position that give them."""

    state: str
    maximum: FloatArray
    minimum: FloatArray
    max_comb: Any
    max_pos: Any
    min_comb: Any
    min_pos: Any
    evaluations: int
    per_section: dict[str, dict[int, tuple[float, int, int]]]
    """Section -> combination -> (largest |primary| over its usable rows, row,
    position): the line « section × combinaison » of the Torseurs sheet."""


def primary_column(fr: FamilyRows) -> str:
    """The quantity a section is read by, combination by combination."""
    family = fr.family
    if family.circular:
        return M_RES
    if family.moments:
        return family.moments[0]
    for name in ("MXX", "MYY"):
        if name in fr.columns:
            return name
    return family.quantities[0]


def envelope(
    fr: FamilyRows,
    combinations: list[tuple[int, GenericCombination]],
    state: str,
    sections: list[SectionRows],
) -> StateEnvelope:
    n, c = len(fr.index), len(fr.columns)
    maximum = np.full((n, c), -np.inf)
    minimum = np.full((n, c), np.inf)
    max_comb = np.full((n, c), -1, dtype=np.int64)
    min_comb = np.full((n, c), -1, dtype=np.int64)
    max_pos = np.full((n, c), -1, dtype=np.int64)
    min_pos = np.full((n, c), -1, dtype=np.int64)
    primary = fr.column(primary_column(fr))
    usable = {
        s.section.name: np.where(
            s.mask & ~(s.singular if s.section.exclude_singular else False)
        )[0]
        for s in sections
    }
    per_section: dict[str, dict[int, tuple[float, int, int]]] = {
        name: {} for name in usable
    }
    count = 0
    for ci, pi, values in evaluate(fr, combinations):
        count += 1
        higher = values > maximum
        maximum = np.where(higher, values, maximum)
        max_comb[higher] = ci
        max_pos[higher] = pi
        lower = values < minimum
        minimum = np.where(lower, values, minimum)
        min_comb[lower] = ci
        min_pos[lower] = pi
        metric = np.abs(values[:, primary])
        for name, rows in usable.items():
            if rows.size == 0:
                continue
            k = int(rows[int(np.argmax(metric[rows]))])
            best = per_section[name].get(ci)
            if best is None or metric[k] > best[0]:
                per_section[name][ci] = (float(metric[k]), k, pi)
    return StateEnvelope(
        state,
        maximum,
        minimum,
        max_comb,
        max_pos,
        min_comb,
        min_pos,
        count,
        per_section,
    )


@dataclass(frozen=True)
class Target:
    """A design quantity: a column, and `max`, `min` or `abs` (largest modulus)."""

    label: str
    column: str
    sense: str
    role: str
    """N, M or V: the column of the summary it fills."""


def targets(fr: FamilyRows) -> list[Target]:
    family = fr.family
    out: list[Target] = []
    if family.kind == "poutre":
        out += [Target("N max", "N", "max", "N"), Target("N min", "N", "min", "N")]
        for m in family.moments:
            out += [
                Target(f"{m} max", m, "max", "M"),
                Target(f"{m} min", m, "min", "M"),
            ]
        if family.circular:
            out.append(Target("M max (résultante)", M_RES, "max", "M"))
        for v in family.shears:
            out.append(Target(f"|{v}| max", v, "abs", "V"))
        if family.circular:
            out.append(Target("V max (résultante)", V_RES, "max", "V"))
    elif family.kind == "coque":
        for m in ("MXX", "MYY"):
            if m in fr.columns:
                out += [
                    Target(f"{m} max", m, "max", "M"),
                    Target(f"{m} min", m, "min", "M"),
                ]
    else:
        for q in family.quantities:
            out += [Target(f"{q} max", q, "max", q), Target(f"{q} min", q, "min", q)]
    return out


def triplet(fr: FamilyRows, target: Target) -> dict[str, str | None]:
    """The columns N, M, V of the summary for the row of `target`."""
    family = fr.family
    if family.kind == "coque":
        plate = target.column if target.role == "M" else "MXX"
        return {
            "N": NORMAL_OF_MOMENT[plate],
            "M": plate,
            "V": SHEAR_OF_MOMENT[plate],
        }
    if family.kind == "poutre":
        if family.circular:
            return {"N": "N", "M": M_RES, "V": V_RES}
        moment: str | None = (
            target.column if target.role == "M" else (family.moments or (None,))[0]
        )
        if target.role == "V":
            moment = next(
                (m for m in family.moments if SHEAR_OF_MOMENT.get(m) == target.column),
                moment,
            )
        shear = SHEAR_OF_MOMENT.get(moment or "")
        return {
            "N": "N",
            "M": moment,
            "V": shear if shear in fr.columns else (family.shears or (None,))[0],
        }
    return {"N": None, "M": None, "V": None}


def unit_of(fr: FamilyRows, column: str) -> str:
    if column == M_RES:
        return "N·m"
    if column == V_RES:
        return "N"
    return si_unit(_deliverable_family(fr), fr.info.field, column)


def _deliverable_family(fr: FamilyRows) -> str:
    return fr.info.family


def _pick(
    env: StateEnvelope, fr: FamilyRows, rows: Any, target: Target
) -> tuple[int, float, int, int] | None:
    """(row, value, combination, position) of `target` over `rows`."""
    if rows.size == 0:
        return None
    c = fr.column(target.column)
    if target.sense == "max":
        k = int(rows[int(np.argmax(env.maximum[rows, c]))])
        return (
            k,
            float(env.maximum[k, c]),
            int(env.max_comb[k, c]),
            int(env.max_pos[k, c]),
        )
    if target.sense == "min":
        k = int(rows[int(np.argmin(env.minimum[rows, c]))])
        return (
            k,
            float(env.minimum[k, c]),
            int(env.min_comb[k, c]),
            int(env.min_pos[k, c]),
        )
    hi = int(rows[int(np.argmax(env.maximum[rows, c]))])
    lo = int(rows[int(np.argmin(env.minimum[rows, c]))])
    if abs(env.maximum[hi, c]) >= abs(env.minimum[lo, c]):
        return (
            hi,
            float(env.maximum[hi, c]),
            int(env.max_comb[hi, c]),
            int(env.max_pos[hi, c]),
        )
    return (
        lo,
        float(env.minimum[lo, c]),
        int(env.min_comb[lo, c]),
        int(env.min_pos[lo, c]),
    )


def torsor_entry(
    fr: FamilyRows,
    combinations: list[GenericCombination],
    row: int,
    ci: int,
    pi: int,
) -> dict[str, Any]:
    """Place, combination, position and the full torsor of one row."""
    comb = combinations[ci]
    vector = value_at(fr, comb, pi, row)
    return {
        "lieu": fr.place(row),
        "combinaison": comb.name,
        "famille_combinaison": comb.family,
        "position_mobile": comb.mobile_cases[pi] if pi >= 0 else None,
        "charge_mobile": comb.mobile_label if pi >= 0 else None,
        "torseur_si": {
            name: float(v) for name, v in zip(fr.columns, vector, strict=True)
        },
        "unites_si": {name: unit_of(fr, name) for name in fr.columns},
    }


def section_torsors(
    fr: FamilyRows,
    combinations: list[GenericCombination],
    env: StateEnvelope,
    sec: SectionRows,
) -> list[dict[str, Any]]:
    """The design torsors of a section for one limit state: one per target, plus the
    extreme read in the excluded rows when it is larger (marked non significant)."""
    out: list[dict[str, Any]] = []
    excluded = sec.singular if sec.section.exclude_singular else np.zeros_like(sec.mask)
    usable = np.where(sec.mask & ~excluded)[0]
    flagged = np.where(sec.mask & excluded)[0]
    for target in targets(fr):
        picked = _pick(env, fr, usable, target)
        if picked is None:
            continue
        row, value, ci, pi = picked
        entry = {
            "section": sec.section.name,
            "famille": fr.family.name,
            "etat_limite": env.state,
            "grandeur": target.label,
            "colonne": target.column,
            "sens": target.sense,
            "role": target.role,
            "triplet": triplet(fr, target),
            "valeur_si": value,
            "unite_si": unit_of(fr, target.column),
            "significative": True,
            "motif": None,
            # Section circulaire : la synthèse montre les résultantes, les composantes
            # restent dans la feuille Torseurs.
            "principal": not (
                fr.family.circular and target.column in ("MFY", "MFZ", "VY", "VZ")
            ),
            **torsor_entry(fr, combinations, row, ci, pi),
        }
        if not sec.section.exclude_singular and int(row) in sec.reasons:
            entry["significative"] = False
            entry["motif"] = sec.reasons[int(row)]
        out.append(entry)
        alt = _pick(env, fr, flagged, target)
        if alt is None:
            continue
        a_row, a_value, a_ci, a_pi = alt
        larger = (
            a_value > value
            if target.sense == "max"
            else a_value < value
            if target.sense == "min"
            else abs(a_value) > abs(value)
        )
        if larger:
            out.append(
                {
                    **entry,
                    "valeur_si": a_value,
                    "significative": False,
                    "motif": sec.reasons.get(a_row, "zone exclue"),
                    **torsor_entry(fr, combinations, a_row, a_ci, a_pi),
                }
            )
    return out


def combination_lines(
    fr: FamilyRows,
    combinations: list[GenericCombination],
    env: StateEnvelope,
    section: str,
) -> list[dict[str, Any]]:
    """One line per combination of the state: the torsor where |primary| is largest
    over the usable rows of the section."""
    out = []
    primary = primary_column(fr)
    for ci, (value, row, pi) in sorted(env.per_section.get(section, {}).items()):
        out.append(
            {
                "section": section,
                "famille": fr.family.name,
                "etat_limite": env.state,
                "grandeur": f"|{primary}| max",
                "valeur_si": value,
                "unite_si": unit_of(fr, primary),
                **torsor_entry(fr, combinations, row, ci, pi),
            }
        )
    return out


def member_lines(
    fr: FamilyRows,
    combinations: list[GenericCombination],
    env: StateEnvelope,
) -> list[dict[str, Any]]:
    """Detail of a beam family: per member, the design values of the state."""
    out = []
    members = sorted({m for m in fr.member if m})
    for member in members:
        rows = np.array([i for i, m in enumerate(fr.member) if m == member])
        values: dict[str, Any] = {}
        for target in targets(fr):
            picked = _pick(env, fr, rows, target)
            if picked is None:
                continue
            row, value, ci, pi = picked
            comb = combinations[ci]
            values[target.label] = {
                "valeur_si": value,
                "unite_si": unit_of(fr, target.column),
                "coordonnees_m": [float(v) for v in fr.xyz[row]],
                "combinaison": comb.name,
                "position_mobile": comb.mobile_cases[pi] if pi >= 0 else None,
            }
        out.append(
            {
                "famille": fr.family.name,
                "groupe": member,
                "etat_limite": env.state,
                "valeurs": values,
            }
        )
    return out


__all__ = [
    "NORMAL_OF_MOMENT",
    "SHEAR_OF_MOMENT",
    "SHORT_LABELS",
    "STATE_LABELS",
    "StateEnvelope",
    "Target",
    "combination_lines",
    "combinations_of_state",
    "envelope",
    "evaluate",
    "member_lines",
    "primary_column",
    "section_torsors",
    "targets",
    "torsor_entry",
    "triplet",
    "unit_of",
    "value_at",
]
