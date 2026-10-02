"""2D reinforcement of a plate by `CALC_FERRAILLAGE` (lot 43).

The 1D scheme (`aster_expert.ferraillage.poutre`, `ssll13*`) rebuilds a synthetic
beam and runs a separate `.comm` on combined forces. A plate is designed where its
forces are: on the combined results of the project's own `.comm`, which the
project's generator writes (one `MECA_STATIQUE` per combination of
`aster_expert.combinaisons.enumeration`). This module gives the generator the
commands, and the `ferraillage` step the reading and the checks:

- `plate_rebar_block`: `CALC_FERRAILLAGE` (`TYPE_STRUCTURE='2D'`, `EC2`, `Pa`) on
  each combination of a declared family, then the tables read back: densities of
  every cell of the plate (`FERR_ELEM`) and generalized forces of the cells around
  the check node (`EFGE_ELNO`) -- the command reads `EFGE_ELNO` (U4.81.42, « But »),
  which the generator must have computed;
- `check_group_block`: the cells around the check node (`DEFI_GROUP`,
  `OPTION='APPUI'`);
- `analyze_plate`: maxima of each density, the independent check of the ULS
  densities around the check node with `aster_expert.rebar` (a 1 m strip in each
  direction, `MXY` ignored: exact only where `MXY` vanishes, which the report
  shows), the minimum areas of EN 1992-1-1 (9.2.1.1, 7.3.2) and the envelope.

Known facts used (base `connaissances/`): `MXX > 0` stretches the upper face
(`DNSXS`, CA-045) -- the upper face is the side of the cell normal; under `MXX`
alone the 2D densities are those of a 1 m strip (CA-045); `FERR_MIN='EC2'` is only
right in `MPa` (CA-041): it is not used here, the minima are computed by the
module. How `CALC_FERRAILLAGE` reduces the nodal values of `EFGE_ELNO` to one
density per cell is not documented (U4.81.42, R7.04.05): the check compares the
module at the mean of the cell's nodes and at each node, and says which matches.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aster_expert.combinaisons.enumeration import Combination, enumerate_combinations
from aster_expert.ferraillage.unites import check_ferr_min_unit
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import RebarFamily, RebarPlate
from aster_expert.projet.errors import ProjectError
from aster_expert.rebar.minimum import (
    as_min_crack_control,
    as_min_flexure,
    size_factor_k,
)
from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.ultimate import design_ultimate

DENSITIES = ("DNSXI", "DNSXS", "DNSYI", "DNSYS")
FORCES = ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY")
TABLE_FORMAT_R = "E20.12"
CHECK_GROUP_SUFFIX = "_V"
"""Cells around the check node: `<check_node>_V` (`DEFI_GROUP`, `OPTION='APPUI'`)."""
RELATIVE_TOLERANCE = 1.0e-6
"""Independent check: module vs `CALC_FERRAILLAGE`, relative (CLAUDE.md, a quantity
the theory reproduces exactly)."""
ABSOLUTE_FLOOR = 1.0e-12
"""m2/m: below, both densities count as zero."""


@dataclass(frozen=True)
class PlateValues:
    """The plate's numbers, resolved and converted to the model units (m, Pa)."""

    thickness: float
    cover: float
    fck: float
    fyk: float
    fctm: float
    eys: float
    alpha_cc: float
    sigs_els: float
    sigc_els: float
    sigc_els_qp: float
    alpha_e: float
    kt: float
    wk: float
    phi: float


def plate_values(ctx: ProjectContext, plate: RebarPlate) -> PlateValues:
    n = ctx.number
    mpa = 1.0e6
    fyk = n(plate.fyk_mpa, unit="MPa") * mpa
    return PlateValues(
        thickness=n(plate.thickness_m, unit="m"),
        cover=n(plate.cover_mm, unit="mm") / 1000.0,
        fck=n(plate.fck_mpa, unit="MPa") * mpa,
        fyk=fyk,
        fctm=n(plate.fctm_mpa, unit="MPa") * mpa,
        eys=n(plate.eys_mpa, unit="MPa") * mpa,
        alpha_cc=n(plate.alpha_cc),
        sigs_els=n(plate.sigma_s_ratio) * fyk,
        sigc_els=n(plate.sigma_c_els_mpa, unit="MPa") * mpa,
        sigc_els_qp=n(plate.sigma_c_els_qp_mpa, unit="MPa") * mpa,
        alpha_e=n(plate.alpha_e),
        kt=n(plate.kt),
        wk=n(plate.wk_mm, unit="mm") / 1000.0,
        phi=n(plate.phi_mm, unit="mm") / 1000.0,
    )


