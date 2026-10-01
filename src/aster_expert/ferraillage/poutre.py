"""Reinforcement of a 1D member by `CALC_FERRAILLAGE`, from the combined forces
of an executed project (lot 41, étape 2.4; method of the first project's lot 39).

`CALC_FERRAILLAGE` needs a Code_Aster result: it is built in the scheme of the
official test cases `ssll13*` -- one `SEG2` per section, the combined forces
imposed by `CREA_CHAMP/CART_SIEF_R`, `CREA_RESU` -- one instant per combination
of the families the declaration names. The synthetic cells are parallel to X
without `ORIENTATION`: same local frame as a member of axis X (x_l = X). The
sections are the element ends of the member (not averaged: the shear force jumps
at a support, an average would falsify it).

After the run, the areas are read from the `FERR_POUTRE` table, enveloped per
abscissa and family, and complemented outside Code_Aster by the independent EN
1992-1-1 module (`aster_expert.rebar`): minimum areas (9.2.1.1, 7.3.2 -- not
`FERR_MIN`, wrong in `Pa`, constat CA-041), shear and torsion (6.2, 6.3), and a
hand check of the ULS areas at the declared sections (1e-6 relative, pivots A
and B). No verdict of conformity: computed areas, under the fiche's hypotheses.

Every number comes from the declaration (`rebar.members`) and the data file;
the prose of the Markdown table and the figure, which name the project's faces
and decisions, come from the project's report extension.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aster_expert.combinaisons.efforts import load_cases
from aster_expert.combinaisons.enumeration import (
    Combination,
    combine,
    enumerate_combinations,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import RebarFamily, RebarMember
from aster_expert.projet.errors import ProjectError
from aster_expert.rebar.biaxial import design_biaxial
from aster_expert.rebar.minimum import (
    as_min_crack_control,
    as_min_flexure,
    reference_bar_diameter,
    rho_w_min,
    size_factor_k,
    steel_stress_table_7_2n,
)
from aster_expert.rebar.model import Concrete, Rectangle, Steel
from aster_expert.rebar.shear import design_shear_torsion
from aster_expert.rebar.ultimate import design_ultimate

PRODUCER = "src/aster_expert/ferraillage/poutre.py"
"""Written in the header of the generated `.comm`."""
TABLE_TITLE = "FERR_POUTRE"
FACES = ("AYS", "AYI", "AZS", "AZI")
AREAS = (*FACES, "AST", "ATOT")
CASE_NAME = "poutre"
KC_BENDING = 0.4
"""kc of 7.3.2 (7.1) for pure bending."""


@dataclass(frozen=True)
class MemberValues:
    """The member's numbers, resolved from the declaration and the data (m, MPa;
    Pa where `CALC_FERRAILLAGE` is written in Pa)."""

    hy: float
    hz: float
    cover: float
    phi_mm: float
    wk_mm: float
    fck_mpa: float
    fyk_mpa: float
    eys_pa: float

    @property
    def fck_pa(self) -> float:
        return self.fck_mpa * 1e6

    @property
    def fyk_pa(self) -> float:
        return self.fyk_mpa * 1e6


def member_values(ctx: ProjectContext, member: RebarMember) -> MemberValues:
    return MemberValues(
        hy=ctx.number(member.hy, unit="m"),
        hz=ctx.number(member.hz, unit="m"),
        cover=ctx.number(member.cover, unit="m"),
        phi_mm=ctx.number(member.phi_mm, unit="mm"),
        wk_mm=ctx.number(member.wk_mm, unit="mm"),
        fck_mpa=ctx.number(member.fck_mpa),
        fyk_mpa=ctx.number(member.fyk_mpa),
        eys_pa=ctx.number(member.eys_pa),
    )


def _num(x: float) -> str:
    return repr(float(x))


def member_combinations(ctx: ProjectContext, member: RebarMember) -> list[Combination]:
    section = ctx.declaration.combinations
    if section is None:
        message = "ferraillage : le projet ne déclare pas de combinaisons"
        raise ProjectError(message)
    families = {f.family for f in member.families}
    return [
        c for c in enumerate_combinations(section, ctx.number) if c.family in families
    ]


def member_sections(
    ctx: ProjectContext, mess_path: Path
) -> tuple[list[dict[str, float]], dict[str, list[dict[str, float]]]]:
    """The (element, node) rows of the member, in the order of the tables, and
    the rows of each elementary case (same order, checked)."""
    section = ctx.declaration.combinations
    if section is None or section.forces is None:
        message = "ferraillage : le projet ne déclare pas d'efforts d'éléments"
        raise ProjectError(message)
    forces = section.forces
    raw, _ = load_cases(mess_path, forces)
    reference = raw[forces.reference_case]
    for case in forces.cases:
        rows = raw[case]
        if len(rows) != len(reference) or any(
            (a["MAILLE"], a["NOEUD"]) != (b["MAILLE"], b["NOEUD"])
            for a, b in zip(rows, reference, strict=True)
        ):
            message = (
                f"table d'efforts du cas {case} : lignes différentes de la référence"
            )
            raise ProjectError(message)
    return reference, raw


def combined_row(
    raw: dict[str, list[dict[str, float]]],
    combination: Combination,
    index: int,
    components: tuple[str, ...],
) -> dict[str, float]:
    return {
        comp: combine(
            combination.coefficients,
            {case: raw[case][index][comp] for case in combination.coefficients},
        )
        for comp in components
    }


def _affe(member: RebarMember, v: MemberValues, family: RebarFamily) -> str:
    lines = [
        'TOUT="OUI"',
        'TYPE_STRUCTURE="1D"',
        *(f"{k}={_num(v.cover)}" for k in ("C_SUP_Y", "C_INF_Y", "C_SUP_Z", "C_INF_Z")),
        f"FYK={_num(v.fyk_pa)}",
        f"FCK={_num(v.fck_pa)}",
        f"EYS={_num(v.eys_pa)}",
        'TYPE_DIAGRAMME="B2"',
        f"ALPHA_CC={_num(member.alpha_cc)}",
    ]
    if family.type_comb == "ELU":
        if family.gamma_c is None or family.gamma_s is None:
            message = f"famille {family.family} (ELU) : gamma_c et gamma_s requis"
            raise ProjectError(message)
        lines += [f"GAMMA_S={_num(family.gamma_s)}", f"GAMMA_C={_num(family.gamma_c)}"]
    else:
        lines += [
            f"ALPHA_E={_num(member.alpha_e)}",
            f"SIGS_ELS={_num(member.sigma_s_ratio * v.fyk_pa)}",
            *(
                f"SIGC_{f}_ELS={_num(member.sigma_c_ratio * v.fck_pa)}"
                for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
            ),
        ]
    if family.type_comb == "ELS_QP":
        lines += [
            f"SIGC_ELS_QP={_num(member.sigma_c_qp_ratio * v.fck_pa)}",
            f"KT={_num(member.kt)}",
        ]
        lines += [
            f"WMAX_{f}={_num(v.wk_mm / 1000.0)}"
            for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
        ]
        lines += [
            f"PHI_{f}={_num(v.phi_mm / 1000.0)}"
            for f in ("INF_Y", "SUP_Y", "INF_Z", "SUP_Z")
        ]
    return "\n".join(f"            {line}," for line in lines)


def build_comm(
    member: RebarMember,
    v: MemberValues,
    rows: list[dict[str, float]],
    raw: dict[str, list[dict[str, float]]],
    combos: list[Combination],
    components: tuple[str, ...],
) -> str:
    fields = []
    cmp_list = ", ".join(f'"{c}"' for c in components)
    for i, combination in enumerate(combos, start=1):
        occurrences = []
        for k in range(len(rows)):
            values = combined_row(raw, combination, k, components)
            vale = ", ".join(_num(values[c]) for c in components)
            occurrences.append(
                f'        _F(GROUP_MA="S{k + 1:03d}", NOM_CMP=({cmp_list}), '
                f"VALE=({vale})),"
            )
        joined = "\n".join(occurrences)
        fields.append(
            f"""# instant {i} : {combination.name} ({combination.family})
