# ruff: noqa: E501 -- en-têtes des CSV (une ligne « # » par fichier, phrase entière)
"""Displacements of lot 53 for PONTONS-ALU-01 (consigne `docs/lots/lot53_consigne.md`):
DX, DY, DZ (and the rotations of the pile heads and footings) under berthing (AC, ACA)
and mooring (AML, AM1, AM2, AMF), post-processing of variant B52 of lot 52.

Nothing is recomputed by Code_Aster: the DEPL tables of the lot 52 run (unit 32, every
node, six components) are read again by the reader of lot 52 (`exports_lot52.load`,
which also folds the link reactions, CA-036) and combined with the events and the rules
of lot 52 (`combinaisons_lot51quater`, envelopes by decomposition of
`combinaisons_lot51ter`).

Output points (`output_points`), read from the mesh groups only:

- the 20 pin bearings: `axe` (translation of the pin point carried by ear 1, the deck,
  u + θ ∧ (P − N), choice A11), `chevetre` (node of the cap beam under the pin, group
  `AX_<axis>_K`), `relatif` (pin point by ear 1 minus pin point by the cap node, the
  slide of `deplacements_axes.csv`);
- mid-span of the main beams of T1 to T5 and the tip of the cantilever, sides YM, YP;
- the 20 pile heads (+0,69) and the centre of the 5 footings (no node there: mean of the
  two nodes of Y = 0 at equal distance, i.e. linear interpolation);
- the two supports of the abutment.

Every point is a linear combination of nodal DEPL (`Term`), so that its value under an
event or a combination is the same combination of its unit values.
"""

from __future__ import annotations

import csv
import json
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.combinaisons_lot51ter import (
    Event,
    brute_force,
    envelope,
    governing,
)
from pontons_alu_01.exports_lot51 import geo, sha256
from pontons_alu_01.exports_lot51 import write as write_csv
from pontons_alu_01.exports_lot51ter import (
    VariantData51ter,
    _beam_nodes,
    force_rows,
    pier_of,
    pin_results,
    reaction_rows,
    soil_forces,
)
from pontons_alu_01.exports_lot52 import load

FloatArray = NDArray[np.float64]
LOT = "lot53"
SOURCE_LOT = "lot52"
CODE = "B52"
SEED = 53
MM = 1e3
MRAD = 1e3
COMPONENTS = ("DX", "DY", "DZ", "DRX", "DRY", "DRZ")
UNIT_PREFIXES = ("ACN_", "ACX_", "ACZ_", "AMY_", "AMX_")
UNIT_THERMAL = ("TP", "TM")
FAMILIES = ("AC", "ACA", "AM", "AMF")
"""Actions of the events of the lot (AM: AML, AM1, AM2)."""
STATES = ("ELS_caracteristique", "ELS_frequent", "ELU_accidentel")
VARIANTS = (
    ("total", ()),
    ("total_hors_T", ("T",)),
    ("variables_avec_T", ("G",)),
    ("variables_sans_T", ("G", "T")),
)
"""Name and actions set to zero (G: G1, G2 and DEJ, P49; T: TP, TM)."""
EXCLUDED_CASES = {"G": ("G1", "G2", "DEJ"), "T": ("TP", "TM")}
ROTATION_KINDS = ("tete", "semelle")


# --------------------------------------------------------------------------- points


@dataclass(frozen=True)
class Term:
    node: int
    weight: float
    pin: tuple[float, float, float] | None
    """Point carried by the node (u + θ ∧ (P − N)); None: the node itself."""


@dataclass(frozen=True)
class OutPoint:
    name: str
    kind: str
    """axe, chevetre, relatif, mi_travee, porte_a_faux, tete, semelle, culee."""
    place: str
    """Pier (P1…), span (T1…, PF) or CULEE."""
    side: str
    x: float
    y: float
    z: float
    terms: tuple[Term, ...]

    @property
    def rotations(self) -> bool:
        return self.kind in ROTATION_KINDS

    @property
    def absolute(self) -> bool:
        return self.kind != "relatif"

    @property
    def node(self) -> int | None:
        """The node when the point is one node itself, else None."""
        if len(self.terms) == 1 and self.terms[0].pin is None:
            return self.terms[0].node
        return None


def _node_point(
    vd: VariantData51ter, name: str, kind: str, place: str, side: str, node: int
) -> OutPoint:
    x, y, z = (geo(c) for c in vd.model.coords[node - 1])
    return OutPoint(name, kind, place, side, x, y, z, (Term(node, 1.0, None),))


def footing_centre_terms(vd: VariantData51ter, pier: str) -> tuple[Term, ...]:
    """The node at the centre of the footing, or the two nodes of the same Y at equal
    distance in X (weights ½): linear interpolation."""
    footing = next(f for f in vd.g.footings if f.pier == pier)
    xc, yc, _ = footing.centre
    coords = vd.model.coords
    nodes = [
        n
        for n in vd.model.group_nodes[f"SEMELLE_{pier}"]
        if abs(float(coords[n - 1][1]) - yc) < 1e-9
    ]
    exact = [n for n in nodes if abs(float(coords[n - 1][0]) - xc) < 1e-9]
    if exact:
        return (Term(exact[0], 1.0, None),)
    below = max(
        (n for n in nodes if float(coords[n - 1][0]) < xc),
        key=lambda n: float(coords[n - 1][0]),
    )
    above = min(
        (n for n in nodes if float(coords[n - 1][0]) > xc),
        key=lambda n: float(coords[n - 1][0]),
    )
    d0 = xc - float(coords[below - 1][0])
    d1 = float(coords[above - 1][0]) - xc
    if abs(d0 - d1) > 1e-9:
        message = (
            f"semelle {pier} : nœuds non symétriques autour du centre ({d0}, {d1})"
        )
        raise ValueError(message)
    return (Term(below, 0.5, None), Term(above, 0.5, None))