def rebar_combinations(
    ctx: ProjectContext, plate: RebarPlate
) -> list[tuple[int, Combination, RebarFamily]]:
    """(index, combination, family) of every combination whose family the plate
    declares, numbered from 1 in the enumeration order (table titles)."""
    section = ctx.declaration.combinations
    if section is None:
        message = "ferraillage 2D : le projet ne déclare pas de combinaisons"
        raise ProjectError(message)
    families = {f.family: f for f in plate.families}
    out: list[tuple[int, Combination, RebarFamily]] = []
    for combination in enumerate_combinations(section, ctx.number):
        family = families.get(combination.family)
        if family is not None:
            out.append((len(out) + 1, combination, family))
    if not out:
        message = (
            f"ferraillage 2D de {plate.group} : aucune combinaison des familles "
            f"{sorted(families)}"
        )
        raise ProjectError(message)
    return out


def ferr_title(index: int, prefix: str = "") -> str:
    return f"{prefix}FER{index:02d}"


def efge_title(index: int, prefix: str = "") -> str:
    return f"{prefix}EFG{index:02d}"


def _r(value: float) -> str:
    return repr(float(value))


def check_group_block(plate: RebarPlate, mesh: str) -> str:
    """The cells having at least one node in the check node group."""
    return f"""
{mesh} = DEFI_GROUP(
    reuse={mesh},
    MAILLAGE={mesh},
    CREA_GROUP_MA=_F(
        NOM="{plate.check_node}{CHECK_GROUP_SUFFIX}",
        OPTION="APPUI",
        GROUP_NO="{plate.check_node}",
        TYPE_APPUI="AU_MOINS_UN",
    ),
)
"""


def _affe(plate: RebarPlate, v: PlateValues, family: RebarFamily) -> str:
    lines = [
        f'GROUP_MA="{plate.group}"',
        'TYPE_STRUCTURE="2D"',
        f"C_INF={_r(v.cover)}",
        f"C_SUP={_r(v.cover)}",
        f"FCK={_r(v.fck)}",
        f"FYK={_r(v.fyk)}",
        f"EYS={_r(v.eys)}",
        # Écrit explicitement : la valeur par défaut du catalogue est 0,85.
        f"ALPHA_CC={_r(v.alpha_cc)}",
    ]
    if family.type_comb == "ELU":
        assert family.gamma_c is not None
        assert family.gamma_s is not None
        lines += [f"GAMMA_C={_r(family.gamma_c)}", f"GAMMA_S={_r(family.gamma_s)}"]
    elif family.type_comb == "ELS":
        lines += [
            f"SIGS_ELS={_r(v.sigs_els)}",
            f"SIGC_INF_ELS={_r(v.sigc_els)}",
            f"SIGC_SUP_ELS={_r(v.sigc_els)}",
            f"ALPHA_E={_r(v.alpha_e)}",
        ]
    else:
        lines += [
            f"SIGC_ELS_QP={_r(v.sigc_els_qp)}",
            f"ALPHA_E={_r(v.alpha_e)}",
            f"KT={_r(v.kt)}",
            f"WMAX_INF={_r(v.wk)}",
            f"WMAX_SUP={_r(v.wk)}",
            f"PHI_INF_X={_r(v.phi)}",
            f"PHI_SUP_X={_r(v.phi)}",
            f"PHI_INF_Y={_r(v.phi)}",
            f"PHI_SUP_Y={_r(v.phi)}",
        ]
    body = ",\n            ".join(lines)
    return f"""_F(
            {body},
        )"""


