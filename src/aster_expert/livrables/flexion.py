"""Export of the design sections for MM's bending software (lot 49 bis).

MM types, by hand, the geometry of a section and a table « Type | N (kN) | M (kN·m) »
into a reinforced-concrete bending software. One file per design section and plane of
bending, `flexion_composee/<section>[_<moment>].csv`, written to be copied line by line:

- `;` separator, decimal comma, UTF-8 with BOM (Excel in French opens it as is);
- a header, one datum per line, in the order of input of the software (type of section,
  h, b, ds, di; concrete, steel, exposure class, cnom; equivalence rule; conventions);
- the table `N° ; Type ; N (kN) ; M (kN.m)`, then an empty column, then the
  traceability (combination, moving position, place, concomitant V, raw values of
  Code_Aster and their frame);
- at most four lines per limit state (M max and M min with the concomitant N, N max
  and N min with the concomitant M), states in the order of the `Type` list of the
  software: `ELU`, `ELUA`, `ELS` (characteristic), `ELSfiss` (the state the project
  declares for cracking);
- a footer with the SHA-256 of the MED of results.

Conventions are converted here, never left to the reader:

- N > 0 in compression: N = −N(Code_Aster), Code_Aster giving N > 0 in tension
  (R3.08.01, « Le tenseur des contraintes » : N = ∫ σxx dS);
- M > 0 compresses the top fibre, declared per plane (`top_fibre`). With
  MFY = ∫ z σxx dS and MFZ = −∫ y σxx dS (R3.08.01), a top fibre on +z_l gives
  M = −MFY, on −z_l M = +MFY, on +y_l M = +MFZ, on −y_l M = −MFZ; for a shell, MXX > 0
  stretches the top face (CA-045), so a top fibre on the normal side gives M = −MXX;
- a circular section in skew bending exports the resultant √(MFY² + MFZ²) ≥ 0, with a
  warning (the software computes plane bending; there is no « M min »).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import numpy as np

from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.sections import M_RES, V_RES, FamilyRows, SectionRows
from aster_expert.livrables.torseurs import (
    SHEAR_OF_MOMENT,
    STATE_LABELS,
    StateEnvelope,
    Target,
    _pick,
    torsor_entry,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import (
    BendingExport,
    BendingPlane,
    EngineeringSummarySection,
    LengthOrData,
    TextOrData,
)
from aster_expert.projet.errors import ProjectError

TYPE_OF_STATE = {
    "ELU_fondamental": "ELU",
    "ELU_accidentel": "ELUA",
    "ELS_caracteristique": "ELS",
}
TYPE_ORDER = ("ELU", "ELUA", "ELS", "ELSfiss")
_FIBRE_SIGN = {
    ("MFY", "+z_l"): -1.0,
    ("MFY", "-z_l"): 1.0,
    ("MFZ", "+y_l"): 1.0,
    ("MFZ", "-y_l"): -1.0,
    ("MXX", "+n"): -1.0,
    ("MXX", "-n"): 1.0,
    ("MYY", "+n"): -1.0,
    ("MYY", "-n"): 1.0,
}
_NORMAL = {"MFY": "N", "MFZ": "N", "MXX": "NXX", "MYY": "NYY", "resultante": "N"}


def moment_sign(plane: BendingPlane) -> float:
    """Factor from the Code_Aster moment to « M > 0 compresses the top fibre »."""
    if plane.moment == "resultante":
        return 1.0
    key = (plane.moment, plane.top_fibre or "")
    if key not in _FIBRE_SIGN:
        message = (
            f"export : fibre {plane.top_fibre} incompatible avec le moment "
            f"{plane.moment} (MFY : ±z_l ; MFZ : ±y_l ; MXX, MYY : ±n)"
        )
        raise ProjectError(message)
    return _FIBRE_SIGN[key]


def number(value: float, decimals: int = 1) -> str:
    """French decimal comma, no « -0,0 »."""
    text = f"{value:.{decimals}f}"
    if float(text) == 0.0:
        text = f"{0.0:.{decimals}f}"
    return text.replace(".", ",")


def _length(ctx: ProjectContext, item: LengthOrData, unit: str) -> tuple[float, str]:
    if item.data is not None:
        found = ctx.data().items().get(item.data)
        if found is None or found.status != "fourni" or isinstance(found.value, str):
            message = f"export : donnée {item.data} absente ou à fournir"
            raise ProjectError(message)
        assert found.value is not None
        value, source_unit = float(found.value), found.unit  # type: ignore[arg-type]
        source = f"{item.source} (données : {item.data})"
    else:
        assert item.value is not None and item.unit is not None
        value, source_unit, source = item.value, item.unit, item.source
    factor = {
        ("m", "m"): 1.0,
        ("mm", "m"): 1.0e-3,
        ("m", "mm"): 1.0e3,
        ("mm", "mm"): 1.0,
    }.get((source_unit, unit))
    if factor is None:
        message = f"export : unité {source_unit!r} non convertible en {unit}"
        raise ProjectError(message)
    return value * factor, source


def _text(ctx: ProjectContext, item: TextOrData) -> tuple[str, str]:
    if item.data is not None:
        found = ctx.data().items().get(item.data)
        if found is None or found.status != "fourni":
            message = f"export : donnée {item.data} absente ou à fournir"
            raise ProjectError(message)
        return str(found.value), f"{item.source} (données : {item.data})"
    assert item.value is not None
    return item.value, item.source


@dataclass
class ExportLine:
    state: str
    type_label: str
    case: str
    n_kn: float
    m_knm: float
    entry: dict[str, Any]


def _lines_of_state(
    fr: FamilyRows,
    combinations: list[GenericCombination],
    env: StateEnvelope,
    sec: SectionRows,
    plane: BendingPlane,
    type_label: str,
) -> list[ExportLine]:
    excluded = sec.singular if sec.section.exclude_singular else np.zeros_like(sec.mask)
    rows = np.where(sec.mask & ~excluded)[0]
    sign = moment_sign(plane)
    column = M_RES if plane.moment == "resultante" else plane.moment
    normal = _NORMAL[plane.moment]
    wanted: list[tuple[str, Target]] = []
    if plane.moment == "resultante":
        wanted.append(("M max", Target("M max", M_RES, "max", "M")))
    else:
        hi, lo = ("max", "min") if sign > 0 else ("min", "max")
        wanted += [
            ("M max", Target("M max", column, hi, "M")),
            ("M min", Target("M min", column, lo, "M")),
        ]
    # N > 0 en compression : N max du logiciel = N min de Code_Aster.
    wanted += [
        ("N max", Target("N max", normal, "min", "N")),
        ("N min", Target("N min", normal, "max", "N")),
    ]
    out: list[ExportLine] = []
    seen: dict[tuple[int, int, int, str, str], ExportLine] = {}
    for case, target in wanted:
        picked = _pick(env, fr, rows, target)
        if picked is None:
            continue
        row, _value, ci, pi = picked
        entry = torsor_entry(fr, combinations, row, ci, pi)
        torsor = entry["torseur_si"]
        key = (
            int(fr.node[row]),
            ci,
            pi,
            number(-torsor[normal] * 1.0e-3),
            number(sign * torsor[column] * 1.0e-3),
        )
        same = seen.get(key)
        if same is not None:
            # Même nœud, même combinaison et position, mêmes N et M au dixième : une
            # seule ligne, qui nomme les cas qu'elle couvre.
            same.case += ", " + case
            continue
        line = ExportLine(
            state=env.state,
            type_label=type_label,
            case=case,
            n_kn=-torsor[normal] * 1.0e-3,
            m_knm=sign * torsor[column] * 1.0e-3,
            entry=entry,
        )
        seen[key] = line
        out.append(line)
    return out


def export_table(
    summary: EngineeringSummarySection,
    fr: FamilyRows,
    combinations: list[GenericCombination],
    envelopes: dict[str, StateEnvelope],
    sec: SectionRows,
    plane: BendingPlane,
) -> tuple[list[ExportLine], list[str]]:
    """The lines of one file, and the limit states left out (with why)."""
    types: list[tuple[str, str]] = []
    left_out: list[str] = []
    for state in envelopes:
        label = TYPE_OF_STATE.get(state)
        if label is not None:
            types.append((label, state))
        if state == summary.cracking.state:
            types.append(("ELSfiss", state))
        elif label is None:
            left_out.append(
                f"{STATE_LABELS[state]} : ni caractéristique ni de fissuration "
                f"(fissuration : {STATE_LABELS[summary.cracking.state]}, "
                f"{summary.cracking.source})"
            )
    types.sort(key=lambda t: TYPE_ORDER.index(t[0]))
    lines: list[ExportLine] = []
    for label, state in types:
        lines += _lines_of_state(fr, combinations, envelopes[state], sec, plane, label)
    for absent in summary.absent_limit_states:
        left_out.append(f"{STATE_LABELS[absent.state]} : absent ({absent.reason})")
    return lines, left_out


def _place(fr: FamilyRows, entry: dict[str, Any]) -> tuple[str, str]:
    lieu = entry["lieu"]
    parts = [lieu["groupe"]] if lieu["groupe"] else []
    if lieu["maille_med"] is not None:
        parts.append(f"maille {lieu['maille_med']}")
        if lieu["extremite"] is not None:
            parts.append(f"extrémité {lieu['extremite']}")
    parts.append(f"nœud {lieu['noeud_med']}")
    x, y, z = lieu["coordonnees_m"]
    axis = fr.family.axis
    if axis is not None:
        value = {"X": x, "Y": y, "Z": z}[axis]
        cote = f"{axis} = {number(value, 3)}"
    else:
        cote = f"X = {number(x, 3)} ; Y = {number(y, 3)} ; Z = {number(z, 3)}"
    return ", ".join(parts), cote


def write_export(
    ctx: ProjectContext,
    summary: EngineeringSummarySection,
    fr: FamilyRows,
    combinations: list[GenericCombination],
    envelopes: dict[str, StateEnvelope],
    sec: SectionRows,
    plane: BendingPlane,
    med_sha256: str | None,
) -> tuple[str, list[ExportLine]]:
    """The text of one file (with its BOM) and its lines."""
    export = sec.section.bending_export
    assert isinstance(export, BendingExport)
    lines, left_out = export_table(summary, fr, combinations, envelopes, sec, plane)
    h, h_src = _length(ctx, export.h, "m")
    b, b_src = _length(ctx, export.b, "m")
    ds, ds_src = _length(ctx, export.ds, "m")
    di, di_src = _length(ctx, export.di, "m")
    if plane.rotated:
        h, b, h_src, b_src = (
            b,
            h,
            b_src + " (section tournée)",
            h_src + " (section tournée)",
        )
    cnom, cnom_src = _length(ctx, export.cnom, "mm")
    concrete, concrete_src = _text(ctx, export.concrete)
    steel, steel_src = _text(ctx, export.steel)
    exposure, exposure_src = _text(ctx, export.exposure)
    sign = moment_sign(plane)
    raw_moment = "√(MFY² + MFZ²)" if plane.moment == "resultante" else plane.moment
    buffer = io.StringIO()
    w = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    w.writerow(["Section de dimensionnement", sec.section.label, sec.section.name])
    w.writerow(["Projet", ctx.declaration.name, ""])
    w.writerow(["Plan de flexion", plane.label, raw_moment])
    w.writerow(["Type de section", export.section_type, ""])
    w.writerow(["h (m)", number(h, 2), h_src])
    w.writerow(["b (m)", number(b, 2), b_src])
    w.writerow(["ds (m)", number(ds, 3), ds_src])
    w.writerow(["di (m)", number(di, 3), di_src])
    w.writerow(["Classe de béton", concrete, concrete_src])
    w.writerow(["Acier", steel, steel_src])
    w.writerow(["Classe d'exposition", exposure, exposure_src])
    w.writerow(["cnom (mm)", number(cnom, 0), cnom_src])
    if export.per_metre:
        w.writerow(
            ["Largeur", "b = 1,00 m : efforts par mètre de largeur (kN/m, kN.m/m)", ""]
        )
    if export.equivalence:
        w.writerow(["Équivalence", export.equivalence, ""])
    normal = _NORMAL[plane.moment]
    w.writerow(
        [
            "Convention N",
            f"N > 0 en compression : N = −{normal} de Code_Aster (Code_Aster : N > 0 "
            "en traction, R3.08.01)",
            "",
        ]
    )
    if plane.moment == "resultante":
        w.writerow(
            [
                "Convention M",
                "M = √(MFY² + MFZ²) ≥ 0 (section circulaire : pas de fibre supérieure "
                "propre)",
                "",
            ]
        )
        w.writerow(
            [
                "Avertissement",
                "section circulaire en flexion déviée : le moment résultant est "
                "exporté ; le logiciel traite une flexion plane ; « M min » sans objet",
                "",
            ]
        )
    else:
        w.writerow(
            [
                "Convention M",
                f"M > 0 comprime la fibre supérieure ({plane.top_fibre}) : "
                f"M = {'−' if sign < 0 else '+'}{plane.moment} de Code_Aster",
                "MFY = ∫z·σxx dS, MFZ = −∫y·σxx dS (R3.08.01) ; MXX > 0 tend la face "
                "supérieure (CA-045)",
            ]
        )
    for text in left_out:
        w.writerow(["État limite non exporté", text, ""])
    if fr.family.caveat:
        w.writerow(["Réserve de la famille", fr.family.caveat, ""])
    if sec.section.caveat:
        w.writerow(["Limite de la lecture", sec.section.caveat, ""])
    for note in sec.notes:
        w.writerow(["Lecture", note, ""])
    w.writerow([])
    v_column = (
        V_RES if plane.moment == "resultante" else SHEAR_OF_MOMENT.get(plane.moment, "")
    )
    raw_columns = ["MFY", "MFZ"] if plane.moment == "resultante" else [plane.moment]
    unit_m = "kN.m/m" if export.per_metre else "kN.m"
    unit_n = "kN/m" if export.per_metre else "kN"
    w.writerow(
        [
            "N°",
            "Type",
            f"N ({unit_n})",
            f"M ({unit_m})",
            "",
            "Cas dimensionnant",
            "Combinaison",
            "Position mobile",
            "Lieu",
            "Cote (m)",
            f"V concomitant ({unit_n})",
            *[f"{c} brut Code_Aster ({unit_m})" for c in raw_columns],
            f"{normal} brut Code_Aster ({unit_n})",
            "Repère des valeurs brutes",
        ]
    )
    for number_, line in enumerate(lines, 1):
        torsor = line.entry["torseur_si"]
        place, cote = _place(fr, line.entry)
        w.writerow(
            [
                number_,
                line.type_label,
                number(line.n_kn),
                number(line.m_knm),
                "",
                line.case,
                line.entry["combinaison"],
                line.entry["position_mobile"] or "",
                place,
                cote,
                number(torsor[v_column] * 1.0e-3) if v_column in torsor else "",
                *[number(torsor[c] * 1.0e-3) for c in raw_columns],
                number(torsor[normal] * 1.0e-3),
                fr.info.convention,
            ]
        )
    w.writerow([])
    w.writerow(["Empreinte du MED source (resultats.med, SHA-256)", med_sha256 or ""])
    return "﻿" + buffer.getvalue(), lines


def file_name(section: str, plane: BendingPlane, planes: int) -> str:
    if planes == 1:
        return f"{section}.csv"
    suffix = "RES" if plane.moment == "resultante" else plane.moment
    return f"{section}_{suffix}.csv"


__all__ = [
    "TYPE_ORDER",
    "ExportLine",
    "export_table",
    "file_name",
    "moment_sign",
    "number",
    "write_export",
]