def output_points(vd: VariantData51ter) -> list[OutPoint]:
    m = vd.model
    pts: list[OutPoint] = []
    for a in vd.g.axes:
        ear = m.group_nodes[a.ear_group(1)][0]
        (cap,) = m.group_nodes[a.cap_group]
        pier, _ = pier_of(a.name)
        pin = (float(a.pin[0]), float(a.pin[1]), float(a.pin[2]))
        px, py, pz = (geo(c) for c in pin)
        pts.append(
            OutPoint(
                f"{a.name}_axe", "axe", pier, a.side, px, py, pz, (Term(ear, 1.0, pin),)
            )
        )
        pts.append(_node_point(vd, f"{a.name}_chevetre", "chevetre", pier, a.side, cap))
        pts.append(
            OutPoint(
                f"{a.name}_relatif",
                "relatif",
                pier,
                a.side,
                px,
                py,
                pz,
                (Term(ear, 1.0, pin), Term(cap, -1.0, pin)),
            )
        )
    n_spans = len(vd.g.footings)
    for k in range(1, n_spans + 1):
        for side in ("YM", "YP"):
            nodes = _beam_nodes(vd, f"PP_T{k}_{side}")
            x0, x1 = (float(m.coords[n - 1][0]) for n in (nodes[0], nodes[-1]))
            mid = min(
                nodes, key=lambda n: abs(float(m.coords[n - 1][0]) - (x0 + x1) / 2)
            )
            pts.append(
                _node_point(vd, f"T{k}_mi_{side}", "mi_travee", f"T{k}", side, mid)
            )
    for side in ("YM", "YP"):
        tip = _beam_nodes(vd, f"PP_PF_{side}")[-1]
        pts.append(_node_point(vd, f"PF_bout_{side}", "porte_a_faux", "PF", side, tip))
    for f in vd.g.footings:
        for chev in ("C1", "C2"):
            for side in ("YM", "YP"):
                (n,) = m.group_nodes[f"TP_{f.pier}_{chev}_{side}_A"]
                pts.append(
                    _node_point(
                        vd, f"{f.pier}{chev}_{side}_tete", "tete", f.pier, side, n
                    )
                )
    for f in vd.g.footings:
        xc, yc, zc = f.centre
        pts.append(
            OutPoint(
                f"{f.pier}_semelle_centre",
                "semelle",
                f.pier,
                "",
                geo(xc),
                geo(yc),
                geo(zc),
                footing_centre_terms(vd, f.pier),
            )
        )
    for side in ("YM", "YP"):
        (n,) = m.group_nodes[f"APP_CULEE_{side}"]
        pts.append(_node_point(vd, f"CULEE_{side}", "culee", "CULEE", side, n))
    return pts


def point_value(
    p: OutPoint, depl: dict[int, FloatArray], coords: FloatArray
) -> FloatArray:
    """DX, DY, DZ, DRX, DRY, DRZ of a point under one case (m, rad)."""
    out = np.zeros(6)
    for t in p.terms:
        d = np.asarray(depl[t.node][:6], dtype=np.float64)
        tr = d[:3]
        if t.pin is not None:
            tr = tr + np.cross(d[3:6], np.array(t.pin) - coords[t.node - 1])
        out[:3] += t.weight * tr
        out[3:] += t.weight * d[3:6]
    return out


def unit_values(vd: VariantData51ter, pts: list[OutPoint]) -> dict[str, FloatArray]:
    """Per unit case: array (points, 6) in m and rad."""
    coords = vd.model.coords
    return {
        c: np.array([point_value(p, vd.tables.depl[c], coords) for p in pts])
        for c in vd.cases
    }


def exported_cases(vd: VariantData51ter) -> list[str]:
    return [c for c in vd.cases if c.startswith(UNIT_PREFIXES) or c in UNIT_THERMAL]


@dataclass(frozen=True)
class Quantity:
    point: int
    component: int

    def scale(self) -> float:
        return MM if self.component < 3 else MRAD


def quantities(pts: list[OutPoint]) -> list[Quantity]:
    out = []
    for i, p in enumerate(pts):
        comps = (0, 1, 2, 3, 4) if p.rotations else (0, 1, 2)
        out += [Quantity(i, c) for c in comps]
    return out


def quantity_arrays(
    unit: dict[str, FloatArray], qs: list[Quantity]
) -> dict[str, FloatArray]:
    pi = np.array([q.point for q in qs])
    ci = np.array([q.component for q in qs])
    return {c: a[pi, ci] for c, a in unit.items()}


def unit_label(q: Quantity) -> str:
    return "mm" if q.component < 3 else "mrad"


# --------------------------------------------------------------------------- events


def event_value(ev: Event, unit: dict[str, FloatArray]) -> FloatArray:
    """Characteristic value of an event without modules (points, 6)."""
    if ev.modules:
        message = f"{ev.name} : événement à modules, hors du lot"
        raise ValueError(message)
    total = np.zeros_like(next(iter(unit.values())))
    for case, c in ev.coefficients.items():
        total = total + c * unit[case]
    return total


def lot_events(vd: VariantData51ter) -> dict[str, Event]:
    return {n: e for n, e in vd.ev.items() if e.action in FAMILIES}


