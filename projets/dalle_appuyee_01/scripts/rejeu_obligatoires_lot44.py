"""Lot 44, étape 2 : rejeu de la détection des paramètres obligatoires sur la fiche
de la phase 1 du lot 43.

La phase 1 prévoyait `CALC_FERRAILLAGE` en 2D, à l'ELU, à l'ELS et à l'ELS_QP
(constat du point 14 de la fiche). Ce script le déclare (`PlannedCommand`), avec ce
que la fiche de la phase 1 couvrait déjà : une valeur du fichier de données (même
« à fournir ») ou une question du point 14 qui nomme le mot-clé (γc, γs, SIGS_ELS).
Rien d'autre n'est déclaré couvert : c'est la couverture qu'avait réellement la
fiche remise à MM.

`aster_expert.agent.obligatoires` lit alors les mots-clés obligatoires de chaque
combinaison (catalogue 17.4, puis table `data/config/obligations_execution.yaml`) et
ajoute une question par mot-clé non couvert. Attendu (lot 44) : les quatre
paramètres ELS que la seconde intervention de MM a dû fixer au lot 43 (σc, αe, KT,
Es).

Sortie : `references/rejeu_obligatoires_lot44.json`. Déterministe.

Usage : `.venv/bin/python projets/dalle_appuyee_01/scripts/rejeu_obligatoires_lot44.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_fiche_lot43 import DATA, build_sheet

from aster_expert.agent.hypotheses import HypothesesSheet, PlannedCommand
from aster_expert.agent.model_data import load_model_data
from aster_expert.agent.obligatoires import (
    add_missing_parameters,
    default_rules_path,
    load_execution_rules,
    missing_parameters,
)
from aster_expert.catalogue.models import CommandSchema
from aster_expert.catalogue.query import load_command_schema
from aster_expert.constats.base import base_dir, load_base, resolve_sheet

SUMMARY = (
    ROOT
    / "projets"
    / "dalle_appuyee_01"
    / "references"
    / "rejeu_obligatoires_lot44.json"
)
CATALOGUE = ROOT / "data" / "processed" / "catalogue"
DIGEST = "sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5"

PHASE1_COVERAGE = {
    "AFFE.C_INF": "data:durabilite.distance_parement_axe_armatures",
    "AFFE.C_SUP": "data:durabilite.distance_parement_axe_armatures",
    "AFFE.FYK": "data:acier.nuance",
    "AFFE.FCK": "data:beton.classe",
    "AFFE.WMAX_INF": "data:durabilite.ouverture_fissure_limite",
    "AFFE.WMAX_SUP": "data:durabilite.ouverture_fissure_limite",
    "AFFE.PHI_INF_X": "data:acier.diametre_barres",
    "AFFE.PHI_SUP_X": "data:acier.diametre_barres",
    "AFFE.PHI_INF_Y": "data:acier.diametre_barres",
    "AFFE.PHI_SUP_Y": "data:acier.diametre_barres",
    # Nommés dans les options de la question du point 14 de la phase 1.
    "AFFE.GAMMA_C": "point:14",
    "AFFE.GAMMA_S": "point:14",
    "AFFE.SIGS_ELS": "point:14",
}

ELS_PARAMETERS = {
    "σc": ("AFFE.SIGC_INF_ELS", "AFFE.SIGC_SUP_ELS", "AFFE.SIGC_ELS_QP"),
    "αe": ("AFFE.ALPHA_E",),
    "KT": ("AFFE.KT",),
    "Es": ("AFFE.EYS",),
}


def planned_sheet() -> HypothesesSheet:
    planned = tuple(
        PlannedCommand(
            command="CALC_FERRAILLAGE",
            point_label="14",
            options={"TYPE_STRUCTURE": "2D", "TYPE_COMB": comb},
            covered_by=PHASE1_COVERAGE,
        )
        for comb in ("ELU", "ELS", "ELS_QP")
    )
    sheet = resolve_sheet(build_sheet(), load_base(base_dir(ROOT)))
    return sheet.model_copy(update={"planned_commands": planned})


def schemas() -> dict[str, CommandSchema]:
    return {
        "CALC_FERRAILLAGE": load_command_schema(CATALOGUE, DIGEST, "CALC_FERRAILLAGE")
    }


def summary() -> dict[str, object]:
    sheet = planned_sheet()
    data = load_model_data(DATA)
    rules = load_execution_rules(default_rules_path(ROOT))
    missing = missing_parameters(sheet, data, schemas(), rules)
    found = {m.mandatory.keyword for m in missing}
    augmented = add_missing_parameters(sheet, missing)
    return {
        "parametres_manquants": [m.label() for m in missing],
        "questions_ajoutees": len(augmented.entries) - len(sheet.entries),
        "parametres_els_lot43": {
            name: sorted(k for k in keys if k in found)
            for name, keys in ELS_PARAMETERS.items()
        },
        "bloqueurs_avant": len(sheet.generation_blockers(data)),
        "bloqueurs_apres": len(augmented.generation_blockers(data)),
    }


def main() -> int:
    result = summary()
    SUMMARY.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for line in result["parametres_manquants"]:  # type: ignore[attr-defined]
        print(line)
    print(f"questions ajoutées : {result['questions_ajoutees']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
