"""Lot 47 -- fiche d'hypothèses of the jetty ESTACADE-PIEUX-01.

Three categories (CLAUDE.md, lot 44):

- MM's decisions E1 to E16, origin `arbitrage_mm`, text copied as written in
  `donnees/sources/arbitrage_estacade_pieux_01_lot47.md` (E1 to E12 of the lot
  instruction, E13 to E16 of MM's answers in the chat), and E17 to E19 of the lot 47
  bis instruction (`donnees/sources/arbitrage_estacade_pieux_01_lot47bis.md`: reading
  rules v2, TR case of the combination 100, sensitivity variant of the cap height), and
  E20 of the lot 47 quater instruction (DKT or DST for a slab coupled to beams sharing
  its nodes, the decision of the precedent PRE-039; the reference is unchanged);
- the agent's choices U1 to U6 (`choix_agent`), each in a domain of the partition
  rule and with its named verifiers;
- the `code_aster` facts, by reference to the shared base (K1 to K6): the findings
  consulted before writing the commands, and CA-054 to CA-057 established by the
  probe S1 of this lot.

Recording time of the decisions: `donnees/sources/enregistrement_lot47.json` and
`enregistrement_lot47bis.json` (MM wrote neither date nor hour). Idempotent: rerun
`.venv/bin/python projets/estacade_pieux_01/scripts/fiche_lot47.py`; a test replays
it and compares byte for byte.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.agent.arbitration import (
    insert_practice_entry,
    record_agent_choice,
    record_practice_decision,
)
from aster_expert.agent.enregistrement import (
    check_quotes,
    parse_arbitration,
    record_decisions,
)
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    FindingReference,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.prevues import carry_planned_commands
from aster_expert.projet.context import load_project
from estacade_pieux_01.discretisation import PRODUCTION_SIZE, JettyMesh
from estacade_pieux_01.donnees import model_values

PROJECT = ROOT / "projets" / "estacade_pieux_01"
FICHE = PROJECT / "fiche" / "hypotheses_estacade_pieux_01.json"
SOURCES = PROJECT / "donnees" / "sources"
LATER_RECORDINGS = ("enregistrement_E21_E23_lot49bis.md",)
"""Structured arbitrations recorded by `aster-expert fiche enregistrer` (lot 48 bis
on), replayed in order after E1 to E20."""
ARBITRATION = "arbitrage_estacade_pieux_01_lot47 (donnees/sources/arbitrage_estacade_pieux_01_lot47.md)"
ARBITRATION_BIS = "arbitrage_estacade_pieux_01_lot47bis (donnees/sources/arbitrage_estacade_pieux_01_lot47bis.md)"
ARBITRATION_QUATER = "arbitrage_estacade_pieux_01_lot47quater (donnees/sources/arbitrage_estacade_pieux_01_lot47quater.md)"
VALIDITY = (
    "Contre-calcul du modèle source d'avant-projet (lot 47), tel que MM l'a décidé ; "
    "hors de ce contre-calcul, la décision n'est pas établie."
)


VALIDITY_OF = {
    "E20": (
        "Dalle mince à moyennement épaisse (h/L ≤ 1/10), poutres au plan moyen (E20, "
        "texte de MM) ; établie sur le plan factoriel du lot 47 ter (dalle de 0,40 m, "
        "chevêtres de 1,20 × 0,90 et 0,80 m, maillage de 0,05 m) et CA-058."
    ),
}
"""Domain of validity written by MM for a decision, when MM wrote one."""


def recorded_at(name: str = "enregistrement_lot47.json") -> datetime:
    data = json.loads((SOURCES / name).read_text(encoding="utf-8"))
    return datetime.fromisoformat(data["enregistre_le"])


def mm_decisions(name: str = "arbitrage_estacade_pieux_01_lot47.md") -> dict[str, str]:
    """Text of each decision, read in the arbitration file (never retyped)."""
    text = (SOURCES / name).read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("| E") and "|" in line[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            out[cells[0]] = cells[1]
    blocks = text.split("### ")[1:]
    for block in blocks:
        head = block.split(" ", 1)[0]
        quoted = [ln[2:] for ln in block.splitlines() if ln.startswith("> ")]
        if head.startswith("E") and quoted:
            out[head] = " ".join(quoted)
    return out


TOPICS = {
    "E1": "Géométrie retenue : celle du modèle source",
    "E2": "Chevêtres : section, position et recouvrement avec la dalle",
    "E3": "Sections des pieux par tronçon",
    "E4": "Appui vertical en pointe des pieux",
    "E5": "Comportement : linéaire",
    "E6": "Ressorts de la file 1 : correction de recopie et nœuds manquants",
    "E7": "Matériaux",
    "E8": "Charge mobile TS : pas et positions ; UDL",
    "E9": "Freinage",
    "E10": "Température",
    "E11": "Combinaisons",
    "E12": "Tolérances de comparaison",
    "E13": "Formulations d'éléments et variantes de sensibilité",
    "E14": "Étendue du bouchon des pieux",
    "E15": "Surface d'application des roues (TS et LM2)",
    "E16": "Positions de LM2",
}
TOPICS_BIS = {
    "E17": "Règles de lecture v2 de la comparaison (écrites après la première exécution)",
    "E18": "Cas TR de la combinaison 100 : essieu de 160 kN sur le trottoir",
    "E19": "Variante de sensibilité : chevêtre de 0,80 m",
}
TOPICS_QUATER = {
    "E20": "DKT ou DST pour une dalle couplée à des poutres qui partagent ses nœuds",
}

DISCARDED = {
    "E1": [("Description à 36,2 m et 8 files", "non retenue par MM (E1)")],
    "E2": [
        (
            "Chevêtre excentré sous la dalle",
            "« sans excentrement » (E2) ; double compte accepté, chiffré sans correction",
        )
    ],
    "E3": [("Section mixte acier-béton au droit du bouchon", "exclue par E3")],
    "E4": [("Rotations bloquées en pointe", "« rotations libres » (E4)")],
    "E5": [("Ressorts à palier (non linéaires)", "« sans palier » (E5)")],
    "E6": [
        (
            "Valeurs du tableau source aux nœuds −8,00 et −8,50 de la file 1",
            "erreur de recopie (E6)",
        )
    ],
    "E7": [
        (
            "Autre poids volumique de l'acier",
            "la valeur du modèle source est retenue (E7)",
        )
    ],
    "E8": [
        (
            "Autre pas ou positions transversales",
            "pas de 0,50 m, « axé » et « bord de voie » (E8)",
        )
    ],
    "E9": [
        ("Freinage appliqué en face supérieure", "appliqué dans le plan moyen (E9)")
    ],
    "E10": [("ΔT appliqué aussi aux pieux", "dalle et chevêtres seulement (E10)")],
    "E11": [
        ("Combinaisons recalculées selon une norme", "reproduites telles quelles (E11)")
    ],
    "E12": [
        (
            "Tolérance unique pour toutes les grandeurs",
            "3 %, 5 % et 10 % selon la grandeur (E12)",
        )
    ],
    "E13": [
        ("DKT et POU_D_E", "option proposée, non retenue par MM (E13)"),
        (
            "DST et POU_D_T",
            "option proposée, non retenue ; DST gardé en variante de sensibilité (E13)",
        ),
    ],
    "E14": [
        (
            "Nœud du tablier à +0,70, à 0,00, à −0,80 ou à −2,25",
            "options proposées, non retenues (E14)",
        ),
    ],
    "E15": [
        ("Diffusion à 45° jusqu'au plan moyen", "non retenue par MM (E15)"),
        ("Les deux, la diffusion en sensibilité", "non retenue par MM (E15)"),
    ],
    "E16": [
        ("Toute la largeur de la dalle", "non retenue par MM (E16)"),
        ("Axé seulement", "non retenue par MM (E16)"),
    ],
    "E17": [
        (
            "Règles de lecture v1 (docs/essais_lot47.md § 2.5)",
            "conservées avec leurs verdicts dans l'historique, remplacées pour la "
            "comparaison par E17",
        )
    ],
    "E18": [
        (
            "Essieu en charge ponctuelle",
            "une force nodale sur une plaque est singulière (E18)",
        ),
        (
            "Essieu posé en travers du trottoir",
            "trottoir de 1,50 m trop étroit pour un essieu de 2,00 m (E18)",
        ),
        (
            "Essieu ajouté aussi à la charge des trottoirs de LM1",
            "« ce cas ne s'applique qu'à la combinaison 100 » (E18)",
        ),
    ],
    "E19": [
        (
            "Chevêtre de 0,80 m comme référence",
            "« la référence reste à 0,90 m (E2) » (E19)",
        )
    ],
    "E20": [
        (
            "DKT pour toute dalle, la barre seule lue",
            "sous-estime l'effort tranchant du chevêtre près des appuis "
            "(plan factoriel du lot 47 ter)",
        ),
        (
            "DST sans condition",
            "« DKT reste admis pour une dalle sans poutre couplée » (E20)",
        ),
    ],
}

NOTES = {
    "E8": (
        "Application par la session (à relire par MM) : TS, centre du tandem en "
        "X = 15,60 + 0,50 k, k = −29 … 29 (59 positions, toutes les empreintes sur la "
        "dalle, symétriques par rapport au milieu) ; « axé » : roues à Y = ±1,00 ; « bord "
        "de voie » : roue extérieure tangente au bord Y = 1,50 de la voie, roues à "
        "Y = 1,30 et −0,70, côté Y > 0 seulement (le côté Y < 0 en est l'image miroir)."
    ),
    "E9": "Une seule direction, +X.",
    "E20": (
        "Fonde le précédent PRE-039 (lot 47 quater). Ne modifie pas la référence de "
        "l'estacade : E13 garde la dalle DKT, la consigne du lot 47 quater interdisant tout "
        "changement de la référence (E1 à E19)."
    ),
    "E16": (
        "Erreur de la session dans la description proposée (Y = ±1,325) : la règle "
        "choisie, roue tangente au bord de la voie avec l'empreinte de 0,60 m selon Y, "
        "donne Y = 1,20 et −0,80 ; c'est la règle qui est appliquée. Positions selon X : "
        "15,575 − 0,50 k et 15,625 + 0,50 k, k = 0 … 30 (62 positions, empreintes de "
        "0,35 m alignées sur les mailles de 0,05 m)."
    ),
}


def mm_entries(
    at: datetime,
    topics: dict[str, str] = TOPICS,
    arbitration: str = ARBITRATION,
    texts: dict[str, str] | None = None,
) -> list[PracticeHypothesisEntry]:
    texts = mm_decisions() if texts is None else texts
    source_file = arbitration.split("(")[1].removesuffix(")").removeprefix("donnees/")
    out = []
    for label, topic in topics.items():
        open_entry = PracticeHypothesisEntry(
            point_label=label, topic=topic, status="non_tranche", notes=NOTES.get(label)
        )
        out.append(
            record_practice_decision(
                entry=open_entry,
                option_retained=texts[label],
                justification=(
                    f"Décision {label} de MM, recopiée à l'identique ({source_file})."
                ),
                validity_domain=VALIDITY_OF.get(label, VALIDITY),
                sources=(
                    PracticeSource(
                        origin="arbitrage_mm",
                        reference=f"{arbitration}, {label}",
                        date=at.date(),
                    ),
                ),
                discarded_variants=tuple(
                    DiscardedVariant(description=d, reason=r)
                    for d, r in DISCARDED[label]
                ),
                decided_by="MM",
                decided_at=at,
            )
        )
    return out


def agent_entries(at: datetime, size_note: str) -> list[PracticeHypothesisEntry]:
    reference = "session du lot 47 (projets/estacade_pieux_01, docs/essais_lot47.md)"

    def choice(
        label: str,
        topic: str,
        domain: object,
        verified_by: tuple[str, ...],
        option: str,
        justification: str,
        validity: str,
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
            validity_domain=validity,
            discarded_variants=tuple(
                DiscardedVariant(description=d, reason=r) for d, r in discarded
            ),
            reference=reference,
            decided_at=at,
        )

    return [
        choice(
            "U1",
            "Repère global, origine et unités",
            "repere",
            ("CTL-005", "CTL-013"),
            "X le long du tablier depuis l'about (X = 0), Y transversal depuis l'axe du "
            "tablier, Z vers le haut égal à la cote NGF (dalle au plan moyen Z = +1,30, "
            "pointes à Z = −13,00) ; unités m, N, Pa, kg ; RHO = γ / g avec g = 9,81 m/s² "
            "(sans effet sur les résultats : la pesanteur redonne exactement γ).",
            "Les cotes de B1 à B3 se lisent directement ; les résultantes et l'équilibre "
            "contrôlent les unités.",
            "Modèle de l'estacade du lot 47.",
            [
                (
                    "Origine au milieu du tablier",
                    "les files de B1 sont données depuis l'about",
                )
            ],
        ),
        choice(
            "U2",
            "Type et taille des mailles",
            "maillage",
            ("projet:mesh_check", "CTL-013"),
            "QUAD4 réguliers de " + size_note + " sur la dalle (624 × 120 mailles), "
            "taille qui divise toutes les cotes utiles (files, lignes de pieux, bords de "
            "voie, bords des empreintes de TS et LM2 aux pas d'E8 et E16) : chaque "
            "empreinte est une réunion de mailles entières ; chevêtres : SEG2 de la "
            "dalle sur les lignes des files ; pieux : un SEG2 entre deux cotes "
            "successives (ressorts tous les 0,50 m, changements de section de B2, nœud "
            "du plan moyen).",
            "Évite l'évaluation aux nœuds d'une pression en marche (CA-029, PAT-003) ; "
            "maillage contrôlé par 364 invariants calculés avant exécution.",
            "Charges de roue à empreinte rectangulaire alignée ; DKT plans.",
            [
                (
                    "Maillage libre avec raffinement local sous les roues",
                    "les positions mobiles couvrent toute la voie : une grille régulière alignée y est plus simple et exacte",
                ),
                (
                    "Pression de roue définie par une fonction de X et Y",
                    "évaluée aux nœuds, elle déborde d'une demi-maille (CA-029)",
                ),
            ],
        ),
        choice(
            "U3",
            "Suite de convergence de la dalle sous charge de roue",
            "convergence",
            ("projet:convergence",),
            "Trois maillages de rapport 2 (h = 0,10 / 0,05 / 0,025 m), TS axé centré en "
            "X = 8,10 et X = 5,60 ; critère de docs/essais_lot47.md § 2.7.",
            "Aucune solution de référence : l'écart entre maillages successifs doit "
            "décroître et rester petit au maillage de production.",
            "Grandeurs locales de la dalle sous TS seulement.",
            [
                (
                    "Comparaison à une solution analytique",
                    "aucune n'existe pour ce modèle",
                )
            ],
        ),
        choice(
            "U4",
            "Noms des groupes du maillage",
            "noms_groupes",
            ("projet:mesh_check",),
            "Noms de la convention de nommage de la fiche (24 caractères au plus) : "
            "dalle, voie, trottoirs, rives, chevêtres, pieux, tronçons, têtes, pointes "
            "et groupes de ressorts par famille et par cote.",
            "Les invariants du maillage contrôlent chaque groupe (cardinal, type, boîte).",
            "Maillage du lot 47.",
            [
                (
                    "Noms au-delà de 24 caractères",
                    "tronqués en silence par Code_Aster (lot 28)",
                )
            ],
        ),
        choice(
            "U5",
            "Lecture des champs pour la comparaison",
            "lecture_champs",
            ("CTL-005", "projet:contre_calcul"),
            "Dalle : EFGE_NOEU calculé sur la seule dalle (DIAG-011), composantes MXX, "
            "QX, NXX ; pieux et chevêtres : EFGE_ELNO (extrémités d'élément, sans "
            "moyenne) ; déplacements DEPL ; zones, signes et enveloppes de "
            "docs/essais_lot47.md § 2.3 à 2.5 (critères écrits avant l'exécution).",
            "EFGE_NOEU sur des éléments de repères différents déclenche UTILITAI_4 "
            "(DIAG-011, sonde S1) ; les modules des barres évitent les conventions "
            "d'axes inconnues du modèle source.",
            "Comparaison au modèle source du lot 47.",
            [
                (
                    "EFGE_NOEU sur tout le modèle",
                    "repères locaux incompatibles aux nœuds partagés (DIAG-011)",
                )
            ],
        ),
        choice(
            "U6",
            "Étendue du modèle",
            "etendue_modele",
            ("CTL-006",),
            "Ouvrage entier, sans réduction par symétrie ; la symétrie par rapport à "
            "X = 15,60 et Y = 0 est contrôlée sur les cas symétriques.",
            "Les charges mobiles, le freinage et TS en bord de voie ne sont pas "
            "symétriques.",
            "Modèle du lot 47.",
            [("Demi-ouvrage", "charges non symétriques")],
        ),
    ]


CONSTATS = (
    ("CA-020", "K1"),
    ("CA-034", "K1"),
    ("CA-029", "K2"),
    ("CA-021", "K2"),
    ("CA-048", "K2"),
    ("CA-028", "K2"),
    ("CA-047", "K2"),
    ("CA-045", "K2"),
    ("CA-037", "K3"),
    ("CA-054", "K3"),
    ("CA-055", "K4"),
    ("CA-056", "K5"),
    ("CA-057", "K6"),
    ("CA-058", "K7"),
)


def group_names(values: object) -> list[MeshGroupNaming]:
    mesh = JettyMesh(values, PRODUCTION_SIZE)  # type: ignore[arg-type]
    names: list[tuple[str, str, str]] = []
    for g in mesh.invariants()["groups"]:
        kind = "noeud" if g["kind"] == "node" else "maille"
        names.append((g["name"], kind, f"{g['count']} {g.get('cell_type', 'nœuds')}"))
    return [
        MeshGroupNaming(
            group_name=name,
            kind=kind,  # type: ignore[arg-type]
            description=f"Groupe du maillage de l'estacade ({desc}).",
            status="choix_agent",
            point_label="U4",
            verified_by=("projet:mesh_check",),
        )
        for name, kind, desc in names
    ]


def build_sheet() -> HypothesesSheet:
    ctx = load_project("estacade_pieux_01", ROOT)
    values = model_values(ctx)
    at = recorded_at()
    sheet = HypothesesSheet(
        project_name="ESTACADE-PIEUX-01",
        structure_description=(
            "Estacade sur pieux (contre-calcul d'un modèle non validé) : tablier-dalle "
            "de 31,20 × 6,00 × 0,40 m sur 7 chevêtres de 1,20 × 0,90 m, 14 pieux "
            "tubulaires métalliques à ressorts de sol horizontaux, appui vertical en "
            "pointe à −13,00 m NGF."
        ),
        aster_version="17.4.0",
        created_at=at,
        entries=tuple(
            FindingReference(constat_id=cid, point_label=label)
            for cid, label in CONSTATS
        ),
        group_naming=tuple(group_names(values)),
    )
    bis = mm_entries(
        recorded_at("enregistrement_lot47bis.json"),
        TOPICS_BIS,
        ARBITRATION_BIS,
        mm_decisions("arbitrage_estacade_pieux_01_lot47bis.md"),
    )
    quater = mm_entries(
        recorded_at("enregistrement_lot47quater.json"),
        TOPICS_QUATER,
        ARBITRATION_QUATER,
        mm_decisions("arbitrage_estacade_pieux_01_lot47quater.md"),
    )
    for entry in [*mm_entries(at), *agent_entries(at, "0,05 m"), *bis, *quater]:
        sheet = insert_practice_entry(sheet, entry)
    # Lot 49 bis : E21 à E23, enregistrées par `aster-expert fiche enregistrer`, rejouées
    # ici par la même fonction pour que la fiche reste reproductible.
    for name in LATER_RECORDINGS:
        text = (SOURCES / name).read_text(encoding="utf-8")
        arbitration = parse_arbitration(text)
        check_quotes(
            arbitration,
            (PROJECT / arbitration.source).read_text(encoding="utf-8"),
        )
        sheet, _done = record_decisions(sheet, arbitration)
    return sheet


def main() -> None:
    # `fiche prevoir` écrit `planned_commands` dans la fiche : ne pas les perdre.
    sheet = carry_planned_commands(build_sheet(), FICHE)
    FICHE.write_text(
        json.dumps(json.loads(sheet.model_dump_json()), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        FICHE.relative_to(ROOT),
        len(sheet.entries),
        "entrées,",
        len(sheet.group_naming),
        "groupes",
    )
    print(
        "bloqueurs :",
        sheet.generation_blockers() or "aucun (hors références de constats)",
    )


if __name__ == "__main__":
    main()
