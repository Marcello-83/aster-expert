"""Lot 43, phase 2 : report de l'arbitrage de MM dans la fiche de la dalle.

Source : `donnees/sources/arbitrage_dalle_appuyee_01_v1.md` (copie à l'identique du
document déposé par MM dans le partage). Section A : décisions de pratique P1 à P6 ;
section B : choix de modélisation rédigés par le superviseur, validés avec le
document (« le lancement de la phase 2 avec ce document vaut validation par MM de
toutes les lignes »). Chaque décision passe par `record_practice_decision`, avec une
source d'origine `arbitrage_mm` et la référence « arbitrage_dalle_appuyee_01_v1 ».

Les articles d'Eurocode sont reportés « tels quels, avec la mention référence
normative fournie par MM, non indexée » (consigne du document) : jamais présentés
comme vérifiés par l'outil.

Entrée : la fiche proposée de la phase 1 (`build_fiche_lot43.build_sheet`, inchangée).
Sorties : `fiche/historique/hypotheses_dalle_arbitree_lot43.json` et
`fiche/historique/fiche_arbitree_lot43.md` (lot 44 : la fiche courante est produite
par `decisions_lot44.py` à partir de celle-ci).
Déterministe : `DECIDED_AT` est l'heure de l'enregistrement (MM n'a écrit ni date ni
heure ; règle du quai, lot 24).

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/arbitrer_fiche_lot43.py`
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_fiche_lot43 import build_sheet

from aster_expert.agent.arbitration import record_practice_decision
from aster_expert.agent.drafting import SearchAttempt, record_unfounded_point
from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    DiscardedVariant,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.catalogue.query import catalogue_vocabulary
from aster_expert.connaissances.base import load_knowledge
from aster_expert.connaissances.modeles import Precedent
from aster_expert.connaissances.precedents import precedent_source
from aster_expert.constats.base import (
    base_dir,
    externalize_sheet,
    load_base,
    resolve_sheet,
)

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
# Lot 44 : la fiche arbitrée du lot 43 est conservée telle quelle comme historique ;
# la fiche courante (`fiche/hypotheses_dalle_arbitree.json`) est celle du lot 44
# (`decisions_lot44.py`, correction de Es par MM).
FICHE = PROJECT / "fiche" / "historique" / "hypotheses_dalle_arbitree_lot43.json"
DOCUMENT = PROJECT / "fiche" / "historique" / "fiche_arbitree_lot43.md"
DATA = PROJECT / "donnees" / "dalle_model_data.yaml"
SOURCES = PROJECT / "donnees" / "sources"

REFERENCE = "arbitrage_dalle_appuyee_01_v1"
DECIDED_AT = datetime.fromisoformat("2026-10-02T04:37:34-04:00")
DECIDED_BY = "MM"
SECTION_B_BY = (
    "Claude (superviseur), section B de arbitrage_dalle_appuyee_01_v1 — document "
    "validé par MM"
)
NORME = "référence normative fournie par MM, non indexée"


def _mm(section: str) -> PracticeSource:
    return PracticeSource(
        origin="arbitrage_mm",
        reference=f"{REFERENCE}, {section}",
        date=date(2026, 10, 2),
    )


def _norme(article: str) -> PracticeSource:
    return PracticeSource(origin="norme", reference=f"{article} — {NORME}")


def _out(description: str, reason: str) -> DiscardedVariant:
    return DiscardedVariant(description=description, reason=reason)


def _precedent(precedent_id: str) -> PracticeSource:
    base = load_knowledge(ROOT)
    entry = base.entries[precedent_id]
    assert isinstance(entry, Precedent)
    return precedent_source(entry)


DECISIONS: dict[str, dict[str, object]] = {
    "0": {
        "option_retained": (
            "Calcul élastique linéaire et non fissuré de la dalle seule (plaque), sous "
            "chargement statique. Les flèches obtenues sont des flèches instantanées et "
            "non fissurées ; la flèche à long terme (fluage, fissuration, EC2 7.4.3) est "
            "hors périmètre, et le compte rendu le dit explicitement. Le ferraillage est "
            "calculé par CALC_FERRAILLAGE sur les efforts élastiques."
        ),
        "justification": (
            "Décision P2 de MM : « Le calcul est élastique linéaire et non fissuré. Les "
            "flèches obtenues sont des flèches instantanées et non fissurées. »"
        ),
        "validity_domain": (
            "Flèches instantanées seulement ; aucune flèche différée, aucun effet de la "
            "fissuration sur la raideur ; EC2 7.4.3 hors périmètre."
        ),
        "sources": (_mm("A, P2"), _norme("EN 1992-1-1, 7.4.3")),
        "discarded": (
            _out(
                "Estimation des flèches à long terme (fluage, fissuration).",
                "Hors périmètre de ce lot (P2).",
            ),
        ),
        "by": DECIDED_BY,
    },
    "1": {
        "option_retained": ("Modélisation DKT (Love-Kirchhoff) pour toute la dalle."),
        "justification": (
            "Décision P1 de MM : avec h/L = 0,30/4,00 = 1/13,3, la part de cisaillement "
            "transverse dans la flèche d'une bande simplement appuyée vaut environ "
            "0,8·E/(κG)·(h/L)², soit à peu près 1,3 % avec ν = 0,2 et κ = 5/6, négligeable "
            "devant la précision d'ingénieur ; les moments d'une plaque appuyée y sont peu "
            "sensibles. La référence du niveau E est Kirchhoff (Navier) : DKT est la seule "
            "modélisation qui rend la comparaison exacte, sans correction."
        ),
        "validity_domain": (
            "Déformation d'effort tranchant négligée (environ 1,3 % de la flèche selon "
            "l'estimation de MM) ; aucune étude de sensibilité DST dans ce lot."
        ),
        "sources": (_mm("A, P1"),),
        "discarded": (
            _out(
                "DST (cisaillement transverse), y compris en sensibilité.",
                "Ajoute un écart de modèle qui brouille le niveau E, sans bénéfice pour "
                "cet ouvrage ; la sensibilité DST est hors périmètre de ce lot (P1).",
            ),
            _out(
                "Q4GG (modélisation du cas test SSLS127).",
                "Même raison que DST : écart de modèle par rapport à Kirchhoff (P1).",
            ),
        ),
        "by": DECIDED_BY,
    },
    "4": {
        "option_retained": (
            "Deux cas de charge calculés séparément, chacun comparé à Navier. "
            "G : poids propre, poids volumique 25 kN/m³, appliqué par PESANTEUR avec "
            "g = 9,81 m/s² et RHO = 25 000 / 9,81 = 2 548,42 kg/m³, de façon que ρ·g vaille "
            "exactement 25 kN/m³ ; résultante attendue 25 × 6 × 4 × 0,30 = 180,0 kN. "
            "Q : exploitation de 10 kPa en charge surfacique de direction globale −Z "
            "(FORCE_COQUE/FZ), et non en PRES, pour ne pas dépendre de l'orientation des "
            "normales ; résultante attendue 240,0 kN."
        ),
        "justification": "Décision P3 de MM.",
        "validity_domain": (
            "Exploitation uniforme sur toute la dalle ; aucune disposition partielle. "
            "RHO est un artifice pour obtenir ρ·g = 25 kN/m³ (le poids volumique du béton "
            "armé, pas sa masse volumique réelle) : il n'est valable qu'en statique."
        ),
        "sources": (_mm("A, P3"), _norme("EN 1991-1-1, annexe A")),
        "discarded": (
            _out(
                "RHO = 2500 kg/m³ et g = 9,81 m/s² (poids 24,5 kN/m³).",
                "MM retient 25 kN/m³ exactement (P3).",
            ),
            _out(
                "Exploitation par FORCE_COQUE/PRES après ORIE_NORM_COQUE.",
                "Le résultat dépendrait de l'orientation des normales (P3).",
            ),
            _out(
                "Dispositions partielles (damier) de l'exploitation.",
                "Non retenues par P3 : exploitation uniforme de 10 kPa.",
            ),
        ),
        "by": DECIDED_BY,
    },
    "5": {
        "option_retained": (
            "Béton C30/37 : E = Ecm = 33 000 MPa, ν = 0,2 (béton non fissuré), fck = 30 MPa, "
            "fctm = 2,9 MPa. Calcul élastique linéaire et non fissuré. ν est figé avant "
            "l'écriture du critère du niveau E."
        ),
        "justification": "Décision P2 de MM.",
        "validity_domain": (
            "Béton non fissuré : raideur de flexion surestimée pour une dalle fissurée ; "
            "flèches instantanées seulement."
        ),
        "sources": (
            _mm("A, P2"),
            _norme("EN 1992-1-1, tableau 3.1"),
            _norme("EN 1992-1-1, 3.1.3(4)"),
        ),
        "discarded": (
            _out(
                "ν = 0 (béton fissuré).",
                "MM retient le béton non fissuré, ν = 0,2 (P2).",
            ),
            _out(
                "Module effectif à long terme.",
                "Flèche à long terme hors périmètre (P2).",
            ),
        ),
        "by": DECIDED_BY,
    },
    "6": {
        "option_retained": (
            "Dalle entière, sans symétrie. Appui bilatéral sur les quatre bords : DZ = 0 "
            "sur `APPUIS`, rotations libres (hypothèse de Navier, coins retenus). Plan de "
            "la dalle : blocage isostatique, DX = DY = 0 au coin `P_A` et DY = 0 au coin "
            "`P_B`, adjacent selon X, sans aucune redondance avec d'autres conditions "
            "(DIAG-001). La réaction concentrée aux coins, dirigée vers le bas, est attendue "
            "et se commente comme résultat physique. La symétrie des résultats selon les "
            "deux axes est un contrôle de niveau D."
        ),
        "justification": "Décision P4 de MM.",
        "validity_domain": (
            "Appui bilatéral : un appui réel qui laisse les coins se soulever (contact "
            "unilatéral) n'est pas représenté."
        ),
        "sources": (_mm("A, P4"),),
        "discarded": (
            _out(
                "Appui unilatéral (contact).",
                "Calcul de contact non linéaire, hors périmètre (P4).",
            ),
            _out(
                "Quart de dalle avec deux plans de symétrie.",
                "Le modèle est petit ; la symétrie devient un contrôle de niveau D, et le "
                "piège des conditions de symétrie des coques disparaît (P4).",
            ),
        ),
        "by": DECIDED_BY,
    },
    "9": {
        "option_retained": (
            "Origine au coin A (0, 0, 0). X selon le côté de 6,00 m, Y selon le côté de "
            "4,00 m, Z vers le haut. Plan de la dalle à z = 0 (feuillet moyen). Unités "
            "m, N, Pa, kg."
        ),
        "justification": (
            "Section B de l'arbitrage (choix de modélisation vérifié par le niveau E et les "
            "contrôles D). Repère de la série de Navier (origine au coin)."
        ),
        "validity_domain": "Convention de repère : sans limite physique.",
        "sources": (_mm("B, repère"),),
        "discarded": (
            _out(
                "Origine au centre de la dalle.",
                "Non retenue par la section B (origine au coin A).",
            ),
            _out(
                "Précédent PRE-012 (repère du quai).",
                "Repère propre au quai (axe de tube, cote CM) ; seule la déclaration du "
                "repère et des unités dans la fiche est reprise.",
            ),
        ),
        "by": SECTION_B_BY,
    },
    "10": {
        "option_retained": (
            "Mailles QUAD4 régulières sous la modélisation DKT. Suite de convergence de "
            "rapport 2 : tailles 0,50 / 0,25 / 0,125 m, soit 12×8, 24×16 et 48×32 mailles, "
            "avec un nœud au centre (3,0 ; 2,0) dans les trois maillages. Moments au centre "
            "lus en EFGE_NOEU au nœud `CENTRE` pour la comparaison à Navier ; EFGE_ELNO "
            "sert seulement à contrôler l'écart de lissage au centre."
        ),
        "justification": (
            "Section B de l'arbitrage. Le précédent PRE-013 (quai) n'avait fait l'objet "
            "d'aucune étude de convergence : la suite de rapport 2 en tient lieu ici."
        ),
        "validity_domain": (
            "Convergence établie aux seuls points de comparaison (centre) ; les coins, où "
            "Mxy est maximal, ne sont pas couverts par la référence de Navier au même titre."
        ),
        "sources": (_mm("B, mailles, suite de convergence, lecture des moments"),),
        "discarded": (
            _out("TRIA3.", "Non retenus par la section B (QUAD4 réguliers)."),
            _out(
                "Moments lus en EFGE_ELNO d'une maille pour la comparaison.",
                "EFGE_ELNO ne sert qu'à contrôler l'écart de lissage (section B).",
            ),
        ),
        "by": SECTION_B_BY,
    },
    "13": {
        "option_retained": (
            "Catégorie d'usage E (aires de stockage) : ψ0 = 1,0, ψ1 = 0,9, ψ2 = 0,8. "
            "ELU fondamental : 1,35 G + 1,5 Q, G toujours défavorable (aucun cas "
            "favorable). ELS caractéristique : G + Q. ELS quasi permanent : G + 0,8 Q. "
            "PRE-016 (quai) n'est retenu que pour γG = 1,35 et γQ = 1,5."
        ),
        "justification": (
            "Décision P5 de MM : 10 kPa dépasse les valeurs usuelles des catégories A à D ; "
            "la catégorie E est la seule cohérente avec cette intensité. G est toujours "
            "défavorable sur une travée isostatique."
        ),
        "validity_domain": (
            "Dalle isostatique sous deux actions (G, Q) ; le reste de PRE-016 (actions du "
            "quai) ne s'applique pas."
        ),
        "sources": (
            _mm("A, P5"),
            _precedent("PRE-016"),
            _norme("EN 1991-1-1, tableau 6.1"),
            _norme("EN 1990, tableau A1.1"),
            _norme("EN 1990, 6.10"),
        ),
        "discarded": (
            _out(
                "γG favorable (1,0 G + 1,5 Q).",
                "G est toujours défavorable sur une travée isostatique (P5).",
            ),
            _out(
                "Catégories d'usage A à D.",
                "10 kPa dépasse leurs valeurs usuelles (P5).",
            ),
            _out(
                "Reste du précédent PRE-016 (actions G, EAU, Q1, Q3, A du quai).",
                "Actions propres au quai (P5).",
            ),
        ),
        "by": DECIDED_BY,
    },
    "14": {
        "option_retained": (
            "Acier B500B, fyk = 500 MPa. γc = 1,5 et γs = 1,15 en situation durable ; "
            "ALPHA_CC = 1,0 écrit explicitement dans le .comm (la valeur par défaut 0,85 "
            "n'est pas retenue). Barres HA12 dans les deux directions, nappes inférieure "
            "et supérieure. Distance du parement à l'axe, enrobage nominal 30 mm : lit "
            "extérieur (barres portant dans la petite portée, Y) 30 + 6 = 36 mm ; lit "
            "intérieur (barres portant dans la grande portée, X) 30 + 12 + 6 = 48 mm. "
            "CALC_FERRAILLAGE n'admet qu'une distance par face en 2D (catalogue 17.4 : "
            "C_INF et C_SUP, un réel chacun) : 48 mm est retenu pour les deux directions et "
            "déclaré ; la contre-vérification manuelle utilise la même valeur. ELS en XC1 : "
            "wk limite = 0,4 mm sous combinaison quasi permanente ; σs ≤ 0,8 fyk sous "
            "combinaison caractéristique ; pas de limite sur σc en XC1. Ferraillage "
            "minimal : non-fragilité As,min = max(0,26·fctm/fyk ; 0,0013)·b·d ; maîtrise de "
            "la fissuration en flexion simple, kc = 0,4, k = 1,0, fct,eff = fctm, Act = "
            "b·h/2 ; armatures de répartition ≥ 20 % des armatures principales. Méthode 2D "
            "native de CALC_FERRAILLAGE pour les plaques ; contre-vérification "
            "indépendante au centre de la dalle (Mxy nul par symétrie) ; coins relevés et "
            "commentés, armatures de coin signalées, non calculées."
        ),
        "justification": (
            "Décision P6 de MM. Distance à l'axe selon PRE-018 (enrobage mesuré au nu de "
            "l'armature). MM écarte « PRE-021 (D21, Act = zone tendue complète) », poutre "
            "tendue du quai : aucune entrée PRE-021 n'existe dans la base (PRE-001 à "
            "PRE-018) et D21 n'est enregistrée dans aucune fiche du dépôt ; le domaine de "
            "validité invoqué est consigné tel quel (dalle fléchie, pas tendue)."
        ),
        "validity_domain": (
            "Une seule distance (48 mm) pour les deux directions : défavorable pour le lit "
            "extérieur (Y, 36 mm réels). wk = 0,4 mm est la valeur recommandée du tableau "
            "7.1N ; MM vérifie le tableau 7.1NF de l'annexe nationale. Armatures de coin "
            "(9.3.1.3) non calculées."
        ),
        "sources": (
            _mm("A, P6"),
            _precedent("PRE-018"),
            _norme("EN 1992-1-1, tableau 2.1N"),
            _norme("EN 1992-1-1, 3.1.6(1)P (annexe nationale française)"),
            _norme("EN 1992-1-1, tableau 7.1N"),
            _norme("EN 1992-1-1, 7.2(5)"),
            _norme("EN 1992-1-1, 9.3.1.1 et 9.2.1.1"),
            _norme("EN 1992-1-1, 7.3.2"),
        ),
        "discarded": (
            _out(
                "ALPHA_CC = 0,85 (défaut de CALC_FERRAILLAGE).",
                "Annexe nationale française : αcc = 1,0, comme au quai (P6).",
            ),
            _out(
                "Deux distances par face (36 mm en Y, 48 mm en X).",
                "Une seule distance par face en 2D dans CALC_FERRAILLAGE ; 48 mm, "
                "sécuritaire, est retenu (P6).",
            ),
            _out(
                "Précédent PRE-017 (XS3, wk = 0,2 mm, enrobage 65 mm du quai).",
                "Exposition XC1 et enrobage de 30 mm donnés par MM.",
            ),
            _out(
                "Act = zone tendue complète (« PRE-021 / D21 » cité par MM).",
                "Concerne une poutre tendue ; la dalle est fléchie (P6).",
            ),
            _out(
                "Calcul des armatures de coin (9.3.1.3).",
                "Signalées, non calculées (P6).",
            ),
        ),
        "by": DECIDED_BY,
    },
}

GROUPS = (
    ("DALLE", "maille", "Toutes les mailles QUAD4 de la dalle (surface).", "1"),
    ("APPUI_X0", "maille", "Bord X = 0 (SEG2).", "6"),
    ("APPUI_X6", "maille", "Bord X = 6,00 (SEG2).", "6"),
    ("APPUI_Y0", "maille", "Bord Y = 0 (SEG2).", "6"),
    ("APPUI_Y4", "maille", "Bord Y = 4,00 (SEG2).", "6"),
    ("APPUIS", "noeud", "Réunion des nœuds des quatre bords : DZ = 0.", "6"),
    ("P_A", "noeud", "Coin A (0, 0, 0) : DX = DY = 0.", "6"),
    ("P_B", "noeud", "Coin B (6, 0, 0), adjacent selon X : DY = 0.", "6"),
    ("CENTRE", "noeud", "Nœud central (3,0 ; 2,0) : comparaison à Navier.", "10"),
)


COMPLEMENT = "arbitrage_dalle_appuyee_01_complement_els"


def els_parameters_entry() -> PracticeHypothesisEntry:
    """Lot 43, phase 2: the ELS parameters U4.81.42 makes mandatory in 2D and the
    arbitration did not fix, asked to MM during the session and answered."""
    question = record_unfounded_point(
        point_label="14",
        topic="Paramètres ELS obligatoires de CALC_FERRAILLAGE en 2D (ALPHA_E, SIGC_*_ELS, SIGC_ELS_QP, KT, EYS)",
        searches=(
            SearchAttempt(
                profile="syntaxe",
                query="SIGC_INF_ELS SIGC_SUP_ELS SIGS_ELS ALPHA_E contrainte admissible béton ELS obligatoire (U4.81.42)",
                outcome=(
                    "U4.81.42 : SIGC_INF_ELS et SIGC_SUP_ELS obligatoires en 2D à l'ELS, "
                    "ALPHA_E obligatoire à l'ELS et à l'ELS_QP, SIGC_ELS_QP et KT "
                    "obligatoires à l'ELS_QP, EYS « couramment 210000 MPa » ; aucune de "
                    "ces valeurs n'est fixée par arbitrage_dalle_appuyee_01_v1"
                ),
            ),
        ),
        options_considered=(
            "ALPHA_E = 15 ou Es/Ecm",
            "SIGC_*_ELS = 0,6 fck avec étude de sensibilité, ou valeur non contraignante",
            "SIGC_ELS_QP = 0,45 fck ou valeur non contraignante",
            "KT = 0,4 ou 0,6 ; EYS = 200 ou 210 GPa",
        ),
    )
    return record_practice_decision(
        entry=question,
        option_retained=(
            "ALPHA_E = 15. SIGC_INF_ELS = SIGC_SUP_ELS = 0,6 fck = 18 MPa, avec un second "
            "calcul à valeur non contraignante pour montrer que la limite n'est pas active "
            "(rapportée si elle l'est). SIGC_ELS_QP = 0,45 fck = 13,5 MPa. KT = 0,4 "
            "(chargement de longue durée). EYS = 210 000 MPa (Es = 210 GPa, comme au quai)."
        ),
        justification=(
            "Réponses de MM aux questions de la session (complément d'arbitrage, "
            "donnees/sources/arbitrage_dalle_appuyee_01_complement_els.md) : ces "
            "paramètres sont obligatoires en 2D selon U4.81.42 et l'arbitrage v1 dit « pas "
            "de limite sur σc en XC1 »."
        ),
        validity_domain=(
            "La limite σc = 18 MPa est un artifice de saisie exigé par la commande, sans "
            "exigence de l'EC2 en XC1 : son inactivité est vérifiée par la sensibilité."
        ),
        sources=(_mm_complement(),),
        discarded_variants=(
            DiscardedVariant(
                description="ALPHA_E = Es/Ecm (≈ 6,4).", reason="MM retient 15."
            ),
            DiscardedVariant(
                description="SIGC_*_ELS non contraignant sans sensibilité.",
                reason="MM retient 0,6 fck et demande la sensibilité.",
            ),
            DiscardedVariant(
                description="KT = 0,6 (courte durée).", reason="Longue durée."
            ),
            DiscardedVariant(
                description="EYS = 200 000 MPa.",
                reason="MM retient 210 GPa, comme au quai.",
            ),
        ),
        decided_by=DECIDED_BY,
        decided_at=DECIDED_AT,
    )


def _mm_complement() -> PracticeSource:
    return PracticeSource(
        origin="arbitrage_mm",
        reference=f"{COMPLEMENT} (réponses de MM en séance, lot 43, phase 2)",
        date=date(2026, 10, 2),
    )


def arbitrate(proposed: HypothesesSheet) -> HypothesesSheet:
    entries = []
    for e in proposed.entries:
        if isinstance(e, PracticeHypothesisEntry):
            d = DECISIONS[e.point_label or ""]
            e = record_practice_decision(  # noqa: PLW2901
                entry=e,
                option_retained=str(d["option_retained"]),
                justification=str(d["justification"]),
                validity_domain=str(d["validity_domain"]),
                sources=d["sources"],  # type: ignore[arg-type]
                discarded_variants=d["discarded"],  # type: ignore[arg-type]
                decided_by=str(d["by"]),
                decided_at=DECIDED_AT,
            )
        entries.append(e)
    entries.append(els_parameters_entry())
    groups = tuple(
        MeshGroupNaming(
            group_name=name,
            kind=kind,  # type: ignore[arg-type]
            description=description,
            status="tranche",
            point_label=point,
        )
        for name, kind, description, point in GROUPS
    )
    return proposed.model_copy(
        update={"entries": tuple(entries), "group_naming": groups}
    )


def final_sheet() -> HypothesesSheet:
    """The arbitrated fiche as versioned: its `code_aster` entries replaced by
    references to the shared base (CA-046 to CA-051, versed by
    `verser_connaissances_lot43.py`; lot 41 rule)."""
    return externalize_sheet(arbitrate(build_sheet()), load_base(base_dir(ROOT)))


def render(sheet: HypothesesSheet) -> str:
    resolved = resolve_sheet(sheet, load_base(base_dir(ROOT)))
    data = load_model_data(DATA)
    blockers = resolved.generation_blockers(data)
    lines = [
        f"# Fiche arbitrée -- {sheet.project_name}",
        "",
        f"Décisions de MM reportées de `{REFERENCE}` (copie : "
        "`donnees/sources/arbitrage_dalle_appuyee_01_v1.md`), origine `arbitrage_mm`. "
        "Les articles d'Eurocode sont des références normatives fournies par MM, non "
        "indexées par l'outil.",
        "",
    ]
    for e in resolved.entries:
        if isinstance(e, PracticeHypothesisEntry):
            lines += [
                f"## Point {e.point_label} — {e.topic}",
                "",
                f"**Retenu** ({e.decided_by}) : {e.option_retained}",
                "",
                f"*Justification* : {e.justification}",
                "",
                f"*Domaine de validité* : {e.validity_domain}",
                "",
                "*Variantes écartées* :",
                *[f"- {v.description} — {v.reason}" for v in e.discarded_variants],
                "",
                "*Sources* : "
                + " ; ".join(f"{s.origin} : {s.reference}" for s in e.sources),
                "",
            ]
    lines += ["## Points établis par la documentation", ""]
    lines += [
        f"- Point {e.point_label} — {e.topic}"
        for e in resolved.entries
        if isinstance(e, CodeAsterHypothesisEntry)
    ]
    lines += ["", "## Noms de groupes (tranchés)", ""]
    lines += [
        f"- `{g.group_name}` ({g.kind}, point {g.point_label}) : {g.description}"
        for g in sheet.group_naming
    ]
    lines += ["", f"## Bloqueurs de génération : {len(blockers)}", ""]
    lines += [f"- {b}" for b in blockers] or ["- Aucun."]
    return "\n".join(lines) + "\n"


def main() -> int:
    sheet = final_sheet()
    resolved = resolve_sheet(sheet, load_base(base_dir(ROOT)))
    data = load_model_data(DATA)
    vocabulary = catalogue_vocabulary_or_empty()
    gaps = resolved.group_naming_gaps(vocabulary)
    discrepancies = check_consistency(data, resolved, SOURCES)
    FICHE.write_text(
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    DOCUMENT.write_text(render(sheet), encoding="utf-8")
    print(f"fiche arbitrée : {FICHE.relative_to(ROOT)}")
    print(f"bloqueurs (fiche et données) : {len(resolved.generation_blockers(data))}")
    print(f"écarts de nommage des groupes : {list(gaps)}")
    print(f"écarts données/sources : {[str(d) for d in discrepancies]}")
    return 1 if gaps or discrepancies else 0


def catalogue_vocabulary_or_empty() -> frozenset[str]:
    """Vocabulary of the installed catalogue (lot 25), empty when unavailable."""
    root = ROOT / "data" / "processed" / "catalogue"
    digests = sorted(p for p in root.glob("sha256:*") if p.is_dir())
    if not digests:
        return frozenset()
    return catalogue_vocabulary(root, digests[-1].name)


if __name__ == "__main__":
    raise SystemExit(main())
