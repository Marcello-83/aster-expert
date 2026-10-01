"""Lot 43 : fiche d'hypothèses PROPOSÉE de la dalle appuyée (jamais validée).

Construit `fiche/hypotheses_dalle_projet.json` et le document d'arbitrage
`fiche/fiche_a_arbitrer.md` par les seuls chemins d'écriture du tronc commun
(skill `hypotheses-drafting`) :

- `record_code_aster_finding` pour un point fondé par la documentation et le
  catalogue (extraits recopiés des lectures `get_document_section` de la session,
  vérifiés contre le corpus `external/codeaster-doc` quand il est présent) ;
- `FindingReference` pour un constat de la base partagée (jamais recopié) ;
- `record_unfounded_point` pour un point de pratique, avec la trace des recherches,
  et `propose_precedent` pour un précédent du quai jugé applicable (fusionnés par
  `_with_precedent` : l'entrée reste non tranchée) ;
- `MeshGroupNaming` non tranchés.

Aucune décision pratique n'est prise ici : MM arbitre (lot 43, interdits).
Déterministe : relancer le script réécrit les mêmes octets.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/build_fiche_lot43.py`
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.arbitration import render_decision_sheet
from aster_expert.agent.drafting import (
    SearchAttempt,
    record_code_aster_finding,
    record_unfounded_point,
)
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
    FindingReference,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
)
from aster_expert.agent.model_data import check_consistency, load_model_data
from aster_expert.connaissances.base import load_knowledge
from aster_expert.connaissances.modeles import Precedent
from aster_expert.connaissances.precedents import propose_precedent
from aster_expert.constats.base import base_dir, load_base, resolve_sheet

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
FICHE = PROJECT / "fiche" / "hypotheses_dalle_projet.json"
DOCUMENT = PROJECT / "fiche" / "fiche_a_arbitrer.md"
DATA = PROJECT / "donnees" / "dalle_model_data.yaml"
SOURCES = PROJECT / "donnees" / "sources"
CORPUS = ROOT / "external" / "codeaster-doc"

VERSION = "17.4.0"
DOC_COMMIT = "9c8c179f57ef7ca1d2891cac275ee4823a57967c"
SRC_COMMIT = "50ebc13c70ee9df62faf93ddcb746a3757b3042a"
CATALOGUE_HASH = "b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca"
IMAGE_DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
CREATED_AT = datetime.fromisoformat("2026-10-01T12:00:00-04:00")


def _doc(
    document_id: str,
    section: tuple[str, ...],
    source_path: str,
    profile: str,
    excerpt: str,
) -> DocumentarySource:
    return DocumentarySource(
        document_id=document_id,
        aster_version=VERSION,
        section_path=section,
        source_path=source_path,
        source_commit=DOC_COMMIT,
        profile=profile,
        excerpt=excerpt,
    )


def _cat(command: str, *keyword_path: str) -> CatalogueSource:
    return CatalogueSource(
        command=command,
        aster_version=VERSION,
        keyword_path=keyword_path,
        catalogue_hash=CATALOGUE_HASH,
        image_digest=IMAGE_DIGEST,
    )


# --- sources documentaires (extraits recopiés des lectures intégrales) -----------

R3_07_03_INTRO = _doc(
    "R3.07.03",
    ("Introduction",),
    "source/manuals/man_r/r3/r3.07.03/Introduction.rst",
    "methode",
    '"DST", "DST, DSQ", "modèle avec énergie de cisaillement transverse en élasticité"',
)
R3_07_03_DKT = _doc(
    "R3.07.03",
    ("Introduction",),
    "source/manuals/man_r/r3/r3.07.03/Introduction.rst",
    "methode",
    '"DKT", "DKT, DKQ", "modèle de Love-Kirchhoff, dédié aux relations de comportement '
    "linéaire et non linéaires",
)
U2_02_01_MINCE = _doc(
    "U2.02.01",
    ("Conclusion_et_conseils_d_utilisation",),
    "source/manuals/man_u/u2/u2.02.01/Conclusion_et_conseils_d_utilisation.rst",
    "methode",
    "pour ces structures, dont le rapport h/L est inférieur à 1/20, les effets de "
    "cisaillement transverse peuvent être négligés et la théorie de Kirchhoff s’applique.",
)
U2_02_01_EPAIS = _doc(
    "U2.02.01",
    ("Conclusion_et_conseils_d_utilisation",),
    "source/manuals/man_u/u2/u2.02.01/Conclusion_et_conseils_d_utilisation.rst",
    "methode",
    "pour ces structures, on utilisera des éléments de plaque DST, DSQ et Q4G qui tiennent "
    "compte du cisaillement transverse",
)
U4_44_01_FORCE_COQUE = _doc(
    "U4.44.01",
    (
        "Chargements_de_type_Neumann_pour_les__l_ments_de_structure_",
        "Chargements de type Neumann pour les éléments de structure",
        "Mot-clé FORCE_COQUE",
    ),
    "source/manuals/man_u/u4/u4.44.01/Chargements_de_type_Neumann_pour_les__l_ments_de_structure_.rst",
    "syntaxe",
    "La pression appliquée est positive suivant le sens contraire de la normale à "
    "l’élément",
)
U4_44_01_GLOBAL = _doc(
    "U4.44.01",
    (
        "Chargements_de_type_Neumann_pour_les__l_ments_de_structure_",
        "Chargements de type Neumann pour les éléments de structure",
        "Mot-clé FORCE_COQUE",
    ),
    "source/manuals/man_u/u4/u4.44.01/Chargements_de_type_Neumann_pour_les__l_ments_de_structure_.rst",
    "syntaxe",
    "Dans le repère **global**  avec les mot-clefs FX, FY, FZ, MX, MY et MZ",
)
V3_03_127_APPUI = _doc(
    "V3.03.127",
    ("Solution_de_r_f_rence",),
    "source/manuals/man_v/v3/v3.03.127/Solution_de_r_f_rence.rst",
    "theorie",
    "La dalle est simplement appuyée sur les quatre lisières",
)

DOCUMENTARY = (
    R3_07_03_INTRO,
    R3_07_03_DKT,
    U2_02_01_MINCE,
    U2_02_01_EPAIS,
    U4_44_01_FORCE_COQUE,
    U4_44_01_GLOBAL,
    V3_03_127_APPUI,
)


def check_excerpts(corpus: Path = CORPUS) -> list[str]:
    """Excerpts not found verbatim in their source file (empty: all found).
    Without the corpus (Cloud), nothing can be checked: the list says so."""
    if not corpus.is_dir():
        return [f"corpus absent : {corpus}"]
    missing = []
    for source in DOCUMENTARY:
        assert source.source_path is not None
        assert source.excerpt is not None
        text = (corpus / source.source_path).read_text(encoding="utf-8")
        if source.excerpt not in text:
            missing.append(f"{source.document_id} : {source.excerpt[:60]}…")
    return missing


# --- points code_aster ------------------------------------------------------------


def _code_aster_entries() -> tuple[CodeAsterHypothesisEntry | FindingReference, ...]:
    plate_models = record_code_aster_finding(
        point_label="1",
        topic="Modélisations de plaque recevables pour une dalle plane et leur cinématique",
        options_considered=("DKT", "DKTG", "DST", "Q4G", "Q4GG", "COQUE_3D"),
        option_retained=(
            "Le catalogue 17.4 (AFFE_MODELE/AFFE/MODELISATION) propose pour une plaque plane "
            "DKT et DKTG (modèle de Love-Kirchhoff, sans énergie de cisaillement transverse), "
            "DST, Q4G et Q4GG (énergie de cisaillement transverse en élasticité), et la coque "
            "COQUE_3D. U2.02.01 conseille DKT/DKQ pour h/L < 1/20 (Kirchhoff) et DST/DSQ/Q4G "
            "(ou de préférence une coque courbe) pour une structure épaisse."
        ),
        justification=(
            "R3.07.03 § Introduction classe DKT (Love-Kirchhoff) et DST/Q4G (cisaillement "
            "transverse) ; U2.02.01 § Conclusion et conseils d'utilisation donne la limite "
            "h/L < 1/20 des structures minces ; valeurs confirmées au catalogue."
        ),
        notes=(
            "Pour la dalle, h/L = 0,30/4,00 = 1/13,3 sur la petite portée (1/20 sur la "
            "grande) : la dalle est entre la limite « mince » (1/20) et la limite des plaques "
            "(1/10, constat CA-002). Les documents lus ne disent pas quelle modélisation "
            "retenir dans cette zone. Cas test officiel le plus proche : SSLS127 (V3.03.127, "
            "dalle en béton armé appuyée sur 4 côtés, régime élastique), modélisé en DKTG et "
            "Q4GG, jamais en DKT (ssls127d.comm, codeaster-src "
            + SRC_COMMIT[:12]
            + ")."
        ),
        sources=(
            R3_07_03_INTRO,
            R3_07_03_DKT,
            U2_02_01_MINCE,
            U2_02_01_EPAIS,
            _cat("AFFE_MODELE", "AFFE", "MODELISATION"),
        ),
    )
    thickness = record_code_aster_finding(
        point_label="1",
        topic="Caractéristiques de plaque : épaisseur et repère local (AFFE_CARA_ELEM/COQUE)",
        option_retained=(
            "AFFE_CARA_ELEM/COQUE porte EPAIS (réel), ANGL_REP ou VECTEUR (repère local de "
            "référence des efforts généralisés), A_CIS (défaut 0,8333333), COEF_RIGI_DRZ "
            "(défaut 1e-5) et EXCENTREMENT ; GROUP_MA est obligatoire."
        ),
        justification="Schéma du catalogue 17.4 (mot-clé facteur COQUE de AFFE_CARA_ELEM).",
        sources=(
            _cat("AFFE_CARA_ELEM", "COQUE", "EPAIS"),
            _cat("AFFE_CARA_ELEM", "COQUE", "ANGL_REP"),
            _cat("AFFE_CARA_ELEM", "COQUE", "VECTEUR"),
        ),
    )
    loads = record_code_aster_finding(
        point_label="4",
        topic="Application du poids propre et d'une charge surfacique uniforme sur une plaque",
        options_considered=(
            "FORCE_COQUE/FZ (repère global)",
            "FORCE_COQUE/PRES (normale à la maille)",
        ),
        option_retained=(
            "Poids propre : AFFE_CHAR_MECA/PESANTEUR (GRAVITE, DIRECTION), avec RHO de "
            "DEFI_MATERIAU/ELAS. Charge surfacique : AFFE_CHAR_MECA/FORCE_COQUE, soit FZ dans "
            "le repère global, soit PRES, positive dans le sens contraire de la normale à la "
            "maille (le sens dépend donc de l'orientation des mailles, ORIE_NORM_COQUE)."
        ),
        justification=(
            "U4.44.01 § Mot-clé FORCE_COQUE (lu en entier) ; catalogue 17.4 (PESANTEUR, "
            "FORCE_COQUE). Le cas test ssls127d.comm applique FORCE_COQUE/PRES = -10000 Pa "
            "après MODI_MAILLAGE/ORIE_NORM_COQUE (VECT_NORM = (0, 0, 1))."
        ),
        sources=(
            U4_44_01_FORCE_COQUE,
            U4_44_01_GLOBAL,
            _cat("AFFE_CHAR_MECA", "PESANTEUR", "GRAVITE"),
            _cat("AFFE_CHAR_MECA", "FORCE_COQUE", "FZ"),
            _cat("AFFE_CHAR_MECA", "FORCE_COQUE", "PRES"),
        ),
    )
    analysis = record_code_aster_finding(
        point_label="5",
        topic="Opérateur de résolution et loi élastique isotrope",
        option_retained=(
            "Statique linéaire : MECA_STATIQUE (MODELE, CHAM_MATER, CARA_ELEM, EXCIT), "
            "résultat evol_elas. Matériau : DEFI_MATERIAU/ELAS (E, NU, RHO)."
        ),
        justification=(
            "Schémas du catalogue 17.4 (MECA_STATIQUE, DEFI_MATERIAU/ELAS). Cas test "
            "ssls135a.comm (DKT, béton ELAS E = 3e10, NU = 0,15, RHO = 2500, MECA_STATIQUE "
            "puis CALC_FERRAILLAGE 2D) : même chaîne d'opérateurs."
        ),
        sources=(
            _cat("MECA_STATIQUE"),
            _cat("DEFI_MATERIAU", "ELAS", "E"),
            _cat("DEFI_MATERIAU", "ELAS", "NU"),
            _cat("DEFI_MATERIAU", "ELAS", "RHO"),
        ),
    )
    supports = record_code_aster_finding(
        point_label="6",
        topic="Appui simple d'une dalle en plaque et blocages de symétrie dans le cas test officiel",
        option_retained=(
            "DDL_IMPO de AFFE_CHAR_MECA bloque DX, DY, DZ, DRX, DRY, DRZ par GROUP_NO ou "
            "GROUP_MA. Dans SSLS127 (dalle appuyée sur ses quatre lisières), l'appui simple "
            "est DZ = 0 sur les bords, rotations libres ; sur le quart de dalle, la symétrie "
            "de normale Y bloque DY et DRX, celle de normale X bloque DX et DRY."
        ),
        justification=(
            "Catalogue 17.4 (AFFE_CHAR_MECA/DDL_IMPO) ; V3.03.127 § Solution de référence ; "
            "ssls127d.comm (codeaster-src " + SRC_COMMIT[:12] + ") : "
            'DDL_IMPO=(_F(GROUP_NO=("LCONTX", "LCONTY"), DZ=0.0), '
            '_F(GROUP_NO="LSYMX", DY=0.0, DRX=0.0), _F(GROUP_NO="LSYMY", DX=0.0, DRY=0.0)).'
        ),
        notes=(
            "Un cas test est une référence exécutable, pas un modèle transposable : SSLS127 "
            "est en Q4GG/DKTG, sur un quart de dalle. Il ne bloque pas DRZ aux plans de "
            "symétrie, alors que le constat CA-030 (DKT, plan X = constante) bloque DX, DRY, "
            "DRZ : les deux sont rapportés, sans être départagés ici."
        ),
        sources=(
            V3_03_127_APPUI,
            _cat("AFFE_CHAR_MECA", "DDL_IMPO", "DZ"),
            _cat("AFFE_CHAR_MECA", "DDL_IMPO", "DRX"),
            _cat("AFFE_CHAR_MECA", "DDL_IMPO", "DRY"),
        ),
    )
    rebar = record_code_aster_finding(
        point_label="14",
        topic="CALC_FERRAILLAGE en 2D : options disponibles dans le catalogue 17.4",
        options_considered=("METHODE_2D='CAPRA-MAURY'", "METHODE_2D='SANDWICH'"),
        option_retained=(
            "CALC_FERRAILLAGE (CODIFICATION='EC2' par défaut) : TYPE_COMB ELU, ELS ou ELS_QP ; "
            "METHODE_2D CAPRA-MAURY (défaut) ou SANDWICH ; UNITE_CONTRAINTE MPa ou Pa "
            "(obligatoire) ; en 2D, C_INF et C_SUP obligatoires (une valeur par face, "
            "commune aux deux directions) ; FCK, FYK, GAMMA_C, GAMMA_S, ALPHA_CC (défaut "
            "0,85), SIGS_ELS, SIGC_INF_ELS, SIGC_SUP_ELS, WMAX_INF, WMAX_SUP, SIGC_ELS_QP, "
            "KT, PHI_INF_X/Y, PHI_SUP_X/Y, FERR_MIN (VALE_MIN ou EC2), FERR_MIN_FISS. Sortie : "
            "densités DNSXI, DNSXS, DNSYI, DNSYS (champ FERR_ELEM)."
        ),
        justification=(
            "Schéma complet du catalogue 17.4 (get_command_schema, CALC_FERRAILLAGE) ; cas test "
            "ssls135a.comm (DKT, TYPE_STRUCTURE='2D', TYPE_COMB='ELS', C_INF = C_SUP = 0,04, "
            "composantes DNSXI…DNSYS de FERR_ELEM)."
        ),
        notes=(
            "Déduction : en 2D, CALC_FERRAILLAGE n'admet qu'une distance C_INF (et C_SUP) pour "
            "les deux nappes d'une face, alors que, dans une dalle réelle, les nappes X et Y "
            "d'une même face sont à des hauteurs différentes (l'une est au-dessus de "
            "l'autre). Le choix de la valeur unique est une question de pratique (point 14)."
        ),
        sources=(
            _cat("CALC_FERRAILLAGE", "TYPE_COMB"),
            _cat("CALC_FERRAILLAGE", "METHODE_2D"),
            _cat("CALC_FERRAILLAGE", "AFFE", "C_INF"),
            _cat("CALC_FERRAILLAGE", "AFFE", "WMAX_INF"),
            _cat("CALC_FERRAILLAGE", "UNITE_CONTRAINTE"),
        ),
    )
    references = (
        # Critère d'élancement 1/10 (U2.02.01, R3.07.03).
        FindingReference(constat_id="CA-002", point_label="1"),
        # Efforts généralisés EFGE_* : grandeurs à lire sur une plaque (exactes).
        FindingReference(constat_id="CA-025", point_label="1"),
        # Poids propre sous PESANTEUR : RHO × EPAIS × g.
        FindingReference(constat_id="CA-024", point_label="4"),
        # Effort surfacique de direction globale fixe : FORCE_COQUE/FX, FY, FZ.
        FindingReference(constat_id="CA-018", point_label="4"),
        # Symétrie d'un plan X = constante pour DKT : DX, DRY, DRZ.
        FindingReference(constat_id="CA-030", point_label="6"),
        # Réactions : exactes si FLEX = MEMB·EPAIS²/12 (ELAS isotrope + EPAIS).
        FindingReference(constat_id="CA-023", point_label="6"),
        # Commandes de ferraillage de la version 17.4.
        FindingReference(constat_id="CA-039", point_label="14"),
        # Ferraillage minimal : FERR_MIN='EC2' juste en MPa seulement.
        FindingReference(constat_id="CA-041", point_label="14"),
        # 2D Capra-Maury : MXX > 0 tend la face supérieure (côté normale).
        FindingReference(constat_id="CA-045", point_label="14"),
    )
    return (plate_models, thickness, loads, analysis, supports, rebar, *references)


# --- points de pratique -----------------------------------------------------------


def _precedents() -> dict[str, Precedent]:
    base = load_knowledge(ROOT)
    return {k: v for k, v in base.entries.items() if isinstance(v, Precedent)}


def _with_precedent(
    entry: PracticeHypothesisEntry, precedent_id: str, precedents: dict[str, Precedent]
) -> PracticeHypothesisEntry:
    """Merge a precedent proposal into an unfounded point: its option joins the
    options, its notes join the search trace. Still `non_tranche`."""
    proposal, _source = propose_precedent(
        precedents[precedent_id],
        point_label=entry.point_label or "?",
        topic=entry.topic,
    )
    return entry.model_copy(
        update={
            "options_considered": entry.options_considered
            + proposal.options_considered,
            "notes": f"{entry.notes} {proposal.notes}",
        }
    )


def _practice_entries() -> tuple[PracticeHypothesisEntry, ...]:
    precedents = _precedents()
    perimeter = record_unfounded_point(
        point_label="0",
        topic="Objet et périmètre du calcul",
        searches=(
            SearchAttempt(
                profile="methode",
                query="précédents : périmètre du calcul (search_connaissances, couche precedents)",
                outcome=(
                    "PRE-009 (quai) : périmètre d'un modèle 3D d'écran ; son contenu (géotechnique "
                    "amont, charges localisées) ne s'applique pas à une dalle isolée, non proposé"
                ),
            ),
        ),
        options_considered=(
            "Calcul élastique linéaire de la dalle seule (plaque), béton non fissuré, "
            "chargement statique ; flèches instantanées ; ferraillage par CALC_FERRAILLAGE "
            "sur les efforts élastiques.",
            "Même calcul, complété d'une estimation des flèches à long terme (fluage, "
            "fissuration) hors du modèle élastique.",
        ),
        deduction=(
            "MM demande « les déplacements » sans dire s'ils sont instantanés ou à long terme ; "
            "un calcul élastique linéaire ne donne que les premiers. La comparaison à Navier "
            "(niveau E) porte sur le calcul élastique."
        ),
    )
    element = record_unfounded_point(
        point_label="1",
        topic="Choix de la modélisation de plaque de la dalle (h/L = 1/13,3)",
        searches=(
            SearchAttempt(
                profile="methode",
                query="DKT DST Kirchhoff cisaillement transverse plaque mince épaisse choix modélisation",
                outcome=(
                    "U2.02.01 § Conclusion : DKT pour h/L < 1/20, DST/Q4G ou coque courbe pour "
                    "les structures épaisses ; rien pour 1/20 < h/L < 1/10"
                ),
            ),
            SearchAttempt(
                profile="methode",
                query="plaque rectangulaire simplement appuyée pression uniforme flèche centre DKT (famille V)",
                outcome="SSLS127 (DKTG, Q4GG), SSNV129 (DKT, contact) : aucun ne départage DKT et DST pour cet élancement",
            ),
            SearchAttempt(
                profile="methode",
                query="précédents : choix de modélisation de coque (search_connaissances, couche precedents)",
                outcome=(
                    "PRE-001 et PRE-011 (quai) : tube métallique facettisé de 14 mm, élancement "
                    "sans rapport ; non proposés"
                ),
            ),
        ),
        options_considered=(
            "DKT (Love-Kirchhoff) : cohérent avec la référence de Navier demandée (Kirchhoff) ; "
            "ignore la déformation d'effort tranchant.",
            "DST (cisaillement transverse, k = 5/6) : plus proche de la plaque épaisse ; la "
            "flèche dépasse alors celle de Kirchhoff d'un terme d'effort tranchant, la "
            "comparaison à Navier n'est plus exacte.",
            "Q4GG (modélisation du cas test SSLS127).",
        ),
        deduction=(
            "Le niveau E demandé (Navier, Kirchhoff) n'est exact que pour DKT ; avec DST, il "
            "faudrait une référence de Reissner-Mindlin ou accepter un écart de cisaillement "
            "à estimer. Les mailles QUAD4 donnent l'élément DKQ (R3.07.03)."
        ),
    )
    loads = record_unfounded_point(
        point_label="4",
        topic="Valeurs et application des charges : poids volumique, g, forme de la charge d'exploitation",
        searches=(
            SearchAttempt(
                profile="syntaxe",
                query="FORCE_COQUE PRES pression positive normale sens FX FY FZ repère global",
                outcome="U4.44.01 § FORCE_COQUE : FZ global ou PRES normale ; ne fixe aucune valeur de charge",
            ),
            SearchAttempt(
                profile="methode",
                query="précédents : poids propre, poids volumique (search_connaissances, couche precedents)",
                outcome="aucun précédent sur le poids volumique d'un béton armé",
            ),
        ),
        options_considered=(
            "Poids volumique du béton armé 25 kN/m³ (EN 1991-1-1, annexe A, tableau A.1), "
            "RHO et g choisis pour le reproduire.",
            "RHO = 2500 kg/m³ et g = 9,81 m/s² (poids 24,5 kN/m³).",
            "Exploitation par FORCE_COQUE/FZ (indépendante de l'orientation des mailles).",
            "Exploitation par FORCE_COQUE/PRES après ORIE_NORM_COQUE (schéma de SSLS127).",
            "Exploitation sur toute la dalle seulement, ou aussi des dispositions partielles "
            "(damier) pour les moments maximaux.",
        ),
        deduction=(
            "Une dalle isostatique sur quatre appuis simples sous charge uniforme a ses "
            "moments maximaux sous chargement total ; une disposition partielle n'est utile "
            "que pour une dalle continue (hors périmètre de la description)."
        ),
    )
    material = record_unfounded_point(
        point_label="5",
        topic="Paramètres élastiques du béton C30/37 (E, ν) et hypothèse de béton non fissuré",
        searches=(
            SearchAttempt(
                profile="methode",
                query="précédents : module béton (search_connaissances, couche precedents)",
                outcome="aucun résultat",
            ),
        ),
        options_considered=(
            "E = Ecm (EN 1992-1-1, tableau 3.1, C30/37), ν = 0,2 (EN 1992-1-1, 3.1.3(4), "
            "béton non fissuré).",
            "ν = 0 (EN 1992-1-1, 3.1.3(4), béton fissuré).",
            "Module effectif à long terme pour les flèches différées.",
        ),
        deduction=(
            "Les moments de Navier dépendent de ν (Mx et My au centre) mais pas de E ; la "
            "flèche dépend de E et de ν. La valeur de ν est donc à fixer avant le critère du "
            "niveau E."
        ),
    )
    boundary = record_unfounded_point(
        point_label="6",
        topic="Représentation de l'appui simple et des mouvements de corps rigide de membrane",
        searches=(
            SearchAttempt(
                profile="theorie",
                query="plaque mince simplement appuyée charge uniforme solution analytique (famille V)",
                outcome="SSLS127 : DZ = 0 sur le contour, quart de dalle ; ne dit rien des coins ni de la membrane",
            ),
            SearchAttempt(
                profile="methode",
                query="précédents : appui (search_connaissances, couches precedents et patrons)",
                outcome="PRE-014 (appui vertical d'un écran, DZ au pied des tubes) : hors sujet, non proposé",
            ),
        ),
        options_considered=(
            "Appui bilatéral DZ = 0 sur tout le contour, rotations libres (« appui simple » de "
            "Navier : les coins sont retenus contre le soulèvement).",
            "Appui unilatéral (contact) : les coins peuvent se soulever ; non linéaire, hors "
            "de la solution de Navier.",
            "Blocage de membrane minimal (DX, DY en un coin, DY ou DX en un second) pour "
            "supprimer les mouvements de corps rigide dans le plan, sans effort parasite.",
            "Dalle entière, ou quart de dalle avec deux plans de symétrie (schéma de SSLS127).",
        ),
        deduction=(
            "La solution de Navier suppose w = 0 et Mn = 0 sur tout le bord, donc des réactions "
            "de coin dirigées vers le bas (les coins sont tenus). Un modèle « DZ = 0 bilatéral » "
            "la reproduit ; un appui réel qui laisse les coins se soulever n'est pas cette plaque."
        ),
    )
    frame = _with_precedent(
        record_unfounded_point(
            point_label="9",
            topic="Repère global, origine et unités du modèle",
            searches=(
                SearchAttempt(
                    profile="methode",
                    query="précédents : repère global (search_connaissances, couche precedents)",
                    outcome="PRE-012 (quai, point 9) : repère déclaré dans la fiche, unités m, N, Pa, kg",
                ),
            ),
            options_considered=(
                "Origine au coin de la dalle, X le long du grand côté (0 à 6,00), Y le long du "
                "petit côté (0 à 4,00), Z vertical ascendant (repère de la série de Navier).",
                "Origine au centre de la dalle (symétries en X = 0 et Y = 0).",
            ),
        ),
        "PRE-012",
        precedents,
    )
    mesh = _with_precedent(
        record_unfounded_point(
            point_label="10",
            topic="Discrétisation : type de mailles, taille, étude de convergence, nœud au centre",
            searches=(
                SearchAttempt(
                    profile="methode",
                    query="convergence maillage (search_connaissances, toutes couches)",
                    outcome="aucun résultat : la base ne contient aucune étude de convergence",
                ),
            ),
            options_considered=(
                "QUAD4 réguliers (DKQ), nombre pair de mailles par côté pour qu'un nœud tombe au "
                "centre ; suite de trois maillages à tailles divisées par 2 (critère de "
                "convergence de CLAUDE.md).",
                "TRIA3 (DKT triangulaire).",
                "Moments au centre lus en EFGE_NOEU (moyenne aux nœuds) ou en EFGE_ELNO d'une "
                "maille adjacente au centre (SSLS127 lit EFGE_ELNO d'une maille).",
            ),
        ),
        "PRE-013",
        precedents,
    )
    combinations = _with_precedent(
        record_unfounded_point(
            point_label="13",
            topic="Combinaisons d'actions ELU et ELS (poids propre G, exploitation Q)",
            searches=(
                SearchAttempt(
                    profile="methode",
                    query="précédents : combinaisons (search_connaissances, couche precedents)",
                    outcome="PRE-016 (quai, point 13) : combinaisons de l'EN 1990, γG 1,35/1,00, γQ 1,50",
                ),
            ),
            options_considered=(
                "ELU fondamentale γG G + γQ Q ; ELS caractéristique G + Q ; ELS quasi permanente "
                "G + ψ2 Q (EN 1990, 6.10, 6.14b, 6.16b), ψ selon la catégorie d'usage.",
            ),
        ),
        "PRE-016",
        precedents,
    )
    durability = _with_precedent(
        _with_precedent(
            record_unfounded_point(
                point_label="14",
                topic="Ferraillage : acier, distance parement–axe, ELS en XC1 (contraintes, fissuration), ferraillage minimal",
                searches=(
                    SearchAttempt(
                        profile="methode",
                        query="précédents : enrobage, fissuration, axe des armatures (search_connaissances)",
                        outcome="PRE-017 (durabilité du quai, XS3, wk 0,2 mm) et PRE-018 (axe des armatures à 0,10 m) trouvés",
                    ),
                    SearchAttempt(
                        profile="syntaxe",
                        query="CALC_FERRAILLAGE (get_command_schema)",
                        outcome="TYPE_COMB ELU/ELS/ELS_QP, WMAX_INF/WMAX_SUP en 2D, METHODE_2D CAPRA-MAURY/SANDWICH",
                    ),
                ),
                options_considered=(
                    "Acier B500B (fyk = 500 MPa, classe B) — à confirmer, la description ne le "
                    "donne pas.",
                    "Distance parement–axe = enrobage + φ/2 de la nappe extérieure, une valeur "
                    "par face (C_INF, C_SUP) commune aux deux directions, ou la valeur de la "
                    "nappe intérieure (plus défavorable).",
                    "ELS en XC1 : maîtrise de la fissuration sous combinaison quasi permanente "
                    "(ELS_QP, WMAX) avec wk de l'EN 1992-1-1, tableau 7.1N ; limitation des "
                    "contraintes sous combinaison caractéristique (ELS, SIGS_ELS, SIGC_*_ELS) "
                    "selon EN 1992-1-1, 7.2.",
                    "Ferraillage minimal : FERR_MIN='EC2' (en MPa, constat CA-041) ou aucun.",
                    "METHODE_2D : CAPRA-MAURY (défaut, constat CA-045) ou SANDWICH.",
                    "γc, γs, αcc : valeurs de l'EN 1992-1-1 (tableau 2.1N, 3.1.6) ou de l'annexe "
                    "nationale ; ALPHA_CC vaut 0,85 par défaut dans le catalogue.",
                ),
                deduction=(
                    "L'enrobage de 30 mm n'est pas la distance à l'axe (PRE-018) ; il faut un "
                    "diamètre de barre pour passer de l'un à l'autre. ALPHA_CC = 0,85 par défaut "
                    "dans CALC_FERRAILLAGE alors que le quai a retenu 1,0 (projet.yaml du quai) : "
                    "valeur à fixer explicitement."
                ),
            ),
            "PRE-017",
            precedents,
        ),
        "PRE-018",
        precedents,
    )
    return (
        perimeter,
        element,
        loads,
        material,
        boundary,
        frame,
        mesh,
        combinations,
        durability,
    )


GROUPS = (
    MeshGroupNaming(
        group_name="DALLE",
        kind="maille",
        description="Toutes les mailles QUAD4 de la dalle.",
        point_label="1",
    ),
    MeshGroupNaming(
        group_name="BORD_X0",
        kind="maille",
        description="Bord X = 0 (SEG2), appui simple.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="BORD_XL",
        kind="maille",
        description="Bord X = longueur (SEG2), appui simple.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="BORD_Y0",
        kind="maille",
        description="Bord Y = 0 (SEG2), appui simple.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="BORD_YL",
        kind="maille",
        description="Bord Y = largeur (SEG2), appui simple.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="APPUIS",
        kind="noeud",
        description="Nœuds des quatre bords (appui simple, réactions).",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="COIN_O",
        kind="noeud",
        description="Nœud du coin (0, 0) : blocage de membrane.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="COIN_X",
        kind="noeud",
        description="Nœud du coin (longueur, 0) : blocage de membrane.",
        point_label="6",
    ),
    MeshGroupNaming(
        group_name="CENTRE",
        kind="noeud",
        description="Nœud au centre de la dalle (flèche et moments du niveau E).",
        point_label="10",
    ),
)


def build_sheet() -> HypothesesSheet:
    return HypothesesSheet(
        project_name="DALLE-APPUYEE-01",
        structure_description=(
            "Dalle en béton armé C30/37 de 6,00 m × 4,00 m et 0,30 m d'épaisseur, simplement "
            "appuyée sur ses quatre côtés ; poids propre et exploitation uniforme de 10 kPa ; "
            "déplacements, moments et ferraillage (ELU, ELS en XC1, enrobage 30 mm), avec "
            "comparaison à la solution analytique (description de MM, lot 43)."
        ),
        aster_version=VERSION,
        created_at=CREATED_AT,
        entries=(*_code_aster_entries(), *_practice_entries()),
        group_naming=GROUPS,
    )


PREAMBLE = """\
> **Fiche PROPOSÉE, non validée (lot 43).** Elle a été rédigée par la session à partir
> de la documentation, du catalogue 17.4, des cas tests et de la base `connaissances/`.
> Les points « code_aster » sont établis par les sources citées (niveau A ou B) ; les
> points « pratique » ci-dessous sont des **questions** : aucune option n'est retenue,
> les précédents du quai sont **proposés**, jamais appliqués. Tant que MM n'a pas
> tranché chaque point et chaque nom de groupe, la génération est bloquée.
>
> Les articles de l'EN 1990, de l'EN 1991-1-1 et de l'EN 1992-1-1 cités dans les options
> le sont **sans accès au texte des normes** (l'outil n'en indexe aucune) : chaque
> renvoi est à vérifier par MM avant d'être retenu.

