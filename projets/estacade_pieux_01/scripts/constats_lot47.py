"""Lot 47 -- findings of the probe S1 written in the shared base (CA-054 to CA-057).

Each finding carries the execution source of the probe
(`references/cas/sonde_lot47.comm`, run of commit 9519b6c, criteria of
`docs/essais_lot47.md` section 1 written before the run); every value cited is
printed in the versioned listing extract `references/cas/sonde_lot47_listing_extrait.txt`.
The fiche of the jetty references them (`FindingReference`). Idempotent: rerun
`.venv/bin/python projets/estacade_pieux_01/scripts/constats_lot47.py`.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.drafting import record_execution_finding
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
    ExecutionSource,
)
from aster_expert.constats.base import base_dir, build_constat, write_constat
from aster_expert.constats.models import FindingOrigin

VERSION = "17.4.0"
DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
COMMIT = "9519b6c2ee8bef547f820a7e4c7102438d5bf5af"
CASE = "projets/estacade_pieux_01/references/cas/sonde_lot47.comm"
LISTING = "projets/estacade_pieux_01/references/cas/sonde_lot47_listing_extrait.txt"
FICHE = "projets/estacade_pieux_01/fiche/hypotheses_estacade_pieux_01.json"
ORIGIN_PROJECT = "ESTACADE-PIEUX-01"
DOC_COMMIT = "9c8c179f57ef7ca1d2891cac275ee4823a57967c"


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _execution(
    quantity: str, obtained: float, reference: str, expected: float
) -> ExecutionSource:
    return ExecutionSource(
        aster_version=VERSION,
        image_digest=DIGEST,
        repo_commit=COMMIT,
        working_tree_modified=False,
        case_path=CASE,
        case_sha256=_sha(CASE),
        mess_path=LISTING,
        quantity=quantity,
        value_obtained=obtained,
        reference=reference,
        reference_value=expected,
        relative_deviation=(obtained - expected) / expected,
        validation_level="D",
    )


def _u2_thermal() -> DocumentarySource:
    return DocumentarySource(
        document_id="U2.02.01",
        aster_version=VERSION,
        section_path=("Cha_nage_thermom_canique",),
        source_path="source/manuals/man_u/u2/u2.02.01/Cha_nage_thermom_canique.rst",
        source_commit=DOC_COMMIT,
        fragment_id="U2.02.01#Cha_nage_thermom_canique",
        profile="methode",
        excerpt=(
            "Pour ces éléments, il est nécessaire de préparer le calcul de la "
            "température sur les couches en amont de la commande *AFFE_MATERIAU* . "
            "Pour cela, l'utilisateur doit utiliser la commande *CREA_RESU*  avec "
            "l'opération *PREP_VARC*"
        ),
    )


def _u4_force_arete() -> DocumentarySource:
    return DocumentarySource(
        document_id="U4.44.01",
        aster_version=VERSION,
        section_path=(
            "Chargements_de_type_Neumann_",
            "Chargements de type Neumann",
            "Mot-clé FORCE_ARETE",
        ),
        source_path="source/manuals/man_u/u4/u4.44.01/Chargements_de_type_Neumann_.rst",
        source_commit=DOC_COMMIT,
        fragment_id=(
            "U4.44.01#Chargements_de_type_Neumann_::chargements_de_type_neumann/"
            "mot_cle_force_arete"
        ),
        profile="syntaxe",
        excerpt=(
            "Ce chargement s’applique aux modélisations suivantes: DKT, DST, Q4G, "
            "3D et COQUE_3D."
        ),
    )


def entries() -> list[tuple[str, str, CodeAsterHypothesisEntry, list[str], list[str]]]:
    thermal = record_execution_finding(
        topic=(
            "Température uniforme sur une dalle DKT et une poutre POU_D_T qui "
            "partagent leurs nœuds (dilatation thermique)"
        ),
        sources=(
            _u2_thermal(),
            CatalogueSource(
                command="CREA_RESU", aster_version=VERSION, keyword_path=("PREP_VARC",)
            ),
            CatalogueSource(
                command="AFFE_MATERIAU",
                aster_version=VERSION,
                keyword_path=("AFFE_VARC",),
            ),
            _execution(
                "T1 : DX du nœud Q (x = 1,0 m), dilatation libre",
                2.75e-4,
                "alpha dT L = 1e-5 x 27,5 x 1,0",
                2.75e-4,
            ),
        ),
        option_retained=(
            "Deux occurrences d'AFFE_MATERIAU/AFFE_VARC (NOM_VARC='TEMP', VALE_REF) : "
            "sur les coques DKT, EVOL d'un EVOL_THER préparé par CREA_RESU/PREP_VARC "
            "(MODELE, CARA_ELEM, GROUP_MA) à partir d'un champ NOEU_TEMP_R de "
            "composantes TEMP_MIL, TEMP_INF, TEMP_SUP (syntaxe du cas test hsls01a) ; "
            "sur les poutres POU_D_T, CHAM_GD d'un champ NOEU_TEMP_R de composante "
            "TEMP (syntaxe du cas test ssll12a). Une plaque DKT et une poutre qui "
            "partagent leurs nœuds, isostatiques, se dilatent librement : DX = α ΔT L "
            "exact (2,750000000000e-4 m), efforts NXX, NYY et N du chevêtre au bruit "
            "numérique (≤ 4e-9)."
        ),
        justification=(
            "Sonde S1 du lot 47 (docs/essais_lot47.md, section 1, critère écrit avant "
            "l'exécution) : DX du nœud x = 1,0 et DY(0,6) − DY(0) exacts à 1e-12, "
            "réaction résultante 1,7e-9 N ; U2.02.01 § Chaînage thermomécanique pour "
            "PREP_VARC des coques."
        ),
        repo_root=ROOT,
        point_label="K3",
        notes=(
            "Un champ TEMP seul n'a pas été essayé sur DKT, ni PREP_VARC sur les "
            "poutres : la sonde n'établit que la combinaison écrite."
        ),
    )
    macro = record_execution_finding(
        topic=(
            "MACRO_ELAS_MULT : plusieurs cas de charge d'un modèle linéaire en une "
            "factorisation, avec PESANTEUR et des ressorts DIS_T"
        ),
        sources=(
            CatalogueSource(
                command="MACRO_ELAS_MULT",
                aster_version=VERSION,
                keyword_path=("CAS_CHARGE",),
            ),
            _execution(
                "T2 : PP, résultante DZ des réactions d'appui (MACRO_ELAS_MULT)",
                24596.605,
                "poids de la plaque, du chevêtre et du pieu",
                24596.605,
            ),
        ),
        option_retained=(
            "MACRO_ELAS_MULT(CHAR_MECA_GLOBAL=<conditions aux limites>, CAS_CHARGE=(_F("
            "NOM_CAS=..., CHAR_MECA=<charge>), ...)) calcule chaque cas avec une seule "
            "matrice ; PESANTEUR y est admise sur un modèle qui porte des ressorts DIS_T "
            "dotés d'une masse M_T_D_N nulle (DIAG-004). Le résultat (mult_elas) se lit "
            "par CALC_CHAMP, POST_RELEVE_T (une ligne par NOM_CAS, NUME_ORDRE = rang dans "
            "CAS_CHARGE) et IMPR_RESU au format MED, où les cas sont des pas (k, k) dans "
            "l'ordre de CAS_CHARGE."
        ),
        justification=(
            "Sonde S1 du lot 47 : les quatre résultantes (PP, G2, FR, GC) égales aux "
            "charges déclarées à 1e-12 ; inventaire du MED par medcoupling (pas 1 à 4 "
            "pour MULT____DEPL et MULT____EFGE_NOEU)."
        ),
        repo_root=ROOT,
        point_label="K4",
        notes=(
            "Le validateur de niveau B de l'outil ne résout pas un tuple de concepts "
            "(CHAR_MECA_GLOBAL=(CL,)) : écrire une référence simple pour que la "
            "commande et la suite soient confrontées au catalogue (lot 47)."
        ),
    )
    arete = record_execution_finding(
        topic="Charge linéique sur le bord d'une dalle DKT (FORCE_ARETE)",
        sources=(
            _u4_force_arete(),
            _execution(
                "T2 : GC (FORCE_ARETE FZ = -500 N/m sur 1,0 m), résultante DZ",
                500.0,
                "q x L = 500 x 1,0",
                500.0,
            ),
        ),
        option_retained=(
            "AFFE_CHAR_MECA/FORCE_ARETE (FX, FY, FZ en repère global, force par unité "
            "de longueur) sur un groupe de mailles SEG2 du bord de la dalle, ces SEG2 "
            "étant affectées en DKT dans AFFE_MODELE avec les QUAD4 : la résultante est "
            "exactement q × L."
        ),
        justification=(
            "U4.44.01 § Mot-clé FORCE_ARETE (modélisations DKT, DST, Q4G, 3D, COQUE_3D) ; "
            "sonde S1 du lot 47, résultante 500,000 N pour 500 N attendus."
        ),
        repo_root=ROOT,
        point_label="K5",
    )
    cercle = record_execution_finding(
        topic=(
            "Section de tube corrodé donnée par A et I : tube uniforme équivalent "
            "(AFFE_CARA_ELEM/POUTRE, SECTION='CERCLE')"
        ),
        sources=(
            CatalogueSource(
                command="AFFE_CARA_ELEM",
                aster_version=VERSION,
                keyword_path=("POUTRE",),
            ),
            _execution(
                "T2 : PP, effort normal N en tête du pieu suspendu (poids du pieu)",
                2396.605,
                "γ A L avec A de B2 = 305,30 cm², L = 1,0 m, γ = 78,5 kN/m³",
                2396.605,
            ),
        ),
        option_retained=(
            "Une section tubulaire donnée par son aire A et son inertie I s'écrit "
            "SECTION='CERCLE', CARA=('R', 'EP') avec le tube uniforme qui a exactement "
            "ces A et I : R² + r² = 4 I / A, R² − r² = A / π, EP = R − r. Le poids du "
            "pieu suspendu (N en tête) vaut γ A L à 1e-12 : l'aire de la section CERCLE "
            "est celle du tube, sans correction."
        ),
        justification=(
            "Sonde S1 du lot 47 (pieu de 1,0 m sous PESANTEUR) ; déduction "
            "géométrique pour R et EP, vérifiée sur les cinq tronçons de B2 par I/R = "
            "I/v publié (4 752,9 ; 5 394,8 ; 4 886,7 ; 5 593,3 cm³)."
        ),
        repo_root=ROOT,
        point_label="K6",
        notes=(
            "L'inertie n'est pas mesurée par la sonde : elle découle de la même "
            "formule géométrique du tube (déduction), non d'une exécution."
        ),
    )
    return [
        (
            "CA-054",
            "Une température uniforme portée par des coques DKT et des poutres qui "
            "partagent leurs nœuds s'écrit par deux AFFE_VARC : EVOL préparé par "
            "CREA_RESU/PREP_VARC (TEMP_MIL/INF/SUP) sur les coques, CHAM_GD de "
            "composante TEMP sur les poutres.",
            thermal,
            ["AFFE_MATERIAU", "CREA_CHAMP", "CREA_RESU", "MECA_STATIQUE"],
            [
                "AFFE_VARC",
                "PREP_VARC",
                "TEMP",
                "TEMP_MIL",
                "TEMP_INF",
                "TEMP_SUP",
                "VALE_REF",
                "DKT",
                "POU_D_T",
                "EVOL_THER",
                "NOEU_TEMP_R",
            ],
        ),
        (
            "CA-055",
            "MACRO_ELAS_MULT résout plusieurs cas d'un modèle linéaire en une "
            "factorisation, PESANTEUR comprise avec des ressorts DIS_T de masse nulle ; "
            "le MED range les cas en pas (k, k) dans l'ordre de CAS_CHARGE.",
            macro,
            ["MACRO_ELAS_MULT", "CALC_CHAMP", "POST_RELEVE_T", "IMPR_RESU"],
            [
                "CAS_CHARGE",
                "CHAR_MECA_GLOBAL",
                "NOM_CAS",
                "PESANTEUR",
                "DIS_T",
                "M_T_D_N",
                "MED",
            ],
        ),
        (
            "CA-056",
            "Une charge linéique sur le bord d'une dalle DKT s'applique par "
            "FORCE_ARETE sur des SEG2 affectées en DKT ; sa résultante est exacte.",
            arete,
            ["AFFE_CHAR_MECA", "AFFE_MODELE"],
            ["FORCE_ARETE", "DKT", "SEG2", "FZ"],
        ),
        (
            "CA-057",
            "Un tube donné par A et I s'écrit SECTION='CERCLE' avec le tube uniforme "
            "équivalent (R, EP) ; l'aire et donc le poids sont exacts.",
            cercle,
            ["AFFE_CARA_ELEM"],
            ["POUTRE", "SECTION", "CERCLE", "R", "EP", "POU_D_T"],
        ),
    ]


def main() -> None:
    directory = base_dir(ROOT)
    for constat_id, summary, entry, commands, keywords in entries():
        constat = build_constat(
            entry,
            constat_id=constat_id,
            summary=summary,
            origin=FindingOrigin(
                project=ORIGIN_PROJECT, fiche=FICHE, point_label=entry.point_label
            ),
            commands=commands,
            keywords=keywords,
        )
        print(write_constat(constat, directory).relative_to(ROOT))


if __name__ == "__main__":
    main()