@dataclass
class EventExtreme:
    family: str
    max_value: float
    max_event: str
    min_value: float
    min_event: str


def event_extremes(
    events: dict[str, Event], values: dict[str, FloatArray], qs: list[Quantity]
) -> list[dict[str, EventExtreme]]:
    """Per quantity and per family (and « toutes »): max and min over the events."""
    out: list[dict[str, EventExtreme]] = []
    names = list(events)
    stack = np.array([[values[n][q.point, q.component] for q in qs] for n in names])
    groups = {
        fam: [i for i, n in enumerate(names) if events[n].action == fam]
        for fam in FAMILIES
    }
    groups["toutes"] = list(range(len(names)))
    for j, q in enumerate(qs):
        row: dict[str, EventExtreme] = {}
        for fam, idx in groups.items():
            col = stack[idx, j]
            hi, lo = int(np.argmax(col)), int(np.argmin(col))
            row[fam] = EventExtreme(
                fam,
                float(col[hi]) * q.scale(),
                names[idx[hi]],
                float(col[lo]) * q.scale(),
                names[idx[lo]],
            )
        out.append(row)
    return out


# --------------------------------------------------------------------------- combinations


@dataclass
class Combined:
    value: float
    """Displayed unit (mm, mrad)."""
    label: str
    coefficients: dict[str, float]
    """Coefficients of the unit cases that enter the value (excluded actions removed)."""


def _strip(label: str, ev: dict[str, Event], without: tuple[str, ...]) -> str:
    if not without:
        return label
    head, _, body = label.partition(": ")
    kept = [
        part
        for part in body.split(" + ")
        if ev[part.split("×")[0].split("[")[0]].action not in without
    ]
    return f"{head}: " + (" + ".join(kept) if kept else "aucune action")


def combined_extremes(
    vd: VariantData51ter, f: dict[str, FloatArray], qs: list[Quantity]
) -> dict[tuple[str, str], list[tuple[Combined, Combined]]]:
    """Per (state, variant): per quantity, (max, min) and their combinations."""
    out: dict[tuple[str, str], list[tuple[Combined, Combined]]] = {}
    for state in STATES:
        for variant, without in VARIANTS:
            excluded = {c for a in without for c in EXCLUDED_CASES[a]}
            pair = []
            for sign in (1.0, -1.0):
                ext = envelope(vd.bs, vd.ev, f, state, sign=sign, without=without)
                items = []
                for k, q in enumerate(qs):
                    name, coefs = governing(vd.bs, vd.ev, ext, k)
                    items.append(
                        Combined(
                            float(ext.value[k]) * q.scale(),
                            _strip(name, vd.ev, without),
                            {c: v for c, v in coefs.items() if c not in excluded},
                        )
                    )
                pair.append(items)
            out[(state, variant)] = list(zip(pair[0], pair[1], strict=True))
    return out


def value_from(coefs: dict[str, float], f: dict[str, FloatArray], k: int) -> float:
    return float(sum(c * f[case][k] for case, c in coefs.items()))


# --------------------------------------------------------------------------- checks


def check_fingerprints(ctx: ProjectContext, state: dict[str, Any]) -> dict[str, Any]:
    """Criterion 1: .comm and mesh of the run read again against lot 52."""
    s = state[CODE]
    run = Path(s["execution"]["execution_dir"])
    exports = ctx.results_dir / SOURCE_LOT / "exports" / CODE
    head = (
        (exports / "deplacements_elementaires.csv")
        .open("r", encoding="utf-8")
        .readline()
    )
    got = {
        "comm_execution": sha256(run / "pontons_alu_01.comm"),
        "comm_lot52": sha256(Path(s["comm"])),
        "maillage": sha256(Path(s["maillage"]["med"])),
    }
    declared = {"maillage_etat": s["maillage"]["med_sha256"]}
    ok = (
        got["comm_execution"] == got["comm_lot52"]
        and f".comm sha256 {got['comm_execution']}" in head
        and got["maillage"] == declared["maillage_etat"]
        and f"maillage sha256 {got['maillage']}" in head
    )
    return {**got, **declared, "execution": run.name, "reussi": ok}


def _csv_rows(path: Path, cases: set[str]) -> dict[str, list[list[str]]]:
    out: dict[str, list[list[str]]] = {c: [] for c in cases}
    with path.open("r", encoding="utf-8", newline="") as stream:
        next(stream)
        reader = csv.reader(stream, delimiter=";")
        next(reader)
        for row in reader:
            if row[0] in out:
                out[row[0]].append(row)
    return out


def _gap(
    a: list[list[Any]], b: list[list[str]], numeric: list[int]
) -> tuple[float, float]:
    """Largest |a − b| over the numeric columns and the largest |a| (absolute)."""
    if len(a) != len(b):
        message = f"nombre de lignes : {len(a)} relues contre {len(b)}"
        raise ValueError(message)
    gap, big = 0.0, 0.0
    for ra, rb in zip(a, b, strict=True):
        for i in numeric:
            va = float(ra[i])
            if va != va:  # nan : cellule vide
                if rb[i] != "":
                    return float("inf"), big
                continue
            gap = max(gap, abs(va - float(rb[i])))
            big = max(big, abs(va))
    return gap, big


