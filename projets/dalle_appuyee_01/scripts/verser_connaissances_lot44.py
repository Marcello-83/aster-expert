"""Lot 44 : constat CA-053 (paramètres de CALC_FERRAILLAGE `optional` au catalogue,
obligatoires à l'exécution).

Au lot 43, la fiche de la dalle n'a pas demandé σc, αe, KT et Es ; il a fallu une
seconde intervention de MM (journal d'autonomie, n° 21). Au lot 44, en écrivant la
détection des paramètres obligatoires (`aster_expert.agent.obligatoires`), la session
a constaté que le catalogue 17.4 déclare ces mots-clés `optional` sans valeur par
défaut : leur obligation se lit dans U4.81.42 et dans l'implémentation, pas dans le
schéma. Ce fait sur Code_Aster va dans la base partagée (règle du lot 41) ; la table
`data/config/obligations_execution.yaml` en est la forme exploitable par l'outil.

Sources lues au lot 44 par `get_document_section` (U4.81.42 § Erreurs et alarmes,
§ Opérandes ALPHA_E et EYS) et `get_command_schema` (CALC_FERRAILLAGE, AFFE). Les
sources d'implémentation (`bibfor/calculel/w175af.F90`, messages `CALCULEL_74`,
`CALCULEL_82`, `CALCULEL7_8`, commit `codeaster-src` 50ebc13c) n'ont pas de type de
source dans le schéma : elles sont citées dans les notes.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/verser_connaissances_lot44.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.drafting import record_code_aster_finding
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DocumentarySource,
)
from aster_expert.catalogue.query import catalogue_identifiers, resolve_active_digest
from aster_expert.constats.base import base_dir, build_constat, write_constat
from aster_expert.constats.models import FindingOrigin

VERSION = "17.4.0"
DOC_COMMIT = "9c8c179f57ef7ca1d2891cac275ee4823a57967c"
CATALOGUE_HASH = "b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca"
IMAGE_DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
FICHE = "projets/dalle_appuyee_01/fiche/hypotheses_dalle_arbitree.json"
CONSTAT_ID = "CA-053"
SUMMARY = (
    "Piège : en 17.4, le catalogue déclare optionnels, sans valeur par défaut, "
    "ALPHA_E, SIGC_*_ELS, SIGC_ELS_QP, KT et EYS de CALC_FERRAILLAGE, que la commande "
    "exige à l'exécution selon TYPE_COMB et TYPE_STRUCTURE : le schéma seul ne les "
    "fait pas demander."
)


def _cat(*path: str) -> CatalogueSource:
    return CatalogueSource(
        command="CALC_FERRAILLAGE",
        aster_version=VERSION,
        keyword_path=path,
        catalogue_hash=CATALOGUE_HASH,
        image_digest=IMAGE_DIGEST,
    )


ERREURS = DocumentarySource(
    document_id="U4.81.42",
    aster_version=VERSION,
    section_path=("Erreurs_et_alarmes",),
    source_path="source/manuals/man_u/u4/u4.81.42/Erreurs_et_alarmes.rst",
    source_commit=DOC_COMMIT,
    profile="syntaxe",
    excerpt=(
        "dans le cas EC2 à l’ELS_QP: si les mots-clé ALPHA_E, FYK, FCK, SIGC_ELS_QP, "
        "WMAX_INF/SUP(_Y/Z), KT, PHI_X/Y/Z_INF/SUP ne sont pas renseignés;"
    ),
)
ALPHA_E = DocumentarySource(
    document_id="U4.81.42",
    aster_version=VERSION,
    section_path=("Op_randes",),
    source_path="source/manuals/man_u/u4/u4.81.42/Op_randes.rst",
    source_commit=DOC_COMMIT,
    profile="syntaxe",
    excerpt=(
        "Il est obligatoire de renseigner sa valeur pour le calcul aux États Limites de "
        "Service Caractéristique (ELS) et Quasi Permanent(ELS_QP)."
    ),
)


def entry() -> CodeAsterHypothesisEntry:
    return record_code_aster_finding(
        topic=(
            "CALC_FERRAILLAGE : mots-clés optionnels au catalogue, obligatoires à "
            "l'exécution selon TYPE_COMB et TYPE_STRUCTURE"
        ),
        option_retained=(
            "Catalogue 17.4 : AFFE.ALPHA_E, AFFE.SIGC_INF_ELS, AFFE.SIGC_SUP_ELS, "
            "AFFE.SIGC_ELS_QP, AFFE.KT, AFFE.EYS (et FYK, FCK, GAMMA_C, GAMMA_S, "
            "SIGS_ELS, WMAX_*, PHI_*) ont le statut `optional` sans valeur par défaut. "
            "U4.81.42 § Erreurs et alarmes et l'implémentation arrêtent pourtant le "
            "calcul (<F>) s'ils manquent : EC2 à l'ELU : GAMMA_S, GAMMA_C, FYK, FCK, EYS "
            "(message CALCULEL_74) ; à l'ELS : ALPHA_E, SIGS_ELS, FCK et, en 2D, "
            "SIGC_INF_ELS/SIGC_SUP_ELS (CALCULEL_82) ; à l'ELS_QP : ALPHA_E, FYK, FCK, "
            "EYS, SIGC_ELS_QP, KT et, en 2D, WMAX_INF/SUP, PHI_INF/SUP_X/Y (CALCULEL7_8)."
        ),
        justification=(
            "U4.81.42 § Erreurs et alarmes et § Opérande ALPHA_E (lus en entier au lot "
            "44) ; schéma du catalogue 17.4 (get_command_schema CALC_FERRAILLAGE, AFFE, "
            "variante CODIFICATION='EC2') ; table exploitable : "
            "data/config/obligations_execution.yaml (aster_expert.agent.obligatoires)."
        ),
        notes=(
            "Sources d'implémentation (codeaster-src 50ebc13c70ee) : "
            "bibfor/calculel/w175af.F90 contrôle n32 n33 n34 n35 n36 n37 à l'ELU, n17 "
            "n24 n37 à l'ELS (et n26 seul en 2D : SIGC_SUP_ELS, alors que U4.81.42 et "
            "CALCULEL_82 citent aussi SIGC_INF_ELS), n17 n34 n35 n37 n54 n55 à l'ELS_QP ; "
            "messages code_aster/Messages/calculel.py (74, 82) et calculel7.py (8). "
            "EYS n'est pas cité par U4.81.42 § Erreurs et alarmes mais l'est par les "
            "messages CALCULEL_74 et CALCULEL7_8 ; son opérande U4.81.42 dit seulement "
            "« La valeur couramment utilisée est 210000 MPa ». Conséquence au lot 43 : "
            "seconde intervention de MM (journal d'autonomie, n° 21). Non vérifié par "
            "exécution au lot 44."
        ),
        sources=(
            ERREURS,
            ALPHA_E,
            _cat("AFFE", "ALPHA_E"),
            _cat("AFFE", "SIGC_ELS_QP"),
            _cat("AFFE", "KT"),
            _cat("AFFE", "EYS"),
        ),
    )


def main() -> int:
    digest = resolve_active_digest(ROOT / "config" / "versions.yaml")
    commands, keywords = catalogue_identifiers(
        ROOT / "data" / "processed" / "catalogue", digest
    )
    constat = build_constat(
        entry(),
        constat_id=CONSTAT_ID,
        summary=SUMMARY,
        origin=FindingOrigin(project="DALLE-APPUYEE-01", fiche=FICHE, point_label="14"),
        commands=commands,
        keywords=keywords,
    )
    path = write_constat(constat, base_dir(ROOT))
    print(
        f"constat écrit : {path.relative_to(ROOT)} (niveau {constat.validation_level})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
