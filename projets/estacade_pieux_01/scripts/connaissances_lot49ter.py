"""Lot 49 ter -- knowledge drawn from the deliverables of the jetty.

1. PAT-014 « barre partageant ses nœuds avec une plaque » : the forces of the bar
   alone are not a design quantity; one designs on the T section (CA-058, E25); proof:
   the comparison of D1 (equilibrium of a cut, docs/essais_lot49ter.md).
2. PAT-015 « lecture au nu » : exclusion bands ±b/2 along the beam–plate lines and a
   disc around the point supports (PAT-013, E26).
3. CTL-015 : controls of the delivery chain (D3 disjoint zones and sign, D4 convention,
   D5 number formats), generic tests of the trunk.

Idempotent: rerun `.venv/bin/python projets/estacade_pieux_01/scripts/connaissances_lot49ter.py`.
Status `observé`: no promotion (one project only).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.connaissances.base import write_entry
from aster_expert.connaissances.modeles import (
    CaughtError,
    CodeEvidence,
    ConstatEvidence,
    Control,
    DocumentEvidence,
    ExecutionEvidence,
    Pattern,
    TestEvidence,
)

PROJECT = "estacade_pieux_01"
TODAY = dt.date(2026, 10, 9)
CASE = f"projets/{PROJECT}/references/cas/estacade_pieux_01.comm"
CASE_SHA = "fe73819a8501c5196d62ffe88ff6d7adf0e0b18dab24e5b3ec5ab7ea57d6e692"
PRODUCTION = "20261005T101455-e0d5c870"
TESTS = "tests/unit/test_livrables_lot49ter.py"
REPORT = "docs/essais_lot49ter.md"


def pat014() -> Pattern:
    return Pattern(
        id="PAT-014",
        title="Poutre partageant ses nœuds avec une plaque : dimensionner sur la "
        "section en T, jamais sur la barre seule",
        summary="Quand une poutre et une plaque partagent leurs nœuds, la barre seule "
        "porte une part de l'effort qui dépend de la formulation de plaque (DKT, DST) et "
        "du maillage : la grandeur de dimensionnement est le total de la section en T, "
        "barre plus bande de plaque, contrôlé par l'équilibre d'une coupe.",
        origin_project=PROJECT,
        date=TODAY,
        validation_level="D",
        status="observé",
        sources=(
            ExecutionEvidence(
                run=PRODUCTION,
                case_path=CASE,
                case_sha256=CASE_SHA,
                outcome="réussite",
                level="C",
                note="livrables de la production du lot 47 relus au lot 49 ter",
            ),
            DocumentEvidence(
                path=REPORT,
                section="D1 : section en T et équilibre d'une coupe",
                note="sous PP, coupes Y = 0 et Y = −2,50 : moment total de la coupe "
                "égal à l'équilibre du corps libre à moins de 10⁻⁹ ; à l'ELU, effort "
                "tranchant et moment sur appui de la barre seule 3 à 4 fois sous ceux "
                "de la source, section en T du même ordre",
            ),
            TestEvidence(
                path=TESTS,
                function="test_the_tee_section_adds_the_trapezoid_integral_of_the_band",
                note="intégrale par trapèzes de la bande, barre seule gardée",
            ),
            ConstatEvidence(constat_id="CA-058"),
        ),
        commands=("CALC_CHAMP",),
        keywords=(
            "DKT",
            "DST",
            "POU_D_T",
            "EFGE_ELNO",
            "EFGE_NOEU",
            "MFY",
            "MYY",
            "QY",
        ),
        problem="Une poutre au plan moyen d'une plaque, nœuds partagés (chevêtre sous "
        "une dalle) : la plaque et la barre se partagent l'effort à chaque nœud. La "
        "part de la barre change avec la formulation de plaque (effort tranchant près "
        "d'un appui : 27 % en DKT, 90 % en DST, CA-058) et avec le maillage ; un "
        "ferraillage fait sur la barre seule peut être faux d'un facteur 3 à 4.",
        solution="Déclarer la section en T (largeur ±b/2 de part et d'autre de la "
        "ligne, b la largeur de la poutre) : N_T = N + ∫NYY, M_T = MFY + ∫MYY, "
        "V_T = VZ + ∫QY par trapèzes sur les nœuds de plaque de même abscisse, cas par "
        "cas ; dimensionner sur ce total à tous les états limites ; garder la barre "
        "seule en colonne de traçabilité ; prouver la lecture par l'équilibre d'une "
        "coupe (moyenne des deux extrémités d'élément au nœud de la coupe, moments "
        "nodaux consistants des charges réparties non comptés).",
        fragment="tee_section:\n  plate_family: tablier\n  half_width: 0.60\n"
        "  across: X\n  along: Y\n  parts:\n    - {beam: N, plate: NYY}\n"
        "    - {beam: MFY, plate: MYY}\n    - {beam: VZ, plate: QY}\n",
        fragment_language="python",
        conditions="Poutre et plaque au même plan moyen (E20), repère de plaque égal au "
        "repère global (ANGL_REP = (0, 0)), lecture EFGE_NOEU de la plaque et EFGE_ELNO "
        "de la barre. Le signe des parts dépend du repère local de la poutre : le "
        "vérifier par une coupe en console (isostatique).",
        controls=("CTL-005", "CTL-015"),
        constats=("CA-058",),
        implementation=(
            CodeEvidence(
                path="src/aster_expert/livrables/sections.py", symbol="compose_tee"
            ),
            CodeEvidence(
                path="src/aster_expert/livrables/coupe.py", symbol="cut_equilibrium"
            ),
        ),
    )


def pat015() -> Pattern:
    return Pattern(
        id="PAT-015",
        title="Lecture au nu : bande ±b/2 le long des lignes poutre–plaque et disque "
        "autour des appuis ponctuels",
        summary="Une plaque reliée à une poutre par ses nœuds se lit au nu de la poutre : "
        "les nœuds à moins de b/2 de la ligne sont hors de la valeur de "
        "dimensionnement (gardés en valeur d'axe pour comparaison), en plus des disques "
        "autour des appuis ponctuels (PAT-013).",
        origin_project=PROJECT,
        date=TODAY,
        validation_level="C",
        status="observé",
        sources=(
            ExecutionEvidence(
                run=PRODUCTION,
                case_path=CASE,
                case_sha256=CASE_SHA,
                outcome="réussite",
                level="C",
                note="QY de 10 409 kN/m sur la ligne du chevêtre et 577 kN/m à 5 cm "
                "(lots 49, 49 bis) : valeurs sans signification physique",
            ),
            DocumentEvidence(
                path=REPORT,
                section="2.6 Bande d'exclusion E26",
                note="règle E26 de MM (lot 49 ter), EN 1992-1-1 §5.3.2.2(3) citée "
                "d'après MM et le superviseur",
            ),
            TestEvidence(
                path=TESTS,
                function="test_the_band_excludes_the_plate_strictly_inside_half_the_"
                "beam_width",
                note="nu lu, intérieur de la bande exclu, motif écrit",
            ),
        ),
        commands=("CALC_CHAMP",),
        keywords=("DKT", "EFGE_NOEU", "MXX", "MYY", "QX", "QY"),
        problem="Le long d'une ligne de nœuds partagés avec une poutre, la plaque porte "
        "un effort d'interaction nodal (CA-058) : ses valeurs sur la ligne et à ses "
        "voisins immédiats n'ont pas de sens physique et dépendent du maillage ; une "
        "lecture « hors disques » ne les écarte pas (une ligne n'est pas un disque).",
        solution="Déclarer sur la famille de poutres une bande de demi-largeur b/2 "
        "(exclusion_band) : tout nœud de plaque à moins de b/2 (strictement) d'un nœud "
        "de la poutre est exclu de la valeur de dimensionnement de toutes les familles "
        "de coque ; le nu (distance b/2) est lu ; les disques PAT-013 restent ; les "
        "valeurs de la bande sont rapportées en « axe (comparaison) ».",
        fragment='exclusion_band:\n  half_width: 0.60\n  source: "E26 de MM"\n',
        fragment_language="python",
        conditions="Poutre de largeur b au plan moyen d'une plaque, nœuds partagés ; "
        "appui monolithique (lecture au nu). La demi-largeur est une décision de "
        "lecture, déclarée avant la lecture.",
        controls=("CTL-015",),
        constats=("CA-058",),
        implementation=(
            CodeEvidence(
                path="src/aster_expert/livrables/sections.py", symbol="singular_rows"
            ),
        ),
    )


def ctl015() -> Control:
    return Control(
        id="CTL-015",
        title="Chaîne de livraison : zones disjointes et signe de section, convention "
        "ingénieur, format d'affichage de chaque cellule",
        summary="Avant de livrer une synthèse ingénieur : aucune ligne ni aucun nœud "
        "dans deux sections d'une même famille, aucune ligne identique entre deux "
        "sections, le signe de moment déclaré par section (D3) ; synthèse en "
        "convention ingénieur, torseurs bruts en convention Code_Aster (D4) ; toute "
        "cellule numérique du classeur au format de son unité (D5).",
        origin_project=PROJECT,
        date=TODAY,
        validation_level="B",
        status="observé",
        sources=(
            TestEvidence(
                path=TESTS,
                function="test_two_sections_of_a_family_must_not_share_a_row",
                note="D3 : recouvrement refusé, partage déclaré admis",
            ),
            TestEvidence(
                path=TESTS,
                function="test_identical_lines_in_two_sections_are_refused",
                note="D3 : lignes identiques refusées",
            ),
            TestEvidence(
                path=TESTS,
                function="test_a_span_section_keeps_the_span_sign_and_names_it",
                note="D3, D4 : signe retenu et intitulés physiques",
            ),
            TestEvidence(
                path="tests/unit/test_synthese_ingenieur.py",
                function="test_the_workbook_puts_the_engineering_sheets_first",
                note="D4, D5 : convention dite en tête de feuille, number_format relu",
            ),
        ),
        commands=(),
        keywords=("EFGE_ELNO", "EFGE_NOEU"),
        detects="Deux sections d'une famille qui lisent les mêmes lignes (dalle en "
        "travée contenant des moments de chapeau ; chevêtre en travée et au nu avec "
        "trois lignes identiques) ; une feuille « Synthèse » en convention Code_Aster "
        "qui contredit les CSV ; des cellules au format « Standard » "
        "(−166.3100644693008).",
        parameters="Sections déclarées (zone, moment_signs, shared_rows) ; table "
        "config/arrondis.yaml ; format des valeurs sans unité (0.00E+00).",
        implementation=CodeEvidence(
            path="src/aster_expert/livrables/ingenieur.py", symbol="disjoint_zones"
        ),
        scope="tronc commun",
        caught_error=CaughtError(
            mode="a posteriori",
            description="Relecture du superviseur des livrables du lot 49 bis "
            "(défauts D3, D4, D5 de la consigne du lot 49 ter).",
            evidence=DocumentEvidence(
                path="docs/lots/lot49ter_consigne.md",
                section="Étape 1 — Les six défauts",
                note=None,
            ),
        ),
    )


def main() -> None:
    for entry in (pat014(), pat015(), ctl015()):
        print(write_entry(ROOT, entry).relative_to(ROOT))


if __name__ == "__main__":
    main()