CH{i:02d} = CREA_CHAMP(
    MAILLAGE=MA,
    OPERATION="AFFE",
    TYPE_CHAM="CART_SIEF_R",
    AFFE=(
{joined}
    ),
)
"""
        )
    affe = "\n".join(
        f'        _F(NOM_CHAM="EFGE_ELNO", CHAM_GD=CH{i:02d}, INST={float(i)}, '
        "MODELE=MODEL, CARA_ELEM=CARA),"
        for i in range(1, len(combos) + 1)
    )
    calls = []
    for family in member.families:
        insts = ", ".join(
            repr(float(i))
            for i, c in enumerate(combos, start=1)
            if c.family == family.family
        )
        calls.append(
            f"""# {family.family}
RESU = CALC_FERRAILLAGE(
    RESULTAT=RESU,
    CARA_ELEM=CARA,
    reuse=RESU,
    CODIFICATION="EC2",
    TYPE_COMB="{family.type_comb}",
    UNITE_CONTRAINTE="Pa",
    INST=({insts},),
    AFFE=(
        _F(
{_affe(member, v, family)}
        ),
    ),
)
"""
        )
    header = "".join(f"# {line}\n" for line in member.comm_header)
    return f"""{header}# Produit par {PRODUCER} -- ne pas éditer.

