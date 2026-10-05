"""Comparison v2 of the jetty (lot 47 bis): reading rules of E17, combination 100 with
the TR case of E18, as written in docs/essais_lot47bis.md § 1 before the readings.

The v1 module (`comparaison.py`, docs/essais_lot47.md § 2.3 to 2.5) is kept as it is:
its verdicts stay in the history. Here:

- every ELU value names the family that governs it (ELU+ or ELU-) and the position
  of the moving load (E17.1);
- piles: C3 from the head (+1.30) down to -0.80, head element included; C5 on the
  whole pile (E17.1);
- cap beams: total of the bar and of the slab band |X - X_file| <= 0.60 at the same Y,
  s·MFY - ∫MYY dX and VZ + ∫QY dX (trapezoids on the slab nodes), the bar alone for
  information (E17.2);
- slab: C9, C12, C13 outside the closed discs of radius 0.60 m centred on the 14 pile
  heads (E17.3); C11: mean of NXX over each cross-section X = const (E17.4);
- combination 100: TR = 5 kPa on the two sidewalks + the sidewalk axle of E18,
  enveloped over its positions (TRE_k), wherever the combination 100 is read.

Contre-calcul d'un modèle non validé: never a level E; nothing is tuned toward the
source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from estacade_pieux_01.combinaisons import Combination, find
from estacade_pieux_01.comparaison import (
    CASE_OF,
    LEVEL,
    SOURCE,
    TOLERANCE,
    Comparison,
    Extractor,
    Scalar,
    _col,
    _gap,
    _norm,
    _signed,
)
from estacade_pieux_01.donnees import ModelValues
from estacade_pieux_01.lecture import FloatArray, IntArray, Results, bcomp, comp

RADIUS = 0.60
"""E17.3: radius of the discs excluded around the pile heads (m)."""
BAND = 0.60
"""E17.2: half-width of the slab band of a cap beam (m)."""
CRITERIA = "docs/essais_lot47bis.md § 1 (E17, E18), écrits avant la relecture"
FAMILIES_ELU = ("ELU+", "ELU-")


def merge(base: Results, extra: Results) -> Results:
    """The cases of `extra` (another run on the same mesh) added to `base`."""
    for name in ("slab_nodes", "beam_cells", "beam_nodes"):
        if not np.array_equal(getattr(base, name), getattr(extra, name)):
            message = f"résultats sur des maillages différents ({name})"
            raise ValueError(message)
    if not np.allclose(base.coords, extra.coords, atol=0.0, rtol=0.0):
        message = "résultats sur des maillages différents (coordonnées)"
        raise ValueError(message)
    for kind in ("slab", "depl", "beams"):
        target = getattr(base, kind)
        for case, values in getattr(extra, kind).items():
            if case in target:
                message = f"cas {case} présent dans les deux exécutions"
                raise ValueError(message)
            target[case] = values
    return base


@dataclass
class Env:
    """Envelope of one column at every point, with the governing family and case."""

    maximum: FloatArray
    minimum: FloatArray
    arg_max: list[str]
    arg_min: list[str]
    fam_max: list[str]
    fam_min: list[str]


class CombinerV2:
    """Combinations of B5 with the TR case of E18 in the combination 100."""

    def __init__(self, cmp: Comparison, tr_axle: list[str]) -> None:
        self.base = cmp.comb
        self.tr_axle = tr_axle

    def combine(self, c: Combination, ex: Extractor, scalar: Scalar) -> Env:
        if c.number == 100 and self.tr_axle:
            coef = c.coefficients["TR"]
            fixed = c.gamma_g * (ex("PP") + ex("G2")) + coef * ex(CASE_OF["TR"])
            stack = np.stack([scalar(fixed + coef * ex(n)) for n in self.tr_axle])
            imax = np.argmax(stack, axis=0)
            imin = np.argmin(stack, axis=0)
            fam = [c.family] * stack.shape[1]
            return Env(
                np.max(stack, axis=0),
                np.min(stack, axis=0),
                [self.tr_axle[i] for i in imax],
                [self.tr_axle[i] for i in imin],
                fam,
                list(fam),
            )
        e = self.base.combine(c, ex, scalar)
        fam = [c.family] * len(e.maximum)
        return Env(e.maximum, e.minimum, e.arg_max, e.arg_min, fam, list(fam))

    def column(self, number: int, column: str, ex: Extractor, scalar: Scalar) -> Env:
        if column != "ELU":
            return self.combine(find(number, column), ex, scalar)
        a = self.combine(find(number, "ELU+"), ex, scalar)
        b = self.combine(find(number, "ELU-"), ex, scalar)
        ta = a.maximum >= b.maximum
        tb = a.minimum <= b.minimum
        return Env(
            np.where(ta, a.maximum, b.maximum),
            np.where(tb, a.minimum, b.minimum),
            [x if t else y for x, y, t in zip(a.arg_max, b.arg_max, ta, strict=True)],
            [x if t else y for x, y, t in zip(a.arg_min, b.arg_min, tb, strict=True)],
            [x if t else y for x, y, t in zip(a.fam_max, b.fam_max, ta, strict=True)],
            [x if t else y for x, y, t in zip(a.fam_min, b.fam_min, tb, strict=True)],
        )


def _row(
    point: str,
    label: str,
    value: float,
    source: float | None,
    tolerance: float | None,
    rule: str,
    where: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    gap = _gap(value, source) if source is not None else float("nan")
    if tolerance is None or source is None:
        verdict = "—"
    else:
        verdict = "dans la tolérance" if abs(gap) <= tolerance else "hors tolérance"
    return {
        "point": point,
        "colonne": label,
        "code_aster": value,
        "source": source,
        "ecart_relatif": gap,
        "tolerance": tolerance,
        "verdict": verdict,
        "regle": rule,
        "lieu": where,
        "note": note,
    }


class ComparisonV2:
    def __init__(
        self,
        v: ModelValues,
        results: Results,
        positions: dict[str, Any],
        tr_axle: list[str],
    ) -> None:
        self.c1 = Comparison(v, results, positions)
        self.v = v
        self.r = results
        self.comb = CombinerV2(self.c1, tr_axle)
        self.x, self.y = self.c1.x, self.c1.y
        self.away = self._away()
        self._band = self._band_weights()

    # -- geometry ----------------------------------------------------------------
    def _away(self) -> np.ndarray[Any, Any]:
        near = np.zeros(len(self.x), dtype=bool)
        for p in self.v.piles():
            near |= np.hypot(self.x - p.x, self.y - p.y) <= RADIUS + 1e-9
        out: np.ndarray[Any, Any] = ~near
        return out

    def _band_weights(self) -> tuple[IntArray, FloatArray]:
        """(indices, trapezoid weights) of the slab band of each cap row."""
        rows = self.c1.cap_rows
        xyz = self.c1.beam_xyz[rows]
        idx_rows = []
        w_rows = []
        for xb, yb in xyz[:, :2]:
            sel = np.nonzero(
                (np.abs(self.y - yb) < 1e-6) & (np.abs(self.x - xb) <= BAND + 1e-9)
            )[0]
            order = sel[np.argsort(self.x[sel])]
            xs = self.x[order]
            w = np.zeros(len(xs))
            dx = np.diff(xs)
            w[:-1] += dx / 2.0
            w[1:] += dx / 2.0
            idx_rows.append(order)
            w_rows.append(w)
        sizes = {len(i) for i in idx_rows}
        if len(sizes) != 1:
            message = f"bandes de dalle de tailles différentes : {sorted(sizes)}"
            raise ValueError(message)
        return np.array(idx_rows, dtype=np.int64), np.array(w_rows)

    def band_integral(self, case: str, component: str) -> FloatArray:
        idx, w = self._band
        out: FloatArray = np.sum(self.r.slab[case][idx, comp(component)] * w, axis=1)
        return out

    def _where_beam(self, row: int) -> dict[str, Any]:
        p = self.c1.beam_xyz[row]
        return {"X": float(p[0]), "Y": float(p[1]), "Z": float(p[2])}

    def _where_slab(self, i: int) -> dict[str, Any]:
        return {"X": float(self.x[i]), "Y": float(self.y[i])}

    # -- cap beam extractors (rows of cap_rows, in that order) --------------------
    def cap_ex(self, quantity: str, *, total: bool) -> Extractor:
        signs = self.c1.cap_sign[:, None]
        rows = self.c1.cap_rows

        def ex(case: str) -> FloatArray:
            if quantity == "M":
                bar = signs * self.r.beams[case][rows][:, [bcomp("MFY")]]
                if not total:
                    return bar
                out: FloatArray = bar - self.band_integral(case, "MYY")[:, None]
                return out
            vz = self.r.beams[case][rows][:, [bcomp("VZ")]]
            if not total:
                return vz
            total_v: FloatArray = vz + self.band_integral(case, "QY")[:, None]
            return total_v

        return ex

    # -- points ------------------------------------------------------------------
    def _value_row(
        self,
        point: str,
        label: str,
        env: Env,
        i: int,
        source: float | None,
        tolerance: float | None,
        rule: str,
        where: dict[str, Any],
        *,
        use_min: bool = False,
        factor: float = 1e-3,
        note: str = "",
    ) -> dict[str, Any]:
        value = float(env.minimum[i] if use_min else env.maximum[i]) * factor
        case = env.arg_min[i] if use_min else env.arg_max[i]
        family = env.fam_min[i] if use_min else env.fam_max[i]
        return _row(
            point,
            label,
            value,
            source,
            tolerance,
            rule,
            {**where, "cas_mobile": case, "famille": family},
            note,
        )

    def c1_c2(self) -> list[dict[str, Any]]:
        out = []
        env = self.comb.column(107, "ELS_c", lambda c: self.r.depl[c], _norm)
        i = int(np.nanargmax(env.maximum))
        xyz = self.r.coords[i]
        row = self._value_row(
            "C1",
            "ELS c (107)",
            env,
            i,
            0.5,
            None,
            "max √(DX²+DY²+DZ²), tous les nœuds (inchangé)",
            {"X": float(xyz[0]), "Y": float(xyz[1]), "Z": float(xyz[2])},
            factor=100.0,
        )
        row["verdict"] = (
            "compatible avec l'arrondi"
            if 0.25 <= row["code_aster"] < 0.75
            else "non compatible avec l'arrondi"
        )
        out.append(row)
        top = np.array(
            [
                abs(self.c1.beam_xyz[r, 2] - self.v.z_mid) < LEVEL
                for r in self.c1.pile_rows
            ]
        )
        rows = self.c1.pile_rows[top]
        ex = self.c1.beam_ex(rows, ("N",))
        for column in ("ELS_f", "ELS_c", "ELU"):
            env = self.comb.column(112, column, ex, lambda a: -_col(a))
            i = int(np.argmax(env.maximum))
            out.append(
                self._value_row(
                    "C2",
                    f"{column} (112)",
                    env,
                    i,
                    SOURCE["C2"][column],
                    TOLERANCE["C2"],
                    "max(−N), extrémité haute de l'élément de tête (inchangé)",
                    self._where_beam(int(rows[i])),
                )
            )
        return out

    def pile_rows_between(self, low: float, high: float) -> IntArray:
        """Rows of the pile elements whose two nodes lie in [low, high]."""
        rows = self.c1.pile_rows
        z = self.c1.beam_xyz[:, 2]
        cell_low = np.minimum(z[0::2], z[1::2])
        cell_high = np.maximum(z[0::2], z[1::2])
        lo = np.repeat(cell_low, 2)[rows]
        hi = np.repeat(cell_high, 2)[rows]
        sel: IntArray = rows[(lo >= low - LEVEL) & (hi <= high + LEVEL)]
        return sel

    def _bar(
        self,
        point: str,
        rows: IntArray,
        names: tuple[str, str],
        number: int,
        columns: tuple[str, ...],
        rule: str,
        source_key: str,
    ) -> list[dict[str, Any]]:
        ex = self.c1.beam_ex(rows, names)
        out = []
        for column in columns:
            env = self.comb.column(number, column, ex, _norm)
            i = int(np.argmax(env.maximum))
            published = SOURCE[source_key].get(column)
            if isinstance(published, tuple):
                src: float | None = float(max(abs(published[0]), abs(published[1])))
            elif published is None:
                src = None
            else:
                src = float(abs(published))
            out.append(
                self._value_row(
                    point,
                    f"{column} ({number})"
                    + ("" if src is not None else ", information"),
                    env,
                    i,
                    src,
                    TOLERANCE[point] if src is not None else None,
                    rule,
                    self._where_beam(int(rows[i])),
                )
            )
        return out

    def piles(self) -> list[dict[str, Any]]:
        top, bottom = self.v.plug
        head_zone = self.pile_rows_between(bottom, self.v.z_mid)
        plug = self.c1._pile_zone(bottom, top)
        whole = self.c1.pile_rows
        cols = ("ELS_f", "ELS_c", "ELU")
        return [
            *self._bar(
                "C3",
                head_zone,
                ("MFY", "MFZ"),
                111,
                cols,
                "max √(MFY²+MFZ²), éléments entre +1,30 et −0,80 (E17.1)",
                "C3",
            ),
            *self._bar(
                "C4",
                plug,
                ("VY", "VZ"),
                114,
                cols,
                "max √(VY²+VZ²), bouchon −0,80 à +0,70 (inchangé)",
                "C4",
            ),
            *self._bar(
                "C5",
                whole,
                ("MFY", "MFZ"),
                111,
                cols,
                "max √(MFY²+MFZ²), tout le pieu (E17.1)",
                "C5",
            ),
        ]

    def caps(self) -> list[dict[str, Any]]:
        rows = self.c1.cap_rows
        y = self.c1.beam_xyz[rows, 1]
        span = np.nonzero(np.abs(y) < self.v.y_piles - LEVEL)[0]
        support = np.nonzero(np.abs(np.abs(y) - self.v.y_piles) < LEVEL)[0]
        off_support = np.nonzero(np.abs(np.abs(y) - self.v.y_piles) >= LEVEL)[0]
        out: list[dict[str, Any]] = []
        for total in (True, False):
            tag = "total barre + dalle" if total else "barre seule, information"
            exm = self.cap_ex("M", total=total)
            exv = self.cap_ex("V", total=total)

            def sub(ex: Extractor, sel: np.ndarray[Any, Any]) -> Extractor:
                def inner(case: str) -> FloatArray:
                    out_: FloatArray = ex(case)[sel]
                    return out_

                return inner

            for column, number in (("ELS_f", 105), ("ELS_c", 105), ("ELU", 112)):
                env = self.comb.column(number, column, sub(exm, span), _col)
                i = int(np.argmax(env.maximum))
                out.append(
                    self._value_row(
                        "C6",
                        f"{column} ({number}), {tag}",
                        env,
                        i,
                        SOURCE["C6"][column],
                        TOLERANCE["C6"] if total else None,
                        "max M_T = s·MFY − ∫MYY dX, |Y| < 2,00 (E17.2)"
                        if total
                        else "max s·MFY, |Y| < 2,00",
                        self._where_beam(int(rows[span[i]])),
                    )
                )
            for column in ("ELU", "ELS_f", "ELS_c"):
                best: tuple[float, Env, int, int] | None = None
                for number in range(100, 116):
                    env = self.comb.column(number, column, sub(exm, support), _col)
                    i = int(np.argmin(env.minimum))
                    if best is None or env.minimum[i] < best[0]:
                        best = (float(env.minimum[i]), env, i, number)
                assert best is not None
                _, env, i, number = best
                verdict = total and column == "ELU"
                row = self._value_row(
                    "C7",
                    f"{column} (enveloppe 100-115, gouvernée par {number}), {tag}"
                    + ("" if verdict or not total else ", information"),
                    env,
                    i,
                    177.0,
                    TOLERANCE["C7"] if verdict else None,
                    "min M_T aux nœuds Y = ±2,00, comparé en module (E17.2)"
                    if total
                    else "min s·MFY aux nœuds Y = ±2,00, comparé en module",
                    {**self._where_beam(int(rows[support[i]])), "combinaison": number},
                    use_min=True,
                )
                row["moment_signe_kNm"] = row["code_aster"]
                row["code_aster"] = abs(row["code_aster"])
                row["ecart_relatif"] = _gap(row["code_aster"], 177.0)
                if row["tolerance"] is not None:
                    row["verdict"] = (
                        "dans la tolérance"
                        if abs(row["ecart_relatif"]) <= row["tolerance"]
                        else "hors tolérance"
                    )
                out.append(row)
            for column in ("ELU", "ELS_f", "ELS_c"):
                for label, sel in (
                    ("toutes lignes", None),
                    ("hors Y = ±2,00", off_support),
                ):
                    ex = exv if sel is None else sub(exv, sel)
                    envs = [
                        self.comb.column(n, column, ex, lambda a: np.abs(_col(a)))
                        for n in (105, 112)
                    ]
                    k = int(np.argmax([float(np.max(e.maximum)) for e in envs]))
                    env = envs[k]
                    i = int(np.argmax(env.maximum))
                    judged = total and column == "ELU" and sel is None
                    picked = rows[i] if sel is None else rows[sel[i]]
                    out.append(
                        self._value_row(
                            "C8",
                            f"{column} (105, 112 ; gouvernée par {(105, 112)[k]}), "
                            f"{tag}, {label}" + ("" if judged else ", information"),
                            env,
                            i,
                            653.0,
                            TOLERANCE["C8"] if judged else None,
                            "max |V_T| = |VZ + ∫QY dX| (E17.2)"
                            if total
                            else "max |VZ|",
                            self._where_beam(int(picked)),
                        )
                    )
        return out

    def slab(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        chapeau = self.c1._chapeau_mask()
        for point, mask, number, sign, rule in (
            (
                "C9",
                chapeau & self.away,
                111,
                1.0,
                "max MXX, |X − X_i| ≤ 0,60, hors disques (E17.3)",
            ),
            ("C10", ~chapeau, 112, -1.0, "max(−MXX), |X − X_i| > 0,60 (inchangé)"),
        ):
            idx = np.nonzero(mask)[0]
            ex = self.c1.slab_ex("MXX", mask)
            for column in ("ELS_f", "ELS_c", "ELU"):
                env = self.comb.column(number, column, ex, _signed(sign))
                i = int(np.argmax(env.maximum))
                out.append(
                    self._value_row(
                        point,
                        f"{column} ({number})",
                        env,
                        i,
                        SOURCE[point][column],
                        TOLERANCE[point],
                        rule,
                        self._where_slab(int(idx[i])),
                    )
                )
        out += self.c11()
        lane = np.abs(self.y) <= self.v.lane[1] + LEVEL
        for label, mask, number, judged in (
            ("courant", lane & self.away, 111, True),
            ("rive", ~lane & self.away, 100, True),
            ("rive, dans les disques compris, information", ~lane, 100, False),
        ):
            idx = np.nonzero(mask)[0]
            env = self.comb.column(
                number, "ELU", self.c1.slab_ex("QX", mask), lambda a: np.abs(_col(a))
            )
            i = int(np.argmax(env.maximum))
            src = SOURCE["C12"]["courant" if label == "courant" else "rive"]
            out.append(
                self._value_row(
                    "C12",
                    f"ELU {label} ({number})",
                    env,
                    i,
                    src,
                    TOLERANCE["C12"] if judged else None,
                    "max |QX|, hors disques (E17.3)"
                    + (" ; TR d'E18" if number == 100 else ""),
                    self._where_slab(int(idx[i])),
                )
            )
        # Information : combinaison 100 avec TR = 5 kPa seul (charge de v1).
        mask = ~lane & self.away
        idx = np.nonzero(mask)[0]
        e1 = self.c1.comb.column(
            100, "ELU", self.c1.slab_ex("QX", mask), lambda a: np.abs(_col(a))
        )
        i = int(np.argmax(e1.maximum))
        out.append(
            _row(
                "C12",
                "ELU rive (100), TR = 5 kPa seul (charge de v1), information",
                float(e1.maximum[i]) / 1e3,
                SOURCE["C12"]["rive"],
                None,
                "max |QX|, hors disques, sans l'essieu d'E18",
                self._where_slab(int(idx[i])),
            )
        )
        ts_all = self.c1.comb.ts["axe"] + self.c1.comb.ts["bord"]
        for model, names, base in (
            ("LM1", ts_all, ["UDL", "TR"]),
            ("LM2", self.c1.comb.lm2, []),
        ):
            idx = np.nonzero(self.away)[0]
            env13 = self.c1.comb.elementary(
                names, base, self.c1.slab_ex("MXX", self.away), lambda a: -_col(a)
            )
            envq = self.c1.comb.elementary(
                names,
                base,
                self.c1.slab_ex("QX", self.away),
                lambda a: np.abs(_col(a)),
            )
            src = SOURCE["C13"][model]
            for label, value, s, i, case in (
                (
                    "Mxx inf.",
                    float(np.max(env13.maximum)),
                    src[0],
                    int(np.argmax(env13.maximum)),
                    env13.arg_max,
                ),
                (
                    "Mxx sup.",
                    float(np.min(env13.minimum)),
                    src[1],
                    int(np.argmin(env13.minimum)),
                    env13.arg_min,
                ),
                (
                    "V (|Qxx|)",
                    float(np.max(envq.maximum)),
                    src[2],
                    int(np.argmax(envq.maximum)),
                    envq.arg_max,
                ),
            ):
                out.append(
                    _row(
                        "C13",
                        f"{model} {label}",
                        value / 1e3,
                        s,
                        TOLERANCE["C13"],
                        "enveloppe non pondérée, dalle hors disques (E17.3)",
                        {**self._where_slab(int(idx[i])), "cas_mobile": case[i]},
                    )
                )
        return out

    def section_means(self, case: str) -> tuple[FloatArray, FloatArray]:
        """(X of each node line, (1/B) ∫ NXX dY) of a case."""
        xs = np.unique(np.round(self.x, 6))
        nxx = self.r.slab[case][:, comp("NXX")]
        means = np.empty(len(xs))
        for j, x in enumerate(xs):
            sel = np.abs(self.x - x) < 1e-6
            order = np.argsort(self.y[sel])
            y, n = self.y[sel][order], nxx[sel][order]
            means[j] = float(np.trapezoid(n, y) / (y[-1] - y[0]))
        return xs, means

    def c11(self) -> list[dict[str, Any]]:
        out = []
        for label, case in (("FR", "FR"), ("TE-", "TEM")):
            xs, means = self.section_means(case)
            j = int(np.argmax(np.abs(means)))
            out.append(
                _row(
                    "C11",
                    f"{label} seul",
                    abs(float(means[j])) / 1e3,
                    SOURCE["C11"][label],
                    TOLERANCE["C11"],
                    "max sur X de |(1/6,00) ∫ NXX dY| (E17.4)",
                    {
                        "X": float(xs[j]),
                        "NXX_moyen_signe_kN_m": float(means[j]) / 1e3,
                        "lignes": len(xs),
                    },
                )
            )
        return out

    def all_points(self) -> list[dict[str, Any]]:
        return [*self.c1_c2(), *self.piles(), *self.caps(), *self.slab()]

    # -- control of the reading of the total (§ 1.5) ------------------------------
    def total_check(self) -> dict[str, Any]:
        """Free body Y < Y0 under PP: shear and moment of the full cut against its
        weight (docs/essais_lot47bis.md § 1.5)."""
        v = self.v
        rows = self.c1.cap_rows
        xyz = self.c1.beam_xyz[rows]
        unit = (
            v.gamma_concrete * v.thickness * v.length
            + len(v.x_files) * v.gamma_concrete * v.cap_width * v.cap_height
        )
        out: dict[str, Any] = {"critere": "écart relatif ≤ 2 %", "coupes": {}}
        for y0 in (-2.50, -2.25):
            on = np.abs(xyz[:, 1] - y0) < 1e-6
            beams = self.r.beams["PP"][rows[on]]
            vz = float(np.sum(beams[:, bcomp("VZ")])) / 2.0
            mfy = float(np.sum(self.c1.cap_sign[on] * beams[:, bcomp("MFY")])) / 2.0
            line = np.nonzero(np.abs(self.y - y0) < 1e-6)[0]
            line = line[np.argsort(self.x[line])]
            xs = self.x[line]
            slab = self.r.slab["PP"][line]
            qy = float(np.trapezoid(slab[:, comp("QY")], xs))
            myy = float(np.trapezoid(slab[:, comp("MYY")], xs))
            mxy_edges = float(slab[-1, comp("MXY")] - slab[0, comp("MXY")])
            arm = y0 + v.width / 2.0
            weight = unit * arm
            shear = vz + qy
            moment = mfy - myy
            moment_expected = -weight * arm / 2.0
            shear_gap = (abs(shear) - weight) / weight
            moment_gap = (moment - moment_expected) / abs(moment_expected)
            out["coupes"][f"Y0={y0:+.2f}"] = {
                "poids_W_N": weight,
                "somme_VZ_chevetres_N": vz,
                "integrale_QY_N": qy,
                "effort_total_N": shear,
                "signe_effort_total": "+" if shear > 0 else "−",
                "ecart_relatif_effort": shear_gap,
                "terme_de_bord_MXY_N": mxy_edges,
                "somme_sMFY_Nm": mfy,
                "integrale_MYY_Nm": myy,
                "moment_total_Nm": moment,
                "moment_attendu_Nm": moment_expected,
                "ecart_relatif_moment": moment_gap,
                "verdict": "RÉUSSI"
                if abs(shear_gap) <= 0.02 and abs(moment_gap) <= 0.02
                else "ÉCHEC",
            }
        out["verdict"] = (
            "RÉUSSI"
            if all(c["verdict"] == "RÉUSSI" for c in out["coupes"].values())
            else "ÉCHEC"
        )
        return out


ScalarFn = Callable[[FloatArray], FloatArray]

__all__ = ["BAND", "CRITERIA", "RADIUS", "CombinerV2", "ComparisonV2", "Env", "merge"]
