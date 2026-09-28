"""Lot 39, étape 2 : constats `code_aster` du point 14 sur ce que `CALC_FERRAILLAGE`
fait et ne fait pas (`data/examples/combiwall_inputs/lot39_essais.json`).

Chaque source d'exécution cite un `.comm` versionné et l'extrait versionné de son
listing ; la valeur obtenue est **relue dans l'extrait** (jamais saisie), la valeur
de référence est calculée ici par le module indépendant (`aster_expert.rebar`) ou
par la formule de `R7.04.05` indiquée dans `reference`. Le texte des constats est
de la session ; `scripts/build_combiwall_reference.py` les enregistre.

Usage : python scripts/build_lot39_constats.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aster_expert.rebar.biaxial import design_biaxial  # noqa: E402
from aster_expert.rebar.minimum import as_min_flexure, rho_w_min  # noqa: E402
from aster_expert.rebar.model import Concrete, Rectangle, Steel  # noqa: E402
from aster_expert.rebar.serviceability import design_els  # noqa: E402
from aster_expert.rebar.ultimate import design_ultimate  # noqa: E402

OUT = ROOT / "data" / "examples" / "combiwall_inputs" / "lot39_essais.json"
ESSAIS = "data/examples/lot39_essais"
REPORTS = f"{ESSAIS}/rapports"
C = Concrete(fck=35.0, gamma_c=1.5, alpha_cc=1.0)
S = Steel(fyk=500.0, gamma_s=1.15)
Z = Rectangle(width=1.40, depth=2.50, cover_pos=0.10, cover_neg=0.10)
Y = Rectangle(width=2.50, depth=1.40, cover_pos=0.10, cover_neg=0.10)
FYD = 500.0 / 1.15
COT = 1.0 / math.tan(math.radians(21.8))
TK = max(1.40 * 2.50 / (2.0 * 3.90), 0.20)
AK = (1.40 - TK) * (2.50 - TK)
COLUMNS_1D = ("AYS", "AYI", "AZS", "AZI", "AST", "ATOT")
COLUMNS_2D = ("DNSXI", "DNSXS", "DNSYI", "DNSYS", "DNSXT", "DNSYT")


def table(name: str, columns: tuple[str, ...]) -> dict[int, dict[str, float]]:
    """`{instant: {column: value}}` of the versioned listing extract."""
    out: dict[int, dict[str, float]] = {}
    text = (ROOT / REPORTS / f"mess_{name}_extrait.txt").read_text("utf-8")
    for line in text.splitlines():
        if line.startswith("RESU "):
            cells = line.split()
            out[round(float(cells[2]))] = dict(
                zip(columns, map(float, cells[6 : 6 + len(columns)]), strict=True)
            )
    return out


def source(
    name: str,
    instant: int,
    column: str,
    quantity: str,
    reference: str,
    reference_value: float,
    columns: tuple[str, ...] = COLUMNS_1D,
) -> dict[str, object]:
    return {
        "context": "lot39",
        "case_path": f"{ESSAIS}/{name}/{name}.comm",
        "mess_path": f"{REPORTS}/mess_{name}_extrait.txt",
        "quantity": quantity,
        "value_obtained": table(name, columns)[instant][column],
        "reference": reference,
        "reference_value": reference_value,
        "validation_level": "C",
    }


def _ulu(section: Rectangle, n: float, m: float) -> float:
    d = design_ultimate(section, C, S, n, m)
    return d.as_pos if m > 0 else d.as_neg


def findings() -> list[dict[str, object]]:
    fctm = C.fctm
    wa = _ulu(Rectangle(width=1.0, depth=0.5, cover_pos=0.05, cover_neg=0.05), 0.0, 0.1)
    plate = Rectangle(width=1.0, depth=0.5, cover_pos=0.05, cover_neg=0.05)
    return [
        {
            "id": "f1_elu_faces",
            "point_label": "14",
            "topic": "CALC_FERRAILLAGE en 1D à l'ELU : faces, signes, points intérieurs et reproduction par le module indépendant (section de la poutre de couronnement, D19)",
            "extraits": ["r7_04_05_1d_elu_balayage", "u4_81_42_composition_1d_2d"],
            "catalogue_refs": [
                {
                    "command": "CALC_FERRAILLAGE",
                    "keyword_path": ["AFFE", "TYPE_STRUCTURE"],
                },
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["TYPE_COMB"]},
            ],
            "option_retained": "En TYPE_STRUCTURE='1D', MFZ > 0 tend la face AYS (+y, côté terre pour la poutre de couronnement, x_l = X) et MFZ < 0 la face AYI ; MFY > 0 tend AZS (+z, face supérieure) et MFY < 0 AZI. h est la dimension selon y (HY) pour MFZ, selon z (HZ) pour MFY. À l'ELU, le calcul suit le diagramme béton rectangulaire simplifié (lot 38) et un couple (N, M) intérieur au domaine du béton seul donne une aire nulle sur les quatre faces. Le module aster_expert.rebar corrigé au lot 39 reproduit ces aires à 1e-12 relatif sur la section réelle avec la distance parement-axe de D19 (0,10 m).",
            "justification": "Essais d19 et limites du lot 39 (exécutions réelles, DIAGNOSTIC JOB : OK) : les faces et les signes sont lus sur des moments d'une seule composante et d'un seul signe ; les valeurs sont confrontées au module indépendant. U4.81.42 (composition du champ) définit AYS/AYI/AZS/AZI comme faces +y/-y « suivant la hauteur h » et +z/-z « suivant la largeur b » ; R7.04.05 : minimisation de As,s + As,i « tout en veillant à ce que les deux sections soient positives ».",
            "notes": "Déduction : le zéro de Code_Aster aux points intérieurs (flexion composée comprimée N = 5 MN, M = 2,183517 MN·m ; ELS QP N = 1 MN, M = 0,5 MN·m) vient de ce qu'aucun plan ultime à aciers positifs n'y réalise l'équilibre ; le module du lot 38 déclarait ces cas « infeasible » (défaut corrigé au lot 39, docs/essais_lot39.md, étape 1). Les quatre essais du lot 38 refaits avec 0,10 m (essai d19) : flexion simple AYS = 2,104822e-03 m², traction AYS = 7,933517e-03 et AYI = 3,566483e-03 m², compression et ELS QP nuls.",
            "sources": [
                source(
                    "d19",
                    1,
                    "AYS",
                    "AYS (m²), flexion simple MFZ = 2,183517 MN·m, ELU, c = 0,10 m",
                    "aster_expert.rebar.ultimate.design_ultimate, bloc rectangulaire, h = 2,50, b = 1,40",
                    _ulu(Z, 0.0, 2.183517),
                ),
                source(
                    "d19",
                    3,
                    "AYI",
                    "AYI (m²), flexion composée N = +5 MN (traction), MFZ = 2,183517 MN·m, ELU",
                    "aster_expert.rebar.ultimate.design_ultimate (face comprimée par M)",
                    design_ultimate(Z, C, S, 5.0, 2.183517).as_neg,
                ),
                source(
                    "limites",
                    2,
                    "AYI",
                    "AYI (m²), MFZ = -1 MN·m seul, ELU",
                    "design_ultimate, h = 2,50, b = 1,40 (face -y tendue)",
                    _ulu(Z, 0.0, -1.0),
                ),
                source(
                    "limites",
                    3,
                    "AZS",
                    "AZS (m²), MFY = +1 MN·m seul, ELU",
                    "design_ultimate, h = 1,40, b = 2,50 (face +z tendue)",
                    _ulu(Y, 0.0, 1.0),
                ),
            ],
        },
        {
            "id": "f2_minimum",
            "point_label": "14",
            "topic": "Ferraillage minimal de CALC_FERRAILLAGE en 1D (FERR_MIN, FERR_MIN_FISS) : ce qui est appliqué, sur quelles faces, et dépendance aux unités",
            "extraits": [
                "u4_81_42_ec2_ferr_min",
                "u4_81_42_ferr_min_fiss",
                "r7_04_05_1d_minimum",
            ],
            "catalogue_refs": [
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["AFFE", "FERR_MIN"]},
                {
                    "command": "CALC_FERRAILLAGE",
                    "keyword_path": ["AFFE", "FERR_MIN_FISS"],
                },
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["UNITE_CONTRAINTE"]},
            ],
            "option_retained": "FERR_MIN='EC2' (catalogue 17.4.0 : 'VALE_MIN' ou 'EC2' ; la documentation U4.81.42 écrit 'BAEL91' dans la section EC2) applique en 1D le minimum de l'EN 1992-1-1 9.2.1.1 (0,26 fctm/fyk b d, au moins 0,0013 b d) sur les QUATRE faces, tendues ou non, même sans effort, et un minimum transversal rho_w,min = 0,08 √fck/fyk multiplié par HY quelle que soit la direction de l'effort tranchant. Ces valeurs ne sont justes qu'avec UNITE_CONTRAINTE='MPa' (longueurs en mm) : avec 'Pa' (longueurs en m), la même commande donne 0,0013 b d et un minimum transversal 1000 fois trop faible. FERR_MIN_FISS='EC2' (maîtrise de la fissuration, EN 1992-1-1 7.3.2) est refusé pour les poutres : <F> <CALCULEL7_40> « Le calcul de ferraillage minimal pour la maîtrise de la fissuration n'est pas encore possible pour les éléments POUTRE ». À traiter hors de Code_Aster : le minimum de maîtrise de la fissuration (7.3.2) en 1D, et le minimum 9.2.1.1 dès que le calcul est conduit en Pa ; la restriction du minimum aux seules faces tendues (9.2.1.1 vise l'armature tendue).",
            "justification": "Essais fermin (Pa), fermin_mpa (MPa, mm) et fiss du lot 39, exécutions réelles ; valeurs de référence calculées par aster_expert.rebar.minimum (EN 1992-1-1 9.2.1.1, expression 9.1N ; 9.2.2(5), expression 9.5N).",
            "notes": "Déduction (non confirmée par la lecture des sources de Code_Aster, hors de portée des sept outils) : en Pa, fctm est calculé à partir de fck exprimé en Pa avec une formule en MPa (0,3 fck^(2/3) cent fois trop faible, d'où 0,0013 b d) et √fck/fyk est mille fois trop faible. L'exécution fiss s'arrête sur l'erreur fatale (niveau B pour cette exécution : consignée ici, pas comme source) ; listing data/examples/lot39_essais/rapports/mess_fiss_extrait.txt.",
            "sources": [
                source(
                    "fermin",
                    2,
                    "AYS",
                    "AYS (m²) avec FERR_MIN='EC2', MFZ = 1 MN·m, UNITE_CONTRAINTE='Pa'",
                    "EN 1992-1-1 9.2.1.1 (9.1N), 0,26 fctm/fyk b d, b = 1,40, d = 2,40 (aster_expert.rebar.minimum.as_min_flexure)",
                    as_min_flexure(1.40, 2.40, fctm, 500.0),
                ),
                source(
                    "fermin_mpa",
                    2,
                    "AYS",
                    "AYS (mm²) avec FERR_MIN='EC2', MFZ = 1e9 N·mm, UNITE_CONTRAINTE='MPa'",
                    "EN 1992-1-1 9.2.1.1 (9.1N), 0,26 fctm/fyk b d en mm² (b = 1400, d = 2400)",
                    as_min_flexure(1400.0, 2400.0, fctm, 500.0),
                ),
                source(
                    "fermin_mpa",
                    3,
                    "AZI",
                    "AZI (mm²) avec FERR_MIN='EC2', aucun effort, UNITE_CONTRAINTE='MPa'",
                    "EN 1992-1-1 9.2.1.1 (9.1N), b = 2500, d = 1300",
                    as_min_flexure(2500.0, 1300.0, fctm, 500.0),
                ),
                source(
                    "fermin_mpa",
                    3,
                    "AST",
                    "AST (mm²/mm) avec FERR_MIN='EC2', aucun effort, UNITE_CONTRAINTE='MPa'",
                    "EN 1992-1-1 9.2.2(5) (9.5N), rho_w,min x HY = 2500 mm",
                    rho_w_min(35.0, 500.0) * 2500.0,
                ),
                source(
                    "fermin",
                    3,
                    "AST",
                    "AST (m²/m) avec FERR_MIN='EC2', aucun effort, UNITE_CONTRAINTE='Pa'",
                    "EN 1992-1-1 9.2.2(5) (9.5N), rho_w,min x HY = 2,50 m",
                    rho_w_min(35.0, 500.0) * 2.50,
                ),
            ],
        },
        {
            "id": "f3_flexion_deviee",
            "point_label": "14",
            "topic": "Flexion déviée en 1D dans CALC_FERRAILLAGE (MFY et MFZ simultanés) : procédure itérative de Bresler",
            "extraits": ["r7_04_05_1d_flexion_deviee"],
            "catalogue_refs": [
                {
                    "command": "CALC_FERRAILLAGE",
                    "keyword_path": ["AFFE", "TYPE_STRUCTURE"],
                }
            ],
            "option_retained": "Sous MFY et MFZ simultanés, les aires ne résultent pas d'une vraie flexion déviée : chaque direction est dimensionnée seule sous N, puis les quatre aires sont augmentées de 10 % de l'aire totale par itération (facteur 1,1 par itération) jusqu'à vérifier l'inéquation de Bresler (EN 1992-1-1 5.8.9(4)). Sous MFY = MFZ = 1 ou 3 MN·m (N = 0), huit itérations : aires direction par direction multipliées par 1,1^8 = 2,1436. Le module aster_expert.rebar.biaxial reproduit la procédure à 1e-13. À traiter hors de Code_Aster si l'on veut une vraie flexion déviée (diagramme d'interaction 3D).",
            "justification": "Essai limites du lot 39 (instants mfz_1, mfy_1, devie_1, mfz_3, mfy_3, devie_3) ; R7.04.05, § Calcul du ferraillage longitudinal en flexion déviée.",
            "notes": "Déduction : la procédure est conservatrice (aire totale 2,14 fois l'aire direction par direction sous deux moments égaux) et discontinue — un moment secondaire infime déclenche au moins une itération de 10 % dès que la direction principale est dimensionnée exactement. Sur la poutre de couronnement (étape 3), 5 à 9 itérations selon les sections contrôlées.",
            "sources": [
                source(
                    "limites",
                    5,
                    "AYS",
                    "AYS (m²), MFY = MFZ = 1 MN·m, ELU",
                    "procédure de Bresler de R7.04.05 (aster_expert.rebar.biaxial.design_biaxial)",
                    design_biaxial(2.50, 1.40, 0.10, C, S, 0.0, 1.0, 1.0).ays,
                ),
                source(
                    "limites",
                    8,
                    "AZS",
                    "AZS (m²), MFY = MFZ = 3 MN·m, ELU",
                    "procédure de Bresler de R7.04.05 (aster_expert.rebar.biaxial.design_biaxial)",
                    design_biaxial(2.50, 1.40, 0.10, C, S, 0.0, 3.0, 3.0).azs,
                ),
                source(
                    "limites",
                    5,
                    "AYS",
                    "AYS (m²), MFY = MFZ = 1 MN·m, comparé au calcul direction par direction sans interaction",
                    "design_ultimate de la seule direction MFZ (sans Bresler)",
                    _ulu(Z, 0.0, 1.0),
                ),
            ],
        },
        {
            "id": "f4_tranchant_torsion",
            "point_label": "14",
            "topic": "Effort tranchant et torsion en 1D dans CALC_FERRAILLAGE : ce que représente AST",
            "extraits": ["r7_04_05_1d_transversal_elu", "u4_81_42_ec2_epure_cisa"],
            "catalogue_refs": [
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["AFFE", "EPURE_CISA"]}
            ],
            "option_retained": "En 1D, AST (m²/m) est une seule densité de cadres droits : Asw/s = [V + T/A_k (h - t_k)] / (z fyd cot θ), z = 0,9 d, t_k = max(A/u ; 2c), A_k = (b - t_k)(h - t_k), θ = 21,8° (cot θ = 2,50018, et non 2,5 exactement) quand les bielles le permettent ; VY et VZ sont traités chacun dans son plan et AST est le maximum des deux directions (VY = VZ = 4 MN donne la valeur de VZ seul). La torsion est convertie en effort tranchant équivalent et ajoutée à V (interaction de R7.04.05, pas les expressions 6.26 à 6.28 de l'EN 1992-1-1 par paroi) ; aucune armature longitudinale de torsion n'est produite séparément (seul EPURE_CISA='OUI' ajoute un effort de traction aux aires longitudinales) ; le critère d'écrasement des bielles (6.29) n'est pas une sortie. Aucun ferraillage sous T = 2 MN·m seul (T_Rd,c = 2,62 MN·m). À traiter hors de Code_Aster : armatures longitudinales de torsion (6.28), cadres de torsion par paroi (6.26-6.27), valeur du critère de bielle (6.29).",
            "justification": "Essai limites du lot 39 (vy_2, vy_4, vz_4, mt_2, mt_4, vy_4_mt_4, vy_4_vz_4) : les cinq valeurs non nulles sont reproduites à 1e-13 par la formule ci-dessus ; R7.04.05, § Calcul du ferraillage transversal.",
            "notes": "vy_2 (V = 2 MN) produit des cadres : V_Rd,c < 2 MN, ce qui exclut la lecture littérale « v_min = 0,053 γc k^1,5 fck^0,5 » de R7.04.05 (qui donnerait V_Rd,c = 2,31 MN) ; déduction : v_min = 0,053/γc k^1,5 fck^0,5 ou 0,035 k^1,5 fck^0,5 (valeurs voisines, non départagées). Le module aster_expert.rebar.shear (EN 1992-1-1 6.2 et 6.3, cot θ = 2,5) diffère de 7,1e-5 relatif sur l'effort tranchant seul (angle), et suit la méthode par paroi de l'EN pour la torsion (cadres 1,885876e-03 m²/m pour deux brins sous T = 4 MN·m contre 1,790828e-03 pour Code_Aster).",
            "sources": [
                source(
                    "limites",
                    10,
                    "AST",
                    "AST (m²/m), VY = 4 MN seul, ELU",
                    "V/(0,9 d fyd cot 21,8°), d = 2,40",
                    4.0 / (0.9 * 2.40 * FYD * COT),
                ),
                source(
                    "limites",
                    11,
                    "AST",
                    "AST (m²/m), VZ = 4 MN seul, ELU",
                    "V/(0,9 d fyd cot 21,8°), d = 1,30",
                    4.0 / (0.9 * 1.30 * FYD * COT),
                ),
                source(
                    "limites",
                    13,
                    "AST",
                    "AST (m²/m), MT = 4 MN·m seul, ELU",
                    "[T/A_k (h - t_k)]/(0,9 d fyd cot 21,8°), h = 2,50, d = 2,40",
                    (4.0 / AK * (2.50 - TK)) / (0.9 * 2.40 * FYD * COT),
                ),
                source(
                    "limites",
                    14,
                    "AST",
                    "AST (m²/m), VY = 4 MN et MT = 4 MN·m, ELU",
                    "[V + T/A_k (h - t_k)]/(0,9 d fyd cot 21,8°)",
                    (4.0 + 4.0 / AK * (2.50 - TK)) / (0.9 * 2.40 * FYD * COT),
                ),
                source(
                    "limites",
                    15,
                    "AST",
                    "AST (m²/m), VY = VZ = 4 MN, ELU",
                    "maximum des deux directions : valeur de VZ seul",
                    4.0 / (0.9 * 1.30 * FYD * COT),
                ),
            ],
        },
        {
            "id": "f5_els",
            "point_label": "14",
            "topic": "ELS caractéristique et ELS quasi permanent en 1D dans CALC_FERRAILLAGE : limitation des contraintes et écart au calcul de R7.04.05",
            "extraits": ["r7_04_05_1d_els_balayage"],
            "catalogue_refs": [
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["AFFE", "SIGS_ELS"]},
                {
                    "command": "CALC_FERRAILLAGE",
                    "keyword_path": ["AFFE", "SIGC_INF_Y_ELS"],
                },
            ],
            "option_retained": "À l'ELS caractéristique, CALC_FERRAILLAGE limite la contrainte de l'acier à SIGS_ELS (0,8 fyk = 400 MPa, EN 1992-1-1 7.2(5)) et celle du béton à SIGC_*_ELS (0,6 fck = 21 MPa, XS3, 7.2(2)), une valeur par face et par axe, section fissurée sans béton tendu, αe = ALPHA_E. Les aires obtenues diffèrent de 0,25 % à 16 % du calcul par pivot acier de R7.04.05 refait à la main et par le module (aster_expert.rebar.serviceability) : cause non établie. La commande ne vérifie pas un ferraillage donné (VERI_FERRAILLAGE n'accepte pas le 1D, lot 38) : la vérification des contraintes d'un ferraillage retenu est à traiter hors de Code_Aster.",
            "justification": "Essai limites du lot 39 (els_mfz_2, els_mfy_1, els_n_m3_mfz_4, qp_mfz_1) confronté au module indépendant et au calcul à la main (docs/essais_lot39.md, étape 1, pour ssll13b CHEFF4 : 6,0447e-04 à la main et par le module contre 5,8876e-04 pour la référence ANALYTIQUE du cas test).",
            "notes": "Écarts relevés : els_mfz_2 -4,4 % (Code_Aster plus faible), els_mfy_1 +0,25 %, els_n_m3_mfz_4 -16 %. Aucun des paramètres essayés (σs, αe, bras de levier, largeur) ne reproduit les valeurs de Code_Aster avec une valeur ronde. ELS quasi permanent (qp_mfz_1, MFZ = 1 MN·m) : Code_Aster 3,859047e-03 m² contre 8,572637e-04 pour le module, qui n'a pas été calibré sur un cas test : écart rapporté, cause non établie, module ELS QP à ne pas utiliser comme référence.",
            "sources": [
                source(
                    "limites",
                    16,
                    "AYS",
                    "AYS (m²), MFZ = 2 MN·m, ELS caractéristique",
                    "pivot acier de R7.04.05 (aster_expert.rebar.serviceability.design_els), h = 2,50, b = 1,40, d = 2,40",
                    design_els(
                        Z, C, S, 0.0, 2.0, sigma_c_lim=21.0, sigma_s_lim=400.0
                    ).as_pos,
                ),
                source(
                    "limites",
                    17,
                    "AZS",
                    "AZS (m²), MFY = 1 MN·m, ELS caractéristique",
                    "pivot acier de R7.04.05 (design_els), h = 1,40, b = 2,50",
                    design_els(
                        Y, C, S, 0.0, 1.0, sigma_c_lim=21.0, sigma_s_lim=400.0
                    ).as_pos,
                ),
            ],
        },
        {
            "id": "f6_plaque",
            "point_label": "14",
            "topic": "CALC_FERRAILLAGE en 2D sur une plaque DKT (méthode de Capra et Maury) : faces, flexion simple et effet de MXY",
            "extraits": ["r7_04_05_2d_capra_maury", "u4_81_42_composition_1d_2d"],
            "catalogue_refs": [
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["METHODE_2D"]},
                {"command": "CALC_FERRAILLAGE", "keyword_path": ["AFFE", "C_SUP"]},
            ],
            "option_retained": "En TYPE_STRUCTURE='2D' (DKT, METHODE_2D='CAPRA-MAURY' par défaut), MXX > 0 tend la face supérieure (DNSXS), MXX < 0 la face inférieure (DNSXI) ; sous NXX et MXX seuls, les densités par mètre sont celles de la flexion composée d'une bande de 1 m (bloc rectangulaire), à 1e-12 : la traction pure se répartit à parts égales sur les deux nappes X et un point intérieur donne zéro. Avec MXY, les densités résultent de l'équilibre par facettes et diffèrent de l'approximation de Wood-Armer (MXY seul : 4,709510e-04 en X et 5,623236e-04 en Y par nappe, contre 5,166373e-04 partout pour Wood-Armer). Dans le cas dégénéré NXX = 1 MN/m, MXX = 0,2 MN·m/m (e = h/2 - c exactement), Code_Aster ajoute 5,687521e-05 m²/m sur DNSXI et DNSYI, que le calcul en bande ne donne pas.",
            "justification": "Essai plaque du lot 39 (un QUAD4 DKT, 1 m x 1 m, épaisseur 0,50 m, c = 0,05 m, efforts imposés, exécution réelle) confronté au module aster_expert.rebar ; R7.04.05, méthode de Capra et Maury.",
            "notes": "Établit le fonctionnement de la commande, pas un dimensionnement. Déduction : la face « supérieure » d'une coque est celle du côté de la normale (repère local) ; pour un radier ou un voile, l'orientation des normales (ORIE_NORM_COQUE) fixe donc quelle nappe est « sup ».",
            "sources": [
                source(
                    "plaque",
                    1,
                    "DNSXS",
                    "DNSXS (m²/m), MXX = +0,2 MN·m/m seul, plaque DKT, ELU",
                    "design_ultimate, bande b = 1 m, h = 0,50, c = 0,05",
                    _ulu(plate, 0.0, 0.2),
                    COLUMNS_2D,
                ),
                source(
                    "plaque",
                    7,
                    "DNSXI",
                    "DNSXI (m²/m), NXX = +1 MN/m seul (traction), plaque DKT, ELU",
                    "N/(2 fyd) par nappe",
                    1.0 / (2.0 * FYD),
                    COLUMNS_2D,
                ),
                source(
                    "plaque",
                    6,
                    "DNSXS",
                    "DNSXS (m²/m), MXY = 0,1 MN·m/m seul, comparé à Wood-Armer",
                    "Wood-Armer : bande de 1 m sous abs(MXY) = 0,1 MN·m/m (design_ultimate)",
                    wa,
                    COLUMNS_2D,
                ),
            ],
        },
    ]


def main() -> int:
    payload = {
        "catalogue": {
            "aster_version": "17.4.0",
            "catalogue_source": "/opt/spack/opt/spack/linux-zen2/code-aster-17.4.0-ecm2bfgr5obydotnlte6xilvggppqnap/lib64/aster/code_aster",
            "catalogue_hash": "b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca",
            "image_digest": "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5",
        },
        "contexts": {
            "lot39": {
                "aster_version": "17.4.0",
                "image_digest": "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5",
                "repo_commit": "069a8889574c502ff2cfc8ddecf2f81492eb24cd",
                "working_tree_modified": True,
                "note": "HEAD au moment des exécutions du lot 39 (commit du lot 38) ; les fichiers du lot 39 n'étaient pas encore commités. Les .comm exécutés sont versionnés tels quels (sha256 contrôlé par scripts/collect_lot39_essais.py).",
            }
        },
        "findings": findings(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"écrit {OUT.relative_to(ROOT)} : {len(payload['findings'])} constats")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
