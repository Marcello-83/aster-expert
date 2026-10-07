# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""Generator of the `.comm` of the jetty ESTACADE-PIEUX-01 (lot 47).

Everything comes from the fiche (decisions E1 to E16 of MM, choices U1 to U6 of the
agent, findings K1 to K6) and from the data file, through `model_values`. Units m, N,
Pa, kg (U1). Blocks, each naming what it applies:

- mesh (MED, unit 20), normals of the slab oriented +Z (`ORIE_NORM_COQUE`, CA-028):
  MXX > 0 stretches the upper face (CA-045);
- wheel prints: X bands of each axle and Y bands of each pair of wheels
  (`CREA_GROUP_MA/BANDE`, `CRIT_NOEUD="TOUS"`), intersected with the lane (PAT-003,
  CA-029), so that each print is a union of whole cells;
- springs: one `CREA_POI1` and one `DISCRET` per stiffness class, every spring node in
  exactly one class (PAT-001, CA-020, CA-034), K_T_D_N (k, k, 0) in the global frame
  and a zero mass M_T_D_N because the model carries `PESANTEUR` (DIAG-004);
- DKT slab (E13), POU_D_T cap beams and piles (E13, CA-037), DIS_T springs; cap beams
  sharing the slab nodes at the mid-plane (E2), piles sharing the cap beam node (E3);
  no kinematic relation is dualised, so the pivots of LIAISON_SOLIDE (CA-032, DIAG-001)
  cannot arise; DZ = 0 at the pile tips only (E4), each blocked once;
- materials (E7, E10), sections: slab EPAIS, cap beam RECTANGLE (E2), piles CERCLE of
  the equivalent tube of each B2 segment (E3, CA-057);
- elementary cases PP, G2, UDL, TR, FR and the moving positions of TS and LM2 (E8, E9,
  E15, E16) by `MACRO_ELAS_MULT` in batches (CA-055, one factorisation per batch, no
  SIEF_ELGA stored: `OPTION="SANS"`), each batch written to the MED then destroyed;
  TE+ and TE- by `MECA_STATIQUE` with the temperature of CA-054 (E10);
- fields: EFGE_NOEU on the slab only (DIAG-011), EFGE_ELNO on the beams, DEPL, REAC_NODA;
- tables of the level D controls (titles of 16 characters at most, CTL-010, `E20.12`).

Variants of E13 (sensitivity only, never the reference): `dst` (DST slab) and
`pou_d_e_chevetres` (POU_D_E cap beams); of E19 (lot 47 bis): `chevetre_0p80` (cap
beam height 0.80 m, the rest unchanged). Mode `convergence`: two TS positions only;
mode `tr_essieu` (lot 47 bis): the positions of the sidewalk axle of E18 only (the
other cases of the combination 100 are those of the production run). Option
`tr_axle`: the production cases plus those positions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from aster_expert.projet.context import ProjectContext
from estacade_pieux_01.charges_mobiles import (
    MovingCase,
    all_cases,
    check_alignment,
    tr_axle_cases,
    ts_cases,
)
from estacade_pieux_01.donnees import ModelValues, model_values
from estacade_pieux_01.transcription import mixed_sections, with_deck_level

TABLE_FORMAT_R = "E20.12"
TITLE_MAX = 16
BAND_TOLERANCE = 1.0e-6
BATCH_SIZE = 25
STATIC_CASES = ("PP", "G2", "UDL", "TR", "FR")
THERMAL_CASES = ("TEP", "TEM")
HARNESS_MOVING = ("TSA_P00", "TSB_P00", "L2A_M00", "L2B_M00")
SYMMETRIC_CASES = ("PP", "G2", "UDL", "TR", "TEP", "TEM")
CONVERGENCE_CASES = ("TSA_M15", "TSA_M20")
"""TS axé centred at X = 8,10 (span between files 2 and 3) and X = 5,60 (file 2)."""
VARIANTS = (
    "reference",
    "dst",
    "pou_d_e_chevetres",
    "chevetre_0p80",
    "dst_chevetre_0p80",
)
DST_VARIANTS = ("dst", "dst_chevetre_0p80")
CAP_0P80_VARIANTS = ("chevetre_0p80", "dst_chevetre_0p80")
MODES = ("production", "convergence", "tr_essieu")
CAP_HEIGHT_E19 = 0.80
"""Cap beam height of the sensitivity variant of E19 (m); the reference is E2."""
PRINT_AREA = {"TS": "VOIE", "LM2": "VOIE", "TR": "TROTT"}
"""Group a print is intersected with: the lane, or the sidewalks (E18)."""


class GenerationError(ValueError):
    """A refusal of the generator."""


