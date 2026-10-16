# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01, lot 51 ter: the whole pontoon, one
parameterised file for every variant (`variantes_lot51ter.yaml`, PONTONS_VARIANTE).

Flat `.comm` written from the data file, the decisions P1 to P59 of the fiche, the
parameters of `maillage_ponton_51ter.py` and the variant. Elementary unit cases only
(linear); the combinations are post-processing (`combinaisons_lot51ter`). Everything
repeated per pier, span, module, zone or cleat is written by a loop over the geometry,
never copied by hand.

From lot 51 bis (`generation_lot51bis`) this lot keeps the pins (P44, P54: LIAISON_DDL
on u_N + θ_N ∧ (P − N)), the pile heads fixed in the ring (P46), the buoyancy DEJ (P49)
and the cases G1, G2, Q, QD, berthing, mooring and temperatures, and changes:

- P53: AVP levels; P58: the whole pontoon, five piers, one footing per pier on its own
  RIGI_PARASOL (one CREA_POI1 occurrence and one POI1 group per footing, CA-034);
- the abutment (X = 0) is the only longitudinal fixed point: YP blocks X, Y, Z, YM
  blocks X, Z; no fixed support at X = 14,02 any more;
- P55: no buoyancy of the aluminium (drained tubes): DEJ acts on the concrete only;
- P56: the houle cases HU and HD of lot 51 bis are replaced by four unit cases of
  1 kPa on the whole deck: HU_TUBES (under the two main beams, 0,20 m each), HU_PANNES
  (under the four purlins, 0,05 m each), HU_PLATELAGE (under the planks, 1,327 m shared
  among the longitudinal members by tributary widths, as G2), HD_TABLIER (on the deck,
  1,895 m, downwards);
- G2, Q, QD and the four houle cases are split into the modules M0 = T1, Mk = PTk +
  T(k+1), M5 = PT5 + PF; the total case is the sum of its module charges;
- 21 berthing zones (start, middle, end of each long span, middle of each small span,
  end of the cantilever) and 20 cleats (two per long span and side);
- ring corners (correction of lot 51 ter): the pieces of tie inside a cap beam
  (ANGLES_ANNEAU) get a concrete without weight (RHO = 0, same stiffness) and no
  buoyancy, so that G1 and DEJ count each m³ of the ring once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation_lot51 import UNIT, _r, _surface_load, _tuple, tube_area
from pontons_alu_01.generation_lot51bis import TRANSLATIONS, _ddl_line, pin_relations
from pontons_alu_01.geometrie_lot51 import SIDES
from pontons_alu_01.geometrie_lot51ter import (
    Geometry51ter,
    geometry,
    half_deck_widths,
    influence_widths,
)
from pontons_alu_01.invariants_lot51ter import corner_pieces
from pontons_alu_01.variantes_lot51ter import Variant51ter, current

G = 9.81
"""m/s², acceleration of gravity turning a unit weight into RHO (CA-048)."""

ALU_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES", "PANNES_SEC", "PANNE_RIVE")
CONCRETE_BEAMS = ("CHEVETRES", "LONGRINES", "PILES")
CONCRETE_GROUPS = (*CONCRETE_BEAMS, "SEMELLE")
BEAM_GROUPS = (*ALU_GROUPS, *CONCRETE_BEAMS)
TA_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES")
"""TA± (jeu A, S2) heats the main beams, posts and diagonals only (P10)."""
HORIZONTAL_GROUPS = (*ALU_GROUPS, "CHEVETRES", "LONGRINES")
THERMAL_CASES = ("TP", "TM", "TAP", "TAM")
SPLIT = ("G2", "Q", "QD", "HU_TUBES", "HU_PANNES", "HU_PLATELAGE", "HD_TABLIER")
"""Cases split by module (consigne § Chargements), the total being their sum."""
WAVE_CASES = ("HU_TUBES", "HU_PANNES", "HU_PLATELAGE", "HD_TABLIER")
BERTHING_DIRECTIONS = ("ACN", "ACX", "ACZ")
MOORING_DIRECTIONS = ("AMY", "AMX")
SHORT = {
    "G2": "G2",
    "Q": "Q",
    "QD": "QD",
    "HU_TUBES": "HUT",
    "HU_PANNES": "HUP",
    "HU_PLATELAGE": "HUL",
    "HD_TABLIER": "HDT",
}
"""Short names of the module charges (concepts of 8 characters at most)."""


