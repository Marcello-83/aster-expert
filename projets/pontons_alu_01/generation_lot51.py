# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01, lot 51: the complete pier and three spans, one
parameterised file for every variant (`variantes_lot51.yaml`, PONTONS_VARIANTE).

Flat `.comm` (fallback accepted by MM at lot 50: the trunk reads it statically),
written from the data file, the decisions P1 to P43 of the fiche, the parameters of
`maillage_palee.py` and the variant. Elementary unit cases only (linear, consigne § 3);
the combinations are post-processing (`combinaisons_lot51`).

What changes with the variant: the links at the pile heads (P40: hinge = the three
translations through a rigid arm, rotations free; fixed = LIAISON_SOLIDE), at the ends
of the ties (monolithic ring: LIAISON_SOLIDE to the cap beam; independent beams: hinge
to the pile head), at the splices (P42: articulated = translations through the arm and
torsion, rotations about y_l and z_l free; continuous = LIAISON_SOLIDE), the bearings
(P38: springs Kx = Ky = k·G·A/Te, Kz; M: Y and Z tied, X free) and the main beam
section (P36). The pile height is a mesh parameter (H_PILES).

Bearing spring: a SEG2 of 1 mm (DIS_T, K_T_D_L, REPERE = GLOBAL) between the top of
the support profile and a node tied to the main beam node by a rigid arm: a discrete
element transmits no moment of a couple (U2.02.03, « Transmission des efforts »), so
its length is kept negligible and the lever arm is carried by the link.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.geometrie_lot51 import (
    SIDES,
    SPANS,
    Geometry51,
    Link,
    geometry,
    half_deck_widths,
    influence_widths,
    zone_names,
)
from pontons_alu_01.variantes_lot51 import Variant, current

G = 9.81
"""m/s², acceleration of gravity turning a unit weight into RHO (CA-048)."""

ALU_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES", "PANNES_SEC", "SUPPORTS")
CONCRETE_BEAMS = ("CHEVETRES", "LONGRINES", "PILES")
CONCRETE_GROUPS = (*CONCRETE_BEAMS, "SEMELLE")
BEAM_GROUPS = (*ALU_GROUPS, *CONCRETE_BEAMS)
TA_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES")
"""TA± (jeu A, S2) heats the main beams, posts and diagonals only (P10)."""
UNIT = 1000.0
"""N or N/m: unit berthing (1 kN/m on 1 m) and mooring (1 kN) cases (consigne § 3)."""

SPLIT = ("G2", "Q", "HU", "HD")
"""Cases split by span (consigne § 3), the total being their sum."""
BERTHING_DIRECTIONS = ("ACN", "ACX", "ACZ")
MOORING_DIRECTIONS = ("AMY", "AMX")


@dataclass(frozen=True)
class Values51:
    e_alu: float
    nu_alu: float
    alpha_alu: float
    gamma_alu: float
    e_concrete: float
    nu_concrete: float
    gamma_concrete: float
    beam_side: float
    beam_thickness: float
    t150: float
    e150: float
    t50: float
    e50: float
    ring_b: float
    ring_h: float
    pile_d: float
    footing_t: float
    kn: float
    kt: float
    g2: float
    q: float
    wave: float
    t_plus: float
    t_minus: float
    ta_plus: float
    ta_minus: float
    kx: float
    kz: float


def bearing_stiffness(d: dict[str, Any]) -> tuple[float, float]:
    """P38 (NF EN 1337-3 § 5.3.3.7, guide Sétra annexe 1 tableau A.2): Kx = G·A/Te,
    Kz = [Σ tᵢ/A′ · (1/(5·G·S²) + 1/Eb)]⁻¹, S = A′/(2·(a′ + b′)·tᵢ); N/m."""
    g = float(d["neoprene.module_cisaillement"]) * 1e6
    a = float(d["neoprene.cote_a"]) * 1e-3
    b = float(d["neoprene.cote_b"]) * 1e-3
    a1 = float(d["neoprene.cote_a_frette"]) * 1e-3
    b1 = float(d["neoprene.cote_b_frette"]) * 1e-3
    ti = float(d["neoprene.epaisseur_feuillet"]) * 1e-3
    n = float(d["neoprene.nombre_feuillets"])
    eb = float(d["neoprene.module_compressibilite"]) * 1e6
    te = n * ti
    area1 = a1 * b1
    shape = area1 / (2.0 * (a1 + b1) * ti)
    kx = g * a * b / te
    kz = 1.0 / (te / area1 * (1.0 / (5.0 * g * shape**2) + 1.0 / eb))
    return kx, kz