@dataclass(frozen=True)
class Options:
    mode: str = "production"
    """`production` (every case), `convergence` (CONVERGENCE_CASES only) or
    `tr_essieu` (the positions of the sidewalk axle of E18 only)."""
    variant: str = "reference"
    tr_axle: bool = False
    """Production mode: add the positions of the sidewalk axle of E18 (lot 47 bis)."""
    cell: float = 0.05
    """Mesh size of the slab, to check the print alignment."""
    mesh_size: float | None = None
    """Lot 47 ter (step 2): size of a coarse slab mesh (0.25 or 0.50 m) on which the
    prints cannot be unions of whole cells. The positions stay those of the
    production mesh (`cell`); each wheel is then applied as a uniform pressure on
    every cell it overlaps, equal to the wheel pressure times the overlapped
    fraction of that cell, so that the force on each cell, and the total load, are
    exact (`fractional_prints`)."""
    post: str | None = "FORCE"
    """MUMPS `POSTTRAITEMENTS` (iterative refinement), `None` for the default of
    Code_Aster. Lot 47: `FORCE` for every run of the jetty, because the finest mesh
    of the convergence series (1,8 million dof) stopped on `<F> <FACTOR_57>` (error
    2,08e-6 for RESI_RELA = 1e-6, DIAG-003) with the default; RESI_RELA itself is
    never relaxed by default, and every run of the lot uses the same solver settings."""
    resi_rela: float | None = None
    """MUMPS `RESI_RELA`, `None` for the default (1e-6). Lot 47: 1e-5 for the
    sensitivity variant `pou_d_e_chevetres` only, which stopped on FACTOR_57 (error
    2,81e-6) even with POSTTRAITEMENTS='FORCE' (DIAG-003: relaxed with a written
    reason, equilibrium checked on the 242 positions)."""
    mixed_plug: bool = False
    """Lot 47 quater, declared variant H1: steel + plug concrete section, homogenised
    in steel, from the head down to the bottom of the plug (`transcription`)."""
    deck_level: float | None = None
    """Lot 47 quater, declared variant H2: deck plane at this level (+1.50) instead of
    the mid-plane of B1; needs the mesh built for that level (`transcription`)."""


def _r(x: float) -> str:
    return repr(float(x))


def _title(text: str, seen: set[str]) -> str:
    if len(text) > TITLE_MAX:
        message = f"intitulé de table trop long ({len(text)} > {TITLE_MAX}) : {text}"
        raise GenerationError(message)
    if text in seen:
        message = f"intitulé de table en double : {text}"
        raise GenerationError(message)
    seen.add(text)
    return text


def _gn(text: str) -> str:
    if len(text) > 24:
        message = f"nom de groupe de plus de 24 caractères : {text}"
        raise GenerationError(message)
    return text


def spring_classes(v: ModelValues) -> dict[float, list[str]]:
    """Node groups of each stiffness (N/m): every spring node is in one level group,
    so in exactly one class (CA-034)."""
    classes: dict[float, list[str]] = {}
    for s in v.springs:
        classes.setdefault(s.k, []).append(s.group)
    return dict(sorted(classes.items()))


def class_group(k: float) -> str:
    return _gn(f"RESS_K{round(k / 1e3):05d}")


def x_band(x: float) -> str:
    return _gn(f"BX_{round(x * 1000):05d}")


def y_band(case: MovingCase) -> str:
    return _gn(f"BY_{case.model}_{case.transverse.upper()}")


def axle_group(case: MovingCase, x: float) -> str:
    return _gn(f"E{case.model[0]}{case.transverse[0].upper()}_{round(x * 1000):05d}")


def moving_cases(v: ModelValues, options: Options) -> tuple[MovingCase, ...]:
    if options.mode == "convergence":
        chosen = {c.name: c for c in ts_cases(v, "axe")}
        cases = tuple(chosen[n] for n in CONVERGENCE_CASES)
    elif options.mode == "tr_essieu":
        cases = tr_axle_cases(v)
    else:
        cases = all_cases(v, options.cell)
        if options.tr_axle:
            cases = (*cases, *tr_axle_cases(v))
    bad = check_alignment(cases, options.cell)
    if bad and options.mesh_size is None:
        message = f"empreintes non alignées sur le maillage : {bad[:3]}"
        raise GenerationError(message)
    return cases


