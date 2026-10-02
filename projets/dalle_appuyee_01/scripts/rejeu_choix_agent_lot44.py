"""Lot 44, étape 1 : rejeu de la catégorie `choix_agent` sur la fiche de la phase 1.

Entrée : la fiche PROPOSÉE de la phase 1 du lot 43 (`build_fiche_lot43.build_sheet`,
inchangée) et les données de la phase 1 (`donnees/historique/dalle_model_data_phase1.yaml`).
Le rejeu applique la règle de partage du lot 44 (`CLAUDE.md`, skill
`hypotheses-drafting`) : ce que les contrôles ou le niveau E vérifient devient un
choix de l'agent (`record_agent_choice`, domaine et vérificateurs nommés) ; ce qui
engage l'ouvrage reste une question à MM.

- les 9 noms de groupes : `choix_agent` (CTL-008 invariants de maillage, CTL-009
  longueur des noms) ;
- point 9, repère : `choix_agent` (domaine `repere`) ;
- point 10, mailles, taille, suite de convergence, lecture des moments :
  `choix_agent` (domaines `maillage`, `convergence`, `lecture_champs`), et la valeur
  `maillage.taille_elements` est fournie par cette décision ;
- point 6 : la question mêlait une condition d'appui physique (bilatéral ou
  unilatéral : reste à MM) et deux choix vérifiés par contrôle (blocage isostatique
  de la membrane, dalle entière avec symétrie contrôlée) : elle est scindée, la
  première moitié reste une question.

Rien d'autre n'est modifié : matériaux, charges, combinaisons, ferraillage,
modélisation de plaque et périmètre restent des questions. Les choix retenus sont
ceux qu'a validés la section B de l'arbitrage du lot 43, pour que le rejeu se
compare à ce qui a été fait ; leur auteur est ici l'agent.

Sorties : `fiche/hypotheses_dalle_rejeu_lot44.json`, `fiche/fiche_a_arbitrer_rejeu_lot44.md`
et `references/rejeu_choix_agent_lot44.json` (comptage avant et après). Déterministe.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/rejeu_choix_agent_lot44.py`
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_fiche_lot43 import DATA, SOURCES, build_sheet

from aster_expert.agent.arbitration import record_agent_choice, render_decision_sheet
from aster_expert.agent.drafting import SearchAttempt, record_unfounded_point
from aster_expert.agent.hypotheses import (
    DiscardedVariant,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
)
from aster_expert.agent.model_data import (
    DataValue,
    ModelData,
    ValueSource,
    check_consistency,
    load_model_data,
)
from aster_expert.constats.base import base_dir, load_base, resolve_sheet

PROJECT = ROOT / "projets" / "dalle_appuyee_01"
FICHE = PROJECT / "fiche" / "hypotheses_dalle_rejeu_lot44.json"
DOCUMENT = PROJECT / "fiche" / "fiche_a_arbitrer_rejeu_lot44.md"
SUMMARY = PROJECT / "references" / "rejeu_choix_agent_lot44.json"

DECIDED_AT = datetime.fromisoformat("2026-10-02T14:00:00-04:00")
REFERENCE = "rejeu lot 44 de la fiche de la phase 1 du lot 43 (règle de partage)"

GROUP_VERIFIERS = ("CTL-008", "CTL-009")


def _practice(sheet: HypothesesSheet, point: str) -> PracticeHypothesisEntry:
    (entry,) = (
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.point_label == point
    )
    return entry


def _frame(question: PracticeHypothesisEntry) -> PracticeHypothesisEntry:
    return record_agent_choice(
        entry=question,
        domain="repere",
        verified_by=("CTL-008", "CTL-006"),
        option_retained=(
            "Origine au coin A (0, 0, 0) ; X selon le côté de 6,00 m, Y selon le côté de "
            "4,00 m, Z vertical ascendant ; plan de la dalle z = 0 (feuillet moyen). "
            "Unités m, N, Pa, kg (PRE-012)."
        ),
        justification=(
            "Repère de la série de Navier (origine au coin), qui rend la comparaison du "
            "niveau E directe ; il ne change rien à la physique représentée. Les "
            "coordonnées et boîtes englobantes des groupes sont vérifiées par les "
            "invariants du maillage (CTL-008), l'orientation des axes par la symétrie des "
            "résultats selon X = 3,00 et Y = 2,00 (CTL-006)."
        ),
        validity_domain="Dalle rectangulaire de cette fiche.",
        discarded_variants=(
            DiscardedVariant(
                description="Origine au centre de la dalle",
                reason="la série de Navier est écrite depuis un coin ; aucun gain ici",
            ),
        ),
        reference=REFERENCE,
        decided_at=DECIDED_AT,
    )


def _mesh(question: PracticeHypothesisEntry) -> PracticeHypothesisEntry:
    return record_agent_choice(
        entry=question,
        domain=("maillage", "convergence", "lecture_champs"),
        verified_by=("CTL-008", "CTL-012", "REF-014"),
        option_retained=(
            "QUAD4 réguliers (DKQ sous DKT) ; suite de convergence de rapport 2 : tailles "
            "0,50, 0,25 et 0,125 m (12×8, 24×16, 48×32 mailles), nœud au centre (3,00 ; "
            "2,00) dans les trois maillages ; calcul de référence sur la taille 0,125 m. "
            "Moments au centre lus en EFGE_NOEU ; EFGE_ELNO sert seulement à contrôler "
            "l'écart de lissage au centre."
        ),
        justification=(
            "Choix technique vérifié : les comptages de mailles et de nœuds et le nœud "
            "central par les invariants du maillage (CTL-008), la décroissance de "
            "l'erreur au raffinement ×2 contre Navier (CTL-012, critère de CLAUDE.md), la "
            "lecture des moments par la comparaison du niveau E à Navier (REF-014)."
        ),
        validity_domain=(
            "Calcul élastique linéaire de la dalle ; une erreur qui ne décroît pas au "
            "raffinement remet le choix en cause."
        ),
        discarded_variants=(
            DiscardedVariant(
                description="TRIA3 (DKT triangulaire)",
                reason="maillage moins régulier, nœud central moins direct à garantir",
            ),
            DiscardedVariant(
                description="Moments lus en EFGE_ELNO d'une maille adjacente",
                reason="valeur d'un coin de maille, pas du nœud central de Navier",
            ),
        ),
        reference=REFERENCE,
        decided_at=DECIDED_AT,
    )


def _support_split(
    question: PracticeHypothesisEntry,
) -> tuple[PracticeHypothesisEntry, PracticeHypothesisEntry]:
    """Point 6 scindé : l'appui physique reste à MM, le reste est un choix vérifié."""
    physical = record_unfounded_point(
        point_label="6",
        topic="Condition d'appui physique des bords : bilatérale ou unilatérale",
        searches=(
            SearchAttempt(
                profile="theorie",
                query=(
                    "plaque mince simplement appuyée charge uniforme solution analytique "
                    "(famille V)"
                ),
                outcome=(
                    "SSLS127 : DZ = 0 sur le contour, quart de dalle ; ne dit rien des "
                    "coins ni de la membrane"
                ),
            ),
        ),
        options_considered=question.options_considered[:2],
        deduction=(
            "La solution de Navier suppose w = 0 sur tout le bord, coins tenus : seul "
            "l'appui bilatéral la reproduit. C'est une condition d'appui physique de "
            "l'ouvrage : elle reste à MM (règle de partage, lot 44)."
        ),
    )
    restraint = record_unfounded_point(
        point_label="6",
        topic="Blocage des mouvements de corps rigide de membrane et étendue du modèle",
        searches=(
            SearchAttempt(
                profile="methode",
                query="précédents et diagnostics : blocage, symétrie (search_connaissances)",
                outcome=(
                    "DIAG-001 (redondance de blocage et pivot nul), CA-030 (symétrie d'une "
                    "coque DKT) : à éviter en modélisant la dalle entière"
                ),
            ),
        ),
        options_considered=question.options_considered[2:],
    )
    decided = record_agent_choice(
        entry=restraint,
        domain=("blocage_isostatique", "etendue_modele"),
        verified_by=("CTL-005", "CTL-006"),
        option_retained=(
            "Dalle entière, sans plan de symétrie. Plan de la dalle bloqué de façon "
            "isostatique : DX = DY = 0 au coin A (0, 0), DY = 0 au coin B (6,00 ; 0), sans "
            "autre condition sur DX, DY (DIAG-001)."
        ),
        justification=(
            "Le blocage isostatique ne transmet aucun effort sous charges verticales : "
            "l'équilibre des seules composantes bloquées le vérifie (CTL-005, CA-036). La "
            "dalle entière fait de la symétrie un contrôle de niveau D (CTL-006) au lieu "
            "d'une hypothèse, et écarte le piège des conditions de symétrie des coques "
            "(CA-030)."
        ),
        validity_domain="Charges perpendiculaires au plan de la dalle.",
        discarded_variants=(
            DiscardedVariant(
                description="Quart de dalle avec deux plans de symétrie (SSLS127)",
                reason=(
                    "la symétrie devient une hypothèse non contrôlée ; conditions de "
                    "symétrie DKT à départager (CA-030 contre SSLS127)"
                ),
            ),
        ),
        reference=REFERENCE,
        decided_at=DECIDED_AT,
    )
    return physical, decided