def plate_rebar_block(
    ctx: ProjectContext,
    plate: RebarPlate,
    *,
    result_of: dict[str, str],
    cara: str,
    sigc_els_override: float | None = None,
    type_combs: frozenset[str] | None = None,
    prefix: str = "",
) -> str:
    """`CALC_FERRAILLAGE` and the read-back tables for every combination of a
    declared family. `result_of` maps a combination name to its result concept
    (on which `EFGE_ELNO` is computed). `sigc_els_override` (Pa) replaces
    `SIGC_*_ELS`: the sensitivity run of a limit that must not be active;
    `type_combs` restricts the families written and `prefix` marks the titles of
    such a second run (`S` -> `SFER02`)."""
    v = plate_values(ctx, plate)
    if sigc_els_override is not None:
        v = PlateValues(**{**v.__dict__, "sigc_els": sigc_els_override})
    blocks = []
    for index, combination, family in rebar_combinations(ctx, plate):
        if type_combs is not None and family.type_comb not in type_combs:
            continue
        result = result_of[combination.name]
        ferr, efge = ferr_title(index, prefix), efge_title(index, prefix)
        blocks.append(f"""
# {plate.label} : {combination.name} ({combination.family}, TYPE_COMB={family.type_comb})
{result} = CALC_FERRAILLAGE(
    reuse={result},
    RESULTAT={result},
    CARA_ELEM={cara},
    CODIFICATION="EC2",
    TYPE_COMB="{family.type_comb}",
    UNITE_CONTRAINTE="Pa",
    AFFE=({_affe(plate, v, family)},),
)
T_{ferr} = CREA_TABLE(
    RESU=_F(
        RESULTAT={result},
        NOM_CHAM="FERR_ELEM",
        TOUT_ORDRE="OUI",
        NOM_CMP={DENSITIES!r},
        GROUP_MA="{plate.group}",
    )
)
IMPR_TABLE(TABLE=T_{ferr}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{ferr}")
T_{efge} = CREA_TABLE(
    RESU=_F(
        RESULTAT={result},
        NOM_CHAM="EFGE_ELNO",
        TOUT_ORDRE="OUI",
        NOM_CMP={FORCES!r},
        GROUP_MA="{plate.check_node}{CHECK_GROUP_SUFFIX}",
    )
)
IMPR_TABLE(TABLE=T_{efge}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}", TITRE="{efge}")
""")
    text = "".join(blocks)
    check_ferr_min_unit(text)
    return text


# --- reading -----------------------------------------------------------------


def titled_table(text: str, title: str) -> list[dict[str, str]]:
    """Rows of the `IMPR_TABLE` printed with `TITRE=title` (marker
    `##<title>ASTER ...`), as `{column: cell}`."""
    marker = re.compile(rf"^##{re.escape(title)}ASTER\b")
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if marker.match(ln)), None)
    if start is None:
        message = f"table {title} absente du listing"
        raise ProjectError(message)
    header = lines[start + 1].split()
    rows = []
    for line in lines[start + 2 :]:
        if not line.strip() or line.startswith("#"):
            break
        cells = line.split()
        if len(cells) != len(header):
            message = f"table {title} : ligne de {len(cells)} cellules pour {len(header)} colonnes"
            raise ProjectError(message)
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def _strip_design(
    v: PlateValues, family: RebarFamily, n_tension: float, moment: float
) -> tuple[float, float]:
    """(upper, lower) densities of a 1 m strip, m2/m: `moment` > 0 stretches the
    upper face (CA-045), the module's positive face."""
    assert family.gamma_c is not None
    assert family.gamma_s is not None
    design = design_ultimate(
        Rectangle(width=1.0, depth=v.thickness, cover_pos=v.cover, cover_neg=v.cover),
        Concrete(fck=v.fck / 1e6, gamma_c=family.gamma_c, alpha_cc=v.alpha_cc),
        Steel(fyk=v.fyk / 1e6, es=v.eys / 1e6, gamma_s=family.gamma_s),
        n_tension / 1e6,
        moment / 1e6,
    )
    return design.as_pos, design.as_neg


def _densities(
    v: PlateValues, family: RebarFamily, forces: dict[str, float]
) -> dict[str, float]:
    xs, xi = _strip_design(v, family, forces["NXX"], forces["MXX"])
    ys, yi = _strip_design(v, family, forces["NYY"], forces["MYY"])
    return {"DNSXI": xi, "DNSXS": xs, "DNSYI": yi, "DNSYS": ys}


