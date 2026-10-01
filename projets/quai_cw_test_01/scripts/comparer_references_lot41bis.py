"""Lot 41 bis, étape 3 : critère de non-régression après changement d'environnement.

Critère écrit avant l'exécution (`docs/essais_lot41bis.md`) :

1. la comparaison du lot 41 est refaite **sans modification** (`comparer_references_lot41`,
   mêmes références, même classement) ; les fichiers identiques au lot 41 doivent le
   rester, les fichiers « admis » doivent l'être encore, et les 2 fichiers en échec
   formel au lot 41 doivent présenter exactement les mêmes lignes non énumérées
   qu'alors, rien d'autre ;
2. ces 2 fichiers doivent être identiques à l'octet à leur nouvelle référence
   (`references/lot41bis/`, sorties du lot 41 figées avant l'exécution).

Écrit `references/lot41bis/comparaison_critere_lot41.json` (sortie du script du lot
41) et `references/lot41bis/comparaison.json` (verdict du lot 41 bis).

Usage : python projets/quai_cw_test_01/scripts/comparer_references_lot41bis.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import comparer_references_lot41 as lot41

REFERENCES = lot41.REFERENCES
NEW_REFERENCES = REFERENCES / "lot41bis"
# Nouvelle référence -> sortie rejouée.
NEW_PAIRS = {
    "maillage/combiwall_mesh_invariants.yaml": lot41.PROJECT
    / "maillage"
    / "combiwall_mesh_invariants.yaml",
    "ferraillage/poutre.comm": lot41.RESULTS / "ferraillage" / "poutre.comm",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _non_enumerated(entry: dict[str, Any]) -> list[Any]:
    return [
        [p["ligne"], p["reference"], p["sortie"]]
        for p in entry.get("differences", [])
        if p["classe"] == "non énuméré"
    ]


def main() -> int:
    before = json.loads(
        (REFERENCES / "comparaison_lot41.json").read_text(encoding="utf-8")
    )
    rerun_path = NEW_REFERENCES / "comparaison_critere_lot41.json"
    lot41.main(["--sortie", str(rerun_path)])
    after = json.loads(rerun_path.read_text(encoding="utf-8"))
    old = {e["reference"]: e for e in before["fichiers"]}
    new = {e["reference"]: e for e in after["fichiers"]}

    rows: list[dict[str, Any]] = []
    for reference, entry in new.items():
        prior = old[reference]
        if prior["statut"] == "identique":
            ok = entry["statut"] == "identique"
            rule = "identique au lot 41 : doit le rester"
        elif prior["verdict"].startswith("réussi"):
            ok = entry["verdict"].startswith("réussi")
            rule = "admis au lot 41 : doit l'être encore"
        else:
            ok = _non_enumerated(entry) == _non_enumerated(prior)
            rule = "échec formel au lot 41 : mêmes lignes non énumérées, rien d'autre"
        rows.append(
            {
                "reference": reference,
                "regle": rule,
                "statut_lot41": prior["statut"],
                "statut_lot41bis": entry["statut"],
                "verdict": "réussi" if ok else "échec",
            }
        )
    for reference, produced in NEW_PAIRS.items():
        expected = _sha(NEW_REFERENCES / reference)
        obtained = _sha(produced) if produced.is_file() else None
        rows.append(
            {
                "reference": f"lot41bis/{reference}",
                "regle": "identique à l'octet à la nouvelle référence",
                "sha256_reference": expected,
                "sha256_sortie": obtained,
                "verdict": "réussi" if obtained == expected else "échec",
            }
        )
    failures = [r["reference"] for r in rows if r["verdict"] == "échec"]
    report = {
        "critere": "docs/essais_lot41bis.md, écrit avant l'exécution",
        "lignes": rows,
        "identiques_lot41bis": after["identiques"],
        "differents_admis_lot41bis": after["differents_admis"],
        "echecs_formels_critere_lot41": after["echecs"],
        "vues_informatives_identiques": after["vues_informatives_identiques"],
        "echecs": failures,
        "verdict": "réussi" if not failures else "échec",
    }
    (NEW_REFERENCES / "comparaison.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Lot 41 bis : {len(rows) - len(failures)}/{len(rows)} lignes du critère "
        f"réussies ; échecs : {failures or 'aucun'}"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