def values(ctx: ProjectContext, variant: Variant) -> Values51:
    """Every number of the data file and of the variant, converted once to m, N, Pa."""
    d = {k: v.value for k, v in ctx.data().items().items()}

    def f(key: str) -> float:
        value = d[key]
        assert isinstance(value, int | float)
        return float(value)

    kx, kz = bearing_stiffness(d)
    return Values51(
        e_alu=f("aluminium.module_young") * 1e6,
        nu_alu=f("aluminium.coefficient_poisson"),
        alpha_alu=f("aluminium.dilatation") * 1e-6,
        gamma_alu=f("aluminium.poids_volumique") * 1e3,
        e_concrete=f("beton.module_young") * 1e9,
        nu_concrete=f("beton.coefficient_poisson"),
        gamma_concrete=f("beton.poids_volumique") * 1e3,
        beam_side=variant.beam_side_mm * 1e-3,
        beam_thickness=variant.beam_thickness_mm * 1e-3,
        t150=f("tubes_150.cote") * 1e-3,
        e150=f("tubes_150.epaisseur") * 1e-3,
        t50=f("tubes_50.cote") * 1e-3,
        e50=f("tubes_50.epaisseur") * 1e-3,
        ring_b=f("anneau.largeur"),
        ring_h=f("anneau.hauteur"),
        pile_d=f("sections_beton.poteau_diametre"),
        footing_t=f("sections_beton.semelle_epaisseur"),
        kn=f("sol.raideur_normale") * 1e3,
        kt=f("sol.raideur_tangentielle") * 1e3,
        g2=f("charges.g2") * 1e3,
        q=f("charges.q") * 1e3,
        wave=f("charges.houle_unitaire") * 1e3,
        t_plus=f("charges.t_plus"),
        t_minus=-f("charges.t_moins"),
        ta_plus=f("charges.ta_plus"),
        ta_minus=f("charges.ta_moins"),
        kx=kx * variant.kh_factor,
        kz=kz,
    )


# --------------------------------------------------------------------------- cases


def berthing_cases(g: Geometry51) -> list[tuple[str, str, str, str]]:
    """(case, direction, zone, side) of the 30 unit berthing cases."""
    return [
        (f"{d}_{z}_{s}", d, z, s)
        for z in zone_names(g.parameters)
        for s, _ in SIDES
        for d in BERTHING_DIRECTIONS
    ]


def mooring_cases(g: Geometry51) -> list[tuple[str, str, int, str]]:
    """(case, direction, cleat, side) of the 16 unit mooring cases."""
    cleats = sorted({int(n[2]) for n in g.node_groups if n.startswith("TQ")})
    return [
        (f"{d}_TQ{k}_{s}", d, k, s)
        for k in cleats
        for s, _ in SIDES
        for d in MOORING_DIRECTIONS
    ]


def mechanical_cases(g: Geometry51) -> list[str]:
    out = ["G1"]
    for base in ("G2", "Q"):
        out += [base, *(f"{base}_{t}" for t in SPANS)]
    out.append("QD")
    for base in ("HU", "HD"):
        out += [base, *(f"{base}_{t}" for t in SPANS)]
    out += [c for c, *_ in berthing_cases(g)]
    out += [c for c, *_ in mooring_cases(g)]
    return out


THERMAL_CASES = ("TP", "TM", "TAP", "TAM")


def all_cases(g: Geometry51) -> list[str]:
    return [*mechanical_cases(g), *THERMAL_CASES]


def case_label(case: str) -> str:
    fixed = {
        "G1": "poids propre (aluminium 27 kN/m³, béton armé 25 kN/m³)",
        "G2": "G2 = 1,0 kN/m² sur les trois travées (P8)",
        "Q": "Q = 5 kPa sur les trois travées",
        "QD": "Q½ = 5 kPa sur la moitié Y > 0, trois travées",
        "HU": "houle, 1 kPa vers le haut, trois travées",
        "HD": "houle, 1 kPa vers le bas, trois travées",
        "TP": "T+ = +46 °C, tout l'aluminium",
        "TM": "T− = −28 °C, tout l'aluminium",
        "TAP": "TA+ = +56 °C, poutres, montants, diagonales (S2)",
        "TAM": "TA− = −23 °C, poutres, montants, diagonales (S2)",
    }
    if case in fixed:
        return fixed[case]
    head, *rest = case.split("_")
    if head in SPLIT and len(rest) == 1:
        return f"{fixed[head]} : travée {rest[0]} seule"
    if head in BERTHING_DIRECTIONS:
        zone, side = rest
        what = {
            "ACN": "⊥ au bord vers l'intérieur",
            "ACX": "selon +X",
            "ACZ": "selon +Z",
        }[head]
        return f"accostage unitaire 1 kN/m sur 1 m, zone {zone}, rive {side}, {what}"
    if head in MOORING_DIRECTIONS:
        cleat, side = rest
        what = {"AMY": "⊥ au bord vers l'extérieur", "AMX": "selon +X"}[head]
        return f"amarrage unitaire 1 kN, taquet {cleat} rive {side}, {what}"
    message = f"cas inconnu : {case}"
    raise KeyError(message)