def check_reread(ctx: ProjectContext, vd: VariantData51ter) -> dict[str, Any]:
    """Criterion 2: five unit cases drawn (seed 53), reactions, forces and DEPL read
    again from the tables against the CSV of lot 52."""
    cases = sorted(random.Random(SEED).sample(list(vd.cases), 5))
    exports = ctx.results_dir / SOURCE_LOT / "exports" / CODE
    chosen = set(cases)
    react = [r for r in reaction_rows(vd) if r[0] in chosen]
    forces = [r for r in force_rows(vd) if r[0] in chosen]
    depl = [
        [c, n, *(float(x) for x in vd.tables.depl[c][n])]
        for c in cases
        for n in sorted(vd.tables.depl[c])
    ]
    files = {
        "reactions": ("reactions_elementaires.csv", react, list(range(6, 12))),
        "efforts": ("efforts_elementaires.csv", forces, list(range(9, 15))),
        "deplacements": ("deplacements_elementaires.csv", depl, list(range(2, 8))),
    }
    out: dict[str, Any] = {"cas": cases}
    ok = True
    for key, (name, rows, numeric) in files.items():
        ref = _csv_rows(exports / name, chosen)
        worst = 0.0
        for c in cases:
            mine = [r for r in rows if r[0] == c]
            gap, big = _gap(mine, ref[c], numeric)
            rel = gap / big if big > 0 else gap
            worst = max(worst, rel)
        out[key] = {"fichier": name, "ecart_relatif_max": worst}
        ok = ok and worst <= 1e-6
    out["reussi"] = ok
    return out


def check_tp(ctx: ProjectContext, vd: VariantData51ter) -> dict[str, Any]:
    """Criterion 3: DX of the pin of C2 of P5 under TP against `deplacements_axes.csv`."""
    path = ctx.results_dir / SOURCE_LOT / "exports" / CODE / "deplacements_axes.csv"
    n = len(vd.g.footings)
    ref: dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        next(stream)
        for row in csv.DictReader(stream, delimiter=";"):
            if row["palee"] == f"P{n}" and row["chevetre"] == "C2":
                ref[row["rive"]] = float(row["DX_TP"])
    pins = pin_results(vd, "TP")
    out: dict[str, Any] = {}
    for side in ("YM", "YP"):
        got = pins[f"P{n}C2_{side}"].dx
        out[side] = {
            "DX_mm": got * MM,
            "lot52_mm": ref[side] * MM,
            "ecart_relatif": abs(got - ref[side]) / abs(ref[side]),
        }
    out["reussi"] = all(out[s]["ecart_relatif"] <= 1e-9 for s in ("YM", "YP"))
    return out


def check_links(pts: list[OutPoint], unit: dict[str, FloatArray]) -> dict[str, Any]:
    """Criterion 6: relative Y of the guided side and relative Z of every pin, zero."""
    rel = [i for i, p in enumerate(pts) if p.kind == "relatif"]
    guided = [i for i in rel if pts[i].side == "YP"]
    worst_y, worst_z = 0.0, 0.0
    for a in unit.values():
        scale = float(np.abs(a[:, :3]).max()) or 1.0
        worst_y = max(worst_y, float(np.abs(a[guided, 1]).max()) / scale)
        worst_z = max(worst_z, float(np.abs(a[rel, 2]).max()) / scale)
    return {
        "DY_relatif_YP_max_relatif": worst_y,
        "DZ_relatif_max_relatif": worst_z,
        "reussi": worst_y <= 1e-9 and worst_z <= 1e-9,
    }


def check_brute_force(
    vd: VariantData51ter,
    f: dict[str, FloatArray],
    qs: list[Quantity],
    pts: list[OutPoint],
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]],
) -> dict[str, Any]:
    """Criterion 5: 12 extremes drawn (seed 53) against the explicit enumeration of
    every branch of their state, and against their governing combination."""
    rng = random.Random(SEED)
    rows = []
    worst = 0.0
    for _ in range(12):
        state = rng.choice(STATES)
        variant, without = rng.choice(VARIANTS)
        k = rng.randrange(len(qs))
        sign = rng.choice((1.0, -1.0))
        excluded = {c for a in without for c in EXCLUDED_CASES[a]}
        values = {c: (0.0 if c in excluded else float(a[k])) for c, a in f.items()}
        found = [brute_force(b, vd.ev, values, sign) for b in vd.bs if b.state == state]
        best = max(found) if sign > 0 else min(found)
        mine = combos[(state, variant)][k][0 if sign > 0 else 1]
        q = qs[k]
        best_disp = best * q.scale()
        again = value_from(mine.coefficients, f, k) * q.scale()
        tol = max(1e-9 * abs(best_disp), 1e-12 * q.scale())
        err = max(abs(mine.value - best_disp), abs(again - mine.value))
        worst = max(worst, err / max(abs(best_disp), 1e-30))
        rows.append(
            {
                "etat": state,
                "variante": variant,
                "point": pts[q.point].name,
                "direction": COMPONENTS[q.component],
                "sens": "max" if sign > 0 else "min",
                "enveloppe": mine.value,
                "enumeration": best_disp,
                "combinaison_reevaluee": again,
                "reussi": err <= tol,
            }
        )
    return {
        "tirages": rows,
        "ecart_relatif_max": worst,
        "reussi": all(r["reussi"] for r in rows),
    }


