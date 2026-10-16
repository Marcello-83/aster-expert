"""Fiche de PONTONS-ALU-01 (lots 50 à 51 bis), reconstruite de façon reproductible.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/fiche_lot50.py

Fiche vide du lot (`aster-expert projet creer`), décisions P1 à P23 (lot 50) puis P24 à P28
(lot 50 bis), P29 à P43 (lot 51), P44 à P51 (lot 51 bis), P53 à P59 (lot 51 ter), P60 et P61 (lot
51 quater, P56 ré-arbitrée) de MM rejouées depuis
`donnees/sources/enregistrement_*.md` (même fonction que `aster-expert fiche enregistrer`),
choix de l'agent A1 à A9 (domaines du lot 44), convention de nommage des
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
from pontons_alu_01.geometrie_lot51 import geometry as geometry_lot51
from pontons_alu_01.geometrie_lot51bis import geometry as geometry_lot51bis
from pontons_alu_01.geometrie_lot51ter import geometry as geometry_lot51ter
from pontons_alu_01.invariants import invariants
from pontons_alu_01.invariants_lot51 import invariants as invariants_lot51
from pontons_alu_01.invariants_lot51bis import invariants as invariants_lot51bis
from pontons_alu_01.invariants_lot51ter import invariants as invariants_lot51ter
from pontons_alu_01.variantes_lot51ter import variants as variants_lot51ter

PROJECT = Path(__file__).resolve().parents[1]
FICHE = PROJECT / "fiche" / "hypotheses_pontons_alu_01.json"
RECORDINGS = (
    PROJECT / "donnees" / "sources" / "enregistrement_P1_P23_lot50.md",
    PROJECT / "donnees" / "sources" / "enregistrement_P24_P28_lot50bis.md",
    PROJECT / "donnees" / "sources" / "enregistrement_P29_P43_lot51.md",
    PROJECT / "donnees" / "sources" / "enregistrement_P44_P51_lot51bis.md",
    PROJECT / "donnees" / "sources" / "enregistrement_P53_P59_lot51ter.md",
    PROJECT / "donnees" / "sources" / "enregistrement_P60_P61_lot51quater.md",
)
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
            "PIEDS_SUPPORTS, TETES_POTEAUX), rotules côté quai séparées au lot 50 bis "
            "(APP_QUAI_YM, APP_QUAI_YP, P25), un groupe par élément (PP_YM, PP_YP, "
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


def lot51_entries(at: datetime) -> list[PracticeHypothesisEntry]:
    """Choices of the agent for the pier of lot 51 (domains of lot 44)."""

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
            validity_domain="Modèle de la palée et des trois travées (lot 51).",
            discarded_variants=tuple(
                DiscardedVariant(description=d, reason=r) for d, r in discarded
            ),
            reference="session du lot 51 (projets/pontons_alu_01, docs/essais_lot51.md)",
            decided_at=at,
        )

    return [
        choice(
            "A5",
            "Noms des groupes du maillage de la palée",
            "noms_groupes",
            ("projet:mesh_check",),
            "Barres PP_<travée>_<rive>, MONT_, DIAG_, PANNE_<travée>_<i> (travées T1, PT, "
            "T2), SUP_ et NEO_<appui>_<rive> (appuis A1, A2, A3), CHEV_C1, CHEV_C2, "
            "LONG_YM, LONG_YP, PILE_<chevêtre>_<rive> ; familles CHEVETRES, LONGRINES, "
            "PILES, NEOPRENES ; zones d'accostage ACC_<zone>_<rive>, taquets TQk_<rive> ; "
            "liaisons <nom>_A et <nom>_B (LR_, BR_, SC_, EC_, TP_, LG_, PS_) ; APP_FIXE, "
            "NB_<appui>_<rive>, TETES_PILES, PIEDS_PILES ; 24 caractères au plus.",
            "Les invariants calculés à part contrôlent chaque groupe (cardinal, type, "
            "boîte).",
            [("Noms au-delà de 24 caractères", "tronqués en silence par Code_Aster")],
        ),
        choice(
            "A6",
            "Nœuds distincts aux liaisons et ressorts néoprène de 1 mm",
            "maillage",
            ("projet:mesh_check", "projet:controles"),
            "Petite travée et longrines arrêtées à 1 mm du nœud auquel elles sont liées "
            "(éclissages, angles de l'anneau) ; ressort néoprène en SEG2 de 1 mm (DIS_T) "
            "relié au nœud de la poutre par un bras rigide ; SEG2 d'au plus 0,25 m, au "
            "moins 4 éléments par barre.",
            "Invariant « nœuds confondus » du vérificateur ; U2.02.03 : un discret ne "
            "transmet pas le moment d'un couple, sa longueur doit rester négligeable ; "
            "harnais D sur les 68 cas.",
            [
                ("Nœuds confondus non fusionnés", "refusés par mesh check"),
                (
                    "Ressort entre le profilé et l'axe de la poutre (0,118 m)",
                    "couple non transmis par le discret (U2.02.03)",
                ),
            ],
        ),
        choice(
            "A7",
            "Lecture des efforts des appuis néoprène",
            "lecture_champs",
            ("projet:controles",),
            "Effort de l'appui sur le tablier F = −K·(u_haut − u_bas), repère global, Fz > "
            "0 en compression ; variante M (sans raideur) : effort intérieur en tête du "
            "profilé support ramené au repère global.",
            "Critère 4 de docs/essais_lot51.md : les deux lectures concordent sur R.",
            [
                (
                    "SIEF_ELGA du discret",
                    "convention du repère de l'élément SEG2 à établir",
                )
            ],
        ),
    ]


def lot51bis_entries(at: datetime) -> list[PracticeHypothesisEntry]:
    """Choices of the agent for the pier type of lot 51 bis (domains of lot 44)."""

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
            validity_domain="Modèle de la palée type et des trois travées (lot 51 bis).",
            discarded_variants=tuple(
                DiscardedVariant(description=d, reason=r) for d, r in discarded
            ),
            reference="session du lot 51 bis (projets/pontons_alu_01, docs/essais_lot51bis.md)",
            decided_at=at,
        )

    return [
        choice(
            "A8",
            "Noms des groupes des appuis à axe",
            "noms_groupes",
            ("projet:mesh_check",),
            "Groupes d'un nœud AX_<appui>_<rive>_1 (oreille de la grande travée), _2 "
            "(oreille de la petite travée) et _K (nœud du chevêtre sous l'appui), appuis "
            "A1, A2, A3, rives YM, YP ; APP_A3 (oreilles en X = 14,02) ; les autres noms "
            "sont ceux du lot 51 (A5) ; 24 caractères au plus.",
            "Les invariants calculés à part contrôlent chaque groupe (cardinal, boîte).",
            [("Noms au-delà de 24 caractères", "tronqués en silence par Code_Aster")],
        ),
        choice(
            "A9",
            "Lecture des efforts transmis par les axes",
            "lecture_champs",
            ("projet:controles",),
            "Effort de l'axe sur le chevêtre = REAC_NODA du nœud AX_<appui>_<rive>_K "
            "(seules les relations de l'axe y agissent), repère global ; en X = 14,02, "
            "opposé de REAC_NODA de l'oreille ; rotation relative autour de Y = DRY de "
            "l'oreille − DRY du nœud du chevêtre.",
            "Critère 4 de docs/essais_lot51bis.md : la somme des REAC_NODA des oreilles et "
            "du nœud du chevêtre est nulle, appui par appui et cas par cas.",
            [
                (
                    "Multiplicateurs de Lagrange des relations",
                    "non imprimés par CREA_TABLE ; REAC_NODA les porte aux nœuds",
                )
            ],
        ),
    ]


def group_naming() -> tuple[MeshGroupNaming, ...]:
    lot50 = [
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
    ]
    known = {n.group_name for n in lot50}
    lot51 = [
        MeshGroupNaming(
            group_name=g["name"],
            kind="noeud" if g["kind"] == "node" else "maille",
            description=(
                "Groupe du maillage de la palée, lot 51 ("
                f"{g['count']} {g.get('cell_type', 'nœuds')}, H = 1,32 m)."
            ),
            status="choix_agent",
            point_label="A5",
            verified_by=("projet:mesh_check",),
        )
        for g in invariants_lot51(geometry_lot51({"H_PILES": 1.32}))["groups"]
        if g["name"] not in known
    ]
    known |= {n.group_name for n in lot51}
    lot51bis = [
        MeshGroupNaming(
            group_name=g["name"],
            kind="noeud" if g["kind"] == "node" else "maille",
            description=(
                "Groupe du maillage de la palée type, lot 51 bis ("
                f"{g['count']} {g.get('cell_type', 'nœuds')}, variante H80C)."
            ),
            status="choix_agent",
            point_label="A8",
            verified_by=("projet:mesh_check",),
        )
        for g in invariants_lot51bis(
            geometry_lot51bis({"H_ANNEAU": 0.8, "H_PILES": 1.3})
        )["groups"]
        if g["name"] not in known
    ]
    known |= {n.group_name for n in lot51bis}
    lot51ter = [
        MeshGroupNaming(
            group_name=g["name"],
            kind="noeud" if g["kind"] == "node" else "maille",
            description=(
                "Groupe du maillage du ponton intégral, lot 51 ter ("
                f"{g['count']} {g.get('cell_type', 'nœuds')}, variante B10)."
            ),
            status="choix_agent",
            point_label="A10",
            verified_by=("projet:mesh_check",),
        )
        for g in invariants_lot51ter(
            geometry_lot51ter(variants_lot51ter()["B10"].mesh_overrides)
        )["groups"]
        if g["name"] not in known
    ]
    return tuple(lot50 + lot51 + lot51bis + lot51ter)


def lot51ter_entries(at: datetime) -> list[PracticeHypothesisEntry]:
    """Choices of the agent for the whole pontoon of lot 51 ter (domains of lot 44)."""

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
            validity_domain="Modèle du ponton intégral (lot 51 ter).",
            discarded_variants=tuple(
                DiscardedVariant(description=d, reason=r) for d, r in discarded
            ),
            reference="session du lot 51 ter (projets/pontons_alu_01, docs/essais_lot51ter.md)",
            decided_at=at,
        )

    return [
        choice(
            "A10",
            "Noms des groupes du ponton intégral",
            "noms_groupes",
            ("projet:mesh_check",),
            "Travées T1 à T5, PT1 à PT5, PF ; palées P1 à P5 (CHEV_<palée>_<C1|C2>, "
            "LONG_<palée>_<rive>, PILE_<palée>_<chevêtre>_<rive>, SEMELLE_<palée>, "
            "SOL_<palée>) ; appuis AX_<palée><chevêtre>_<rive>_1, _2, _K ; culée "
            "APP_CULEE, APP_CULEE_YM, APP_CULEE_YP ; zones ACC_<T1D|T1M|T1F|PTk|PF>_<rive> ; "
            "taquets TQ1 à TQ10 par rive ; ANGLES_ANNEAU, LONGRINES_COURANT ; 24 caractères "
            "au plus.",
            "Les invariants calculés à part contrôlent chaque groupe (cardinal, boîte).",
            [("Noms au-delà de 24 caractères", "tronqués en silence par Code_Aster")],
        ),
        choice(
            "A11",
            "Lecture du déplacement en X des axes et de l'équilibre des palées",
            "lecture_champs",
            ("projet:controles",),
            "DX d'un axe = translation en X du point de l'axe portée par l'oreille 1, "
            "u_N + θ_N ∧ (P − N) ; glissement = la même moins celle portée par le nœud "
            "du chevêtre ; ΣRz d'une palée = Σ des forces −k_n × aire × u_z des nœuds de "
            "sa semelle (aires tributaires de RIGI_PARASOL).",
            "Critères 5 à 7 de docs/essais_lot51ter.md (équilibre sous AM1, dilatation "
            "sous TP, appuis à axe).",
            [
                (
                    "DX du nœud de l'oreille",
                    "décalé de θ × (P − N) par la rotation de l'oreille sous l'axe",
                )
            ],
        ),
    ]


def build_sheet() -> HypothesesSheet:
    arbitrations = [
        parse_arbitration(r.read_text(encoding="utf-8")) for r in RECORDINGS
    ]
    for arbitration in arbitrations:
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
    sheet, _done = record_decisions(sheet, arbitrations[0])
    for entry in agent_entries(arbitrations[0].recorded_at):
        sheet = insert_practice_entry(sheet, entry)
    for arbitration in arbitrations[1:3]:
        sheet, _done = record_decisions(sheet, arbitration)
    for entry in lot51_entries(arbitrations[2].recorded_at):
        sheet = insert_practice_entry(sheet, entry)
    sheet, _done = record_decisions(sheet, arbitrations[3])
    for entry in lot51bis_entries(arbitrations[3].recorded_at):
        sheet = insert_practice_entry(sheet, entry)
    sheet, _done = record_decisions(sheet, arbitrations[4])
    for entry in lot51ter_entries(arbitrations[4].recorded_at):
        sheet = insert_practice_entry(sheet, entry)
    sheet, _done = record_decisions(sheet, arbitrations[5])
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