def print_groups_block(cases: tuple[MovingCase, ...]) -> str:
    """X and Y bands, then the axle prints (intersections): two commands, a group is
    visible only after the command that creates it."""
    bands: dict[str, str] = {}
    prints: dict[str, tuple[str, str, str]] = {}
    united: set[str] = set()
    for case in cases:
        a0 = case.axles[0]
        yname = y_band(case)
        if yname not in bands:
            # The two wheels of an axle: two bands, united; a single wheel (E18):
            # one band, under the name of the union.
            single = len(a0.wheels_y) == 1
            for i, y in enumerate(a0.wheels_y):
                name = yname if single else f"{yname}{i}"
                bands[name] = (
                    f'_F(NOM="{name}", OPTION="BANDE", POINT=(0.0, {_r(y)}, 0.0), '
                    f"VECT_NORMALE=(0.0, 1.0, 0.0), DIST={_r(a0.half_y + BAND_TOLERANCE)}, "
                    'CRIT_NOEUD="TOUS"),'
                )
            if not single:
                bands[yname] = ""
                united.add(yname)
        for axle in case.axles:
            xname = x_band(axle.x) + {"TS": "", "LM2": "L", "TR": "T"}[case.model]
            if xname not in bands:
                bands[xname] = (
                    f'_F(NOM="{xname}", OPTION="BANDE", POINT=({_r(axle.x)}, 0.0, 0.0), '
                    f"VECT_NORMALE=(1.0, 0.0, 0.0), DIST={_r(axle.half_x + BAND_TOLERANCE)}, "
                    'CRIT_NOEUD="TOUS"),'
                )
            prints[axle_group(case, axle.x)] = (xname, yname, PRINT_AREA[case.model])
    band_lines = "\n        ".join(b for b in bands.values() if b)
    unions = sorted(united)
    union_lines = "\n        ".join(
        f'_F(NOM="{y}", UNION=("{y}0", "{y}1")),' for y in unions
    )
    print_lines = "\n        ".join(
        f'_F(NOM="{name}", INTERSEC=("{x}", "{y}", "{area}")),'
        for name, (x, y, area) in sorted(prints.items())
    )
    unions_block = (
        f"""MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=(
        {union_lines}
    ),
)
"""
        if unions
        else ""
    )
    sidewalk = (
        "# E18 : l'essieu de trottoir de la combinaison 100 est intersecté avec les\n"
        "# trottoirs (TROTT), une bande en Y par roue.\n"
        if any(area == "TROTT" for (_, _, area) in prints.values())
        else ""
    )
    return f"""
# Empreintes des roues (E15, PAT-003) : bandes en X (essieux) et en Y (roues), toutes
# les mailles dont tous les nœuds sont dans la bande (CRIT_NOEUD="TOUS"), puis
# intersection avec la voie : chaque empreinte est une réunion de mailles entières.
{sidewalk}MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_MA=(
        {band_lines}
    ),
)
{unions_block}MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_MA=(
        {print_lines}
    ),
)
"""


def pile_materials(v: ModelValues, options: Options) -> tuple[str, str]:
    """(definitions, AFFE_MATERIAU lines) of the pile steel. Reference: ACIER on PIEUX.
    H1 (lot 47 quater): one steel material per mixed segment, RHO = (γs·As + γc·Ac) /
    (g·A) so that the self-weight is that of the steel and of the plug concrete, and
    ACIER on the other segments; the segments cover each pile once (no overlap)."""
    if not options.mixed_plug:
        return "", '_F(GROUP_MA=("PIEUX",), MATER=ACIER),'
    mixed = mixed_sections(v)
    names = {m.name for m in mixed}
    defs = "".join(
        f"# H1 (lot 47 quater) : tronçon {m.name}, acier + béton du bouchon homogénéisés en acier,\n"
        f"# n = {m.ratio:.6g}, A = {m.area:.6g} m2, I = {m.inertia:.6g} m4.\n"
        f"ACIER_{m.name} = DEFI_MATERIAU(\n"
        f"    ELAS=_F(E={_r(v.e_steel)}, NU={_r(v.nu_steel)}, RHO={_r(m.density)})\n"
        ")\n"
        for m in mixed
    )
    plain = [f'"PIEU_{s.name}"' for s in v.sections if s.name not in names]
    lines = [f'_F(GROUP_MA=("PIEU_{m.name}",), MATER=ACIER_{m.name}),' for m in mixed]
    if plain:
        lines.append(f"_F(GROUP_MA=({', '.join(plain)},), MATER=ACIER),")
    return defs, "\n        ".join(lines)