def hand_estimate(
    vd: VariantData51ter, pts: list[OutPoint], unit: dict[str, FloatArray]
) -> dict[str, Any]:
    """DY of the pile heads of the last pier under ACN at its zone (rive YM), against the
    hand estimate written before the run (`docs/essais_lot53.md`, § 1)."""
    pier = vd.g.footings[-1].pier
    case = f"ACN_PT{len(vd.g.footings)}_YM"
    f = next(ft for ft in vd.g.footings if ft.pier == pier)
    m = vd.model
    heads = [i for i, p in enumerate(pts) if p.kind == "tete" and p.place == pier]
    dy_model = float(np.mean([unit[case][i, 1] for i in heads]))
    head_z = float(m.coords[m.group_nodes[f"TP_{pier}_C1_YM_A"][0] - 1][2])
    foot_z = float(m.coords[m.group_nodes[f"PS_{pier}_C1_YM_A"][0] - 1][2])
    length = head_z - foot_z
    inertia = np.pi * vd.vals.pile_d**4 / 64.0
    k_piles = 4.0 * 12.0 * vd.vals.e_concrete * inertia / length**3
    lx = f.xs[-1] - f.xs[0]
    ly = f.ys[-1] - f.ys[0]
    ix = lx * ly**3 / 12.0
    lever = vd.g.levels["axe_appui"] - f.z
    height = head_z - f.z
    flex = {
        "piles": 1.0 / k_piles,
        "translation_semelle": 1.0 / (vd.vals.kt * f.area),
        "balancement_semelle": lever * height / (vd.vals.kn * ix),
    }
    total = sum(flex.values())
    forces = soil_forces(vd, component=1)[pier][1][case]
    f_pier = -float(forces.sum())
    estimate = f_pier * total
    return {
        "cas": case,
        "palee": pier,
        "force_Y_reprise_N": f_pier,
        "force_appliquee_N": 1000.0,
        "souplesse_mm_par_kN": {k: v * 1e6 for k, v in flex.items()},
        "souplesse_totale_mm_par_kN": total * 1e6,
        "longueur_piles_m": length,
        "DY_tete_modele_mm": dy_model * MM,
        "DY_tete_estimation_mm": estimate * MM,
        "rapport_modele_estimation": dy_model / estimate if estimate else float("nan"),
    }


# --------------------------------------------------------------------------- fields


def nodal_field(vd: VariantData51ter, coefs: dict[str, float]) -> FloatArray:
    """DEPL of every node (nodes in order, 6 components, m and rad) of a combination."""
    n = vd.model.coords.shape[0]
    out = np.zeros((n, 6))
    for case, c in coefs.items():
        d = vd.tables.depl[case]
        out += c * np.array([d[k][:6] for k in range(1, n + 1)])
    return out


@dataclass
class FieldChoice:
    key: str
    title: str
    source: str
    """Event name or combination label."""
    coefficients: dict[str, float]
    governing: str
    """Quantity and value that chose it."""


def _abs_dy(qs: list[Quantity], pts: list[OutPoint], comp: int) -> list[int]:
    return [
        k for k, q in enumerate(qs) if q.component == comp and pts[q.point].absolute
    ]


def field_choices(
    pts: list[OutPoint],
    qs: list[Quantity],
    events: dict[str, Event],
    ev_values: dict[str, FloatArray],
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]],
) -> list[FieldChoice]:
    """The 6 events and 4 combinations of the MED (consigne § MED et vues)."""
    out: list[FieldChoice] = []
    abs_points = [i for i, p in enumerate(pts) if p.absolute]
    selectors: list[tuple[str, str, Callable[[Event], bool]]] = [
        ("EV_AC_DY", "AC le plus défavorable en |DY|", lambda e: e.action == "AC"),
        ("EV_ACA_DY", "ACA le plus défavorable en |DY|", lambda e: e.action == "ACA"),
        (
            "EV_AML_DY",
            "AML le plus défavorable en |DY|",
            lambda e: e.name.startswith("AML_"),
        ),
        ("EV_AMF_DY", "AMF le plus défavorable en |DY|", lambda e: e.action == "AMF"),
    ]
    for key, title, pick in selectors:
        names = [n for n, e in events.items() if pick(e)]
        scores = {n: float(np.abs(ev_values[n][abs_points, 1]).max()) for n in names}
        best = max(names, key=lambda n: scores[n])
        i = abs_points[int(np.argmax(np.abs(ev_values[best][abs_points, 1])))]
        out.append(
            FieldChoice(
                key,
                title,
                best,
                dict(events[best].coefficients),
                f"|DY| = {scores[best] * MM:.3f} mm en {pts[i].name}",
            )
        )
    for key, name in (("EV_AM1_PX", "AM1_+X"), ("EV_AM2_YP", "AM2_YP")):
        out.append(
            FieldChoice(
                key,
                name,
                name,
                dict(events[name].coefficients),
                "imposé par la consigne",
            )
        )
    for key, title, state, variant, comp in (
        (
            "CO_ELSC_DY",
            "max |DY| ELS caractéristique",
            "ELS_caracteristique",
            "total",
            1,
        ),
        (
            "CO_ELSC_DX_HT",
            "max |DX| ELS caractéristique hors thermique",
            "ELS_caracteristique",
            "total_hors_T",
            0,
        ),
        ("CO_ELSF_DY", "max |DY| ELS fréquent", "ELS_frequent", "total", 1),
        ("CO_ELUA_DY", "max |DY| ELU accidentel", "ELU_accidentel", "total", 1),
    ):
        ks = _abs_dy(qs, pts, comp)
        rows = combos[(state, variant)]
        best_k, best_c = ks[0], rows[ks[0]][0]
        for k in ks:
            for c in rows[k]:
                if abs(c.value) > abs(best_c.value):
                    best_k, best_c = k, c
        out.append(
            FieldChoice(
                key,
                title,
                best_c.label,
                dict(best_c.coefficients),
                f"{COMPONENTS[comp]} = {best_c.value:.3f} mm en {pts[qs[best_k].point].name}",
            )
        )
    return out