def replay_sheet(sheet: HypothesesSheet) -> HypothesesSheet:
    """La fiche de la phase 1 réécrite selon la règle de partage du lot 44."""
    entries: list[object] = []
    for entry in sheet.entries:
        if isinstance(entry, PracticeHypothesisEntry) and entry.point_label == "9":
            entries.append(_frame(entry))
        elif isinstance(entry, PracticeHypothesisEntry) and entry.point_label == "10":
            entries.append(_mesh(entry))
        elif isinstance(entry, PracticeHypothesisEntry) and entry.point_label == "6":
            entries.extend(_support_split(entry))
        else:
            entries.append(entry)
    groups = tuple(
        MeshGroupNaming(
            group_name=g.group_name,
            kind=g.kind,
            description=g.description,
            status="choix_agent",
            point_label=g.point_label,
            verified_by=GROUP_VERIFIERS,
        )
        for g in sheet.group_naming
    )
    return sheet.model_copy(update={"entries": tuple(entries), "group_naming": groups})


def replay_data(data: ModelData) -> ModelData:
    """`maillage.taille_elements` fournie par le choix de l'agent du point 10."""
    groups = {name: dict(values) for name, values in data.groups.items()}
    groups["maillage"]["taille_elements"] = DataValue(
        status="fourni",
        value=0.125,
        unit="m",
        source=ValueSource(kind="decision", point_label="10"),
        comment="Taille du calcul de référence (choix de l'agent, point 10).",
    )
    return data.model_copy(update={"groups": groups})


