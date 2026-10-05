"""Comparison of the Code_Aster results with the published values of the source model
(table B6), as written in docs/essais_lot47.md § 2.3 to 2.5 before the run.

Contre-calcul d'un modèle non validé: the source values are not a reference, the
comparison is never a level E. Every quantity is read as the criteria say (zones,
signs, combinations, envelopes over the positions of TS); nothing here is tuned
toward the source.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from estacade_pieux_01.combinaisons import Combination, find
from estacade_pieux_01.donnees import ModelValues
from estacade_pieux_01.lecture import (
    FloatArray,
    IntArray,
    Results,
    bcomp,
    comp,
    slab_xy,
)

LEVEL = 1.0e-6

# B6, values of the source model (units of B6: kN, kN·m, kN·m/m, kN/m, cm).
SOURCE: dict[str, dict[str, Any]] = {
    "C1": {"ELS_c": 0.5, "comb": 107, "unite": "cm"},
    "C2": {
        "ELS_f": 514,
        "ELS_c": 727,
        "ELU": 1048,
        "comb": 112,
        "unite": "kN",
        "alternatives": {"ELS_f": 554, "ELS_c": 767, "ELU": 1102},
    },
    "C3": {
        "ELS_f": (155, -209),
        "ELS_c": (186, -312),
        "ELU": (260, -449),
        "comb": 111,
        "unite": "kN·m",
    },
    "C4": {"ELU": 253, "comb": 114, "unite": "kN"},
    "C5": {"ELU": (273, -463), "comb": 111, "unite": "kN·m"},
    "C6": {"ELS_f": 180, "ELS_c": 276, "ELU": 408, "comb": (105, 112), "unite": "kN·m"},
    "C7": {"ELU": -177, "comb": None, "unite": "kN·m"},
    "C8": {"ELU": (620, -653), "comb": (105, 112), "unite": "kN"},
    "C9": {"ELS_f": 79, "ELS_c": 118, "ELU": 174, "comb": 111, "unite": "kN·m/m"},
    "C10": {"ELS_f": 82, "ELS_c": 134, "ELU": 198, "comb": 112, "unite": "kN·m/m"},
    "C11": {"FR": 18.9, "TE-": 64.1, "unite": "kN/m"},
    "C12": {"courant": 320, "rive": 568, "comb": (111, 100), "unite": "kN/m"},
    "C13": {"LM1": (85, -47, 154), "LM2": (64, -30, 138), "unite": "kN·m/m, kN/m"},
}
TOLERANCE = {
    "C2": 0.03,
    "C3": 0.05,
    "C4": 0.05,
    "C5": 0.05,
    "C6": 0.05,
    "C7": 0.05,
    "C8": 0.05,
    "C9": 0.10,
    "C10": 0.10,
    "C11": 0.10,
    "C12": 0.10,
    "C13": 0.10,
}
CASE_OF = {"TE+": "TEP", "TE-": "TEM", "TR": "TR", "FR": "FR"}

Extractor = Callable[[str], FloatArray]
Scalar = Callable[[FloatArray], FloatArray]


def _col(a: FloatArray) -> FloatArray:
    out: FloatArray = a[:, 0]
    return out


def _signed(sign: float) -> Scalar:
    def scalar(a: FloatArray) -> FloatArray:
        out: FloatArray = sign * a[:, 0]
        return out

    return scalar


def _norm(a: FloatArray) -> FloatArray:
    out: FloatArray = np.sqrt(np.sum(a * a, axis=1))
    return out


@dataclass
class Envelope:
    maximum: FloatArray
    """Per point, max over the TS positions."""
    minimum: FloatArray
    arg_max: list[str]
    """Case of the max, per point (the TS position, or `—`)."""
    arg_min: list[str]


class Combiner:
    """Values of a combination at every point of a quantity, enveloped over TS."""

    def __init__(self, results: Results, positions: dict[str, Any]) -> None:
        self.results = results
        self.ts = {
            t: sorted(
                n
                for n, p in positions.items()
                if p["modele"] == "TS" and p["transversal"] == t
            )
            for t in ("axe", "bord")
        }
        self.lm2 = sorted(n for n, p in positions.items() if p["modele"] == "LM2")

    def combine(self, c: Combination, ex: Extractor, scalar: Scalar) -> Envelope:
        fixed = c.gamma_g * (ex("PP") + ex("G2"))
        for action, coef in c.coefficients.items():
            if action == "LM1":
                fixed = fixed + coef * (ex("UDL") + ex("TR"))
            else:
                fixed = fixed + coef * ex(CASE_OF[action])
        lm1 = c.coefficients.get("LM1")
        if lm1 is None or c.ts_position is None:
            value = scalar(fixed)
            return Envelope(value, value, ["—"] * len(value), ["—"] * len(value))
        names = self.ts[c.ts_position]
        stack = np.stack([scalar(fixed + lm1 * ex(n)) for n in names])
        imax = np.argmax(stack, axis=0)
        imin = np.argmin(stack, axis=0)
        return Envelope(
            np.max(stack, axis=0),
            np.min(stack, axis=0),
            [names[i] for i in imax],
            [names[i] for i in imin],
        )

    def column(
        self, number: int, column: str, ex: Extractor, scalar: Scalar
    ) -> Envelope:
        """`ELS_f`, `ELS_c` or `ELU` (envelope of ELU+ and ELU-)."""
        if column != "ELU":
            return self.combine(find(number, column), ex, scalar)
        a = self.combine(find(number, "ELU+"), ex, scalar)
        b = self.combine(find(number, "ELU-"), ex, scalar)
        take_a_max = a.maximum >= b.maximum
        take_a_min = a.minimum <= b.minimum
        return Envelope(
            np.where(take_a_max, a.maximum, b.maximum),
            np.where(take_a_min, a.minimum, b.minimum),
            [
                x if t else y
                for x, y, t in zip(a.arg_max, b.arg_max, take_a_max, strict=True)
            ],
            [
                x if t else y
                for x, y, t in zip(a.arg_min, b.arg_min, take_a_min, strict=True)
            ],
        )

    def elementary(
        self, names: list[str], base: list[str], ex: Extractor, scalar: Scalar
    ) -> Envelope:
        """Unweighted envelope of Σ base + one moving case, over `names` (C13)."""
        fixed = sum((ex(b) for b in base), start=np.zeros_like(ex(names[0])))
        stack = np.stack([scalar(fixed + ex(n)) for n in names])
        imax = np.argmax(stack, axis=0)
        imin = np.argmin(stack, axis=0)
        return Envelope(
            np.max(stack, axis=0),
            np.min(stack, axis=0),
            [names[i] for i in imax],
            [names[i] for i in imin],
        )


def _gap(value: float, source: float) -> float:
    return (value - source) / abs(source) if source else math.nan


def _row(
    point: str,
    label: str,
    value: float,
    source: float,
    tolerance: float | None,
    where: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    gap = _gap(value, source)
    if tolerance is None:
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
        "lieu": where,
        "note": note,
    }


class Comparison:
    def __init__(
        self, v: ModelValues, results: Results, positions: dict[str, Any]
    ) -> None:
        self.v = v
        self.r = results
        self.comb = Combiner(results, positions)
        self.x, self.y = slab_xy(results)
        self.beam_xyz = results.coords[results.beam_nodes]
        cell_mid = self._cell_mid_z()
        piles = results.beam_rows("PIEUX")
        caps = results.beam_rows("CHEVETRES")
        self.pile_rows = piles
        self.cap_rows = caps
        self.mid_z = cell_mid
        self.cap_sign = self._cap_signs()

    # -- geometry ----------------------------------------------------------------
    def _cell_mid_z(self) -> FloatArray:
        z = self.beam_xyz[:, 2]
        mids = (z[0::2] + z[1::2]) / 2.0
        out: FloatArray = np.repeat(mids, 2)
        return out

    def _where_slab(self, i: int) -> dict[str, Any]:
        return {"X": float(self.x[i]), "Y": float(self.y[i])}

    def _where_beam(self, row: int) -> dict[str, Any]:
        p = self.beam_xyz[row]
        return {"X": float(p[0]), "Y": float(p[1]), "Z": float(p[2])}

    # -- extractors --------------------------------------------------------------
    def slab_ex(self, name: str, mask: np.ndarray[Any, Any] | None = None) -> Extractor:
        k = comp(name)

        def ex(case: str) -> FloatArray:
            a = self.r.slab[case][:, [k]]
            out: FloatArray = a if mask is None else a[mask]
            return out

        return ex

    def beam_ex(self, rows: IntArray, names: tuple[str, ...]) -> Extractor:
        ks = [bcomp(n) for n in names]

        def ex(case: str) -> FloatArray:
            out: FloatArray = self.r.beams[case][rows][:, ks]
            return out

        return ex

    def _cap_signs(self) -> FloatArray:
        """Sign s per cap row: + if MFY under G = PP + G2 is positive at Y = 0 of its
        cap beam (sagging there, § 2.3), so that s·MFY is the sagging moment."""
        rows = self.cap_rows
        g = (
            self.r.beams["PP"][rows, bcomp("MFY")]
            + self.r.beams["G2"][rows, bcomp("MFY")]
        )
        xyz = self.beam_xyz[rows]
        signs = np.zeros(len(rows))
        for x in self.v.x_files:
            on_cap = np.abs(xyz[:, 0] - x) < LEVEL
            centre = on_cap & (np.abs(xyz[:, 1]) < LEVEL)
            ref = float(np.mean(g[centre]))
            signs[on_cap] = 1.0 if ref > 0 else -1.0
        return signs

    # -- points ------------------------------------------------------------------
    def c1(self) -> list[dict[str, Any]]:
        def ex(case: str) -> FloatArray:
            out: FloatArray = self.r.depl[case]
            return out

        env = self.comb.column(107, "ELS_c", ex, _norm)
        i = int(np.nanargmax(env.maximum))
        value_cm = float(env.maximum[i]) * 100.0
        xyz = self.r.coords[i]
        row = _row(
            "C1",
            "ELS c (107)",
            value_cm,
            0.5,
            None,
            {
                "X": float(xyz[0]),
                "Y": float(xyz[1]),
                "Z": float(xyz[2]),
                "TS": env.arg_max[i],
            },
        )
        compatible = 0.25 <= value_cm < 0.75
        row["verdict"] = (
            "compatible avec l'arrondi"
            if compatible
            else "non compatible avec l'arrondi"
        )
        return [row]

    def c2(self) -> list[dict[str, Any]]:
        top = np.array(
            [abs(self.beam_xyz[r, 2] - self.v.z_mid) < LEVEL for r in self.pile_rows]
        )
        rows = self.pile_rows[top]
        ex = self.beam_ex(rows, ("N",))
        out = []
        for column in ("ELS_f", "ELS_c", "ELU"):
            env = self.comb.column(112, column, ex, lambda a: -_col(a))
            i = int(np.argmax(env.maximum))
            src = SOURCE["C2"][column]
            alt = SOURCE["C2"]["alternatives"][column]
            row = _row(
                "C2",
                f"{column} (112)",
                float(env.maximum[i]) / 1e3,
                src,
                TOLERANCE["C2"],
                {**self._where_beam(int(rows[i])), "TS": env.arg_max[i]},
                f"écart à la valeur alternative {alt} : "
                f"{_gap(float(env.maximum[i]) / 1e3, alt):+.3f}",
            )
            out.append(row)
        return out

    def _bar_modulus(
        self,
        point: str,
        rows: IntArray,
        names: tuple[str, str],
        number: int,
        columns: tuple[str, ...],
        source: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ex = self.beam_ex(rows, names)
        out = []
        for column in columns:
            env = self.comb.column(number, column, ex, _norm)
            i = int(np.argmax(env.maximum))
            published = source[column]
            if isinstance(published, tuple):
                governing = max(abs(published[0]), abs(published[1]))
                note = (
                    f"publié {published[0]} / {published[1]} : "
                    f"module comparé à {governing}"
                )
            else:
                governing = abs(published)
                note = ""
            comps = (
                self.r.beams
            )  # signed components at the governing point, for information
            del comps
            out.append(
                _row(
                    point,
                    f"{column} ({number})",
                    float(env.maximum[i]) / 1e3,
                    governing,
                    TOLERANCE[point],
                    {**self._where_beam(int(rows[i])), "TS": env.arg_max[i]},
                    note,
                )
            )
        return out

    def _pile_zone(self, low: float, high: float) -> IntArray:
        z = self.mid_z[self.pile_rows]
        sel: IntArray = self.pile_rows[(z >= low - LEVEL) & (z <= high + LEVEL)]
        return sel

    def c3_c4_c5(self) -> list[dict[str, Any]]:
        top, bottom = self.v.plug
        plug = self._pile_zone(bottom, top)
        below = self._pile_zone(-1e9, bottom - 2 * LEVEL)
        rows = self._bar_modulus(
            "C3", plug, ("MFY", "MFZ"), 111, ("ELS_f", "ELS_c", "ELU"), SOURCE["C3"]
        )
        rows += self._bar_modulus("C4", plug, ("VY", "VZ"), 114, ("ELU",), SOURCE["C4"])
        rows += self._bar_modulus(
            "C5", below, ("MFY", "MFZ"), 111, ("ELU",), SOURCE["C5"]
        )
        return rows

    def _cap_moment_ex(self, rows: IntArray) -> Extractor:
        index = {int(r): j for j, r in enumerate(self.cap_rows)}
        signs = np.array([self.cap_sign[index[int(r)]] for r in rows])[:, None]
        k = bcomp("MFY")

        def ex(case: str) -> FloatArray:
            out: FloatArray = signs * self.r.beams[case][rows][:, [k]]
            return out

        return ex

    def c6_c7_c8(self) -> list[dict[str, Any]]:
        y = self.beam_xyz[self.cap_rows, 1]
        span = self.cap_rows[np.abs(y) < self.v.y_piles - LEVEL]
        supports = self.cap_rows[np.abs(np.abs(y) - self.v.y_piles) < LEVEL]
        out = []
        ex = self._cap_moment_ex(span)
        for column, number in (("ELS_f", 105), ("ELS_c", 105), ("ELU", 112)):
            env = self.comb.column(number, column, ex, _col)
            i = int(np.argmax(env.maximum))
            out.append(
                _row(
                    "C6",
                    f"{column} ({number})",
                    float(env.maximum[i]) / 1e3,
                    SOURCE["C6"][column],
                    TOLERANCE["C6"],
                    {**self._where_beam(int(span[i])), "TS": env.arg_max[i]},
                )
            )
        ex7 = self._cap_moment_ex(supports)
        best: tuple[float, int, str, int] | None = None
        for number in range(100, 116):
            env = self.comb.column(number, "ELU", ex7, _col)
            i = int(np.argmin(env.minimum))
            if best is None or env.minimum[i] < best[0]:
                best = (float(env.minimum[i]), i, env.arg_min[i], number)
        assert best is not None
        value = best[0] / 1e3
        out.append(
            _row(
                "C7",
                f"ELU (enveloppe 100-115, gouvernée par {best[3]})",
                abs(value),
                177.0,
                TOLERANCE["C7"],
                {
                    **self._where_beam(int(supports[best[1]])),
                    "TS": best[2],
                    "moment_signe_kNm": value,
                },
                "minimum de M_travée comparé en module à |−177|",
            )
        )
        exv = self.beam_ex(self.cap_rows, ("VZ",))
        envs = [self.comb.column(n, "ELU", exv, _col) for n in (105, 112)]
        vmax = max(float(np.max(e.maximum)) for e in envs)
        vmin = min(float(np.min(e.minimum)) for e in envs)
        governing = max(abs(vmax), abs(vmin)) / 1e3
        out.append(
            _row(
                "C8",
                "ELU (105, 112)",
                governing,
                653.0,
                TOLERANCE["C8"],
                {"VZ_max_kN": vmax / 1e3, "VZ_min_kN": vmin / 1e3},
                "module de l'effort tranchant comparé à |−653| ; publié 620 / −653",
            )
        )
        return out

    def _chapeau_mask(self) -> np.ndarray[Any, Any]:
        half = self.v.cap_width / 2.0
        near = np.zeros(len(self.x), dtype=bool)
        for xf in self.v.x_files:
            near |= np.abs(self.x - xf) <= half + LEVEL
        return near

    def c9_c10(self) -> list[dict[str, Any]]:
        chapeau = self._chapeau_mask()
        travee = ~chapeau
        out = []
        idx_c = np.nonzero(chapeau)[0]
        idx_t = np.nonzero(travee)[0]
        for point, mask, idx, number, sign in (
            ("C9", chapeau, idx_c, 111, 1.0),
            ("C10", travee, idx_t, 112, -1.0),
        ):
            ex = self.slab_ex("MXX", mask)
            for column in ("ELS_f", "ELS_c", "ELU"):
                env = self.comb.column(number, column, ex, _signed(sign))
                i = int(np.argmax(env.maximum))
                out.append(
                    _row(
                        point,
                        f"{column} ({number})",
                        float(env.maximum[i]) / 1e3,
                        SOURCE[point][column],
                        TOLERANCE[point],
                        {**self._where_slab(int(idx[i])), "TS": env.arg_max[i]},
                    )
                )
        return out

    def c11(self) -> list[dict[str, Any]]:
        out = []
        for label, case in (("FR", "FR"), ("TE-", "TEM")):
            values = np.abs(self.r.slab[case][:, comp("NXX")])
            i = int(np.argmax(values))
            out.append(
                _row(
                    "C11",
                    f"{label} seul",
                    float(values[i]) / 1e3,
                    SOURCE["C11"][label],
                    TOLERANCE["C11"],
                    {
                        **self._where_slab(i),
                        "NXX_signe_kN_m": float(self.r.slab[case][i, comp("NXX")])
                        / 1e3,
                    },
                )
            )
        return out

    def c12(self) -> list[dict[str, Any]]:
        out = []
        lane = np.abs(self.y) <= self.v.lane[1] + LEVEL
        for label, mask, number in (("courant", lane, 111), ("rive", ~lane, 100)):
            idx = np.nonzero(mask)[0]
            env = self.comb.column(
                number, "ELU", self.slab_ex("QX", mask), lambda a: np.abs(_col(a))
            )
            i = int(np.argmax(env.maximum))
            out.append(
                _row(
                    "C12",
                    f"ELU {label} ({number})",
                    float(env.maximum[i]) / 1e3,
                    SOURCE["C12"][label],
                    TOLERANCE["C12"],
                    {**self._where_slab(int(idx[i])), "TS": env.arg_max[i]},
                )
            )
        # Lecture complémentaire, sans verdict : consoles d'about.
        about = (self.x <= self.v.x_files[0] + self.v.cap_width / 2.0 + LEVEL) | (
            self.x >= self.v.x_files[-1] - self.v.cap_width / 2.0 - LEVEL
        )
        for label, number in (("courant", 111), ("rive", 100)):
            idx = np.nonzero(about)[0]
            env = self.comb.column(
                number, "ELU", self.slab_ex("QX", about), lambda a: np.abs(_col(a))
            )
            i = int(np.argmax(env.maximum))
            out.append(
                _row(
                    "C12",
                    f"ELU consoles d'about ({number}), information",
                    float(env.maximum[i]) / 1e3,
                    SOURCE["C12"][label],
                    None,
                    {**self._where_slab(int(idx[i])), "TS": env.arg_max[i]},
                    "lecture complémentaire, sans verdict",
                )
            )
        return out

    def c13(self) -> list[dict[str, Any]]:
        out = []
        ts_all = self.comb.ts["axe"] + self.comb.ts["bord"]
        for model, names, base in (
            ("LM1", ts_all, ["UDL", "TR"]),
            ("LM2", self.comb.lm2, []),
        ):
            ex = self.slab_ex("MXX")
            env = self.comb.elementary(names, base, ex, lambda a: -_col(a))
            i_inf = int(np.argmax(env.maximum))
            i_sup = int(np.argmin(env.minimum))
            env_q = self.comb.elementary(
                names, base, self.slab_ex("QX"), lambda a: np.abs(_col(a))
            )
            i_q = int(np.argmax(env_q.maximum))
            src = SOURCE["C13"][model]
            out.append(
                _row(
                    "C13",
                    f"{model} Mxx inf.",
                    float(env.maximum[i_inf]) / 1e3,
                    src[0],
                    TOLERANCE["C13"],
                    {**self._where_slab(i_inf), "cas": env.arg_max[i_inf]},
                )
            )
            out.append(
                _row(
                    "C13",
                    f"{model} Mxx sup.",
                    float(env.minimum[i_sup]) / 1e3,
                    src[1],
                    TOLERANCE["C13"],
                    {**self._where_slab(i_sup), "cas": env.arg_min[i_sup]},
                )
            )
            out.append(
                _row(
                    "C13",
                    f"{model} V (|Qxx|)",
                    float(env_q.maximum[i_q]) / 1e3,
                    src[2],
                    TOLERANCE["C13"],
                    {**self._where_slab(i_q), "cas": env_q.arg_max[i_q]},
                )
            )
        return out

    def all_points(self) -> list[dict[str, Any]]:
        return [
            *self.c13(),
            *self.c1(),
            *self.c2(),
            *self.c3_c4_c5(),
            *self.c6_c7_c8(),
            *self.c9_c10(),
            *self.c11(),
            *self.c12(),
        ]


__all__ = ["SOURCE", "TOLERANCE", "Combiner", "Comparison", "Envelope"]