# --------------------------------------------------------------------------- files


def source_line(vd: VariantData51ter, state: dict[str, Any]) -> str:
    s = state[CODE]
    run = Path(s["execution"]["execution_dir"]).name
    return (
        f"PONTONS-ALU-01, lot 53 (déplacements sous accostage et amarrage, post-traitement de la variante "
        f"{CODE} du lot 52 : {vd.variant.description}) : relecture des tables de l'exécution {run}, "
        f".comm sha256 {sha256(vd.comm)}, maillage sha256 {s['maillage']['med_sha256']} ; aucune nouvelle "
        "exécution."
    )


POINT_NOTE = (
    "Points : <axe>_axe = point de l'axe d'appui porté par l'oreille 1 (tablier) ; <axe>_chevetre = nœud du "
    "chevêtre sous l'axe ; <axe>_relatif = tablier − chevêtre au point de l'axe (Y : jeu, nul par liaison côté "
    "YP guidé ; X : glissement) ; Tk_mi_<rive> = poutre principale à mi-travée ; PF_bout_<rive> = bout du "
    "porte-à-faux ; <palée><chevêtre>_<rive>_tete = tête de pile (+0,69) ; <palée>_semelle_centre = centre de "
    "la semelle (moyenne des deux nœuds de Y = 0 à égale distance) ; CULEE_<rive> = appui de la culée. Repère "
    "global : X le long du ponton depuis la culée, Y transversal, Z vers le haut."
)


def point_columns(p: OutPoint) -> list[Any]:
    return [p.name, p.kind, p.place, p.side, p.x, p.y, p.z]


POINT_HEADER = ["point", "type", "palee_ou_travee", "rive", "x", "y", "z"]


def unit_rows(
    pts: list[OutPoint], unit: dict[str, FloatArray], cases: list[str]
) -> list[list[Any]]:
    rows = []
    for c in cases:
        for i, p in enumerate(pts):
            u = unit[c][i]
            rows.append(
                [
                    *point_columns(p),
                    c,
                    *(float(x) * MM for x in u[:3]),
                    *(float(x) * MRAD for x in u[3:]),
                ]
            )
    return rows


def write_exports(
    out: Path,
    src: str,
    pts: list[OutPoint],
    qs: list[Quantity],
    unit: dict[str, FloatArray],
    cases: list[str],
    ev_ext: list[dict[str, EventExtreme]],
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]],
    synthesis: list[list[Any]],
    relabel: dict[str, str] | None = None,
) -> dict[str, int]:
    """The four CSV of the lot; `relabel` replaces words of the headers (lot 54: its
    own rules and events)."""
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, int] = {}

    def write(path: Path, header: str, columns: list[str], rows: Any) -> int:
        for old, new in (relabel or {}).items():
            header = header.replace(old, new)
        return write_csv(path, header, columns, rows)

    files["deplacements_unitaires.csv"] = write(
        out / "deplacements_unitaires.csv",
        f"{src} Déplacements des points de sortie sous les cas unitaires d'accostage (ACN, ACX, ACZ : "
        "1 kN/m sur 1 m), d'amarrage (AMY, AMX : 1 kN) et thermiques (TP, TM, en référence). ACA et AMF n'ont pas "
        "de cas unitaires propres : ce sont les mêmes cas avec d'autres coefficients (evenements.csv du lot 52). "
        f"Unités : mm (DX, DY, DZ), mrad (DRX, DRY, DRZ). {POINT_NOTE}",
        [
            *POINT_HEADER,
            "cas",
            "DX_mm",
            "DY_mm",
            "DZ_mm",
            "DRX_mrad",
            "DRY_mrad",
            "DRZ_mrad",
        ],
        unit_rows(pts, unit, cases),
    )
    rows = []
    for k, q in enumerate(qs):
        for fam, e in ev_ext[k].items():
            rows.append(
                [
                    *point_columns(pts[q.point]),
                    COMPONENTS[q.component],
                    unit_label(q),
                    fam,
                    e.max_value,
                    e.max_event,
                    e.min_value,
                    e.min_event,
                ]
            )
    files["deplacements_evenements.csv"] = write(
        out / "deplacements_evenements.csv",
        f"{src} Extrêmes positif et négatif, sur les événements de chaque famille, à la valeur caractéristique "
        "(coefficients d'evenements.csv du lot 52, sans facteur partiel ni ψ) : AC (accostage caractéristique, "
        "ACN avec ACX ou ACZ, 168), ACA (accostage accidentel, 168), AM (AML local 60, AM1 2, AM2 2), AMF "
        "(amarrage accidentel, 60) ; « toutes » : les quatre familles ensemble. Unités : mm, mrad (DRX, DRY des "
        f"têtes et des semelles). {POINT_NOTE}",
        [
            *POINT_HEADER,
            "direction",
            "unite",
            "famille",
            "max",
            "evenement_max",
            "min",
            "evenement_min",
        ],
        rows,
    )
    rows = []
    for k, q in enumerate(qs):
        for state in STATES:
            cells: list[Any] = []
            for variant, _ in VARIANTS:
                hi, lo = combos[(state, variant)][k]
                cells += [hi.value, hi.label, lo.value, lo.label]
            rows.append(
                [
                    *point_columns(pts[q.point]),
                    COMPONENTS[q.component],
                    unit_label(q),
                    state,
                    *cells,
                ]
            )
    files["deplacements_combinaisons.csv"] = write(
        out / "deplacements_combinaisons.csv",
        f"{src} Extrêmes des combinaisons du lot 52 (règles de combinaisons.csv : branches, emplacements, "
        "dispositions défavorables de Q et QD par modules ; P49, P57, P59, P60, P61) à l'ELS caractéristique, à "
        "l'ELS fréquent et à l'ELU accidentel, avec la combinaison gouvernante. Quatre variantes : total ; "
        "total_hors_T (TP, TM mis à zéro) ; variables_avec_T (actions variables seules, sans G ni DEJ, T "
        "inclus) ; variables_sans_T (sans G, DEJ, ni T). Une action exclue est mise à zéro dans toutes les "
        "branches (option ∅ de son emplacement ; dominante, la combinaison se réduit aux accompagnements) ; le "
        "libellé omet les événements exclus. Unités : mm, mrad. "
        f"{POINT_NOTE}",
        [
            *POINT_HEADER,
            "direction",
            "unite",
            "etat_limite",
            *(
                f"{v}_{s}"
                for v, _ in VARIANTS
                for s in ("max", "combinaison_max", "min", "combinaison_min")
            ),
        ],
        rows,
    )
    files["deplacements_synthese.csv"] = write(
        out / "deplacements_synthese.csv",
        f"{src} Une ligne par palée, valeurs totales (G, DEJ compris), extrême en valeur absolue rendu signé, mm. "
        "DY tête : têtes des 4 piles (+0,69). DY tablier : point de l'axe porté par le tablier, 4 axes de la "
        "palée. Jeu Y relatif : tablier − chevêtre au point de l'axe, côté YM (Y libre ; côté YP guidé, nul par "
        "liaison, dernière colonne en contrôle). DX axe hors T : point de l'axe porté par le tablier, TP et TM "
        "exclus. DZ axe : point de l'axe porté par le tablier. ELS c = ELS caractéristique, ELU acc = ELU "
        "accidentel.",
        SYNTHESIS_COLUMNS,
        synthesis,
    )
    return files