# --------------------------------------------------------------------------- loads


def _r(x: float) -> str:
    return repr(float(x))


def _tuple(items: tuple[str, ...] | list[str]) -> str:
    return (
        "("
        + ", ".join(f'"{i}"' for i in items)
        + ("," if len(items) == 1 else "")
        + ")"
    )


def tube_area(side: float, thickness: float) -> float:
    return side**2 - (side - 2.0 * thickness) ** 2


def weights(v: Values51, g: Geometry51) -> dict[str, float]:
    """Self-weight of each family (N), from the data, the variant and the parameters
    (the bearing springs and the links carry no mass)."""
    area = {
        "POUTRES_PRINC": tube_area(v.beam_side, v.beam_thickness),
        "MONTANTS": tube_area(v.t150, v.e150),
        "DIAGONALES": tube_area(v.t150, v.e150),
        "SUPPORTS": tube_area(v.t150, v.e150),
        "PANNES_SEC": tube_area(v.t50, v.e50),
    }
    out = {
        fam: v.gamma_alu * a * sum(m.length for m in g.family(fam))
        for fam, a in area.items()
    }
    for fam in ("CHEVETRES", "LONGRINES"):
        out[fam] = (
            v.gamma_concrete
            * v.ring_b
            * v.ring_h
            * sum(m.length for m in g.family(fam))
        )
    out["PILES"] = (
        v.gamma_concrete
        * math.pi
        * v.pile_d**2
        / 4.0
        * sum(m.length for m in g.family("PILES"))
    )
    fx, fy = g.footing_x, g.footing_y
    out["SEMELLE"] = (
        v.gamma_concrete * v.footing_t * (fx[-1] - fx[0]) * (fy[-1] - fy[0])
    )
    return out


def span_length(g: Geometry51, span: str) -> float:
    return g.member(f"PP_{span}_YM").length


def applied_loads(v: Values51, g: Geometry51) -> dict[str, dict[str, float]]:
    """Applied resultant of each case (N), from the data and the parameters only."""
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    deck = {t: sum(influence_widths(g, t).values()) * span_length(g, t) for t in SPANS}
    half = {t: sum(half_deck_widths(g, t).values()) * span_length(g, t) for t in SPANS}
    out: dict[str, dict[str, float]] = {
        "G1": {**zero, "DZ": -sum(weights(v, g).values())}
    }
    pressures = {"G2": -v.g2, "Q": -v.q, "HU": v.wave, "HD": -v.wave}
    for base, pressure in pressures.items():
        out[base] = {**zero, "DZ": pressure * sum(deck.values())}
        for t in SPANS:
            out[f"{base}_{t}"] = {**zero, "DZ": pressure * deck[t]}
    out["QD"] = {**zero, "DZ": -v.q * sum(half.values())}
    lengths = {z.name: z.x1 - z.x0 for z in g.zones}
    for case, d, zone, side in berthing_cases(g):
        inward = 1.0 if side == "YM" else -1.0
        comp = {"ACN": ("DY", inward), "ACX": ("DX", 1.0), "ACZ": ("DZ", 1.0)}[d]
        out[case] = {**zero, comp[0]: comp[1] * UNIT * lengths[f"ACC_{zone}_{side}"]}
    for case, d, _, side in mooring_cases(g):
        outward = -1.0 if side == "YM" else 1.0
        comp = {"AMY": ("DY", outward), "AMX": ("DX", 1.0)}[d]
        out[case] = {**zero, comp[0]: comp[1] * UNIT}
    for case in THERMAL_CASES:
        out[case] = dict(zero)
    return out


def _surface_load(name: str, pressure: float, widths: dict[str, float]) -> list[str]:
    """P22: a surface pressure carried by the longitudinal bars, FZ = p × width."""
    lines = [f"{name} = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=("]
    for group, w in widths.items():
        lines.append(
            f'    _F(GROUP_MA="{group}", FZ={_r(pressure * w)}),  # b = {w:.3f} m'
        )
    lines.append("))")
    return lines


def _thermal(case: str, dt: float, groups: tuple[str, ...]) -> list[str]:
    """CA-054: TEMP field on the bars, AFFE_VARC with VALE_REF = 0 (ΔT given)."""
    return [
        f'T_{case} = CREA_CHAMP(OPERATION="AFFE", TYPE_CHAM="NOEU_TEMP_R", MAILLAGE=MAIL,'
        f' AFFE=_F(GROUP_MA={_tuple(groups)}, NOM_CMP="TEMP", VALE={_r(dt)}))',
        f"M_{case} = AFFE_MATERIAU(",
        "    MAILLAGE=MAIL,",
        f"    AFFE=(_F(GROUP_MA={_tuple(ALU_GROUPS)}, MATER=ALU), "
        f"_F(GROUP_MA={_tuple(CONCRETE_GROUPS)}, MATER=BETON)),",
        f'    AFFE_VARC=_F(GROUP_MA={_tuple(groups)}, NOM_VARC="TEMP", CHAM_GD=T_{case},'
        " VALE_REF=0.0),",
        ")",
        f"{case} = MECA_STATIQUE(MODELE=MODELE, CHAM_MATER=M_{case}, CARA_ELEM=CARA,"
        ' EXCIT=_F(CHARGE=CL), SOLVEUR=_F(METHODE="MUMPS"))',
    ]


