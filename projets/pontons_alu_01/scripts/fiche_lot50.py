"""Fiche de PONTONS-ALU-01 (lot 50), reconstruite de façon reproductible.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/fiche_lot50.py

Fiche vide du lot (`aster-expert projet creer`), décisions P1 à P23 de MM rejouées depuis
`donnees/sources/enregistrement_P1_P23_lot50.md` (même fonction que `aster-expert fiche
enregistrer`), choix de l'agent A1 à A4 (domaines du lot 44), convention de nommage des
groupes tirée des invariants du maillage, commandes prévues conservées (`fiche
prevoir`). Un test rejoue ce script et compare le JSON octet pour octet.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aster_expert.agent.arbitration import insert_practice_entry, record_agent_choice
from aster_expert.agent.enregistrement import (
    check_quotes,
    parse_arbitration,
    record_decisions,
)
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
)
from aster_expert.agent.prevues import carry_planned_commands
from pontons_alu_01.geometrie import geometry
from pontons_alu_01.invariants import invariants

PROJECT = Path(__file__).resolve().parents[1]
FICHE = PROJECT / "fiche" / "hypotheses_pontons_alu_01.json"
RECORDING = PROJECT / "donnees" / "sources" / "enregistrement_P1_P23_lot50.md"
CREATED = datetime.fromisoformat("2026-10-12T08:38:25.125860-04:00")
DESCRIPTION = (
    "Panne (passerelle d'accès sur pieux) en aluminium soudé : une travée de 6,25 m, "
    "poutres principales MP1200, montants, diagonales et pannes secondaires "
    "tubulaires, profilés supports sur chevêtre béton neuf, deux poteaux et "
    "demi-semelle sur sol élastique ; reprise PRO d'un AVP Sofistik"
)
REFERENCE = "session du lot 50 (projets/pontons_alu_01, docs/essais_lot50.md)"


def agent_entries(at: datetime) -> list[PracticeHypothesisEntry]:
    def choice(
        label: str,
        topic: str,
        domain: str,
        verified_by: tuple[str, ...],
        option: str,
        justification: str,
        discarded: list[tuple[str, str]],
    ) -> PracticeHypothesisEntry:
        return record_agent_choice(
            entry=PracticeHypothesisEntry(
                point_label=label, topic=topic, status="non_tranche"
            ),
            domain=domain,  # type: ignore[arg-type]
            verified_by=verified_by,
            option_retained=option,
            justification=justification,
            validity_domain="Modèle de la travée PONTONS-ALU-01 du lot 50.",
            discarded_variants=tuple(
                DiscardedVariant(description=d, reason=r) for d, r in discarded
            ),
            reference=REFERENCE,
            decided_at=at,
        )

    return [
        choice(
            "A1",
            "Noms des groupes du maillage",
            "noms_groupes",
            ("projet:mesh_check",),
            "Groupes de la consigne du lot 50 (POUTRES_PRINC, MONTANTS, DIAGONALES, "
            "PANNES_SEC, SUPPORTS, CHEVETRE, POTEAUX, SEMELLE, APP_QUAI, "
            "PIEDS_SUPPORTS, TETES_POTEAUX), un groupe par élément (PP_YM, PP_YP, "
            "MONT_i, DIAG_i, PANNE_i, SUP_i, POT_i), groupes de charges (ACC_YM, "
            "ACC_YP, AMAR_YM, AMAR_YP) et de liaisons (LR_nn, ROT_Sk, ROT_Ck), 24 "
            "caractères au plus.",
            "Les invariants du maillage contrôlent chaque groupe (cardinal, type, boîte).",
            [("Noms au-delà de 24 caractères", "tronqués en silence par Code_Aster")],
        ),
        choice(
            "A2",
            "Repère et recalage des coordonnées",
            "repere",
            ("projet:mesh_check",),
            "X le long du tablier, X = 0 à l'appui côté quai, Y transversal, Z = cote "
            "NGF, en m ; points de construction recalés sur la grille de 1 mm (arrondi "
            "au plus proche, demi vers le haut) : plan moyen +1,3575 → +1,358 et axe "
            "des pannes +1,4575 → +1,458 (0,5 mm), croisements des pannes avec la "
            "diagonale 5 (pente 1/1,5) à 0,3 mm près.",
            "Consigne du lot 50 (grille de 1 mm) ; mesh check contrôle les nœuds "
            "imposés et la grille.",
            [("Cotes de P21 à 0,1 mm", "hors de la grille de 1 mm demandée")],
        ),
        choice(
            "A3",
            "Taille et type des mailles",
            "maillage",
            ("projet:mesh_check",),
            "SEG2 d'au plus 0,25 m sur chaque tronçon entre deux points de "
            "construction, au moins 4 éléments par barre (profilés supports de "
            "0,15 m : 4 éléments) ; semelle en QUAD4 d'au plus 0,25 m.",
            "Consigne du lot 50 (discrétisation) ; comptages contrôlés par les "
            "invariants calculés avant l'exécution.",
            [("Étude de maillage", "exclue par MM (pas de contrôles à outrance)")],
        ),
        choice(
            "A4",
            "Lecture des efforts des barres",
            "lecture_champs",
            ("projet:controles",),
            "Efforts des barres lus en EFGE_ELNO (extrémités de chaque élément), "
            "repère local déclaré dans projet.yaml (z_l = +Z pour les barres "
            "horizontales, y_l = +X pour les verticales).",
            "Le harnais D contrôle l'équilibre de chaque cas ; la synthèse relit chaque "
            "valeur par `resultats lire`.",
            [("EFGE_NOEU", "moyenne aux nœuds partagés de barres différentes")],
        ),
    ]


def group_naming() -> tuple[MeshGroupNaming, ...]:
    return tuple(
        MeshGroupNaming(
            group_name=g["name"],
            kind="noeud" if g["kind"] == "node" else "maille",
            description=(
                "Groupe du maillage de la travée ("
                f"{g['count']} {g.get('cell_type', 'nœuds')})."
            ),
            status="choix_agent",
            point_label="A1",
            verified_by=("projet:mesh_check",),
        )
        for g in invariants(geometry())["groups"]
    )


def build_sheet() -> HypothesesSheet:
    arbitration = parse_arbitration(RECORDING.read_text(encoding="utf-8"))
    check_quotes(
        arbitration, (PROJECT / arbitration.source).read_text(encoding="utf-8")
    )
    sheet = HypothesesSheet(
        project_name="PONTONS-ALU-01",
        structure_description=DESCRIPTION,
        aster_version="17.4.0",
        created_at=CREATED,
        entries=(),
        group_naming=group_naming(),
    )
    sheet, _done = record_decisions(sheet, arbitration)
    for entry in agent_entries(arbitration.recorded_at):
        sheet = insert_practice_entry(sheet, entry)
    return sheet


def main() -> None:
    sheet = carry_planned_commands(build_sheet(), FICHE)
    FICHE.write_text(
        json.dumps(json.loads(sheet.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        FICHE.name, len(sheet.entries), "entrées,", len(sheet.group_naming), "groupes"
    )


if __name__ == "__main__":
    main()
