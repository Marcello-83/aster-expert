"""Project deliverables of PONTONS-ALU-01 (lot 50) that the generic chain does not
write: both sets of combinations (A, S2; B, PRO) side by side, from the elementary
cases of the deliverables (`resultats/livrables/donnees/`, never a new run).

- per family of beams: for N, VY, VZ, MT, MFY, MFZ, the min and max per limit state
  and set, with the complete concomitant torsor, the place (member, element, end,
  coordinates), the combination and its elementary cases; convention of Code_Aster
  and of the AVP tables (N > 0 in tension; for the main beams y_l is the strong axis:
  MFY = My, VZ = Vz, MFZ = Mz, VY = Vy, MT = Mx);
- reactions of the quay hinges, per node and per limit state;
- displacements under the characteristic SLS: UZ min / max of the deck, |UY| max, UX
  at the supports (feet of the support profiles, heads of the posts);
- comparison with the AVP results (§ D6), orders of magnitude only.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.livrables.donnees import Deliverables, FieldArrays
from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons import STATE_OF_FAMILY, Combination, combinations

FloatArray = NDArray[np.float64]

BEAM_FAMILIES = {
    "poutres_principales": ("POUTRES_PRINC", "PP_"),
    "montants": ("MONTANTS", "MONT_"),
    "diagonales": ("DIAGONALES", "DIAG_"),
    "pannes_secondaires": ("PANNES_SEC", "PANNE_"),
    "profiles_supports": ("SUPPORTS", "SUP_"),
    "chevetre": ("CHEVETRE", "CHEVETRE"),
    "poteaux": ("POTEAUX", "POT_"),
}
STATES = (
    "ELU_fondamental",
    "ELU_accidentel",
    "ELS_caracteristique",
    "ELS_frequent",
    "ELS_quasi_permanent",
)
DECK_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES", "PANNES_SEC")

AVP = {
    # § D6 de l'annexe « Données » : ELU fondamental et accidentel, kN et kN·m.
    "poutres_principales": {
        "ELU_fondamental": {
            "N": (-139, 78),
            "VY": (-18, 13),
            "VZ": (-28, 20),
            "MFY": (-32, 20),
            "MFZ": (-5, 5),
        },
        "ELU_accidentel": {
            "N": (-150, 123),
            "VY": (-60, 49),
            "MFY": (-23, 20),
            "MFZ": (-15, 7),
        },
    },
    "montants": {
        "ELU_fondamental": {"N": (-33, 38), "VY": (-26, 29), "MFY": (-7, 4)},
        "ELU_accidentel": {"N": (-41, 108), "MFY": (-10, 9)},
    },
    "diagonales": {
        "ELU_fondamental": {"N": (-53, 32), "MFY": (-10, 5)},
        "ELU_accidentel": {"N": (-156, 60), "MFY": (-18, 4)},
    },
    "pannes_secondaires": {
        "ELU_fondamental": {"N": (-51, 64), "VY": (-5, 8), "MFY": (-1, 1)},
        "ELU_accidentel": {"N": (-42, 53), "VY": (-10, 10)},
    },
    "poteaux": {
        "ELU_fondamental": {"N": (-72, 14), "MFY": (-20, 52)},
        "ELU_accidentel": {"N": (-58, 26), "MFZ": (-20, 17)},
    },
}


@dataclass(frozen=True)
class Rows:
    """Rows of a field restricted to a set of cells or nodes, with their place."""

    index: NDArray[np.int64]
    labels: list[str]
    coords: FloatArray


def _field(d: Deliverables, ctx: ProjectContext, name: str) -> FieldArrays:
    section = ctx.declaration.deliverables
    assert section is not None
    info = next(i for i in d.field_infos(section.fields) if i.field == name)
    return d.field(info)


def _beam_rows(d: Deliverables, fa: FieldArrays, group: str, prefix: str) -> Rows:
    member_of: dict[int, str] = {}
    for key in d.mesh.arrays:
        if key.startswith("gma_") and key.split("_", 2)[2].startswith(prefix):
            name = key.split("_", 2)[2]
            if prefix == "CHEVETRE" or name != group:
                for cell in d.mesh.arrays[key].tolist():
                    member_of[int(cell)] = name
    cells = d.mesh.cell_group(group)
    assert cells is not None
    level, ids = cells
    wanted = set(ids.tolist())
    sel = np.flatnonzero(
        (fa.kind == 1)
        & (fa.level == level)
        & np.isin(fa.entity, np.array(sorted(wanted)))
    )
    nodes = fa.node_of_row(d.mesh)[sel]
    labels = [
        f"{member_of.get(int(fa.entity[i]), group)} maille {int(fa.entity[i])}"
        f" extrémité {int(fa.local[i]) + 1}"
        for i in sel
    ]
    return Rows(sel, labels, d.mesh.coords[nodes])


def _combined(
    fa: FieldArrays, combo: Combination, rows: NDArray[np.int64]
) -> FloatArray:
    total = np.zeros((len(rows), fa.arrays["cas/G1"].shape[1]))
    for case, coef in combo.coefficients.items():
        total += coef * fa.arrays[f"cas/{case}"][rows]
    return total


def _extremes(
    fa: FieldArrays, rows: Rows, combos: list[Combination], components: tuple[str, ...]
) -> list[dict[str, Any]]:
    stack = np.stack([_combined(fa, c, rows.index) for c in combos])  # (C, R, K)
    out = []
    for k, comp in enumerate(components):
        values = stack[:, :, k]
        for kind, flat in (("min", values.argmin()), ("max", values.argmax())):
            ci, ri = np.unravel_index(int(flat), values.shape)
            combo = combos[int(ci)]
            torsor = stack[ci, ri]
            out.append(
                {
                    "composante": comp,
                    "extremum": kind,
                    "valeur": float(values[ci, ri]),
                    **{c: float(torsor[j]) for j, c in enumerate(components)},
                    "lieu": rows.labels[int(ri)],
                    "x_m": float(rows.coords[ri][0]),
                    "y_m": float(rows.coords[ri][1]),
                    "z_m": float(rows.coords[ri][2]),
                    "combinaison": combo.name,
                    "definition": combo.definition,
                }
            )
    return out


def _by_state(set_name: str) -> dict[str, list[Combination]]:
    out: dict[str, list[Combination]] = {}
    for c in combinations(set_name):
        out.setdefault(STATE_OF_FAMILY[c.family], []).append(c)
    return out


def beam_torsors(ctx: ProjectContext) -> dict[str, list[dict[str, Any]]]:
    d = Deliverables(ctx.results_dir / "livrables")
    fa = _field(d, ctx, "EFGE_ELNO")
    comps = tuple(fa.info.components)
    out: dict[str, list[dict[str, Any]]] = {}
    for family, (group, prefix) in BEAM_FAMILIES.items():
        rows = _beam_rows(d, fa, group, prefix)
        lines = []
        for set_name in ("A", "B"):
            for state, combos in _by_state(set_name).items():
                for line in _extremes(fa, rows, combos, comps):
                    lines.append({"jeu": set_name, "etat_limite": state, **line})
        out[family] = lines
    return out


def node_extremes(
    ctx: ProjectContext, field: str, groups: tuple[str, ...], state_filter: str | None
) -> list[dict[str, Any]]:
    d = Deliverables(ctx.results_dir / "livrables")
    fa = _field(d, ctx, field)
    comps = tuple(fa.info.components)
    nodes = np.unique(np.concatenate([d.mesh.node_group(g) for g in groups]))
    sel = np.flatnonzero((fa.kind == 0) & np.isin(fa.entity, nodes))
    rows = Rows(
        sel,
        [f"nœud {int(fa.entity[i])}" for i in sel],
        d.mesh.coords[fa.entity[sel]],
    )
    out = []
    for set_name in ("A", "B"):
        for state, combos in _by_state(set_name).items():
            if state_filter is not None and state != state_filter:
                continue
            for line in _extremes(fa, rows, combos, comps):
                out.append({"jeu": set_name, "etat_limite": state, **line})
    return out


def comparison(torsors: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for family, states in AVP.items():
        for state, comps in states.items():
            for comp, (lo, hi) in comps.items():
                row: dict[str, Any] = {
                    "famille": family,
                    "etat_limite": state,
                    "composante": comp,
                    "avp_min": lo,
                    "avp_max": hi,
                }
                for set_name in ("A", "B"):
                    for kind in ("min", "max"):
                        v = next(
                            line["valeur"]
                            for line in torsors[family]
                            if line["jeu"] == set_name
                            and line["etat_limite"] == state
                            and line["composante"] == comp
                            and line["extremum"] == kind
                        )
                        row[f"{set_name}_{kind}"] = round(v / 1000.0, 1)
                out.append(row)
    return out


def _write_csv(path: Path, lines: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(lines[0]), delimiter=";")
        writer.writeheader()
        for line in lines:
            writer.writerow(
                {
                    k: (f"{v:.6g}".replace(".", ",") if isinstance(v, float) else v)
                    for k, v in line.items()
                }
            )


HEADER = (
    "Unités SI (N, N·m, m). Convention Code_Aster et des tableaux de l'AVP : N > 0 en "
    "traction ; repère local de projet.yaml (poutres principales : y_l = axe fort, "
    "MFY = My, VZ = Vz, MFZ = Mz, VY = Vy, MT = Mx). Jeu A : combinaisons de S2 "
    "reproduites ; jeu B : PRO (EN 1990). Torseur concomitant : même lieu, même "
    "combinaison."
)


def write_all(ctx: ProjectContext, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    torsors = beam_torsors(ctx)
    files = []
    for family, lines in torsors.items():
        path = out_dir / f"torseurs_{family}.csv"
        _write_csv(path, lines)
        files.append(path.name)
    reactions = node_extremes(ctx, "REAC_NODA", ("APP_QUAI",), None)
    _write_csv(out_dir / "reactions_appuis_quai.csv", reactions)
    deck = node_extremes(ctx, "DEPL", DECK_GROUPS, "ELS_caracteristique")
    _write_csv(out_dir / "deplacements_tablier_els_car.csv", deck)
    supports = node_extremes(
        ctx, "DEPL", ("PIEDS_SUPPORTS", "TETES_POTEAUX"), "ELS_caracteristique"
    )
    _write_csv(out_dir / "deplacements_appuis_els_car.csv", supports)
    cmp = comparison(torsors)
    _write_csv(out_dir / "comparaison_avp.csv", cmp)
    summary = {
        "convention": HEADER,
        "fichiers": [
            *files,
            "reactions_appuis_quai.csv",
            "deplacements_tablier_els_car.csv",
            "deplacements_appuis_els_car.csv",
            "comparaison_avp.csv",
        ],
        "comparaison_avp": cmp,
        "deplacements_tablier_els_car": [
            {k: line[k] for k in ("jeu", "composante", "extremum", "valeur", "lieu")}
            for line in deck
            if line["composante"] in ("DX", "DY", "DZ")
        ],
    }
    (out_dir / "syntheses_lot50.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


__all__ = ["AVP", "beam_torsors", "comparison", "node_extremes", "write_all"]