@dataclass(frozen=True)
class Values51ter:
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
    purlin_side: float
    purlin_thickness: float
    ring_b: float
    ring_h: float
    pile_d: float
    footing_t: float
    kn: float
    kt: float
    g2: float
    q: float
    width_tube: float
    width_purlin: float
    width_planks: float
    width_deck_top: float
    t_plus: float
    t_minus: float
    ta_plus: float
    ta_minus: float


def values(ctx: ProjectContext, variant: Variant51ter) -> Values51ter:
    """Every number of the data file, the variant and the mesh parameters, converted
    once to m, N, Pa."""
    d = {k: v.value for k, v in ctx.data().items().items()}
    p = geometry(variant.mesh_overrides).parameters

    def f(key: str) -> float:
        value = d[key]
        assert isinstance(value, int | float)
        return float(value)

    return Values51ter(
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
        purlin_side=variant.purlin_side_mm * 1e-3,
        purlin_thickness=variant.purlin_thickness_mm * 1e-3,
        ring_b=float(p["B_ANNEAU"]),
        ring_h=float(p["H_ANNEAU"]),
        pile_d=f("sections_beton.poteau_diametre"),
        footing_t=f("palee_lot51bis.semelle_epaisseur"),
        kn=f("sol.raideur_normale") * 1e3,
        kt=f("sol.raideur_tangentielle") * 1e3,
        g2=f("charges.g2") * 1e3,
        q=f("charges.q") * 1e3,
        width_tube=f("houle_lot51ter.largeur_tube"),
        width_purlin=f("houle_lot51ter.largeur_panne"),
        width_planks=f("houle_lot51ter.largeur_platelage"),
        width_deck_top=f("houle_lot51ter.largeur_tablier_dessus"),
        t_plus=f("charges.t_plus"),
        t_minus=-f("charges.t_moins"),
        ta_plus=f("charges.ta_plus"),
        ta_minus=f("charges.ta_moins"),
    )


# --------------------------------------------------------------------------- cases


def zone_names(g: Geometry51ter) -> list[str]:
    """The 21 berthing zones, in the order of X (one name for both sides)."""
    return list(dict.fromkeys(z.name.removeprefix("ACC_")[:-3] for z in g.zones))


def berthing_cases(g: Geometry51ter) -> list[tuple[str, str, str, str]]:
    """(case, direction, zone, side) of the 126 unit berthing cases."""
    return [
        (f"{d}_{z}_{s}", d, z, s)
        for z in zone_names(g)
        for s, _ in SIDES
        for d in BERTHING_DIRECTIONS
    ]


def mooring_cases(g: Geometry51ter) -> list[tuple[str, str, int, str]]:
    """(case, direction, cleat, side) of the 40 unit mooring cases."""
    return [
        (f"{d}_TQ{n}_{s}", d, n, s)
        for n, _, _ in g.cleats
        for s, _ in SIDES
        for d in MOORING_DIRECTIONS
    ]


def mechanical_cases(g: Geometry51ter) -> list[str]:
    out = ["G1", "DEJ"]
    for base in SPLIT:
        out += [base, *(f"{base}_{m}" for m in g.modules())]
    out += [c for c, *_ in berthing_cases(g)]
    out += [c for c, *_ in mooring_cases(g)]
    return out


def all_cases(g: Geometry51ter) -> list[str]:
    return [*mechanical_cases(g), *THERMAL_CASES]


