# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01 (lot 50).

MM asked for a `.comm` he can read and edit, with a Python parameter block and loops
instead of unrolled lists. The trunk reads a production `.comm` with its static parser
(`aster_expert.parsing.comm_parser`): a name used as a value (`E=E_ALU`) or a command
inside a loop is « dynamic », so the level B validation would be partial and the
deliverables chain (`aster_expert.livrables.inventaire`) would refuse the file. The
fallback MM accepted is kept: the generator writes a flat `.comm`, in the order and with
the section titles MM asked for, every repeated item on one line, the parameters
recalled in the header. Everything comes from the data file, the fiche (P1 to P23) and
the parameter block of `maillage_pontons.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.geometrie import (
    Geometry,
    geometry,
    half_deck_widths,
    influence_widths,
)

G = 9.81
"""m/s², acceleration of gravity turning a unit weight into RHO (CA-048)."""

ALU_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES", "PANNES_SEC", "SUPPORTS")
CONCRETE_GROUPS = ("CHEVETRE", "POTEAUX", "SEMELLE")
BEAM_GROUPS = (*ALU_GROUPS, "CHEVETRE", "POTEAUX")
TA_GROUPS = ("POUTRES_PRINC", "MONTANTS", "DIAGONALES")
"""Jeu A (P10): S2 heats the main beams, posts and diagonals only."""


@dataclass(frozen=True)
class Values:
    e_alu: float
    nu_alu: float
    alpha_alu: float
    gamma_alu: float
    e_concrete: float
    nu_concrete: float
    gamma_concrete: float
    pp_area: float
    pp_iy: float
    pp_iz: float
    pp_jx: float
    pp_avz: float
    t150: float
    e150: float
    t50: float
    e50: float
    cap_b: float
    cap_h: float
    post_d: float
    footing_t: float
    kn: float
    kt: float
    g2: float
    q: float
    wave: float
    mooring: float
    berthing: float
    berthing_acc: float
    t_plus: float
    t_minus: float
    ta_plus: float
    ta_minus: float


def values(ctx: ProjectContext) -> Values:
    """Every number of the data file, converted once to m, N, Pa."""
    d = {k: v.value for k, v in ctx.data().items().items()}

    def f(key: str) -> float:
        value = d[key]
        assert isinstance(value, int | float)
        return float(value)

    return Values(
        e_alu=f("aluminium.module_young") * 1e6,
        nu_alu=f("aluminium.coefficient_poisson"),
        alpha_alu=f("aluminium.dilatation") * 1e-6,
        gamma_alu=f("aluminium.poids_volumique") * 1e3,
        e_concrete=f("beton.module_young") * 1e9,
        nu_concrete=f("beton.coefficient_poisson"),
        gamma_concrete=f("beton.poids_volumique") * 1e3,
        pp_area=f("poutres_principales.aire") * 1e-6,
        pp_iy=f("poutres_principales.inertie_forte") * 1e-12,
        pp_iz=f("poutres_principales.inertie_faible") * 1e-12,
        pp_jx=f("poutres_principales.inertie_torsion") * 1e-8,
        pp_avz=f("poutres_principales.aire_cisaillement_z") * 1e-4,
        t150=f("tubes_150.cote") * 1e-3,
        e150=f("tubes_150.epaisseur") * 1e-3,
        t50=f("tubes_50.cote") * 1e-3,
        e50=f("tubes_50.epaisseur") * 1e-3,
        cap_b=f("sections_beton.chevetre_largeur"),
        cap_h=f("sections_beton.chevetre_hauteur"),
        post_d=f("sections_beton.poteau_diametre"),
        footing_t=f("sections_beton.semelle_epaisseur"),
        kn=f("sol.raideur_normale") * 1e3,
        kt=f("sol.raideur_tangentielle") * 1e3,
        g2=f("charges.g2") * 1e3,
        q=f("charges.q") * 1e3,
        wave=f("charges.houle_unitaire") * 1e3,
        mooring=f("charges.amarrage") * 1e3,
        berthing=f("charges.accostage") * 1e3,
        berthing_acc=f("charges.accostage_accidentel") * 1e3,
        t_plus=f("charges.t_plus"),
        t_minus=-f("charges.t_moins"),
        ta_plus=f("charges.ta_plus"),
        ta_minus=f("charges.ta_moins"),
    )


MECHANICAL_CASES = ("G1", "G2", "Q", "QD", "HU", "HD", "AMM", "AMP", "ACM", "ACP")
ACCIDENTAL_CASES = ("AAM", "AAP")
THERMAL_CASES = ("TP", "TM", "TAP", "TAM")
ALL_CASES = (*MECHANICAL_CASES, *ACCIDENTAL_CASES, *THERMAL_CASES)
CASE_LABELS = {
    "G1": "poids propre (aluminium 27 kN/m³, béton armé 25 kN/m³)",
    "G2": "G2 = 1,0 kN/m² sur tout le tablier (P8, P22)",
    "Q": "Q = 5 kPa sur tout le tablier",
    "QD": "Q½ = 5 kPa sur la moitié Y > 0",
    "HU": "houle, 1 kPa vers le haut",
    "HD": "houle, 1 kPa vers le bas",
    "AMM": "amarrage 2 × 8 kN, poutre Y = −0,75, vers −Y",
    "AMP": "amarrage 2 × 8 kN, poutre Y = +0,75, vers +Y",
    "ACM": "accostage 16 kN/m, poutre Y = −0,75, vers +Y",
    "ACP": "accostage 16 kN/m, poutre Y = +0,75, vers −Y",
    "AAM": "accostage accidentel 77 kN/m, poutre Y = −0,75, vers +Y",
    "AAP": "accostage accidentel 77 kN/m, poutre Y = +0,75, vers −Y",
    "TP": "T+ = +46 °C, tout l'aluminium (jeu B)",
    "TM": "T− = −28 °C, tout l'aluminium (jeu B)",
    "TAP": "TA+ = +56 °C, poutres, montants, diagonales (jeu A, S2)",
    "TAM": "TA− = −23 °C, poutres, montants, diagonales (jeu A, S2)",
}

PP_AY_HYPOTHESIS = "AY = AZ"
"""Avy of the MP1200 is given nowhere (D3): AY is taken equal to AZ, a provisional
hypothesis reported to MM (horizontal shear flexibility of the main beams)."""


def _r(x: float) -> str:
    return repr(float(x))


def _tuple(items: tuple[str, ...] | list[str]) -> str:
    return (
        "("
        + ", ".join(f'"{i}"' for i in items)
        + ("," if len(items) == 1 else "")
        + ")"
    )


def weights(v: Values, g: Geometry) -> dict[str, float]:
    """Self-weight of each family (N), from the data and the parameters."""
    a150 = v.t150**2 - (v.t150 - 2 * v.e150) ** 2
    a50 = v.t50**2 - (v.t50 - 2 * v.e50) ** 2
    area = {
        "POUTRES_PRINC": v.pp_area,
        "MONTANTS": a150,
        "DIAGONALES": a150,
        "SUPPORTS": a150,
        "PANNES_SEC": a50,
    }
    out = {
        fam: v.gamma_alu * area[fam] * sum(m.length for m in g.family(fam))
        for fam in area
    }
    out["CHEVETRE"] = v.gamma_concrete * v.cap_b * v.cap_h * g.member("CHEVETRE").length
    out["POTEAUX"] = (
        v.gamma_concrete
        * math.pi
        * v.post_d**2
        / 4.0
        * sum(m.length for m in g.family("POTEAUX"))
    )
    fx, fy = g.footing_x, g.footing_y
    out["SEMELLE"] = (
        v.gamma_concrete * v.footing_t * (fx[-1] - fx[0]) * (fy[-1] - fy[0])
    )
    return out


def applied_loads(v: Values, g: Geometry) -> dict[str, dict[str, float]]:
    """Applied resultant of each case (N), from the data and the parameters only."""
    span = g.parameters["L"]
    width = sum(influence_widths(g).values())
    half = sum(half_deck_widths(g).values())
    x0, x1 = g.parameters["X_ACCOSTAGE"]
    n_moor = len(g.parameters["X_AMARRAGE"])
    zero = {"DX": 0.0, "DY": 0.0, "DZ": 0.0}
    out = {
        "G1": {**zero, "DZ": -sum(weights(v, g).values())},
        "G2": {**zero, "DZ": -v.g2 * width * span},
        "Q": {**zero, "DZ": -v.q * width * span},
        "QD": {**zero, "DZ": -v.q * half * span},
        "HU": {**zero, "DZ": v.wave * width * span},
        "HD": {**zero, "DZ": -v.wave * width * span},
        "AMM": {**zero, "DY": -v.mooring * n_moor},
        "AMP": {**zero, "DY": v.mooring * n_moor},
        "ACM": {**zero, "DY": v.berthing * (x1 - x0)},
        "ACP": {**zero, "DY": -v.berthing * (x1 - x0)},
        "AAM": {**zero, "DY": v.berthing_acc * (x1 - x0)},
        "AAP": {**zero, "DY": -v.berthing_acc * (x1 - x0)},
    }
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
    """CA-054: TEMP field on the beams, AFFE_VARC with VALE_REF = 0 (ΔT given)."""
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


def _outputs(result: str, case: str, *, multiple: bool) -> list[str]:
    """Tables read by the level D harness: resultant of the quay supports, spring
    displacements of the footing (CA-036: only blocked components are summed)."""
    where = f'NOM_CAS="{case}"' if multiple else 'TOUT_ORDRE="OUI"'
    return [
        f'T_RP_{case} = POST_RELEVE_T(ACTION=_F(OPERATION="EXTRACTION", INTITULE="RP_{case}",'
        f' RESULTAT={result}, NOM_CHAM="REAC_NODA", {where}, GROUP_NO="APP_QUAI",'
        ' RESULTANTE=("DX", "DY", "DZ")))',
        f'IMPR_TABLE(TABLE=T_RP_{case}, UNITE=6, FORMAT_R="E20.12")',
        f'T_DS_{case} = POST_RELEVE_T(ACTION=_F(OPERATION="EXTRACTION", INTITULE="DS_{case}",'
        f' RESULTAT={result}, NOM_CHAM="DEPL", {where}, GROUP_NO="N_SEMELLE",'
        ' NOM_CMP=("DX", "DY", "DZ")))',
        f'IMPR_TABLE(TABLE=T_DS_{case}, UNITE=6, FORMAT_R="E20.12")',
    ]


def build_comm(ctx: ProjectContext, *, mesh_label: str) -> tuple[str, dict[str, Any]]:
    v = values(ctx)
    g = geometry()
    p = g.parameters
    widths = influence_widths(g)
    half = half_deck_widths(g)
    fx, fy = g.footing_x, g.footing_y
    footing_area = (fx[-1] - fx[0]) * (fy[-1] - fy[0])
    centre = ((fx[0] + fx[-1]) / 2.0, (fy[0] + fy[-1]) / 2.0, g.footing_z)
    pp_az = v.pp_area / v.pp_avz
    out: list[str] = []
    w = out.append
    w(
        "# PONTONS-ALU-01 : une travée de panne (passerelle d'accès sur pieux) en aluminium"
    )
    w("# soudé, calcul PRO (lot 50). Code_Aster 17.4. Unités : m, N, Pa, °C.")
    w(
        f"# Maillage : {mesh_label}, produit par maillage_pontons.py (paramètres en tête)."
    )
    w(
        "# Généré par pontons_alu_01.generation à partir de la fiche (décisions P1 à P23 de"
    )
    w(
        "# MM), des données (donnees/pontons_alu_01_model_data.yaml) et des paramètres du"
    )
    w(
        "# script de maillage : régénérer plutôt qu'éditer (aster-expert projet pontons_alu_01"
    )
    w(
        "# generer). Cas élémentaires seulement ; combinaisons et livrables : post-traitement."
    )
    w("#")
    w("# Paramètres (rappel)")
    w(
        f"#   L = {p['L']} m (P1), B = {p['B']} m (P2), plan moyen +{g.deck_z} NGF, pannes +{g.purlin_z} (P7, P21)"
    )
    w(
        f"#   aluminium E = {v.e_alu:.4g} Pa, ν = {v.nu_alu}, α = {v.alpha_alu:.3g} /°C, γ = {v.gamma_alu:.0f} N/m³ (D3)"
    )
    w(
        f"#   béton E = {v.e_concrete:.4g} Pa, ν = {v.nu_concrete}, γ = {v.gamma_concrete:.0f} N/m³ (P20, D4)"
    )
    w(
        f"#   sol kn = {v.kn:.4g} N/m³, kt = {v.kt:.4g} N/m³ sous {footing_area:.4f} m² (P19)"
    )
    w(
        f"#   G2 = {v.g2:.0f} Pa, Q = {v.q:.0f} Pa, houle unitaire {v.wave:.0f} Pa, amarrage {v.mooring:.0f} N,"
    )
    w(f"#   accostage {v.berthing:.0f} / {v.berthing_acc:.0f} N/m (P8, P9, P13, D4)")
    w(
        f"#   ΔT : T+ {v.t_plus:+g}, T− {v.t_minus:+g} (jeu B), TA+ {v.ta_plus:+g}, TA− {v.ta_minus:+g} (jeu A) °C (P10)"
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
    w("# Barres : poutres de Timoshenko 3D (POU_D_T) ; semelle : DKT ; sol : DIS_T.")
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
        "# Poutres principales MP1200 (P4, D3) : IY = inertie forte (y_l horizontal), AZ = A/Avz ;"
    )
    w(
        f"# Avy non donné : {PP_AY_HYPOTHESIS} (hypothèse provisoire, à confirmer par MM)."
    )
    w(
        "# Tubes carrés à angles vifs (D3) : A, I et JX (Bredt) calculés par Code_Aster (U4.42.01)."
    )
    w(
        "# Repère local : z_l = +Z pour les barres horizontales (VECT_Z), y_l = +X pour les verticales."
    )
    w("CARA = AFFE_CARA_ELEM(")
    w("    MODELE=MODELE,")
    w("    POUTRE=(")
    w(
        '        _F(GROUP_MA="POUTRES_PRINC", SECTION="GENERALE", CARA=("A", "IY", "IZ", "JX", "AY", "AZ"),'
        f" VALE=({_r(v.pp_area)}, {_r(v.pp_iy)}, {_r(v.pp_iz)}, {_r(v.pp_jx)}, {_r(pp_az)}, {_r(pp_az)})),"
    )
    w(
        '        _F(GROUP_MA=("MONTANTS", "DIAGONALES", "SUPPORTS"), SECTION="RECTANGLE", CARA=("H", "EP"),'
        f" VALE=({_r(v.t150)}, {_r(v.e150)})),"
    )
    w(
        f'        _F(GROUP_MA="PANNES_SEC", SECTION="RECTANGLE", CARA=("H", "EP"), VALE=({_r(v.t50)}, {_r(v.e50)})),'
    )
    w(
        f'        _F(GROUP_MA="CHEVETRE", SECTION="RECTANGLE", CARA=("HY", "HZ"), VALE=({_r(v.cap_b)}, {_r(v.cap_h)})),'
    )
    w(
        f'        _F(GROUP_MA="POTEAUX", SECTION="CERCLE", CARA=("R",), VALE=({_r(v.post_d / 2.0)},)),'
    )
    w("    ),")
    w("    ORIENTATION=(")
    w(
        f"        _F(GROUP_MA={_tuple(('POUTRES_PRINC', 'MONTANTS', 'DIAGONALES', 'PANNES_SEC', 'CHEVETRE'))},"
        ' CARA="VECT_Z", VALE=(0.0, 0.0, 1.0)),'
    )
    w(
        '        _F(GROUP_MA=("SUPPORTS", "POTEAUX"), CARA="VECT_Y", VALE=(1.0, 0.0, 0.0)),'
    )
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
        "# P5 : rotules fixes côté quai (translations bloquées). P6, P7, P18 : liaisons rigides"
    )
    w(
        "# LIAISON_SOLIDE (U4.44.01) panne / montant ou diagonale (LR_01 à LR_44), tête de profilé"
    )
    w(
        "# support / tablier, tête de poteau / axe du chevêtre, pied de poteau / plan moyen de la"
    )
    w(
        "# semelle. P18 : pied de profilé support articulé sur le chevêtre, bras rigide de"
    )
    w(
        "# l'axe du chevêtre au dessus du chevêtre : u_S = u_C + θ_C ∧ (0, 0, h) (LIAISON_DDL)."
    )
    n_links = len(g.links)
    names = [f'_F(GROUP_NO="LR_{i:02d}")' for i in range(1, n_links + 1)]
    h = p["Z_SUPPORT_BAS"] - p["Z_CHEVETRE"]
    w("CL = AFFE_CHAR_MECA(")
    w("    MODELE=MODELE,")
    w('    DDL_IMPO=_F(GROUP_NO="APP_QUAI", DX=0.0, DY=0.0, DZ=0.0),')
    w("    LIAISON_SOLIDE=(")
    for k in range(0, n_links, 6):
        w("        " + ", ".join(names[k : k + 6]) + ",")
    w("    ),")
    w("    LIAISON_DDL=(")
    for k in range(1, len(g.hinges) + 1):
        s, c = f"ROT_S{k}", f"ROT_C{k}"
        w(
            f'        _F(GROUP_NO=("{s}", "{c}", "{c}"), DDL=("DX", "DX", "DRY"), COEF_MULT=(1.0, -1.0, {_r(-h)}), COEF_IMPO=0.0),'
        )
        w(
            f'        _F(GROUP_NO=("{s}", "{c}", "{c}"), DDL=("DY", "DY", "DRX"), COEF_MULT=(1.0, -1.0, {_r(h)}), COEF_IMPO=0.0),'
        )
        w(
            f'        _F(GROUP_NO=("{s}", "{c}"), DDL=("DZ", "DZ"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),'
        )
    w("    ),")
    w(")")
    w("")
    w(
        "# ---------------------------------------------------------------- 6. CAS DE CHARGE"
    )
    w(
        "# D4. Actions de surface (P22) : FORCE_POUTRE sur les barres longitudinales, largeur"
    )
    w(
        f"# d'influence b de chaque ligne, tablier limité aux axes des poutres principales (Σ b = {sum(widths.values()):.3f} m)."
    )
    w(
        "CH_G1 = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))"
    )
    out.extend(_surface_load("CH_G2", -v.g2, widths))
    out.extend(_surface_load("CH_Q", -v.q, widths))
    out.extend(_surface_load("CH_QD", -v.q, half))
    out.extend(_surface_load("CH_HU", v.wave, widths))
    out.extend(_surface_load("CH_HD", -v.wave, widths))
    w(
        "# P13 : amarrage vers l'extérieur, accostage vers l'intérieur, sur une poutre principale."
    )
    w(
        f'CH_AMM = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_NODALE=_F(GROUP_NO="AMAR_YM", FY={_r(-v.mooring)}))'
    )
    w(
        f'CH_AMP = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_NODALE=_F(GROUP_NO="AMAR_YP", FY={_r(v.mooring)}))'
    )
    w(
        f'CH_ACM = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA="ACC_YM", FY={_r(v.berthing)}))'
    )
    w(
        f'CH_ACP = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA="ACC_YP", FY={_r(-v.berthing)}))'
    )
    w(
        f'CH_AAM = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA="ACC_YM", FY={_r(v.berthing_acc)}))'
    )
    w(
        f'CH_AAP = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA="ACC_YP", FY={_r(-v.berthing_acc)}))'
    )
    w("")
    w(
        "# ---------------------------------------------------------------- 7. RÉSOLUTION"
    )
    w("# Cas mécaniques : une factorisation (MACRO_ELAS_MULT, CA-055).")
    w("ELEM = MACRO_ELAS_MULT(")
    w("    MODELE=MODELE,")
    w("    CHAM_MATER=CHMAT,")
    w("    CARA_ELEM=CARA,")
    w("    CHAR_MECA_GLOBAL=CL,")
    w("    CAS_CHARGE=(")
    for case in (*MECHANICAL_CASES, *ACCIDENTAL_CASES):
        w(
            f'        _F(NOM_CAS="{case}", CHAR_MECA=CH_{case}, OPTION="SANS"),  # {CASE_LABELS[case]}'
        )
    w("    ),")
    w('    SOLVEUR=_F(METHODE="MUMPS", POSTTRAITEMENTS="FORCE"),')
    w(")")
    # Semelle d'abord : EFGE_NOEU après un EFGE_ELNO restreint aux barres n'est pas
    # calculé (alarme CALCULEL2_89, lot 50) ; ordre de l'estacade (lot 47).
    w('ELEM = CALC_CHAMP(reuse=ELEM, RESULTAT=ELEM, GROUP_MA="SEMELLE", CONTRAINTE=("EFGE_NOEU",))')
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
        w(f"# {CASE_LABELS[case]}")
        out.extend(_thermal(case, dt, groups))
        w(
            f'{case} = CALC_CHAMP(reuse={case}, RESULTAT={case}, GROUP_MA="SEMELLE", CONTRAINTE=("EFGE_NOEU",))'
        )
        w(
            f'{case} = CALC_CHAMP(reuse={case}, RESULTAT={case}, GROUP_MA={_tuple(BEAM_GROUPS)}, CONTRAINTE=("EFGE_ELNO",))'
        )
        w(f'{case} = CALC_CHAMP(reuse={case}, RESULTAT={case}, FORCE=("REAC_NODA",))')
    w("")
    w("# ---------------------------------------------------------------- 8. SORTIES")
    w(
        "# Tables du contrôle d'équilibre (niveau D) : RP_<cas> réactions côté quai, DS_<cas>"
    )
    w("# déplacements des nœuds de la semelle (efforts des ressorts k·u).")
    for case in (*MECHANICAL_CASES, *ACCIDENTAL_CASES):
        out.extend(_outputs("ELEM", case, multiple=True))
    for case in THERMAL_CASES:
        out.extend(_outputs(case, case, multiple=False))
    w("IMPR_RESU(")
    w('    FORMAT="MED",')
    w("    UNITE=80,")
    w("    RESU=(")
    w(
        '        _F(RESULTAT=ELEM, NOM_RESU_MED="ELEM", NOM_CHAM=("DEPL", "EFGE_ELNO", "REAC_NODA"), CARA_ELEM=CARA),'
    )
    for case in THERMAL_CASES:
        w(
            f'        _F(RESULTAT={case}, NOM_RESU_MED="{case}", NOM_CHAM=("DEPL", "EFGE_ELNO", "EFGE_NOEU", "REAC_NODA"), CARA_ELEM=CARA),'
        )
    w("    ),")
    w(")")
    w("")
    w("FIN()")
    report = {
        "cases": {c: CASE_LABELS[c] for c in ALL_CASES},
        "influence_widths_m": widths,
        "half_deck_widths_m": half,
        "rigid_links": n_links,
        "hinges": len(g.hinges),
        "footing_area_m2": footing_area,
        "pp_shear": {"AZ": pp_az, "AY": pp_az, "AY_hypothesis": PP_AY_HYPOTHESIS},
        "weights_n": weights(v, g),
        "applied_loads_n": applied_loads(v, g),
    }
    return "\n".join(out) + "\n", report


__all__ = [
    "ALL_CASES",
    "MECHANICAL_CASES",
    "THERMAL_CASES",
    "Values",
    "applied_loads",
    "build_comm",
    "values",
    "weights",
]