DEBUT(CODE="OUI")

MA = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)

MODEL = AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=_F(GROUP_MA="POUTRE", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"),
)

CARA = AFFE_CARA_ELEM(
    MODELE=MODEL,
    POUTRE=_F(
        CARA=("HY", "HZ"),
        GROUP_MA=("POUTRE",),
        SECTION="RECTANGLE",
        VALE=({_num(v.hy)}, {_num(v.hz)}),
    ),
)

{"".join(fields)}
RESU = CREA_RESU(
    OPERATION="AFFE",
    TYPE_RESU="EVOL_ELAS",
    AFFE=(
{affe}
    ),
)

{"".join(calls)}
T_FERR = CREA_TABLE(
    RESU=_F(
        RESULTAT=RESU,
        NOM_CHAM="FERR_ELEM",
        TOUT_ORDRE="OUI",
        NOM_CMP=("AYS", "AYI", "AZS", "AZI", "AST", "ATOT"),
        TOUT="OUI",
    )
)
IMPR_TABLE(TABLE=T_FERR, UNITE=6, FORMAT_R="E20.12", TITRE="{TABLE_TITLE}")

FIN()
"""


def mesh_text(member: RebarMember, count: int) -> str:
    """One SEG2 per section, own nodes, along X (1 m apart, 0,5 m long): the
    geometry carries no information, only the local frame (x_l = X) matters."""
    title = member.mesh_title
    lines = [f"% {title}", "TITRE", title, "FINSF", "", "COOR_3D"]
    for k in range(1, count + 1):
        lines.append(f"A{k:03d} {float(k):.12f} 0.000000000000 0.000000000000")
        lines.append(f"B{k:03d} {k + 0.5:.12f} 0.000000000000 0.000000000000")
    lines += ["FINSF", "", "SEG2"]
    lines += [f"M{k:03d} A{k:03d} B{k:03d}" for k in range(1, count + 1)]
    lines += ["FINSF", "", "GROUP_MA", "POUTRE"]
    lines += [f"  M{k:03d}" for k in range(1, count + 1)]
    lines += ["FINSF", ""]
    for k in range(1, count + 1):
        lines += ["GROUP_MA", f"S{k:03d}", f"  M{k:03d}", "FINSF", ""]
    lines += ["FIN", ""]
    return "\n".join(lines)


def export_text() -> str:
    return (
        "P time_limit 600\nP memory_limit 2048\nP ncpus 1\nP mpi_nbcpu 1\n"
        f"P mpi_nbnoeud 1\nF comm {CASE_NAME}.comm D 1\nF mail {CASE_NAME}.mail D 20\n"
    )


def prepare_member(
    ctx: ProjectContext, member: RebarMember, mess_path: Path, out_dir: Path
) -> Path:
    """Write the `CALC_FERRAILLAGE` case (`poutre.comm`, `.mail`, `.export`) and
    its inputs (`sections.csv`, `efforts.csv`); return the `.comm`."""
    section = ctx.declaration.combinations
    assert section is not None and section.forces is not None
    components = section.forces.components
    v = member_values(ctx, member)
    rows, raw = member_sections(ctx, mess_path)
    combos = member_combinations(ctx, member)
    out_dir.mkdir(parents=True, exist_ok=True)
    comm_path = out_dir / f"{CASE_NAME}.comm"
    comm_path.write_text(build_comm(member, v, rows, raw, combos, components), "utf-8")
    (out_dir / f"{CASE_NAME}.mail").write_text(mesh_text(member, len(rows)), "utf-8")
    (out_dir / f"{CASE_NAME}.export").write_text(export_text(), "utf-8")
    with (out_dir / "sections.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["section", "maille", "noeud", "x_m"])
        for k, row in enumerate(rows, start=1):
            writer.writerow(
                [f"S{k:03d}", int(row["MAILLE"]), int(row["NOEUD"]), row["COOR_X"]]
            )
    with (out_dir / "efforts.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["instant", "combinaison", "famille", "section", *components])
        for i, combination in enumerate(combos, start=1):
            for k in range(len(rows)):
                values = combined_row(raw, combination, k, components)
                writer.writerow(
                    [
                        i,
                        combination.name,
                        combination.family,
                        f"S{k + 1:03d}",
                        *(f"{values[c]:.12e}" for c in components),
                    ]
                )
    return comm_path


# --- after the run ---------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_table(mess: Path) -> dict[tuple[int, str], dict[str, float]]:
    """`{(instant, section): {AYS, ..., ATOT}}` from the `FERR_POUTRE` table."""
    lines = mess.read_text(encoding="utf-8").splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith(f"##{TABLE_TITLE}")), None
    )
    if start is None:
        message = f"table {TABLE_TITLE} absente du listing {mess}"
        raise ProjectError(message)
    header = lines[start + 1].split()
    out: dict[tuple[int, str], dict[str, float]] = {}
    for line in lines[start + 2 :]:
        if not line.strip() or line.startswith("#"):
            break
        cells = line.split()
        row = dict(zip(header, cells, strict=True))
        # The table prints the mesh cell number (1..n, the order of the mesh
        # file), not its name M001...
        section = f"S{int(row['MAILLE']):03d}"
        out[(round(float(row["INST"])), section)] = {a: float(row[a]) for a in AREAS}
    return out


def extract(mess: Path) -> str:
    lines = mess.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(f"##{TABLE_TITLE}"))
    end = start + 2
    while end < len(lines) and lines[end].strip() and not lines[end].startswith("#"):
        end += 1
    diag = [ln for ln in lines if "DIAGNOSTIC JOB" in ln]
    return "\n".join([*lines[start:end], "", *diag, ""])


def _gammas(member: RebarMember) -> dict[str, tuple[float, float]]:
    return {
        f.family: (f.gamma_c, f.gamma_s)  # type: ignore[misc]
        for f in member.families
        if f.type_comb == "ELU"
    }


def _materials(
    member: RebarMember, v: MemberValues, family: str
) -> tuple[Concrete, Steel]:
    gamma_c, gamma_s = _gammas(member)[family]
    return Concrete(fck=v.fck_mpa, gamma_c=gamma_c, alpha_cc=member.alpha_cc), Steel(
        fyk=v.fyk_mpa, gamma_s=gamma_s
    )


def hand_check(
    member: RebarMember,
    v: MemberValues,
    efforts: list[dict[str, str]],
    sections: dict[str, dict[str, str]],
    results: dict[tuple[int, str], dict[str, float]],
) -> list[dict[str, object]]:
    """Module vs `CALC_FERRAILLAGE` on every ULS combination at the check
    sections (all element ends meeting at each abscissa)."""
    gammas = _gammas(member)
    checks: list[dict[str, object]] = []
    for label, x in member.check_sections.items():
        names = [s for s, row in sections.items() if abs(float(row["x_m"]) - x) < 1e-9]
        for row in efforts:
            if row["section"] not in names or row["famille"] not in gammas:
                continue
            concrete, steel = _materials(member, v, row["famille"])
            n, mfy, mfz = (float(row[c]) / 1e6 for c in ("N", "MFY", "MFZ"))
            design = design_biaxial(v.hy, v.hz, v.cover, concrete, steel, n, mfy, mfz)
            pivots = (
                design_ultimate(
                    Rectangle(
                        width=v.hz, depth=v.hy, cover_pos=v.cover, cover_neg=v.cover
                    ),
                    concrete,
                    steel,
                    n,
                    mfz,
                ).pivot,
                design_ultimate(
                    Rectangle(
                        width=v.hy, depth=v.hz, cover_pos=v.cover, cover_neg=v.cover
                    ),
                    concrete,
                    steel,
                    n,
                    mfy,
                ).pivot,
            )
            ca = results[(int(row["instant"]), row["section"])]
            module = {
                "AYS": design.ays,
                "AYI": design.ayi,
                "AZS": design.azs,
                "AZI": design.azi,
            }
            deviations = {}
            for face in FACES:
                a, b = ca[face], module[face]
                if max(abs(a), abs(b)) <= 1e-12:
                    deviations[face] = 0.0
                else:
                    deviations[face] = abs(b - a) / max(abs(a), abs(b))
            in_scope = all(p in ("A", "B", "none") for p in pivots) and not any(
                p == "C" for p in pivots
            )
            checks.append(
                {
                    "section": label,
                    "section_code_aster": row["section"],
                    "maille_poutre": int(sections[row["section"]]["maille"]),
                    "noeud_poutre": int(sections[row["section"]]["noeud"]),
                    "combinaison": row["combinaison"],
                    "N_MN": n,
                    "MFY_MNm": mfy,
                    "MFZ_MNm": mfz,
                    "pivots_z_y": list(pivots),
                    "iterations_bresler": design.iterations,
                    "code_aster": {f: ca[f] for f in FACES},
                    "module": module,
                    "ecart_relatif_max": max(deviations.values()),
                    "dans_le_critere": in_scope,
                    "reussite": (max(deviations.values()) <= 1e-6)
                    if in_scope
                    else None,
                }
            )
    return checks


def minima(v: MemberValues) -> dict[str, dict[str, float | bool]]:
    """As,min per face: 9.2.1.1 (9.1N) and 7.3.2 (7.1) with sigma_s from Table 7.2N
    through (7.6N) (declared phi and wk, kc = 0,4 pure bending, h_cr = h/2)."""
    # fctm does not depend on gamma_c.
    concrete = Concrete(fck=v.fck_mpa, gamma_c=1.5)
    fctm = concrete.fctm
    out: dict[str, dict[str, float | bool]] = {}
    for faces, width, depth in (("AY", v.hz, v.hy), ("AZ", v.hy, v.hz)):
        d = depth - v.cover
        phi_star = reference_bar_diameter(
            v.phi_mm, fct_eff=fctm, kc=KC_BENDING, h_cr=depth / 2.0, h_minus_d=v.cover
        )
        sigma_s, bounded = steel_stress_table_7_2n(phi_star, v.wk_mm)
        act = width * depth / 2.0
        crack = as_min_crack_control(
            kc=KC_BENDING,
            k=size_factor_k(min(width, depth)),
            fct_eff=fctm,
            act=act,
            sigma_s=sigma_s,
        )
        out[faces] = {
            "b_m": width,
            "h_m": depth,
            "d_m": d,
            "as_min_9_2_1_1": as_min_flexure(width, d, fctm, v.fyk_mpa),
            "phi_star_mm": phi_star,
            "sigma_s_MPa": sigma_s,
            "sigma_s_borne_tableau": bounded,
            "act_m2": act,
            "as_min_7_3_2": crack,
        }
    return out


def shear_torsion(
    member: RebarMember,
    v: MemberValues,
    efforts: list[dict[str, str]],
    results: dict[tuple[int, str], dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Per section, envelope over the ULS combinations of the EN 1992-1-1 module:
    links for VY (+ MT), for VZ (+ MT), longitudinal torsion steel, crushing ratio."""
    gammas = _gammas(member)
    out: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "asw_s_y": 0.0,
            "asw_s_z": 0.0,
            "at_s": 0.0,
            "asl_t": 0.0,
            "bielle": 0.0,
        }
    )
    for row in efforts:
        if row["famille"] not in gammas:
            continue
        concrete, steel = _materials(member, v, row["famille"])
        n, vy, vz, mt = (float(row[c]) / 1e6 for c in ("N", "VY", "VZ", "MT"))
        ca = results[(int(row["instant"]), row["section"])]
        env = out[row["section"]]
        for key, width, depth, shear, as_l in (
            ("y", v.hz, v.hy, vy, max(ca["AYS"], ca["AYI"])),
            ("z", v.hy, v.hz, vz, max(ca["AZS"], ca["AZI"])),
        ):
            section = Rectangle(
                width=width, depth=depth, cover_pos=v.cover, cover_neg=v.cover
            )
            result = design_shear_torsion(
                section, concrete, steel, v_ed=shear, t_ed=mt, n_comp=-n, as_l=as_l
            )
            env[f"asw_s_{key}"] = max(env[f"asw_s_{key}"], result.asw_s)
            env["at_s"] = max(env["at_s"], result.at_s)
            env["asl_t"] = max(env["asl_t"], result.asl_torsion)
            env["bielle"] = max(env["bielle"], result.crushing_ratio)
    return out