def case_label(case: str) -> str:
    fixed = {
        "G1": "poids propre (aluminium 27 kN/m³, béton 25 kN/m³ ; angles de l'anneau comptés une fois)",
        "DEJ": "déjaugeage : poussée d'Archimède 10 kN/m³ sur tout le volume de béton des cinq palées, vers le haut (P49)",
        "G2": "G2 = 1,0 kN/m² sur tout le tablier (P8)",
        "Q": "Q = 5 kPa sur tout le tablier",
        "QD": "Q½ = 5 kPa sur la moitié Y > 0 du tablier",
        "HU_TUBES": "houle, 1 kPa vers le haut sous les 2 poutres principales (0,20 m chacune, P56)",
        "HU_PANNES": "houle, 1 kPa vers le haut sous les 4 pannes (0,05 m chacune, P56)",
        "HU_PLATELAGE": "houle, 1 kPa vers le haut sous les planches (1,327 m, largeurs tributaires, P56)",
        "HD_TABLIER": "houle, 1 kPa vers le bas sur le platelage (1,895 m, largeurs tributaires, P56)",
        "TP": "T+ = +46 °C, tout l'aluminium",
        "TM": "T− = −28 °C, tout l'aluminium",
        "TAP": "TA+ = +56 °C, poutres, montants, diagonales (S2)",
        "TAM": "TA− = −23 °C, poutres, montants, diagonales (S2)",
    }
    if case in fixed:
        return fixed[case]
    head, _, tail = case.rpartition("_")
    if head in SPLIT and tail.startswith("M"):
        return f"{fixed[head]} : module {tail} seul"
    direction, *rest = case.split("_")
    if direction in BERTHING_DIRECTIONS:
        zone, side = rest
        what = {
            "ACN": "⊥ au bord vers l'intérieur",
            "ACX": "selon +X",
            "ACZ": "selon +Z",
        }[direction]
        return f"accostage unitaire 1 kN/m sur 1 m, zone {zone}, rive {side}, {what}"
    if direction in MOORING_DIRECTIONS:
        cleat, side = rest
        what = {"AMY": "⊥ au bord vers l'extérieur", "AMX": "selon +X"}[direction]
        return f"amarrage unitaire 1 kN, taquet {cleat} rive {side}, {what}"
    message = f"cas inconnu : {case}"
    raise KeyError(message)


# --------------------------------------------------------------------------- loads


def module_widths(
    v: Values51ter, g: Geometry51ter, base: str, module: str
) -> tuple[float, dict[str, float]]:
    """(pressure in Pa, width carried by each member group in m) of the charge of
    `base` on `module`: FZ = pressure × width on each group (P22, P56)."""
    widths: dict[str, float] = {}
    for span in g.modules()[module]:
        deck = influence_widths(g, span)
        if base in ("G2", "Q", "HU_PLATELAGE", "HD_TABLIER"):
            scale = {
                "G2": 1.0,
                "Q": 1.0,
                "HU_PLATELAGE": v.width_planks / g.parameters["LARGEUR_TABLIER"],
                "HD_TABLIER": v.width_deck_top / g.parameters["LARGEUR_TABLIER"],
            }[base]
            widths.update({k: w * scale for k, w in deck.items()})
        elif base == "QD":
            widths.update(half_deck_widths(g, span))
        elif base == "HU_TUBES":
            widths.update({f"PP_{span}_{s}": v.width_tube for s, _ in SIDES})
        elif base == "HU_PANNES":
            widths.update({k: v.width_purlin for k in deck if k.startswith("PANNE_")})
        else:
            message = f"cas réparti inconnu : {base}"
            raise KeyError(message)
    pressure = {
        "G2": -v.g2,
        "Q": -v.q,
        "QD": -v.q,
        "HU_TUBES": UNIT,
        "HU_PANNES": UNIT,
        "HU_PLATELAGE": UNIT,
        "HD_TABLIER": -UNIT,
    }[base]
    return pressure, widths


