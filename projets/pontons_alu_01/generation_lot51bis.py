# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01, lot 51 bis: one pier type and three spans, one
parameterised file for every variant (`variantes_lot51bis.yaml`, PONTONS_VARIANTE).

Flat `.comm` written from the data file, the decisions P1 to P51 of the fiche, the
parameters of `maillage_palee_51bis.py` and the variant. Elementary unit cases only
(linear); the combinations are post-processing (`combinaisons_lot51bis`).

From lot 51 (`generation_lot51`, variant R) this lot keeps the deck, the loads, the
quay hinges and the ring, and changes (consigne of lot 51 bis):

- P44: pin bearings instead of the elastomeric bearings and support profiles. The pin
  is not a mesh node: with P its point and N a node, the translation of P carried by N
  is u_N + θ_N ∧ (P − N). Linear relations (LIAISON_DDL): the translations of P carried
  by the two ears that meet on the axis are equal, and so are their rotations about X
  (articulated splice: rotations about y_l = Y and z_l = Z free, P42, P44); P carried by
  the first ear and P carried by the cap beam node under it have the same Z (pin, both
  sides) and, on side YP only, the same Y; X is free (slotted hole). At X = 14,02 the pin
  sits on a fixed support: Z, and Y on side YP, of P are zero;
- P45: X is fixed at the quay hinges only (unchanged);
- P46: the four pile heads are fixed in the cap beams (LIAISON_SOLIDE);
- P47, P48: levels and footing from the mesh parameters, ring height from the variant;
- P49: new case DEJ, buoyancy of the whole concrete volume (FORCE_POUTRE on the bars of
  concrete, FORCE_COQUE on the footing, 10 kN/m³ × section or thickness, upwards).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation_lot51 import (
    SPLIT,
    THERMAL_CASES,
    UNIT,
    _r,
    _surface_load,
    _tuple,
    berthing_cases,
    mooring_cases,
    span_length,
    tube_area,
)
from pontons_alu_01.generation_lot51 import case_label as case_label_lot51
from pontons_alu_01.geometrie_lot51 import (
    SPANS,
    Point,
    half_deck_widths,
    influence_widths,
)
from pontons_alu_01.geometrie_lot51bis import Axis, Geometry51bis, geometry
from pontons_alu_01.variantes_lot51bis import Variant51bis, current

G = 9.81
"""m/s², acceleration of gravity turning a unit weight into RHO (CA-048)."""

ALU_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES", "PANNES_SEC")
CONCRETE_BEAMS = ("CHEVETRES", "LONGRINES", "PILES")
CONCRETE_GROUPS = (*CONCRETE_BEAMS, "SEMELLE")
BEAM_GROUPS = (*ALU_GROUPS, *CONCRETE_BEAMS)
TA_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES")
"""TA± (jeu A, S2) heats the main beams, posts and diagonals only (P10)."""
TRANSLATIONS = ("DX", "DY", "DZ")


@dataclass(frozen=True)
class Values51bis:
    e_alu: float
    nu_alu: float
    alpha_alu: float
    gamma_alu: float
    e_concrete: float
    nu_concrete: float
    gamma_concrete: float
    gamma_water: float
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


def values(ctx: ProjectContext, variant: Variant51bis) -> Values51bis:
    """Every number of the data file and of the variant, converted once to m, N, Pa."""
    d = {k: v.value for k, v in ctx.data().items().items()}

    def f(key: str) -> float:
        value = d[key]
        assert isinstance(value, int | float)
        return float(value)

    return Values51bis(
        e_alu=f("aluminium.module_young") * 1e6,
        nu_alu=f("aluminium.coefficient_poisson"),
        alpha_alu=f("aluminium.dilatation") * 1e-6,
        gamma_alu=f("aluminium.poids_volumique") * 1e3,
        e_concrete=f("beton.module_young") * 1e9,
        nu_concrete=f("beton.coefficient_poisson"),
        gamma_concrete=f("beton.poids_volumique") * 1e3,
        gamma_water=f("palee_lot51bis.poids_volumique_eau") * 1e3,
        beam_side=variant.beam_side_mm * 1e-3,
        beam_thickness=variant.beam_thickness_mm * 1e-3,
        t150=f("tubes_150.cote") * 1e-3,
        e150=f("tubes_150.epaisseur") * 1e-3,
        t50=f("tubes_50.cote") * 1e-3,
        e50=f("tubes_50.epaisseur") * 1e-3,
        ring_b=f("anneau.largeur"),
        ring_h=variant.ring_height,
        pile_d=f("sections_beton.poteau_diametre"),
        footing_t=f("palee_lot51bis.semelle_epaisseur"),
        kn=f("sol.raideur_normale") * 1e3,
        kt=f("sol.raideur_tangentielle") * 1e3,
        g2=f("charges.g2") * 1e3,
        q=f("charges.q") * 1e3,
        wave=f("charges.houle_unitaire") * 1e3,
        t_plus=f("charges.t_plus"),
        t_minus=-f("charges.t_moins"),
        ta_plus=f("charges.ta_plus"),
        ta_minus=f("charges.ta_moins"),
    )