SYNTHESIS_COLUMNS = [
    "palee",
    "DY_tete_max_ELS_c",
    "DY_tete_max_ELU_acc",
    "DY_tablier_max_ELS_c",
    "DY_tablier_max_ELU_acc",
    "jeu_Y_relatif_YM_max_ELS_c",
    "jeu_Y_relatif_YM_max_ELU_acc",
    "DX_axe_max_hors_T_ELS_c",
    "DX_axe_max_hors_T_ELU_acc",
    "DZ_axe_min_ELS_c",
    "DZ_axe_max_ELS_c",
    "DZ_axe_min_ELU_acc",
    "DZ_axe_max_ELU_acc",
    "jeu_Y_relatif_YP_max_controle",
]


def synthesis_rows(
    vd: VariantData51ter,
    pts: list[OutPoint],
    qs: list[Quantity],
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]],
) -> list[list[Any]]:
    index = {(q.point, q.component): k for k, q in enumerate(qs)}

    def pick(
        pier: str,
        kind: str,
        comp: int,
        state: str,
        variant: str,
        mode: str,
        side: str = "",
    ) -> float:
        ks = [
            index[(i, comp)]
            for i, p in enumerate(pts)
            if p.place == pier and p.kind == kind and (not side or p.side == side)
        ]
        vals = [c.value for k in ks for c in combos[(state, variant)][k]]
        if mode == "min":
            return min(vals)
        if mode == "max":
            return max(vals)
        return max(vals, key=abs)

    rows = []
    c, a = "ELS_caracteristique", "ELU_accidentel"
    for f in vd.g.footings:
        p = f.pier
        rows.append(
            [
                p,
                pick(p, "tete", 1, c, "total", "abs"),
                pick(p, "tete", 1, a, "total", "abs"),
                pick(p, "axe", 1, c, "total", "abs"),
                pick(p, "axe", 1, a, "total", "abs"),
                pick(p, "relatif", 1, c, "total", "abs", "YM"),
                pick(p, "relatif", 1, a, "total", "abs", "YM"),
                pick(p, "axe", 0, c, "total_hors_T", "abs"),
                pick(p, "axe", 0, a, "total_hors_T", "abs"),
                pick(p, "axe", 2, c, "total", "min"),
                pick(p, "axe", 2, c, "total", "max"),
                pick(p, "axe", 2, a, "total", "min"),
                pick(p, "axe", 2, a, "total", "max"),
                max(
                    abs(pick(p, "relatif", 1, s, "total", "abs", "YP")) for s in STATES
                ),
            ]
        )
    return rows


def largest(
    pts: list[OutPoint],
    qs: list[Quantity],
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]],
    ev_ext: list[dict[str, EventExtreme]],
    comp: int,
) -> dict[str, list[dict[str, Any]]]:
    """The 3 largest |value| of a direction over the absolute points: combinations
    (totals, three states; one entry per point) and events (characteristic)."""
    found: list[tuple[float, str, str, str]] = []
    for k, q in enumerate(qs):
        if q.component != comp or not pts[q.point].absolute:
            continue
        best = max(
            ((c.value, s, c.label) for s in STATES for c in combos[(s, "total")][k]),
            key=lambda t: abs(t[0]),
        )
        found.append((best[0], pts[q.point].name, best[1], best[2]))
    ev: list[tuple[float, str, str, str]] = []
    for k, q in enumerate(qs):
        if q.component != comp or not pts[q.point].absolute:
            continue
        e = ev_ext[k]["toutes"]
        v, n = (
            (e.max_value, e.max_event)
            if abs(e.max_value) >= abs(e.min_value)
            else (e.min_value, e.min_event)
        )
        ev.append((v, pts[q.point].name, "caractéristique", n))
    out = {}
    for key, items in (("combinaisons", found), ("evenements", ev)):
        items.sort(key=lambda t: -abs(t[0]))
        out[key] = [
            {"valeur_mm": v, "point": p, "etat": s, "combinaison_ou_evenement": lab}
            for v, p, s, lab in items[:3]
        ]
    return out