"""


def render(sheet: HypothesesSheet) -> str:
    resolved = resolve_sheet(sheet, load_base(base_dir(ROOT)))
    data = load_model_data(DATA)
    blockers = resolved.generation_blockers(data)
    discrepancies = check_consistency(data, resolved, SOURCES)
    code_aster = [e for e in resolved.entries if e.nature == "code_aster"]
    lines = [
        render_decision_sheet(resolved).rstrip(),
        "",
        "## Points établis par la documentation (rappel)",
        "",
    ]
    for e in code_aster:
        assert isinstance(e, CodeAsterHypothesisEntry)
        lines.append(f"- **Point {e.point_label}** — {e.topic} : {e.option_retained}")
    lines += ["", "## Noms de groupes proposés (à trancher)", ""]
    lines += [
        f"- `{g.group_name}` ({g.kind}, point {g.point_label}) : {g.description}"
        for g in sheet.group_naming
    ]
    lines += ["", f"## Bloqueurs de génération ({len(blockers)}, fiche et données)", ""]
    lines += [f"- {b}" for b in blockers]
    lines += ["", "## Cohérence des données fournies avec leur source", ""]
    lines += [f"- écart : {d}" for d in discrepancies] or [
        "- Aucun écart : chaque valeur fournie figure dans le texte de sa source "
        "(`check_consistency`)."
    ]
    return PREAMBLE + "\n".join(lines) + "\n"


def main() -> int:
    missing = check_excerpts()
    if missing and not missing[0].startswith("corpus absent"):
        print("extraits introuvables dans le corpus :", *missing, sep="\n  ")
        return 1
    sheet = build_sheet()
    FICHE.write_text(
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    DOCUMENT.write_text(render(sheet), encoding="utf-8")
    code_aster = sum(1 for e in sheet.entries if e.nature in ("code_aster", "constat"))
    practice = sum(1 for e in sheet.entries if e.nature == "pratique")
    print(f"fiche écrite : {FICHE.relative_to(ROOT)}")
    print(f"document d'arbitrage : {DOCUMENT.relative_to(ROOT)}")
    print(
        f"entrées code_aster tranchées : {code_aster - len(sheet.finding_references())} "
        f"(+ {len(sheet.finding_references())} constats référencés) ; "
        f"entrées pratique non tranchées : {practice} ; "
        f"is_ready_for_generation : {sheet.is_ready_for_generation}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