# --------------------------------------------------------------------------- cases


def mechanical_cases(g: Geometry51bis) -> list[str]:
    out = ["G1", "DEJ"]
    for base in ("G2", "Q"):
        out += [base, *(f"{base}_{t}" for t in SPANS)]
    out.append("QD")
    for base in ("HU", "HD"):
        out += [base, *(f"{base}_{t}" for t in SPANS)]
    out += [c for c, *_ in berthing_cases(g)]
    out += [c for c, *_ in mooring_cases(g)]
    return out


def all_cases(g: Geometry51bis) -> list[str]:
    return [*mechanical_cases(g), *THERMAL_CASES]


def case_label(case: str) -> str:
    if case == "DEJ":
        return "déjaugeage : poussée d'Archimède 10 kN/m³ sur tout le volume de béton de la palée, vers le haut (P49)"
    if case == "G1":
        return "poids propre (aluminium 27 kN/m³, béton 25 kN/m³)"
    return case_label_lot51(case)


# --------------------------------------------------------------------------- loads


def concrete_volumes(v: Values51bis, g: Geometry51bis) -> dict[str, float]:
    """Volume of concrete of each family as modelled (m³): bar lengths × section,
    footing area × thickness."""
    ring = v.ring_b * v.ring_h
    pile = math.pi * v.pile_d**2 / 4.0
    fx, fy = g.footing_x, g.footing_y
    return {
        "CHEVETRES": ring * sum(m.length for m in g.family("CHEVETRES")),
        "LONGRINES": ring * sum(m.length for m in g.family("LONGRINES")),
        "PILES": pile * sum(m.length for m in g.family("PILES")),
        "SEMELLE": v.footing_t * (fx[-1] - fx[0]) * (fy[-1] - fy[0]),
    }


def weights(v: Values51bis, g: Geometry51bis) -> dict[str, float]:
    """Self-weight of each family (N), from the data, the variant and the parameters
    (the links carry no mass)."""
    area = {
        "POUTRES_PRINC": tube_area(v.beam_side, v.beam_thickness),
        "MONTANTS": tube_area(v.t150, v.e150),
        "DIAGONALES": tube_area(v.t150, v.e150),
        "PANNES_SEC": tube_area(v.t50, v.e50),
    }
    out = {
        fam: v.gamma_alu * a * sum(m.length for m in g.family(fam))
        for fam, a in area.items()
    }
    for fam, vol in concrete_volumes(v, g).items():
        out[fam] = v.gamma_concrete * vol
    return out