def model_block(v: ModelValues, options: Options) -> str:
    slab = "DST" if options.variant in DST_VARIANTS else "DKT"
    cap = "POU_D_E" if options.variant == "pou_d_e_chevetres" else "POU_D_T"
    cap_height = (
        CAP_HEIGHT_E19 if options.variant in CAP_0P80_VARIANTS else v.cap_height
    )
    classes = spring_classes(v)
    poi1 = "\n        ".join(
        f'_F(NOM_GROUP_MA="{class_group(k)}", GROUP_NO=({", ".join(repr(g) for g in groups)},)),'
        for k, groups in classes.items()
    )
    springs = ", ".join(f'"{class_group(k)}"' for k in classes)
    discrets = "\n        ".join(
        f'_F(GROUP_MA="{class_group(k)}", CARA="K_T_D_N", REPERE="GLOBAL", '
        f"VALE=({_r(k)}, {_r(k)}, 0.0)),\n        "
        f'_F(GROUP_MA="{class_group(k)}", CARA="M_T_D_N", VALE=(0.0,)),'
        for k in classes
    )
    mixed = {m.name: m for m in mixed_sections(v)} if options.mixed_plug else {}
    piles = "\n        ".join(
        f'_F(GROUP_MA="PIEU_{s.name}", SECTION="CERCLE", CARA=("R", "EP"), '
        f"VALE=({_r(tube[0])}, {_r(tube[1])})),"
        for s in v.sections
        for tube in [
            mixed[s.name].equivalent_tube() if s.name in mixed else s.equivalent_tube()
        ]
    )
    steel_defs, steel_affe = pile_materials(v, options)
    return f"""
# Ressorts (B3, E5, E6) : une maille POI1 par nœud, une classe par raideur (CA-034).
MAILR = CREA_MAILLAGE(
    MAILLAGE=MAIL,
    CREA_POI1=(
        {poi1}
    ),
)

# E13 : dalle {slab}, chevêtres {cap}, pieux POU_D_T ; arêtes de rive en {slab} pour
# FORCE_ARETE (CA-056) ; ressorts DIS_T.
MODELE = AFFE_MODELE(
    MAILLAGE=MAILR,
    AFFE=(
        _F(GROUP_MA=("DALLE", "RIVE_YM", "RIVE_YP"), PHENOMENE="MECANIQUE", MODELISATION="{slab}"),
        _F(GROUP_MA=("CHEVETRES",), PHENOMENE="MECANIQUE", MODELISATION="{cap}"),
        _F(GROUP_MA=("PIEUX",), PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),
        _F(GROUP_MA=({springs},), PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),
    ),
)

# E7, E10 : béton Ecm = {v.e_concrete:.6g} Pa, ν = {v.nu_concrete}, RHO = γ / g ;
# acier {v.e_steel:.6g} Pa, ν = {v.nu_steel} ; α du béton (dalle et chevêtres).
BETON = DEFI_MATERIAU(
    ELAS=_F(E={_r(v.e_concrete)}, NU={_r(v.nu_concrete)}, RHO={_r(v.gamma_concrete / v.gravity)}, ALPHA={_r(v.alpha)})
)
ACIER = DEFI_MATERIAU(
    ELAS=_F(E={_r(v.e_steel)}, NU={_r(v.nu_steel)}, RHO={_r(v.gamma_steel / v.gravity)})
)
{steel_defs}CHMAT = AFFE_MATERIAU(
    MAILLAGE=MAILR,
    AFFE=(
        _F(GROUP_MA=("DALLE", "CHEVETRES"), MATER=BETON),
        {steel_affe}
    ),
)

# Sections : dalle EPAIS, x_l = X (ANGL_REP) ; chevêtre rectangle {v.cap_width} (selon X)
# × {cap_height} (selon Z), y_l = −X donc z_l vertical (E2{", E19" if cap_height != v.cap_height else ""}) ; pieux, tube équivalent
# à A et I de chaque tronçon de B2 (CA-057), y_l = X ; ressorts (k, k, 0), masse nulle
# (DIAG-004).
CARA = AFFE_CARA_ELEM(
    MODELE=MODELE,
    COQUE=_F(GROUP_MA="DALLE", EPAIS={_r(v.thickness)}, ANGL_REP=(0.0, 0.0)),
    POUTRE=(
        _F(GROUP_MA="CHEVETRES", SECTION="RECTANGLE", CARA=("HY", "HZ"), VALE=({_r(v.cap_width)}, {_r(cap_height)})),
        {piles}
    ),
    ORIENTATION=(
        _F(GROUP_MA="CHEVETRES", CARA="VECT_Y", VALE=(-1.0, 0.0, 0.0)),
        _F(GROUP_MA="PIEUX", CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),
    ),
    DISCRET=(
        {discrets}
    ),
)

# E4 : DZ = 0 en pointe, rotations libres ; aucune autre condition, aucune relation
# cinématique dualisée (DIAG-001).
CL = AFFE_CHAR_MECA(MODELE=MODELE, DDL_IMPO=_F(GROUP_NO="PIEDS", DZ=0.0))
"""


def static_loads_block(v: ModelValues) -> str:
    lane_area = v.length * (v.lane[1] - v.lane[0])
    fr = v.fr_total / lane_area
    return f"""
# B4, E7 : PP (pesanteur, toutes les mailles ; ressorts de masse nulle).
CH_PP = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE={_r(v.gravity)}, DIRECTION=(0.0, 0.0, -1.0)))
# G2 : trottoirs, voie, garde-corps sur chaque rive (FORCE_ARETE, CA-056).
CH_G2 = AFFE_CHAR_MECA(
    MODELE=MODELE,
    FORCE_COQUE=(
        _F(GROUP_MA="TROTT", FZ={_r(-v.g2_sidewalk)}),
        _F(GROUP_MA="VOIE", FZ={_r(-v.g2_lane)}),
    ),
    FORCE_ARETE=_F(GROUP_MA=("RIVE_YM", "RIVE_YP"), FZ={_r(-v.g2_guard)}),
)
CH_UDL = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="VOIE", FZ={_r(-v.udl)}))
CH_TR = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="TROTT", FZ={_r(-v.tr)}))
# E9 : {v.fr_total:.6g} N selon +X sur la voie ({lane_area:.6g} m²), dans le plan moyen.
CH_FR = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA="VOIE", FX={_r(fr)}))
"""