def loaded_length(g: Geometry51ter, member: str) -> float:
    return g.member(member).length


def concrete_volumes_by_pier(
    v: Values51ter, g: Geometry51ter
) -> dict[str, dict[str, float]]:
    """Volume of concrete of each family of each pier as modelled (m³): bar lengths ×
    section, the pieces of tie inside a cap beam left out (counted with the cap
    beam), footing area × thickness."""
    ring = v.ring_b * v.ring_h
    pile = math.pi * v.pile_d**2 / 4.0
    corners = corner_pieces(g)
    out: dict[str, dict[str, float]] = {}
    for f in g.footings:

        def inside(x: float, f: Any = f) -> bool:
            return bool(f.xs[0] - 1e-9 <= x <= f.xs[-1] + 1e-9)

        corner_length = sum(
            math.dist(a, b) for a, b, _ in corners if inside(a[0]) and inside(b[0])
        )
        out[f.pier] = {
            "CHEVETRES": ring
            * sum(m.length for m in g.family("CHEVETRES") if m.span == f.pier),
            "LONGRINES": ring
            * (
                sum(m.length for m in g.family("LONGRINES") if m.span == f.pier)
                - corner_length
            ),
            "PILES": pile
            * sum(m.length for m in g.family("PILES") if m.span == f.pier),
            "SEMELLE": v.footing_t * f.area,
        }
    return out


def concrete_volumes(v: Values51ter, g: Geometry51ter) -> dict[str, float]:
    by_pier = concrete_volumes_by_pier(v, g)
    return {
        fam: sum(vol[fam] for vol in by_pier.values())
        for fam in ("CHEVETRES", "LONGRINES", "PILES", "SEMELLE")
    }


def section_areas(v: Values51ter) -> dict[str, float]:
    return {
        "POUTRES_PRINC": tube_area(v.beam_side, v.beam_thickness),
        "MONTANTS": tube_area(v.t150, v.e150),
        "DIAGONALES": tube_area(v.t150, v.e150),
        "PANNES_SEC": tube_area(v.purlin_side, v.purlin_thickness),
        "PANNE_RIVE": tube_area(v.purlin_side, v.purlin_thickness),
    }


def weights(v: Values51ter, g: Geometry51ter) -> dict[str, float]:
    """Self-weight of each family (N), from the data, the variant and the parameters
    (the links carry no mass, the ring corners are counted once)."""
    out = {
        fam: v.gamma_alu * a * sum(m.length for m in g.family(fam))
        for fam, a in section_areas(v).items()
    }
    for fam, vol in concrete_volumes(v, g).items():
        out[fam] = v.gamma_concrete * vol
    return out


def applied_loads(v: Values51ter, g: Geometry51ter) -> dict[str, dict[str, float]]:
    """Applied resultant of each case (N), from the data and the parameters only."""
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    out: dict[str, dict[str, float]] = {
        "G1": {**zero, "DZ": -sum(weights(v, g).values())},
        "DEJ": {**zero, "DZ": v.gamma_water * sum(concrete_volumes(v, g).values())},
    }
    for base in SPLIT:
        total = 0.0
        for module in g.modules():
            pressure, widths = module_widths(v, g, base, module)
            dz = sum(pressure * w * loaded_length(g, k) for k, w in widths.items())
            out[f"{base}_{module}"] = {**zero, "DZ": dz}
            total += dz
        out[base] = {**zero, "DZ": total}
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
        f'_F(GROUP_MA={_tuple(CONCRETE_GROUPS)}, MATER=BETON), _F(GROUP_MA="ANGLES_ANNEAU", MATER=BETON0)),',
        f'    AFFE_VARC=_F(GROUP_MA={_tuple(groups)}, NOM_VARC="TEMP", CHAM_GD=T_{case},'
        " VALE_REF=0.0),",
        ")",
        f"{case} = MECA_STATIQUE(MODELE=MODELE, CHAM_MATER=M_{case}, CARA_ELEM=CARA,"
        ' EXCIT=_F(CHARGE=CL), SOLVEUR=_F(METHODE="MUMPS"))',
    ]


