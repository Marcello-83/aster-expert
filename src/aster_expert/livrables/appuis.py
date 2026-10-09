"""Design moment on a support (lot 49 ter, rule E27 of MM): M_dim = max(M_nu ;
fraction × M_encastrement).

The clause (EN 1992-1-1, §5.3.2.2(3) and its note) is cited after MM and the
supervisor: the corpus of the repository does not contain the Eurocode. Everything
here is declared by the project (`DesignSection.design_moment`), nothing knows a
structure.

For every combination of a limit state and every position of its moving load, support
by support (`supports`: the nearest node of a node group, compared on the declared
axes):

- M_nu: the largest moment of the support's sign (`moment_signs` of the section) over
  the usable rows of the section, in the reference;
- M_enc: the same over the rows of `axis_rule`, in the auxiliary model, under the same
  combination and position, its excluded cases (`DerivedModel.excluded_cases`) left
  out;
- M_axe: the same rows of `axis_rule` in the reference (comparison only);
- M_dim = max(M_nu ; fraction × M_enc), with the governing term.

The envelope keeps, per limit state, the largest M_dim with its support, combination,
position and the concomitant N and V read at the face (the row of M_nu) in the
reference: the convention of the exported torsor. Everything is computed on the rows
the rule needs only (`subset`), by the arithmetic of `aster_expert.livrables.torseurs`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.donnees import Mesh
from aster_expert.livrables.sections import (
    AXES,
    M_RES,
    FamilyRows,
    SectionRows,
)
from aster_expert.livrables.torseurs import evaluate, torsor_entry, unit_of
from aster_expert.projet.declaration import DesignMoment
from aster_expert.projet.errors import ProjectError

SIGN = {"positive": 1.0, "negative": -1.0}


def subset(fr: FamilyRows, rows: Any) -> FamilyRows:
    """A view of `fr` restricted to `rows` (cases sliced; places kept)."""
    rows = np.asarray(rows, dtype=np.int64)
    synthetic = {
        k: fr.synthetic[int(r)] for k, r in enumerate(rows) if int(r) in fr.synthetic
    }
    return FamilyRows(
        family=fr.family,
        info=fr.info,
        index=fr.index[rows],
        node=fr.node[rows],
        xyz=fr.xyz[rows],
        kind=fr.kind[rows],
        element=fr.element[rows],
        local=fr.local[rows],
        level=fr.level[rows],
        member=[fr.member[int(r)] for r in rows],
        columns=fr.columns,
        cases={c: v[rows] for c, v in fr.cases.items()},
        added=fr.added,
        synthetic=synthetic,
        tee=fr.tee,
    )


def support_of(mesh: Mesh, dm: DesignMoment, xyz: Any) -> tuple[Any, Any]:
    """(support index of each point, coordinates of the supports)."""
    nodes = mesh.node_group(dm.supports.node_group)
    if nodes.size == 0:
        message = f"E27 : groupe d'appuis {dm.supports.node_group} vide"
        raise ProjectError(message)
    axes = [AXES[a] for a in dm.supports.axes]
    centres = np.unique(np.round(mesh.coords[nodes][:, axes], 6), axis=0)
    d = np.linalg.norm(xyz[:, None, axes] - centres[None, :, :], axis=2)
    return np.argmin(d, axis=1), centres


def section_sign(sec: SectionRows, dm: DesignMoment) -> float:
    if dm.quantity == M_RES:
        return 1.0
    declared = sec.section.moment_signs.get(dm.quantity)
    if declared not in SIGN:
        message = (
            f"section {sec.section.name} : E27 sur {dm.quantity} exige un signe "
            "d'appui déclaré (`moment_signs` : positive ou negative)"
        )
        raise ProjectError(message)
    return SIGN[declared]


@dataclass
class SupportMoment:
    """Per limit state: the governing M_dim and, per support, its own envelope."""

    state: str
    best: dict[str, Any] | None = None
    per_support: dict[int, dict[str, Any]] = field(default_factory=dict)
    extremes: dict[int, dict[str, tuple[float, int, int]]] = field(default_factory=dict)
    """Support -> own envelope of M_nu and of M_axe (value, combination, position):
    comparison columns, not the instant of M_dim."""
    evaluations: int = 0


def _per_support(values: Any, support: Any, count: int) -> tuple[Any, Any]:
    """(max per support, row of that max) of `values` over rows grouped by support;
    −inf where a support has no row."""
    best = np.full(count, -np.inf)
    where = np.full(count, -1, dtype=np.int64)
    for k in range(count):
        rows = np.nonzero(support == k)[0]
        if rows.size:
            j = rows[int(np.argmax(values[rows]))]
            best[k], where[k] = values[j], j
    return best, where


def design_moment(
    *,
    mesh: Mesh,
    ref: FamilyRows,
    sec: SectionRows,
    ref_axis_rows: Any,
    aux: FamilyRows,
    aux_axis_rows: Any,
    dm: DesignMoment,
    state_combinations: dict[str, list[tuple[int, GenericCombination]]],
    excluded: tuple[str, ...],
) -> dict[str, SupportMoment]:
    """E27 for one section, per limit state (see module docstring)."""
    sign = section_sign(sec, dm)
    excluded_rows = (
        sec.singular if sec.section.exclude_singular else np.zeros_like(sec.mask)
    )
    nu_rows = np.where(sec.mask & ~excluded_rows)[0]
    if nu_rows.size == 0 or len(ref_axis_rows) == 0 or len(aux_axis_rows) == 0:
        message = (
            f"section {sec.section.name} : E27 sans ligne au nu "
            f"({nu_rows.size}), à l'axe ({len(ref_axis_rows)}) ou dans "
            f"{dm.auxiliary} ({len(aux_axis_rows)})"
        )
        raise ProjectError(message)
    ref_rows = np.concatenate([nu_rows, np.asarray(ref_axis_rows, dtype=np.int64)])
    ref_sub = subset(ref, ref_rows)
    aux_sub = subset(aux, aux_axis_rows)
    n_nu = nu_rows.size
    s_ref, centres = support_of(mesh, dm, ref_sub.xyz)
    s_aux, _ = support_of(mesh, dm, aux_sub.xyz)
    count = len(centres)
    q_ref = ref_sub.column(dm.quantity)
    q_aux = aux_sub.column(dm.quantity)
    out: dict[str, SupportMoment] = {}
    for state, combos in state_combinations.items():
        result = SupportMoment(state)
        aux_values = {
            (ci, pi): values[:, q_aux]
            for ci, pi, values in evaluate(aux_sub, combos, exclude=excluded)
        }
        for ci, pi, values in evaluate(ref_sub, combos):
            result.evaluations += 1
            signed = sign * values[:, q_ref]
            m_nu, at_nu = _per_support(signed[:n_nu], s_ref[:n_nu], count)
            m_axe, _ = _per_support(signed[n_nu:], s_ref[n_nu:], count)
            m_enc, at_enc = _per_support(sign * aux_values[(ci, pi)], s_aux, count)
            m_dim = np.maximum(m_nu, dm.fraction * m_enc)
            for k in range(count):
                for key, value in (("M_nu", m_nu[k]), ("M_axe", m_axe[k])):
                    own = result.extremes.setdefault(k, {})
                    if np.isfinite(value) and value > own.get(key, (-np.inf,))[0]:
                        own[key] = (float(value), ci, pi)
                if not np.isfinite(m_nu[k]) or not np.isfinite(m_enc[k]):
                    continue
                current = result.per_support.get(k)
                if current is not None and m_dim[k] <= current["M_dim"]:
                    continue
                governing = (
                    "M_nu" if m_nu[k] >= dm.fraction * m_enc[k] else "0,65·M_enc"
                )
                if dm.fraction != 0.65 and governing != "M_nu":
                    governing = f"{dm.fraction:g}·M_enc"
                result.per_support[k] = {
                    "appui": [float(v) for v in centres[k]],
                    "combinaison_index": ci,
                    "position_index": pi,
                    "M_nu": float(m_nu[k]),
                    "M_enc": float(m_enc[k]),
                    "fraction_M_enc": float(dm.fraction * m_enc[k]),
                    "M_dim": float(m_dim[k]),
                    "M_axe": float(m_axe[k]),
                    "terme_gouvernant": governing,
                    "ligne_nu": int(nu_rows[int(at_nu[k])]),
                    "ligne_auxiliaire": int(aux_axis_rows[int(at_enc[k])]),
                }
        for entry in result.per_support.values():
            if result.best is None or entry["M_dim"] > result.best["M_dim"]:
                result.best = entry
        out[state] = result
    return out


def describe(
    result: SupportMoment,
    *,
    ref: FamilyRows,
    aux: FamilyRows,
    sec: SectionRows,
    dm: DesignMoment,
    combinations: list[GenericCombination],
    sign: float,
) -> dict[str, Any] | None:
    """The governing E27 entry of a state, with the torsor read at the face (N and V
    of the reference at the row of M_nu, same instant) and its M replaced by M_dim."""
    best = result.best
    if best is None:
        return None
    ci, pi = best["combinaison_index"], best["position_index"]
    entry = torsor_entry(ref, combinations, best["ligne_nu"], ci, pi)
    torsor = dict(entry["torseur_si"])
    torsor[dm.quantity] = sign * best["M_dim"]
    aux_place = aux.place(best["ligne_auxiliaire"])
    unit = unit_of(ref, dm.quantity)
    per_support = []
    for k, e in sorted(result.per_support.items()):
        comb = combinations[e["combinaison_index"]]
        per_support.append(
            {
                "appui": e["appui"],
                "combinaison": comb.name,
                "position_mobile": comb.mobile_cases[e["position_index"]]
                if e["position_index"] >= 0
                else None,
                **{
                    key: e[key]
                    for key in (
                        "M_nu",
                        "M_enc",
                        "fraction_M_enc",
                        "M_dim",
                        "M_axe",
                        "terme_gouvernant",
                    )
                },
                "index": k,
                **{
                    f"{key}_max": {
                        "valeur": value,
                        "combinaison": combinations[ci].name,
                        "position_mobile": combinations[ci].mobile_cases[pi]
                        if pi >= 0
                        else None,
                    }
                    for key, (value, ci, pi) in result.extremes.get(k, {}).items()
                },
            }
        )
    return {
        "section": sec.section.name,
        "famille": ref.family.name,
        "etat_limite": result.state,
        "grandeur": f"M_dim sur appui (E27, {dm.quantity})",
        "libelle_ingenieur": "moment sur appui de dimensionnement (E27)",
        "colonne": dm.quantity,
        "role": "M",
        "valeur_si": sign * best["M_dim"],
        "unite_si": unit,
        "significative": True,
        "motif": None,
        "principal": True,
        "e27": {
            "regle": "M_dim = max(M_nu ; "
            f"{dm.fraction:g} × M_encastrement) (E27, {dm.source})",
            "auxiliaire": dm.auxiliary,
            "M_nu_si": best["M_nu"],
            "M_enc_si": best["M_enc"],
            "fraction": dm.fraction,
            "fraction_M_enc_si": best["fraction_M_enc"],
            "M_dim_si": best["M_dim"],
            "M_axe_si": best["M_axe"],
            "terme_gouvernant": best["terme_gouvernant"],
            "signe": sign,
            "appui": best["appui"],
            "lieu_auxiliaire": aux_place,
            "convention": "valeurs signées dans le sens d'appui de la section "
            "(M > 0 : moment sur appui) ; N et V lus au nu dans la référence, à la "
            "ligne de M_nu, même combinaison et même position ; M_axe : comparaison "
            "seulement",
            "evaluations": result.evaluations,
            "par_appui": per_support,
            "M_nu_max_si": max(
                (v["M_nu"][0] for v in result.extremes.values() if "M_nu" in v),
                default=None,
            ),
            "M_axe_max_si": max(
                (v["M_axe"][0] for v in result.extremes.values() if "M_axe" in v),
                default=None,
            ),
        },
        **{**entry, "torseur_si": torsor},
    }


__all__ = ["SupportMoment", "describe", "design_moment", "subset", "support_of"]
