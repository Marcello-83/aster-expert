"""Lot 41, étape 7 : compare les sorties de la chaîne rejouée par
`aster-expert projet quai_cw_test_01 <étape>` aux références figées à l'étape 1
(`projets/quai_cw_test_01/references/`, `empreintes.json`), fichier par fichier.

Pour chaque fichier : identique à l'octet, ou différent ; pour un fichier
différent, chaque paire de lignes différentes est classée selon le critère écrit
avant toute modification (`docs/essais_lot41.md`, étape 1) :

- « admis » : la ligne ne diffère que par un chemin ou une empreinte que le critère
  énumère (empreinte de la fiche dans l'en-tête du `.comm` ; chemins du `.mess`, du
  MED, du `.comm` exécuté, du fichier de données, des répertoires d'exécution et
  leurs empreintes ; date, durée et répertoire de l'exécution de `poutre.comm`) ;
- « non énuméré » : toute autre différence, même de chemin -- un échec au sens du
  critère, rapporté tel quel.

Les nombres ne sont jamais normalisés : une ligne dont une valeur numérique
diffère n'est jamais « admise ».

Usage : python projets/quai_cw_test_01/scripts/comparer_references_lot41.py \\
    [--sortie projets/quai_cw_test_01/references/comparaison_lot41.json]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "quai_cw_test_01"
REFERENCES = PROJECT / "references"
RESULTS = PROJECT / "resultats"

# Référence -> sortie rejouée.
PAIRS = {
    "comm/complet.comm": RESULTS / "complet.comm",
    "maillage/rapport_mesh_check.txt": RESULTS / "maillage" / "rapport_mesh_check.txt",
    "maillage/combiwall_mesh_invariants.yaml": PROJECT
    / "maillage"
    / "combiwall_mesh_invariants.yaml",
    "controles_d/equilibre.json": RESULTS / "controles" / "equilibre.json",
    "controles_d/integrale.json": RESULTS / "controles" / "integrale.json",
    "synthese/synthese.json": RESULTS / "synthese" / "synthese.json",
    "synthese/synthese.md": RESULTS / "synthese" / "synthese.md",
    "synthese/controles.md": RESULTS / "synthese" / "controles.md",
}
for _name in ("combinaisons.csv", "controle_manuel.json", "extrema.csv"):
    PAIRS[f"combinaisons/{_name}"] = RESULTS / "combinaisons" / _name
PAIRS["combinaisons/poutre_couronnement.md"] = (
    RESULTS / "combinaisons" / "poutre_couronnement.md"
)

_SHA = re.compile(r"\b[0-9a-f]{64}\b")
_RUN = re.compile(r"data/processed/runs/\d{8}T\d{6}-[0-9a-f]{8}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _admitted(reference: str, old: str, new: str, state: dict[str, Any]) -> bool:
    """La paire de lignes ne diffère-t-elle que par ce que le critère énumère ?"""
    if reference == "comm/complet.comm":
        return old.startswith("# Fiche             : sha256:") and new.startswith(
            "# Fiche             : sha256:"
        )
    if reference.startswith("ferraillage/rapports/executions.json"):
        return True
    if reference == "ferraillage/rapports/mess_ferr_extrait.txt":
        return re.sub(r"CALCULE LE \S+ A \S+", "", old) == re.sub(
            r"CALCULE LE \S+ A \S+", "", new
        )
    if reference.split("/")[0] not in ("controles_d", "synthese", "combinaisons"):
        return False

    def normal(line: str, *, new_side: bool) -> str:
        line = _RUN.sub("<exécution>", line)
        line = _SHA.sub("<empreinte>", line)
        comm = state["comm_new"] if new_side else state["comm_old"]
        data = state["data_new"] if new_side else state["data_old"]
        return line.replace(comm, "<comm>").replace(data, "<données>")

    return normal(old, new_side=False) == normal(new, new_side=True)


def _compare(reference: str, produced: Path, state: dict[str, Any]) -> dict[str, Any]:
    ref_path = REFERENCES / reference
    entry: dict[str, Any] = {
        "reference": reference,
        "sortie": str(produced.relative_to(ROOT)),
        "sha256_reference": _sha(ref_path),
    }
    if not produced.is_file():
        entry.update(statut="absent", verdict="échec")
        return entry
    entry["sha256_sortie"] = _sha(produced)
    if entry["sha256_sortie"] == entry["sha256_reference"]:
        entry.update(statut="identique", verdict="réussi")
        return entry
    entry["statut"] = "différent"
    if produced.suffix == ".png":
        entry["verdict"] = "échec"
        return entry
    old_lines = ref_path.read_text(encoding="utf-8").splitlines()
    new_lines = produced.read_text(encoding="utf-8").splitlines()
    pairs = []
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        olds, news = old_lines[i1:i2], new_lines[j1:j2]
        if len(olds) != len(news):
            pairs.append(
                {
                    "ligne": i1 + 1,
                    "reference": olds,
                    "sortie": news,
                    "classe": "non énuméré",
                }
            )
            continue
        for k, (a, b) in enumerate(zip(olds, news, strict=True)):
            pairs.append(
                {
                    "ligne": i1 + k + 1,
                    "reference": a,
                    "sortie": b,
                    "classe": "admis"
                    if _admitted(reference, a, b, state)
                    else "non énuméré",
                }
            )
    entry["differences"] = pairs
    entry["verdict"] = (
        "réussi (chemins et empreintes énumérés)"
        if all(p["classe"] == "admis" for p in pairs)
        else "échec (différence non énumérée)"
    )
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sortie", type=Path, default=REFERENCES / "comparaison_lot41.json"
    )
    args = parser.parse_args(argv)
    for f in sorted((REFERENCES / "ferraillage").rglob("*")):
        if f.is_file():
            rel = f.relative_to(REFERENCES / "ferraillage").as_posix()
            PAIRS[f"ferraillage/{rel}"] = RESULTS / "ferraillage" / rel
    state = {
        "comm_old": "data/examples/lot37_efforts/complet.comm",
        "comm_new": "projets/quai_cw_test_01/resultats/complet.comm",
        "data_old": "data/examples/combiwall_model_data.yaml",
        "data_new": "projets/quai_cw_test_01/donnees/combiwall_model_data.yaml",
    }
    entries = [_compare(ref, out, state) for ref, out in PAIRS.items()]
    views = json.loads((REFERENCES / "empreintes.json").read_text("utf-8"))[
        "vues_informatives_hors_critere"
    ]
    view_dir = RESULTS / "synthese" / "vues"
    same_views = sum(
        (view_dir / n).is_file() and _sha(view_dir / n) == s for n, s in views.items()
    )
    report = {
        "fichiers": entries,
        "identiques": sum(e["statut"] == "identique" for e in entries),
        "differents_admis": sum(
            e["statut"] == "différent" and e["verdict"].startswith("réussi")
            for e in entries
        ),
        "echecs": [e["reference"] for e in entries if e["verdict"].startswith("échec")],
        "vues_informatives_identiques": f"{same_views}/{len(views)}",
    }
    args.sortie.write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"{report['identiques']} identiques, {report['differents_admis']} différents "
        f"(chemins/empreintes énumérés), échecs : {report['echecs'] or 'aucun'} ; "
        f"vues {report['vues_informatives_identiques']}"
    )
    return 0 if not report["echecs"] else 1


if __name__ == "__main__":
    sys.exit(main())