# --------------------------------------------------------------------------- step


@dataclass
class Lot53:
    vd: VariantData51ter
    pts: list[OutPoint]
    qs: list[Quantity]
    unit: dict[str, FloatArray]
    f: dict[str, FloatArray]
    events: dict[str, Event]
    ev_values: dict[str, FloatArray]
    ev_ext: list[dict[str, EventExtreme]]
    combos: dict[tuple[str, str], list[tuple[Combined, Combined]]]
    timings: dict[str, float]


def compute(
    ctx: ProjectContext,
    state: dict[str, Any],
    vd: VariantData51ter | None = None,
) -> Lot53:
    """Points, unit values, events and envelopes of B52 of lot 52 (lot 54: of the
    variant `vd`, already loaded with its own events and rules)."""
    t0 = time.perf_counter()
    vd = vd if vd is not None else load(ctx, CODE, state).vd
    t1 = time.perf_counter()
    pts = output_points(vd)
    qs = quantities(pts)
    unit = unit_values(vd, pts)
    f = quantity_arrays(unit, qs)
    events = lot_events(vd)
    ev_values = {n: event_value(e, unit) for n, e in events.items()}
    ev_ext = event_extremes(events, ev_values, qs)
    t2 = time.perf_counter()
    combos = combined_extremes(vd, f, qs)
    t3 = time.perf_counter()
    return Lot53(
        vd,
        pts,
        qs,
        unit,
        f,
        events,
        ev_values,
        ev_ext,
        combos,
        {
            "lecture_tables": t1 - t0,
            "points_evenements": t2 - t1,
            "enveloppes": t3 - t2,
        },
    )


def step_exports(ctx: ProjectContext, state: dict[str, Any]) -> dict[str, Any]:
    r = compute(ctx, state)
    out = ctx.results_dir / LOT / "exports" / CODE
    synthesis = synthesis_rows(r.vd, r.pts, r.qs, r.combos)
    cases = exported_cases(r.vd)
    files = write_exports(
        out,
        source_line(r.vd, state),
        r.pts,
        r.qs,
        r.unit,
        cases,
        r.ev_ext,
        r.combos,
        synthesis,
    )
    choices = field_choices(r.pts, r.qs, r.events, r.ev_values, r.combos)
    summary: dict[str, Any] = {
        "fichiers": files,
        "points": len(r.pts),
        "grandeurs": len(r.qs),
        "cas_unitaires_exportes": len(cases),
        "evenements": {
            fam: sum(1 for e in r.events.values() if e.action == fam)
            for fam in FAMILIES
        },
        "branches": {s: sum(1 for b in r.vd.bs if b.state == s) for s in STATES},
        "temps_s": r.timings,
        "plus_grands_DY": largest(r.pts, r.qs, r.combos, r.ev_ext, 1),
        "plus_grands_DX": largest(r.pts, r.qs, r.combos, r.ev_ext, 0),
        "champs_med": [c.__dict__ for c in choices],
        "controle_empreintes": check_fingerprints(ctx, state),
        "controle_relecture": check_reread(ctx, r.vd),
        "controle_TP_P5": check_tp(ctx, r.vd),
        "controle_liaisons": check_links(r.pts, r.unit),
        "controle_enumeration": check_brute_force(r.vd, r.f, r.qs, r.pts, r.combos),
        "ordre_de_grandeur_P5": hand_estimate(r.vd, r.pts, r.unit),
    }
    fields = {c.key: nodal_field(r.vd, c.coefficients) for c in choices}
    summary["controle_champs_points"] = check_fields_at_points(r, choices, fields)
    work = ctx.results_dir / LOT / CODE / "med_travail"
    work.mkdir(parents=True, exist_ok=True)
    np.savez(work / "champs.npz", **fields)  # type: ignore[arg-type]
    (ctx.results_dir / LOT / "exports" / "synthese.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", "utf-8"
    )
    return summary


def check_fields_at_points(
    r: Lot53, choices: list[FieldChoice], fields: dict[str, FloatArray]
) -> dict[str, Any]:
    """Criterion 7 (part): at the nodal output points, the field of each choice against
    its value computed from the points (events: event_value; combinations: the value of
    `deplacements_combinaisons.csv` of the quantity that chose it)."""
    worst = 0.0
    for c in choices:
        field = fields[c.key]
        biggest = float(np.abs(field[:, :3]).max())
        for i, p in enumerate(r.pts):
            if p.node is None:
                continue
            ref = sum(coef * r.unit[case][i] for case, coef in c.coefficients.items())
            worst = max(worst, float(np.abs(field[p.node - 1] - ref).max()) / biggest)
    return {"ecart_relatif_max": worst, "reussi": worst <= 1e-9}


__all__ = [
    "CODE",
    "LOT",
    "OutPoint",
    "Term",
    "compute",
    "event_value",
    "footing_centre_terms",
    "output_points",
    "point_value",
    "step_exports",
]
