"""Diagrams of the engineering summary (lot 49 bis), drawn with matplotlib (Agg).

From `paquet/diagrammes.json` only (written by `aster_expert.livrables.ingenieur`):

- one plate per family of beams: N, M and V along each member (one small multiple per
  member, rows N / M / V), the ELU envelope (band between max and min) and the
  characteristic ELS envelope (lines), the extrema of the ELU envelope written with
  their value and their coordinate; kN and kN·m;
- one plate per declared cut of a shell: the components along the cut, same
  envelopes, the excluded zones (exclusion discs, nodes shared with a beam) hatched.

Two series per plot, in the first two slots of the reference categorical palette of
the dataviz method (blue, orange), on a light surface (the plates are printed);
identity is never carried by colour alone: a legend names both series.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ELU_COLOUR = "#2a78d6"
ELS_COLOUR = "#eb6834"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
COLUMNS = 7
UNITS = {"N": "kN", "M": "kN·m", "V": "kN"}
STATE_NAMES = {"ELU_fondamental": "ELU fondamental", "ELS_caracteristique": "ELS car."}


def _axis_label(role: str, column: str) -> str:
    """The component itself (Code_Aster sign), or M, V for a resultant."""
    name = {"M_RES": "M", "V_RES": "V"}.get(column, column)
    return f"{name} ({UNITS[role]})"


def _style(ax: Any) -> None:
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(MUTED)
        spine.set_linewidth(0.6)
    ax.tick_params(colors=MUTED, labelsize=7)


def _member_series(
    rows: list[dict[str, Any]], key: str
) -> tuple[list[float], list[float]]:
    """(abscissa, value) of the element ends of a member, element after element along
    it: at a node, the end of one element then the start of the next (a jump shows as
    a step, never as a saw tooth)."""
    elements: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        elements.setdefault(r["maille_med"], []).append(r)
    ordered: list[dict[str, Any]] = []
    for ends in sorted(
        elements.values(), key=lambda e: sum(r["abscisse_m"] for r in e) / len(e)
    ):
        ordered += sorted(ends, key=lambda r: r["abscisse_m"])
    return [r["abscisse_m"] for r in ordered], [r[key] * 1.0e-3 for r in ordered]


def _annotate(
    ax: Any, vertical: bool, s: list[float], v: list[float], which: str
) -> None:
    if not v:
        return
    k = (
        max(range(len(v)), key=v.__getitem__)
        if which == "max"
        else min(range(len(v)), key=v.__getitem__)
    )
    text = f"{v[k]:.1f}\n@ {s[k]:+.2f} m"
    xy = (v[k], s[k]) if vertical else (s[k], v[k])
    ax.annotate(
        text,
        xy=xy,
        xytext=(6 if which == "max" else -6, 0),
        textcoords="offset points",
        ha="left" if which == "max" else "right",
        va="center",
        fontsize=6.5,
        color=INK,
    )
    ax.plot(*xy, marker="o", markersize=3.5, color=ELU_COLOUR, zorder=4)


def draw_beams(entry: dict[str, Any], out: Path) -> Path:
    rows: list[dict[str, Any]] = entry["lignes"]
    members = sorted({r["groupe"] or entry["famille"] for r in rows})
    by_member = {
        m: [r for r in rows if (r["groupe"] or entry["famille"]) == m] for m in members
    }
    vertical = entry["axe"] == "Z"
    quantities = [(q, c) for q, c in entry["grandeurs"].items() if c]
    states = [s for s in entry["etats"] if s in STATE_NAMES]
    bands = math.ceil(len(members) / COLUMNS)
    ncols = min(COLUMNS, len(members))
    nrows = bands * len(quantities)
    size = (2.3 * ncols + 0.6, (3.4 if vertical else 2.2) * nrows + 0.9)
    fig, axes = plt.subplots(nrows, ncols, figsize=size, squeeze=False)
    for band in range(bands):
        for j in range(ncols):
            index = band * COLUMNS + j
            for i, (role, column) in enumerate(quantities):
                ax = axes[band * len(quantities) + i][j]
                if index >= len(members):
                    ax.set_visible(False)
                    continue
                member = members[index]
                _style(ax)
                for state, colour in zip(
                    states, (ELU_COLOUR, ELS_COLOUR), strict=False
                ):
                    s, hi = _member_series(by_member[member], f"{state}/{column}/max")
                    _, lo = _member_series(by_member[member], f"{state}/{column}/min")
                    label = STATE_NAMES[state]
                    one_sided = column == "M_RES" or column == "V_RES"
                    if state == "ELU_fondamental" and not one_sided:
                        if vertical:
                            ax.fill_betweenx(
                                s, lo, hi, color=colour, alpha=0.15, linewidth=0
                            )
                        else:
                            ax.fill_between(
                                s, lo, hi, color=colour, alpha=0.15, linewidth=0
                            )
                    for values, style in ((hi, "-"), (lo, "--")):
                        if one_sided and values is lo:
                            continue
                        xs, ys = (values, s) if vertical else (s, values)
                        ax.plot(
                            xs,
                            ys,
                            style,
                            color=colour,
                            linewidth=1.3,
                            label=label if values is hi else None,
                        )
                    if state == "ELU_fondamental":
                        _annotate(ax, vertical, s, hi, "max")
                        if not one_sided:
                            _annotate(ax, vertical, s, lo, "min")
                if vertical:
                    ax.axvline(0.0, color=MUTED, linewidth=0.6)
                    ax.set_ylabel(f"{entry['axe']} (m)", fontsize=7, color=MUTED)
                    ax.set_xlabel(_axis_label(role, column), fontsize=7, color=MUTED)
                else:
                    ax.axhline(0.0, color=MUTED, linewidth=0.6)
                    ax.set_xlabel(f"{entry['axe']} (m)", fontsize=7, color=MUTED)
                    ax.set_ylabel(_axis_label(role, column), fontsize=7, color=MUTED)
                name = {"M_RES": "M = √(MFY²+MFZ²)", "V_RES": "V = √(VY²+VZ²)"}.get(
                    column, column
                )
                ax.set_title(f"{member}\n{name}", fontsize=7.5, color=INK)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, frameon=False, ncols=2)
    fig.suptitle(
        f"{entry['famille']} : N, M, V le long des éléments — enveloppes "
        "(trait plein : "
        "max, tirets : min) ; extrema ELU annotés (valeur, cote)",
        fontsize=10,
        color=INK,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path = out / f"diagramme_{_slug(entry['famille'])}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def _spans(points: list[dict[str, Any]]) -> list[tuple[float, float]]:
    """Contiguous excluded stretches of a cut."""
    out: list[tuple[float, float]] = []
    start = None
    previous = None
    for p in points:
        if p["exclu"] and start is None:
            start = p["abscisse_m"]
        if not p["exclu"] and start is not None:
            out.append((start, previous if previous is not None else start))
            start = None
        previous = p["abscisse_m"]
    if start is not None and previous is not None:
        out.append((start, previous))
    return out


def draw_cut(cut: dict[str, Any], out: Path) -> Path:
    comps = cut["composantes"]
    fig, axes = plt.subplots(
        len(comps), 1, figsize=(11, 2.8 * len(comps) + 0.8), squeeze=False
    )
    s = [p["abscisse_m"] for p in cut["points"]]
    width = 0.5 * min(
        (b - a for a, b in zip(s[:-1], s[1:], strict=True) if b > a), default=0.05
    )
    for i, comp in enumerate(comps):
        ax = axes[i][0]
        _style(ax)
        for a, b in _spans(cut["points"]):
            ax.axvspan(
                a - width,
                b + width,
                facecolor="none",
                edgecolor=MUTED,
                hatch="///",
                linewidth=0.0,
                label="zone exclue" if (a, b) == _spans(cut["points"])[0] else None,
            )
        for state, colour in zip(cut["etats"], (ELU_COLOUR, ELS_COLOUR), strict=False):
            hi = [p[f"{state}/{comp}/max"] * 1.0e-3 for p in cut["points"]]
            lo = [p[f"{state}/{comp}/min"] * 1.0e-3 for p in cut["points"]]
            if state == "ELU_fondamental":
                ax.fill_between(s, lo, hi, color=colour, alpha=0.15, linewidth=0)
            ax.plot(
                s,
                hi,
                "-",
                color=colour,
                linewidth=1.3,
                label=STATE_NAMES.get(state, state),
            )
            ax.plot(s, lo, "--", color=colour, linewidth=1.3)
            if state == "ELU_fondamental":
                kept = [k for k, p in enumerate(cut["points"]) if not p["exclu"]]
                for which in ("max", "min"):
                    series = hi if which == "max" else lo
                    if not kept:
                        continue
                    k = (max if which == "max" else min)(kept, key=series.__getitem__)
                    ax.plot(s[k], series[k], "o", markersize=3.5, color=colour)
                    ax.annotate(
                        f"{series[k]:.1f} @ {s[k]:.2f} m",
                        (s[k], series[k]),
                        xytext=(4, 6 if which == "max" else -10),
                        textcoords="offset points",
                        fontsize=7,
                        color=INK,
                    )
        ax.axhline(0.0, color=MUTED, linewidth=0.6)
        ax.set_ylabel(f"{comp} (kN·m/m)", fontsize=8, color=MUTED)
        ax.set_xlabel(f"{cut['le_long_de']} (m)", fontsize=8, color=MUTED)
        ax.legend(fontsize=7, frameon=False, loc="upper right")
    fig.suptitle(
        f"Coupe {cut['coupe']} ({cut['famille']}, {cut['axe']} = "
        f"{cut['valeur_lue_m']:.3f} m) : "
        "enveloppes ELU (bande, extrema hors zones exclues annotés) et ELS car. ; "
        "hachures : disques d'exclusion et nœuds partagés avec une poutre",
        fontsize=9,
        color=INK,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = out / f"coupe_{cut['coupe']}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def _slug(text: str) -> str:
    keep = "".join(c if c.isalnum() else "_" for c in text.lower())
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ç", "c")):
        keep = keep.replace(a, b)
    return keep.strip("_")


def draw_all(package: Path) -> list[Path]:
    data = json.loads((package / "diagrammes.json").read_text("utf-8"))
    out = package / "diagrammes"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    made = [draw_beams(e, out) for e in data["poutres"] if e["lignes"]]
    made += [draw_cut(c, out) for c in data["coupes"] if c["points"]]
    return made


__all__ = ["draw_all", "draw_beams", "draw_cut"]