def _gap(a: float, b: float) -> float:
    if max(abs(a), abs(b)) <= ABSOLUTE_FLOOR:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b))


def minimum_areas(v: PlateValues) -> dict[str, float]:
    """EN 1992-1-1 minima per metre (m2/m), bending: 9.2.1.1 (9.1N) and 7.3.2
    (7.1) with `kc = 0,4`, `k` of 7.3.2(2), `fct,eff = fctm`, `Act = b h / 2`,
    `sigma_s = fyk`; distribution steel >= 20 % of the main steel (9.3.1.1(2))
    is a ratio, reported, not an area."""
    d = v.thickness - v.cover
    flexure = as_min_flexure(1.0, d, v.fctm / 1e6, v.fyk / 1e6)
    crack = as_min_crack_control(
        kc=0.4,
        k=size_factor_k(v.thickness),
        fct_eff=v.fctm / 1e6,
        act=1.0 * v.thickness / 2.0,
        sigma_s=v.fyk / 1e6,
    )
    return {
        "d_m": d,
        "as_min_9_2_1_1_m2_per_m": flexure,
        "as_min_7_3_2_m2_per_m": crack,
        "as_min_m2_per_m": max(flexure, crack),
        "repartition_min_ratio_9_3_1_1": 0.2,
    }