# --------------------------------------------------------------------------- links


def arm_terms(link: Link) -> list[tuple[str, str, float]]:
    """u_A = u_B + θ_B ∧ (A − B): for each translation, the terms (node group, ddl,
    coefficient) of u_A − u_B − θ_B ∧ d = 0, zero coefficients dropped."""
    a, b = f"{link.name}_A", f"{link.name}_B"
    dx, dy, dz = (round(p - q, 9) for p, q in zip(link.a, link.b, strict=True))
    rows = {
        "DX": [("DRY", -dz), ("DRZ", dy)],
        "DY": [("DRZ", -dx), ("DRX", dz)],
        "DZ": [("DRX", -dy), ("DRY", dx)],
    }
    out = []
    for ddl, extra in rows.items():
        terms = [(a, ddl, 1.0), (b, ddl, -1.0)]
        terms += [(b, r, c) for r, c in extra if c != 0.0]
        out.append(terms)
    return [t for terms in out for t in [*terms, ("", "", 0.0)]]


def _ddl_lines(terms: list[tuple[str, str, float]]) -> list[str]:
    """LIAISON_DDL occurrences from `arm_terms` (separated by empty terms)."""
    out, current = [], []
    for t in terms:
        if t[0] == "":
            out.append(current)
            current = []
        else:
            current.append(t)
    lines = []
    for eq in out:
        groups = tuple(g for g, _, _ in eq)
        ddls = tuple(d for _, d, _ in eq)
        coefs = ", ".join(_r(c) for _, _, c in eq)
        lines.append(
            f"        _F(GROUP_NO={_tuple(groups)}, DDL={_tuple(ddls)}, COEF_MULT=({coefs},), COEF_IMPO=0.0),"
        )
    return lines


def link_plan(g: Geometry51, variant: Variant) -> dict[str, list[Link]]:
    """Which link is written how: `solide` (LIAISON_SOLIDE), `bras` (translations
    through the arm), `bras_torsion` (arm and DRX), `mecanique` (DY, DZ tied)."""
    plan: dict[str, list[Link]] = {"solide": [], "bras": [], "bras_torsion": []}
    for lk in g.links:
        if lk.kind == "solide":
            plan["solide"].append(lk)
        elif lk.kind == "bras":
            plan["bras"].append(lk)
        elif lk.kind == "eclissage":
            plan["solide" if variant.splice == "continu" else "bras_torsion"].append(lk)
        elif lk.kind == "tete_pile":
            pile = lk.name.removeprefix("TP_")
            hinge = variant.heads[pile] == "rotule"
            plan["bras" if hinge else "solide"].append(lk)
        elif lk.kind == "longrine":
            if variant.ring == "monolithique":
                plan["solide"].append(lk)
            else:
                pile = lk.name.removeprefix("LG_")
                head = g.link(f"TP_{pile}")
                plan["bras"].append(Link(lk.name, "longrine_tete", lk.a, head.a))
        else:
            message = f"liaison {lk.name} : nature {lk.kind} inconnue"
            raise ValueError(message)
    return plan


# --------------------------------------------------------------------------- .comm