def moving_loads_block(cases: tuple[MovingCase, ...]) -> str:
    lines = []
    for case in cases:
        groups = ", ".join(f'"{axle_group(case, a.x)}"' for a in case.axles)
        lines.append(
            f"CH_{case.name} = AFFE_CHAR_MECA(MODELE=MODELE, "
            f"FORCE_COQUE=_F(GROUP_MA=({groups},), FZ={_r(-case.pressure)}))"
        )
    return (
        "\n# E8, E15, E16 : une charge par position (empreintes de B4 au plan moyen).\n"
        + "\n".join(lines)
        + "\n"
    )


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def print_area_bounds(
    v: ModelValues, case: MovingCase, y: float
) -> tuple[float, float]:
    """Y range of the group a print is intersected with (PRINT_AREA): the lane, or
    the sidewalk on the side of the wheel."""
    if case.model in ("TS", "LM2"):
        return v.lane
    return (v.lane[1], v.y_max) if y > 0 else (v.y_min, v.lane[0])


def fractional_prints(
    v: ModelValues,
    cases: tuple[MovingCase, ...],
    x_nodes: tuple[float, ...],
    y_nodes: tuple[float, ...],
) -> tuple[
    dict[tuple[int, int], tuple[float, float, float, float]],
    dict[str, dict[tuple[int, int], float]],
]:
    """Cells overlapped by the prints and, per case, the pressure (Pa) on each.

    The pressure of a cell is the wheel pressure times the overlapped area divided
    by the cell area: the force on each cell is exact, so is the total; two prints
    on one cell add up (one occurrence per cell and case, never two, so that no
    occurrence of FORCE_COQUE overrides another)."""
    cells: dict[tuple[int, int], tuple[float, float, float, float]] = {}
    loads: dict[str, dict[tuple[int, int], float]] = {}
    for case in cases:
        forces: dict[tuple[int, int], float] = {}
        applied = 0.0
        for axle in case.axles:
            x0, x1 = axle.bounds_x()
            for y in axle.wheels_y:
                ya, yb = print_area_bounds(v, case, y)
                y0, y1 = max(y - axle.half_y, ya), min(y + axle.half_y, yb)
                for i, (xa, xb) in enumerate(zip(x_nodes, x_nodes[1:], strict=False)):
                    ox = _overlap(x0, x1, xa, xb)
                    if ox <= 0.0:
                        continue
                    for j, (yc, yd) in enumerate(
                        zip(y_nodes, y_nodes[1:], strict=False)
                    ):
                        oy = _overlap(y0, y1, yc, yd)
                        if oy <= 0.0:
                            continue
                        cells[(i, j)] = (xa, xb, yc, yd)
                        force = case.pressure * ox * oy
                        forces[(i, j)] = forces.get((i, j), 0.0) + force
                        applied += force
        if abs(applied - case.total) > 1e-9 * case.total:
            message = (
                f"{case.name} : charge représentée {applied} N pour {case.total} N "
                "(empreinte hors de son groupe)"
            )
            raise GenerationError(message)
        loads[case.name] = {
            ij: f / ((cells[ij][1] - cells[ij][0]) * (cells[ij][3] - cells[ij][2]))
            for ij, f in forces.items()
        }
    return cells, loads


def cell_group(ij: tuple[int, int]) -> str:
    return _gn(f"Q{ij[0]:03d}_{ij[1]:02d}")


def fractional_groups_block(
    cells: dict[tuple[int, int], tuple[float, float, float, float]],
) -> str:
    """One group per overlapped cell: X band of its column, Y band of its row
    (`BANDE`, `CRIT_NOEUD="TOUS"`, PAT-003), intersected with DALLE (the bands also
    hold the SEG2 of the cap beams, piles and edges)."""
    columns = {i: (b[0], b[1]) for (i, _), b in cells.items()}
    rows = {j: (b[2], b[3]) for (_, j), b in cells.items()}
    bands = [
        f'_F(NOM="{_gn(f"CX_{i:03d}")}", OPTION="BANDE", POINT=({_r((a + b) / 2.0)}, 0.0, 0.0), '
        f"VECT_NORMALE=(1.0, 0.0, 0.0), DIST={_r((b - a) / 2.0 + BAND_TOLERANCE)}, "
        'CRIT_NOEUD="TOUS"),'
        for i, (a, b) in sorted(columns.items())
    ] + [
        f'_F(NOM="{_gn(f"CY_{j:02d}")}", OPTION="BANDE", POINT=(0.0, {_r((a + b) / 2.0)}, 0.0), '
        f"VECT_NORMALE=(0.0, 1.0, 0.0), DIST={_r((b - a) / 2.0 + BAND_TOLERANCE)}, "
        'CRIT_NOEUD="TOUS"),'
        for j, (a, b) in sorted(rows.items())
    ]
    inter = [
        f'_F(NOM="{cell_group(ij)}", INTERSEC=("CX_{ij[0]:03d}", "CY_{ij[1]:02d}", "DALLE")),'
        for ij in sorted(cells)
    ]
    band_lines = "\n        ".join(bands)
    inter_lines = "\n        ".join(inter)
    return f"""
# Lot 47 ter, maillage grossier : les empreintes ne sont plus des réunions de mailles
# entières. Une maille par groupe (bande de sa colonne en X, de sa rangée en Y,
# CRIT_NOEUD="TOUS", PAT-003, intersectées avec DALLE) ; chaque roue charge chaque
# maille qu'elle recouvre de sa pression × la fraction recouverte : force exacte par
# maille, charge totale exacte (contrôle de résultante des pointes).
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_MA=(
        {band_lines}
    ),
)
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_MA=(
        {inter_lines}
    ),
)
"""