def analyze_plate(
    ctx: ProjectContext, plate: RebarPlate, mess_path: Path, out_dir: Path
) -> dict[str, Any]:
    """Read the tables of `plate_rebar_block` in the listing, check the ULS
    densities around the check node, write `ferraillage_<group>.json/.md`."""
    text = mess_path.read_text(encoding="utf-8", errors="replace")
    v = plate_values(ctx, plate)
    minima = minimum_areas(v)
    combos: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    envelope = dict.fromkeys(DENSITIES, 0.0)
    for index, combination, family in rebar_combinations(ctx, plate):
        rows = titled_table(text, ferr_title(index))
        by_cell = {r["MAILLE"]: {c: float(r[c]) for c in DENSITIES} for r in rows}
        maxima: dict[str, tuple[str, dict[str, float]]] = {}
        for c in DENSITIES:
            cell = max(by_cell, key=lambda name, c=c: by_cell[name][c])  # type: ignore[misc]
            maxima[c] = (cell, by_cell[cell])
        if family.type_comb != "ELS":
            # Envelope of the needs: ULS and crack control (ELS_QP); the
            # characteristic ELS only limits stresses (reported per combination).
            for c in DENSITIES:
                envelope[c] = max(envelope[c], maxima[c][1][c])
        combos.append(
            {
                "index": index,
                "combinaison": combination.name,
                "famille": combination.family,
                "type_comb": family.type_comb,
                "coefficients": combination.coefficients,
                "mailles": len(by_cell),
                "max": {
                    c: {"maille": maxima[c][0], "m2_par_m": maxima[c][1][c]}
                    for c in DENSITIES
                },
            }
        )
        if family.type_comb != "ELU":
            continue
        efge = titled_table(text, efge_title(index))
        cells: dict[str, list[dict[str, float | str]]] = {}
        for r in efge:
            cells.setdefault(r["MAILLE"], []).append(
                {"noeud": r["NOEUD"], **{c: float(r[c]) for c in FORCES}}
            )
        for cell, nodes in sorted(cells.items(), key=lambda item: int(item[0])):
            mean = {c: sum(float(n[c]) for n in nodes) / len(nodes) for c in FORCES}
            module_mean = _densities(v, family, mean)
            per_node = {
                str(n["noeud"]): _densities(v, family, {c: float(n[c]) for c in FORCES})
                for n in nodes
            }
            aster = by_cell[cell]
            gap_mean = max(_gap(aster[c], module_mean[c]) for c in DENSITIES)
            gap_nodes = {
                node: max(_gap(aster[c], d[c]) for c in DENSITIES)
                for node, d in per_node.items()
            }
            checks.append(
                {
                    "combinaison": combination.name,
                    "maille": cell,
                    "efforts_moyens": mean,
                    "mxy_max_abs": max(abs(float(n["MXY"])) for n in nodes),
                    "code_aster": aster,
                    "module_moyenne_des_noeuds": module_mean,
                    "ecart_moyenne": gap_mean,
                    "ecarts_par_noeud": gap_nodes,
                    "reussite_moyenne": gap_mean <= RELATIVE_TOLERANCE,
                }
            )
    result = {
        "plaque": plate.group,
        "libelle": plate.label,
        "valeurs": v.__dict__,
        "minima_en_1992": minima,
        "enveloppe_besoins_elu_els_qp_m2_par_m": envelope,
        "enveloppe_avec_minimum_m2_par_m": {
            c: max(envelope[c], minima["as_min_m2_per_m"]) for c in DENSITIES
        },
        "combinaisons": combos,
        "controle_independant": {
            "noeud": plate.check_node,
            "tolerance_relative": RELATIVE_TOLERANCE,
            "mailles": checks,
            "reussites_moyenne": sum(1 for c in checks if c["reussite_moyenne"]),
            "comparaisons": len(checks),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"ferraillage_{plate.group}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / f"ferraillage_{plate.group}.md").write_text(
        render_plate(result), encoding="utf-8"
    )
    return result


def _cm2(x: float) -> str:
    return f"{x * 1e4:.3f}"


def render_plate(result: dict[str, Any]) -> str:
    lines = [
        f"# Ferraillage 2D -- {result['libelle']} ({result['plaque']})",
        "",
        "Densités de CALC_FERRAILLAGE (cm²/m), maximum sur les mailles par combinaison.",
        "Face « S » : côté de la normale des mailles (CA-045).",
        "",
        "| Combinaison | TYPE_COMB | DNSXI | DNSXS | DNSYI | DNSYS |",
        "|---|---|---|---|---|---|",
    ]
    for c in result["combinaisons"]:
        cells = " | ".join(_cm2(c["max"][d]["m2_par_m"]) for d in DENSITIES)
        lines.append(f"| {c['combinaison']} | {c['type_comb']} | {cells} |")
    m = result["minima_en_1992"]
    lines += [
        "",
        f"Minimum (cm²/m, d = {m['d_m']:.3f} m) : 9.2.1.1 {_cm2(m['as_min_9_2_1_1_m2_per_m'])} ; "
        f"7.3.2 {_cm2(m['as_min_7_3_2_m2_per_m'])} ; retenu {_cm2(m['as_min_m2_per_m'])} ; "
        "répartition ≥ 20 % des armatures principales (9.3.1.1(2)).",
        "",
        "| Enveloppe (ELU, ELS QP) | " + " | ".join(DENSITIES) + " |",
        "|---|---|---|---|---|",
        "| besoin | "
        + " | ".join(
            _cm2(result["enveloppe_besoins_elu_els_qp_m2_par_m"][d]) for d in DENSITIES
        )
        + " |",
        "| avec minimum | "
        + " | ".join(
            _cm2(result["enveloppe_avec_minimum_m2_par_m"][d]) for d in DENSITIES
        )
        + " |",
        "",
    ]
    chk = result["controle_independant"]
    lines += [
        f"## Contrôle indépendant autour du nœud {chk['noeud']} (ELU, module `aster_expert.rebar`)",
        "",
        f"{chk['reussites_moyenne']}/{chk['comparaisons']} mailles reproduites à "
        f"{chk['tolerance_relative']:g} près par la moyenne des efforts aux nœuds de la maille.",
        "",
        "| Combinaison | Maille | |MXY| max (N·m/m) | écart (moyenne) | écart min (un nœud) |",
        "|---|---|---|---|---|",
    ]
    for c in chk["mailles"]:
        best = (
            min(c["ecarts_par_noeud"].values()) if c["ecarts_par_noeud"] else math.nan
        )
        lines.append(
            f"| {c['combinaison']} | {c['maille']} | {c['mxy_max_abs']:.4g} | "
            f"{c['ecart_moyenne']:.3e} | {best:.3e} |"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "CHECK_GROUP_SUFFIX",
    "DENSITIES",
    "PlateValues",
    "analyze_plate",
    "check_group_block",
    "efge_title",
    "ferr_title",
    "minimum_areas",
    "plate_rebar_block",
    "plate_values",
    "rebar_combinations",
    "render_plate",
    "titled_table",
]