def applied_loads(v: Values51bis, g: Geometry51bis) -> dict[str, dict[str, float]]:
    """Applied resultant of each case (N), from the data and the parameters only."""
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    deck = {t: sum(influence_widths(g, t).values()) * span_length(g, t) for t in SPANS}
    half = {t: sum(half_deck_widths(g, t).values()) * span_length(g, t) for t in SPANS}
    out: dict[str, dict[str, float]] = {
        "G1": {**zero, "DZ": -sum(weights(v, g).values())},
        "DEJ": {**zero, "DZ": v.gamma_water * sum(concrete_volumes(v, g).values())},
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


# --------------------------------------------------------------------------- pins

Term = tuple[str, str, float]
"""(node group, ddl, coefficient) of a LIAISON_DDL relation."""


def carried(group: str, node: Point, pin: Point, ddl: str, sign: float) -> list[Term]:
    """`sign` × component `ddl` of the translation of `pin` carried by `node`:
    u_N + θ_N ∧ (P − N), zero coefficients dropped."""
    dx, dy, dz = (round(p - n, 9) for p, n in zip(pin, node, strict=True))
    extra = {
        "DX": [("DRY", dz), ("DRZ", -dy)],
        "DY": [("DRZ", dx), ("DRX", -dz)],
        "DZ": [("DRX", dy), ("DRY", -dx)],
    }[ddl]
    terms = [(group, ddl, sign)]
    terms += [(group, r, sign * c) for r, c in extra if c != 0.0]
    return terms


def pin_relations(axis: Axis) -> list[tuple[str, list[Term]]]:
    """(label, terms) of each relation of a pin bearing (P44), right-hand side 0."""
    out: list[tuple[str, list[Term]]] = []
    first = (axis.ear_group(1), axis.ears[0])
    if len(axis.ears) == 2:
        second = (axis.ear_group(2), axis.ears[1])
        for ddl in TRANSLATIONS:
            out.append(
                (
                    f"axe commun, {ddl}",
                    carried(*first, axis.pin, ddl, 1.0)
                    + carried(*second, axis.pin, ddl, -1.0),
                )
            )
        out.append(
            (
                "éclissage articulé, torsion DRX",
                [(first[0], "DRX", 1.0), (second[0], "DRX", -1.0)],
            )
        )
    blocked = ("DY", "DZ") if axis.blocks_y else ("DZ",)
    for ddl in blocked:
        terms = carried(*first, axis.pin, ddl, 1.0)
        if axis.cap is not None:
            terms += carried(axis.cap_group, axis.cap, axis.pin, ddl, -1.0)
            out.append((f"appui sur le chevêtre, {ddl}", terms))
        else:
            out.append((f"appui sur support fixe, {ddl}", terms))
    return out


def _ddl_line(terms: list[Term]) -> str:
    groups = tuple(t[0] for t in terms)
    ddls = tuple(t[1] for t in terms)
    coefs = ", ".join(_r(t[2]) for t in terms)
    return f"        _F(GROUP_NO={_tuple(groups)}, DDL={_tuple(ddls)}, COEF_MULT=({coefs},), COEF_IMPO=0.0),"


def reaction_groups(g: Geometry51bis) -> tuple[str, ...]:
    """Node groups whose REAC_NODA is exported (unit 33): quay hinges, the ears at
    X = 14,02 (fixed support) and every node of a pin relation."""
    out = ["APP_QUAI", "APP_A3"]
    for a in g.axes:
        out += [a.ear_group(k) for k in range(1, len(a.ears) + 1)]
        if a.cap is not None:
            out.append(a.cap_group)
    return tuple(dict.fromkeys(out))


# --------------------------------------------------------------------------- .comm


def build_comm(  # noqa: PLR0915 -- un .comm écrit d'un trait, section par section
    ctx: ProjectContext, *, mesh_label: str, variant: Variant51bis | None = None
) -> tuple[str, dict[str, Any]]:
    variant = variant or current()
    v = values(ctx, variant)
    g = geometry(variant.mesh_overrides)
    p = g.parameters
    lv = g.levels
    fx, fy = g.footing_x, g.footing_y
    footing_area = (fx[-1] - fx[0]) * (fy[-1] - fy[0])
    centre = ((fx[0] + fx[-1]) / 2.0, (fy[0] + fy[-1]) / 2.0, g.footing_z)
    solid = [lk for lk in g.links if lk.kind in ("solide", "tete_pile", "longrine")]
    out: list[str] = []
    w = out.append
    w(
        "# PONTONS-ALU-01, lot 51 bis : palée type (4 piles, anneau BA), trois travées en"
    )
    w(
        "# aluminium soudé rehaussées de 0,50 m, appuis articulés à axe. Calcul linéaire,"
    )
    w("# cas élémentaires unitaires.")
    w(f"# Variante {variant.code} : {variant.description}.")
    w(
        f"# Code_Aster 17.4. Unités : m, N, Pa, °C. Maillage : {mesh_label} (maillage_palee_51bis.py,"
    )
    w(
        f"# H_ANNEAU = {variant.ring_height:g} m, H_PILES = {variant.pile_height:g} m). Généré par pontons_alu_01.generation_lot51bis"
    )
    w(
        "# à partir de la fiche (P1 à P51), des données et de variantes_lot51bis.yaml : régénérer"
    )
    w(
        "# plutôt qu'éditer. Combinaisons et exports : post-traitement (scripts/lot51bis.py)."
    )
    w("#")
    w("# Paramètres et cotes (rappel, m NGF)")
    w(
        f"#   travées T1 et T2 de {p['L']} m, petite travée entre chevêtres en X = {p['X_PALEE'][0]} et {p['X_PALEE'][1]} ;"
    )
    w(
        f"#   B = {p['B']} m, tablier {p['LARGEUR_TABLIER']} m (P35) ; plan moyen +{lv['plan_moyen']}, pannes +{lv['pannes']},"
        f" sous-face des poutres +{lv['sous_face_poutres']} (P47)"
    )
    w(
        f"#   axe d'appui +{lv['axe_appui']}, dessus des chevêtres +{lv['dessus_chevetre']}, axe de l'anneau {lv['axe_anneau']},"
        f" têtes de piles {lv['tete_piles']}, dessus de la semelle {lv['dessus_semelle']}"
    )
    w(
        f"#   poutres principales tube {variant.beam_label} mm (P36) ; anneau {v.ring_b} × {v.ring_h} m (P48) ;"
        f" piles Ø {v.pile_d} m, hauteur libre {variant.pile_height:g} m, 4 têtes encastrées (P46)"
    )
    w(
        f"#   semelle {fx[-1] - fx[0]:.2f} × {fy[-1] - fy[0]:.2f} × {v.footing_t} m (P48) ; sol kn = {v.kn:.4g} N/m³,"
        f" kt = {v.kt:.4g} N/m³ (P19)"
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
    w("# Barres : POU_D_T ; semelle : DKT ; sol : DIS_T (P19).")
    w("MODELE = AFFE_MODELE(")
    w("    MAILLAGE=MAIL,")
    w("    AFFE=(")
    w(
        f'        _F(GROUP_MA={_tuple(BEAM_GROUPS)}, PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),'
    )
    w('        _F(GROUP_MA="SEMELLE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),')
    w('        _F(GROUP_MA="SOL", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),')
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
        "# Repère local : z_l = +Z pour les barres horizontales (VECT_Z), y_l = +X pour les piles."
    )
    w("CARA = AFFE_CARA_ELEM(")
    w("    MODELE=MODELE,")
    w("    POUTRE=(")
    w(
        '        _F(GROUP_MA="POUTRES_PRINC", SECTION="RECTANGLE", CARA=("H", "EP"),'
        f" VALE=({_r(v.beam_side)}, {_r(v.beam_thickness)})),"
    )
    w(
        '        _F(GROUP_MA=("MONTANTS", "DIAGONALES"), SECTION="RECTANGLE", CARA=("H", "EP"),'
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
    w('        _F(GROUP_MA="PILES", CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),')
    w("    ),")
    w(
        f'    COQUE=_F(GROUP_MA="SEMELLE", EPAIS={_r(v.footing_t)}, ANGL_REP=(0.0, 0.0)),'
    )
    w('    DISCRET=_F(GROUP_MA="SOL", CARA="M_T_D_N", VALE=0.0),')
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
        "# P35, P45 : rotule côté quai Y > 0 fixe (X, Y, Z), rotule Y < 0 guidée (X, Z) : seul"
    )
    w(
        "# point fixe en X de la chaîne des travées. LIAISON_SOLIDE : pannes / montants et"
    )
    w(
        "# diagonales (LR_), tête de pile encastrée dans le chevêtre (TP_, P46), angle de"
    )
    w("# l'anneau monolithique (LG_), pied de pile / semelle (PS_).")
    w(
        "# P44, appuis à axe (axe parallèle à Y, point P non maillé) : LIAISON_DDL sur la"
    )
    w(
        "# translation de P portée par un nœud N, u_N + θ_N ∧ (P − N) ; oreilles des deux travées"
    )
    w(
        "# (AX_<appui>_<rive>_1 et _2) : translations de P égales et DRX égales ; oreille 1 et"
    )
    w(
        "# nœud du chevêtre (_K) : Z égal, et Y égal en YP ; X libre (trou oblong). A3 (X = 14,02) :"
    )
    w("# support fixe, Z de P nul, et Y nul en YP.")
    w("CL = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w(
        '    DDL_IMPO=(_F(GROUP_NO="APP_QUAI_YP", DX=0.0, DY=0.0, DZ=0.0), _F(GROUP_NO="APP_QUAI_YM", DX=0.0, DZ=0.0)),'
    )
    w("    LIAISON_SOLIDE=(")
    for lk in solid:
        w(f'        _F(GROUP_NO=("{lk.name}_A", "{lk.name}_B")),')
    w("    ),")
    w("    LIAISON_DDL=(")
    n_relations = 0
    for axis in g.axes:
        w(
            f"        # appui {axis.name} : axe en ({_r(axis.pin[0])}, {_r(axis.pin[1])}, {_r(axis.pin[2])})"
            + (", Y bloqué" if axis.blocks_y else ", Y libre")
        )
        for label, terms in pin_relations(axis):
            w(f"        # {label}")
            w(_ddl_line(terms))
            n_relations += 1
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
        f"# d'influence b de chaque ligne, tablier de {p['LARGEUR_TABLIER']} m, une charge par travée."
    )
    w(
        "CG1 = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))"
    )
    ring_area = v.ring_b * v.ring_h
    pile_area = math.pi * v.pile_d**2 / 4.0
    w(
        f"# P49 : déjaugeage, {v.gamma_water:g} N/m³ × section (barres de béton, N/m) ou × épaisseur"
    )
    w("# (semelle, N/m², FORCE_COQUE en repère global, PAT-005), vers le haut.")
    w("CDEJ = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w("    FORCE_POUTRE=(")
    w(
        f'        _F(GROUP_MA=("CHEVETRES", "LONGRINES"), FZ={_r(v.gamma_water * ring_area)}),  # {v.ring_b} × {v.ring_h} m'
    )
    w(
        f'        _F(GROUP_MA="PILES", FZ={_r(v.gamma_water * pile_area)}),  # Ø {v.pile_d} m'
    )
    w("    ),")
    w(
        f'    FORCE_COQUE=_F(GROUP_MA="SEMELLE", FZ={_r(v.gamma_water * v.footing_t)}),  # e = {v.footing_t} m'
    )
    w(")")
    concepts: dict[str, tuple[str, ...]] = {"G1": ("CG1",), "DEJ": ("CDEJ",)}
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
        "# Accostage : 1 kN/m sur la zone de 1 m de la poutre de rive ; ACN ⊥ au bord vers"
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
    w("# Amarrage : 1 kN au taquet ; AMY ⊥ au bord vers l'extérieur, AMX selon +X.")
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
        "# Harnais D (listing, E20.12) : RP_<cas> rotules du quai, RAM_ et RAP_<cas> oreilles des"
    )
    w(
        "# appuis à axe sur support fixe en X = 14,02 (YM, YP), DS_<cas> déplacements des nœuds"
    )
    w("# de la semelle (efforts des ressorts k·u).")
    tables = (
        ("RP", "REAC_NODA", "APP_QUAI", 'RESULTANTE=("DX", "DY", "DZ")'),
        ("RAM", "REAC_NODA", "AX_A3_YM_1", 'RESULTANTE=("DX", "DY", "DZ")'),
        ("RAP", "REAC_NODA", "AX_A3_YP_1", 'RESULTANTE=("DX", "DY", "DZ")'),
        ("DS", "DEPL", "N_SEMELLE", 'NOM_CMP=("DX", "DY", "DZ")'),
    )
    for case in all_cases(g):
        result = "ELEM" if case in mechanical else case
        where = f'NOM_CAS="{case}"' if case in mechanical else 'TOUT_ORDRE="OUI"'
        for prefix, field, group, extra in tables:
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
        "# 32 déplacements de tous les nœuds, 33 réactions (rotules du quai, appuis à axe : oreilles"
    )
    w("# et nœuds des chevêtres, efforts des relations de l'axe).")
    reac = reaction_groups(g)
    for result in ("ELEM", *THERMAL_CASES):
        for unit, field, where in (
            (31, "EFGE_ELNO", f"GROUP_MA={_tuple(BEAM_GROUPS)}"),
            (32, "DEPL", 'TOUT="OUI"'),
            (33, "REAC_NODA", f"GROUP_NO={_tuple(reac)}"),
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
        "levels_m_ngf": dict(lv),
        "links": {"solide": [lk.name for lk in solid]},
        "pin_relations": n_relations,
        "footing_area_m2": footing_area,
        "concrete_volumes_m3": concrete_volumes(v, g),
        "weights_n": weights(v, g),
        "applied_loads_n": applied_loads(v, g),
    }
    return "\n".join(out) + "\n", report


__all__ = [
    "ALU_GROUPS",
    "BEAM_GROUPS",
    "SPLIT",
    "THERMAL_CASES",
    "Values51bis",
    "all_cases",
    "applied_loads",
    "build_comm",
    "carried",
    "case_label",
    "concrete_volumes",
    "mechanical_cases",
    "pin_relations",
    "reaction_groups",
    "values",
    "weights",
]