def fractional_loads_block(loads: dict[str, dict[tuple[int, int], float]]) -> str:
    """One AFFE_CHAR_MECA per position; the cells of equal pressure share one
    occurrence of FORCE_COQUE."""
    lines = []
    for name, pressures in loads.items():
        by_value: dict[float, list[tuple[int, int]]] = {}
        for ij, p in sorted(pressures.items()):
            by_value.setdefault(float(f"{p:.12e}"), []).append(ij)
        occurrences = "\n        ".join(
            f"_F(GROUP_MA=({', '.join(repr(cell_group(ij)) for ij in ijs)},), FZ={_r(-p)}),"
            for p, ijs in sorted(by_value.items())
        )
        lines.append(
            f"CH_{name} = AFFE_CHAR_MECA(\n    MODELE=MODELE,\n    FORCE_COQUE=(\n"
            f"        {occurrences}\n    ),\n)"
        )
    return (
        "\n# E8, E15, E16, E18 : une charge par position, empreintes par fractions de\n"
        "# mailles (maillage grossier, lot 47 ter).\n" + "\n".join(lines) + "\n"
    )


def solver_keyword(options: Options) -> str:
    """The `SOLVEUR` keyword shared by every solve of a run (empty for the default)."""
    parts = []
    if options.post is not None:
        parts.append(f'POSTTRAITEMENTS="{options.post}"')
    if options.resi_rela is not None:
        parts.append(f"RESI_RELA={options.resi_rela!r}")
    if not parts:
        return ""
    return f', SOLVEUR=_F(METHODE="MUMPS", {", ".join(parts)})'


def thermal_block(v: ModelValues, options: Options) -> str:
    # The reference ran TE+ and TE- with the default solver (they succeeded); only a
    # relaxed RESI_RELA (variant pou_d_e_chevetres) is carried to them, which the
    # thermal solve of that variant needed (FACTOR_57, error 1,41e-6).
    solver = solver_keyword(options) if options.resi_rela is not None else ""
    _defs, steel_affe = pile_materials(v, options)
    out = []
    for name, sign in (("TEP", 1.0), ("TEM", -1.0)):
        dt = sign * v.delta_t
        out.append(
            f"""
# E10 : {name}, ΔT = {dt:+.4g} °C sur la dalle (PREP_VARC) et les chevêtres (TEMP), CA-054.
T_{name}_C = CREA_CHAMP(
    OPERATION="AFFE",
    TYPE_CHAM="NOEU_TEMP_R",
    MAILLAGE=MAILR,
    AFFE=_F(GROUP_MA="DALLE", NOM_CMP=("TEMP_MIL", "TEMP_INF", "TEMP_SUP"), VALE=({_r(dt)}, {_r(dt)}, {_r(dt)})),
)
R_{name}_C = CREA_RESU(OPERATION="AFFE", TYPE_RESU="EVOL_THER", AFFE=_F(NOM_CHAM="TEMP", CHAM_GD=T_{name}_C, INST=0.0))
P_{name}_C = CREA_RESU(
    OPERATION="PREP_VARC",
    TYPE_RESU="EVOL_THER",
    PREP_VARC=_F(MODELE=MODELE, CARA_ELEM=CARA, EVOL_THER=R_{name}_C, GROUP_MA="DALLE"),
)
T_{name}_P = CREA_CHAMP(
    OPERATION="AFFE",
    TYPE_CHAM="NOEU_TEMP_R",
    MAILLAGE=MAILR,
    AFFE=_F(GROUP_MA="CHEVETRES", NOM_CMP="TEMP", VALE={_r(dt)}),
)
M_{name} = AFFE_MATERIAU(
    MAILLAGE=MAILR,
    AFFE=(
        _F(GROUP_MA=("DALLE", "CHEVETRES"), MATER=BETON),
        {steel_affe}
    ),
    AFFE_VARC=(
        _F(GROUP_MA="DALLE", NOM_VARC="TEMP", EVOL=P_{name}_C, NOM_CHAM="TEMP", VALE_REF=0.0),
        _F(GROUP_MA="CHEVETRES", NOM_VARC="TEMP", CHAM_GD=T_{name}_P, VALE_REF=0.0),
    ),
)
{name} = MECA_STATIQUE(MODELE=MODELE, CHAM_MATER=M_{name}, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CL){solver})
"""
        )
    return "".join(out)


