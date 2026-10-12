"""Deliverables of lot 50 bis for PONTONS-ALU-01, from the elementary cases of the
deliverables (`resultats/livrables/`, and `resultats/balayage/k<k>/livrables/` for the
inertia sweep), never a new run.

- P28, simplified elastic ratio of every aluminium family, at every element end
  (EFGE_ELNO) and every ULS combination (fundamental and accidental) of sets B and
  B′ (P27): σ = |N|/A + |MFY|/Wel,y + |MFZ|/Wel,z against f0/γM1, τ = √(VY² + VZ²)/Av
  against f0/(√3·γM1), and the same with f0,haz at the welded ends. An indicator, not
  an EC9 check (no class, buckling, lateral-torsional buckling, joints).
- the summary per family (N, My, Mz, V and the maximum ratio, with place and
  combination), the support profiles (forces at the foot, transmitted to the cap
  beam), the purlins, the quay hinges node by node (P25);
- the inertia sweep (k × IY of the main beams): deflection at the characteristic SLS,
  total and under the variable actions alone, relative to the chord of the supports;
  My max at ULS; I needed for L/200, L/250, L/300 (fit a + b/k, docs/essais_lot50bis.md
  § 3) and Wel,y needed for a ratio of 1,0 (f0 and f0,haz);
- the comparison with lot 50 (P24, P25) on the elementary and ULS envelopes.

Hypotheses of the tool, written in docs/essais_lot50bis.md § 4 before the results: Av of
the MP1200 = Avz for both directions; tubes Wel = I/(h/2), Av = A/2; welded end: node
shared by two aluminium bars or more, node of a rigid link, foot of a support profile.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.livrables.donnees import Deliverables, FieldArrays
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons import (
    STATE_OF_FAMILY,
    Combination,
    set_b,
    set_b_prime,
)
from pontons_alu_01.geometrie import geometry

FloatArray = NDArray[np.float64]

WARNING = (
    "AVERTISSEMENT : taux élastique simplifié (P28), indicateur de dimensionnement. Ce "
    "taux ne vérifie ni la classe de section, ni le flambement, ni le déversement, ni "
    "les assemblages ; ce n'est pas une vérification EC9, qui viendra plus tard."
)
FAMILIES = {
    "poutres_principales": ("POUTRES_PRINC", "PP_", "mp1200"),
    "montants": ("MONTANTS", "MONT_", "tube_150"),
    "diagonales": ("DIAGONALES", "DIAG_", "tube_150"),
    "pannes_secondaires": ("PANNES_SEC", "PANNE_", "tube_50"),
    "profiles_supports": ("SUPPORTS", "SUP_", "tube_150"),
}
ALU_PREFIXES = tuple(prefix for _, prefix, _ in FAMILIES.values())
SETS = {"B": set_b, "B′": set_b_prime}
ULS = ("ELU_fondamental", "ELU_accidentel")
SLS_C = "ELS_caracteristique"
PERMANENT = ("G1", "G2")
LIMITS = (200, 250, 300)


@dataclass(frozen=True)
class Section:
    """Section properties (m, m², m³) and strengths (Pa) of one family."""

    name: str
    area: float
    w_y: float
    w_z: float
    a_v: float
    f0: float
    f0_haz: float
    gamma_m1: float
    source: str


def sections(ctx: ProjectContext) -> dict[str, Section]:
    d = {k: v.value for k, v in ctx.data().items().items()}

    def f(key: str) -> float:
        value = d[key]
        assert isinstance(value, int | float)
        return float(value)

    gamma = f("resistances_aluminium.gamma_m1")

    def tube(prefix: str, strength: str) -> Section:
        h = f(f"{prefix}.cote") * 1e-3
        t = f(f"{prefix}.epaisseur") * 1e-3
        area = h**2 - (h - 2 * t) ** 2
        inertia = (h**4 - (h - 2 * t) ** 4) / 12.0
        w = inertia / (h / 2.0)
        return Section(
            name=f"tube {h * 1e3:g} × {h * 1e3:g} × {t * 1e3:g}",
            area=area,
            w_y=w,
            w_z=w,
            a_v=area / 2.0,
            f0=f(f"resistances_aluminium.f0_{strength}") * 1e6,
            f0_haz=f(f"resistances_aluminium.f0_haz_{strength}") * 1e6,
            gamma_m1=gamma,
            source="angles vifs : A = h² − (h − 2t)², Wel = I/(h/2), Av = A/2",
        )

    return {
        "mp1200": Section(
            name="MP1200",
            area=f("poutres_principales.aire") * 1e-6,
            w_y=f("poutres_principales.module_fort") * 1e-9,
            w_z=f("poutres_principales.module_faible") * 1e-9,
            a_v=f("poutres_principales.aire_cisaillement_z") * 1e-4,
            f0=f("resistances_aluminium.f0_poutres_principales") * 1e6,
            f0_haz=f("resistances_aluminium.f0_haz_poutres_principales") * 1e6,
            gamma_m1=gamma,
            source="D3 : Wel,y, Wel,z ; Av = Avz pour les deux directions",
        ),
        "tube_150": tube("tubes_150", "tubes_150"),
        "tube_50": tube("tubes_50", "tubes_50"),
    }


@dataclass(frozen=True)
class Rows:
    index: NDArray[np.int64]
    labels: list[str]
    coords: FloatArray
    welded: NDArray[np.bool_]
    members: list[str]


def _beam_field(d: Deliverables, ctx: ProjectContext, name: str) -> FieldArrays:
    section = ctx.declaration.deliverables
    assert section is not None
    info = next(i for i in d.field_infos(section.fields) if i.field == name)
    return d.field(info)


def _member_groups(d: Deliverables) -> dict[str, str]:
    """Member group name -> its prefix, for the aluminium members."""
    out = {}
    for key in d.mesh.arrays:
        if key.startswith("gma_"):
            name = key.split("_", 2)[2]
            for prefix in ALU_PREFIXES:
                if name.startswith(prefix):
                    out[name] = prefix
    return out


def welded_nodes(d: Deliverables) -> set[int]:
    """Nodes shared by two aluminium members or more, nodes of the rigid links (LR_nn)
    and feet of the support profiles (docs/essais_lot50bis.md § 4)."""
    count: dict[int, int] = {}
    for name in _member_groups(d):
        for node in d.mesh.node_group(name).tolist():
            count[int(node)] = count.get(int(node), 0) + 1
    out = {n for n, c in count.items() if c >= 2}
    for key in d.mesh.arrays:
        if key.startswith("gno_LR_"):
            out |= {int(n) for n in d.mesh.arrays[key].tolist()}
    out |= {int(n) for n in d.mesh.node_group("PIEDS_SUPPORTS").tolist()}
    return out


def beam_rows(d: Deliverables, fa: FieldArrays, group: str, prefix: str) -> Rows:
    member_of: dict[int, str] = {}
    for name in _member_groups(d):
        if name.startswith(prefix) and name != group:
            cells = d.mesh.cell_group(name)
            assert cells is not None
            for cell in cells[1].tolist():
                member_of[int(cell)] = name
    cells = d.mesh.cell_group(group)
    assert cells is not None
    level, ids = cells
    sel = np.flatnonzero((fa.kind == 1) & (fa.level == level) & np.isin(fa.entity, ids))
    nodes = fa.node_of_row(d.mesh)[sel]
    welded = welded_nodes(d)
    members = [member_of.get(int(fa.entity[i]), group) for i in sel]
    labels = [
        f"{m} maille {int(fa.entity[i])} extrémité {int(fa.local[i]) + 1}"
        for m, i in zip(members, sel, strict=True)
    ]
    return Rows(
        sel,
        labels,
        d.mesh.coords[nodes],
        np.array([int(n) in welded for n in nodes]),
        members,
    )


def _stack(
    fa: FieldArrays, combos: list[Combination], rows: Iterable[int]
) -> FloatArray:
    index = np.asarray(list(rows), dtype=np.int64)
    out = np.zeros((len(combos), len(index), fa.arrays["cas/G1"].shape[1]))
    for c, combo in enumerate(combos):
        for case, coef in combo.coefficients.items():
            out[c] += coef * fa.arrays[f"cas/{case}"][index]
    return out


def _by_state(set_name: str) -> dict[str, list[Combination]]:
    out: dict[str, list[Combination]] = {}
    for c in SETS[set_name]():
        out.setdefault(STATE_OF_FAMILY[c.family], []).append(c)
    return out


def ratios(stack: FloatArray, comps: list[str], s: Section) -> dict[str, FloatArray]:
    """σ and τ of every (combination, row), and their ratios to f0 and f0,haz."""
    n, vy, vz = (stack[:, :, comps.index(c)] for c in ("N", "VY", "VZ"))
    my, mz = stack[:, :, comps.index("MFY")], stack[:, :, comps.index("MFZ")]
    sigma = np.abs(n) / s.area + np.abs(my) / s.w_y + np.abs(mz) / s.w_z
    tau = np.hypot(vy, vz) / s.a_v
    root3 = math.sqrt(3.0)
    return {
        "sigma": sigma,
        "tau": tau,
        "taux_sigma_f0": sigma / (s.f0 / s.gamma_m1),
        "taux_tau_f0": tau / (s.f0 / (root3 * s.gamma_m1)),
        "taux_sigma_haz": sigma / (s.f0_haz / s.gamma_m1),
        "taux_tau_haz": tau / (s.f0_haz / (root3 * s.gamma_m1)),
    }


def _place(rows: Rows, r: int) -> dict[str, Any]:
    return {
        "lieu": rows.labels[r],
        "soudee": "oui" if bool(rows.welded[r]) else "non",
        "x_m": round(float(rows.coords[r][0]), 4),
        "y_m": round(float(rows.coords[r][1]), 4),
        "z_m": round(float(rows.coords[r][2]), 4),
    }


def family_summary(ctx: ProjectContext, root: Path) -> list[dict[str, Any]]:
    """Synthesis per family, set and limit state (ULS of B and B′, characteristic SLS):
    N min/max, |My|, |Mz|, V max and the maximum simplified ratios, each with place,
    combination and concomitant torsor."""
    d = Deliverables(root)
    fa = _beam_field(d, ctx, "EFGE_ELNO")
    comps = list(fa.info.components)
    secs = sections(ctx)
    out: list[dict[str, Any]] = []
    for family, (group, prefix, key) in FAMILIES.items():
        rows = beam_rows(d, fa, group, prefix)
        s = secs[key]
        for set_name in SETS:
            by_state = _by_state(set_name)
            for state in (*ULS, SLS_C):
                combos = by_state[state]
                stack = _stack(fa, combos, rows.index.tolist())
                rat = ratios(stack, comps, s)
                quantities: dict[str, tuple[FloatArray, str, float, str]] = {
                    "N_min": (stack[:, :, comps.index("N")], "min", 1e-3, "kN"),
                    "N_max": (stack[:, :, comps.index("N")], "max", 1e-3, "kN"),
                    "My_abs_max": (
                        np.abs(stack[:, :, comps.index("MFY")]),
                        "max",
                        1e-3,
                        "kN·m",
                    ),
                    "Mz_abs_max": (
                        np.abs(stack[:, :, comps.index("MFZ")]),
                        "max",
                        1e-3,
                        "kN·m",
                    ),
                    "V_max": (
                        np.hypot(
                            stack[:, :, comps.index("VY")],
                            stack[:, :, comps.index("VZ")],
                        ),
                        "max",
                        1e-3,
                        "kN",
                    ),
                    "taux_sigma_f0": (rat["taux_sigma_f0"], "max", 1.0, "-"),
                    "taux_tau_f0": (rat["taux_tau_f0"], "max", 1.0, "-"),
                }
                welded = rows.welded
                if welded.any():
                    for name in ("taux_sigma_haz", "taux_tau_haz"):
                        masked = np.where(welded[None, :], rat[name], -np.inf)
                        quantities[name] = (masked, "max", 1.0, "-")
                for name, (values, kind, scale, unit) in quantities.items():
                    flat = values.argmin() if kind == "min" else values.argmax()
                    ci, ri = np.unravel_index(int(flat), values.shape)
                    torsor = stack[ci, ri]
                    out.append(
                        {
                            "famille": family,
                            "section": s.name,
                            "jeu": set_name,
                            "etat_limite": state,
                            "grandeur": name,
                            "valeur": float(values[ci, ri]) * scale,
                            "unite": unit,
                            **_place(rows, int(ri)),
                            **{
                                f"{c}_concomitant": float(torsor[j]) * 1e-3
                                for j, c in enumerate(comps)
                            },
                            "combinaison": combos[int(ci)].name,
                        }
                    )
    return out


def support_feet(ctx: ProjectContext, root: Path) -> list[dict[str, Any]]:
    """Forces of each support profile at its foot (Z = Z_SUPPORT_BAS): N, VY, VZ are
    the forces the articulation transmits to the cap beam (P18). POU_D_T local axes of
    projet.yaml: x_l = +Z, y_l = +X, z_l = +Y (VY along X, VZ along Y)."""
    d = Deliverables(root)
    fa = _beam_field(d, ctx, "EFGE_ELNO")
    comps = list(fa.info.components)
    z_foot = geometry().parameters["Z_SUPPORT_BAS"]
    rows = beam_rows(d, fa, "SUPPORTS", "SUP_")
    out = []
    for member in sorted(set(rows.members)):
        pick = [
            k
            for k, m in enumerate(rows.members)
            if m == member and abs(rows.coords[k][2] - z_foot) < 1e-6
        ]
        assert len(pick) == 1, member
        r = rows.index[pick[0]]
        y = float(rows.coords[pick[0]][1])
        for set_name in SETS:
            by_state = _by_state(set_name)
            for state in (*ULS, SLS_C):
                combos = by_state[state]
                stack = _stack(fa, combos, [int(r)])[:, 0, :]
                for comp in ("N", "VY", "VZ"):
                    col = stack[:, comps.index(comp)]
                    for kind, ci in (("min", col.argmin()), ("max", col.argmax())):
                        out.append(
                            {
                                "profile": member,
                                "y_m": round(y, 4),
                                "jeu": set_name,
                                "etat_limite": state,
                                "composante": comp,
                                "extremum": kind,
                                "valeur_kN": float(col[ci]) * 1e-3,
                                "combinaison": combos[int(ci)].name,
                            }
                        )
    return out


def hinge_reactions(ctx: ProjectContext, root: Path) -> list[dict[str, Any]]:
    """REAC_NODA of each quay hinge (P25), per set and limit state, min and max."""
    d = Deliverables(root)
    fa = _beam_field(d, ctx, "REAC_NODA")
    comps = list(fa.info.components)
    out = []
    for group in ("APP_QUAI_YM", "APP_QUAI_YP"):
        node = int(d.mesh.node_group(group)[0])
        r = int(np.flatnonzero((fa.kind == 0) & (fa.entity == node))[0])
        y = float(d.mesh.coords[node][1])
        for set_name in SETS:
            by_state = _by_state(set_name)
            for state in (*ULS, SLS_C):
                combos = by_state[state]
                stack = _stack(fa, combos, [r])[:, 0, :]
                for comp in comps:
                    col = stack[:, comps.index(comp)]
                    for kind, ci in (("min", col.argmin()), ("max", col.argmax())):
                        out.append(
                            {
                                "rotule": group,
                                "y_m": round(y, 4),
                                "jeu": set_name,
                                "etat_limite": state,
                                "composante": comp,
                                "extremum": kind,
                                "valeur_kN": float(col[ci]) * 1e-3,
                                "combinaison": combos[int(ci)].name,
                            }
                        )
    return out


def _relative_deflection(
    d: Deliverables, fa: FieldArrays, combos: list[Combination], variable_only: bool
) -> tuple[float, str, str]:
    """Largest |UZ − chord| of a main beam over the combinations (m), with the beam
    and the combination; the chord joins UZ at X = 0 and X = L of the same beam."""
    comps = list(fa.info.components)
    k = comps.index("DZ")
    span = geometry().parameters["L"]
    best = (0.0, "", "")
    for beam in ("PP_YM", "PP_YP"):
        nodes = d.mesh.node_group(beam)
        rows = np.array(
            [
                int(np.flatnonzero((fa.kind == 0) & (fa.entity == n))[0])
                for n in nodes.tolist()
            ]
        )
        x = d.mesh.coords[nodes][:, 0]
        i0, i1 = int(np.argmin(x)), int(np.argmax(x))
        for combo in combos:
            uz = np.zeros(len(rows))
            for case, coef in combo.coefficients.items():
                if variable_only and case in PERMANENT:
                    continue
                uz += coef * fa.arrays[f"cas/{case}"][rows, k]
            chord = uz[i0] + (uz[i1] - uz[i0]) * (x - x[i0]) / (x[i1] - x[i0])
            rel = uz - chord
            j = int(np.argmax(np.abs(rel)))
            if abs(rel[j]) > abs(best[0]):
                best = (float(rel[j]), beam, combo.name)
    assert abs(span - (float(x[i1]) - float(x[i0]))) < 1e-9
    return best


def _absolute_uz(
    d: Deliverables, fa: FieldArrays, combos: list[Combination], variable_only: bool
) -> tuple[float, str]:
    comps = list(fa.info.components)
    k = comps.index("DZ")
    nodes = np.unique(
        np.concatenate([d.mesh.node_group(b) for b in ("PP_YM", "PP_YP")])
    )
    rows = np.array(
        [
            int(np.flatnonzero((fa.kind == 0) & (fa.entity == n))[0])
            for n in nodes.tolist()
        ]
    )
    best = (0.0, "")
    for combo in combos:
        uz = np.zeros(len(rows))
        for case, coef in combo.coefficients.items():
            if variable_only and case in PERMANENT:
                continue
            uz += coef * fa.arrays[f"cas/{case}"][rows, k]
        j = int(np.argmax(np.abs(uz)))
        if abs(uz[j]) > abs(best[0]):
            best = (float(uz[j]), combo.name)
    return best


def sweep_point(ctx: ProjectContext, root: Path, k: float) -> dict[str, Any]:
    """One line of the inertia table (k × IY): deflections at the characteristic SLS,
    My max of a main beam at ULS, Wel,y needed for a ratio of 1,0. Wel,y needed is
    |My| / (f/γM1 − |N|/A − |Mz|/Wel,z) over the (combination, end) pairs where the
    bracket is positive; `part_N_Mz_max` is the largest (|N|/A + |Mz|/Wel,z)/(f/γM1),
    the part no Wel,y can reduce, and `cas_impossibles` counts the pairs where it
    reaches 1,0 (A and Wel,z must change, not Wel,y)."""
    d = Deliverables(root)
    depl = _beam_field(d, ctx, "DEPL")
    efge = _beam_field(d, ctx, "EFGE_ELNO")
    comps = list(efge.info.components)
    s = sections(ctx)["mp1200"]
    rows = beam_rows(d, efge, "POUTRES_PRINC", "PP_")
    out: dict[str, Any] = {"k": k}
    for set_name in SETS:
        by_state = _by_state(set_name)
        sls = by_state[SLS_C]
        for variable_only, tag in ((False, "total"), (True, "variables")):
            rel, beam, combo = _relative_deflection(d, depl, sls, variable_only)
            out[f"{set_name}|fleche_relative_{tag}_mm"] = rel * 1e3
            out[f"{set_name}|fleche_relative_{tag}_lieu"] = f"{beam} ; {combo}"
            uz, combo_abs = _absolute_uz(d, depl, sls, variable_only)
            out[f"{set_name}|uz_absolu_{tag}_mm"] = uz * 1e3
            out[f"{set_name}|uz_absolu_{tag}_combinaison"] = combo_abs
        uls = by_state["ELU_fondamental"] + by_state["ELU_accidentel"]
        stack = _stack(efge, uls, rows.index.tolist())
        my = np.abs(stack[:, :, comps.index("MFY")])
        ci, ri = np.unravel_index(int(my.argmax()), my.shape)
        out[f"{set_name}|My_max_ELU_kNm"] = float(my[ci, ri]) * 1e-3
        out[f"{set_name}|My_max_ELU_lieu"] = f"{rows.labels[ri]} ; {uls[ci].name}"
        for state, label in (("ELU_fondamental", "fond"), ("ELU_accidentel", "acc")):
            combos = by_state[state]
            sub = _stack(efge, combos, rows.index.tolist())
            n = np.abs(sub[:, :, comps.index("N")])
            mz = np.abs(sub[:, :, comps.index("MFZ")])
            my = np.abs(sub[:, :, comps.index("MFY")])
            for strength, mask, tag in (
                (s.f0, np.ones(len(rows.index), dtype=bool), "f0"),
                (s.f0_haz, rows.welded, "f0_haz"),
            ):
                key = f"{set_name}|{label}|{tag}"
                limit = strength / s.gamma_m1
                base = np.where(mask[None, :], (n / s.area + mz / s.w_z) / limit, 0.0)
                ci, ri = np.unravel_index(int(base.argmax()), base.shape)
                out[f"{key}|part_N_Mz_max"] = float(base[ci, ri])
                out[f"{key}|part_N_Mz_max_lieu"] = (
                    f"{rows.labels[ri]} ; {combos[ci].name}"
                )
                room = limit * (1.0 - base)
                feasible = mask[None, :] & (room > 0.0)
                need = np.where(feasible, my / np.where(feasible, room, 1.0), 0.0)
                ci, ri = np.unravel_index(int(need.argmax()), need.shape)
                impossible = int((mask[None, :] & (room <= 0.0)).sum())
                out[f"{key}|Wel_y_necessaire_mm3"] = (
                    float(need[ci, ri]) * 1e9 if impossible == 0 else math.inf
                )
                out[f"{key}|Wel_y_necessaire_lieu"] = (
                    f"{rows.labels[ri]} ; {combos[ci].name}"
                    if impossible == 0
                    else "impossible par Wel,y seul (part N + Mz ≥ 1)"
                )
                out[f"{key}|cas_impossibles"] = impossible
    return out


def fit_inverse(ks: list[float], f: list[float]) -> tuple[float, float, float]:
    """Least squares f(k) = a + b/k; returns a, b and the largest residual."""
    m = np.array([[1.0, 1.0 / k] for k in ks])
    (a, b), *_ = np.linalg.lstsq(m, np.array(f), rcond=None)
    residual = float(np.max(np.abs(m @ np.array([a, b]) - np.array(f))))
    return float(a), float(b), residual


def needed_inertia(
    ctx: ProjectContext, table: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """I needed of one main beam for a relative deflection under the variable actions
    of L/200, L/250, L/300 (fit a + b/k, docs/essais_lot50bis.md § 3)."""
    d = {k: v.value for k, v in ctx.data().items().items()}
    iy = float(d["poutres_principales.inertie_forte"])  # type: ignore[arg-type]
    span = geometry().parameters["L"]
    ks = [float(line["k"]) for line in table]
    out = []
    for set_name in SETS:
        f = [
            abs(float(line[f"{set_name}|fleche_relative_variables_mm"]))
            for line in table
        ]
        a, b, residual = fit_inverse(ks, f)
        for limit in LIMITS:
            target = span * 1e3 / limit
            k_need = b / (target - a) if target > a else math.inf
            out.append(
                {
                    "jeu": set_name,
                    "critere": f"L/{limit}",
                    "fleche_limite_mm": target,
                    "ajustement_a_mm": a,
                    "ajustement_b_mm": b,
                    "residu_max_mm": residual,
                    "k_necessaire": k_need,
                    "Iy_necessaire_mm4": k_need * iy,
                    "Iy_necessaire_cm4": k_need * iy * 1e-4,
                    "Iy_MP1200_mm4": iy,
                }
            )
    return out


def lot50_comparison(
    ctx: ProjectContext, old_root: Path, new_root: Path
) -> list[dict[str, Any]]:
    """Effect of P24 and P25: ULS envelopes of set B per family (N, |My|, |Mz|), the
    temperature cases TP and TM alone (N min/max), and the quay hinges (DY under TP and
    at ULS), lot 50 against lot 50 bis."""
    out: list[dict[str, Any]] = []
    old, new = Deliverables(old_root), Deliverables(new_root)
    uls = _by_state("B")["ELU_fondamental"]
    for family, (group, prefix, _key) in FAMILIES.items():
        values: dict[str, dict[str, float]] = {}
        for tag, d in (("lot50", old), ("lot50bis", new)):
            fa = _beam_field(d, ctx, "EFGE_ELNO")
            comps = list(fa.info.components)
            rows = beam_rows(d, fa, group, prefix)
            stack = _stack(fa, uls, rows.index.tolist())
            v = {
                "ELU B, N min (kN)": stack[:, :, comps.index("N")].min() * 1e-3,
                "ELU B, N max (kN)": stack[:, :, comps.index("N")].max() * 1e-3,
                "ELU B, |My| max (kN·m)": np.abs(stack[:, :, comps.index("MFY")]).max()
                * 1e-3,
                "ELU B, |Mz| max (kN·m)": np.abs(stack[:, :, comps.index("MFZ")]).max()
                * 1e-3,
            }
            for case in ("TP", "TM"):
                n = fa.arrays[f"cas/{case}"][rows.index, comps.index("N")]
                v[f"{case} seul, N min (kN)"] = n.min() * 1e-3
                v[f"{case} seul, N max (kN)"] = n.max() * 1e-3
            values[tag] = {k: float(x) for k, x in v.items()}
        for quantity in values["lot50"]:
            out.append(
                {
                    "famille": family,
                    "grandeur": quantity,
                    "lot50": values["lot50"][quantity],
                    "lot50bis": values["lot50bis"][quantity],
                }
            )
    for tag, d in (("lot50", old), ("lot50bis", new)):
        fa = _beam_field(d, ctx, "REAC_NODA")
        comps = list(fa.info.components)
        nodes = d.mesh.node_group("APP_QUAI")
        for node in nodes.tolist():
            r = int(np.flatnonzero((fa.kind == 0) & (fa.entity == node))[0])
            y = float(d.mesh.coords[node][1])
            side = "Y < 0" if y < 0 else "Y > 0"
            stack = _stack(fa, uls, [r])[:, 0, :]
            for comp in ("DY", "DZ"):
                tp = float(fa.arrays["cas/TP"][r, comps.index(comp)]) * 1e-3
                out.append(
                    {
                        "famille": f"rotule {side}",
                        "grandeur": f"TP seul, R{comp[1]} (kN)",
                        tag: tp,
                    }
                )
                col = stack[:, comps.index(comp)] * 1e-3
                out.append(
                    {
                        "famille": f"rotule {side}",
                        "grandeur": f"ELU B, R{comp[1]} min / max (kN)",
                        tag: f"{col.min():.1f} / {col.max():.1f}".replace(".", ","),
                    }
                )
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for line in out:
        key = (line["famille"], line["grandeur"])
        merged.setdefault(key, {"famille": key[0], "grandeur": key[1]}).update(line)
    return list(merged.values())


def _cell(v: Any) -> Any:
    if isinstance(v, float):
        if math.isinf(v):
            return "inf"
        return f"{v:.6g}".replace(".", ",")
    return v


def write_csv(path: Path, lines: list[dict[str, Any]], header: str) -> None:
    fields: list[str] = []
    for line in lines:
        fields += [k for k in line if k not in fields]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        stream.write(f"# {header}\n")
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for line in lines:
            writer.writerow({k: _cell(line.get(k, "")) for k in fields})


__all__ = [
    "WARNING",
    "Section",
    "family_summary",
    "fit_inverse",
    "hinge_reactions",
    "lot50_comparison",
    "needed_inertia",
    "ratios",
    "sections",
    "support_feet",
    "sweep_point",
    "welded_nodes",
    "write_csv",
]
