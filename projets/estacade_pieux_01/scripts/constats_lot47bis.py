"""Lot 47 bis -- finding of the probe S2 written in the shared base (CA-058).

A DKT slab and a coplanar POU_D_T beam that share their nodes: near a point
support, the slab carries most of the shear of the T-section; the bar alone is not
the shear of the section, the total bar + slab band is. Execution source: the probe
S2 (`references/cas/sonde_lot47bis.comm`, criterion of docs/essais_lot47bis.md § 6
written before the run, commit c2fc6f9); every value cited is printed in the
versioned listing extract `references/cas/sonde_lot47bis_listing_extrait.txt`. The
fiche of the jetty references it (point K7). Idempotent: rerun
`.venv/bin/python projets/estacade_pieux_01/scripts/constats_lot47bis.py`.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.drafting import record_execution_finding
from aster_expert.agent.hypotheses import CatalogueSource, ExecutionSource
from aster_expert.constats.base import base_dir, build_constat, write_constat
from aster_expert.constats.models import FindingOrigin

VERSION = "17.4.0"
DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"
COMMIT = "c2fc6f9ed3533fb678a59efc64ba1d86c23a908c"
CASE = "projets/estacade_pieux_01/references/cas/sonde_lot47bis.comm"
LISTING = "projets/estacade_pieux_01/references/cas/sonde_lot47bis_listing_extrait.txt"
FICHE = "projets/estacade_pieux_01/fiche/hypotheses_estacade_pieux_01.json"
ORIGIN_PROJECT = "ESTACADE-PIEUX-01"


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _execution(
    quantity: str, obtained: float, reference: str, expected: float
) -> ExecutionSource:
    return ExecutionSource(
        aster_version=VERSION,
        image_digest=DIGEST,
        repo_commit=COMMIT,
        working_tree_modified=True,
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


def main() -> None:
    entry = record_execution_finding(
        topic=(
            "Dalle DKT et poutre POU_D_T coplanaires à nœuds partagés : partage de "
            "l'effort tranchant près d'un appui ponctuel, grandeur à comparer"
        ),
        sources=(
            CatalogueSource(
                command="AFFE_MODELE",
                aster_version=VERSION,
                keyword_path=("AFFE", "MODELISATION"),
            ),
            _execution(
                "S2 : Σ DZ des réactions des deux appuis ponctuels",
                71999.99999946,
                "W = q b L = 10 kPa × 1,20 × 6,00 m",
                72000.0,
            ),
            _execution(
                "S2 : |VZ| de la poutre seule à Y = −1,90 (extrémité côté travée)",
                6484.706369945,
                "effort tranchant total de la section en T (statique) à Y = −1,90",
                22800.0,
            ),
            _execution(
                "S2 : |MFY| de la poutre seule sur appui (Y = −2,00, côté console)",
                4826.356527417,
                "moment total de la section en T sur appui (statique)",
                6000.0,
            ),
            _execution(
                "S2 : MFY de la poutre seule en travée (Y = 0)",
                16594.8764602,
                "moment total de la section en T en travée (statique)",
                18000.0,
            ),
        ),
        option_retained=(
            "Une dalle DKT et une poutre POU_D_T coplanaires qui partagent leurs nœuds "
            "forment une section en T dont l'effort se partage entre la barre "
            "(EFGE_ELNO : VZ, MFY) et la dalle (EFGE_NOEU : QY, MYY). Près d'un appui "
            "ponctuel porté par un nœud de la poutre, la dalle DKT (sans déformation "
            "d'effort tranchant) porte la plus grande part de l'effort tranchant : sur "
            "la sonde S2 (bande de 1,20 m, QUAD4 de 0,05 m, poutre 1,20 × 0,90 m), la "
            "barre seule porte 28 % de l'effort tranchant à 0,10 m de l'appui, 79 % du "
            "moment sur appui et 92 % du moment en travée. La grandeur d'une section "
            "en T est le total : VZ + ∫QY dX et s·MFY − ∫MYY dX sur la bande de dalle "
            "(trapèzes sur les nœuds de la ligne), qui redonne la statique à 0,1 % pour "
            "l'effort tranchant et à 3e-11 pour le moment. Comparer la barre seule à un "
            "calcul de section en T est une erreur de lecture."
        ),
        justification=(
            "Sonde S2 du lot 47 bis (docs/essais_lot47bis.md § 6, critère écrit avant "
            "l'exécution, réussi) : section en T isostatique, réactions exactes à "
            "7,5e-12, totaux comparés à la statique ; la part de la barre est la "
            "grandeur mesurée. Confirmé sur l'estacade du lot 47 (production, § 7 du "
            "rapport du lot 47 bis)."
        ),
        repo_root=ROOT,
        point_label="K7",
        notes=(
            "Les parts dépendent de la rigidité relative et du maillage : au lot 47, "
            "l'effort tranchant de la barre près du pieu décroît au raffinement de la "
            "dalle (88,9 → 60,4 → 36,9 kN pour h = 0,10 → 0,025 m) quand le moment "
            "reste stable ; le total n'en dépend pas. Le terme de bord [MXY] aux "
            "extrémités de la bande n'entre pas dans le total (rapporté à part). Les "
            "valeurs nodales de la dalle sont lues par POST_RELEVE_T, qui émet "
            "<A> <POSTRELE_70> (DIAG-012) : le repère local de la dalle (ANGL_REP = "
            "(0, 0), normale +Z) est ici le repère global."
        ),
    )
    constat = build_constat(
        entry,
        constat_id="CA-058",
        summary=(
            "Dalle DKT et poutre POU_D_T coplanaires à nœuds partagés : près d'un appui "
            "ponctuel la dalle porte l'essentiel de l'effort tranchant ; l'effort de la "
            "section en T est le total barre + bande de dalle, jamais la barre seule."
        ),
        origin=FindingOrigin(project=ORIGIN_PROJECT, fiche=FICHE, point_label="K7"),
        commands=["AFFE_MODELE", "CALC_CHAMP", "AFFE_CARA_ELEM"],
        keywords=["DKT", "POU_D_T", "EFGE_NOEU", "EFGE_ELNO", "QY", "VZ", "MFY", "MYY"],
    )
    print(write_constat(constat, base_dir(ROOT)).relative_to(ROOT))


if __name__ == "__main__":
    main()