@dataclass
class RebarResult:
    """What the report extension renders (Markdown, figure)."""

    member: RebarMember
    values: MemberValues
    families: tuple[str, ...]
    n_combinations: int
    xs: list[float]
    envelope: dict[tuple[float, str], dict[str, float]]
    all_env: dict[float, dict[str, float]]
    governing: dict[float, dict[str, str]]
    minima: dict[str, dict[str, float | bool]]
    shear_x: dict[float, dict[str, float]]
    rho_w: float
    summary: dict[str, Any] = field(default_factory=dict)


def analyze_member(
    ctx: ProjectContext,
    member: RebarMember,
    run_dir: Path,
    out_dir: Path,
) -> RebarResult:
    """Read the run of `poutre.comm` (checked identical to the generated one) and
    write `rapports/`, `ferraillage.csv`, `enveloppes.csv`, `controle_main.json`,
    `synthese.csv`, `resume.json`; the extension writes the rest."""
    v = member_values(ctx, member)
    families = tuple(f.family for f in member.families)
    executed = run_dir / f"{CASE_NAME}.comm"
    versioned = out_dir / f"{CASE_NAME}.comm"
    if (
        hashlib.sha256(executed.read_bytes()).hexdigest()
        != hashlib.sha256(versioned.read_bytes()).hexdigest()
    ):
        message = (
            f"le .comm exécuté ({executed}) diffère du .comm préparé ({versioned})"
        )
        raise ProjectError(message)
    mess = run_dir / "proc.0" / "fort.6"
    (out_dir / "rapports").mkdir(exist_ok=True)
    (out_dir / "rapports" / "mess_ferr_extrait.txt").write_text(extract(mess), "utf-8")
    results = parse_table(mess)
    sections = {r["section"]: r for r in _read_csv(out_dir / "sections.csv")}
    efforts = _read_csv(out_dir / "efforts.csv")
    by_instant = {int(r["instant"]): (r["combinaison"], r["famille"]) for r in efforts}
    n_combinations = len(by_instant)
    if not len(results) == len(efforts) == n_combinations * len(sections):
        message = (
            f"table {TABLE_TITLE} : {len(results)} lignes pour {len(efforts)} efforts "
            f"({n_combinations} combinaisons × {len(sections)} sections)"
        )
        raise ProjectError(message)

    with (out_dir / "ferraillage.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["instant", "combinaison", "famille", "section", "x_m", *AREAS])
        for (inst, sec), values in sorted(results.items()):
            combination, family = by_instant[inst]
            writer.writerow(
                [inst, combination, family, sec, sections[sec]["x_m"]]
                + [f"{values[a]:.12e}" for a in AREAS]
            )

    # Envelope per abscissa (all element ends at that X), family and area.
    xs = sorted({round(float(r["x_m"]), 6) for r in sections.values()})
    envelope: dict[tuple[float, str], dict[str, float]] = {}
    unresolved: list[tuple[int, str]] = []
    for (inst, sec), values in results.items():
        family = by_instant[inst][1]
        if any(values[a] < 0.0 for a in AREAS):
            unresolved.append((inst, sec))
        key = (round(float(sections[sec]["x_m"]), 6), family)
        current = envelope.setdefault(key, dict.fromkeys(AREAS, 0.0))
        for a in AREAS:
            current[a] = max(current[a], values[a])
    with (out_dir / "enveloppes.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["x_m", "famille", *AREAS])
        for x in xs:
            for family in families:
                values = envelope[(x, family)]
                writer.writerow([x, family] + [f"{values[a]:.12e}" for a in AREAS])

    mins = minima(v)
    checks = hand_check(member, v, efforts, sections, results)
    in_scope = [c for c in checks if c["dans_le_critere"]]
    failures = [c for c in in_scope if not c["reussite"]]
    worst = max((float(c["ecart_relatif_max"]) for c in in_scope), default=None)  # type: ignore[arg-type]
    (out_dir / "controle_main.json").write_text(
        json.dumps(
            {
                "critere": "1e-6 relatif (1e-12 m² absolu pour une aire nulle), "
                "pivots A et B, combinaisons ELU fondamentale et accidentelle",
                "nombre_de_comparaisons": len(checks),
                "dans_le_critere": len(in_scope),
                "echecs": len(failures),
                "ecart_relatif_max_dans_le_critere": worst,
                "comparaisons": checks,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    shear = shear_torsion(member, v, efforts, results)
    all_env: dict[float, dict[str, float]] = {}
    for x in xs:
        all_env[x] = {a: max(envelope[(x, f)][a] for f in families) for a in AREAS}

    def dominant(x: float, area: str) -> str:
        """The family whose envelope is the largest (the first one on a tie)."""
        return max(families, key=lambda f: envelope[(x, f)][area])

    governing: dict[float, dict[str, str]] = {
        x: {a: dominant(x, a) for a in FACES} for x in xs
    }
    shear_x: dict[float, dict[str, float]] = {}
    for sec, row in sections.items():
        x = round(float(row["x_m"]), 6)
        current = shear_x.setdefault(x, dict.fromkeys(shear[sec], 0.0))
        for k, value in shear[sec].items():
            current[k] = max(current[k], value)
    rho_w = rho_w_min(v.fck_mpa, v.fyk_mpa)
    bw_label = f"{v.hz:.2f}".replace(".", "_")
    header = [
        "x_m",
        *(f"{f}_calc_ferraillage" for f in FACES),
        *(f"{f}_famille" for f in FACES),
        "As_min_AY_9_2_1_1",
        "As_min_AY_7_3_2",
        "As_min_AZ_9_2_1_1",
        "As_min_AZ_7_3_2",
        *(f"{f}_retenu" for f in FACES),
        "AST_calc_ferraillage_m2_par_m",
        "Asw_s_VY_EN_m2_par_m",
        "Asw_s_VZ_EN_m2_par_m",
        "At_s_torsion_par_brin_EN_m2_par_m",
        f"Asw_s_min_9_2_2_bw_{bw_label}",
        "Asl_torsion_EN_m2",
        "critere_bielle_EN",
    ]
    rows = []
    for x in xs:
        env = all_env[x]
        retained = {
            f: max(
                env[f],
                float(mins[f[:2]]["as_min_9_2_1_1"]),
                float(mins[f[:2]]["as_min_7_3_2"]),
            )
            for f in FACES
        }
        s = shear_x[x]
        rows.append(
            [
                x,
                *(env[f] for f in FACES),
                *(governing[x][f] for f in FACES),
                mins["AY"]["as_min_9_2_1_1"],
                mins["AY"]["as_min_7_3_2"],
                mins["AZ"]["as_min_9_2_1_1"],
                mins["AZ"]["as_min_7_3_2"],
                *(retained[f] for f in FACES),
                env["AST"],
                s["asw_s_y"],
                s["asw_s_z"],
                s["at_s"],
                rho_w * v.hz,
                s["asl_t"],
                s["bielle"],
            ]
        )
    with (out_dir / "synthese.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for r in rows:
            writer.writerow(
                [f"{val:.6e}" if isinstance(val, float) else val for val in r]
            )
    summary = {
        "sections": len(sections),
        "instants": n_combinations,
        "aires_negatives_non_resolues": len(unresolved),
        "minima": mins,
        "controle_main": {
            "comparaisons": len(checks),
            "dans_le_critere": len(in_scope),
            "echecs": len(failures),
        },
        "max_par_face_toutes_familles": {
            f: max(all_env[x][f] for x in xs) for f in (*FACES, "AST")
        },
        "max_bielle": max(shear_x[x]["bielle"] for x in xs),
        "max_asl_torsion": max(shear_x[x]["asl_t"] for x in xs),
    }
    (out_dir / "resume.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    result = RebarResult(
        member=member,
        values=v,
        families=families,
        n_combinations=n_combinations,
        xs=xs,
        envelope=envelope,
        all_env=all_env,
        governing=governing,
        minima=mins,
        shear_x=shear_x,
        rho_w=rho_w,
        summary=summary,
    )
    if member.report is not None:
        ctx.extension(member.report)(ctx, result, out_dir)
    return result


__all__ = [
    "AREAS",
    "CASE_NAME",
    "FACES",
    "MemberValues",
    "RebarResult",
    "analyze_member",
    "build_comm",
    "extract",
    "hand_check",
    "member_combinations",
    "member_sections",
    "member_values",
    "mesh_text",
    "minima",
    "parse_table",
    "prepare_member",
    "shear_torsion",
]