def _fields_and_output(resu: str, med_name: str) -> str:
    return f"""{resu} = CALC_CHAMP(reuse={resu}, RESULTAT={resu}, GROUP_MA="DALLE", CONTRAINTE=("EFGE_NOEU",))
{resu} = CALC_CHAMP(reuse={resu}, RESULTAT={resu}, GROUP_MA=("CHEVETRES", "PIEUX"), CONTRAINTE=("EFGE_ELNO",))
{resu} = CALC_CHAMP(reuse={resu}, RESULTAT={resu}, FORCE=("REAC_NODA",))
IMPR_RESU(
    FORMAT="MED",
    UNITE=80,
    RESU=(
        _F(RESULTAT={resu}, NOM_RESU_MED="{med_name}", NOM_CHAM="DEPL", NOM_CMP=("DX", "DY", "DZ"), CARA_ELEM=CARA),
        _F(RESULTAT={resu}, NOM_RESU_MED="{med_name}", NOM_CHAM="EFGE_NOEU", NOM_CMP=("NXX", "NYY", "MXX", "MYY", "MXY", "QX", "QY"), GROUP_MA="DALLE", CARA_ELEM=CARA),
        _F(RESULTAT={resu}, NOM_RESU_MED="{med_name}", NOM_CHAM="EFGE_ELNO", GROUP_MA=("CHEVETRES", "PIEUX"), CARA_ELEM=CARA),
    ),
)
"""


def _case_tables(resu: str, case: str, seen: set[str], *, by_name: bool) -> str:
    pick = f'NOM_CAS="{case}"' if by_name else 'TOUT_ORDRE="OUI"'
    out = f"""T_RP_{case} = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="{_title("RP_" + case, seen)}", RESULTAT={resu}, NOM_CHAM="REAC_NODA", {pick}, GROUP_NO=("PIEDS",), RESULTANTE=("DX", "DY", "DZ"))
)
IMPR_TABLE(TABLE=T_RP_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
T_DR_{case} = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="{_title("DR_" + case, seen)}", RESULTAT={resu}, NOM_CHAM="DEPL", {pick}, GROUP_NO=("RESSORTS",), NOM_CMP=("DX", "DY"))
)
IMPR_TABLE(TABLE=T_DR_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
"""
    if case in SYMMETRIC_CASES:
        out += f"""T_SY_{case} = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="{_title("SYMETRIE_" + case, seen)}", RESULTAT={resu}, NOM_CHAM="DEPL", {pick}, GROUP_NO=("SYM_NOEUDS",), NOM_CMP=("DX", "DY", "DZ"))
)
IMPR_TABLE(TABLE=T_SY_{case}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
"""
    return out