def build_comm(
    ctx: ProjectContext, *, mesh_label: str, variant: Variant | None = None
) -> tuple[str, dict[str, Any]]:
    variant = variant or current()
    v = values(ctx, variant)
    g = geometry(variant.mesh_overrides)
    p = g.parameters
    fx, fy = g.footing_x, g.footing_y
    footing_area = (fx[-1] - fx[0]) * (fy[-1] - fy[0])
    centre = ((fx[0] + fx[-1]) / 2.0, (fy[0] + fy[-1]) / 2.0, g.footing_z)
    plan = link_plan(g, variant)
    out: list[str] = []
    w = out.append
    w(
        "# PONTONS-ALU-01, lot 51 : palée complète (4 piles, anneau BA), trois travées en"
    )
    w(
        "# aluminium soudé, appuis néoprène. Calcul linéaire, cas élémentaires unitaires."
    )
    w(f"# Variante {variant.code} : {variant.description}.")
    w(
        f"# Code_Aster 17.4. Unités : m, N, Pa, °C. Maillage : {mesh_label} (maillage_palee.py,"
    )
    w(
        f"# H_PILES = {variant.pile_height:g} m). Généré par pontons_alu_01.generation_lot51 à partir"
    )
    w(
        "# de la fiche (P1 à P43), des données et de variantes_lot51.yaml : régénérer plutôt"
    )
    w("# qu'éditer. Combinaisons et exports : post-traitement (scripts/lot51.py).")
    w("#")
    w("# Paramètres (rappel)")
    w(
        f"#   travées T1 et T2 de {p['L']} m, petite travée entre chevêtres en X = {p['X_PALEE'][0]} et {p['X_PALEE'][1]} ;"
    )
    w(
        f"#   B = {p['B']} m, tablier {p['LARGEUR_TABLIER']} m (P35), plan moyen +{g.deck_z}, pannes +{g.purlin_z}"
    )
    w(
        f"#   poutres principales tube {variant.beam_label} mm (P36) ; anneau {v.ring_b} × {v.ring_h} m (P43) ;"
        f" piles Ø {v.pile_d} m, H = {variant.pile_height:g} m (P41)"
    )
    w(
        f"#   néoprènes (P38) : Kx = Ky = {v.kx:.6g} N/m (facteur {variant.kh_factor:g}), Kz = {v.kz:.6g} N/m, Kθ = 0 ;"
        f" appuis : {variant.bearings}"
    )
    w(
        f"#   têtes de piles : {', '.join(f'{k} {h}' for k, h in variant.heads.items())} ; anneau {variant.ring} ;"
        f" éclissages {variant.splice} (P42)"
    )
    w(
        f"#   sol kn = {v.kn:.4g} N/m³, kt = {v.kt:.4g} N/m³ sous {footing_area:.4f} m² (P19)"
    )
    w("")
    w('DEBUT(CODE="OUI")')
    w("")
    w("# ---------------------------------------------------------------- 1. MAILLAGE")
    w('MAIL0 = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)')
    w(
        "# Appui élastique réparti (P19) : une maille POI1 par nœud de la semelle (ssls135a)."
    )
    w(
        'MAIL = CREA_MAILLAGE(MAILLAGE=MAIL0, CREA_POI1=_F(NOM_GROUP_MA="SOL", GROUP_MA="SEMELLE"))'
    )
    w(
        'MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=_F(GROUP_MA="SEMELLE", NOM="N_SEMELLE"))'
    )
    w("")
    w("# ---------------------------------------------------------------- 2. MODÈLE")
    w("# Barres : POU_D_T ; semelle : DKT ; sol et néoprènes : DIS_T (P19, P38).")
    w("MODELE = AFFE_MODELE(")
    w("    MAILLAGE=MAIL,")
    w("    AFFE=(")
    w(
        f'        _F(GROUP_MA={_tuple(BEAM_GROUPS)}, PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),'
    )
    w('        _F(GROUP_MA="SEMELLE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),')
    w(
        '        _F(GROUP_MA=("SOL", "NEOPRENES"), PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),'
    )
    w("    ),")
    w(")")
    w("")
    w("# ---------------------------------------------------------------- 3. MATÉRIAUX")
    w("# RHO = γ / g (CA-048). Températures : aluminium seulement (P10).")
    w(
        f"ALU = DEFI_MATERIAU(ELAS=_F(E={_r(v.e_alu)}, NU={_r(v.nu_alu)}, "
        f"RHO={_r(v.gamma_alu / G)}, ALPHA={_r(v.alpha_alu)}))"
    )
    w(
        f"BETON = DEFI_MATERIAU(ELAS=_F(E={_r(v.e_concrete)}, NU={_r(v.nu_concrete)}, "
        f"RHO={_r(v.gamma_concrete / G)}))"
    )
    w("CHMAT = AFFE_MATERIAU(")
    w("    MAILLAGE=MAIL,")
    w(
        f"    AFFE=(_F(GROUP_MA={_tuple(ALU_GROUPS)}, MATER=ALU), _F(GROUP_MA={_tuple(CONCRETE_GROUPS)}, MATER=BETON)),"
    )
    w(")")
    w("")
    w(
        "# ---------------------------------------------------------------- 4. CARACTÉRISTIQUES"
    )
    w(
        "# Tubes carrés à angles vifs : A, I et JX (Bredt) calculés par Code_Aster (U4.42.01)."
    )
    w(
        "# Repère local : z_l = +Z pour les barres horizontales (VECT_Z), y_l = +X pour les verticales."
    )
    w(
        "# Néoprènes (P38) : K_T_D_L dans le repère global (REPERE = GLOBAL), sans masse."
    )
    kh = (0.0, 0.0, 0.0) if variant.bearings == "mecanique" else (v.kx, v.kx, v.kz)
    w("CARA = AFFE_CARA_ELEM(")
    w("    MODELE=MODELE,")
    w("    POUTRE=(")
    w(
        '        _F(GROUP_MA="POUTRES_PRINC", SECTION="RECTANGLE", CARA=("H", "EP"),'
        f" VALE=({_r(v.beam_side)}, {_r(v.beam_thickness)})),"
    )
    w(
        '        _F(GROUP_MA=("MONTANTS", "DIAGONALES", "SUPPORTS"), SECTION="RECTANGLE", CARA=("H", "EP"),'
        f" VALE=({_r(v.t150)}, {_r(v.e150)})),"
    )
    w(
        f'        _F(GROUP_MA="PANNES_SEC", SECTION="RECTANGLE", CARA=("H", "EP"), VALE=({_r(v.t50)}, {_r(v.e50)})),'
    )
    w(
        f'        _F(GROUP_MA=("CHEVETRES", "LONGRINES"), SECTION="RECTANGLE", CARA=("HY", "HZ"), VALE=({_r(v.ring_b)}, {_r(v.ring_h)})),'
    )
    w(
        f'        _F(GROUP_MA="PILES", SECTION="CERCLE", CARA=("R",), VALE=({_r(v.pile_d / 2.0)},)),'
    )
    w("    ),")
    w("    ORIENTATION=(")
    w(
        f"        _F(GROUP_MA={_tuple(('POUTRES_PRINC', 'MONTANTS', 'DIAGONALES', 'PANNES_SEC', 'CHEVETRES', 'LONGRINES'))},"
        ' CARA="VECT_Z", VALE=(0.0, 0.0, 1.0)),'
    )
    w(
        '        _F(GROUP_MA=("SUPPORTS", "PILES"), CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),'
    )
    w("    ),")
    w(
        f'    COQUE=_F(GROUP_MA="SEMELLE", EPAIS={_r(v.footing_t)}, ANGL_REP=(0.0, 0.0)),'
    )
    w("    DISCRET=(")
    w('        _F(GROUP_MA="SOL", CARA="M_T_D_N", VALE=0.0),')
    w('        _F(GROUP_MA="NEOPRENES", CARA="M_T_D_L", VALE=0.0),')
    w(
        f'        _F(GROUP_MA="NEOPRENES", CARA="K_T_D_L", REPERE="GLOBAL", VALE=({_r(kh[0])}, {_r(kh[1])}, {_r(kh[2])})),'
    )
    w("    ),")
    w(
        "    # P19 : raideurs globales k × surface, réparties au prorata des surfaces (U4.42.01)."
    )
    w("    RIGI_PARASOL=_F(")
    w(
        '        GROUP_MA="SEMELLE", GROUP_MA_POI1="SOL", COEF_GROUP=1.0, CARA="K_T_D_N",'
    )
    w(
        f"        VALE=({_r(v.kt * footing_area)}, {_r(v.kt * footing_area)}, {_r(v.kn * footing_area)}),"
    )
    w(f"        COOR_CENTRE=({_r(centre[0])}, {_r(centre[1])}, {_r(centre[2])}),")
    w("    ),")
    w(")")
    w("")
    w(
        "# ---------------------------------------------------------------- 5. LIAISONS ET APPUIS"
    )
    w(
        "# P35 : rotule côté quai Y > 0 fixe, rotule Y < 0 guidée (libre en Y). Appuis de la"
    )
    w(
        "# travée 2 en X = 14,02 : pied des profilés supports encastré sur un support fixe."
    )
    w(
        "# LIAISON_SOLIDE : pannes / montants et diagonales (LR_), pied des profilés supports /"
    )
    w(
        "# chevêtre (SC_, P39), pied de pile / semelle (PS_), et selon la variante tête de pile"
    )
    w(
        "# encastrée (TP_), anneau monolithique (LG_), éclissage continu (EC_). LIAISON_DDL :"
    )
    w(
        "# bras rigide u_A = u_B + θ_B ∧ (A − B) pour le haut du néoprène (BR_), la tête de pile"
    )
    w(
        "# en rotule (TP_), le bout de longrine indépendante (LG_ → tête de pile), l'éclissage"
    )
    w("# articulé (EC_, plus DRX : rotations autour de y_l et z_l libres, P42).")
    w("CL = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w(
        '    DDL_IMPO=(_F(GROUP_NO="APP_QUAI_YP", DX=0.0, DY=0.0, DZ=0.0), _F(GROUP_NO="APP_QUAI_YM", DX=0.0, DZ=0.0),'
        ' _F(GROUP_NO="APP_FIXE", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0)),'
    )
    w("    LIAISON_SOLIDE=(")
    for lk in plan["solide"]:
        w(f'        _F(GROUP_NO=("{lk.name}_A", "{lk.name}_B")),')
    w("    ),")
    w("    LIAISON_DDL=(")
    for lk in plan["bras"]:
        if lk.kind == "longrine_tete":
            pile = lk.name.removeprefix("LG_")
            terms = arm_terms(lk)
            terms = [
                (f"TP_{pile}_A" if grp == f"{lk.name}_B" else grp, d, c)
                for grp, d, c in terms
            ]
            w(
                f"        # {lk.name} : bout de longrine → tête de pile TP_{pile}_A (anneau indépendant)"
            )
            out.extend(_ddl_lines(terms))
        else:
            out.extend(_ddl_lines(arm_terms(lk)))
    for lk in plan["bras_torsion"]:
        out.extend(_ddl_lines(arm_terms(lk)))
        w(
            f'        _F(GROUP_NO=("{lk.name}_B", "{lk.name}_A"), DDL=("DRX", "DRX"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),'
        )
    if variant.bearings == "mecanique":
        w(
            "        # Variante M : appui mécanique articulé, Y et Z liés, X libre (néoprène sans raideur)."
        )
        for app in ("A1", "A2", "A3"):
            for side, _ in SIDES:
                for ddl in ("DY", "DZ"):
                    w(
                        f'        _F(GROUP_NO=("BR_{app}_{side}_A", "NB_{app}_{side}"), DDL=("{ddl}", "{ddl}"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),'
                    )
    w("    ),")
    w(")")
    w("")
    w(
        "# ---------------------------------------------------------------- 6. CAS DE CHARGE"
    )
    w(
        "# Actions de surface (P22) : FORCE_POUTRE sur les barres longitudinales, largeur"
    )
    w(
        f"# d'influence b de chaque ligne, tablier de {p['LARGEUR_TABLIER']} m, une charge par travée (§ 3)."
    )
    w(
        "CG1 = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))"
    )
    concepts: dict[str, tuple[str, ...]] = {"G1": ("CG1",)}
    pressures = {"G2": -v.g2, "Q": -v.q, "HU": v.wave, "HD": -v.wave}
    for base, pressure in pressures.items():
        names = []
        for t in SPANS:
            name = f"C{base}{t}"
            out.extend(_surface_load(name, pressure, influence_widths(g, t)))
            concepts[f"{base}_{t}"] = (name,)
            names.append(name)
        concepts[base] = tuple(names)
    half: dict[str, float] = {}
    for t in SPANS:
        half.update(half_deck_widths(g, t))
    out.extend(_surface_load("CQD", -v.q, half))
    concepts["QD"] = ("CQD",)
    w(
        "# Accostage (§ 3) : 1 kN/m sur la zone de 1 m de la poutre de rive ; ACN ⊥ au bord vers"
    )
    w(
        "# l'intérieur, ACX selon +X, ACZ selon +Z. Charge appliquée sur l'axe de la poutre."
    )
    for k, (case, d, zone, side) in enumerate(berthing_cases(g), start=1):
        inward = 1.0 if side == "YM" else -1.0
        comp, val = {
            "ACN": ("FY", inward * UNIT),
            "ACX": ("FX", UNIT),
            "ACZ": ("FZ", UNIT),
        }[d]
        name = f"CAC{k:02d}"
        w(
            f'{name} = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA="ACC_{zone}_{side}", {comp}={_r(val)}))  # {case}'
        )
        concepts[case] = (name,)
    w(
        "# Amarrage (§ 3) : 1 kN au taquet ; AMY ⊥ au bord vers l'extérieur, AMX selon +X."
    )
    for k, (case, d, cleat, side) in enumerate(mooring_cases(g), start=1):
        outward = -1.0 if side == "YM" else 1.0
        comp, val = {"AMY": ("FY", outward * UNIT), "AMX": ("FX", UNIT)}[d]
        name = f"CAM{k:02d}"
        w(
            f'{name} = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_NODALE=_F(GROUP_NO="TQ{cleat}_{side}", {comp}={_r(val)}))  # {case}'
        )
        concepts[case] = (name,)
    w("")
    w(
        "# ---------------------------------------------------------------- 7. RÉSOLUTION"
    )
    w(
        "# Cas mécaniques : une factorisation (MACRO_ELAS_MULT, CA-055) ; un cas total = somme"
    )
    w("# des charges de ses travées.")
    w("ELEM = MACRO_ELAS_MULT(")
    w("    MODELE=MODELE,")
    w("    CHAM_MATER=CHMAT,")
    w("    CARA_ELEM=CARA,")
    w("    CHAR_MECA_GLOBAL=CL,")
    w("    CAS_CHARGE=(")
    mechanical = mechanical_cases(g)
    for case in mechanical:
        charge = concepts[case]
        text = charge[0] if len(charge) == 1 else "(" + ", ".join(charge) + ")"
        w(f'        _F(NOM_CAS="{case}", CHAR_MECA={text}, OPTION="SANS"),')
    w("    ),")
    w('    SOLVEUR=_F(METHODE="MUMPS", POSTTRAITEMENTS="FORCE"),')
    w(")")
    w(
        f'ELEM = CALC_CHAMP(reuse=ELEM, RESULTAT=ELEM, GROUP_MA={_tuple(BEAM_GROUPS)}, CONTRAINTE=("EFGE_ELNO",))'
    )
    w('ELEM = CALC_CHAMP(reuse=ELEM, RESULTAT=ELEM, FORCE=("REAC_NODA",))')
    w("# Températures uniformes (P10), CA-054 : un champ de matériau par cas.")
    thermal = {
        "TP": (v.t_plus, ALU_GROUPS),
        "TM": (v.t_minus, ALU_GROUPS),
        "TAP": (v.ta_plus, TA_GROUPS),
        "TAM": (v.ta_minus, TA_GROUPS),
    }
    for case, (dt, groups) in thermal.items():
        w(f"# {case_label(case)}")
        out.extend(_thermal(case, dt, groups))
        w(
            f'{case} = CALC_CHAMP(reuse={case}, RESULTAT={case}, GROUP_MA={_tuple(BEAM_GROUPS)}, CONTRAINTE=("EFGE_ELNO",))'
        )
        w(f'{case} = CALC_CHAMP(reuse={case}, RESULTAT={case}, FORCE=("REAC_NODA",))')
    w("")
    w("# ---------------------------------------------------------------- 8. SORTIES")
    w(
        "# Harnais D (listing, E20.12) : RP_<cas> rotules du quai, RF_<cas> pieds fixes en"
    )
    w(
        "# X = 14,02, DS_<cas> déplacements des nœuds de la semelle (efforts des ressorts k·u)."
    )
    for case in all_cases(g):
        result = "ELEM" if case in mechanical else case
        where = f'NOM_CAS="{case}"' if case in mechanical else 'TOUT_ORDRE="OUI"'
        for prefix, field, group, extra in (
            ("RP", "REAC_NODA", "APP_QUAI", 'RESULTANTE=("DX", "DY", "DZ")'),
            ("RF", "REAC_NODA", "APP_FIXE", 'RESULTANTE=("DX", "DY", "DZ")'),
            ("DS", "DEPL", "N_SEMELLE", 'NOM_CMP=("DX", "DY", "DZ")'),
        ):
            w(
                f'T{prefix} = POST_RELEVE_T(ACTION=_F(OPERATION="EXTRACTION", INTITULE="{prefix}_{case}",'
                f' RESULTAT={result}, NOM_CHAM="{field}", {where}, GROUP_NO="{group}", {extra}))'
            )
            w(f'IMPR_TABLE(TABLE=T{prefix}, UNITE=6, FORMAT_R="E20.12")')
            w(f"DETRUIRE(NOM=T{prefix})")
    w(
        "# Tables d'export (E25.16, 17 chiffres) : unité 31 efforts des barres (EFGE_ELNO),"
    )
    w(
        "# 32 déplacements de tous les nœuds, 33 réactions des appuis (rotules du quai, pieds fixes)."
    )
    for result in ("ELEM", *THERMAL_CASES):
        for unit, field, where in (
            (31, "EFGE_ELNO", f"GROUP_MA={_tuple(BEAM_GROUPS)}"),
            (32, "DEPL", 'TOUT="OUI"'),
            (33, "REAC_NODA", 'GROUP_NO=("APP_QUAI", "APP_FIXE")'),
        ):
            w(
                f'TX = CREA_TABLE(RESU=_F(RESULTAT={result}, NOM_CHAM="{field}", TOUT_ORDRE="OUI", TOUT_CMP="OUI", {where}, INTITULE="{result}"))'
            )
            w(f'IMPR_TABLE(TABLE=TX, UNITE={unit}, FORMAT_R="E25.16")')
            w("DETRUIRE(NOM=TX)")
    w("")
    w("FIN()")
    report = {
        "variant": variant.code,
        "cases": {c: case_label(c) for c in all_cases(g)},
        "links": {k: [lk.name for lk in v_] for k, v_ in plan.items()},
        "bearing_stiffness_n_per_m": {"kx": v.kx, "ky": v.kx, "kz": v.kz},
        "footing_area_m2": footing_area,
        "weights_n": weights(v, g),
        "applied_loads_n": applied_loads(v, g),
    }
    return "\n".join(out) + "\n", report


__all__ = [
    "ALU_GROUPS",
    "BEAM_GROUPS",
    "THERMAL_CASES",
    "Values51",
    "all_cases",
    "applied_loads",
    "arm_terms",
    "bearing_stiffness",
    "berthing_cases",
    "build_comm",
    "case_label",
    "link_plan",
    "mechanical_cases",
    "mooring_cases",
    "values",
    "weights",
]