def reaction_groups(g: Geometry51ter) -> tuple[str, ...]:
    """Node groups whose REAC_NODA is exported (unit 33): the abutment supports and
    every node of a pin relation (ears and cap beam nodes)."""
    out = ["APP_CULEE"]
    for a in g.axes:
        out += [a.ear_group(k) for k in range(1, len(a.ears) + 1)]
        out.append(a.cap_group)
    return tuple(dict.fromkeys(out))


HARNESS_TABLES = (
    ("R", "REAC_NODA", "APP_CULEE", 'RESULTANTE=("DX", "DY", "DZ")'),
    ("S", "DEPL", "N_SEMELLE", 'NOM_CMP=("DX", "DY", "DZ")'),
)
"""Harness D (listing, E20.12): R<cas> abutment reactions, S<cas> displacements of the
footing nodes (forces k·u of the soil springs). Titles of 16 characters at most
(IMPR_TABLE truncates the title)."""


# --------------------------------------------------------------------------- .comm


def build_comm(  # noqa: PLR0915 -- un .comm écrit d'un trait, section par section
    ctx: ProjectContext, *, mesh_label: str, variant: Variant51ter | None = None
) -> tuple[str, dict[str, Any]]:
    variant = variant or current()
    v = values(ctx, variant)
    g = geometry(variant.mesh_overrides)
    p = g.parameters
    lv = g.levels
    solid = [lk for lk in g.links if lk.kind in ("solide", "tete_pile", "longrine")]
    for case in all_cases(g):
        for prefix, *_ in HARNESS_TABLES:
            if len(prefix + case) > 16:
                message = f"intitulé {prefix}{case} de plus de 16 caractères"
                raise ValueError(message)
    out: list[str] = []
    w = out.append
    w(
        "# PONTONS-ALU-01, lot 51 ter : ponton intégral (culée, 5 palées, 5 grandes travées,"
    )
    w(
        "# porte-à-faux d'extrémité), cotes de l'AVP, appuis articulés à axe. Calcul linéaire,"
    )
    w("# cas élémentaires unitaires.")
    w(f"# Variante {variant.code} : {variant.description}.")
    w(
        f"# Code_Aster 17.4. Unités : m, N, Pa, °C. Maillage : {mesh_label} (maillage_ponton_51ter.py)."
    )
    w(
        "# Généré par pontons_alu_01.generation_lot51ter à partir de la fiche (P1 à P59), des données"
    )
    w(
        "# et de variantes_lot51ter.yaml : régénérer plutôt qu'éditer. Combinaisons et exports :"
    )
    w("# post-traitement (scripts/lot51ter.py).")
    w("#")
    w("# Géométrie et cotes (rappel, m NGF)")
    w(
        "#   travées : "
        + " ; ".join(f"{s.name} {s.x0:g} → {s.x1:g}" for s in g.spans)
        + " (m, X depuis la ligne d'appui de la culée)"
    )
    w(
        f"#   B = {p['B']} m, tablier {p['LARGEUR_TABLIER']} m (P35) ; dessus +{lv['dessus_tablier']}, poutres +{lv['poutres']},"
        f" pannes +{lv['pannes']} (P53)"
    )
    w(
        f"#   axe d'appui +{lv['axe_appui']} (P54), dessus des chevêtres +{lv['dessus_chevetre']}, axe de l'anneau +{lv['axe_anneau']},"
        f" têtes de piles +{lv['tete_piles']}"
    )
    w(
        "#   piles (hauteur libre, m) : "
        + " ; ".join(
            f"{f.pier} {h:g} (plan moyen de la semelle {f.z:g})"
            for f, h in zip(g.footings, variant.pile_heights, strict=True)
        )
    )
    w(
        f"#   poutres principales tube {variant.beam_label} mm, pannes et panne de rive tube {variant.purlin_label} mm ;"
        f" anneau {v.ring_b} × {v.ring_h} m ; piles Ø {v.pile_d} m, 4 têtes encastrées par palée (P46)"
    )
    w(
        f"#   semelles {p['COTE_SEMELLE']:.2f} × {p['COTE_SEMELLE']:.2f} × {v.footing_t} m (P48) ; sol kn = {v.kn:.4g} N/m³,"
        f" kt = {v.kt:.4g} N/m³ (P19)"
    )
    w("")
    w('DEBUT(CODE="OUI")')
    w("")
    w("# ---------------------------------------------------------------- 1. MAILLAGE")
    w('MAIL0 = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)')
    w(
        "# Appui élastique réparti (P19) : une maille POI1 par nœud de chaque semelle (ssls135a),"
    )
    w("# un groupe POI1 par semelle (CA-034 : une maille par nœud).")
    w("MAIL = CREA_MAILLAGE(")
    w("    MAILLAGE=MAIL0,")
    w(
        "    CREA_POI1=("
        + ", ".join(
            f'_F(NOM_GROUP_MA="{f.poi1}", GROUP_MA="{f.group}")' for f in g.footings
        )
        + "),"
    )
    w(")")
    w(
        'MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=_F(GROUP_MA="SEMELLE", NOM="N_SEMELLE"))'
    )
    soil = tuple(f.poi1 for f in g.footings)
    w("")
    w("# ---------------------------------------------------------------- 2. MODÈLE")
    w("# Barres : POU_D_T ; semelles : DKT ; sol : DIS_T (P19).")
    w("MODELE = AFFE_MODELE(")
    w("    MAILLAGE=MAIL,")
    w("    AFFE=(")
    w(
        f'        _F(GROUP_MA={_tuple(BEAM_GROUPS)}, PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),'
    )
    w('        _F(GROUP_MA="SEMELLE", PHENOMENE="MECANIQUE", MODELISATION="DKT"),')
    w(
        f'        _F(GROUP_MA={_tuple(soil)}, PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),'
    )
    w("    ),")
    w(")")
    w("")
    w("# ---------------------------------------------------------------- 3. MATÉRIAUX")
    w(
        "# RHO = γ / g (CA-048). Températures : aluminium seulement (P10). BETON0 : angles de l'anneau"
    )
    w(
        "# (morceaux de longrine dans l'épaisseur d'un chevêtre), même raideur, sans poids : chaque"
    )
    w("# m³ de l'anneau n'est pesé qu'une fois (correction du lot 51 ter).")
    w(
        f"ALU = DEFI_MATERIAU(ELAS=_F(E={_r(v.e_alu)}, NU={_r(v.nu_alu)}, "
        f"RHO={_r(v.gamma_alu / G)}, ALPHA={_r(v.alpha_alu)}))"
    )
    w(
        f"BETON = DEFI_MATERIAU(ELAS=_F(E={_r(v.e_concrete)}, NU={_r(v.nu_concrete)}, "
        f"RHO={_r(v.gamma_concrete / G)}))"
    )
    w(
        f"BETON0 = DEFI_MATERIAU(ELAS=_F(E={_r(v.e_concrete)}, NU={_r(v.nu_concrete)}, RHO=0.0))"
    )
    w("CHMAT = AFFE_MATERIAU(")
    w("    MAILLAGE=MAIL,")
    w(
        f'    AFFE=(_F(GROUP_MA={_tuple(ALU_GROUPS)}, MATER=ALU), _F(GROUP_MA={_tuple(CONCRETE_GROUPS)}, MATER=BETON), _F(GROUP_MA="ANGLES_ANNEAU", MATER=BETON0)),'
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
        f'        _F(GROUP_MA=("PANNES_SEC", "PANNE_RIVE"), SECTION="RECTANGLE", CARA=("H", "EP"), VALE=({_r(v.purlin_side)}, {_r(v.purlin_thickness)})),'
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
        f'        _F(GROUP_MA={_tuple(HORIZONTAL_GROUPS)}, CARA="VECT_Z", VALE=(0.0, 0.0, 1.0)),'
    )
    w('        _F(GROUP_MA="PILES", CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),')
    w("    ),")
    w(
        f'    COQUE=_F(GROUP_MA="SEMELLE", EPAIS={_r(v.footing_t)}, ANGL_REP=(0.0, 0.0)),'
    )
    w(f'    DISCRET=_F(GROUP_MA={_tuple(soil)}, CARA="M_T_D_N", VALE=0.0),')
    w(
        "    # P19 : raideurs globales k × surface de chaque semelle, réparties au prorata des"
    )
    w("    # surfaces (U4.42.01), une occurrence par semelle.")
    w("    RIGI_PARASOL=(")
    for f in g.footings:
        cx, cy, cz = f.centre
        w(
            f'        _F(GROUP_MA="{f.group}", GROUP_MA_POI1="{f.poi1}", COEF_GROUP=1.0, CARA="K_T_D_N",'
            f" VALE=({_r(v.kt * f.area)}, {_r(v.kt * f.area)}, {_r(v.kn * f.area)}),"
            f" COOR_CENTRE=({_r(cx)}, {_r(cy)}, {_r(cz)})),"
        )
    w("    ),")
    w(")")
    w("")
    w(
        "# ---------------------------------------------------------------- 5. LIAISONS ET APPUIS"
    )
    w(
        "# Culée (X = 0, P58) : seul point fixe longitudinal ; axe YP : X, Y, Z bloqués ; axe YM :"
    )
    w(
        "# X, Z bloqués. LIAISON_SOLIDE : pannes / montants, diagonales et panne de rive (LR_),"
    )
    w(
        "# têtes de piles encastrées dans les chevêtres (TP_, P46), angles de l'anneau monolithique"
    )
    w("# (LG_), pieds de piles / semelles (PS_).")
    w(
        "# P44, P54, appuis à axe (axe parallèle à Y, point P non maillé, Z = +1,16) : LIAISON_DDL sur"
    )
    w(
        "# la translation de P portée par un nœud N, u_N + θ_N ∧ (P − N) ; oreilles des deux travées"
    )
    w(
        "# (AX_<palée><chevêtre>_<rive>_1 et _2) : translations de P égales et DRX égales ; oreille 1 et"
    )
    w(
        "# nœud du chevêtre (_K) : Z égal, et Y égal en YP ; X libre (trou oblong). Chevêtre C2 de la"
    )
    w(
        "# dernière palée : une seule oreille (petite travée continue avec le porte-à-faux)."
    )
    w("CL = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w(
        '    DDL_IMPO=(_F(GROUP_NO="APP_CULEE_YP", DX=0.0, DY=0.0, DZ=0.0), _F(GROUP_NO="APP_CULEE_YM", DX=0.0, DZ=0.0)),'
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
            + f", {len(axis.ears)} oreille(s)"
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
        "CG1 = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))"
    )
    ring_area = v.ring_b * v.ring_h
    pile_area = math.pi * v.pile_d**2 / 4.0
    w(
        "# P49 : déjaugeage du béton seul (P55 : tubes percés, aucune flottabilité de l'aluminium),"
    )
    w(
        f"# {v.gamma_water:g} N/m³ × section (barres de béton, N/m ; angles de l'anneau exclus) ou × épaisseur"
    )
    w("# (semelles, N/m², FORCE_COQUE en repère global, PAT-005), vers le haut.")
    w("CDEJ = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w("    FORCE_POUTRE=(")
    w(
        f'        _F(GROUP_MA=("CHEVETRES", "LONGRINES_COURANT"), FZ={_r(v.gamma_water * ring_area)}),  # {v.ring_b} × {v.ring_h} m'
    )
    w(
        f'        _F(GROUP_MA="PILES", FZ={_r(v.gamma_water * pile_area)}),  # Ø {v.pile_d} m'
    )
    w("    ),")
    w(
        f'    FORCE_COQUE=_F(GROUP_MA="SEMELLE", FZ={_r(v.gamma_water * v.footing_t)}),  # e = {v.footing_t} m'
    )
    w(")")
    w(
        "# Actions réparties (P22, P56) : FORCE_POUTRE sur les barres longitudinales, FZ = pression ×"
    )
    w(
        "# largeur portée par chaque barre ; une charge par module (M0 = T1, Mk = PTk + T(k+1),"
    )
    w(
        f"# M{len(g.footings)} = PT{len(g.footings)} + PF) ; le cas total est la somme de ses modules."
    )
    concepts: dict[str, tuple[str, ...]] = {"G1": ("CG1",), "DEJ": ("CDEJ",)}
    for base in SPLIT:
        names = []
        for module in g.modules():
            name = f"C{SHORT[base]}{module}"
            pressure, widths = module_widths(v, g, base, module)
            w(f"# {base}, module {module} ({' + '.join(g.modules()[module])})")
            out.extend(_surface_load(name, pressure, widths))
            concepts[f"{base}_{module}"] = (name,)
            names.append(name)
        concepts[base] = tuple(names)
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
        name = f"CAC{k:03d}"
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
    w("# des charges de ses modules.")
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
        "# Harnais D (listing, E20.12) : R<cas> réactions de la culée, S<cas> déplacements des nœuds"
    )
    w("# des cinq semelles (efforts des ressorts k·u).")
    for case in all_cases(g):
        result = "ELEM" if case in mechanical else case
        where = f'NOM_CAS="{case}"' if case in mechanical else 'TOUT_ORDRE="OUI"'
        for prefix, field, group, extra in HARNESS_TABLES:
            w(
                f'T{prefix} = POST_RELEVE_T(ACTION=_F(OPERATION="EXTRACTION", INTITULE="{prefix}{case}",'
                f' RESULTAT={result}, NOM_CHAM="{field}", {where}, GROUP_NO="{group}", {extra}))'
            )
            w(f'IMPR_TABLE(TABLE=T{prefix}, UNITE=6, FORMAT_R="E20.12")')
            w(f"DETRUIRE(NOM=T{prefix})")
    w(
        "# Tables d'export (E25.16, 17 chiffres) : unité 31 efforts des barres (EFGE_ELNO),"
    )
    w(
        "# 32 déplacements de tous les nœuds, 33 réactions (culée, appuis à axe : oreilles et nœuds"
    )
    w("# des chevêtres, efforts des relations de l'axe).")
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
        "spans": [s.__dict__ for s in g.spans],
        "footings": [
            {"pier": f.pier, "z_mid": f.z, "area_m2": f.area, "centre": f.centre}
            for f in g.footings
        ],
        "links": {"solide": [lk.name for lk in solid]},
        "pin_relations": n_relations,
        "concrete_volumes_m3": concrete_volumes(v, g),
        "concrete_volumes_by_pier_m3": concrete_volumes_by_pier(v, g),
        "weights_n": weights(v, g),
        "applied_loads_n": applied_loads(v, g),
    }
    return "\n".join(out) + "\n", report


__all__ = [
    "ALU_GROUPS",
    "BEAM_GROUPS",
    "HARNESS_TABLES",
    "SPLIT",
    "THERMAL_CASES",
    "TRANSLATIONS",
    "WAVE_CASES",
    "Values51ter",
    "all_cases",
    "applied_loads",
    "berthing_cases",
    "build_comm",
    "case_label",
    "concrete_volumes",
    "concrete_volumes_by_pier",
    "mechanical_cases",
    "module_widths",
    "mooring_cases",
    "reaction_groups",
    "section_areas",
    "values",
    "weights",
    "zone_names",
]