def batches(names: list[str]) -> list[list[str]]:
    return [names[i : i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]


def solve_block(
    names: list[str],
    harness: set[str],
    seen: set[str],
    post: str | None = None,
    resi_rela: float | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    out = []
    manifest = []
    options = []
    if post is not None:
        options.append(f'POSTTRAITEMENTS="{post}"')
    if resi_rela is not None:
        options.append(f"RESI_RELA={resi_rela!r}")
    solver = (
        ""
        if not options
        else f'\n    SOLVEUR=_F(METHODE="MUMPS", {", ".join(options)}),'
    )
    for i, batch in enumerate(batches(names), start=1):
        resu = f"MB{i:02d}"
        cases = "\n        ".join(
            f'_F(NOM_CAS="{n}", CHAR_MECA=CH_{n}, OPTION="SANS"),' for n in batch
        )
        tables = "".join(
            _case_tables(resu, n, seen, by_name=True) for n in batch if n in harness
        )
        all_rows = f"""T_RA_{resu} = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="{_title("RPIEDS_" + resu, seen)}", RESULTAT={resu}, NOM_CHAM="REAC_NODA", TOUT_ORDRE="OUI", GROUP_NO=("PIEDS",), RESULTANTE=("DX", "DY", "DZ"))
)
IMPR_TABLE(TABLE=T_RA_{resu}, UNITE=6, FORMAT_R="{TABLE_FORMAT_R}")
"""
        out.append(
            f"""
# Lot {i} : {len(batch)} cas, une factorisation (CA-055), sans SIEF_ELGA stocké.
{resu} = MACRO_ELAS_MULT(
    MODELE=MODELE,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    CHAR_MECA_GLOBAL=CL,
    CAS_CHARGE=(
        {cases}
    ),{solver}
)
{_fields_and_output(resu, resu)}{tables}{all_rows}DETRUIRE(NOM={resu})
"""
        )
        manifest.append({"resultat": resu, "cas": batch})
    return "".join(out), manifest


SYMMETRY_SOURCES = ("PIEUX", "CHEVETRES", "RIVE_YM", "RIVE_YP")


def groups_block() -> str:
    """Nodes of a symmetric set for CTL-006: one CREA_GROUP_NO per GROUP_MA, then
    their UNION (DIAG-010: several GROUP_MA in one occurrence stopped a later command
    on <F> <JEVEUX_10>, &&SSCGNO.LITMP2 -- reproduced by the first production run of
    this lot)."""
    singles = "\n        ".join(
        f'_F(GROUP_MA="{g}", NOM="{_gn("SYMN_" + g)}"),' for g in SYMMETRY_SOURCES
    )
    union = ", ".join(f'"SYMN_{g}"' for g in SYMMETRY_SOURCES)
    return f"""
# Ensemble symétrique de nœuds pour CTL-006 : un groupe par GROUP_MA puis UNION
# (DIAG-010).
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=(
        {singles}
    ),
)
MAIL = DEFI_GROUP(
    reuse=MAIL,
    MAILLAGE=MAIL,
    CREA_GROUP_NO=_F(UNION=({union},), NOM="SYM_NOEUDS"),
)
"""


def build_comm(
    ctx: ProjectContext, *, mesh_label: str, options: Options | None = None
) -> tuple[str, dict[str, Any]]:
    options = options or Options()
    if options.variant not in VARIANTS:
        message = f"variante inconnue : {options.variant} ({VARIANTS})"
        raise GenerationError(message)
    if options.mode not in MODES:
        message = f"mode inconnu : {options.mode} ({MODES})"
        raise GenerationError(message)
    v = model_values(ctx)
    if options.deck_level is not None:
        v = with_deck_level(v, options.deck_level)
    seen: set[str] = set()
    cases = moving_cases(v, options)
    if options.mesh_size is not None:
        from estacade_pieux_01.discretisation import JettyMesh  # noqa: PLC0415

        coarse = JettyMesh(v, options.mesh_size, exact=False)
        cells, frac = fractional_prints(v, cases, coarse.x_nodes(), coarse.y_nodes())
        prints_text = fractional_groups_block(cells)
        loads_text = fractional_loads_block(frac)
    else:
        prints_text = print_groups_block(cases)
        loads_text = moving_loads_block(cases)
    names = [c.name for c in cases]
    spring_union = ", ".join(f'"{s.group}"' for s in v.springs)
    production = options.mode == "production"
    statics = list(STATIC_CASES) if production else []
    harness = set(STATIC_CASES) | set(HARNESS_MOVING) if production else set()
    solve, manifest = solve_block(
        statics + names, harness, seen, options.post, options.resi_rela
    )
    thermal = ""
    if production:
        thermal = thermal_block(v, options)
        for name in THERMAL_CASES:
            thermal += _fields_and_output(name, name) + _case_tables(
                name, name, seen, by_name=False
            )
    header = (
        f"# Estacade ESTACADE-PIEUX-01 (lot 47) -- maillage {mesh_label}, mode {options.mode}, "
        f"variante {options.variant}.\n"
        + (
            "# Lot 47 quater, variante déclarée H1 : section mixte acier + béton du bouchon.\n"
            if options.mixed_plug
            else ""
        )
        + (
            f"# Lot 47 quater, variante déclarée H2 : plan du tablier à {options.deck_level}.\n"
            if options.deck_level is not None
            else ""
        )
        + (
            f"# Lot 47 ter : dalle de {options.mesh_size} m, empreintes par fractions de mailles.\n"
            if options.mesh_size is not None
            else ""
        )
        + "# Contre-calcul d'un modèle non validé. Généré par estacade_pieux_01.generation à\n"
        "# partir de la fiche (fiche/hypotheses_estacade_pieux_01.json) et des données\n"
        "# (donnees/estacade_pieux_01_model_data.yaml) : ne pas éditer. Unités m, N, Pa (U1).\n"
    )
    text = f"""{header}
DEBUT(CODE="OUI")

MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)

# CA-028, CA-045 : normales de la dalle +Z, MXX > 0 tend la face supérieure.
MAIL = MODI_MAILLAGE(
    reuse=MAIL,
    MAILLAGE=MAIL,
    ORIE_NORM_COQUE=_F(GROUP_MA=("DALLE",), VECT_NORM=(0.0, 0.0, 1.0), GROUP_NO="COIN_ABOUT"),
)
MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=_F(UNION=({spring_union},), NOM="RESSORTS"))
{groups_block() if production else ""}{prints_text}{model_block(v, options)}{static_loads_block(v) if production else ""}{loads_text}{solve}{thermal}
FIN()
"""
    report = {
        "comm_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "mode": options.mode,
        "variante": options.variant,
        "section_mixte_bouchon": options.mixed_plug,
        "plan_tablier": v.z_mid,
        "taille_dalle": options.mesh_size
        if options.mesh_size is not None
        else options.cell,
        "lots": manifest,
        "cas_thermiques": list(THERMAL_CASES) if production else [],
        "tables": sorted(seen),
        "positions": {
            c.name: {
                "modele": c.model,
                "transversal": c.transverse,
                "x": c.x,
                "roues_y": list(c.axles[0].wheels_y),
                "essieux_x": [a.x for a in c.axles],
                "pression_pa": c.pressure,
                "charge_totale_n": c.total,
            }
            for c in cases
        },
        "classes_ressorts": {
            class_group(k): groups for k, groups in spring_classes(v).items()
        },
    }
    return text, report


__all__ = [
    "BATCH_SIZE",
    "CONVERGENCE_CASES",
    "CAP_0P80_VARIANTS",
    "CAP_HEIGHT_E19",
    "DST_VARIANTS",
    "GenerationError",
    "MODES",
    "HARNESS_MOVING",
    "Options",
    "STATIC_CASES",
    "SYMMETRIC_CASES",
    "THERMAL_CASES",
    "VARIANTS",
    "build_comm",
    "fractional_prints",
    "spring_classes",
]