def counts() -> dict[str, object]:
    base = load_base(base_dir(ROOT))
    data = load_model_data(DATA)
    before_sheet = resolve_sheet(build_sheet(), base)
    after_sheet = resolve_sheet(replay_sheet(build_sheet()), base)
    before = before_sheet.generation_blockers(data)
    after = after_sheet.generation_blockers(replay_data(data))
    lifted = [b for b in before if b not in after]
    added = [b for b in after if b not in before]
    return {
        "bloqueurs_avant": len(before),
        "bloqueurs_apres": len(after),
        "bloqueurs_leves": lifted,
        "bloqueurs_nouveaux": added,
        "choix_agent_entrees": [
            f"point {e.point_label} : {e.topic}" for e in after_sheet.agent_choices()
        ],
        "choix_agent_groupes": [g.group_name for g in after_sheet.agent_group_names()],
        "ecarts_donnees": [
            str(d) for d in check_consistency(replay_data(data), after_sheet, SOURCES)
        ],
    }


def main() -> int:
    sheet = replay_sheet(build_sheet())
    FICHE.write_text(
        json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    resolved = resolve_sheet(sheet, load_base(base_dir(ROOT)))
    DOCUMENT.write_text(
        render_decision_sheet(resolved).rstrip() + "\n", encoding="utf-8"
    )
    summary = counts()
    SUMMARY.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"bloqueurs : {summary['bloqueurs_avant']} avant, "
        f"{summary['bloqueurs_apres']} après "
        f"({len(summary['bloqueurs_leves'])} levés, "  # type: ignore[arg-type]
        f"{len(summary['bloqueurs_nouveaux'])} nouveaux)"  # type: ignore[arg-type]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
